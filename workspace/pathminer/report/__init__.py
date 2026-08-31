# v0.1
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
