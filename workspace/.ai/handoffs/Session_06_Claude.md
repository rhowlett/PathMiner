# Session 06 Handoff — BoardSource and file-backed board model

- **Session:** 06
- **AI:** Claude
- **Model:** claude-sonnet-5
- **Effort:** high
- **Status:** READY_FOR_REVIEW
- **Branch:** ai/session-06-claude-board-source
- **Base commit:** d7f836456098ea9bb1119dadd35cbacb69aaadff
- **Final commit:** 442947af4c771e5460378b48045a21e6a8fe1e6a

---

## Preflight (recorded before coding)

- Active model: Claude Sonnet 5 (`claude-sonnet-5`).
- Branch: `ai/session-06-claude-board-source` (already checked out in this worktree).
- Base commit at session start: `451668d81382265bc0f68a2250359987a964b1a9`
  (`chore: integrate Session 05 and assign Session 06`), which is
  `SESSION_STATUS.csv`'s recorded base commit
  `d7f836456098ea9bb1119dadd35cbacb69aaadff` plus that one status-file
  commit — `git show --stat` confirmed the only diff between the two is
  `.ai/coordination/SESSION_STATUS.csv`. No implementation drift between
  the coordinator-recorded base and the actual worktree HEAD.
- Prerequisite: Session 05 (KiCad syntax/stackup/prefs extraction).
  `SESSION_STATUS.csv` row 5 shows `INTEGRATED`, merged into `main` at
  `d7f836456098`. Confirmed.
- Owned write scope (from the session prompt): `pathminer/kicad/board.py`,
  `pathminer/kicad/source.py`, `pathminer/models/board.py`,
  `tests/test_board_source.py`, `tests/fixtures/kicad/`. No other writer
  claims these paths (git status was clean at start; no other branch
  touches them per `SESSION_STATUS.csv`).
- Required tests (session prompt): `python3 -m pytest -q tests/test_board_source.py`
  and, when proportionate, `python3 -m pytest -q`.
