# PathMiner Implementation Punch List

**Baseline:** PathMiner v0.13 (`pcb_trace_resistance.py`)  
**Date:** 2026-08-24  
**Status:** Proposed work plan  
**Companion document:** `PathMiner_Project_Specification.md`

## Purpose

This punch list converts the UI/UX audit, the v0.13 design contracts, the library-refactor recommendations, and the future power/signal-return-path discussion into an ordered implementation plan.

Priority meanings:

- **P0 — Foundation:** required before feature growth.
- **P1 — Core product:** required for a coherent PathMiner v1 workflow.
- **P2 — Expansion:** power-system, return-path, and thermal capability.
- **P3 — Advanced:** frequency-aware signal-return and field-solver correlation.

Every item remains open until its stated completion condition is met.

## 1. Protect the validated baseline — P0

- [x] **BASE-001 — Freeze and tag the v0.13 baseline.** Preserve the current single-file program, schemas, sample inputs, reports, and acceptance board files.
  **Done when:** the archived version reproduces 118/118 headless checks, 284/284 IP5385 real-board checks, and produces 1 net / 11 pairs from the IP5385 batch report.
  **Status (Session 01):** CLOSED — all three suites verified PASS; golden fixtures and executable comparator committed.

- [ ] **BASE-002 — Record behavioral compatibility requirements.** List every current CLI command, input field, report field, default, warning, and output format that must survive the refactor.  
  **Done when:** the list is reviewed against the README, schema, and v0.13 code.

- [ ] **BASE-003 — Rename the user-facing application to PathMiner.** Update the window title, command name, help text, report metadata, and stale references to “PCB Trace / Via Resistance Calculator,” “Stackup tab,” and the former Via / Path settings location.  
  **Done when:** no current UI message directs users to a renamed or removed location.

- [ ] **BASE-004 — Preserve a generated single-file distribution.** Add `tools/build_single_file.py` after the package split.  
  **Done when:** the generated file passes the same aggregate self-test as the package.

- [ ] **BASE-005 — Defer a C/C++ rewrite until profiling justifies it.** Optimize graph reuse and sparse factorization first; retain a pure-Python solver fallback for KiCad.  
  **Done when:** the decision and performance thresholds for introducing compiled acceleration are documented.

## 2. Split the code into enforceable layers — P0

- [ ] **ARCH-001 — Create the package structure.** Add `core/`, `kicad/`, `models/`, `analysis/`, `report/`, `storage/`, `cli/`, `ui/`, `plugin/`, and `tests/`.  
  **Done when:** the application runs from the package and dependency direction is tested.

- [ ] **ARCH-002 — Enforce dependency direction.** `core` must not import KiCad, I/O, Qt, or wx; nothing may import `ui`.  
  **Done when:** an automated import-boundary test fails on a forbidden dependency.

- [ ] **ARCH-003 — Introduce `BoardSource`.** Define a protocol for nets, tracks, arcs, vias, pads, pours, stackup, and stable pad lookup. Implement file-backed and future live-KiCad adapters.  
  **Done when:** the same analysis accepts either adapter without branching above `kicad/`.

- [ ] **ARCH-004 — Create a common network model.** Define `Node`, `Edge`, `ResistorNetwork`, provenance metadata, and solver results.  
  **Done when:** point-to-point, ladder, and mesh builders all emit the same network type.

- [ ] **ARCH-005 — Create shared domain state.** Add `ProjectContext`, `SelectionModel`, `AnalysisProfile`, `AnalysisScenario`, `AnalysisResult`, `Verdict`, and `JobState`.  
  **Done when:** UI tabs exchange these objects rather than copying widget state.

- [ ] **ARCH-006 — Consolidate solvers behind one dispatcher.** Support dense, pure-Python sparse/CG, and optional SciPy backends with identical results and metadata.  
  **Done when:** backend agreement is asserted on the same networks.

- [ ] **ARCH-007 — Reuse a factorization for multiple terminal pairs.** Build/factor a graph once per net/model/pitch and back-solve each pair.  
  **Done when:** batch runtime scales primarily with graph construction plus inexpensive pair solves.

- [ ] **ARCH-008 — Create a report registry.** New report types must register an ID, options schema, runner, and renderers without enlarging a monolithic Report tab.  
  **Done when:** resistance reporting is the first registered implementation.

