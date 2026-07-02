import json
import uuid
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List
from schemas import (
    VES_SCHEMA,
    COMMON_HEADER_SCHEMA,
    HEARTBEAT_SCHEMA,
    FAULT_SCHEMA,
    MEASUREMENT_SCHEMA,
    NOTIFICATION_SCHEMA,
    STATE_CHANGE_SCHEMA,
    THRESHOLD_CROSSING_ALERT_SCHEMA,
    PNF_REGISTRATION_SCHEMA,
    STND_DEFINED_SCHEMA
)
from flask import Flask, request, jsonify, render_template
from jsonschema import validate, ValidationError

# ────────────────────────────────────────────────
# App setup
# ────────────────────────────────────────────────

app = Flask(__name__, template_folder="templates", static_folder="static")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("VES-COLLECTOR")

# ────────────────────────────────────────────────
# In-memory event store
# ────────────────────────────────────────────────

EVENT_STORE: List[Dict[str, Any]] = []
# Current state of every discovered network device
DEVICE_STORE: Dict[str, Dict[str, Any]] = {}

#Schemas to validate
DOMAIN_SCHEMAS = {
    "fault": (
        "faultFields",
        FAULT_SCHEMA
    ),

    "heartbeat": (
        "heartbeatFields",
        HEARTBEAT_SCHEMA
    ),

    "measurement": (
        "measurementFields",
        MEASUREMENT_SCHEMA
    ),

    "notification": (
        "notificationFields",
        NOTIFICATION_SCHEMA
    ),

    "stateChange": (
        "stateChangeFields",
        STATE_CHANGE_SCHEMA
    ),

    "thresholdCrossingAlert": (
        "thresholdCrossingAlertFields",
        THRESHOLD_CROSSING_ALERT_SCHEMA
    ),

    # NEW
    "pnfRegistration": (
        "pnfRegistrationFields",
        PNF_REGISTRATION_SCHEMA
    ),

    # NEW
    "stndDefined": (
        "stndDefinedFields",
        STND_DEFINED_SCHEMA
    )
}

def validate_domain(event):

    header = event["commonEventHeader"]

    domain = header["domain"]

    if domain not in DOMAIN_SCHEMAS:
        raise ValidationError(
            f"Unsupported VES domain '{domain}'"
        )

    field_name, schema = DOMAIN_SCHEMAS[domain]

    if field_name not in event:
        raise ValidationError(
            f"Missing '{field_name}' for domain '{domain}'"
        )

    validate(
        event[field_name],
        schema
    )

# ────────────────────────────────────────────────
# Event Processing
# ────────────────────────────────────────────────

def process_pnf(event):

    header = event["commonEventHeader"]

    logger.info(
        "[PNF REGISTRATION] Device=%s",
        header.get("reportingEntityName", "UNKNOWN")
    )


def handle_file_ready(event):

    logger.info(
        "[FILE READY] %s",
        event["commonEventHeader"]["eventName"]
    )


def handle_o1_registration(event):

    logger.info(
        "[O1 PNF REGISTRATION] %s",
        event["commonEventHeader"]["eventName"]
    )


def handle_threshold(event):

    logger.info(
        "[STND THRESHOLD ALERT] %s",
        event["commonEventHeader"]["eventName"]
    )


def handle_threshold_clear(event):

    logger.info(
        "[THRESHOLD CLEARED] %s",
        event["commonEventHeader"]["eventName"]
    )


def process_stnd(event):

    event_name = (
        event["commonEventHeader"]
        .get("eventName", "")
        .lower()
    )

    if "file-ready" in event_name:
        handle_file_ready(event)

    elif "notifypnfregistration" in event_name:
        handle_o1_registration(event)

    elif "thresholdcrossingalert" in event_name:
        handle_threshold(event)

    elif "cleared" in event_name:
        handle_threshold_clear(event)

    else:
        logger.info(
            "[UNKNOWN STND EVENT] %s",
            event_name
        )


def process_event(event):

    domain = event["commonEventHeader"]["domain"]

    if domain == "pnfRegistration":
        process_pnf(event)

    elif domain == "stndDefined":
        process_stnd(event)

# ────────────────────────────────────────────────
# Helpers
# ────────────────────────────────────────────────

def get_device_id(event: Dict[str, Any]) -> str:

    header = event.get("commonEventHeader", {})

    return (
        header.get("reportingEntityName")
        or header.get("sourceName")
        or "UNKNOWN_DEVICE"
    )
def get_or_create_device(device_id: str):

    if device_id not in DEVICE_STORE:

        DEVICE_STORE[device_id] = {

            "deviceId": device_id,

            "status": "ONLINE",

            "registered": False,

            "vendor": None,

            "model": None,

            "lastSeen": None,

            "eventCount": 0,

            "heartbeat": None,

            "faults": [],

            "measurements": [],

            "notifications": [],

            "stateChanges": [],

            "thresholds": [],

            "files": [],

            "events": []
        }

    return DEVICE_STORE[device_id]
