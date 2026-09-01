# v0.2
"""ARCH-002: automated import-boundary guard for the pathminer package.

Rules enforced (from documents/library_refactor_recommendations.md S2 R1
and .ai/planning/PathMiner_Implementation_Punch_List.md ARCH-002):

    core/     - pure physics and maths.
                Must NOT import: KiCad packages, Qt packages, wx, or file
                I/O libraries; must NOT import pathminer.kicad, pathminer.ui,
                pathminer.storage, pathminer.plugin, or pathminer.report.

    kicad/    - file formats and live-board adapter.
                Must NOT import: Qt packages or wx.
                Must NOT import: pathminer.ui.

    models/   - geometry-to-network builders.
                Must NOT import: Qt packages or wx.
                Must NOT import: pathminer.ui.

    analysis/ - orchestration layer.
                Must NOT import: Qt packages or wx.
                Must NOT import: pathminer.ui.

    report/   - serialisation and rendering.
                Must NOT import: Qt packages or wx.
                Must NOT import: pathminer.ui.

    storage/  - project files and atomic writes.
                Must NOT import: Qt packages or wx.
                Must NOT import: pathminer.ui.

    cli/      - command-line entry points.
                Must NOT import: Qt packages or wx.
                Must NOT import: pathminer.ui.

    plugin/   - KiCad plugin shim (may import wx via pcbnew; must NOT import Qt).
                Must NOT import: Qt packages.
                Must NOT import: pathminer.ui.

    UNIVERSAL - Nothing (except pathminer.ui itself) may import pathminer.ui.

Detection method: static AST walk over every .py file in the relevant tree.
Absolute and relative imports are both resolved to canonical dotted names.
The test is green today because the stub __init__.py files are empty or
contain only docstrings and comments.  It turns red the moment a forbidden
dependency is introduced -- which is the intended safety guard.

Done-when clause (ARCH-002): "an automated import-boundary test fails on a
forbidden dependency."  The self-check section below exercises the actual
boundary-enforcement path against temporary package files and asserts that
the guard raises pytest.fail.Exception on violations.
"""

from __future__ import annotations

import ast
from pathlib import Path
from typing import Sequence

import pytest

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

WORKSPACE = Path(__file__).parent.parent
PATHMINER = WORKSPACE / "pathminer"


# ---------------------------------------------------------------------------
# Package-context helper
# ---------------------------------------------------------------------------

def _package_of_file(py_file: Path, pathminer_root: Path) -> str:
    """Return the dotted package name that *contains* py_file.

    For pathminer/core/__init__.py  -> "pathminer.core"
    For pathminer/core/utils.py     -> "pathminer.core"

    The containing package is always the directory holding the file,
    expressed relative to pathminer_root.parent (the workspace root).
    """
    pkg_dir = py_file.parent
    rel = pkg_dir.relative_to(pathminer_root.parent)
    return ".".join(rel.parts)


# ---------------------------------------------------------------------------
# Relative-import resolver
# ---------------------------------------------------------------------------

def _resolve_relative(
    level: int,
    module: str | None,
    imported_names: list[str],
    py_file: Path,
    pathminer_root: Path,
) -> list[str]:
    """Resolve a relative ImportFrom node to canonical absolute dotted names.

    Python semantics:
        level=1 (.)   means: current package (directory of py_file)
        level=2 (..)  means: parent package (one level up)
        level=N       means: N-1 levels up from current package

    For pathminer/core/utils.py (package = pathminer.core):
        from . import x      -> pathminer.core.x
        from .. import ui    -> pathminer.ui
        from ..ui import app -> pathminer.ui

    The result list contains all resolved absolute dotted names.
    """
    pkg = _package_of_file(py_file, pathminer_root)
    pkg_parts = pkg.split(".") if pkg else []
    # Go up (level-1) package levels from the containing package.
    go_up = level - 1
    if go_up >= len(pkg_parts):
        # Relative import escapes the top-level package -- malformed code.
        # Return an empty list; a SyntaxError or ImportError will catch this at runtime.
        return []
    base_parts = pkg_parts[: len(pkg_parts) - go_up] if go_up > 0 else pkg_parts
    base = ".".join(base_parts)

    results: list[str] = []
    if module:
        # from ..module import name  ->  base.module
        abs_mod = f"{base}.{module}" if base else module
        results.append(abs_mod)
    else:
        # from .. import name1, name2  ->  base.name1, base.name2
        for name in imported_names:
            abs_name = f"{base}.{name}" if base else name
            results.append(abs_name)
    return results


