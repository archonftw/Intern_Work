import requests
import random
import uuid
import time
import os
import tempfile

VENDOR_MODELS = [
    ("Ericsson", "Radio 4408"), ("Ericsson", "AIR 6449"), ("Ericsson", "Baseband 6630"), ("Ericsson", "Router 6675"),
    ("Nokia", "AirScale-BTS"), ("Nokia", "AirScale-DU"), ("Nokia", "AirScale-CU"), ("Nokia", "AirScale-Radio"),
    ("Huawei", "BBU5900"), ("Huawei", "BBU3910"), ("Huawei", "LampSite"), ("Huawei", "AAU5613"),
    ("Samsung", "vRAN-CU"), ("Samsung", "vRAN-DU"), ("Samsung", "Compact Macro"), ("Samsung", "Massive MIMO Radio"),
    ("Mavenir", "OpenRAN-DU"), ("Mavenir", "OpenRAN-CU"), ("Mavenir", "OpenBeam-RU"),
    ("Radisys", "Connect RAN DU"), ("Radisys", "Connect RAN CU"), ("Radisys", "Open RAN Platform"),
    ("NEC", "5G DU"), ("NEC", "5G CU"), ("NEC", "Radio Unit"),
    ("Fujitsu", "5G DU"), ("Fujitsu", "Virtual CU"), ("Fujitsu", "Radio Unit"),
    ("Cisco", "Ultra Packet Core"), ("Cisco", "NCS540"), ("Cisco", "Catalyst 8500"),
    ("Juniper", "MX480"), ("Juniper", "ACX7100"), ("Juniper", "PTX10001"),
    ("Ciena", "6500 Packet Optical"), ("Ciena", "WaveLogic 5"),
    ("ZTE", "ZXSDR B8200"), ("ZTE", "AAU 64T64R"),
    ("Intel", "FlexRAN Reference Platform"), ("Dell", "PowerEdge XR8000"),
    ("HPE", "ProLiant DL360 Gen11"), ("Supermicro", "SuperServer SYS-220")
]

NETWORK_FUNCTIONS = []

for name in [
    "gNB-01", "gNB-02", "gNB-03", "gNB-04",
    "DU-01", "DU-02", "DU-03", "DU-04",
    "CU-CP-01", "CU-CP-02", "CU-UP-01", "CU-UP-02",
    "RU-01", "RU-02", "RU-03", "RU-04",
    "AMF-01", "AMF-02", "SMF-01", "SMF-02", "UPF-01", "UPF-02",
    "UDM-01", "UDM-02", "AUSF-01", "PCF-01", "NSSF-01", "NRF-01",
    "NEF-01", "AF-01", "LMF-01", "IMS-01", "SBC-01", "PCRF-01",
    "Router-01", "Router-02", "Switch-01", "Switch-02",
    "MEC-01", "MEC-02", "Near-RT-RIC-01", "Non-RT-RIC-01",
    "O-CU-01", "O-DU-01", "O-RU-01"
]:
    vendor, model = random.choice(VENDOR_MODELS)
    equip_type = name.split("-")[0]
    NETWORK_FUNCTIONS.append({
        "name": name,
        "vendor": vendor,
        "model": model,
        "type": equip_type,
        "pnfId": f"pnf-{name.lower()}",
        "serialNumber": uuid.uuid4().hex[:8].upper(),
        "softwareVersion": f"{random.randint(20,24)}.{random.randint(0,9)}.{random.randint(0,9)}",
        "ip": f"192.168.1.{random.randint(2,254)}"
    })

PM_FILE_DIR = os.path.join(tempfile.gettempdir(), "ves_pm_files")
os.makedirs(PM_FILE_DIR, exist_ok=True)

# Global configuration and sequence states
VES_URL = "http://localhost:8080/eventListener/v7"
_FAULT_SEQUENCE_COUNT = 0
_HEARTBEAT_SEQUENCE_COUNT = 0
_NOTIFICATION_SEQUENCE_COUNT = 0
_PNF_REG_SEQUENCE_COUNT = 0
_STATE_CHANGE_SEQUENCE_COUNT = 0
_STND_HB_SEQUENCE_COUNT = 0
_STND_FAULT_SEQUENCE_COUNT = 0
_STND_FILE_SEQUENCE_COUNT = 0
_STND_NEW_ALARM_SEQUENCE_COUNT = 0
_TCA_SEQUENCE_COUNT = 0

