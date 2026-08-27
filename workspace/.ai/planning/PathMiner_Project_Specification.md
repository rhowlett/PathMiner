# PathMiner Full Project Specification

**Document version:** 1.0-draft  
**Date:** 2026-08-24  
**Product baseline:** PathMiner v0.13  
**Status:** Target product and technical specification  
**Companion plan:** `PathMiner_Implementation_Punch_List.md`

## 1. Purpose

PathMiner is a standalone analysis application and automation library for KiCad PCB projects. Its initial validated capability is DC copper resistance analysis from one physical pad to another. The target product expands that foundation into an intent-driven engineering workflow for:

1. Routed-copper investigation.
2. DC resistance and voltage-drop analysis.
3. Multi-net source-to-load power-path analysis through components.
4. Power and ground return-current analysis.
5. Current-density, power-loss, and thermal-risk mapping.
6. Frequency-aware signal-return-path screening.
7. Reproducible reporting and CI regression against board revisions.

This specification defines the product workflow, calculation methods, software architecture, data contracts, storage and sharing methods, user interface, command-line interface, validation requirements, and staged delivery boundaries.

## 2. Product definition

### 2.1 Product statement

PathMiner reads a KiCad project and answers increasingly broad versions of one engineering question:

> From this source to this load, where does current flow, what electrical and thermal cost does the implemented geometry impose, and does the design meet its requirements?

The application shall use real PCB geometry—stackup, tracks, arcs, vias, pads, filled zones, splits, and component connections—to build electrical networks. It shall preserve the already validated distinction between:

- A representative or least-resistance route.
- The full network-equivalent result, including parallel copper.
- The operating point created by applying a source and load to that network.
- The engineering verdict relative to explicit requirements.

### 2.2 Primary users

- PCB designers checking power routes and return structures.
- Electrical engineers defining sources, loads, and allowable drop.
- Reviewers signing off board revisions.
- Test and validation engineers correlating calculated results with measurements.
- Build/CI systems rerunning saved audits against revised KiCad projects.

### 2.3 Core use cases

1. Calculate a single trace or manually described trace/via chain.
2. Select two pads on a routed net and calculate representative-path and full-network resistance.
3. Audit one source pad against all loads on a power net.
4. Capture a multi-net path through FETs, fuses, shunts, connectors, and conversion stages.
5. Apply constant-current, constant-resistance, or constant-power loads.
6. Determine endpoint voltage, loss, source-limit behavior, margin, and failure reasons.
7. Compare fast and mesh solutions or compare a baseline with a virtual geometry change.
8. Solve simultaneous power/ground return currents and display voltage, current-density, and loss maps.
9. Screen high-speed routes for return-plane discontinuities and transition risk.
10. Export a reproducible result or gate a board revision in CI.

## 3. Scope and confidence boundaries

### 3.1 In scope

- KiCad `.kicad_pro`, `.kicad_sch`, and `.kicad_pcb` projects.
- Editable stackup and fabrication assumptions without modifying the KiCad source.
- Trace, via-barrel, zone ladder, and zone mesh resistance.
- Nodal analysis of arbitrary resistive networks.
- Saved selections, captured paths, component bridge models, source/load profiles, scenarios, and reports.
- Multi-net DC power paths and shallow or arbitrary parallel branches.
- Simultaneous DC source/load and ground-return scenarios.
- Spatial current-density and Joule-loss maps.
- Scoped IPC trace-temperature-rise estimates.
- Future board thermal-network analysis and electrothermal iteration.
- Geometry-based and frequency-aware signal-return screening.
- GUI, CLI, and a thin KiCad path-capture plugin sharing one analysis library.

### 3.2 Explicit limitations

- The validated v0.13 resistance model is not automatically a full power-integrity, thermal, or signal-integrity signoff tool.
- A signal-return plane mesh without mutual inductive coupling to the signal conductor cannot prove that high-frequency return current localizes beneath the trace.
- Vector paths drawn around obstacles may be used for explanation or initialization, but not as an authoritative electrical solution.
- A raw Joule-power map is not a temperature map. Temperature requires a thermal network, material properties, and boundary conditions.
- The existing IPC-2221 trace-rise calculation remains a limited isolated-trace estimate and shall be labeled accordingly.
- Pad spreading resistance, thermal-relief-spoke resistance, separate electrodeposited-copper resistivity, blind/buried/microvia refinements, radiation, and full-wave electromagnetic behavior remain model-specific limitations until implemented and validated.

### 3.3 Confidence labels

Every analysis type shall publish one of these confidence levels:

| Label | Meaning |
|---|---|
| **Validated** | Covered by analytic vectors, regression boards, and an accepted reference or measurement within a published error band. |
| **Correlated** | Compared against a higher-fidelity solver or measurements for defined geometry/frequency classes. |
| **Estimated** | Physically motivated approximation with documented assumptions and bounds. |
| **Screening** | Risk-identification method; not suitable for signoff. |

The report must not imply a higher confidence level than the model has earned.

## 4. Product principles

1. **One owner per concept.** Board facts, operating scenarios, solver policy, and report formatting have different owners.
2. **One shared selection model.** Net and endpoint selection shall not be reimplemented by each destination.
3. **One result contract.** GUI, CLI, and reports shall render the same structured result.
4. **Stable intent, disposable geometry.** Persist `REF.PAD` and named intent; re-resolve geometry on every run.
5. **Provenance is part of the number.** Values without source, conditions, and units are incomplete.
6. **Fail loudly on incomplete models.** Missing bridge values and unresolved hops are errors, not optimistic zeroes.
7. **List every applicable failure.** Do not short-circuit after the first reason.
8. **Fast by default, accurate when necessary.** Auto-select the least expensive defensible model and explain escalation.
9. **No silent model promotion.** Screening output cannot be presented as signoff.
10. **Reproducibility before convenience.** Every saved run records exact inputs, versions, hashes, and assumptions.

## 5. Target information architecture

### 5.1 Primary navigation

The standalone GUI shall provide five primary destinations:

| Destination | Responsibility |
|---|---|
| **Project** | Files, board facts, stackup, fabrication assumptions, metadata/model readiness, saved profiles. |
| **Investigation** | Search, raw inspection, topology, stable path capture, and analysis-scope selection. |
| **Analysis** | Scenarios, solver policy, execution, results, verdicts, comparisons, and what-if studies. |
| **Reports** | Selection of completed runs, templates, preview, and export. |
| **Diagnostics** | Validation issues, jobs, logs, convergence, environment, and troubleshooting. |

Project is a prerequisite destination rather than one of the four engineering work domains. Diagnostics supports every stage and is not a required final step.

### 5.2 Persistent shell

The application shell shall display:

- Active project and board.
- Active analysis profile/scenario.
- Dirty/saved state.
- Readiness: `Ready`, `Ready with assumptions`, or `Blocked`.
- Shared job status: current task, progress, estimate, elapsed time, cancel, warnings, and errors.

The shell shall not duplicate full settings. A compact effective-settings summary may link to the owning Project or Analysis section.

### 5.3 Project destination

Project owns:

- `.kicad_pro`, `.kicad_sch`, and `.kicad_pcb` resolution.
- Recent-project access.
- Stackup and board-derived material data.
- Fabrication assumptions: plating, drill interpretation, barrel-length convention, and outer-layer plating behavior.
- Project-local model files and their readiness.
- Saved analysis profiles and storage health.

Project does not own load current, load power, source voltage, ambient operating scenario, pair selection, solver pitch, or report format.

Project sections shall use disclosure arrows and live summaries. The controls `Expand All ▼` and `Collapse All ▶` shall appear above the first section. Drawers and sheets shall not be used.

### 5.4 Investigation destination

Investigation shall use a stable split view:

- **Scope browser:** searchable/filterable nets, components, pads, captured paths, and power-tree nodes.
- **Main view:** PCB canvas or topology/path view with synchronized selection.
- **Inspector:** raw board properties, connectivity, geometry, stable identifiers, provenance, and parser findings.
- **Selection summary:** source, sink, pair rule, selected nets/paths, and an action to add them to Analysis.

Core selection shall remain visible and shall not require a modal dialog. Selecting a table row highlights the board element; selecting a board element selects its corresponding row.

### 5.5 Analysis destination

Analysis shall provide four secondary modes:

1. **Configure and Run** — scope, scenario, source/load, solver policy, overrides, and estimate.
2. **Results** — verdicts, metrics, budgets, breakdowns, maps, assumptions, and solver details.
3. **Compare / What-if** — baseline and one or more virtual variants.
4. **Manual Estimate** — manually described geometry using the same calculation and result contracts.

Trace and Via / Path shall no longer be separate primary tabs. A manual trace is a path containing one trace segment.

### 5.6 Reports destination

Reports shall consume immutable completed runs. It shall provide:

- Run or run-comparison selection.
- Report type and template.
- Result filters.
- Section inclusion.
- Markdown, text, PDF, JSON, and future HTML formats.
- Rendered preview.
- Export location and generated-file history.

Reports shall not define net pairs, electrical conditions, or solver settings. If inputs have changed since the selected run, Reports shall show `Results out of date` and link to Analysis; it shall not rerun implicitly.

### 5.7 Diagnostics destination

Diagnostics shall provide:

- Model/readiness issues.
- Parser and geometry warnings.
- Active and completed jobs.
- Solver convergence and backend information.
- Searchable/filterable logs by severity and subsystem.
- Environment, dependency, schema, and application versions.
- Click-through to the affected project item, selection, analysis, or board location.
- Sanitized diagnostic-bundle export.

## 6. End-to-end user journey

1. The user opens a KiCad project.
2. PathMiner resolves related files, parses the board and stackup, discovers `.pathminer/`, loads schemas and models, and reports readiness.
3. In Investigation, the user searches or selects a net, pad pair, component chain, saved path, power-tree branch, or signal channel.
4. The user sends the stable selection to Analysis.
5. Analysis applies an operating profile and explicit source/load scenario, selects a solver, forecasts cost, and validates completeness.
6. The user runs the analysis through the shared job system.
7. Results show an engineering verdict, margins, electrical budget, element breakdown, maps, provenance, confidence, and limitations.
8. The user may clone the scenario and test virtual geometry, fabrication, temperature, source, or load changes.
9. Reports renders one or more completed runs without changing them.
10. The saved configuration can be rerun by CLI or CI against the next board revision.

## 7. Core domain model

### 7.1 Board and geometry

The `BoardSource` abstraction shall provide:

- Ordered stackup.
- Nets by stable name and transient KiCad code.
- Tracks and arcs with layer, endpoints, width, and true length.
- Vias with physical geometry and declared span metadata.
- Pads with `REF.PAD`, pin function, layers, position, and electrical net.
- Filled copper polygons by net and layer.
- Project and schematic fields needed for MPN/model matching.
- Direct stable lookup: `pad("U9.5")`.

Two implementations are required:

- `FileBoardSource` for standalone/CLI parsing.
- `LiveKiCadBoardSource` for the plugin.

### 7.2 Electrical network

The common network shall contain nodes and typed edges. Edge types include:

- Trace.
- Arc.
- Via barrel or via sub-span.
- Pour strip.
- Pour mesh edge.
- Component bridge.
- Source internal resistance.
- Load or source constraint.
- Capacitor/via AC impedance for frequency-aware analysis.

Every edge shall retain geometry and provenance sufficient to report its resistance/impedance, current, voltage drop, loss, and source assumptions.

### 7.3 Selection

A selection may be:

- One explicit pad pair.
- One source against every other terminal on a net.
- All pairs on a small net.
- A validated explicit list.
- One captured multi-net path.
- A power-tree branch or full tree.
- A DC return scenario.
- A signal channel.

The GUI and JSON shall support `all`, `from-source`, `first-two`, and `explicit`, but the default shall not select every routed net with every possible pair. For large designs, the normal defaults are the current Investigation selection, a saved profile, or explicitly suggested power nets.

### 7.4 Analysis profile and scenario

An analysis profile contains reusable defaults:

- Fabrication reference or override.
- Ambient/environment.
- Source and load defaults.
- Solver policy and mesh controls.
- Warning and verdict thresholds.
- Model confidence requirements.

A scenario is a run-specific application of a profile to a selection, with optional net/pair/path overrides.

Override order is:

1. Schema default.
2. Project/fabrication default.
3. Analysis profile.
4. Net/path override.
5. Pair/branch override.
6. Unsaved run override.

The effective result shall identify which level supplied each value.

### 7.5 Result and verdict

`AnalysisResult` shall include:

- Stable run ID and analysis type.
- Selection and scenario snapshot.
- Electrical and thermal metrics.
- Representative route and network-equivalent values where applicable.
- Per-edge/branch breakdown.
- Maps and references to map arrays.
- List of verdict reason codes in causal order.
- Voltage margin, delivered percentage, and other analysis-specific margins.
- Warnings, assumptions, limitations, and confidence label.
- Solver backend, graph size, convergence, runtime, and estimate accuracy.
- Input/tool/schema hashes and versions.

## 8. Calculation specification

### 8.1 Units and material constants

Internal calculations shall use SI units. Input/output layers may display mm, mil, µm, oz/ft², °C, °F, A, V, W, Ω, and scaled resistance units.

Baseline copper constants:

```text
ρ20 = 1.724e-8 Ω·m
αCu = 0.00393 K⁻¹
1 oz/ft² = 34.798 µm
```