# ---------------------------------------------------------------------------
# AST import collector (absolute and relative)
# ---------------------------------------------------------------------------

def _collect_imports(py_file: Path, pathminer_root: Path | None = None) -> list[str]:
    """Return canonical absolute module names for every import in *py_file*.

    Handles all five forms that a caller might use to reach a forbidden module::

        import pathminer.ui                   -> ["pathminer", "pathminer.ui"]
        from pathminer.ui import app          -> ["pathminer", "pathminer.ui",
                                                  "pathminer.ui.app"]
        from pathminer import ui              -> ["pathminer", "pathminer.ui"]
        from .. import ui   (in core/)        -> ["pathminer.ui", "pathminer"]
        from ..ui import app (in core/)       -> ["pathminer.ui", "pathminer"]

    The result contains both full dotted forms and top-level names so that
    callers can match against either ``"pathminer.ui"`` or ``"PySide6"``.
    """
    root = pathminer_root if pathminer_root is not None else PATHMINER
    src = py_file.read_text(encoding="utf-8")
    try:
        tree = ast.parse(src, filename=str(py_file))
    except SyntaxError as exc:
        pytest.fail(f"SyntaxError in {py_file}: {exc}")

    names: list[str] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            # import foo.bar  ->  ["foo", "foo.bar"]
            for alias in node.names:
                top = alias.name.split(".")[0]
                names.append(top)
                if "." in alias.name:
                    names.append(alias.name)

        elif isinstance(node, ast.ImportFrom):
            if node.level and node.level > 0:
                # Relative import: resolve to absolute dotted names.
                imported_names = [alias.name for alias in node.names]
                abs_names = _resolve_relative(
                    node.level, node.module, imported_names, py_file, root
                )
                for abs_name in abs_names:
                    names.append(abs_name)
                    top = abs_name.split(".")[0]
                    if top not in names:
                        names.append(top)

            elif node.module:
                # Absolute import: from module import name1, name2
                top = node.module.split(".")[0]
                names.append(top)
                names.append(node.module)
                # Also record module.name so "from pathminer import ui"
                # produces "pathminer.ui" (not just "pathminer").
                for alias in node.names:
                    full = f"{node.module}.{alias.name}"
                    names.append(full)

    return names


# ---------------------------------------------------------------------------
# Violation finder (pure; does not call pytest.fail)
# ---------------------------------------------------------------------------

def _find_violations(
    files: list[Path],
    forbidden: Sequence[str],
    pathminer_root: Path,
) -> list[str]:
    """Return human-readable violation strings, one per forbidden import found.

    Does NOT call pytest.fail -- callers decide how to report.
    """
    violations: list[str] = []
    for py_file in files:
        imports = _collect_imports(py_file, pathminer_root)
        for imp in imports:
            for forbidden_name in forbidden:
                if imp == forbidden_name or imp.startswith(forbidden_name + "."):
                    violations.append(
                        f"  {py_file}: imports '{imp}'"
                        f" (forbidden: '{forbidden_name}')"
                    )
    return violations


# ---------------------------------------------------------------------------
# File lister
# ---------------------------------------------------------------------------

def _files_in_root(pathminer_root: Path, subpkg: str) -> list[Path]:
    """All .py files under pathminer_root/subpkg/ (recursive)."""
    d = pathminer_root / subpkg
    if not d.exists():
        return []
    return sorted(d.rglob("*.py"))


def _files_in(subpkg: str) -> list[Path]:
    """All .py files under PATHMINER/subpkg/ using the live package tree."""
    return _files_in_root(PATHMINER, subpkg)


# ---------------------------------------------------------------------------
# Boundary check (calls pytest.fail on violation)
# ---------------------------------------------------------------------------

