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

"""pathminer.report — serialisation and rendering.

Layer contract: imports analysis (and transitively core, kicad, models).
No Qt.  No wx.
Provides the report registry: each report type registers an ID, options
schema, runner, and renderers (text, Markdown, PDF).

Planned modules (extracted in later sessions):
    netsel.py   — net-selection JSON read/write
    render.py   — text, Markdown, and PDF renderers
    registry.py — report-type registration and dispatch
"""
