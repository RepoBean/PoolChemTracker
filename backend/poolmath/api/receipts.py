"""Receipt ingestion via a *local* vision model (Ollama /api/chat).

Flow: POST a receipt photo -> a DRAFT parse (nothing written to the DB).
The frontend shows it for review/edit; POST /confirm merges the items into
inventory and persists a ReceiptLog (and the image, if supplied).

Opt-in and cloud-free: with POOLMATH_VLM_URL unset the scan endpoint 503s and
GET /api/ai/status reports disabled, so the rest of the app is unaffected.
The VLM call uses stdlib urllib — no new runtime dependency.
"""

from __future__ import annotations

import base64
import json
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlmodel import Session, select

from .. import config
from ..db import get_session
from ..models import (
    Chemical, Pool, ReceiptItem, ReceiptLog, utcnow,
)
from ..units import is_dry, normalize_unit

router = APIRouter(prefix="/api/pools", tags=["receipts"])
ai_router = APIRouter(prefix="/api/ai", tags=["ai"])

MAX_UPLOAD_BYTES = 10 * 1024 * 1024
_ALLOWED_EXT = {".jpg", ".jpeg", ".png", ".webp"}

_VLM_PROMPT = (
    "Parse this pool-chemical store receipt. For each chemical line item extract: "
    "name (product name), strength if printed (e.g. '12.5%'), package_qty (the "
    "numeric quantity of one package, e.g. 2.5), unit (e.g. 'gallons', 'lbs', 'oz'), "
    "and price in USD. Ignore non-chemical line items (tools, brushes, bags, liners) "
    "and tax/grand-total lines. Output null rather than guess for anything "
    "unreadable. Normalize units to: gal, quart, fl_oz, l, ml, lb, oz_wt, kg, g — "
    "use weight units (oz_wt, lb) for dry/powder chemicals and volume units "
    "(fl_oz, gal) for liquids."
)


def vlm_configured() -> bool:
    return config.VLM_URL is not None


def _call_vlm(image_bytes: bytes) -> dict:
    """Ollama /api/chat: image base64 in messages[0].images, and `format` set to a
    JSON schema so the reply parses as the item list. stdlib urllib only."""
    assert config.VLM_URL is not None
    payload = {
        "model": config.VLM_MODEL,
        "stream": False,
        "format": {
            "type": "object",
            "properties": {
                "items": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": ["string", "null"]},
                            "strength": {"type": ["string", "null"]},
                            "package_qty": {"type": ["number", "null"]},
                            "unit": {"type": ["string", "null"]},
                            "price": {"type": ["number", "null"]},
                        },
                        "required": ["name"],
                    },
                },
                "total": {"type": ["number", "null"]},
            },
            "required": ["items"],
        },
        "messages": [{
            "role": "user",
            "content": _VLM_PROMPT,
            "images": [base64.b64encode(image_bytes).decode("ascii")],
        }],
    }
    req = urllib.request.Request(
        config.VLM_URL.rstrip("/") + "/api/chat",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=300) as resp:
        body = json.loads(resp.read())
    return json.loads(body["message"]["content"])


def _get_pool(pool_id: int, session: Session) -> Pool:
    pool = session.get(Pool, pool_id)
    if not pool:
        raise HTTPException(404, "pool not found")
    return pool


# --- draft parse -----------------------------------------------------------
@router.post("/{pool_id}/receipts")
def scan_receipt(pool_id: int, file: UploadFile = File(...),
                 session: Session = Depends(get_session)):
    _get_pool(pool_id, session)
    if not vlm_configured():
        raise HTTPException(
            503,
            "Receipt scanning needs a local vision model. Set POOLMATH_VLM_URL to "
            "an Ollama instance (e.g. http://192.168.123.81:11434) and "
            "POOLMATH_VLM_MODEL to a vision model, then restart.",
        )
    ext = Path(file.filename or "").suffix.lower()
    if ext not in _ALLOWED_EXT:
        raise HTTPException(422, "image must be .jpg, .jpeg, .png or .webp")
    data = file.file.read(MAX_UPLOAD_BYTES + 1)
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(413, "image too large (max 10 MB)")

    try:
        raw = _call_vlm(data)
    except (urllib.error.URLError, urllib.error.HTTPError, KeyError,
            ValueError, OSError) as e:
        raise HTTPException(502, f"vision model request failed: {e}")

    items: list[ReceiptItem] = []
    for r in raw.get("items") or []:
        if not isinstance(r, dict):
            continue
        name = str(r.get("name") or "").strip()
        if not name:
            continue
        strength = r.get("strength")
        unit_raw = r.get("unit")
        unit = normalize_unit(str(unit_raw) if unit_raw is not None else None,
                              dry=is_dry(name)) or (str(unit_raw) if unit_raw else "fl_oz")
        items.append(ReceiptItem(
            name=name,
            strength=str(strength).strip() if strength is not None else None,
            package_qty=r.get("package_qty"),
            unit=unit,
            price=r.get("price"),
        ))
    return {"items": items, "total": raw.get("total"), "raw": json.dumps(raw)}


