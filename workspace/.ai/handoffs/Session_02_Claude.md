<!-- v0.2 -->
# Session 02 — Package and CI skeleton [READY_FOR_REVIEW]

**Status:** READY_FOR_REVIEW
**AI:** Claude
**Model:** claude-sonnet-4-6 (matches assignment)
**Effort level:** high
**Date:** 2026-09-01 (repaired; original 2026-08-31)
**Branch:** ai/session-02-claude-package-skeleton
**Base commit:** a8c49c95249d7c9d6f295b480deae801587af369
**Final commit:** 3b87edc4b03cbd8351d04c79cdc17bb2d0d2a291

---

## Executive Summary

Session 02 creates the installable `pathminer` package shell and the ARCH-002
automated dependency-direction guard without moving any production behaviour.
The v0.13 tool (`tools/pcb_trace_resistance.py`) is unchanged byte-for-byte.

This handoff was updated after a CHANGES_REQUESTED repair pass (2026-09-01).
See "Repair changes" below for what changed from the initial submission.

**Punch-list contribution:**

| ID | Role | Status |
|---|---|---|
| ARCH-001 | package-skeleton slice (full closure in Session 08) | implemented |
| ARCH-002 | import-boundary guard | implemented, verified |

**Test results (post-repair):**

| Command | Exit code | Result |
|---|---|---|
| `python3 tools/pcb_trace_resistance.py --selftest` (pre-change baseline) | 0 | 118/118 PASS |
| `python3 -m pytest -q` (post-repair, 48 tests) | 0 | 48 passed in 0.08 s |
| `python3 tools/pcb_trace_resistance.py --selftest` (post-repair) | 0 | 118/118 PASS |
| `python3 tests/baseline/regression_compare.py all` | 0 | 118/118, 284/284, 1 net/11 pairs PASS |

---

## Repair changes (CHANGES_REQUESTED 2026-09-01)

### Finding 1 — pyproject.toml backend and Python floor
- Backend corrected from `setuptools.backends.legacy:build` to `setuptools.build_meta`.
- `requires-python` raised from `>=3.9` to `>=3.10` (matches repository automation).
- Python 3.9 removed from classifiers; 3.10/3.11/3.12 retained.

### Finding 2 — Installability proven
Commands run and recorded:
```
python -m pip install -e ".[gui,dev]"
  Successfully installed pathminer-0.14.0.dev0

python -I -c "import pathminer; assert pathminer.__version__ == '0.14.0.dev0'"
  -> version OK: 0.14.0.dev0

python -m pip check
  -> No broken requirements found.

python -m build --wheel --outdir <scratchpad>/pathminer_wheel_build .
  Successfully built pathminer-0.14.0.dev0-py3-none-any.whl

(fresh venv) pip install pathminer-0.14.0.dev0-py3-none-any.whl
python -I -c "import pathminer; assert pathminer.__version__ == '0.14.0.dev0'"
  -> non-editable wheel install OK: 0.14.0.dev0

(fresh venv) pip check
  -> No broken requirements found.
```

### Finding 3 — CI workflow moved
Old path (ineffective inside workspace/): `workspace/.github/workflows/ci.yml`
New path (worktree root, one level above workspace/): `.github/workflows/ci.yml`
The workspace-level file was removed with `git rm`.

### Finding 4 — CI installs PySide6 and runs full regression
The workflow now uses `python -m pip install -e ".[gui,dev]"` (includes PySide6
required by v0.13 selftest import). Full canonical regression added as a
conditional step on Python 3.12 / ubuntu-latest only.

Full canonical regression run locally (2026-09-01):
```
python tests/baseline/regression_compare.py all
  === headless ===  PASS  118/118 vectors match golden fixture exactly
  === powerbank === PASS  284/284 vectors match golden fixture exactly
  === report ===    PASS  1 net(s), 11 pair(s) match golden fixture (tol=1e-06)
  === All suites PASS ===
  exit code: 0
```

### Finding 5 — AST import collector corrected for relative imports
`_collect_imports` now fully resolves all five forbidden-import forms to
canonical absolute dotted names:

| Source form | Resolved to |
|---|---|
| `import pathminer.ui` | `pathminer.ui` |
| `from pathminer.ui import app` | `pathminer.ui` |
| `from pathminer import ui` | `pathminer.ui` |
| `from .. import ui` (in core/) | `pathminer.ui` |
| `from ..ui import app` (in core/) | `pathminer.ui` |

New helpers: `_package_of_file`, `_resolve_relative`, `_find_violations`
(pure; returns violation strings without calling `pytest.fail`).
`_check_no_forbidden` now accepts an optional `pathminer_root` parameter.

