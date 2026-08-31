# v0.1
"""pathminer.plugin — thin KiCad PCB editor plugin shim.

Layer contract: imports kicad and analysis.  No Qt (uses pcbnew/wxPython
when called from within KiCad, but must not require Qt to be installed).

The plugin captures ordered pad sequences from the live board and delegates
all analysis to pathminer.analysis.  It must not duplicate solver logic.

Planned modules (later sessions):
    action.py   — pcbnew.ActionPlugin subclass (registered via KiCad plugin API)
    capture.py  — modeless ordered-pad capture dialog using wxPython
    bridge.py   — LiveBoardSource adapter wrapping pcbnew Board object
"""
