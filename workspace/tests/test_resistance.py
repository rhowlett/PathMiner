# v0.1
"""Tests for pathminer.core.resistance.

Session 03 (PWR-001: preserve validated trace, via, path, ladder, and
mesh calculations). These tests port the trace- and via-resistance
acceptance vectors from v0.13's headless selftest
(``tools/pcb_trace_resistance.py::selftest``) unchanged, retaining the
original vector IDs (V2, V3, V4, V6, V7, V8, and the "v0.2 regression"
block) so this module's numerical behavior remains auditable against
the v0.13 baseline (ARCH-010).

Stackup/Z-geometry (S8.2) is out of this session's scope, so the
per-layer geometry v0.13's ``Stackup.geometry()`` would normally
produce is reproduced here as a literal fixture (``GEO_ON`` /
``GEO_OFF``) instead of being built from a ``Stackup`` object. The
fixture values were hand-derived from v0.13's reference stackup (the
surveyed KiCad 9 board also used by the original selftest's V1-V8):

    F.Mask            0.010 mm
    F.Cu     (copper) 0.035 mm
    dielectric 1      0.100 mm  FR4
    In1.Cu   (copper) 0.070 mm
    dielectric 2      1.240 mm  FR4
    In2.Cu   (copper) 0.070 mm
    dielectric 3      0.100 mm  FR4
    B.Cu     (copper) 0.035 mm
    B.Mask            0.010 mm

with 25 um outer-layer plating, hole diameter 0.3 mm (V2-V6), and
plating diameter 25 um (V2-V8). GEO_ON models outer-layer plating
growth enabled (D8 on); GEO_OFF models it disabled. Once the
stackup/geometry extraction session lands ``Stackup.geometry()``, its
output should reproduce these same dicts for this reference board;
that equivalence is exercised again as an integration regression in a
later session rather than by re-deriving ``Stackup`` here.
"""

from __future__ import annotations

import math

import pytest

from pathminer.core import materials, units
from pathminer.core.resistance import (
    barrel_area,
    barrel_diameters,
    barrel_length_mm,
    resistance_at_temp,
    trace_resistance,
    via_resistance,
)

# ---------------------------------------------------------------------------
# Reference geometry fixture (see module docstring)
# ---------------------------------------------------------------------------

GEO_ON = [
    {"name": "F.Cu", "z_top_mm": -0.025, "finished_mm": 0.060, "z_ctr_mm": 0.005},
    {"name": "In1.Cu", "z_top_mm": 0.135, "finished_mm": 0.070, "z_ctr_mm": 0.170},
    {"name": "In2.Cu", "z_top_mm": 1.445, "finished_mm": 0.070, "z_ctr_mm": 1.480},
    {"name": "B.Cu", "z_top_mm": 1.615, "finished_mm": 0.060, "z_ctr_mm": 1.645},
]

GEO_OFF = [
    {"name": "F.Cu", "z_top_mm": 0.000, "finished_mm": 0.035, "z_ctr_mm": 0.0175},
    {"name": "In1.Cu", "z_top_mm": 0.135, "finished_mm": 0.070, "z_ctr_mm": 0.170},
    {"name": "In2.Cu", "z_top_mm": 1.445, "finished_mm": 0.070, "z_ctr_mm": 1.480},
    {"name": "B.Cu", "z_top_mm": 1.615, "finished_mm": 0.035, "z_ctr_mm": 1.6325},
]

HOLE_M = 0.3e-3
PLATING_M = 25e-6


def _trace_on(layer: str, geo, length_mil: float = 50, width_mil: float = 4) -> float:
    g = next(x for x in geo if x["name"] == layer)
    return trace_resistance(
        length_mil * units.MIL_TO_M,
        width_mil * units.MIL_TO_M,
        g["finished_mm"] * units.MM_TO_M,
    )


