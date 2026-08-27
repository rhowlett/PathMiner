# PathMiner v0.13 Behavioral Compatibility Inventory

**Date:** 2026-08-26 (corrected 2026-08-26 during strict Session 01 repair)  
**Baseline Commit:** fe507fd01017cd0930739cbd8c4cc3f916b47e98  
**Document Status:** Session 01 closure requirement (BASE-002)  
**Model:** claude-sonnet-4-6 (authorized substitution; prompt specified Haiku-4.5)

This document lists every CLI command, input field, output field, default value, warning, and report format that must survive the refactor without breaking existing workflows.

---

## 1. CLI Commands and Invocation

### 1.1 GUI Launch
```
python3 tools/pcb_trace_resistance.py
python3 tools/pcb_trace_resistance.py <board.kicad_pcb>
```
- **Behavior:** Launch PySide6 GUI, optionally pre-loading a board file
- **Preserved:** Window title, tab names, menu structure
- **Required:** Same application icon, window icon, theme support

### 1.2 Selftest
```
python3 tools/pcb_trace_resistance.py --selftest [board.kicad_pcb]
```
- **Behavior:** Run 118 headless acceptance vectors; if board supplied, run additional reference-board or real-board tests
- **Preserved:** All 656 acceptance vector IDs and expected values
- **Output Format:** `[PASS] <vector_id> <description> got <value> want <expected>`
- **Summary:** `<count>/<count> checks passed`
- **Exit Code:** 0 on all pass, non-zero if any test fails

### 1.3 Emit Schema
```
python3 tools/pcb_trace_resistance.py --emit-schema [file.json]
```
- **Behavior:** Output the v0.13 JSON schema for net selection
- **Preserved:** Schema structure in `schema/pcb_net_selection.schema.json`
- **Default:** Write to stdout if no file given
- **Output Format:** JSON, schema version tracking

### 1.4 Emit Nets
```
python3 tools/pcb_trace_resistance.py --emit-nets <board.kicad_pcb> --out sel.json
```
- **Behavior:** Read board and emit a template net-selection file with all routed nets listed
- **Preserved:** Generated file conforms to schema, includes metadata section
- **Output Format:** JSON with version, description, available_nets, select=[all nets]

### 1.5 Dump Stackup
```
python3 tools/pcb_trace_resistance.py --dump-stackup <board.kicad_pcb> [--plating <um|mil|oz>] [--outer-plating]
```
- **Behavior:** Parse board stackup and emit layer, copper weight, thickness, and plating details
- **Preserved:** Layer order, thickness calculations, plating thickness modes
- **Options:**
  - `--plating` — specify barrel plating in micrometers, mil, or oz (D2)
  - `--outer-plating` — add 2× plating to outer layer thickness (D8)
- **Output Format:** Human-readable table and JSON

### 1.6 Report (Batch Mode)
```
python3 tools/pcb_trace_resistance.py --report <board.kicad_pcb> --nets sel.json \
    [--plating <um|mil|oz>] [--zone-model none|ladder|mesh] [--mesh-pitch <mm>] \
    [--ambient <°C>] [--current <A>] [--format md|txt|json|pdf] [--out <FILE>]
```
- **Behavior:** Read board and net selection, compute resistance for all selected pairs, emit report
- **Preserved:** All option names, defaults, and output formats
- **Options:**
  - `--plating` — default: **18.0 µm** (IPC-6012 Class 2 minimum; D2 amended v0.11 in DEFAULT_OPTIONS); error only if explicitly 0 or null
  - `--zone-model` — default: `ladder` (none, ladder, mesh)
  - `--mesh-pitch` — default: 0.25 mm (for mesh model)
  - `--ambient` — default: 25°C, affects temperature rise
  - `--current` — default: **1.0 A** (from DEFAULT_OPTIONS; non-zero so temperature rise is computed by default)
  - `--format` — default: `md` (Markdown)
  - `--out` — default: stdout (- or FILE)
- **Output Formats:**
  - **Markdown (.md):** Sections, tables, code blocks, details/summary
  - **Text (.txt):** Plain ASCII, no formatting
  - **PDF (.pdf):** A4, page margins, rendered from Markdown
  - **JSON (.json):** Structured result with metadata, per-pair data, summaries

---

## 2. GUI Tabs and Components

### 2.1 Trace Tab
**Purpose:** Calculate DC resistance and temperature rise of a manually described trace

