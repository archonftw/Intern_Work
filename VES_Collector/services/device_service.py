from datetime import datetime, timezone
from typing import Any,Dict

from storage.memory import DEVICE_STORE

from config import (
MAX_EVENTS_PER_DEVICE,
MAX_FAULTS_PER_DEVICE,
MAX_NOTIFICATIONS_PER_DEVICE,
MAX_STATE_CHANGES_PER_DEVICE,
MAX_THRESHOLDS_PER_DEVICE
)


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

            "heartbeatIntervalSec": None,

            "faults": [],

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
    device["status"] = "ONLINE"

    device["eventCount"] += 1

    device["events"].append(event)

    if len(device["events"]) > MAX_EVENTS_PER_DEVICE:
        device["events"] = device["events"][-MAX_EVENTS_PER_DEVICE:]

    if domain == "heartbeat":

        device["heartbeat"] = event

        interval = event.get("heartbeatFields", {}).get("heartbeatInterval")
        if interval is not None:
            device["heartbeatIntervalSec"] = interval

    elif domain == "fault":

        device["faults"].append(event)

        if len(device["faults"]) > MAX_FAULTS_PER_DEVICE:
            device["faults"] = device["faults"][-MAX_FAULTS_PER_DEVICE:]

    elif domain == "notification":

        device["notifications"].append(event)

        if len(device["notifications"]) > MAX_NOTIFICATIONS_PER_DEVICE:
            device["notifications"] = device["notifications"][-MAX_NOTIFICATIONS_PER_DEVICE:]

    elif domain == "stateChange":

        device["stateChanges"].append(event)

        if len(device["stateChanges"]) > MAX_STATE_CHANGES_PER_DEVICE:
            device["stateChanges"] = device["stateChanges"][-MAX_STATE_CHANGES_PER_DEVICE:]

    elif domain == "thresholdCrossingAlert":

        device["thresholds"].append(event)

        if len(device["thresholds"]) > MAX_THRESHOLDS_PER_DEVICE:
            device["thresholds"] = device["thresholds"][-MAX_THRESHOLDS_PER_DEVICE:]

    elif domain == "pnfRegistration":

        device["registered"] = True

        fields = event.get("pnfRegistrationFields", {})

        device["vendor"] = fields.get("vendorName")

        device["model"] = fields.get("modelNumber")
