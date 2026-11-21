# v0.3
################################################################################
#  Project   : PathMiner
#  File      : __init__.py
#  Copyright : (c) 2026 brickChip and Richard Howlett. All rights reserved.
#  Author    : Richard Howlett <rhowlett@eenerd.com>
#  License   : PolyForm Noncommercial 1.0.0. Free for noncommercial use;
#              commercial use requires written permission from the owner.
#              Full terms in LICENSE at the project root.
#  Warranty  : None. Provided as is; the owner is not liable for any
#              damages arising from its use (No Liability, LICENSE).
#  SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
################################################################################

"""pathminer.core — pure physics and mathematics.

Layer contract: no KiCad, no Qt, no wx, no file I/O.
Nothing in this sub-package may import from pathminer.kicad,
pathminer.ui, pathminer.storage, pathminer.plugin, or pathminer.report.

Planned modules (extracted in Sessions 03–04):
    units.py      — unit conversions and constants
    materials.py  — trace, via, barrel resistance; temperature coefficient; IPC rise
    geometry.py   — polygon helpers, arc handling, clustering
    solver.py     — dense, CG, and optional SciPy backends
    network.py    — ResistorNetwork, Edge, TwoTerminalResult

Session 08 (BASE-004, ARCH-006, ARCH-010): ``tools/pcb_trace_resistance.py``
(the legacy compatibility facade) now aliases its own solver-dispatch and
pure-geometry names directly onto ``geometry.py`` / ``solver.py`` rather than
keeping duplicate copies, so this sub-package is consumed by both the split
``pathminer`` package and the legacy script. See that file's own module
docstring and ``tests/test_compatibility.py``.
"""