The resistance-temperature relationship is:

```text
R(T) = R20 · [1 + αCu · (T − 20°C)]
```

Electrodeposited barrel copper currently uses the same resistivity as annealed foil. This shall be reported as an approximation until a separately validated material model is supplied.

### 8.2 Stackup and Z geometry

- Use the stackup block's physical top-to-bottom order; never infer order from KiCad layer ordinals.
- The general board thickness may include solder mask and shall not be used as a via barrel span.
- If stackup is absent, an estimated even-dielectric distribution may be created and clearly flagged.
- User stackup edits are scenario variants and shall not modify the KiCad file.
- When outer plating is enabled, outer copper grows outward and dielectric interfaces remain fixed.

For each copper layer retain foil thickness, finished thickness, outer/inner status, Z faces, Z center, and effective oz.

### 8.3 Trace resistance

For a rectangular trace:

```text
R20 = ρ20 · L / (W · tfinished)
```

The result shall retain length, width, thickness, layer, cross-sectional area, squares, and provenance of thickness.

Current density for a uniform trace section is:

```text
J = I / (W · tfinished)
```

### 8.4 Via barrel resistance

The hole convention shall be explicit:

```text
Drilled-bit convention: OD = hole; ID = OD − 2tplating
Finished-hole convention: ID = hole; OD = ID + 2tplating
Abarrel = π/4 · (OD² − ID²)
R20 = ρ20 · Lbarrel / Abarrel
Rarray = R20 / (count · sharing_pct/100)
```

The electrical span shall be derived from the layers that actually land on the via, not from the via token's declared layers. A via landing on three or more layers becomes series sub-spans ordered by stackup Z.

Supported span conventions:

- Copper center-to-center — default.
- Facing surfaces.
- Outer surfaces.

Required guards:

- `2tplating ≥ OD` is a hard error.
- Finished ID below 50 µm is a warning.
- Annular ring is checked against project rules when available, otherwise the configured fallback.
- Blind, buried, and microvias retain their observed type and must not be silently treated as validated through-via geometry.

### 8.5 Path and network resistance

For a manually declared strict series chain:

```text
Rpath = Σ Rsegment
Vdrop = I · Rhot
Ploss = I² · Rhot
```

For a routed net, construct a graph of copper nodes and edges. The representative route is the Dijkstra minimum-resistance path after edge resistance is known.

The full network-equivalent resistance shall use nodal analysis:

1. Ground endpoint A.
2. Inject 1 A at endpoint B.
3. Assemble the conductance/Laplacian matrix.
4. Solve node voltages.
5. `Req = VB − VA`; with `VA = 0`, `Req = VB`.

The network shall be restricted to the connected component containing the endpoints. Reachability must be checked before solving.

Representative-path and network-equivalent values answer different questions and shall never share an ambiguous total label.

### 8.6 Filled copper: ladder and mesh

Tracks crossing a filled zone shall be clipped at the fill boundary. Copper inside the zone shall not remain as a duplicate one-dimensional track edge.

#### Fast ladder

- Determine the pour's principal axis, length, width, aspect ratio, external ties, and via stations.
- Build one strip per copper layer along the principal axis.
- Add via rungs at actual via stations.
- Merge physical copper ties; do not connect them with near-zero resistors.
- Warn when aspect ratio is below 2:1 or geometry otherwise violates the strip assumption.

#### Raster mesh

- Rasterize actual filled polygons at configured pitch.
- Omit cells outside copper, including voids and obstacles.
- For adjacent cells on a layer:

```text
Rhorizontal = (ρ/t) · Δx/Δy
Rvertical   = (ρ/t) · Δy/Δx
```

- Merge all cells covered by a via's finite barrel disc on each landing layer.
- Connect landing-layer hubs through calculated via sub-span resistance.
- Refine pitch until the requested convergence criterion or configured limit is reached.

The mesh is the general geometry model. The ladder is a fast approximation whose use must be justified and recorded.

### 8.7 Automatic model selection

`Auto` is the default solver policy:

- Simple manual trace/via chain: point-to-point series builder.
- Routed traces/vias without zones: routed graph.
- Long strip-like stitched pour: ladder.
- Square, highly perforated, split, thermally relieved, or otherwise complex pour: mesh.

The UI and result shall show the selected model and reason. A user override is permitted but shall retain an override marker and any applicable warning.

### 8.8 Captured multi-net paths and component bridges

A reusable path shall be an ordered sequence of stable `REF.PAD` identifiers. Consecutive nodes resolve as follows:

- Same electrical net: copper edge or copper subnetwork calculated from the board.
- Same component reference: internal component bridge requiring an electrical model.
- Neither: broken path; analysis is blocked and the exact hop is named.
- Same pad in and out: legal zero-ohm bridge.

Net names are stored only to detect drift. They are not the primary lookup key.

Bridge-value precedence is:

1. Run or project instance override.
2. Dedicated component field such as `R_bridge` or condition-specific `Rds_on`.
3. Safely parsed `Value` only when the part is a resistor-like component.
4. Missing value → `ERROR_INCOMPLETE`.

The error shall list every missing bridge in one pass and identify the hop, attempted sources, original value text, and available fixes.

Parallel path groups may be represented explicitly for readability, but they shall be solved through the common nodal network rather than reduced by an assumed series/parallel formula.

### 8.9 Source models

The preferred DC source model is:

```text
Voc                  open-circuit voltage
Rsource              internal/source resistance
Imax                 optional maximum source current
source_conditions    SoC, temperature, age, frequency/test method, or other provenance
```

Source internal resistance is a series element:

```text
Rtotal = Rsource + Rpath + Rbridges
Vsource_terminal = Voc − I·Rsource
Vsink = Voc − I·Rtotal
```

A legacy `voltage_v` input may be interpreted as `Voc` with `Rsource = 0` and no current limit, but the report shall identify the ideal-source assumption.

### 8.10 Load models and operating point

Exactly one load mode is active for a sink.

#### Constant current

```text
Iunclamped = Iload
Vsink = Voc − I·Rtotal
```

#### Constant resistance

```text
Iunclamped = Voc / (Rtotal + Rload)
Vsink = I · Rload
```

#### Constant power

```text
D = Voc² − 4·Pload·Rtotal
```

If `D < 0`, no DC steady state exists:

```text
Pmax = Voc² / (4·Rtotal)
verdict includes FAIL_NO_STEADY_STATE
```

Otherwise choose the physically relevant high-voltage/low-current root:

```text
Vsink = (Voc + √D) / 2
Iunclamped = Pload / Vsink
```

After solving any load mode, apply the source current limit:

```text
I = min(Iunclamped, Imax)       when Imax exists
Vsink = Voc − I·Rtotal
```

