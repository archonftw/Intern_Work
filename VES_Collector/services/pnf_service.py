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

# ==========================================================
# Extraction
# ==========================================================

def extract_pnf_fields(event):
    """
    Extract the required fields from a pnfRegistration VES event.
    """

    event_data = event.get("event", {})

    header = event_data.get("commonEventHeader", {})
    pnf_fields = event_data.get("pnfRegistrationFields", {})
    additional = pnf_fields.get("additionalFields", {})

    return {
        "receivedTime": _utc_now(),

        "oamV4IpAddress": _safe_get(
            pnf_fields,
            "oamV4IpAddress"
        ),

        "protocol": _safe_get(
            additional,
            "protocol"
        ),

        "username": _safe_get(
            additional,
            "username"
        ),

        "password": _safe_get(
            additional,
            "password"
        ),

        # Prefer commonEventHeader.vendorName if present.
        # If your generator later places it inside additionalFields,
        # this will still work.
        "vendorName": (
            header.get("vendorName")
            or additional.get("vendorName")
            or ""
        )
    }


# ==========================================================
# Storage
# ==========================================================

def process_pnf_registration(event):
    """
    Called whenever a pnfRegistration event is received.
    """

    pnf = extract_pnf_fields(event)

    PNF_STORE.append(pnf)

    LOGGER.info(
        "Stored PNF Registration : %s (%s)",
        pnf["vendorName"],
        pnf["oamV4IpAddress"]
    )

    try:
        forward_pnf(pnf)
    except Exception as exc:
        LOGGER.warning("PNF forwarding failed: %s", exc)

    return pnf


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

    success = 0

    for pnf in PNF_STORE:
        try:
            forward_pnf(pnf)
            success += 1
        except Exception as exc:
            LOGGER.warning(exc)

    return {
        "forwarded": success,
        "total": len(PNF_STORE)
    }