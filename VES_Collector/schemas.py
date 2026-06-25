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
        "lastEpochMicrosec": {"type": "number"}
    },
    "additionalProperties": True
}

HEARTBEAT_SCHEMA = {
    "type": "object",
    "properties": {
        "heartbeatInterval": {"type": "number"}
    },
    "additionalProperties": True
}

FAULT_SCHEMA = {
    "type": "object",
    "properties": {
        "alarmCondition": {"type": "string"},
        "alarmInterfaceA": {"type": "string"},
        "eventSeverity": {"type": "string"},
        "specificProblem": {"type": "string"},
        "faultFieldsVersion": {"type": "string"}
    },
    "additionalProperties": True
}

MEASUREMENT_SCHEMA = {
    "type": "object",
    "properties": {
        "measurementInterval": {"type": "number"},
        "measurements": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "value": {}
                },
                "required": ["name", "value"],
                "additionalProperties": True
            }
        }
    },
    "additionalProperties": True
}

NOTIFICATION_SCHEMA = {
    "type": "object",
    "properties": {
        "changeIdentifier": {"type": "string"},
        "changeType": {"type": "string"},
        "notificationFieldsVersion": {"type": "string"}
    },
    "additionalProperties": True
}

STATE_CHANGE_SCHEMA = {
    "type": "object",
    "properties": {
        "oldState": {"type": "string"},
        "newState": {"type": "string"},
        "stateInterface": {"type": "string"}
    },
    "additionalProperties": True
}

THRESHOLD_CROSSING_ALERT_SCHEMA = {
    "type": "object",
    "properties": {
        "indicatorName": {"type": "string"},
        "indicatorValue": {"type": "number"},
        "thresholdValue": {"type": "number"}
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
                "heartbeatFields": HEARTBEAT_SCHEMA,
                "faultFields": FAULT_SCHEMA,
                "measurementFields": MEASUREMENT_SCHEMA,
                "notificationFields": NOTIFICATION_SCHEMA,
                "stateChangeFields": STATE_CHANGE_SCHEMA,
                "thresholdCrossingAlertFields":
                    THRESHOLD_CROSSING_ALERT_SCHEMA
            },
            "additionalProperties": True
        }
    },
    "additionalProperties": True
}