# ---------------------------------------------------------------------------
# V2 — via barrel resistance, all layer-pair spans (centre convention)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "a, b, want_l_mm, want_r_uohm",
    [
        ("F.Cu", "In1.Cu", 0.1650, 131.70),
        ("F.Cu", "In2.Cu", 1.4750, 1177.35),
        ("B.Cu", "In1.Cu", 1.4750, 1177.35),
        ("B.Cu", "In2.Cu", 0.1650, 131.70),
        ("F.Cu", "B.Cu", 1.6400, 1309.06),
    ],
)
def test_v2_via_barrel_resistance(a, b, want_l_mm, want_r_uohm):
    r, length_m, _area = via_resistance(GEO_ON, a, b, HOLE_M, PLATING_M)
    assert length_m * 1e3 == pytest.approx(want_l_mm, rel=1e-3)
    assert r * 1e6 == pytest.approx(want_r_uohm, rel=1e-3)


def test_v2_symmetry_f_to_in1_equals_b_to_in2():
    r1, _, _ = via_resistance(GEO_ON, "F.Cu", "In1.Cu", HOLE_M, PLATING_M)
    r2, _, _ = via_resistance(GEO_ON, "B.Cu", "In2.Cu", HOLE_M, PLATING_M)
    assert r1 == pytest.approx(r2, rel=1e-9)


# ---------------------------------------------------------------------------
# V3 — barrel-length span conventions
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "mode, want_l_mm, want_r_uohm",
    [
        ("facing", 0.1000, 79.82),
        ("centre", 0.1650, 131.70),
        ("outer", 0.2300, 183.59),
    ],
)
def test_v3_barrel_length_conventions(mode, want_l_mm, want_r_uohm):
    r, length_m, _area = via_resistance(
        GEO_ON, "F.Cu", "In1.Cu", HOLE_M, PLATING_M, mode=mode
    )
    assert length_m * 1e3 == pytest.approx(want_l_mm, rel=1e-3)
    assert r * 1e6 == pytest.approx(want_r_uohm, rel=1e-3)


# ---------------------------------------------------------------------------
# V4 — hole conventions
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "convention, want_od_mm, want_id_mm, want_area_um2, want_r_uohm",
    [
        ("bit", 0.300, 0.250, 21598.4, 1309.06),
        ("finished", 0.350, 0.300, 25525.4, 1107.66),
    ],
)
def test_v4_hole_conventions(convention, want_od_mm, want_id_mm, want_area_um2, want_r_uohm):
    od, idia = barrel_diameters(HOLE_M, PLATING_M, convention)
    r, _length_m, area = via_resistance(
        GEO_ON, "F.Cu", "B.Cu", HOLE_M, PLATING_M, convention=convention
    )
    assert od * 1e3 == pytest.approx(want_od_mm, rel=1e-3)
    assert idia * 1e3 == pytest.approx(want_id_mm, rel=1e-3)
    assert area * 1e12 == pytest.approx(want_area_um2, rel=1e-3)
    assert r * 1e6 == pytest.approx(want_r_uohm, rel=1e-3)


# ---------------------------------------------------------------------------
# V5 — manual series path: trace + via + trace (S8.5 Rpath = sum(Rsegment))
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "geo, want_t1_uohm, want_v_uohm, want_t2_uohm, want_tot_mohm, want_via_pct",
    [
        (GEO_ON, 3591.7, 1177.4, 3078.6, 7.8476, 15.0),
        (GEO_OFF, 6157.1, 1167.4, 3078.6, 10.4031, 11.2),
    ],
)
def test_v5_trace_via_trace_series_path(
    geo, want_t1_uohm, want_v_uohm, want_t2_uohm, want_tot_mohm, want_via_pct
):
    t1 = _trace_on("F.Cu", geo)
    t2 = _trace_on("In2.Cu", geo)
    v, _length_m, _area = via_resistance(geo, "F.Cu", "In2.Cu", HOLE_M, PLATING_M)
    total = t1 + v + t2
    assert t1 * 1e6 == pytest.approx(want_t1_uohm, rel=1e-3)
    assert v * 1e6 == pytest.approx(want_v_uohm, rel=1e-3)
    assert t2 * 1e6 == pytest.approx(want_t2_uohm, rel=1e-3)
    assert total * 1e3 == pytest.approx(want_tot_mohm, rel=1e-3)
    assert v / total * 100 == pytest.approx(want_via_pct, rel=1e-2)


