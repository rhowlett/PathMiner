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

"""pathminer.analysis — analysis orchestration.

Layer contract: imports core, kicad, and models.  No Qt.  No wx.
Selects which pair list, which resistance model, and which solver;
collects and returns typed result records.

Planned modules (extracted in Sessions 07–08):
    resistance.py — point-to-point resistance analysis runner
"""
