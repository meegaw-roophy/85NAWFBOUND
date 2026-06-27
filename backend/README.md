# Backend (FastAPI)

Quick start:

1. Create a Python virtual environment and activate it.

```bash
python -m venv .venv
source .venv/bin/activate  # or .venv\\Scripts\\activate on Windows
pip install -r requirements.txt
```

2. Start Postgres (docker-compose) and run the app:

```bash
docker compose up -d
uvicorn app.main:app --reload --port 8000
```

3. Configure environment variables:

```bash
copy ..\.env.example ..\.env
```

Open `..\.env` and set:
- `STRIPE_API_KEY` to your Stripe secret key
- `STRIPE_WEBHOOK_SECRET` to the webhook signing secret from Stripe

4. Test Stripe webhooks locally:

- Option A: use `ngrok`

```bash
ngrok http 8000
```

Then set Stripe webhook endpoint to:

`https://<YOUR_NGROK_ID>.ngrok.io/api/v1/webhooks/stripe`

- Option B: use Stripe CLI

```bash
stripe listen --forward-to localhost:8000/api/v1/webhooks/stripe
```

In Stripe, subscribe the endpoint to events such as:
- `invoice.payment_succeeded`
- `invoice.payment_failed`
- `payment_intent.succeeded`
- `payment_intent.payment_failed`
- `customer.subscription.created`

When Stripe sends a webhook, the backend updates the local payment record stored in the database.

