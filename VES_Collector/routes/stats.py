from flask import Blueprint, jsonify,request
from config import MAX_GLOBAL_EVENT_STORE
from storage.memory import EVENT_STORE,DEVICE_STORE

stats_bp = Blueprint(
    "stats",
    __name__
)


@stats_bp.route("/api/stats")
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


@stats_bp.route("/api/domains")
def domains():

    counts = {}

    for event in EVENT_STORE:

        domain = event["domain"]

        counts[domain] = (
            counts.get(domain, 0) + 1
        )

    return jsonify(counts)

@stats_bp.route("/api/events")
def api_events():
    try:
        limit = int(request.args.get("limit", 100))
    except (TypeError, ValueError):
        limit = 100

    limit = max(1, min(limit, MAX_GLOBAL_EVENT_STORE))

    return jsonify(EVENT_STORE[-limit:])


@stats_bp.route("/healthcheck")
def health():
    return jsonify({
        "status": "UP",
        "events": len(EVENT_STORE),
        "devices": len(DEVICE_STORE)
    })
