# PathMiner v0.13 Repository Map

## Current shape

- `tools/pcb_trace_resistance.py` is the working v0.13 monolith and contains the GUI, CLI, parsing, physics, solvers, reports, and aggregate self-test.
- `schema/pcb_net_selection.schema.json` is the existing saved-selection contract.
- `documents/via_tab_design_contract.md` contains accepted formulas and stable acceptance-vector detail.
- `documents/path_capture_design.md` specifies ordered multi-net path capture.
- `documents/library_refactor_recommendations.md` describes proposed package boundaries and extraction order.
- `ai_reference/` contains example selections, reports, and the reference KiCad project archive.

## Hotspot rule

The monolith, package export hubs, schema registries, report registry, and release documents are shared hotspots. Only sessions whose owned scope names one of these may modify it. Extraction sessions 03–07 add isolated modules/tests; Session 08 is the compatibility-facade integrator.

## Packaged files

- `README.md`
- `ai_reference/code_samples/.gitkeep`
- `ai_reference/doc_samples/PACK_P_report.md`
- `ai_reference/doc_samples/PACK_P_report.pdf`
- `ai_reference/doc_samples/resistance_report.md`
- `ai_reference/examples/net_selection_PACK.json`
- `ai_reference/examples/nets.example.json`
- `ai_reference/kicad_project_example/Ref_PowerBank_injoinic_IP5385_v0.8.zip`
- `core/.gitkeep`
- `documents/change_log.md`
- `documents/help/.gitkeep`
- `documents/library_refactor_recommendations.md`
- `documents/path_capture_design.md`
- `documents/user_guides/.gitkeep`
- `documents/via_tab_design_contract.md`
- `schema/pcb_net_selection.schema.json`
- `tests/.gitkeep`
- `tools/pcb_trace_resistance.py`
- `ui/.gitkeep`
- `ui/common/.gitkeep`
- `ui/dialogs/.gitkeep`
- `ui/tabs/.gitkeep`
- `ui/themes/.gitkeep`
- `ui/widgets/.gitkeep`
