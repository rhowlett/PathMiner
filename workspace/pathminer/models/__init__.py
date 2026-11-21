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

"""pathminer.models — geometry-to-network builders.

Layer contract: imports core and kicad.  No Qt.  No wx.
Converts board geometry into a ResistorNetwork for the solver.

Planned modules (extracted in Sessions 03–07):
    p2p.py      — point-to-point track/via builder
    ladder.py   — via-array + per-layer strip builder for pours
    mesh.py     — rasterised pour-grid builder
"""
