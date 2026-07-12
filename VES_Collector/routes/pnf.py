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
# Get all PNF registrations
# ==========================================================

@pnf_bp.route("/api/pnf", methods=["GET"])
def get_pnfs():
    return jsonify(get_all_pnfs())


# ==========================================================
# Search
# ==========================================================

@pnf_bp.route("/api/pnf/search", methods=["GET"])
def search():

    query = request.args.get("q", "")

    return jsonify(search_pnfs(query))


# ==========================================================
# Forward configuration
# ==========================================================

@pnf_bp.route("/api/pnf/config", methods=["GET"])
def config():

    return jsonify(get_forward_config())


@pnf_bp.route("/api/pnf/config", methods=["POST"])
def update_config():

    body = request.json or {}

    config = update_forward_config(
        host=body.get("host"),
        port=body.get("port"),
        path=body.get("path")
    )

    return jsonify({
        "message": "PNF forwarding configuration updated.",
        "config": config
    })


# ==========================================================
# Forward all stored PNF registrations
# ==========================================================

@pnf_bp.route("/api/pnf/forward", methods=["POST"])
def forward():

    result = forward_all_pnfs()

    return jsonify(result)