def get_device(name=None):
    """Return a device record by name, or a random one."""
    if name:
        return next(d for d in NETWORK_FUNCTIONS if d["name"] == name)
    return random.choice(NETWORK_FUNCTIONS)

def fault_event(device=None):
    global _FAULT_SEQUENCE_COUNT
    device = device or get_device()
    
    alarm = random.choice(["Cell Down", "Link Failure", "Radio Failure", "Power Alarm"])
    severity = random.choice(["WARNING", "MAJOR", "CRITICAL"])
    priority = "High" if severity == "CRITICAL" else "Low"
    
    current_time_ms = int(time.time() * 1000)
    timestamp_str = str(current_time_ms * 1000)
    iso_time = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    
    device_name = device.get("name", "Unknown-Device")
    vendor = device.get("vendor", "Generic-Vendor")
    equip_type = device.get("type", "O-RU")
    model = device.get("model", "Model-X")
    pnf_id = device.get("pnfId", f"pnf-{device_name}")

    event_payload = {
        "event": {
            "commonEventHeader": {
                "domain": "fault",
                "eventId": f"fault-{current_time_ms}-{_FAULT_SEQUENCE_COUNT}",
                "eventName": f"fault_Fault_Alarms_{alarm.replace(' ', '')}",
                "eventType": "Fault_Alarms",
                "sequence": _FAULT_SEQUENCE_COUNT,
                "priority": priority,
                "reportingEntityId": f"ctrl-{device_name}",
                "reportingEntityName": device_name,
                "sourceId": pnf_id,
                "sourceName": pnf_id,
                "startEpochMicrosec": timestamp_str,
                "lastEpochMicrosec": timestamp_str,
                "nfNamingCode": equip_type[:3].upper(),
                "nfVendorName": vendor,
                "timeZoneOffset": "+00:00",
                "version": "4.1",
                "vesEventListenerVersion": "7.2.1"
            },
            "faultFields": {
                "faultFieldsVersion": "4.0",
                "alarmCondition": alarm,
                "alarmInterfaceA": "N1",
                "eventSourceType": "Fault_Alarms",
                "specificProblem": "Auto Generated Fault",
                "eventSeverity": severity,
                "vfStatus": "Active",
                "alarmAdditionalInformation": {
                    "eventTime": iso_time,
                    "equipType": equip_type,
                    "vendor": vendor,
                    "model": model
                }
            }
        }
    }
    
    _FAULT_SEQUENCE_COUNT += 1
    return send_to_ves(event_payload, f"Fault Alarm ({alarm})")

def heartbeat_event(device=None):
    global _HEARTBEAT_SEQUENCE_COUNT
    device = device or get_device()
    
    current_time_ms = int(time.time() * 1000)
    timestamp_str = str(current_time_ms * 1000)
    iso_time = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    
    device_name = device.get("name", "Unknown-Device")
    vendor = device.get("vendor", "Generic-Vendor")
    equip_type = device.get("type", "O-RU")
    pnf_id = device.get("pnfId", f"pnf-{device_name}")

    event_payload = {
        "event": {
            "commonEventHeader": {
                "domain": "heartbeat",
                "eventId": f"hb-{current_time_ms}-{_HEARTBEAT_SEQUENCE_COUNT}",
                "eventName": f"heartbeat_{device_name}",
                "eventType": "heartbeat",
                "sequence": _HEARTBEAT_SEQUENCE_COUNT,
                "priority": "Low",
                "reportingEntityId": f"ctrl-{device_name}",
                "reportingEntityName": device_name,
                "sourceId": pnf_id,
                "sourceName": pnf_id,
                "startEpochMicrosec": timestamp_str,
                "lastEpochMicrosec": timestamp_str,
                "nfNamingCode": equip_type[:3].upper(),
                "nfVendorName": vendor,
                "timeZoneOffset": "+00:00",
                "version": "4.1",
                "vesEventListenerVersion": "7.2.1"
            },
            "heartbeatFields": {
                "heartbeatFieldsVersion": "3.0",
                "heartbeatInterval": random.choice([20, 30, 60]),
                "additionalFields": {
                    "eventTime": iso_time
                }
            }
        }
    }
    
    _HEARTBEAT_SEQUENCE_COUNT += 1
    return send_to_ves(event_payload, "Periodic Heartbeat")

