# v0.2
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

# Exact V13/V14 acceptance-vector identities split into
# tests/test_geometry.py / tests/test_solver.py (Session 04). Neither module
# keeps these names in an importable data structure (test_geometry.py's V13
# names live only in inline "# V13 ..." comments; test_solver.py's V14 names
# live only in its two test function names), so - unlike V11 below, which is
# imported directly from tests/test_solver.py's own V11_CASES - these are
# hand-transcribed from those comments and from the aggregate selftest's own
# chk() call sites. A rename or removal on either side without updating this
# list is exactly the drift test_aggregate_selftest_reports_the_module_split_
# vector_identities exists to catch.
EXPECTED_V13_NAMES = frozenset({
    "V13 point inside",
    "V13 point outside",
    "V13 point on edge counts as inside",
    "V13 pour length",
    "V13 pour width",
    "V13 pour aspect",
    "V13 axis is x",
    "V13 clip outside length",
    "V13 clip inside length",
    "V13 clusters found",
    "V13 array centroid",
    "V13 array extent",
})
EXPECTED_V14_NAMES = frozenset({
    "V14 single centroid rung gives no parallel benefit",
    "V14 two separated rungs do help",
})


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


@pytest.fixture(scope="module")
def test_solver_reference():
    """tests/test_solver.py, loaded as a module under its own name so pytest's
    own collection of that file (a separate sys.modules entry) is untouched.
    Used only to read its V11_CASES data, not to re-run its tests."""
    return _load_module_from_path("test_solver_reference", REPO_ROOT / "tests" / "test_solver.py")


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


def test_aggregate_selftest_reports_the_module_split_vector_identities(
        facade, test_solver_reference):
    """ARCH-010 Done-when: "module tests and the aggregate --selftest report
    the same acceptance-vector identities." Checked as an *exact* identity
    match, not merely a shared prefix, so a renamed, removed, or added vector
    on either side is caught: the aggregate --selftest's V11/V13/V14 names
    must equal exactly (as sets) the module tests' own vector identities
    (V11 imported directly from tests/test_solver.py's V11_CASES; V13/V14
    hand-transcribed from that file's and tests/test_geometry.py's inline
    "# V13 ..." comments and test function names, since neither keeps V13/V14
    identities in an importable data structure - see the module-level
    EXPECTED_V13_NAMES/EXPECTED_V14_NAMES comment).

    V20 (also tests/test_solver.py) is explicitly *not* checked here: its
    backend-agreement block in the aggregate selftest (``_v20``) only runs
    given a board with a '/SDA' net matching v0.13's small hand-built
    reference board, which no fixture in this repository provides (see
    tools/pcb_trace_resistance.py's own V20 code and
    tests/baseline/README.md, which already documents V20 as "Skipped (not
    the reference test board)" for both canonical suites, predating this
    session) - accounted for explicitly rather than silently ignored."""
    _failures, vectors = _selftest_vectors(facade, board_path=None)
    reported_status = dict(vectors)
    assert all(status == "PASS" for status in reported_status.values()), (
        "aggregate --selftest reported at least one FAIL vector")

    expected_v11 = frozenset(case[0] for case in test_solver_reference.V11_CASES)
    assert len(expected_v11) == 7, "unexpected V11_CASES count in tests/test_solver.py"

    expected_by_prefix = {
        "V11": expected_v11,
        "V13": EXPECTED_V13_NAMES,
        "V14": EXPECTED_V14_NAMES,
    }
    for prefix, expected in expected_by_prefix.items():
        reported = {name for name in reported_status if name.startswith(prefix + " ")}
        missing = expected - reported
        unexpected = reported - expected
        assert not missing and not unexpected, (
            f"{prefix} identities differ between the aggregate --selftest and "
            f"the module tests: missing from aggregate {sorted(missing)!r}, "
            f"unexpected in aggregate {sorted(unexpected)!r}")


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


def test_check_does_not_pass_when_both_sides_fail_identically(build_single_file):
    """Regression for a real bug found in coordinator review: ``check()``
    only compared the two runs *against each other*, so two runs that failed
    identically (e.g. both "0/1 checks passed", exit 1) agreed with each
    other and were reported as a false PASS. Each side must now be confirmed
    to actually pass on its own before any comparison happens."""
    fake_fail = subprocess.CompletedProcess(
        args=[], returncode=1,
        stdout=("  [FAIL] V1 something                                       "
                "got            0  want            1\n\n0/1 checks passed\n"),
        stderr="",
    )
    with patch.object(build_single_file, "_run_selftest", return_value=fake_fail):
        assert build_single_file.check(None) != 0


def test_check_fails_cleanly_on_an_unparseable_summary(build_single_file):
    """Regression: a missing/unparseable "N/N checks passed" summary must
    produce a clear failure (return 1), never a ``TypeError`` from unpacking
    ``None`` as ``passed, total = summary``."""
    fake_garbage = subprocess.CompletedProcess(
        args=[], returncode=1, stdout="not a selftest report at all\n", stderr="")
    with patch.object(build_single_file, "_run_selftest", return_value=fake_garbage):
        assert build_single_file.check(None) != 0   # must not raise TypeError


def test_check_fails_when_only_one_side_actually_passes(build_single_file):
    """The generated file must not be allowed to disagree with a passing
    split facade by itself also failing - both sides failing the same way is
    covered above; this covers one side passing and the other not."""
    real_split_result = subprocess.run(
        [sys.executable, str(FACADE_PATH), "--selftest"],
        capture_output=True, text=True, cwd=REPO_ROOT,
    )
    assert real_split_result.returncode == 0   # sanity: the split facade itself passes

    fake_single_fail = subprocess.CompletedProcess(
        args=[], returncode=1,
        stdout=("  [FAIL] V1 something                                       "
                "got            0  want            1\n\n0/1 checks passed\n"),
        stderr="",
    )

    def fake_run_selftest(script, board):
        return fake_single_fail if script != FACADE_PATH else real_split_result

    with patch.object(build_single_file, "_run_selftest", side_effect=fake_run_selftest):
        assert build_single_file.check(None) != 0
