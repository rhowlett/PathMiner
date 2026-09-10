# v0.1
"""Tests for pathminer.analysis.builders (Session 07, ARCH-004 + QA-005 slice).

Covers the three builders and the ARCH-004 Done-when ("point-to-point, ladder,
and mesh builders all emit the same network type"):

    * every builder returns a ``pathminer.core.network.ResistorNetwork`` that
      solves to a ``TwoTerminalResult``;
    * point-to-point series pricing equals ``pathminer.core.resistance`` term by
      term (PWR-001 parity — no duplicated formula);
    * the ladder strip/rung/tie numerics reproduce the hand answer;
    * the mesh rasterises the fill and is deterministic;
    * the fast-vs-mesh correlation and mesh-refinement convergence fixtures
      (QA-005 contribution): on a strip-like pour the ladder and mesh agree, and
      the mesh converges toward the ladder as the pitch refines.
"""

from __future__ import annotations

import pytest

from pathminer.core.network import ResistorNetwork, TwoTerminalResult
from pathminer.core.resistance import trace_resistance, via_resistance
from pathminer.core.units import MM_TO_M
from pathminer.analysis.builders import (
    DEFAULT_MESH_PITCH_MM,
    Tie,
    TraceSegment,
    ViaSegment,
    ViaStation,
    build_ladder,
    build_mesh,
    build_point_to_point,
)

# A minimal two-copper-layer stackup geometry (the shape core.resistance wants).
GEO = [
    {"name": "F.Cu", "z_top_mm": 0.0, "finished_mm": 0.035, "z_ctr_mm": 0.0175},
    {"name": "B.Cu", "z_top_mm": 1.6, "finished_mm": 0.035, "z_ctr_mm": 1.6175},
]
ORDER = ["F.Cu", "B.Cu"]
PLATING_M = 25e-6


class _Pour:
    """Minimal pour: net + per-layer fill polygons (the models.board.Pour shape)."""

    def __init__(self, net, fills):
        self.net = net
        self.fills = fills


def _rect(x0, y0, x1, y1):
    return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]


# ---------------------------------------------------------------------------
# ARCH-004 Done-when: all three builders emit the same network type.
# ---------------------------------------------------------------------------


def _p2p():
    return build_point_to_point(
        [TraceSegment("F.Cu", 10.0, 0.5)], GEO, PLATING_M
    )


def _ladder():
    pour = _Pour(4, {"F.Cu": _rect(0, 0, 20, 2), "B.Cu": _rect(0, 0, 20, 2)})
    stations = [ViaStation((10.0, 1.0), ("F.Cu", "B.Cu"), 0.3)]
    ties = [Tie("F.Cu", (0.5, 1.0), "A"), Tie("F.Cu", (19.5, 1.0), "B")]
    return build_ladder(pour, stations, ties, GEO, PLATING_M, ORDER)


def _mesh():
    pour = _Pour(4, {"F.Cu": _rect(0, 0, 20, 2), "B.Cu": _rect(0, 0, 20, 2)})
    stations = [ViaStation((10.0, 1.0), ("F.Cu", "B.Cu"), 0.3)]
    ties = [Tie("F.Cu", (0.5, 1.0), "A"), Tie("F.Cu", (19.5, 1.0), "B")]
    return build_mesh(pour, stations, ties, GEO, PLATING_M, ORDER, pitch_mm=0.5)


@pytest.mark.parametrize("builder", [_p2p, _ladder, _mesh],
                         ids=["point_to_point", "ladder", "mesh"])
def test_all_builders_emit_resistor_network(builder):
    """ARCH-004: the three builders all return the one common network type."""
    net = builder()
    assert isinstance(net, ResistorNetwork)
    assert type(net) is ResistorNetwork


def test_all_builders_produce_solvable_networks():
    assert isinstance(_p2p().two_terminal(0, 1), TwoTerminalResult)
    assert isinstance(_ladder().two_terminal("A", "B"), TwoTerminalResult)
    assert isinstance(_mesh().two_terminal("A", "B"), TwoTerminalResult)


# ---------------------------------------------------------------------------
# Point-to-point series builder.
# ---------------------------------------------------------------------------


