# v0.1
"""pathminer.kicad — KiCad file formats and live-board adapter.

Layer contract: imports core.  No Qt.  No wx.
Provides the BoardSource protocol and FileBoardSource implementation.

Planned modules (extracted in Sessions 05–06):
    sexpr.py    — minimal S-expression parser for .kicad_pcb files
    stackup.py  — copper layer and dielectric stackup from board or manual input
    prefs.py    — KiCad application preferences discovery
    board.py    — FileBoardSource implementing the BoardSource protocol
"""
