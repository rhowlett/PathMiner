# Session 04 — AI Handoff

- Status: READY_FOR_REVIEW (re-submitted after coordinator review
  `CHANGES_REQUESTED`, then the 2026-09-08 coordinator correction making
  non-positive resistances raise; see "Review repair" and "2026-09-08
  correction" below)
- AI / model / speed / effort: Claude / Opus-4.8 / not-applicable / extra
- Branch / worktree: ai/session-04-claude-geometry-solver
- Base commit: `5d97fc7d00421f048042a91b37d4f188a75352fa`
  (recorded base per SESSION_STATUS.csv is `293a1bed9cc8`; `5d97fc7` is that
  coordinator-approved commit plus one metadata-only edit to
  `SESSION_STATUS.csv` — the "integrate Session 03 and assign Session 04"
  bookkeeping. `293a1be`, Session 02's result commit `a6ac7b7`, and
  Session 03's result commit `1b97f16` are all ancestors of HEAD; no
  owned-scope file differs between `293a1be` and `5d97fc7`. Recorded HEAD per
  the prompt's "record `git rev-parse HEAD`" rule.)
- Final commit: `0cbae38afa9b3aafc77ec030326b9c6d086b24ff`
  (first cut `deb88813e9b97561a5c05cf73050ec9682e9919e`; first review repair
  `583ed1fa345dd9195c9e316d93bf5dd540eb2c52`; the 2026-09-08 non-positive
  correction commit above supersedes both on the same branch. The handoff-update
  commit that follows it carries this file pair.)
- Patch checksum: sha256 `70243e248a28e5dd334971f8d267edc3a7dec52da8c571e403b2fb1cea2e87c8`
  (diff `5d97fc7..0cbae38`, owned-scope files: geometry.py, solver.py,
  test_geometry.py, test_solver.py, ADR-010.md)

## Preflight (recorded before any edit)

- Prerequisite Session 02: INTEGRATED (SESSION_STATUS.csv row 2; result commit
  `a6ac7b7`, in HEAD ancestry). Session 03 also INTEGRATED (`1b97f16`, in
  ancestry).
- Owned write scope confirmed unclaimed: all five target files were absent
  before this session.
- Environment: Python 3.12.13, pytest 9.1.1, **SciPy 1.18.1 / NumPy 2.5.2
  present** — so the optional-SciPy backend path executes rather than skipping.
- Pre-change tests: `python3 -m pytest -q` → **93 passed**, exit 0.

## Review repair (coordinator `CHANGES_REQUESTED`, 2026-09-05)

Coordinator review of the first cut (`deb8881`) requested backend
consistency: dense, CG, SciPy, and `auto` must behave identically for
disconnected endpoints, unrelated components, `src == dst`, non-positive /
non-finite resistances, missing endpoints, and CG non-convergence — while
preserving v0.13 numerical parity on valid connected graphs — with explicit
regression tests asserting consistent outcomes across every available backend.

**Root cause (inherited from v0.13, not a port defect).** v0.13's
`_solve_scipy` validated its inputs and restricted the solve to the source's
connected component, but `solve_cg` did neither (it returned the last iterate
for a disconnected or non-converged system) and the dense `network_resistance`
path raised a bare `singular network matrix` on unrelated components and
`KeyError` on `src == dst` / a missing endpoint. The three backends could
disagree on whether a network was solvable at all.

**Repair (owned scope only — `pathminer/core/solver.py`, `tests/test_solver.py`,
`documents/adr/ADR-010.md`, and this handoff pair):**

- Added one shared helper `pathminer.core.solver._prepare(edges, src, dst)`
  that every edge-list backend and the `auto` dispatcher now route through. It
  validates resistances (finite required; non-positive `r <= 0` on a real edge
  rejected with a named error; self-loops dropped as in v0.13), checks endpoint
  presence and `src != dst`, computes `src`'s connected
  component, requires `dst` in it, and returns the component-restricted edge
  list with v0.13's `sorted(…, key=str)` node order.
- Added a **convergence guard** to `solve_cg`: it raises
  `ValueError("conjugate-gradient solve did not converge")` when the residual
  never falls below `tol` within `maxit`, instead of returning the iterate — so
  CG can no longer report a plausible value for an unconverged system.
- Unified the error taxonomy across all backends (`non-finite resistance in
  network`, `endpoint not in graph`, `source and sink are the same node`,
  `endpoints are not connected`, `conjugate-gradient solve did not converge`).
- Unrelated (disconnected) components are now **dropped consistently** by every
  backend (the rule v0.13 already applied only in `_solve_scipy`), so a stray
  island neither changes the answer nor makes the dense/CG solve diverge.

**Parity preserved.** For a valid connected network the component is the whole
graph, so `_prepare` changes neither the node set nor its ordering. Re-run of
the V11/V20 parity cross-check: `solve_cg` and `solve_scipy` remain
**bit-identical** (`==`) to v0.13 and the dense dispatcher stays within 1e-12
of v0.13 `network_resistance` (24/24 checks). The only inputs whose behavior
changed are the previously undefined or backend-divergent ones, which now fail
loudly and identically. Two v0.13-tolerated inputs are now rejected: a
non-finite (`NaN`/`inf`) resistance (v0.13's dense path poisoned the matrix with
`1/NaN`; its sparse path silently dropped it), and — per the 2026-09-08
coordinator correction — a non-positive (`r <= 0`) resistance on a real edge,
which v0.13 silently dropped on every path. Carry an "open" as an omitted edge
(not `inf`) and a "short" by merging the two nodes (not `0`). Self-loops
(`u == v`) remain dropped. This is documented in ADR-010's "Backend Consistency
and Input Validation" section.

**New regression tests** (`tests/test_solver.py`, "Cross-backend consistency"
section), each asserting the same outcome across every available backend:
disconnected endpoints raise on all; unrelated component ignored identically;
`src == dst` raises on all; zero and negative resistances raise on all
(a self-loop is still dropped, asserted separately); non-finite
(`NaN`/`+inf`/`-inf`) raises on all; missing endpoint raises on all; CG
non-convergence raises (dense/scipy still solve); and a combined
solvable/unsolvable-diagnosis agreement test. The now-obsolete
`test_dense_singular_network_raises` (which asserted the old bare "singular
network matrix" on a disconnected edge list) was replaced by
`test_disconnected_endpoints_raise_on_every_backend`; the raw-matrix
`test_solve_dense_singular_matrix_raises` for the `solve_dense` primitive is
retained.

## 2026-09-08 correction (coordinator: non-positive must raise)

A follow-up coordinator correction required that **zero and negative
resistances raise the same named error across dense, CG, SciPy, and `auto`**
rather than being silently dropped (self-loop handling unchanged). The first
repair had kept v0.13's "drop `r <= 0`" behavior; a dropped zero/negative edge
hides corrupt input and is inconsistent with rejecting `NaN`/`inf`.

- `pathminer/core/solver._prepare` now raises
  `ValueError("non-positive resistance in network")` when `r <= 0` on a real
  edge (`u != v`). Self-loops (`u == v`) are still dropped, checked *before* the
  sign test, so their handling is unchanged.
- `tests/test_solver.py`: the old `test_non_positive_resistances_are_dropped_consistently`
  is replaced by `test_non_positive_resistance_raises_on_every_backend`
  (parametrized over zero and negative, asserting the named error on every
  available backend and on `auto`) plus `test_self_loop_is_still_dropped_not_raised`.
  Focused suite 79 → **81** (net +2).
- ADR-010's behavior table and parity note updated; this handoff pair updated.
- **Parity re-verified** after the correction: v0.13 cross-check **24/24**
  (`solve_cg`/`solve_scipy` bit-identical, dense within 1e-12) and the canonical
  IP5385 regression PASS — no valid connected graph carries a non-positive edge,
  so the change touches corrupt input only.

## Implementation note (required before coding, item 1 of Required work)

The v0.13 source of truth is `tools/pcb_trace_resistance.py` (5545 lines). Its
pure-geometry helpers and numerical backends are already free of Qt/KiCad/I/O
and extract cleanly:

- **Geometry** (into `pathminer/core/geometry.py`): `_pt_in_poly`,
  `_seg_poly_crossings`, `_dist_to_poly`, `_principal_axis`,
  `clip_track_to_pour`, `cluster_vias`, `via_array_summary`, `_arc_length_mm`.
  These are pure planar geometry on coordinate tuples and vertex rings; they
  know nothing about nets, boards, or stackups.
- **Solver** (into `pathminer/core/solver.py`): `_solve_dense`, `solve_cg`,
  `_solve_scipy`, the dense/sparse crossover embedded in `network_resistance`,
  `DENSE_NODE_LIMIT = 400`, `calibrate_solver`, `estimate_seconds`, and the
  optional-SciPy import guard `HAVE_SCIPY`.

Scope boundaries observed:

- `Pour`, `parse_pours`, `build_pour_ladder`, `build_graph_pour`,
  `mesh_pour_edges`, and `estimate_nodes` were **not** ported: they parse KiCad
  copper or build the net graph and are board/network-coupled (Sessions
  05–07), not pure geometry/solver. `_principal_axis` (used by `Pour`) is pure
  and was extracted; `Pour` itself is left for the board/model layer.
- `network_resistance` takes an adjacency map plus a resistance function
  (`rfun`) — a network-layer shape (ARCH-004, Session 07). Rather than pull the
  network representation into `core`, the dispatcher here
  (`two_terminal_resistance`) operates on the backend-neutral **edge list**
  `[(u, v, r), …]` that the CG/SciPy backends already share, and reproduces the
  same dense/sparse crossover. Session 07 builds edge lists and calls it.
- IPC-2221 trace-temperature-rise is not geometry/solver and stays out (as in
  Session 03; RET-007 / Session 31).

Public names are new and descriptive (the v0.13 helpers were private, e.g.
`_pt_in_poly`); each function's docstring records the v0.13 symbol it came from
so the compatibility session (08) can wire the legacy script to import from
`pathminer.core`. This follows Session 03's precedent (which likewise renamed
private helpers to clean public APIs and documented provenance).

## Punch-list status

| ID | Role | Status | Evidence |
|---|---|---|---|
| BASE-005 | closure owner | closed | Done-when is "the decision and performance thresholds for introducing compiled acceleration are documented." `documents/adr/ADR-010.md` records the deferral decision (defer C/C++ rewrite; optimize graph/factorization reuse first; keep the pure-Python `solve_cg` fallback always available; adopt SciPy opportunistically) **and** the thresholds: `DENSE_NODE_LIMIT = 400` dense/sparse crossover, the SciPy-else-CG sparse preference, the CG `tol=1e-13`/`maxit=50000`, the `t = a·nodes^b` calibration model, and explicit trigger criteria for revisiting compiled acceleration. The pure-Python fallback is retained in code (`solve_cg`, guarded `HAVE_SCIPY`). Thresholds are codified in `pathminer/core/solver.py` and regression-pinned by `tests/test_solver.py::test_dense_node_limit_is_400`. |
| ARCH-006 | contributor (backend slice) | implemented | "Consolidate solvers behind one dispatcher … with identical results and metadata. Done when: backend agreement is asserted on the same networks." `two_terminal_resistance` is the single dispatcher over dense / pure-Python CG / optional SciPy. Backend agreement is asserted on the same networks in `tests/test_solver.py` (`test_v11_backends_agree` across all 7 V11 topologies; `test_v20_scipy_and_python_solvers_agree`). The review repair strengthens this slice: agreement now covers *failure*, not just value — every backend routes through the shared `_prepare`, so dense/CG/SciPy/`auto` accept and reject the same inputs (asserted in the new cross-backend consistency tests). Left **implemented, not closed**: ARCH-006's overall closure is Session 08 (SESSION_INDEX.md / plan §15.2), which also owns the compatibility façade that routes the legacy runtime through this dispatcher. |
| ARCH-010 | contributor | implemented | "Split the self-test by module while retaining stable vector IDs." Module tests retain the original v0.13 acceptance-vector identities for this slice (V11 network, V13 geometry, V14 shunt array, V20 backend agreement/calibration) in test IDs and docstrings, so a future aggregate `--selftest` and these module tests report the same vector identities. Closure remains later (Session 08/10). |

## Changes

- Files added:
  - `pathminer/core/geometry.py`
  - `pathminer/core/solver.py`
  - `tests/test_geometry.py`
  - `tests/test_solver.py`
  - `documents/adr/ADR-010.md`
- Files modified: none
- Files removed: none
- Public APIs changed (all new, additive):
  - `pathminer.core.geometry`: `point_in_polygon(pt, poly)`,
    `segment_polygon_crossings(p1, p2, poly)`, `distance_to_polygon(pt, poly)`,
    `principal_axis(pts) -> ((cx,cy),(ux,uy),length,width,u0)`,
    `clip_segment_to_polygon(p1, p2, poly) -> (outside, inside)`,
    `cluster_points(points, max_gap=2.0)`, `cluster_summary(groups)`,
    `arc_length(sx, sy, mx, my, ex, ey)`.
  - `pathminer.core.solver`: `HAVE_SCIPY`, `DENSE_NODE_LIMIT`,
    `solve_dense(matrix, rhs)`, `solve_cg(edges, src, dst, tol=1e-13,
    maxit=50000) -> (r, n, its)`, `solve_scipy(edges, src, dst) -> (r, n, 1)`,
    `two_terminal_resistance(edges, src, dst, backend="auto",
    dense_limit=DENSE_NODE_LIMIT) -> float`, `calibrate_solver() -> dict`,
    `estimate_seconds(nodes) -> float`. `__all__` is unchanged; the shared
    validator `_prepare` is private (leading underscore, not exported).
    Signatures are unchanged by the repair; the only public-surface change is
    stricter, named `ValueError`s (see the behavior table in ADR-010): `solve_cg`
    now raises `"conjugate-gradient solve did not converge"` rather than
    returning a non-converged iterate, and all backends now raise the same
    validation errors (`non-finite resistance in network`, `endpoint not in
    graph`, `source and sink are the same node`, `endpoints are not connected`).
- Schemas/migrations changed: none.
- Compatibility consequences: none. `tools/pcb_trace_resistance.py` was not
  touched; it remains the runtime behavioral source of truth and still carries
  its own copies of these functions. Wiring the legacy script (or its generated
  replacement) to import from `pathminer.core` is a Session 08 step.

## Verification

All commands below are the **post-correction** results (2026-09-08 re-run); the
first-cut counts (70 focused / 163 full) and the first-repair counts (79 / 172)
are superseded by the 2026-09-08 non-positive correction (81 focused / 174 full).

| Command | Exit | Result/counts | Runtime | Notes |
|---|---:|---|---:|---|
| `python3 -m pytest -q` (pre-change baseline) | 0 | 93 passed | — | Recorded before any edit (first cut). |
| `python3 -m pytest tests/test_geometry.py tests/test_solver.py` | 0 | **81 passed** | ~1.9s | Required focused command. 79 first-repair + 2 net from the 2026-09-08 non-positive correction (replaced the non-positive-dropped test with parametrized zero/negative named-error tests plus a self-loop-still-dropped test). |
| `python3 -m pytest` (post-correction, full suite) | 0 | **174 passed** | ~2.1s | 93 baseline + 81 session tests; no regressions; import-boundary tests (ARCH-002) still pass against the `core/` files. |
| `QT_QPA_PLATFORM=offscreen python3 tests/baseline/regression_compare.py all` | 0 | **headless 118/118, powerbank 284/284, IP5385 report 1 net / 11 pairs** — all match golden fixtures | — | Canonical IP5385 regression. `tools/pcb_trace_resistance.py` is untouched, so the v0.13 runtime is byte-for-byte unchanged; board SHA-256 `0a1ca4dc…` and netsel SHA-256 `ff8e5ec8…` verified. |
| v0.13 parity cross-check (ad-hoc, `QT_QPA_PLATFORM=offscreen`) | 0 | **24/24 PASS** | — | Re-run after the repair. On every V11/V20 vector, `solve_cg` and `solve_scipy` are **bit-identical** (`==`) to v0.13 `solve_cg` / `_solve_scipy`; `two_terminal_resistance(backend="dense")` matches v0.13 `network_resistance` within 1e-12. Confirms the shared `_prepare`/component restriction did not perturb valid connected-graph numerics. Not committed. |

- SciPy/NumPy are installed, so all SciPy-guarded tests executed (none skipped
  for missing SciPy). No fixture or dependency was unavailable.
- The focused suite grew from 70 to 81 (70 → 79 in the first repair, 79 → 81 in
  the 2026-09-08 non-positive correction): the required verification command's
  count changed because the coordinator authorized the added regression tests.

## Decisions and assumptions

- **Dispatcher operates on edge lists, not adjacency+rfun.** v0.13's
  `network_resistance(adj, a, b, rfun)` mixes the network representation
  (ARCH-004, Session 07) with backend dispatch. To keep `core/solver.py` pure
  and backend-independent, `two_terminal_resistance` takes the backend-neutral
  `[(u, v, r), …]` edge list already shared by `solve_cg`/`solve_scipy`, and
  reproduces the identical dense/sparse crossover (`node_count <=
  DENSE_NODE_LIMIT` → dense, else SciPy-if-present-else-CG). The dense path was
  re-derived from an edge list to build the same grounded conductance matrix
  and return `V[dst]`; verified equal to v0.13 `network_resistance` within
  1e-12 (parity cross-check). Session 07 will build edge lists (merging
  equipotential groups, pricing edges via `core.resistance`) and call this.
- **Node ordering is `sorted(nodes, key=str)`** in all three backends and the
  dense dispatcher, matching v0.13's CG/SciPy convention and making output
  deterministic (Required-work item 5). v0.13's small-graph dense path used
  dict-insertion order; the resulting float differences are ~1e-15, far inside
  the V11 tolerances (1e-12 exact rationals, 1e-10 for the bridge).
- **Public names + provenance docstrings** (see Implementation note). Behavior,
  epsilons, and tie-breaks are copied verbatim; only names change.
- **`solve_scipy` gains a named `RuntimeError`** when SciPy is absent (v0.13
  only ever called it under `if HAVE_SCIPY`). This is a guard on a newly public
  function, not a numerical change, and satisfies the acceptance gate's
  "named errors as applicable."
- **BASE-005 marked closed.** Its Done-when is documentation of a decision and
  thresholds, which is fully within this session's owned scope (ADR-010 +
  codified thresholds). This differs from Session 03's PWR-001 (left open
  because its clause required cross-session modules); BASE-005 has no such
  cross-session dependency.
