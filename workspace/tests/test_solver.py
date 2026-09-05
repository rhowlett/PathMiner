# v0.1
"""Tests for pathminer.core.solver.

Session 04 (BASE-005 closure; ARCH-006 backend slice). These port the
network-solver acceptance vectors from v0.13's headless selftest
(``tools/pcb_trace_resistance.py::selftest``) unchanged, retaining the
original vector IDs so behavior stays auditable against the v0.13 baseline
(ARCH-010):

    V11 — synthetic two-terminal topologies with hand-checkable answers.
    V14 — the shunt-array vector that separates a ladder from a lump.
    V20 — solver backend agreement and the calibration/time forecast.

The V11/V20 networks are additionally run through every available backend
(dense, pure-Python CG, and, when installed, SciPy) and asserted to agree on
the same network — the ARCH-006 "backend agreement is asserted on the same
networks" Done-when clause, contributed here as the backend slice.
"""

from __future__ import annotations

import math

import pytest

from pathminer.core.solver import (
    DENSE_NODE_LIMIT,
    HAVE_SCIPY,
    calibrate_solver,
    estimate_seconds,
    solve_cg,
    solve_dense,
    solve_scipy,
    two_terminal_resistance,
)

# ---------------------------------------------------------------------------
# V11 synthetic topologies: (id, edges, src, dst, expected, tolerance)
# Tolerances are v0.13's own per-vector selftest tolerances.
# ---------------------------------------------------------------------------

V11_CASES = [
    ("V11 series 1+2+3",
     [("A", "B", 1), ("B", "C", 2), ("C", "D", 3)], "A", "D", 6.0, 1e-12),
    ("V11 parallel 2||3",
     [("A", "B", 2), ("A", "B", 3)], "A", "B", 1.2, 1e-12),
    ("V11 1||(2+3)",
     [("A", "B", 1), ("A", "C", 2), ("C", "B", 3)], "A", "B", 5.0 / 6.0, 1e-12),
    ("V11 unbalanced bridge",
     [("A", "B", 1), ("A", "C", 2), ("B", "D", 3), ("C", "D", 4), ("B", "C", 5)],
     "A", "D", 2.3943661971830985, 1e-10),
    ("V11 balanced bridge ignores bridge",
     [("A", "B", 1), ("A", "C", 1), ("B", "D", 2), ("C", "D", 2), ("B", "C", 7)],
     "A", "D", 1.5, 1e-12),
    ("V11 stub carries nothing",
     [("A", "B", 1), ("B", "C", 2), ("B", "S", 99)], "A", "C", 3.0, 1e-12),
    ("V11 ten 10-ohm in parallel",
     [("A", "B", 10.0)] * 10, "A", "B", 1.0, 1e-12),
]


@pytest.mark.parametrize("name,edges,src,dst,expected,tol",
                         V11_CASES, ids=[c[0] for c in V11_CASES])
def test_v11_dense_matches_hand_answer(name, edges, src, dst, expected, tol):
    # The default "auto" backend routes these tiny graphs to the dense solve.
    assert two_terminal_resistance(edges, src, dst) == pytest.approx(expected, abs=tol)
    assert two_terminal_resistance(edges, src, dst, backend="dense") == \
        pytest.approx(expected, abs=tol)


@pytest.mark.parametrize("name,edges,src,dst,expected,tol",
                         V11_CASES, ids=[c[0] for c in V11_CASES])
def test_v11_cg_matches_hand_answer(name, edges, src, dst, expected, tol):
    assert two_terminal_resistance(edges, src, dst, backend="cg") == \
        pytest.approx(expected, abs=1e-7)


@pytest.mark.skipif(not HAVE_SCIPY, reason="SciPy not installed")
@pytest.mark.parametrize("name,edges,src,dst,expected,tol",
                         V11_CASES, ids=[c[0] for c in V11_CASES])
def test_v11_scipy_matches_hand_answer(name, edges, src, dst, expected, tol):
    assert two_terminal_resistance(edges, src, dst, backend="scipy") == \
        pytest.approx(expected, abs=1e-7)


@pytest.mark.parametrize("name,edges,src,dst,expected,tol",
                         V11_CASES, ids=[c[0] for c in V11_CASES])
def test_v11_backends_agree(name, edges, src, dst, expected, tol):
    """ARCH-006: every available backend agrees on the same network."""
    dense = two_terminal_resistance(edges, src, dst, backend="dense")
    cg = two_terminal_resistance(edges, src, dst, backend="cg")
    assert dense == pytest.approx(cg, abs=1e-9)
    if HAVE_SCIPY:
        scipy_r = two_terminal_resistance(edges, src, dst, backend="scipy")
        assert dense == pytest.approx(scipy_r, abs=1e-9)
        assert cg == pytest.approx(scipy_r, abs=1e-9)


# ---------------------------------------------------------------------------
# V14 shunt array: one centroid rung gives no parallel benefit; two do.
# ---------------------------------------------------------------------------


def _shunt(rungs_at):
    e = []
    for lay in ("A", "B"):
        for u0, u1 in zip([0.0, 1.0, 2.0, 3.0], [1.0, 2.0, 3.0, 4.0]):
            e.append(((lay, u0), (lay, u1), 1.0))
    for u in rungs_at:
        e.append((("A", u), ("B", u), 0.1))
    return two_terminal_resistance(e, ("A", 0.0), ("A", 4.0))


def test_v14_single_centroid_rung_gives_no_parallel_benefit():
    assert _shunt([2.0]) == pytest.approx(4.0, abs=1e-9)


