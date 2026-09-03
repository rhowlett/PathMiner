# v0.1
"""Tests for pathminer.core.units.

Session 03 (PWR-001). Values and boundaries are ported from the v0.13
module ``tools/pcb_trace_resistance.py`` (MIL_TO_M, MM_TO_M,
format_ohms) so these tests double as the acceptance record for that
extraction.
"""

from __future__ import annotations

import pytest

from pathminer.core import units


# ---------------------------------------------------------------------------
# Conversion constants
# ---------------------------------------------------------------------------

def test_mil_to_m_value():
    assert units.MIL_TO_M == 2.54e-5


def test_mm_to_m_value():
    assert units.MM_TO_M == 1.0e-3


def test_mil_to_m_matches_1000_mil_in_meters():
    # 1000 mil = 1 inch = 0.0254 m.
    assert 1000 * units.MIL_TO_M == pytest.approx(0.0254)


def test_mm_to_m_matches_1650_mm_board():
    # Sanity check against the v0.13 reference stackup's core thickness.
    assert 1.65 * units.MM_TO_M == pytest.approx(0.00165)


# ---------------------------------------------------------------------------
# format_ohms — auto-scaled resistance display
# ---------------------------------------------------------------------------

def test_format_ohms_microohm_range():
    assert units.format_ohms(5e-4) == "500 uohm"


def test_format_ohms_milliohm_range():
    assert units.format_ohms(0.05) == "50 mohm"


def test_format_ohms_ohm_range():
    assert units.format_ohms(5.0) == "5 ohm"


def test_format_ohms_kiloohm_range():
    assert units.format_ohms(5000.0) == "5 kohm"


def test_format_ohms_lower_boundary_is_exclusive():
    # r < 1e-3 is strict, so exactly 1e-3 falls into the milliohm branch.
    assert units.format_ohms(1e-3) == "1 mohm"


def test_format_ohms_one_ohm_boundary_is_exclusive():
    # r < 1.0 is strict, so exactly 1.0 falls into the ohm branch.
    assert units.format_ohms(1.0) == "1 ohm"


def test_format_ohms_kilo_boundary_is_exclusive():
    # r < 1e3 is strict, so exactly 1e3 falls into the kiloohm branch.
    assert units.format_ohms(1e3) == "1 kohm"


def test_format_ohms_zero_is_microohm_range():
    assert units.format_ohms(0.0) == "0 uohm"
