# v0.1
"""Raster pour mesh builder (project specification S8.6 "Raster mesh").

Session 07. Rasterises a pour's actual filled polygons into a per-layer
resistor grid — the general geometry model, valid for any pour shape. Ports
v0.13's ``mesh_pour_edges`` numerics unchanged:

    * a shared bounding box gridded at ``pitch`` (at least 2 cells per side);
    * only cells whose centre lies inside the fill on that layer are live
      (voids/obstacles are absent);
    * ``rs = rho / (t)`` ohms-per-square, so an in-plane cell edge is
      ``rs * px/py`` across x and ``rs * py/px`` across y;
    * a via barrel is a finite disc: every cell it covers on a landing layer is
      merged into one hub, and hubs on consecutive landing layers are joined by
      the ``via_resistance`` barrel;
    * a tie fuses external copper to the nearest live cell.

Determinism note (numerics-preserving refinement over v0.13): v0.13 selected a
via's hub cell and a tie's nearest cell by ``set`` iteration order, which is not
stable. This builder iterates live cells in sorted order and breaks nearest-cell
ties by cell index. All cells a barrel covers are merged into one electrical
node regardless, so the two-terminal result is unchanged; only the *name* of the
representative node becomes reproducible.

Layer contract (ARCH-002): analysis layer — imports ``pathminer.core`` only;
no Qt, no wx.
"""

from __future__ import annotations

import math
from typing import Any, Mapping, Sequence

from pathminer.core.geometry import point_in_polygon
from pathminer.core.materials import RHO_CU_20C
from pathminer.core.network import Provenance, ResistorNetwork
from pathminer.core.resistance import via_resistance
from pathminer.core.units import MM_TO_M

from .pour import Tie, ViaStation, pour_geometry

__all__ = [
    "DEFAULT_MESH_PITCH_MM",
    "build_mesh",
]

# v0.13's default mesh pitch (``DEFAULT_OPTIONS["mesh_pitch_mm"]``).
DEFAULT_MESH_PITCH_MM = 0.25


def build_mesh(
    pour: object,
    stations: Sequence[ViaStation],
    ties: Sequence[Tie],
    geo: Sequence[Mapping[str, Any]],
    plating_m: float,
    order: Sequence[str],
    *,
    pitch_mm: float = DEFAULT_MESH_PITCH_MM,
    convention: str = "bit",
    mode: str = "centre",
    name: str = "mesh",
) -> ResistorNetwork:
    """Build a raster-mesh network for one pour.

    *pour* is any object with ``.net`` and ``.fills``. *order* is the copper
    stacking order; only layers present in it are meshed. *pitch_mm* is the cell
    size. Returns a :class:`ResistorNetwork` whose nodes are ``(layer, i, j)``
    grid cells; ``network.terminals`` maps each tie's external key to its node,
    and ``network.notes`` records the grid size.
    """
    g = pour_geometry(pour)
    net_id = g.net
    rank = {nm: i for i, nm in enumerate(order)}
    net = ResistorNetwork(name=name)

    xs = [p[0] for poly in g.fills.values() for p in poly]
    ys = [p[1] for poly in g.fills.values() for p in poly]
    x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
    nx = max(int(round((x1 - x0) / pitch_mm)), 2)
    ny = max(int(round((y1 - y0) / pitch_mm)), 2)
    px, py = (x1 - x0) / nx, (y1 - y0) / ny

    def ctr(i: int, j: int):
        return (x0 + (i + 0.5) * px, y0 + (j + 0.5) * py)

    # Live cells per layer, held as a sorted list for deterministic iteration.
    live: dict[str, list] = {}
    for layer, poly in g.fills.items():
        if layer not in rank:
            continue
        live[layer] = sorted(
            (i, j)
            for i in range(nx)
            for j in range(ny)
            if point_in_polygon(ctr(i, j), poly)
        )

    for layer, cells in live.items():
        gg = next(x for x in geo if x["name"] == layer)
        rs = RHO_CU_20C / (gg["finished_mm"] * MM_TO_M)  # ohms per square
        cellset = set(cells)
        for (i, j) in cells:
            if (i + 1, j) in cellset:
                net.add_edge(
                    (layer, i, j),
                    (layer, i + 1, j),
                    rs * px / py,
                    "mesh",
                    Provenance("board-derived", name, {"layer": layer, "axis": "x"}),
                )
            if (i, j + 1) in cellset:
                net.add_edge(
                    (layer, i, j),
                    (layer, i, j + 1),
                    rs * py / px,
                    "mesh",
                    Provenance("board-derived", name, {"layer": layer, "axis": "y"}),
                )

    # A via barrel is a finite disc: merge every cell it covers into one hub.
    for st in stations:
        pt = st.point
        rad = st.hole_mm / 2.0
        lays = sorted((l for l in st.layers if l in rank), key=lambda l: rank[l])
        hub: dict[str, tuple] = {}
        for layer in lays:
            cells = live.get(layer)
            if not cells:
                continue
            covered = [
                (i, j)
                for (i, j) in cells
                if math.hypot(ctr(i, j)[0] - pt[0], ctr(i, j)[1] - pt[1]) <= rad
            ]
            if not covered:
                covered = [
                    min(
                        cells,
                        key=lambda c: (
                            math.hypot(ctr(*c)[0] - pt[0], ctr(*c)[1] - pt[1]),
                            c,
                        ),
                    )
                ]
            base = (layer, *covered[0])
            for c in covered[1:]:
                net.merge((layer, *c), base)
            hub[layer] = base
        for a, b in zip(lays, lays[1:]):
            ha, hb = hub.get(a), hub.get(b)
            if ha and hb:
                r, length_m, area_m2 = via_resistance(
                    geo,
                    a,
                    b,
                    st.hole_mm * MM_TO_M,
                    plating_m,
                    convention=convention,
                    mode=mode,
                )
                net.add_edge(
                    ha,
                    hb,
                    r,
                    "via",
                    Provenance(
                        "board-derived",
                        name,
                        {
                            "from": a,
                            "to": b,
                            "hole_mm": st.hole_mm,
                            "point": pt,
                            "in_pour": True,
                            "length_m": length_m,
                            "area_m2": area_m2,
                        },
                    ),
                )

    for t in ties:
        cells = live.get(t.layer)
        if not cells:
            continue
        pt = t.point
        c = min(
            cells,
            key=lambda cc: (math.hypot(ctr(*cc)[0] - pt[0], ctr(*cc)[1] - pt[1]), cc),
        )
        net.merge((t.layer, *c), t.external())
        net.terminals.setdefault(str(t.external()), t.external())

    net.notes.append(
        f"pour meshed at {pitch_mm:g} mm: {nx}x{ny} cells per layer - slow model, "
        "valid for any pour shape"
    )
    return net
