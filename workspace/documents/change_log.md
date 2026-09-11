<!-- v0.3 -->
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

**Deliberately out of scope** (not this session's punch items; see `.ai/handoffs/Session_08_Claude.md`
decisions): `pathminer.core.materials`/`units`/`resistance` (PWR-001, left open by Session 03 pending
the modules this session's prerequisites do not include for that item), and the KiCad/board/network
duplication in this file (`BoardNets`, `build_graph_pour`, `mesh_pour_edges`, `Pour`, GUI classes),
which is not this session's assigned scope and was left untouched.
