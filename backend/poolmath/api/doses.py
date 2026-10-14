"""Dose logging + consumption/cost summary."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from ..db import get_session
from ..models import Chemical, DoseLog, DoseLogCreate, Pool
from ..units import convert

router = APIRouter(prefix="/api/pools", tags=["doses"])


def _get_pool(pool_id: int, session: Session) -> Pool:
    pool = session.get(Pool, pool_id)
    if not pool:
        raise HTTPException(404, "pool not found")
    return pool


@router.post("/{pool_id}/doses", status_code=201)
def create_dose(pool_id: int, body: DoseLogCreate, session: Session = Depends(get_session)):
    _get_pool(pool_id, session)
    dose = DoseLog(pool_id=pool_id, **body.model_dump(exclude={"applied_at", "chemical_id"}))
    if body.applied_at:
        dose.applied_at = body.applied_at

    # Optionally draw down inventory and derive cost. The dose and the inventory
    # item may use different units (dose in fl oz, jug tracked in gal), so convert
    # into the item's unit before decrementing and pricing.
    if body.chemical_id is not None:
        item = session.get(Chemical, body.chemical_id)
        if not item or item.pool_id != pool_id:
            raise HTTPException(404, "chemical (inventory item) not found")
        # Prefer the inventory item's canonical name/strength so free-text
        # variants stop fragmenting consumption totals. (Free-text doses with no
        # chemical_id keep whatever was typed.)
        dose.chemical = item.name
        if item.strength:
            dose.strength = item.strength
        used = convert(body.amount, body.unit, item.unit)
        if used is None:
            raise HTTPException(
                422,
                f"dose is in {body.unit} but '{item.name}' is tracked in {item.unit}; "
                "those units aren't compatible",
            )
        item.qty_on_hand = max(0.0, item.qty_on_hand - used)
        if dose.cost is None and item.cost_per_unit is not None:
            dose.cost = round(used * item.cost_per_unit, 2)
        session.add(item)

    session.add(dose)
    session.commit()
    session.refresh(dose)
    return dose


@router.get("/{pool_id}/doses")
def list_doses(
    pool_id: int,
    start: Optional[datetime] = None,
    end: Optional[datetime] = None,
    session: Session = Depends(get_session),
):
    _get_pool(pool_id, session)
    q = select(DoseLog).where(DoseLog.pool_id == pool_id)
    if start:
        q = q.where(DoseLog.applied_at >= start)
    if end:
        q = q.where(DoseLog.applied_at <= end)
    return session.exec(q.order_by(DoseLog.applied_at)).all()


@router.get("/{pool_id}/consumption")
def consumption(
    pool_id: int,
    start: Optional[datetime] = None,
    end: Optional[datetime] = None,
    session: Session = Depends(get_session),
):
    _get_pool(pool_id, session)
    q = select(DoseLog).where(DoseLog.pool_id == pool_id)
    if start:
        q = q.where(DoseLog.applied_at >= start)
    if end:
        q = q.where(DoseLog.applied_at <= end)
    rows = session.exec(q).all()

    # One row per chemical, in a single base unit. Group by normalized name
    # (case/whitespace-insensitive) so "acid", "Acid" and "ac id " variants
    # don't fragment; the base unit is the inventory item's unit when one
    # matches, else the unit of the highest-cost dose in the window.
    inventory = {" ".join(c.name.lower().split()): c
                 for c in session.exec(select(Chemical).where(Chemical.pool_id == pool_id)).all()}
    groups: dict[str, list[DoseLog]] = {}
    for d in rows:
        groups.setdefault(" ".join(d.chemical.lower().split()), []).append(d)

    items = []
    for key, group in groups.items():
        inv = inventory.get(key)
        if inv is not None:
            name, base = inv.name, inv.unit
        else:
            name = group[0].chemical
            base = max(group, key=lambda d: d.cost or 0.0).unit
        total = 0.0
        for d in group:
            converted = convert(d.amount, d.unit, base)
            if converted is not None:  # incompatible dimensions: count, don't sum
                total += converted
        items.append({
            "chemical": name, "unit": base,
            "total_amount": round(total, 2),
            "total_cost": round(sum(d.cost or 0.0 for d in group), 2),
            "count": len(group),
        })
    items.sort(key=lambda a: a["total_cost"], reverse=True)
    return {"items": items, "total_cost": round(sum(a["total_cost"] for a in items), 2)}
