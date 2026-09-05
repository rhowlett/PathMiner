# v0.1
"""pathminer.core.solver — backend-independent two-terminal resistance solvers.

Session 04 (BASE-005 closure; ARCH-006 backend slice). This module extracts
the three numerical backends from PathMiner v0.13
(``tools/pcb_trace_resistance.py``) and consolidates them behind one
dispatcher, preserving numerical behavior:

    * ``solve_dense``   — Gauss-Jordan with partial pivoting (v0.13 ``_solve_dense``).
    * ``solve_cg``      — pure-Python Jacobi-preconditioned conjugate gradient
                          on the grounded Laplacian (v0.13 ``solve_cg``); the
                          fallback that is always available, including inside a
                          KiCad-bundled interpreter with no SciPy.
    * ``solve_scipy``   — the same nodal problem through SciPy's compiled
                          sparse ``spsolve`` when SciPy is installed (v0.13
                          ``_solve_scipy``); optional and opportunistic.

The three backends solve the *same* nodal problem (ground the source, inject
1 A at the sink, read the sink potential = two-terminal resistance) and must
agree on the same networks (ARCH-006 Done-when; asserted in
``tests/test_solver.py`` as the V11/V20 backend-agreement vectors).

Backend selection and the compiled-acceleration decision thresholds
------------------------------------------------------------------
``two_terminal_resistance`` is the single dispatcher. With ``backend="auto"``
(the default) it reproduces v0.13's crossover in ``network_resistance``:

    * networks with at most ``DENSE_NODE_LIMIT`` (400) nodes use the dense
      Gauss-Jordan solve — O(n^3) but tiny for point-to-point / ladder graphs;
    * larger networks (meshed pours) fall through to the sparse path, which is
      SciPy's ``spsolve`` when available and the pure-Python CG otherwise.

``calibrate_solver`` / ``estimate_seconds`` learn this machine's cost model
``t = a * nodes^b`` from two synthetic grids and forecast solve time; this is
the profiling hook that ADR-010 (see ``documents/adr/ADR-010.md``) requires
before any compiled (C/C++) rewrite is considered. The pure-Python fallback
remains supported per ADR-003.

Layer contract (ARCH-002): pure mathematics — no KiCad, Qt, wx, or file I/O,
and no upward pathminer imports. Inputs are backend-neutral edge lists
``[(u, v, r), ...]`` of hashable node keys and positive resistances; the
network layer (Session 07) is responsible for building them (from an
adjacency map, merging equipotential groups, pricing edges). NumPy/SciPy are
optional accelerators, not a persistence or I/O dependency.
"""

from __future__ import annotations

import math

__all__ = [
    "HAVE_SCIPY",
    "DENSE_NODE_LIMIT",
    "solve_dense",
    "solve_cg",
    "solve_scipy",
    "two_terminal_resistance",
    "calibrate_solver",
    "estimate_seconds",
]


try:                                            # optional, never required
    import numpy as _np
    import scipy.sparse as _sp
    import scipy.sparse.linalg as _spl
    HAVE_SCIPY = True
except ImportError:                             # pure-Python fallback below
    HAVE_SCIPY = False


# Networks with more than this many nodes use the sparse path instead of the
# dense O(n^3) Gauss-Jordan solve. This is the dense/sparse crossover that
# v0.13 named in ``network_resistance``; it is also the first of the
# compiled-acceleration decision thresholds documented in ADR-010.
DENSE_NODE_LIMIT = 400


# --------------------------------------------------------------------------
# Dense backend (v0.13 ``_solve_dense``)
# --------------------------------------------------------------------------


def solve_dense(matrix, rhs):
    """Solve ``matrix @ x = rhs`` by Gauss-Jordan with partial pivoting.

    Ported verbatim from v0.13 ``_solve_dense``. Networks routed here are tens
    of nodes. Raises ``ValueError('singular network matrix')`` when the system
    is singular (e.g. the sink is unreachable from the grounded source).
    """
    n = len(rhs)
    M = [list(row) + [rhs[i]] for i, row in enumerate(matrix)]
    for c in range(n):
        p = max(range(c, n), key=lambda r: abs(M[r][c]))
        if abs(M[p][c]) < 1e-18:
            raise ValueError("singular network matrix")
        M[c], M[p] = M[p], M[c]
        pv = M[c][c]
        for r in range(n):
            if r == c:
                continue
            f = M[r][c] / pv
            if f:
                for k in range(c, n + 1):
                    M[r][k] -= f * M[c][k]
    return [M[i][n] / M[i][i] for i in range(n)]


# --------------------------------------------------------------------------
# Pure-Python sparse backend (v0.13 ``solve_cg``) — always available
# --------------------------------------------------------------------------