- [ ] **ARCH-009 — Generate defaults from schemas.** Remove duplicated `DEFAULT_OPTIONS` and schema defaults.  
  **Done when:** one schema definition produces GUI defaults, CLI defaults, and validation behavior.

- [ ] **ARCH-010 — Split the self-test by module while retaining stable vector IDs.**  
  **Done when:** module tests and the aggregate `--selftest` report the same acceptance-vector identities.

## 3. Establish project-local storage and sharing — P0

- [ ] **DATA-001 — Create the `.pathminer/` project layout.** Separate reproducible inputs from generated results, reports, cache, and logs.  
  **Done when:** PathMiner discovers the folder beside the `.kicad_pro` file and can initialize it without modifying KiCad libraries.

- [ ] **DATA-002 — Define versioned JSON Schemas.** Cover project metadata, analysis profiles, selections, captured paths, component models, signal channels, run manifests, and result documents.  
  **Done when:** every persisted input and structured result validates before use or save.

- [ ] **DATA-003 — Add schema migration.** Read prior supported versions, migrate in memory, show changes, and write only after explicit confirmation or a CLI migration command.  
  **Done when:** v0.13 net-selection files load without loss.

- [ ] **DATA-004 — Use stable design identifiers.** Persist `REF.PAD`, net names for drift checking, relative board paths, and human-readable IDs; never depend on net numbers, route coordinates, layer assignments, or track/via UUIDs for re-resolution.  
  **Done when:** a rerouted board resolves the same paths or produces a named drift error.

- [ ] **DATA-005 — Implement a lean component-model sidecar.** Support sources, sinks, grounds, passives, capacitors, and pin-to-pin bridges with units, conditions, and provenance.  
  **Done when:** models can be resolved by project override, MPN, or controlled fallback without editing official KiCad libraries.

- [ ] **DATA-006 — Snapshot external model data into the project.** A global or company component database may supply a model, but each run must use a project-local resolved snapshot.  
  **Done when:** another user can reproduce a run without access to the original external database.

- [ ] **DATA-007 — Store analysis assumptions with provenance.** Mark each value as board-derived, project default, library-derived, user override, or run override.  
  **Done when:** result and report views can show the effective value and its origin.

- [ ] **DATA-008 — Write atomically.** Validate, write a temporary sibling file, flush, and replace; never leave a partial JSON file.  
  **Done when:** interrupted-write tests preserve the previous valid version.

- [ ] **DATA-009 — Define version-control policy.** Commit configuration, profiles, paths, selections, component snapshots, and schemas; ignore cache/logs and generated results/reports by default.  
  **Done when:** initialization can generate a recommended `.gitignore` fragment.

- [ ] **DATA-010 — Add analysis-bundle export/import.** Bundle relative-path inputs, schemas, checksums, optional results, and optional reports; exclude caches and machine-specific paths.  
  **Done when:** an imported bundle validates and reproduces the recorded run on another machine.

- [ ] **DATA-011 — Add immutable run manifests.** Record board hash, input hashes, tool/schema versions, backend, settings, timestamps, runtime, and result hash.  
  **Done when:** a report can identify exactly which run produced it.

## 4. Rebuild the application shell and tab ownership — P1

- [ ] **UI-001 — Adopt the primary navigation:** `Project | Investigation | Analysis | Reports | Diagnostics`.  
  **Done when:** Project is first, Diagnostics is last/supporting, and no Import-only tab remains after load.

- [ ] **UI-002 — Add a persistent project header.** Show project, board, active profile, dirty state, and readiness.  
  **Done when:** users can identify the active context from every primary destination.

- [ ] **UI-003 — Add a shared job/status bar.** Show operation, progress, estimate, elapsed time, cancel, and warning/error count.  
  **Done when:** every slow analysis uses the same job model.

- [ ] **UI-004 — Build the Project destination.** Own files, board facts, stackup, fabrication assumptions, metadata/model readiness, and saved profiles.  
  **Done when:** voltage/current/load and solver pitch no longer live with board facts.

- [ ] **UI-005 — Build the Investigation destination.** Add searchable net/refdes/pad browser, topology/path view, raw inspector, and source/sink selection.  
  **Done when:** a user can select a path without a modal dialog and send it to Analysis.

- [ ] **UI-006 — Create one shared scope picker.** Replace `NetTraceDialog` and the two transfer lists with a filterable selection table and shared `SelectionModel`.  
  **Done when:** include/exclude conflicts are impossible in the normal UI.

