<!-- v0.2 -->
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
