"""Quick (categorical color) tests: OCT 5-drop chlorine swatches + pH marks
matching the Taylor #5113 Pool & Spa Water Tests kit."""

import pytest
from sqlmodel import Session, create_engine
from sqlmodel.pool import StaticPool

from poolmath import models
from poolmath.db import _migrate_columns
from poolmath.models import FC_COLOR_STEPS, PH_QUICK_VALUES


def _make_pool(client, **kw) -> int:
    return client.post("/api/pools", json={"name": "P", "volume_gal": 10000, **kw}).json()["id"]


@pytest.mark.parametrize("color", list(FC_COLOR_STEPS))
def test_quick_fc_color_derives_lower_bound(client, color):
    """Each OCT swatch maps to its numeric lower bound ('none' -> 0.0)."""
    pid = _make_pool(client)
    body = client.post(f"/api/pools/{pid}/tests", json={
        "test_type": "quick", "fc_color": color,
    }).json()
    assert body["test"]["fc"] == pytest.approx(FC_COLOR_STEPS[color])
    assert body["test"]["fc_color"] == color  # raw category kept for the UI
    assert body["test"]["test_type"] == "quick"
    assert body["test"]["is_approx"] is True


def test_quick_none_triggers_add_chlorine_recommendation(client):
    """fc_color 'none' -> fc 0 -> the FC-below-minimum dose fires, no CYA needed."""
    pid = _make_pool(client)
    body = client.post(f"/api/pools/{pid}/tests", json={
        "test_type": "quick", "fc_color": "none",
    }).json()
    assert body["test"]["fc"] == 0.0
    rec = body["recommendation"]
    assert rec is not None
    assert rec["level"] == "danger"
    assert "BELOW minimum" in rec["message"] and "12.5%" in rec["message"]
    # 10k gal, 0 -> 1 ppm of 12.5% = 10.7 fl oz (TFP constant).
    assert rec["dose"]["amount"] == pytest.approx(10.7, abs=0.1)
    assert rec["dose"]["unit"] == "fl_oz"


def test_quick_with_cya_uses_cya_targets(client):
    """When CYA *is* provided, the normal CYA-based recommendation wins."""
    pid = _make_pool(client)
    body = client.post(f"/api/pools/{pid}/tests", json={
        "test_type": "quick", "fc_color": "1", "cya": 50,
    }).json()
    assert body["test"]["fc"] == 1.0
    rec = body["recommendation"]
    assert rec["level"] == "danger"  # 1 < min 4 at CYA 50
    assert body["targets"]["min_fc"] == 4


def test_quick_mid_scale_no_recommendation_without_cya(client):
    """FC >= 1.0 with no CYA: nothing to recommend (no targets), no crash."""
    pid = _make_pool(client)
    body = client.post(f"/api/pools/{pid}/tests", json={
        "test_type": "quick", "fc_color": "5",
    }).json()
    assert body["test"]["fc"] == 5.0
    assert body["recommendation"] is None
    assert body["targets"] is None


def test_quick_ph_chip_derives_numeric_ph(client):
    pid = _make_pool(client)
    body = client.post(f"/api/pools/{pid}/tests", json={
        "test_type": "quick", "ph_quick": "7.5",
    }).json()
    assert body["test"]["ph"] == 7.5
    assert body["test"]["ph_quick"] == "7.5"
    assert body["test"]["is_approx"] is True


@pytest.mark.parametrize("ph", PH_QUICK_VALUES)
def test_quick_ph_values_accepted(client, ph):
    pid = _make_pool(client)
    assert client.post(f"/api/pools/{pid}/tests", json={
        "test_type": "quick", "ph_quick": ph,
    }).status_code == 201


def test_explicit_fc_wins_over_fc_color(client):
    """If both are given, the precise reading is the number; color is metadata."""
    pid = _make_pool(client)
    body = client.post(f"/api/pools/{pid}/tests", json={
        "test_type": "full", "fc": 4.2, "fc_color": "5",
    }).json()
    assert body["test"]["fc"] == 4.2
    assert body["test"]["is_approx"] is True  # a color reading is approximate


@pytest.mark.parametrize("bad", [
    {"test_type": "quick", "fc_color": "purple"},
    {"test_type": "quick", "ph_quick": "7.1"},
    {"test_type": "sometimes"},
])
def test_invalid_quick_values_rejected(client, bad):
    pid = _make_pool(client)
    assert client.post(f"/api/pools/{pid}/tests", json=bad).status_code == 422


def test_full_tests_unaffected_regression(client):
    """Full 7-way logging behaves exactly as before and marks is_approx False."""
    pid = _make_pool(client)
    body = client.post(f"/api/pools/{pid}/tests", json={
        "fc": 3, "cc": 0, "ph": 7.6, "ta": 70, "ch": 350, "cya": 50, "water_temp_f": 82,
    }).json()
    t = body["test"]
    assert t["test_type"] == "full" and t["fc_color"] is None and t["ph_quick"] is None
    assert t["is_approx"] is False
    assert t["csi"] is not None
    assert body["recommendation"]["level"] == "danger"  # FC 3 < min 4


def test_startup_migration_adds_columns_to_old_db():
    """A DB from before quick tests (no test_type/fc_color/ph_quick columns) must
    survive startup: create_all leaves it alone, the guard ALTERs in the columns."""
    old_ddl = """
    CREATE TABLE pool (id INTEGER PRIMARY KEY, name VARCHAR NOT NULL,
        volume_gal FLOAT NOT NULL, surface_type VARCHAR NOT NULL,
        chlorine_source VARCHAR NOT NULL, uses_salt BOOLEAN NOT NULL,
        uses_borates BOOLEAN NOT NULL, created_at DATETIME NOT NULL);
    CREATE TABLE testlog (id INTEGER PRIMARY KEY, pool_id INTEGER NOT NULL,
        taken_at DATETIME NOT NULL, fc FLOAT, cc FLOAT, ph FLOAT, ta FLOAT,
        ch FLOAT, cya FLOAT, salt FLOAT, borate FLOAT, water_temp_f FLOAT,
        tds FLOAT, csi FLOAT, notes VARCHAR);
    """
    eng = create_engine("sqlite://", connect_args={"check_same_thread": False},
                        poolclass=StaticPool)
    with eng.begin() as conn:
        for stmt in old_ddl.split(";"):
            if stmt.strip():
                conn.exec_driver_sql(stmt)
    # Patch db.engine for the migration, then run what init_db() runs.
    from poolmath import db as dbmod
    saved = dbmod.engine
    dbmod.engine = eng
    try:
        models.SQLModel.metadata.create_all(eng)
        _migrate_columns()
    finally:
        dbmod.engine = saved
    with eng.connect() as c:
        cols = {r[1] for r in c.exec_driver_sql("PRAGMA table_info(testlog)")}
    assert {"test_type", "fc_color", "ph_quick"} <= cols
    # An insert with the new columns now works.
    with Session(eng) as s:
        s.add(models.Pool(name="P", volume_gal=100, created_at=models.utcnow()))
        s.flush()
        s.add(models.TestLog(pool_id=1, fc=2.0, test_type="quick", fc_color="2"))
        s.commit()


def test_is_approx_in_listed_tests(client):
    pid = _make_pool(client)
    client.post(f"/api/pools/{pid}/tests", json={"test_type": "quick", "fc_color": "2"})
    client.post(f"/api/pools/{pid}/tests", json={"fc": 6})
    rows = client.get(f"/api/pools/{pid}/tests").json()
    assert [r["is_approx"] for r in rows] == [True, False]
    assert rows[0]["fc"] == 2.0