If the limit binds, calculate delivered current/power/resistive-load voltage as applicable and add `FAIL_SOURCE_LIMIT` when the requested demand is not delivered. For a true constant-power load, the report shall state that the clamped point is a constant-current-mode idealization and may represent collapse or hiccup behavior in a real converter.

### 8.11 Operating point, budget, and verdicts

Operating-point analysis uses physical source/load inputs and computed path resistance. Budget analysis compares that result with explicit requirements such as minimum sink voltage.

For fixed current, the total series-resistance allowance is:

```text
Rtotal_allowed = (Voc − Vmin) / I
Rpath_allowed = Rtotal_allowed − Rsource − Rbridges
```

`Rpath_allowed` is the remaining copper allowance when source and bridge resistances are treated separately.

The general voltage-budget result is:

```text
budget = Voc − Vmin
used = Voc − Vsink_actual
voltage_margin_pct = (budget − used) / budget · 100
```

`budget ≤ 0` is an invalid or already-unsatisfied voltage requirement and shall be reported without division.

Interpretation:

- 100%: no voltage budget used.
- 0%: exactly at the minimum.
- Negative: voltage requirement failed.

For current or power demand:

```text
delivered_pct = delivered_demand / requested_demand · 100
```

At minimum, verdict reason codes are:

| Code | Meaning |
|---|---|
| `PASS` | Demand delivered and voltage requirement met. |
| `FAIL_SOURCE_LIMIT` | Source current limit prevents full demand. |
| `FAIL_VOLTAGE` | Sink voltage is below its requirement. |
| `FAIL_NO_STEADY_STATE` | Constant-power operating point has no real high-voltage solution. |
| `ERROR_INCOMPLETE` | Required data or topology is missing or unresolved. |

Reason codes are a list, ordered cause-first. A source limit and resulting voltage failure may both be present.

The voltage budget shall be broken down into source internal resistance, copper, component bridges, and remaining margin so that corrective action targets the actual contributor.

### 8.12 Parallel branch current and imbalance

After solving the network, branch current is calculated from the solved node voltages:

```text
Iedge = (Va − Vb) / Redge
Pedge = Iedge² · Redge
```

For `N` intended parallel branches:

```text
Iequal = Itotal / N
imbalance_pct = max(|Ii − Iequal|) / Iequal · 100
```

Default bands:

- Below 5%: balanced.
- 5% to below 10%: acceptable.
- 10% to 20%: warning.
- Above 20%: flag.

Thresholds are profile-overridable, but the actual percentage is always reported.

### 8.13 Multi-load power tree

The power-tree model links:

- Source nodes.
- Regulators or conversion stages.
- Protection devices and shunts.
- Distribution nets.
- Loads and operating states.
- Ground/return nodes.

Initial implementation may solve one stable captured source-to-sink path at a time. Full power-tree analysis shall solve all enabled loads simultaneously so shared edges carry combined current.

Linear constant-current cases use signed current injections. Nonlinear constant-power or device models require iteration or an appropriate nonlinear solver. The result must state convergence method and tolerance.

### 8.14 DC ground-return analysis

For a DC scenario, component models identify current leaving source-positive terminals and returning through named ground/reference terminals. The return network shall be solved as a conductive copper graph or mesh:

1. Build ground/reference copper on every participating layer.
2. Treat slots, voids, antipads, cutouts, and copper removed by other geometry as absent/high-resistance regions.
3. Connect layers through physically landing ground vias.
4. Inject each load's return current at its ground pad(s).
5. Withdraw total current at the source-return pad(s).
6. Assert Kirchhoff current balance before solving.
7. Solve node voltage and edge current simultaneously for the complete operating state.

Obstruction corner branching is not manually prescribed. Current divides automatically according to the solved network impedance.

Steady-state capacitors are open circuits except for explicitly modeled leakage. They do not create DC ground sources.

When multiple DC loads operate simultaneously, their signed currents sum algebraically. Root-sum-square is not used for deterministic DC current. Separate, statistically uncorrelated AC-noise sources may be combined by power/RMS rules only when the scenario explicitly declares that relationship.

### 8.15 Current density and spatial power loss

For each solved conductive element:

```text
Trace: J = I / (W·t)
Via:   J = I / Abarrel
Mesh edge: J = I / (t·edge_cross_section_width)
Power: P = Irms²·R
```

Spatial mapping shall allocate each edge's loss to grid cells using geometric overlap/length, or split it between adjacent mesh cells according to a documented rule. Each heat-source map shall include:

- Watts per cell.
- W/mm².
- Grid pitch and origin.
- Scenario/load state.
- Layer or combined-board view.
- Mapping/conservation check confirming that cell power sums to network resistive loss within tolerance.

### 8.16 Temperature methods

#### Existing trace estimate

The existing IPC-2221 curve fit is retained for a rectangular trace:

```text
I = k · ΔT^0.44 · A^0.725
ΔT = [I / (k·A^0.725)]^(1/0.44)
k = 0.048 external, 0.024 internal
```

The UI/report shall state its chart range, extrapolation status, still-air assumption, and lack of plane heatsinking.

#### Board thermal network

A board temperature map requires a separate thermal solve. The minimum defensible model is a finite-difference/thermal-resistance network containing:

- In-plane copper conduction.
- Through-board dielectric and copper-via conduction.
- Board-surface convection boundary conditions.
- Optional component/case heat sources and sinks.
- Optional radiation when needed.

Convection contributes a boundary term:

```text
qconv = h · A · (Tsurface − Tambient)
```

It shall not be used as an isolated per-cell temperature formula that ignores lateral and through-board conduction.

For electrothermal analysis:

1. Solve electrical network at initial temperature.
2. Map `I²R` power into thermal cells.
3. Solve temperature field.
4. Update copper resistance with `R(T)`.
5. Repeat until maximum temperature or resistance change is below tolerance.

Report convergence, iterations, energy balance, and any non-convergence.

### 8.17 Signal-return-path analysis

Signal return shall be delivered in two levels.

#### Level 1 — geometry/continuity screening

For each route or channel:

- Determine adjacent candidate reference planes from stackup.
- Follow the route and identify reference-plane changes.
- Detect plane splits, voids, cutouts, gaps, and excessive reference detours beneath/near the route.
- At signal-via transitions, identify nearby return vias or capacitive reference transfers.
- Record transition spacing, detour length, and unresolved return changes.
- Link every issue to the PCB view.

This level is a Screening analysis and does not calculate full-wave channel behavior.

#### Level 2 — frequency-aware impedance/current screening

At each analysis frequency `ω = 2πf`, model:

```text
Resistive/inductive edge: Z = R + jωL
Capacitor: Zc = ESR + jωESL + 1/(jωC)
Via transition: Zv = Rvia + jωLvia
```

