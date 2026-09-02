# v0.1
"""pathminer.ui — Qt widgets and application shell.

Layer contract: imports everything (core, kicad, models, analysis, report,
storage, cli).  NOTHING outside this sub-package may import pathminer.ui.
This rule is enforced by tests/test_import_boundaries.py.

The full GUI is implemented in tools/pcb_trace_resistance.py (v0.13) and
will be extracted into this sub-package in later UI sessions.

Planned modules (later sessions):
    app.py          — QApplication setup and main window
    project.py      — Project destination widget
    investigation.py — Investigation browser and selection widget
    analysis.py     — Analysis configure/run widget
    reports.py      — Reports destination (completed-run consumer)
    diagnostics.py  — Diagnostics destination
    widgets/        — shared reusable widgets
"""
