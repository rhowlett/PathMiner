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

"""pathminer.kicad — KiCad file formats and live-board adapter.

Layer contract: imports core.  No Qt.  No wx.
Provides the BoardSource protocol and FileBoardSource implementation.

Planned modules (extracted in Sessions 05–06):
    sexpr.py    — minimal S-expression parser for .kicad_pcb files
    stackup.py  — copper layer and dielectric stackup from board or manual input
    prefs.py    — KiCad application preferences discovery
    board.py    — FileBoardSource implementing the BoardSource protocol
"""
