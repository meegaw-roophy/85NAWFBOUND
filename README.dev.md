Developer quick start

1) Prepare environment

```powershell
cd C:\Users\Admin\Desktop\VEKTRA
copy .env.example .env
# edit .env to set DB, STRIPE_API_KEY, STRIPE_WEBHOOK_SECRET
```

2) Run services, migrations, backend

```powershell
# on Windows, use helper
scripts\dev_start.ps1
# OR manually
docker compose up -d
cd backend
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

3) Run tests

Linux/macOS:
```bash
./scripts/run_tests.sh
```

Windows (PowerShell):
```powershell
scripts\run_tests.ps1
```

4) Forward Stripe events (use Stripe CLI)

```powershell
# Windows helper
scripts\stripe_cli_forward.ps1 -Port 8000
# or directly
stripe listen --forward-to localhost:8000/api/v1/webhooks/stripe
```

5) Quick local webhook test without Stripe (unsigned JSON)

```bash
python scripts/send_test_webhook.py --url http://localhost:8000/api/v1/webhooks/stripe --local-payment-id 1
```

Notes:
- If you set `STRIPE_WEBHOOK_SECRET`, the `verify_stripe_webhook` function will validate signatures; use Stripe CLI or ngrok for signed events.
- The `Makefile` provides cross-platform shortcuts for Linux/macOS. On Windows use the PowerShell scripts.
