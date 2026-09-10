# Session 06 Handoff — BoardSource and file-backed board model

- **Session:** 06
- **AI:** Claude
- **Model:** claude-sonnet-5
- **Effort:** high
- **Status:** READY_FOR_REVIEW
- **Branch:** ai/session-06-claude-board-source
- **Base commit:** 451668d81382265bc0f68a2250359987a964b1a9
- **Final commit:** 883fce5e8c71e4e075c8b2859384f9ff7c331476

---

## Review corrections applied (this revision)

A review of the first submission (base commit incorrectly recorded as
`d7f8364`, final commit `442947a`) found three issues. All three are
addressed in this revision:

1. **Ambiguous cross-net pad identities silently combined.** Fixed in
   commit `883fce5` — see the new "Cross-net ambiguous-pad fix" note
   under Implementation, the updated Decisions, and Known issues (a
   genuine instance of this was found in the IP5385 reference board
   itself, `LED1.1`).
2. **ARCH-003 was marked closed without the required evidence.**
   Downgraded to `implemented`/open below; see Punch-list status for
   what specifically remains before closure is justified.
3. **Base commit was recorded incorrectly** (`d7f8364`, the state
   *before* the coordinator's `451668d` ledger commit, instead of
   `451668d` itself, the actual pre-implementation commit). Corrected in
   the header above and throughout this document; this also removes the
   coordinator's `SESSION_STATUS.csv` ledger-transition commit from this
   session's reviewable diff (`git diff 451668d..883fce5` now shows only
   this session's own commits).

A fourth point was raised as an observation rather than a required
correction: the reviewer's environment lacks `pytest` and `PySide6`, so
the test results below could not be independently rerun there, and the
real-board tests in this suite are not the canonical v0.13 118/284
selftest regression. See "Verification environment and scope" under
Tests and results for a direct response.

---

## Preflight (recorded before coding, corrected above)