**Input Fields:**
- `Length` — numeric with unit selector (mil, mm, in, cm)
- `Width` — numeric with unit selector (mil, mm, in, cm)
- `Copper weight` — pull-down: 0.5, 1, 2, 3, 4, 5, 6, 8, 10 oz/ft²
- `Layer` — radio or combo: Internal, Outer (affects IPC-2221 k factor)
- `Current` — numeric, amperes, default 0
- `Ambient temperature` — numeric with C/F selector, default 25°C
- `Calculate button` — trigger resistance and temperature calculation

**Output Fields:**
- `Resistance at 20°C` — in ohms with auto-scaled units (mΩ, µΩ, nΩ)
- `Sheet resistance` — Ω/square geometry detail line
- `Temperature rise` — °C (or °F), only if current > 0
- `Resistance at temperature` — ohms at operating temperature
- `Voltage drop` — I·R, only if current > 0
- `Power dissipation` — I²·R, only if current > 0
- `Warnings` — yellow box if operating point outside IPC-2221 chart or exceeds 105°C FR-4 limit

**Preserved Behavior:**
- IPC-2221 k factors: 0.048 (external), 0.024 (internal)
- Temperature coefficient: α = 0.00393/K
- Auto-scaling follows engineering conventions
- Warnings appear for invalid operating points

### 2.2 Via / Path Tab
**Purpose:** Calculate resistance of trace/via chains or routes traced from a board

**Input Fields:**
- **Via settings (read-only echo)** — group box "Via settings (set on the Setup tab)"; shows in-force drill convention, barrel length, outer plating, zone model, mesh pitch
  - Actual controls live in Setup tab → "Via and zone modelling" section (moved in v0.13)
- **Segment table (add/remove rows):**
  - Row type selector: trace or via
  - For trace: layer, length, width, length unit, width unit
  - For via: from-layer, to-layer, hole diameter, pad diameter, hole unit, pad unit
- **Board trace button** — opens dialog to pick net and endpoints from a loaded board; populates segment table automatically
- **Calculate button** — trigger end-to-end resistance calculation

**Output Fields:**
- **Traced path label** — "Traced "<net>": <pair>, <N> trace segment(s), <M> via(s)"
- **Network equivalent** — only shown if parallel copper exists
- **Segment table with calculations** — per-row length, width, resistance, shared contribution
- **Total resistance** — sum of traced path resistance
- **Network-equivalent resistance** — whole net if applicable
- **Parallel-copper detection** — warning if branches exist, advisory on effect

**Preserved Behavior:**
- Via layer conventions: D3 (hole size definition), D4 (barrel length) — settings now on Setup tab
- Plating defaults to 18.0 µm (D2 amended v0.11); error only if explicitly cleared to 0
- Zone model defaults to ladder for performance — setting now on Setup tab
- Warnings for branches, zone nets, unreachable endpoints
- Board-net tracing uses Dijkstra with resistance weighting
- Via electrical span derived from actual landing layers, not declared layers

### 2.3 Setup Tab
**Purpose:** Configure board files, global operating conditions, via and zone modelling, and stackup geometry. Tab label in v0.13: "Setup" (renamed from "Stackup" in v0.13; class is `SetupTab`; attribute alias `setup_tab = stackup_tab` preserved for backward compatibility).

The Setup tab contains four collapsible sections ("Expand all" / "Collapse all" controls at top):

#### Section 1: Files
- **Files table** — 3-row table: KiCad project, board (.kicad_pcb), net selection (.json)
- **Open project / Open board / Open net selection buttons** — file pickers per row
- Opening the project file resolves the associated board automatically
- Recent projects listed from KiCad preferences

#### Section 2: Global settings
Group box label: "Global settings (shared by all tabs)" (`GlobalConditions` widget)

- **Barrel plating** — numeric + unit selector (um, mil, oz), default **18 µm** (IPC-6012 Class 2 minimum; D2 amended v0.11); preset combo (IPC-6012 class options)
- **Signal voltage (V)** — numeric, default **3.3 V**
- **Constant current (A)** — numeric, default **1.0 A**
- **Ambient** — numeric + C/F toggle, default **25°C**

These values are shared across Trace, Via/Path, and Report tabs.

#### Section 3: Via and zone modelling
- **Hole value means** — combo: bit (drilled hole size), finished (plated hole size); default bit
- **Barrel length** — combo: facing (pad surface to surface), centre (copper centre-to-centre, default), outer (outer surface to outer surface)
- **Outer plating checkbox** — "Plating also thickens the outer copper layers (grows the board by 2× plating)"; default **checked** (D8 on)
- **Zone model** — combo: ladder (default), mesh, none
- **Mesh pitch (mm)** — numeric, default **0.25**, active only when mesh selected

*Note in UI:* "The zone model here is the default; individual pad pairs can override it on the Report tab."

