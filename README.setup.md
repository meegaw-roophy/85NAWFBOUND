## Quick setup

1. Enter the project folder:

```bash
cd VEKTRA/backend
```

2. Create virtualenv and install:

```bash
python -m venv .venv
source .venv/bin/activate  # or .venv\\Scripts\\activate on Windows
pip install -r requirements.txt
```

3. Start infra:

```bash
cd ../infra
docker compose up -d
```

4. Run the API:

```bash
cd ../backend
uvicorn app.main:app --reload --port 8000
```
