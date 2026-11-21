# v0.2
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
