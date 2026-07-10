import logging

from services.file_ready_service import process_file_ready, is_file_ready_event

logger = logging.getLogger("VES-COLLECTOR")


def handle_file_ready(event):
    records = process_file_ready(event)
    logger.info(
        "[FILE READY] %s | %d file(s) stored",
        event["commonEventHeader"]["eventName"], len(records)
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

    if "cleared" in event_name:
        handle_threshold_clear(event)

    elif is_file_ready_event(event) or "file-ready" in event_name or "fileready" in event_name:
        handle_file_ready(event)

    elif "notifypnfregistration" in event_name:
        handle_o1_registration(event)

    elif "thresholdcrossingalert" in event_name:
        handle_threshold(event)

    else:
        logger.info(
            "[UNKNOWN STND EVENT] %s",
            event_name
        )