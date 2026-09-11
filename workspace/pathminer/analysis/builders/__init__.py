# v0.1
"""pathminer.analysis.builders — geometry-to-network resistance builders.

Session 07 (ARCH-004). Every builder here returns the one common network type
``pathminer.core.network.ResistorNetwork`` (that shared return type is the
ARCH-004 Done-when), priced by the validated v0.13 formulas in
``pathminer.core.resistance`` (PWR-001):

    point_to_point.build_point_to_point — simple manual trace/via series chain.
    ladder.build_ladder                 — fast 1-D strip + via-rung pour model.
    mesh.build_mesh                     — general raster-grid pour model.

Shared inputs (``ViaStation``, ``Tie``, ``PourGeometry``) live in ``pour``.
The automatic choice between these models is
``pathminer.analysis.model_selection`` (S8.7).

Layer contract (ARCH-002): imports ``pathminer.core`` only; no Qt, no wx.
"""

from __future__ import annotations

from .ladder import LADDER_MIN_ASPECT, build_ladder
from .mesh import DEFAULT_MESH_PITCH_MM, build_mesh
from .point_to_point import (
    Segment,
    TraceSegment,
    ViaSegment,
    build_point_to_point,
)
from .pour import PourGeometry, Tie, ViaStation, pour_geometry

__all__ = [
    # point-to-point
    "TraceSegment",
    "ViaSegment",
    "Segment",
    "build_point_to_point",
    # ladder
    "LADDER_MIN_ASPECT",
    "build_ladder",
    # mesh
    "DEFAULT_MESH_PITCH_MM",
    "build_mesh",
    # shared pour inputs
    "PourGeometry",
    "pour_geometry",
    "ViaStation",
    "Tie",
]
