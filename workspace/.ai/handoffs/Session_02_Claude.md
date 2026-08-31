<!-- v0.1 -->
# Session 02 — Package and CI skeleton [READY_FOR_REVIEW]

**Status:** READY_FOR_REVIEW  
**AI:** Claude  
**Model:** claude-sonnet-4-6 (matches assignment)  
**Effort level:** high  
**Date:** 2026-08-31  
**Branch:** ai/session-02-claude-package-skeleton  
**Base commit:** a8c49c95249d7c9d6f295b480deae801587af369  
**Final commit:** 96b4a50eab1c2c65dd3ca39242f121457e7f9779  

---

## Executive Summary

Session 02 creates the installable `pathminer` package shell and the ARCH-002
automated dependency-direction guard without moving any production behaviour.
The v0.13 tool (`tools/pcb_trace_resistance.py`) is unchanged byte-for-byte.

**Punch-list contribution:**

| ID | Role | Status |
|---|---|---|
| ARCH-001 | package-skeleton slice (full closure in Session 08) | implemented |
| ARCH-002 | import-boundary guard | implemented, verified |

**Test results:**

| Command | Exit code | Result |
|---|---|---|
| `python3 tools/pcb_trace_resistance.py --selftest` (pre-change) | 0 | 118/118 PASS |
| `python3 -m pytest -q` (post-change, 37 tests) | 0 | 37 passed in 0.02 s |
| `python3 tools/pcb_trace_resistance.py --selftest` (post-change) | 0 | 118/118 PASS |

---

## Implementation Note

### Approach (written before coding, per §Required work §1)

Session 02 is purely structural. No code is extracted from
`tools/pcb_trace_resistance.py`; that is the work of Sessions 03–08.
The session therefore:

1. Creates `pyproject.toml` so the package is installable with
   `pip install -e .` and pytest can be invoked via `python3 -m pytest`.
2. Creates `pathminer/__init__.py` and nine sub-package stub `__init__.py`
   files — one per layer in the dependency contract — containing only
   docstrings and version/import stubs.
3. Creates `tests/test_import_boundaries.py` with 37 pytest tests that use
   static AST analysis to enforce the dependency direction. The tests are
   green today (empty stubs have no imports) and turn red if a forbidden
   import is introduced in any future session.
4. Creates `.github/workflows/ci.yml` so every push to `main` or an
   `ai/session-*` branch runs the pytest suite and the v0.13 selftest.

The "I/O" restriction on `pathminer.core` is interpreted as: core must not
import file I/O libraries (`json`, `csv`, `sqlite3`, `configparser`,
`yaml`, `toml`, `pickle`, `shelve`, `dbm`). These belong in `storage/`
and `report/`. Core is permitted to use `math`, `cmath`, `dataclasses`,
`typing`, `functools`, `itertools`, and similar stdlib utilities.

### Layer contract (as documented in `pathminer/__init__.py`)

```
core/       pure physics and maths.  No KiCad, no Qt, no I/O.
kicad/      file formats and live-board adapter.  Imports core.  No Qt.
models/     geometry → resistor network.  Imports core + kicad.
analysis/   orchestration.  Imports core, kicad, models.
report/     serialisation and rendering.  Imports analysis.
storage/    project files, atomic writes, migration.  Imports core + analysis contracts.
cli/        command-line entry points.  Imports analysis + report + storage.
ui/         Qt widgets.  Imports everything.  NOTHING may import ui.
plugin/     KiCad plugin shim.  Imports kicad + analysis.  No Qt.
```

---

## Detailed Test Results

### Pre-change baseline (before any file was created)

```
$ python3 tools/pcb_trace_resistance.py --selftest
118/118 checks passed
exit code: 0
```

```
$ python3 -m pytest -q
no tests ran in 0.02s
exit code: 0
```

### Post-change

