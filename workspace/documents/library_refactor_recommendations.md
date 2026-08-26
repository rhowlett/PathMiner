<!-- v0.2 -->
# PathMiner — from script to library, architecture review

Subject: `pcb_trace_resistance.py` v0.13, 5546 lines, 88 top-level symbols.
Scope: structural review only. No code changed.
Purpose: split into reusable modules, support more analyses and report types, enable a KiCad
plugin, and stop a 5k-line script becoming a 20k-line one.

---

## 1. What the measurements say

I parsed the file and mapped every top-level symbol, its size, and its dependency direction.

| | Lines | Share |
|---|---|---|
| Qt-touching symbols | 2523 | 45% |
| Pure-Python symbols | 2297 | 41% |
| Selftest vectors | 788 | 14% |

**The single most important finding: the core has no Qt dependency.** I looked for pure
symbols that reference Qt ones and found exactly one — a selftest vector that deliberately
constructs a `MainWindow` to test the GUI. Nothing in the physics, parsing, graph building,
solving, or reporting touches the UI.

That means this is an **extraction, not a rewrite**. The seams already exist; the file just
doesn't have folders.

The second finding is where the growth risk actually is. The UI is 45% of the code and the
physics another program would want to borrow is *tiny*:

| Proposed module | Lines |
|---|---|
| `core/units.py` | 8 |
| `core/materials.py` — trace, via, barrel, tempco, IPC rise | 37 |
| `core/solver.py` — dense, CG, scipy, calibration | 213 |
| `core/geometry.py` — polygons, arcs, clustering | 137 |
| `kicad/sexpr.py` | 45 |
| `kicad/stackup.py` | 131 |
| `kicad/board.py` | 269 |
| `kicad/prefs.py` | 65 |
| `models/graph.py` | 218 |
| `models/mesh.py` | 61 |
| `models/path.py` | 154 |
| `analysis/resistance.py` | 160 |
| `report/netsel.py` | 100 |
| `report/render.py` | 230 |
| `ui/` (7 tabs/widgets + helpers) | 2150 |
| `tests/` | 788 |

**37 lines is the answer to "I just want the resistance calculation in another program."**
`core/materials.py` plus `core/units.py` is a 45-line drop-in with no dependencies at all — not
scipy, not Qt, not KiCad.

---

## 2. Recommendations

### R1 — Layer strictly, and enforce the direction

```
core/        pure physics and maths. No KiCad, no Qt, no I/O.
kicad/       file formats and the live board. Imports core. No Qt.
models/      geometry -> resistor network. Imports core + kicad.
analysis/    orchestration: which pairs, which model, collect results.
report/      serialisation and rendering. Imports analysis.
ui/          Qt. Imports everything. Nothing imports ui.
```

Add a test that asserts the direction — walk each module's imports and fail if `core` imports
anything above it. It is the one rule that will actually decay without a guard, and it is five
lines of `ast` to check.

### R2 — The three resistance models are one solver and three builders

You proposed `p2p_resistance.py`, `ladder_resistance.py`, `mesh_resistance.py` with a common
input and output. I'd adjust the seam slightly, because the measurements show these three
already share a solver and differ only in how they *build the network*:

```
geometry ──► [builder] ──► ResistorNetwork ──► [solver] ──► TwoTerminalResult
```

Writing them as three parallel implementations would triplicate `network_resistance`,
`solve_cg` and `_solve_scipy` — 213 lines each time, and three places to fix the next
singular-matrix bug. Instead:

```python
# core/network.py — the common structure, ~40 lines
@dataclass(frozen=True)
class Edge:
    a: Hashable; b: Hashable; ohms: float
    kind: str = ""            # trace | via | pour | mesh — provenance for reports
    meta: dict = field(default_factory=dict)

@dataclass
class ResistorNetwork:
    edges: list[Edge]
    def solve(self, a, b) -> TwoTerminalResult: ...

@dataclass(frozen=True)
class TwoTerminalResult:
    ohms: float
    path: list[Edge]          # least-resistance route, itemised
    path_ohms: float
    nodes: int
    seconds: float
    backend: str              # "dense" | "cg" | "scipy"
    notes: list[str]
```

Then each model file is small and independently usable:

| File | Builds | Standalone use |
|---|---|---|
| `models/p2p.py` | Track segments and vias between two points | Give it segments; no KiCad needed |
| `models/ladder.py` | Via array + per-layer strips over a pour | Stitched bus resistance |
| `models/mesh.py` | Rasterised pour grid | Any pour shape |

