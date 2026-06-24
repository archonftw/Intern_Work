"""
Sample VES 7.x event payloads for testing the collector.
Run with: python sample_events.py
"""

import json
import time
import requests

BASE_URL = "http://localhost:8080"


def post(path: str, payload: dict):
    url = f"{BASE_URL}{path}"
    r = requests.post(url, json=payload, headers={"Content-Type": "application/json"})
    print(f"\n→ POST {path}")
    print(f"  Status : {r.status_code}")
    if r.text:
        print(f"  Body   : {r.text[:200]}")


# ─── Fault Event ──────────────────────────────────────────────────────────────

fault_event = {
    "event": {
        "commonEventHeader": {
            "domain":                  "fault",
            "eventId":                 "fault-001",
            "eventName":               "Fault_gNB_RadioLinkFailure",
            "lastEpochMicrosec":       int(time.time() * 1e6),
            "priority":                "High",
            "reportingEntityName":     "gnb-du-01",
            "sequence":                1,
            "sourceName":              "gnb-01",
            "startEpochMicrosec":      int(time.time() * 1e6),
            "version":                 "4.1",
            "vesEventListenerVersion": "7.2.1"
        },
        "faultFields": {
            "alarmCondition":      "RadioLinkFailure",
            "alarmInterfaceA":     "NR-Uu",
            "eventCategory":       "EQUIPMENT",
            "eventSeverity":       "CRITICAL",
            "eventSourceType":     "gNB",
            "faultFieldsVersion":  "4.0",
            "specificProblem":     "Radio link failure detected on cell 001",
            "vfStatus":            "Active",
            "alarmAdditionalInformation": {
                "cellId": "001",
                "tac":    "100"
            }
        }
    }
}

# ─── Measurement Event ────────────────────────────────────────────────────────

measurement_event = {
    "event": {
        "commonEventHeader": {
            "domain":                  "measurement",
            "eventId":                 "meas-001",
            "eventName":               "Measurement_gNB_KPI",
            "lastEpochMicrosec":       int(time.time() * 1e6),
            "priority":                "Normal",
            "reportingEntityName":     "gnb-cu-01",
            "sequence":                1,
            "sourceName":              "gnb-01",
            "startEpochMicrosec":      int(time.time() * 1e6),
            "version":                 "4.1",
            "vesEventListenerVersion": "7.2.1"
        },
        "measurementFields": {
            "measurementInterval":      900,
            "measurementFieldsVersion": "4.0",
            "requestRate":              1250.5,
            "meanRequestLatency":       3.2,
            "cpuUsageArray": [
                {"cpuIdentifier": "cpu-0", "cpuUsageActive": 42.3}
            ],
            "memoryUsageArray": [
                {"memoryIdentifier": "mem-0", "memoryConfigured": 16384, "memoryUsed": 7200}
            ],
            "additionalMeasurements": [
                {
                    "name": "5g-kpis",
                    "hashMap": {
                        "DRB.UEThpDl":  "125.4",
                        "DRB.UEThpUl":  "45.2",
                        "RRC.ConnMean":  "312"
                    }
                }
            ]
        }
    }
}

# ─── Batch (fault + measurement) ─────────────────────────────────────────────

batch_payload = {
    "eventList": [
        {**fault_event["event"]},
        {**measurement_event["event"], "commonEventHeader": {
            **measurement_event["event"]["commonEventHeader"],
            "eventId": "meas-002",
            "sequence": 2
        }}
    ]
}

# ─── Run ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=== VES 7.x Collector Test ===")

    post("/eventListener/v7", fault_event)
    post("/eventListener/v7", measurement_event)
    post("/eventListener/v7/eventBatch", batch_payload)

    # Query collected events
    r = requests.get(f"{BASE_URL}/collector/events?domain=fault")
    print(f"\n→ GET /collector/events?domain=fault")
    print(f"  Status : {r.status_code}")
    data = r.json()
    print(f"  Total  : {data['total']} fault events")
