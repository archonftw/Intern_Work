from flask import Blueprint, jsonify

config_bp = Blueprint("config", __name__)


@config_bp.route("/api/config", methods=["GET"])
def get_config():

    # Temporary response to test dashboard connection
    return jsonify({
        "status": "ok",
        "message": "Configuration API working",
        "device": "netopeer2"
    })