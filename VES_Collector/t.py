from services.netconf_service import forward_pnf_netconf

test_pnf = {
    "serialNumber": "TEST-001",
    "vendorName": "Ericsson",
    "unitType": "gNB",
    "unitFamily": "5G-RAN",
    "modelNumber": "Radio 4408",
    "softwareVersion": "23.1.0",
    "oamV4IpAddress": "192.168.1.10",
    "protocol": "SSH",
    "username": "root",
    "receivedTime": "2026-07-21T00:00:00Z",
}

forward_pnf_netconf(
    test_pnf,
    host="localhost",
    port=830,
    username="archon",
    key_filename="/home/archon/.ssh/id_ed25519",
)

print("Sent OK")