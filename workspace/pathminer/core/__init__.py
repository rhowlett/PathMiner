# v0.1
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
"""
