# AI Guidance & System Prompts

This file contains the strict constraints and rules fed to the AI coding assistant (Cursor/Claude/Gemini) during the development of this MVP. 

## 1. Architectural Constraints
* **No raw SQL.** All database interactions must use SQLAlchemy ORM.
* **ACID Compliance:** Any endpoint modifying a user's wallet balance MUST use pessimistic locking (`with_for_update()`) and explicit transaction blocks. If any step fails, the entire session must rollback.
* **Idempotency:** The payment processing route must check for the presence of an `Idempotency-Key` header before touching the database.

## 2. Interface Safety
* **Strict Input Validation:** All incoming JSON payloads must be validated against a Pydantic or Marshmallow schema before hitting the business logic.
* **No Silent Failures:** If an operation fails (e.g., Insufficient Funds), the API must return a clear 400-level HTTP status code with a standard JSON error response: `{"error": "description"}`.

## 3. Testing Rules
* For every core business function generated, generate a corresponding `pytest` function.
* Tests must cover the happy path AND edge cases (e.g., negative investment amounts, zero wallet balance, missing idempotency keys).