All three return a `ResistorNetwork`. One solver, one bug surface, and a caller can mix them —
which the tool already does per-pair.

**Keep a one-call convenience layer on top**, because that is the actual ask:

```python
from pathminer import trace_ohms, via_ohms, p2p_ohms
trace_ohms(length_mm=50, width_mm=0.1, thickness_um=35)      # -> float
via_ohms(drill_mm=0.3, plating_um=18, span_mm=1.6)           # -> float
p2p_ohms(segments, vias, stackup)                            # -> TwoTerminalResult
```

Someone borrowing this for another tool should not have to learn `ResistorNetwork`.

### R3 — Do not write the C executables

Measured on this machine, a 6400-node grid:

| Approach | Time | Cost |
|---|---|---|
| In-tree Python CG | ~7 s | already written |
| scipy `spsolve` | 77 ms | one import |
| scipy `splu` + reuse | 24 ms + 0.9 ms per extra pair | one import |
| C + OpenMP | ~20–40 ms est. | toolchain, per-platform binaries |

Sparse matvec is memory-bandwidth-bound, so threading adds maybe 2–4× over compiled code,
against 100–400× for the import. **And a compiled dependency actively fights the KiCad plugin
goal** (R5): plugins run inside KiCad's bundled Python, where you cannot assume a compiler or
ship a wheel per platform.

The remaining win is algorithmic and pure-Python: factor the Laplacian **once per net** and
back-substitute per pair. The report solves N pairs on one graph and currently re-solves from
scratch each time. That is the optimisation to do; C is not.

### R4 — Make the board a protocol, not a parser

`BoardNets` is 269 lines and 8 callers — the highest fan-in in the file. It currently means
"parsed `.kicad_pcb`". For the plugin it must also mean "live `pcbnew` board".

```python
class BoardSource(Protocol):
    def nets(self) -> list[NetInfo]: ...
    def tracks(self, net) -> list[Track]: ...
    def vias(self, net) -> list[Via]: ...
    def pads(self, net) -> list[Pad]: ...
    def pours(self, net) -> list[Pour]: ...
    def stackup(self) -> Stackup: ...
```