### Finding 6 — Self-checks exercise actual enforcement path
Old self-checks merely inspected string return values.
New self-checks (13 tests) use `tmp_path` to create real temporary package
files and call the actual guard functions:
- 5 collection-correctness tests (absolute + relative import forms)
- 1 control test (sibling `.` import NOT flagged as `pathminer.ui`)
- 4 `_find_violations` tests (forbidden detected, allowed clean, json in core,
  json allowed in storage)
- 3 `_check_no_forbidden` tests that assert `pytest.fail.Exception` is raised
  (Qt absolute, relative `..ui`, `from pathminer import ui`) and one that
  asserts it does NOT raise on a clean core.

### Finding 8 — Trailing whitespace
`git diff --check HEAD` returned clean before each commit. No trailing whitespace.

---

## Implementation Note

### Approach (written before coding, per Required work S1)

Session 02 is purely structural. No code is extracted from
`tools/pcb_trace_resistance.py`; that is the work of Sessions 03-08.
The session therefore:

1. Creates `pyproject.toml` so the package is installable with
   `python -m pip install -e ".[gui,dev]"` and pytest can be invoked via
   `python3 -m pytest`.
2. Creates `pathminer/__init__.py` and nine sub-package stub `__init__.py`
   files -- one per layer in the dependency contract -- containing only
   docstrings and version/import stubs.
3. Creates `tests/test_import_boundaries.py` with 48 pytest tests that use
   static AST analysis (with proper relative-import resolution) to enforce
   the dependency direction. Green today (stubs are empty); turns red when
   any forbidden import is introduced in any future session.
4. Creates `.github/workflows/ci.yml` at the worktree root (one level above
   workspace/) so every push to `main` or an `ai/session-*` branch runs the
   pytest suite, v0.13 selftest, and (on 3.12/ubuntu) the full regression.

### Layer contract (as documented in `pathminer/__init__.py`)

```
core/     pure physics and maths.  No KiCad, no Qt, no I/O.
kicad/    file formats and live-board adapter.  Imports core.  No Qt.
models/   geometry to network.  Imports core + kicad.
analysis/ orchestration.  Imports core, kicad, models.
report/   serialisation and rendering.  Imports analysis.
storage/  project files, atomic writes, migration.
cli/      command-line entry points.  Imports analysis + report + storage.
ui/       Qt widgets.  Imports everything.  NOTHING may import ui.
plugin/   KiCad plugin shim.  Imports kicad + analysis.  No Qt.
```

---

## Detailed Test Results

### Pre-change baseline

```
$ python3 tools/pcb_trace_resistance.py --selftest
118/118 checks passed
exit code: 0

$ python3 -m pytest -q
no tests ran in 0.02s
exit code: 0
```

### Post-repair (final)

```
$ python3 -m pytest -v
============================= test session starts ==============================
platform darwin -- Python 3.12.13, pytest-9.1.1, pluggy-1.6.0
rootdir: .../pathminer-session-02-claude/workspace
configfile: pyproject.toml
testpaths: tests
collected 48 items

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
tests/test_import_boundaries.py::test_selfcheck_absolute_import_detected PASSED
tests/test_import_boundaries.py::test_selfcheck_from_module_import_name_detected PASSED
tests/test_import_boundaries.py::test_selfcheck_from_pkg_import_subpkg_detected PASSED
tests/test_import_boundaries.py::test_selfcheck_relative_dotdot_import_ui PASSED
tests/test_import_boundaries.py::test_selfcheck_relative_dotdot_from_ui_import_app PASSED
tests/test_import_boundaries.py::test_selfcheck_relative_dot_import_sibling_not_ui PASSED
tests/test_import_boundaries.py::test_selfcheck_find_violations_non_empty_on_forbidden PASSED
tests/test_import_boundaries.py::test_selfcheck_find_violations_empty_on_allowed PASSED
tests/test_import_boundaries.py::test_selfcheck_find_violations_json_in_core PASSED
tests/test_import_boundaries.py::test_selfcheck_find_violations_json_allowed_in_storage PASSED
tests/test_import_boundaries.py::test_selfcheck_guard_raises_on_qt_import PASSED
tests/test_import_boundaries.py::test_selfcheck_guard_raises_on_relative_ui_import PASSED
tests/test_import_boundaries.py::test_selfcheck_guard_raises_on_from_pkg_import_ui PASSED
tests/test_import_boundaries.py::test_selfcheck_guard_passes_on_clean_core PASSED

============================== 48 passed in 0.08s ==============================
exit code: 0

$ python3 tools/pcb_trace_resistance.py --selftest
118/118 checks passed
exit code: 0

$ python3 tests/baseline/regression_compare.py all
=== headless ===   PASS  118/118 vectors match golden fixture exactly
=== powerbank ===  PASS  284/284 vectors match golden fixture exactly
=== report ===     PASS  1 net(s), 11 pair(s) match golden fixture (tol=1e-06)
=== All suites PASS ===
exit code: 0
```

