"""API tests against an in-memory DB (no real data file touched)."""

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


def test_health(client):
    assert client.get("/api/health").json()["status"] == "ok"


def test_pool_crud(client):
    r = client.post("/api/pools", json={"name": "Backyard", "volume_gal": 21000})
    assert r.status_code == 201
    pool = r.json()
    assert pool["surface_type"] == "plaster" and pool["chlorine_source"] == "liquid"
    pid = pool["id"]

    assert len(client.get("/api/pools").json()) == 1

    r = client.patch(f"/api/pools/{pid}", json={"volume_gal": 22000})
    assert r.json()["volume_gal"] == 22000

    detail = client.get(f"/api/pools/{pid}").json()
    assert detail["pool"]["name"] == "Backyard"
    assert detail["latest_test"] is None and detail["targets"] is None

    assert client.delete(f"/api/pools/{pid}").status_code == 204
    assert client.get(f"/api/pools/{pid}").status_code == 404


def test_targets_endpoint(client):
    r = client.post("/api/chem/targets", json={"cya": 50, "chlorine_source": "liquid"})
    body = r.json()
    assert body["min_fc"] == 4 and body["target_fc_high"] == 8 and body["slam_fc"] == 20


def test_csi_endpoint(client):
    r = client.post("/api/chem/csi", json={
        "ph": 7.5, "temperature_f": 80, "calcium_hardness": 350,
        "total_alkalinity": 70, "cyanuric_acid": 50,
    })
    body = r.json()
    assert body["status"] == "ideal" and -0.2 <= body["csi"] <= 0.05


def test_volume_endpoint(client):
    r = client.post("/api/chem/volume", json={
        "shape": "rectangular", "length_ft": 32, "width_ft": 16, "avg_depth_ft": 5.5,
    })
    assert r.json()["gallons"] == pytest.approx(21000, rel=0.03)


def test_dose_endpoint_chlorine(client):
    r = client.post("/api/chem/dose", json={
        "parameter": "fc", "chemical": "liquid_chlorine", "current": 3, "goal": 7,
        "volume_gal": 20000, "strength": "12.5",
    })
    body = r.json()
    # 4 ppm * 2 (per 10k) * 10.7 = ~85.6 fl oz
    assert body["unit"] == "fl_oz" and body["amount"] == pytest.approx(85.6, abs=1.0)


def test_dose_ph_requires_ta(client):
    r = client.post("/api/chem/dose", json={
        "parameter": "ph", "chemical": "muriatic_acid", "current": 8.0, "goal": 7.5,
        "volume_gal": 10000,
    })
    assert r.status_code == 422


def test_auth_guard(monkeypatch, client):
    from poolmath import config
    monkeypatch.setattr(config, "AUTH_TOKEN", "secret")
    assert client.get("/api/pools").status_code == 401
    assert client.get("/api/pools", headers={"X-Auth-Token": "secret"}).status_code == 200
