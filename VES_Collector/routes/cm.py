from flask import Blueprint, request, jsonify
from services.netconf_service import netconf_service as netconf
import json


cm_bp = Blueprint("cm", __name__, url_prefix="/api/cm")


def _resolve_device_id(data=None):
    #This function tells which device sent the data
    if data and isinstance(data, dict) and data.get("device_id"):
        return data["device_id"]
    if getattr(netconf, "sessions", None):
        return next(iter(netconf.sessions))
    return None


#This routes connects out VES collector to a network device
@cm_bp.route("/connect", methods=["POST"])
def connect():
    data = request.json or {}
    required = ["device_id", "host", "username"]
    if not all(k in data for k in required):
        print("Some fields are missing to connect the device")
        return jsonify({"error": f"Missing required connection fields: {required}"}), 400

    try:
        res = netconf.connect(
            device_id=data["device_id"],
            host=data["host"],
            port=int(data.get("port", 830)),
            username=data["username"],
            key_filename=data.get("key_filename"),
            key_passphrase=data.get("key_passphrase")
        )
        print("Device connected Successfully")
        return jsonify(res), 200
    except Exception as e:
        print("Error in connecting to device")
        return jsonify({"error": str(e)}), 500

#Hit this endpoint to know list of all device currently maintaining a netconf session
@cm_bp.route("/sessions", methods=["GET"])
def list_sessions():
    sessions = getattr(netconf, "sessions", {}) 
    print("The online sessions are",sessions)
    return jsonify({"connected_devices": list(sessions.keys())}), 200


#Tells all the modules,protofols, and features a device supports. Give it device_id in the URL to know
@cm_bp.route("/capabilities/<device_id>", methods=["GET"])
def capabilities(device_id):
    try:
        result = netconf.capabilities(device_id)
        print("The Capabilities of device",device_id,"are :",result)
        return jsonify({"capabilities": result}), 200
    except Exception as e:
        print("Error in retrieving capabilities of device ",device_id)
        return jsonify({"error": str(e)}), 500


@cm_bp.route("/modules", methods=["GET"])
def get_modules():
    device_id = request.args.get("device_id") or _resolve_device_id()
    if not device_id:
        return jsonify({"error": "No active NETCONF session connected"}), 400

    try:
        modules = netconf.modules(device_id)
        print("Log: Netconf modules fetched Successfully")
        print(json.dumps(modules,indent=2)) #prints moddules neatly

        return jsonify(modules), 200
    except Exception as e:
        print("Error in fetching module")
        return jsonify({"error": str(e)}), 500


#Dual purpose endpoint for reading and changing device configurations
@cm_bp.route("/config", methods=["GET", "POST"])
def manage_config():
    #U send it device id and datastore and model
    if request.method == "GET":
        module = request.args.get("module")
        datastore = request.args.get("datastore", "running")
        device_id = request.args.get("device_id") or _resolve_device_id()

        if not device_id:
            print("No device id found")
            return jsonify({"error": "No active NETCONF session connected"}), 400

        try:
            config_xml = netconf.get_config(device_id, source=datastore, module=module)
            print("This is the requested configuration :",config_xml)
            return jsonify({
                "device_id": device_id,
                "module": module,
                "datastore": datastore,
                "config": config_xml
            }), 200
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    #To change the configuration
    elif request.method == "POST":
        data = request.json or {}
        device_id = data.get("device_id") or _resolve_device_id()
        datastore = data.get("datastore", "candidate")
        config_payload = data.get("config")

        if not device_id:
            print("No device id found")
            return jsonify({"error": "No active NETCONF session connected"}), 400
        if not config_payload:
            print("No configuration found")
            return jsonify({"error": "Missing 'config' XML payload"}), 400

        try:
            edit_res = netconf.edit_config(
                device_id, 
                config=config_payload, 
                target=datastore
            )
            print("The new configuration is :",edit_res)
            return jsonify({
                "status": "success",
                "device_id": device_id,
                "datastore": datastore,
                "edit_result": edit_res
            }), 200
        except Exception as e:
            print("Error in changing the configuration")
            return jsonify({"error": str(e)}), 500


#Validates onfiguration before saving
@cm_bp.route("/validate", methods=["POST"])
def validate_config():
    data = request.json or {}
    device_id = data.get("device_id") or _resolve_device_id()
    datastore = data.get("datastore", "candidate")

    if not device_id:
        print("No device id found")
        return jsonify({"error": "No active NETCONF session connected"}), 400

    try:
        val_res = netconf.validate(device_id, source=datastore)
        print("Configuration validated")
        return jsonify({"status": "valid", "device_id": device_id, "result": val_res}), 200
    except Exception as e:
        print("Erroor in validating configuration")
        return jsonify({"error": str(e)}), 400

#Saves the netconf configuration
@cm_bp.route("/commit", methods=["POST"])
def commit_config():
    data = request.json or {}
    device_id = data.get("device_id") or _resolve_device_id()

    if not device_id:
        print("No device id found to commit")
        return jsonify({"error": "No active NETCONF session connected"}), 400

    try:
        res = netconf.commit(device_id)
        print("Committing the configuration was successfull")
        return jsonify({"status": "committed", "device_id": device_id, "result": res}), 200
    except Exception as e:
        print("Error in commiting the configuration")
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