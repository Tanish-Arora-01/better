"""Marshmallow schemas for strict request payload validation.

Every incoming JSON payload is validated against one of these schemas
before it reaches the business logic, per the Interface Safety rules
in ai_guidance.md.
"""

import uuid as _uuid

from marshmallow import Schema, ValidationError, fields, validate, validates

# Re-export so routes can catch it from a single import.
__all__ = [
    "SIPMandateCreateSchema",
    "ProcessSIPSchema",
    "ValidationError",
]


def _validate_uuid(value: str) -> None:
    """Raise ``ValidationError`` if *value* is not a valid UUID-4 string."""
    try:
        _uuid.UUID(value, version=4)
    except (ValueError, AttributeError):
        raise ValidationError("Not a valid UUID.")


class SIPMandateCreateSchema(Schema):
    """Validates the payload for creating a new SIP mandate.

    Required fields:
        user_id  – valid UUID-4 string.
        fund_name – non-empty string, max 100 characters.
        amount   – positive integer (strictly > 0).
    """

    user_id = fields.String(
        required=True,
        validate=_validate_uuid,
        metadata={"description": "UUID of the owning user."},
    )
    fund_name = fields.String(
        required=True,
        validate=validate.Length(min=1, max=100),
        metadata={"description": "Name of the mutual fund, e.g. 'Nifty Bank Index'."},
    )
    amount = fields.Integer(
        required=True,
        strict=True,
        validate=validate.Range(min=1, error="Amount must be strictly greater than 0."),
        metadata={"description": "SIP instalment amount (paise). Must be > 0."},
    )


class ProcessSIPSchema(Schema):
    """Validates the payload for processing a SIP instalment.

    Required fields:
        mandate_id – valid UUID-4 string.
    """

    mandate_id = fields.String(
        required=True,
        validate=_validate_uuid,
        metadata={"description": "UUID of the SIP mandate to process."},
    )
