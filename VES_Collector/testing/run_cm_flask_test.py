import sys, os
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, ROOT)

from app import app
from services import netconf_service as ns

# Fake reply/session like before
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

# insert fake session
ns.netconf_service.sessions['flask-test-device'] = FakeSession()

with app.test_client() as client:
    # sessions
    r = client.get('/api/cm/sessions')
    print('GET /api/cm/sessions', r.status_code, r.get_data(as_text=True))

    # modules
    r = client.get('/api/cm/modules', query_string={'device_id':'flask-test-device'})
    print('GET /api/cm/modules', r.status_code, r.get_data(as_text=True))

    # get config
    r = client.get('/api/cm/config', query_string={'device_id':'flask-test-device','datastore':'running'})
    print('GET /api/cm/config', r.status_code, r.get_data(as_text=True))

    # validate
    r = client.post('/api/cm/validate', json={'device_id':'flask-test-device','datastore':'candidate'})
    print('POST /api/cm/validate', r.status_code, r.get_data(as_text=True))

    # commit
    r = client.post('/api/cm/commit', json={'device_id':'flask-test-device'})
    print('POST /api/cm/commit', r.status_code, r.get_data(as_text=True))

    # discard
    r = client.post('/api/cm/disconnect', json={'device_id':'flask-test-device'})
    print('POST /api/cm/disconnect', r.status_code, r.get_data(as_text=True))
