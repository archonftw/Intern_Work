from flask import Blueprint, jsonify
from services.db_service import get_db_connection, release_db_connection
from storage import memory as storage_memory
from psycopg2.extras import RealDictCursor
import logging

logger = logging.getLogger("VES-COLLECTOR")

devices_bp = Blueprint(
    "devices",
    __name__
)

def error(code: int, msg: str):
    return jsonify({"error": msg}), code

@devices_bp.route("/api/devices")
def api_devices():
    """
    Retrieves aggregated device/source information directly from PostgreSQL.
    """
    conn = get_db_connection()
    if not conn:
        # Fallback to in-memory event store
        events = storage_memory.EVENT_STORE
        devices_map = {}
        for ev in events:
            src = ev.get('sourceName') or ev.get('source_name') or ev.get('event', {}).get('commonEventHeader', {}).get('sourceName')
            if not src:
                continue
            entry = devices_map.setdefault(src, {"deviceId": src, "lastSeen": None, "eventCount": 0, "faultCount": 0, "thresholdCount": 0, "is_registered": 0})
            entry["eventCount"] += 1
            # domain may be at top or in event.commonEventHeader.domain
            domain = ev.get('domain') or ev.get('event', {}).get('commonEventHeader', {}).get('domain')
            if domain == 'fault': entry['faultCount'] += 1
            if domain == 'thresholdCrossingAlert': entry['thresholdCount'] += 1
            if domain == 'pnfRegistration': entry['is_registered'] = 1
            # update lastSeen
            ts = ev.get('receivedAt') or ev.get('received_at')
            if ts:
                entry['lastSeen'] = ts

        devices = []
        for v in devices_map.values():
            devices.append({
                "deviceId": v["deviceId"],
                "status": "live",
                "registered": bool(v.get("is_registered")),
                "vendor": "Unknown",
                "model": "Unknown",
                "lastSeen": v.get("lastSeen"),
                "eventCount": v.get("eventCount", 0),
                "faultCount": v.get("faultCount", 0),
                "thresholdCount": v.get("thresholdCount", 0)
            })
        devices.sort(key=lambda d: d.get('lastSeen') or '', reverse=True)
        return jsonify(devices), 200

    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT 
                    source_name AS device_id,
                    MAX(received_at) AS last_seen,
                    COUNT(*) AS event_count,
                    COUNT(CASE WHEN domain = 'fault' THEN 1 END) AS fault_count,
                    COUNT(CASE WHEN domain = 'thresholdCrossingAlert' THEN 1 END) AS threshold_count,
                    MAX(CASE WHEN domain = 'pnfRegistration' THEN 1 ELSE 0 END) AS is_registered
                FROM ves_events
                WHERE source_name IS NOT NULL AND source_name != ''
                GROUP BY source_name
                ORDER BY last_seen DESC;
            """)
            rows = cur.fetchall()

            devices = []
            for row in rows:
                devices.append({
                    "deviceId": row["device_id"],
                    "status": "live",
                    "registered": bool(row["is_registered"]),
                    "vendor": "Unknown",
                    "model": "Unknown",
                    "lastSeen": row["last_seen"].isoformat() if row["last_seen"] else None,
                    "eventCount": row["event_count"],
                    "faultCount": row["fault_count"],
                    "thresholdCount": row["threshold_count"]
                })
            return jsonify(devices), 200
    except Exception as e:
        logger.error("Database error in api_devices: %s", e)
        return error(500, f"Database error: {str(e)}")
    finally:
        release_db_connection(conn)


@devices_bp.route("/api/device/<device_id>")
def api_device(device_id):
    """
    Retrieves detailed summary statistics for a specific device from PostgreSQL.
    """
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT 
                    source_name AS device_id,
                    MAX(received_at) AS last_seen,
                    COUNT(*) AS event_count,
                    MAX(CASE WHEN domain = 'pnfRegistration' THEN 1 ELSE 0 END) AS is_registered
                FROM ves_events
                WHERE source_name = %s
                GROUP BY source_name;
            """, (device_id,))
            row = cur.fetchone()

            if not row:
                return error(404, "Device not found")

            # Fetch faults and thresholds safely
            cur.execute("""
                SELECT domain, raw_payload FROM ves_events 
                WHERE source_name = %s AND domain IN ('fault', 'thresholdCrossingAlert')
                ORDER BY received_at DESC;
            """, (device_id,))
            rows = cur.fetchall()

            faults = []
            thresholds = []
            for r in rows:
                raw = r["raw_payload"] or {}
                if r["domain"] == "fault":
                    faults.append(raw)
                elif r["domain"] == "thresholdCrossingAlert":
                    thresholds.append(raw)

            device_data = {
                "deviceId": row["device_id"],
                "status": "live",
                "registered": bool(row["is_registered"]),
                "vendor": "Unknown",
                "model": "Unknown",
                "lastSeen": row["last_seen"].isoformat() if row["last_seen"] else None,
                "eventCount": row["event_count"],
                "faults": faults,
                "thresholds": thresholds
            }
            return jsonify(device_data), 200
    except Exception as e:
        logger.error("Database error in api_device: %s", e)
        return error(500, f"Database error: {str(e)}")
    finally:
        release_db_connection(conn)


@devices_bp.route("/api/device/<device_id>/events")
def api_device_events(device_id):
    """
    Retrieves all formatted events associated with a specific device from PostgreSQL.
    """
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT 
                    collector_id, 
                    event_id, 
                    source_name, 
                    domain, 
                    event_name, 
                    priority, 
                    received_at, 
                    raw_payload 
                FROM ves_events 
                WHERE source_name = %s 
                ORDER BY received_at DESC 
                LIMIT 100;
            """, (device_id,))
            rows = cur.fetchall()

            events = []
            for row in rows:
                raw = row["raw_payload"] or {}
                received_str = row["received_at"].isoformat() if row["received_at"] else None
                
                # Format to match what the frontend device modal expects
                event_obj = {
                    "collectorId": str(row["collector_id"]),
                    "eventId": row["event_id"],
                    "sourceName": row["source_name"],
                    "domain": row["domain"],
                    "eventName": row["event_name"],
                    "priority": row["priority"],
                    "receivedAt": received_str,
                    "commonEventHeader": raw.get("event", {}).get("commonEventHeader", {
                        "domain": row["domain"],
                        "eventId": row["event_id"],
                        "sourceName": row["source_name"],
                        "eventName": row["event_name"]
                    }),
                    "raw": raw
                }
                events.append(event_obj)

            return jsonify(events), 200
    except Exception as e:
        logger.error("Database error in api_device_events: %s", e)
        return error(500, f"Database error: {str(e)}")
    finally:
        release_db_connection(conn)