"""SQLModel tables + API request/response schemas."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel
from sqlmodel import Field, SQLModel


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


# --- Tables ----------------------------------------------------------------
class Pool(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    volume_gal: float
    surface_type: str = "plaster"        # plaster|pebble|vinyl|fiberglass|painted
    chlorine_source: str = "liquid"      # liquid|swg|tabs
    uses_salt: bool = False
    uses_borates: bool = False
    created_at: datetime = Field(default_factory=utcnow)


class TestLog(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    pool_id: int = Field(foreign_key="pool.id", index=True)
    taken_at: datetime = Field(default_factory=utcnow, index=True)
    fc: Optional[float] = None
    cc: Optional[float] = None
    ph: Optional[float] = None
    ta: Optional[float] = None
    ch: Optional[float] = None
    cya: Optional[float] = None
    salt: Optional[float] = None
    borate: Optional[float] = None
    water_temp_f: Optional[float] = None
    tds: Optional[float] = None
    csi: Optional[float] = None           # computed on save
    notes: Optional[str] = None


class DoseLog(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    pool_id: int = Field(foreign_key="pool.id", index=True)
    applied_at: datetime = Field(default_factory=utcnow, index=True)
    chemical: str
    strength: Optional[str] = None
    amount: float
    unit: str
    parameter_targeted: Optional[str] = None
    from_value: Optional[float] = None
    to_value: Optional[float] = None
    cost: Optional[float] = None
    test_log_id: Optional[int] = Field(default=None, foreign_key="testlog.id")


class Chemical(SQLModel, table=True):
    """Inventory-lite for consumption/cost tracking (a primary goal)."""
    id: Optional[int] = Field(default=None, primary_key=True)
    pool_id: int = Field(foreign_key="pool.id", index=True)
    name: str
    strength: Optional[str] = None
    unit: str
    qty_on_hand: float = 0.0
    cost_per_unit: Optional[float] = None


# --- API schemas -----------------------------------------------------------
class PoolCreate(BaseModel):
    name: str
    volume_gal: float
    surface_type: str = "plaster"
    chlorine_source: str = "liquid"
    uses_salt: bool = False
    uses_borates: bool = False


class PoolUpdate(BaseModel):
    name: Optional[str] = None
    volume_gal: Optional[float] = None
    surface_type: Optional[str] = None
    chlorine_source: Optional[str] = None
    uses_salt: Optional[bool] = None
    uses_borates: Optional[bool] = None


class TestLogCreate(BaseModel):
    taken_at: Optional[datetime] = None
    fc: Optional[float] = None
    cc: Optional[float] = None
    ph: Optional[float] = None
    ta: Optional[float] = None
    ch: Optional[float] = None
    cya: Optional[float] = None
    salt: Optional[float] = None
    borate: Optional[float] = None
    water_temp_f: Optional[float] = None
    tds: Optional[float] = None
    notes: Optional[str] = None


class ChemicalCreate(BaseModel):
    name: str
    strength: Optional[str] = None
    unit: str
    qty_on_hand: float = 0.0
    cost_per_unit: Optional[float] = None


class ChemicalUpdate(BaseModel):
    name: Optional[str] = None
    strength: Optional[str] = None
    unit: Optional[str] = None
    qty_on_hand: Optional[float] = None
    cost_per_unit: Optional[float] = None


class DoseLogCreate(BaseModel):
    applied_at: Optional[datetime] = None
    chemical: str
    strength: Optional[str] = None
    amount: float
    unit: str
    parameter_targeted: Optional[str] = None
    from_value: Optional[float] = None
    to_value: Optional[float] = None
    cost: Optional[float] = None
    test_log_id: Optional[int] = None
    chemical_id: Optional[int] = None  # optional inventory item to decrement
