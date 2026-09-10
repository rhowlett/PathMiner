# Session 07 — Common network, builders and model-selection policy

- **Session:** 07
- **AI / model / effort:** Claude / Opus-4.8 / extra
- **Role:** implementing writer
- **Branch:** `ai/session-07-claude-network-builders`
- **Base commit:** `27bc7503676067b705a283680726d173bee00038` ("chore: integrate Session 06 and assign Session 07")
- **Final commit:** `ff567d876d4577bedb164fec545eadfcfff9ae85`
  (implementation `1a975b7`; self-review fixes `e4f2fe5`; coordinator-review fixes `ff567d8`)
- **Status:** READY_FOR_REVIEW

## Objective (met)

Created the common typed resistor-network model and the pure point-to-point,
ladder, and mesh builders, plus an explainable automatic model-selection policy
and fast-versus-mesh correlation fixtures.

## Implementation note (written before coding)

- Session 04 already consolidated the three solver backends behind
  `pathminer.core.solver.two_terminal_resistance`, which consumes a
  backend-neutral edge list `[(u, v, r), ...]` and whose docstring names *this*
  layer as responsible for "building them (from an adjacency map, merging
  equipotential groups, pricing edges)." Session 07 therefore adds the network
  type and builders **on top of** the existing solver rather than re-deriving
  any numerics.
- Pricing reuses the validated v0.13 formulas already ported into
  `pathminer.core.resistance` (Session 03, PWR-001): `trace_resistance` and
  `via_resistance`. No resistance formula is duplicated in this session.
- Pour axis/aspect analysis reuses `pathminer.core.geometry.principal_axis` /
  `point_in_polygon` (Session 04). `pathminer.models.board.Pour` (Session 06) is
  pure geometry and, by its own docstring, delegates axis/mesh/ladder analysis
  to this network-builder layer — so the ladder/mesh builders accept any object
  exposing `.net` and `.fills` (in particular that `Pour`).
- Equipotential ties are modelled with union-find node **merges**, not near-zero
  tie resistors, exactly as v0.13's `build_graph_pour` does ("a tie is the same
  physical copper, so merge the nodes rather than joining them with a near-zero
  resistor, which would wreck the solver's conditioning").

## Punch-item status