- Active model: Claude Sonnet 5 (`claude-sonnet-5`).
- Branch: `ai/session-06-claude-board-source` (already checked out in this worktree).
- Base commit: `451668d81382265bc0f68a2250359987a964b1a9`
  (`chore: integrate Session 05 and assign Session 06` — the coordinator's
  assignment commit; this is the actual commit implementation started
  from and the correct value for this field. The original submission of
  this handoff incorrectly recorded `d7f836456098ea9bb1119dadd35cbacb69aaadff`,
  the commit *before* that assignment commit, which pulled an unrelated
  ledger-only commit into this session's reviewable diff. `git show --stat
  451668d` confirms its only content is `.ai/coordination/SESSION_STATUS.csv`.)
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

**Cross-net ambiguous-pad fix (added in this revision).** The original
`_build_pad_index` grouped pads by net, then merged same-`REF.PAD`-name
terminals into one board-wide index across *all* net groups — but it
merged unconditionally, so two pads sharing a name on *different* nets
were combined into one `Terminal` reporting only the first net seen; the
second pad's real net was silently lost. `_terminals_for_net` already
performs the correct same-net collapse independently per net, so a name
recurring across different net groups at the index-build stage is, by
construction, always a genuine cross-net collision, never a legitimate
same-net duplicate. Fixed by tracking which net first claimed each name
and raising `AmbiguousPadError` — but only when that specific name is
looked up via `pad()`/`check_drift()`/`resolve()`, not at construction:
excluding the ambiguous name from the index and continuing to build it
for everything else means one bad component does not brick lookup of
every other terminal on the board. This distinction mattered in practice
— see the real-board finding below.

---

## Punch-list status

| ID | Role | Status | Evidence |
|---|---|---|---|
| ARCH-003 | Closure owner | **implemented** (not closed — see "What remains" below) | `pathminer/models/board.py` (protocol), `pathminer/kicad/board.py` (`parse_board`), `pathminer/kicad/source.py` (`FileBoardSource`) added and demonstrated against a real board and five synthetic fixtures. `tests/test_board_source.py` (56 tests): protocol conformance, stable `REF.PAD` lookup (`pad()`), terminal alias collapsing, cross-net ambiguous-identity rejection, and named drift diagnostics (`check_drift`/`resolve`, `PadNotFoundError`, `NetDriftError`). |
| DATA-004 | Contributes resolution slice | implemented | `FileBoardSource.check_drift()`/`resolve()` resolve a `REF.PAD` against the current board and compare the recorded net name, raising `PadNotFoundError` (broken identity) or `NetDriftError` (net renamed) as distinct, named failures — not the whole DATA-004 item (persistence/schema of paths is a later session's scope), but the resolution mechanism DATA-004's Done-when clause depends on. `test_rerouted_board_same_ref_pad_still_resolves_geometry` and the `TestDriftDiagnostics` class demonstrate "a rerouted board resolves the same paths or produces a named drift error" at the `BoardSource` layer. |

**ARCH-003 — what remains before closure.** The exact Done-when clause
is "the same analysis accepts either adapter without branching." This
session built and tested one adapter (`FileBoardSource`) against the
`BoardSource` protocol; `isinstance(source, BoardSource)` demonstrates
that `FileBoardSource` *satisfies* the protocol's shape, but that is not
the same claim as "the same analysis code accepts either adapter without
branching" — that requires a *second* protocol-conforming adapter and a
piece of analysis code exercised against both, showing neither needs an
adapter-specific branch. No second adapter exists yet, and building the
live `pcbnew`-backed one is explicitly out of this session's scope. The
minimal remaining step to actually close ARCH-003 is smaller than a full
live adapter, though: a lightweight second `BoardSource`-conforming test
double (even an in-memory/synthetic one, not `pcbnew`-backed) run through
one shared piece of consuming code would be sufficient evidence. That
step, or the real `LiveKiCadBoardSource` (AUTO-004), is left to whichever
session next needs to prove non-branching — most naturally Session 07
(the first real consumer of `BoardSource`) or the plugin session.

Per Session Execution Rule 8 and the session prompt: no punch item is
closed without evidence for its exact Done-when clause. ARCH-003 is
therefore left as `implemented`, not `closed`; DATA-004 remains open
overall and is not marked complete by this session.

---

## Files changed

### Added
- `pathminer/models/board.py` — domain dataclasses (`Net`, `Track`, `Via`,
  `Pad`, `Terminal`, `TerminalAlias`, `Pour`), `PadDrift`, exceptions
  (`BoardSourceError`, `PadNotFoundError`, `AmbiguousPadError`,
  `NetDriftError`), `ref_pad_name()`, and the `BoardSource` `Protocol`.
- `pathminer/kicad/board.py` — `parse_board(path) -> ParsedBoard`;
  private helpers `_q`, `_parse_pours`, `_split_tracks_at_vias`.
- `pathminer/kicad/source.py` — `FileBoardSource`; private helpers
  `_terminals_for_net`, `_build_pad_index`.
- `tests/test_board_source.py` — 56 tests (positive, boundary, failure,
  cross-net ambiguous-identity rejection, drift, real-board regression).
- `tests/fixtures/kicad/board_min.kicad_pcb` — synthetic 2-net,
  2-footprint board: a track split by a mid-run via, an arc, a filled
  zone, and one aliased `REF.PAD` (`U2.S`, two physical pads).
- `tests/fixtures/kicad/board_no_stackup.kicad_pcb` — `board_min` with
  the `(setup (stackup ...))` block removed, for the manual-stackup
  fallback path.
- `tests/fixtures/kicad/board_rerouted.kicad_pcb` — `board_min` with net
  1 renamed `"SIG_A"` → `"SIG_A_MOVED"`; `REF.PAD` identities unchanged,
  for net-drift tests.
- `tests/fixtures/kicad/board_ambiguous_pad.kicad_pcb` — one footprint
  `J1` whose two pads share the `REF.PAD` name `J1.SIG` but sit on two
  different nets, reproducing the cross-net collision bug directly.

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
  `AmbiguousPadError(BoardSourceError)` (carries `.ref_pad: str` and
  `.nets: tuple[int, ...]`), `NetDriftError(BoardSourceError)` (carries
  `.drift: PadDrift`)
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
Result: 56 passed in 0.45s
```

### Import boundary check

```
Command: python3 -m pytest -ra tests/test_import_boundaries.py
Exit code: 0
Result: 48 passed in 0.32s
```

### Full regression suite (post-change)

```
Command: python3 -m pytest -ra
Exit code: 0
Result: 380 passed in 4.55s (324 pre-existing + 56 new; 0 failed, 0 errors, 0 skipped)
```

### Real-board regression (IP5385, within test_board_source.py::TestRealBoardRegression)

```
Command: python3 -m pytest -ra tests/test_board_source.py::TestRealBoardRegression
Exit code: 0
Result: 8 passed — parses cleanly; 4-layer non-estimated stackup; C53.1 and
U9.S REF.PAD resolve correctly, U9.S collapsing 3 physical "S" pads into
one Terminal with 2 aliases; unknown REF.PAD raises PadNotFoundError;
pours present; net_name(3) == "GNDREF"; LED1.1 (a genuine cross-net
collision already present on this board) raises AmbiguousPadError
reporting all 5 conflicting nets; U9.S/C53.1 still resolve normally
alongside that unrelated ambiguity.
```

### Cross-net ambiguous-pad regression

```
Command: python3 -m pytest -ra tests/test_board_source.py::TestAmbiguousPadIdentity
Exit code: 0
Result: 6 passed — board_ambiguous_pad.kicad_pcb (J1.SIG on nets 1 and 2)
constructs without error; pad("J1.SIG") raises AmbiguousPadError
reporting both nets (1, 2); check_drift/resolve on the same name raise
the same named error rather than a misleading drift or a silently wrong
net.
```

### git diff --check

```
Command: git diff --check
Exit code: 0
Result: clean (no whitespace errors)
```

No unavailable fixtures or dependencies in this session's own execution
environment. All commands above were executed and their results
recorded directly; nothing here is an unrun or assumed result. See
"Verification environment and scope" immediately below for what these
results do and do not cover for a reviewer with a different environment.

### Verification environment and scope

A reviewer reported being unable to independently rerun the above in
their own environment (no `pytest`, no `PySide6`) and noted that the
real-board tests here are not the canonical v0.13 regression. Both
points are accurate and are addressed directly, without changing what
was actually run:

- **Reproducing this session's results needs only `pytest`, not
  `PySide6`.** Confirmed by inspection: no file under `pathminer/` or
  `tests/` imports `PySide6` or `pcbnew` for real (the only occurrences
  are string literals inside `tests/test_import_boundaries.py`'s
  forbidden-name lists/self-checks, and inside synthetic `.kicad_pcb`
  generator-field text). `python3 -m pytest -ra` in a plain `pip install
  pytest` environment should reproduce the 380-passed result reported
  here exactly. This session's own execution environment happens to also
  have `PySide6` installed (used by no test in this run), so that was
  not separately verified in a `PySide6`-free environment; the import
  scan above is the evidence, not a second live run.
- **`PySide6` is required only for the legacy monolith**
  (`tools/pcb_trace_resistance.py`), which imports it unconditionally at
  module level even for its own `--selftest`. That file was not touched
  by this session and this session's required verification commands
  (the session prompt's `python3 -m pytest -q tests/test_board_source.py`
  and `python3 -m pytest -q`) never import it.
- **The 8 `TestRealBoardRegression` tests are not the canonical v0.13
  regression** (BASE-001: 118/118 headless + 284/284 IP5385 real-board
  checks via the monolith's own `--selftest`/batch-report path). They
  are a narrower, `BoardSource`-scoped parity check: does `FileBoardSource`
  read the IP5385 board's stackup, a handful of known `REF.PAD` facts,
  and its pours correctly, and does it correctly flag the one genuine
  data ambiguity (`LED1.1`) the board contains? That canonical regression
  was not in this session's required verification list, was not run by
  this session, and is not superseded or replaced by anything here — it
  remains BASE-001/QA-004's evidence, not ARCH-003's.

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
9. **Cross-net `REF.PAD` collisions are excluded from the index, not
   raised at construction (added in this revision).** A name can only
   recur across the per-net grouping in `_build_pad_index` when it is a
   genuine cross-net collision (same-net duplicates are already
   collapsed by `_terminals_for_net` before that point), so every
   recurrence is unconditionally wrong to merge. Raising immediately at
   `FileBoardSource.__init__` was considered and rejected: the IP5385
   reference board's own `LED1` footprint has exactly this collision
   (five pads, five different nets, one shared generic pin function
   `"1"`), and a single such component should not make every other
   terminal on an otherwise-valid 200-footprint board unreachable.
   `AmbiguousPadError` is therefore raised lazily, only when that
   specific `REF.PAD` name is looked up.

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

- **The IP5385 reference board contains a genuine `REF.PAD` ambiguity:**
  `LED1`'s five pads all share pin function `"1"` while sitting on five
  different nets (76, 77, 78, 79, 113), so `LED1.1` cannot be resolved as
  a single terminal. This is a characteristic of that board's own data
  (a generic/repeated pin-function label on a multi-pad component), not
  a defect in this session's code — it is exactly the case
  `AmbiguousPadError` exists to report rather than silently mis-resolve.
  Because `ref_pad_name()` always prefers a truthy pin function over the
  bare pad name (matching v0.13), `LED1`'s five pads are not
  individually addressable via `pad("LED1.<n>")` at all — pin function
  `"1"` wins for every one of them regardless of pad name. A future
  session that needs to address one of `LED1`'s pads individually will
  need `pads(net=...)` / `terminals(net, dedupe=False)` (both already
  net-scoped and unaffected by this ambiguity) rather than the
  whole-board `pad()` lookup.
- Otherwise none. All 380 tests pass. No forbidden imports introduced
  (48/48 import-boundary tests pass). `git diff --check` clean.

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
handoff. ARCH-003 is `implemented`, not `closed` — see "What remains"
under Punch-list status; closing it needs either a second
`BoardSource`-conforming implementation (a lightweight test double
suffices) exercised against shared analysis code, or an explicit decision
to defer that closure evidence to Session 07 (first real `BoardSource`
consumer) or the plugin session (AUTO-004, the real live adapter). Once
resolved one way or the other, integrate and open Session 07 (Common
network, builders and model-selection policy), which depends on
Session 03, Session 04, and this session.
