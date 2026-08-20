import os
import json
import logging

import psycopg2
from psycopg2.extras import RealDictCursor
from psycopg2.pool import SimpleConnectionPool


logger = logging.getLogger("VES-DB")


# ------------------------------------------------------------------
# Database Configuration
# ------------------------------------------------------------------

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "ves_collector")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")

db_pool = None


# ------------------------------------------------------------------
# Connection Pool
# ------------------------------------------------------------------

def init_db_pool():
    """
    Initialize the PostgreSQL connection pool and create required tables.
    """

    global db_pool

    logger.info(
        "DB_POOL | START | Initializing PostgreSQL connection pool | "
        "host=%s | port=%s | database=%s | user=%s",
        DB_HOST,
        DB_PORT,
        DB_NAME,
        DB_USER,
    )

    try:
        db_pool = SimpleConnectionPool(
            minconn=1,
            maxconn=10,
            host=DB_HOST,
            port=DB_PORT,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
        )

        logger.info(
            "DB_POOL | SUCCESS | PostgreSQL connection pool established"
        )

        logger.info(
            "DB_POOL | NEXT_STEP | Verifying and creating database tables"
        )

        create_tables()

        logger.info(
            "DB_POOL | SUCCESS | Database initialization completed successfully"
        )

    except Exception:
        db_pool = None

        logger.exception(
            "DB_POOL | ERROR | Failed to initialize PostgreSQL connection pool | "
            "host=%s | port=%s | database=%s",
            DB_HOST,
            DB_PORT,
            DB_NAME,
        )


# ------------------------------------------------------------------
# Connection Handling
# ------------------------------------------------------------------

def get_db_connection():
    """
    Get a connection from the PostgreSQL connection pool.
    Returns None if the database is unavailable.
    """

    global db_pool

    logger.debug("DB_CONNECTION | START | Requesting database connection")

    if not db_pool:
        logger.info(
            "DB_CONNECTION | INFO | Connection pool not initialized. "
            "Attempting initialization."
        )

        init_db_pool()

    if not db_pool:
        logger.error(
            "DB_CONNECTION | ERROR | Cannot provide database connection. "
            "Connection pool initialization failed."
        )
        return None

    try:
        conn = db_pool.getconn()

        logger.debug(
            "DB_CONNECTION | SUCCESS | Database connection acquired from pool"
        )

        return conn

    except Exception:
        logger.exception(
            "DB_CONNECTION | ERROR | Failed to acquire connection from pool"
        )
        return None


def release_db_connection(conn):
    """
    Return a connection back to the PostgreSQL connection pool.
    """

    if not conn:
        logger.debug(
            "DB_CONNECTION | INFO | No connection provided for release"
        )
        return

    if not db_pool:
        logger.warning(
            "DB_CONNECTION | WARNING | Cannot release connection because "
            "connection pool is unavailable"
        )
        return

    try:
        db_pool.putconn(conn)

        logger.debug(
            "DB_CONNECTION | SUCCESS | Database connection returned to pool"
        )

    except Exception:
        logger.exception(
            "DB_CONNECTION | ERROR | Failed to return connection to pool"
        )


# ------------------------------------------------------------------
# Table Creation
# ------------------------------------------------------------------

