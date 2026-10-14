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


# Free-text unit words (receipts, model output) -> app unit tokens.
_UNIT_ALIASES: dict[str, str] = {
    "gal": "gal", "gallon": "gal", "gallons": "gal",
    "quart": "quart", "quarts": "quart", "qt": "quart", "qts": "quart",
    "fl_oz": "fl_oz", "fl oz": "fl_oz", "floz": "fl_oz", "fl. oz.": "fl_oz",
    "l": "l", "liter": "l", "liters": "l", "litre": "l", "litres": "l",
    "ml": "ml", "milliliter": "ml", "milliliters": "ml", "millilitre": "ml",
    "lb": "lb", "lbs": "lb", "pound": "lb", "pounds": "lb",
    "kg": "kg", "kilogram": "kg", "kilograms": "kg",
    "g": "g", "gram": "g", "grams": "g", "gm": "g", "gms": "g",
    # Bare "oz" is ambiguous and handled separately below.
    "oz": "fl_oz", "ounce": "fl_oz", "ounces": "fl_oz",
    "oz_wt": "oz_wt", "oz wt": "oz_wt",
}

# Name hints that a chemical is dry/powder (bare "oz" on the receipt = weight).
# NB: "chlor" alone is not a hint — "liquid pool chlorine" is a liquid.
# The dry ones (cal-hypo, calcium chloride) are caught by their other words.
_DRY_HINTS = (
    "hypo", "calcium", "chloride", "baking", "soda", "stabilizer",
    "cyanuric", "cya", "salt", "sodium", "borax", "boric", "alum", "diatom",
    "powder", "granular", "dry",
)


def is_dry(name: str) -> bool:
    n = name.lower()
    return any(h in n for h in _DRY_HINTS)


def normalize_unit(raw: Optional[str], *, dry: bool = False) -> Optional[str]:
    """Map a free-text unit word onto the app's unit set (see module docstring).
    Bare 'oz' becomes oz_wt for dry/powder chemicals, fl_oz for liquids.
    Unknown words come back as None so callers can keep the original text."""
    if not raw:
        return None
    key = " ".join(raw.strip().lower().split())
    if key in ("oz", "ounce", "ounces"):
        return "oz_wt" if dry else "fl_oz"
    return _UNIT_ALIASES.get(key)


def convert(amount: float, from_unit: str, to_unit: str) -> Optional[float]:
    """Convert ``amount`` from one unit to another within the same dimension.
    Returns ``None`` if the units aren't compatible (e.g. volume vs weight)."""
    if from_unit == to_unit:
        return amount
    t = _table(from_unit)
    if t is None or _table(to_unit) is not t:
        return None
    return amount * t[from_unit] / t[to_unit]
