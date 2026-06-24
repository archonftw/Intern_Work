"""
VES Collector + Dashboard (VES 7.x tolerant)
- Fault + Measurement ingestion
- Live dashboard support
- Simple in-memory store (upgrade to DB/Kafka later)
"""

import json
import uuid
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List

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

# ────────────────────────────────────────────────
# Flexible VES schema (tolerant mode)
# ────────────────────────────────────────────────

COMMON_HEADER_SCHEMA = {
    "type": "object",
    "required": ["domain", "eventId", "eventName"],
    "properties": {
        "domain": {"type": "string"},
        "eventId": {"type": "string"},
        "eventName": {"type": "string"},
        "sourceName": {"type": "string"},
        "reportingEntityName": {"type": "string"},
        "priority": {"type": "string"},
        "vesEventListenerVersion": {"type": "string"},
        "startEpochMicrosec": {"type": "number"},
        "lastEpochMicrosec": {"type": "number"},
    },
    "additionalProperties": True
}

FAULT_SCHEMA = {
    "type": "object",
    "properties": {
        "alarmCondition": {"type": "string"},
        "eventSeverity": {"type": "string"},
        "eventSourceType": {"type": "string"},
        "specificProblem": {"type": "string"},
        "vfStatus": {"type": "string"},
        "alarmAdditionalInformation": {"type": "object"},
    },
    "additionalProperties": True
}

MEASUREMENT_SCHEMA = {
    "type": "object",
    "properties": {
        "measurementFieldsVersion": {"type": "string"},
        "measurementInterval": {"type": "number"},
    },
    "additionalProperties": True
}

VES_SCHEMA = {
    "type": "object",
    "required": ["event"],
    "properties": {
        "event": {
            "type": "object",
            "required": ["commonEventHeader"],
            "properties": {
                "commonEventHeader": COMMON_HEADER_SCHEMA,
                "faultFields": FAULT_SCHEMA,
                "measurementFields": MEASUREMENT_SCHEMA,
            },
            "additionalProperties": True
        }
    },
    "additionalProperties": True
}

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
    except ValidationError as e:
        return error(400, f"Schema error: {e.message}")

    event = body["event"]
    store_event(event)

    return "", 202


@app.route("/eventListener/v7/eventBatch", methods=["POST"])
def ingest_batch():
    if not request.is_json:
        return error(415, "Expected JSON")

    body = request.get_json()
    if "eventList" not in body:
        return error(400, "Missing eventList")

    accepted = 0

    for event in body["eventList"]:
        try:
            validate({"event": event}, VES_SCHEMA)
            store_event(event)
            accepted += 1
        except ValidationError:
            continue

    return jsonify({
        "accepted": accepted,
        "total": len(body["eventList"])
    }), 202


# ────────────────────────────────────────────────
# Dashboard Pages
# ────────────────────────────────────────────────

@app.route("/dashboard")
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
    return jsonify({
        "totalEvents": len(EVENT_STORE),
        "faultEvents": len([e for e in EVENT_STORE if e["domain"] == "fault"]),
        "measurementEvents": len([e for e in EVENT_STORE if e["domain"] == "measurement"]),
    })


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