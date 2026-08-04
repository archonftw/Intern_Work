import logging
import re
from threading import Lock
from urllib.parse import parse_qs, urlparse
from lxml import etree
from ncclient import manager
from ncclient.operations import RPCError

LOGGER = logging.getLogger("VES-COLLECTOR")

VES_PNF_NS = "urn:ves:pnf-registration"
NETCONF_NS = "urn:ietf:params:xml:ns:netconf:base:1.0"


class NetconfManager:

    def __init__(self):
        self.sessions = {}
        self.lock = Lock()

    def connect(self, device_id, host, port, username, key_filename):
        with self.lock:
            if device_id in self.sessions:
                return {"status": "already_connected", "device_id": device_id}

            session = manager.connect(
                host=host,
                port=port,
                username=username,
                password=None,
                hostkey_verify=False,
                look_for_keys=True,
                allow_agent=True,
                key_filename=key_filename,
                timeout=10,
                device_params={"name": "default"},
            )

            self.sessions[device_id] = session
            LOGGER.info("NETCONF connected: %s", device_id)
            return {"status": "connected", "session_id": session.session_id}

    def capabilities(self, device_id):
        session = self.sessions.get(device_id)
        if not session:
            raise RuntimeError(f"No active NETCONF session for device_id: {device_id}")
        return list(session.server_capabilities)

    def modules(self, device_id=None):
        """
        Parses YANG modules from session capabilities, scans the live datastore XML,
        and ensures essential server modules are always populated.
        """
        modules_list = []
        seen_names = set()
        
        with self.lock:
            target_sessions = (
                {device_id: self.sessions[device_id]}
                if device_id and device_id in self.sessions
                else dict(self.sessions)
            )

        # 1. Standard essential Netopeer2 server modules to guarantee in the UI
        ESSENTIAL_MODULES = [
            {"name": "ietf-netconf-server", "revision": "2019-11-20", "capability": "urn:ietf:params:xml:ns:yang:ietf-netconf-server"},
            {"name": "ietf-keystore", "revision": "2019-11-20", "capability": "urn:ietf:params:xml:ns:yang:ietf-keystore"},
            {"name": "ietf-truststore", "revision": "2019-11-20", "capability": "urn:ietf:params:xml:ns:yang:ietf-truststore"},
            {"name": "ietf-netconf-acm", "revision": "2018-02-14", "capability": "urn:ietf:params:xml:ns:yang:ietf-netconf-acm"},
            {"name": "ves-pnf-registration", "revision": "2024-01-01", "capability": "urn:ves:pnf-registration"},
        ]

        # 2. Parse standard advertised capability strings from NETCONF Hello
        for dev_id, session in target_sessions.items():
            for capability in session.server_capabilities:
                if "module=" in capability:
                    parsed = urlparse(capability)
                    params = parse_qs(parsed.query)

                    mod_name = params.get("module", [""])[0]
                    revision = params.get("revision", ["N/A"])[0]

                    if mod_name and mod_name not in seen_names:
                        seen_names.add(mod_name)
                        modules_list.append({
                            "device_id": dev_id,
                            "name": mod_name,
                            "revision": revision,
                            "capability": capability
                        })

        # 3. Inject essential server modules if they were not explicitly in Hello capabilities
        if target_sessions:
            dev_id = next(iter(target_sessions.keys()))
            for mod in ESSENTIAL_MODULES:
                if mod["name"] not in seen_names:
                    seen_names.add(mod["name"])
                    modules_list.append({
                        "device_id": dev_id,
                        "name": mod["name"],
                        "revision": mod["revision"],
                        "capability": mod["capability"]
                    })

        return modules_list
    
    def get_config(self, device_id, source="running", module=None):
        session = self.sessions.get(device_id)
        if not session:
            raise RuntimeError(f"No active NETCONF session for device_id: {device_id}")

        try:
            reply = session.get_config(source=source)
            xml_raw = reply.xml if isinstance(reply.xml, str) else reply.xml.decode("utf-8")
            
            # Parse XML robustly with recovery enabled
            parser = etree.XMLParser(recover=True, encoding="utf-8")
            root = etree.fromstring(xml_raw.encode("utf-8"), parser=parser)
            
            if root is None:
                return f'<data xmlns="{NETCONF_NS}"/>'

            # Locate <data> element (handles namespaces or lack thereof)
            data = root.find(f"{{{NETCONF_NS}}}data")
            if data is None:
                # Fallback search by localname
                for child in root:
                    if etree.QName(child.tag).localname == "data":
                        data = child
                        break

            if data is None or len(data) == 0:
                return f'<data xmlns="{NETCONF_NS}"/>'

            # If a specific module was requested, filter top-level children
            if module:
                clean_module = module.strip().lower()

                MODULE_TAG_MAP = {
                    "ves-pnf-registration": ["pnf"],
                    "ietf-netconf-server": ["netconf-server"],
                    "ietf-keystore": ["keystore"],
                    "ietf-truststore": ["truststore"],
                    "ietf-netconf-acm": ["nacm"],
                    "ietf-netconf-monitoring": ["netconf-state"]
                }

                target_tags = MODULE_TAG_MAP.get(clean_module, [clean_module])

                global_namespaces = dict(data.nsmap) if data.nsmap else {}
                for child in data:
                    if child.nsmap:
                        global_namespaces.update(child.nsmap)

                matching_nodes = []
                for child in data:
                    qname = etree.QName(child.tag)
                    local_tag = qname.localname.lower()
                    ns_uri = (qname.namespace or "").lower()

                    # Check local tag match
                    if any(tag == local_tag or tag in local_tag for tag in target_tags):
                        matching_nodes.append(child)
                        continue

                    # Check URI match
                    if clean_module in ns_uri:
                        matching_nodes.append(child)
                        continue

                    # Check global namespace map match
                    for prefix, uri in global_namespaces.items():
                        if uri and clean_module in str(uri).lower() and ns_uri == str(uri).lower():
                            matching_nodes.append(child)
                            break

                container = etree.Element(f"{{{NETCONF_NS}}}data")
                for node in matching_nodes:
                    container.append(etree.fromstring(etree.tostring(node)))

                return etree.tostring(container, encoding="unicode", pretty_print=True)

            # Return full datastore XML
            return etree.tostring(data, encoding="unicode", pretty_print=True)

        except Exception as e:
            LOGGER.error("get_config error on %s: %s", device_id, str(e))
            # Return empty data container on error instead of throwing a 500 Server Error
            return f'<data xmlns="{NETCONF_NS}"/>'
    
    def edit_config(self, device_id, config=None, target="candidate", default_operation="merge", **kwargs):
        # Support both 'config' and 'config_xml' kwargs
        config = config or kwargs.get("config_xml")
        
        session = self.sessions.get(device_id)
        if not session:
            raise RuntimeError(f"No active NETCONF session for device_id: {device_id}")

        config_str = str(config or "").strip()

        # Parse XML to clean up any outer <data> tag wrapper if present
        try:
            parsed_xml = etree.fromstring(config_str.encode("utf-8"))
            
            # If user sent <data xmlns="...">...</data>, extract its children
            local_tag = etree.QName(parsed_xml.tag).localname
            if local_tag == "data":
                inner_xml = "".join(etree.tostring(child, encoding="unicode") for child in parsed_xml)
            else:
                inner_xml = config_str
        except Exception:
            # Fallback if raw string or snippet
            inner_xml = config_str

        # Remove outer <config> if user already supplied one
        if inner_xml.startswith("<config") and inner_xml.endswith("</config>"):
            config_xml = inner_xml
        else:
            config_xml = f'<config xmlns="{NETCONF_NS}">{inner_xml}</config>'

        try:
            reply = session.edit_config(target=target, config=config_xml, default_operation=default_operation)
            return reply.xml
        except RPCError as exc:
            raise RuntimeError(f"Edit Config Failed: {exc.message}") from exc
    
    def validate(self, device_id, source="candidate"):
        """
        Validates the specified datastore against active Netopeer2 YANG schemas.
        """
        session = self.sessions.get(device_id)
        if not session:
            raise RuntimeError(f"No active NETCONF session for device_id: {device_id}")

        try:
            reply = session.validate(source=source)
            return reply.xml
        except RPCError as exc:
            raise RuntimeError(f"Validation Failed: {exc.message}") from exc

    def commit(self, device_id):
        session = self.sessions.get(device_id)
        if not session:
            raise RuntimeError(f"No active NETCONF session for device_id: {device_id}")
        
        try:
            return session.commit().xml
        except RPCError as exc:
            raise RuntimeError(f"Commit Failed: {exc.message}") from exc

    def discard_changes(self, device_id):
        """
        Reverts uncommitted edits in candidate datastore.
        """
        session = self.sessions.get(device_id)
        if not session:
            raise RuntimeError(f"No active NETCONF session for device_id: {device_id}")

        try:
            return session.discard_changes().xml
        except RPCError as exc:
            raise RuntimeError(f"Discard Changes Failed: {exc.message}") from exc

    def disconnect(self, device_id):
        with self.lock:
            session = self.sessions.pop(device_id, None)

        if session:
            try:
                session.close_session()
            except Exception:
                pass

        return {"status": "closed", "device_id": device_id}


def _esc(value):
    """Escape a value for safe inclusion inside XML element text."""
    return (
        str(value if value is not None else "")
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&apos;")
    )


def build_pnf_edit_config_xml(pnf: dict) -> str:
    """
    Build NETCONF edit-config payload for PNF Registration.
    """
    serial = _esc(pnf.get("serialNumber") or "UNKNOWN")

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


def forward_pnf_netconf(
    pnf: dict,
    host: str,
    port: int,
    username: str,
    key_filename: str,
    timeout: int = 10,
) -> str:
    """
    Sends a single PNF record to netopeer2 server via NETCONF edit-config.
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
                host,
                port,
                key_filename,
                getattr(reply, "ok", None),
            )

            return "ok"

    except RPCError as exc:
        raise RuntimeError(f"NETCONF RPC error: {exc}") from exc
    except Exception as exc:
        raise RuntimeError(f"NETCONF connection/edit-config failed: {exc}") from exc