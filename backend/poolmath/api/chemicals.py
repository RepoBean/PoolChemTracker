"""Chemical inventory CRUD (for consumption/cost tracking)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from ..db import get_session
from ..models import Chemical, ChemicalCreate, ChemicalUpdate, Pool

router = APIRouter(prefix="/api/pools", tags=["inventory"])


def _get_pool(pool_id: int, session: Session) -> Pool:
    pool = session.get(Pool, pool_id)
    if not pool:
        raise HTTPException(404, "pool not found")
    return pool


@router.get("/{pool_id}/chemicals")
def list_chemicals(pool_id: int, session: Session = Depends(get_session)):
    _get_pool(pool_id, session)
    return session.exec(select(Chemical).where(Chemical.pool_id == pool_id)).all()


@router.post("/{pool_id}/chemicals", status_code=201)
def create_chemical(pool_id: int, body: ChemicalCreate, session: Session = Depends(get_session)):
    _get_pool(pool_id, session)
    item = Chemical(pool_id=pool_id, **body.model_dump())
    session.add(item)
    session.commit()
    session.refresh(item)
    return item


def _get_item(pool_id: int, chem_id: int, session: Session) -> Chemical:
    item = session.get(Chemical, chem_id)
    if not item or item.pool_id != pool_id:
        raise HTTPException(404, "chemical not found")
    return item


@router.patch("/{pool_id}/chemicals/{chem_id}")
def update_chemical(pool_id: int, chem_id: int, body: ChemicalUpdate,
                    session: Session = Depends(get_session)):
    item = _get_item(pool_id, chem_id, session)
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(item, k, v)
    session.add(item)
    session.commit()
    session.refresh(item)
    return item


@router.delete("/{pool_id}/chemicals/{chem_id}", status_code=204)
def delete_chemical(pool_id: int, chem_id: int, session: Session = Depends(get_session)):
    item = _get_item(pool_id, chem_id, session)
    session.delete(item)
    session.commit()