def solve_cg(edges, src, dst, tol=1e-13, maxit=50000):
    """Two-terminal resistance by Jacobi-preconditioned CG on the grounded Laplacian.

    Ported verbatim from v0.13 ``solve_cg``. Returns ``(resistance, node_count,
    iterations)``. Equipotential groups must already be merged by the caller -
    tiny tie resistors destroy the conditioning.
    """
    nodes = sorted({u for u, _v, _r in edges} | {v for _u, v, _r in edges}, key=str)
    idx = {n: i for i, n in enumerate(nodes)}
    n = len(nodes)
    nbr = [[] for _ in range(n)]
    diag = [0.0] * n
    for u, v, r in edges:
        if r <= 0 or u == v:
            continue
        g = 1.0 / r
        iu, iv = idx[u], idx[v]
        nbr[iu].append((iv, g)); nbr[iv].append((iu, g))
        diag[iu] += g; diag[iv] += g
    gnd = idx[src]

    def mv(x):
        y = [0.0] * n
        for i in range(n):
            if i == gnd:
                continue
            s = diag[i] * x[i]
            for j, g in nbr[i]:
                if j != gnd:
                    s -= g * x[j]
            y[i] = s
        return y

    b = [0.0] * n; b[idx[dst]] = 1.0; b[gnd] = 0.0
    x = [0.0] * n
    r = b[:]
    M = [1.0 / diag[i] if diag[i] > 0 else 1.0 for i in range(n)]
    z = [M[i] * r[i] for i in range(n)]; z[gnd] = 0.0
    p = z[:]; rz = sum(r[i] * z[i] for i in range(n))
    its = 0
    for its in range(1, maxit + 1):
        Ap = mv(p)
        pAp = sum(p[i] * Ap[i] for i in range(n))
        if abs(pAp) < 1e-300:
            break
        a = rz / pAp
        for i in range(n):
            x[i] += a * p[i]; r[i] -= a * Ap[i]
        r[gnd] = 0.0
        if max(abs(v) for v in r) < tol:
            break
        z = [M[i] * r[i] for i in range(n)]; z[gnd] = 0.0
        rz2 = sum(r[i] * z[i] for i in range(n))
        beta = rz2 / rz; rz = rz2
        for i in range(n):
            p[i] = z[i] + beta * p[i]
    return x[idx[dst]], len(nodes), its


# --------------------------------------------------------------------------
# Optional compiled sparse backend (v0.13 ``_solve_scipy``)
# --------------------------------------------------------------------------


def solve_scipy(edges, src, dst):
    """Same nodal problem through compiled sparse code when SciPy is installed.

    Ported verbatim from v0.13 ``_solve_scipy``. Returns ``(resistance,
    node_count, 1)``. Two to three orders of magnitude faster than the Python
    CG on meshed pours; the result must agree with it (V20). Raises
    ``RuntimeError`` if SciPy/NumPy are not installed and ``ValueError`` when
    the endpoints are not connected or the solve is not finite.
    """
    if not HAVE_SCIPY:
        raise RuntimeError("SciPy backend requested but scipy/numpy are not installed")
    nodes = sorted({u for u, _v, _r in edges} | {v for _u, v, _r in edges}, key=str)
    idx = {n: i for i, n in enumerate(nodes)}
    n = len(nodes)
    rows, cols, vals = [], [], []
    for u, v, r in edges:
        if r <= 0 or u == v:
            continue
        g = 1.0 / r
        iu, iv = idx[u], idx[v]
        rows += [iu, iv, iu, iv]
        cols += [iu, iv, iv, iu]
        vals += [g, g, -g, -g]
    # A disconnected graph makes the grounded Laplacian singular. scipy returns
    # NaNs with only a warning on stderr, so check reachability first and fail
    # loudly instead of reporting a nonsense resistance.
    nbr = {}
    for u, v, r in edges:
        if r > 0 and u != v:
            nbr.setdefault(u, []).append(v)
            nbr.setdefault(v, []).append(u)
    seen_n, stack = {src}, [src]
    while stack:                                     # full component, not early exit
        cur = stack.pop()
        for nx in nbr.get(cur, ()):
            if nx not in seen_n:
                seen_n.add(nx); stack.append(nx)
    if dst not in seen_n:
        raise ValueError("endpoints are not connected")
    # Other components are still singular even when src and dst are connected,
    # so solve over the source's component alone.
    L = _sp.coo_matrix((vals, (rows, cols)), shape=(n, n)).tocsr()
    gnd = idx[src]
    comp = {idx[u] for u in seen_n}
    keep = [i for i in sorted(comp) if i != gnd]
    Lr = L[keep, :][:, keep].tocsc()
    b = _np.zeros(len(keep))
    pos = keep.index(idx[dst])
    b[pos] = 1.0
    x = _spl.spsolve(Lr, b)
    val = float(x[pos])
    if not math.isfinite(val):
        raise ValueError("nodal solve did not produce a finite resistance")
    return val, n, 1


# --------------------------------------------------------------------------
# Dispatcher (v0.13 ``network_resistance`` dense/sparse crossover, on edges)
# --------------------------------------------------------------------------


