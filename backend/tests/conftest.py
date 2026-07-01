"""Shared test fixtures — in-memory DB so no real data file is touched."""

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool

from poolmath import db
from poolmath.main import app


@pytest.fixture()
def client():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    SQLModel.metadata.create_all(engine)

    def override_get_session():
        with Session(engine) as session:
            yield session

    app.dependency_overrides[db.get_session] = override_get_session
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