```
$ python3 -m pytest -v
============================= test session starts ==============================
platform darwin -- Python 3.12.13, pytest-9.1.1, pluggy-1.6.0
rootdir: .../pathminer-session-02-claude/workspace
configfile: pyproject.toml
testpaths: tests
collected 37 items

tests/test_import_boundaries.py::test_core_no_forbidden_external_imports PASSED
tests/test_import_boundaries.py::test_core_no_upward_internal_imports PASSED
tests/test_import_boundaries.py::test_kicad_no_qt_imports PASSED
tests/test_import_boundaries.py::test_kicad_no_wx_imports PASSED
tests/test_import_boundaries.py::test_headless_layers_no_qt[models] PASSED
tests/test_import_boundaries.py::test_headless_layers_no_qt[analysis] PASSED
tests/test_import_boundaries.py::test_headless_layers_no_qt[report] PASSED
tests/test_import_boundaries.py::test_headless_layers_no_qt[storage] PASSED
tests/test_import_boundaries.py::test_headless_layers_no_qt[cli] PASSED
tests/test_import_boundaries.py::test_headless_layers_no_wx[models] PASSED
tests/test_import_boundaries.py::test_headless_layers_no_wx[analysis] PASSED
tests/test_import_boundaries.py::test_headless_layers_no_wx[report] PASSED
tests/test_import_boundaries.py::test_headless_layers_no_wx[storage] PASSED
tests/test_import_boundaries.py::test_headless_layers_no_wx[cli] PASSED
tests/test_import_boundaries.py::test_plugin_no_qt_imports PASSED
tests/test_import_boundaries.py::test_no_subpkg_imports_ui[core] PASSED
tests/test_import_boundaries.py::test_no_subpkg_imports_ui[kicad] PASSED
tests/test_import_boundaries.py::test_no_subpkg_imports_ui[models] PASSED
tests/test_import_boundaries.py::test_no_subpkg_imports_ui[analysis] PASSED
tests/test_import_boundaries.py::test_no_subpkg_imports_ui[report] PASSED
tests/test_import_boundaries.py::test_no_subpkg_imports_ui[storage] PASSED
tests/test_import_boundaries.py::test_no_subpkg_imports_ui[cli] PASSED
tests/test_import_boundaries.py::test_no_subpkg_imports_ui[plugin] PASSED
tests/test_import_boundaries.py::test_root_package_does_not_import_ui PASSED
tests/test_import_boundaries.py::test_subpackage_is_importable[pathminer] PASSED
tests/test_import_boundaries.py::test_subpackage_is_importable[pathminer.core] PASSED
tests/test_import_boundaries.py::test_subpackage_is_importable[pathminer.kicad] PASSED
tests/test_import_boundaries.py::test_subpackage_is_importable[pathminer.models] PASSED
tests/test_import_boundaries.py::test_subpackage_is_importable[pathminer.analysis] PASSED
tests/test_import_boundaries.py::test_subpackage_is_importable[pathminer.report] PASSED
tests/test_import_boundaries.py::test_subpackage_is_importable[pathminer.storage] PASSED
tests/test_import_boundaries.py::test_subpackage_is_importable[pathminer.cli] PASSED
tests/test_import_boundaries.py::test_subpackage_is_importable[pathminer.ui] PASSED
tests/test_import_boundaries.py::test_subpackage_is_importable[pathminer.plugin] PASSED
tests/test_import_boundaries.py::test_selfcheck_guard_detects_forbidden_import PASSED
tests/test_import_boundaries.py::test_selfcheck_guard_detects_ui_import PASSED
tests/test_import_boundaries.py::test_selfcheck_guard_allows_stdlib_in_non_core PASSED

============================== 37 passed in 0.02s ==============================
exit code: 0
```

```
$ python3 tools/pcb_trace_resistance.py --selftest
118/118 checks passed
exit code: 0
```

---

## Files Changed

### Added

| File | Purpose |
|---|---|
| `pyproject.toml` | PEP 517/518 installable package; pytest config with pythonpath and testpaths |
| `pathminer/__init__.py` | Package root; `__version__ = "0.14.0.dev0"`; layer-contract docstring |
| `pathminer/core/__init__.py` | Stub; layer-contract note; planned module list |
| `pathminer/kicad/__init__.py` | Stub; layer-contract note; planned module list |
| `pathminer/models/__init__.py` | Stub; layer-contract note; planned module list |
| `pathminer/analysis/__init__.py` | Stub; layer-contract note; planned module list |
| `pathminer/report/__init__.py` | Stub; layer-contract note; planned module list |
| `pathminer/storage/__init__.py` | Stub; layer-contract note; planned module list |
| `pathminer/cli/__init__.py` | Stub + `main()` stub that exits with a clear message; console script wired |
| `pathminer/ui/__init__.py` | Stub; documents the "nothing imports ui" rule |
| `pathminer/plugin/__init__.py` | Stub; layer-contract note (wx allowed via pcbnew; Qt forbidden) |
| `tests/test_import_boundaries.py` | 37-test ARCH-002 import-boundary guard (static AST) |
| `.github/workflows/ci.yml` | CI: pytest + selftest on push/PR; lint non-blocking |

