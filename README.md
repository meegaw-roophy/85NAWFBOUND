# VEKTRA

VEKTRA — personal and business progress tracking app (backend FastAPI).

Structure:
- `backend/` — FastAPI app and infra
- `frontend/` — frontend app (TBD; Django/React)
- `infra/` — docker-compose, postgres
- `ai/` — AI integration notes (Claude)
- `payments/` — payment integrations (Stripe, M-Pesa)

Next steps: install dependencies, configure Postgres, and use the current Django templates frontend.
Helpful notes:
- The local Git repository is already initialized and mirrored to `C:\Users\Admin\Documents\GitHub\85NAWFBOUND`.
- The frontend is now finalized as Django templates, and it includes a live health check plus auth/snapshot/report UI on the dashboard.
- To run everything locally with Docker Compose:

```bash
cd infra
docker compose up -d
# backend: http://localhost:8000
# frontend: http://localhost:8001
```

- If you want to add a remote URL, use:

```bash
git remote add origin <REMOTE_URL>
git branch -M main
git push -u origin main
```

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