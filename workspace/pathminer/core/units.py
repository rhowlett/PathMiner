# v0.1
"""pathminer.core.units — pure unit-conversion and display constants/helpers.

Extracted from ``tools/pcb_trace_resistance.py`` (v0.13) as part of
Session 03 (PWR-001: preserve validated trace, via, path, ladder, and
mesh calculations). Values and behaviour are ported unchanged from
v0.13; see ``documents/change_log.md`` and
``.ai/planning/PathMiner_Project_Specification.md`` S8.1 for provenance
and the calculation specification.

No KiCad, Qt, wx, or file I/O (ARCH-002).
"""

from __future__ import annotations

MIL_TO_M: float = 2.54e-5
"""One thousandth of an inch (1 mil), in metres."""

MM_TO_M: float = 1.0e-3
"""One millimetre, in metres."""


def format_ohms(r: float) -> str:
    """Auto-scale a resistance in ohms to a short, human-readable string.

    Ported unchanged from v0.13 ``format_ohms``. Thresholds are strict
    on the low side: ``r < 1e-3`` -> microohms, ``r < 1.0`` ->
    milliohms, ``r < 1e3`` -> ohms, otherwise kiloohms.
    """
    if r < 1e-3:
        return f"{r * 1e6:.4g} uohm"
    if r < 1.0:
        return f"{r * 1e3:.4g} mohm"
    if r < 1e3:
        return f"{r:.4g} ohm"
    return f"{r / 1e3:.4g} kohm"
