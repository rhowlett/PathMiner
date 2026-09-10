# Session 07 — Common network, builders and model-selection policy

- **Session:** 07
- **AI / model / effort:** Claude / Opus-4.8 / extra
- **Role:** implementing writer
- **Branch:** `ai/session-07-claude-network-builders`
- **Base commit:** `27bc7503676067b705a283680726d173bee00038` ("chore: integrate Session 06 and assign Session 07")
- **Final commit:** `1a975b73ad4d5a671e527a74c735bafbe4b621cd`
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
| PWR-002 | contribution (policy slice) | implemented (open) | `pathminer/analysis/model_selection.py` chooses point-to-point / ladder / mesh from geometry, states a reason, and **escalates or warns** on square/complex pours rather than silently laddering; user override retained with marker + warning. Tested in `tests/test_model_selection.py`. UI reason/override wiring is a later session. |
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
- `pathminer/analysis/model_selection.py` — `MODELS`, `ModelChoice`, `select_model`, `select_model_for_pour`.
- `tests/test_network.py`, `tests/test_builders.py`, `tests/test_model_selection.py`.

**Modified / removed:** none. (No existing or shared file was touched; all work is within the session's owned write scope.)

## APIs / schemas changed

- New public APIs only, all additive under `pathminer.core.network`,
  `pathminer.analysis.builders`, and `pathminer.analysis.model_selection`.
- No existing API signature, schema, default, unit, tolerance, or numerical
  behavior was changed. `pathminer/core/__init__.py` and
  `pathminer/analysis/__init__.py` were **not** modified (out of scope); the new
  modules are imported by their full dotted path.

## Tests / results

| Command | Exit | Result | Runtime |
|---|---|---|---|
| `python3 -m pytest -q tests/test_network.py tests/test_builders.py tests/test_model_selection.py` | 0 | 65 passed | ~0.55 s |
| `python3 -m pytest -q` (full regression) | 0 | 445 passed (380 baseline + 65 new) | ~2.29 s |

Environment: SciPy 1.18.1 / NumPy 2.5.2 present (the mesh fixtures exercise the
sparse SciPy backend via the dispatcher; the pure-Python CG path is the fallback
when SciPy is absent and is what the `backend` field would report then).
No tests were skipped in this run. No unrun test is reported as passing.

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
  scope. No net-level graph builder ("routed traces/vias without zones") is
  provided here; `select_model` names that case as `point_to_point`.
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
- **PWR sessions:** `model_selection.select_model_for_pour` and the three
  builders are the intended entry points for the routed/pour analysis runner;
  `ModelChoice` carries the reason/override/warnings the result renderer needs.

## Recommended next action

Coordinator review of the diff and handoff; on approval, integrate at the
recorded final commit and open the dependent sessions (08, 13, and the PWR
wave) that consume `ResistorNetwork` and the builders. Consider assigning the
paired ChatGPT prompt as a read-only reviewer of the numerics.

Status: **READY_FOR_REVIEW**
