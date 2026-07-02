import requests
import random
import uuid
import time
from datetime import datetime

VES_URL = "http://localhost:8080/eventListener/v7"

# ────────────────────────────────────────────────
# Simulated device fleet
# Each NF has a persistent identity so vendor/model/serial stay
# consistent across every event it sends (matches real PNF behavior,
# and lets the dashboard's Devices panel show meaningful info).
# ────────────────────────────────────────────────

VENDOR_MODELS = [
    ("Ericsson", "RU-4408"),
    ("Nokia", "AirScale-BTS"),
    ("Huawei", "BBU-5900"),
    ("Samsung", "vRAN-CU"),
    ("Mavenir", "OpenRAN-DU"),
]

NETWORK_FUNCTIONS = []

for name in ["gNB-01", "gNB-02", "DU-01", "DU-02", "CU-CP-01", "CU-UP-01", "AMF-01", "SMF-01"]:
    vendor, model = random.choice(VENDOR_MODELS)
    NETWORK_FUNCTIONS.append({
        "name": name,
        "vendor": vendor,
        "model": model,
        "serialNumber": uuid.uuid4().hex[:8].upper(),
        "softwareVersion": f"{random.randint(20, 24)}.{random.randint(0, 9)}.{random.randint(0, 9)}",
    })


def get_device(name=None):
    """Return a device record by name, or a random one."""
    if name:
        return next(d for d in NETWORK_FUNCTIONS if d["name"] == name)
    return random.choice(NETWORK_FUNCTIONS)


def current_microseconds():
    return int(time.time() * 1_000_000)


def common_header(domain, event_type, source, event_name=None):
    now = current_microseconds()

    return {
        "domain": domain,
        "eventId": str(uuid.uuid4()),
        "eventName": event_name or f"{domain}_event",
        "eventType": event_type,
        "sequence": random.randint(1, 100000),
        "priority": random.choice(["Normal", "High"]),
        "reportingEntityName": source,
        "sourceName": source,
        "startEpochMicrosec": now,
        "lastEpochMicrosec": now,
        "version": "4.0"
    }


def heartbeat_event(device=None):
    device = device or get_device()

    return {
        "event": {
            "commonEventHeader": common_header(
                "heartbeat",
                "System",
                device["name"]
            ),
            "heartbeatFields": {
                "heartbeatInterval": 30
            }
        }
    }


def fault_event(device=None):
    device = device or get_device()

    return {
        "event": {
            "commonEventHeader": common_header(
                "fault",
                "Alarm",
                device["name"]
            ),
            "faultFields": {
                "alarmCondition": random.choice([
                    "Cell Down",
                    "Link Failure",
                    "Radio Failure",
                    "Power Alarm"
                ]),
                "alarmInterfaceA": "N1",
                "eventSeverity": random.choice([
                    "WARNING",
                    "MAJOR",
                    "CRITICAL"
                ]),
                "specificProblem": "Auto Generated Fault",
                "faultFieldsVersion": "4.0"
            }
        }
    }


def measurement_event(device=None):
    device = device or get_device()

    return {
        "event": {
            "commonEventHeader": common_header(
                "measurement",
                "KPI",
                device["name"]
            ),
            "measurementFields": {
                "measurementInterval": 60,
                "measurements": [
                    {
                        "name": "CPU_Usage",
                        "value": round(random.uniform(10, 99), 2)
                    },
                    {
                        "name": "Memory_Usage",
                        "value": round(random.uniform(20, 95), 2)
                    },
                    {
                        "name": "Connected_UEs",
                        "value": random.randint(50, 1000)
                    },
                    {
                        "name": "Throughput_Mbps",
                        "value": round(random.uniform(100, 3000), 2)
                    }
                ]
            }
        }
    }


def notification_event(device=None):
    device = device or get_device()

    return {
        "event": {
            "commonEventHeader": common_header(
                "notification",
                "Notification",
                device["name"]
            ),
            "notificationFields": {
                "changeIdentifier": str(uuid.uuid4()),
                "changeType": random.choice([
                    "Software",
                    "Configuration",
                    "Policy"
                ]),
                "notificationFieldsVersion": "4.0"
            }
        }
    }


def state_change_event(device=None):
    device = device or get_device()

    return {
        "event": {
            "commonEventHeader": common_header(
                "stateChange",
                "State",
                device["name"]
            ),
            "stateChangeFields": {
                "oldState": random.choice([
                    "LOCKED",
                    "DISABLED"
                ]),
                "newState": random.choice([
                    "UNLOCKED",
                    "ENABLED"
                ]),
                "stateInterface": "O1"
            }
        }
    }


