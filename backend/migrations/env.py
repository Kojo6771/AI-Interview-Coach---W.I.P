from importlib import import_module
from logging.config import fileConfig
from typing import Any

from alembic import context
from sqlalchemy import engine_from_config, pool

from app.config import Database_URL
from app.database import Base

import_module("app.models")


config = context.config
config.set_main_option("sqlalchemy.url", Database_URL.replace("%", "%%"))
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def include_object(
    _object: Any,
    name: str,
    type_: str,
    reflected: bool,
    _compare_to: Any,
) -> bool:
    _ = _object, _compare_to
    if type_ == "table" and reflected and name.startswith("legacy_"):
        return False
    return True


def run_migrations_offline() -> None:
    context.configure(
        url=Database_URL,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        include_object=include_object,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            include_object=include_object,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