def notification_event(device=None):
    global _NOTIFICATION_SEQUENCE_COUNT
    device = device or get_device()
    
    current_time_ms = int(time.time() * 1000)
    timestamp_str = str(current_time_ms * 1000)
    iso_time = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    
    device_name = device.get("name", "Unknown-Device")
    vendor = device.get("vendor", "Generic-Vendor")
    equip_type = device.get("type", "O-RU")
    pnf_id = device.get("pnfId", f"pnf-{device_name}")
    
    change_type = random.choice(["informal", "configurationChange", "stateChange"])
    new_state = random.choice(["all-good", "in-service", "active"])
    old_state = random.choice(["not-too-bad", "maintenance", "standby"])

    event_payload = {
        "event": {
            "commonEventHeader": {
                "domain": "notification",
                "eventId": f"notif-{current_time_ms}-{_NOTIFICATION_SEQUENCE_COUNT}",
                "eventName": f"notification_Notification_Fields",
                "eventType": "Notification_Fields",
                "sequence": _NOTIFICATION_SEQUENCE_COUNT,
                "priority": "Low",
                "reportingEntityId": f"ctrl-{device_name}",
                "reportingEntityName": device_name,
                "sourceId": pnf_id,
                "sourceName": pnf_id,
                "startEpochMicrosec": timestamp_str,
                "lastEpochMicrosec": timestamp_str,
                "nfNamingCode": equip_type[:3].upper(),
                "nfVendorName": vendor,
                "timeZoneOffset": "+00:00",
                "version": "4.1",
                "vesEventListenerVersion": "7.2.1"
            },
            "notificationFields": {
                "notificationFieldsVersion": "2.0",
                "changeContact": device_name,
                "changeIdentifier": pnf_id,
                "changeType": change_type,
                "newState": new_state,
                "oldState": old_state,
                "stateInterface": "N1",
                "additionalFields": {
                    "eventTime": iso_time
                }
            }
        }
    }
    
    _NOTIFICATION_SEQUENCE_COUNT += 1
    return send_to_ves(event_payload, f"Notification Status ({change_type})")

def pnf_registration_event(device=None):
    global _PNF_REG_SEQUENCE_COUNT
    device = device or get_device()
    
    current_time_ms = int(time.time() * 1000)
    timestamp_str = str(current_time_ms * 1000)
    
    device_name = device.get("name", "Unknown-Device")
    vendor = device.get("vendor", "Generic-Vendor")
    equip_type = device.get("type", "O-RU")
    model = device.get("model", "Model-X")
    pnf_id = device.get("pnfId", f"pnf-{device_name}")
    serial = device.get("serialNumber", "SN-UNKNOWN")
    sw_ver = device.get("softwareVersion", "1.0.0")
    ip_addr = device.get("ip", "127.0.0.1")
    
    manufacture_date = "2025-01-16"
    last_service_date = "2025-03-26"
    mac_address = f"00:0A:95:{random.randint(10,99)}:{random.randint(10,99)}:{random.randint(10,99)}"

    event_payload = {
        "event": {
            "commonEventHeader": {
                "domain": "pnfRegistration",
                "eventId": f"pnfreg-{current_time_ms}-{_PNF_REG_SEQUENCE_COUNT}",
                "eventName": f"pnfRegistration_PNF_Registration",
                "eventType": "PNF_Registration",
                "sequence": _PNF_REG_SEQUENCE_COUNT,
                "priority": "Low",
                "reportingEntityId": f"ctrl-{device_name}",
                "reportingEntityName": device_name,
                "sourceId": pnf_id,
                "sourceName": pnf_id,
                "startEpochMicrosec": timestamp_str,
                "lastEpochMicrosec": timestamp_str,
                "nfNamingCode": equip_type[:3].upper(),
                "nfVendorName": vendor,
                "timeZoneOffset": "+00:00",
                "version": "4.1",
                "vesEventListenerVersion": "7.2.1"
            },
            "pnfRegistrationFields": {
                "pnfRegistrationFieldsVersion": "2.1",
                "lastServiceDate": last_service_date,
                "macAddress": mac_address,
                "manufactureDate": manufacture_date,
                "modelNumber": model,
                "oamV4IpAddress": ip_addr,
                "oamV6IpAddress": f"2001:db8::{random.randint(1,99)}",
                "serialNumber": f"{vendor}-{equip_type}-{serial}",
                "softwareVersion": sw_ver,
                "unitFamily": f"{vendor}-{equip_type}",
                "unitType": equip_type,
                "vendorName": vendor,
                "additionalFields": {
                    "oamPort": "830",
                    "protocol": "SSH",
                    "username": "netconf",
                    "password": "netconf-password!",
                    "reconnectOnChangedSchema": "false",
                    "sleep-factor": "1.5",
                    "tcpOnly": "false",
                    "connectionTimeout": "20000",
                    "maxConnectionAttempts": "100",
                    "betweenAttemptsTimeout": "2000",
                    "keepaliveDelay": "120"
                }
            }
        }
    }
    
    _PNF_REG_SEQUENCE_COUNT += 1
    return send_to_ves(event_payload, "PNF Registration Profile")