def test_p2p_series_sum_equals_two_terminal_and_hand_price():
    segments = [
        TraceSegment("F.Cu", 10.0, 0.5),
        ViaSegment("F.Cu", "B.Cu", 0.3),
        TraceSegment("B.Cu", 10.0, 0.5),
    ]
    net = build_point_to_point(segments, GEO, PLATING_M)

    # Term-by-term parity with core.resistance (no duplicated formula).
    r_tr = trace_resistance(10.0 * MM_TO_M, 0.5 * MM_TO_M, 0.035 * MM_TO_M)
    r_via, _l, _a = via_resistance(GEO, "F.Cu", "B.Cu", 0.3 * MM_TO_M, PLATING_M)
    expected = r_tr + r_via + r_tr

    assert net.two_terminal(0, 3).resistance == pytest.approx(expected, abs=1e-15)
    # A strict series chain: the network-equivalent equals the sum of edges.
    assert sum(r for _u, _v, r in net.edge_list()) == pytest.approx(expected, abs=1e-15)


def test_p2p_terminals_are_first_and_last_node():
    net = build_point_to_point(
        [TraceSegment("F.Cu", 1.0, 0.2), TraceSegment("F.Cu", 1.0, 0.2)],
        GEO, PLATING_M,
    )
    assert net.terminals == {"start": 0, "end": 2}


def test_p2p_via_array_derates_resistance():
    single = build_point_to_point(
        [ViaSegment("F.Cu", "B.Cu", 0.3, count=1)], GEO, PLATING_M
    ).two_terminal(0, 1).resistance
    quad = build_point_to_point(
        [ViaSegment("F.Cu", "B.Cu", 0.3, count=4)], GEO, PLATING_M
    ).two_terminal(0, 1).resistance
    assert quad == pytest.approx(single / 4.0, abs=1e-15)


def test_p2p_length_convention_changes_via_length():
    centre = build_point_to_point(
        [ViaSegment("F.Cu", "B.Cu", 0.3)], GEO, PLATING_M, mode="centre"
    ).two_terminal(0, 1).resistance
    outer = build_point_to_point(
        [ViaSegment("F.Cu", "B.Cu", 0.3)], GEO, PLATING_M, mode="outer"
    ).two_terminal(0, 1).resistance
    # "outer" spans the full copper thickness on both layers -> longer barrel.
    assert outer > centre


def test_p2p_empty_chain_raises():
    with pytest.raises(ValueError, match="no segments"):
        build_point_to_point([], GEO, PLATING_M)


def test_p2p_unknown_layer_raises():
    with pytest.raises(ValueError, match="not in the stackup"):
        build_point_to_point([TraceSegment("In1.Cu", 1.0, 0.2)], GEO, PLATING_M)


def test_p2p_bad_segment_type_raises():
    with pytest.raises(TypeError, match="unknown segment type"):
        build_point_to_point(["not a segment"], GEO, PLATING_M)


def test_p2p_hole_closed_by_plating_raises():
    # A 0.03 mm bit fully closes under 25 um plating (2*25um = 0.05 > 0.03).
    with pytest.raises(ValueError, match="hole closed by plating"):
        build_point_to_point(
            [ViaSegment("F.Cu", "B.Cu", 0.03)], GEO, PLATING_M
        )


# ---------------------------------------------------------------------------
# Ladder builder.
# ---------------------------------------------------------------------------


def test_ladder_single_layer_strip_matches_hand_price():
    # One layer, two ties, no vias: a single strip run over the tie span.
    pour = _Pour(4, {"F.Cu": _rect(0, 0, 20, 2)})
    ties = [Tie("F.Cu", (0.5, 1.0), "A"), Tie("F.Cu", (19.5, 1.0), "B")]
    net = build_ladder(pour, [], ties, GEO, PLATING_M, ORDER)

    span_mm = 19.0                     # u = +9.5 minus u = -9.5 along the axis
    expected = trace_resistance(span_mm * MM_TO_M, 2.0 * MM_TO_M, 0.035 * MM_TO_M)
    assert net.two_terminal("A", "B").resistance == pytest.approx(expected, abs=1e-12)


def test_ladder_ties_are_fused_to_pour_nodes():
    net = _ladder()
    # Each external tie key resolves (via merge) to a pour strip node.
    a_node = net.canonical("A")
    assert a_node != "A"
    assert a_node[0] == "pour"          # ("pour", net, layer, u)


