# v0.1
"""Tests for pathminer.core.geometry.

Session 04 (BASE-005 / geometry slice of the M1 extraction). These port the
pure-geometry acceptance vectors from v0.13's headless selftest
(``tools/pcb_trace_resistance.py::selftest``) unchanged, retaining the
original vector IDs (the "V13 pour geometry" block) so this module's
numerical behavior stays auditable against the v0.13 baseline (ARCH-010).
Positive, boundary, and degenerate/fallback cases are added for the helpers
whose v0.13 coverage was indirect (distance_to_polygon,
segment_polygon_crossings, arc_length).
"""

from __future__ import annotations

import math

import pytest

from pathminer.core.geometry import (
    arc_length,
    clip_segment_to_polygon,
    cluster_points,
    cluster_summary,
    distance_to_polygon,
    point_in_polygon,
    principal_axis,
    segment_polygon_crossings,
)

# v0.13 reference square used by the V13 vectors: a 10 x 1 strip.
SQ = [(0.0, 0.0), (10.0, 0.0), (10.0, 1.0), (0.0, 1.0)]


# ---------------------------------------------------------------------------
# V13 point-in-polygon
# ---------------------------------------------------------------------------


def test_v13_point_inside():
    assert point_in_polygon((5.0, 0.5), SQ) is True


def test_v13_point_outside():
    assert point_in_polygon((5.0, 2.0), SQ) is False


def test_v13_point_on_edge_counts_as_inside():
    assert point_in_polygon((5.0, 0.0), SQ) is True


def test_point_on_vertex_counts_as_inside():
    # Boundary: an exact vertex is on the boundary -> inside by v0.13's rule.
    assert point_in_polygon((0.0, 0.0), SQ) is True


def test_point_far_outside_each_side():
    assert point_in_polygon((-1.0, 0.5), SQ) is False
    assert point_in_polygon((11.0, 0.5), SQ) is False
    assert point_in_polygon((5.0, -1.0), SQ) is False


# ---------------------------------------------------------------------------
# V13 principal axis (drives pour length / width / aspect / axis)
# ---------------------------------------------------------------------------


def test_v13_principal_axis_of_strip():
    (cx, cy), (ux, uy), length, width, u0 = principal_axis(SQ)
    assert length == pytest.approx(10.0, abs=1e-9)          # V13 pour length
    assert width == pytest.approx(1.0, abs=1e-9)            # V13 pour width
    assert (length / width) == pytest.approx(10.0, abs=1e-9)  # V13 pour aspect
    assert abs(ux) == pytest.approx(1.0, abs=1e-9)          # V13 axis is x
    assert abs(uy) == pytest.approx(0.0, abs=1e-9)
    assert cx == pytest.approx(5.0, abs=1e-9)
    assert cy == pytest.approx(0.5, abs=1e-9)


def test_principal_axis_of_diagonal_cloud():
    # A cloud along y = x should report a 45-degree principal axis.
    pts = [(0.0, 0.0), (1.0, 1.0), (2.0, 2.0), (3.0, 3.0)]
    (_c), (ux, uy), length, width, _u0 = principal_axis(pts)
    assert abs(ux) == pytest.approx(abs(uy), abs=1e-9)      # 45 degrees
    assert length == pytest.approx(math.hypot(3.0, 3.0), abs=1e-9)
    assert width == pytest.approx(0.0, abs=1e-9)


# ---------------------------------------------------------------------------
# V13 track clipping against a pour outline
# ---------------------------------------------------------------------------


def test_v13_clip_lengths():
    out, ins = clip_segment_to_polygon((-5.0, 0.5), (5.0, 0.5), SQ)
    assert sum(f for _a, _b, f in out) == pytest.approx(0.5, abs=1e-9)  # V13 clip outside
    assert sum(f for _a, _b, f in ins) == pytest.approx(0.5, abs=1e-9)  # V13 clip inside


def test_clip_fully_inside_is_all_inside():
    out, ins = clip_segment_to_polygon((2.0, 0.5), (8.0, 0.5), SQ)
    assert out == []
    assert sum(f for _a, _b, f in ins) == pytest.approx(1.0, abs=1e-9)


def test_clip_fully_outside_is_all_outside():
    out, ins = clip_segment_to_polygon((-5.0, 5.0), (5.0, 5.0), SQ)
    assert ins == []
    assert sum(f for _a, _b, f in out) == pytest.approx(1.0, abs=1e-9)