def test_v14_two_separated_rungs_do_help():
    assert _shunt([1.0, 3.0]) < 4.0 - 1e-9


# ---------------------------------------------------------------------------
# V20 backend agreement on the hand answer 3||6 and the time forecast.
# ---------------------------------------------------------------------------

V20_EDGES = [((0, 0), (0, 1), 1.0), ((0, 1), (0, 2), 2.0), ((0, 0), (0, 2), 6.0)]


def test_v20_dense_hand_answer_3_parallel_6():
    # (1 + 2) || 6 = 3 || 6 = 2.0
    assert two_terminal_resistance(V20_EDGES, (0, 0), (0, 2), backend="dense") == \
        pytest.approx(2.0, abs=1e-9)


@pytest.mark.skipif(not HAVE_SCIPY, reason="SciPy not installed")
def test_v20_scipy_and_python_solvers_agree():
    rs, _n1, _i1 = solve_scipy(V20_EDGES, (0, 0), (0, 2))
    rp, _n2, _i2 = solve_cg(V20_EDGES, (0, 0), (0, 2))
    assert rs == pytest.approx(rp, abs=1e-9)      # V20 scipy and python agree
    assert rs == pytest.approx(2.0, abs=1e-9)     # V20 against the hand answer 3||6


def test_v20_calibration_is_sane():
    c = calibrate_solver()
    assert c["a"] > 0                             # positive rate
    assert 0.8 <= c["b"] <= 3.0                   # exponent is clamped sane
    assert c["backend"] in ("scipy", "python")


def test_v20_estimate_grows_with_node_count():
    assert estimate_seconds(4000) > estimate_seconds(400)


# ---------------------------------------------------------------------------
# Backend return signatures (metadata carried alongside the resistance).
# ---------------------------------------------------------------------------


def test_solve_cg_returns_resistance_nodes_iterations():
    r, n, its = solve_cg(V20_EDGES, (0, 0), (0, 2))
    assert r == pytest.approx(2.0, abs=1e-7)
    assert n == 3
    assert its >= 1


@pytest.mark.skipif(not HAVE_SCIPY, reason="SciPy not installed")
def test_solve_scipy_returns_resistance_nodes_iterations():
    r, n, its = solve_scipy(V20_EDGES, (0, 0), (0, 2))
    assert r == pytest.approx(2.0, abs=1e-9)
    assert n == 3
    assert its == 1


# ---------------------------------------------------------------------------
# Dispatcher / compiled-acceleration threshold (BASE-005 documentation).
# ---------------------------------------------------------------------------


def test_dense_node_limit_is_400():
    # The documented dense/sparse crossover (ADR-010). A change here is a
    # deliberate threshold change, not incidental.
    assert DENSE_NODE_LIMIT == 400


def _grid_edges(side):
    e = []
    for r in range(side):
        for c in range(side):
            if c + 1 < side:
                e.append(((r, c), (r, c + 1), 1.0))
            if r + 1 < side:
                e.append(((r, c), (r + 1, c), 1.0))
    return e


def test_auto_uses_dense_at_or_below_limit():
    # A 20x20 grid has 400 nodes == limit -> dense; a 21x21 grid has 441 > 400
    # -> sparse. Both must return the same resistance across backends.
    small = _grid_edges(20)                        # 400 nodes
    big = _grid_edges(21)                          # 441 nodes
    r_small_auto = two_terminal_resistance(small, (0, 0), (19, 19))
    r_small_dense = two_terminal_resistance(small, (0, 0), (19, 19), backend="dense")
    assert r_small_auto == pytest.approx(r_small_dense, abs=1e-6)

    r_big_auto = two_terminal_resistance(big, (0, 0), (20, 20))
    r_big_cg = two_terminal_resistance(big, (0, 0), (20, 20), backend="cg")
    assert r_big_auto == pytest.approx(r_big_cg, abs=1e-6)


def test_custom_dense_limit_forces_sparse_path():
    # Lowering the limit pushes a small graph onto the sparse path; the answer
    # must not change.
    r_auto = two_terminal_resistance(V20_EDGES, (0, 0), (0, 2))
    r_forced_sparse = two_terminal_resistance(V20_EDGES, (0, 0), (0, 2), dense_limit=1)
    assert r_auto == pytest.approx(r_forced_sparse, abs=1e-7)


# ---------------------------------------------------------------------------
# Failure modes (named errors — acceptance gate).
# ---------------------------------------------------------------------------


def test_dense_singular_network_raises():
    # dst sits in a disconnected component -> singular grounded matrix.
    edges = [("A", "B", 1.0), ("C", "D", 1.0)]
    with pytest.raises(ValueError, match="singular network matrix"):
        two_terminal_resistance(edges, "A", "D", backend="dense")


def test_dense_endpoint_not_in_graph_raises():
    with pytest.raises(ValueError, match="endpoint not in graph"):
        two_terminal_resistance([("A", "B", 1.0)], "Z", "B", backend="dense")


def test_unknown_backend_raises():
    with pytest.raises(ValueError, match="unknown solver backend"):
        two_terminal_resistance([("A", "B", 1.0)], "A", "B", backend="wishful")


@pytest.mark.skipif(not HAVE_SCIPY, reason="SciPy not installed")
def test_scipy_disconnected_endpoints_raise():
    edges = [("A", "B", 1.0), ("C", "D", 1.0)]
    with pytest.raises(ValueError, match="not connected"):
        solve_scipy(edges, "A", "D")


def test_solve_dense_singular_matrix_raises():
    with pytest.raises(ValueError, match="singular network matrix"):
        solve_dense([[1.0, 1.0], [1.0, 1.0]], [1.0, 2.0])