Two implementations: `kicad/file_board.py` (today's parser) and `kicad/live_board.py`
(`pcbnew`). Everything above `kicad/` becomes source-agnostic. **Define this before the plugin
work starts**, or the plugin becomes a fork.

### R5 — Plugin constraints that change the design now

- KiCad's plugin API is Python inside KiCad's interpreter. **scipy may not be there** — so the
  pure-Python CG stops being a nicety and becomes a hard requirement. Keep the fallback and
  keep V20's "both backends agree" vector.
- KiCad's own UI is wxPython. A PySide6 app cannot be embedded. So the plugin should be a thin
  wx dialog over `analysis/` + `report/`, which only works if R1 holds.
- The plugin entry point is small: get selection → net → `analyse_net` → `report_markdown` →
  show or save. If that is more than ~150 lines, the layering is wrong.

### R6 — Report types become a registry, not a longer tab

`ReportTab` is 699 lines, already the largest symbol in the file. Adding four report types by
editing it is how 5k becomes 20k.

```python
@register_report("resistance")
class ResistanceReport(Report):
    id, title, options_schema
    def run(self, board, selection, opts, progress) -> ReportResult
    def render(self, result, fmt) -> str | bytes
```

The UI enumerates the registry and builds its controls from `options_schema` — which is
exactly the metadata-driven approach GRUN already uses for CLI tools. One new report type is
then one new file plus a decorator, and the CLI gets it for free.

### R7 — Extract the generic widgets into a shared UI kit

`CollapsibleSection` (59), `TransferList` (55), the files table, `_num_edit`, `_pair`,
`_small`, `_hline` — none of these know anything about PCBs. They are the beginnings of the
house style you mentioned wanting to standardise. Put them in a `qtkit` package that this tool
and GRUN both depend on. Roughly 250 lines today, and it stops the next tool re-deriving a
disclosure triangle.

### R8 — Pad the seams that are already leaking

Small things the analysis surfaced, worth fixing during the split rather than after:

- **`Q` is a terrible module-level constant name** (coordinate quantisation). It collided with
  Qt naming badly enough that my own dependency analyser produced two false positives on it.
  Rename to `QUANT_DP` in `core/geometry.py`.
- **`_solve_dense`, `solve_cg`, `_solve_scipy` have inconsistent privacy.** They are the same
  role; make all three public in `core/solver.py` with one dispatcher.
- **`DEFAULT_OPTIONS` and `NETSEL_SCHEMA` are one concept in two places** and must be edited
  together — a defect waiting to happen. Generate the defaults *from* the schema.
- **`selftest` is 345 lines and knows about every layer**, including the GUI. Split per module
  (`tests/test_materials.py`, `test_solver.py`, …) and keep an aggregate `--selftest`. The
  V15–V23 vectors already partition cleanly along the proposed module lines.

### R9 — Multi-net paths through components need a data model, not a code change

"From one pad, through different components, to an end sink" is a *bridging* problem: a fuse,
FET, shunt or connector joins two nets that the board file deliberately keeps separate. The
graph work is trivial once the data exists — add an edge between two pads on different nets.
The hard part is where the resistance comes from:

```json
{ "bridges": [
  { "ref": "F1",  "from": "1", "to": "2", "ohms": 0.002,  "source": "datasheet" },
  { "ref": "Q3",  "from": "S", "to": "D", "ohms": 0.0021, "source": "Rds_on @ 4.5V" },
  { "ref": "R20", "from": "1", "to": "2", "ohms": 0.001,  "source": "shunt value" }
]}
```

Three ways to populate it, in increasing order of effort: hand-written JSON; from the BOM/
schematic (which is why targeting the `.kicad_pro` rather than the `.kicad_pcb` was the right
call); or a component library keyed by MPN. **Start with hand-written JSON** — it is a new
schema file and about 30 lines of graph code, and it unblocks the end-to-end battery-to-load
question immediately.

Note this makes the result a *system* resistance, and the report should say which bridges were
applied and where each value came from. A silent 2.1 mΩ FET is exactly the kind of assumption
that has bitten twice already in this project.

### R10 — Package it properly, and keep a single-file escape hatch

```
pathminer/                 installable package
  core/  kicad/  models/  analysis/  report/  ui/
tools/build_single_file.py  concatenate for drop-in use
```

The single-file form has been genuinely useful — you have run `--selftest` and `--report` all
through this project. Don't lose it; **generate** it from the package instead. A build script
that concatenates in dependency order and asserts the result passes the full selftest gives
you both, and the assertion catches import-order mistakes the package form would hide.

---

## 3. Suggested order

Each step leaves the tool working and the selftest green.

1. `core/` — units, materials, solver, geometry. Zero risk; nothing depends on Qt.
2. `kicad/` — sexpr, stackup, board, prefs. Introduce `BoardSource` (R4) at this point.
3. `core/network.py` + `models/` — the common structure and three builders (R2).
4. `analysis/` and `report/`, with the report registry (R6).
5. `ui/`, extracting `qtkit` (R7) on the way out.
6. Single-file build script (R10), asserting selftest parity.
7. Then, and only then, the plugin (R5) and bridges (R9).

Steps 1–2 are mechanical and could be done in an afternoon. Step 3 is the only one requiring
real design thought.

---

## 4. Questions I need answered

**Q1 — Public API surface.** The package is `pathminer` (D9). What is the supported top-level
import: the convenience functions (R2), or the full dataclasses? This decides what you may
refactor later without breaking your other tools.

**Q2 — Is scipy allowed as an optional dependency of the library**, or must the published
package be standard-library-only with scipy purely opportunistic? The plugin argues for the
latter; report runtimes on big boards argue for the former.

**Q3 — Does the KiCad plugin need the full report UI, or is "selected net → report file →
open it" enough for v1?** The answer changes whether `qtkit` needs a wx sibling or whether the
plugin stays dialog-free.

**Q4 — What are the other report types you have in mind?** Their shape determines whether
`ReportResult` (R6) needs to be generic over per-pair rows, per-net rows, or per-board rows. I
would rather design the registry against three real examples than one.

**Q5 — For component bridges (R9), do you want values hand-entered, pulled from the BOM, or
looked up by MPN?** And should a missing bridge value be an error, or an open circuit with a
warning?

**Q6 — Is `docs/change_log.md` per-package or per-module?** Per-file version tags are
unambiguous, but with ~16 files the single project log is the readable choice; confirm before
the split so the baseline entry is right.

**Q7 — Do you want the selftest vectors to move with their modules** (V21 geometry →
`tests/test_geometry.py`) and lose their V-numbers, or keep the V-numbering as a stable index
across files? The numbers have been useful in conversation; they will look arbitrary inside a
per-module test file.
