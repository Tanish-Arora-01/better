"""Engine integration tests – proving idempotency, ACID, and validation.

Uses an in-memory SQLite database (``config.TestingConfig``).
Each test is self-contained with fresh DB state via fixtures.

Test matrix:
    1. Mandate creation (happy path)
    2. Successful SIP deduction (happy path)
    3. Idempotency: duplicate Idempotency-Key → single deduction
    4. Interface Safety: insufficient balance → 400 + FAILED transaction
    5. Validation: negative SIP amount → 400 validation error
"""

import json
import uuid

import pytest

from app import create_app, db
from app.models import SIPMandate, Transaction, TransactionStatus, User


# ── Fixtures ────────────────────────────────────────────────────────

@pytest.fixture()
def app():
    """In-memory SQLite app for isolated tests."""
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
def seed_user(app) -> str:
    """Insert a User with the default 100 000 balance and return the ID."""
    with app.app_context():
        user = User(name="Integration Tester")
        db.session.add(user)
        db.session.commit()
        return user.id


@pytest.fixture()
def seed_mandate(app, seed_user) -> str:
    """Insert an ACTIVE mandate (amount=5000) and return the ID."""
    with app.app_context():
        mandate = SIPMandate(
            user_id=seed_user,
            fund_name="Nifty Bank Index",
            amount=5000,
        )
        db.session.add(mandate)
        db.session.commit()
        return mandate.id


# =====================================================================
# 1. Test: Successfully creating a SIP Mandate
# =====================================================================

class TestMandateCreation:
    """Prove that the mandate creation route works end-to-end."""

    def test_create_mandate_returns_201_with_correct_fields(
        self, client, seed_user
    ):
        payload = {
            "user_id": seed_user,
            "fund_name": "Nifty FMCG",
            "amount": 7500,
        }
        resp = client.post(
            "/api/mandates",
            data=json.dumps(payload),
            content_type="application/json",
        )

        assert resp.status_code == 201, resp.get_json()
        body = resp.get_json()
        assert body["user_id"] == seed_user
        assert body["fund_name"] == "Nifty FMCG"
        assert body["amount"] == 7500
        assert body["status"] == "ACTIVE"
        # UUID is present and well-formed
        uuid.UUID(body["id"])


# =====================================================================
# 2. Test: Successful SIP deduction
# =====================================================================

class TestSuccessfulDeduction:
    """Prove that a valid SIP call deducts from the wallet and
    creates a COMPLETED transaction."""

    def test_process_sip_deducts_balance_and_returns_completed(
        self, app, client, seed_mandate, seed_user
    ):
        resp = client.post(
            "/api/process-sip",
            data=json.dumps({"mandate_id": seed_mandate}),
            content_type="application/json",
            headers={"Idempotency-Key": "engine-deduct-001"},
        )

        assert resp.status_code == 201, resp.get_json()
        body = resp.get_json()
        assert body["status"] == "COMPLETED"
        assert body["amount"] == 5000
        assert body["idempotency_key"] == "engine-deduct-001"

        # Verify the wallet has been reduced from 100 000 → 95 000.
        with app.app_context():
            user = db.session.get(User, seed_user)
            assert user.wallet_balance == 95_000


# =====================================================================
# 3. Idempotency Test
# =====================================================================

class TestIdempotency:
    """Prove that submitting the same Idempotency-Key twice results in
    exactly ONE wallet deduction and the second response is a 200 with
    the original transaction details."""

    def test_duplicate_key_deducts_only_once(
        self, app, client, seed_mandate, seed_user
    ):
        headers = {"Idempotency-Key": "engine-idem-key"}
        payload = json.dumps({"mandate_id": seed_mandate})

        # ── First call: should create the transaction (201) ──────────
        resp1 = client.post(
            "/api/process-sip",
            data=payload,
            content_type="application/json",
            headers=headers,
        )
        assert resp1.status_code == 201
        txn1 = resp1.get_json()
        assert txn1["status"] == "COMPLETED"

        # ── Second call: same key → 200, same transaction returned ───
        resp2 = client.post(
            "/api/process-sip",
            data=payload,
            content_type="application/json",
            headers=headers,
        )
        assert resp2.status_code == 200, (
            "Second call must return 200 (not 201) for an existing key"
        )
        txn2 = resp2.get_json()

        # Same transaction ID proves no new row was created.
        assert txn2["id"] == txn1["id"]
        assert txn2["idempotency_key"] == "engine-idem-key"
        assert txn2["status"] == "COMPLETED"

        # ── Balance must be deducted only ONCE ───────────────────────
        with app.app_context():
            user = db.session.get(User, seed_user)
            assert user.wallet_balance == 95_000, (
                f"Expected 95000 (single deduction), got {user.wallet_balance}"
            )

            # Only one Transaction row for this key.
            txn_count = (
                db.session.query(Transaction)
                .filter_by(idempotency_key="engine-idem-key")
                .count()
            )
            assert txn_count == 1


# =====================================================================
# 4. Interface Safety Test – Insufficient Balance
# =====================================================================

class TestInsufficientBalance:
    """Prove that when the wallet is too low the engine returns 400
    and records a FAILED transaction (no silent failure)."""

    def test_low_balance_returns_400_and_failed_transaction(
        self, app, client, seed_user
    ):
        # Create a mandate whose amount exceeds the wallet.
        with app.app_context():
            big_mandate = SIPMandate(
                user_id=seed_user,
                fund_name="Ultra Expensive Fund",
                amount=200_000,  # wallet is only 100 000
            )
            db.session.add(big_mandate)
            db.session.commit()
            big_id = big_mandate.id

        resp = client.post(
            "/api/process-sip",
            data=json.dumps({"mandate_id": big_id}),
            content_type="application/json",
            headers={"Idempotency-Key": "engine-broke-key"},
        )

        assert resp.status_code == 400
        body = resp.get_json()
        assert "Insufficient" in body["error"]
        assert body["transaction"]["status"] == "FAILED"
        assert body["transaction"]["error_message"] == "Insufficient wallet balance."

        # Wallet balance must remain untouched.
        with app.app_context():
            user = db.session.get(User, seed_user)
            assert user.wallet_balance == 100_000

            # A FAILED transaction row was still persisted (audit trail).
            failed_txn = db.session.get(
                Transaction, body["transaction"]["id"]
            )
            assert failed_txn is not None
            assert failed_txn.status == TransactionStatus.FAILED


# =====================================================================
# 5. Validation Test – Negative Amount
# =====================================================================

class TestNegativeAmountValidation:
    """Prove that a negative SIP amount is rejected at the schema layer
    before touching the database."""

    def test_negative_amount_returns_400_validation_error(
        self, client, seed_user
    ):
        resp = client.post(
            "/api/mandates",
            data=json.dumps({
                "user_id": seed_user,
                "fund_name": "Nifty Bank Index",
                "amount": -500,
            }),
            content_type="application/json",
        )

        assert resp.status_code == 400
        body = resp.get_json()
        assert body["error"] == "Invalid payload"
        assert "amount" in body["details"]
