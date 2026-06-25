import requests
import random
import uuid
import time
from datetime import datetime

VES_URL = "http://localhost:8080/eventListener/v7"

NETWORK_FUNCTIONS = [
    "gNB-01",
    "gNB-02",
    "DU-01",
    "DU-02",
    "CU-CP-01",
    "CU-UP-01",
    "AMF-01",
    "SMF-01"
]


def current_microseconds():
    return int(time.time() * 1_000_000)


def common_header(domain, event_type, source):
    now = current_microseconds()

    return {
        "domain": domain,
        "eventId": str(uuid.uuid4()),
        "eventName": f"{domain}_event",
        "eventType": event_type,
        "sequence": random.randint(1, 100000),
        "priority": random.choice(["Normal", "High"]),
        "reportingEntityName": source,
        "sourceName": source,
        "startEpochMicrosec": now,
        "lastEpochMicrosec": now,
        "version": "4.0"
    }


def heartbeat_event():
    source = random.choice(NETWORK_FUNCTIONS)

    return {
        "event": {
            "commonEventHeader": common_header(
                "heartbeat",
                "System",
                source
            ),
            "heartbeatFields": {
                "heartbeatInterval": 30
            }
        }
    }


def fault_event():
    source = random.choice(NETWORK_FUNCTIONS)

    return {
        "event": {
            "commonEventHeader": common_header(
                "fault",
                "Alarm",
                source
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


def measurement_event():
    source = random.choice(NETWORK_FUNCTIONS)

    return {
        "event": {
            "commonEventHeader": common_header(
                "measurement",
                "KPI",
                source
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


def notification_event():
    source = random.choice(NETWORK_FUNCTIONS)

    return {
        "event": {
            "commonEventHeader": common_header(
                "notification",
                "Notification",
                source
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


def state_change_event():
    source = random.choice(NETWORK_FUNCTIONS)

    return {
        "event": {
            "commonEventHeader": common_header(
                "stateChange",
                "State",
                source
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


def threshold_event():
    source = random.choice(NETWORK_FUNCTIONS)

    cpu = round(random.uniform(80, 100), 2)

    return {
        "event": {
            "commonEventHeader": common_header(
                "thresholdCrossingAlert",
                "Threshold",
                source
            ),
            "thresholdCrossingAlertFields": {
                "indicatorName": "CPU_Usage",
                "indicatorValue": cpu,
                "thresholdValue": 90
            }
        }
    }


EVENT_GENERATORS = [
    heartbeat_event,
    fault_event,
    measurement_event,
    notification_event,
    state_change_event,
    threshold_event
]


def send_event():
    event = random.choice(EVENT_GENERATORS)()

    try:
        response = requests.post(
            VES_URL,
            json=event,
            timeout=5
        )

        domain = event["event"]["commonEventHeader"]["domain"]

        print(
            f"[{datetime.now().strftime('%H:%M:%S')}] "
            f"{domain:<25} "
            f"Status={response.status_code}"
        )

    except Exception as e:
        print(f"ERROR: {e}")


if __name__ == "__main__":
    print("Starting VES Traffic Generator...")
    print(f"Target: {VES_URL}")

    while True:
        send_event()

        time.sleep(
            random.uniform(0.1, 0.5)
        )