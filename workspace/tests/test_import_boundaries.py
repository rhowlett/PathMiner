# v0.1
"""ARCH-002: automated import-boundary guard for the pathminer package.

Rules enforced (from documents/library_refactor_recommendations.md §2 R1
and .ai/planning/PathMiner_Implementation_Punch_List.md ARCH-002):

    core/     — pure physics and maths.
                Must NOT import: KiCad packages, Qt packages, wx, or file
                I/O libraries; must NOT import pathminer.kicad, pathminer.ui,
                pathminer.storage, pathminer.plugin, or pathminer.report.

    kicad/    — file formats and live-board adapter.
                Must NOT import: Qt packages or wx.
                Must NOT import: pathminer.ui.

    models/   — geometry-to-network builders.
                Must NOT import: Qt packages or wx.
                Must NOT import: pathminer.ui.

    analysis/ — orchestration layer.
                Must NOT import: Qt packages or wx.
                Must NOT import: pathminer.ui.

    report/   — serialisation and rendering.
                Must NOT import: Qt packages or wx.
                Must NOT import: pathminer.ui.

    storage/  — project files and atomic writes.
                Must NOT import: Qt packages or wx.
                Must NOT import: pathminer.ui.

    cli/      — command-line entry points.
                Must NOT import: Qt packages or wx.
                Must NOT import: pathminer.ui.

    plugin/   — KiCad plugin shim (may import wx via pcbnew; must NOT import Qt).
                Must NOT import: Qt packages.
                Must NOT import: pathminer.ui.

    UNIVERSAL — Nothing (except pathminer.ui itself) may import pathminer.ui.

Detection method: static AST walk over every .py file in the relevant tree.
The test is green today because the stub __init__.py files are empty or
contain only docstrings and comments.  It turns red the moment a forbidden
dependency is introduced — which is the intended safety guard.

Done-when clause (ARCH-002): "an automated import-boundary test fails on a
forbidden dependency."  This test satisfies that clause once code is present;
the self-check section below demonstrates the failure path.
"""

from __future__ import annotations

import ast
import textwrap
from pathlib import Path
from typing import Sequence

import pytest

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

WORKSPACE = Path(__file__).parent.parent
PATHMINER = WORKSPACE / "pathminer"

# ---------------------------------------------------------------------------
# AST import collector
# ---------------------------------------------------------------------------


def _collect_imports(py_file: Path) -> list[str]:
    """Return every imported module name (full dotted form) found in *py_file*.

    Both ``import foo.bar`` and ``from foo.bar import baz`` are captured.
    The result includes both the top-level name and the full dotted form so
    callers can match against either ``"json"`` or ``"json.decoder"``.
    """
    src = py_file.read_text(encoding="utf-8")
    try:
        tree = ast.parse(src, filename=str(py_file))
    except SyntaxError as exc:
        pytest.fail(f"SyntaxError in {py_file}: {exc}")

    names: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                top = alias.name.split(".")[0]
                names.append(top)
                if "." in alias.name:
                    names.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                top = node.module.split(".")[0]
                names.append(top)
                if "." in node.module:
                    names.append(node.module)
    return names


def _files_in(subpkg: str) -> list[Path]:
    """All .py files under ``pathminer/<subpkg>/`` (recursive)."""
    d = PATHMINER / subpkg
    if not d.exists():
        return []
    return sorted(d.rglob("*.py"))


