from typing import Dict, List, Any

EVENT_STORE: List[Dict[str, Any]] = []

DEVICE_STORE: Dict[str, Dict[str, Any]] = {}

FILE_STORE: List[Dict[str, Any]] = []

# ==============================
# PNF Registration Storage
# ==============================

PNF_STORE = []

PNF_FORWARD_CONFIG = {
    "host": "127.0.0.1",
    "port": 9001,
    "path": "/pnfRegistration"
}