def _dense_two_terminal(edges, src, dst):
    """Dense two-terminal resistance from an edge list.

    Reproduces v0.13 ``network_resistance``'s small-graph branch: ground
    *src*, inject 1 A at *dst*, and read ``V[dst]`` from the grounded
    conductance matrix solved by :func:`solve_dense`. Parallel edges between
    the same pair add in parallel; non-positive resistances are dropped.
    """
    nodes_all = sorted({u for u, _v, _r in edges} | {v for _u, v, _r in edges}, key=str)
    if src not in nodes_all or dst not in nodes_all:
        raise ValueError("endpoint not in graph")
    nodes = [n for n in nodes_all if n != src]        # src is ground, excluded
    idx = {n: i for i, n in enumerate(nodes)}
    size = len(nodes)
    G = [[0.0] * size for _ in range(size)]
    for u, v, r in edges:
        if r <= 0:
            continue
        g = 1.0 / r
        iu = idx.get(u)
        iv = idx.get(v)
        if iu is not None:
            G[iu][iu] += g
        if iv is not None:
            G[iv][iv] += g
        if iu is not None and iv is not None:
            G[iu][iv] -= g
            G[iv][iu] -= g
    inj = [0.0] * size
    inj[idx[dst]] = 1.0
    V = solve_dense(G, inj)
    return V[idx[dst]]


def two_terminal_resistance(edges, src, dst, backend="auto",
                            dense_limit=DENSE_NODE_LIMIT):
    """Two-terminal resistance of a network given as an edge list.

    *edges* is a sequence of ``(u, v, r)`` with hashable node keys and
    resistance ``r`` in ohms; *src* and *dst* are node keys. Returns the
    scalar resistance in ohms.

    *backend* selects the numerical backend and defaults to ``"auto"``:

        ``"auto"``   dense when the node count is at most *dense_limit*,
                     otherwise ``"scipy"`` if SciPy is installed else ``"cg"``
                     (this reproduces v0.13's ``network_resistance`` crossover);
        ``"dense"``  force the Gauss-Jordan solve;
        ``"cg"``     force the pure-Python conjugate-gradient solve;
        ``"scipy"``  force the compiled SciPy sparse solve.

    All backends solve the same nodal problem and agree within solver
    precision on the same network (ARCH-006).
    """
    node_count = len({u for u, _v, _r in edges} | {v for _u, v, _r in edges})
    if backend == "auto":
        backend = "dense" if node_count <= dense_limit else ("scipy" if HAVE_SCIPY else "cg")
    if backend == "dense":
        return _dense_two_terminal(edges, src, dst)
    if backend == "scipy":
        r, _n, _its = solve_scipy(edges, src, dst)
        return r
    if backend == "cg":
        r, _n, _its = solve_cg(edges, src, dst)
        return r
    raise ValueError(f"unknown solver backend: {backend!r}")


# --------------------------------------------------------------------------
# Calibration and time forecast (v0.13 ``calibrate_solver`` / ``estimate_seconds``)
# --------------------------------------------------------------------------


_CALIB = {}


def calibrate_solver():
    """Time two synthetic grids to learn this machine's ``t = a * nodes^b``.

    Ported verbatim from v0.13 ``calibrate_solver``. Cached; costs a fraction
    of a second the first time it is asked. Returned dict carries ``a``, ``b``,
    the active ``backend``, and the timing ``samples``. This is the profiling
    hook ADR-010 requires before compiled acceleration is considered.
    """
    if _CALIB:
        return _CALIB
    import time as _time
    pts = []
    for side in (12, 22):
        edges = []
        for r in range(side):
            for c in range(side):
                if c + 1 < side:
                    edges.append(((r, c), (r, c + 1), 1.0))
                if r + 1 < side:
                    edges.append(((r, c), (r + 1, c), 1.0))
        n = side * side
        t0 = _time.perf_counter()
        if HAVE_SCIPY:
            solve_scipy(edges, (0, 0), (side - 1, side - 1))
        else:
            solve_cg(edges, (0, 0), (side - 1, side - 1))
        pts.append((n, max(_time.perf_counter() - t0, 1e-6)))
    (n1, t1), (n2, t2) = pts
    b = math.log(t2 / t1) / math.log(n2 / n1) if n2 != n1 and t1 > 0 else 1.5
    b = min(max(b, 0.8), 3.0)
    a = t1 / (n1 ** b)
    _CALIB.update({"a": a, "b": b, "backend": "scipy" if HAVE_SCIPY else "python",
                   "samples": pts})
    return _CALIB


def estimate_seconds(nodes):
    """Forecast solve time for a network of *nodes* nodes from the calibration.

    Ported verbatim from v0.13 ``estimate_seconds``.
    """
    c = calibrate_solver()
    return c["a"] * (max(nodes, 2) ** c["b"])
