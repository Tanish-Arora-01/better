"""SQLAlchemy ORM models for the SIP Billing Engine."""

import enum
import uuid
from typing import List, Optional

from sqlalchemy import CheckConstraint, Enum, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app import db


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class MandateStatus(enum.Enum):
    """Allowed statuses for a SIP mandate."""

    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"
    CANCELLED = "CANCELLED"


class TransactionStatus(enum.Enum):
    """Allowed statuses for a transaction."""

    PENDING = "PENDING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class User(db.Model):  # type: ignore[name-defined]
    """A user with a wallet that funds SIP investments.

    Attributes:
        id: UUID primary key.
        name: Display name of the user.
        wallet_balance: Balance in *paise* (integer). Default 100 000.
            A database-level CHECK constraint prevents it from going negative.
        mandates: One-to-many relationship with SIPMandate.
    """

    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint("wallet_balance >= 0", name="ck_users_wallet_non_negative"),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    wallet_balance: Mapped[int] = mapped_column(Integer, nullable=False, default=100_000)

    # Relationships
    mandates: Mapped[List["SIPMandate"]] = relationship(
        "SIPMandate", back_populates="user", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<User {self.name} balance={self.wallet_balance}>"


class SIPMandate(db.Model):  # type: ignore[name-defined]
    """A recurring SIP investment instruction tied to a user.

    Attributes:
        id: UUID primary key.
        user_id: FK to the owning User.
        fund_name: Name of the mutual fund (e.g. 'Nifty Bank Index').
        amount: SIP instalment amount in paise (integer).
        status: Current mandate lifecycle status.
        user: Many-to-one relationship with User.
        transactions: One-to-many relationship with Transaction.
    """

    __tablename__ = "sip_mandates"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=False
    )
    fund_name: Mapped[str] = mapped_column(String(120), nullable=False)
    amount: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[MandateStatus] = mapped_column(
        Enum(MandateStatus), nullable=False, default=MandateStatus.ACTIVE
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="mandates")
    transactions: Mapped[List["Transaction"]] = relationship(
        "Transaction", back_populates="mandate", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<SIPMandate {self.fund_name} amount={self.amount} status={self.status.value}>"


class Transaction(db.Model):  # type: ignore[name-defined]
    """A single SIP instalment execution against a mandate.

    The ``idempotency_key`` column has a UNIQUE constraint so that
    re-processing the same instalment is safely a no-op.

    Attributes:
        id: UUID primary key.
        mandate_id: FK to the parent SIPMandate.
        amount: Debit amount in paise (integer).
        idempotency_key: Caller-supplied key ensuring at-most-once processing.
        status: Current transaction lifecycle status.
        error_message: Human-readable reason when status is FAILED.
        mandate: Many-to-one relationship with SIPMandate.
    """

    __tablename__ = "transactions"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    mandate_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("sip_mandates.id"), nullable=False
    )
    amount: Mapped[int] = mapped_column(Integer, nullable=False)
    idempotency_key: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False
    )
    status: Mapped[TransactionStatus] = mapped_column(
        Enum(TransactionStatus), nullable=False, default=TransactionStatus.PENDING
    )
    error_message: Mapped[Optional[str]] = mapped_column(
        String(500), nullable=True, default=None
    )

    # Relationships
    mandate: Mapped["SIPMandate"] = relationship(
        "SIPMandate", back_populates="transactions"
    )

    def __repr__(self) -> str:
        return f"<Transaction {self.idempotency_key} status={self.status.value}>"
