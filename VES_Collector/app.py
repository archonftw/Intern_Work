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
    THRESHOLD_CROSSING_ALERT_SCHEMA
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
# Helpers
# ────────────────────────────────────────────────

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
    except ValidationError as e:
        return error(400, f"Schema error: {e.message}")

    event = body["event"]
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