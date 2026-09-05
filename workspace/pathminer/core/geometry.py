# v0.1
"""pathminer.core.geometry — pure planar-geometry helpers.

Session 04 (BASE-005 / geometry slice of the M1 extraction). These are the
polygon, oriented-bounding-box, clustering, track-clipping, and arc-length
helpers extracted verbatim (numerical behavior preserved) from PathMiner
v0.13 (``tools/pcb_trace_resistance.py``). Only the public names change;
every expression, epsilon, and tie-breaking rule is copied unchanged so the
v0.13 acceptance vectors (V13 pour/clip/cluster geometry) reproduce exactly.

Layer contract (ARCH-002): this module is pure mathematics — no KiCad, Qt,
wx, file I/O, or upward pathminer imports. It consumes plain coordinate
tuples ``(x, y)`` and polygons as ``[(x, y), ...]`` vertex rings; it knows
nothing about nets, boards, or stackups. The KiCad/board layer (Sessions
05–06) parses copper into these primitives and the network layer (Session
07) consumes the results.

Provenance map (v0.13 symbol -> public name):
    _pt_in_poly        -> point_in_polygon
    _seg_poly_crossings-> segment_polygon_crossings
    _dist_to_poly      -> distance_to_polygon
    _principal_axis    -> principal_axis
    clip_track_to_pour -> clip_segment_to_polygon
    cluster_vias       -> cluster_points
    via_array_summary  -> cluster_summary
    _arc_length_mm     -> arc_length

Units are carried by the caller: coordinates and returned lengths/distances
are in whatever unit the input uses (millimetres on a KiCad board). These
functions are unit-agnostic; they neither assume nor convert units.
"""

from __future__ import annotations

import math

__all__ = [
    "point_in_polygon",
    "segment_polygon_crossings",
    "distance_to_polygon",
    "principal_axis",
    "clip_segment_to_polygon",
    "cluster_points",
    "cluster_summary",
    "arc_length",
]


# --------------------------------------------------------------------------
# Point / polygon predicates (v0.13 V13 "pour geometry" vectors)
# --------------------------------------------------------------------------


def point_in_polygon(pt, poly):
    """Ray casting. Points exactly on an edge count as inside.

    Ported verbatim from v0.13 ``_pt_in_poly``. *poly* is an ordered ring of
    ``(x, y)`` vertices; the closing edge (last -> first) is implicit.
    """
    x, y = pt
    inside = False
    n = len(poly)
    for i in range(n):
        x1, y1 = poly[i]
        x2, y2 = poly[(i + 1) % n]
        if abs((x2 - x1) * (y - y1) - (y2 - y1) * (x - x1)) < 1e-9 \
                and min(x1, x2) - 1e-9 <= x <= max(x1, x2) + 1e-9 \
                and min(y1, y2) - 1e-9 <= y <= max(y1, y2) + 1e-9:
            return True
        if (y1 > y) != (y2 > y):
            xi = x1 + (y - y1) * (x2 - x1) / (y2 - y1)
            if x < xi:
                inside = not inside
    return inside


def segment_polygon_crossings(p1, p2, poly):
    """Parameters t in (0,1) where segment p1->p2 crosses the polygon boundary.

    Ported verbatim from v0.13 ``_seg_poly_crossings``. Returns the sorted,
    de-duplicated (rounded to 9 decimals) crossing parameters.
    """
    (ax, ay), (bx, by) = p1, p2
    dx, dy = bx - ax, by - ay
    ts = []
    n = len(poly)
    for i in range(n):
        x1, y1 = poly[i]
        x2, y2 = poly[(i + 1) % n]
        ex, ey = x2 - x1, y2 - y1
        den = dx * ey - dy * ex
        if abs(den) < 1e-15:
            continue
        t = ((x1 - ax) * ey - (y1 - ay) * ex) / den
        u = ((x1 - ax) * dy - (y1 - ay) * dx) / den
        if 1e-9 < t < 1 - 1e-9 and -1e-9 <= u <= 1 + 1e-9:
            ts.append(t)
    return sorted(set(round(t, 9) for t in ts))


def distance_to_polygon(pt, poly):
    """Distance from a point to a polygon boundary (edges, not just vertices).

    Ported verbatim from v0.13 ``_dist_to_poly``.
    """
    x, y = pt
    best = float("inf")
    n = len(poly)
    for i in range(n):
        x1, y1 = poly[i]
        x2, y2 = poly[(i + 1) % n]
        dx, dy = x2 - x1, y2 - y1
        d2 = dx * dx + dy * dy
        t = 0.0 if d2 == 0 else max(0.0, min(1.0, ((x - x1) * dx + (y - y1) * dy) / d2))
        best = min(best, math.hypot(x - (x1 + t * dx), y - (y1 + t * dy)))
    return best


