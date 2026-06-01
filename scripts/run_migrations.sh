#!/usr/bin/env bash
set -euo pipefail

echo "Running alembic migrations (backend)"
if [ -f backend/alembic.ini ]; then
  cd backend
  alembic upgrade head
  cd -
else
  echo "No backend/alembic.ini found"
fi

echo "Running Django migrations (frontend placeholder)"
if [ -d frontend/django_project ]; then
  cd frontend/django_project
  python manage.py migrate || true
  cd -
else
  echo "No frontend/django_project found"
fi

echo "Migrations complete"