def _check_no_forbidden(
    subpkg: str,
    forbidden: Sequence[str],
    *,
    pathminer_root: Path | None = None,
) -> None:
    """Assert no file in *subpkg* imports any name from *forbidden*.

    Parameters
    ----------
    subpkg:
        Sub-package directory name relative to ``pathminer_root``.
    forbidden:
        Sequence of module-name prefixes that must not appear.
    pathminer_root:
        Root of the pathminer package directory.  Defaults to PATHMINER
        (the live workspace tree).  Pass a temporary directory in tests.
    """
    root = pathminer_root if pathminer_root is not None else PATHMINER
    files = _files_in_root(root, subpkg)
    violations = _find_violations(files, forbidden, root)
    if violations:
        bullet_list = "\n".join(violations)
        pytest.fail(
            f"pathminer/{subpkg}/ contains forbidden import(s):\n{bullet_list}"
        )


# ---------------------------------------------------------------------------
# Qt / wx / KiCad external forbidden names (shared across rules)
# ---------------------------------------------------------------------------

_QT_PACKAGES = frozenset({
    "PyQt5", "PyQt6", "PySide2", "PySide6", "qtpy", "pyqtgraph",
})

_WX_PACKAGES = frozenset({
    "wx",
})

_KICAD_PACKAGES = frozenset({
    "pcbnew", "kiutils", "sexprdata",
})

# File I/O libraries that pure-physics core must not use.
_IO_LIBRARIES = frozenset({
    "json", "csv", "sqlite3", "configparser", "tomllib", "tomli",
    "yaml", "toml", "pickle", "shelve", "dbm",
})

# ---------------------------------------------------------------------------
# ARCH-002 Rule A: pathminer.core -- pure physics, no external I/O / UI / KiCad
# ---------------------------------------------------------------------------

_CORE_FORBIDDEN_EXTERNAL = _QT_PACKAGES | _WX_PACKAGES | _KICAD_PACKAGES | _IO_LIBRARIES

_CORE_FORBIDDEN_INTERNAL = frozenset({
    "pathminer.kicad",
    "pathminer.models",
    "pathminer.analysis",
    "pathminer.report",
    "pathminer.storage",
    "pathminer.cli",
    "pathminer.ui",
    "pathminer.plugin",
})


def test_core_no_forbidden_external_imports() -> None:
    """pathminer.core must not import KiCad, Qt, wx, or file-I/O libraries."""
    _check_no_forbidden("core", sorted(_CORE_FORBIDDEN_EXTERNAL))


def test_core_no_upward_internal_imports() -> None:
    """pathminer.core must not import any higher pathminer sub-package."""
    _check_no_forbidden("core", sorted(_CORE_FORBIDDEN_INTERNAL))


# ---------------------------------------------------------------------------
# ARCH-002 Rule B: pathminer.kicad -- no Qt, no wx
# ---------------------------------------------------------------------------


def test_kicad_no_qt_imports() -> None:
    """pathminer.kicad must not import Qt packages."""
    _check_no_forbidden("kicad", sorted(_QT_PACKAGES))


def test_kicad_no_wx_imports() -> None:
    """pathminer.kicad must not import wx (wx is only allowed in pathminer.plugin)."""
    _check_no_forbidden("kicad", sorted(_WX_PACKAGES))


# ---------------------------------------------------------------------------
# ARCH-002 Rule C: models, analysis, report, storage, cli -- no Qt, no wx
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("subpkg", ["models", "analysis", "report", "storage", "cli"])
def test_headless_layers_no_qt(subpkg: str) -> None:
    """Headless layers must not import Qt packages."""
    _check_no_forbidden(subpkg, sorted(_QT_PACKAGES))


@pytest.mark.parametrize("subpkg", ["models", "analysis", "report", "storage", "cli"])
def test_headless_layers_no_wx(subpkg: str) -> None:
    """Headless layers must not import wx."""
    _check_no_forbidden(subpkg, sorted(_WX_PACKAGES))


# ---------------------------------------------------------------------------
# ARCH-002 Rule D: plugin -- no Qt (wx/pcbnew is allowed via KiCad runtime)
# ---------------------------------------------------------------------------


def test_plugin_no_qt_imports() -> None:
    """pathminer.plugin must not import Qt packages (it uses wx via KiCad)."""
    _check_no_forbidden("plugin", sorted(_QT_PACKAGES))


# ---------------------------------------------------------------------------
# ARCH-002 Rule E (universal): nothing outside pathminer.ui may import it
# ---------------------------------------------------------------------------

_ALL_SUBPKGS_EXCEPT_UI = [
    "core", "kicad", "models", "analysis", "report", "storage", "cli", "plugin",
]


