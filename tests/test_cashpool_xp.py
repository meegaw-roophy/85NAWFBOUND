import asyncio
import datetime
import os
import sys

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

from app.main import app
from app.api.v1 import snapshots as snapshots_api
from app.crud import xp_level
from app.db.models import Base
from app.db.session import get_session


@pytest.fixture()
def client(tmp_path, monkeypatch):
    engine = create_async_engine(f"sqlite+aiosqlite:///{(tmp_path / 'test.db').as_posix()}")
    Session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async def create():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    asyncio.run(create())

    async def override():
        async with Session() as session:
            yield session

    app.dependency_overrides[get_session] = override
    monkeypatch.setattr(snapshots_api, "AsyncSessionLocal", Session)
    yield TestClient(app)
    app.dependency_overrides.pop(get_session, None)
    asyncio.run(engine.dispose())


def _login(client):
    user = client.post("/api/v1/auth/register", json={
        "username": "saver", "email": "saver@example.com", "password": "pw123456!"}).json()
    token = client.post("/api/v1/auth/token", data={"username": "saver", "password": "pw123456!"}).json()["access_token"]
    return user["id"], {"Authorization": f"Bearer {token}"}


def _log(client, user_id, headers, days_ago, **fields):
    # Backdated by timestamp: create_snapshot matches same-day repeats on
    # timestamp, so a backdated log_date would collide with today's log.
    when = datetime.datetime.combine(datetime.date.today() - datetime.timedelta(days=days_ago), datetime.time(12))
    return client.post(f"/api/v1/users/{user_id}/snapshots", headers=headers, json={"timestamp": when.isoformat(), **fields})


def test_xp_levels_grow_by_half_each_level():
    assert xp_level(0) == (1, 0, 100)
    assert xp_level(99) == (1, 99, 100)
    assert xp_level(100) == (2, 0, 150)
    assert xp_level(260) == (3, 10, 225)


def test_cashpool_matches_report_definitions(client):
    user_id, headers = _login(client)
    _log(client, user_id, headers, 2, daily_income=5000, expenses=4000, expense_category="food")
    _log(client, user_id, headers, 1, daily_income=2000, expenses=500, expense_category="transport")
    _log(client, user_id, headers, 0, daily_income=1650, expenses=1900)

    pool = client.get("/api/v1/cashpool", headers=headers).json()
    assert pool["period_income"] == 8650
    assert pool["period_expenses"] == 6400
    assert pool["current_savings_rate"] == pytest.approx(2250 / 8650, abs=1e-4)
    assert pool["daily_spend_cap"] is None          # no currency-blind default
    assert pool["current_runway_days"] is None      # capital never logged

    pool = client.put("/api/v1/cashpool", headers=headers, json={"daily_spend_cap": 1500}).json()
    assert pool["cap_breach_count"] == 2

    categories = client.get("/api/v1/cashpool/spending-by-category", headers=headers).json()["categories"]
    assert categories == {"food": 4000, "transport": 500, "uncategorized": 1900}


def test_unknown_expense_category_is_rejected(client):
    user_id, headers = _login(client)
    assert _log(client, user_id, headers, 0, expenses=10, expense_category="crypto").status_code == 422


def test_xp_is_awarded_once_per_day_and_cannot_be_self_granted(client):
    user_id, headers = _login(client)
    _log(client, user_id, headers, 1, mood_score=6)
    _log(client, user_id, headers, 0, mood_score=6)
    before = client.get("/api/v1/gamification/points", headers=headers).json()
    assert before["total_points"] >= 20
    assert before["points_to_next"] == before["xp_level_span"] - before["xp_into_level"]

    _log(client, user_id, headers, 0, mood_score=9)  # same day again
    assert client.get("/api/v1/gamification/points", headers=headers).json() == before

    granted = client.post("/api/v1/gamification/points/transaction?points=9999&reason=x", headers=headers)
    assert granted.status_code in (404, 405)