- **(Repair) Shared `_prepare`, not per-backend patches.** Consistency is
  enforced structurally: one helper validates and restricts to `src`'s
  component, and every backend calls it. This is why dense/CG/SciPy cannot
  drift apart on edge cases, and why parity holds (for a connected graph the
  helper is a no-op on the node set/order).
- **(Repair) `src == dst` raises rather than returning 0.0.** Grounding `src`
  and reading `V[src]` would give a self-consistent `0.0`, but a self-resistance
  query is far more likely a caller error; a named error is loud and matches the
  other degenerate-input handling. Chosen for consistency and safety; recorded
  in ADR-010's behavior table.
- **(Repair) Non-finite and non-positive resistances rejected; self-loops
  dropped.** `NaN`/`inf` — which v0.13 handled inconsistently (dense poisoned
  via `1/NaN`; sparse silently dropped) — now raises on every backend. Per the
  2026-09-08 coordinator correction, a non-positive `r <= 0` on a real edge,
  which v0.13 silently dropped on every path, now also raises the named
  `non-positive resistance in network` on every backend rather than being
  dropped. No valid connected graph carries either, so parity is unaffected.
  `inf` as "open" and `0` as "short" are not supported; omit the edge or merge
  the nodes. Self-loops (`u == v`) remain dropped, unchanged.