def state_change_event(device=None):
    global _STATE_CHANGE_SEQUENCE_COUNT
    device = device or get_device()
    
    current_time_ms = int(time.time() * 1000)
    timestamp_str = str(current_time_ms * 1000)
    iso_time = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    
    device_name = device.get("name", "Unknown-Device")
    vendor = device.get("vendor", "Generic-Vendor")
    equip_type = device.get("type", "O-RU")
    pnf_id = device.get("pnfId", f"pnf-{device_name}")
    
    new_state = random.choice(["inService", "active", "normal"])
    old_state = random.choice(["maintenance", "standby", "offline"])

    event_payload = {
        "event": {
            "commonEventHeader": {
                "domain": "stateChange",
                "eventId": f"state-{current_time_ms}-{_STATE_CHANGE_SEQUENCE_COUNT}",
                "eventName": f"stateChange_State_Fields",
                "eventType": "State_Fields",
                "sequence": _STATE_CHANGE_SEQUENCE_COUNT,
                "priority": "Low",
                "reportingEntityId": f"ctrl-{device_name}",
                "reportingEntityName": device_name,
                "sourceId": pnf_id,
                "sourceName": pnf_id,
                "startEpochMicrosec": timestamp_str,
                "lastEpochMicrosec": timestamp_str,
                "nfNamingCode": equip_type[:3].upper(),
                "nfVendorName": vendor,
                "timeZoneOffset": "+00:00",
                "version": "4.1",
                "vesEventListenerVersion": "7.2.1"
            },
            "stateChangeFields": {
                "stateChangeFieldsVersion": "4.0",
                "newState": new_state,
                "oldState": old_state,
                "stateInterface": "N1",
                "additionalFields": {
                    "eventTime": iso_time
                }
            }
        }
    }
    
    _STATE_CHANGE_SEQUENCE_COUNT += 1
    return send_to_ves(event_payload, f"State Transition ({old_state} -> {new_state})")

