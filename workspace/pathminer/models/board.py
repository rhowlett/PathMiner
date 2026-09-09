# v0.1
"""pathminer.models.board — board domain contracts (ARCH-003).

Defines the KiCad-agnostic vocabulary a board adapter exposes to the rest
of PathMiner: nets, copper segments (tracks/arcs), vias, pads, filled-
copper pours, the physical stackup, and the stable `BoardSource` protocol
itself.

Two adapters are required by the project specification (S7.1):
`FileBoardSource` (`pathminer.kicad.source`, standalone/CLI parsing of a
``.kicad_pcb`` file, backed by the parser in `pathminer.kicad.board`) and
a future `LiveKiCadBoardSource` (the plugin, backed by `pcbnew`). Every
analysis above this layer must accept either without branching (ARCH-003
Done-when clause).

This module is pure data plus the `Stackup` type already defined in
`pathminer.kicad.stackup` (Session 05); it parses nothing itself.  A board
adapter converts raw board geometry into these types.

Design contract (`.ai/planning/PathMiner_Project_Specification.md` S7.1,
S9.4; ADR-006):

- `REF.PAD` (e.g. "U9.5", "Q3.S") is the stable design identifier.
- Net numbers, route coordinates, layer assignments, and track/via UUIDs
  are transient navigation aids, never persistent identity.
- Net *name* is stored only to detect drift on rerun (S12.3); it is never
  the primary lookup key.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Optional, Protocol, Sequence, Tuple, runtime_checkable

from pathminer.kicad.stackup import Stackup

Point = Tuple[float, float]

__all__ = [
    "Point",
    "Net",
    "Track",
    "Via",
    "Pad",
    "TerminalAlias",
    "Terminal",
    "Pour",
    "PadDrift",
    "BoardSourceError",
    "PadNotFoundError",
    "NetDriftError",
    "ref_pad_name",
    "BoardSource",
]


# ---------------------------------------------------------------------------
# Raw geometry records
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Net:
    """One declared KiCad net.

    `number` is the transient in-file net code (S9.4: never a persistent
    identifier); `name` is the human-readable, drift-checked label.
    """

    number: int
    name: str


@dataclass(frozen=True)
class Track:
    """One straight or arc copper segment.

    `shape` is ``"line"`` or ``"arc"``.  `length_mm` is the true length
    (arc length, not the chord) for arcs (S7.1: "true length").
    """

    net: int
    layer: str
    start: Point
    end: Point
    width_mm: Optional[float]
    length_mm: float
    shape: str = "line"


@dataclass(frozen=True)
class Via:
    """One via barrel.

    `declared_layers` is the via token's own layer pair/range — NOT the
    electrical span, which depends on what actually lands on the via
    (S8.4).  Resolving that span is the network builder's job
    (Session 07), not the board adapter's.
    """

    net: int
    at: Point
    size_mm: Optional[float]
    drill_mm: Optional[float]
    declared_layers: Tuple[str, ...]
    via_type: str = "through"  # "through" | "blind" | "micro"


@dataclass(frozen=True)
class Pad(object):
    """One raw physical pad, as parsed from a footprint.

    Several physical pads may share one electrical identity (a split
    thermal pad, a multi-pad supply pin) — see `Terminal`.
    """

    net: int
    at: Point
    layers: Tuple[str, ...]
    ref: str
    pad_name: str
    pin_function: str


@dataclass(frozen=True)
class Pour:
    """One net's filled copper, one polygon list per layer.

    Pure geometry storage: pour axis/aspect analysis and mesh/ladder
    rasterization belong to the network-builder layer (Session 07,
    ARCH-004), which consumes `fills` via `pathminer.core.geometry`.
    """

    net: int
    fills: Mapping[str, Sequence[Point]]

    def layers(self) -> list[str]:
        return list(self.fills)


# ---------------------------------------------------------------------------
# Stable terminal identity (ARCH-003 / DATA-004)
# ---------------------------------------------------------------------------


def ref_pad_name(ref: str, pad_name: str, pin_function: str) -> str:
    """The stable `REF.PAD` identifier for one pad (S7.1, S9.4).

    Prefers the pin function when present (e.g. ``"Q3.S"``), otherwise the
    bare pad name (e.g. ``"U9.5"``), matching the v0.13 terminal-naming
    convention so persisted v0.13 selections keep resolving.
    """
    if ref and pin_function:
        return f"{ref}.{pin_function}"
    if ref:
        return f"{ref}.{pad_name}"
    return f"pad {pad_name}"


@dataclass(frozen=True)
class TerminalAlias:
    """A physical pad collapsed into a `Terminal` because it shares the
    same `REF.PAD` name (S7.1)."""

    pad_name: str
    point: Point


@dataclass(frozen=True)
class Terminal:
    """One electrical terminal on the board: a stable `REF.PAD` name plus
    every physical pad collapsed into it.

    A footprint often repeats a pin name across pads — a thermal pad split
    into several, or a multi-pad supply pin. Those are one electrical
    terminal, so `pad("REF.PAD")` must resolve to one `Terminal`, not one
    row per physical pad.
    """

    ref_pad: str
    net: int
    point: Point
    layers: Tuple[str, ...]
    ref: str
    pad_name: str
    pin_function: str
    aliases: Tuple[TerminalAlias, ...] = ()


# ---------------------------------------------------------------------------
# Drift diagnostics (S12.3, ADR-006, DATA-004 resolution slice)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PadDrift:
    """Result of comparing a persisted `REF.PAD` / net-name pair against
    the current board (S12.3)."""

    ref_pad: str
    expected_net: str
    current_net: str
    drifted: bool


class BoardSourceError(Exception):
    """Base class for `BoardSource` lookup/drift failures."""


class PadNotFoundError(BoardSourceError, KeyError):
    """No terminal named `REF.PAD` exists on this board."""


class NetDriftError(BoardSourceError):
    """`REF.PAD` resolves, but its current net name does not match the net
    name recorded at save time (S12.3). Carries the `PadDrift` so a caller
    can offer Abort / Continue Once / Update File (GUI) or
    `--accept-net-changes` (CLI) without re-resolving."""

    def __init__(self, drift: PadDrift) -> None:
        self.drift = drift
        super().__init__(
            f"{drift.ref_pad}: recorded net {drift.expected_net!r} does not "
            f"match current net {drift.current_net!r}"
        )


# ---------------------------------------------------------------------------
# BoardSource protocol (ARCH-003)
# ---------------------------------------------------------------------------


@runtime_checkable
class BoardSource(Protocol):
    """Board-geometry provider (ARCH-003, project specification S7.1).

    `FileBoardSource` (`pathminer.kicad.source`) is the standalone/CLI
    implementation. A future `LiveKiCadBoardSource` plugin adapter must
    satisfy the same protocol so analysis code never branches on which
    adapter supplied the board.
    """

    @property
    def stackup(self) -> Stackup:
        """The board's physical copper/dielectric stackup."""
        ...

    def nets(self) -> Sequence[Net]:
        """Every declared net, by stable name and transient KiCad code."""
        ...

    def net_name(self, net: int) -> str:
        """The current name of net *net*, or a placeholder if unknown."""
        ...

    def tracks(self, net: Optional[int] = None) -> Sequence[Track]:
        """Straight and arc copper segments, optionally filtered to one
        net."""
        ...

    def vias(self, net: Optional[int] = None) -> Sequence[Via]:
        """Via barrels, optionally filtered to one net."""
        ...

    def pads(self, net: Optional[int] = None) -> Sequence[Pad]:
        """Raw physical pads, optionally filtered to one net."""
        ...

    def pours(self, net: Optional[int] = None) -> Mapping[int, Pour]:
        """Filled copper polygons by net (and, within each `Pour`, by
        layer)."""
        ...

    def terminals(self, net: int, dedupe: bool = True) -> Sequence[Terminal]:
        """Pads on *net* as electrical terminals, one entry per distinct
        `REF.PAD` name by default (`dedupe=True`)."""
        ...

    def pad(self, ref_pad: str) -> Terminal:
        """Direct stable lookup by `REF.PAD` (e.g. ``"U9.5"``).

        Raises `PadNotFoundError` when no terminal has that name.
        """
        ...

    def check_drift(self, ref_pad: str, expected_net: str) -> PadDrift:
        """Non-raising drift check: resolve *ref_pad* and compare its
        current net name against *expected_net* (S12.3).

        Raises `PadNotFoundError` when *ref_pad* does not exist at all —
        that is a broken identity, not drift.
        """
        ...

    def resolve(self, ref_pad: str, expected_net: Optional[str] = None) -> Terminal:
        """Strict resolution: raises `PadNotFoundError` if *ref_pad* does
        not exist, and `NetDriftError` if *expected_net* is given and does
        not match the pad's current net (CLI default-fail behavior,
        S12.3)."""
        ...
