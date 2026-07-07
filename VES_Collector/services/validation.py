from jsonschema import validate, ValidationError

from schemas.schema import (
    FAULT_SCHEMA,
    HEARTBEAT_SCHEMA,
    MEASUREMENT_SCHEMA,
    NOTIFICATION_SCHEMA,
    STATE_CHANGE_SCHEMA,
    THRESHOLD_CROSSING_ALERT_SCHEMA,
    PNF_REGISTRATION_SCHEMA,
    STND_DEFINED_SCHEMA
)

from config import KNOWN_UNVALIDATED_DOMAINS
import logging

logger = logging.getLogger("VES-COLLECTOR")
# Schemas to validate per VES domain
DOMAIN_SCHEMAS = {
    "fault": (
        "faultFields",
        FAULT_SCHEMA
    ),

    "heartbeat": (
        "heartbeatFields",
        HEARTBEAT_SCHEMA
    ),

    "measurement": (
        "measurementFields",
        MEASUREMENT_SCHEMA
    ),

    "notification": (
        "notificationFields",
        NOTIFICATION_SCHEMA
    ),

    "stateChange": (
        "stateChangeFields",
        STATE_CHANGE_SCHEMA
    ),

    "thresholdCrossingAlert": (
        "thresholdCrossingAlertFields",
        THRESHOLD_CROSSING_ALERT_SCHEMA
    ),

    "pnfRegistration": (
        "pnfRegistrationFields",
        PNF_REGISTRATION_SCHEMA
    ),

    "stndDefined": (
        "stndDefinedFields",
        STND_DEFINED_SCHEMA
    )
}


def validate_domain(event):

    header = event["commonEventHeader"]
    domain = header["domain"]

    if domain in KNOWN_UNVALIDATED_DOMAINS:
        logger.info("Domain '%s' has no field schema - skipping field validation", domain)
        return

    if domain not in DOMAIN_SCHEMAS:
        raise ValidationError(
            f"Unsupported VES domain '{domain}'"
        )

    field_name, schema = DOMAIN_SCHEMAS[domain]

    if field_name not in event:
        raise ValidationError(
            f"Missing '{field_name}' for domain '{domain}'"
        )

    validate(
        event[field_name],
        schema
    )