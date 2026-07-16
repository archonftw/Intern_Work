import logging
from datetime import datetime, timezone

import requests

from storage.memory import PNF_STORE, PNF_FORWARD_CONFIG


LOGGER = logging.getLogger(__name__)


# ==========================================================
# Helpers
# ==========================================================

def _utc_now():
    return datetime.now(timezone.utc).isoformat()


def _safe_get(data, key, default=""):
    value = data.get(key, default)
    return "" if value is None else value


# ==========================================================
# Extraction
# ==========================================================

def extract_pnf_fields(event):
    """
    Extract the required fields from either a native pnfRegistration 
    or a stndDefined pnfRegistration VES event.
    """
    event_data = event.get("event", {})
    header = event_data.get("commonEventHeader", {})
    domain = header.get("domain", "")

    # Initialize empty tracking scopes
    unit_type = ""
    unit_family = ""
    model_number = ""
    serial_number = ""
    software_version = ""
    oam_v4_ip_address = ""
    protocol = ""
    username = ""
    password = ""
    
    # Extract baseline fallback vendor directly from header fields
    vendor_name = header.get("nfVendorName") or header.get("vendorName") or ""

    # ==========================================
    # Path A: Handle Standard-Defined Events
    # ==========================================
    if domain == "stndDefined":
        stnd_fields = event_data.get("stndDefinedFields", {}) or {}
        data = stnd_fields.get("data", {}) or {}
        
        unit_type = _safe_get(data, "unitType")
        unit_family = _safe_get(data, "unitFamily")
        model_number = _safe_get(data, "modelNumber")
        serial_number = _safe_get(data, "serialNumber")
        software_version = _safe_get(data, "softwareVersion")
        oam_v4_ip_address = _safe_get(data, "oamV4IpAddress")
        
        # Pull configurations from 3GPP data nested structures if present
        protocol = _safe_get(data, "protocol")
        username = _safe_get(data, "username")
        password = _safe_get(data, "password")
        
        if not vendor_name:
            vendor_name = _safe_get(data, "vendorName")

    # ==========================================
    # Path B: Handle Native Native VES Domain
    # ==========================================
    else:
        pnf_fields = event_data.get("pnfRegistrationFields", {}) or {}
        additional = pnf_fields.get("additionalFields", {}) or {}
        
        unit_type = _safe_get(pnf_fields, "unitType")
        unit_family = _safe_get(pnf_fields, "unitFamily")
        model_number = _safe_get(pnf_fields, "modelNumber")
        serial_number = _safe_get(pnf_fields, "serialNumber")
        software_version = _safe_get(pnf_fields, "softwareVersion")
        oam_v4_ip_address = _safe_get(pnf_fields, "oamV4IpAddress")
        
        protocol = _safe_get(additional, "protocol")
        username = _safe_get(additional, "username")
        password = _safe_get(additional, "password")
        
        if not vendor_name:
            vendor_name = _safe_get(additional, "vendorName")

    return {
        "receivedTime": _utc_now(),
        "unitType": unit_type,
        "unitFamily": unit_family,
        "modelNumber": model_number,
        "serialNumber": serial_number,
        "softwareVersion": software_version,
        "oamV4IpAddress": oam_v4_ip_address,
        "protocol": protocol,
        "username": username,
        "password": password,
        "vendorName": vendor_name
    }

# ==========================================================
# Storage + automatic forwarding
# ==========================================================

def process_pnf_registration(event):
    """
    Called whenever a pnfRegistration event is received.
    Extraction, storage, and forwarding all happen here automatically —
    no manual trigger is needed for any individual event.
    """

    pnf = extract_pnf_fields(event)

    PNF_STORE.append(pnf)

    LOGGER.info(
        "Stored PNF Registration : %s (%s)",
        pnf["vendorName"],
        pnf["oamV4IpAddress"]
    )

    _attempt_forward(pnf)

    return pnf


def _attempt_forward(pnf):
    """
    Attempts to forward a single PNF record and records the outcome
    directly on the record so the UI can reflect real forward status
    instead of relying on a manual per-event action.
    """

    if not _forward_config_is_set():
        pnf["forwarded"] = False
        pnf["forwardError"] = "Forward destination not configured"
        return

    try:
        status_code = forward_pnf(pnf)
        pnf["forwarded"] = True
        pnf["forwardError"] = None
        pnf["forwardStatusCode"] = status_code
        pnf["forwardedAt"] = _utc_now()
    except Exception as exc:
        LOGGER.warning("PNF forwarding failed: %s", exc)
        pnf["forwarded"] = False
        pnf["forwardError"] = str(exc)


def _forward_config_is_set():
    host = PNF_FORWARD_CONFIG.get("host")
    port = PNF_FORWARD_CONFIG.get("port")
    path = PNF_FORWARD_CONFIG.get("path")
    return bool(host) and bool(port) and bool(path)


def get_all_pnfs():
    return PNF_STORE


# ==========================================================
# Searching
# ==========================================================

def search_pnfs(query):
    if not query:
        return PNF_STORE

    query = query.lower()

    results = []

    for item in PNF_STORE:

        if (
            query in item["vendorName"].lower()
            or query in item["oamV4IpAddress"].lower()
            or query in item["protocol"].lower()
            or query in item["username"].lower()
            or query in item["password"].lower()
        ):
            results.append(item)

    return results


# ==========================================================
# Forward Configuration
# ==========================================================

def get_forward_config():
    return PNF_FORWARD_CONFIG


def update_forward_config(host=None, port=None, path=None):

    if host:
        PNF_FORWARD_CONFIG["host"] = host

    if port:
        PNF_FORWARD_CONFIG["port"] = int(port)

    if path:
        PNF_FORWARD_CONFIG["path"] = path

    return PNF_FORWARD_CONFIG


# ==========================================================
# Forwarding
# ==========================================================

def forward_pnf(pnf):

    url = (
        f"http://"
        f"{PNF_FORWARD_CONFIG['host']}:"
        f"{PNF_FORWARD_CONFIG['port']}"
        f"{PNF_FORWARD_CONFIG['path']}"
    )

    response = requests.post(
        url,
        json=pnf,
        timeout=5
    )

    LOGGER.info(
        "Forwarded PNF to %s (HTTP %s)",
        url,
        response.status_code
    )

    return response.status_code


def forward_all_pnfs():
    """
    Re-attempts forwarding for every stored PNF, e.g. after the
    forward destination has just been configured. This is a bulk
    retry/backfill utility, not the primary forwarding path — new
    events are always forwarded automatically as they arrive.
    """

    success = 0

    for pnf in PNF_STORE:
        try:
            forward_pnf(pnf)
            pnf["forwarded"] = True
            pnf["forwardError"] = None
            pnf["forwardedAt"] = _utc_now()
            success += 1
        except Exception as exc:
            LOGGER.warning(exc)
            pnf["forwarded"] = False
            pnf["forwardError"] = str(exc)

    return {
        "forwarded": success,
        "total": len(PNF_STORE)
    }