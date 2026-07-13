import os
from typing import Dict, List, Any
from dotenv import load_dotenv

load_dotenv()

EVENT_STORE: List[Dict[str, Any]] = []

DEVICE_STORE: Dict[str, Dict[str, Any]] = {}

FILE_STORE: List[Dict[str, Any]] = []

# ==============================
# PNF Registration Storage
# ==============================

PNF_STORE: List[Dict[str, Any]] = []

PNF_FORWARD_CONFIG = {
    "host": os.getenv("PNF_FORWARD_HOST", "127.0.0.1"),
    "port": int(os.getenv("PNF_FORWARD_PORT", "9001")),
    "path": os.getenv("PNF_FORWARD_PATH", "/pnfRegistration"),
}