# Idempotent SIP Billing Engine

A lightweight, fault-tolerant backend system and React dashboard for processing Systematic Investment Plan (SIP) installments. 

Built for the Better Software engineering assessment, this project prioritizes **Correctness, Interface Safety, and Change Resilience** over feature volume.

## 🏗️ Architecture & Guardrails
To ensure safe money movement and prevent invalid states, this engine implements:
* **Idempotency:** The `/api/process-sip` endpoint requires an `Idempotency-Key` header. Duplicate requests (e.g., network retries) are intercepted at the database level to prevent double-charging.
* **ACID Transactions:** Financial deductions use pessimistic row-level locking (`with_for_update()`) and explicit transaction blocks to prevent race conditions during concurrent requests.
* **Finite State Machine (FSM):** Transactions strictly follow a `PENDING` -> `COMPLETED` or `FAILED` lifecycle enforced via Enum columns.
* **Interface Safety:** All payloads are strictly validated using Marshmallow schemas before reaching the business logic.

## 💻 Tech Stack
* **Backend:** Python 3.13, Flask, SQLAlchemy ORM, Marshmallow
* **Database:** SQLite (File-based for MVP simplicity, structured for easy Postgres migration)
* **Frontend:** React 19, Vite, Tailwind CSS v4
* **Testing:** Pytest

## 🚀 How to Run Locally

### 1. Start the Backend (Flask)
Open a terminal in the root directory and run:

```bash
# Create and activate virtual environment
python -m venv venv
venv\Scripts\activate  # Use 'source venv/bin/activate' on Mac/Linux

# Install dependencies
pip install -r requirements.txt

# Run the Flask server (runs on port 5000)
python run.py
