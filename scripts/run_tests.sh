#!/usr/bin/env bash
set -e
ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

python -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
python -m pytest -q
