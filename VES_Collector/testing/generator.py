import requests
import random
import uuid
import time
import os
import tempfile
from datetime import datetime,timedelta,UTC
from utils import VENDOR_MODELS

VES_URL = "http://localhost:8080/eventListener/v7"



NETWORK_FUNCTIONS = []

for name in [
    # gNBs
    "gNB-01",
    "gNB-02",
    "gNB-03",
    "gNB-04",

    # Distributed Units
    "DU-01",
    "DU-02",
    "DU-03",
    "DU-04",

    # Central Units
    "CU-CP-01",
    "CU-CP-02",
    "CU-UP-01",
    "CU-UP-02",

    # Radio Units
    "RU-01",
    "RU-02",
    "RU-03",
    "RU-04",

    # 5G Core
    "AMF-01",
    "AMF-02",
    "SMF-01",
    "SMF-02",
    "UPF-01",
    "UPF-02",
    "UDM-01",
    "UDM-02",
    "AUSF-01",
    "PCF-01",
    "NSSF-01",
    "NRF-01",
    "NEF-01",
    "AF-01",
    "LMF-01",

    # IMS / Voice
    "IMS-01",
    "SBC-01",
    "PCRF-01",

    # Transport
    "Router-01",
    "Router-02",
    "Switch-01",
    "Switch-02",

    # Edge / MEC
    "MEC-01",
    "MEC-02",

    # O-RAN Components
    "Near-RT-RIC-01",
    "Non-RT-RIC-01",
    "O-CU-01",
    "O-DU-01",
    "O-RU-01",
]:
    vendor, model = random.choice(VENDOR_MODELS)
    NETWORK_FUNCTIONS.append({
    "name": name,
    "vendor": vendor,
    "model": model,
    "serialNumber": uuid.uuid4().hex[:8].upper(),
    "softwareVersion": f"{random.randint(20,24)}.{random.randint(0,9)}.{random.randint(0,9)}",
    "ip": f"192.168.1.{random.randint(2,254)}"
})

PM_FILE_DIR = os.path.join(tempfile.gettempdir(), "ves_pm_files")
os.makedirs(PM_FILE_DIR, exist_ok=True)

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

def pnf_registration_event(device=None):
    device = device or get_device()

    manufacture_date = (
        datetime.now() - timedelta(days=random.randint(500, 3000))
    ).strftime("%Y-%m-%d")

    last_service_date = (
        datetime.now() - timedelta(days=random.randint(1, 365))
    ).strftime("%Y-%m-%d")

    return {
        "event": {
            "commonEventHeader": common_header(
                "pnfRegistration",
                "PNF Registration",
                device["name"]
            ),
            "pnfRegistrationFields": {
                "pnfRegistrationFieldsVersion": "4.0",
                "lastServiceDate": last_service_date,
                "macAddress": ":".join(
                    f"{random.randint(0,255):02X}" for _ in range(6)
                ),
                "manufactureDate": manufacture_date,
                "modelNumber": device["model"],
                "oamV4IpAddress": device["ip"],
                "serialNumber": device["serialNumber"],
                "softwareVersion": device["softwareVersion"],
                "unitFamily": random.choice([
                    "5G-RAN",
                    "vDU",
                    "vCU",
                    "RU"
                ]),
                "unitType": random.choice([
                    "gNB",
                    "DU",
                    "CU",
                    "RU"
                ]),
                "additionalFields": {
                    "protocol": random.choice([
                        "SSH",
                        "HTTPS",
                        "NETCONF"
                    ]),
                    "vendorName":random.choice([
                        "Radisys","Ercission","Nokia","Samsung"
                    ]),
                    "username": "root",
                    "password": "root",
                    "port": random.choice([
                        22,
                        443,
                        830
                    ]),
                    "keyId": f"KEY-{uuid.uuid4().hex[:8].upper()}"
                }
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


def _write_pm_file(device):
    """
    Write a small pseudo-3GPP PM measurement XML file to disk and return
    (file_path, file_size_bytes). This stands in for what a real NF would
    push to an SFTP/S3 endpoint - here it's a real local file so the
    collector's fileReady preview can actually fetch and display it.
    """
    now = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    file_id = uuid.uuid4().hex

    content = f"""<?xml version="1.0" encoding="UTF-8"?>
<measCollecFile xmlns="http://www.3gpp.org/ftp/specs/archive/32_series/32.435#measCollec">
  <fileHeader fileFormatVersion="32.435 V10.0" vendorName="{device['vendor']}" dnPrefix="{device['name']}">
    <fileSender localDn="{device['name']}"/>
    <measCollec beginTime="{now}"/>
  </fileHeader>
  <measData>
    <managedElement localDn="ManagedElement=1,GNBDUFunction=1" swVersion="{device['softwareVersion']}"/>
    <measInfo measInfoId="PM_{file_id}">
      <granPeriod duration="PT15M" endTime="{now}"/>
      <repPeriod duration="PT15M"/>
      <measTypes>CPU_Usage Memory_Usage Connected_UEs Throughput_Mbps</measTypes>
      <measValue measObjLdn="{device['name']}">
        <r p="1">{round(random.uniform(10, 99), 2)}</r>
        <r p="2">{round(random.uniform(20, 95), 2)}</r>
        <r p="3">{random.randint(50, 1000)}</r>
        <r p="4">{round(random.uniform(100, 3000), 2)}</r>
      </measValue>
    </measInfo>
  </measData>
  <fileFooter>
    <measCollec endTime="{now}"/>
  </fileFooter>
</measCollecFile>
"""

    filename = f"{file_id}.xml"
    filepath = os.path.join(PM_FILE_DIR, filename)
    with open(filepath, "w") as f:
        f.write(content)

    return filepath, os.path.getsize(filepath)


def stnd_file_ready_event(device=None):
    device = device or get_device()

    now = datetime.now(UTC)
    filepath, file_size = _write_pm_file(device)

    return {
        "event": {
            "commonEventHeader": {
                **common_header(
                    "stndDefined",
                    "FileReady",
                    device["name"],
                    "stndDefined_FileReady"
                ),
                "eventType": "fileReady",
                "version": "4.0",
                "sequence": random.randint(1, 100000),
                "vesEventListenerVersion": "7.2"
            },
            "stndDefinedFields": {
                "stndDefinedFieldsVersion": "1.0",
                "data": {
                    "systemDN": "ManagedElement=1,GNBDUFunction=1",
                    "additionalText": "Bulk data file transfer readiness notification.",
                    "eventTime": now.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
                    "fileInfoList": [
                        {
                            "fileSize": file_size,
                            "fileLocation": f"file://{filepath}",
                            "fileFormat": "XML",
                            "fileDataType": "PM",
                            "fileReadyTime": now.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
                            "fileExpirationTime": (
                                now + timedelta(days=7)
                            ).strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
                            "fileCompression": "none"
                        }
                    ]
                }
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
    payload = generator(device)
    post_event(payload)


if __name__ == "__main__":
    print("Starting VES Traffic Generator...")
    print(f"Target: {VES_URL}")
    print(f"Simulated PM files written to: {PM_FILE_DIR}")

    register_all_devices()

    while True:
        send_event()

        time.sleep(
            random.uniform(0.1, 0.5)
        )