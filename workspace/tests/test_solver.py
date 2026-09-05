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
    # The raw dense primitive still guards a genuinely singular matrix.
    with pytest.raises(ValueError, match="singular network matrix"):
        solve_dense([[1.0, 1.0], [1.0, 1.0]], [1.0, 2.0])


# ---------------------------------------------------------------------------
# Cross-backend consistency (coordinator CHANGES_REQUESTED repair).
#
# Every edge-list backend now routes through the shared validation/component
# handling in ``pathminer.core.solver._prepare``, so dense, CG, SciPy, and the
# ``auto`` dispatcher fail and succeed on exactly the same inputs. Each test
# below asserts the SAME outcome across every available backend. v0.13 was
# inconsistent here: ``_solve_scipy`` validated and restricted to the source's
# component, but ``solve_cg`` returned a plausible-but-wrong value for a
# disconnected or non-converged system and the dense path raised a bare
# ``singular network matrix`` (or ``KeyError``) on unrelated components,
# ``src == dst``, or a missing endpoint.
# ---------------------------------------------------------------------------

AVAILABLE_BACKENDS = ["dense", "cg"] + (["scipy"] if HAVE_SCIPY else [])


def _resistance_each_backend(edges, src, dst):
    """Return {backend: resistance} for every available backend."""
    return {b: two_terminal_resistance(edges, src, dst, backend=b)
            for b in AVAILABLE_BACKENDS}


def _assert_all_backends_raise(edges, src, dst, match):
    """Assert every available backend raises ValueError matching *match*."""
    for backend in AVAILABLE_BACKENDS:
        with pytest.raises(ValueError, match=match):
            two_terminal_resistance(edges, src, dst, backend=backend)


def test_disconnected_endpoints_raise_on_every_backend():
    # dst is in a different component from src: no finite resistance exists, so
    # no backend may return a value (v0.13's CG would have returned garbage).
    edges = [("A", "B", 1.0), ("C", "D", 1.0)]
    _assert_all_backends_raise(edges, "A", "D", "not connected")
    _assert_all_backends_raise(edges, "A", "D", "not connected")  # backend="auto"
    with pytest.raises(ValueError, match="not connected"):
        two_terminal_resistance(edges, "A", "D")            # auto too


def test_unrelated_component_is_ignored_consistently():
    # A stray disconnected island must not change the answer or crash any
    # backend; the src<->dst resistance is solved over src's component alone.
    base = [("A", "B", 1.0), ("B", "C", 1.0)]               # A..C = 2.0
    stray = base + [("X", "Y", 5.0), ("Y", "Z", 7.0)]       # unrelated island
    got = _resistance_each_backend(stray, "A", "C")
    for backend, r in got.items():
        assert r == pytest.approx(2.0, abs=1e-9), f"{backend} = {r}"
    # And the stray island leaves the answer identical to the clean network.
    clean = _resistance_each_backend(base, "A", "C")
    for backend in AVAILABLE_BACKENDS:
        assert got[backend] == pytest.approx(clean[backend], abs=1e-12)


def test_src_equals_dst_raises_on_every_backend():
    # A self-resistance query is degenerate (v0.13 raised a bare KeyError);
    # every backend now raises the same named error rather than returning 0.0.
    _assert_all_backends_raise([("A", "B", 1.0)], "A", "A", "same node")


def test_non_positive_resistances_are_dropped_consistently():
    # r <= 0 edges are dropped by every backend (v0.13 behavior): adding a
    # zero-ohm and a negative parallel edge must not change 2||3 = 1.2.
    clean = [("A", "B", 2.0), ("A", "B", 3.0)]
    with_bad = clean + [("A", "B", 0.0), ("A", "B", -4.0)]
    got = _resistance_each_backend(with_bad, "A", "B")
    for backend, r in got.items():
        assert r == pytest.approx(1.2, abs=1e-9), f"{backend} = {r}"


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), float("-inf")])
def test_non_finite_resistance_raises_on_every_backend(bad):
    # A NaN/inf resistance is corrupt input. v0.13's dense path poisoned the
    # matrix with 1/NaN while its sparse path silently dropped it; now every
    # backend rejects it with the same named error.
    edges = [("A", "B", 1.0), ("B", "C", bad)]
    _assert_all_backends_raise(edges, "A", "C", "non-finite resistance")


def test_missing_endpoint_raises_on_every_backend():
    # An endpoint that appears on no edge is a caller error, consistently named.
    _assert_all_backends_raise([("A", "B", 1.0)], "Z", "B", "endpoint not in graph")
    _assert_all_backends_raise([("A", "B", 1.0)], "A", "Z", "endpoint not in graph")


def test_cg_non_convergence_raises_not_returns():
    # With maxit far too small the residual never reaches tol; CG must raise
    # instead of returning the last (wrong) iterate. dense/scipy have no
    # iteration limit and still solve the same network.
    edges = _grid_edges(6)                                  # 36-node grid
    with pytest.raises(ValueError, match="did not converge"):
        solve_cg(edges, (0, 0), (5, 5), maxit=1)
    # The very same network solves cleanly on every backend at the default limit.
    got = _resistance_each_backend(edges, (0, 0), (5, 5))
    ref = got["dense"]
    for backend, r in got.items():
        assert r == pytest.approx(ref, abs=1e-6), f"{backend} = {r}"


def test_all_backends_agree_on_a_disconnected_diagnosis():
    # The three backends must not disagree on whether a system is solvable:
    # a disconnected network raises on all, a connected one returns on all.
    disconnected = [("A", "B", 1.0), ("C", "D", 1.0)]
    connected = [("A", "B", 1.0), ("B", "C", 1.0)]
    raised = 0
    for backend in AVAILABLE_BACKENDS:
        try:
            two_terminal_resistance(disconnected, "A", "D", backend=backend)
        except ValueError:
            raised += 1
    assert raised == len(AVAILABLE_BACKENDS)               # all raised, none returned
    got = _resistance_each_backend(connected, "A", "C")
    assert all(r == pytest.approx(2.0, abs=1e-9) for r in got.values())