#### Section 4: Stackup
- **Load .kicad_pcb / New manual stackup / Revert to file** buttons
- **Edit in** unit selector (mm, mil, um)
- **Stackup table** — columns: Layer, Type, Thickness, = oz, (edit)
  - Layer name (read-only from file)
  - Copper weight shown as oz equivalent
  - Thickness editable; edited rows marked `*`
  - Revert restores file values
- **Summary label** — layer count, core thickness, copper finish totals
- Fallback to manual stackup mode if board has no stackup section

**Preserved Behavior:**
- Layer ordinals from `(stackup)` block, not from layer tag numbers (KiCad gotcha)
- Plating thickness added to outer layers only, not inner layers (D8)
- Copper weight stored as oz/ft², converted to µm thickness via 34.798 µm/oz
- All four sections are collapsible; state does not persist between runs

### 2.4 Report Tab
**Purpose:** Define pad-pair scope, pair-level overrides, report sections, output format, and generate reports. Global operating conditions (plating, current, voltage, ambient) and global zone model are owned by the Setup tab; Report tab supplies per-pair overrides only.

**Sections:**

#### Report on these nets
- **Transfer list:** Available nets ↔ Selected nets (with Add/Remove buttons)
- **Default:** All routed nets selected
- **Preserved:** Dual-list UI, double-click to move

#### Ignore these nets
- **Transfer list:** Selected nets ↔ Ignored nets
- **Preserved:** Ignore always wins over select (after apply)

#### Point-to-point pairs
- **Table:** Net, Terminals, Pairs (combo), Source (combo, for from-source mode)
- **Pair modes:** all, first-two, from-source, explicit
  - `all` — every pair: N(N-1)/2 rows
  - `first-two` — top two terminals only
  - `from-source` — one driver pad to every other
  - `explicit` — user-specified pairs (stored in JSON)
- **Source terminal** — combo for from-source mode, defaults to first terminal
- **Per-pair overrides table (overrides the Setup tab global defaults for individual pairs):**
  - Pair identifier (e.g., Z1.SDA>Z2.SDA)
  - Voltage (V) — optional per-pair override
  - Current (A) — optional per-pair override
  - Zone model — optional per-pair override (overrides Setup tab "Via and zone modelling" → Zone model)
  - Mesh pitch (mm) — optional per-pair override

**Report configuration:**
- **Sections checkboxes:** Assumptions, Stackup, Selection, Summary, Detail, Notes
- **Format selector:** Markdown, Text, PDF, JSON (all use same canonical JSON)
- **Preview button** — render to preview pane without saving
- **Generate button** — save report to file

**Output Fields (same in all formats):**
- **Assumptions** — stackup, plating, conventions, zone model, mesh pitch, ambient, current
- **Stackup** — layer table with copper weights and thicknesses
- **Selection** — nets selected, ignored, pair mode for each
- **Summary** — pass/fail for each pair, organized by net
- **Detail** — per-pair: endpoints, distance, layer transitions, resistance breakdown
- **Notes** — warnings, branch detection, parallel copper effects

**Preserved Behavior:**
- Selection list is always visible (no modal dialogs in v0.13)
- Ignore beats select (set difference)
- Pair modes affect row count in detail table
- Format selector changes output file extension
- All formats render the same data structure (JSON as canonical)

---

## 3. Input Schemas and Validation

### 3.1 Net Selection File (pcb_net_selection.schema.json)
**Location:** `schema/pcb_net_selection.schema.json` (frozen)

**Required Top-Level:**
- `_meta` object with `version` (pattern: `v?\d+\.\d+(\.\d+)?`)

**Optional Top-Level:**
- `select` — array of net names or glob patterns (include list)
- `ignore` — array of net names or glob patterns (exclude list)
- `_available_nets` — informational array (ignored on read)
- `options` — operating conditions and solver settings
- `nets` — per-net overrides

**Options Object** (with DEFAULT_OPTIONS fallback values for CLI batch mode):
- `plating_um` — positive number, max 1000; **CLI default: 18.0 µm** (D2 amended v0.11); schema has no explicit default; error if explicitly 0 or null
- `hole_convention` — "bit" or "finished"; **default: "bit"**
- `length_convention` — "centre", "facing", or "outer"; **default: "centre"**
- `outer_plating_adds` — boolean (apply D8 rule); **default: true**
- `zone_model` — "none", "ladder", or "mesh"; **default: "ladder"**
- `mesh_pitch_mm` — positive, max 5; **default: 0.25**
- `ambient_c` — temperature in Celsius, min -273.15; **default: 25.0**
- `current_a` — non-negative amperes; **default: 1.0**
- `signal_voltage_v` — source voltage for drop calculations; **default: 3.3**
- `pairs` — "all", "first-two", "from-source"; **default: "all"**
- `max_pairs_warn` — integer threshold to warn on large reports; **default: 28**
- `sections` — object with boolean flags for report sections; **default: all true**