# --- confirm (merge into inventory) ----------------------------------------
def _norm(s: str) -> str:
    """Case-insensitive, whitespace-collapsed comparison key for names/strengths."""
    return " ".join(s.lower().split())


def _match_chemical(pool_id: int, it: ReceiptItem, session: Session) -> Optional[Chemical]:
    """Whitespace/case-insensitive name match; if the item has a strength, it must
    match too (a 12.5% jug is not a 6% jug)."""
    wanted = _norm(it.name)
    want_strength = _norm(it.strength) if it.strength else None
    for c in session.exec(select(Chemical).where(Chemical.pool_id == pool_id)).all():
        if _norm(c.name) != wanted:
            continue
        if want_strength is not None and _norm(c.strength or "") != want_strength:
            continue
        return c
    return None


def _store_image(image: UploadFile) -> Optional[str]:
    """Persist under <DB dir>/receipts/<utc-timestamp><ext>; skip on bad input."""
    ext = Path(image.filename or "").suffix.lower()
    if ext not in _ALLOWED_EXT:
        return None
    data = image.file.read(MAX_UPLOAD_BYTES + 1)
    if len(data) > MAX_UPLOAD_BYTES:
        return None
    directory = Path(config.DB_PATH).parent / "receipts"
    directory.mkdir(parents=True, exist_ok=True)
    dest = directory / f"{utcnow().strftime('%Y%m%dT%H%M%S%f')}{ext}"
    dest.write_bytes(data)
    return str(dest)


@router.post("/{pool_id}/receipts/confirm", status_code=201)
def confirm_receipt(
    pool_id: int,
    items: str = Form(...),
    received_at: Optional[str] = Form(None),
    image: Optional[UploadFile] = File(None),
    session: Session = Depends(get_session),
):
    _get_pool(pool_id, session)
    try:
        parsed = [ReceiptItem.model_validate(x) for x in json.loads(items)]
    except (ValueError, TypeError) as e:
        raise HTTPException(422, f"invalid items: {e}")
    if not parsed:
        raise HTTPException(422, "confirm at least one item")
    for it in parsed:
        if it.package_qty is None or it.package_qty <= 0:
            raise HTTPException(422, f"'{it.name}': package_qty must be a positive number")

    when = utcnow()
    if received_at:
        try:
            when = datetime.fromisoformat(received_at)
        except ValueError:
            raise HTTPException(422, "received_at must be ISO 8601")
        if when.tzinfo is None:  # store tz-aware like everything else
            when = when.replace(tzinfo=timezone.utc)

    image_path = _store_image(image) if image is not None else None

    merged = []
    for it in parsed:
        chem_item = _match_chemical(pool_id, it, session)
        created = False
        if chem_item is None:
            chem_item = Chemical(pool_id=pool_id, name=it.name, strength=it.strength,
                                 unit=it.unit, qty_on_hand=0.0, cost_per_unit=None)
            created = True
        else:
            # Backfill strength we hadn't recorded before.
            if it.strength and not chem_item.strength:
                chem_item.strength = it.strength
        chem_item.qty_on_hand = round(chem_item.qty_on_hand + it.package_qty, 4)
        if it.price is not None:
            chem_item.cost_per_unit = round(it.price / it.package_qty, 4)
        session.add(chem_item)
        merged.append({
            "name": chem_item.name, "created": created,
            "qty_on_hand": chem_item.qty_on_hand, "cost_per_unit": chem_item.cost_per_unit,
        })

    log = ReceiptLog(
        pool_id=pool_id, received_at=when, image=image_path,
        items_json=json.dumps([i.model_dump() for i in parsed]),
        total_cost=round(sum(i.price or 0.0 for i in parsed), 2),
    )
    session.add(log)
    session.commit()
    session.refresh(log)
    return {"receipt": log, "items": merged}


@router.get("/{pool_id}/receipts")
def list_receipts(pool_id: int, limit: int = 20,
                  session: Session = Depends(get_session)):
    _get_pool(pool_id, session)
    return session.exec(
        select(ReceiptLog)
        .where(ReceiptLog.pool_id == pool_id)
        .order_by(ReceiptLog.received_at.desc())
        .limit(limit)
    ).all()


# --- lightweight capability probe (frontend hides the button when disabled) --
@ai_router.get("/status")
def ai_status():
    return {"enabled": vlm_configured(),
            "model": config.VLM_MODEL if vlm_configured() else None}
