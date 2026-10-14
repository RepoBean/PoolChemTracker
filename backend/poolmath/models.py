"""SQLModel tables + API request/response schemas."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, computed_field, field_serializer, field_validator
from sqlmodel import Field, SQLModel


# --- Quick (categorical) test vocabulary -----------------------------------
# OTO 5-drop swatch steps -> numeric FC lower bound used for charting and
# targeting. "none" (no color change) means FC < 0.5, so it maps to 0.0.
FC_COLOR_STEPS: dict[str, float] = {
    "none": 0.0, "0.5": 0.5, "1": 1.0, "2": 2.0, "3": 3.0, "5": 5.0, "10": 10.0,
    "15": 15.0, "20": 20.0, "30": 30.0, "40": 40.0, "50": 50.0, "100": 100.0,
}
# Coarse pH chip values (test-strip / drop resolution).
PH_QUICK_VALUES: tuple[str, ...] = (
    "7.2", "7.4", "7.6", "7.8", "8.0", "8.2", "8.4",
)


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _iso_utc(v: datetime) -> str:
    """Serialize a datetime as explicit UTC. SQLite stores our ``utcnow()`` values
    as naive strings; without an offset a browser's ``new Date()`` parses them as
    *local* time, shifting every displayed timestamp. Emitting +00:00 keeps clients
    (and future MQTT/export consumers) unambiguous."""
    if v.tzinfo is None:
        v = v.replace(tzinfo=timezone.utc)
    return v.isoformat()


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

    @field_serializer("created_at")
    def _ser_created_at(self, v: datetime) -> str:
        return _iso_utc(v)


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
    test_type: str = "full"               # "full" | "quick" (categorical)
    fc_color: Optional[str] = None        # OTO 5-drop swatch step (FC_COLOR_STEPS)
    ph_quick: Optional[str] = None        # coarse pH chip, 7.2..8.4 step 0.2

    @computed_field
    @property
    def is_approx(self) -> bool:
        """True for categorical readings (quick mode or an OTO color step) so the
        UI can mark them as approximate on charts. Derived — not a column."""
        return self.test_type == "quick" or self.fc_color is not None

    @field_serializer("taken_at")
    def _ser_taken_at(self, v: datetime) -> str:
        return _iso_utc(v)


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

    @field_serializer("applied_at")
    def _ser_applied_at(self, v: datetime) -> str:
        return _iso_utc(v)


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
    test_type: str = "full"               # "full" | "quick"
    fc_color: Optional[str] = None        # OTO 5-drop swatch step
    ph_quick: Optional[str] = None        # coarse pH chip

    @field_validator("test_type")
    @classmethod
    def _check_test_type(cls, v: str) -> str:
        if v not in ("full", "quick"):
            raise ValueError("test_type must be 'full' or 'quick'")
        return v

    @field_validator("fc_color")
    @classmethod
    def _check_fc_color(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in FC_COLOR_STEPS:
            raise ValueError(f"fc_color must be one of: {', '.join(FC_COLOR_STEPS)}")
        return v

    @field_validator("ph_quick")
    @classmethod
    def _check_ph_quick(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in PH_QUICK_VALUES:
            raise ValueError("ph_quick must be 7.2..8.4 in 0.2 steps")
        return v


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