def stnd_defined_heartbeat_event(device=None):
    global _STND_HB_SEQUENCE_COUNT
    device = device or get_device()
    
    current_time_ms = int(time.time() * 1000)
    timestamp_str = str(current_time_ms * 1000)
    iso_time = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    
    device_name = device.get("name", "Unknown-Device")
    vendor = device.get("vendor", "Generic-Vendor")
    equip_type = device.get("type", "O-RU")
    pnf_id = device.get("pnfId", f"pnf-{device_name}")
    serial = device.get("serialNumber", "SN-UNKNOWN")

    event_payload = {
        "event": {
            "commonEventHeader": {
                "domain": "stndDefined",
                "eventId": f"stnd-hb-{current_time_ms}-{_STND_HB_SEQUENCE_COUNT}",
                "eventName": f"stndDefined_heartbeat_heartbeat",
                "eventType": "heartbeat_heartbeat",
                "sequence": _STND_HB_SEQUENCE_COUNT,
                "priority": "Low",
                "reportingEntityId": f"ctrl-{device_name}",
                "reportingEntityName": device_name,
                "sourceId": pnf_id,
                "sourceName": pnf_id,
                "startEpochMicrosec": timestamp_str,
                "lastEpochMicrosec": timestamp_str,
                "nfNamingCode": equip_type[:3].upper(),
                "nfVendorName": vendor,
                "timeZoneOffset": "+00:00",
                "version": "4.1",
                "stndDefinedNamespace": "3GPP-Heartbeat",
                "vesEventListenerVersion": "7.2.1"
            },
            "stndDefinedFields": {
                "schemaReference": "https://forge.3gpp.org/rep/sa5/MnS/raw/Rel-16/OpenAPI/TS28532_HeartbeatNtf.yaml#components/schemas/NotifyHeartbeat",
                "data": {
                    "href": f"https://{device_name.lower()}.domain/3gpp-management/v1/heartbeat",
                    "notificationId": _STND_HB_SEQUENCE_COUNT,
                    "notificationType": "notifyHeartbeat",
                    "eventTime": iso_time,
                    "systemDN": f"SubNetwork=RAN,MeContext={device_name},ManagedElement={serial}",
                    "heartbeatNtfPeriod": 120
                },
                "stndDefinedFieldsVersion": "1.0"
            }
        }
    }
    
    _STND_HB_SEQUENCE_COUNT += 1
    return send_to_ves(event_payload, "Standard-Defined 3GPP Heartbeat")

def stnd_defined_notify_cleared_alarm_event(device=None):
    global _STND_FAULT_SEQUENCE_COUNT
    device = device or get_device()
    
    current_time_ms = int(time.time() * 1000)
    timestamp_str = str(current_time_ms * 1000)
    iso_time = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    
    device_name = device.get("name", "Unknown-Device")
    vendor = device.get("vendor", "Generic-Vendor")
    equip_type = device.get("type", "O-RU")
    pnf_id = device.get("pnfId", f"pnf-{device_name}")
    serial = device.get("serialNumber", "SN-UNKNOWN")
    
    alarm = random.choice(["LinkDown", "HighCpuUsage", "BgpNeighborLoss"])
    severity = random.choice(["WARNING", "MINOR", "MAJOR", "CRITICAL"])

    event_payload = {
        "event": {
            "commonEventHeader": {
                "domain": "stndDefined",
                "eventId": f"stnd-fault-{current_time_ms}-{_STND_FAULT_SEQUENCE_COUNT}",
                "eventName": f"stndDefined_faultsupervision_cleared_{alarm.lower()}",
                "eventType": "faultsupervision_cleared",
                "sequence": _STND_FAULT_SEQUENCE_COUNT,
                "priority": "Low",
                "reportingEntityId": f"ctrl-{device_name}",
                "reportingEntityName": device_name,
                "sourceId": pnf_id,
                "sourceName": pnf_id,
                "startEpochMicrosec": timestamp_str,
                "lastEpochMicrosec": timestamp_str,
                "nfNamingCode": equip_type[:3].upper(),
                "nfVendorName": vendor,
                "timeZoneOffset": "+00:00",
                "version": "4.1",
                "stndDefinedNamespace": "3GPP-FaultSupervision",
                "vesEventListenerVersion": "7.2.1"
            },
            "stndDefinedFields": {
                "schemaReference": "https://forge.3gpp.org/rep/sa5/MnS/raw/Rel-16/OpenAPI/TS28532_FaultMnS.yaml#components/schemas/NotifyClearedAlarm",
                "data": {
                    "href": f"https://{device_name.lower()}.domain/3gpp-management/v1/faults/{_STND_FAULT_SEQUENCE_COUNT}",
                    "notificationId": _STND_FAULT_SEQUENCE_COUNT,
                    "notificationType": "notifyClearedAlarm",
                    "eventTime": iso_time,
                    "systemDN": f"SubNetwork=RAN,MeContext={device_name},ManagedElement={serial}",
                    "alarmId": f"alarm-{alarm}-{_STND_FAULT_SEQUENCE_COUNT}",
                    "alarmType": "COMMUNICATIONS_ALARM",
                    "probableCause": alarm,
                    "perceivedSeverity": severity,
                    "clearUserId": vendor,
                    "clearSystemId": vendor
                },
                "stndDefinedFieldsVersion": "1.0"
            }
        }
    }
    
    _STND_FAULT_SEQUENCE_COUNT += 1
    return send_to_ves(event_payload, f"Standard-Defined 3GPP Cleared Alarm ({alarm})")

