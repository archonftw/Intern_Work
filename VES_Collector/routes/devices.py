from flask import Blueprint, jsonify

from storage.memory import DEVICE_STORE



devices_bp = Blueprint(
    "devices",
    __name__
)


def error(code: int, msg: str):
    return jsonify({"error": msg}), code



@devices_bp.route("/api/devices")
def api_devices():

    devices = []

    for device in DEVICE_STORE.values():

        devices.append({

            "deviceId": device["deviceId"],

            "status": device["status"],

            "registered": device["registered"],

            "vendor": device["vendor"],

            "model": device["model"],

            "lastSeen": device["lastSeen"],

            "eventCount": device["eventCount"],

            "faultCount": len(device["faults"]),

            "thresholdCount": len(device["thresholds"])
        })

    return jsonify(devices)


@devices_bp.route("/api/device/<device_id>")
def api_device(device_id):

    device = DEVICE_STORE.get(device_id)

    if device is None:
        return error(404, "Device not found")

    return jsonify(device)


@devices_bp.route("/api/device/<device_id>/events")
def api_device_events(device_id):

    device = DEVICE_STORE.get(device_id)

    if device is None:
        return error(404, "Device not found")

    return jsonify(device["events"])
