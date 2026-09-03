# v0.1
"""pathminer.core.materials — copper material constants.

Extracted from ``tools/pcb_trace_resistance.py`` (v0.13) as part of
Session 03 (PWR-001). Values are the v0.13 sources of truth (see the
v0.13 module docstring, "Conventions / sources of truth", and
``.ai/planning/PathMiner_Project_Specification.md`` S8.1): IACS
annealed-copper resistivity and temperature coefficient, and the
standard copper-weight-to-thickness conversion.

No KiCad, Qt, wx, or file I/O (ARCH-002).
"""

from __future__ import annotations

RHO_CU_20C: float = 1.724e-8
"""Copper resistivity at 20 C, IACS annealed foil, in ohm-metres.

Electrodeposited via-barrel plating is measurably more resistive than
annealed foil, but v0.13 uses this single figure for both foil and
barrel copper absent a separately validated measurement. This is
reported as an approximation per the project specification (S8.1)
until a separately validated material model is supplied.
"""

ALPHA_CU: float = 0.00393
"""Copper temperature coefficient of resistance, per kelvin."""

OZ_TO_UM: float = 34.798
"""Copper-weight-to-thickness conversion: micrometres per oz/ft^2."""
