.PHONY: deps migrate start test stripe-listen

deps:
	python -m pip install -r backend/requirements.txt

migrate:
	cd backend && alembic upgrade head

start:
	docker compose up -d
	uvicorn app.main:app --reload --port 8000

test:
	python -m pytest -q

stripe-listen:
	stripe listen --forward-to localhost:8000/api/v1/webhooks/stripe
