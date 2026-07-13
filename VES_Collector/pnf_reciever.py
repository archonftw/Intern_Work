"""
Minimal receiver for forwarded PNF registration events.

Run this alongside your VES collector, then set the PNF forward
config (via the dashboard's "Configure Forwarding" button, or
POST /api/pnf/config) to:

    host: 127.0.0.1  (or this machine's IP if running elsewhere)
    port: 9001
    path: /pnf-events

Every PNF record the collector forwards will show up here, both
printed to the console and kept in an in-memory list you can
inspect via GET /received.
"""

import logging
from datetime import datetime, timezone

from flask import Flask, request, jsonify

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
LOGGER = logging.getLogger("pnf-receiver")

app = Flask(__name__)

received_events = []


@app.route("/pnf-events", methods=["POST"])
def receive_pnf_event():
    payload = request.get_json(silent=True) or {}

    record = {
        "receivedAt": datetime.now(timezone.utc).isoformat(),
        "payload": payload,
    }
    received_events.append(record)

    LOGGER.info(
        "Received forwarded PNF: vendor=%s ip=%s (total received: %d)",
        payload.get("vendorName", "?"),
        payload.get("oamV4IpAddress", "?"),
        len(received_events),
    )

    return jsonify({"status": "received"}), 200


@app.route("/received", methods=["GET"])
def list_received():
    """Inspect everything captured so far."""
    return jsonify({
        "count": len(received_events),
        "events": received_events,
    })


@app.route("/received/clear", methods=["POST"])
def clear_received():
    received_events.clear()
    return jsonify({"status": "cleared"})


@app.route("/healthcheck", methods=["GET"])
def healthcheck():
    return jsonify({"status": "up"})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=9001, debug=True)