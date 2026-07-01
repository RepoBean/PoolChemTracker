"""Tests for test-logging, dose-logging, inventory, and consumption."""

import pytest


def _make_pool(client, **kw) -> int:
    body = {"name": "P", "volume_gal": 10000, **kw}
    return client.post("/api/pools", json=body).json()["id"]


def test_log_test_computes_csi_and_targets(client):
    pid = _make_pool(client, chlorine_source="liquid")
    r = client.post(f"/api/pools/{pid}/tests", json={
        "fc": 3, "cc": 0, "ph": 7.6, "ta": 70, "ch": 350, "cya": 50, "water_temp_f": 82,
    })
    assert r.status_code == 201
    body = r.json()
    assert body["test"]["csi"] is not None
    assert isinstance(body["csi_status"], str)
    assert body["targets"]["target_fc_low"] == 6 and body["targets"]["slam_fc"] == 20
    # FC 3 is below min (4) -> danger, with a chlorine dose suggestion.
    assert body["recommendation"]["level"] == "danger"
    assert body["recommendation"]["dose"]["unit"] == "fl_oz"


def test_log_test_no_csi_when_incomplete(client):
    pid = _make_pool(client)
    body = client.post(f"/api/pools/{pid}/tests", json={"fc": 5, "ph": 7.5}).json()
    assert body["test"]["csi"] is None and body["recommendation"] is None


def test_test_history_ordered(client):
    pid = _make_pool(client)
    for fc in (4, 5, 6):
        client.post(f"/api/pools/{pid}/tests", json={"fc": fc, "ph": 7.5})
    rows = client.get(f"/api/pools/{pid}/tests").json()
    assert [r["fc"] for r in rows] == [4, 5, 6]


def test_inventory_dose_decrement_and_cost(client):
    pid = _make_pool(client)
    inv = client.post(f"/api/pools/{pid}/chemicals", json={
        "name": "12.5% liquid chlorine", "unit": "fl_oz", "qty_on_hand": 128, "cost_per_unit": 0.05,
    }).json()
    dose = client.post(f"/api/pools/{pid}/doses", json={
        "chemical": "12.5% liquid chlorine", "amount": 32, "unit": "fl_oz",
        "parameter_targeted": "fc", "chemical_id": inv["id"],
    }).json()
    assert dose["cost"] == pytest.approx(1.6)  # 32 * 0.05, derived from inventory
    assert client.get(f"/api/pools/{pid}/chemicals").json()[0]["qty_on_hand"] == 96


def test_consumption_summary(client):
    pid = _make_pool(client)
    client.post(f"/api/pools/{pid}/doses", json={"chemical": "acid", "amount": 16, "unit": "fl_oz", "cost": 2.0})
    client.post(f"/api/pools/{pid}/doses", json={"chemical": "acid", "amount": 8, "unit": "fl_oz", "cost": 1.0})
    client.post(f"/api/pools/{pid}/doses", json={"chemical": "bleach", "amount": 100, "unit": "fl_oz", "cost": 5.0})
    summary = client.get(f"/api/pools/{pid}/consumption").json()
    assert summary["total_cost"] == pytest.approx(8.0)
    acid = next(i for i in summary["items"] if i["chemical"] == "acid")
    assert acid["total_amount"] == 24 and acid["count"] == 2
