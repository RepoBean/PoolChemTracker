"""TFP published reference data — the source of truth for targets, chemical
choices, and dosing constants.

Every number here is traceable to ``docs/tfp-reference.md`` (TroubleFreePool's
published articles). The chemistry engine (``chemistry.py``) uses these values
directly rather than the ``pypoolchem`` library's dosing/target numbers, which
diverge from TFP (chlorine ~25% low, muriatic acid grossly off in v0.1.1).
``pypoolchem`` IS used for CSI, where it matches TFP.
"""

from __future__ import annotations

# --- FC / CYA relationship -------------------------------------------------
# CYA ppm -> (min_fc, target_low, target_high)
FC_CYA_LIQUID: dict[int, tuple[int, int, int]] = {
    20: (2, 3, 5),
    30: (2, 4, 6),
    40: (3, 5, 7),
    50: (4, 6, 8),
    60: (5, 7, 9),
    70: (5, 8, 10),
    80: (6, 9, 11),
    90: (7, 10, 12),
    100: (8, 11, 13),
}
FC_CYA_SWG: dict[int, tuple[int, int, int]] = {
    20: (2, 3, 5),
    30: (2, 3, 6),
    40: (2, 3, 7),
    50: (2, 3, 8),
    60: (3, 4, 9),
    70: (3, 5, 10),
    80: (4, 6, 11),
    90: (4, 6, 12),
    100: (5, 7, 13),
}
# CYA ppm -> SLAM (shock) FC
SLAM_FC: dict[int, int] = {
    20: 10, 30: 12, 40: 16, 50: 20, 60: 24, 70: 28, 80: 31, 90: 35, 100: 39,
}

# Universal maintenance minimum when CYA is unknown/unstabilized: TFP's
# "keep FC at 1.0" rule (the FC/CYA chart starts at CYA 20).
MIN_FC_NO_CYA = 1.0

MUSTARD_SLAM_FACTOR = 0.60  # mustard/yellow-algae SLAM ≈ 0.6 × CYA
SLAM_FACTOR = 0.40          # continuous SLAM ≈ 0.4 × CYA (floor 10) outside the table

# Recommended CYA range by chlorine source
CYA_RECOMMENDED = {"liquid": (30, 60), "swg": (60, 90)}

# --- Recommended target ranges --------------------------------------------
# param -> (acceptable_min, ideal_low, ideal_high, acceptable_max)
# Defaults are plaster + liquid chlorine (this pool). CH varies by surface.
IDEAL_RANGES = {
    "ph": (7.2, 7.6, 7.8, 8.0),
    "ta": (50, 60, 80, 90),
    "cc": (0.0, 0.0, 0.0, 0.5),
    "csi": (-0.6, -0.3, 0.3, 0.6),
}
CH_BY_SURFACE = {
    # surface -> (acceptable_min, ideal_low, ideal_high, acceptable_max)
    "plaster": (250, 350, 550, 650),
    "pebble": (250, 350, 550, 650),
    "vinyl": (0, 0, 0, 650),        # not needed for the liner itself
    "fiberglass": (0, 0, 0, 650),
    "painted": (250, 350, 550, 650),
}
SALT_COMFORT = (1500, 2000)  # optional, non-SWG
BORATES_OPTIONAL = (30, 50)

# --- Dosing constants (per ppm change, per 10,000 US gal) ------------------
# Liquid chlorine: fl_oz = dFC * (gal/1e4) * (CHLORINE_FLOZ_K / percent)
# 12.5% -> 10.7 fl oz/ppm; 10% -> 13.4; 6% -> 22.3.
CHLORINE_FLOZ_K = 133.75
# Cal-hypo: oz_wt = dFC * (gal/1e4) * (CAL_HYPO_OZ_K / percent); 73% -> ~2 oz.
CAL_HYPO_OZ_K = 146.0
BAKING_SODA_LB_PER_PPM = 0.15          # lb TA-up per ppm
CALCIUM_CHLORIDE_OZ_PER_PPM = {"anhydrous": 1.85, "dihydrate": 2.4}  # CH-up
CYA_OZ_PER_PPM = 1.30                  # granular stabilizer
SALT_LB_FACTOR = 8.34                  # lb = gal * dppm * 8.34 / 1e6

# Muriatic acid (31.45% base). Nonlinear; these are TFP-aligned estimates.
MURIATIC_BASE_PERCENT = 31.45
MURIATIC_TA_FLOZ_PER_PPM = 2.56        # fl oz 31.45% per ppm TA down
MURIATIC_PH_K = 40.0                   # fl_oz = dpH * (gal/1e4) * (TA/100) * K

# Secondary effects (ppm per ppm FC added)
CAL_HYPO_CH_PER_FC = 0.7
DICHLOR_CYA_PER_FC = 0.9
TRICHLOR_CYA_PER_FC = 0.6

FL_OZ_PER_GAL = 128.0
OZ_PER_LB = 16.0