- Pre-change baseline: `python3 -m pytest -ra` → **324 passed** (matches
  Session 05's final count exactly).
- Blockers: none. Preflight clear; proceeded to implementation.

---

## Implementation note (written before coding)

**Objective:** define `BoardSource`, implement `FileBoardSource`, and
provide stable `REF.PAD` lookup plus drift diagnostics (ARCH-003).

**Source inspected:**
- v0.13 `BoardNets` (`tools/pcb_trace_resistance.py` lines 3776-3992) —
  the class this session extracts from. Its constructor harvests
  nets/tracks/arcs/vias/pads/zone_nets/pours and splits tracks at mid-run
  vias; `terminals()` (lines 3968-3992) already implements the
  `REF.PAD`-style dedupe/alias convention this session formalizes as
  `Terminal`/`pad()`.
- `_arc_length_mm`/`_q` (lines 3745-3751) — arc length is already
  extracted as `pathminer.core.geometry.arc_length` (Session 04); `_q`
  (coordinate quantisation, `Q=4`) was not previously extracted and is
  kept as a small module-private helper in the new `kicad/board.py`,
  matching the v0.13 constant exactly.
- `parse_pours`/`Pour` (lines 1458-1502) — filled-zone harvesting is
  extracted; `Pour`'s principal-axis/aspect-ratio/contains() methods are
  **not** carried over (see Decisions — that is network-builder/ARCH-004
  scope, Session 07).
- `pathminer/kicad/stackup.py` (Session 05) — reused via `load_stackup`/
  `manual_stackup` for the `BoardSource.stackup` property, including the
  spec-required (S8.2) estimated-fallback when no `(stackup)` block
  exists.
- Project specification S7.1 (`BoardSource` abstraction), S8.8 (path
  resolution rules), S9.4 (stable identifiers, `REF.PAD`), S12.3 (net
  drift) — these sections drove the protocol surface and the
  `PadNotFoundError`/`NetDriftError`/`PadDrift` design.

**Design split across the three owned modules** (recorded because the
owned-scope split is not self-evident from the prompt alone):

- `pathminer/models/board.py` — pure domain contracts: `Net`, `Track`,
  `Via`, `Pad`, `Terminal`, `TerminalAlias`, `Pour`, `PadDrift`, the
  `ref_pad_name()` naming rule, the named exceptions, and the
  `@runtime_checkable` `BoardSource` `Protocol` itself. This module
  imports `pathminer.kicad.stackup.Stackup` only (to type the
  `.stackup` property) — it parses nothing.
- `pathminer/kicad/board.py` — `parse_board()`: the mechanical,
  behavior-preserving extraction of `BoardNets`'s geometry-harvesting
  constructor logic (not its graph-building methods) into the
  `models.board` types, plus the stackup fallback.
- `pathminer/kicad/source.py` — `FileBoardSource`, the concrete
  `BoardSource` implementation: wraps `parse_board()`'s output, builds
  the board-wide `REF.PAD` index, and implements `pad()`, `terminals()`,
  `check_drift()`, and `resolve()`.

This keeps `kicad` → `models` as a one-directional import (no cycle: the
only thing `models/board.py` imports from `kicad` is the leaf module
`kicad.stackup`, which imports nothing from `kicad.board`/`kicad.source`).
`ARCH-002`'s automated import-boundary test does not forbid this
direction (it only forbids Qt/wx across `models`/`kicad`, and forbids
`core` from importing upward) — confirmed by running
`tests/test_import_boundaries.py` unchanged and green (48/48).

---

## Punch-list status

| ID | Role | Status | Evidence |
|---|---|---|---|
| ARCH-003 | Closure owner | **closed** | `pathminer/models/board.py` (protocol), `pathminer/kicad/board.py` (`parse_board`), `pathminer/kicad/source.py` (`FileBoardSource`) added. Done-when clause — "the same analysis accepts either adapter without branching" — demonstrated by `FileBoardSource` satisfying the `runtime_checkable` `BoardSource` `Protocol` (`isinstance(source, BoardSource)` asserted in tests) with no `LiveKiCadBoardSource`-specific branching anywhere above `kicad/`. A future live adapter need only satisfy the same protocol. `tests/test_board_source.py` (48 tests): protocol conformance, stable `REF.PAD` lookup (`pad()`), terminal alias collapsing, and named drift diagnostics (`check_drift`/`resolve`, `PadNotFoundError`, `NetDriftError`) against three committed synthetic fixtures plus the real IP5385 board. |
| DATA-004 | Contributes resolution slice | implemented | `FileBoardSource.check_drift()`/`resolve()` resolve a `REF.PAD` against the current board and compare the recorded net name, raising `PadNotFoundError` (broken identity) or `NetDriftError` (net renamed) as distinct, named failures — not the whole DATA-004 item (persistence/schema of paths is a later session's scope), but the resolution mechanism DATA-004's Done-when clause depends on. `test_rerouted_board_same_ref_pad_still_resolves_geometry` and the `TestDriftDiagnostics` class demonstrate "a rerouted board resolves the same paths or produces a named drift error" at the `BoardSource` layer. |

Per Session Execution Rule 8 and the session prompt: only ARCH-003's
exact Done-when clause is asserted closed here; DATA-004 remains open
overall and is not marked complete by this session.

---

## Files changed

### Added
- `pathminer/models/board.py` — domain dataclasses (`Net`, `Track`, `Via`,
  `Pad`, `Terminal`, `TerminalAlias`, `Pour`), `PadDrift`, exceptions
  (`BoardSourceError`, `PadNotFoundError`, `NetDriftError`),
  `ref_pad_name()`, and the `BoardSource` `Protocol`.
- `pathminer/kicad/board.py` — `parse_board(path) -> ParsedBoard`;
  private helpers `_q`, `_parse_pours`, `_split_tracks_at_vias`.
- `pathminer/kicad/source.py` — `FileBoardSource`; private helpers
  `_terminals_for_net`, `_build_pad_index`.
- `tests/test_board_source.py` — 48 tests (positive, boundary, failure,
  drift, real-board regression).
- `tests/fixtures/kicad/board_min.kicad_pcb` — synthetic 2-net,
  2-footprint board: a track split by a mid-run via, an arc, a filled
  zone, and one aliased `REF.PAD` (`U2.S`, two physical pads).
- `tests/fixtures/kicad/board_no_stackup.kicad_pcb` — `board_min` with
  the `(setup (stackup ...))` block removed, for the manual-stackup
  fallback path.
- `tests/fixtures/kicad/board_rerouted.kicad_pcb` — `board_min` with net
  1 renamed `"SIG_A"` → `"SIG_A_MOVED"`; `REF.PAD` identities unchanged,
  for net-drift tests.

### Modified
- None.

### Removed
- None.

`tools/pcb_trace_resistance.py` was not touched (out of owned scope; the
monolith and the new modules coexist, matching the Session 05 precedent).

---

## APIs and schemas changed

New public surface only; nothing existing was modified.

**`pathminer.models.board`**
- `Point` (type alias), `Net`, `Track`, `Via`, `Pad`, `TerminalAlias`,
  `Terminal`, `Pour`, `PadDrift` — frozen dataclasses.
- `ref_pad_name(ref, pad_name, pin_function) -> str`
- `BoardSourceError(Exception)`, `PadNotFoundError(BoardSourceError, KeyError)`,
  `NetDriftError(BoardSourceError)` (carries `.drift: PadDrift`)
- `BoardSource` — `@runtime_checkable` `typing.Protocol` with `.stackup`,
  `.nets()`, `.net_name(net)`, `.tracks(net=None)`, `.vias(net=None)`,
  `.pads(net=None)`, `.pours(net=None)`, `.terminals(net, dedupe=True)`,
  `.pad(ref_pad)`, `.check_drift(ref_pad, expected_net)`,
  `.resolve(ref_pad, expected_net=None)`.

**`pathminer.kicad.board`**
- `ParsedBoard` — internal aggregate (not part of the `BoardSource`
  surface); `path`, `net_names`, `tracks`, `vias`, `pads`, `pours`,
  `zone_nets`, `stackup`, `notes`.
- `parse_board(path: str) -> ParsedBoard`

**`pathminer.kicad.source`**
- `FileBoardSource(path: str)` — implements `BoardSource`; also exposes
  `.path` and `.notes` (parser diagnostics: mid-run via splits, stackup
  fallback) as an extra, non-protocol convenience for future
  diagnostics work (UI-014/AUTO-006), not a required interface member.

No JSON schema was added or changed (schema work is DATA-002/Session 10).

---

## Tests and results

### Pre-change baseline

```
Command: python3 -m pytest -ra
Exit code: 0
Result: 324 passed in 1.65s
```

### Session 06 focused tests

```
Command: python3 -m pytest -ra tests/test_board_source.py
Exit code: 0
Result: 48 passed in 0.42s
```

### Import boundary check

```
Command: python3 -m pytest -ra tests/test_import_boundaries.py
Exit code: 0
Result: 48 passed in 0.17s
```

### Full regression suite (post-change)

```
Command: python3 -m pytest -ra
Exit code: 0
Result: 372 passed in 1.93s (324 pre-existing + 48 new; 0 failed, 0 errors, 0 skipped)
```

### Real-board regression (IP5385, ad hoc + within test_board_source.py::TestRealBoardRegression)

```
Command: python3 -m pytest -ra tests/test_board_source.py::TestRealBoardRegression
Exit code: 0
Result: 6 passed (parses cleanly; 4-layer non-estimated stackup; C53.1 and
U9.S REF.PAD resolve correctly, U9.S collapsing 3 physical "S" pads into
one Terminal with 2 aliases; unknown REF.PAD raises PadNotFoundError;
pours present; net_name(3) == "GNDREF")
```

### git diff --check

```
Command: git diff --check
Exit code: 0
Result: clean (no whitespace errors)
```

No unavailable fixtures or dependencies. All commands executed and
results recorded directly; nothing here is an unrun/assumed result.

---

## Decisions

1. **Split the owned scope as models=contracts, kicad=implementation.**
   `pathminer/models/board.py` holds the pure protocol/dataclasses;
   `pathminer/kicad/{board,source}.py` hold the parser and the concrete
   adapter. See the Implementation note above for the full rationale and
   the import-direction check against `test_import_boundaries.py`.
2. **`Pour` carries only raw fill polygons.** v0.13's `Pour` also computed
   principal axis/length/width/aspect and had `contains()`/
   `any_layer_contains()`. Those are pour *analysis* for automatic
   model selection and mesh/ladder building (PWR-002, ARCH-004), not
   board *geometry storage* — deliberately left for Session 07, which
   will consume `Pour.fills` via `pathminer.core.geometry` directly (no
   duplicated formulas).
3. **Graph-building (`build_graph`, ladder/mesh) is out of scope.** Only
   the geometry-harvesting half of `BoardNets` was extracted, per the
   session's "smallest coherent implementation" instruction and the
   explicit ARCH-004/Session 07 boundary in the refactor plan (S6 Sprint
   3 vs. Sprint 4).
4. **`pad()` indexes the whole board, not one net.** `REF.PAD` names are
   assumed unique per component regardless of which net a lookup call
   happens to be reasoning about, so `FileBoardSource` builds one
   board-wide index at construction; `terminals(net)` still recomputes
   per-net (matching v0.13 exactly, including the `dedupe=False` raw-row
   behavior).
5. **`resolve()`/`check_drift()` raise `PadNotFoundError` for a missing
   pad, not a drift result.** A pad that does not exist at all is a
   broken identity (matches the spec's own framing in S12.3: "resolve
   every REF.PAD... and compare recorded net names" presumes resolution
   succeeds); only a *resolved* pad whose net name changed is drift.
6. **Estimated-stackup fallback added to `parse_board`.** S8.2: "If
   stackup is absent, an estimated even-dielectric distribution may be
   created and clearly flagged." `parse_board` catches `load_stackup`'s
   `ValueError` and falls back to `manual_stackup()` (4 copper layers,
   the existing default), recording a note. This is additive behavior
   needed for `BoardSource.stackup` to always be usable; it does not
   change `pathminer.kicad.stackup` itself.
7. **Class-scoped pytest fixtures use `@classmethod`**, matching the
   Session 05 convention (avoids the pytest 10 deprecation warning).
8. **Fixture files are committed** under `tests/fixtures/kicad/` (unlike
   Session 05's tmp_path-only synthetic content), because this session's
   owned scope explicitly lists that directory.

---

## Assumptions

1. `pathminer/models/__init__.py`'s docstring ("models: imports core and
   kicad... converts board geometry into a ResistorNetwork") describes
   the *future* builder modules (`p2p.py`/`ladder.py`/`mesh.py`,
   Session 07), not `board.py`; it was not updated (not in owned scope)
   and is not contradicted by `models/board.py` importing only
   `kicad.stackup`.
2. `pathminer/kicad/__init__.py`'s docstring ("kicad: imports core...
   Provides the BoardSource protocol and FileBoardSource implementation")
   is read as describing the *package's* responsibility, satisfied by
   `kicad/board.py` + `kicad/source.py` together; the protocol's
   canonical definition lives in `models/board.py` per the design-split
   rationale above. Not modified (not in owned scope).
3. Pads sharing one `REF.PAD` name are assumed to share one net (used to
   justify a single board-wide `pad()` index rather than a per-net one).
   Confirmed true on both the synthetic fixtures and the IP5385 reference
   board's `U9.S` (3 pads, all net 94).
4. No `.kicad_pcb` arc fixture existed in the IP5385 reference board to
   copy verbatim (checked: the board has no `(arc ...)` blocks), so the
   arc block in `board_min.kicad_pcb` was hand-constructed following the
   parser's expected `(start)`/`(mid)`/`(end)`/`(width)`/`(layer)`/`(net)`
   shape; verified it parses and produces a true arc length greater than
   the chord.

---

## Deviations

None from v0.13 numerical behavior. `parse_board`'s estimated-stackup
fallback is new *coverage* (a board that has no `(stackup)` block
previously had no path through this session's `BoardSource` layer at
all — v0.13's `load_stackup`/`SetupTab` handled that case at the
GUI/report layer, not inside `BoardNets`), not a change to any existing
formula, unit, tolerance, or default. `manual_stackup()`'s own behavior
(including its Session 05 `ValueError` deviation for `n_copper < 1`) is
unchanged and untouched by this session.

---

## Known issues

None. All 372 tests pass. No forbidden imports introduced (48/48 import-
boundary tests pass). `git diff --check` clean.

---

## Dependent-session impact

- **Session 07 (Common network, builders and model-selection policy,
  ARCH-004):** should import `pathminer.kicad.source.FileBoardSource` and
  consume it purely through the `pathminer.models.board.BoardSource`
  protocol (nets/tracks/vias/pads/pours/stackup) to build `Node`/`Edge`/
  `ResistorNetwork`. Via electrical-span resolution (which layers actually
  land on a via) and pour ladder/mesh geometry (principal axis, rasterize)
  are both still open work for that session — `Via.declared_layers` and
  `Pour.fills` are the raw inputs it will need.
- **Session 08 (compatibility integration):** `tools/pcb_trace_resistance.py`
  is unchanged; the monolith and the new `BoardSource` stack coexist until
  that session's compatibility facade work.
- **Session 09+ (domain contracts) / a future plugin session (AUTO-004):**
  a `LiveKiCadBoardSource` implementing the same `pathminer.models.board.BoardSource`
  protocol can be added as a sibling to `FileBoardSource` in
  `pathminer.kicad.source` (or a new module) without any change to
  analysis code above `kicad/`, per the protocol design here.
- **DATA-004 (full closure, later session):** the resolution mechanism
  (`resolve`/`check_drift`) exists; persisting/loading `REF.PAD`-keyed
  paths and the GUI/CLI drift-handling policy (Abort/Continue
  Once/Update File; `--accept-net-changes`) from S12.3 are not built here
  and remain that session's scope.

---

## Recommended next action

Coordinator: this session is **READY_FOR_REVIEW**. Verify the diff and
handoff, then integrate and open Session 07 (Common network, builders and
model-selection policy), which depends on Session 03, Session 04, and
this session.