| ID | Role | Status | Evidence |
|----|------|--------|----------|
| ARCH-004 | closure owner | **closed** | Done-when ("point-to-point, ladder, and mesh builders all emit the same network type") demonstrated: `tests/test_builders.py::test_all_builders_emit_resistor_network` asserts all three builders return `pathminer.core.network.ResistorNetwork`, and `test_all_builders_produce_solvable_networks` asserts each solves to a `TwoTerminalResult`. |
| ARCH-006 | contribution (dispatcher prerequisites) | implemented (open) | `ResistorNetwork.edge_list()` produces the backend-neutral `[(u,v,r)]` the Session 04 dispatcher consumes, and `ResistorNetwork.two_terminal()` delegates to it; backend passthrough agreement tested (`tests/test_network.py::test_backend_passthrough_agrees`). Whole-item closure remains with the dispatcher owner. |
| PWR-002 | contribution (policy slice) | implemented (open) | `pathminer/analysis/model_selection.py` chooses point-to-point / routed-graph / ladder / mesh from geometry (S8.7's four cases), states a reason, and **escalates or warns** on square/complex/unknown pours rather than silently laddering; a zone-less routed net is reported `ROUTED_GRAPH` (unsupported until its builder exists) rather than assumed to be a series chain; every applicable warning is retained across a user override. Tested in `tests/test_model_selection.py`. UI reason/override wiring is a later session. |
| QA-005 | contribution (correlation fixture slice) | implemented (open) | Fast-vs-mesh correlation and mesh-refinement convergence fixtures: `tests/test_builders.py::test_fast_ladder_matches_mesh_within_tolerance` (mesh within 3% of the ladder on a strip-like pour) and `test_mesh_converges_toward_ladder_as_pitch_refines` (monotone convergence to <1% as pitch refines). Full cost/backend-choice closure is a later session. |

Only the coordinator may mark the session INTEGRATED.

## Files

**Added**

- `pathminer/core/network.py` — `Node`, `Provenance`, `Edge`, `TwoTerminalResult`, `ResistorNetwork` (union-find merges, `edge_list`, `two_terminal`, `from_edges`).
- `pathminer/analysis/builders/__init__.py` — package exports.
- `pathminer/analysis/builders/pour.py` — `PourGeometry` / `pour_geometry`, `ViaStation`, `Tie` (shared ladder+mesh inputs).
- `pathminer/analysis/builders/point_to_point.py` — `TraceSegment`, `ViaSegment`, `build_point_to_point`.
- `pathminer/analysis/builders/ladder.py` — `LADDER_MIN_ASPECT`, `build_ladder`.
- `pathminer/analysis/builders/mesh.py` — `DEFAULT_MESH_PITCH_MM`, `build_mesh`.
- `pathminer/analysis/model_selection.py` — `MODELS`, `ROUTED_GRAPH`, `ModelChoice`, `select_model`, `select_model_for_pour` (plus the `COMPLEX_POUR_WARNING` / `UNKNOWN_GEOMETRY_WARNING` / `ROUTED_UNSUPPORTED_WARNING` constants).
- `tests/test_network.py`, `tests/test_builders.py`, `tests/test_model_selection.py`.

**Modified / removed:** none. (No existing or shared file was touched; all work is within the session's owned write scope.)

## APIs / schemas changed

- New public APIs only, all additive under `pathminer.core.network`,
  `pathminer.analysis.builders`, and `pathminer.analysis.model_selection`.
- `select_model` / `select_model_for_pour` gained a keyword-only `series_chain`
  flag (default `False`) and can now return the `ROUTED_GRAPH` sentinel for a
  zone-less routed net — added in coordinator-review, still within this new
  session's own API surface (no external caller yet).
- No existing API signature, schema, default, unit, tolerance, or numerical
  behavior was changed. `pathminer/core/__init__.py` and
  `pathminer/analysis/__init__.py` were **not** modified (out of scope); the new
  modules are imported by their full dotted path.

## Tests / results

| Command | Exit | Result | Runtime |
|---|---|---|---|
| `python3 -m pytest -q tests/test_network.py tests/test_builders.py tests/test_model_selection.py` | 0 | 78 passed | ~0.55 s |
| `python3 -m pytest -q` (full regression) | 0 | 458 passed (380 baseline + 78 new) | ~2.73 s |
| `python3 -m pytest -q tests/test_import_boundaries.py` (ARCH-002 guard) | 0 | 48 passed | ~0.18 s |

Environment: SciPy 1.18.1 / NumPy 2.5.2 present (the mesh fixtures exercise the
sparse SciPy backend via the dispatcher; the pure-Python CG path is the fallback
when SciPy is absent and is what the `backend` field would report then).
No tests were skipped in this run. No unrun test is reported as passing.

## Coordinator review pass (findings addressed)

Three defects raised in coordinator review were fixed in `ff567d8`, all within
owned scope, each with a regression test:

- **Ladder dropped coincident terminal aliases.** Ties were keyed by
  `(layer, point)`, so two terminals on the same copper point overwrote each
  other and the dropped one failed to solve (`endpoint not in graph`). Ties are
  now grouped by point and **every** external terminal is merged into that node
  (coincident terminals become one electrical node). (Test:
  `test_builders.py::test_ladder_preserves_coincident_terminal_aliases`.)
- **Complex-pour override lost its warning.** `select_model(has_pour=True,
  aspect=10, complex_pour=True, override="ladder")` returned no warning. All
  caveats (low-aspect, complex, unknown-geometry) are now collected before the
  model is chosen, so an override to the ladder retains "the strip assumption
  does not hold / cannot be justified" (S8.7). (Tests:
  `test_model_selection.py::test_override_to_ladder_on_complex_pour_retains_warning`,
  `...on_unknown_geometry_retains_warning`.)
- **No-zone selection assumed a series chain.** `has_pour=False` always chose
  `point_to_point`, but S8.7 distinguishes a manual series chain from a routed
  graph. A new `series_chain` flag now separates them: a manual chain →
  `point_to_point`; a routed net → `ROUTED_GRAPH`, reported **unsupported** (no
  routed-graph builder exists yet) with a retained warning. (Tests:
  `test_model_selection.py::test_no_zone_routed_net_reports_unsupported`,
  `...test_no_zone_series_chain_selects_point_to_point`,
  `...test_routed_override_to_point_to_point_retains_unsupported_warning`.)

## Self-review pass (findings addressed)

An automated review of the diff was run (`/code-review`, medium). All tests
passed; the findings were edge cases the happy path did not exercise (65 tests
at that point, now 78). Addressed in `e4f2fe5`, all within owned scope:

- **Hashability contract:** `Edge`/`Provenance` were `frozen=True` (advertising
  hashability) but held a dict `detail`, so `hash()` raised `TypeError`. `detail`
  is now excluded from the generated hash; both are genuinely hashable. Equality
  still compares `detail`. (Test: `test_network.py::test_provenance_and_edge_are_hashable_despite_dict_detail`.)
- **Mesh failure modes:** a non-positive pitch and a zero-extent fill now raise
  named `ValueError`s (were `ZeroDivisionError`); a modelled layer missing from
  the stackup raises the same `"layer ... not in the stackup"` `ValueError` the
  other builders raise (was an opaque `StopIteration`). (Tests in
  `test_builders.py`.)
- **Cross-builder consistency:** the mesh now skips a via reaching fewer than two
  modelled layers with the same note the ladder emits (matching v0.13 before its
  ladder/mesh split); the ladder now ties in only on layers that are both filled
  and modelled, matching its own strip-layer filter, so a tie cannot fuse into a
  strip-less node.
- **De-duplication (within this session's own new code):** the `finished_mm`
  layer lookup is consolidated into `builders/pour.py`; the low-aspect warning
  string is consolidated into `builders/ladder.low_aspect_warning`, used by both
  the ladder note and the model-selection warning so their wording cannot drift.
- **Provenance completeness:** `ViaStation.pad_mm` now flows into via-edge
  provenance detail (it was carried but unused).

Findings left as documented decisions rather than code changes:

- **Backend-choice mirror (root cause in `solver.py`, out of scope):**
  `ResistorNetwork.two_terminal` re-derives the dense/sparse crossover to report
  the resolved backend because `two_terminal_resistance` does not return it. This
  mirror is commented; the clean fix (dispatcher returns its resolved backend)
  belongs to the solver's owning session — see Dependent-session impact.
- **`node_count`/`edge_count` are submitted-graph counts:** they report the graph
  handed to the solver (which is exactly what the crossover uses), not the
  post-component-restriction sub-network. Clarified in the docstring; this
  matches the dispatcher's own accounting.
- **Mesh bbox spans all fill layers:** the grid bounding box is taken over every
  fill layer (including any not in `order`), identical to v0.13's
  `mesh_pour_edges`. Left unchanged to preserve v0.13 numerical parity; in
  practice pour fills lie on copper layers that are all in `order`.

## Decisions

1. **Merges, not tie resistors** for equipotential ties (`ResistorNetwork.merge`
   + `edge_list` collapse), preserving v0.13's conditioning contract.
2. **Single validator:** `add_edge` does not re-validate resistance
   finiteness/positivity; the solver's shared `_prepare` remains the one
   validator, so `build → solve` raises the same named errors as a raw edge list
   (verified in `test_network.py`).
3. **Pure builders take explicit geometry/topology inputs** (`ViaStation`,
   `Tie`, a `.net`/`.fills` pour), not the whole `BoardSource`. This keeps the
   builders deterministic and unit-testable and respects dependency direction;
   wiring a live/file `BoardSource` into them is a later (integration/PWR)
   session, matching where that orchestration lived in v0.13
   (`build_graph_pour`).
4. **Model-selection escalation rule:** a pour with aspect below
   `LADDER_MIN_ASPECT` (v0.13's 2:1), or flagged complex, or of unknown
   geometry, escalates to the mesh; a strip-like pour uses the ladder. Overrides
   are honoured but keep the marker and any warning (S8.7).

## Assumptions

- The per-copper-layer geometry `geo` passed to the builders is the mapping
  shape produced by `Stackup.geometry()` and expected by
  `pathminer.core.resistance` (`name`, `z_top_mm`, `finished_mm`, `z_ctr_mm`).
- A pour is represented as `.net` + `.fills` (`{layer: [(x, y), ...]}`), matching
  `pathminer.models.board.Pour`.

## Deviations (numerics-preserving)

- **Mesh determinism refinement over v0.13.** v0.13's `mesh_pour_edges` chose a
  via's hub cell and a tie's nearest cell by `set` iteration order, which is not
  stable. `build_mesh` iterates live cells in sorted order and breaks
  nearest-cell distance ties by cell index. Because every cell a barrel covers
  is merged into one electrical node regardless of which is named the
  representative, the two-terminal **result is unchanged**; only the node
  *identity* becomes reproducible (`tests/test_builders.py::test_mesh_is_deterministic`).
- **`build_ladder` does not itself skip a pour that has no vias.** v0.13's
  `build_graph_pour` decided, as orchestration, to ignore a pour with no landing
  vias ("pour present but no vias land in it; zone copper ignored"). The pure
  `build_ladder` builds strips from whatever via/tie stations it is given; the
  strip/rung/tie **numerics are identical** to v0.13 for the overlapping case.
  The "ignore a vialess pour" policy belongs to the caller/orchestration layer,
  as it did in v0.13.

## Known issues / limitations

- The builders are not yet wired to a `BoardSource`; track-vs-pour clipping,
  pad-in-pour tie discovery, and via-array clustering (v0.13 `build_graph_pour`)
  are the integration layer's responsibility and are out of this session's
  scope. No routed net-graph builder ("routed traces/vias without zones") is
  provided here; `select_model` returns `ROUTED_GRAPH` for that case and marks
  it unsupported until the builder lands (a future session must add it).
- Fast-vs-mesh agreement depends on matching boundary conditions: the QA-005
  fixture distributes the end injection across the pour width so the mesh's
  point-contact spreading matches the ladder's full-width strip node. A single
  point tie legitimately shows a larger mesh-vs-ladder gap (constriction
  resistance the 1-D ladder cannot represent); this is physical, not a defect.

## Dependent-session impact

- **Session 08 (compatibility integration / single-file build):** may re-export
  `ResistorNetwork` and the builders through the package hubs
  (`pathminer/core/__init__.py`, `pathminer/analysis/__init__.py`), which this
  session intentionally left untouched.
- **Session 13 (headless runner / factorization reuse, ARCH-007):**
  `ResistorNetwork.edge_list()` is the stable hand-off point for building/factor
  a graph once per net/model and back-solving pairs.
- **Solver-owning session (ARCH-006 follow-up):** consider having
  `two_terminal_resistance` return its resolved backend so
  `ResistorNetwork.two_terminal` reports it directly instead of mirroring the
  crossover. Purely a robustness/no-drift improvement; `core/solver.py` is
  outside this session's write scope.
- **PWR sessions:** `model_selection.select_model_for_pour` and the three
  builders are the intended entry points for the routed/pour analysis runner;
  `ModelChoice` carries the reason/override/warnings the result renderer needs.
  Callers must pass `series_chain=True` for a manual chain; a routed net returns
  `ROUTED_GRAPH`, which the runner must surface as unsupported.
- **A future session must add the routed net-graph builder** (S8.7 "routed
  traces/vias without zones"); until then `select_model` returns `ROUTED_GRAPH`
  as unsupported.

## Recommended next action

Coordinator review of the diff and handoff; on approval, integrate at the
recorded final commit and open the dependent sessions (08, 13, and the PWR
wave) that consume `ResistorNetwork` and the builders. Consider assigning the
paired ChatGPT prompt as a read-only reviewer of the numerics.

Status: **READY_FOR_REVIEW**
