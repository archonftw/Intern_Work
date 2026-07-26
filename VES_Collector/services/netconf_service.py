import logging

from ncclient import manager
from ncclient.operations import RPCError

LOGGER = logging.getLogger("VES-COLLECTOR")

VES_PNF_NS = "urn:ves:pnf-registration"


def _esc(value):
    """Escape a value for safe inclusion inside XML element text."""
    return (
        str(value if value is not None else "")
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def build_pnf_edit_config_xml(pnf: dict) -> str:
    """
    Build NETCONF edit-config payload.
    """

    serial = _esc(
        pnf.get("serialNumber") or "UNKNOWN"
    )

    return f"""
<config xmlns="urn:ietf:params:xml:ns:netconf:base:1.0">
    <pnf xmlns="urn:ves:pnf-registration"
         xmlns:xc="urn:ietf:params:xml:ns:netconf:base:1.0"
         xc:operation="merge">

        <serial-number>{serial}</serial-number>
        <vendor-name>{_esc(pnf.get('vendorName'))}</vendor-name>
        <unit-type>{_esc(pnf.get('unitType'))}</unit-type>
        <unit-family>{_esc(pnf.get('unitFamily'))}</unit-family>
        <model-number>{_esc(pnf.get('modelNumber'))}</model-number>
        <software-version>{_esc(pnf.get('softwareVersion'))}</software-version>
        <oam-v4-ip-address>{_esc(pnf.get('oamV4IpAddress'))}</oam-v4-ip-address>
        <protocol>{_esc(pnf.get('protocol'))}</protocol>
        <username>{_esc(pnf.get('username'))}</username>
        <received-time>{_esc(pnf.get('receivedTime'))}</received-time>

    </pnf>
</config>
"""

def forward_pnf_netconf(pnf: dict, host: str, port: int, username: str, key_filename: str, timeout: int = 10) -> str:
    """
    Sends a single PNF record to the netopeer2 server via NETCONF
    edit-config against the running datastore (writable-running is
    advertised in this server's capabilities, so no candidate/commit
    step is required).

    Authenticates via SSH private key (key_filename), not password —
    this project intentionally does not use password auth for NETCONF.

    Returns a short status string on success. Raises on failure so
    callers can catch and stamp forwardError, same pattern as the
    original HTTP forward_pnf().
    """
    config_xml = build_pnf_edit_config_xml(pnf)

    if not key_filename:
        raise RuntimeError("No SSH key_filename configured for NETCONF forwarding")

    try:
        with manager.connect(
            host=host,
            port=port,
            username=username,
            password=None,
            hostkey_verify=False,
            look_for_keys=True,
            allow_agent=True,
            key_filename=key_filename,
            device_params={"name": "default"},
            timeout=timeout,
        ) as m:
            reply = m.edit_config(target="running", config=config_xml)

            LOGGER.info(
                "Forwarded PNF %s to NETCONF target %s:%s via key %s (ok=%s)",
                pnf.get("serialNumber"),
                host, port, key_filename,
                getattr(reply, "ok", None),
            )

            return "ok"

    except RPCError as exc:
        raise RuntimeError(f"NETCONF RPC error: {exc}") from exc
    except Exception as exc:
        raise RuntimeError(f"NETCONF connection/edit-config failed: {exc}") from exc