### Modified

None.

### Removed

None.

---

## APIs and Schemas Changed

- **New public API:** `pathminer.__version__` (`"0.14.0.dev0"`)
- **New console script:** `pathminer` → `pathminer.cli:main` (stub; exits with message)
- No schemas changed.

---

## Decisions

1. **Static AST analysis for import guard.** Chosen over runtime `importlib` inspection
   because it catches violations before any code runs, works on empty stubs, and has no
   import-side-effects. Approach documented in `documents/library_refactor_recommendations.md §2 R1`.

2. **Version `0.14.0.dev0`.** The v0.13 baseline is preserved unchanged in `tools/`.
   The package starts at `0.14.0.dev0` to signal pre-release development status without
   claiming a release. Full release numbering will be confirmed by the coordinator
   before the Resistance v1 milestone.

3. **`json` and other I/O libraries forbidden in `core/`.** Serialisation belongs in
   `storage/` and `report/`. This matches the "no I/O" clause in the layer contract
   from `documents/library_refactor_recommendations.md §2 R1`.

4. **`wx` allowed in `plugin/` (but not Qt).** The KiCad plugin uses wx via the
   `pcbnew` runtime; banning wx from `plugin/` would block that legitimate use.
   Qt remains forbidden in `plugin/` since KiCad does not provide it.

5. **Lint step is non-blocking (`continue-on-error: true`).** This matches the
   plan to promote lint to required only at the QA-009 release-gate session.

6. **`documents/change_log.md` not updated.** That file is outside the owned write
   scope for this session. The coordinator should add a changelog entry when integrating.

---

## Assumptions

- The `pathminer` PyPI name is not claimed; the coordinator will confirm before a
  public release.
- `pip install -e ".[dev]"` resolves correctly in CI (Python 3.9+, setuptools ≥68).
  PySide6 is excluded from CI install because the test suite does not need Qt.
- The `ruff` lint step uses version available via `pip install ruff`; no pinned version
  is required while the step is non-blocking.

---

## Deviations

- None. All work is within the owned write scope.

---

## Known Issues / Open Items

- **`__pycache__/` directories are not ignored by `.gitignore`** at the workspace level.
  The root `.gitignore` covers `.venv/` and `pathminer-session-*/` but not `__pycache__/`.
  Adding a workspace `.gitignore` is outside this session's scope. The coordinator should
  add `**/__pycache__/` to the root `.gitignore` during integration.

- **`documents/change_log.md` not updated** — outside owned scope (see Decision 6).

- **ARCH-001 not fully closed.** The Done-when clause ("the application runs from the
  package") requires code extraction (Sessions 03–08). Session 02 contributes only the
  package-skeleton slice. This is consistent with the SESSION_STATUS.csv note:
  "ARCH-001 closes in Session 08."

- **`pathminer.cli:main()` stub exits with exit code 1.** This is intentional; the real
  CLI is implemented in a later session.

---

## Dependent Session Impact

- **Sessions 03–08 (code extraction):** Start from this commit. Each session imports
  the sub-package it owns; the import-boundary test will catch violations immediately.
- **Session 08 (compatibility integration):** Closes ARCH-001 by wiring the extracted
  code to produce a working program from the package. Must pass all 37 boundary tests.
- **All subsequent sessions:** Should run `python3 -m pytest -q` as part of their
  pre-change baseline check (the test suite now exists and takes < 1 s).
- **CI workflow:** Active from first push of this branch. Sessions that push their
  branches will automatically get pytest + selftest coverage.

---

## Recommended Next Action

Coordinator: integrate this branch into main, then open Sessions 03, 04, and 05
(W2-A, W2-B, W2-C — parallel, disjoint write scopes) from the integrated commit.
Add `**/__pycache__/` to the root `.gitignore` and a `documents/change_log.md` entry
during integration.

**READY_FOR_REVIEW**