- **(Repair) CG convergence is checked, never assumed.** `solve_cg` raises if
  the residual never reaches `tol` within `maxit`. For the SPD grounded
  Laplacian of a connected component CG always converges well within `maxit`, so
  this never fires for valid inputs (V11/V20 unchanged); it only prevents
  returning a non-converged iterate.

## Deviations, known failures, or incomplete work

- `documents/change_log.md` was not updated: it is outside this session's owned
  write scope, and Sessions 02–03 likewise left it to integration. Recommend
  the coordinator or the integration session add the Session 04 entry.
- `pathminer/core/__init__.py`'s planning comment lists `geometry.py` and
  `solver.py` as "extracted in Sessions 03–04" with brief descriptions that
  match what was built; it was left untouched (outside owned write scope).
- No known test failures. Nothing was skipped for a missing dependency.

## Impact on dependent sessions

- **Session 05 (KiCad syntax, stackup, prefs)** and **Session 06
  (BoardSource / file-backed board model):** copper parsed from a board should
  be handed to `core.geometry` as plain `(x, y)` tuples and `[(x, y), …]`
  rings; `Pour`-style strip scoring can be rebuilt on `principal_axis`.
- **Session 07 (common network + builders):** build the network as an edge list
  and call `pathminer.core.solver.two_terminal_resistance` (or a chosen
  backend directly); price edges with `pathminer.core.resistance`
  (Session 03) and clip tracks with
  `pathminer.core.geometry.clip_segment_to_polygon`. The dispatcher already
  reproduces v0.13's model dispatch, so ladder/mesh builders need only produce
  edges.
- **Session 08 (compatibility integration + single-file build):** closure point
  for ARCH-006 — route `tools/pcb_trace_resistance.py` (or its generated
  replacement) through `two_terminal_resistance`, re-verify the full V-vector
  set end to end, and remove the legacy in-file solver/geometry copies.
- **Session 13 (factorization reuse, ARCH-007):** ADR-010 names graph/
  factorization reuse as the first optimization before any compiled work; build
  it on this dispatcher's stable API.
- All APIs introduced are additive and self-contained; no breaking change to
  any existing surface is expected.

## Recommended next action

Coordinator: review this diff and handoff (optionally route a read-only
paired-model review of `deb8881` per the Session Execution Rules), then
integrate onto the branch Sessions 05–07 start from. BASE-005 is presented as
closed via ADR-010; ARCH-006/ARCH-010 remain contributor slices to be closed in
their named later sessions. Only the coordinator marks the session INTEGRATED.
