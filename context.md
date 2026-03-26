# SIP Billing Engine – Context for Continuation

> **Last updated:** 2026-03-25  
> **Status:** Full stack complete – React frontend integrated.

---

## 1. Project Overview

An **Idempotent SIP (Systematic Investment Plan) Billing Engine** built for a technical assessment.

| Layer | Tech |
|---|---|
| Language | Python 3.13 |
| Web framework | Flask 3.1 |
| ORM | Flask-SQLAlchemy 3.1 (SQLAlchemy 2.x `Mapped` style) |
| Database | SQLite (file-based default, in-memory for tests) |
| Validation | Marshmallow 3.23 (`SIPMandateCreateSchema`, `ProcessSIPSchema`) |
| Tests | pytest 8.3 |

| Framework | React 19 + Vite 6 |
| Styling | Tailwind CSS v4 (dark mode design system) |
| Integration | Axios/Fetch wrapper (`api.js`) to `http://localhost:5000/api` |

---

## 2. Project Structure

```
Demo/
├── ai+guidance.md          # Architectural rules (source of truth)
├── config.py               # Config & TestingConfig classes
├── run.py                  # Dev server entry point
├── requirements.txt        # Pinned dependencies
├── app/
│   ├── __init__.py         # App factory, db, error handler, CORS
│   ├── models.py           # User, SIPMandate, Transaction
│   ├── routes.py           # API blueprint (5 endpoints)
│   └── schemas.py          # Marshmallow validation schemas
├── frontend/               # Vite React SPA
│   ├── src/
│   │   ├── api.js          # API service wrapper with idempotency logic
│   │   ├── Dashboard.jsx   # Main UI component
│   │   └── index.css       # Tailwind v4 configuration and tokens
│   └── vite.config.js      # Vite config with API proxy
└── tests/
    ├── __init__.py
    ├── test_engine.py      # 5 integration tests (idempotency, ACID, validation)
    ├── test_models.py      # 6 tests
    ├── test_routes.py      # 13 tests
    └── test_schemas.py     # 11 tests
```

---

## 3. Key Design Decisions

### 3.1 UUID Primary Keys
All models use `String(36)` columns with `uuid.uuid4()` defaults instead of auto-incrementing integers, providing globally unique identifiers.

### 3.2 Database-Level Constraints
- **`User.wallet_balance`**: `CHECK(wallet_balance >= 0)` – enforced at DB level via `CheckConstraint`.
- **`Transaction.idempotency_key`**: `UNIQUE` + `NOT NULL` – prevents duplicate transaction processing.

### 3.3 Enums
- `MandateStatus`: `ACTIVE`, `PAUSED`, `CANCELLED`
- `TransactionStatus`: `PENDING`, `COMPLETED`, `FAILED`

Both stored as SQLAlchemy `Enum` columns backed by Python `enum.Enum`.

### 3.4 Relationships
```
User  ──1:N──▶  SIPMandate  ──1:N──▶  Transaction
```
- `user.mandates` / `mandate.user` (cascade: all, delete-orphan)
- `mandate.transactions` / `txn.mandate` (cascade: all, delete-orphan)

### 3.5 Validation Schemas (Marshmallow)

| Schema | Fields | Validations |
|---|---|---|
| `SIPMandateCreateSchema` | `user_id`, `fund_name`, `amount` | UUID-4, length 1–100, integer > 0 |
| `ProcessSIPSchema` | `mandate_id` | UUID-4 |

A custom UUID-4 validator (`_validate_uuid`) is shared by both schemas.

### 3.6 Global Error Handler

`app/__init__.py` registers a Flask `@app.errorhandler(ValidationError)` that catches any Marshmallow `ValidationError` raised in a request and returns:

```json
{"error": "Invalid payload", "details": { ... }}
```

with HTTP **400**.

### 3.7 API Routes (`app/routes.py`)

