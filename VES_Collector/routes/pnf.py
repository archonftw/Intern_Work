from flask import Blueprint, request, jsonify
from services.db_service import get_db_connection, release_db_connection
from psycopg2.extras import RealDictCursor
import logging

from services.pnf_service import (
    get_forward_config,
    update_forward_config,
    forward_all_pnfs
)
from storage import memory as storage_memory

logger = logging.getLogger("VES-COLLECTOR")

pnf_bp = Blueprint("pnf", __name__)


# ==========================================================
# Helpers
# ==========================================================

def _mask_pnf(pnf):
    """
    Returns a copy of a PNF record safe to expose over the API —
    credentials are masked the same way they are before logging.
    """
    masked = dict(pnf)
    if masked.get("password"):
        masked["password"] = "********"
    return masked


def _mask_pnfs(pnfs):
    return [_mask_pnf(p) for p in pnfs]


def _get_all_pnfs_from_db():
    """
    Extracts PNF registration records from stored pnfRegistration events in PostgreSQL.
    """
    conn = get_db_connection()
    if not conn:
        # Fallback: read from in-memory PNF store
        return list(storage_memory.PNF_STORE)

    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT received_at, source_name, raw_payload 
                FROM ves_events 
                WHERE domain = 'pnfRegistration'
                ORDER BY received_at DESC;
            """)
            rows = cur.fetchall()

            pnfs = []
            for row in rows:
                raw = row["raw_payload"]
                fields = raw.get("pnfRegistrationFields", {})
                pnfs.append({
                    "receivedTime": row["received_at"].isoformat() if row["received_at"] else None,
                    "unitType": fields.get("pnfId") or row["source_name"],
                    "vendorName": fields.get("vendorName"),
                    "modelNumber": fields.get("modelNumber"),
                    "oamV4IpAddress": fields.get("oamV4IpAddress"),
                    "protocol": "NETCONF",
                    "username": fields.get("serialNumber"),
                    "forwarded": True,
                    "forwardedAt": row["received_at"].isoformat() if row["received_at"] else None
                })
            return pnfs
    except Exception as e:
        logger.error("Failed to fetch PNF records from database: %s", e)
        return []
    finally:
        release_db_connection(conn)


def _search_pnfs_from_db(query):
    pnfs = _get_all_pnfs_from_db()
    if not query:
        return pnfs
    q = query.lower()
    return [
        p for p in pnfs 
        if q in (p.get("unitType") or "").lower() 
        or q in (p.get("vendorName") or "").lower() 
        or q in (p.get("oamV4IpAddress") or "").lower()
    ]


# ==========================================================
# Get all PNF registrations
# ==========================================================

@pnf_bp.route("/api/pnf", methods=["GET"])
def get_pnfs():
    return jsonify(_mask_pnfs(_get_all_pnfs_from_db()))


# ==========================================================
# Search
# ==========================================================

@pnf_bp.route("/api/pnf/search", methods=["GET"])
def search():
    query = request.args.get("q", "")
    return jsonify(_mask_pnfs(_search_pnfs_from_db(query)))


# ==========================================================
# Forward configuration
# ==========================================================

@pnf_bp.route("/api/pnf/config", methods=["GET"])
def config():
    return jsonify(get_forward_config())


@pnf_bp.route("/api/pnf/config", methods=["POST"])
def update_config():
    body = request.json or {}

    port = body.get("port")
    if port is not None and port != "":
        try:
            port = int(port)
        except (TypeError, ValueError):
            return jsonify({
                "error": "port must be a valid integer"
            }), 400
    else:
        port = None

    config = update_forward_config(
        host=body.get("host"),
        port=port,
        username=body.get("username"),
        key_filename=body.get("key_filename"),
    )

    return jsonify({
        "message": "PNF NETCONF forwarding configuration updated.",
        "config": config
    })


# ==========================================================
# Forward all stored PNF registrations
# ==========================================================

@pnf_bp.route("/api/pnf/forward", methods=["POST"])
def forward():
    result = forward_all_pnfs()
    return jsonify(result)