# ---------------------------------------------------------------------------
# segment-polygon crossings (used by the clipper; direct coverage)
# ---------------------------------------------------------------------------


def test_segment_one_crossing_entering():
    # Enters the strip at its left edge x = 0 (t = 0.5), then ends inside.
    assert segment_polygon_crossings((-5.0, 0.5), (5.0, 0.5), SQ) == [0.5]


def test_segment_two_crossings_passing_through():
    # Enters at x = 0 (t = 0.25) and exits at x = 10 (t = 0.75).
    assert segment_polygon_crossings((-5.0, 0.5), (15.0, 0.5), SQ) == [0.25, 0.75]


def test_segment_no_crossing():
    assert segment_polygon_crossings((-5.0, 5.0), (5.0, 5.0), SQ) == []


# ---------------------------------------------------------------------------
# distance to polygon boundary
# ---------------------------------------------------------------------------


def test_distance_outside():
    assert distance_to_polygon((5.0, 5.0), SQ) == pytest.approx(4.0, abs=1e-9)


def test_distance_inside_is_to_nearest_edge():
    assert distance_to_polygon((5.0, 0.5), SQ) == pytest.approx(0.5, abs=1e-9)


def test_distance_to_corner():
    assert distance_to_polygon((-3.0, -4.0), SQ) == pytest.approx(5.0, abs=1e-9)


# ---------------------------------------------------------------------------
# V13 clustering
# ---------------------------------------------------------------------------


def test_v13_clusters_found():
    cl = cluster_points([(0, 0), (1, 0), (2, 0), (20, 0)], max_gap=2.0)
    assert sorted(len(c) for c in cl) == [1, 3]             # V13 clusters found


def test_v13_array_summary():
    cl = cluster_points([(0, 0), (1, 0), (2, 0), (20, 0)], max_gap=2.0)
    summ = cluster_summary(cl)
    big = max(summ, key=lambda a: a["count"])
    assert big["centroid"][0] == pytest.approx(1.0, abs=1e-9)   # V13 array centroid
    assert big["extent_mm"] == pytest.approx(2.0, abs=1e-9)     # V13 array extent


def test_cluster_gap_boundary_splits():
    # Points exactly max_gap apart chain together; beyond it, they split.
    joined = cluster_points([(0, 0), (2, 0)], max_gap=2.0)
    assert sorted(len(c) for c in joined) == [2]
    split = cluster_points([(0, 0), (2.0001, 0)], max_gap=2.0)
    assert sorted(len(c) for c in split) == [1, 1]


def test_cluster_empty_input():
    assert cluster_points([], max_gap=2.0) == []


def test_cluster_summary_single_point_has_zero_extent():
    summ = cluster_summary([[(3.0, 4.0)]])
    assert summ[0]["count"] == 1
    assert summ[0]["extent_mm"] == pytest.approx(0.0, abs=1e-9)
    assert summ[0]["centroid"] == (3.0, 4.0)


# ---------------------------------------------------------------------------
# arc length
# ---------------------------------------------------------------------------


def test_arc_semicircle_upper():
    # Unit semicircle (r, 0) -> (0, r) -> (-r, 0): length = pi * r.
    assert arc_length(1.0, 0.0, 0.0, 1.0, -1.0, 0.0) == pytest.approx(math.pi, abs=1e-9)


def test_arc_semicircle_lower_runs_other_way():
    # Same endpoints, mid below the axis: exercises the "arc runs the other
    # way" branch and still measures a half turn = pi.
    assert arc_length(1.0, 0.0, 0.0, -1.0, -1.0, 0.0) == pytest.approx(math.pi, abs=1e-9)


def test_arc_quarter_circle():
    s2 = math.sqrt(0.5)
    assert arc_length(1.0, 0.0, s2, s2, 0.0, 1.0) == pytest.approx(math.pi / 2.0, abs=1e-9)


def test_arc_collinear_falls_back_to_chord():
    assert arc_length(0.0, 0.0, 1.0, 0.0, 2.0, 0.0) == pytest.approx(2.0, abs=1e-12)


def test_arc_radius_scales_length():
    # Radius-2 semicircle: length = pi * 2.
    assert arc_length(2.0, 0.0, 0.0, 2.0, -2.0, 0.0) == pytest.approx(2.0 * math.pi, abs=1e-9)