**Net Overrides:**
- Per-net: `pairs`, `source`, `explicit_pairs` (array of "PAD>PAD"), `pair_overrides`
- Per-pair in pair_overrides: `voltage_v`, `current_a`, `zone_model`, `mesh_pitch_mm`

**Preserved Validation:**
- Schema version format enforced (pattern match)
- Plating must be positive if present; CLI uses 18.0 µm default from DEFAULT_OPTIONS if not specified; error if explicitly 0 or null
- Hole and length conventions have specific allowed values
- Glob patterns in select/ignore (e.g., "/SDA", "/SCL")
- Empty select treated as "all nets"
- Ignore applied after select (set difference)
- Unknown keys rejected (additionalProperties: false)

---

## 4. Numerical Constants and Boundaries

### 4.1 Material Properties
- **Copper resistivity:** 1.724e-8 Ω·m (IACS annealed, 20°C)
- **Temperature coefficient α:** 0.00393 /K
- **Copper weight to thickness:** 34.798 µm/oz

### 4.2 IPC-2221 Curve Fit
- **External layer k:** 0.048
- **Internal layer k:** 0.024
- **Formula:** I = k·dT^0.44·A^0.725 (A in mils², dT in °C)
- **Safe limit:** 105°C for FR-4 (warning above this)

### 4.3 Via Conventions
- **Hole size modes (D3):** bit (drilled) or finished (plated)
- **Barrel length modes (D4):**
  - facing: pad surface to surface (shortest)
  - centre: copper centre-to-centre (default)
  - outer: outer surface to outer surface (longest)
  - Range: ~39% variation between conventions

### 4.4 Zone Model Thresholds
- **Dense solver node limit:** 400 (D_DENSE_NODE_LIMIT)
- **Zone-pad reach:** 1.0 mm (thermal relief + pad clearance)

### 4.5 Numerical Precision
- **Trace resistance auto-scaling:** mΩ, µΩ, nΩ, pΩ
- **Comparison tolerance for network-vs-path:** 1e-9 × path resistance

---

## 5. Warnings and Error Messages

### 5.1 Warnings (Yellow box in GUI, prefixed "Warning:")
- **Branch detection:** "branch at <node>: the other copper is a stub" or "...does not change the result"
- **Via electrical span mismatch:** "Declared via span(s) {...} vs traced electrical span(s) {...}"
- **Zone-net warning:** "this net has a copper zone and zone_model is 'none': the pour is ignored"
- **Trace outside IPC-2221 range:** "Temperature rise computation outside IPC-2221 chart (>10A or <0.1A typical)"
- **Temperature exceeds 105°C:** "Ambient + rise exceeds typical FR-4 limit (105°C)"
- **No pad terminals found:** "no pad terminals found; traced between two loose track ends"
- **Multiple pad terminals:** "net has N pad terminals; traced between the first two"
- **No electrical parameters:** "no electrical parameters supplied: path chosen by physical length"

### 5.2 Errors (Exceptions, GUI dialogs, or non-zero exit)
- **Invalid plating:** "plating must be positive" (D2 enforcement)
- **Singular matrix:** "singular network matrix" (degenerate graph)
- **No continuous path:** "net N: no continuous path between the two endpoints"
- **Net has no routed copper:** "net N has no routed copper"
- **Cannot identify endpoints:** "cannot identify two endpoints"
- **Unresolved via:** "missing plating value for via" (when computing)
- **Bad JSON schema:** "unknown key caught" (additionalProperties violation)
- **Bad net selection:** "unused select reported" (requested nets not found)

---

## 6. Report Output Fields

### 6.1 Assumptions Section
- Stackup source and date
- Plating thickness and convention (hole, barrel-length, outer-layer)
- Zone model and mesh pitch
- Ambient temperature
- Current
- Solver backend (Python, SciPy if available)

### 6.2 Stackup Section
Table: Layer | Copper (oz) | Finished (µm) | Material | Thickness
- Row per layer in stack order
- Calculated thickness from weight and density
- Outer layers show plated thickness (D8 effect)

### 6.3 Selection Section
- Nets selected: names, count
- Nets ignored: names, count
- Pair mode per net (all, first-two, from-source, explicit)
- Source terminal if from-source mode

