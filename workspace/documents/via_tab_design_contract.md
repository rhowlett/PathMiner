<!-- v0.12 -->
# Via Resistance Tab — Design Contract

Target: `pcb_trace_resistance.py` v0.3. Standalone single-file PySide6 script.
Status: schema frozen; **implemented in v0.13. 284/284 on a real 4-layer board, 254/254 on the test board, 118/118 headless.**
Empirical basis: `Symbol_Testing.kicad_pcb` (KiCad 9.0, `version 20241229`), 4 layers,
mixed inner copper. Revised board adds a third part: 26 segments, 15 vias, and three
multi-terminal nets (/SDA, /SCL, NRST) that are trees with a T-junction.

---

## 1. Decision register — all closed

| ID | Decision | Evidence / rationale |
|---|---|---|
| **D1** | Path is an ordered **segment list**, not a fixed trace/via/trace form | Net 7 on the reference board is a real 3-via chain (F→B, B→In1, F→In1). A fixed form cannot express it. |
| **D2** | Barrel plating enterable as µm / mil / oz. **Amended v0.11:** defaults to the IPC-6012 Class 2 minimum, 18 µm, rather than being required; lives in Global settings and is printed with every result | Plating is a fab process parameter, distinct from foil weight, and present in **no** EDA file. `t=0` ⇒ zero area ⇒ divide-by-zero, so it cannot have a computable default. |
| **D3** | `A = π/4·(OD² − ID²)`. Default convention: **OD = the KiCad hole value**, `ID = OD − 2t`. Selector offers the finished-hole reading | Owner-specified. Note the counter-evidence in §5; the alternative is 15 % lower resistance, so the convention is surfaced in the report, not buried. |
| **D4** | Barrel length is **centre-to-centre** by default; `facing` and `outer` selectable | ±39 % swing on an adjacent-layer hop. Centre-to-centre sits between the extremes and matches where current spreads into the landing copper. |
| **D5** | **Through vias only** | Zero blind/buried/micro vias in the corpus — no data to validate a cone model against. |
| **D6** | Stackup table is **editable after load**, with dirty marker and revert-to-file | Lets the designer sweep stackup variants without editing and reloading the board. |
| **D7** | Current and ambient are **global** across both tabs | — |
| **D8** | Outer-layer copper **adds plating thickness by default** (checkbox to disable). Plating grows **outward**; dielectric interfaces stay fixed and the board gets thicker | Panel plating deposits on F.Cu/B.Cu as well as in the barrel. Inner layers are foil only. Worth 25 % of the acceptance path. |

**Resolved out of scope for v0.3:** via ΔT (no defensible model — barrels are short and plane-heatsunk); automatic net tracing from the board file (needs zone/pad geometry matching, netdiff-shaped work).

---

## 2. Constants

```python
RHO_CU_20C = 1.724e-8    # ohm-m, IACS annealed copper @ 20 C          (existing)
ALPHA_CU   = 0.00393     # 1/K                                          (existing)
OZ_TO_UM   = 34.798      # um per oz/ft^2                               (existing)
```

Barrel copper reuses `RHO_CU_20C`. Electrodeposited plating is measurably more resistive than annealed foil, but no separate figure is justified without a measurement; recorded here as a known approximation, not an oversight.

---

## 3. Data model

### 3.1 Stackup

Ordered top→bottom. **Order comes from the stackup block's own sequence, never from layer ordinals** (§5).

```python
StackupLayer = {
    "name":      str,     # "F.Cu", "dielectric 1"
    "kind":      str,     # "copper" | "dielectric" | "mask" | "silk" | "paste"
    "type_raw":  str,     # KiCad's type string, e.g. "prepreg", "core"
    "base_mm":   float,   # as loaded from file
    "user_mm":   float,   # editable (D6); == base_mm until touched
    "dirty":     bool,
    "material":  str | None,
    "epsilon_r": float | None,
}
```

Derived per copper layer, recomputed whenever plating or D8 changes:

```python
CopperLayer = {
    "name":         str,
    "index_top":    int,   # 1-based from top
    "index_bottom": int,   # 1-based from bottom  -> both shown in pickers
    "is_outer":     bool,
    "foil_mm":      float, # user_mm
    "finished_mm":  float, # foil + plating if is_outer and D8 else foil
    "oz":           float, # finished_mm*1000 / OZ_TO_UM
    "z_top_mm":     float,
    "z_ctr_mm":     float,
}
```

