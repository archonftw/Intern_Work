import logging
from datetime import datetime, timezone

from storage.memory import PNF_STORE, NETCONF_FORWARD_CONFIG
from services.netconf_service import (forward_pnf_netconf,netconf_service,build_pnf_edit_config_xml)


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
    Extract PNF registration fields from VES event.
    Supports:
    - native pnfRegistration
    - stndDefined pnfRegistration
    """

    event_data = event.get("event", {})
    header = event_data.get("commonEventHeader", {})
    domain = header.get("domain", "")

    vendor_name = (
        header.get("nfVendorName")
        or header.get("vendorName")
        or ""
    )

    unit_type = ""
    unit_family = ""
    model_number = ""
    serial_number = ""
    software_version = ""
    oam_v4_ip_address = ""
    protocol = ""
    username = ""
    password = ""


    # ==========================================
    # stndDefined
    # ==========================================
    if domain == "stndDefined":

        stnd_fields = event_data.get(
            "stndDefinedFields",
            {}
        ) or {}

        data = stnd_fields.get(
            "data",
            {}
        ) or {}


        unit_type = _safe_get(data, "unitType")
        unit_family = _safe_get(data, "unitFamily")
        model_number = _safe_get(data, "modelNumber")
        serial_number = _safe_get(data, "serialNumber")
        software_version = _safe_get(data, "softwareVersion")
        oam_v4_ip_address = _safe_get(data, "oamV4IpAddress")

        protocol = _safe_get(data, "protocol")
        username = _safe_get(data, "username")
        password = _safe_get(data, "password")


        if not vendor_name:
            vendor_name = _safe_get(
                data,
                "vendorName"
            )


    # ==========================================
    # Native VES
    # ==========================================
    else:

        pnf_fields = event_data.get(
            "pnfRegistrationFields",
            {}
        ) or {}


        additional = pnf_fields.get(
            "additionalFields",
            {}
        ) or {}


        unit_type = _safe_get(
            pnf_fields,
            "unitType"
        )

        unit_family = _safe_get(
            pnf_fields,
            "unitFamily"
        )

        model_number = _safe_get(
            pnf_fields,
            "modelNumber"
        )

        serial_number = _safe_get(
            pnf_fields,
            "serialNumber"
        )

        software_version = _safe_get(
            pnf_fields,
            "softwareVersion"
        )

        oam_v4_ip_address = _safe_get(
            pnf_fields,
            "oamV4IpAddress"
        )


        protocol = _safe_get(
            additional,
            "protocol"
        )

        username = _safe_get(
            additional,
            "username"
        )

        password = _safe_get(
            additional,
            "password"
        )


        if not vendor_name:
            vendor_name = _safe_get(
                additional,
                "vendorName"
            )


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
# Storage + Forwarding
# ==========================================================

def process_pnf_registration(event):
    """
    Extracts PNF fields, stores in local memory, and auto-syncs
    directly to Netopeer2 using the PNF's dynamic serial number.
    """
    pnf = extract_pnf_fields(event)
    PNF_STORE.append(pnf)

    LOGGER.info(
        "Stored PNF Registration: %s (%s)",
        pnf.get("vendorName"),
        pnf.get("oamV4IpAddress")
    )

    # 1. Attempt standard forwarding
    _attempt_forward(pnf)

    # 2. Dynamic NETCONF sync to Netopeer2 using PNF serial number
    push_pnf_to_netopeer(pnf)

    return pnf


def push_pnf_to_netopeer(pnf):
    """Pushes extracted PNF fields as YANG XML into Netopeer2 using dynamic serial number."""
    # Dynamically resolve device ID: Serial Number -> Unit Type -> Fallback
    device_id = pnf.get("serialNumber") or pnf.get("unitType") or "local-netopeer"

    active_sessions = getattr(netconf_service, "sessions", {})

    # Automatically connect a dedicated session for this dynamic device ID
    if device_id not in active_sessions:
        try:
            netconf_service.connect(
                device_id=device_id,
                host="127.0.0.1",
                port=830,
                username="archon",
                key_filename="/home/archon/.ssh/id_ed25519"
            )
            LOGGER.info("[Netopeer Auto-Connect] Connected session for PNF: %s", device_id)
        except Exception as err:
            LOGGER.error("[Netopeer Auto-Connect Error] Failed to connect %s: %s", device_id, err)
            return

    # Construct YANG XML matching ves-pnf-registration schema
    config_xml = build_pnf_edit_config_xml(pnf)

    try:
        # Edit candidate and commit live
        netconf_service.edit_config(device_id=device_id, config=config_xml, target="candidate")
        netconf_service.commit(device_id=device_id)
        LOGGER.info("[Netopeer2 Push] PNF '%s' successfully committed to live datastore.", device_id)
    except Exception as exc:
        LOGGER.error("[Netopeer2 Push Error] Failed to commit PNF '%s' to Netopeer2: %s", device_id, exc)

def _attempt_forward(pnf):

    if not _forward_config_is_set():

        pnf["forwarded"] = False

        pnf["forwardError"] = (
            "NETCONF forward destination not configured"
        )

        return


    try:

        forward_pnf(pnf)

        pnf["forwarded"] = True

        pnf["forwardError"] = None

        pnf["forwardedAt"] = _utc_now()


    except Exception as exc:

        LOGGER.warning(
            "PNF NETCONF forwarding failed: %s",
            exc
        )

        pnf["forwarded"] = False

        pnf["forwardError"] = str(exc)



def _forward_config_is_set():

    return (

        bool(NETCONF_FORWARD_CONFIG.get("host"))

        and bool(NETCONF_FORWARD_CONFIG.get("port"))

        and bool(NETCONF_FORWARD_CONFIG.get("username"))

        and bool(NETCONF_FORWARD_CONFIG.get("key_filename"))

    )



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

            query in item.get(
                "vendorName",
                ""
            ).lower()

            or query in item.get(
                "oamV4IpAddress",
                ""
            ).lower()

            or query in item.get(
                "protocol",
                ""
            ).lower()

            or query in item.get(
                "username",
                ""
            ).lower()

        ):

            results.append(item)


    return results



# ==========================================================
# NETCONF Configuration
# ==========================================================

def get_forward_config():

    return dict(NETCONF_FORWARD_CONFIG)



def update_forward_config(
        host=None,
        port=None,
        username=None,
        key_filename=None
):

    if host:

        NETCONF_FORWARD_CONFIG["host"] = host


    if port:

        NETCONF_FORWARD_CONFIG["port"] = int(port)


    if username:

        NETCONF_FORWARD_CONFIG["username"] = username


    if key_filename:

        NETCONF_FORWARD_CONFIG["key_filename"] = key_filename


    return get_forward_config()



# ==========================================================
# Forwarding
# ==========================================================

def forward_pnf(pnf):
    print("PNF forwarded:",pnf)
    return forward_pnf_netconf(

        pnf,

        host=NETCONF_FORWARD_CONFIG["host"],

        port=NETCONF_FORWARD_CONFIG["port"],

        username=NETCONF_FORWARD_CONFIG["username"],

        key_filename=NETCONF_FORWARD_CONFIG["key_filename"]

    )



def forward_all_pnfs():

    success = 0


    for pnf in PNF_STORE:

        try:

            forward_pnf(pnf)

            pnf["forwarded"] = True

            pnf["forwardError"] = None

            pnf["forwardedAt"] = _utc_now()


            success += 1


        except Exception as exc:

            LOGGER.warning(
                "Forward failed: %s",
                exc
            )

            pnf["forwarded"] = False

            pnf["forwardError"] = str(exc)



    return {

        "forwarded": success,

        "total": len(PNF_STORE)

    }