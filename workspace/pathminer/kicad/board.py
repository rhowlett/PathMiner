# v0.1
"""pathminer.kicad.board — parse a ``.kicad_pcb`` file into board geometry.

Session 06 (ARCH-003 closure). Mechanical extraction of the geometry-
harvesting half of v0.13's ``BoardNets`` (``tools/pcb_trace_resistance.py``
lines 3776-3992) into the ``pathminer.models.board`` domain types. The
graph-building half of ``BoardNets`` (``build_graph``, pour ladder/mesh)
is network-builder scope (ARCH-004, Session 07) and is intentionally not
extracted here.

Layer contract (ARCH-002): imports `pathminer.core` (geometry) and
`pathminer.kicad` (sexpr, stackup) only. No Qt, no wx, no upward imports.

Provenance map (v0.13 symbol -> this module):
    BoardNets.__init__ (net/track/via/pad/zone harvesting) -> parse_board
    BoardNets._split_tracks_at_vias                         -> _split_tracks_at_vias
    parse_pours / Pour                                       -> _parse_pours
    _arc_length_mm                                           -> pathminer.core.geometry.arc_length
    _q                                                        -> _q (kept module-private, same Q=4)
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from pathminer.core.geometry import arc_length
from pathminer.kicad.sexpr import parse_sexpr
from pathminer.kicad.stackup import Stackup, load_stackup, manual_stackup
from pathminer.models.board import Pad, Point, Pour, Track, Via

# Coordinate quantisation: decimal places in mm (0.1 um). Matches v0.13's
# module-level ``Q = 4`` / ``_q()`` in tools/pcb_trace_resistance.py.
_Q = 4


def _q(v: float) -> float:
    return round(float(v), _Q)


@dataclass
class ParsedBoard:
    """Raw board geometry harvested from one ``.kicad_pcb`` file.

    Internal to `pathminer.kicad`; `pathminer.kicad.source.FileBoardSource`
    wraps this to implement the `pathminer.models.board.BoardSource`
    protocol. Not itself part of the public `BoardSource` surface.
    """

    path: str
    net_names: dict[int, str]
    tracks: list[Track]
    vias: list[Via]
    pads: list[Pad]
    pours: dict[int, Pour]
    zone_nets: set[int]
    stackup: Stackup
    notes: list[str] = field(default_factory=list)


def parse_board(path: str) -> ParsedBoard:
    """Parse a ``.kicad_pcb`` file into a `ParsedBoard`.

    Raises
    ------
    OSError
        If the file cannot be read.
    ValueError
        If the file's root node is not ``kicad_pcb``.
    """
    text = open(path, "r", encoding="utf-8").read()
    root = parse_sexpr(text)
    if root.head != "kicad_pcb":
        raise ValueError("not a .kicad_pcb file")

    notes: list[str] = []

    net_names: dict[int, str] = {}
    for n in root.findall("net"):
        k = n.kids()
        if k:
            net_names[int(k[0])] = str(k[1]) if len(k) > 1 else ""

    tracks: list[Track] = []
    for s in root.findall("segment"):
        net = s.val("net", cast=int)
        if net is None:
            continue
        a = s.get("start").kids()
        b = s.get("end").kids()
        p1 = (_q(a[0]), _q(a[1]))
        p2 = (_q(b[0]), _q(b[1]))
        length_mm = math.hypot(p2[0] - p1[0], p2[1] - p1[1])
        tracks.append(
            Track(
                net=net,
                layer=str(s.get("layer").kids()[0]),
                start=p1,
                end=p2,
                width_mm=s.val("width"),
                length_mm=length_mm,
                shape="line",
            )
        )
    for s in root.findall("arc"):
        net = s.val("net", cast=int)
        if net is None:
            continue
        a = s.get("start").kids()
        m = s.get("mid").kids()
        b = s.get("end").kids()
        p1 = (_q(a[0]), _q(a[1]))
        p2 = (_q(b[0]), _q(b[1]))
        length_mm = arc_length(p1[0], p1[1], float(m[0]), float(m[1]), p2[0], p2[1])
        tracks.append(
            Track(
                net=net,
                layer=str(s.get("layer").kids()[0]),
                start=p1,
                end=p2,
                width_mm=s.val("width"),
                length_mm=length_mm,
                shape="arc",
            )
        )

    vias: list[Via] = []
    for v in root.findall("via"):
        net = v.val("net", cast=int)
        if net is None:
            continue
        a = v.get("at").kids()
        kinds = [c for c in v.kids() if isinstance(c, str)]
        via_type = "micro" if "micro" in kinds else ("blind" if "blind" in kinds else "through")
        lay = v.get("layers")
        vias.append(
            Via(
                net=net,
                at=(_q(a[0]), _q(a[1])),
                size_mm=v.val("size"),
                drill_mm=v.val("drill"),
                declared_layers=tuple(str(x) for x in lay.kids()) if lay else (),
                via_type=via_type,
            )
        )

    pads: list[Pad] = []
    for fp in root.findall("footprint"):
        at = fp.get("at").kids()
        fx, fy = float(at[0]), float(at[1])
        frot = math.radians(-float(at[2])) if len(at) > 2 else 0.0
        ref = ""
        for pr in fp.findall("property"):
            k = pr.kids()
            if k and str(k[0]) == "Reference":
                ref = str(k[1]) if len(k) > 1 else ""
        for p in fp.findall("pad"):
            net = p.val("net", cast=int)
            if net is None:
                continue
            lay = p.get("layers")
            lays = [str(x) for x in lay.kids()] if lay else []
            cu = tuple(l for l in lays if ".Cu" in l or l == "*.Cu")
            if not cu:
                continue
            pat = p.get("at").kids()
            px, py = float(pat[0]), float(pat[1])
            ax = fx + px * math.cos(frot) - py * math.sin(frot)
            ay = fy + px * math.sin(frot) + py * math.cos(frot)
            pf = p.get("pinfunction")
            fn = str(pf.kids()[0]) if pf and pf.kids() else ""
            pads.append(
                Pad(
                    net=net,
                    at=(_q(ax), _q(ay)),
                    layers=cu,
                    ref=ref,
                    pad_name=str(p.kids()[0]) if p.kids() else "",
                    pin_function=fn,
                )
            )

    zone_nets: set[int] = set()
    for z in root.findall("zone"):
        n = z.val("net", cast=int)
        if n is not None:
            zone_nets.add(n)

    pours = _parse_pours(root)

    tracks, split_notes = _split_tracks_at_vias(tracks, vias)
    notes.extend(split_notes)

    try:
        stackup = load_stackup(path)
    except ValueError as exc:
        stackup = manual_stackup()
        notes.append(
            f"no usable (stackup) block on this board; using an estimated "
            f"manual stackup ({exc})"
        )

    return ParsedBoard(
        path=path,
        net_names=net_names,
        tracks=tracks,
        vias=vias,
        pads=pads,
        pours=pours,
        zone_nets=zone_nets,
        stackup=stackup,
        notes=notes,
    )


def _parse_pours(root) -> dict[int, Pour]:
    """Filled zone copper, grouped by net then layer.

    Extracted from v0.13 ``parse_pours`` (tools/pcb_trace_resistance.py
    lines 1484-1502); geometry summary (principal axis, aspect ratio) is
    intentionally not computed here — see `pathminer.models.board.Pour`.
    """
    by_net: dict[int, dict[str, list[Point]]] = {}
    for z in root.findall("zone"):
        net = z.val("net", cast=int)
        if net is None:
            continue
        for fp in z.findall("filled_polygon"):
            lay = fp.get("layer")
            if lay is None or not lay.kids():
                continue
            layer = str(lay.kids()[0])
            pts = fp.get("pts")
            if pts is None:
                continue
            poly = [(_q(c.kids()[0]), _q(c.kids()[1])) for c in pts.findall("xy")]
            if len(poly) >= 3:
                by_net.setdefault(net, {}).setdefault(layer, []).extend(poly)
    return {n: Pour(net=n, fills=f) for n, f in by_net.items()}


def _split_tracks_at_vias(
    tracks: list[Track], vias: list[Via]
) -> tuple[list[Track], list[str]]:
    """KiCad does not break a track where a via lands on it mid-run, so a
    stitching array is invisible to endpoint-only landing detection. Split
    every track at any via lying on its interior.

    Extracted from v0.13 ``BoardNets._split_tracks_at_vias``
    (tools/pcb_trace_resistance.py lines 3852-3887).
    """
    notes: list[str] = []
    by_net: dict[int, list[Point]] = {}
    for v in vias:
        by_net.setdefault(v.net, []).append(v.at)

    out: list[Track] = []
    for track in tracks:
        (ax, ay), (bx, by) = track.start, track.end
        dx, dy = bx - ax, by - ay
        d2 = dx * dx + dy * dy
        hits: list[tuple[float, Point]] = []
        if d2 > 0:
            for pt in by_net.get(track.net, []):
                t = ((pt[0] - ax) * dx + (pt[1] - ay) * dy) / d2
                if not (1e-9 < t < 1 - 1e-9):
                    continue
                cx, cy = ax + t * dx, ay + t * dy
                if math.hypot(pt[0] - cx, pt[1] - cy) <= 1e-4:
                    hits.append((t, pt))
        if not hits:
            out.append(track)
            continue
        hits.sort()
        notes.append(
            f"track {track.start}->{track.end} on {track.layer} split at "
            f"{len(hits)} mid-run via(s)"
        )
        prev, prev_t = track.start, 0.0
        for t, pt in hits:
            out.append(
                Track(
                    net=track.net,
                    layer=track.layer,
                    start=prev,
                    end=pt,
                    width_mm=track.width_mm,
                    length_mm=track.length_mm * (t - prev_t),
                    shape=track.shape,
                )
            )
            prev, prev_t = pt, t
        out.append(
            Track(
                net=track.net,
                layer=track.layer,
                start=prev,
                end=track.end,
                width_mm=track.width_mm,
                length_mm=track.length_mm * (1.0 - prev_t),
                shape=track.shape,
            )
        )
    return out, notes