**Z-assignment rule (D8).** Dielectric interfaces are fixed. Inner layers keep both faces. `F.Cu` is pinned at its **lower** face and grows upward; `B.Cu` is pinned at its **upper** face and grows downward. Board thickness therefore increases by `2 × plating`.

### 3.2 Path segments

```python
TraceSegment = {
    "kind": "trace",
    "layer": str,            # copper layer name -> thickness from stackup
    "length": (value, unit), # mil | mm
    "width":  (value, unit),
}

ViaSegment = {
    "kind": "via",
    "from_layer": str,       # REQUIRED user input, never from the via token
    "to_layer":   str,
    "hole":  (value, unit),  # mm | mil, interpreted per D3 convention
    "pad":   (value, unit),  # annular-ring check only, not resistance
    "count": int,            # parallel vias
    "sharing_pct": float,    # default 100
}
```

### 3.3 Global settings

`plating` (required, µm/mil/oz) · `drill_convention` ∈ {bit, finished} · `length_convention` ∈ {facing, centre, outer} · `outer_plating_adds` (bool) · `current_a` · `ambient` (shared with trace tab per D7).

---

## 4. Formulas

```
Trace       R = ρ·L / (W · t_finished)

Barrel      OD, ID per D3 convention:
              bit:      OD = hole,      ID = OD − 2·t_plate
              finished: ID = hole,      OD = ID + 2·t_plate
            A = π/4·(OD² − ID²)
            L = |z(a) − z(b)| per D4 convention
            R = ρ·L / A
            R_array = R / (count · sharing_pct/100)

Path        R_total = Σ R_segment        (series; D4 — the via is a plain series element)
            R_hot   = R_total · (1 + α·(T − 20))
            drop    = I · R_hot
            power   = I² · R_hot
```

**Guards.** `2·t_plate ≥ OD` ⇒ hard error, "hole closed by plating". `ID < 50 µm` ⇒ warn. Plating unset ⇒ blank result, "select plating thickness". Annular ring `(pad − hole)/2` checked against `design_settings.rules.min_via_annular_width` from the `.kicad_pro` when loaded, else IPC-6012 Class 2 (0.05 mm).

---

## 5. KiCad parsing contract

Source of truth: `.kicad_pcb` `(setup (stackup ...))`. All values mm.

**Six gotchas, each observed in the reference board:**

1. **Layer ordinals are not stack order.** `F.Cu=0, In1.Cu=4, In2.Cu=6, B.Cu=2` — sorting by ordinal puts B.Cu second from top. Use the stackup block's sequence.
2. **The via token's `(layers ...)` is the physical barrel, not the electrical span.** All 12 vias declare `F.Cu`/`B.Cu`; actual spans are F→In1, F→In2, B→In1, B→In2, F→B — a 9.6× resistance spread. Entry/exit is user input. Always.
3. **`(general (thickness 1.67))` includes solder mask.** Copper + dielectric is 1.65. Never a barrel span.
4. **`uuid`, not `tstamp`.** Dev docs are stale for KiCad 9. Accept both.
5. **Net classes live in `.kicad_pro`** (`net_settings.classes`), and classes may **omit** `track_width`/`via_diameter` entirely rather than restating them — "Signal" and "Terminal Block" both do. Fall back to Default, never `KeyError`.
6. **The stackup block is optional.** Absent ⇒ fall back to `general.thickness` with even dielectric distribution, and flag the estimate.

