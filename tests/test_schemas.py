"""Tests for Marshmallow validation schemas and Flask error handler."""

import json
import uuid

import pytest
from marshmallow import ValidationError

from app import create_app
from app.schemas import ProcessSIPSchema, SIPMandateCreateSchema


# ── Fixtures ────────────────────────────────────────────────────────

@pytest.fixture()
def mandate_schema() -> SIPMandateCreateSchema:
    return SIPMandateCreateSchema()


@pytest.fixture()
def process_schema() -> ProcessSIPSchema:
    return ProcessSIPSchema()


@pytest.fixture()
def app():
    return create_app(config_name="config.TestingConfig")


@pytest.fixture()
def client(app):
    return app.test_client()


# ── SIPMandateCreateSchema: happy path ──────────────────────────────

def test_mandate_schema_valid(mandate_schema):
    """A fully valid payload deserialises without errors."""
    data = mandate_schema.load({
        "user_id": str(uuid.uuid4()),
        "fund_name": "Nifty Bank Index",
        "amount": 5000,
    })
    assert data["fund_name"] == "Nifty Bank Index"
    assert data["amount"] == 5000


# ── SIPMandateCreateSchema: edge / failure cases ────────────────────

def test_mandate_schema_rejects_missing_fields(mandate_schema):
    """All three fields are required; omitting any raises ValidationError."""
    with pytest.raises(ValidationError) as exc_info:
        mandate_schema.load({})
    errors = exc_info.value.messages
    assert "user_id" in errors
    assert "fund_name" in errors
    assert "amount" in errors


def test_mandate_schema_rejects_invalid_uuid(mandate_schema):
    """A malformed user_id is rejected."""
    with pytest.raises(ValidationError) as exc_info:
        mandate_schema.load({
            "user_id": "not-a-uuid",
            "fund_name": "Nifty FMCG",
            "amount": 1000,
        })
    assert "user_id" in exc_info.value.messages


def test_mandate_schema_rejects_zero_amount(mandate_schema):
    """Amount must be strictly > 0; zero is rejected."""
    with pytest.raises(ValidationError) as exc_info:
        mandate_schema.load({
            "user_id": str(uuid.uuid4()),
            "fund_name": "Nifty Bank Index",
            "amount": 0,
        })
    assert "amount" in exc_info.value.messages


def test_mandate_schema_rejects_negative_amount(mandate_schema):
    """Negative amounts are rejected."""
    with pytest.raises(ValidationError) as exc_info:
        mandate_schema.load({
            "user_id": str(uuid.uuid4()),
            "fund_name": "Nifty Bank Index",
            "amount": -500,
        })
    assert "amount" in exc_info.value.messages


def test_mandate_schema_rejects_long_fund_name(mandate_schema):
    """fund_name exceeding 100 chars is rejected."""
    with pytest.raises(ValidationError) as exc_info:
        mandate_schema.load({
            "user_id": str(uuid.uuid4()),
            "fund_name": "X" * 101,
            "amount": 1000,
        })
    assert "fund_name" in exc_info.value.messages


def test_mandate_schema_rejects_empty_fund_name(mandate_schema):
    """fund_name must not be empty."""
    with pytest.raises(ValidationError) as exc_info:
        mandate_schema.load({
            "user_id": str(uuid.uuid4()),
            "fund_name": "",
            "amount": 1000,
        })
    assert "fund_name" in exc_info.value.messages


# ── ProcessSIPSchema: happy path ────────────────────────────────────

def test_process_schema_valid(process_schema):
    """A valid UUID mandate_id passes validation."""
    data = process_schema.load({"mandate_id": str(uuid.uuid4())})
    assert "mandate_id" in data


# ── ProcessSIPSchema: edge / failure cases ──────────────────────────

def test_process_schema_rejects_missing_mandate_id(process_schema):
    """mandate_id is required."""
    with pytest.raises(ValidationError) as exc_info:
        process_schema.load({})
    assert "mandate_id" in exc_info.value.messages


def test_process_schema_rejects_invalid_uuid(process_schema):
    """A malformed mandate_id is rejected."""
    with pytest.raises(ValidationError) as exc_info:
        process_schema.load({"mandate_id": "garbage"})
    assert "mandate_id" in exc_info.value.messages


# ── Flask error handler integration ─────────────────────────────────

def test_error_handler_returns_400_json(app, client):
    """When a route raises ValidationError, the global handler returns
    a standardised 400 JSON response."""

    @app.route("/test-validation", methods=["POST"])
    def _test_route():
        schema = SIPMandateCreateSchema()
        schema.load({})  # will raise ValidationError
        return "", 204  # pragma: no cover

    resp = client.post(
        "/test-validation",
        data=json.dumps({}),
        content_type="application/json",
    )
    assert resp.status_code == 400
    body = resp.get_json()
    assert body["error"] == "Invalid payload"
    assert "details" in body
    assert "user_id" in body["details"]
    assert "fund_name" in body["details"]
    assert "amount" in body["details"]
