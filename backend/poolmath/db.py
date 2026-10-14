"""Database engine + session dependency."""

from __future__ import annotations

from collections.abc import Iterator

from sqlmodel import Session, SQLModel, create_engine

from . import config

engine = create_engine(config.database_url(), connect_args={"check_same_thread": False})


# SQLite's create_all won't add columns to tables that already exist, so an
# existing DB started before a column was introduced would crash on insert.
# (table, column, column-declaration) pairs to backfill on startup.
_COLUMN_MIGRATIONS: list[tuple[str, str, str]] = [
    ("testlog", "test_type", "VARCHAR NOT NULL DEFAULT 'full'"),
    ("testlog", "fc_color", "VARCHAR"),
    ("testlog", "ph_quick", "VARCHAR"),
]


def _migrate_columns() -> None:
    with engine.begin() as conn:
        for table, col, decl in _COLUMN_MIGRATIONS:
            cols = {r[1] for r in conn.exec_driver_sql(f"PRAGMA table_info({table})")}
            # Empty result = table didn't exist; create_all (above) just made it.
            if cols and col not in cols:
                conn.exec_driver_sql(f"ALTER TABLE {table} ADD COLUMN {col} {decl}")


def init_db() -> None:
    # Ensure table classes are registered before create_all.
    from . import models  # noqa: F401

    SQLModel.metadata.create_all(engine)
    _migrate_columns()


def get_session() -> Iterator[Session]:
    with Session(engine) as session:
        yield session