def create_tables():
    """
    Create required PostgreSQL tables and indexes if they do not exist.
    """

    logger.info(
        "DB_TABLES | START | Verifying/creating required database tables"
    )

    conn = get_db_connection()

    if not conn:
        logger.error(
            "DB_TABLES | ERROR | Cannot create tables because no database "
            "connection is available"
        )
        return False

    try:
        with conn.cursor() as cur:

            logger.debug(
                "DB_TABLES | INFO | Executing CREATE TABLE and CREATE INDEX queries"
            )

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

                CREATE INDEX IF NOT EXISTS idx_ves_events_domain
                    ON ves_events(domain);

                CREATE INDEX IF NOT EXISTS idx_ves_events_source
                    ON ves_events(source_name);

                CREATE INDEX IF NOT EXISTS idx_ves_events_received
                    ON ves_events(received_at DESC);
            """)

            conn.commit()

            logger.info(
                "DB_TABLES | SUCCESS | Tables and indexes verified/created successfully"
            )

            return True

    except Exception:
        try:
            conn.rollback()

            logger.info(
                "DB_TABLES | INFO | Database transaction rolled back"
            )

        except Exception:
            logger.exception(
                "DB_TABLES | ERROR | Failed to rollback transaction"
            )

        logger.exception(
            "DB_TABLES | ERROR | Failed while creating/verifying database tables"
        )

        return False

    finally:
        release_db_connection(conn)


# ------------------------------------------------------------------
# Save Event
# ------------------------------------------------------------------

def save_event_to_db(event_body: dict):
    """
    Parses standard fields from any VES event domain
    and saves the raw JSON payload plus extracted metadata into PostgreSQL.
    """

    logger.info(
        "DB_SAVE_EVENT | START | Processing event for database storage"
    )

    try:
        # Support both wrapped:
        # {"event": {"commonEventHeader": ...}}
        # and flat structures.

        event_root = event_body.get("event", event_body)
        header = event_root.get("commonEventHeader", {})

        event_id = (
            header.get("eventId")
            or event_body.get("eventId")
        )

        source_name = (
            header.get("sourceName")
            or event_body.get("sourceName")
            or "unknown-source"
        )

        domain = (
            header.get("domain")
            or event_body.get("domain", "unknown")
        )

        event_name = (
            header.get("eventName")
            or event_body.get("eventName")
        )

        priority = (
            header.get("priority")
            or event_body.get("priority")
        )

        logger.info(
            "DB_SAVE_EVENT | INFO | Event extracted | "
            "event_id=%s | source=%s | domain=%s | event_name=%s",
            event_id,
            source_name,
            domain,
            event_name,
        )

    except Exception:
        logger.exception(
            "DB_SAVE_EVENT | ERROR | Failed while extracting event fields"
        )
        raise

    conn = get_db_connection()

    if not conn:
        error_message = (
            "Database connection unavailable. Event could not be saved."
        )

        logger.error(
            "DB_SAVE_EVENT | ERROR | %s | event_id=%s | domain=%s",
            error_message,
            event_id,
            domain,
        )

        raise RuntimeError(error_message)

    try:
        logger.debug(
            "DB_SAVE_EVENT | INFO | Inserting event into ves_events table | "
            "event_id=%s",
            event_id,
        )

        with conn.cursor() as cur:

            cur.execute("""
                INSERT INTO ves_events (
                    event_id,
                    source_name,
                    domain,
                    event_name,
                    priority,
                    raw_payload
                )
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (
                event_id,
                source_name,
                domain,
                event_name,
                priority,
                json.dumps(event_body),
            ))

            conn.commit()

        logger.info(
            "DB_SAVE_EVENT | SUCCESS | Event saved successfully | "
            "event_id=%s | source=%s | domain=%s",
            event_id,
            source_name,
            domain,
        )

    except Exception:
        try:
            conn.rollback()

            logger.warning(
                "DB_SAVE_EVENT | INFO | Transaction rolled back | "
                "event_id=%s",
                event_id,
            )

        except Exception:
            logger.exception(
                "DB_SAVE_EVENT | ERROR | Failed to rollback transaction | "
                "event_id=%s",
                event_id,
            )

        logger.exception(
            "DB_SAVE_EVENT | ERROR | Failed to save event | "
            "event_id=%s | source=%s | domain=%s",
            event_id,
            source_name,
            domain,
        )

        raise

    finally:
        release_db_connection(conn)


# ------------------------------------------------------------------
# Fetch Events
# ------------------------------------------------------------------

