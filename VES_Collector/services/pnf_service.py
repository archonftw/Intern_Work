import logging
from datetime import datetime, timezone

from storage.memory import PNF_STORE, NETCONF_FORWARD_CONFIG
from services.netconf_service import forward_pnf_netconf


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