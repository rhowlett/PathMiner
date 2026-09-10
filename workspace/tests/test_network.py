# v0.1
"""Tests for pathminer.core.network (Session 07, ARCH-004).

The common typed network is the object every builder emits and the solver
consumes. These tests cover:

    * ``from_edges`` + ``two_terminal`` reproducing the V11 hand answers, so the
      network layer agrees with ``pathminer.core.solver`` on the same graphs
      (ARCH-006 dispatcher-prerequisite contribution);
    * equipotential ``merge`` collapsing nodes in ``edge_list`` (v0.13's "merge
      the nodes rather than joining them with a near-zero resistor" contract)
      and producing the right parallel/series results;
    * ``two_terminal`` resolving a pre-merge node key through ``canonical``;
    * the ``TwoTerminalResult`` / ``Provenance`` records;
    * named failure modes propagating unchanged from the solver.
"""

from __future__ import annotations

import pytest

from pathminer.core.network import (
    Edge,
    Provenance,
    ResistorNetwork,
    TwoTerminalResult,
)
from pathminer.core.solver import HAVE_SCIPY, two_terminal_resistance

# ---------------------------------------------------------------------------
# from_edges + two_terminal agree with the solver on the V11 hand answers.
# ---------------------------------------------------------------------------

V11_CASES = [
    ("series 1+2+3",
     [("A", "B", 1), ("B", "C", 2), ("C", "D", 3)], "A", "D", 6.0),
    ("parallel 2||3",
     [("A", "B", 2), ("A", "B", 3)], "A", "B", 1.2),
    ("1||(2+3)",
     [("A", "B", 1), ("A", "C", 2), ("C", "B", 3)], "A", "B", 5.0 / 6.0),
    ("unbalanced bridge",
     [("A", "B", 1), ("A", "C", 2), ("B", "D", 3), ("C", "D", 4), ("B", "C", 5)],
     "A", "D", 2.3943661971830985),
    ("ten 10-ohm in parallel",
     [("A", "B", 10.0)] * 10, "A", "B", 1.0),
]


@pytest.mark.parametrize("name,edges,src,dst,expected",
                         V11_CASES, ids=[c[0] for c in V11_CASES])
def test_from_edges_two_terminal_matches_hand_answer(name, edges, src, dst, expected):
    net = ResistorNetwork.from_edges(edges, name="v11")
    result = net.two_terminal(src, dst)
    assert isinstance(result, TwoTerminalResult)
    assert result.resistance == pytest.approx(expected, abs=1e-9)


@pytest.mark.parametrize("name,edges,src,dst,expected",
                         V11_CASES, ids=[c[0] for c in V11_CASES])
def test_network_matches_raw_solver(name, edges, src, dst, expected):
    """The network must not diverge from the raw dispatcher on the same edges."""
    net = ResistorNetwork.from_edges(edges)
    raw = two_terminal_resistance(net.edge_list(), src, dst)
    assert net.two_terminal(src, dst).resistance == pytest.approx(raw, abs=1e-12)


@pytest.mark.parametrize("backend", ["dense", "cg"] + (["scipy"] if HAVE_SCIPY else []))
def test_backend_passthrough_agrees(backend):
    edges = [("A", "B", 1), ("A", "C", 2), ("C", "B", 3)]
    net = ResistorNetwork.from_edges(edges)
    result = net.two_terminal("A", "B", backend=backend)
    assert result.resistance == pytest.approx(5.0 / 6.0, abs=1e-7)
    assert result.backend == backend


# ---------------------------------------------------------------------------
# Equipotential merge.
# ---------------------------------------------------------------------------


def test_merge_collapses_nodes_in_edge_list():
    net = ResistorNetwork()
    net.add_edge("A", "B", 1.0)
    net.add_edge("C", "D", 2.0)
    net.merge("B", "C")                       # B and C are the same copper
    canon = {net.canonical(n) for n in ("A", "B", "C", "D")}
    assert net.canonical("B") == net.canonical("C")
    # 3 distinct electrical nodes remain (A, B==C, D); 2 edges, none collapsed.
    assert net.node_count == 3
    assert net.edge_count == 2
    assert len(canon) == 3
    # A..D is now a 1 + 2 series = 3 ohm chain through the merged node.
    assert net.two_terminal("A", "D").resistance == pytest.approx(3.0, abs=1e-9)


def test_merge_drops_self_edge():
    net = ResistorNetwork()
    net.add_edge("A", "B", 5.0)
    net.add_edge("A", "B", 7.0)               # second A-B path
    net.merge("A", "B")                        # ... now shorted out
    # Both edges become self-edges on one node and are dropped from edge_list.
    assert net.edge_list() == []
    assert net.edge_count == 0


