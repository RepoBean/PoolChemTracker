"""Receipt ingestion: unit normalization, mock-VLM draft parse, confirm merge."""

import json
import pytest

from poolmath import config
from poolmath.api import receipts as receipts_api
from poolmath.units import normalize_unit

FAKE_JPG = b"\xff\xd8\xff\xd9"  # minimal JPEG-ish bytes; content is never decoded


def _make_pool(client, **kw) -> int:
    return client.post("/api/pools", json={"name": "P", "volume_gal": 10000, **kw}).json()["id"]


# --- unit normalization -----------------------------------------------------
@pytest.mark.parametrize("raw,expected", [
    ("gallons", "gal"), ("Gallon", "gal"), ("gal", "gal"),
    ("quarts", "quart"), ("fl oz", "fl_oz"), ("fl_oz", "fl_oz"),
    ("liters", "l"), ("ml", "ml"),
    ("lbs", "lb"), ("pound", "lb"), ("kg", "kg"), ("grams", "g"),
])
def test_normalize_unit_aliases(raw, expected):
    assert normalize_unit(raw) == expected


@pytest.mark.parametrize("name,expected", [
    ("Liquid Pool Chlorine", "fl_oz"),   # liquid: bare oz -> fluid
    ("Bleach", "fl_oz"),
    ("Cal-Hypo 73%", "oz_wt"),           # dry/powder: bare oz -> weight
    ("Sodium Biking Soda", "oz_wt"),
    ("Cyanuric Acid Stabilizer", "oz_wt"),
    ("Pool Salt", "oz_wt"),
])
def test_normalize_bare_oz_by_chemical_type(name, expected):
    from poolmath.units import is_dry
    assert normalize_unit("oz", dry=is_dry(name)) == expected


def test_normalize_unknown_unit_is_none():
    assert normalize_unit("barrels") is None
    assert normalize_unit(None) is None


# --- capability probe + 503 path --------------------------------------------
def test_ai_status_disabled_by_default(client):
    body = client.get("/api/ai/status").json()
    assert body == {"enabled": False, "model": None}


def test_scan_503_when_vlm_unset(client):
    pid = _make_pool(client)
    r = client.post(f"/api/pools/{pid}/receipts",
                    files={"file": ("r.jpg", FAKE_JPG, "image/jpeg")})
    assert r.status_code == 503
    assert "POOLMATH_VLM_URL" in r.json()["detail"]
    # Draft path must not have written anything.
    assert client.get(f"/api/pools/{pid}/receipts").json() == []


def test_ai_status_reflects_config(monkeypatch, client):
    monkeypatch.setattr(config, "VLM_URL", "http://ollama:11434")
    monkeypatch.setattr(config, "VLM_MODEL", "llama3.2-vision")
    body = client.get("/api/ai/status").json()
    assert body == {"enabled": True, "model": "llama3.2-vision"}


def test_scan_rejects_bad_extension(client, monkeypatch):
    monkeypatch.setattr(config, "VLM_URL", "http://ollama:11434")
    pid = _make_pool(client)
    r = client.post(f"/api/pools/{pid}/receipts",
                    files={"file": ("r.gif", b"gif", "image/gif")})
    assert r.status_code == 422


# --- draft parse (mocked VLM — no real model in tests) -----------------------
FAKE_PARSE = {
    "items": [
        {"name": "Liquid Pool Chlorine", "strength": "12.5%", "package_qty": 2.5,
         "unit": "gallons", "price": 10.99},
        {"name": "Cal-Hypo 73%", "strength": None, "package_qty": 8,
         "unit": "oz", "price": 3.49},
        # A nameless line: the endpoint must drop it. (Dropping non-chemicals
        # like towels is the model's job — the prompt instructs it — and the
        # review form is the human backstop.)
        {"name": None, "strength": None, "package_qty": 1, "unit": "lbs", "price": 9.99},
    ],
    "total": 39.47,
}


@pytest.fixture()
def vlm(client, monkeypatch, tmp_path):
    """Config points at a fake Ollama; the HTTP call is stubbed with canned JSON."""
    monkeypatch.setattr(config, "VLM_URL", "http://ollama.test:11434")
    monkeypatch.setattr(config, "VLM_MODEL", "llama3.2-vision")
    monkeypatch.setattr(config, "DB_PATH", str(tmp_path / "poolmath.db"))
    seen = {}

    def fake_call_vlm(image_bytes: bytes) -> dict:
        seen["image"] = image_bytes
        return FAKE_PARSE

    monkeypatch.setattr(receipts_api, "_call_vlm", fake_call_vlm)
    return seen


def test_scan_returns_draft_with_normalized_units(client, vlm):
    pid = _make_pool(client)
    r = client.post(f"/api/pools/{pid}/receipts",
                    files={"file": ("r.jpg", FAKE_JPG, "image/jpeg")})
    assert r.status_code == 200
    body = r.json()
    assert vlm["image"] == FAKE_JPG  # bytes actually reached the (stubbed) VLM
    items = body["items"]
    assert body["total"] == 39.47
    assert isinstance(body["raw"], str) and json.loads(body["raw"])["total"] == 39.47
    # Nameless junk is dropped; units normalized.
    assert [i["name"] for i in items] == ["Liquid Pool Chlorine", "Cal-Hypo 73%"]
    assert items[0]["unit"] == "gal"
    assert items[1]["unit"] == "oz_wt"  # bare oz on a dry chemical -> weight
    # Draft wrote nothing to inventory.
    assert client.get(f"/api/pools/{pid}/chemicals").json() == []


