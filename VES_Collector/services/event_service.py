# Library imports
import uuid
import logging
from datetime import datetime, timezone
from typing import Any, Dict
from jsonschema import validate

# Custom imports
from storage.memory import EVENT_STORE
from services.pnf_service import process_pnf_registration
from services.validation import validate_domain
from services.device_service import update_device
from services.stnd_service import process_stnd
from config import MAX_GLOBAL_EVENT_STORE

logger = logging.getLogger("VES-COLLECTOR")


def process_event(event):
    domain = event["commonEventHeader"]["domain"]

    if domain == "pnfRegistration":
        process_pnf_registration({"event": event})

    elif domain == "stndDefined":
        process_stnd(event)


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

    if len(EVENT_STORE) > MAX_GLOBAL_EVENT_STORE:
        del EVENT_STORE[: len(EVENT_STORE) - MAX_GLOBAL_EVENT_STORE]

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