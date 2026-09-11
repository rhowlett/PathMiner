# v0.1
"""tests/test_compatibility.py — Session 08 compatibility-facade tests.

Session 08 (closure owner of BASE-004, ARCH-006, ARCH-010) turns
``tools/pcb_trace_resistance.py`` into a *compatibility facade*: its
numerical solver dispatcher and pure planar-geometry helpers are now thin
aliases onto ``pathminer.core.solver`` / ``pathminer.core.geometry``
(Sessions 03/04/07) instead of duplicated copies, and
``tools/build_single_file.py`` regenerates a self-contained single-file
distribution from that facade (BASE-004).

These tests check the *wiring*, not the numerics again: the numerics
(v0.13 parity) are already exhaustively pinned by
``tests/baseline/regression_compare.py`` against the frozen golden fixtures
(118 headless + 284 real-board selftest vectors, plus the 11-pair batch
report), which this session re-ran and left passing unchanged, and by
``tests/test_solver.py`` / ``tests/test_geometry.py`` for the package side.
What is unique to this module:

    * the facade's solver/geometry names really are the package's objects,
      not look-alike copies (ARCH-006's "one dispatcher");
    * the legacy dispatcher (``network_resistance``) actually routes through
      ``pathminer.core.solver.two_terminal_resistance`` and the dense/sparse
      backends still agree on the same network through that route;
    * the aggregate ``--selftest`` and the split module tests report the
      same acceptance-vector identities (ARCH-010);
    * the generated single-file build has no import-time dependency on the
      ``pathminer`` package and passes the same aggregate self-test as the
      split package (BASE-004).
"""
from __future__ import annotations

import importlib.util
import re
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

from pathminer.core import geometry as pm_geometry
from pathminer.core import solver as pm_solver

REPO_ROOT = Path(__file__).resolve().parent.parent
FACADE_PATH = REPO_ROOT / "tools" / "pcb_trace_resistance.py"
BUILD_SCRIPT_PATH = REPO_ROOT / "tools" / "build_single_file.py"

# Report-line parser matching selftest()'s own print format
# ("  [PASS] <name>  got <g>  want <w>"); see tools/pcb_trace_resistance.py.
_REPORT_LINE = re.compile(r"\[(PASS|FAIL)\]\s+(.*?)\s{2,}got\b")

# Acceptance-vector prefixes that Session 04 split into pathminer.core module
# tests (see tests/test_solver.py / tests/test_geometry.py docstrings and
# ".ai/handoffs/Session_04_Claude.md"). ARCH-010's Done-when is that the
# aggregate --selftest and these module tests report the same identities.
MODULE_SPLIT_VECTOR_PREFIXES = ("V11", "V13", "V14")