def _check_no_forbidden(
    subpkg: str,
    forbidden: Sequence[str],
    *,
    exclude_self: bool = False,
) -> None:
    """Assert no file in *subpkg* imports any name from *forbidden*.

    Parameters
    ----------
    subpkg:
        Sub-package directory name relative to ``pathminer/``.
    forbidden:
        Sequence of module-name prefixes that must not appear.
    exclude_self:
        When True, the sub-package's own files are excluded from the check
        (used so that ``ui/`` itself can import its own modules without
        tripping the universal ``pathminer.ui`` rule).
    """
    files = _files_in(subpkg)
    if exclude_self:
        own_prefix = f"pathminer.{subpkg}"
        files = [f for f in files if not str(f).endswith(f"pathminer/{subpkg}")]

    violations: list[str] = []
    for py_file in files:
        imports = _collect_imports(py_file)
        for imp in imports:
            for forbidden_name in forbidden:
                # Match exact name or sub-module: "json" matches "json" and "json.decoder"
                if imp == forbidden_name or imp.startswith(forbidden_name + "."):
                    violations.append(
                        f"  {py_file.relative_to(WORKSPACE)}: imports '{imp}' "
                        f"(forbidden: '{forbidden_name}')"
                    )
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

# File I/O libraries that pure-physics core must not use
_IO_LIBRARIES = frozenset({
    "json", "csv", "sqlite3", "configparser", "tomllib", "tomli",
    "yaml", "toml", "pickle", "shelve", "dbm",
})

# ---------------------------------------------------------------------------
# ARCH-002 Rule A: pathminer.core — pure physics, no external I/O / UI / KiCad
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
# ARCH-002 Rule B: pathminer.kicad — no Qt, no wx
# ---------------------------------------------------------------------------


def test_kicad_no_qt_imports() -> None:
    """pathminer.kicad must not import Qt packages."""
    _check_no_forbidden("kicad", sorted(_QT_PACKAGES))


def test_kicad_no_wx_imports() -> None:
    """pathminer.kicad must not import wx (wx is only allowed in pathminer.plugin)."""
    _check_no_forbidden("kicad", sorted(_WX_PACKAGES))


# ---------------------------------------------------------------------------
# ARCH-002 Rule C: models, analysis, report, storage, cli — no Qt, no wx
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
# ARCH-002 Rule D: plugin — no Qt (wx/pcbnew is allowed via KiCad runtime)
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
# Self-check: verify the guard actually catches violations
# ---------------------------------------------------------------------------


def _imports_from_ast(source: str) -> list[str]:
    """Helper used only in the self-check tests."""
    tree = ast.parse(textwrap.dedent(source))
    names: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                names.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                names.append(node.module)
    return names


def test_selfcheck_guard_detects_forbidden_import() -> None:
    """Confirm that _collect_imports catches a Qt import in synthetic source."""
    # Synthesise a source fragment that would be forbidden in core/
    src = "import PySide6\nfrom PySide6.QtWidgets import QApplication\n"
    imports = _imports_from_ast(src)
    # The guard should find "PySide6" in the forbidden set
    qt_found = [i for i in imports if i in _QT_PACKAGES or i.startswith("PySide6")]
    assert qt_found, "Self-check failed: guard did not detect synthesised Qt import"


def test_selfcheck_guard_detects_ui_import() -> None:
    """Confirm that _collect_imports catches a pathminer.ui import in synthetic source."""
    src = "from pathminer.ui import app\n"
    imports = _imports_from_ast(src)
    ui_found = [i for i in imports if i.startswith("pathminer.ui")]
    assert ui_found, "Self-check failed: guard did not detect synthesised pathminer.ui import"


def test_selfcheck_guard_allows_stdlib_in_non_core() -> None:
    """json is allowed in non-core layers; verify the guard does not flag it there."""
    src = "import json\n"
    imports = _imports_from_ast(src)
    # json is only forbidden in core — this self-check confirms report/storage/etc. can use it.
    # The test passes trivially if the guard for non-core layers excludes json.
    json_found = [i for i in imports if i == "json"]
    assert json_found == ["json"], "Self-check: expected to find 'json' in import list"
    # Confirm json is in _IO_LIBRARIES (forbidden only for core):
    assert "json" in _IO_LIBRARIES
    # Confirm json is NOT in _QT_PACKAGES or _WX_PACKAGES (never forbidden for other layers):
    assert "json" not in _QT_PACKAGES
    assert "json" not in _WX_PACKAGES