- [ ] **UI-007 — Provide an explicit-pair editor.**  
  **Done when:** choosing `explicit` always exposes a visible, validated pair list.

- [ ] **UI-008 — Build the Analysis destination.** Include Configure and Run, Results, Compare/What-if, and Manual Estimate modes.  
  **Done when:** net scope, scenarios, overrides, solver choice, execution, and interpretation no longer live in Reports.

- [ ] **UI-009 — Merge Trace and Via / Path.** Represent a manual trace as a one-segment manual path; use the same thickness source, computation, and renderer as longer paths.  
  **Done when:** the old tabs can be removed without losing capability.

- [ ] **UI-010 — Distinguish representative path from full-network result.**  
  **Done when:** least-resistance path and network-equivalent resistance have separate labels and explanations.

- [ ] **UI-011 — Add inherited overrides.** Use profile default → net override → pair/path override, with bulk editing and effective-value provenance.  
  **Done when:** large batches do not require editing every pair row.

- [ ] **UI-012 — Create one reusable result renderer.** Show verdict reasons, primary metrics, margins, budget, element breakdown, assumptions, and solver details.  
  **Done when:** Analysis and report preview consume the same `AnalysisResult`.

- [ ] **UI-013 — Build the Reports destination as a pure consumer.** Select completed runs, templates, result filters, sections, format, preview, and export.  
  **Done when:** Reports cannot change pair scope or silently rerun a solver.

- [ ] **UI-014 — Build Diagnostics.** Include issues, validation, jobs, logs, convergence, environment, and clickable links back to affected objects.  
  **Done when:** parser/solver warnings no longer disappear into tab-specific labels.

- [ ] **UI-015 — Standardize section behavior.** Use collapsible sections, `Expand All ▼`, `Collapse All ▶`, live header summaries, and split panes; do not use drawers or sheets.  
  **Done when:** all primary destinations follow the same interaction convention.

- [ ] **UI-016 — Add search, keyboard, and accessibility behavior.** Preserve selection across destinations; use text/icons in addition to color; provide sensible tab order and copyable values.  
  **Done when:** core workflows are usable without relying on color or pointer-only actions.

## 5. Complete DC resistance and system-power analysis — P1

- [ ] **PWR-001 — Preserve validated trace, via, path, ladder, and mesh calculations.**  
  **Done when:** all v0.13 acceptance vectors pass through the new APIs.

- [ ] **PWR-002 — Implement automatic model selection.** Choose point-to-point, ladder, or mesh based on geometry; show the reason and allow an override.  
  **Done when:** square/complex pours warn or escalate rather than silently using a questionable ladder.

- [ ] **PWR-003 — Add captured multi-net paths.** Resolve ordered `REF.PAD` hops across copper and component bridges.  
  **Done when:** the same path reruns after rerouting and net drift is handled explicitly.

- [ ] **PWR-004 — Resolve bridge resistance with strict precedence.** Project/run override → dedicated field → safe resistance-value parse → error.  
  **Done when:** missing values are reported together with what was tried and how to fix them.

- [ ] **PWR-005 — Add real source models.** Support OCV, source/internal resistance, maximum current, conditions, and provenance.  
  **Done when:** source drop and current limiting are reported separately from copper drop.

- [ ] **PWR-006 — Add three load models.** Constant current, constant resistance, and constant power.  
  **Done when:** operating-point and no-steady-state cases are covered by tests.

- [ ] **PWR-007 — Apply source current limits after solving every load type.**  
  **Done when:** current, resistance, and power loads all enter the same current-limit regime correctly.

- [ ] **PWR-008 — Implement multi-reason verdicts.** At minimum: `PASS`, `FAIL_VOLTAGE`, `FAIL_SOURCE_LIMIT`, `FAIL_NO_STEADY_STATE`, and `ERROR_INCOMPLETE`.  
  **Done when:** co-occurring failures are retained in causal order.

- [ ] **PWR-009 — Add voltage and delivery margins.** Show budget used by source resistance, copper, and bridges.  
  **Done when:** a user can distinguish a source problem from a path problem.

- [ ] **PWR-010 — Support parallel component/path branches.** Use the common nodal solver and report current division, dissipation, and imbalance.  
  **Done when:** N-branch imbalance thresholds are configurable and tested.

- [ ] **PWR-011 — Build the power-tree model.** Link sources, conversion stages, loads, grounds, and component bridges across nets.  
  **Done when:** Investigation can display the tree and Analysis can scope a branch or the full tree.

