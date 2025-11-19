# Loan Management System — Sprint 01 Minimal Implementation

This repository contains a minimal implementation for Sprint 01 of a Microfinance Loan Management System.

What is included
- Flask backend with SQLite (`app.db`)
- Application submission API and HTML form (`/`)
- Document upload (saved to `uploads/`)
- Verifier dashboard (`/verifier`) with Verify / Send Back actions
- Simple notification hook (console by default, SMTP if configured via `.env`)

Quick start

1. Create a virtual environment and install dependencies

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

2. (Optional) Configure SMTP by copying `.env.example` to `.env` and filling values.

3. Run the app

```bash
python3 app.py
```

4. Open in browser
- Application form: http://127.0.0.1:5000/
- Verifier dashboard: http://127.0.0.1:5000/verifier

API examples

Submit application with files (curl):

```bash
curl -v -X POST http://127.0.0.1:5000/api/applications \
  -F "name=Alice" -F "email=alice@example.com" -F "amount=5000" -F "purpose=Business" \
  -F "documents=@/path/to/id.jpg" -F "documents=@/path/to/income.pdf"
```

List applications:

```bash
curl http://127.0.0.1:5000/api/applications
```

Verify application:

```bash
curl -X POST http://127.0.0.1:5000/api/applications/1/verify \
  -H "Content-Type: application/json" \
  -d '{"action":"verify","comment":"KYC ok"}'
```

Notes
- Uploaded files are stored in `uploads/` in the repo root.
- Database file `app.db` is created automatically on first run.

Next steps you might want me to do
- Add proper authentication for agents/verifiers
- Add server-side validation and file-type checks
- Swap local storage for cloud storage (S3) and add background tasks for heavy processing
- Add tests and CI
# Loan_management_system