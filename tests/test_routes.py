"""Tests for API routes: mandates CRUD and SIP processing."""

import json
import uuid

import pytest

from app import create_app, db
from app.models import MandateStatus, SIPMandate, Transaction, TransactionStatus, User


# ── Fixtures ────────────────────────────────────────────────────────

@pytest.fixture()
def app():
    app = create_app(config_name="config.TestingConfig")
    with app.app_context():
        db.create_all()
        yield app
        db.session.rollback()
        db.drop_all()


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def seed_user(app):
    """Create and return a user with the default 100 000 balance."""
    with app.app_context():
        user = User(name="TestUser")
        db.session.add(user)
        db.session.commit()
        # Refresh to bind to session
        user_id = user.id
    return user_id


@pytest.fixture()
def seed_mandate(app, seed_user):
    """Create and return an ACTIVE mandate for the seeded user."""
    with app.app_context():
        mandate = SIPMandate(
            user_id=seed_user,
            fund_name="Nifty Bank Index",
            amount=5000,
        )
        db.session.add(mandate)
        db.session.commit()
        mandate_id = mandate.id
    return mandate_id


# =====================================================================
# POST /api/mandates
# =====================================================================

class TestCreateMandate:
    """Tests for POST /api/mandates."""

    def test_create_mandate_success(self, client, seed_user):
        resp = client.post(
            "/api/mandates",
            data=json.dumps({
                "user_id": seed_user,
                "fund_name": "Nifty FMCG",
                "amount": 3000,
            }),
            content_type="application/json",
        )
        assert resp.status_code == 201
        body = resp.get_json()
        assert body["fund_name"] == "Nifty FMCG"
        assert body["amount"] == 3000
        assert body["status"] == "ACTIVE"

    def test_create_mandate_user_not_found(self, client):
        resp = client.post(
            "/api/mandates",
            data=json.dumps({
                "user_id": str(uuid.uuid4()),
                "fund_name": "Nifty Bank Index",
                "amount": 1000,
            }),
            content_type="application/json",
        )
        assert resp.status_code == 400
        assert "not found" in resp.get_json()["error"]

    def test_create_mandate_invalid_payload(self, client):
        """Missing required fields triggers 400 with validation details."""
        resp = client.post(
            "/api/mandates",
            data=json.dumps({}),
            content_type="application/json",
        )
        assert resp.status_code == 400
        body = resp.get_json()
        assert body["error"] == "Invalid payload"
        assert "details" in body


# =====================================================================
# GET /api/mandates/<user_id>
# =====================================================================

class TestListMandates:
    """Tests for GET /api/mandates/<user_id>."""

    def test_list_mandates_success(self, client, seed_mandate, seed_user):
        resp = client.get(f"/api/mandates/{seed_user}")
        assert resp.status_code == 200
        body = resp.get_json()
        assert len(body) == 1
        assert body[0]["fund_name"] == "Nifty Bank Index"

    def test_list_mandates_empty(self, client, seed_user):
        resp = client.get(f"/api/mandates/{seed_user}")
        assert resp.status_code == 200
        assert resp.get_json() == []

    def test_list_mandates_user_not_found(self, client):
        resp = client.get(f"/api/mandates/{uuid.uuid4()}")
        assert resp.status_code == 404
        assert "not found" in resp.get_json()["error"]


# =====================================================================
# POST /api/process-sip  –  Idempotency & ACID
# =====================================================================

class TestProcessSIP:
    """Tests for POST /api/process-sip."""

    # ── Happy path ───────────────────────────────────────────────────

    def test_process_sip_success(self, app, client, seed_mandate, seed_user):
        """Successful deduction: 201, COMPLETED status, balance reduced."""
        resp = client.post(
            "/api/process-sip",
            data=json.dumps({"mandate_id": seed_mandate}),
            content_type="application/json",
            headers={"Idempotency-Key": "key-001"},
        )
        assert resp.status_code == 201
        body = resp.get_json()
        assert body["status"] == "COMPLETED"
        assert body["amount"] == 5000

        # Verify wallet was deducted.
        with app.app_context():
            user = db.session.get(User, seed_user)
            assert user.wallet_balance == 95_000

    # ── Idempotency ──────────────────────────────────────────────────

    def test_idempotency_returns_existing_transaction(self, app, client, seed_mandate, seed_user):
        """Second call with same key returns 200 with the *same* transaction."""
        headers = {"Idempotency-Key": "key-idem"}
        payload = json.dumps({"mandate_id": seed_mandate})

        resp1 = client.post(
            "/api/process-sip",
            data=payload,
            content_type="application/json",
            headers=headers,
        )
        assert resp1.status_code == 201

        resp2 = client.post(
            "/api/process-sip",
            data=payload,
            content_type="application/json",
            headers=headers,
        )
        assert resp2.status_code == 200
        assert resp2.get_json()["id"] == resp1.get_json()["id"]

        # Balance should only be deducted once.
        with app.app_context():
            user = db.session.get(User, seed_user)
            assert user.wallet_balance == 95_000

    # ── Missing idempotency key ──────────────────────────────────────

    def test_missing_idempotency_key_returns_400(self, client, seed_mandate):
        resp = client.post(
            "/api/process-sip",
            data=json.dumps({"mandate_id": seed_mandate}),
            content_type="application/json",
        )
        assert resp.status_code == 400
        assert "Idempotency-Key" in resp.get_json()["error"]

    # ── Insufficient funds ───────────────────────────────────────────

    def test_insufficient_balance_returns_400(self, app, client, seed_user):
        """When wallet < mandate amount, txn is FAILED with error message."""
        # Create a mandate with amount > wallet balance.
        with app.app_context():
            mandate = SIPMandate(
                user_id=seed_user,
                fund_name="Expensive Fund",
                amount=999_999,
            )
            db.session.add(mandate)
            db.session.commit()
            big_mandate_id = mandate.id

        resp = client.post(
            "/api/process-sip",
            data=json.dumps({"mandate_id": big_mandate_id}),
            content_type="application/json",
            headers={"Idempotency-Key": "key-broke"},
        )
        assert resp.status_code == 400
        body = resp.get_json()
        assert "Insufficient" in body["error"]
        assert body["transaction"]["status"] == "FAILED"

    # ── Mandate not found ────────────────────────────────────────────

    def test_mandate_not_found_returns_400(self, client):
        resp = client.post(
            "/api/process-sip",
            data=json.dumps({"mandate_id": str(uuid.uuid4())}),
            content_type="application/json",
            headers={"Idempotency-Key": "key-ghost"},
        )
        assert resp.status_code == 400
        assert "not found" in resp.get_json()["error"]

    # ── Paused / Cancelled mandate ───────────────────────────────────

    def test_paused_mandate_returns_400(self, app, client, seed_mandate):
        """A non-ACTIVE mandate cannot be processed."""
        with app.app_context():
            mandate = db.session.get(SIPMandate, seed_mandate)
            mandate.status = MandateStatus.PAUSED
            db.session.commit()

        resp = client.post(
            "/api/process-sip",
            data=json.dumps({"mandate_id": seed_mandate}),
            content_type="application/json",
            headers={"Idempotency-Key": "key-paused"},
        )
        assert resp.status_code == 400
        assert "PAUSED" in resp.get_json()["error"]

    # ── Invalid payload ──────────────────────────────────────────────

    def test_invalid_payload_returns_400(self, client):
        resp = client.post(
            "/api/process-sip",
            data=json.dumps({}),
            content_type="application/json",
            headers={"Idempotency-Key": "key-bad"},
        )
        assert resp.status_code == 400
        assert resp.get_json()["error"] == "Invalid payload"
