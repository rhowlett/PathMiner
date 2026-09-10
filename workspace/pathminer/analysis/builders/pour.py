# v0.1
"""Shared pour geometry and station/tie inputs for the ladder and mesh builders.

Session 07. Both the fast ladder (project specification S8.6 "Fast ladder")
and the raster mesh (S8.6 "Raster mesh") work from the same pour geometry —
the oriented bounding box (principal axis, length, width, aspect) computed by
``pathminer.core.geometry.principal_axis`` — and from the same via-station and
copper-tie inputs. This module holds those shared pieces so the two builders,
and the model-selection policy (S8.7), agree on one geometry description.

:class:`PourGeometry` reproduces v0.13's ``Pour`` strip analysis numerically
(the same ``principal_axis`` output and ``project`` formula), but takes any
object exposing ``.net`` and ``.fills`` — in particular
``pathminer.models.board.Pour`` (Session 06), which is pure geometry storage
and delegates axis/aspect analysis to this network-builder layer, exactly as
its own docstring says it should.

Layer contract (ARCH-002): analysis layer — imports ``pathminer.core`` only;
no Qt, no wx.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Hashable, List, Mapping, Optional, Sequence, Tuple

from pathminer.core.geometry import principal_axis

Point = Tuple[float, float]

__all__ = [
    "Point",
    "PourGeometry",
    "pour_geometry",
    "ViaStation",
    "Tie",
]


@dataclass(frozen=True)
class PourGeometry:
    """A pour's filled copper plus its oriented-bounding-box strip analysis.

    ``centroid``/``axis`` are the principal-axis origin and unit direction;
    ``length``/``width`` are the extents along and across that axis; ``aspect``
    is ``length/width`` (``inf`` for a degenerate zero-width cloud). These are
    v0.13's ``Pour`` fields, computed the same way, so the ladder strip pricing
    and the aspect-ratio model-selection warning are unchanged.
    """

    net: int
    fills: Mapping[str, Sequence[Point]]
    centroid: Point
    axis: Point
    length: float
    width: float
    u0: float

    @property
    def aspect(self) -> float:
        return self.length / self.width if self.width > 1e-9 else float("inf")

    def layers(self) -> List[str]:
        return list(self.fills)

    def project(self, pt: Point) -> float:
        """Distance of *pt* along the pour's long axis (v0.13 ``Pour.project``)."""
        return (pt[0] - self.centroid[0]) * self.axis[0] + (
            pt[1] - self.centroid[1]
        ) * self.axis[1]


def pour_geometry(pour: object) -> PourGeometry:
    """Compute :class:`PourGeometry` for any object with ``.net`` and ``.fills``.

    Raises ``ValueError`` if the pour has no filled copper at all (an empty
    ``fills``), because a strip/mesh has nothing to model.
    """
    fills = dict(pour.fills)  # type: ignore[attr-defined]
    allpts = [p for poly in fills.values() for p in poly]
    if not allpts:
        raise ValueError("pour has no filled copper")
    (cx, cy), (ux, uy), length, width, u0 = principal_axis(allpts)
    return PourGeometry(
        net=int(getattr(pour, "net", 0)),
        fills=fills,
        centroid=(cx, cy),
        axis=(ux, uy),
        length=length,
        width=width,
        u0=u0,
    )


@dataclass(frozen=True)
class ViaStation:
    """One via (or stitching-via location) that lands inside a pour.

    ``layers`` are the copper layers the barrel actually lands on; the builder
    keeps only those present in the stackup ``order`` and prices the barrel in
    series between consecutive landings (S8.4). A station reaching fewer than
    two stackup layers carries no current and is skipped with a note.
    """

    point: Point
    layers: Tuple[str, ...]
    hole_mm: float
    pad_mm: float = 0.0


@dataclass(frozen=True)
class Tie:
    """A point where external copper (a track end or pad) joins the pour.

    ``node`` is the external node key to fuse into the pour node at this point
    (the same physical copper → one node, never a tie resistor). When ``node``
    is omitted the builder uses ``(layer, point)`` as the external key, matching
    v0.13's track/pad node naming.
    """

    layer: str
    point: Point
    node: Optional[Hashable] = None

    def external(self) -> Hashable:
        return self.node if self.node is not None else (self.layer, self.point)