@pytest.mark.parametrize("subpkg", _ALL_SUBPKGS_EXCEPT_UI)
def test_no_subpkg_imports_ui(subpkg: str) -> None:
    """No sub-package except ui itself may import pathminer.ui."""
    _check_no_forbidden(subpkg, ["pathminer.ui"])


def test_root_package_does_not_import_ui() -> None:
    """pathminer/__init__.py must not import pathminer.ui."""
    root_init = PATHMINER / "__init__.py"
    imports = _collect_imports(root_init)
    ui_imports = [
        imp for imp in imports
        if imp == "pathminer.ui" or imp.startswith("pathminer.ui.")
    ]
    assert not ui_imports, (
        f"pathminer/__init__.py imports pathminer.ui: {ui_imports!r}"
    )


# ---------------------------------------------------------------------------
# Smoke test: all declared sub-packages are importable
# ---------------------------------------------------------------------------

_EXPECTED_SUBPKGS = [
    "pathminer",
    "pathminer.core",
    "pathminer.kicad",
    "pathminer.models",
    "pathminer.analysis",
    "pathminer.report",
    "pathminer.storage",
    "pathminer.cli",
    "pathminer.ui",
    "pathminer.plugin",
]


@pytest.mark.parametrize("module_name", _EXPECTED_SUBPKGS)
def test_subpackage_is_importable(module_name: str) -> None:
    """Every declared sub-package must be importable without error."""
    import importlib

    try:
        importlib.import_module(module_name)
    except ImportError as exc:
        pytest.fail(f"Cannot import {module_name!r}: {exc}")


# ---------------------------------------------------------------------------
# Self-checks: boundary-enforcement exercised against temporary package files
#
# Each test creates a minimal pathminer/core/ tree in a tmp_path directory,
# calls the real import collector or guard function, and asserts the expected
# outcome.  These tests prove the failure path works -- not just that string
# helpers return the right strings.
# ---------------------------------------------------------------------------


def _make_stub(tmp_path: Path, rel_path: str, source: str) -> Path:
    """Write *source* to tmp_path/rel_path, creating parent dirs."""
    f = tmp_path / rel_path
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(source)
    return f


# --- Import-collection correctness ---


def test_selfcheck_absolute_import_detected(tmp_path: Path) -> None:
    """'import pathminer.ui' is collected as 'pathminer.ui'."""
    f = _make_stub(tmp_path, "pathminer/core/__init__.py", "import pathminer.ui\n")
    root = tmp_path / "pathminer"
    imports = _collect_imports(f, root)
    assert "pathminer.ui" in imports, f"Got: {imports}"


def test_selfcheck_from_module_import_name_detected(tmp_path: Path) -> None:
    """'from pathminer.ui import app' is collected as 'pathminer.ui'."""
    f = _make_stub(tmp_path, "pathminer/core/__init__.py",
                   "from pathminer.ui import app\n")
    root = tmp_path / "pathminer"
    imports = _collect_imports(f, root)
    assert "pathminer.ui" in imports, f"Got: {imports}"


def test_selfcheck_from_pkg_import_subpkg_detected(tmp_path: Path) -> None:
    """'from pathminer import ui' is collected as 'pathminer.ui'."""
    f = _make_stub(tmp_path, "pathminer/core/__init__.py",
                   "from pathminer import ui\n")
    root = tmp_path / "pathminer"
    imports = _collect_imports(f, root)
    assert "pathminer.ui" in imports, f"Got: {imports}"


def test_selfcheck_relative_dotdot_import_ui(tmp_path: Path) -> None:
    """'from .. import ui' in pathminer/core/ resolves to 'pathminer.ui'."""
    f = _make_stub(tmp_path, "pathminer/core/__init__.py", "from .. import ui\n")
    root = tmp_path / "pathminer"
    imports = _collect_imports(f, root)
    assert "pathminer.ui" in imports, f"Got: {imports}"


def test_selfcheck_relative_dotdot_from_ui_import_app(tmp_path: Path) -> None:
    """'from ..ui import app' in pathminer/core/ resolves to 'pathminer.ui'."""
    f = _make_stub(tmp_path, "pathminer/core/__init__.py",
                   "from ..ui import app\n")
    root = tmp_path / "pathminer"
    imports = _collect_imports(f, root)
    assert "pathminer.ui" in imports, f"Got: {imports}"