Assemble a complex nodal admittance matrix:

```text
Y(ω) · V(ω) = I(ω)
Iij(ω) = [Vi(ω) − Vj(ω)] / Zij(ω)
```

For relative return-distribution screening, the tool may use a normalized 1 A RMS port excitation between defined driver/receiver reference nodes and shall label all currents as normalized. Absolute loss requires an actual current spectrum or driver/receiver port model. A correlated PEEC or field-solver implementation shall excite the signal/return port pair so the signal conductor and return structure participate in the same electromagnetic network.

Capacitors are impedances connecting two physical nodes; they are not independent “mini ground sources.” Their current emerges from the solved network.

A simple `R + jωL` plane mesh does not by itself model the mutual inductive coupling that attracts return current beneath the signal trace. Before displaying localized high-frequency return density as a correlated result, PathMiner shall add a validated partial-element-equivalent-circuit (PEEC), mutual-inductance, or external-field-solver method.

Vector routing toward an obstruction and around its corners may assist visualization, mesh seeding, or issue explanation. It shall not determine branch magnitude or claim physical accuracy without correlation.

#### Signal-return outputs

- Reference plane used by route segment.
- Discontinuity/transition list.
- Return-current magnitude and phase when a correlated impedance model exists.
- Transition impedance or relative risk.
- Detour distance and nearest valid return transition.
- Frequency/edge-rate conditions.
- Confidence label and validation domain.

### 8.18 Solver convergence and cost

- Small networks may use dense Gaussian/Gauss-Jordan elimination with pivoting.
- Larger resistive meshes use sparse direct solution when SciPy is available or the tested pure-Python CG fallback otherwise.
- Frequency-aware networks require complex sparse solution.
- A graph/factorization shall be reused across terminal pairs where topology and edge values are unchanged.
- Solve-time forecasting shall be based on measured machine calibration and presented as an estimate.
- Mesh refinement shall track result change, node count, runtime, and stopping criteria.
- Non-convergence, singularity, disconnected components, and invalid values are structured errors.

## 9. Data storage, schemas, and sharing

### 9.1 Storage location

Authoritative PathMiner data shall live beside the KiCad project:

```text
MyProject/
  MyProject.kicad_pro
  MyProject.kicad_sch
  MyProject.kicad_pcb
  .pathminer/
    project.json
    profiles/
    selections/
    paths/
    components/
    signals/
    schemas/
    results/
    reports/
    cache/
    logs/
```

PathMiner shall not write sidecars into official or shared `.pretty` libraries. Those locations may be read-only and are not project-portable.

### 9.2 Version-control policy

Commit by default:

- `project.json`.
- Profiles.
- Selections.
- Captured paths.
- Component-model snapshots and instance overrides.
- Signal-channel definitions.
- Schema versions/migration metadata when project-specific.

Ignore by default:

- Cache.
- Logs.
- Generated results.
- Generated reports.

Projects that require formal signoff may explicitly commit selected immutable run records and reports or publish them through an artifact/document system.

### 9.3 File rules

- JSON is the canonical structured format.
- Existing net-selection compatibility uses JSON Schema Draft-07; all new files are explicitly schema-versioned.
- Application path fields are relative to the KiCad project directory, regardless of which JSON file contains them. JSON `$schema` references follow normal URI resolution relative to the containing file.
- Units are encoded in field names or structured quantity objects; ambiguous bare values are forbidden.
- Every write is schema-validated and atomic.
- Unsupported future schema versions fail with a clear migration message.
- Unknown properties are rejected unless a schema explicitly permits extension metadata.
- Files shall be formatted deterministically to support meaningful Git diffs.

### 9.4 Stable identifiers

Persist:

- `REF.PAD` such as `U9.5` or `Q3.S`.
- Human-stable IDs for paths, profiles, scenarios, models, and channels.
- Net name as a recorded validation value.
- Component pin function as human-readable corroboration.

Do not use as persistent identity:

- KiCad net number.
- Route coordinate.
- Pad layer.
- Track/via UUID.

Coordinates and UUIDs may appear in generated results for navigation, but they are regenerated on each run.

### 9.5 Recommended project metadata

```json
{
  "$schema": "schemas/project-v1.json",
  "schema_version": "1.0",
  "project_id": "ref_powerbank_ip5385",
  "kicad_project": "Ref_PowerBank.kicad_pro",
  "default_profile": ".pathminer/profiles/nominal_25c.json",
  "model_sources": [".pathminer/components/project_models.json"],
  "created_by": "PathMiner",
  "notes": "Reference design resistance and return-path audit"
}
```

### 9.6 Analysis profile example

```json
{
  "$schema": "../schemas/analysis-profile-v1.json",
  "schema_version": "1.0",
  "id": "nominal_25c",
  "environment": {"ambient_c": 25.0},
  "fabrication": {
    "plating_um": 18.0,
    "hole_convention": "bit",
    "barrel_length": "centre",
    "outer_plating_adds": true
  },
  "solver": {
    "policy": "auto",
    "default_zone_model": "ladder",
    "mesh_pitch_mm": 0.25,
    "mesh_convergence_pct": 0.5
  },
  "thresholds": {
    "max_pairs_warn": 28,
    "parallel_warn_pct": 10.0,
    "parallel_flag_pct": 20.0
  }
}
```

### 9.7 Captured path example

```json
{
  "$schema": "../schemas/paths-v1.json",
  "schema_version": "1.0",
  "board": "Ref_PowerBank.kicad_pcb",
  "paths": [
    {
      "id": "pack_to_usbc",
      "title": "Battery pack to USB-C VBUS",
      "source": {
        "at": "JP1.3",
        "recorded_net": "PACK_P",
        "ocv_v": 8.0,
        "r_internal_ohms": 0.05,
        "max_current_a": 8.0,
        "provenance": "2S pack DCIR at 50% SoC, 25 C"
      },
      "sink": {
        "at": "J2.A4",
        "recorded_net": "VBUS",
        "min_voltage_v": 4.75,
        "load": {"mode": "constant_power", "power_w": 50.0}
      },
      "hops": [
        {"at": "JP1.3"},
        {"at": "U9.5"},
        {
          "at": "U9.1",
          "bridge": {
            "ohms": 0.0021,
            "conditions": "Vgs=4.5 V, 25 C",
            "provenance": "datasheet"
          }
        },
        {"at": "R20.1"},
        {
          "at": "R20.2",
          "bridge": {"ohms": 0.001, "provenance": "Value field R001"}
        },
        {"at": "J2.A4"}
      ]
    }
  ]
}
```

### 9.8 Lean component-model sidecar

A component model should remain compact. The recommended top-level concepts are:

1. Schema/version.
2. Model ID.
3. Match rule.
4. Component class.
5. Duty/state default.
6. Pins.
7. Internal bridges.
8. Provenance/conditions.