def stnd_defined_notify_file_ready_event(device=None):
    global _STND_FILE_SEQUENCE_COUNT
    device = device or get_device()
    
    current_time_ms = int(time.time() * 1000)
    timestamp_str = str(current_time_ms * 1000)
    iso_time = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    
    device_name = device.get("name", "Unknown-Device")
    vendor = device.get("vendor", "Generic-Vendor")
    equip_type = device.get("type", "O-RU")
    pnf_id = device.get("pnfId", f"pnf-{device_name}")
    serial = device.get("serialNumber", "SN-UNKNOWN")
    
    start_window = time.strftime("%Y%m%d.%H%M", time.gmtime(time.time() - 900))
    end_window = time.strftime("%H%M", time.gmtime())

    event_payload = {
        "event": {
            "commonEventHeader": {
                "domain": "stndDefined",
                "eventId": f"stnd-file-{current_time_ms}-{_STND_FILE_SEQUENCE_COUNT}",
                "eventName": f"stndDefined_fileready_pm_export",
                "eventType": "fileready_pm_export",
                "sequence": _STND_FILE_SEQUENCE_COUNT,
                "priority": "Low",
                "reportingEntityId": f"ctrl-{device_name}",
                "reportingEntityName": device_name,
                "sourceId": pnf_id,
                "sourceName": pnf_id,
                "startEpochMicrosec": timestamp_str,
                "lastEpochMicrosec": timestamp_str,
                "nfNamingCode": equip_type[:3].upper(),
                "nfVendorName": vendor,
                "timeZoneOffset": "+00:00",
                "version": "4.1",
                "stndDefinedNamespace": "file-ready",
                "vesEventListenerVersion": "7.2.1"
            },
            "stndDefinedFields": {
                "schemaReference": "https://forge.3gpp.org/rep/sa5/MnS/raw/Rel-16/OpenAPI/TS28532_FileDataReportingMnS.yaml#components/schemas/NotifyFileReady",
                "data": {
                    "href": f"https://{device_name.lower()}.domain/3gpp-management/v1/files/{_STND_FILE_SEQUENCE_COUNT}",
                    "notificationId": _STND_FILE_SEQUENCE_COUNT,
                    "notificationType": "notifyFileReady",
                    "eventTime": iso_time,
                    "systemDN": f"SubNetwork=RAN,MeContext={device_name},ManagedElement={serial}",
                    "fileInfoList": [
                        {
                            "fileLocation": f"/pm-data-files/A{start_window}-{end_window}_{pnf_id}.xml",
                            "fileSize": random.randint(1000, 5000),
                            "fileReadyTime": iso_time,
                            "fileExpirationTime": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(time.time() + 86400)),
                            "fileCompression": "no",
                            "fileFormat": "xml",
                            "fileDataType": "Performance"
                        }
                    ],
                    "additionalText": "O-RAN Software Community OAM Performance Upload"
                },
                "stndDefinedFieldsVersion": "1.0"
            }
        }
    }
    
    _STND_FILE_SEQUENCE_COUNT += 1
    return send_to_ves(event_payload, "Standard-Defined 3GPP File Ready Notification")

