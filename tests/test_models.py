"""Tests for SQLAlchemy models: User, SIPMandate, Transaction."""

import pytest
from sqlalchemy.exc import IntegrityError

from app import create_app, db
from app.models import (
    MandateStatus,
    SIPMandate,
    Transaction,
    TransactionStatus,
    User,
)


@pytest.fixture()
def app():
    """Create an application instance configured for testing."""
    app = create_app(config_name="config.TestingConfig")
    yield app


@pytest.fixture()
def session(app):
    """Provide a transactional database session scoped to each test."""
    with app.app_context():
        db.create_all()
        yield db.session
        db.session.rollback()
        db.drop_all()


# ------------------------------------------------------------------
# Happy-path tests
# ------------------------------------------------------------------

def test_create_user(session):
    """A user can be inserted and read back with correct defaults."""
    user = User(name="Alice")
    session.add(user)
    session.commit()

    fetched = session.get(User, user.id)
    assert fetched is not None
    assert fetched.name == "Alice"
    assert fetched.wallet_balance == 100_000


def test_create_mandate_linked_to_user(session):
    """A SIPMandate is correctly linked to its parent User."""
    user = User(name="Bob")
    session.add(user)
    session.flush()

    mandate = SIPMandate(
        user_id=user.id,
        fund_name="Nifty Bank Index",
        amount=5000,
    )
    session.add(mandate)
    session.commit()

    assert mandate.user.name == "Bob"
    assert mandate.status == MandateStatus.ACTIVE
    assert len(user.mandates) == 1


def test_create_transaction_linked_to_mandate(session):
    """A Transaction is correctly linked to its parent SIPMandate."""
    user = User(name="Charlie")
    session.add(user)
    session.flush()

    mandate = SIPMandate(
        user_id=user.id,
        fund_name="Nifty FMCG",
        amount=3000,
    )
    session.add(mandate)
    session.flush()

    txn = Transaction(
        mandate_id=mandate.id,
        amount=3000,
        idempotency_key="txn-001",
    )
    session.add(txn)
    session.commit()

    assert txn.mandate.fund_name == "Nifty FMCG"
    assert txn.status == TransactionStatus.PENDING
    assert len(mandate.transactions) == 1


# ------------------------------------------------------------------
# Constraint tests
# ------------------------------------------------------------------

def test_wallet_balance_cannot_go_negative(session):
    """The DB-level CHECK constraint rejects a negative wallet_balance."""
    user = User(name="Dave", wallet_balance=-1)
    session.add(user)
    with pytest.raises(IntegrityError):
        session.commit()


def test_idempotency_key_must_be_unique(session):
    """Duplicate idempotency_key values are rejected by the UNIQUE constraint."""
    user = User(name="Eve")
    session.add(user)
    session.flush()

    mandate = SIPMandate(
        user_id=user.id,
        fund_name="Nifty Bank Index",
        amount=2000,
    )
    session.add(mandate)
    session.flush()

    txn1 = Transaction(
        mandate_id=mandate.id, amount=2000, idempotency_key="dup-key"
    )
    session.add(txn1)
    session.commit()

    txn2 = Transaction(
        mandate_id=mandate.id, amount=2000, idempotency_key="dup-key"
    )
    session.add(txn2)
    with pytest.raises(IntegrityError):
        session.commit()


def test_tables_create_without_errors(app):
    """All tables can be created from scratch without any errors."""
    with app.app_context():
        db.drop_all()
        db.create_all()
        table_names = db.inspect(db.engine).get_table_names()
        assert "users" in table_names
        assert "sip_mandates" in table_names
        assert "transactions" in table_names
