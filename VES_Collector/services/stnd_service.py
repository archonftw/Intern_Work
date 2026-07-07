import logging

logger = logging.getLogger("VES-COLLECTOR")


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

    # NOTE: "cleared" is checked before the generic thresholdcrossingalert
    # check, since a real event name like "ThresholdCrossingAlert_Cleared"
    # contains both substrings and should route to the "cleared" handler.
    if "cleared" in event_name:
        handle_threshold_clear(event)

    elif "file-ready" in event_name:
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
