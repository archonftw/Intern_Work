from flask import Blueprint, jsonify, request

from services.pnf_service import (
    get_all_pnfs,
    search_pnfs,
    get_forward_config,
    update_forward_config,
    forward_all_pnfs
)

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


# ==========================================================
# Get all PNF registrations
# ==========================================================

@pnf_bp.route("/api/pnf", methods=["GET"])
def get_pnfs():
    return jsonify(_mask_pnfs(get_all_pnfs()))


# ==========================================================
# Search
# ==========================================================

@pnf_bp.route("/api/pnf/search", methods=["GET"])
def search():

    query = request.args.get("q", "")

    return jsonify(_mask_pnfs(search_pnfs(query)))


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
        path=body.get("path")
    )

    return jsonify({
        "message": "PNF forwarding configuration updated.",
        "config": config
    })


# ==========================================================
# Forward all stored PNF registrations
# (retry/backfill utility — new events are already forwarded
# automatically as they arrive; this exists for re-sending
# records that failed, e.g. before a destination was configured)
# ==========================================================

@pnf_bp.route("/api/pnf/forward", methods=["POST"])
def forward():

    result = forward_all_pnfs()

    return jsonify(result)