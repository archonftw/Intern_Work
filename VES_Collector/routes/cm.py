from flask import Blueprint, request, jsonify
from services.netconf_service import NetconfManager

cm_bp = Blueprint("cm", __name__, url_prefix="/api/cm")
netconf = NetconfManager()


def _resolve_device_id(data=None):
    if data and isinstance(data, dict) and data.get("device_id"):
        return data["device_id"]
    if netconf.sessions:
        return next(iter(netconf.sessions))
    return None


@cm_bp.route("/connect", methods=["POST"])
def connect():
    data = request.json or {}
    required = ["device_id", "host", "username"]
    if not all(k in data for k in required):
        return jsonify({"error": f"Missing required connection fields: {required}"}), 400

    try:
        res = netconf.connect(
            device_id=data["device_id"],
            host=data["host"],
            port=int(data.get("port", 830)),
            username=data["username"],
            key_filename=data.get("key_filename")
        )
        return jsonify(res), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@cm_bp.route("/sessions", methods=["GET"])
def list_sessions():
    return jsonify({"connected_devices": list(netconf.sessions.keys())}), 200


# 1. FIX FOR STEP 3: Add missing capabilities route
@cm_bp.route("/capabilities/<device_id>", methods=["GET"])
def capabilities(device_id):
    try:
        result = netconf.capabilities(device_id)
        return jsonify({"capabilities": result}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@cm_bp.route("/modules", methods=["GET"])
def get_modules():
    device_id = request.args.get("device_id") or _resolve_device_id()
    if not device_id:
        return jsonify({"error": "No active NETCONF session connected"}), 400

    try:
        modules = netconf.modules(device_id)
        return jsonify(modules), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@cm_bp.route("/config", methods=["GET", "POST"])
def manage_config():
    if request.method == "GET":
        module = request.args.get("module")
        datastore = request.args.get("datastore", "running")
        device_id = request.args.get("device_id") or _resolve_device_id()

        if not device_id:
            return jsonify({"error": "No active NETCONF session connected"}), 400

        try:
            config_xml = netconf.get_config(device_id, source=datastore, module=module)
            return jsonify({
                "device_id": device_id,
                "module": module,
                "datastore": datastore,
                "config": config_xml
            }), 200
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    elif request.method == "POST":
        data = request.json or {}
        device_id = data.get("device_id") or _resolve_device_id()
        datastore = data.get("datastore", "candidate")
        config_payload = data.get("config")

        if not device_id:
            return jsonify({"error": "No active NETCONF session connected"}), 400
        if not config_payload:
            return jsonify({"error": "Missing 'config' XML payload"}), 400

        try:
            # FIX: Key is named 'config', not 'config_xml'
            edit_res = netconf.edit_config(
                device_id, 
                config=config_payload, 
                target=datastore
            )

            return jsonify({
                "status": "success",
                "device_id": device_id,
                "datastore": datastore,
                "edit_result": edit_res
            }), 200
        except Exception as e:
            return jsonify({"error": str(e)}), 500

@cm_bp.route("/validate", methods=["POST"])
def validate_config():
    data = request.json or {}
    device_id = data.get("device_id") or _resolve_device_id()
    datastore = data.get("datastore", "candidate")

    if not device_id:
        return jsonify({"error": "No active NETCONF session connected"}), 400

    try:
        val_res = netconf.validate(device_id, source=datastore)
        return jsonify({"status": "valid", "device_id": device_id, "result": val_res}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@cm_bp.route("/commit", methods=["POST"])
def commit_config():
    data = request.json or {}
    device_id = data.get("device_id") or _resolve_device_id()

    if not device_id:
        return jsonify({"error": "No active NETCONF session connected"}), 400

    try:
        res = netconf.commit(device_id)
        return jsonify({"status": "committed", "device_id": device_id, "result": res}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@cm_bp.route("/discard", methods=["POST"])
def discard_config():
    data = request.json or {}
    device_id = data.get("device_id") or _resolve_device_id()

    if not device_id:
        return jsonify({"error": "No active NETCONF session connected"}), 400

    try:
        res = netconf.discard_changes(device_id)
        return jsonify({"status": "discarded", "device_id": device_id, "result": res}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@cm_bp.route("/disconnect", methods=["POST"])
def disconnect():
    data = request.json or {}
    device_id = data.get("device_id") or _resolve_device_id()

    if not device_id:
        return jsonify({"error": "No active session to disconnect"}), 400

    res = netconf.disconnect(device_id)
    return jsonify(res), 200