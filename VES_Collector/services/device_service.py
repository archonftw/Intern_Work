from datetime import datetime, timezone
from typing import Any, Dict
from services.db_service import get_db_connection, release_db_connection
from psycopg2.extras import RealDictCursor
import logging

logger = logging.getLogger("VES-COLLECTOR")

def get_device_id(event: Dict[str, Any]) -> str:
    header = event.get("commonEventHeader", {})
    return (
        header.get("reportingEntityName")
        or header.get("sourceName")
        or "UNKNOWN_DEVICE"
    )

def get_or_create_device(device_id: str):
    """
    Retrieves device details aggregated dynamically from PostgreSQL events.
    """
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # Check if device has registration or events in DB
            cur.execute("""
                SELECT 
                    source_name AS device_id,
                    MAX(received_at) AS last_seen,
                    COUNT(*) AS event_count,
                    COUNT(CASE WHEN domain = 'fault' THEN 1 END) AS fault_count,
                    COUNT(CASE WHEN domain = 'thresholdCrossingAlert' THEN 1 END) AS threshold_count,
                    MAX(CASE WHEN domain = 'pnfRegistration' THEN 1 ELSE 0 END) AS is_registered
                FROM ves_events
                WHERE source_name = %s
                GROUP BY source_name;
            """, (device_id,))
            row = cur.fetchone()

            # Check vendor/model from pnfRegistration if available
            cur.execute("""
                SELECT raw_payload FROM ves_events 
                WHERE source_name = %s AND domain = 'pnfRegistration'
                ORDER BY received_at DESC LIMIT 1;
            """, (device_id,))
            pnf_row = cur.fetchone()
            
            vendor = None
            model = None
            if pnf_row:
                fields = pnf_row["raw_payload"].get("pnfRegistrationFields", {})
                vendor = fields.get("vendorName")
                model = fields.get("modelNumber")

            if not row:
                return {
                    "deviceId": device_id,
                    "status": "ONLINE",
                    "registered": False,
                    "vendor": vendor,
                    "model": model,
                    "lastSeen": None,
                    "eventCount": 0,
                    "heartbeat": None,
                    "heartbeatIntervalSec": None,
                    "faults": [],
                    "notifications": [],
                    "stateChanges": [],
                    "thresholds": [],
                    "files": [],
                    "events": []
                }

            # Fetch specific domain events for completeness
            cur.execute("""
                SELECT raw_payload, domain FROM ves_events 
                WHERE source_name = %s 
                ORDER BY received_at DESC LIMIT 100;
            """, (device_id,))
            event_rows = cur.fetchall()

            all_raw_events = [r["raw_payload"] for r in event_rows]
            faults = [r["raw_payload"] for r in event_rows if r["domain"] == 'fault']
            notifications = [r["raw_payload"] for r in event_rows if r["domain"] == 'notification']
            state_changes = [r["raw_payload"] for r in event_rows if r["domain"] == 'stateChange']
            thresholds = [r["raw_payload"] for r in event_rows if r["domain"] == 'thresholdCrossingAlert']
            
            heartbeat_row = next((r["raw_payload"] for r in event_rows if r["domain"] == 'heartbeat'), None)
            hb_interval = None
            if heartbeat_row:
                hb_interval = heartbeat_row.get("event", {}).get("heartbeatFields", {}).get("heartbeatInterval")

            return {
                "deviceId": row["device_id"],
                "status": "ONLINE",
                "registered": bool(row["is_registered"]),
                "vendor": vendor,
                "model": model,
                "lastSeen": row["last_seen"].isoformat() if row["last_seen"] else None,
                "eventCount": row["event_count"],
                "heartbeat": heartbeat_row,
                "heartbeatIntervalSec": hb_interval,
                "faults": faults,
                "notifications": notifications,
                "stateChanges": state_changes,
                "thresholds": thresholds,
                "files": [],
                "events": all_raw_events
            }
    except Exception as e:
        logger.error("Database error in get_or_create_device: %s", e)
        return {"deviceId": device_id, "status": "ERROR", "events": []}
    finally:
        release_db_connection(conn)


def update_device(event: Dict[str, Any]):
    """
    Since incoming events are already saved directly to PostgreSQL via 
    save_event_to_db(body) during ingestion, update_device acts as a helper 
    or can be used for any localized state updates if required.
    """
    device_id = get_device_id(event)
    # The database already stores the event via ingestion pipeline.
    # This keeps compatibility with any service calls expecting update_device.
    return get_or_create_device(device_id)