from flask import Blueprint, jsonify, request
from config import MAX_GLOBAL_EVENT_STORE
from services.db_service import get_db_connection, release_db_connection
from storage import memory as storage_memory
from psycopg2.extras import RealDictCursor
import logging

logger = logging.getLogger("VES-COLLECTOR")

stats_bp = Blueprint(
    "stats",
    __name__
)

@stats_bp.route("/api/stats")
def stats():
    conn = get_db_connection()
    if not conn:
        # Fallback to in-memory event store
        events = storage_memory.EVENT_STORE
        total_events = len(events)
        domain_counts = {}
        critical_faults = major_faults = warning_faults = 0
        for ev in events:
            domain = (ev.get('domain') or ev.get('event', {}).get('commonEventHeader', {}).get('domain')) or 'unknown'
            domain_counts[domain] = domain_counts.get(domain, 0) + 1
            if domain == 'fault':
                raw = ev.get('raw') or ev.get('event') or ev
                fault_fields = raw.get('faultFields') or raw.get('event', {}).get('faultFields', {})
                severity = (fault_fields.get('eventSeverity') or '').upper()
                if severity == 'CRITICAL':
                    critical_faults += 1
                elif severity == 'MAJOR':
                    major_faults += 1
                elif severity == 'WARNING':
                    warning_faults += 1

        return jsonify({
            "totalEvents": total_events,
            "faultEvents": domain_counts.get("fault", 0),
            "measurementEvents": domain_counts.get("measurement", 0),
            "heartbeatEvents": domain_counts.get("heartbeat", 0),
            "notificationEvents": domain_counts.get("notification", 0),
            "stateChangeEvents": domain_counts.get("stateChange", 0),
            "thresholdEvents": domain_counts.get("thresholdCrossingAlert", 0),
            "pnfRegistrationEvents": domain_counts.get("pnfRegistration", 0),
            "stndDefinedEvents": domain_counts.get("stndDefined", 0),
            "criticalFaults": critical_faults,
            "majorFaults": major_faults,
            "warningFaults": warning_faults
        })

    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # Total events count
            cur.execute("SELECT COUNT(*) as total FROM ves_events;")
            total_events = cur.fetchone()["total"]

            # Domain breakdown counts
            cur.execute("SELECT domain, COUNT(*) as count FROM ves_events GROUP BY domain;")
            domain_counts = {row["domain"]: row["count"] for row in cur.fetchall()}

            # Fault severities breakdown
            cur.execute("SELECT raw_payload FROM ves_events WHERE domain = 'fault';")
            fault_rows = cur.fetchall()

            critical_faults = 0
            major_faults = 0
            warning_faults = 0

            for row in fault_rows:
                raw = row["raw_payload"] or {}
                # Handle both wrapped and unwrapped fault field structures
                fault_fields = raw.get("faultFields") or raw.get("event", {}).get("faultFields", {})
                severity = fault_fields.get("eventSeverity", "").upper()
                
                if severity == "CRITICAL":
                    critical_faults += 1
                elif severity == "MAJOR":
                    major_faults += 1
                elif severity == "WARNING":
                    warning_faults += 1

            return jsonify({
                "totalEvents": total_events,
                "faultEvents": domain_counts.get("fault", 0),
                "measurementEvents": domain_counts.get("measurement", 0),
                "heartbeatEvents": domain_counts.get("heartbeat", 0),
                "notificationEvents": domain_counts.get("notification", 0),
                "stateChangeEvents": domain_counts.get("stateChange", 0),
                "thresholdEvents": domain_counts.get("thresholdCrossingAlert", 0),
                "pnfRegistrationEvents": domain_counts.get("pnfRegistration", 0),
                "stndDefinedEvents": domain_counts.get("stndDefined", 0),
                "criticalFaults": critical_faults,
                "majorFaults": major_faults,
                "warningFaults": warning_faults
            })
    except Exception as e:
        logger.error("Failed to fetch stats from DB: %s", e)
        return jsonify({"error": str(e)}), 500
    finally:
        release_db_connection(conn)


