# Per-list caps to keep memory bounded on a long-running collector
MAX_EVENTS_PER_DEVICE = 100
MAX_MEASUREMENTS_PER_DEVICE = 20
MAX_FAULTS_PER_DEVICE = 50
MAX_NOTIFICATIONS_PER_DEVICE = 50
MAX_STATE_CHANGES_PER_DEVICE = 50
MAX_THRESHOLDS_PER_DEVICE = 50
MAX_GLOBAL_EVENT_STORE = 1000

KNOWN_UNVALIDATED_DOMAINS = {"syslog", "voiceQuality", "other"}

MAX_FILE_STORE = 5000
ALLOW_REMOTE_FETCH = False   # flip True to actually fetch files, not just show metadata
ALLOW_PRIVATE_IPS = False    # flip True in dev if fetching from localhost/testing rig
MAX_FETCH_BYTES = 10 * 1024 * 1024
FETCH_TIMEOUT_SEC = 15