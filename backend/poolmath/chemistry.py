"""Chemistry service — the single source of truth for the API layer.

Design (validated against pypoolchem v0.1.1 and TFP's published data):
  * **CSI / equilibrium**  -> delegated to ``pypoolchem`` (matches TFP).
  * **FC/CYA targets, SLAM, ideal ranges, all dosing** -> computed here from
    TFP published data (``tfp_data``), because pypoolchem's dosing diverges from
    TFP (chlorine ~25% low; muriatic acid ~100x off in v0.1.1).

Keep this module free of web/DB concerns so it stays unit-testable in isolation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, Optional

import pypoolchem as _ppc

from . import tfp_data as tfp

ChlorineSource = Literal["liquid", "swg", "tabs"]
Surface = Literal["plaster", "pebble", "vinyl", "fiberglass", "painted"]


# --------------------------------------------------------------------------
# FC / CYA targets
# --------------------------------------------------------------------------
@dataclass
class FcCyaTargets:
    cya: float
    source: str
    min_fc: float
    target_fc_low: float
    target_fc_high: float
    slam_fc: float
    mustard_slam_fc: float
    recommended_cya_low: int
    recommended_cya_high: int
    cya_in_recommended_range: bool


def _interp(table: dict, x: float) -> tuple[float, ...]:
    """Linear-interpolate a CYA-keyed table of numeric tuples."""
    keys = sorted(table)
    if x <= keys[0]:
        return _as_tuple(table[keys[0]])
    if x >= keys[-1]:
        return _as_tuple(table[keys[-1]])
    lo = max(k for k in keys if k <= x)
    hi = min(k for k in keys if k >= x)
    if lo == hi:
        return _as_tuple(table[lo])
    f = (x - lo) / (hi - lo)
    a, b = _as_tuple(table[lo]), _as_tuple(table[hi])
    return tuple(av + (bv - av) * f for av, bv in zip(a, b))


def _as_tuple(v) -> tuple[float, ...]:
    return v if isinstance(v, tuple) else (v,)


def slam_fc(cya: float) -> float:
    """SLAM (shock) FC. Matches the TFP table at published points, and uses the
    0.4×CYA rule (floor 10) outside 20–100."""
    tbl = tfp.SLAM_FC
    keys = sorted(tbl)
    if cya < keys[0]:
        return max(10.0, cya * tfp.SLAM_FACTOR)
    if cya > keys[-1]:
        return cya * tfp.SLAM_FACTOR
    return _interp(tbl, cya)[0]


def fc_cya_targets(cya: float, source: ChlorineSource = "liquid") -> FcCyaTargets:
    is_swg = source == "swg"
    table = tfp.FC_CYA_SWG if is_swg else tfp.FC_CYA_LIQUID
    min_fc, tlo, thi = _interp(table, cya)
    rec_lo, rec_hi = tfp.CYA_RECOMMENDED["swg" if is_swg else "liquid"]
    return FcCyaTargets(
        cya=cya,
        source=source,
        min_fc=round(min_fc, 1),
        target_fc_low=round(tlo, 1),
        target_fc_high=round(thi, 1),
        slam_fc=round(slam_fc(cya), 1),
        mustard_slam_fc=round(cya * tfp.MUSTARD_SLAM_FACTOR, 1),
        recommended_cya_low=rec_lo,
        recommended_cya_high=rec_hi,
        cya_in_recommended_range=rec_lo <= cya <= rec_hi,
    )


# --------------------------------------------------------------------------
# CSI (delegated to pypoolchem — the part it gets right)
# --------------------------------------------------------------------------
def csi(
    ph: float,
    temperature_f: float,
    calcium_hardness: float,
    total_alkalinity: float,
    cyanuric_acid: float = 0.0,
    salt: float = 0.0,
    borates: float = 0.0,
) -> float:
    return round(
        _ppc.calculate_csi(
            ph=ph,
            temperature_f=temperature_f,
            calcium_hardness=calcium_hardness,
            total_alkalinity=total_alkalinity,
            cyanuric_acid=cyanuric_acid,
            salt=salt,
            borates=borates,
        ),
        2,
    )


def csi_status(value: float) -> str:
    """etching < -0.6 <= acceptable_low < -0.3 <= ideal <= 0.3 < acceptable_high <= 0.6 < scaling"""
    lo_max, id_lo, id_hi, hi_max = tfp.IDEAL_RANGES["csi"]
    if value < lo_max:
        return "etching"
    if value < id_lo:
        return "acceptable_low"
    if value <= id_hi:
        return "ideal"
    if value <= hi_max:
        return "acceptable_high"
    return "scaling"


# --------------------------------------------------------------------------
# Ideal ranges + status classification (dashboard colors)
# --------------------------------------------------------------------------
def ideal_range(param: str, *, surface: Surface = "plaster", source: ChlorineSource = "liquid",
                cya: Optional[float] = None) -> tuple[float, float, float, float]:
    """Return (acceptable_min, ideal_low, ideal_high, acceptable_max) for a param."""
    if param == "ch":
        return tfp.CH_BY_SURFACE.get(surface, tfp.CH_BY_SURFACE["plaster"])
    if param == "cya":
        lo, hi = tfp.CYA_RECOMMENDED["swg" if source == "swg" else "liquid"]
        return (lo, lo, hi, hi)
    if param == "fc":
        if cya is None:
            raise ValueError("fc range requires cya")
        t = fc_cya_targets(cya, source)
        return (t.min_fc, t.target_fc_low, t.target_fc_high, t.slam_fc)
    return tfp.IDEAL_RANGES[param]


Status = Literal["low", "acceptable_low", "ideal", "acceptable_high", "high"]


def classify(param: str, value: float, **kw) -> Status:
    """Classify a reading for UI coloring. For FC, 'high' (up to SLAM) is still
    safe — the frontend colors above-target-but-safe as neutral, not red."""
    amin, ilo, ihi, amax = ideal_range(param, **kw)
    if value < amin:
        return "low"
    if value < ilo:
        return "acceptable_low"
    if value <= ihi:
        return "ideal"
    if value <= amax:
        return "acceptable_high"
    return "high"


# --------------------------------------------------------------------------
# Dosing (TFP-aligned; the API passes current+goal+volume+chemical+strength)
# --------------------------------------------------------------------------
@dataclass
class DoseResult:
    chemical: str
    parameter: str
    amount: float
    unit: str
    direction: str = "increase"          # increase | decrease
    side_effects: dict = field(default_factory=dict)
    note: str = ""


def _per_10k(volume_gal: float) -> float:
    return volume_gal / 10_000.0


def dose_fc_liquid_chlorine(delta_fc: float, volume_gal: float, percent: float = 12.5) -> DoseResult:
    fl_oz = delta_fc * _per_10k(volume_gal) * (tfp.CHLORINE_FLOZ_K / percent)
    return DoseResult(
        chemical=f"liquid_chlorine_{percent:g}%", parameter="fc",
        amount=round(fl_oz, 1), unit="fl_oz",
        note="Pour in front of a return; run pump ≥30 min.",
    )


def dose_fc_cal_hypo(delta_fc: float, volume_gal: float, percent: float = 73.0) -> DoseResult:
    oz = delta_fc * _per_10k(volume_gal) * (tfp.CAL_HYPO_OZ_K / percent)
    return DoseResult(
        chemical=f"cal_hypo_{percent:g}%", parameter="fc",
        amount=round(oz, 1), unit="oz_wt",
        side_effects={"ch": round(delta_fc * tfp.CAL_HYPO_CH_PER_FC, 1)},
        note="Raises CH. Wait 24 h before adjusting pH/TA (calcium clouding).",
    )


def dose_fc_dichlor(delta_fc: float, volume_gal: float, percent: float = 56.0) -> DoseResult:
    oz = delta_fc * _per_10k(volume_gal) * (tfp.CAL_HYPO_OZ_K / percent)  # similar magnitude
    return DoseResult(
        chemical=f"dichlor_{percent:g}%", parameter="fc",
        amount=round(oz, 1), unit="oz_wt",
        side_effects={"cya": round(delta_fc * tfp.DICHLOR_CYA_PER_FC, 1)},
        note="Raises CYA; not for routine use (TFP).",
    )


def dose_ta_baking_soda(delta_ta: float, volume_gal: float) -> DoseResult:
    lb = delta_ta * _per_10k(volume_gal) * tfp.BAKING_SODA_LB_PER_PPM
    return DoseResult(
        chemical="baking_soda", parameter="ta",
        amount=round(lb, 2), unit="lb",
        note="Only raise TA if below ~50. Slight pH rise.",
    )


def dose_ch_calcium_chloride(delta_ch: float, volume_gal: float, form: str = "dihydrate") -> DoseResult:
    k = tfp.CALCIUM_CHLORIDE_OZ_PER_PPM[form]
    oz = delta_ch * _per_10k(volume_gal) * k
    return DoseResult(
        chemical=f"calcium_chloride_{form}", parameter="ch",
        amount=round(oz, 1), unit="oz_wt",
    )


def dose_cya(delta_cya: float, volume_gal: float) -> DoseResult:
    oz = delta_cya * _per_10k(volume_gal) * tfp.CYA_OZ_PER_PPM
    return DoseResult(
        chemical="cya_granular", parameter="cya",
        amount=round(oz, 1), unit="oz_wt",
        note="Sock method. Dose as if already present; retest in ~1 week.",
    )


def dose_salt(delta_salt: float, volume_gal: float) -> DoseResult:
    lb = volume_gal * delta_salt * tfp.SALT_LB_FACTOR / 1_000_000.0
    return DoseResult(chemical="pool_salt", parameter="salt", amount=round(lb, 1), unit="lb")


def dose_ph_down_muriatic(delta_ph: float, volume_gal: float, total_alkalinity: float,
                          percent: float = 31.45) -> DoseResult:
    """Muriatic acid to lower pH. Nonlinear (TA-buffered) — an ESTIMATE. TFP
    guidance: lower toward 7.2 and retest. Also lowers TA."""
    base = abs(delta_ph) * _per_10k(volume_gal) * (total_alkalinity / 100.0) * tfp.MURIATIC_PH_K
    fl_oz = base * (tfp.MURIATIC_BASE_PERCENT / percent)
    return DoseResult(
        chemical=f"muriatic_acid_{percent:g}%", parameter="ph", amount=round(fl_oz, 1),
        unit="fl_oz", direction="decrease",
        note="Estimate — acid demand is nonlinear. Also lowers TA. Retest; pump ≥30 min.",
    )


def dose_ta_down_muriatic(delta_ta: float, volume_gal: float, percent: float = 31.45) -> DoseResult:
    fl_oz = abs(delta_ta) * _per_10k(volume_gal) * tfp.MURIATIC_TA_FLOZ_PER_PPM
    fl_oz *= tfp.MURIATIC_BASE_PERCENT / percent
    return DoseResult(
        chemical=f"muriatic_acid_{percent:g}%", parameter="ta", amount=round(fl_oz, 1),
        unit="fl_oz", direction="decrease",
        note="Also lowers pH; aerate to bring pH back up. Manage pH primarily.",
    )


# --------------------------------------------------------------------------
# Volume (geometry; pypoolchem handles the shapes)
# --------------------------------------------------------------------------
_SHAPES = {
    "rectangular": _ppc.PoolShape.RECTANGULAR,
    "round": _ppc.PoolShape.ROUND,
    "oval": _ppc.PoolShape.OVAL,
    "kidney": _ppc.PoolShape.KIDNEY,
    "freeform": _ppc.PoolShape.FREEFORM,
}


def pool_volume(shape: str, length_ft: float, width_ft: float, avg_depth_ft: float,
                shallow_depth_ft: Optional[float] = None,
                deep_depth_ft: Optional[float] = None) -> float:
    gal = _ppc.calculate_pool_volume(
        _SHAPES[shape], length_ft, width_ft, avg_depth_ft,
        shallow_depth_ft=shallow_depth_ft, deep_depth_ft=deep_depth_ft,
    )
    return round(gal)
