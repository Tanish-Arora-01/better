"""REST API routes for the SIP Billing Engine.

Endpoints:
    POST /api/users             – Create a new user.
    GET  /api/users/<user_id>   – Get user details (balance).
    POST /api/mandates          – Create a new SIP mandate.
    GET  /api/mandates/<user_id> – List all mandates for a user.
    POST /api/process-sip       – Process a SIP instalment (idempotent, ACID).
"""

from flask import Blueprint, jsonify, request

from app import db
from app.models import (
    MandateStatus,
    SIPMandate,
    Transaction,
    TransactionStatus,
    User,
)
from app.schemas import ProcessSIPSchema, SIPMandateCreateSchema, ValidationError

api = Blueprint("api", __name__, url_prefix="/api")

# ── Schema singletons ───────────────────────────────────────────────
_mandate_create_schema = SIPMandateCreateSchema()
_process_sip_schema = ProcessSIPSchema()


# ── Helpers ──────────────────────────────────────────────────────────

def _user_to_dict(user: User) -> dict:
    """Serialise a User to a JSON-safe dict."""
    return {
        "id": user.id,
        "name": user.name,
        "wallet_balance": user.wallet_balance,
    }


def _txn_to_dict(txn: Transaction) -> dict:
    """Serialise a Transaction to a JSON-safe dict."""
    return {
        "id": txn.id,
        "mandate_id": txn.mandate_id,
        "amount": txn.amount,
        "idempotency_key": txn.idempotency_key,
        "status": txn.status.value,
        "error_message": txn.error_message,
    }


def _mandate_to_dict(mandate: SIPMandate) -> dict:
    """Serialise a SIPMandate to a JSON-safe dict."""
    return {
        "id": mandate.id,
        "user_id": mandate.user_id,
        "fund_name": mandate.fund_name,
        "amount": mandate.amount,
        "status": mandate.status.value,
    }


# =====================================================================
# POST /api/users  –  Create a new user
# =====================================================================

@api.route("/users", methods=["POST"])
def create_user():
    """Create a new user with the default wallet balance.

    Request JSON:
        name (str): Display name of the user.

    Returns:
        201 with the new user on success.
        400 if name is missing.
    """
    data = request.get_json(force=True)
    name = data.get("name", "").strip()
    if not name:
        return jsonify({"error": "Name is required."}), 400

    user = User(name=name)
    db.session.add(user)
    db.session.commit()
    return jsonify(_user_to_dict(user)), 201


# =====================================================================
# GET /api/users/<user_id>  –  Get user details
# =====================================================================

@api.route("/users/<string:user_id>", methods=["GET"])
def get_user(user_id: str):
    """Return user details including wallet balance.

    Returns:
        200 with user data.
        404 if user not found.
    """
    user = db.session.get(User, user_id)
    if user is None:
        return jsonify({"error": f"User {user_id} not found."}), 404
    return jsonify(_user_to_dict(user)), 200


# =====================================================================
# POST /api/mandates  –  Create a new SIP mandate
# =====================================================================

@api.route("/mandates", methods=["POST"])
def create_mandate():
    """Create a new SIP mandate for a user.

    Request JSON:
        user_id   (str): UUID of the user.
        fund_name (str): Mutual fund name.
        amount    (int): SIP amount in paise (> 0).

    Returns:
        201 with the new mandate on success.
        400 on validation or user-not-found errors.
    """
    data = _mandate_create_schema.load(request.get_json(force=True))

    user = db.session.get(User, data["user_id"])
    if user is None:
        return jsonify({"error": f"User {data['user_id']} not found."}), 400

    mandate = SIPMandate(
        user_id=data["user_id"],
        fund_name=data["fund_name"],
        amount=data["amount"],
    )
    db.session.add(mandate)
    db.session.commit()

    return jsonify(_mandate_to_dict(mandate)), 201


# =====================================================================
# GET /api/mandates/<user_id>  –  List mandates for a user
# =====================================================================

@api.route("/mandates/<string:user_id>", methods=["GET"])
def list_mandates(user_id: str):
    """Return all mandates belonging to the given user.

    Returns:
        200 with a list of mandates.
        404 if the user does not exist.
    """
    user = db.session.get(User, user_id)
    if user is None:
        return jsonify({"error": f"User {user_id} not found."}), 404

    mandates = (
        db.session.query(SIPMandate)
        .filter_by(user_id=user_id)
        .all()
    )
    return jsonify([_mandate_to_dict(m) for m in mandates]), 200


# =====================================================================
# POST /api/process-sip  –  Idempotent SIP instalment processing
# =====================================================================

@api.route("/process-sip", methods=["POST"])
def process_sip():
    """Process a single SIP instalment with strict idempotency and ACID.

    Headers:
        Idempotency-Key (required): Caller-supplied unique key.

    Request JSON:
        mandate_id (str): UUID of the mandate to execute.

    Algorithm:
        1. Reject if Idempotency-Key header is missing.
        2. If a Transaction with this key already exists → return it (200).
        3. Otherwise, inside an explicit transaction block:
            a. Lock the User row (``with_for_update``).
            b. If balance >= mandate amount → deduct, create COMPLETED txn.
            c. Else → create FAILED txn with error message.
        4. On any unexpected exception → rollback, return 500.
    """
    # ── 1. Extract idempotency key from headers ──────────────────────
    idempotency_key: str | None = request.headers.get("Idempotency-Key")
    if not idempotency_key:
        return jsonify({"error": "Missing Idempotency-Key header."}), 400

    # ── 2. Validate body ─────────────────────────────────────────────
    data = _process_sip_schema.load(request.get_json(force=True))

    # ── 3. Idempotency check – return existing txn if key seen before ─
    existing_txn: Transaction | None = (
        db.session.query(Transaction)
        .filter_by(idempotency_key=idempotency_key)
        .first()
    )
    if existing_txn is not None:
        return jsonify(_txn_to_dict(existing_txn)), 200

    # ── 4. Look up mandate ───────────────────────────────────────────
    mandate: SIPMandate | None = db.session.get(SIPMandate, data["mandate_id"])
    if mandate is None:
        return jsonify({"error": f"Mandate {data['mandate_id']} not found."}), 400

    if mandate.status != MandateStatus.ACTIVE:
        return jsonify({"error": f"Mandate is {mandate.status.value}, not ACTIVE."}), 400

    # ── 5. ACID block – pessimistic lock on User row ─────────────────
    try:
        # Lock the user row to prevent concurrent balance modifications.
        user: User = (
            db.session.query(User)
            .filter_by(id=mandate.user_id)
            .with_for_update()
            .one()
        )

        if user.wallet_balance >= mandate.amount:
            # Sufficient funds → deduct and mark COMPLETED.
            user.wallet_balance -= mandate.amount
            txn = Transaction(
                mandate_id=mandate.id,
                amount=mandate.amount,
                idempotency_key=idempotency_key,
                status=TransactionStatus.COMPLETED,
            )
            db.session.add(txn)
            db.session.commit()
            return jsonify(_txn_to_dict(txn)), 201
        else:
            # Insufficient funds → record FAILED transaction.
            txn = Transaction(
                mandate_id=mandate.id,
                amount=mandate.amount,
                idempotency_key=idempotency_key,
                status=TransactionStatus.FAILED,
                error_message="Insufficient wallet balance.",
            )
            db.session.add(txn)
            db.session.commit()
            return jsonify({
                "error": "Insufficient wallet balance.",
                "transaction": _txn_to_dict(txn),
            }), 400

    except Exception as exc:
        db.session.rollback()
        return jsonify({"error": f"Internal server error: {str(exc)}"}), 500