def test_merge_yields_parallel_resistance():
    # Two separate 4-ohm resistors, their ends fused at both sides -> 2 ohm.
    net = ResistorNetwork()
    net.add_edge(("p", 0), ("p", 1), 4.0)
    net.add_edge(("q", 0), ("q", 1), 4.0)
    net.merge(("p", 0), ("q", 0))
    net.merge(("p", 1), ("q", 1))
    assert net.two_terminal(("p", 0), ("p", 1)).resistance == pytest.approx(2.0, abs=1e-9)


def test_two_terminal_resolves_pre_merge_key():
    # A tie-style external node fused into a graph node must still be a valid
    # endpoint: two_terminal canonicalises it first.
    net = ResistorNetwork()
    net.add_edge(("g", 0), ("g", 1), 3.0)
    net.merge("EXT_A", ("g", 0))              # EXT_A has no edges of its own
    net.merge("EXT_B", ("g", 1))
    result = net.two_terminal("EXT_A", "EXT_B")
    assert result.resistance == pytest.approx(3.0, abs=1e-9)
    # The reported source/sink are the canonical (merged) nodes.
    assert result.source == net.canonical("EXT_A")
    assert result.sink == net.canonical("EXT_B")


# ---------------------------------------------------------------------------
# Records: TwoTerminalResult metadata and Provenance.
# ---------------------------------------------------------------------------


def test_result_reports_graph_size_and_backend():
    edges = [("A", "B", 1), ("B", "C", 2), ("C", "D", 3)]
    net = ResistorNetwork.from_edges(edges)
    result = net.two_terminal("A", "D")
    assert result.node_count == 4
    assert result.edge_count == 3
    assert result.backend == "dense"          # tiny graph -> auto picks dense


def test_auto_backend_resolves_to_sparse_on_large_graph():
    # A 21x21 grid (441 nodes) is above the dense limit, so auto resolves to a
    # sparse backend and reports which one it used.
    edges = []
    side = 21
    for r in range(side):
        for c in range(side):
            if c + 1 < side:
                edges.append(((r, c), (r, c + 1), 1.0))
            if r + 1 < side:
                edges.append(((r, c), (r + 1, c), 1.0))
    net = ResistorNetwork.from_edges(edges)
    result = net.two_terminal((0, 0), (side - 1, side - 1))
    assert result.node_count == side * side
    assert result.backend == ("scipy" if HAVE_SCIPY else "cg")


def test_add_edge_records_provenance_and_kind():
    net = ResistorNetwork(name="demo")
    prov = Provenance("board-derived", "demo", {"layer": "F.Cu", "length_mm": 3.0})
    edge = net.add_edge("A", "B", 1.5, "trace", prov)
    assert isinstance(edge, Edge)
    assert edge.kind == "trace"
    assert edge.provenance is prov
    assert net.edges[0].provenance.detail["layer"] == "F.Cu"


def test_default_provenance_carries_network_name():
    net = ResistorNetwork(name="ladder")
    edge = net.add_edge("A", "B", 1.0)
    assert edge.provenance.model == "ladder"
    assert edge.provenance.origin == "board-derived"


def test_edges_view_is_insertion_ordered_and_immutable():
    net = ResistorNetwork()
    net.add_edge("A", "B", 1.0)
    net.add_edge("B", "C", 2.0)
    view = net.edges
    assert isinstance(view, tuple)
    assert [e.resistance for e in view] == [1.0, 2.0]


# ---------------------------------------------------------------------------
# Failure modes propagate from the shared solver validator, named consistently.
# ---------------------------------------------------------------------------


def test_disconnected_endpoints_raise():
    net = ResistorNetwork.from_edges([("A", "B", 1.0), ("C", "D", 1.0)])
    with pytest.raises(ValueError, match="not connected"):
        net.two_terminal("A", "D")


def test_src_equals_dst_raises():
    net = ResistorNetwork.from_edges([("A", "B", 1.0)])
    with pytest.raises(ValueError, match="same node"):
        net.two_terminal("A", "A")


def test_non_positive_resistance_raises():
    net = ResistorNetwork.from_edges([("A", "B", 1.0), ("A", "C", 0.0), ("C", "B", 2.0)])
    with pytest.raises(ValueError, match="non-positive resistance"):
        net.two_terminal("A", "B")


def test_unrelated_component_is_ignored():
    # A stray island must not change the answer (solver restricts to src's
    # component); the network layer inherits that behaviour.
    net = ResistorNetwork.from_edges(
        [("A", "B", 1.0), ("B", "C", 1.0), ("X", "Y", 5.0)]
    )
    assert net.two_terminal("A", "C").resistance == pytest.approx(2.0, abs=1e-9)