---

## Files Changed

### Added
| File | Purpose |
|---|---|
| `../. github/workflows/ci.yml` (worktree root) | CI at correct Git location; `.[gui,dev]` install; full regression on 3.12 |
| `pyproject.toml` | PEP 517/518 installable package; `setuptools.build_meta`; `>=3.10` |
| `pathminer/__init__.py` | Package root; `__version__`; layer-contract docstring |
| `pathminer/core/__init__.py` | Stub; layer-contract note; planned module list |
| `pathminer/kicad/__init__.py` | Stub |
| `pathminer/models/__init__.py` | Stub |
| `pathminer/analysis/__init__.py` | Stub |
| `pathminer/report/__init__.py` | Stub |
| `pathminer/storage/__init__.py` | Stub |
| `pathminer/cli/__init__.py` | Stub + `main()` stub |
| `pathminer/ui/__init__.py` | Stub |
| `pathminer/plugin/__init__.py` | Stub |
| `tests/test_import_boundaries.py` | 48-test ARCH-002 guard with proper relative-import resolution |

### Removed
| File | Reason |
|---|---|
| `workspace/.github/workflows/ci.yml` | Ineffective inside workspace/; replaced by worktree-root location |

### Modified
None to production files. pyproject.toml and test file modified in repair pass.

---

## APIs and Schemas Changed

- **New public API:** `pathminer.__version__` (`"0.14.0.dev0"`)
- **New console script:** `pathminer` -> `pathminer.cli:main` (stub; exits with message)
- No schemas changed.

---

## Decisions

1. **Static AST analysis for import guard.** Chosen over runtime `importlib` inspection
   because it catches violations before any code runs. Relative imports resolved using
   `_package_of_file` + `_resolve_relative` to canonical absolute dotted names.

2. **Version `0.14.0.dev0`.** Pre-release signal; confirms development status.
   Final versioning to be confirmed by coordinator before Resistance v1 milestone.

3. **`json` and other I/O libraries forbidden in `core/`.** Serialisation belongs in
   `storage/` and `report/`. Matches "no I/O" in the layer contract.

4. **`wx` allowed in `plugin/` (but not Qt).** KiCad plugin uses wx via the
   `pcbnew` runtime; banning wx from `plugin/` would block that legitimate use.

5. **Lint step is non-blocking (`continue-on-error: true`).** Matches the
   plan to promote lint to required only at the QA-009 release-gate session.

6. **Full canonical regression on 3.12/ubuntu only.** The regression takes ~40 s
   total and requires PySide6 + KiCad board files. Adding it to every matrix
   slot would make CI slow without proportionate benefit; the fixtures and
   comparator are stable enough that one slot is sufficient at this stage.

7. **`documents/change_log.md` not updated.** Outside owned write scope;
   coordinator to add entry on integration.

---

## Assumptions

- `pathminer` PyPI name is not claimed; coordinator to confirm before public release.
- `python -m pip install -e ".[gui,dev]"` installs correctly (Python 3.10+, setuptools>=68).
- GitHub Actions Ubuntu runners have no GUI display; `--selftest` runs headless because
  PySide6 is imported at module top-level but the application is not started.

---

## Deviations

- None. All work is within the owned write scope including the coordinator-granted
  narrow amendment (workflow location + repair files).

---

## Known Issues / Open Items

- **`__pycache__/`, `build/`, and `pathminer.egg-info/` not excluded by `.gitignore`**
  at the workspace level. The root `.gitignore` covers `.venv/` but not build artefacts.
  Coordinator should add `**/__pycache__/`, `build/`, and `*.egg-info/` to root `.gitignore`
  during integration.

- **`documents/change_log.md` not updated** (outside owned scope).

- **ARCH-001 not fully closed.** Done-when clause requires application to run from
  package (deferred to Session 08). This session contributes the skeleton slice only.

- **`pathminer.cli:main()` stub exits with code 1.** Intentional; real CLI in later session.

---

## Dependent Session Impact

- **Sessions 03-08:** Start from this commit; import-boundary tests catch violations.
- **Session 08:** Closes ARCH-001; must pass all 48 boundary tests.
- **All subsequent sessions:** `python3 -m pytest -q` is a valid pre-change baseline
  command (48 tests, < 0.1 s).
- **CI:** Active from first push; 3.12/ubuntu slot includes full regression.

---

## Recommended Next Action

Coordinator: integrate branch into main; add build artefact patterns to root `.gitignore`
and a `documents/change_log.md` entry during integration; open Sessions 03, 04, and 05
(W2-A, W2-B, W2-C -- parallel, disjoint write scopes) from the integrated commit.

**READY_FOR_REVIEW**
