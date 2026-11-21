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

"""pathminer.storage — project files, atomic writes, schema migration.

Layer contract: imports core, kicad, and analysis contracts.  No Qt.  No wx.
Owns the .pathminer/ project directory, versioned JSON schemas, atomic write
helper, and v0.13 → current migration logic.

Planned modules (later sessions):
    project.py   — .pathminer/ layout, discovery, initialization
    atomic.py    — validate → write-tmp → flush → replace helper
    migrate.py   — schema version detection and in-memory migration
"""
