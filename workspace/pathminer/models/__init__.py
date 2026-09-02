# v0.1
"""pathminer.models — geometry-to-network builders.

Layer contract: imports core and kicad.  No Qt.  No wx.
Converts board geometry into a ResistorNetwork for the solver.

Planned modules (extracted in Sessions 03–07):
    p2p.py      — point-to-point track/via builder
    ladder.py   — via-array + per-layer strip builder for pours
    mesh.py     — rasterised pour-grid builder
"""
