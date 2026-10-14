"""Test-log endpoints: log a reading (server computes CSI + targets + next action)."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from .. import chemistry as chem
from .. import tfp_data as tfp
from ..db import get_session
from ..models import FC_COLOR_STEPS, Pool, TestLog, TestLogCreate

router = APIRouter(prefix="/api/pools", tags=["tests"])


def _compute_csi(t: TestLog) -> Optional[float]:
    if None in (t.ph, t.water_temp_f, t.ch, t.ta):
        return None
    return chem.csi(
        ph=t.ph, temperature_f=t.water_temp_f, calcium_hardness=t.ch,
        total_alkalinity=t.ta, cyanuric_acid=t.cya or 0.0,
        salt=t.salt or 0.0, borates=t.borate or 0.0,
    )


def _recommendation(t: TestLog, pool: Pool, targets) -> Optional[dict]:
    if t.cc is not None and t.cc > 0.5:
        return {"level": "warn", "message": "CC > 0.5 — investigate; SLAM if algae or FC lost overnight."}
    if t.fc is None or targets is None:
        # Quick tests skip CYA (and CH/TA/temp — those only gate CSI), so there
        # are no CYA-derived targets. Fall back to TFP's universal "FC ≥ 1.0"
        # rule so a no-color OCT result still gets a chlorine dose, not silence.
        if (t.test_type == "quick" and t.fc is not None
                and t.fc < tfp.MIN_FC_NO_CYA):
            dose = chem.dose_fc_liquid_chlorine(tfp.MIN_FC_NO_CYA - t.fc, pool.volume_gal, 12.5)
            return {"level": "danger",
                    "message": f"FC {t.fc} is BELOW minimum ({tfp.MIN_FC_NO_CYA:g}). "
                               f"Add ~{dose.amount} {dose.unit} of 12.5% liquid chlorine.",
                    "dose": dose}
        return None
    if t.fc < targets.min_fc:
        goal = (targets.target_fc_low + targets.target_fc_high) / 2
        dose = chem.dose_fc_liquid_chlorine(goal - t.fc, pool.volume_gal, 12.5)
        return {"level": "danger",
                "message": f"FC {t.fc} is BELOW minimum ({targets.min_fc}). Add ~{dose.amount} {dose.unit} "
                           f"of 12.5% liquid chlorine to reach {round(goal, 1)}.",
                "dose": dose}
    if t.fc < targets.target_fc_low:
        goal = (targets.target_fc_low + targets.target_fc_high) / 2
        dose = chem.dose_fc_liquid_chlorine(goal - t.fc, pool.volume_gal, 12.5)
        return {"level": "info",
                "message": f"FC {t.fc} is below target. Add ~{dose.amount} {dose.unit} of 12.5% "
                           f"liquid chlorine to reach {round(goal, 1)}.",
                "dose": dose}
    return {"level": "ok", "message": f"FC {t.fc} is in the target range ({targets.target_fc_low}"
                                      f"–{targets.target_fc_high})."}


def _get_pool(pool_id: int, session: Session) -> Pool:
    pool = session.get(Pool, pool_id)
    if not pool:
        raise HTTPException(404, "pool not found")
    return pool


@router.post("/{pool_id}/tests", status_code=201)
def create_test(pool_id: int, body: TestLogCreate, session: Session = Depends(get_session)):
    pool = _get_pool(pool_id, session)
    fields = body.model_dump(exclude={"taken_at"})
    test = TestLog(pool_id=pool_id, **fields)
    if body.taken_at:
        test.taken_at = body.taken_at
    # Quick tests record a color, not a number. Derive chartable values from
    # the OCT swatch step (lower bound) / pH mark so trends can plot them;
    # both the raw category and the derived number are kept.
    if test.fc is None and test.fc_color is not None:
        test.fc = FC_COLOR_STEPS[test.fc_color]
    if test.ph is None and test.ph_quick is not None:
        test.ph = float(test.ph_quick)
    test.csi = _compute_csi(test)
    session.add(test)
    session.commit()
    session.refresh(test)

    targets = chem.fc_cya_targets(test.cya, pool.chlorine_source) if test.cya is not None else None
    return {
        "test": test,
        "targets": targets,
        "csi_status": chem.csi_status(test.csi) if test.csi is not None else None,
        "recommendation": _recommendation(test, pool, targets),
    }


@router.get("/{pool_id}/tests")
def list_tests(
    pool_id: int,
    start: Optional[datetime] = None,
    end: Optional[datetime] = None,
    limit: int = 500,
    session: Session = Depends(get_session),
):
    _get_pool(pool_id, session)
    q = select(TestLog).where(TestLog.pool_id == pool_id)
    if start:
        q = q.where(TestLog.taken_at >= start)
    if end:
        q = q.where(TestLog.taken_at <= end)
    rows = session.exec(q.order_by(TestLog.taken_at)).all()
    return rows[-limit:] if limit else rows
