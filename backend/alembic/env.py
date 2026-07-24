from logging.config import fileConfig
import os
from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

# this is the Alembic Config object, which provides access to the values in the .ini file
config = context.config

# Interpret the config file for Python logging.
fileConfig(config.config_file_name)

import sys
import os
sys.path.append(os.getcwd())

from app.db.models import Base
target_metadata = Base.metadata

def run_migrations_offline():
    url = os.getenv('DATABASE_URL') or config.get_main_option('sqlalchemy.url')
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online():
    url = os.getenv('DATABASE_URL') or config.get_main_option('sqlalchemy.url')
    
    # asyncpg doesn't work with sync alembic - use psycopg2 format
    url = url.replace('postgresql+asyncpg://', 'postgresql://')
    
    from sqlalchemy import create_engine
    connectable = create_engine(url, poolclass=pool.NullPool)
    
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()
