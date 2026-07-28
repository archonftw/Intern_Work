# VES Collector — NOC Console

A Flask-based network event collector and live monitoring dashboard, built against the **ONAP VES 7.x** standard and **3GPP `stndDefined`** standard notifications. Simulated 5G/O-RAN network functions (gNB, DU, CU, RU, AMF, SMF, UPF, MEC, etc.) send VES-formatted events to the collector, which validates, stores, correlates, and displays them on a NOC-style dashboard — and automatically forwards PNF registration data on to a NETCONF-managed system.

> Full architecture documentation (arc42-structured) is available in `docs/VES_Collector_arc42.pdf` / `.docx`. This README is the practical get-it-running guide.

---

## Table of Contents

- [Features](#features)
- [Architecture at a Glance](#architecture-at-a-glance)
- [Prerequisites](#prerequisites)
- [Setup](#setup)
- [Running the Collector](#running-the-collector)
- [Simulating Traffic](#simulating-traffic)
- [Project Structure](#project-structure)
- [Configuration](#configuration)
- [PNF → NETCONF Forwarding Setup](#pnf--netconf-forwarding-setup)
- [Dashboard Guide](#dashboard-guide)
- [API Reference](#api-reference)
- [Adding a New Domain / stndDefined Sub-Type](#adding-a-new-domain--stnddefined-sub-type)
- [Known Limitations](#known-limitations)
- [Troubleshooting](#troubleshooting)

---

## Features

- **VES 7.x ingestion** — single (`/eventListener/v7`) and batch (`/eventListener/v7/eventBatch`) endpoints, with per-item validation on batch requests.
- **JSON-Schema-backed validation** — every domain and every `stndDefined` sub-type validates against its own schema file in `schemas/`, loaded and cached at runtime (no restart needed to fix or add schemas — just edit the JSON, or call the reload hook).
- **Full domain coverage**: `fault`, `heartbeat`, `measurement`, `notification`, `stateChange`, `thresholdCrossingAlert`, `pnfRegistration`, and `stndDefined` (fanning out into `notifyHeartbeat`, `notifyNewAlarm`, `notifyClearedAlarm`, `notifyFileReady`, `notifyPNFRegistration`).
- **Automatic PNF forwarding** — every PNF registration event is immediately forwarded via **NETCONF** (SSH-key authenticated) to a `netopeer2`/`sysrepo` server, shaped to a custom YANG module.
- **SSRF-guarded file fetching** — `fileReady` events can be previewed/downloaded on demand; private/loopback destinations are refused by default.
- **Live NOC dashboard** — Overview, Alarms (correlated + acknowledgeable), Devices (staleness detection), PNF Registration, Files, STND Defined (grouped by sub-type), and a full Event Explorer with a resizable, sticky detail panel.
- **Traffic generator** (`testing/generator.py`) — simulates 45 realistic network functions across RAN, Core, transport, and O-RAN, with a sequential "one of every event type" test mode.

---

## Architecture at a Glance

```
generator.py --VES JSON/HTTP--> routes/ingestion.py --> event_service.process_single_event()
                                                              │
                                            ┌─────────────────┼─────────────────┐
                                            ▼                 ▼                 ▼
                                    validation.py      process_event()   device_service.py
                                    (schema check)       (domain dispatch)  (staleness)
                                                              │
                                                   ┌──────────┴──────────┐
                                                   ▼                     ▼
                                          pnf_service.py          stnd_service.py
                                          (extract, store,        (fileReady, alarms,
                                           NETCONF forward)         PNF reg routing)
                                                              │
                                                              ▼
                                                    EVENT_STORE (in-memory)
                                                              │
                                                              ▼
                                                    dashboard.html (polls /api/*)
```

See `docs/VES_Collector_arc42.pdf` for the full building-block breakdown, runtime scenarios, and architecture decision log.

---

## Prerequisites

- **Python 3.10+**
- **pip** with `--break-system-packages` if your system Python is externally managed
- A **NETCONF target** for PNF forwarding — this project targets a locally-run [`netopeer2`](https://github.com/CESNET/netopeer2) server backed by `sysrepo`. Forwarding can be left unconfigured if you only need ingestion/dashboard functionality.
- An SSH keypair already trusted by your netopeer2 server, if you want PNF forwarding to work (see [PNF → NETCONF Forwarding Setup](#pnf--netconf-forwarding-setup)).

---

## Setup

```bash
git clone <this-repo-url>
cd VES_Collector

python3 -m venv venv
source venv/bin/activate

pip install -r requirements.txt --break-system-packages
```

If there's no `requirements.txt` yet, the core dependencies are:
```bash
pip install flask jsonschema requests ncclient paramiko python-dotenv --break-system-packages
```

Copy the example env file and fill in anything you need (all optional — the app runs fine with no `.env` at all, just with PNF forwarding disabled until configured):
```bash
cp .env.example .env
```

---

## Running the Collector

```bash
python3 app.py
```

By default this serves the ingestion endpoints and dashboard on **`http://localhost:8080`**. Open that URL in a browser to see the dashboard — it'll show "no events yet" until traffic starts flowing.

---

## Simulating Traffic

From a second terminal (same venv):

```bash
cd testing
python3 generator.py
```

This registers all 45 simulated devices immediately (so the Devices view has vendor/model populated right away), then continuously sends randomized events across every domain.

If you just want to sanity-check that every domain/schema validates correctly, look for (or ask the maintainer for) the **sequential test mode** variant of the generator — it fires exactly one event of every supported type back-to-back and prints the HTTP status + response for each, which is the fastest way to confirm the whole validation pipeline end-to-end after any schema change.

---

## Project Structure

```
VES_Collector/
├── app.py                       Flask entrypoint, blueprint registration
├── config.py                    Buffer caps, timeouts, unvalidated domains, fetch guards
├── .env                         Local secrets/config (NOT committed — see .env.example)
│
├── routes/
│   ├── ingestion.py              /eventListener/v7 (+ batch)
│   └── pnf.py                    /api/pnf/*
│
├── services/
│   ├── event_service.py          Central ingestion pipeline (single entrypoint)
│   ├── validation.py             Domain + stndDefined schema validation
│   ├── schema_service.py         Cached JSON schema loader
│   ├── stnd_service.py           stndDefined event dispatch (fileReady, alarms, PNF reg)
│   ├── pnf_service.py            PNF extraction, storage, automatic NETCONF forward
│   ├── netconf_service.py        NETCONF edit-config builder + sender (ncclient)
│   ├── file_ready_service.py     fileReady extraction + SSRF-guarded fetch
│   └── device_service.py         Device staleness computation
│
├── schemas/                      One JSON Schema file per domain + per stndDefined sub-type
├── storage/
│   └── memory.py                 In-memory stores (EVENT_STORE, PNF_STORE, FILE_STORE, config)
│
├── templates/
│   └── dashboard.html            Main NOC console UI
├── static/                       CSS + JS assets
│
├── testing/
│   └── generator.py              Synthetic multi-domain VES traffic generator
│
├── ves-pnf-registration.yang     Custom YANG module for NETCONF forwarding target
└── docs/
    ├── VES_Collector_arc42.pdf
    └── VES_Collector_arc42.docx
```

---

## Configuration

Everything tunable lives in **`config.py`** (buffer sizes, timeouts, fetch guards) and **`storage/memory.py`** (runtime-configurable forwarding destination).

### `config.py` — key settings

| Setting | Purpose | Default |
|---|---|---|
| `MAX_GLOBAL_EVENT_STORE` | Max events kept in memory | `1000` |
| `MAX_FILE_STORE` | Max fileReady records kept | `5000` |
| `KNOWN_UNVALIDATED_DOMAINS` | Domains explicitly skipped during schema validation | `{"syslog", "voiceQuality", "other"}` |
| `ALLOW_REMOTE_FETCH` | Allow fetching fileReady content at all | `False` |
| `ALLOW_PRIVATE_IPS` | Allow fetching from private/loopback hosts (dev only) | `False` |
| `MAX_FETCH_BYTES` | Size cap on file fetch | `10 MB` |
| `FETCH_TIMEOUT_SEC` | Timeout on file fetch | `15` |

### PNF/NETCONF forwarding config — `storage/memory.py`

```python
NETCONF_FORWARD_CONFIG = {
    "host": None,
    "port": 830,
    "username": None,
    "key_filename": None,     # path to your SSH private key
    "key_passphrase": None,   # only if the key itself is passphrase-protected
}
```

This can be left as-is (forwarding will just report `"NETCONF forward destination not configured"` per record) or set via:
- the dashboard's **Configure Forwarding** modal (PNF Registration view), or
- environment variables in `.env`, if wired up in your copy of `memory.py`:
  ```
  NETCONF_HOST=localhost
  NETCONF_PORT=830
  NETCONF_USERNAME=youruser
  NETCONF_KEY_FILENAME=/home/youruser/.ssh/id_ed25519
  ```

**Note:** this project intentionally uses **SSH key authentication only** for NETCONF — there is no password field, by design (see the arc42 doc's Architecture Decisions section for why).

---

## PNF → NETCONF Forwarding Setup

Only needed if you want the PNF Registration forwarding feature working end-to-end. If you just want to run the collector/dashboard, skip this section.

1. **Install the custom YANG module** into your sysrepo repository:
   ```bash
   sysrepoctl -i ves-pnf-registration.yang
   sysrepoctl -l | grep ves-pnf-registration   # confirm it's listed
   ```

2. **Restart `netopeer2-server`** — schema changes are *not* hot-reloaded into an already-running server process:
   ```bash
   sudo systemctl restart netopeer2-server
   # or kill + relaunch however you normally start it
   ```

3. **Make sure your SSH key is trusted** by the server's configured NETCONF user (check `ietf-netconf-server`/`ietf-ssh-server` config via `sysrepocfg -X -d running -m ietf-netconf-server -f xml`). If your key has a passphrase, load it into `ssh-agent` once rather than relying on `key_passphrase` being passed through — this project's underlying NETCONF client library does not support passing a passphrase directly:
   ```bash
   eval "$(ssh-agent -s)"
   ssh-add ~/.ssh/id_ed25519
   ```

4. **Set the forwarding config** via the dashboard's Configure Forwarding modal (Host, Port, Username, SSH Key Path).

5. **Verify** a registration actually landed:
   ```bash
   curl -s http://localhost:8080/api/pnf | python3 -m json.tool   # check "forwarded": true
   sysrepocfg -X -d running -m ves-pnf-registration -f xml        # confirm the data is really there
   ```

---

## Dashboard Guide

| View | What it's for |
|---|---|
| **Overview** | At-a-glance stats, domain distribution chart, live feed, open-alarm count. |
| **Alarms** | Correlated fault/threshold events grouped by device + condition. Click any row for full detail + occurrence history. Search, filter by domain/severity/time-range, acknowledge. |
| **Devices** | Every reporting network function, staleness status (Online/Stale/Offline), vendor/model from last registration. |
| **PNF Registration** | Every registered PNF, forward status per record, Configure Forwarding, per-record retry. |
| **Files** | `fileReady` announcements; preview or download content on demand. |
| **STND Defined** | `stndDefined` events grouped by resolved notification type. |
| **Event Explorer** | Raw searchable/sortable table of every event, with a resizable side-by-side detail panel — no scrolling needed to inspect any row's full JSON. `stndDefined` rows carry an inline sub-type tag so they're distinguishable at a glance. |

---

## API Reference

| Endpoint | Method | Purpose |
|---|---|---|
| `/eventListener/v7` | POST | Single VES event ingestion |
| `/eventListener/v7/eventBatch` | POST | Batch ingestion (`{"eventList": [...]}`) |
| `/api/events` | GET | Recent events (dashboard feed) |
| `/api/stats` | GET | Aggregate counts per domain |
| `/api/devices` | GET | All tracked devices |
| `/api/device/{id}` | GET | Single device detail |
| `/api/device/{id}/events` | GET | Recent events for one device |
| `/api/pnf` | GET | All PNF registrations (credentials masked) |
| `/api/pnf/search?q=` | GET | Search PNF records |
| `/api/pnf/config` | GET/POST | View/update NETCONF forwarding config |
| `/api/pnf/forward` | POST | Retry forwarding for all stored PNF records |

---

## Adding a New Domain / stndDefined Sub-Type

1. Add the new JSON Schema file to `schemas/`.
2. For a native domain: add an entry to `DOMAIN_SCHEMAS` in `services/validation.py` (field-block name + schema filename).
3. For a new `stndDefined` sub-type: add an entry to `STND_SCHEMA_MAP` keyed by its `notificationType` value.
4. If it needs its own routing/side-effects (like `fileReady` does), add a handler in `services/stnd_service.py`.
5. Add a generator function in `testing/generator.py` so it's covered by the sequential test mode.
6. Run the generator's sequential test mode and confirm a clean `202` for the new type before merging.

---

## Known Limitations

- **In-memory storage only** — all data (events, PNF records, files, device state) is lost on restart. This is intentional for this project's scope, not a bug.
- **Alarm acknowledgement is client-side only** (`localStorage`) — not shared across browsers/operators viewing the same collector instance.
- **stndDefined PNF registration** — an older payload shape (identified by `eventName` convention rather than `notificationType`) may not be covered by current schema mapping/test vectors; confirm with the team before assuming full coverage if you're working with that event type.

---

## Troubleshooting

**"Missing 'notificationType' in stndDefinedFields"**
Your `stndDefined` payload doesn't have `stndDefinedFields.data.notificationType` set, or it's nested differently than expected. Check the payload shape against `schemas/stndDefined-*.json`.

**PNF forwarding says "NETCONF forward destination not configured"**
Set `host`/`port`/`username`/`key_filename` via the dashboard's Configure Forwarding modal or `.env` — see [Configuration](#configuration).

**PNF forwarding fails with a `KeyError` or `SSHSession.connect() got an unexpected keyword argument`**
This is a known `ncclient` version quirk — make sure `manager.connect()` in `netconf_service.py` explicitly passes `look_for_keys`, `allow_agent`, and `key_filename` (even if some are effectively unused), and does **not** pass a `passphrase` kwarg (unsupported in some `ncclient` versions — use `ssh-agent` instead for passphrase-protected keys).

**A newly-installed YANG module isn't showing up over NETCONF**
`netopeer2-server` doesn't hot-reload schema changes — you must actually restart the server process (not just re-run `sysrepoctl -i`) after installing a new module.

**`sysrepoctl -i` fails with "Permission denied"**
Your sysrepo repository directory likely has mixed ownership (some files root-owned from an earlier `sudo` command). Fix with:
```bash
sudo chown -R $(whoami):$(whoami) /path/to/sysrepo/build/repository
```

**Validation error: `'event' is a required property`**
A schema file is written as a full VES-envelope schema (`{"event": {...}}`), but the data being validated wasn't wrapped in that envelope before calling `jsonschema.validate()`. Check whether `validate_domain()` wraps the event correctly for that particular schema.

**File preview does nothing / fails silently**
Check `ALLOW_REMOTE_FETCH` and `ALLOW_PRIVATE_IPS` in `config.py` — remote fetching is disabled by default, and private/loopback hosts are refused unless explicitly allowed (SSRF protection).

---

## Questions?

Check `docs/VES_Collector_arc42.pdf` first — it covers the full architecture, runtime scenarios, and the reasoning behind every major design decision. If it's not answered there, ask in the team channel.
