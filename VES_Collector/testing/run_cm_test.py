import sys
import os

# Ensure project root is on sys.path so imports like services.* work
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)

from services import netconf_service as ns
import json

# Create a fake session that mimics ncclient.manager session reply interface
class FakeReply:
    def __init__(self, xml):
        self.xml = xml

class FakeSession:
    server_capabilities = [
        "urn:ietf:params:xml:ns:yang:ietf-netconf-monitoring?module=ietf-netconf-monitoring&revision=2011-06-01"
    ]

    def get_config(self, source="running"):
        return FakeReply('<rpc-reply><data><example xmlns="urn:example">value</example></data></rpc-reply>')

    def edit_config(self, target, config, default_operation=None):
        return FakeReply('<rpc-reply><ok/></rpc-reply>')

    def validate(self, source=None):
        return FakeReply('<rpc-reply><ok/></rpc-reply>')

    def commit(self):
        return FakeReply('<rpc-reply><ok/></rpc-reply>')

    def discard_changes(self):
        return FakeReply('<rpc-reply><ok/></rpc-reply>')

    def close_session(self):
        pass

# Monkeypatch the connect method to avoid real ncclient connections
def fake_connect(device_id, host, port, username, key_filename, key_passphrase=None):
    ns.netconf_service.sessions[device_id] = FakeSession()
    return {"status": "connected", "device_id": device_id}

ns.netconf_service.connect = fake_connect

# Instead of exercising Flask endpoints, call the service methods directly
device_id = "test-device"

# Monkeypatch the connect method to avoid real ncclient connections
def fake_connect(device_id, host, port, username, key_filename, key_passphrase=None):
    ns.netconf_service.sessions[device_id] = FakeSession()
    return {"status": "connected", "device_id": device_id}

ns.netconf_service.connect = fake_connect

print('Calling netconf_service.connect(...)')
res = ns.netconf_service.connect(device_id=device_id, host='127.0.0.1', port=830, username='user', key_filename='/tmp/fakekey')
print('CONNECT ->', res)

print('\nSessions:', list(ns.netconf_service.sessions.keys()))

print('\nCalling get_config...')
cfg = ns.netconf_service.get_config(device_id=device_id, source='running')
print('GET_CONFIG ->')
print(cfg)

print('\nCalling commit...')
print(ns.netconf_service.commit(device_id=device_id))

print('\nCalling disconnect...')
print(ns.netconf_service.disconnect(device_id=device_id))
