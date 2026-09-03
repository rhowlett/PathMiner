# v0.1
"""Tests for pathminer.core.materials.

Session 03 (PWR-001). Values are ported from the v0.13 module
``tools/pcb_trace_resistance.py`` (RHO_CU_20C, ALPHA_CU, OZ_TO_UM) and
from ``.ai/planning/PathMiner_Project_Specification.md`` S8.1, which
states the same three constants as the calculation specification.
"""

from __future__ import annotations

from pathminer.core import materials


def test_copper_resistivity_value():
    assert materials.RHO_CU_20C == 1.724e-8


def test_copper_temperature_coefficient_value():
    assert materials.ALPHA_CU == 0.00393


def test_oz_to_um_value():
    assert materials.OZ_TO_UM == 34.798


def test_constants_are_positive():
    # Boundary/sanity: none of these physical constants can be zero or
    # negative without indicating a corrupted value.
    assert materials.RHO_CU_20C > 0.0
    assert materials.ALPHA_CU > 0.0
    assert materials.OZ_TO_UM > 0.0
