import logging
from jsonschema import validate, ValidationError
from services.schema_service import load_schema
from config import KNOWN_UNVALIDATED_DOMAINS

logger = logging.getLogger("VES-COLLECTOR")

# domain -> (field_name_in_event, schema_filename)
DOMAIN_SCHEMAS = {
    "fault": ("faultFields", "fault"),
    "heartbeat": ("heartbeatFields", "heartbeat"),
    "measurement": ("measurementFields", "measurement"),
    "notification": ("notificationFields", "notification"),
    "stateChange": ("stateChangeFields", "stateChange"),
    "thresholdCrossingAlert": ("thresholdCrossingAlertFields", "thresholdCrossingAlert"),
    "pnfRegistration": ("pnfRegistrationFields", "pnfRegistration"),
}

# stndDefined notificationType -> schema filename
STND_SCHEMA_MAP = {
    "notifyNewAlarm": "stndDefined-notifyNewAlarm",
    "notifyClearedAlarm": "stndDefined-notifyClearedAlarm",
    "notifyFileReady": "stndDefined-notifyFileReady",
    "notifyPNFRegistration": "stndDefined-notifyPNFRegistration",
    "heartbeat": "stndDefined-heartbeat",
}


def validate_domain(event):
    header = event["commonEventHeader"]
    domain = header["domain"]

    if domain in KNOWN_UNVALIDATED_DOMAINS:
        logger.info("Domain '%s' has no field schema - skipping field validation", domain)
        return

    if domain == "stndDefined":
        _validate_stnd_defined(event)
        return

    if domain not in DOMAIN_SCHEMAS:
        raise ValidationError(f"Unsupported VES domain '{domain}'")

    field_name, schema_name = DOMAIN_SCHEMAS[domain]

    if field_name not in event:
        raise ValidationError(f"Missing '{field_name}' for domain '{domain}'")

    schema = load_schema(schema_name)
    validate({"event": event}, schema)   # Wrapped envelope layout


def _resolve_stnd_type(event: dict) -> str | None:
    header = event.get("commonEventHeader", {})
    # Strip special string formatting structure parameters cleanly
    event_name = header.get("eventName", "").lower().replace("-", "").replace("_", "")
    stnd_fields = event.get("stndDefinedFields", {}) or {}
    data = stnd_fields.get("data", {})

    if "heartbeat" in event_name:
        return "heartbeat"
    if "cleared" in event_name:
        return "notifyClearedAlarm"
    if isinstance(data.get("fileInfoList"), list) or "fileready" in event_name:
        return "notifyFileReady"
    if "pnfregistration" in event_name:
        return "notifyPNFRegistration"
    if "thresholdcrossingalert" in event_name:
        return "notifyNewAlarm"
    return None


def _validate_stnd_defined(event):
    field_name = "stndDefinedFields"
    if field_name not in event:
        raise ValidationError(f"Missing '{field_name}' for domain 'stndDefined'")

    notif_type = _resolve_stnd_type(event)

    if not notif_type:
        raise ValidationError(
            f"Could not resolve stndDefined notification type for eventName "
            f"'{event.get('commonEventHeader', {}).get('eventName')}'"
        )

    schema_name = STND_SCHEMA_MAP.get(notif_type)
    if not schema_name:
        raise ValidationError(f"No schema mapped for resolved type '{notif_type}'")

    schema = load_schema(schema_name)
    # Patched to wrap the absolute full JSON structure exactly as schema expects
    validate({"event": event}, schema)