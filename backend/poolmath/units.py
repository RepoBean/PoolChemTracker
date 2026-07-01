"""Unit conversions so usage can be logged in whatever unit you buy in.

Two dimensions: liquid volume (base = fl oz) and dry weight (base = oz). Converting
across dimensions is undefined — a gallon of muriatic acid is not a pound of it.
"""

from __future__ import annotations

from typing import Optional

# unit -> factor to the dimension's base unit
_VOLUME = {
    "fl_oz": 1.0, "cup": 8.0, "pint": 16.0, "quart": 32.0, "gal": 128.0,
    "ml": 0.0338140227, "l": 33.8140227,
}
_WEIGHT = {
    "oz": 1.0, "oz_wt": 1.0, "lb": 16.0, "g": 0.0352739619, "kg": 35.2739619,
}


def _table(unit: str) -> Optional[dict]:
    if unit in _VOLUME:
        return _VOLUME
    if unit in _WEIGHT:
        return _WEIGHT
    return None


def convert(amount: float, from_unit: str, to_unit: str) -> Optional[float]:
    """Convert ``amount`` from one unit to another within the same dimension.
    Returns ``None`` if the units aren't compatible (e.g. volume vs weight)."""
    if from_unit == to_unit:
        return amount
    t = _table(from_unit)
    if t is None or _table(to_unit) is not t:
        return None
    return amount * t[from_unit] / t[to_unit]
