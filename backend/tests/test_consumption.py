"""Endpoint tests for /doses (canonical naming) and /consumption (unit merging).

Inventory decrement, unit conversion and the 422 incompatible-units path were
already covered in test_logs.py; this file adds what Task 3 changed.
"""

import pytest


def _make_pool(client, **kw) -> int:
    return client.post("/api/pools", json={"name": "P", "volume_gal": 10000, **kw}).json()["id"]


def _dose(client, pid, **kw):
    body = {"chemical": "x", "amount": 1, "unit": "fl_oz", **kw}
    r = client.post(f"/api/pools/{pid}/doses", json=body)
    assert r.status_code == 201, r.text
    return r.json()


# --- /doses: canonical name/strength from the inventory item ----------------
def test_dose_uses_canonical_name_when_chemical_id_given(client):
    pid = _make_pool(client)
    inv = client.post(f"/api/pools/{pid}/chemicals", json={
        "name": "12.5% Liquid Chlorine", "strength": "12.5%", "unit": "gal",
        "qty_on_hand": 2.5, "cost_per_unit": 4.0,
    }).json()
    dose = _dose(client, pid, chemical="liq chlor (store brand)", unit="gal",
                 amount=0.5, chemical_id=inv["id"])
    assert dose["chemical"] == "12.5% Liquid Chlorine"  # free text normalized
    assert dose["strength"] == "12.5%"
    # ...and still decrements/derives cost as before.
    assert dose["cost"] == pytest.approx(2.0)
    assert client.get(f"/api/pools/{pid}/chemicals").json()[0]["qty_on_hand"] == pytest.approx(2.0)


def test_dose_strength_only_overridden_when_item_has_one(client):
    pid = _make_pool(client)
    inv = client.post(f"/api/pools/{pid}/chemicals", json={
        "name": "Stabilizer", "unit": "lb", "qty_on_hand": 5,
    }).json()
    dose = _dose(client, pid, chemical="cya stuff", strength="granular",
                 amount=1, unit="lb", chemical_id=inv["id"])
    assert dose["chemical"] == "Stabilizer"
    assert dose["strength"] == "granular"  # item has no strength -> keep typed


def test_free_text_dose_without_chemical_id_unchanged(client):
    pid = _make_pool(client)
    client.post(f"/api/pools/{pid}/chemicals", json={
        "name": "Muriatic Acid", "unit": "gal", "qty_on_hand": 1,
    })
    dose = _dose(client, pid, chemical="muriatic  ACID", amount=0.5, unit="gal")
    assert dose["chemical"] == "muriatic  ACID"  # untouched without chemical_id


# --- /consumption: one row per chemical, single base unit --------------------
def test_consumption_merges_units_and_case_variants(client):
    pid = _make_pool(client)
    _dose(client, pid, chemical="acid", amount=16, unit="fl_oz", cost=2.0)
    _dose(client, pid, chemical="Acid", amount=1, unit="gal", cost=10.0)
    _dose(client, pid, chemical="ACID", amount=8, unit="fl_oz", cost=1.0)
    summary = client.get(f"/api/pools/{pid}/consumption").json()
    assert len(summary["items"]) == 1  # was three rows before the fix
    a = summary["items"][0]
    # No inventory item -> base unit = unit of the highest-cost dose (gal).
    assert a["unit"] == "gal"
    assert a["total_amount"] == pytest.approx(1.19)  # 1 + 0.125 + 0.0625, rounded to 2 dp
    assert a["total_cost"] == pytest.approx(13.0)
    assert a["count"] == 3


def test_consumption_uses_inventory_unit_when_item_exists(client):
    pid = _make_pool(client)
    client.post(f"/api/pools/{pid}/chemicals", json={
        "name": "Muriatic Acid", "unit": "fl_oz", "qty_on_hand": 32, "cost_per_unit": 0.05,
    })
    _dose(client, pid, chemical="muriatic acid", amount=1, unit="gal", cost=10.0)
    _dose(client, pid, chemical="MURIATIC  ACID", amount=16, unit="fl_oz", cost=1.0)
    summary = client.get(f"/api/pools/{pid}/consumption").json()
    a = summary["items"][0]
    assert a["chemical"] == "Muriatic Acid"  # canonical name from inventory
    assert a["unit"] == "fl_oz"
    assert a["total_amount"] == pytest.approx(128 + 16)
    assert a["count"] == 2


def test_consumption_date_filtering(client):
    pid = _make_pool(client)
    _dose(client, pid, chemical="acid", amount=1, unit="gal", cost=5.0,
          applied_at="2026-09-01T12:00:00+00:00")
    _dose(client, pid, chemical="acid", amount=2, unit="gal", cost=9.0,
          applied_at="2026-10-01T12:00:00+00:00")
    all_summary = client.get(f"/api/pools/{pid}/consumption").json()
    assert all_summary["items"][0]["count"] == 2
    oct_only = client.get(
        f"/api/pools/{pid}/consumption?start=2026-09-15T00:00:00Z").json()
    a = oct_only["items"][0]
    assert a["count"] == 1 and a["total_amount"] == pytest.approx(2)
    assert oct_only["total_cost"] == pytest.approx(9.0)
    before_sep = client.get(
        f"/api/pools/{pid}/consumption?end=2026-09-15T00:00:00Z").json()
    assert before_sep["total_cost"] == pytest.approx(5.0)


def test_consumption_incompatible_dimensions_counted_not_summed(client):
    pid = _make_pool(client)
    _dose(client, pid, chemical="weird", amount=1, unit="gal", cost=10.0)
    _dose(client, pid, chemical="weird", amount=2, unit="lb", cost=1.0)
    a = client.get(f"/api/pools/{pid}/consumption").json()["items"][0]
    assert a["count"] == 2
    assert a["total_cost"] == pytest.approx(11.0)
    assert a["total_amount"] == pytest.approx(1.0)  # the 2 lb can't become gallons
