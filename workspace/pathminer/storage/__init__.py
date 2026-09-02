# v0.1
"""pathminer.storage — project files, atomic writes, schema migration.

Layer contract: imports core, kicad, and analysis contracts.  No Qt.  No wx.
Owns the .pathminer/ project directory, versioned JSON schemas, atomic write
helper, and v0.13 → current migration logic.

Planned modules (later sessions):
    project.py   — .pathminer/ layout, discovery, initialization
    atomic.py    — validate → write-tmp → flush → replace helper
    migrate.py   — schema version detection and in-memory migration
"""