### 6.4 Summary Section
Table per selected net: Terminal Pairs | Distance | Path R | Network R | Margin | Pass/Fail
- One row per pair (count varies by mode)
- Distance in mm, resistance in ohms with scaling
- Pass/Fail based on voltage budget (if provided)

### 6.5 Detail Section
Table: Layer (From) | Layer (To) | Type | Length | Width/Dia | Resistance | % of Total
- One row per segment (trace or via sub-barrel)
- Segments merged if consecutive with same layer/width
- Mesh crossings grouped by run

### 6.6 Notes Section
- Branch warnings and effects
- Zone model applicability
- Parallel copper detection and quantification

---

## 7. Application Metadata and Versioning

### 7.1 Version Tracking
- **Application version:** v0.13 (in file header comment line 2)
- **Per-file changelog:** `documents/change_log.md`
- **Version bump rule:** Minor bumped on every change (no major/patch)

### 7.2 Window Titles
- **GUI:** "PCB Trace / Via Resistance Calculator" (subject to rename in BASE-003)
- **Report windows:** Include board name and net selection file

### 7.3 Help Text
- **Trace tab:** Describes copper weight entry, external/internal layer k factor, temperature limits
- **Via/Path tab:** Refers to Setup tab for drill conventions (D3), barrel-length conventions (D4), plating (D2), outer-layer plating (D8); explains through-via-only limitation (D5)
- **Setup tab:** Shows how to load/edit stackup, fallback to manual mode; describes plating default (18 µm IPC-6012 Class 2), via and zone modelling controls

---

## 8. File Formats and Encoding

### 8.1 Input Files
- **Board files:** `.kicad_pcb` (S-expression, UTF-8)
- **Project files:** `.kicad_pro` (JSON, UTF-8, for preferences/net classes)
- **Net selection:** `.json` (UTF-8, schema-validated)

### 8.2 Output Files
- **Markdown (.md):** UTF-8, with backtick code blocks, tables, bold/italic
- **Text (.txt):** UTF-8, ASCII-safe (no box drawing)
- **PDF (.pdf):** Generated via QPdfWriter, A4 page size, 12pt sans-serif
- **JSON (.json):** UTF-8, compact (no pretty-print in v0.13)

### 8.3 Volatile Fields (Excluded from Golden Fixtures)
- `generated` timestamp (ISO 8601 or similar)
- `generated_by` software version/build
- Report generation time
- Solver backend (varies by system: scipy availability)
- File paths (absolute paths must be normalized to relative)
- Elapsed time for benchmarks (varies by machine)

---

## 9. Acceptance Criteria for Refactor

### Must Preserve
✓ All CLI commands and options (same names, same defaults)  
✓ All GUI tab names and layouts  
✓ All input and output field names  
✓ All acceptance-vector IDs and expected values  
✓ All numerical results within published tolerances  
✓ All warning and error messages  
✓ JSON schema structure  
✓ Report section names and format  

### May Change
✓ Internal code structure (modularization)  
✓ Solver backend (optimize sparse solver)  
✓ UI widgets (e.g., Qt5 → Qt6, if PySide6 remains)  
✓ UI layout (improved spacing, groups, clarity)  
✓ Help text clarity (if no behavioral change)  
✓ Performance (if results preserved)  

### Must Not Change
✗ CLI syntax (breaking changes)  
✗ Numerical behavior (except authorized improvements)  
✗ Schema structure (only extensions allowed)  
✗ Acceptance-vector values (golden test results)  
✗ Default values (e.g., mesh_pitch=0.25 must remain)  
✗ UI tab ownership (Trace, Via/Path, Report, Setup stay separate; via/zone settings remain on Setup tab)  

---

## Revision History

| Date | Session | Change |
|------|---------|--------|
| 2026-08-26 | 01 | Initial inventory from v0.13 baseline |
| 2026-08-26 | 01 (repair) | Corrected: Setup tab (not Stackup), plating default 18 µm, current_a default 1.0 A, signal_voltage_v default 3.3 V, outer_plating_adds default true, max_pairs_warn default 28, zone model owned by Setup tab not Via/Path, schema defaults documented, model substitution recorded |

---

**Document prepared by:** Session 01 (claude-sonnet-4-6; authorized substitution for Haiku-4.5 specified in prompt)  
**Reviewed against:** tools/pcb_trace_resistance.py v0.13 (lines 2069–2083 DEFAULT_OPTIONS, 2667–2793 GlobalConditions, 2797–2946 SetupTab, 3204–3263 ViaPathTab, 5378–5401 MainWindow.__init__), schema/pcb_net_selection.schema.json, README.md  
**Status:** Corrected and re-verified; BASE-002 closure pending coordinator review