def test_ladder_two_layer_via_rung_lowers_resistance():
    # Adding a parallel B.Cu strip through a via rung must not raise the R.
    pour = _Pour(4, {"F.Cu": _rect(0, 0, 20, 2), "B.Cu": _rect(0, 0, 20, 2)})
    ties = [Tie("F.Cu", (0.5, 1.0), "A"), Tie("F.Cu", (19.5, 1.0), "B")]
    one_layer = build_ladder(
        _Pour(4, {"F.Cu": _rect(0, 0, 20, 2)}), [], ties, GEO, PLATING_M, ORDER
    ).two_terminal("A", "B").resistance
    stations = [
        ViaStation((2.0, 1.0), ("F.Cu", "B.Cu"), 0.3),
        ViaStation((18.0, 1.0), ("F.Cu", "B.Cu"), 0.3),
    ]
    two_layer = build_ladder(
        pour, stations, ties, GEO, PLATING_M, ORDER
    ).two_terminal("A", "B").resistance
    assert two_layer < one_layer


def test_ladder_low_aspect_pour_emits_warning_note():
    square = _Pour(4, {"F.Cu": _rect(0, 0, 5, 5)})
    ties = [Tie("F.Cu", (0.5, 2.5), "A"), Tie("F.Cu", (4.5, 2.5), "B")]
    net = build_ladder(square, [], ties, GEO, PLATING_M, ORDER)
    assert any("questionable" in n for n in net.notes)


def test_ladder_via_reaching_one_layer_is_skipped_with_note():
    pour = _Pour(4, {"F.Cu": _rect(0, 0, 20, 2), "B.Cu": _rect(0, 0, 20, 2)})
    ties = [Tie("F.Cu", (0.5, 1.0), "A"), Tie("F.Cu", (19.5, 1.0), "B")]
    stations = [ViaStation((10.0, 1.0), ("F.Cu",), 0.3)]   # only one landing
    net = build_ladder(pour, stations, ties, GEO, PLATING_M, ORDER)
    assert any("reaches only" in n for n in net.notes)
    # No rung was added, so the two layers stay unconnected: B.Cu is a stray
    # island and A..B is the F.Cu-only strip.
    one_layer = build_ladder(
        _Pour(4, {"F.Cu": _rect(0, 0, 20, 2)}), [], ties, GEO, PLATING_M, ORDER
    ).two_terminal("A", "B").resistance
    assert net.two_terminal("A", "B").resistance == pytest.approx(one_layer, abs=1e-12)


# ---------------------------------------------------------------------------
# Mesh builder.
# ---------------------------------------------------------------------------


def test_mesh_rasterises_and_records_grid_note():
    net = _mesh()
    assert net.node_count > 0
    assert any("meshed at" in n for n in net.notes)


def test_mesh_is_deterministic():
    a = _mesh().edge_list()
    b = _mesh().edge_list()
    assert a == b                       # identical node names and ordering


def test_mesh_large_grid_uses_sparse_backend():
    pour = _Pour(4, {"F.Cu": _rect(0, 0, 30, 2), "B.Cu": _rect(0, 0, 30, 2)})
    stations = [ViaStation((15.0, 1.0), ("F.Cu", "B.Cu"), 0.3)]
    ties = [Tie("F.Cu", (0.5, 1.0), "A"), Tie("F.Cu", (29.5, 1.0), "B")]
    net = build_mesh(pour, stations, ties, GEO, PLATING_M, ORDER, pitch_mm=0.25)
    result = net.two_terminal("A", "B")
    assert result.node_count > 400
    assert result.backend in ("scipy", "cg")


def test_mesh_default_pitch_constant():
    assert DEFAULT_MESH_PITCH_MM == 0.25


def test_mesh_unknown_layer_raises_named_error():
    # Consistency with point-to-point / ladder: a modelled layer missing from
    # the stackup raises the same named ValueError, not a bare StopIteration.
    geo_missing = [
        {"name": "B.Cu", "z_top_mm": 1.6, "finished_mm": 0.035, "z_ctr_mm": 1.6175},
    ]
    pour = _Pour(4, {"F.Cu": _rect(0, 0, 20, 2)})
    ties = [Tie("F.Cu", (0.5, 1.0), "A"), Tie("F.Cu", (19.5, 1.0), "B")]
    with pytest.raises(ValueError, match="not in the stackup"):
        build_mesh(pour, [], ties, geo_missing, PLATING_M, ["F.Cu"], pitch_mm=0.5)