# ---------------------------------------------------------------------------
# V6 — parallel via arrays
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "count, want_total_mohm",
    [(1, 7.8476), (2, 7.2589), (4, 6.9646), (8, 6.8174)],
)
def test_v6_parallel_via_array(count, want_total_mohm):
    t1 = _trace_on("F.Cu", GEO_ON)
    t2 = _trace_on("In2.Cu", GEO_ON)
    v, _length_m, _area = via_resistance(
        GEO_ON, "F.Cu", "In2.Cu", HOLE_M, PLATING_M, count=count
    )
    assert (t1 + v + t2) * 1e3 == pytest.approx(want_total_mohm, rel=1e-3)


def test_v6_sharing_50_pct_of_2_vias_equals_1_via():
    v50, _, _ = via_resistance(
        GEO_ON, "F.Cu", "In2.Cu", HOLE_M, PLATING_M, count=2, sharing_pct=50.0
    )
    v1, _, _ = via_resistance(GEO_ON, "F.Cu", "In2.Cu", HOLE_M, PLATING_M, count=1)
    assert v50 == pytest.approx(v1, rel=1e-9)


# ---------------------------------------------------------------------------
# V7 — guards
# ---------------------------------------------------------------------------

def test_v7_over_plating_closes_hole():
    with pytest.raises(ValueError):
        barrel_area(HOLE_M, 150e-6, "bit")


def test_v7_near_limit_plating_leaves_a_thin_id():
    _od, idia = barrel_diameters(HOLE_M, 149e-6, "bit")
    assert idia * 1e6 == pytest.approx(2.0, abs=1e-2)


# ---------------------------------------------------------------------------
# V8 — algebraic identity, both hole conventions
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("convention", ["bit", "finished"])
def test_v8_barrel_area_identity(convention):
    od, idia = barrel_diameters(HOLE_M, PLATING_M, convention)
    expanded = math.pi / 4.0 * (od * od - idia * idia)
    collapsed = math.pi * PLATING_M * (idia + PLATING_M)
    assert expanded == pytest.approx(collapsed, rel=1e-12)


# ---------------------------------------------------------------------------
# v0.2 regression — manual (no-stackup) trace resistance and hot resistance
# ---------------------------------------------------------------------------

def test_v02_regression_1000mil_x_10mil_1oz_trace():
    r20 = trace_resistance(
        1000 * units.MIL_TO_M, 10 * units.MIL_TO_M, 1 * materials.OZ_TO_UM * 1e-6
    )
    assert r20 * 1e3 == pytest.approx(49.5437, rel=1e-4)


def test_v02_regression_hot_resistance_at_temperature():
    r20 = trace_resistance(
        1000 * units.MIL_TO_M, 10 * units.MIL_TO_M, 1 * materials.OZ_TO_UM * 1e-6
    )
    hot = resistance_at_temp(r20, 38.3143)
    assert hot * 1e3 == pytest.approx(53.1094, rel=1e-4)


def test_resistance_at_temp_at_reference_temperature_is_unchanged():
    assert resistance_at_temp(1.0, 20.0) == 1.0


# ---------------------------------------------------------------------------
# Boundary / failure modes preserved from v0.13 (not new guards)
# ---------------------------------------------------------------------------

def test_trace_resistance_zero_width_raises():
    with pytest.raises(ZeroDivisionError):
        trace_resistance(1.0, 0.0, 1e-6)


def test_trace_resistance_zero_thickness_raises():
    with pytest.raises(ZeroDivisionError):
        trace_resistance(1.0, 1e-4, 0.0)


def test_barrel_length_mm_unknown_mode_raises():
    with pytest.raises(ValueError):
        barrel_length_mm(GEO_ON, "F.Cu", "In1.Cu", "sideways")


def test_barrel_length_mm_unknown_layer_raises():
    with pytest.raises(StopIteration):
        barrel_length_mm(GEO_ON, "F.Cu", "NoSuchLayer", "centre")