- [ ] **PWR-012 — Add simultaneous multi-load DC analysis.** Solve shared copper with all enabled loads and duty/state assumptions, not merely one pair at a time.  
  **Done when:** shared-edge currents and voltage drops reflect the combined load case.

- [ ] **PWR-013 — Add scenario and what-if comparison.** Clone a run, change stackup/fabrication/load/geometry overrides, and show deltas without editing the board.  
  **Done when:** baseline and variant results are traceable and exportable.

## 6. Add DC ground-return, current-density, and thermal maps — P2

- [ ] **RET-001 — Identify source and load return terminals.** Use component models and selected operating state to determine DC return injections.  
  **Done when:** every injected ampere has a named source and sink and KCL balances.

- [ ] **RET-002 — Build a resistive ground-plane mesh.** Represent filled copper, voids, splits, antipads, traces that remove plane copper, and layer-to-layer vias.  
  **Done when:** obstacles are geometry/no-conductance regions and current splits naturally through nodal analysis.

- [ ] **RET-003 — Exclude ideal capacitive action from DC steady state.** Include leakage only when explicitly modeled.  
  **Done when:** capacitors do not act as fictitious DC ground sources.

- [ ] **RET-004 — Solve simultaneous DC return currents.** Sum signed injections and solve once per operating scenario.  
  **Done when:** currents combine algebraically and total injection is numerically zero.

- [ ] **RET-005 — Compute branch current and current density.** Cover traces, via barrels, and mesh edges/cells.  
  **Done when:** current-density units and cross-sectional assumptions are present in results.

- [ ] **RET-006 — Generate voltage-gradient and Joule-loss maps.** Compute per-edge `I²R` and allocate it to intersected spatial cells.  
  **Done when:** the heat-source map is in watts/cell and W/mm² with no unsupported temperature claim.

- [ ] **RET-007 — Preserve the IPC trace-rise estimate as a scoped method.** Label extrapolation and the absence of plane heatsinking.  
  **Done when:** it is not confused with whole-board thermal simulation.

- [ ] **RET-008 — Add a board thermal-network solver.** Include in-plane/through-plane conduction and convection boundary conditions; treat radiation as optional.  
  **Done when:** temperature is solved from the full power map rather than from isolated cell convection equations.

- [ ] **RET-009 — Add electrothermal iteration.** Recompute copper resistance from the temperature field until convergence.  
  **Done when:** convergence tolerance, iterations, and non-convergence are reported.

- [ ] **RET-010 — Validate DC return and thermal models.** Use analytic shapes, mesh-refinement studies, measured/reference cases, and an external solver where practical.  
  **Done when:** accuracy bands and known limitations are published.

## 7. Add frequency-aware signal-return screening — P3

- [ ] **SIG-001 — Define signal-channel inputs.** Store driver, receiver, route/net, reference structures, edge rate or frequency sweep, and model provenance.  
  **Done when:** a channel can be rerun without coordinates as persistent identifiers.

- [ ] **SIG-002 — Detect the local reference plane along the route.** Use stackup adjacency and copper continuity.  
  **Done when:** the route is segmented wherever the reference structure changes.

- [ ] **SIG-003 — Detect return-path discontinuities.** Flag plane splits, voids, cutouts, excessive detours, missing stitching vias, and layer transitions lacking a nearby return transition.  
  **Done when:** each issue links to a board location and explains the return mechanism expected.

- [ ] **SIG-004 — Model stitching capacitors and vias as impedances.** Use `Zc = ESR + jωESL + 1/(jωC)` and validated via impedance models.  
  **Done when:** capacitors are network edges, not “mini ground sources.”

- [ ] **SIG-005 — Build a complex impedance network.** Use `Z = R + jωL` and complex nodal analysis across selected frequencies.  
  **Done when:** current conservation and impedance results pass analytic tests.

- [ ] **SIG-006 — Add signal-to-return coupling or a validated PEEC/field-solver method.** A plain plane mesh cannot prove that high-frequency return localizes beneath the trace.  
  **Done when:** current localization is correlated to an accepted reference solver.

- [ ] **SIG-007 — Treat vector/obstacle routing as visualization only until validated.**  
  **Done when:** no signoff result is based solely on corner-routing heuristics.

- [ ] **SIG-008 — Provide overlays and risk metrics.** Show return-current magnitude/phase, detour, discontinuities, transition impedance, and confidence level.  
  **Done when:** every signal-return result is labeled Screening, Correlated, or Signoff-capable.

