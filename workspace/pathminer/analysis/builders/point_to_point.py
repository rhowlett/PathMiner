# v0.1
"""Point-to-point series builder (project specification S8.5, S8.7).

Session 07. Builds a :class:`~pathminer.core.network.ResistorNetwork` for a
simple, manually declared strict series chain of trace and via segments — the
v0.13 "Via / Path" manual path, and the model S8.7 selects for a "Simple manual
trace/via chain". The chain is a linear graph whose nodes are the integers
``0..N``; ``start`` is node ``0`` and ``end`` is node ``N`` (recorded in
``network.terminals``), so ``Rpath = Σ Rsegment`` between them.

Each segment is priced by the validated v0.13 formulas in
``pathminer.core.resistance`` (PWR-001): ``trace_resistance`` for a copper run,
``via_resistance`` for a via barrel (or a derated parallel via array). No
resistance is duplicated here — this builder only assembles and names the graph.

Layer contract (ARCH-002): analysis layer — imports ``pathminer.core`` only;
no Qt, no wx.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence, Union

from pathminer.core.network import Provenance, ResistorNetwork
from pathminer.core.resistance import trace_resistance, via_resistance
from pathminer.core.units import MM_TO_M

from .pour import finished_mm

__all__ = [
    "TraceSegment",
    "ViaSegment",
    "Segment",
    "build_point_to_point",
]


@dataclass(frozen=True)
class TraceSegment:
    """One copper run on one layer: length and width in millimetres."""

    layer: str
    length_mm: float
    width_mm: float


@dataclass(frozen=True)
class ViaSegment:
    """One via barrel span (or a derated parallel via array).

    ``hole_mm`` is interpreted per the build's ``convention`` ("bit" = drilled
    diameter, "finished" = plated diameter). ``count``/``sharing_pct`` derate a
    parallel array exactly as v0.13's ``via_resistance`` does.
    """

    from_layer: str
    to_layer: str
    hole_mm: float
    count: int = 1
    sharing_pct: float = 100.0


Segment = Union[TraceSegment, ViaSegment]


def build_point_to_point(
    segments: Sequence[Segment],
    geo: Sequence[Mapping[str, Any]],
    plating_m: float,
    *,
    convention: str = "bit",
    mode: str = "centre",
    name: str = "point_to_point",
) -> ResistorNetwork:
    """Build a series-chain network from ordered trace/via *segments*.

    *geo* is the per-copper-layer geometry sequence produced by the stackup
    (each mapping carries ``name``, ``z_top_mm``, ``finished_mm``, ``z_ctr_mm``
    — the shape ``pathminer.core.resistance`` expects). *plating_m* is the via
    plating thickness in metres. Returns a :class:`ResistorNetwork` with
    ``terminals["start"] = 0`` and ``terminals["end"] = len(segments)``.

    Raises ``ValueError`` for an empty chain or an unknown trace layer, and
    ``TypeError`` for an unrecognised segment type. Via-plating errors ("hole
    closed by plating") propagate from ``via_resistance`` unchanged.
    """
    if not segments:
        raise ValueError("point-to-point path has no segments")

    net = ResistorNetwork(name=name)
    for i, seg in enumerate(segments):
        u, v = i, i + 1
        if isinstance(seg, TraceSegment):
            finished = finished_mm(geo, seg.layer)
            r = trace_resistance(
                seg.length_mm * MM_TO_M,
                seg.width_mm * MM_TO_M,
                finished * MM_TO_M,
            )
            net.add_edge(
                u,
                v,
                r,
                "trace",
                Provenance(
                    "board-derived",
                    name,
                    {
                        "layer": seg.layer,
                        "length_mm": seg.length_mm,
                        "width_mm": seg.width_mm,
                    },
                ),
            )
        elif isinstance(seg, ViaSegment):
            r, length_m, area_m2 = via_resistance(
                geo,
                seg.from_layer,
                seg.to_layer,
                seg.hole_mm * MM_TO_M,
                plating_m,
                convention=convention,
                mode=mode,
                count=seg.count,
                sharing_pct=seg.sharing_pct,
            )
            net.add_edge(
                u,
                v,
                r,
                "via",
                Provenance(
                    "board-derived",
                    name,
                    {
                        "from": seg.from_layer,
                        "to": seg.to_layer,
                        "hole_mm": seg.hole_mm,
                        "count": seg.count,
                        "sharing_pct": seg.sharing_pct,
                        "length_m": length_m,
                        "area_m2": area_m2,
                    },
                ),
            )
        else:
            raise TypeError(f"unknown segment type: {type(seg).__name__}")

    net.terminals["start"] = 0
    net.terminals["end"] = len(segments)
    return net