def _load_module_from_path(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def facade():
    """The legacy compatibility facade, loaded as a module.

    Loaded from its file path (``tools/`` is not a package) rather than run
    as ``__main__``, so nothing under ``if __name__ == "__main__":`` runs."""
    return _load_module_from_path("pcb_trace_resistance_facade", FACADE_PATH)


@pytest.fixture(scope="module")
def build_single_file():
    """``tools/build_single_file.py``, loaded as a module (for generate_source())."""
    return _load_module_from_path("build_single_file", BUILD_SCRIPT_PATH)


def _selftest_vectors(facade_module, board_path=None):
    """Run selftest(verbose=True, ...) and parse its printed vectors.

    Returns (failures, [(name, status), ...]). Only the pass/fail identity is
    parsed, never the got/want text: a few vectors (V19, V23) legitimately
    print a fresh temp-directory path on every run, which is exactly why
    ``tests/baseline/regression_compare.py`` normalizes those fields before
    comparing against a golden fixture instead of comparing raw text."""
    import io
    from contextlib import redirect_stdout

    buf = io.StringIO()
    with redirect_stdout(buf):
        failures = facade_module.selftest(verbose=True, board_path=board_path)
    vectors = [(m.group(2).strip(), m.group(1)) for m in _REPORT_LINE.finditer(buf.getvalue())]
    return failures, vectors


# ---------------------------------------------------------------------------
# ARCH-006: one solver dispatcher, not a duplicate copy
# ---------------------------------------------------------------------------


def test_facade_solver_primitives_are_the_pathminer_core_objects(facade):
    """The facade's solver names are the package's objects (``is``), not
    look-alike reimplementations - the "one dispatcher" ARCH-006 requires."""
    assert facade._solve_dense is pm_solver.solve_dense
    assert facade.solve_cg is pm_solver.solve_cg
    assert facade._solve_scipy is pm_solver.solve_scipy
    assert facade.calibrate_solver is pm_solver.calibrate_solver
    assert facade.estimate_seconds is pm_solver.estimate_seconds
    assert facade.HAVE_SCIPY == pm_solver.HAVE_SCIPY
    assert facade.DENSE_NODE_LIMIT == pm_solver.DENSE_NODE_LIMIT == 400


def test_network_resistance_routes_through_two_terminal_resistance(facade):
    """The legacy dispatcher (``network_resistance``) actually calls
    ``pathminer.core.solver.two_terminal_resistance`` rather than only having
    the same answer by coincidence."""
    adj = {}
    for u, v, r in (("A", "B", 1.0), ("B", "C", 2.0), ("C", "D", 3.0)):
        d = {"r": r}
        adj.setdefault(u, []).append((v, d))
        adj.setdefault(v, []).append((u, d))
    rfun = lambda d: d["r"]  # noqa: E731

    with patch.object(pm_solver, "two_terminal_resistance",
                      wraps=pm_solver.two_terminal_resistance) as spy:
        result = facade.network_resistance(adj, "A", "D", rfun)

    assert result == pytest.approx(6.0, abs=1e-12)   # V11 "series 1+2+3"
    spy.assert_called_once()
    (edges, src, dst), kwargs = spy.call_args.args, spy.call_args.kwargs
    assert (src, dst) == ("A", "D")
    assert sorted(edges) == sorted([("A", "B", 1.0), ("B", "C", 2.0), ("C", "D", 3.0)])
    assert kwargs["backend"] == "dense"          # 4 nodes <= DENSE_NODE_LIMIT


def test_network_resistance_dense_and_sparse_backends_agree(facade):
    """ARCH-006's Done-when ("backend agreement is asserted on the same
    networks"), demonstrated through the legacy dispatcher itself: forcing
    the dense_limit down below the node count on the *same* adjacency picks
    the sparse path instead, and the two must agree (V11 unbalanced bridge,
    hand-checked value 2.3943661971830985)."""
    adj = {}
    for u, v, r in (("A", "B", 1.0), ("A", "C", 2.0), ("B", "D", 3.0),
                    ("C", "D", 4.0), ("B", "C", 5.0)):
        d = {"r": r}
        adj.setdefault(u, []).append((v, d))
        adj.setdefault(v, []).append((u, d))
    rfun = lambda d: d["r"]  # noqa: E731

    dense = facade.network_resistance(adj, "A", "D", rfun)
    sparse = facade.network_resistance(adj, "A", "D", rfun, dense_limit=1)

    assert dense == pytest.approx(2.3943661971830985, abs=1e-10)
    assert sparse == pytest.approx(dense, abs=1e-9)


def test_network_resistance_raises_on_a_disconnected_graph(facade):
    """Failure-path regression: an unreachable endpoint still raises (v0.13
    raised a bare 'singular network matrix' / KeyError inconsistently across
    backends; the shared pathminer.core.solver._prepare now raises a named
    ValueError on every backend - see ADR-010 and Session 04's handoff)."""
    adj = {}
    for u, v in (("A", "B"), ("X", "Y")):
        d = {"r": 1.0}
        adj.setdefault(u, []).append((v, d))
        adj.setdefault(v, []).append((u, d))
    rfun = lambda d: d["r"]  # noqa: E731

    with pytest.raises(ValueError):
        facade.network_resistance(adj, "A", "X", rfun)


# ---------------------------------------------------------------------------
# Geometry helpers: also one source of truth, not a duplicate copy
# ---------------------------------------------------------------------------


def test_facade_geometry_helpers_are_the_pathminer_core_objects(facade):
    assert facade._pt_in_poly is pm_geometry.point_in_polygon
    assert facade._seg_poly_crossings is pm_geometry.segment_polygon_crossings
    assert facade._dist_to_poly is pm_geometry.distance_to_polygon
    assert facade._principal_axis is pm_geometry.principal_axis
    assert facade.cluster_vias is pm_geometry.cluster_points
    assert facade.via_array_summary is pm_geometry.cluster_summary
    assert facade.clip_track_to_pour is pm_geometry.clip_segment_to_polygon
    assert facade._arc_length_mm is pm_geometry.arc_length


# ---------------------------------------------------------------------------
# ARCH-010: aggregate --selftest and the split module tests agree on identity
# ---------------------------------------------------------------------------


def test_aggregate_selftest_matches_the_headless_golden_vector_count(facade):
    """Pin against tests/baseline/fixtures/headless_118_selftest.json (118
    vectors, all PASS) so a facade wiring regression is caught here too, not
    only by the separate regression_compare.py run."""
    failures, vectors = _selftest_vectors(facade, board_path=None)
    assert failures == []
    assert len(vectors) == 118
    assert all(status == "PASS" for _name, status in vectors)


def test_aggregate_selftest_reports_the_module_split_vector_identities(facade):
    """ARCH-010 Done-when: "module tests and the aggregate --selftest report
    the same acceptance-vector identities." V11/V20 (tests/test_solver.py)
    and V13/V14 (tests/test_geometry.py) are the vectors Session 04 split
    into pathminer.core module tests; the aggregate selftest must still name
    and pass every one of them (V20 itself only runs given a board matching
    v0.13's small hand-built reference board, which is not part of this
    repository's fixtures - see tools/pcb_trace_resistance.py's own V20
    docstring and tests/baseline/README.md; V11/V13/V14 run headless)."""
    _failures, vectors = _selftest_vectors(facade, board_path=None)
    names_by_prefix = {}
    for name, status in vectors:
        prefix = name.split(" ", 1)[0]
        names_by_prefix.setdefault(prefix, []).append(status)

    for prefix in MODULE_SPLIT_VECTOR_PREFIXES:
        matched = names_by_prefix.get(prefix)
        assert matched, f"aggregate --selftest reports no {prefix} vectors"
        assert all(status == "PASS" for status in matched)


# ---------------------------------------------------------------------------
# BASE-004: generated single-file distribution, same aggregate self-test
# ---------------------------------------------------------------------------


def test_generated_single_file_has_no_pathminer_package_dependency(build_single_file):
    source = build_single_file.generate_source()
    compile(source, "<generated single file>", "exec")   # must be valid Python
    # An actual import statement, not merely a mention in a comment (this
    # module's own generated header comment names the source files it
    # inlined, e.g. "from pathminer/core/geometry.py").
    assert not re.search(r"^\s*(import pathminer\b|from pathminer\b)", source, re.MULTILINE)
    assert build_single_file.BOOTSTRAP_BEGIN not in source
    assert build_single_file.BOOTSTRAP_END not in source
    # The inlined pathminer.core source is present, not merely referenced:
    assert "def two_terminal_resistance(" in source
    assert "def point_in_polygon(" in source


def test_build_single_file_check_passes(tmp_path):
    """BASE-004's Done-when, run exactly as the session prompt's verification
    command does: ``python3 tools/build_single_file.py --check``."""
    result = subprocess.run(
        [sys.executable, str(BUILD_SCRIPT_PATH), "--check"],
        capture_output=True, text=True, cwd=REPO_ROOT,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "PASS" in result.stdout
