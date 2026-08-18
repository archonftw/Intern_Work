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

    def connect(self, device_id, host, port, username, key_filename, key_passphrase=None):
        with self.lock:
            if device_id in self.sessions:
                return {"status": "already_connected", "device_id": device_id}

            try:
                # Pure SSH Key Authentication
                session = manager.connect(
                    host=host,
                    port=int(port),
                    username=username,
                    password=key_passphrase,  # None for passwordless SSH keys
                    hostkey_verify=False,
                    look_for_keys=False,
                    allow_agent=False,
                    key_filename=key_filename,
                    timeout=10,
                    device_params={"name": "default"},
                )

                self.sessions[device_id] = session
                LOGGER.info("NETCONF SSH key connected: %s (%s:%s)", device_id, host, port)
                return {"status": "connected", "session_id": str(session.session_id)}
            except Exception as exc:
                LOGGER.error("NETCONF SSH connection failed for %s: %s", device_id, str(exc))
                raise RuntimeError(f"Connection to Netopeer2 failed: {str(exc)}") from exc
   
    def capabilities(self, device_id):
        session = self.sessions.get(device_id)
        if not session:
            raise RuntimeError(f"No active NETCONF session for device_id: {device_id}")
        return list(session.server_capabilities)

    def modules(self, device_id=None):
        """
        Parses YANG modules from session capabilities and ensures essential
        server modules (including ves-pnf-registration) are populated.
        """
        modules_list = []
        seen_names = set()
        
        with self.lock:
            target_sessions = (
                {device_id: self.sessions[device_id]}
                if device_id and device_id in self.sessions
                else dict(self.sessions)
            )

        # Essential Netopeer2/Sysrepo modules to guarantee in UI
        ESSENTIAL_MODULES = [
            {"name": "ves-pnf-registration", "revision": "2024-01-01", "capability": "urn:ves:pnf-registration"},
            {"name": "ietf-netconf-server", "revision": "2019-11-20", "capability": "urn:ietf:params:xml:ns:yang:ietf-netconf-server"},
            {"name": "ietf-keystore", "revision": "2019-11-20", "capability": "urn:ietf:params:xml:ns:yang:ietf-keystore"},
            {"name": "ietf-truststore", "revision": "2019-11-20", "capability": "urn:ietf:params:xml:ns:yang:ietf-truststore"},
            {"name": "ietf-netconf-acm", "revision": "2018-02-14", "capability": "urn:ietf:params:xml:ns:yang:ietf-netconf-acm"},
        ]

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
            
            parser = etree.XMLParser(recover=True, encoding="utf-8")
            root = etree.fromstring(xml_raw.encode("utf-8"), parser=parser)
            
            if root is None:
                return f'<data xmlns="{NETCONF_NS}"/>'

            # Locate <data> element
            data = root.find(f"{{{NETCONF_NS}}}data")
            if data is None:
                for child in root:
                    if etree.QName(child.tag).localname == "data":
                        data = child
                        break

            if data is None or len(data) == 0:
                return f'<data xmlns="{NETCONF_NS}"/>'

            # Filter top-level tags by requested module
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

                    if any(tag == local_tag or tag in local_tag for tag in target_tags):
                        matching_nodes.append(child)
                        continue

                    if clean_module in ns_uri:
                        matching_nodes.append(child)
                        continue

                    for prefix, uri in global_namespaces.items():
                        if uri and clean_module in str(uri).lower() and ns_uri == str(uri).lower():
                            matching_nodes.append(child)
                            break

                # Device Isolation Filter: Safely check for matching serial numbers if present
                if clean_module == "ves-pnf-registration" and device_id and device_id != "local-netopeer":
                    filtered_pnf = []
                    for child in matching_nodes:
                        if etree.QName(child.tag).localname.lower() == "pnf":
                            sn_node = child.find(".//*[local-name()='serial-number']")
                            if sn_node is not None and sn_node.text and sn_node.text.strip() == device_id:
                                filtered_pnf.append(child)
                    if filtered_pnf:
                        matching_nodes = filtered_pnf

                container = etree.Element(f"{{{NETCONF_NS}}}data")
                for node in matching_nodes:
                    container.append(etree.fromstring(etree.tostring(node)))

                return etree.tostring(container, encoding="unicode", pretty_print=True)

            return etree.tostring(data, encoding="unicode", pretty_print=True)

        except Exception as e:
            LOGGER.error("get_config error on %s: %s", device_id, str(e))
            return f'<data xmlns="{NETCONF_NS}"/>'
    
    def edit_config(self, device_id, config=None, target="candidate", default_operation="merge", **kwargs):
        config = config or kwargs.get("config_xml")
        
        session = self.sessions.get(device_id)
        if not session:
            raise RuntimeError(f"No active NETCONF session for device_id: {device_id}")

        config_str = str(config or "").strip()

        # Clean outer <data> or <config> wrappers to avoid duplicate tags
        try:
            parsed_xml = etree.fromstring(config_str.encode("utf-8"))
            local_tag = etree.QName(parsed_xml.tag).localname
            
            if local_tag in ("data", "config"):
                inner_xml = "".join(etree.tostring(child, encoding="unicode") for child in parsed_xml)
            else:
                inner_xml = config_str
        except Exception:
            inner_xml = config_str

        if inner_xml.startswith("<config") and inner_xml.endswith("</config>"):
            config_xml = inner_xml
        else:
            config_xml = f'<config xmlns="{NETCONF_NS}">{inner_xml}</config>'

        try:
            reply = session.edit_config(target=target, config=config_xml, default_operation=default_operation)
            return reply.xml
        except RPCError as exc:
            if target == "candidate":
                try:
                    reply = session.edit_config(target="running", config=config_xml, default_operation=default_operation)
                    return reply.xml
                except RPCError:
                    pass
            raise RuntimeError(f"Edit Config Failed: {exc.message}") from exc
    
    def validate(self, device_id, source="candidate"):
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
    return (
        str(value if value is not None else "")
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&apos;")
    )


def build_pnf_edit_config_xml(pnf: dict) -> str:
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
    config_xml = build_pnf_edit_config_xml(pnf)

    if not key_filename:
        raise RuntimeError("No SSH key_filename configured for NETCONF forwarding")

    try:
        with manager.connect(
            host=host,
            port=int(port),
            username=username,
            password=None,
            hostkey_verify=False,
            look_for_keys=False,
            allow_agent=False,
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


netconf_service = NetconfManager()