"""Validate the chemistry engine against TFP's published data (docs/tfp-reference.md).

These tests are the de-risking guarantee: if a future pypoolchem bump or a
refactor changes a target/dose, the published TFP numbers must still hold.
"""

import pytest

from poolmath import chemistry as chem
from poolmath import tfp_data as tfp


# --- FC/CYA published chart -------------------------------------------------
@pytest.mark.parametrize("cya,expected", list(tfp.FC_CYA_LIQUID.items()))
def test_fc_cya_liquid_table(cya, expected):
    min_fc, tlo, thi = expected
    t = chem.fc_cya_targets(cya, "liquid")
    assert (t.min_fc, t.target_fc_low, t.target_fc_high) == (min_fc, tlo, thi)


@pytest.mark.parametrize("cya,expected", list(tfp.FC_CYA_SWG.items()))
def test_fc_cya_swg_table(cya, expected):
    min_fc, tlo, thi = expected
    t = chem.fc_cya_targets(cya, "swg")
    assert (t.min_fc, t.target_fc_low, t.target_fc_high) == (min_fc, tlo, thi)


@pytest.mark.parametrize("cya,slam", list(tfp.SLAM_FC.items()))
def test_slam_table(cya, slam):
    assert chem.fc_cya_targets(cya, "liquid").slam_fc == slam


def test_tabs_uses_liquid_table():
    assert chem.fc_cya_targets(50, "tabs").target_fc_high == 8


def test_fc_cya_interpolates_between_rows():
    t = chem.fc_cya_targets(45, "liquid")  # between 40:(3,5,7) and 50:(4,6,8)
    assert t.min_fc == 3.5 and t.target_fc_low == 5.5 and t.target_fc_high == 7.5


def test_mustard_slam():
    assert chem.fc_cya_targets(50, "liquid").mustard_slam_fc == 30.0


def test_cya_recommended_flag():
    assert chem.fc_cya_targets(45, "liquid").cya_in_recommended_range is True
    assert chem.fc_cya_targets(80, "liquid").cya_in_recommended_range is False
    assert chem.fc_cya_targets(80, "swg").cya_in_recommended_range is True


# --- CSI (delegated to pypoolchem) ------------------------------------------
def test_csi_balanced_pool():
    v = chem.csi(ph=7.5, temperature_f=80, calcium_hardness=350, total_alkalinity=70, cyanuric_acid=50)
    assert -0.2 <= v <= 0.05
    assert chem.csi_status(v) == "ideal"


def test_csi_high_ph_scales():
    v = chem.csi(ph=8.2, temperature_f=88, calcium_hardness=600, total_alkalinity=120, cyanuric_acid=50)
    assert v > 0.3 and chem.csi_status(v) == "scaling"


def test_csi_status_bands():
    assert chem.csi_status(-0.8) == "etching"
    assert chem.csi_status(-0.45) == "acceptable_low"
    assert chem.csi_status(0.0) == "ideal"
    assert chem.csi_status(0.45) == "acceptable_high"
    assert chem.csi_status(0.8) == "scaling"


# --- Dosing vs TFP/PoolMath constants ---------------------------------------
def test_liquid_chlorine_12_5():
    assert chem.dose_fc_liquid_chlorine(1, 10000, 12.5).amount == pytest.approx(10.7, abs=0.2)


def test_liquid_chlorine_10():
    assert chem.dose_fc_liquid_chlorine(1, 10000, 10).amount == pytest.approx(13.4, abs=0.2)


def test_liquid_chlorine_scales_with_volume():
    assert chem.dose_fc_liquid_chlorine(3, 20000, 12.5).amount == pytest.approx(64.2, abs=0.5)


def test_baking_soda_ta():
    assert chem.dose_ta_baking_soda(10, 10000).amount == pytest.approx(1.5, abs=0.05)


def test_cya_dose():
    assert chem.dose_cya(10, 10000).amount == pytest.approx(13.0, abs=0.5)


def test_calcium_chloride_dihydrate():
    assert chem.dose_ch_calcium_chloride(10, 10000, "dihydrate").amount == pytest.approx(24.0, abs=0.5)


def test_salt_dose():
    assert chem.dose_salt(500, 10000).amount == pytest.approx(41.7, abs=1.0)


def test_cal_hypo_side_effect_ch():
    r = chem.dose_fc_cal_hypo(10, 10000, 73)
    assert r.side_effects["ch"] == pytest.approx(7.0, abs=0.5)


def test_muriatic_ta_down():
    assert chem.dose_ta_down_muriatic(10, 10000).amount == pytest.approx(25.6, abs=1.0)


def test_muriatic_ph_down_is_reasonable():
    # ~0.5 pH drop at TA 70 in 10k gal should be a low-tens of fl oz, not ~0.2 (the pypoolchem bug)
    amt = chem.dose_ph_down_muriatic(0.5, 10000, 70).amount
    assert 8 < amt < 25


# --- Volume -----------------------------------------------------------------
def test_rectangular_volume():
    # 32 x 16 x 5.5 avg ≈ 21,000 gal (32*16*5.5*7.48)
    assert chem.pool_volume("rectangular", 32, 16, 5.5) == pytest.approx(21000, rel=0.03)


# --- Classification ---------------------------------------------------------
def test_classify_fc_above_target_is_high_not_error():
    # FC 9 at CYA 50 (target 6-8, slam 20) -> above target but safe
    assert chem.classify("fc", 9, cya=50, source="liquid") == "acceptable_high"


def test_classify_ph():
    assert chem.classify("ph", 7.0) == "low"
    assert chem.classify("ph", 7.7) == "ideal"
    assert chem.classify("ph", 8.2) == "high"
