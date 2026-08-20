import sys, os
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, ROOT)

from app import app
from storage import memory as storage_memory

# Populate sample events
storage_memory.EVENT_STORE.clear()
storage_memory.EVENT_STORE.extend([
    {
        'collectorId': '1',
        'eventId': 'evt-1',
        'sourceName': 'dev-a',
        'domain': 'fault',
        'eventName': 'Link Down',
        'priority': 'CRITICAL',
        'receivedAt': '2026-08-18T12:00:00Z',
        'raw': {'faultFields': {'eventSeverity': 'CRITICAL'}}
    },
    {
        'collectorId': '2',
        'eventId': 'evt-2',
        'sourceName': 'dev-b',
        'domain': 'heartbeat',
        'eventName': 'HB',
        'priority': 'NORMAL',
        'receivedAt': '2026-08-18T12:01:00Z',
        'raw': {}
    },
    {
        'collectorId': '3',
        'eventId': 'evt-3',
        'sourceName': 'dev-a',
        'domain': 'pnfRegistration',
        'eventName': 'PNF Reg',
        'priority': 'NORMAL',
        'receivedAt': '2026-08-18T12:02:00Z',
        'raw': {'pnfRegistrationFields': {'pnfId': 'pnf-1','vendorName':'Acme'}}
    }
])

# Populate PNF store
storage_memory.PNF_STORE.clear()
storage_memory.PNF_STORE.append({
    'receivedTime': '2026-08-18T12:02:00Z',
    'unitType': 'pnf-1',
    'vendorName': 'Acme',
    'modelNumber': 'X100',
    'oamV4IpAddress': '10.0.0.1',
    'protocol': 'NETCONF',
    'username': 'serial-123',
    'forwarded': False
})

# Populate FILE_STORE
storage_memory.FILE_STORE.clear()
storage_memory.FILE_STORE.append({
    'fileId': 'file-1',
    'receivedAt': '2026-08-18T12:05:00Z',
    'sourceName': 'dev-a',
    'fileFormat': 'csv',
    'fileDataType': 'metrics',
    'fileSize': 1234,
    'fileReadyTime': '2026-08-18T12:06:00Z',
    'fileExpirationTime': '2026-09-18T12:06:00Z',
    'fileLocation': 'http://example.com/file-1'
})

with app.test_client() as client:
    r = client.get('/api/stats')
    print('/api/stats', r.status_code, r.get_data(as_text=True))

    r = client.get('/api/events')
    print('/api/events', r.status_code, r.get_data(as_text=True))

    r = client.get('/api/devices')
    print('/api/devices', r.status_code, r.get_data(as_text=True))

    r = client.get('/api/pnf')
    print('/api/pnf', r.status_code, r.get_data(as_text=True))

    r = client.get('/eventListener/v7')
    print('/eventListener/v7', r.status_code, r.get_data(as_text=True))
