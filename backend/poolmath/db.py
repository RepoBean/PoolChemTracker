"""Database engine + session dependency."""

from __future__ import annotations

from collections.abc import Iterator

from sqlmodel import Session, SQLModel, create_engine

from . import config

engine = create_engine(config.database_url(), connect_args={"check_same_thread": False})


def init_db() -> None:
    # Ensure table classes are registered before create_all.
    from . import models  # noqa: F401

    SQLModel.metadata.create_all(engine)


def get_session() -> Iterator[Session]:
    with Session(engine) as session:
        yield session
