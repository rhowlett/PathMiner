<!-- v0.1 -->
# PathMiner

DC resistance analysis for KiCad PCBs. Reads a `.kicad_pcb` — stackup, tracks, arcs, vias,
pads, filled zones — and answers *"what is the resistance from this pad to that pad, and does
the design pass?"*

It traces real routed copper into a resistor network, derives via barrel spans from the layers
that actually land on them (never from the via's declared layers), models stitched pours as
either a fast 1-D ladder or a rasterised mesh, and solves the whole net by nodal analysis so
parallel copper counts. Output is point-to-point resistance, voltage drop, endpoint voltage and
temperature rise, in Markdown, text, PDF or JSON, driven by a schema-validated JSON
net-selection file so the same audit re-runs from the CLI against every board revision.

## Status

**Working application, pre-split.** All functionality currently lives in the single file
`tools/pcb_trace_resistance.py` (v0.13, 5546 lines). The package folders `core/`, `ui/`,
`tests/` and `schema/` are scaffolded but empty; the split is designed in
`documents/library_refactor_recommendations.md` and has not been executed.

| Selftest | Result |
|---|---|
| Reference test board | 254 / 254 |
| Real 4-layer power bank | 284 / 284 |
| Headless, no board | 118 / 118 |

## Running it

```bash
python3 tools/pcb_trace_resistance.py                       # GUI
python3 tools/pcb_trace_resistance.py board.kicad_pcb       # GUI, board preloaded

python3 tools/pcb_trace_resistance.py --selftest [board.kicad_pcb]
python3 tools/pcb_trace_resistance.py --dump-stackup board.kicad_pcb [--plating 25] [--outer-plating]
python3 tools/pcb_trace_resistance.py --emit-schema [file.json]
python3 tools/pcb_trace_resistance.py --emit-nets board.kicad_pcb --out sel.json
python3 tools/pcb_trace_resistance.py --report board.kicad_pcb --nets sel.json \
        [--plating 18] [--zone-model none|ladder|mesh] [--mesh-pitch 0.25] \
        [--ambient 25] [--current 1] [--format md|txt|json] [--out FILE]
```

Requires **PySide6** for the GUI. `scipy` is optional and used automatically when present —
two to three orders of magnitude faster on meshed pours — with a pure-Python conjugate
gradient fallback when it is absent. The fallback is not optional going forward: a KiCad
plugin runs inside KiCad's bundled interpreter, where scipy may not exist.

## Tree

```
pathminer/
  core/                 business logic, no UI imports          (scaffolded, empty)
  ui/                   Qt layer                               (scaffolded, empty)
    tabs/ common/ dialogs/ themes/ widgets/
  tools/                dev and maintenance scripts
    pcb_trace_resistance.py     the working application, v0.13
  tests/                                                       (scaffolded, empty)
  schema/               data models, validation
    pcb_net_selection.schema.json
  ai_reference/
    code_samples/ doc_samples/ examples/
  documents/
    change_log.md
    via_tab_design_contract.md            the resistance model, D1-D8 closed
    library_refactor_recommendations.md   how to split this into a library, R1-R10
    path_capture_design.md                KiCad plugin + path JSON, D1-D10 closed
    help/ user_guides/
  README.md
```

## Documents

Read them in this order:

1. **`via_tab_design_contract.md`** — what the tool computes and why. Decisions D1–D8 with the
   evidence that closed them, the acceptance vectors, and the KiCad file-format gotchas found
   the hard way (layer ordinals are not stack order; a via's declared layers are the drilled
   barrel, not the current path; a zone fill is cut back around every pad it serves).
2. **`library_refactor_recommendations.md`** — R1–R10 for splitting this into a reusable
   package, with the measured evidence that the core has no Qt dependency and the case against
   writing C.
3. **`path_capture_design.md`** — the KiCad plugin, the path JSON schema, source and sink
   models, and D1–D10.

## Conventions

Per-file version tags on line 1 (line 2 after a shebang), Minor bumped on every change, one
change log at `documents/change_log.md`. Every delivery is a zip of this full tree. See
`documents/change_log.md` for the rules.