- [ ] **SIG-009 — Correlate against openEMS or another field solver.** Include solid-plane, plane-slot, via-transition, with/without stitching, and reference-change test structures.  
  **Done when:** error bounds are documented by frequency and geometry class.

## 8. CLI, plugin, reporting, and automation — P1/P2

- [ ] **AUTO-001 — Replace the monolithic CLI with subcommands.** Provide `gui`, `init`, `validate`, `inspect`, `run`, `run-paths`, `return-dc`, `return-ac`, `report`, `bundle`, `emit-schema`, and `selftest`.  
  **Done when:** every GUI analysis can be run headlessly from saved inputs.

- [ ] **AUTO-002 — Define stable exit codes.** Distinguish pass, engineering failure, invalid input, solver failure, and cancellation.  
  **Done when:** CI can gate a board revision without parsing prose.

- [ ] **AUTO-003 — Make JSON the canonical machine output.** Text, Markdown, PDF, and future HTML are renderings of the same result object.  
  **Done when:** GUI, CLI, and reports agree field-for-field.

- [ ] **AUTO-004 — Build a thin KiCad path-capture plugin.** Use a modeless ordered-capture dialog and the live `BoardSource`; keep analysis in the shared package.  
  **Done when:** the plugin captures, validates, and saves paths without duplicating solver logic.

- [ ] **AUTO-005 — Add report templates and immutable run selection.**  
  **Done when:** changing a report never mutates the source analysis run.

- [ ] **AUTO-006 — Add a diagnostic-bundle export.** Include versions, hashes, schemas, selected logs, and sanitized paths.  
  **Done when:** troubleshooting data can be shared without exposing unrelated project files.

- [ ] **AUTO-007 — Add CI examples.** Show schema validation, a saved audit run, threshold gating, and report artifact generation.  
  **Done when:** a board revision can be automatically accepted or rejected reproducibly.

## 9. Verification and release gates — P0 through P3

- [ ] **QA-001 — Add unit tests for every equation and unit conversion.**  
  **Done when:** trace, barrel, temperature coefficient, load models, margins, branch imbalance, and AC impedances have analytic vectors.

- [ ] **QA-002 — Add schema round-trip and migration tests.**  
  **Done when:** load/save does not lose overrides, explicit pairs, provenance, or unknown-version errors.

- [ ] **QA-003 — Add end-to-end workflow tests.** Project load → investigation selection → analysis → result → report.  
  **Done when:** product behavior, not just solver functions, is covered.

- [ ] **QA-004 — Add real-board regression suites.** Include the IP5385 power-bank board (selftest and batch report), complex pours, zone-only pads, split nets, unreachable terminals, and large ground nets.
  **Done when:** prior real-board defects cannot recur silently.
  **Status (Session 01):** Partial — IP5385 selftest (284 vectors) and batch report (1 net, 11 pairs) fixtures and comparator committed; CI automation deferred.

- [ ] **QA-005 — Add mesh refinement and fast-vs-mesh correlation tests.**  
  **Done when:** automatic solver choice is backed by measured error and cost.

- [ ] **QA-006 — Add performance budgets.** Set thresholds for project load, interactive selection, simple solve, mesh solve, batch solve, and report render.  
  **Done when:** regressions fail automated benchmarks or require an explicit waiver.

- [ ] **QA-007 — Add GUI state and accessibility tests.**  
  **Done when:** selection persistence, disabled-state explanations, keyboard order, progress cancellation, and non-color status are verified.

- [ ] **QA-008 — Publish model confidence and limitations.**  
  **Done when:** reports distinguish validated DC resistance, estimated thermal behavior, and screening-only signal-return results.

- [ ] **QA-009 — Define release gates by capability.**  
  **Done when:** resistance v1, system-power v1, DC-return v1, and signal-return screening each have separate acceptance criteria and version labels.

## Recommended implementation sequence

1. Protect baseline and split architecture (`BASE`, `ARCH`).
2. Establish schemas and `.pathminer/` storage (`DATA`).
3. Rebuild the application shell and shared state (`UI`).
4. Complete multi-net/system-power analysis (`PWR`).
5. Stabilize CLI, reports, plugin capture, and CI (`AUTO`).
6. Add DC return/current-density/thermal capability (`RET`).
7. Add and correlate frequency-aware signal-return screening (`SIG`).
8. Apply the matching verification gates throughout (`QA`).