S-expression parsing reuses the existing head-skipping accessor (each list node's head atom appears both as `node.head` and as `children[0]`).

**Harvested for convenience, not required:** distinct via geometries with counts (reference board: `0.6/0.3 ×12`) to populate a pick-list.

---

## 6. Acceptance vectors — `--selftest` asserts these

Reference board, plating 25 µm, defaults `bit` / `centre` / D8 ON.

**V1 — stackup parse**

| Layer | finished | oz | z_ctr |
|---|---|---|---|
| F.Cu | 60.0 µm | 1.724 | 0.0050 |
| In1.Cu | 70.0 µm | 2.012 | 0.1700 |
| In2.Cu | 70.0 µm | 2.012 | 1.4800 |
| B.Cu | 60.0 µm | 1.724 | 1.6450 |

**Z origin** is the top of the copper+dielectric stack, mask excluded — the mask is applied
after plating and is not part of any barrel span. Only z *differences* enter the math, so the
origin is free; it is pinned here so the numbers above are reproducible.

Board Cu+dielectric: 1.6500 unplated → 1.7000 plated. `general` = 1.67 incl. mask.

**V2 — barrel R, 0.3 hole**

| Span | L (mm) | R |
|---|---|---|
| F.Cu → In1.Cu | 0.1650 | 131.70 µΩ |
| F.Cu → In2.Cu | 1.4750 | 1177.35 µΩ |
| B.Cu → In1.Cu | 1.4750 | 1177.35 µΩ |
| B.Cu → In2.Cu | 0.1650 | 131.70 µΩ |
| F.Cu → B.Cu | 1.6400 | 1309.06 µΩ |

Symmetric stackup ⇒ F→In1 == B→In2 and F→In2 == B→In1. Asymmetry here means the z-assignment is wrong.

**V3 — D4 options, F.Cu→In1.Cu:** facing 0.1000 mm / 79.82 µΩ · centre 0.1650 / 131.70 · outer 0.2300 / 183.59.

**V4 — D3 options, F.Cu→B.Cu:** bit OD 0.300 ID 0.250 A 21598.4 µm² → 1309.06 µΩ · finished OD 0.350 ID 0.300 A 25525.4 µm² → 1107.66 µΩ.

**V5 — acceptance path**, 50×4 mil F.Cu → via → 50×4 mil In2.Cu:

| D8 | F.Cu | via | In2.Cu | total | via share |
|---|---|---|---|---|---|
| ON | 3591.7 µΩ | 1177.4 µΩ | 3078.6 µΩ | **7.8476 mΩ** | 15.0 % |
| OFF | 6157.1 | 1167.4 | 3078.6 | 10.4031 mΩ | 11.2 % |

**V6 — parallel vias** (D8 ON): n=1 → 7.8476 · n=2 → 7.2589 · n=4 → 6.9646 · n=8 → 6.8174 mΩ.
Four vias buy 11 %: the barrel was never the bottleneck. The per-segment % column exists to make this obvious.

**V7 — guards:** `0.3 + 150 µm` ⇒ ValueError · `0.3 + 149 µm` ⇒ ID 2.0 µm, valid + warn · plating unset ⇒ blank.

**V8 — algebraic identity:** `π/4·(OD²−ID²) == π·t·(ID+t)` to 1e-20. Both forms present in the selftest so a future refactor can't silently swap conventions.

---

## 7. UI structure

`QTabWidget`: **Trace** (existing v0.2, unchanged behaviour) · **Via / Path** (new) · **Stackup** (table).

Shared header above the tabs: current, ambient + °C/°F (D7).

Stackup tab: load `.kicad_pcb`, editable thickness per row shown simultaneously in µm/mil/oz, dirty marker, revert-to-file, manual-entry mode for no-file use (D6).

Via/Path tab: global via settings (plating — required, drill convention, length convention, D8 checkbox); segment list with add/remove/reorder; results as a per-segment table (R, R_hot, % of path) plus totals, drop, and power.

Every assumption in force (plating, both conventions, D8 state) prints in the results block. A number without its conventions is not reportable.

---

## 8. Build sequence

1. Stackup loader, headless, `--dump-stackup` prints the V1 table. No Qt.
2. Via/trace math + `--selftest` asserting V1–V8.
3. Stackup tab.
4. Via/Path tab.
5. Wire globals per D7; verify the Trace tab's v0.2 numbers are unchanged when D8 is off.

Step 5 matters: D8 changes outer-layer trace resistance, so the existing tab's answers move. That is a deliberate correction, and it needs a change-log entry saying so.

---

## 9. Implementation status (v0.3)

Built and passing: s-expression parser with head-skipping accessor · stackup loader ·
`--dump-stackup` · `--selftest` (V1–V8, V9 arc length, V10 net tracing, plus eight
v0.2 regressions) ·
editable stackup table with dirty markers and revert · manual fallback · tabbed UI ·
shared globals · segment-chain via/path tab with parallel arrays and sharing derate ·
board-net tracing with named pad-to-pad endpoint picker, resistance-weighted
path search, and whole-network nodal solution.

## 10. Net tracing (v0.4)

Builds the segment chain from routed copper instead of hand entry.

**Graph.** Nodes are `(layer, point)`, points quantised to 0.1 µm. Track and arc edges carry
layer, width and length (arcs use true arc length through start/mid/end). Pads contribute
terminals, with footprint rotation applied.

**Via spans are derived, never declared.** For each via, the set of copper layers with a track
endpoint or pad landing at that point defines the electrical span. Ordered by stackup z, a via
landing on three or more layers becomes series sub-barrels rather than one span.

**Endpoints** come from footprint pads; a net with none falls back to two loose track ends.
The path is a Dijkstra shortest path, then consecutive same-layer same-width runs are merged.

**Warns on:** branches (net is not a series chain, so parallel or stub copper is being ignored),
zone nets (zone conduction unmodelled, real resistance is lower), broken routes, blind/micro
vias, vias with fewer than two landing layers, tracks on layers absent from the stackup.

**Known limits.** Zone copper is not a conductor in this model. Pad-internal resistance is
ignored. Only the traced path is reported, not the full parallel network.

## 11. Pad-to-pad resistance (v0.5)

**Endpoints are named**, `REF.PINFUNCTION` with `REF.PAD` as fallback, so a query reads
`Z1.SDA -> Z3.SDA`. Resistance is only defined between two points, so a net with three or
more terminals requires an explicit pair.

**Least resistance, not least length.** The Dijkstra weight is each edge's computed
resistance, which needs plating and the stackup. Without a plating value the tool says so
and falls back to physical length — width, layer copper weight and via span all change which
route is actually cheapest.

**Two numbers, because they answer different questions.**

- *Least-resistance path* — the single best route, itemised in the results table.
- *Network resistance* — nodal analysis over the whole net (ground one terminal, inject 1 A
  at the other, `R = V`), which counts every parallel branch.

Equal values mean the extra copper is a stub carrying no current. A lower network value means
parallel copper is sharing current and the path figure is pessimistic. The solver is dense
Gauss-Jordan with partial pivoting; nets are tens of nodes, so this is free.

**V11 validates the solver** on hand-computable topologies: series, parallel, series-parallel,
balanced and unbalanced Wheatstone bridges, a stub, and ten-way parallel. The unbalanced bridge
is the one that matters — it cannot be reduced by series/parallel collapsing, and it agrees
with an independent numpy solve to 1e-12.

## 12. Zone copper and via arrays (v0.6)

**Mid-run via splitting.** KiCad does not break a track where a via lands on its interior,
so an endpoint-only landing test drops stitching arrays entirely. Every track is now split
at any via lying on it. Needed regardless of pours.

**Pours.** `filled_polygon` is parsed per layer; the principal axis, length and width come
from an oriented bounding box. Tracks are clipped against the fill: copper inside the pour is
removed from the 1-D track graph, because the pour already models it and keeping both would
double count them in parallel. Boundary crossings and pads inside the fill are **merged** into
pour nodes by union-find, not joined with tiny resistors, which would wreck conditioning.

**Two models.**

| Model | Method | Cost |
|---|---|---|
| `ladder` (default) | Rung at every via, one strip per layer along the pour axis | ~40 nodes, sub-ms |
| `mesh` | Fill rasterised to a resistor grid, barrels merged as finite discs | 400–6000 nodes, 1–7 s |

Graphs above 400 nodes fall through to sparse conjugate gradient; below that, dense
Gauss-Jordan.

**Measured agreement** on `/SDA`, Z1.SDA → Z2.SDA: ladder 36.0502 mΩ; mesh 36.3319 (0.25 mm),
36.3367 (0.125), 36.4885 (0.0625). The ladder is 1.2% below the converged mesh at 1/100th the
cost. Zone ignored gives 53.6345 mΩ, so the pour is worth 33%.

**A single centroid lump was evaluated and rejected.** On a *transfer* array it is within 3%,
but on a *shunt* array — current in and out on the same layer, parallel layers as helpers —
it returns exactly the unstitched resistance. Parallel layers touching at one node are
dead-end stubs; a layer needs two spatially separated crossings before it can carry anything.
V14 pins this. Centroid and extent are still computed, for clustering and reporting.

**Limits.** The ladder assumes current flows along the pour's long axis; below 2:1 aspect it
warns and suggests the mesh. Thermal-relief spokes are not modelled. Pad-internal resistance
is ignored.

## 13. Net selection and reporting (v0.6)

JSON file with a draft-07 schema (`--emit-schema`) and a built-in validator that reports every
error with a JSON path. `select` then `ignore`, both glob-capable, **ignore always wins**;
unmatched patterns are reported rather than silently doing nothing. `options` carries plating,
both conventions, zone model, mesh pitch, ambient and current. Plating still has no default.

`--report` walks every pad pair on every selected net and emits Markdown, text or JSON:
assumptions, stackup, selection with reasons for each skip, a summary table, and a per-pair
element breakdown with each element's share.

## 14. Report tab and pair strategy (v0.7)

**Point-to-point is a per-net rule**, because resistance is only defined between two pads and
`all` grows as N(N-1)/2 — fine at 3 terminals, 190 rows at 20.

| Rule | Rows | Use |
|---|---|---|
| `all` | N(N-1)/2 | Small nets, exhaustive audit |
| `from-source` | N-1 | Power and fan-out: one supply or driver pad against every load |
| `first-two` | 1 | Smoke test |
| `explicit` | as listed | `["Z1.SDA>Z3.SDA"]` |

Stored per net under `nets` in the JSON. A live count shows the pad-pair total before running,
and `max_pairs_warn` (default 28) fires a note in the report.

**Tab layout.** File bar (Open / Save / Save As / New) that refuses to save a document the
schema rejects; two transfer lists seeded with every routed net, one for selection and one for
ignore, with ignore always winning and clashes named; the per-net pair table; zone model and
mesh pitch; format selector and preview.

Opening a file **expands globs to concrete net names** and says so, naming any pattern that
matched nothing. Saving writes concrete names, except an all-nets selection which stays `*`.
Electrical settings come from the Via/Path tab and the shared header, so there is one source
of truth.

**Export**: Markdown, text, JSON, and PDF via a small markdown-to-HTML converter into
`QPdfWriter`/`QTextDocument`.

**Regression worth recording.** The per-net pair mode was introduced as a local named `mode`,
which shadowed the barrel-length convention that the edge-pricing closure reads. Every pair in
every generated report failed to trace, and 149/149 checks still passed because nothing
exercised `analyse_net` or `build_report`. V16 now covers the report path end to end: pair
counts per strategy, no pair erroring, segments summing to the path, and all three renderers.
Coverage of the engine is not coverage of the product.

## 15. Voltage, overrides and layout (v0.8)

**Operating conditions** gained a default signal voltage beside current and ambient. The
summary now carries `V in | I | Drop | V out`, where `V out = V in - I*R_hot`. Resistance is a
property of the copper; voltage and current are what you push through it, so they are inputs
that never change the R columns — V17 asserts exactly that.

**Per-pair overrides.** Every resolved pad pair gets its own voltage and current cell. Blank
means "use the default". Overridden values are marked `*` in the summary so a reader can tell
a per-pair figure from a global one. Stored as `nets.<net>.pair_overrides` keyed `"A>B"`, and
matched in either direction so reversing a pair does not orphan its settings.

**Section toggles.** Six checkboxes — assumptions, stackup, selection, summary, detail, notes
— gate the report and persist in `options.sections`. The collapsible skipped-nets block is
gone; it listed every unselected net on a real board and told the reader nothing. The
selection section now names what was reported and what was explicitly ignored, and nothing
else.

**Layout.** Two columns under the shared operating-condition bar: file buttons, both transfer
lists and the point-to-point section on the left; report controls, assumptions strip, preview
and status on the right, in a draggable splitter.

**Bug worth recording.** Overrides did not survive a file open. `refresh_overrides` prunes its
map against the currently resolved pair list, and on open it ran *before* the per-net pair
modes were applied — so a `from-source` pair was not yet in the list and its override was
discarded. Compounding it, keys were matched in one direction only. Fixed by restoring
overrides after the modes are applied and matching either direction.

## 16. Collapsible layout (v0.9)

Back to a single scrollable column, each section behind a disclosure triangle: nets to report
on, nets to ignore, point-to-point pairs, and the report. Plus Expand all / Collapse all.

**Measured:** a collapsed section is one 23 px header row. All four together go from 1372 px
expanded to 92 px, so the preview can have the tab to itself without a splitter.

**Triangle, not a checkable QGroupBox.** The one-line `setCheckable(True)` puts a checkbox in
the title, and this tab already uses checkboxes to mean *include this section in the report*.
Two checkbox styles with different meanings on one page invites someone to uncheck a group and
wonder why it vanished from the PDF. A triangle can only mean show/hide.

**Headers carry live summaries** so a collapsed section still reports its state: selected
count, ignored count, pad-pair total, output format and zone model.

`TransferList` no longer draws its own `QGroupBox`; the section header owns the title.

**Test note.** V18 needs a `QApplication`, which a headless `--selftest` does not have — the
first version aborted the whole run. It now reuses a running instance or creates an offscreen
one, and records a skip if neither is possible.

## 17. Board loading and trace thickness source (v0.10)

**Board opens from the operating-conditions bar**, which names the file and its directory.
That directory is the default for net-selection JSON and for saved reports, so the selection
file lands beside the board rather than in whatever directory the app was launched from.
`ReportTab.default_dir()` derives it from `stackup.source`; no extra state to keep in sync.

**Trace tab is two columns**: geometry left with Calculate centred and sized to its text,
results and caveats right.

**Thickness has two sources**, behind radio buttons:

| Source | Thickness | IPC location |
|---|---|---|
| Copper weight (default) | oz from the dropdown | user picks external/internal |
| Stackup layer | finished thickness of that layer | **derived** from the layer's position |

The second is the better one when a board is open: the layer already knows whether it is outer
or inner, so `k` (0.048 vs 0.024) stops being a question the user can get wrong. On the
reference board a 1000x10 mil trace reads 49.26 mΩ / 13.18 °C on F.Cu but 24.63 mΩ / 20.33 °C
on In1.Cu — half the resistance and a *higher* rise, because inner copper is thicker but
poorly cooled.

Outer-layer plating (D8) from the Via/Path tab carries through: a 1 oz outer layer reads
60 µm at 25 µm plating. The stackup option is disabled with a tooltip until a `.kicad_pcb` is
open, and selecting it while no board is loaded is impossible rather than silently wrong.

V19 covers all of it, including that manual mode still reproduces the v0.2 number.

## 18. Timing, dedupe and per-pair models (v0.11)

**D2 amended.** Plating now defaults to 18 µm (IPC-6012 Class 2 minimum) instead of being
required. The original reasoning stands — it is the biggest single lever and appears in no
board file — so the mitigation is that the value in force is printed with every result and in
every report, and the default is the pessimistic end of the range rather than a flattering one.

**Terminals dedupe by name.** A footprint that repeats a pin name across pads — a split
thermal pad, a multi-pad supply pin — is one electrical terminal. Previously each pad became
its own terminal, so an N-pad pin multiplied the pair count and recomputed identical work. The
collapsed pads are kept as `aliases` and named in the notes.

**Per-pair zone model.** `pair_overrides` gained `zone_model` and `mesh_pitch_mm`, so one net
can price the cheap pairs with the ladder and the interesting one with the mesh. A graph is
built once per distinct model and reused by every pair that wants it.

**Time forecasting.** Two synthetic grids are timed once to fit `t = a·nodes^b` for this
machine. Each pair shows a forecast node count and solve time, with a running total. Reports
record the actual nodes, model and solve time per pair. On the reference board `/SDA` forecasts
80 nodes / 3 ms on the ladder against 472 / 12 ms meshed at 0.25 mm, 1768 at 0.125, 6888 at
0.0625 — the pitch-squared growth is visible before you commit to it.

**Streaming.** `build_report` takes a `progress` callback fired before and after each net; the
preview appends a line per net as it lands and the callback can cancel the run.

**Solver backend.** scipy is used when installed and the in-tree conjugate gradient when not.
Measured on this machine: `spsolve` at 6400 nodes takes 77 ms against roughly 7 s for the pure
Python CG. V20 asserts both backends return the same answer. **C was considered and rejected**
— see §19.

## 19. Why not C

The mesh solver is raw Python: `mesh_pour_edges` builds the grid, `solve_cg` is a
Jacobi-preconditioned conjugate gradient written in-tree, no libraries. So the question of
whether C would be faster is fair. Measured:

| Approach | 6400-node grid | Effort |
|---|---|---|
| In-tree Python CG | ~7 s | already written |
| scipy `spsolve` | 77 ms | one import |
| scipy `splu` factor + reuse | 24 ms + 0.9 ms per extra pair | one import |
| C with OpenMP | maybe 20–40 ms | build toolchain, per-platform binaries |

Sparse matvec is memory-bandwidth-bound, not compute-bound, so threading buys perhaps 2–4×
on top of compiled code — against 100–400× for the import. C would also cost the single-file
delivery. **The remaining win is algorithmic, not linguistic:** a Laplacian factorised once
per net answers every pad pair by back-substitution at ~1 ms each, instead of re-solving from
scratch per pair. That is worth doing before anyone writes C.

## 20. What a real board broke (v0.12)

First run on a 130-net, 1713-track, 431-via power bank. Four defects, none visible on the
small test board.

**Zone-only pads vanished.** Three of twelve `PACK_P` terminals were missing from the report,
silently. A filled zone is cut back around every pad it serves, so a pad connected only to the
pour has its centre *in a hole in the filled polygon* — containment says no, and with no track
landing either, the terminal was dropped. Pads now tie to the pour within 1 mm of real fill
copper. Measured to the polygon **edge**: the nearest-vertex test read 1.9 mm for what is
actually a 0.15 mm clearance gap. Relief spokes are not modelled, so those pads read slightly
optimistic and say so.

**Silent omission is itself a defect.** Unreachable terminals are now listed.

**scipy returns NaN on a disconnected graph** with only a stderr warning — the grounded
Laplacian is singular. Reachability is now checked before solving.

**The self-test assumed its own board.** Vectors hardcoding `/SDA` crashed elsewhere; they now
skip. V10's sweep is capped — this board's ground net has 95 pads, over 4000 pairs on its own.
And `network <= path` was asserted to 1e-9, tighter than the dense solver's precision: a pure
series chain gave 264325.400385 µΩ by path and 264325.400671 µΩ by network, a 1.1e-9 relative
difference that is arithmetic, not physics. Now 1e-6.

**The model held up.** Ladder against mesh on the real pour: 5.287 vs 6.181 mΩ near, 193.8 vs
195.5 mΩ far — under 1% where it matters, despite the pour being only 1.9:1 and the ladder
warning about it.

## 21. Consolidation (v0.13)

**Stackup tab becomes Setup** and owns everything set once, in four collapsible sections:
Files, Global settings, Via and zone modelling, Stackup. The global bar above the tabs is gone.
Trace, Via/Path and Report now *read* these settings rather than owning them, so there is one
control per concept. Via/Path echoes what is in force instead of duplicating the widgets.

**Zone model and mesh pitch moved off Report.** They are modelling choices, not report
formatting — the Via/Path tab uses them too. Per-pair overrides stay on Report, where the
pair-specific decisions live.

**Files table**: `[Open] | KiCad Project | File Name | Path`, one row each for the project, the
board and the net-selection JSON. The project is the target and its `.kicad_pcb` is opened for
board data; that leaves room to pull the schematic or netlist later without asking the user to
open anything twice. Opening a board directly still works and resolves its project backwards.
A board with no `.kicad_pro` beside it is normal and says so rather than pretending the board
is a project. A folder with two candidate boards is ambiguous and resolves to nothing rather
than guessing.

**KiCad preferences**: the Open dialog starts at KiCad's own last-opened project, read from
`system.open_projects` in `kicad.json` — `~/Library/Preferences/kicad/<ver>/` on macOS,
`%APPDATA%/kicad/<ver>/` on Windows, `$XDG_CONFIG_HOME/kicad/<ver>/` on Linux, newest version
first. Missing or malformed preferences are survivable; nothing is ever opened without being
asked. V23 exercises all three layouts regardless of host OS.

**One more solver bug, found by the refactor.** The reachability guard added in v0.12 stopped
the endpoints being disconnected, but *other* components in the same net still made the
Laplacian singular — scipy returned NaN with only a stderr warning. The solve is now
restricted to the component containing the source.

## 22. Deferred

Via ΔT · blind/buried/microvia geometry · zone conduction · separate plated-copper resistivity · pad spreading resistance (tens of µΩ against a ~1000 µΩ barrel).
