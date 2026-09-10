# v0.1
"""pathminer.kicad.source — FileBoardSource, the file-backed BoardSource.

Session 06 (ARCH-003 closure). Implements the
`pathminer.models.board.BoardSource` protocol by wrapping the parser in
`pathminer.kicad.board`. Also implements the stable `REF.PAD` terminal
lookup and net-drift diagnostics (S7.1, S12.3, ADR-006) that the project
specification requires of every `BoardSource` adapter.

A future `LiveKiCadBoardSource` (the plugin, backed by `pcbnew`) belongs
here or in a sibling module once the plugin session (AUTO-004) needs it;
it must satisfy the same protocol.

Layer contract (ARCH-002): imports `pathminer.kicad` and
`pathminer.models` only. No Qt, no wx.
"""

from __future__ import annotations

from typing import Mapping, Optional, Sequence

from pathminer.kicad.board import ParsedBoard, parse_board
from pathminer.kicad.stackup import Stackup
from pathminer.models.board import (
    AmbiguousPadError,
    Net,
    NetDriftError,
    Pad,
    PadDrift,
    PadNotFoundError,
    Pour,
    Terminal,
    TerminalAlias,
    Track,
    Via,
    ref_pad_name,
)

__all__ = ["FileBoardSource"]


def _terminals_for_net(pads: Sequence[Pad], net: int, dedupe: bool) -> list[Terminal]:
    """Build `Terminal` rows for the pads on one net.

    Extracted from v0.13 ``BoardNets.terminals`` (tools/pcb_trace_resistance.py
    lines 3968-3992): one row per distinct `REF.PAD` name by default;
    later pads with the same name are collapsed into ``aliases`` rather
    than reported as separate terminals.
    """
    raw = [p for p in pads if p.net == net]
    if not dedupe:
        return [
            Terminal(
                ref_pad=ref_pad_name(p.ref, p.pad_name, p.pin_function),
                net=p.net,
                point=p.at,
                layers=p.layers,
                ref=p.ref,
                pad_name=p.pad_name,
                pin_function=p.pin_function,
                aliases=(),
            )
            for p in raw
        ]
    out: list[Terminal] = []
    seen: dict[str, int] = {}
    for p in raw:
        name = ref_pad_name(p.ref, p.pad_name, p.pin_function)
        idx = seen.get(name)
        if idx is None:
            seen[name] = len(out)
            out.append(
                Terminal(
                    ref_pad=name,
                    net=p.net,
                    point=p.at,
                    layers=p.layers,
                    ref=p.ref,
                    pad_name=p.pad_name,
                    pin_function=p.pin_function,
                    aliases=(),
                )
            )
        else:
            existing = out[idx]
            out[idx] = Terminal(
                ref_pad=existing.ref_pad,
                net=existing.net,
                point=existing.point,
                layers=existing.layers,
                ref=existing.ref,
                pad_name=existing.pad_name,
                pin_function=existing.pin_function,
                aliases=existing.aliases + (TerminalAlias(pad_name=p.pad_name, point=p.at),),
            )
    return out


def _build_pad_index(
    pads: Sequence[Pad],
) -> tuple[dict[str, Terminal], dict[str, tuple[int, ...]]]:
    """Board-wide `REF.PAD` -> `Terminal` index, plus any ambiguous names.

    Pads sharing one `REF.PAD` name are collapsed into one electrical
    terminal (S7.1) only when they also share one net -- `_terminals_for_net`
    already performs that same-net collapse (with aliases) for every net
    independently, so a `REF.PAD` name can legitimately appear at most
    once per net group here. If it appears again from a *different* net
    group, the two pads are not actually one electrical node and
    collapsing them would silently misreport one net as the other's.

    Real board data can and does contain this: e.g. the IP5385 reference
    board's ``LED1`` footprint gives every one of its five physically
    distinct, differently-netted pads the same generic pin function
    ``"1"``, so all five collapse to the name ``"LED1.1"``. Bricking the
    *entire* board's terminal lookup over one such component would defeat
    the point of a board adapter, so the ambiguous name is excluded from
    `index` and returned separately in `ambiguous`; a lookup naming it
    specifically fails with `AmbiguousPadError` (see `FileBoardSource.pad`),
    while every other terminal on the board still resolves normally.
    """
    by_net: dict[int, list[Pad]] = {}
    for p in pads:
        by_net.setdefault(p.net, []).append(p)

    index: dict[str, Terminal] = {}
    net_of_name: dict[str, int] = {}
    ambiguous: dict[str, set[int]] = {}
    for net, net_pads in sorted(by_net.items()):
        for terminal in _terminals_for_net(net_pads, net, dedupe=True):
            name = terminal.ref_pad
            if name in ambiguous:
                ambiguous[name].add(net)
                continue
            if name in index:
                ambiguous[name] = {net_of_name[name], net}
                del index[name]
                del net_of_name[name]
                continue
            index[name] = terminal
            net_of_name[name] = net
    return index, {name: tuple(sorted(nets)) for name, nets in ambiguous.items()}


