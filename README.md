# VES Collector & NOC Dashboard

A lightweight [ONAP VES](https://docs.onap.org/projects/onap-vnfrqts-requirements/en/latest/Chapter8/ves_7_2.html) 7.x-compliant event collector and live network operations dashboard, built with Flask. Designed to ingest telemetry from virtual/physical network functions (fault, heartbeat, measurement, notification, state change, threshold crossing, and PNF registration events) and surface them in real time for NOC monitoring.

## Features

- **VES 7.x event ingestion** — single-event and batch endpoints, JSON Schema-validated against the `commonEventHeader` and per-domain field schemas (fault, heartbeat, measurement, notification, stateChange, thresholdCrossingAlert, pnfRegistration, stndDefined)
- **Per-device state tracking** — automatically discovers devices from incoming events and maintains a rolling history of faults, measurements, notifications, state changes, and thresholds per device
- **Lazy device status detection** — derives `ONLINE` / `STALE` / `OFFLINE` status per device from heartbeat cadence and last-seen time, no background polling required
- **Bounded memory footprint** — per-device and global event history is capped so the collector can run indefinitely without growing unbounded
- **Live NOC dashboard** — dark-themed, auto-polling web UI with severity breakdowns, KPI trend charts, alarm correlation, and a filterable event table
- **REST API** for events, devices, stats, and domain breakdowns, so the dashboard (or any other client) can be built independently of the ingestion path

## Architecture

```
                 ┌──────────────────────┐
  VES events ──▶ │  /eventListener/v7    │
  (single)       │  /eventListener/v7/   │
                 │      eventBatch       │
                 └──────────┬───────────┘
                            │ validate (schemas.py)
                            │ dispatch (process_event)
                            ▼
                 ┌──────────────────────┐
                 │   DEVICE_STORE        │  per-device rolling history
                 │   EVENT_STORE         │  global event log (capped)
                 └──────────┬───────────┘
                            │
                 ┌──────────▼───────────┐
                 │   REST API            │  /api/events, /api/devices,
                 │                       │  /api/stats, /api/domains
                 └──────────┬───────────┘
                            │
                 ┌──────────▼───────────┐
                 │   NOC Dashboard        │  templates/dashboard.html
                 └──────────────────────┘
```

## Requirements

- Python 3.9+
- Flask
- jsonschema

Install dependencies:

```bash
pip install flask jsonschema
```

## Running the collector

```bash
python ves_collector.py
```

The server starts on `0.0.0.0:8080`. Open `http://localhost:8080` for the dashboard.

## API Reference

### Ingestion

| Endpoint | Method | Description |
|---|---|---|
| `/eventListener/v7` | `POST` | Ingest a single VES event envelope (`{"event": {...}}`) |
| `/eventListener/v7/eventBatch` | `POST` | Ingest a batch (`{"eventList": [...]}`). Partial failures are reported per-item rather than failing the whole batch |

### Read / Dashboard API

| Endpoint | Method | Description |
|---|---|---|
| `/` | `GET` | NOC dashboard UI |
| `/api/events?limit=N` | `GET` | Most recent `N` events (default 100) |
| `/api/devices` | `GET` | All known devices with live status, fault/threshold counts |
| `/api/device/<device_id>` | `GET` | Full state for a single device |
| `/api/device/<device_id>/events` | `GET` | Recent raw events for a single device |
| `/api/stats` | `GET` | Aggregate counts by domain and fault severity |
| `/api/domains` | `GET` | Event counts grouped by VES domain |
| `/healthcheck` | `GET` | Liveness check, event/device counts, device status breakdown |

## Supported VES domains

| Domain | Field schema | Notes |
|---|---|---|
| `fault` | `faultFields` | Required: `alarmCondition`, `eventSeverity`, `specificProblem` |
| `heartbeat` | `heartbeatFields` | Drives device staleness detection |
| `measurement` | `measurementFields` | Array of `{name, value}` KPI measurements |
| `notification` | `notificationFields` | |
| `stateChange` | `stateChangeFields` | |
| `thresholdCrossingAlert` | `thresholdCrossingAlertFields` | |
| `pnfRegistration` | `pnfRegistrationFields` | Populates device vendor/model |
| `stndDefined` | `stndDefinedFields` | Dispatched further by `eventName` pattern (file-ready, PNF O1 registration, threshold alert/clear) |
| `syslog`, `voiceQuality`, `other` | — | Accepted per spec, passed through without field-level validation |

## Device status model

Device status is computed lazily on every read (no background thread) from `lastSeen` and the device's observed `heartbeatInterval`:

- **ONLINE** — last seen within 2 heartbeat intervals
- **STALE** — missed 2–4 intervals
- **OFFLINE** — missed 4+ intervals
- **UNKNOWN** — no events received yet, or no valid timestamp

Devices that have never sent a `heartbeat` event fall back to a default interval (`DEFAULT_HEARTBEAT_INTERVAL_SEC`, 60s).

## Project structure

```
.
├── ves_collector.py        # Flask app: ingestion, validation, device tracking, REST API
├── schemas.py               # VES 7.x JSON Schemas (common header + per-domain field schemas)
├── templates/
│   └── dashboard.html       # NOC dashboard UI
└── README.md
```

## Known limitations / roadmap

- In-memory storage only — state is lost on restart; no persistence layer yet
- Single-process only — device status and event stores aren't shared across multiple workers/instances
- No authentication on ingestion or API endpoints
- Status transitions are computed on read, not pushed — no alerting hook (e.g. Slack/webhook) on a device going `OFFLINE` yet

## License

Internal / unlicensed — add a license here if this is intended for distribution.
