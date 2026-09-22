<!-- v0.5 -->
# PathMiner — change log

## Versioning rules

- Every source file carries a version tag as its **literal first line** in the file's comment
  syntax (`# v0.3` for Python, `<!-- v0.3 -->` for Markdown). Python files with a shebang carry
  the tag on line 2.
- Format `Major.Minor[.Patch]`, starting at **v0.1** for a new file.
- **Any change to a file increments its Minor by one** — no exceptions.
- **Major** increments only when the project owner declares one; a Major bump resets Minor to 0.
- Files version **independently**. Versions are not synchronised across files.
- Every change session gets an entry here, written in the same pass as the change.
- Docs are tagged in this project because they are contracts, not commentary.

---

## 2026-08-24 — Baseline: project structure created, standalone script promoted to project

| File | Version | Change |
|---|---|---|
| tools/pcb_trace_resistance.py | v0.13 | Existing tool, unchanged. Placed in the tree |
| documents/via_tab_design_contract.md | v0.12 | Existing design contract, unchanged |
| documents/library_refactor_recommendations.md | v0.2 | Existing architecture review, unchanged |
| documents/path_capture_design.md | v0.6 | Existing path-capture design, unchanged |
| schema/pcb_net_selection.schema.json | — | Emitted by the tool; regenerate with `--emit-schema` |
| documents/change_log.md | v0.1 | New. Seeded with rules and this baseline |
| README.md | v0.1 | New. Tree listing, status, how to run |

**Why:** the work has outgrown standalone-script mode. It is now a 5546-line application with
three design documents, a JSON schema, a CLI, and a GUI, and it is about to be split into a
library plus a KiCad plugin. Standalone delivery (single file, no tree) no longer fits, so the
canonical desktop-GUI structure has been materialised and everything placed inside it.

**Mode change recorded:** standalone script → **project**. Future deliveries are a zip of the
full tree, per project conventions §4.

**No code was changed in this pass.** `tools/pcb_trace_resistance.py` is byte-identical to the
v0.13 file already delivered; its version tag is therefore *not* bumped, because nothing in it
was touched. Verification: `--selftest` still reports 254/254 on the reference board, 284/284
on the real power-bank board, 118/118 headless.

**Naming:** the project is now **PathMiner** (decision D9 in `path_capture_design.md`).
Whether `pcb_trace_resistance.py` itself takes the name is open — see Q12 in that document —
so the file keeps its current name for now and lives under `tools/` rather than as the package
entry point.

**Structure deviation from the template:** `ai_reference/examples/` was added for sample JSON
inputs, alongside the template's `code_samples/` and `doc_samples/`. `core/`, `ui/*`, `tests/`
and `schema/` are scaffolded but empty pending the split described in
`documents/library_refactor_recommendations.md`; `.gitkeep` files hold them.

---

## 2026-09-03 — Cross-platform baseline-comparator correction

| File | Version | Change |
|---|---|---|
| tests/baseline/regression_compare.py | v0.2 | Verify input hashes and compare nested segment floats using the existing report tolerance while preserving exact structure |
| tests/baseline/golden_fixtures_notes.md | v0.2 | Document input-hash verification and nested floating-point comparison |
| tests/baseline/README.md | v0.2 | Document the corrected cross-platform report comparison |
| documents/change_log.md | v0.2 | Record the coordinator hotfix |

**Why:** report segment dictionaries were compared with raw Python equality even though their
calculated floating-point leaves can vary in the final few bits with summation order or platform
math behavior. Top-level report values already used a `1e-6` relative tolerance. The comparator
now applies that same tolerance recursively to segment floats while continuing to compare segment
order, keys, layer names, kinds, flags, and integer counts exactly. It also verifies the live board
and net-selection SHA-256 values before accepting a report, so a wrong or changed input cannot be
hidden by the numerical tolerance. The golden fixtures themselves were not changed.

---

## 2026-09-11 — Session 08: compatibility integration and single-file build