class FileBoardSource:
    """`BoardSource` backed by a parsed ``.kicad_pcb`` file.

    Parsing happens once, eagerly, at construction. `notes` exposes
    parser-level diagnostics (mid-run via splits, an estimated stackup
    fallback) that are not part of the `BoardSource` protocol itself but
    are useful for callers building richer diagnostics later
    (UI-014/AUTO-006).

    A `REF.PAD` name that collides across different nets (see
    `_build_pad_index`) does *not* fail construction -- every other
    terminal on the board must stay usable -- but `pad()` (and therefore
    `check_drift`/`resolve`) raises `AmbiguousPadError` if that specific
    name is looked up.
    """

    def __init__(self, path: str) -> None:
        self.path = path
        self._parsed: ParsedBoard = parse_board(path)
        self._pad_index: dict[str, Terminal]
        self._ambiguous_pads: dict[str, tuple[int, ...]]
        self._pad_index, self._ambiguous_pads = _build_pad_index(self._parsed.pads)

    @property
    def notes(self) -> list[str]:
        return list(self._parsed.notes)

    @property
    def stackup(self) -> Stackup:
        return self._parsed.stackup

    def nets(self) -> Sequence[Net]:
        return [Net(number=n, name=name) for n, name in sorted(self._parsed.net_names.items())]

    def net_name(self, net: int) -> str:
        return self._parsed.net_names.get(net, f"<net {net}>")

    def tracks(self, net: Optional[int] = None) -> Sequence[Track]:
        if net is None:
            return list(self._parsed.tracks)
        return [t for t in self._parsed.tracks if t.net == net]

    def vias(self, net: Optional[int] = None) -> Sequence[Via]:
        if net is None:
            return list(self._parsed.vias)
        return [v for v in self._parsed.vias if v.net == net]

    def pads(self, net: Optional[int] = None) -> Sequence[Pad]:
        if net is None:
            return list(self._parsed.pads)
        return [p for p in self._parsed.pads if p.net == net]

    def pours(self, net: Optional[int] = None) -> Mapping[int, Pour]:
        if net is None:
            return dict(self._parsed.pours)
        pour = self._parsed.pours.get(net)
        return {net: pour} if pour is not None else {}

    def terminals(self, net: int, dedupe: bool = True) -> Sequence[Terminal]:
        return _terminals_for_net(self._parsed.pads, net, dedupe)

    def pad(self, ref_pad: str) -> Terminal:
        if ref_pad in self._ambiguous_pads:
            raise AmbiguousPadError(ref_pad, self._ambiguous_pads[ref_pad])
        try:
            return self._pad_index[ref_pad]
        except KeyError:
            raise PadNotFoundError(
                f"no pad named {ref_pad!r} on this board"
            ) from None

    def check_drift(self, ref_pad: str, expected_net: str) -> PadDrift:
        terminal = self.pad(ref_pad)  # raises PadNotFoundError if missing
        current_net = self.net_name(terminal.net)
        return PadDrift(
            ref_pad=ref_pad,
            expected_net=expected_net,
            current_net=current_net,
            drifted=current_net != expected_net,
        )

    def resolve(self, ref_pad: str, expected_net: Optional[str] = None) -> Terminal:
        terminal = self.pad(ref_pad)  # raises PadNotFoundError if missing
        if expected_net is not None:
            drift = self.check_drift(ref_pad, expected_net)
            if drift.drifted:
                raise NetDriftError(drift)
        return terminal
