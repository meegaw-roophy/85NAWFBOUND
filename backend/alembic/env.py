from logging.config import fileConfig
import os
import sys

from dotenv import load_dotenv
from sqlalchemy import pool
from alembic import context
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]

# Load .env before reading DATABASE_URL
load_dotenv(BASE_DIR / ".env")

# Alembic Config
config = context.config

# Logging
fileConfig(config.config_file_name)

# Allow importing app modules
sys.path.append(os.getcwd())

from app.db.models import Base

target_metadata = Base.metadata

def run_migrations_offline():
    url = os.getenv('DATABASE_URL') or config.get_main_option('sqlalchemy.url')
    print("DATABASE_URL =", url)
    print("Driver =", url.split(":")[0])
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online():
    url = os.getenv("DATABASE_URL") or config.get_main_option("sqlalchemy.url")

    print("DATABASE_URL =", url)

    # Convert async URL to sync for Alembic
    url = url.replace("postgresql+asyncpg://", "postgresql://")

    from sqlalchemy import create_engine

    connectable = create_engine(
        url,
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )

        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
