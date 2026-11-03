# CaptchaEarn — full-source starter

A responsive Flask earning-task website with user accounts, one-time transcription tasks, wallet ledger, UPI/Paytm withdrawal requests and an admin dashboard.

## Important operating model
This starter is for **authorized text-transcription tasks only**. It is not connected to third-party CAPTCHA services and must not be used to bypass CAPTCHAs, anti-bot controls, or website access restrictions. Only publish content you own or have permission to use. Do not advertise guaranteed income. You must have a real, sustainable revenue source before offering rewards.

## Run locally
1. Install Python 3.10+.
2. In this folder run:
   ```bash
   python -m venv .venv
   # Windows: .venv\Scripts\activate
   # macOS/Linux: source .venv/bin/activate
   pip install -r requirements.txt
   ```
3. Copy `.env.example` to `.env` and set a strong `SECRET_KEY`, `ADMIN_EMAIL`, and `ADMIN_PASSWORD`.
4. Export those variables in your terminal (or use a local dotenv runner; `python-dotenv` is not included).
5. Start with `python app.py`; open http://127.0.0.1:5000.

## Create the first admin
Set `ADMIN_EMAIL` and `ADMIN_PASSWORD` before first launch. The app creates the admin account once. Keep these credentials private and change the password strategy before public launch.

## Deploy using free-tier services
- Deploy this repository to a Python host such as Render using `render.yaml`.
- Attach a PostgreSQL database and set `DATABASE_URL` to its connection string. A local SQLite file on an ephemeral free web service may be erased during redeploy/restart.
- Set `SECRET_KEY`, `ADMIN_EMAIL`, `ADMIN_PASSWORD`, and `COOKIE_SECURE=1` in the host's environment settings.
- Free-tier limits and availability change; check the provider's current pricing and persistence terms before launch.

## How it works
- Admin adds a task: title, visible text to transcribe, expected answer, and reward.
- A user submits the transcription. Matching is case-insensitive and whitespace-trimmed.
- Each user can earn each task once.
- Withdrawal requests reserve wallet balance. Admin can approve (then make the real transfer separately) or reject (the balance is refunded).
- Payment approval does **not** send money automatically. Integrate a compliant payout provider only after business/KYC review and secure server-side credentials.

## Before accepting real users
This is an MVP starter, not a payment-ready audited production system. Add email verification, password reset, rate limiting, login throttling, audit logs, stronger admin role management, monitoring, backups, privacy/terms/refund policies, anti-fraud checks, and a payment-provider integration. Review local laws, tax, consumer-protection and payment-provider rules. Never store UPI PINs, OTPs, card details or bank passwords. Do not expose task answers in client-side HTML in a real public task marketplace; use server-side validation with task delivery designed for your authorized workflow.