def threshold_event(device=None):
    device = device or get_device()

    cpu = round(random.uniform(80, 100), 2)

    return {
        "event": {
            "commonEventHeader": common_header(
                "thresholdCrossingAlert",
                "Threshold",
                device["name"]
            ),
            "thresholdCrossingAlertFields": {
                "indicatorName": "CPU_Usage",
                "indicatorValue": cpu,
                "thresholdValue": 90
            }
        }
    }


def pnf_registration_event(device=None):
    device = device or get_device()

    return {
        "event": {
            "commonEventHeader": common_header(
                "pnfRegistration", "Registration", device["name"], "10SF-pnfRegistration"
            ),
            "pnfRegistrationFields": {
                "pnfRegistrationFieldsVersion": "1.0",
                "serialNumber": device["serialNumber"],
                "vendorName": device["vendor"],
                "modelNumber": device["model"],
                "softwareVersion": device["softwareVersion"]
            }
        }
    }


def stnd_file_ready_event(device=None):
    device = device or get_device()

    return {
        "event": {
            "commonEventHeader": common_header(
                "stndDefined", "FileReady", device["name"], "FYNG-stndDefined-3gpp-file-ready"
            ),
            "stndDefinedFields": {
                "stndDefinedFieldsVersion": "1.0",
                "fileName": f"PM_{uuid.uuid4().hex[:6]}.xml.gz",
                "location": "/pm/files/",
                "compression": "gzip",
                "fileSize": random.randint(1000, 5000)
            }
        }
    }


def stnd_o1_registration_event(device=None):
    device = device or get_device()

    return {
        "event": {
            "commonEventHeader": common_header(
                "stndDefined", "Registration", device["name"],
                "10SF-stndDefined-o1NotifyPnfRegistration"
            ),
            "stndDefinedFields": {
                "stndDefinedFieldsVersion": "1.0",
                "vendorName": device["vendor"],
                "registrationStatus": "REGISTERED"
            }
        }
    }


def stnd_threshold_alert_event(device=None):
    device = device or get_device()

    return {
        "event": {
            "commonEventHeader": common_header(
                "stndDefined", "Threshold", device["name"],
                "R2D2-TCA-CONT-thresholdCrossingAlert"
            ),
            "stndDefinedFields": {
                "stndDefinedFieldsVersion": "1.0",
                "measurementName": "CPU_Usage",
                "measurementValue": round(random.uniform(91, 99), 2),
                "threshold": 90,
                "eventSeverity": "MAJOR"
            }
        }
    }


def stnd_threshold_clear_event(device=None):
    device = device or get_device()

    return {
        "event": {
            "commonEventHeader": common_header(
                "stndDefined", "Threshold", device["name"],
                "R2D2-TCA-MINOR-cleared"
            ),
            "stndDefinedFields": {
                "stndDefinedFieldsVersion": "1.0",
                "measurementName": "CPU_Usage",
                "measurementValue": round(random.uniform(20, 60), 2),
                "threshold": 90,
                "eventSeverity": "NORMAL"
            }
        }
    }


EVENT_GENERATORS = [
    heartbeat_event,
    fault_event,
    measurement_event,
    notification_event,
    state_change_event,
    threshold_event,
    pnf_registration_event,
    stnd_file_ready_event,
    stnd_o1_registration_event,
    stnd_threshold_alert_event,
    stnd_threshold_clear_event
]


def post_event(event):
    domain = event["event"]["commonEventHeader"]["domain"]
    source = event["event"]["commonEventHeader"]["sourceName"]

    try:
        response = requests.post(
            VES_URL,
            json=event,
            timeout=5
        )

        print(
            f"[{datetime.now().strftime('%H:%M:%S')}] "
            f"{domain:<15} "
            f"{source:<10} "
            f"Status={response.status_code}"
        )

    except Exception as e:
        print(f"ERROR: {e}")


def register_all_devices():
    """Send a pnfRegistration event for every simulated device so the
    dashboard's Devices panel shows vendor/model/serial immediately,
    instead of waiting for a random pnfRegistration event to land."""

    print(f"Registering {len(NETWORK_FUNCTIONS)} devices...")

    for device in NETWORK_FUNCTIONS:
        post_event(pnf_registration_event(device))
        time.sleep(0.05)


def send_event():
    device = get_device()
    generator = random.choice(EVENT_GENERATORS)
    post_event(generator(device))


if __name__ == "__main__":
    print("Starting VES Traffic Generator...")
    print(f"Target: {VES_URL}")

    register_all_devices()

    while True:
        send_event()

        time.sleep(
            random.uniform(0.1, 0.5)
        )