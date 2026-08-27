# Package Build Validation

- Package creation date: 2026-08-26
- Packaging Python: 3.12.13
- PySide6 available during packaging: false
- Baseline `--selftest`: not completed in the packaging environment because PySide6 is not installed
- Archive integrity: both distributable ZIP files are validated after generation by the packaging workflow.
- Catalog integrity: 34 sessions, 34 ChatGPT prompts, 34 Claude prompts, contiguous dependencies, and all 90 punch-list identifiers covered.

The canonical acceptance gate is three verifiable suites (all committed to the repo):

1. **118/118 headless selftest** — `python3 tools/pcb_trace_resistance.py --selftest`
2. **284/284 IP5385 real-board selftest** — uses `ai_reference/kicad_project_example/Ref_PowerBank_injoinic_IP5385_v0.8.kicad_pcb`
3. **IP5385 batch report (1 net, 11 pairs)** — uses the same board with `net_selection_PACK.json`

Session 01 reproduced and recorded all three in the development environment.
Executable regression comparison: `python3 tests/baseline/regression_compare.py all` (exit 0 = baseline intact).

Historical note: the supplied project records referenced a 254/254 "reference board" suite.
That board file is not part of the committed repo. The canonical baseline does not require it;
the IP5385 project (committed to `ai_reference/kicad_project_example/`) is the authoritative
board-level gate.