Example:

```json
{
  "$schema": "../schemas/component-model-v1.json",
  "schema_version": "1.0",
  "id": "CSD18540Q5B_default",
  "match": {"mpn": "CSD18540Q5B", "footprint": "QFN-*"},
  "class": "mosfet",
  "duty_cycle": 1.0,
  "pins": {
    "D": {"role": "power"},
    "S": {"role": "power"},
    "G": {"role": "control"}
  },
  "bridges": [
    {
      "from": "D",
      "to": "S",
      "model": "resistance",
      "ohms": 0.0021,
      "conditions": "Vgs=4.5 V, Id=20 A, Tj=25 C"
    }
  ],
  "provenance": {"type": "datasheet", "revision": "Rev G"}
}
```

Pin roles may include `source`, `sink`, `power`, `ground`, `signal`, `control`, and `passive`. Optional per-pin/source/sink data may define voltage, current, power, resistance, capacitance, minimum voltage, or a reference to a named operating model.

### 9.9 Model resolution and reproducibility

Resolution order:

1. Project instance override keyed by `REF` or `REF.PAD`.
2. Project-local model keyed by explicit model ID or MPN.
3. Configured company/user model library.
4. Controlled symbol/footprint/value inference.
5. Unresolved.

When an external library supplies a model, PathMiner shall copy the resolved model and provenance into the project snapshot or immutable run record. External lookup shall never be the only information needed to reproduce a run.

MPN field aliases may be configured, but PathMiner shall display the exact field and string used. It shall not silently identify parts from a fuzzy match.

### 9.10 Signal-channel example

```json
{
  "$schema": "../schemas/signal-channels-v1.json",
  "schema_version": "1.0",
  "channels": [
    {
      "id": "spi_clk",
      "driver": "U1.12",
      "receiver": "U4.3",
      "signal_net": "/SPI_CLK",
      "reference_nets": ["GND"],
      "edge_rate_s": 1e-9,
      "frequencies_hz": [1e7, 1e8, 5e8],
      "analysis": "return_path_screening",
      "notes": "Check layer transition near U4"
    }
  ]
}
```

### 9.11 Run manifest and result storage

Each run directory shall contain:

```text
results/<run-id>/
  manifest.json
  result.json
  maps/
    voltage_<layer>.bin|json|npz
    current_density_<layer>.bin|json|npz
    power_loss_<layer>.bin|json|npz
  diagnostics.json
```

`manifest.json` records:

- Run ID and timestamp.
- Board/project relative path and cryptographic hash.
- Hash of every input/model/profile file.
- Tool, package, schema, and solver versions.
- Host/backend information needed for interpretation.
- Selection/scenario IDs.
- Runtime, status, and result hash.

Large arrays may use a compact binary format, but `result.json` remains self-describing and references each array with shape, dtype, units, layer, grid transform, and checksum.

### 9.12 Atomic writes, locking, and Git collaboration

- Validate before writing.
- Write to a temporary sibling, flush, and atomically replace.
- Keep one logical model/path/profile per file where practical to reduce merge conflicts.
- Detect unsaved external changes before overwrite.
- Do not create opaque local databases as the sole project source of truth.
- A cache database is permitted only when fully regenerable from committed JSON and KiCad inputs.
- Generated run IDs are immutable; edits create a new run.

### 9.13 Analysis bundles

PathMiner shall export a portable bundle containing:

- Project metadata and relative KiCad file references or optional KiCad snapshots.
- Selected profiles, paths, selections, component snapshots, and signal channels.
- Required schemas.
- Manifest and checksums.
- Optional immutable results and reports.

Exclude caches, unrelated logs, absolute user paths, credentials, and unrelated project files. Import validates checksums, schemas, path traversal, and required content before installation.

## 10. Software architecture

### 10.1 Package layout

```text
pathminer/
  core/          units, materials, network, real/complex solvers, geometry primitives
  kicad/         S-expression parsing, file board, live board, stackup, preferences
  models/        point-to-point, ladder, mesh, component, power-tree, thermal, AC return
  analysis/      validation, orchestration, scenarios, verdicts, comparisons, jobs
  report/        result schemas, report registry, templates, renderers
  storage/       project layout, schemas, migrations, manifests, bundles, atomic I/O
  cli/           subcommands and exit-code mapping
  ui/            PySide6 shell, destinations, shared widgets, result views, maps
  plugin/        thin KiCad/wx path-capture integration
  tests/         unit, schema, regression, product-flow, performance, correlation
tools/
  build_single_file.py
```

### 10.2 Dependency rules

```text
core      imports only standard/approved numeric dependencies
kicad     imports core; no GUI
models    imports core + kicad protocols
analysis  imports core + models + storage contracts
report    imports analysis result contracts
storage   imports schemas/domain contracts; no GUI
cli       imports analysis + report + storage
ui        imports all required layers
plugin    imports shared analysis/storage and live KiCad adapter
```

No package imports `ui`. The core shall remain usable without KiCad or Qt.

### 10.3 Solver strategy

- Pure-Python numerical fallback is mandatory for KiCad plugin compatibility.
- SciPy is optional and automatically used where available.
- Compiled acceleration may be added behind the same interfaces after profiling demonstrates a material unmet requirement.
- The default optimization order is graph reuse, factorization reuse, mesh reduction/refinement, then language-level acceleration.

### 10.4 Job system

Every potentially slow operation shall run through a shared job API with:

- Unique job ID and analysis/run linkage.
- Queued/running/completed/failed/cancelled state.
- Progress units appropriate to the job.
- Estimated and actual time.
- Cooperative cancellation.
- Structured warnings/errors.
- Thread/process isolation appropriate to Python and solver behavior.
- Safe delivery of partial diagnostic information without publishing partial results as complete.

### 10.5 Result and report registries

Analysis types and report types shall register declaratively. A new report shall not require changes to a monolithic widget. Its registration defines:

- ID and title.
- Accepted result type(s).
- Options schema and defaults.
- Renderers and output MIME/extensions.
- Required sections/assets.

## 11. GUI requirements

### 11.1 General behavior

- PySide6 standalone desktop application.
- Minimum supported layout shall remain usable around 1040×900, with scalable panes.
- Long lists/tables must support search, filter, sort, bulk actions, copy, and keyboard navigation.
- State must persist when moving between primary destinations.
- Errors appear beside the affected control and in Diagnostics.
- Disabled actions include an explanation or readiness link.
- Status never relies on color alone.
- Values display units and provenance; overrides are visibly marked.

### 11.2 Shared UI components