def fetch_events_from_db(
    limit=200,
    domain=None,
    source_name=None,
):
    """
    Fetch events from PostgreSQL with optional domain and source filters.
    """

    logger.info(
        "DB_FETCH_EVENTS | START | Fetching events | "
        "limit=%s | domain=%s | source=%s",
        limit,
        domain,
        source_name,
    )

    conn = get_db_connection()

    if not conn:
        logger.error(
            "DB_FETCH_EVENTS | ERROR | Cannot fetch events because "
            "database connection is unavailable"
        )
        return []

    try:
        with conn.cursor(
            cursor_factory=RealDictCursor
        ) as cur:

            query = """
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
            """

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

            logger.debug(
                "DB_FETCH_EVENTS | INFO | Executing event fetch query | "
                "filters=%s",
                conditions,
            )

            cur.execute(query, tuple(params))

            rows = cur.fetchall()

            logger.info(
                "DB_FETCH_EVENTS | INFO | Query completed | rows=%d",
                len(rows),
            )

            formatted_events = []

            for row in rows:
                formatted_events.append({
                    "collectorId": str(row["collector_id"]),
                    "eventId": row["event_id"],
                    "sourceName": row["source_name"],
                    "domain": row["domain"],
                    "eventName": row["event_name"],
                    "priority": row["priority"],
                    "receivedAt": (
                        row["received_at"].isoformat()
                        if row["received_at"]
                        else None
                    ),
                    "raw": row["raw_payload"],
                })

            logger.info(
                "DB_FETCH_EVENTS | SUCCESS | Successfully fetched %d event(s)",
                len(formatted_events),
            )

            return formatted_events

    except Exception:

        logger.exception(
            "DB_FETCH_EVENTS | ERROR | Failed while fetching events | "
            "domain=%s | source=%s | limit=%s",
            domain,
            source_name,
            limit,
        )

        return []

    finally:
        release_db_connection(conn)


# ------------------------------------------------------------------
# Statistics
# ------------------------------------------------------------------

def get_stats_from_db():
    """
    Fetch event statistics grouped by domain.
    """

    logger.info(
        "DB_STATS | START | Fetching event statistics from PostgreSQL"
    )

    conn = get_db_connection()

    if not conn:
        logger.error(
            "DB_STATS | ERROR | Cannot fetch statistics because "
            "database connection is unavailable"
        )
        return {}

    try:
        with conn.cursor(
            cursor_factory=RealDictCursor
        ) as cur:

            logger.debug(
                "DB_STATS | INFO | Fetching total event count"
            )

            cur.execute(
                "SELECT COUNT(*) AS total FROM ves_events"
            )

            total = cur.fetchone()["total"]

            logger.debug(
                "DB_STATS | INFO | Fetching event counts grouped by domain"
            )

            cur.execute("""
                SELECT
                    domain,
                    COUNT(*) AS count
                FROM ves_events
                GROUP BY domain
            """)

            domain_counts = {
                row["domain"] + "Events": row["count"]
                for row in cur.fetchall()
            }

            stats = {
                "totalEvents": total,
                "faultEvents": domain_counts.get(
                    "faultEvents",
                    0,
                ),
                "heartbeatEvents": domain_counts.get(
                    "heartbeatEvents",
                    0,
                ),
                "notificationEvents": domain_counts.get(
                    "notificationEvents",
                    0,
                ),
                "stateChangeEvents": domain_counts.get(
                    "stateChangeEvents",
                    0,
                ),
                "thresholdEvents": (
                    domain_counts.get(
                        "thresholdCrossingAlertEvents",
                        0,
                    )
                    or domain_counts.get(
                        "thresholdEvents",
                        0,
                    )
                ),
                "pnfRegistrationEvents": domain_counts.get(
                    "pnfRegistrationEvents",
                    0,
                ),
                "stndDefinedEvents": domain_counts.get(
                    "stndDefinedEvents",
                    0,
                ),
            }

            logger.info(
                "DB_STATS | SUCCESS | Statistics fetched successfully | "
                "total_events=%s | domains=%s",
                total,
                domain_counts,
            )

            return stats

    except Exception:

        logger.exception(
            "DB_STATS | ERROR | Failed while fetching database statistics"
        )

        return {}

    finally:
        release_db_connection(conn)