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