- Collapsible section with disclosure arrow and live summary.
- Expand/Collapse All text buttons using the agreed arrow semantics.
- Searchable scope table.
- Stable source/sink/path selector.
- Effective-value editor with inheritance/provenance.
- Result/verdict header.
- Metric summary and budget table.
- Element/branch breakdown grid.
- Shared job/progress bar.
- Diagnostics issue list with navigation target.
- PCB/map view and synchronized selection controller.

### 11.3 Result presentation

The standard result hierarchy is:

1. Run state and confidence.
2. Verdict and all reason codes.
3. Primary metrics.
4. Voltage/delivery/analysis-specific margins.
5. Budget allocation.
6. Representative route and full-network comparison.
7. Per-element/branch breakdown.
8. Spatial maps.
9. Assumptions, provenance, limitations, and solver details.

### 11.4 What-if sandbox

Virtual changes shall be stored as scenario overrides rather than edits to the KiCad board. Supported override candidates include:

- Trace width or thickness.
- Via hole, pad, plating, count, or sharing assumption.
- Zone model/pitch.
- Copper-layer thickness.
- Source/load/environment.
- Component bridge value.

The UI shall show baseline, variant, absolute delta, percentage delta, and whether the verdict changed. Applying a change to KiCad is a separate future action requiring explicit confirmation and an auditable ECO; it is not implied by analysis.

## 12. Command-line interface

### 12.1 Command structure

Proposed commands:

```text
pathminer gui [PROJECT]
pathminer init PROJECT
pathminer validate PROJECT [--profile ID]
pathminer inspect PROJECT (--net NET | --pad REF.PAD | --path ID)
pathminer run PROJECT --selection FILE --profile FILE [--out DIR]
pathminer run-paths PROJECT --paths FILE --profile FILE [--path ID]
pathminer return-dc PROJECT --scenario FILE [--out DIR]
pathminer return-ac PROJECT --channels FILE [--channel ID] [--out DIR]
pathminer report --run RUN_DIR --type TYPE --format md|txt|pdf|json|html --out FILE
pathminer bundle export PROJECT [--runs ID...] --out FILE
pathminer bundle import FILE --into PROJECT
pathminer emit-schema [TYPE] [--out FILE]
pathminer selftest [--board FILE] [--suite NAME]
```

Legacy v0.13 options may remain as compatibility aliases for a defined deprecation period.

### 12.2 Exit codes

| Code | Meaning |
|---:|---|
| 0 | Command completed and engineering verdict passed or no verdict was requested. |
| 1 | Command completed but one or more engineering requirements failed. |
| 2 | Input, schema, readiness, drift, or incomplete-model error. |
| 3 | Parser, solver, convergence, or internal execution failure. |
| 4 | Requested resource/model/backend unavailable. |
| 130 | Cancelled/interrupted. |

CLI JSON shall carry detailed reason codes; CI shall not need to parse human-readable text.

### 12.3 Net drift

On rerun, resolve every `REF.PAD` against the current board and compare recorded net names.

- GUI: list all changes and offer Abort, Continue Once, or Update File.
- CLI: fail by default; allow explicit `--accept-net-changes` and separate `--update-paths`.
- Updated paths create a reviewable file change; they are not silently rewritten.

### 12.4 Automation requirements

- Deterministic JSON output ordering.
- Stable field names within a schema major version.
- No GUI imports for headless commands.
- Progress optionally emitted as structured events.
- Reproducible default behavior from saved profiles.
- CI examples for pass/fail gating and artifact generation.

## 13. KiCad plugin

The plugin shall be a thin live-board capture and navigation layer, not a second application.

### 13.1 Required workflow

1. Select a footprint/pad in KiCad and click **Set source**.
2. Select successive footprints/pads and click **Add hop**; selection order is explicitly recorded because KiCad multi-selection has no order.
3. For a component crossing, choose in/out pads and enter or resolve bridge resistance.
4. Validate every added hop immediately.
5. Select the sink and its load/requirement.
6. Save or append the path into `.pathminer/paths/`.

The plugin uses `LiveKiCadBoardSource`. It may provide a quick selected-net report, but all durable analysis and reporting use shared package APIs.

### 13.2 UI technology boundary

KiCad's embedded plugin UI is wx-based; the standalone app is PySide6. Shared business logic and schemas shall not depend on either toolkit. The plugin entry point should remain small enough that capture behavior cannot drift into a separate solver implementation.

## 14. Reporting

### 14.1 Canonical result

JSON is the canonical machine result. Markdown, text, PDF, and HTML are renderings. A renderer must not recompute analysis values.

### 14.2 Report content

Depending on analysis type, a report may include:

- Identification, board hash, run ID, tool/schema versions, and confidence.
- Assumptions and provenance.
- Stackup/fabrication state.
- Scope and selection rules.
- Verdict summary and reason codes.
- Primary metrics and budgets.
- Pair/path/net/power-tree summaries.
- Element and branch breakdowns.
- Maps and figures.
- Solver/backend/convergence details.
- Warnings, limitations, and unresolved issues.
- Baseline-vs-variant comparison.

### 14.3 Signoff behavior

- A report references an immutable run.
- Regenerating formatting from the same result does not create a new analysis run.
- Any analysis input change requires a new run ID.
- Reports display whether the underlying board hash still matches the current project.

## 15. Nonfunctional requirements

### 15.1 Performance targets

Initial targets, to be refined by benchmarking:

- Project metadata and basic board load: interactive, with incremental progress on large boards.
- Search/selection response: under 100 ms for typical board scopes.
- Simple routed-net analysis: perceived immediate or under 500 ms.
- Long solve: show forecast before execution and progress during execution.
- Batch pairs: reuse graph/factorization.
- Map pan/zoom/filter: interactive after computation.

Performance acceptance shall use fixed reference machines/boards and publish node counts, backend, and runtime.

### 15.2 Reliability

- No partial writes.
- No silent terminal/pad omission; unreachable items are listed.
- No NaN/singular result presented as valid.
- All defaults and fallbacks are visible in results.
- Cancellation leaves no completed run manifest.
- A failed analysis may keep diagnostics but not masquerade as an engineering result.

### 15.3 Portability

- Primary targets: Windows, macOS, and Linux.
- Project files use relative paths and portable JSON.
- Pure-Python solver remains available.
- Optional numeric dependencies improve performance but do not redefine results.

### 15.4 Security and privacy

- No network access is required for core analysis.
- External model lookup is optional and provenance-recorded.
- Bundles reject path traversal and sanitize absolute paths.
- Diagnostic exports exclude credentials, unrelated project data, and environment secrets.

### 15.5 Maintainability

- Module import boundaries are tested.
- Public APIs and schema versions follow semantic-versioning rules.
- One project change log records user-visible behavior.
- Report types, analysis types, and schemas are registries/contracts rather than conditional growth inside tabs.

## 16. Verification and validation

### 16.1 Existing acceptance baseline