def update_device(event: Dict[str, Any]):

    device_id = get_device_id(event)

    device = get_or_create_device(device_id)

    domain = event["commonEventHeader"]["domain"]

    device["lastSeen"] = datetime.now(timezone.utc).isoformat()

    device["eventCount"] += 1

    device["events"].append(event)

    if len(device["events"]) > 100:
        device["events"] = device["events"][-100:]

    if domain == "heartbeat":

        device["heartbeat"] = event

    elif domain == "measurement":

        device["measurements"].append(event)

        if len(device["measurements"]) > 20:
            device["measurements"] = device["measurements"][-20:]

    elif domain == "fault":

        device["faults"].append(event)

    elif domain == "notification":

        device["notifications"].append(event)

    elif domain == "stateChange":

        device["stateChanges"].append(event)

    elif domain == "thresholdCrossingAlert":

        device["thresholds"].append(event)

    elif domain == "pnfRegistration":

        device["registered"] = True

        fields = event.get("pnfRegistrationFields", {})

        device["vendor"] = fields.get("vendorName")

        device["model"] = fields.get("modelNumber")

def store_event(event: Dict[str, Any]) -> Dict[str, Any]:
    header = event.get("commonEventHeader", {})

    enriched = {
        "collectorId": str(uuid.uuid4()),
        "receivedAt": datetime.now(timezone.utc).isoformat(),
        "domain": header.get("domain"),
        "eventId": header.get("eventId"),
        "eventName": header.get("eventName"),
        "sourceName": header.get("sourceName"),
        "priority": header.get("priority"),
        "raw": event
    }

    EVENT_STORE.append(enriched)

    logger.info(
        "EVENT | domain=%s | id=%s | source=%s",
        enriched["domain"], enriched["eventId"], enriched["sourceName"]
    )

    return enriched


def error(code: int, msg: str):
    return jsonify({"error": msg}), code


# ────────────────────────────────────────────────
# VES Ingestion API
# ────────────────────────────────────────────────

@app.route("/eventListener/v7", methods=["POST"])
def ingest_event():
    if not request.is_json:
        return error(415, "Expected JSON")

    try:
        body = request.get_json()
    except Exception:
        return error(400, "Invalid JSON")

    try:
        validate(body, VES_SCHEMA)
        event = body["event"]
        validate_domain(event)
        # Process event before storing
        process_event(event)
    except ValidationError as e:
        return error(400, f"Schema error: {e.message}")

    event = body["event"]
    update_device(event)
    store_event(event)

    return "", 202



# ────────────────────────────────────────────────
# Dashboard Pages
# ────────────────────────────────────────────────

@app.route("/")
def dashboard():
    return render_template("dashboard.html")


# ────────────────────────────────────────────────
# API for frontend
# ────────────────────────────────────────────────

@app.route("/api/events")
def api_events():
    limit = int(request.args.get("limit", 100))
    return jsonify(EVENT_STORE[-limit:])

@app.route("/api/devices")
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

@app.route("/api/device/<device_id>")
def api_device(device_id):

    device = DEVICE_STORE.get(device_id)

    if device is None:
        return error(404, "Device not found")

    return jsonify(device)

@app.route("/api/device/<device_id>/events")
def api_device_events(device_id):

    device = DEVICE_STORE.get(device_id)

    if device is None:
        return error(404, "Device not found")

    return jsonify(device["events"])

@app.route("/api/stats")
def stats():

    fault_events = [
        e for e in EVENT_STORE
        if e["domain"] == "fault"
    ]

    critical_faults = 0
    major_faults = 0
    warning_faults = 0

    for e in fault_events:

        fault_fields = (
            e["raw"]
            .get("faultFields", {})
        )

        severity = fault_fields.get(
            "eventSeverity",
            ""
        ).upper()

        if severity == "CRITICAL":
            critical_faults += 1

        elif severity == "MAJOR":
            major_faults += 1

        elif severity == "WARNING":
            warning_faults += 1

    return jsonify({

        "totalEvents": len(EVENT_STORE),

        "faultEvents":
            len(fault_events),

        "measurementEvents":
            len([
                e for e in EVENT_STORE
                if e["domain"] == "measurement"
            ]),

        "heartbeatEvents":
            len([
                e for e in EVENT_STORE
                if e["domain"] == "heartbeat"
            ]),

        "notificationEvents":
            len([
                e for e in EVENT_STORE
                if e["domain"] == "notification"
            ]),

        "stateChangeEvents":
            len([
                e for e in EVENT_STORE
                if e["domain"] == "stateChange"
            ]),

        "thresholdEvents":
            len([
                e for e in EVENT_STORE
                if e["domain"] ==
                "thresholdCrossingAlert"
            ]),
        "pnfRegistrationEvents":
            len([
                e for e in EVENT_STORE
                if e["domain"] == "pnfRegistration"
            ]),
        
        "stndDefinedEvents":
            len([
                e for e in EVENT_STORE
                if e["domain"] == "stndDefined"
            ]),

        "criticalFaults":
            critical_faults,

        "majorFaults":
            major_faults,

        "warningFaults":
            warning_faults
    })


@app.route("/api/domains")
def domains():

    counts = {}

    for event in EVENT_STORE:

        domain = event["domain"]

        counts[domain] = (
            counts.get(domain, 0) + 1
        )

    return jsonify(counts)
# ────────────────────────────────────────────────
# Healthcheck
# ────────────────────────────────────────────────

@app.route("/healthcheck")
def health():
    return jsonify({
        "status": "UP",
        "events": len(EVENT_STORE)
    })


# ────────────────────────────────────────────────
# Run server
# ────────────────────────────────────────────────

if __name__ == "__main__":
    logger.info("VES Collector + Dashboard running on :8080")
    app.run(host="0.0.0.0", port=8080, debug=False)