# v0.2
"""PathMiner — PCB power-path and resistance analysis package.

This is the package root.  Code is being extracted from
``tools/pcb_trace_resistance.py`` (v0.13) in subsequent sessions.
Sub-packages are empty stubs at this point in the refactor (Session 02).

Session 08 (BASE-004, ARCH-006, ARCH-010) turned ``tools/pcb_trace_resistance.py``
into a compatibility facade over the modules extracted so far: its numerical
solver dispatcher and pure planar-geometry helpers are now aliases onto
``pathminer.core.solver`` / ``pathminer.core.geometry`` (Sessions 03/04/07)
rather than duplicated copies, and ``tools/build_single_file.py`` regenerates
a self-contained single-file distribution from that facade. KiCad parsing,
board modelling, network/builder wiring, and the GUI remain independent in
the legacy script pending their own integration sessions.

Package layer contract (ARCH-001 / ARCH-002):

    core/       Pure physics and maths.  No KiCad, no Qt, no I/O.
    kicad/      File formats and the live board.  Imports core.  No Qt.
    models/     Geometry → resistor network.  Imports core + kicad.
    analysis/   Orchestration: pairs, model selection, result collection.
    report/     Serialisation and rendering.  Imports analysis.
    storage/    Project files, atomic writes, schema migration.
    cli/        Command-line entry points.  Imports analysis + report.
    ui/         Qt widgets.  Imports everything.  Nothing may import ui.
    plugin/     KiCad plugin shim.  Imports kicad + analysis.

Nothing above ``core`` may be imported by ``core``.
Nothing at all may import ``ui`` except ``ui`` itself.
These rules are enforced by ``tests/test_import_boundaries.py``.
"""

__version__ = "0.14.0.dev0"
__all__: list[str] = []