All routes are on a Flask `Blueprint` with prefix `/api`.

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/api/users` | Create a new user (seeded balance) |
| `GET` | `/api/users/<user_id>` | Get user details |
| `POST` | `/api/mandates` | Create a new SIP mandate |
| `GET` | `/api/mandates/<user_id>` | List all mandates for a user |
| `POST` | `/api/process-sip` | Process SIP instalment (idempotent, ACID) |

**`POST /api/process-sip` algorithm:**
1. Reject if `Idempotency-Key` header is missing → 400.
2. Query `Transaction` by key. If exists → return it with 200 (no re-processing).
3. Validate body via `ProcessSIPSchema`.
4. Look up mandate; reject if not found or not ACTIVE → 400.
5. Lock `User` row with `with_for_update()` (pessimistic locking).
6. If `wallet_balance >= amount` → deduct, create COMPLETED txn, commit → 201.
7. If insufficient funds → create FAILED txn with error message, commit → 400.
8. On any exception → `db.session.rollback()` → 500.

### 3.8 Frontend Architecture (`frontend/`)
- **API Service Layer (`src/api.js`)**: Wraps fetch calls. For `POST /api/process-sip`, it generates a fresh UUID via `crypto.randomUUID()` and attaches it to the `Idempotency-Key` header automatically on button click.
- **Vite Proxy**: `vite.config.js` proxies `/api` → `http://localhost:5000` to avoid CORS preflight issues during dev.
- **UI (`src/Dashboard.jsx`)**: 
  - On mount: checks `localStorage` for a `sip_user_id`. If none, it creates a demo user automatically.
  - Wallet balance display.
  - List of active SIPs with a "Process Instalment" button.
  - Success/Error toast notifications reacting to HTTP status codes from the backend.

---

## 4. Configuration

| Class | `SQLALCHEMY_DATABASE_URI` | `TESTING` |
|---|---|---|
| `Config` | `sqlite:///sip_billing.db` (project root) | `False` |
| `TestingConfig` | `sqlite:///:memory:` | `True` |

The app factory `create_app(config_name)` accepts a dotted path string (default: `"config.Config"`).

---

## 5. Verified Tests (35 total, all passing ✅)

### Model tests (`test_models.py` – 6 tests)
User/SIPMandate/Transaction CRUD, CHECK constraint on wallet_balance, UNIQUE on idempotency_key, table creation.

### Schema tests (`test_schemas.py` – 11 tests)
Happy path for both schemas. Edge cases: missing fields, invalid UUID, zero/negative amount, empty/long fund_name. Flask error handler integration.

### Route tests (`test_routes.py` – 13 tests)

| Test | What it verifies |
|---|---|
| `test_create_mandate_success` | 201 + correct body |
| `test_create_mandate_user_not_found` | 400 for nonexistent user |
| `test_create_mandate_invalid_payload` | 400 with validation details |
| `test_list_mandates_success` | 200 + correct list |
| `test_list_mandates_empty` | 200 + empty list |
| `test_list_mandates_user_not_found` | 404 |
| `test_process_sip_success` | 201 COMPLETED, balance deducted |
| `test_idempotency_returns_existing_transaction` | 200 same txn, balance deducted only once |
| `test_missing_idempotency_key_returns_400` | 400 |
| `test_insufficient_balance_returns_400` | 400 FAILED txn |
| `test_mandate_not_found_returns_400` | 400 |
| `test_paused_mandate_returns_400` | 400 for non-ACTIVE mandate |
| `test_invalid_payload_returns_400` | 400 validation error |
### Engine integration tests (`test_engine.py` – 5 tests)

| Test | What it proves |
|---|---|
| `test_create_mandate_returns_201_with_correct_fields` | Mandate creation end-to-end |
| `test_process_sip_deducts_balance_and_returns_completed` | Successful deduction, wallet → 95 000 |
| `test_duplicate_key_deducts_only_once` | **Idempotency** – same key twice = 1 deduction, 200 replay |
| `test_low_balance_returns_400_and_failed_transaction` | **Interface safety** – 400 + FAILED txn, balance untouched |
| `test_negative_amount_returns_400_validation_error` | **Validation** – negative amount rejected at schema layer |

---

## 6. AI Guidance Rules (from `ai_guidance.md`)

These constraints **must** be followed in all subsequent work:

1. **No raw SQL** – use SQLAlchemy ORM exclusively.
2. **ACID Compliance** – any wallet-modifying endpoint must use `with_for_update()` + explicit transaction blocks; rollback on failure.
3. **Idempotency** – payment route must check `Idempotency-Key` header before any DB writes.
4. **Strict Input Validation** – validate all JSON via Marshmallow schemas before business logic.
5. **No Silent Failures** – return 400-level status + `{"error": "description"}` on failure.
6. **Testing** – every core function needs a `pytest` test covering happy path + edge cases.

---

## 7. Completion Status

- [x] SQLAlchemy models with constraints (`app/models.py`)
- [x] Marshmallow schemas for request validation (`app/schemas.py`)
- [x] Global validation error handler (`app/__init__.py`)
- [x] API routes with ACID + idempotency (`app/routes.py`)
- [x] Comprehensive tests (35 passing)
- [x] **React Frontend Dashboard (`frontend/`)** 

The MVP requirement is complete.
