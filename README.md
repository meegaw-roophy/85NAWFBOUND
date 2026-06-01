# VEKTRA

VEKTRA — personal and business progress tracking app (backend FastAPI).

Structure:
- `backend/` — FastAPI app and infra
- `frontend/` — frontend app (TBD; Django/React)
- `infra/` — docker-compose, postgres
- `ai/` — AI integration notes (Claude)
- `payments/` — payment integrations (Stripe, M-Pesa)

Next steps: install dependencies, init git, configure Postgres, and choose frontend framework.
Helpful notes:
- To run everything locally with Docker Compose:

```bash
cd infra
docker compose up -d
# backend: http://localhost:8000
# frontend (Django placeholder): http://localhost:8001
```

- Git is not installed in your environment here; install Git and run:

```bash
cd C:/Users/Admin/Desktop/VEKTRA
git init
git add .
git commit -m "Initial VEKTRA scaffold"
```

If you want, I can prepare a `git remote add` command for your chosen hosting provider.
Dockerfiles:
- `backend/Dockerfile` — builds the FastAPI app container used by `infra/docker-compose.yml`.
- `frontend/django_project/Dockerfile` — builds the Django placeholder container.

API routes available locally:
- `POST /api/v1/auth/register` — create a new user
- `POST /api/v1/auth/token` — obtain a Bearer token
- `GET /api/v1/users/me` — verify the current authenticated user
- `POST /api/v1/users/{user_id}/snapshots` — add a snapshot
- `GET /api/v1/users/{user_id}/snapshots` — list user snapshots
- `POST /api/v1/users/{user_id}/reports` — create a report record
- `GET /api/v1/users/{user_id}/reports` — list saved reports
- `POST /api/v1/users/{user_id}/reports/generate` — generate a report from snapshot history
- `POST /api/v1/users/{user_id}/subscriptions` — create or update a subscription record
- `GET /api/v1/users/{user_id}/subscriptions` — list user subscriptions
- `POST /api/v1/users/{user_id}/payments/stripe` — simulate a Stripe payment placeholder
- `POST /api/v1/users/{user_id}/payments/mpesa` — simulate an M-Pesa payment placeholder

The AI report generator will use `CLAUDE_API_KEY` when configured, otherwise it falls back to a structured summary.

Run migrations helper:

```bash
chmod +x scripts/run_migrations.sh
./scripts/run_migrations.sh
```