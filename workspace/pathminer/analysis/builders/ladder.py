# v0.1
"""Fast pour ladder builder (project specification S8.6 "Fast ladder").

Session 07. Models a filled zone as a one-dimensional strip per copper layer
along the pour's principal axis, with via rungs at real via stations and
external copper fused in at ties. This ports v0.13's ladder branch of
``build_graph_pour`` (and ``build_pour_ladder``) unchanged numerically:

    * strip nodes ``("pour", net, layer, round(u, 6))`` at the sorted set of
      via-station and tie projections ``u`` along the axis;
    * each strip run priced by ``trace_resistance`` over the pour's OBB width;
    * via rungs priced by ``via_resistance`` between consecutive landing layers;
    * ties fused with :meth:`ResistorNetwork.merge` (same physical copper → one
      node, never a near-zero tie resistor).

The strip model is a fast approximation valid only for strip-like copper; per
S8.6 it "warn[s] when aspect ratio is below 2:1". This builder emits that note;
the automatic escalation to the mesh lives in
``pathminer.analysis.model_selection`` (S8.7).

Unlike v0.13's ``build_graph_pour``, this pure builder does not itself decide to
ignore a pour that has no vias — that orchestration belongs above it (where it
lived in v0.13). Given the same pour, stations, and ties, the strip/rung/tie
numerics are identical to v0.13.

Layer contract (ARCH-002): analysis layer — imports ``pathminer.core`` only;
no Qt, no wx.
"""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from pathminer.core.network import Provenance, ResistorNetwork
from pathminer.core.resistance import trace_resistance, via_resistance
from pathminer.core.units import MM_TO_M

from .pour import Tie, ViaStation, pour_geometry

__all__ = [
    "LADDER_MIN_ASPECT",
    "build_ladder",
]

# Below this length:width ratio a 1-D strip model is questionable (v0.13
# ``build_graph_pour`` low-aspect note, S8.6 "warn when aspect ratio is below
# 2:1"). Shared with the model-selection policy.
LADDER_MIN_ASPECT = 2.0


def _finished_mm(geo: Sequence[Mapping[str, Any]], layer: str) -> float:
    g = next((x for x in geo if x["name"] == layer), None)
    if g is None:
        raise ValueError(f"layer {layer} is not in the stackup")
    return g["finished_mm"]


def build_ladder(
    pour: object,
    stations: Sequence[ViaStation],
    ties: Sequence[Tie],
    geo: Sequence[Mapping[str, Any]],
    plating_m: float,
    order: Sequence[str],
    *,
    convention: str = "bit",
    mode: str = "centre",
    name: str = "ladder",
) -> ResistorNetwork:
    """Build a per-layer strip + via-rung ladder network for one pour.

    *pour* is any object with ``.net`` and ``.fills`` (e.g.
    ``pathminer.models.board.Pour``). *order* is the copper-layer stacking order
    (top→bottom); only layers present in it are modelled. Returns a
    :class:`ResistorNetwork`; ``network.terminals`` maps each tie's external key
    to its node, and ``network.notes`` carries the low-aspect warning when the
    pour is too square for a strip.
    """
    g = pour_geometry(pour)
    net_id = g.net
    rank = {nm: i for i, nm in enumerate(order)}
    net = ResistorNetwork(name=name)

    if g.aspect < LADDER_MIN_ASPECT:
        net.notes.append(
            f"pour aspect ratio is only {g.aspect:.1f}:1 - a 1-D strip model is "
            "questionable on copper this square; consider the mesh model"
        )

    # Via stations, keyed by their axial projection (v0.13 ``via_layers``).
    via_layers: dict[float, dict[str, Any]] = {}
    for st in stations:
        lays = sorted((l for l in st.layers if l in rank), key=lambda l: rank[l])
        if len(lays) < 2:
            net.notes.append(f"via at {st.point} reaches only {lays} - ignored")
            continue
        u = g.project(st.point)
        via_layers[u] = {
            "layers": lays,
            "hole_mm": st.hole_mm,
            "pad_mm": st.pad_mm,
            "point": st.point,
        }

    # Ties, keyed by (layer, point) → (axial projection, external node).
    tie_pts: dict[tuple, tuple] = {}
    for t in ties:
        if t.layer in g.fills:
            tie_pts[(t.layer, t.point)] = (g.project(t.point), t.external())

    # Strip stations are every via and tie projection along the axis (v0.13).
    us = sorted(set(list(via_layers) + [u for (u, _n) in tie_pts.values()]))

    def pnode(layer: str, u: float):
        return ("pour", net_id, layer, round(u, 6))

    width = g.width
    for layer in g.fills:
        if layer not in rank:
            continue
        finished = _finished_mm(geo, layer)
        for u0, u1 in zip(us, us[1:]):
            du = u1 - u0
            if du <= 1e-9:
                continue
            r = trace_resistance(du * MM_TO_M, width * MM_TO_M, finished * MM_TO_M)
            net.add_edge(
                pnode(layer, u0),
                pnode(layer, u1),
                r,
                "pour",
                Provenance(
                    "board-derived",
                    name,
                    {"layer": layer, "length_mm": du, "width_mm": width},
                ),
            )

    for u, info in via_layers.items():
        lays = info["layers"]
        for a, b in zip(lays, lays[1:]):
            r, length_m, area_m2 = via_resistance(
                geo,
                a,
                b,
                info["hole_mm"] * MM_TO_M,
                plating_m,
                convention=convention,
                mode=mode,
            )
            net.add_edge(
                pnode(a, u),
                pnode(b, u),
                r,
                "via",
                Provenance(
                    "board-derived",
                    name,
                    {
                        "from": a,
                        "to": b,
                        "hole_mm": info["hole_mm"],
                        "point": info["point"],
                        "in_pour": True,
                        "length_m": length_m,
                        "area_m2": area_m2,
                    },
                ),
            )

    for (layer, _pt), (u, ext) in tie_pts.items():
        net.merge(ext, pnode(layer, u))  # same physical copper, one node
        net.terminals.setdefault(str(ext), ext)

    return net