def stnd_defined_notify_new_alarm_event(device=None):
    global _STND_NEW_ALARM_SEQUENCE_COUNT
    device = device or get_device()
    
    current_time_ms = int(time.time() * 1000)
    timestamp_str = str(current_time_ms * 1000)
    iso_time = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    
    device_name = device.get("name", "Unknown-Device")
    vendor = device.get("vendor", "Generic-Vendor")
    equip_type = device.get("type", "O-RU")
    model = device.get("model", "Model-X")
    pnf_id = device.get("pnfId", f"pnf-{device_name}")
    serial = device.get("serialNumber", "SN-UNKNOWN")
    
    alarm = random.choice(["ThresholdCrossingAlert", "InterfaceAnomaly", "LossOfSignal"])
    severity = random.choice(["WARNING", "MINOR", "MAJOR", "CRITICAL"])

    event_payload = {
        "event": {
            "commonEventHeader": {
                "domain": "stndDefined",
                "eventId": f"stnd-new-alarm-{current_time_ms}-{_STND_NEW_ALARM_SEQUENCE_COUNT}",
                "eventName": f"stndDefined_faultsupervision_thresholdcrossingalert_{alarm.lower()}",
                "eventType": "faultsupervision_thresholdcrossingalert",
                "sequence": _STND_NEW_ALARM_SEQUENCE_COUNT,
                "priority": "High" if severity in ["MAJOR", "CRITICAL"] else "Low",
                "reportingEntityId": f"ctrl-{device_name}",
                "reportingEntityName": device_name,
                "sourceId": pnf_id,
                "sourceName": pnf_id,
                "startEpochMicrosec": timestamp_str,
                "lastEpochMicrosec": timestamp_str,
                "nfNamingCode": equip_type[:3].upper(),
                "nfVendorName": vendor,
                "timeZoneOffset": "+00:00",
                "version": "4.1",
                "stndDefinedNamespace": "3GPP-FaultSupervision",
                "vesEventListenerVersion": "7.2.1"
            },
            "stndDefinedFields": {
                "schemaReference": "https://forge.3gpp.org/rep/sa5/MnS/raw/Rel-16/OpenAPI/TS28532_FaultMnS.yaml#components/schemas/NotifyNewAlarm",
                "data": {
                    "href": f"https://{device_name.lower()}.domain/3gpp-management/v1/faults/active/{_STND_NEW_ALARM_SEQUENCE_COUNT}",
                    "notificationId": _STND_NEW_ALARM_SEQUENCE_COUNT,
                    "notificationType": "notifyNewAlarm",
                    "eventTime": iso_time,
                    "systemDN": f"SubNetwork=RAN,MeContext={device_name},ManagedElement={serial}",
                    "alarmId": f"alarm-{alarm}-{_STND_NEW_ALARM_SEQUENCE_COUNT}",
                    "alarmType": "COMMUNICATIONS_ALARM",
                    "probableCause": alarm,
                    "specificProblem": f"Performance threshold limit violated for {alarm}",
                    "perceivedSeverity": severity,
                    "backedUpStatus": False,
                    "backUpObject": "xyz",
                    "trendIndication": "MORE_SEVERE",
                    "thresholdInfo": {
                        "observedMeasurement": "packetLossRate",
                        "observedValue": round(random.uniform(0.05, 15.5), 2)
                    },
                    "correlatedNotifications": [],
                    "stateChangeDefinition": [
                        {
                            "operational-state": "DISABLED"
                        }
                    ],
                    "monitoredAttributes": {
                        "interface": "eth0"
                    },
                    "proposedRepairActions": "Check physical layer transmission link or verify DU scheduling profile routing bounds.",
                    "additionalText": "O-RAN Software Community OAM Core Agent Monitoring Engine",
                    "additionalInformation": {
                        "eventTime": iso_time,
                        "equipType": equip_type,
                        "vendor": vendor,
                        "model": model
                    },
                    "rootCauseIndicator": True
                },
                "stndDefinedFieldsVersion": "1.0"
            }
        }
    }
    
    _STND_NEW_ALARM_SEQUENCE_COUNT += 1
    return send_to_ves(event_payload, f"Standard-Defined 3GPP New Alarm Notification ({alarm})")

