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
FILE_READY_SCHEMA = {
    "type": "object",
    "required": [
        "eventType",
        "version",
        "eventName",
        "sourceName",
        "domain",
        "stndDefinedFields"
    ],
    "properties": {
        "eventType": {
            "type": "string"
        },
        "priority": {
            "type": "string"
        },
        "version": {
            "type": "string"
        },
        "reportingEntityName": {
            "type": "string"
        },
        "sourceName": {
            "type": "string"
        },
        "domain": {
            "type": "string"
        },
        "eventName": {
            "type": "string"
        },
        "sequence": {
            "type": "number"
        },
        "lastEpochMicrosec": {
            "type": "number"
        },
        "vesEventListenerVersion": {
            "type": "string"
        },
        "stndDefinedFields": {
            "type": "object",
            "required": [
                "stndDefinedFieldsVersion",
                "data"
            ],
            "properties": {
                "stndDefinedFieldsVersion": {
                    "type": "string"
                },
                "data": {
                    "type": "object",
                    "required": [
                        "systemDN",
                        "eventTime",
                        "fileInfoList"
                    ],
                    "properties": {
                        "systemDN": {
                            "type": "string"
                        },
                        "additionalText": {
                            "type": "string"
                        },
                        "eventTime": {
                            "type": "string"
                        },
                        "fileInfoList": {
                            "type": "array",
                            "minItems": 1,
                            "items": {
                                "type": "object",
                                "required": [
                                    "fileSize",
                                    "fileLocation",
                                    "fileFormat",
                                    "fileDataType",
                                    "fileReadyTime",
                                    "fileExpirationTime",
                                    "fileCompression"
                                ],
                                "properties": {
                                    "fileSize": {
                                        "type": "number"
                                    },
                                    "fileLocation": {
                                        "type": "string"
                                    },
                                    "fileFormat": {
                                        "type": "string"
                                    },
                                    "fileDataType": {
                                        "type": "string"
                                    },
                                    "fileReadyTime": {
                                        "type": "string"
                                    },
                                    "fileExpirationTime": {
                                        "type": "string"
                                    },
                                    "fileCompression": {
                                        "type": "string"
                                    }
                                }
                            }
                        }
                    }
                }
            }
        },
        "notificationId": {
            "type": "number"
        },
        "href": {
            "type": "string"
        },
        "notificationType": {
            "type": "string"
        }
    }
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
# NEW SCHEMA : STND DEFINED
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


PNF_REGISTRATION_SCHEMA = {
    "type": "object",
    "required": [
        "pnfRegistrationFieldsVersion",
        "lastServiceDate",
        "macAddress",
        "manufactureDate",
        "modelNumber",
        "oamV4IpAddress",
        "serialNumber",
        "softwareVersion",
        "unitFamily",
        "unitType"
    ],
    "properties": {
        "pnfRegistrationFieldsVersion": {
            "type": "string"
        },
        "lastServiceDate": {
            "type": "string"
        },
        "macAddress": {
            "type": "string"
        },
        "manufactureDate": {
            "type": "string"
        },
        "modelNumber": {
            "type": "string"
        },
        "oamV4IpAddress": {
            "type": "string",
            "format":"ipv4"
        },
        "oamV6IpAddress": {
            "type": "string",
            "format":"ipv6"
        },
        "serialNumber": {
            "type": "string"
        },
        "softwareVersion": {
            "type": "string"
        },
        "unitFamily": {
            "type": "string"
        },
        "unitType": {
            "type": "string"
        },
        "additionalFields": {
            "type": "object",
            "properties": {
                "protocol": {
                    "type": "string"
                },
                "username": {
                    "type": "string"
                },
                "password": {
                    "type": "string"
                },
                "port": {
                    "type": "integer"
                },
                "keyId": {
                    "type": "string"
                },
                "vendorName":{
                    "type":"string"
                }
            },
            "additionalProperties": True
        }
    },
    "additionalProperties": True
}