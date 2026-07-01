"""Stateless chemistry endpoints — thin wrappers over the chemistry service."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from .. import chemistry as chem

router = APIRouter(prefix="/api/chem", tags=["chemistry"])


class TargetsReq(BaseModel):
    cya: float
    chlorine_source: str = "liquid"


class CsiReq(BaseModel):
    ph: float
    temperature_f: float
    calcium_hardness: float
    total_alkalinity: float
    cyanuric_acid: float = 0.0
    salt: float = 0.0
    borates: float = 0.0


class VolumeReq(BaseModel):
    shape: str
    length_ft: float
    width_ft: float
    avg_depth_ft: float
    shallow_depth_ft: Optional[float] = None
    deep_depth_ft: Optional[float] = None


class DoseReq(BaseModel):
    parameter: str
    chemical: str = "default"
    current: float
    goal: float
    volume_gal: float
    strength: Optional[str] = None
    total_alkalinity: Optional[float] = None


@router.post("/targets")
def targets(req: TargetsReq):
    return chem.fc_cya_targets(req.cya, req.chlorine_source)  # type: ignore[arg-type]


@router.post("/csi")
def csi(req: CsiReq):
    value = chem.csi(
        ph=req.ph, temperature_f=req.temperature_f, calcium_hardness=req.calcium_hardness,
        total_alkalinity=req.total_alkalinity, cyanuric_acid=req.cyanuric_acid,
        salt=req.salt, borates=req.borates,
    )
    return {"csi": value, "status": chem.csi_status(value)}


@router.post("/volume")
def volume(req: VolumeReq):
    try:
        gal = chem.pool_volume(
            req.shape, req.length_ft, req.width_ft, req.avg_depth_ft,
            shallow_depth_ft=req.shallow_depth_ft, deep_depth_ft=req.deep_depth_ft,
        )
    except KeyError:
        raise HTTPException(422, f"unknown shape: {req.shape}")
    return {"gallons": gal}


@router.post("/dose")
def dose(req: DoseReq):
    try:
        return chem.compute_dose(
            parameter=req.parameter, chemical=req.chemical, current=req.current,
            goal=req.goal, volume_gal=req.volume_gal, strength=req.strength,
            total_alkalinity=req.total_alkalinity,
        )
    except ValueError as e:
        raise HTTPException(422, str(e))
