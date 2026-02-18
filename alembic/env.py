from __future__ import with_statement
import os
import sys
from logging.config import fileConfig
from dotenv import load_dotenv

load_dotenv()

from sqlalchemy import engine_from_config, pool

from alembic import context

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
fileConfig(config.config_file_name)

# Set sqlalchemy.url from env var if present
db_url = os.getenv('DATABASE_URL')
if db_url:
    config.set_main_option('sqlalchemy.url', db_url)

# Attempt to import application metadata for autogenerate support.
# Ensure project root is on sys.path so `web` package can be imported when
# running Alembic from the project root.
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

try:
    # Import the SQLAlchemy `db` instance from the app and use its metadata
    # for Alembic autogeneration. Import inside try/except to avoid hard
    # failures during environments where dependencies are not available.
    from web.server_postgresql import db
    target_metadata = db.metadata
except Exception:
    target_metadata = None


def run_migrations_offline():
    url = config.get_main_option('sqlalchemy.url')
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True)

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix='sqlalchemy.',
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
