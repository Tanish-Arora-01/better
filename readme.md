# Idempotent SIP Billing Engine

A lightweight, fault-tolerant backend system and React dashboard designed for processing Systematic Investment Plan (SIP) installments. This submission for Better Software focuses heavily on system correctness, interface safety, and robust operational guardrails to ensure reliable financial transactions.

## Architecture & Guardrails

* **Idempotency:** Prevents double charges and guarantees safe retries by enforcing strict idempotency keys via HTTP headers.
* **ACID Transactions:** Utilizes pessimistic row locking (`with_for_update()`) to prevent race conditions during concurrent installment processing.
* **Finite State Machine:** Enforces strict execution paths with discrete `PENDING`, `COMPLETED`, and `FAILED` statuses to maintain data integrity.
* **Interface Safety:** Leverages Marshmallow for rigorous payload validation, sanitization, and type-checking at the API boundary layer.

## Tech Stack

* **Backend:** Python 3.13, Flask, SQLAlchemy ORM, Marshmallow
* **Database:** SQLite
* **Frontend:** React 19, Vite, Tailwind CSS v4
* **Testing:** Pytest (35 automated tests)

## How to Run Locally

### Backend Setup

Create and activate a virtual environment:

```bash
python -m venv venv
venv\Scripts\activate  # On macOS/Linux: source venv/bin/activate
```

Install dependencies and start the application:

```bash
pip install -r requirements.txt
python run.py
```

### Frontend Setup

Install Node dependencies and start the Vite development server:

```bash
npm install
npm run dev
```

## Running the Test Suite

Execute the comprehensive automated test suite:

```bash
pytest -v
```

## Required Assessment Files

* **Walkthrough Video:** [link](#https://drive.google.com/drive/folders/1uYf86O0eUigbzAPrG0hO0OntTcwVOlhy?usp=sharing)
* **AI Guidance:** Please review the included `ai_guidance.md` file for details regarding the AI tooling utilized during development.