def principal_axis(pts):
    """Oriented bounding box of a point cloud: (origin, unit axis, length, width, u0).

    Ported verbatim from v0.13 ``_principal_axis``. *origin* is the centroid,
    *unit axis* is the principal direction ``(ux, uy)``, *length* and *width*
    are the extents along and across that axis, and *u0* is the minimum axial
    coordinate. Used by the pour strip model to score aspect ratio.
    """
    n = len(pts)
    cx = sum(p[0] for p in pts) / n
    cy = sum(p[1] for p in pts) / n
    sxx = sum((p[0] - cx) ** 2 for p in pts) / n
    syy = sum((p[1] - cy) ** 2 for p in pts) / n
    sxy = sum((p[0] - cx) * (p[1] - cy) for p in pts) / n
    tr, det = sxx + syy, sxx * syy - sxy * sxy
    disc = max(tr * tr / 4.0 - det, 0.0)
    lam = tr / 2.0 + math.sqrt(disc)
    if abs(sxy) > 1e-15:
        vx, vy = lam - syy, sxy
    else:
        vx, vy = (1.0, 0.0) if sxx >= syy else (0.0, 1.0)
    nrm = math.hypot(vx, vy) or 1.0
    ux, uy = vx / nrm, vy / nrm
    us = [(p[0] - cx) * ux + (p[1] - cy) * uy for p in pts]
    vs = [-(p[0] - cx) * uy + (p[1] - cy) * ux for p in pts]
    length = max(us) - min(us)
    width = max(vs) - min(vs)
    return (cx, cy), (ux, uy), length, width, min(us)


def clip_segment_to_polygon(p1, p2, poly):
    """Split a segment by a polygon outline.

    Ported verbatim from v0.13 ``clip_track_to_pour``. Returns
    ``(outside, inside)`` as lists of ``(pa, pb, frac)`` sub-runs where *frac*
    is the fraction of the original segment length in that sub-run.

    v0.13 note (preserved): copper inside a pour is modelled by the pour strip,
    so inside runs must not also be added as 1-D track edges or they would be
    double counted in parallel.
    """
    ts = [0.0] + segment_polygon_crossings(p1, p2, poly) + [1.0]
    (ax, ay), (bx, by) = p1, p2
    at = lambda t: (round(ax + t * (bx - ax), 6), round(ay + t * (by - ay), 6))  # noqa: E731
    outside, inside = [], []
    for t0, t1 in zip(ts, ts[1:]):
        if t1 - t0 < 1e-9:
            continue
        mid = at((t0 + t1) / 2.0)
        (inside if point_in_polygon(mid, poly) else outside).append((at(t0), at(t1), t1 - t0))
    return outside, inside


# --------------------------------------------------------------------------
# Point-cloud clustering (v0.13 V13 "clusters" / "array" vectors)
# --------------------------------------------------------------------------


def cluster_points(points, max_gap=2.0):
    """Group points into arrays by proximity (single-link). Returns list of lists.

    Ported verbatim from v0.13 ``cluster_vias``. Two points join the same
    cluster when they lie within *max_gap* of each other (chained). Groups are
    each sorted, then ordered by descending size then first point.
    """
    remaining = list(points)
    out = []
    while remaining:
        seed = remaining.pop()
        group = [seed]
        changed = True
        while changed:
            changed = False
            for p in list(remaining):
                if any(math.hypot(p[0] - g[0], p[1] - g[1]) <= max_gap for g in group):
                    group.append(p); remaining.remove(p); changed = True
        out.append(sorted(group))
    return sorted(out, key=lambda g: (-len(g), g[0]))


def cluster_summary(groups):
    """Centroid and extent per cluster - the statics view of each array.

    Ported verbatim from v0.13 ``via_array_summary``. *extent_mm* is the
    maximum pairwise span; naming keeps v0.13's field for compatibility.
    """
    out = []
    for g in groups:
        n = len(g)
        cx = sum(p[0] for p in g) / n
        cy = sum(p[1] for p in g) / n
        span = max(math.hypot(a[0] - b[0], a[1] - b[1]) for a in g for b in g) if n > 1 else 0.0
        out.append({"count": n, "centroid": (round(cx, 4), round(cy, 4)),
                    "extent_mm": round(span, 4), "points": g})
    return out


# --------------------------------------------------------------------------
# Arc length (v0.13 arc-handling helper)
# --------------------------------------------------------------------------


def arc_length(sx, sy, mx, my, ex, ey):
    """Arc length through three points; falls back to the chord if degenerate.

    Ported verbatim from v0.13 ``_arc_length_mm``. The three points are the
    start, a mid point on the arc, and the end. Collinear or zero-radius
    inputs fall back to the straight chord length.
    """
    d = 2.0 * (sx * (my - ey) + mx * (ey - sy) + ex * (sy - my))
    if abs(d) < 1e-12:
        return math.hypot(ex - sx, ey - sy)
    ux = ((sx * sx + sy * sy) * (my - ey) + (mx * mx + my * my) * (ey - sy)
          + (ex * ex + ey * ey) * (sy - my)) / d
    uy = ((sx * sx + sy * sy) * (ex - mx) + (mx * mx + my * my) * (sx - ex)
          + (ex * ex + ey * ey) * (mx - sx)) / d
    r = math.hypot(sx - ux, sy - uy)
    if r < 1e-12:
        return math.hypot(ex - sx, ey - sy)
    a0 = math.atan2(sy - uy, sx - ux)
    a1 = math.atan2(my - uy, mx - ux)
    a2 = math.atan2(ey - uy, ex - ux)

    def norm(a):
        while a < 0: a += 2 * math.pi
        while a >= 2 * math.pi: a -= 2 * math.pi
        return a
    sweep_mid = norm(a1 - a0)
    sweep_end = norm(a2 - a0)
    if sweep_mid > sweep_end:                     # arc runs the other way
        sweep_end = 2 * math.pi - sweep_end
    return r * sweep_end
