from flask import Blueprint, request, jsonify
from jsonschema import ValidationError
from services.event_service import process_single_event
import logging

logger = logging.getLogger("VES-COLLECTOR")

def error(code: int, msg: str):
    return jsonify({"error": msg}), code

ingestion_bp = Blueprint(
    "ingestion",
    __name__
)

@ingestion_bp.route("/eventListener/v7", methods=["POST"])
def ingest_event():
    if not request.is_json:
        return error(415, "Expected JSON")

    try:
        body = request.get_json()
    except Exception:
        return error(400, "Invalid JSON")

    if not isinstance(body, dict):
        return error(400, "Expected a JSON object")

    try:
        process_single_event(body)
    except ValidationError as e:
        return error(400, f"Schema error: {e.message}")
    except Exception:
        logger.exception("Unexpected error processing event")
        return error(500, "Internal processing error")

    return "", 202


@ingestion_bp.route("/eventListener/v7/eventBatch", methods=["POST"])
def ingest_batch():
    if not request.is_json:
        return error(415, "Expected JSON")

    try:
        body = request.get_json()
    except Exception:
        return error(400, "Invalid JSON")

    if not isinstance(body, dict) or "eventList" not in body:
        return error(400, "Expected a JSON object with an 'eventList' array")

    event_list = body["eventList"]

    if not isinstance(event_list, list) or len(event_list) == 0:
        return error(400, "'eventList' must be a non-empty array")

    errors = []

    for idx, single_event_body in enumerate(event_list):
        try:
            if not isinstance(single_event_body, dict):
                raise ValidationError("Batch item must be a JSON object")
            process_single_event(single_event_body)
        except ValidationError as e:
            errors.append({"index": idx, "error": e.message})
        except Exception:
            logger.exception("Unexpected error processing batch item %d", idx)
            errors.append({"index": idx, "error": "Internal processing error"})

    if errors:
        # Partial or total failure: still 202 if some events succeeded,
        # but surface which items failed so the sender can retry just those.
        accepted = len(event_list) - len(errors)
        return jsonify({
            "accepted": accepted,
            "rejected": len(errors),
            "errors": errors
        }), 202 if accepted > 0 else 400

    return "", 202