@stats_bp.route("/api/domains")
def domains():
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT domain, COUNT(*) as count FROM ves_events GROUP BY domain;")
            counts = {row["domain"]: row["count"] for row in cur.fetchall()}
            return jsonify(counts)
    except Exception as e:
        logger.error("Failed to fetch domain counts from DB: %s", e)
        return jsonify({"error": str(e)}), 500
    finally:
        release_db_connection(conn)


@stats_bp.route("/api/events")
def api_events():
    try:
        limit = int(request.args.get("limit", 100))
    except (TypeError, ValueError):
        limit = 100

    limit = max(1, min(limit, MAX_GLOBAL_EVENT_STORE))

    conn = get_db_connection()
    if not conn:
        # Fallback to in-memory event store
        from storage import memory as storage_memory
        rows = storage_memory.EVENT_STORE[:limit]
        events = []
        for row in rows:
            raw = row.get('raw') or {}
            received_str = row.get('receivedAt') or row.get('received_at')
            event_obj = {
                "collectorId": str(row.get('collectorId') or ''),
                "collector_id": row.get('collectorId') or None,
                "eventId": row.get('eventId'),
                "event_id": row.get('eventId'),
                "sourceName": row.get('sourceName'),
                "source_name": row.get('sourceName'),
                "domain": row.get('domain'),
                "eventName": row.get('eventName'),
                "event_name": row.get('eventName'),
                "priority": row.get('priority'),
                "receivedAt": received_str,
                "received_at": received_str,
                "raw": raw,
                "commonEventHeader": raw.get('event', {}).get('commonEventHeader', {
                    "domain": row.get('domain'),
                    "eventId": row.get('eventId'),
                    "sourceName": row.get('sourceName'),
                    "eventName": row.get('eventName'),
                    "priority": row.get('priority')
                })
            }
            events.append(event_obj)
        return jsonify(events)

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
                ORDER BY received_at DESC 
                LIMIT %s;
            """, (limit,))
            rows = cur.fetchall()

            events = []
            for row in rows:
                raw = row["raw_payload"] or {}
                received_str = row["received_at"].isoformat() if row["received_at"] else None
                
                # Provide dual-key support (camelCase & snake_case) for the frontend dashboard
                event_obj = {
                    "collectorId": str(row["collector_id"]),
                    "collector_id": row["collector_id"],
                    "eventId": row["event_id"],
                    "event_id": row["event_id"],
                    "sourceName": row["source_name"],
                    "source_name": row["source_name"],
                    "domain": row["domain"],
                    "eventName": row["event_name"],
                    "event_name": row["event_name"],
                    "priority": row["priority"],
                    "receivedAt": received_str,
                    "received_at": received_str,
                    "raw": raw,
                    "commonEventHeader": raw.get("event", {}).get("commonEventHeader", {
                        "domain": row["domain"],
                        "eventId": row["event_id"],
                        "sourceName": row["source_name"],
                        "eventName": row["event_name"],
                        "priority": row["priority"]
                    })
                }
                events.append(event_obj)

            return jsonify(events)
    except Exception as e:
        logger.error("Failed to fetch events from DB: %s", e)
        return jsonify({"error": str(e)}), 500
    finally:
        release_db_connection(conn)


@stats_bp.route("/healthcheck")
def health():
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM ves_events;")
            event_count = cur.fetchone()[0]

            cur.execute("SELECT COUNT(DISTINCT source_name) FROM ves_events WHERE source_name IS NOT NULL AND source_name != '';")
            device_count = cur.fetchone()[0]

            return jsonify({
                "status": "UP",
                "events": event_count,
                "devices": device_count
            })
    except Exception as e:
        logger.error("Healthcheck DB query failed: %s", e)
        return jsonify({
            "status": "DEGRADED",
            "error": str(e)
        }), 500
    finally:
        release_db_connection(conn)