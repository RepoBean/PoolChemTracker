"""Pool CRUD + detail (latest test, targets, CSI status)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from .. import chemistry as chem
from ..db import get_session
from ..models import Pool, PoolCreate, PoolUpdate, TestLog

router = APIRouter(prefix="/api/pools", tags=["pools"])


@router.get("")
def list_pools(session: Session = Depends(get_session)):
    return session.exec(select(Pool).order_by(Pool.created_at)).all()


@router.post("", status_code=201)
def create_pool(body: PoolCreate, session: Session = Depends(get_session)):
    pool = Pool(**body.model_dump())
    session.add(pool)
    session.commit()
    session.refresh(pool)
    return pool


def _get_pool(pool_id: int, session: Session) -> Pool:
    pool = session.get(Pool, pool_id)
    if not pool:
        raise HTTPException(404, "pool not found")
    return pool


@router.get("/{pool_id}")
def pool_detail(pool_id: int, session: Session = Depends(get_session)):
    pool = _get_pool(pool_id, session)
    latest = session.exec(
        select(TestLog).where(TestLog.pool_id == pool_id).order_by(TestLog.taken_at.desc())
    ).first()

    targets = None
    csi_status = None
    if latest and latest.cya is not None:
        targets = chem.fc_cya_targets(latest.cya, pool.chlorine_source)  # type: ignore[arg-type]
    if latest and latest.csi is not None:
        csi_status = chem.csi_status(latest.csi)

    return {"pool": pool, "latest_test": latest, "targets": targets, "csi_status": csi_status}


@router.patch("/{pool_id}")
def update_pool(pool_id: int, body: PoolUpdate, session: Session = Depends(get_session)):
    pool = _get_pool(pool_id, session)
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(pool, k, v)
    session.add(pool)
    session.commit()
    session.refresh(pool)
    return pool


@router.delete("/{pool_id}", status_code=204)
def delete_pool(pool_id: int, session: Session = Depends(get_session)):
    pool = _get_pool(pool_id, session)
    session.delete(pool)
    session.commit()