def test_selfcheck_relative_dot_import_sibling_not_ui(tmp_path: Path) -> None:
    """'from . import utils' in pathminer/core/ is NOT 'pathminer.ui'."""
    f = _make_stub(tmp_path, "pathminer/core/__init__.py",
                   "from . import utils\n")
    root = tmp_path / "pathminer"
    imports = _collect_imports(f, root)
    ui_imports = [i for i in imports if "pathminer.ui" in i]
    assert not ui_imports, (
        f"Sibling import wrongly resolved to ui: {ui_imports}"
    )


# --- Violation detection (find_violations, no pytest.fail) ---


def test_selfcheck_find_violations_non_empty_on_forbidden(tmp_path: Path) -> None:
    """_find_violations returns entries when a forbidden import is present."""
    f = _make_stub(tmp_path, "pathminer/core/__init__.py", "import PySide6\n")
    root = tmp_path / "pathminer"
    violations = _find_violations([f], ["PySide6"], root)
    assert violations, "Expected violations but got none"


def test_selfcheck_find_violations_empty_on_allowed(tmp_path: Path) -> None:
    """_find_violations returns empty list when no forbidden imports present."""
    f = _make_stub(tmp_path, "pathminer/core/__init__.py", "import math\n")
    root = tmp_path / "pathminer"
    violations = _find_violations([f], ["PySide6", "pathminer.ui"], root)
    assert not violations, f"Unexpected violations: {violations}"


def test_selfcheck_find_violations_json_in_core(tmp_path: Path) -> None:
    """'import json' in core is flagged as an I/O violation."""
    f = _make_stub(tmp_path, "pathminer/core/__init__.py", "import json\n")
    root = tmp_path / "pathminer"
    violations = _find_violations([f], ["json"], root)
    assert violations, "Expected json violation but got none"


def test_selfcheck_find_violations_json_allowed_in_storage(tmp_path: Path) -> None:
    """'import json' in storage is NOT flagged by non-core rules (no json in forbidden)."""
    f = _make_stub(tmp_path, "pathminer/storage/__init__.py", "import json\n")
    root = tmp_path / "pathminer"
    # Storage is only checked for Qt/wx/ui, not I/O libraries.
    violations = _find_violations([f], sorted(_QT_PACKAGES | _WX_PACKAGES), root)
    assert not violations, f"Unexpected violations: {violations}"


# --- Actual guard path: assert _check_no_forbidden raises on violation ---


def test_selfcheck_guard_raises_on_qt_import(tmp_path: Path) -> None:
    """_check_no_forbidden raises pytest.fail.Exception on a Qt import in core."""
    _make_stub(tmp_path, "pathminer/core/__init__.py", "import PySide6\n")
    with pytest.raises(pytest.fail.Exception, match="forbidden import"):
        _check_no_forbidden("core", ["PySide6"],
                            pathminer_root=tmp_path / "pathminer")


def test_selfcheck_guard_raises_on_relative_ui_import(tmp_path: Path) -> None:
    """_check_no_forbidden raises when core uses 'from .. import ui'."""
    _make_stub(tmp_path, "pathminer/core/__init__.py", "from .. import ui\n")
    with pytest.raises(pytest.fail.Exception, match="forbidden import"):
        _check_no_forbidden("core", ["pathminer.ui"],
                            pathminer_root=tmp_path / "pathminer")


def test_selfcheck_guard_raises_on_from_pkg_import_ui(tmp_path: Path) -> None:
    """_check_no_forbidden raises when core uses 'from pathminer import ui'."""
    _make_stub(tmp_path, "pathminer/core/__init__.py",
               "from pathminer import ui\n")
    with pytest.raises(pytest.fail.Exception, match="forbidden import"):
        _check_no_forbidden("core", ["pathminer.ui"],
                            pathminer_root=tmp_path / "pathminer")


def test_selfcheck_guard_passes_on_clean_core(tmp_path: Path) -> None:
    """_check_no_forbidden does NOT raise when core imports only allowed modules."""
    _make_stub(tmp_path, "pathminer/core/__init__.py",
               "import math\nimport dataclasses\n")
    # Should not raise
    _check_no_forbidden(
        "core",
        sorted(_CORE_FORBIDDEN_EXTERNAL | _CORE_FORBIDDEN_INTERNAL),
        pathminer_root=tmp_path / "pathminer",
    )
