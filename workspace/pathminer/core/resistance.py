# v0.1
"""pathminer.core.resistance — trace and via-barrel DC resistance.

Extracted from ``tools/pcb_trace_resistance.py`` (v0.13) as part of
Session 03 (PWR-001: preserve validated trace, via, path, ladder, and
mesh calculations). This module ports the trace-resistance,
temperature-correction, and via-barrel formulas unchanged; see
``.ai/planning/PathMiner_Project_Specification.md`` S8.1, S8.3, and
S8.4 for the calculation specification.

Stackup/Z-geometry extraction (S8.2) is out of this session's owned
write scope (Sessions 04/05 own ``core/geometry.py`` and
``kicad/stackup.py``). ``via_resistance`` and ``barrel_length_mm``
therefore accept a plain sequence of per-copper-layer geometry
mappings rather than a ``Stackup`` object, so this module has no
dependency on the stackup/geometry extraction landing later. Each
mapping must provide:

    "name"         str    -- copper layer name, e.g. "F.Cu"
    "z_top_mm"     float  -- top-face Z position, mm
    "finished_mm"  float  -- finished (plated) copper thickness, mm
    "z_ctr_mm"     float  -- Z center of the copper, mm

This is exactly the per-layer dict shape produced by v0.13's
``Stackup.geometry()``; the stackup-extraction session is expected to
keep producing it so this module's callers do not have to change.

No KiCad, Qt, wx, or file I/O (ARCH-002).
"""

from __future__ import annotations

import math
from typing import Any, Mapping, Sequence

from .materials import ALPHA_CU, RHO_CU_20C
from .units import MM_TO_M


def trace_resistance(length_m: float, width_m: float, thickness_m: float) -> float:
    """DC resistance of a rectangular copper trace, in ohms, at 20 C.

    ``R20 = rho20 * L / (W * t)`` (project specification S8.3).
    """
    return RHO_CU_20C * length_m / (width_m * thickness_m)


def resistance_at_temp(r20: float, temp_c: float) -> float:
    """Resistance at *temp_c*, corrected from a 20 C reference value.

    ``R(T) = R20 * (1 + alphaCu * (T - 20))`` (project specification S8.1).
    """
    return r20 * (1.0 + ALPHA_CU * (temp_c - 20.0))


def barrel_diameters(hole_m: float, plating_m: float, convention: str) -> tuple[float, float]:
    """Return ``(outer_diameter_m, inner_diameter_m)`` for a plated via barrel.

    ``convention`` is one of:
      "bit"      -- *hole_m* is the drilled-bit diameter (the OD); plating
                    grows inward, so ``ID = OD - 2*plating``.
      "finished" -- *hole_m* is the finished (plated) hole diameter (the
                    ID); ``OD = ID + 2*plating``.

    Raises ``ValueError`` if the plating would close the hole
    (``2*plating >= drill``), per the required guard in project
    specification S8.4.
    """
    if convention == "bit":
        od = hole_m
        idia = od - 2.0 * plating_m
    else:
        idia = hole_m
        od = idia + 2.0 * plating_m
    if idia <= 0.0:
        raise ValueError("hole closed by plating: 2*plating >= drill")
    return od, idia


def barrel_area(hole_m: float, plating_m: float, convention: str) -> float:
    """Cross-sectional copper area of a plated via barrel, in m^2.

    ``Abarrel = pi/4 * (OD^2 - ID^2)`` (project specification S8.4).
    """
    od, idia = barrel_diameters(hole_m, plating_m, convention)
    return math.pi / 4.0 * (od * od - idia * idia)


def barrel_length_mm(
    geo: Sequence[Mapping[str, Any]],
    name_a: str,
    name_b: str,
    mode: str,
) -> float:
    """Barrel span, in mm, between copper layers *name_a* and *name_b*.

    ``mode`` selects the span convention (project specification S8.4):
      "centre" -- copper center-to-center (the default elsewhere).
      "facing" -- the facing (inner) surfaces only.
      "outer"  -- the outer surfaces of both layers.

    Raises ``StopIteration`` if either layer name is not present in
    *geo*, and ``ValueError`` for an unrecognised *mode*.
    """
    ga = next(g for g in geo if g["name"] == name_a)
    gb = next(g for g in geo if g["name"] == name_b)
    a0, a1 = ga["z_top_mm"], ga["z_top_mm"] + ga["finished_mm"]
    b0, b1 = gb["z_top_mm"], gb["z_top_mm"] + gb["finished_mm"]
    if mode == "centre":
        return abs(gb["z_ctr_mm"] - ga["z_ctr_mm"])
    if mode == "facing":
        return abs(max(a0, b0) - min(a1, b1))
    if mode == "outer":
        return abs(max(a1, b1) - min(a0, b0))
    raise ValueError(f"bad length mode {mode}")


def via_resistance(
    geo: Sequence[Mapping[str, Any]],
    a: str,
    b: str,
    hole_m: float,
    plating_m: float,
    convention: str = "bit",
    mode: str = "centre",
    count: int = 1,
    sharing_pct: float = 100.0,
) -> tuple[float, float, float]:
    """DC resistance of a via, or a derated parallel via array, at 20 C.

    Returns ``(resistance_ohm, length_m, area_m2)``.

    ``Rarray = R20 / (count * sharing_pct / 100)`` (project
    specification S8.4).
    """
    area = barrel_area(hole_m, plating_m, convention)
    length_m = barrel_length_mm(geo, a, b, mode) * MM_TO_M
    r = RHO_CU_20C * length_m / area
    eff = max(count * sharing_pct / 100.0, 1e-9)
    return r / eff, length_m, area
