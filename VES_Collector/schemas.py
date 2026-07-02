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
    "required": [
        "heartbeatInterval"
    ],
    "properties": {
        "heartbeatInterval": {
            "type": "number"
        }
    }
}


FAULT_SCHEMA = {
    "type": "object",
    "required": [
        "alarmCondition",
        "eventSeverity",
        "specificProblem"
    ],
    "properties": {
        "alarmCondition": {
            "type": "string"
        },
        "alarmInterfaceA": {
            "type": "string"
        },
        "eventSeverity": {
            "type": "string",
            "enum": [
                "CRITICAL",
                "MAJOR",
                "MINOR",
                "WARNING",
                "NORMAL"
            ]
        },
        "specificProblem": {
            "type": "string"
        },
        "faultFieldsVersion": {
            "type": "string"
        }
    },
    "additionalProperties": True
}


MEASUREMENT_SCHEMA = {
    "type": "object",
    "required": [
        "measurementInterval",
        "measurements"
    ],
    "properties": {
        "measurementInterval": {
            "type": "number"
        },
        "measurements": {
            "type": "array",
            "minItems": 1,
            "items": {
                "type": "object",
                "required": [
                    "name",
                    "value"
                ],
                "properties": {
                    "name": {
                        "type": "string"
                    },
                    "value": {}
                }
            }
        }
    }
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


# ------------------------------------------------------------------
# NEW SCHEMA : PNF REGISTRATION
# ------------------------------------------------------------------

PNF_REGISTRATION_SCHEMA = {
    "type": "object",
    "properties": {
        "pnfRegistrationFieldsVersion": {
            "type": "string"
        }
    },
    "additionalProperties": True
}


# ------------------------------------------------------------------
# NEW SCHEMA : STND DEFINED
# This is intentionally generic because different STND events
# have different payloads.
# ------------------------------------------------------------------

STND_DEFINED_SCHEMA = {
    "type": "object",
    "properties": {
        "stndDefinedFieldsVersion": {
            "type": "string"
        }
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
                "commonEventHeader": COMMON_HEADER_SCHEMA
            },
            "additionalProperties": True
        }
    },
    "additionalProperties": False
}