The refactor shall preserve:

- 284/284 checks on the IP5385 real-board selftest and 1 net / 11 pairs from the IP5385 batch report.
- 284/284 checks on the real 4-layer power-bank board.
- 118/118 headless/no-board checks.
- Existing trace/via formula vectors, stackup parsing, routed-net tracing, network topologies, pour ladder/mesh comparisons, JSON selection, report generation, and real-board defect regressions.

### 16.2 Required analytic tests

- Trace resistance and unit conversions.
- Via area, conventions, length modes, arrays, and guards.
- Series, parallel, bridge, stub, and arbitrary nodal networks.
- Constant-current, constant-resistance, and constant-power operating points.
- Current-limit clamping for every load type.
- No-steady-state discriminant.
- Voltage margin and delivered percentage.
- Parallel current division and N-branch imbalance.
- DC mesh conservation and analytic sheet-resistance shapes.
- Complex R/L/C impedance and nodal solutions.
- Thermal-network energy balance and electrothermal convergence.

### 16.3 Geometry and regression tests

- Track split by a mid-run via.
- Multi-layer via actual landing spans.
- Zone-only pads and thermal-relief clearance connection.
- Tracks clipped against pours without double counting.
- Square/complex pours that require mesh.
- Disconnected components and unreachable terminals.
- Large ground nets and combinatorial pair limits.
- Rerouted board with stable `REF.PAD` and changed net name.

### 16.4 Model correlation

#### Resistance

- Compare ladder and pitch-refined mesh by geometry class.
- Compare selected test coupons or measured boards where available.
- Publish typical and worst observed error.

#### DC return and thermal

- Analytic rectangular planes and constrictions.
- Slot/void detours and via transitions.
- Mesh-refinement convergence.
- External PI/thermal solver or measurement for representative boards.

#### Signal return

Reference structures shall include:

- Solid uninterrupted reference plane.
- Plane slot crossing.
- Signal layer transition with and without adjacent ground stitching via.
- Reference-plane change with and without stitching capacitor.
- Different transition distances and frequencies.

Correlate against openEMS or another accepted field solver before promoting localized-current results beyond Screening.

### 16.5 Product workflow tests

Automated tests shall cover:

1. Project load and readiness.
2. Investigation search and selection.
3. Transfer of scope to Analysis.
4. Scenario inheritance and overrides.
5. Run progress/cancel/failure.
6. Result/verdict rendering.
7. Report creation from immutable result.
8. Save/reopen round trip.
9. CLI reproduction of the GUI run.
10. Bundle export/import and checksum validation.

## 17. Delivery phases

### Phase 0 — Preserve and refactor

- Freeze v0.13 behavior.
- Split modules and enforce boundaries.
- Create common network, result, selection, scenario, and job models.
- Preserve single-file generated build.

**Exit:** all existing acceptance checks pass from both package and generated file.

### Phase 1 — Coherent PathMiner v1 resistance product

- Implement Project, Investigation, Analysis, Reports, and Diagnostics.
- Merge Trace and Via / Path into Analysis/Manual Estimate.
- Move selection and solving out of Reports.
- Establish `.pathminer/`, schemas, migrations, run manifests, and bundle support.
- Stabilize CLI and report registry.

**Exit:** one selection and result workflow operates consistently across GUI and CLI.

### Phase 2 — System power paths

- Captured multi-net paths and plugin.
- Component bridge models and provenance.
- Real source and three load models.
- Current limits, multi-reason verdicts, margins, parallel branches, and what-if comparison.
- Initial power-tree view and analysis.

**Exit:** source-to-load audits through components are reproducible and requirement-driven.

### Phase 3 — DC return and thermal-risk mapping

- Simultaneous DC ground-return mesh.
- Voltage/current-density/Joule-loss maps.
- Scoped IPC trace rise and validated raw heat-source maps.
- Board thermal network and electrothermal iteration when validation is complete.

**Exit:** maps conserve electrical power, publish confidence, and correlate within defined bounds.

### Phase 4 — Signal-return screening

- Reference-plane continuity and transition checks.
- Signal-channel storage.
- Frequency-aware R/L/C impedance network.
- Correlation to field-solver test structures.

**Exit:** screening reports identify discontinuities and clearly state frequency and confidence domain.

### Phase 5 — Advanced multiphysics and ecosystem

- Improved PEEC/mutual coupling or field-solver integration.
- Validated component/thermal models.
- Optional KiCad ECO generation after separate safety review.
- Company component-model library synchronization that preserves project snapshots.

## 18. Decisions and deferred items

### 18.1 Decisions established by this specification

- The product name and package are PathMiner.
- Project inputs live in `.pathminer/` beside the KiCad project.
- JSON plus schemas are the portable source of truth.
- External/global model libraries are optional sources, never the sole reproducibility dependency.
- Project/Investigation/Analysis/Reports/Diagnostics is the primary navigation.
- Reports consume completed results and do not own solver configuration.
- Trace and Via / Path merge into one Analysis model.
- DC return is solved by a conductive network/mesh, not manual vector branching.
- Capacitors are open in steady-state DC and impedance edges in AC.
- Deterministic DC currents sum algebraically; statistical RMS combination requires an explicit source relationship.
- Raw `I²R` heat maps and temperature maps are distinct outputs.
- Signal-return localization remains Screening until mutual-coupling/field-solver correlation exists.
- Python remains the reference implementation; compiled acceleration is optional and API-compatible.

### 18.2 Deferred or model-dependent

- Final blind/buried/microvia geometry models.
- Pad spreading and thermal-relief-spoke resistance.
- Separate plated-copper material database.
- Component temperature-dependent nonlinear resistance beyond scenario curves.
- Full converter dynamic behavior and stability.
- Radiation and enclosure airflow CFD.
- Full-wave impedance, TDR, eye diagram, and compliance signoff.
- Automatic board modification/ECO generation.

Each deferred item requires its own model contract, validation domain, and confidence label before becoming a reportable engineering result.

## 19. Definition of project completion

The full PathMiner project described here is complete when:

1. Every saved analysis is reproducible from project-local, schema-validated inputs.
2. GUI and CLI produce the same structured results.
3. Selection, settings, execution, reporting, and diagnostics each have one clear owner.
4. Existing DC resistance accuracy and regressions are preserved.
5. Multi-net power paths correctly model sources, loads, bridges, limits, margins, and parallel sharing.
6. DC return/current-density/power maps conserve current and power and meet published correlation targets.
7. Thermal outputs distinguish scoped estimates from validated board-temperature solutions.
8. Signal-return outputs identify discontinuities and never exceed their published confidence.
9. Reports identify exact board/input/tool versions and immutable run IDs.
10. The matching release gate, tests, model limitations, and user documentation exist for every enabled capability.
