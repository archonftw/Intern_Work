import uuid
import logging
from datetime import datetime, timezone
from typing import Any, Dict
from jsonschema import validate

# Custom imports - remove EVENT_STORE from memory storage
from services.pnf_service import process_pnf_registration
from services.validation import validate_domain
from services.device_service import update_device
from services.stnd_service import process_stnd
from config import MAX_GLOBAL_EVENT_STORE
from services.validation import _resolve_stnd_type
from services.db_service import save_event_to_db

logger = logging.getLogger("VES-COLLECTOR")


def process_event(event):
    domain = event["commonEventHeader"]["domain"]

    if domain == "pnfRegistration":
        process_pnf_registration({"event": event})

    elif domain == "stndDefined":
        process_stnd(event)
        resolved_type = _resolve_stnd_type(event)
        
        if resolved_type == "notifyPNFRegistration":
            logger.info("Routing standard-defined PNF registration to PNF processor")
            process_pnf_registration({"event": event})


def store_event(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Persists the incoming VES event directly into PostgreSQL via db_service.
    """
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

    # Save directly to PostgreSQL database instead of memory list
    try:
        # Wrap the event back into the expected envelope if necessary
        payload_to_save = event if "event" in event else {"event": event}
        save_event_to_db(payload_to_save)
    except Exception as e:
        logger.error("Failed to persist event to database in store_event: %s", e)
        raise e

    logger.info(
        "EVENT | domain=%s | id=%s | source=%s",
        enriched["domain"], enriched["eventId"], enriched["sourceName"]
    )

    return enriched


def process_single_event(body: Dict[str, Any]):
    event = body["event"]
    validate_domain(event)
    process_event(event)
    update_device(event)
    return store_event(event)