| File | Version | Change |
|---|---|---|
| tools/pcb_trace_resistance.py | v0.14 | Legacy compatibility facade: solver dispatcher and pure-geometry helpers now alias `pathminer.core.solver` / `pathminer.core.geometry` instead of duplicating them |
| tools/build_single_file.py | v0.1 | New. Generates a self-contained single-file distribution by inlining `pathminer.core.geometry`/`solver` into the facade |
| pathminer/__init__.py | v0.2 | Docstring: record the Session 08 facade wiring |
| pathminer/core/__init__.py | v0.2 | Docstring: record that `geometry.py`/`solver.py` are now also consumed by the legacy facade |
| tests/test_compatibility.py | v0.1 | New. Facade-wiring, dispatcher-agreement, aggregate/module vector-identity, and generated-file-parity tests |
| documents/change_log.md | v0.3 | This entry |

**Why:** closes the session's three owned punch items —

- **BASE-004** ("preserve a generated single-file distribution... the generated file passes the
  same aggregate self-test as the package"): `tools/build_single_file.py` inlines
  `pathminer/core/geometry.py` and `pathminer/core/solver.py` (found by sentinel comments around
  the facade's `pathminer.core` bootstrap) into a self-contained script with no import-time
  dependency on the `pathminer` package. `--check` regenerates it and diffs its `--selftest`
  vector-by-vector against the split facade's; both report 118/118 headless and 284/284 on the
  real IP5385 board, byte-for-byte the same pass/fail per named vector.
- **ARCH-006** ("consolidate solvers behind one dispatcher... backend agreement is asserted on the
  same networks"): the facade's `_solve_dense`, `solve_cg`, `_solve_scipy`, `DENSE_NODE_LIMIT`,
  `HAVE_SCIPY`, `calibrate_solver`, and `estimate_seconds` are now the same objects as
  `pathminer.core.solver`'s (asserted with `is` in `tests/test_compatibility.py`), and
  `network_resistance` — the legacy dispatcher every call site in this file already used — now
  builds an edge list and delegates the actual solve to
  `pathminer.core.solver.two_terminal_resistance`, forcing the same dense/sparse crossover this
  function always used so its numerics are unchanged.
- **ARCH-010** ("split the self-test by module while retaining stable vector IDs... module tests
  and the aggregate `--selftest` report the same acceptance-vector identities"): Session 04 already
  retained the V11/V13/V14/V20 identities in `tests/test_solver.py` / `tests/test_geometry.py`;
  `tests/test_compatibility.py` now asserts the aggregate `--selftest` reports those same
  identities, all passing, alongside the pathminer.core solver/geometry objects the aggregate run
  actually now calls.

**Numerical behavior preserved exactly.** No formula, tolerance, or default changed. Verification:
`python3 -m pytest -q` — 467 passed (458 baseline + 9 new); `python3 tools/pcb_trace_resistance.py
--selftest` — 118/118; `python3 tests/baseline/regression_compare.py all` — all three canonical
suites (118 headless + 284 real-board selftest vectors, 11-pair IP5385 batch report) match the
frozen golden fixtures exactly, unchanged from the pre-session baseline; `python3
tools/build_single_file.py --check` — PASS (also re-run with `--board` against the real IP5385
board: 284/284 on both sides).

**Deliberately narrowed scope, flagged for coordinator confirmation** (see the corrected handoff):
`pathminer.core.materials`/`units`/`resistance` (PWR-001) and the KiCad/board/network duplication in
this file (`BoardNets`, `build_graph_pour`, `mesh_pour_edges`, `Pour`, GUI classes) were left
untouched. This was decided unilaterally against the punch-list responsibility line ("Contributes
to or extends: None"), read as outranking the session Objective's broader "integrate extracted
modules" wording; a coordinator-review finding correctly noted that priority is not itself stated
in the prompt and asked that the remaining integration be explicitly tracked/assigned rather than
silently left. Recorded here as an open question for the coordinator, not a settled fact.

---

## 2026-09-11 — Session 08 coordinator-review repair

| File | Version | Change |
|---|---|---|
| tools/build_single_file.py | v0.2 | Fix: `--check` could report a false PASS when both the split facade's and the generated file's `--selftest` failed identically (e.g. both "0/1 checks passed", exit 1), or raise `TypeError` on an unparseable summary. Each side is now validated as actually passing (exit 0, parseable summary, `passed == total`, every vector `PASS`) before the two runs are compared against each other. |
| tests/test_compatibility.py | v0.2 | Strengthened ARCH-010 evidence from a shared-prefix check to an exact-identity check (V11 imported from `tests/test_solver.py`'s own `V11_CASES`; V13/V14 hand-transcribed and explicitly documented as such) that would catch a renamed or removed vector. Added three regression tests for the `build_single_file.check()` fix (both-sides-fail, unparseable-summary, one-side-only-fails). |
| documents/change_log.md | v0.4 | This entry |

**Why:** a coordinator/reviewer pass on the Session 08 diff and handoff found four issues, addressed
as follows —

1. **Generated-file check could falsely pass.** Reproduced exactly as reported (both simulated
   selftests at "0/1 checks passed", exit 1, `--check` still printed PASS and returned 0). Fixed in
   `tools/build_single_file.py`'s `check()`: each side's own `--selftest` run is now validated in
   full (exit code, a parseable summary, `passed == total`, no FAIL vector) before any comparison
   between the two runs happens, and a missing/unparseable summary now fails cleanly instead of
   raising `TypeError`. Three new regression tests pin this in `tests/test_compatibility.py`.
2. **Incorrect handoff base commit.** `.ai/handoffs/Session_08_Claude.md`/`.json` named the
   `SESSION_STATUS.csv`-recorded prerequisite commit (`6c5f4f6`) as the session's base commit, but
   the implementation commit's actual git parent — and the correct "record `git rev-parse HEAD`
   before editing" value per the session prompt's Preconditions — is `90482b5` (that same commit
   plus the coordinator's own metadata-only "integrate Session 07 / assign Session 08" ledger edit).
   Both handoff files corrected; no history was rewritten, and no owned-scope file differs between
   the two commits.
3. **ARCH-010 closure evidence was too weak.** The original test only checked that *some* passing
   vector names started with `V11`/`V13`/`V14`, which would miss a renamed or silently dropped
   individual vector. `tests/test_compatibility.py` now compares the aggregate selftest's V11/V13/V14
   names against the module tests' own identities as an exact set (V11 read directly from
   `tests/test_solver.py`'s `V11_CASES`; V13/V14 transcribed by hand from that file's and
   `tests/test_geometry.py`'s inline comments, since neither keeps those identities in an importable
   structure — documented at the point of transcription). V20 remains explicitly excluded and
   explained (no fixture board in this repository supplies the `/SDA` net its check requires; see
   `tests/baseline/README.md`, predating this session). ARCH-010 remains presented as **closed** on
   this strengthened evidence.
4. **Integration-scope narrowing needs coordinator confirmation.** The original handoff presented
   "wire only ARCH-006/ARCH-010's solver+geometry slice, not PWR-001 or KiCad/board/network" as a
   settled decision. That reading (the punch-list responsibility line overriding the Objective's
   broader wording) is reasonable but is *not itself stated as a priority rule* in the prompt, so it
   is now recorded as a flagged, unresolved scope question rather than a foregone conclusion — see
   both handoff files' updated Decisions/Recommended-next-action sections, which ask the coordinator
   to either confirm this scoping or assign the remaining integration (PWR-001; KiCad/board/network)
   explicitly.

**Re-verification after the fix.** `python3 -m pytest -q` — **470 passed** (458 baseline + 12 in
`tests/test_compatibility.py`, up from 9); `python3 tools/pcb_trace_resistance.py --selftest` —
118/118; `QT_QPA_PLATFORM=offscreen python3 tests/baseline/regression_compare.py all` — all three
canonical suites still PASS, unchanged; `python3 tools/build_single_file.py --check` (headless and
`--board` against the real IP5385 board) — PASS, 118/118 and 284/284 on both sides, using the
*corrected* (no-longer-falsifiable) check logic.

---

## 2026-09-22 — Session 08 second coordinator-review repair and scope disposition

| File | Version | Change |
|---|---|---|
| tools/build_single_file.py | v0.3 | Fix: `check()` could still report a false PASS on internally inconsistent output — both sides exiting 0 and printing a summary claiming "N/N checks passed" while their actually-printed vector lines didn't add up to that (e.g. one printed `[PASS]` line, then "118/118 checks passed") — because the first repair validated exit code, summary presence, `passed == total`, and no-FAIL, but never cross-checked the parsed vector count/PASS count against the summary itself. Fixed: each side's parsed vector count must now equal the summary's total, and its parsed PASS count must equal the summary's reported passed count. |
| tests/test_compatibility.py | v0.3 | ARCH-010 evidence changed from a hand-typed parallel list to genuine derivation: `_derive_vector_names()` reads `tests/test_geometry.py` / `tests/test_solver.py`'s actual source via `ast` at test time, so a rename/removal in either module test file is caught by construction. One new regression test added for the `build_single_file.py` fix above. |
| documents/change_log.md | v0.5 | This entry |

**Why — two further coordinator-review findings, addressed:**

1. **`--check` could still be fooled by internally inconsistent output.** The first repair (see the
   entry above) closed the both-sides-fail-identically false PASS, but a reviewer found a second
   path to the same false PASS: output that exits 0 and *claims* a full pass in its summary line
   without the printed vectors actually supporting that claim. `_validate_own_selftest()` now checks
   `len(vectors) == total` and `count(PASS) == passed` in addition to the existing exit-code,
   summary-presence, and FAIL-vector checks (all preserved unchanged). New regression test
   `test_check_rejects_a_summary_that_does_not_match_the_vector_count` reproduces the reviewer's
   exact scenario (both subprocesses exit 0, one `[PASS]` vector, "118/118 checks passed") and
   asserts `check()` rejects it.
2. **ARCH-010's V13/V14 evidence was still not "genuine module-side identity coverage."** A
   hand-typed list that happens to match today's aggregate selftest output does not demonstrate
   that it tracks the module test files — a typo or later drift in either place would go
   undetected. `tests/test_compatibility.py` now parses `tests/test_geometry.py` /
   `tests/test_solver.py`'s real source (inline `# V13 ...` comments where present; a mechanical
   function-name transform where a test has none) at test time. This surfaced one genuine, narrow,
   pre-existing discrepancy: `tests/test_geometry.py`'s inline comments say "V13 clip outside"/"V13
   clip inside" (missing "length"), while the aggregate's stable `chk()` names carry "V13 clip
   outside length"/"V13 clip inside length" — both sides assert the identical value at the
   identical tolerance through the identical aliased helper, so this is a comment-wording gap in a
   file outside this session's owned write scope, not a numerical one. Mapped explicitly and
   narrowly (verified present in the derived set, so the mapping cannot go silently stale); any
   other mismatch still fails the test. ARCH-010 remains **closed**, now on genuine, disclosed
   evidence rather than an unverifiable hand-typed list.

**Coordinator scope disposition (received, recorded verbatim in substance).** The coordinator has
dispositioned the scope question this session raised in its first repair pass:

> Solver/geometry integration is accepted as a bounded contribution. Wider electrical-core and
> KiCad/board/network/builder integration remains incomplete and requires coordinator assignment
> before M1 completion. Do not expand scope or claim that "Contributes: None" overrides the
> session objective.

This session's own prior framing — that the punch-list responsibility line ("Contributes to or
extends: None") controls or outranks the session Objective's broader "integrate extracted modules
into the legacy entry point" wording — is **not** the basis on which this work is accepted; both
handoffs are corrected to state plainly that solver/geometry integration is a bounded, accepted
contribution, and that `pathminer.core.materials`/`units`/`resistance` (PWR-001) wiring and a
KiCad/board/network/builder integration remain **incomplete work that blocks M1 completion**,
requiring explicit coordinator assignment — not an implicit assumption resolved by this session's
own scope reading. No additional integration was attempted in this pass in response to this
disposition (that would itself be an unassigned scope expansion); the disposition is recorded here
and in both handoffs as direction for the coordinator's own tracking and for whichever session is
assigned the remaining work.

**Re-verification after both fixes.** `python3 -m pytest -q` — **471 passed** (458 baseline + 13 in
`tests/test_compatibility.py`, up from 12); `python3 tools/pcb_trace_resistance.py --selftest` —
118/118 (unchanged); `QT_QPA_PLATFORM=offscreen python3 tests/baseline/regression_compare.py all` —
all three canonical suites still PASS, unchanged; `python3 tools/build_single_file.py --check`
(headless and `--board` against the real IP5385 board) — PASS, 118/118 and 284/284 on both sides,
using the further-corrected `check()` logic. No tolerance changed.