def threshold_crossing_alert_event(device=None):
    global _TCA_SEQUENCE_COUNT
    device = device or get_device()
    
    current_time_ms = int(time.time() * 1000)
    timestamp_str = str(current_time_ms * 1000)
    iso_time = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    
    device_name = device.get("name", "Unknown-Device")
    vendor = device.get("vendor", "Generic-Vendor")
    equip_type = device.get("type", "O-RU")
    model = device.get("model", "Model-X")
    pnf_id = device.get("pnfId", f"pnf-{device_name}")
    
    metric = random.choice(["packetLoss", "latencyAnomaly", "jitterThresholdExceeded"])
    severity = random.choice(["WARNING", "MAJOR", "CRITICAL"])

    event_payload = {
        "event": {
            "commonEventHeader": {
                "domain": "thresholdCrossingAlert",
                "eventId": f"tca-{current_time_ms}-{_TCA_SEQUENCE_COUNT}",
                "eventName": f"thresholdCrossingAlert_{equip_type}_TCA_{metric}",
                "eventType": f"{equip_type}_TCA",
                "sequence": _TCA_SEQUENCE_COUNT,
                "priority": "High" if severity == "CRITICAL" else "Medium",
                "reportingEntityId": f"ctrl-{device_name}",
                "reportingEntityName": device_name,
                "sourceId": pnf_id,
                "sourceName": pnf_id,
                "startEpochMicrosec": timestamp_str,
                "lastEpochMicrosec": timestamp_str,
                "nfNamingCode": equip_type[:3].upper(),
                "nfVendorName": vendor,
                "timeZoneOffset": "+00:00",
                "version": "4.1",
                "vesEventListenerVersion": "7.2.1"
            },
            "thresholdCrossingAlertFields": {
                "thresholdCrossingFieldsVersion": "4.0",
                "additionalParameters": [
                    {
                        "criticality": "MAJ" if severity in ["MAJOR", "CRITICAL"] else "MIN",
                        "hashMap": {
                            "additionalProperties": "up-and-down",
                            "observedValue": str(round(random.uniform(5.5, 95.2), 2))
                        },
                        "thresholdCrossed": metric
                    }
                ],
                "alertAction": "CLEAR" if random.choice([True, False]) else "SET",
                "alertDescription": f"Performance telemetry metrics crossing alert parameter limits for field: {metric}",
                "alertType": "INTERFACE-ANOMALY",
                "alertValue": equip_type,
                "associatedAlertIdList": ["loss-of-signal", f"tca-internal-{_TCA_SEQUENCE_COUNT}"],
                "collectionTimestamp": iso_time,
                "dataCollector": "data-lake",
                "elementType": equip_type,
                "eventSeverity": severity,
                "eventStartTimestamp": iso_time,
                "interfaceName": "GigabitEthernet0/1",
                "networkService": "from-a-to-b",
                "possibleRootCause": "Interface utilization saturation or queue exhaustion",
                "additionalFields": {
                    "eventTime": iso_time,
                    "equipType": equip_type,
                    "vendor": vendor,
                    "model": model
                }
            }
        }
    }
    
    _TCA_SEQUENCE_COUNT += 1
    return send_to_ves(event_payload, f"Threshold Crossing Alert ({metric})")

def send_to_ves(payload: dict, event_description: str) -> dict:
    """Utility method to handle the REST HTTP connection logic securely."""
    print(f"Connecting to collector at {VES_URL} ...")
    try:
        response = requests.post(VES_URL, json=payload, timeout=5)
        print(f"HTTP Status Code: {response.status_code}")
        print(f"Collector Response: {response.text}")
        response.raise_for_status()
        print(f"Successfully posted {event_description} to VES.")
    except requests.exceptions.RequestException as e:
        print(f"Failed to deliver {event_description} payload to VES collector: {e}")
    return payload

# --- SEQUENTIAL EXECUTION ENGINE ---
if __name__ == "__main__":
    print("Starting Multi-Domain VES Sequential Tester...")
    print("Firing exactly ONE event of EVERY type back-to-back:\n")
    
    all_event_types = [
        ("Fault", fault_event),
        ("Heartbeat", heartbeat_event),
        ("Notification", notification_event),
        ("PNF Registration", pnf_registration_event),
        ("State Change", state_change_event),
        ("StndDefined 3GPP Heartbeat", stnd_defined_heartbeat_event),
        ("StndDefined 3GPP Cleared Alarm", stnd_defined_notify_cleared_alarm_event),
        ("StndDefined 3GPP File Ready", stnd_defined_notify_file_ready_event),
        ("StndDefined 3GPP New Alarm", stnd_defined_notify_new_alarm_event),
        ("Threshold Crossing Alert (TCA)", threshold_crossing_alert_event)
    ]
    
    test_device = get_device()
    print(f"Using Target Node Profile: {test_device['name']} ({test_device['vendor']})\n")

    for index, (label, event_function) in enumerate(all_event_types, 1):
        print(f"=== [Step {index}/10] Sending Schema Vector: {label} ===")
        event_function(device=test_device)
        print("-" * 60)
        time.sleep(1)
        
    print("All 10 distinct VES test packages dispatched sequentially.")