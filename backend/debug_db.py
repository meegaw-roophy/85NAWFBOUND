import asyncio
from app.db.session import engine
from app.db.models import Snapshot
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

async def check_db():
    async with AsyncSession(engine) as db:
        result = await db.execute(select(Snapshot).where(Snapshot.user_id == 2).limit(1))
        logs = result.scalars().all()
        if logs:
            print(f"FOUND {len(logs)} logs")
            print(f"COLUMNS: {list(logs[0].__dict__.keys())}")
        else:
            print("No logs found")

if __name__ == "__main__":
    asyncio.run(check_db())