@pytest.mark.parametrize("pitch", [0.0, -0.25])
def test_mesh_non_positive_pitch_raises(pitch):
    pour = _Pour(4, {"F.Cu": _rect(0, 0, 20, 2)})
    with pytest.raises(ValueError, match="pitch must be positive"):
        build_mesh(pour, [], [], GEO, PLATING_M, ORDER, pitch_mm=pitch)


def test_mesh_degenerate_fill_raises_named_error():
    # A zero-extent fill (all points share an x) would divide by zero; a named
    # error is raised instead.
    pour = _Pour(4, {"F.Cu": [(5.0, 0.0), (5.0, 2.0), (5.0, 4.0)]})
    with pytest.raises(ValueError, match="zero extent"):
        build_mesh(pour, [], [], GEO, PLATING_M, ORDER, pitch_mm=0.5)


def test_mesh_via_reaching_one_layer_is_skipped_with_note():
    # Same diagnostic the ladder emits, and the way v0.13 reported it before its
    # ladder/mesh split.
    pour = _Pour(4, {"F.Cu": _rect(0, 0, 20, 2), "B.Cu": _rect(0, 0, 20, 2)})
    stations = [ViaStation((10.0, 1.0), ("F.Cu",), 0.3)]
    ties = [Tie("F.Cu", (0.5, 1.0), "A"), Tie("F.Cu", (19.5, 1.0), "B")]
    net = build_mesh(pour, stations, ties, GEO, PLATING_M, ORDER, pitch_mm=0.5)
    assert any("reaches only" in n for n in net.notes)


# ---------------------------------------------------------------------------
# Fast-vs-mesh correlation + mesh refinement (QA-005 contribution).
# ---------------------------------------------------------------------------


def _strip_fixture():
    """A 30x2 mm (15:1) strip-like pour, stitched, with full-width end ties."""
    pour = _Pour(7, {"F.Cu": _rect(0, 0, 30, 2), "B.Cu": _rect(0, 0, 30, 2)})
    stations = [
        ViaStation((14.0, 1.0), ("F.Cu", "B.Cu"), 0.3),
        ViaStation((15.0, 1.0), ("F.Cu", "B.Cu"), 0.3),
        ViaStation((16.0, 1.0), ("F.Cu", "B.Cu"), 0.3),
    ]
    # Distribute each end's injection across the width so the mesh's boundary
    # condition matches the ladder's full-width strip node.
    ys = [0.3, 0.7, 1.0, 1.3, 1.7]
    ties = [Tie("F.Cu", (0.4, y), "A") for y in ys] + \
           [Tie("F.Cu", (29.6, y), "B") for y in ys]
    return pour, stations, ties


def test_fast_ladder_matches_mesh_within_tolerance():
    pour, stations, ties = _strip_fixture()
    ladder_r = build_ladder(
        pour, stations, ties, GEO, PLATING_M, ORDER
    ).two_terminal("A", "B").resistance
    mesh_r = build_mesh(
        pour, stations, ties, GEO, PLATING_M, ORDER, pitch_mm=0.25
    ).two_terminal("A", "B").resistance
    # On a strip-like pour the fast ladder is a good approximation of the mesh.
    assert mesh_r == pytest.approx(ladder_r, rel=0.03)


def test_mesh_converges_toward_ladder_as_pitch_refines():
    pour, stations, ties = _strip_fixture()
    ladder_r = build_ladder(
        pour, stations, ties, GEO, PLATING_M, ORDER
    ).two_terminal("A", "B").resistance
    errors = []
    for pitch in (0.5, 0.25, 0.125):
        mesh_r = build_mesh(
            pour, stations, ties, GEO, PLATING_M, ORDER, pitch_mm=pitch
        ).two_terminal("A", "B").resistance
        errors.append(abs(mesh_r / ladder_r - 1.0))
    # Refining the pitch monotonically reduces the disagreement with the ladder.
    assert errors[0] > errors[1] > errors[2]
    assert errors[-1] < 0.01
