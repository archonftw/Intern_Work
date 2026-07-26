from ncclient import manager

with manager.connect(
    host="127.0.0.1",
    port=830,
    username="archon",
    hostkey_verify=False,
    device_params={"name": "default"},
) as m:
    print(m.server_capabilities)