def test_scan_502_when_vlm_fails(client, monkeypatch):
    import urllib.error
    monkeypatch.setattr(config, "VLM_URL", "http://ollama.test:11434")

    def boom(_):
        raise urllib.error.URLError("connection refused")

    monkeypatch.setattr(receipts_api, "_call_vlm", boom)
    pid = _make_pool(client)
    r = client.post(f"/api/pools/{pid}/receipts",
                    files={"file": ("r.jpg", FAKE_JPG, "image/jpeg")})
    assert r.status_code == 502


# --- confirm: merge into inventory -------------------------------------------
def _confirm(client, pid, items, **kw):
    data = {"items": json.dumps(items)}
    data.update(kw)
    return client.post(f"/api/pools/{pid}/receipts/confirm", data=data)


def test_confirm_name_normalization_match_updates_qty_and_cost(client):
    pid = _make_pool(client)
    client.post(f"/api/pools/{pid}/chemicals", json={
        "name": "12.5% Liquid Chlorine", "strength": "12.5%", "unit": "gal",
        "qty_on_hand": 2.5, "cost_per_unit": 4.0,
    })
    r = _confirm(client, pid, [{
        "name": "  12.5%   liquid  chlorine", "strength": "12.5%",
        "package_qty": 2.5, "unit": "gal", "price": 11.25,
    }])
    assert r.status_code == 201
    assert r.json()["items"][0]["created"] is False
    inv = client.get(f"/api/pools/{pid}/chemicals").json()
    assert len(inv) == 1  # matched, not duplicated
    assert inv[0]["qty_on_hand"] == pytest.approx(5.0)
    assert inv[0]["cost_per_unit"] == pytest.approx(4.5)  # 11.25 / 2.5


def test_confirm_strength_mismatch_creates_new(client):
    pid = _make_pool(client)
    client.post(f"/api/pools/{pid}/chemicals", json={
        "name": "Liquid Chlorine", "strength": "12.5%", "unit": "gal",
        "qty_on_hand": 2.5, "cost_per_unit": 4.0,
    })
    r = _confirm(client, pid, [{
        "name": "liquid chlorine", "strength": "6%",
        "package_qty": 1, "unit": "gal", "price": 6.0,
    }])
    assert r.json()["items"][0]["created"] is True
    inv = client.get(f"/api/pools/{pid}/chemicals").json()
    assert len(inv) == 2


def test_confirm_no_match_creates_with_unit_and_cost(client):
    pid = _make_pool(client)
    r = _confirm(client, pid, [{
        "name": "Sodium Biking Soda", "strength": None,
        "package_qty": 3.75, "unit": "lb", "price": 12.90,
    }])
    assert r.json()["items"][0]["created"] is True
    inv = client.get(f"/api/pools/{pid}/chemicals").json()
    assert inv[0]["name"] == "Sodium Biking Soda"
    assert inv[0]["unit"] == "lb"
    assert inv[0]["qty_on_hand"] == pytest.approx(3.75)
    assert inv[0]["cost_per_unit"] == pytest.approx(12.90 / 3.75, abs=1e-4)


def test_confirm_persists_receipt_log(client):
    pid = _make_pool(client)
    _confirm(client, pid, [
        {"name": "A", "package_qty": 1, "unit": "gal", "price": 5.0},
        {"name": "B", "package_qty": 2, "unit": "lb", "price": 3.5},
    ], received_at="2026-10-12T18:30:00")
    logs = client.get(f"/api/pools/{pid}/receipts").json()
    assert len(logs) == 1
    assert logs[0]["item_count"] == 2
    assert logs[0]["total_cost"] == pytest.approx(8.5)
    assert logs[0]["received_at"].startswith("2026-10-12T18:30:00")
    assert logs[0]["image"] is None


def test_confirm_stores_image_only_on_confirm(client, vlm, tmp_path):
    pid = _make_pool(client)
    files = {"items": (None, json.dumps([
        {"name": "Liquid Chlorine", "package_qty": 2.5, "unit": "gal", "price": 10.0}
    ]))}
    r = client.post(f"/api/pools/{pid}/receipts/confirm",
                    data=files, files={"image": ("r.jpg", FAKE_JPG, "image/jpeg")})
    assert r.status_code == 201
    log = client.get(f"/api/pools/{pid}/receipts").json()[0]
    assert log["image"] is not None
    assert (tmp_path / "receipts").is_dir()
    stored = list((tmp_path / "receipts").glob("*.jpg"))
    assert len(stored) == 1 and stored[0].read_bytes() == FAKE_JPG


def test_confirm_rejects_bad_qty(client):
    pid = _make_pool(client)
    r = _confirm(client, pid, [{"name": "X", "package_qty": 0, "unit": "gal"}])
    assert r.status_code == 422
    assert client.get(f"/api/pools/{pid}/receipts").json() == []
