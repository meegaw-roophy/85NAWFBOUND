# VEKTRA

VEKTRA — personal and business progress tracking app with AI-powered insights.

## Structure

- `backend/` — FastAPI REST API (auth, snapshots, goals, reports, payments, analytics)
- `frontend/` — Django templates dashboard with Chart.js visualizations
- `infra/` — Docker Compose (Postgres, backend, frontend)
- `ai/` — AI integration (Anthropic Claude for report generation)
- `payments/` — Payment integrations (Stripe subscriptions, M-Pesa STK push)

## Quick Start

```bash
cd infra
cp .env.example .env   # fill in secrets
docker compose up -d
# backend: http://localhost:8000
# frontend: http://localhost:8001
```

## API Routes

### Auth
- `POST /api/v1/auth/register` — create a new user
- `POST /api/v1/auth/token` — obtain a Bearer token
- `GET /api/v1/users/me` — current authenticated user
- `PATCH /api/v1/users/me` — update profile (username, email)
- `POST /api/v1/users/me/password` — change password

### Snapshots
- `POST /api/v1/users/{user_id}/snapshots` — add a snapshot (mood, energy, focus, income, expenses, savings)
- `GET /api/v1/users/{user_id}/snapshots` — list user snapshots

### Goals
- `POST /api/v1/users/{user_id}/goals` — create a goal
- `GET /api/v1/users/{user_id}/goals` — list goals (filter by `?status=active|completed|paused|cancelled`)
- `GET /api/v1/users/{user_id}/goals/{goal_id}` — get a single goal
- `PATCH /api/v1/users/{user_id}/goals/{goal_id}` — update goal progress/status
- `DELETE /api/v1/users/{user_id}/goals/{goal_id}` — delete a goal

### Reports
- `POST /api/v1/users/{user_id}/reports` — create a report record
- `GET /api/v1/users/{user_id}/reports` — list saved reports
- `POST /api/v1/users/{user_id}/reports/generate` — generate AI-powered report from snapshot history

### Analytics
- `GET /api/v1/users/{user_id}/analytics/summary?days=30` — dashboard analytics (mood trends, finances, goal progress)

### Payments
- `POST /api/v1/users/{user_id}/subscriptions` — create/update subscription
- `GET /api/v1/users/{user_id}/subscriptions` — list subscriptions
- `POST /api/v1/users/{user_id}/payments/stripe` — Stripe subscription payment
- `POST /api/v1/users/{user_id}/payments/stripe/checkout` — Stripe Checkout session
- `POST /api/v1/users/{user_id}/payments/mpesa` — M-Pesa STK push payment
- `POST /api/v1/webhooks/stripe` — Stripe webhook handler

### System
- `GET /api/v1/health` — health check

## Features

- **Goal Tracking**: Set financial, wellness, career, education, and fitness goals with progress tracking and auto-completion
- **Mood & Energy Tracking**: Daily snapshots with 0-10 scales for mood, energy, and focus
- **Financial Tracking**: Income, expenses, and savings per snapshot with trend analysis
- **AI Reports**: Claude-powered analysis of your snapshot history with actionable insights
- **Dashboard Analytics**: Chart.js visualizations — mood trends, income vs expenses, goal progress bars
- **Stripe Payments**: Subscription management via Stripe Checkout and webhooks
- **M-Pesa Payments**: Mobile money integration for East African users
- **Security**: Random JWT secrets, password strength validation, rate limiting, CORS enforcement

## Environment Variables

See `backend/.env.example` and `infra/.env.example` for full list.

Key variables:
- `SECRET_KEY` — JWT signing key (auto-generated if unset)
- `DATABASE_URL` — PostgreSQL connection string
- `CLAUDE_API_KEY` — Anthropic API key for AI reports
- `STRIPE_API_KEY` — Stripe secret key
- `STRIPE_WEBHOOK_SECRET` — Stripe webhook signing secret

## Migrations

```bash
chmod +x scripts/run_migrations.sh
./scripts/run_migrations.sh
```
