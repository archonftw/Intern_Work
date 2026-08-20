import os
import json
import logging
import psycopg2
from psycopg2.extras import RealDictCursor
from psycopg2.pool import SimpleConnectionPool

logger = logging.getLogger("VES-DB")

# Initialize connection pool using environment variables or defaults
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "ves_collector")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")

db_pool = None

def init_db_pool():
    global db_pool
    try:
        db_pool = SimpleConnectionPool(
            minconn=1,
            maxconn=10,
            host=DB_HOST,
            port=DB_PORT,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD
        )
        logger.info("PostgreSQL connection pool established successfully.")
        create_tables()
    except Exception as e:
        logger.error("Failed to connect to PostgreSQL: %s", e)

def get_db_connection():
    global db_pool
    if not db_pool:
        init_db_pool()
    if not db_pool:
        # Pool could not be created (Postgres unavailable). Return None to allow fallbacks.
        return None
    return db_pool.getconn()

def release_db_connection(conn):
    if db_pool and conn:
        db_pool.putconn(conn)

def create_tables():
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS ves_events (
                    collector_id SERIAL PRIMARY KEY,
                    event_id VARCHAR(255),
                    source_name VARCHAR(255),
                    domain VARCHAR(100),
                    event_name VARCHAR(255),
                    priority VARCHAR(50),
                    received_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    raw_payload JSONB NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_ves_events_domain ON ves_events(domain);
                CREATE INDEX IF NOT EXISTS idx_ves_events_source ON ves_events(source_name);
                CREATE INDEX IF NOT EXISTS idx_ves_events_received ON ves_events(received_at DESC);
            """)
            conn.commit()
            logger.info("Database tables verified/created successfully.")
    except Exception as e:
        conn.rollback()
        logger.error("Error creating database tables: %s", e)
    finally:
        release_db_connection(conn)

def save_event_to_db(event_body: dict):
    """
    Parses standard fields from any VES event domain (handling both wrapped and unwrapped JSON structures)
    and saves raw JSON payload + extracted indexes into PostgreSQL.
    """
    # Support both wrapped {"event": {"commonEventHeader": ...}} and flat structures
    event_root = event_body.get("event", event_body)
    header = event_root.get("commonEventHeader", {})

    event_id = header.get("eventId") or event_body.get("eventId")
    source_name = header.get("sourceName") or event_body.get("sourceName") or "unknown-source"
    domain = header.get("domain") or event_body.get("domain", "unknown")
    event_name = header.get("eventName") or event_body.get("eventName")
    priority = header.get("priority") or event_body.get("priority")

    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO ves_events (event_id, source_name, domain, event_name, priority, raw_payload)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (
                event_id,
                source_name,
                domain,
                event_name,
                priority,
                json.dumps(event_body)
            ))
            conn.commit()
    except Exception as e:
        conn.rollback()
        logger.error("Failed to save event to PostgreSQL: %s", e)
        raise e
    finally:
        release_db_connection(conn)

def fetch_events_from_db(limit=200, domain=None, source_name=None):
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            query = "SELECT collector_id, event_id, source_name, domain, event_name, priority, received_at, raw_payload FROM ves_events"
            params = []
            conditions = []

            if domain:
                conditions.append("domain = %s")
                params.append(domain)
            if source_name:
                conditions.append("source_name = %s")
                params.append(source_name)

            if conditions:
                query += " WHERE " + " AND ".join(conditions)

            query += " ORDER BY received_at DESC LIMIT %s"
            params.append(limit)

            cur.execute(query, tuple(params))
            rows = cur.fetchall()

            # Format to match existing frontend expectations (mapping raw_payload -> raw, timestamps, etc.)
            formatted_events = []
            for row in rows:
                formatted_events.append({
                    "collectorId": str(row["collector_id"]),
                    "eventId": row["event_id"],
                    "sourceName": row["source_name"],
                    "domain": row["domain"],
                    "eventName": row["event_name"],
                    "priority": row["priority"],
                    "receivedAt": row["received_at"].isoformat() if row["received_at"] else None,
                    "raw": row["raw_payload"]
                })
            return formatted_events
    except Exception as e:
        logger.error("Error fetching events from PostgreSQL: %s", e)
        return []
    finally:
      release_db_connection(conn)

def get_stats_from_db():
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT COUNT(*) as total FROM ves_events")
            total = cur.fetchone()["total"]

            cur.execute("SELECT domain, COUNT(*) as count FROM ves_events GROUP BY domain")
            domain_counts = {row["domain"] + "Events": row["count"] for row in cur.fetchall()}

            stats = {
                "totalEvents": total,
                "faultEvents": domain_counts.get("faultEvents", 0),
                "heartbeatEvents": domain_counts.get("heartbeatEvents", 0),
                "notificationEvents": domain_counts.get("notificationEvents", 0),
                "stateChangeEvents": domain_counts.get("stateChangeEvents", 0),
                "thresholdEvents": domain_counts.get("thresholdCrossingAlertEvents", 0) or domain_counts.get("thresholdEvents", 0),
                "pnfRegistrationEvents": domain_counts.get("pnfRegistrationEvents", 0),
                "stndDefinedEvents": domain_counts.get("stndDefinedEvents", 0)
            }
            return stats
    except Exception as e:
        logger.error("Error fetching stats from PostgreSQL: %s", e)
        return {}
    finally:
        release_db_connection(conn)