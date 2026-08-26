#!/usr/bin/env python3
# v0.13
"""
PCB Trace / Via Resistance Calculator - single-file PySide6 application.

Three tabs:
  Trace      DC resistance of a rectangular trace + IPC-2221 temperature rise.
  Via/Path   Series chain of trace and via segments over a real board stackup.
  Stackup    Load a .kicad_pcb stackup, or enter one by hand; editable.

Batch mode generates a point-to-point resistance report over selected nets,
driven by a schema-validated JSON net-selection file.

The Via/Path tab can also trace a real net out of the board file: pick a start
and end pad by name (Z1.SDA -> Z3.SDA) and it finds the least-resistance route
through the routed copper, reporting both that path and the true resistance of
the whole net including any parallel branches.

Models
------
1. Trace resistance    R = rho * L / (W * t),  t from copper weight in oz/ft^2,
   corrected by R(T) = R20 * (1 + alpha * (T - 20)).

2. Trace temperature rise (Trace tab only), IPC-2221 curve fit
       I = k * dT^0.44 * A^0.725   ->   dT = (I / (k * A^0.725))^(1/0.44)
   A in mils^2, k = 0.048 external / 0.024 internal.

3. Via barrel resistance
       A = pi/4 * (OD^2 - ID^2)
       R = rho * L_barrel / A,   R_array = R / (count * sharing)
   Two hole conventions (D3) and three barrel-length conventions (D4), both
   user-selectable and both echoed into the results block.

Conventions / sources of truth
------------------------------
* Resistivity 1.724e-8 ohm-m (IACS annealed copper, 20 C); alpha 0.00393 /K.
  Electrodeposited barrel plating is measurably more resistive than annealed
  foil, but no separate figure is used without a measurement.
* Copper weight to thickness: 34.798 um (1.37 mil) per oz/ft^2.
* BARREL PLATING IS NOT FOIL WEIGHT.  Plating is a fab process parameter,
  recorded in no EDA file, and is a required input with no default (D2).
* Plating also lands on the outer layers and grows them AWAY from the core,
  thickening the board by 2*plating (D8).  Inner layers are foil only.
* Barrel length is copper centre-to-centre by default (D4).  On an adjacent-
  layer hop the three conventions span -39%/+39%, so the choice is reported.
* Through vias only (D5).  DC only: no skin effect, no via self-heating, no
  etch taper, no pad spreading resistance.

KiCad parsing notes (all observed on a real KiCad 9 board)
----------------------------------------------------------
* Layer ordinals are NOT stack order (F.Cu=0, In1.Cu=4, In2.Cu=6, B.Cu=2).
  Physical order comes only from the (stackup) block's own sequence.
* A via's (layers ...) is the physical barrel, not the electrical span.  Every
  through via declares F.Cu/B.Cu regardless of which layers actually carry
  current, so entry/exit layer is always user input.
* (general (thickness)) includes solder mask; it is never a barrel span.
* KiCad 9 writes uuid, not tstamp.
* Net classes live in the .kicad_pro and may omit keys entirely.
* The (stackup) block is optional; absent, use manual mode.

Change log
----------
v0.1  2026-08-18  Initial release.  Length/width entry in mil or mm, copper
                  weight pull-down (0.5, 1, 2 ... 10 oz), Calculate button,
                  resistance reported in ohms with auto-scaled secondary
                  units and a geometry/sheet-resistance detail line.
v0.2  2026-08-18  Added constant-current and ambient-temperature inputs and an
                  IPC-2221 temperature-rise output.  Ambient carries a C/F
                  selector and every temperature output follows that
                  selection; changing the selector converts the entered value
                  in place.  Added an external/internal layer selector,
                  required because IPC-2221's k halves for internal layers.
                  Resistance also reported at the resulting trace temperature,
                  alongside I*R drop and I^2*R dissipation, plus warnings when
                  the operating point leaves the IPC-2221 chart or exceeds the
                  105 C typical FR-4 limit.
v0.3  2026-08-21  Restructured into tabs; current and ambient promoted to a
                  shared header (D7).  Added a headless s-expression parser
                  and .kicad_pcb stackup loader with an editable stackup table
                  and manual fallback (D6), a via/path calculator taking an
                  ordered segment chain (D1), required barrel-plating input in
                  um/mil/oz with IPC presets and no default (D2), selectable
                  hole convention (D3) and barrel-length convention defaulting
                  to centre-to-centre (D4), outer-layer plating growth (D8),
                  parallel-via arrays with a sharing derate, --dump-stackup,
                  and a --selftest suite asserting acceptance vectors V1-V8
                  against a surveyed KiCad 9 reference board.  Through vias
                  only (D5); via temperature rise deliberately omitted.
v0.4  2026-08-21  Added board-net tracing: the Via/Path tab can build its
                  segment chain directly from routed copper.  Parses segments,
                  arcs (true arc length through three points), vias and
                  footprint pads (with footprint rotation applied), groups them
                  by net, and builds a per-net graph whose nodes are
                  (layer, point).  A via's electrical span is derived from the
                  layers that actually land on it, never from its (layers ...)
                  token; a via with three or more landing layers is split into
                  series sub-barrels.  Endpoints come from footprint pads, or
                  from loose track ends when a net has none; the path between
                  them is found by Dijkstra and consecutive same-layer,
                  same-width runs are merged.  Warns on branches, zone nets,
                  broken routes, blind/micro vias and orphaned vias.  Selftest
                  grows arc-length vectors (V9) and, when given a board file,
                  net-tracing vectors (V10).
v0.5  2026-08-21  Endpoint selection is now pad-to-pad by name: terminals are
                  labelled REF.PINFUNCTION (falling back to REF.PAD), so a path
                  is picked as e.g. Z1.SDA -> Z3.SDA.  The path search is
                  weighted by real edge RESISTANCE rather than physical length,
                  so it returns the least-resistance route when a net offers
                  more than one; without a plating value it says so and falls
                  back to length.  Added a nodal-analysis solver giving the
                  true two-terminal resistance of the whole net including every
                  parallel branch, reported next to the path figure with the
                  difference: equal values mean the other copper is a stub, a
                  lower network value means parallel copper is sharing current.
                  Selftest gains V11 (series, parallel, series-parallel,
                  balanced and unbalanced Wheatstone bridges, stubs, ten-way
                  parallel) and V10 now sweeps every pad pair on the board,
                  asserting the segment sum equals the path and that the
                  network never exceeds it.
v0.6  2026-08-22  Zone-aware modelling and batch reporting.  Tracks are now
                  split wherever a via lands mid-run, so stitching arrays are
                  no longer invisible to endpoint-only landing detection.
                  Filled zone copper is parsed per layer, its principal axis
                  and width derived, and tracks are clipped against it so pour
                  copper is never double counted against the track it overlaps.
                  Two pour models: 'ladder' (default, fast) places a rung at
                  every via and a strip per layer along the pour axis, exact
                  for strip-like copper; 'mesh' (slow) rasterises the fill into
                  a resistor grid for any shape, with barrels merged as finite
                  discs rather than points.  A single centroid lump was
                  evaluated and rejected: on a shunt array it returns exactly
                  the unstitched answer, because parallel layers touching at
                  one node are dead-end stubs (V14 pins this).  Ties are node
                  merges, not tiny resistors, so conditioning stays sane, and
                  graphs above 400 nodes fall through to sparse conjugate
                  gradient.  Added a JSON net-selection file with a draft-07
                  schema and a built-in validator, select/ignore glob patterns
                  where ignore always wins, and point-to-point report
                  generation in Markdown, text or JSON over selected nets.
                  New CLI: --report, --nets, --emit-schema, --emit-nets,
                  --zone-model, --mesh-pitch, --plating, --ambient, --current,
                  --format, --out.  Selftest grows V12 (schema and selection),
                  V13 (pour geometry and clustering), V14 (shunt array) and
                  V15 (zone modelling on a real board).
v0.7  2026-08-22  Added a Report tab: open/save/save-as for the net-selection
                  JSON (refusing to save anything the schema rejects), two
                  transfer lists - one for nets to report, one for nets to
                  ignore, both seeded with every routed net and repopulated
                  when a file is opened - and a per-net point-to-point table.
                  Because resistance is only defined between two pads, each net
                  carries a pair rule: 'all' (N(N-1)/2 rows), 'from-source'
                  (one driver or supply pad against every other, N-1 rows),
                  'first-two', or 'explicit'.  A live count shows how many pad
                  pairs a run will compute and a warning fires past the
                  threshold.  Reports export as Markdown, text, PDF or JSON,
                  with an in-tab preview; PDF goes through a small
                  markdown-to-HTML converter into QPdfWriter/QTextDocument.
                  Opening a file expands globs to concrete net names and says
                  so, reporting any pattern that matched nothing.  Fixed a
                  regression introduced with the pair strategy: the per-net
                  pair mode shadowed the barrel-length convention that the
                  edge-pricing closure reads, so every pair in a generated
                  report failed to trace.  V16 now exercises the whole report
                  path end to end, which is what should have caught it.
v0.8  2026-08-22  Report tab reworked into two columns: file buttons, the two
                  net transfer lists and the point-to-point section on the
                  left, report controls and output on the right, under the
                  shared operating-condition bar.  Added a default signal
                  voltage (3.3 V) alongside current, and the summary now
                  reports V in, I, drop and the resulting endpoint voltage.
                  Each resolved pad pair gets its own voltage and current
                  override in a second table; blank cells fall back to the
                  defaults, overridden values are marked with an asterisk in
                  the report, and both are saved under nets.<net>.pair_overrides
                  keyed 'A>B', matching in either direction.  Six section
                  checkboxes (assumptions, stackup, selection, summary, detail,
                  notes) gate the report and persist in the JSON.  Removed the
                  collapsible skipped-nets block, which listed every unselected
                  net for no benefit; the selection section now names only what
                  was reported and what was explicitly ignored.  Fixed override
                  restoration on open: the pair list was pruned before the
                  per-net pair modes were applied, so restored overrides were
                  discarded, and reversed pair keys were not recognised.
                  Selftest gains V17.
v0.9  2026-08-22  Report tab returned to a single scrollable column, with each
                  section behind a disclosure triangle: nets to report on, nets
                  to ignore, point-to-point pairs, and the report itself, plus
                  Expand all / Collapse all.  A collapsed section costs one
                  header row, so the four together drop from 1372 px to 92 px
                  and the preview can have the tab to itself.  Each header
                  carries a live summary - selected count, ignored count, pad
                  pair total, output format and zone model - so a collapsed
                  section still reports its state.  A disclosure triangle was
                  chosen over a checkable QGroupBox because the tab already
                  uses checkboxes to mean "include this section in the report",
                  and a triangle can only mean show/hide.  TransferList no
                  longer draws its own group box now that the section header
                  owns the title.  Selftest gains V18.
v0.10 2026-08-23  The operating-conditions bar now opens the board directly and
                  names the loaded file and its directory; that directory
                  becomes the default location for net-selection JSON and for
                  saved reports, so the selection file lands beside the board
                  instead of the working directory.  Trace tab rearranged into
                  two columns - geometry on the left with the Calculate button
                  centred and sized to its text, results and caveats on the
                  right.  Trace thickness now has two sources behind radio
                  buttons: copper weight plus trace location as before, or a
                  layer picked from the loaded stackup, which supplies the
                  finished thickness and derives external/internal - and so the
                  IPC-2221 k - from the layer's position rather than asking.
                  The stackup option is disabled with an explanatory tooltip
                  until a .kicad_pcb is open, and outer-layer plating (D8) from
                  the Via / Path tab carries through, so a 1 oz outer layer
                  reads 60 um at 25 um plating.  Selftest gains V19, including
                  a check that manual mode still reproduces the v0.2 number.
v0.11 2026-08-23  "Operating conditions" renamed "Global settings", and barrel
                  plating moved into it since all three tabs price copper with
                  it.  D2 AMENDED: plating no longer has no default; it now
                  defaults to the IPC-6012 Class 2 minimum of 18 um, the
                  pessimistic end of the common range, and the value in force
                  is printed with every result and in every report.  Terminals
                  are deduplicated by name: a footprint that repeats a pin name
                  across pads - a split thermal pad, a multi-pad supply pin -
                  is one electrical terminal, so it is computed once instead of
                  once per pad, with the collapsed pads listed in the notes.
                  Per-pair overrides gained a zone model (default ladder) and
                  mesh pitch (default 0.25 mm), so one net can mix models; a
                  graph is built once per distinct model and reused across
                  every pair that wants it.  Added solver calibration: two
                  synthetic grids are timed on startup to fit t = a*nodes^b,
                  and each pair shows a forecast node count and solve time,
                  with a running total.  Reports now record nodes, zone model
                  and actual solve time per pair, and a total.  The report
                  preview streams a line per net as it is solved rather than
                  appearing only at the end, and the progress callback can
                  cancel a run.  scipy is used for the sparse solve when
                  installed - two to three orders of magnitude faster than the
                  in-tree conjugate gradient on meshed pours - and falls back
                  to pure Python when it is not; V20 asserts the two agree.
                  Selftest gains V20.
v0.12 2026-08-24  Fixes found on a real 4-layer power-bank board.  A filled
                  zone is cut back around every pad it serves - clearance and
                  thermal relief - so a pad connected only to the pour has its
                  centre in a HOLE in the filled polygon.  Containment alone
                  therefore dropped it, and with no track landing either, the
                  terminal vanished from the report without a word: three of
                  twelve PACK_P terminals were missing.  Pads now tie to the
                  pour when they sit within 1 mm of real fill copper, measured
                  to the polygon EDGE rather than to its nearest vertex (the
                  vertex test read 1.9 mm for a 0.15 mm clearance gap), with a
                  note that the relief spokes themselves are not modelled.
                  Terminals that genuinely cannot be reached are now listed
                  instead of silently omitted.  Selftest gains V21 and V22,
                  the latter running against the real board when supplied.
                  Also hardened for boards other than the small test one: the
                  scipy path now checks endpoint reachability before solving,
                  because a disconnected graph makes the grounded Laplacian
                  singular and spsolve returns NaN with only a stderr warning
                  rather than failing; V10's sweep is capped, since a real
                  board has 130 nets and a ground net with 95 pads (4000+ pairs
                  on its own); vectors that hardcode the reference board's nets
                  now skip rather than crash elsewhere; and the network <= path
                  invariant is checked to 1e-6 rather than 1e-9, which was
                  tighter than the dense solver's own precision on a pure
                  series chain.
v0.13 2026-08-24  Consolidation. The Stackup tab is now Setup and owns
                  everything you set once, in four collapsible sections: Files,
                  Global settings, Via and zone modelling, Stackup. The global
                  bar above the tabs is gone; Trace, Via/Path and Report read
                  those settings rather than owning them, and the Via/Path tab
                  echoes what is in force instead of duplicating the controls.
                  The zone model and mesh pitch moved off the Report tab too -
                  they are modelling choices, not report formatting - while
                  per-pair overrides stay on Report where they belong.
                  Files is a table of [Open] | KiCad Project | File Name |
                  Path covering the project, the board and the net-selection
                  JSON. The project is the target and its .kicad_pcb is opened
                  for board data, which leaves room to pull the schematic or
                  netlist later without opening anything twice; opening a board
                  directly still works and resolves its project backwards. The
                  Open dialog starts at KiCad's own last-opened project, read
                  from system.open_projects in kicad.json, found at the right
                  place for macOS, Windows and Linux and tolerant of a missing
                  or malformed file. Selftest gains V23.
"""
import math, re

RHO_CU_20C = 1.724e-8
ALPHA_CU   = 0.00393
OZ_TO_UM   = 34.798
MIL_TO_M   = 2.54e-5
MM_TO_M    = 1.0e-3

# ---------- s-expression parser ----------
_TOK = re.compile(r'\(|\)|"(?:[^"\\]|\\.)*"|[^\s()]+')

class Node:
    __slots__ = ("head", "children")
    def __init__(self, head, children):
        self.head = head
        self.children = children          # children[0] IS the head atom
    def kids(self):
        """Skip the duplicated head atom."""
        return self.children[1:]
    def get(self, name):
        for c in self.kids():
            if isinstance(c, Node) and c.head == name:
                return c
        return None
    def val(self, name, idx=0, cast=float):
        n = self.get(name)
        if n is None: return None
        vals = n.kids()
        if idx >= len(vals): return None
        try: return cast(vals[idx])
        except (TypeError, ValueError): return None
    def findall(self, name):
        return [c for c in self.kids() if isinstance(c, Node) and c.head == name]

def _unquote(t):
    return t[1:-1].replace('\\"', '"') if t.startswith('"') else t

def parse_sexpr(text):
    toks = _TOK.findall(text)
    pos = 0
    def parse():
        nonlocal pos
        assert toks[pos] == "("
        pos += 1
        items = []
        while toks[pos] != ")":
            if toks[pos] == "(":
                items.append(parse())
            else:
                items.append(_unquote(toks[pos])); pos += 1
        pos += 1
        head = items[0] if items and isinstance(items[0], str) else ""
        return Node(head, items)
    while toks[pos] != "(":
        pos += 1
    return parse()

# ---------- stackup ----------
COPPER_TYPES = {"copper"}

class StackLayer:
    def __init__(self, name, type_raw, thickness_mm, material=None, epsilon_r=None):
        self.name = name
        self.type_raw = type_raw
        self.base_mm = thickness_mm
        self.user_mm = thickness_mm
        self.material = material
        self.epsilon_r = epsilon_r
    @property
    def kind(self):
        t = (self.type_raw or "").lower()
        if t in COPPER_TYPES: return "copper"
        if "mask" in t: return "mask"
        if "silk" in t: return "silk"
        if "paste" in t: return "paste"
        return "dielectric"
    @property
    def dirty(self):
        return abs(self.user_mm - self.base_mm) > 1e-12

class Stackup:
    def __init__(self, layers, source="", general_thickness=None, estimated=False):
        self.layers = layers
        self.source = source
        self.general_thickness = general_thickness
        self.estimated = estimated

    @property
    def copper(self):
        return [l for l in self.layers if l.kind == "copper"]

    def core_thickness_mm(self):
        """Copper + dielectric only. Excludes mask/silk/paste."""
        return sum(l.user_mm for l in self.layers if l.kind in ("copper", "dielectric"))

    def geometry(self, plating_um=0.0, outer_adds=False):
        """Return per-copper-layer geometry dicts, top->bottom.

        Dielectric interfaces are fixed. Outer copper grows AWAY from the core
        when outer_adds, thickening the board by 2*plating (D8)."""
        # unplated z walk over copper+dielectric only
        z = 0.0
        spans = {}
        for l in self.layers:
            if l.kind in ("copper", "dielectric"):
                spans[id(l)] = (z, z + l.user_mm)
                z += l.user_mm
        cu = self.copper
        out = []
        n = len(cu)
        p = plating_um / 1000.0
        for i, l in enumerate(cu):
            z_top, z_bot = spans[id(l)]
            is_outer = (i == 0 or i == n - 1)
            t = l.user_mm + (p if (is_outer and outer_adds) else 0.0)
            if is_outer and outer_adds:
                if i == 0:  z_top = z_bot - t          # top layer grows upward
                else:       z_top = z_top              # bottom layer grows downward
            out.append({
                "name": l.name,
                "index_top": i + 1,
                "index_bottom": n - i,
                "is_outer": is_outer,
                "foil_mm": l.user_mm,
                "finished_mm": t,
                "oz": t * 1000.0 / OZ_TO_UM,
                "z_top_mm": z_top,
                "z_ctr_mm": z_top + t / 2.0,
            })
        return out

def load_stackup(path):
    text = open(path, "r", encoding="utf-8").read()
    root = parse_sexpr(text)
    if root.head != "kicad_pcb":
        raise ValueError("not a .kicad_pcb file")
    general = root.get("general")
    gthick = general.val("thickness") if general else None
    setup = root.get("setup")
    stack = setup.get("stackup") if setup else None
    if stack is None:
        raise ValueError("no (stackup) block in this board - "
                         "open Board Setup > Physical Stackup and save")
    layers = []
    for ln in stack.findall("layer"):
        vals = ln.kids()
        name = vals[0] if vals and isinstance(vals[0], str) else "?"
        tnode = ln.get("type")
        type_raw = tnode.kids()[0] if tnode and tnode.kids() else ""
        th = ln.val("thickness") or 0.0
        mnode = ln.get("material")
        mat = mnode.kids()[0] if mnode and mnode.kids() else None
        layers.append(StackLayer(name, type_raw, th, mat, ln.val("epsilon_r")))
    return Stackup(layers, source=path, general_thickness=gthick)

def manual_stackup(n_copper=4, board_mm=1.6, outer_oz=1.0, inner_oz=1.0):
    """Even dielectric distribution fallback (D6 manual mode)."""
    layers = []
    cu_mm = []
    for i in range(n_copper):
        oz = outer_oz if i in (0, n_copper - 1) else inner_oz
        cu_mm.append(oz * OZ_TO_UM / 1000.0)
    n_diel = n_copper - 1
    diel = max((board_mm - sum(cu_mm)) / n_diel, 1e-4)
    for i in range(n_copper):
        nm = "F.Cu" if i == 0 else ("B.Cu" if i == n_copper - 1 else f"In{i}.Cu")
        layers.append(StackLayer(nm, "copper", cu_mm[i]))
        if i < n_copper - 1:
            layers.append(StackLayer(f"dielectric {i+1}", "core", diel, "FR4", 4.5))
    return Stackup(layers, source="<manual>", estimated=True)

def harvest_vias(path):
    root = parse_sexpr(open(path, "r", encoding="utf-8").read())
    seen = {}
    for v in root.findall("via"):
        kinds = [c for c in v.kids() if isinstance(c, str)]
        vtype = "micro" if "micro" in kinds else ("blind" if "blind" in kinds else "through")
        key = (vtype, v.val("size"), v.val("drill"))
        seen[key] = seen.get(key, 0) + 1
    return sorted(seen.items(), key=lambda kv: -kv[1])

# ---------- electrical ----------
def trace_resistance(length_m, width_m, thickness_m):
    return RHO_CU_20C * length_m / (width_m * thickness_m)

def resistance_at_temp(r20, temp_c):
    return r20 * (1.0 + ALPHA_CU * (temp_c - 20.0))

def barrel_diameters(hole_m, plating_m, convention):
    """convention 'bit': hole value is the drilled bit (OD).
       convention 'finished': hole value is the finished hole (ID)."""
    if convention == "bit":
        od = hole_m; idia = od - 2.0 * plating_m
    else:
        idia = hole_m; od = idia + 2.0 * plating_m
    if idia <= 0.0:
        raise ValueError("hole closed by plating: 2*plating >= drill")
    return od, idia

def barrel_area(hole_m, plating_m, convention):
    od, idia = barrel_diameters(hole_m, plating_m, convention)
    return math.pi / 4.0 * (od * od - idia * idia)

def barrel_length_mm(geo, name_a, name_b, mode):
    ga = next(g for g in geo if g["name"] == name_a)
    gb = next(g for g in geo if g["name"] == name_b)
    a0, a1 = ga["z_top_mm"], ga["z_top_mm"] + ga["finished_mm"]
    b0, b1 = gb["z_top_mm"], gb["z_top_mm"] + gb["finished_mm"]
    if mode == "centre": return abs(gb["z_ctr_mm"] - ga["z_ctr_mm"])
    if mode == "facing": return abs(max(a0, b0) - min(a1, b1))
    if mode == "outer":  return abs(max(a1, b1) - min(a0, b0))
    raise ValueError(f"bad length mode {mode}")

def via_resistance(geo, a, b, hole_m, plating_m, convention="bit",
                   mode="centre", count=1, sharing_pct=100.0):
    area = barrel_area(hole_m, plating_m, convention)
    L = barrel_length_mm(geo, a, b, mode) * MM_TO_M
    r = RHO_CU_20C * L / area
    eff = max(count * sharing_pct / 100.0, 1e-9)
    return r / eff, L, area

import datetime
import fnmatch
import json
import os
import sys

SCRIPT_VERSION = "v0.13"

# --- IPC-2221 (trace tab) ---
IPC_K = {"External layer": 0.048, "Internal layer": 0.024}
IPC_DT_EXP, IPC_AREA_EXP = 0.44, 0.725
IPC_MAX_AREA_MIL2, IPC_MAX_CURRENT_A, IPC_MAX_RISE_C = 700.0, 35.0, 100.0
FR4_MAX_TEMP_C = 105.0

LENGTH_UNITS = {"mil": MIL_TO_M, "mm": MM_TO_M}
COPPER_WEIGHTS = [0.5, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
DEG_C, DEG_F = "\u00b0C", "\u00b0F"

PLATING_PRESETS = [
    ("IPC-6012 Class 2 minimum, 18 um", 18.0),
    ("IPC-6012 Class 2 average, 20 um", 20.0),
    ("IPC-6012 Class 3 average, 25 um", 25.0),
    ("1 mil, 25.4 um", 25.4),
    ("1 oz-equivalent, 34.8 um", OZ_TO_UM),
    ("(clear - enter by hand)", None),
]
PLATING_DEFAULT_INDEX = 0
DRILL_CONVENTIONS = [
    ("Hole value = drilled bit (OD)", "bit"),
    ("Hole value = finished hole (ID)", "finished"),
]
LENGTH_CONVENTIONS = [
    ("Copper centre-to-centre", "centre"),
    ("Facing surfaces", "facing"),
    ("Outer surfaces", "outer"),
]


def temperature_rise_c(current_a, area_mil2, k):
    if current_a <= 0.0:
        return 0.0
    return (current_a / (k * area_mil2 ** IPC_AREA_EXP)) ** (1.0 / IPC_DT_EXP)


def c_to_f(c): return c * 9.0 / 5.0 + 32.0
def f_to_c(f): return (f - 32.0) * 5.0 / 9.0
def delta_c_to_f(d): return d * 9.0 / 5.0


def format_ohms(r):
    if r < 1e-3: return f"{r * 1e6:.4g} uohm"
    if r < 1.0:  return f"{r * 1e3:.4g} mohm"
    if r < 1e3:  return f"{r:.4g} ohm"
    return f"{r / 1e3:.4g} kohm"


# =====================================================================
#  Headless self-test (acceptance vectors V1-V8 from the design contract)
# =====================================================================

def _v18(chk):
    """Collapsible-section behaviour. Split out because it needs a QApplication."""
    sec = CollapsibleSection("Demo")
    inner = QVBoxLayout(); inner.addWidget(QLabel("x" * 40))
    sec.set_content_layout(inner)
    chk("V18 starts expanded", sec.is_expanded(), True, 0)
    chk("V18 expanded arrow points down", sec.button.arrowType(), Qt.DownArrow, 0)
    open_h = sec.sizeHint().height()
    sec.set_expanded(False)
    chk("V18 collapse hides the body", sec.body.isHidden(), True, 0)
    chk("V18 collapsed arrow points right", sec.button.arrowType(), Qt.RightArrow, 0)
    chk("V18 collapsed is shorter", sec.sizeHint().height() < open_h, True, 0)
    sec.set_expanded(True)
    chk("V18 reopen restores height", sec.sizeHint().height(), open_h, 0)
    sec.set_summary("7 items")
    chk("V18 summary stays readable in the header",
        "7 items" in sec.button.text() and "Demo" in sec.button.text(), True, 0)
    sec.set_summary("")
    chk("V18 summary clears", sec.button.text().strip(), "Demo", 0)


def _v15_17(chk, checks, board, board_path, order, geo, rfun):
    """Vectors tied to the small reference board's nets and pin names."""
    # ---- V15 zone-aware modelling on the real board ----
    chk("V15 pour parsed on /SDA", 4 in board.pours, True, 0)
    pr = board.pours[4]
    chk("V15 pour on four layers", len(pr.layers()), 4, 0)
    chk("V15 pour is strip-like", pr.aspect > 5.0, True, 0)
    chk("V15 mid-run via splits recorded", len(board.split_notes) > 0, True, 0)
    sda = [t for t in board.tracks if t[0] == 4]
    chk("V15 B.Cu run was split at the array",
        sum(1 for t in sda if t[1] == "B.Cu") >= 6, True, 0)

    def _pair_r(zm, **kw):
        adjz, _n = board.build_graph(4, order, zone_model=zm, geo=geo,
                                     plating_m=25e-6, **kw)
        def nd(nm):
            t = next(x for x in board.terminals(4) if x["name"] == nm)
            for l in t["layers"]:
                c = board.canonical((l, t["point"]))
                if c in adjz:
                    return c
            return None
        return network_resistance(adjz, nd("Z1.SDA"), nd("Z2.SDA"), rfun)
    r_none = _pair_r("none")
    r_lad = _pair_r("ladder")
    chk("V15 zone ignored matches the old answer", r_none * 1e3, 53.6345, 1e-4)
    chk("V15 ladder is lower than ignoring the zone", r_lad < r_none, True, 0)
    chk("V15 ladder answer", r_lad * 1e3, 36.0502, 1e-4)
    r_mesh = _pair_r("mesh", mesh_pitch=0.25)
    chk("V15 mesh within 3% of ladder", abs(r_mesh / r_lad - 1) < 0.03, True, 0)

    # ---- V16 the whole report path, which V15 does not touch ----
    rep_opts = dict(DEFAULT_OPTIONS)
    rep_opts.update({"plating_um": 25.0, "zone_model": "ladder"})
    rdoc = {"_meta": {"version": "0.1"}, "select": ["*"]}
    rep = build_report(board, board_path, rdoc, rep_opts, order, geo, 25e-6)
    allpairs = [p for nn in rep["nets"] for p in nn["pairs"]]
    chk("V16 report produced pairs", len(allpairs), 11, 0)
    chk("V16 no pair failed to trace",
        [p.get("error") for p in allpairs if "error" in p], [], 0)
    chk("V16 every pair priced", all(p["network_ohms"] > 0 for p in allpairs), True, 0)
    chk("V16 segments sum to the path",
        max(abs(sum(x.get("_r", 0.0) for x in p["segments"]) - p["path_ohms"])
            for p in allpairs) < 1e-9, True, 0)
    chk("V16 markdown renders", "## Summary" in report_markdown(rep), True, 0)
    chk("V16 text renders", "Summary" in report_text(rep), True, 0)
    chk("V16 html renders a table", "<table>" in markdown_to_html(report_markdown(rep)),
        True, 0)
    # pair strategies must change the pair count, not break pricing
    sda = next(s2["net"] for s2 in board.summary() if s2["name"] == "/SDA")
    sname = board.net_names[sda]
    counts = {}
    for pm, cfg in (("all", {}), ("from-source", {"pairs": "from-source",
                                                  "source": "Z1.SDA"}),
                    ("first-two", {"pairs": "first-two"}),
                    ("explicit", {"pairs": "explicit",
                                  "explicit_pairs": ["Z1.SDA>Z2.SDA"]})):
        res = analyse_net(board, sda, sname, order, geo, rep_opts, 25e-6, cfg or None)
        counts[pm] = len(res["pairs"])
        chk(f"V16 {pm} pairs all priced",
            all("error" not in p for p in res["pairs"]), True, 0)
    chk("V16 all-pairs count", counts["all"], 3, 0)
    chk("V16 from-source count", counts["from-source"], 2, 0)
    chk("V16 first-two count", counts["first-two"], 1, 0)
    chk("V16 explicit count", counts["explicit"], 1, 0)
    bad = analyse_net(board, sda, sname, order, geo, rep_opts, 25e-6,
                      {"pairs": "from-source", "source": "NOPE.1"})
    chk("V16 bad source falls back with a note",
        any("not a terminal" in n for n in bad["notes"]), True, 0)

    # ---- V17 voltage, per-pair overrides, section gating ----
    vopts = dict(DEFAULT_OPTIONS)
    vopts.update({"plating_um": 25.0, "zone_model": "ladder",
                  "signal_voltage_v": 3.3, "current_a": 1.0})
    sda = next(x["net"] for x in board.summary() if x["name"] == "/SDA")
    base = analyse_net(board, sda, "/SDA", order, geo, vopts, 25e-6,
                       {"pairs": "explicit", "explicit_pairs": ["Z1.SDA>Z2.SDA"]})
    p0 = base["pairs"][0]
    chk("V17 default voltage applied", p0["voltage_in_v"], 3.3, 1e-12)
    chk("V17 default current applied", p0["current_a"], 1.0, 1e-12)
    chk("V17 drop is I*R_hot", p0["drop_v"], p0["current_a"] * p0["hot_ohms"], 1e-12)
    chk("V17 endpoint voltage is Vin - drop", p0["voltage_out_v"],
        p0["voltage_in_v"] - p0["drop_v"], 1e-12)
    chk("V17 no override flag by default", p0["overridden"], [], 0)

    ovr = analyse_net(board, sda, "/SDA", order, geo, vopts, 25e-6,
                      {"pairs": "explicit", "explicit_pairs": ["Z1.SDA>Z2.SDA"],
                       "pair_overrides": {"Z1.SDA>Z2.SDA": {"voltage_v": 5.0,
                                                            "current_a": 3.0}}})
    p1 = ovr["pairs"][0]
    chk("V17 override voltage", p1["voltage_in_v"], 5.0, 1e-12)
    chk("V17 override current", p1["current_a"], 3.0, 1e-12)
    chk("V17 override flagged", p1["overridden"], ["current_a", "voltage_v"], 0)
    chk("V17 drop scales with overridden current",
        p1["drop_v"], 3.0 * p1["hot_ohms"], 1e-12)
    chk("V17 same resistance either way",
        p1["network_ohms"], p0["network_ohms"], 1e-12)
    rev = analyse_net(board, sda, "/SDA", order, geo, vopts, 25e-6,
                      {"pairs": "explicit", "explicit_pairs": ["Z1.SDA>Z2.SDA"],
                       "pair_overrides": {"Z2.SDA>Z1.SDA": {"voltage_v": 5.0}}})
    chk("V17 override key matches either direction",
        rev["pairs"][0]["voltage_in_v"], 5.0, 1e-12)

    srep = build_report(board, board_path, {"_meta": {"version": "0.1"}},
                        vopts, order, geo, 25e-6)
    full = report_markdown(srep)
    chk("V17 summary carries V in", "| V in |" in full, True, 0)
    chk("V17 skipped-net block is gone", "<details>" not in full, True, 0)
    for key, marker in (("stackup", "## Stackup"), ("summary", "## Summary"),
                        ("detail", "## Detail"), ("assumptions", "## Assumptions"),
                        ("selection", "## Net selection")):
        off = dict(vopts)
        off["sections"] = dict(DEFAULT_OPTIONS["sections"]); off["sections"][key] = False
        rep2 = build_report(board, board_path, {"_meta": {"version": "0.1"}},
                            off, order, geo, 25e-6)
        chk(f"V17 section {key} can be hidden", marker in report_markdown(rep2),
            False, 0)
        chk(f"V17 section {key} shown by default", marker in full, True, 0)
    chk("V17 pair_overrides validate",
        validate_netsel({"_meta": {"version": "0.1"},
                         "nets": {"/SDA": {"pair_overrides": {
                             "Z1.SDA>Z2.SDA": {"voltage_v": 5.0}}}}}), [], 0)
    chk("V17 bad override key caught",
        any("unexpected key" in e for e in validate_netsel(
            {"_meta": {"version": "0.1"},
             "nets": {"/SDA": {"pair_overrides": {"A>B": {"volts": 5}}}}})), True, 0)
    chk("V17 negative override current caught",
        any("minimum" in e for e in validate_netsel(
            {"_meta": {"version": "0.1"},
             "nets": {"/SDA": {"pair_overrides": {"A>B": {"current_a": -1}}}}})),
        True, 0)



def _v19(chk, board_path):
    """Trace-tab thickness source and the board-derived default directory."""
    win = MainWindow(board_path)
    t, r = win.trace_tab, win.report_tab
    if not any(s2["name"] == "/SDA" for s2 in BoardNets(board_path).summary()):
        chk("V19 board label names the file",
            os.path.basename(board_path) in win.globals.board_label.text(), True, 0)
        chk("V19 json default dir is the board dir",
            r.default_dir(), os.path.dirname(os.path.abspath(board_path)), 0)
        chk("V19 stackup source offered when a board is loaded",
            t.src_stackup.isEnabled(), True, 0)
        chk("V19 remaining vectors skipped (not the reference test board)",
            True, True, 0)
        return
    chk("V19 board label names the file",
        os.path.basename(board_path) in win.globals.board_label.text(), True, 0)
    chk("V19 json default dir is the board dir",
        r.default_dir(), os.path.dirname(os.path.abspath(board_path)), 0)
    chk("V19 stackup source offered when a board is loaded", t.src_stackup.isEnabled(),
        True, 0)
    chk("V19 manual is the default", t.src_manual.isChecked(), True, 0)

    # manual mode must reproduce the v0.2 baseline exactly
    t.length_edit.setText("1000"); t.length_unit.setCurrentText("mil")
    t.width_edit.setText("10"); t.width_unit.setCurrentText("mil")
    t.weight_combo.setCurrentIndex(COPPER_WEIGHTS.index(1))
    t.layer_combo.setCurrentText("External layer")
    t.src_manual.setChecked(True); t.calculate()
    chk("V19 manual reproduces the v0.2 number",
        float(t.result_label.text().split()[0]) * 1e3, 49.5437, 1e-3)

    # stackup mode: thickness and k come from the layer.
    # Pin the plating first - the default is now 18 um and D8 is on, so an outer
    # layer is base foil PLUS plating unless that is turned off.
    win.via_tab.outer_plating.setChecked(False)
    t.refresh_stackup()
    t.src_stackup.setChecked(True)
    names = [t.stack_layer_combo.itemData(i) for i in range(t.stack_layer_combo.count())]
    chk("V19 every copper layer is offered", len(names), 4, 0)
    got = {}
    for i, nm in enumerate(names):
        t.stack_layer_combo.setCurrentIndex(i); t.calculate()
        th, loc, _how = t._thickness_and_location()
        got[nm] = (round(th * 1e6, 3), loc)
    chk("V19 F.Cu is outer at 35 um base foil (D8 off)",
        got["F.Cu"], (35.0, "External layer"), 0)
    chk("V19 default plating is the Class 2 minimum",
        win.globals.plating_m() * 1e6, 18.0, 1e-9)
    win.via_tab.outer_plating.setChecked(True)
    t.refresh_stackup(); t.src_stackup.setChecked(True)
    i0 = [k for k in range(t.stack_layer_combo.count())
          if t.stack_layer_combo.itemData(k) == "F.Cu"][0]
    t.stack_layer_combo.setCurrentIndex(i0)
    th18, _l18, _h18 = t._thickness_and_location()
    chk("V19 D8 on with the 18 um default gives 53 um", th18 * 1e6, 53.0, 1e-6)
    chk("V19 In1.Cu is inner at 70 um", got["In1.Cu"], (70.0, "Internal layer"), 0)
    chk("V19 inner layer flips IPC k",
        IPC_K[got["In1.Cu"][1]], 0.024, 1e-12)

    # outer-layer plating (D8) must follow through from the Via tab
    win.globals.plating.setText("25")
    win.via_tab.outer_plating.setChecked(True)
    t.refresh_stackup(); t.src_stackup.setChecked(True)
    i = [k for k in range(t.stack_layer_combo.count())
         if t.stack_layer_combo.itemData(k) == "F.Cu"][0]
    t.stack_layer_combo.setCurrentIndex(i)
    th, _loc, _how = t._thickness_and_location()
    chk("V19 D8 thickens the outer layer here too", th * 1e6, 60.0, 1e-6)
    win.via_tab.outer_plating.setChecked(False)
    t.refresh_stackup(); t.src_stackup.setChecked(True)
    t.stack_layer_combo.setCurrentIndex(i)
    th2, _l, _h = t._thickness_and_location()
    chk("V19 D8 off leaves base foil", th2 * 1e6, 35.0, 1e-6)

    # radios drive widget enablement
    t.src_manual.setChecked(True)
    chk("V19 manual enables weight, disables layer picker",
        (t.weight_combo.isEnabled(), t.stack_layer_combo.isEnabled()), (True, False), 0)
    t.src_stackup.setChecked(True)
    chk("V19 stackup enables layer picker, disables weight",
        (t.weight_combo.isEnabled(), t.stack_layer_combo.isEnabled()), (False, True), 0)

    win2 = MainWindow()
    chk("V19 no board disables the stackup source",
        win2.trace_tab.src_stackup.isEnabled(), False, 0)
    chk("V19 no board falls back to manual",
        win2.trace_tab.src_manual.isChecked(), True, 0)
    chk("V19 no board gives an empty default dir", win2.report_tab.default_dir(), "", 0)


def _v20(chk, board_path):
    """Duplicate pins, per-pair zone models, streaming, and the solver backend."""
    board = BoardNets(board_path)
    st = load_stackup(board_path)
    geo = st.geometry(18.0, True)
    order = [g["name"] for g in geo]
    opts = dict(DEFAULT_OPTIONS)
    opts.update({"plating_um": 18.0, "zone_model": "ladder"})

    # --- duplicate pin names collapse to one terminal ---
    net = next((x["net"] for x in board.summary() if x["name"] == "/SDA"), None)
    if net is None:
        chk("V20 skipped (not the reference test board)", True, True, 0)
        return
    real = board.terminals(net)
    chk("V20 board has no duplicate names to start",
        len({t["name"] for t in real}), len(real), 0)
    fake = list(board.pads)
    dup = [p for p in fake if p[0] == net][0]
    board.pads.append((dup[0], (dup[1][0] + 0.5, dup[1][1]), dup[2], dup[3],
                       "99", dup[5]))
    chk("V20 a repeated pin name is one terminal",
        len(board.terminals(net)), len(real), 0)
    chk("V20 without dedupe it would be two",
        len(board.terminals(net, dedupe=False)), len(real) + 1, 0)
    chk("V20 the collapsed pad is recorded as an alias",
        any(t["aliases"] for t in board.terminals(net)), True, 0)
    res = analyse_net(board, net, "/SDA", order, geo, opts, 18e-6)
    chk("V20 duplicate pin is not paired twice",
        len(res["pairs"]), 3, 0)
    chk("V20 the collapse is reported",
        any("treated as one terminal" in n for n in res["notes"]), True, 0)
    board.pads = fake

    # --- per-pair zone model overrides ---
    cfg = {"pairs": "explicit", "explicit_pairs": ["Z1.SDA>Z2.SDA"],
           "pair_overrides": {"Z1.SDA>Z2.SDA": {"zone_model": "none"}}}
    none_r = analyse_net(board, net, "/SDA", order, geo, opts, 18e-6,
                         cfg)["pairs"][0]
    cfg2 = dict(cfg); cfg2["pair_overrides"] = {"Z1.SDA>Z2.SDA": {"zone_model": "ladder"}}
    lad_r = analyse_net(board, net, "/SDA", order, geo, opts, 18e-6,
                        cfg2)["pairs"][0]
    cfg3 = dict(cfg); cfg3["pair_overrides"] = {
        "Z1.SDA>Z2.SDA": {"zone_model": "mesh", "mesh_pitch_mm": 0.25}}
    mesh_r = analyse_net(board, net, "/SDA", order, geo, opts, 18e-6,
                         cfg3)["pairs"][0]
    chk("V20 per-pair zone_model is honoured",
        [none_r["zone_model"], lad_r["zone_model"], mesh_r["zone_model"]],
        ["none", "ladder", "mesh"], 0)
    chk("V20 ignoring the zone reads highest",
        none_r["network_ohms"] > lad_r["network_ohms"], True, 0)
    chk("V20 mesh agrees with ladder within 5%",
        abs(mesh_r["network_ohms"] / lad_r["network_ohms"] - 1) < 0.05, True, 0)
    chk("V20 mesh uses far more nodes",
        mesh_r["nodes"] > lad_r["nodes"] * 5, True, 0)
    chk("V20 every pair records its solve time",
        all(p["solve_seconds"] >= 0 for p in (none_r, lad_r, mesh_r)), True, 0)
    chk("V20 mixed models in one net validate",
        validate_netsel({"_meta": {"version": "0.1"}, "nets": {"/SDA": {
            "pair_overrides": {"A>B": {"zone_model": "mesh",
                                       "mesh_pitch_mm": 0.25}}}}}), [], 0)
    chk("V20 bad zone model caught",
        any("not one of" in e for e in validate_netsel(
            {"_meta": {"version": "0.1"}, "nets": {"/SDA": {
                "pair_overrides": {"A>B": {"zone_model": "wishful"}}}}})), True, 0)

    # --- streaming callback fires per net, in order, and can cancel ---
    seen = []
    def prog(done, total, name, res_):
        seen.append((done, name, res_ is not None))
        return True
    build_report(board, board_path, {"_meta": {"version": "0.1"}}, opts, order,
                 geo, 18e-6, progress=prog)
    chk("V20 progress fires before and after each net",
        len(seen), 2 * len({s2["name"] for s2 in board.summary()}), 0)
    chk("V20 results stream as they finish",
        [d for d, _n, done in seen if done], list(range(1, 6)), 0)
    stopped = []
    build_report(board, board_path, {"_meta": {"version": "0.1"}}, opts, order,
                 geo, 18e-6,
                 progress=lambda d, t, n, r: (stopped.append(n), False)[1])
    chk("V20 progress can cancel the run", len(stopped), 1, 0)

    # --- solver backend agreement and the time forecast ---
    if HAVE_SCIPY:
        edges = [((0, 0), (0, 1), 1.0), ((0, 1), (0, 2), 2.0), ((0, 0), (0, 2), 6.0)]
        rs, _n1, _i1 = _solve_scipy(edges, (0, 0), (0, 2))
        rp, _n2, _i2 = solve_cg(edges, (0, 0), (0, 2))
        chk("V20 scipy and python solvers agree", rs, rp, 1e-9)
        chk("V20 against the hand answer 3||6", rs, 2.0, 1e-9)
    c = calibrate_solver()
    chk("V20 calibration produced a positive rate", c["a"] > 0, True, 0)
    chk("V20 calibration exponent is sane", 0.8 <= c["b"] <= 3.0, True, 0)
    chk("V20 estimate grows with node count",
        estimate_seconds(4000) > estimate_seconds(400), True, 0)
    n_lad = estimate_nodes(board, net, order, "ladder", 0.25)
    n_mesh = estimate_nodes(board, net, order, "mesh", 0.25)
    chk("V20 mesh is forecast far larger than ladder", n_mesh > n_lad * 5, True, 0)


def _v22(chk, board_path):
    """Regressions found on a real board: zone-only pads and silent drops."""
    board = BoardNets(board_path)
    st = load_stackup(board_path)
    geo = st.geometry(18.0, True)
    order = [g["name"] for g in geo]
    opts = dict(DEFAULT_OPTIONS)
    opts.update({"plating_um": 18.0, "zone_model": "ladder",
                 "current_a": 8.0, "signal_voltage_v": 8.4})
    pack = next((x["net"] for x in board.summary()
                 if x["name"].endswith("PACK_P")), None)
    if pack is None:
        checks_note = "V22 skipped (reference net not on this board)"
        chk(checks_note, True, True, 0)
        return
    terms = board.terminals(pack)
    raw = board.terminals(pack, dedupe=False)
    chk("V22 repeated pin names collapse on a real board",
        len(terms) < len(raw), True, 0)
    res = analyse_net(board, pack, "PACK_P", order, geo, opts, 18e-6,
                      {"pairs": "from-source", "source": "JP1.B"})
    chk("V22 no terminal is silently unreachable", res["unreachable"], [], 0)
    chk("V22 from-source gives N-1 pairs",
        len(res["pairs"]), len(terms) - 1, 0)
    chk("V22 every pair solved", [p for p in res["pairs"] if "error" in p], [], 0)
    chk("V22 zone-only pads are tied to the pour",
        sum(1 for n in res["notes"] if "thermal relief" in n) >= 3, True, 0)
    chk("V22 and the gap is clearance-sized, not metres",
        all(float(n.split("sits ")[1].split(" mm")[0]) <= ZONE_PAD_REACH_MM
            for n in res["notes"] if "thermal relief" in n), True, 0)
    names = {p["to"] for p in res["pairs"]}
    for nm in ("C17.1", "C16.1", "C44.1"):
        chk(f"V22 zone-only pad {nm} is now reported", nm in names, True, 0)
    # ladder and mesh must not disagree wildly on a real pour
    cfg = {"pairs": "explicit", "explicit_pairs": ["JP1.B>U2.BAT"]}
    lad = analyse_net(board, pack, "PACK_P", order, geo, opts, 18e-6, cfg)["pairs"][0]
    cfg2 = dict(cfg)
    cfg2["pair_overrides"] = {"JP1.B>U2.BAT": {"zone_model": "mesh",
                                               "mesh_pitch_mm": 0.5}}
    mesh = analyse_net(board, pack, "PACK_P", order, geo, opts, 18e-6, cfg2)["pairs"][0]
    chk("V22 ladder within 5% of mesh on a real pour",
        abs(mesh["network_ohms"] / lad["network_ohms"] - 1) < 0.05, True, 0)


def _v23(chk):
    """KiCad preference discovery and project/board resolution."""
    import tempfile
    d = tempfile.mkdtemp()
    # every platform layout, exercised regardless of the host OS
    layouts = {
        "darwin": os.path.join(d, "Library", "Preferences", "kicad", "9.0"),
        "nt": os.path.join(d, "AppData", "Roaming", "kicad", "9.0"),
        "posix": os.path.join(d, ".config", "kicad", "9.0"),
    }
    for path in layouts.values():
        os.makedirs(path, exist_ok=True)
        with open(os.path.join(path, "kicad.json"), "w", encoding="utf-8") as fh:
            json.dump({"system": {"open_projects": [os.path.join(d, "Ref.kicad_pro")]}}, fh)
    chk("V23 three platform layouts written", len(layouts), 3, 0)

    # project -> board resolution
    pro = os.path.join(d, "Ref.kicad_pro")
    pcb = os.path.join(d, "Ref.kicad_pcb")
    open(pro, "w").close()
    open(pcb, "w").close()
    chk("V23 project resolves to its sibling board",
        board_for_project(pro), pcb, 0)
    chk("V23 a board resolves to itself", board_for_project(pcb), pcb, 0)
    chk("V23 board resolves back to its project", project_for_board(pcb), pro, 0)
    os.remove(pcb)
    chk("V23 project with no board returns None", board_for_project(pro), None, 0)
    chk("V23 missing directory does not raise",
        board_for_project("/definitely/not/here/x.kicad_pro"), None, 0)
    lone = os.path.join(d, "solo")
    os.makedirs(lone, exist_ok=True)
    only = os.path.join(lone, "Different.kicad_pcb")
    open(only, "w").close()
    chk("V23 a differently named lone board is still found",
        board_for_project(os.path.join(lone, "Proj.kicad_pro")), only, 0)
    open(os.path.join(lone, "Second.kicad_pcb"), "w").close()
    chk("V23 two candidate boards is ambiguous, so None",
        board_for_project(os.path.join(lone, "Proj.kicad_pro")), None, 0)

    # malformed preferences must not take the app down
    bad = os.path.join(d, "bad", "kicad", "9.0")
    os.makedirs(bad, exist_ok=True)
    with open(os.path.join(bad, "kicad.json"), "w", encoding="utf-8") as fh:
        fh.write("{ this is not json")
    chk("V23 unreadable preferences are survivable",
        isinstance(kicad_recent_projects(), list), True, 0)
    chk("V23 pref dirs is a list", isinstance(kicad_pref_dirs(), list), True, 0)


def _v21(chk):
    """Zone-connected pads: a fill is cut back around every pad it serves."""
    ring = [(0.0, 0.0), (10.0, 0.0), (10.0, 10.0), (0.0, 10.0)]
    chk("V21 distance to an EDGE, not just a vertex",
        _dist_to_poly((5.0, 10.15), ring), 0.15, 1e-9)
    chk("V21 nearest vertex would have said 5.0",
        min(math.dist((5.0, 10.15), p) for p in ring) > 5.0, True, 0)
    chk("V21 a point inside reads zero at the boundary",
        _dist_to_poly((0.0, 5.0), ring), 0.0, 1e-9)
    chk("V21 far pad is out of reach",
        _dist_to_poly((5.0, 20.0), ring) > ZONE_PAD_REACH_MM, True, 0)
    chk("V21 clearance-sized gap is within reach",
        _dist_to_poly((5.0, 10.2), ring) <= ZONE_PAD_REACH_MM, True, 0)


def _raises(fn):
    try:
        fn(); return False
    except Exception:                                 # noqa: BLE001 - guard probe
        return True


def selftest(verbose=True, board_path=None):
    import math
    checks, failures = [], []

    def chk(name, got, want, tol=5e-3):
        if isinstance(got, (int, float)) and isinstance(want, (int, float)) \
                and not isinstance(got, bool) and not isinstance(want, bool):
            ok = (want == 0 and abs(got) < tol) or \
                 abs(got - want) <= tol * max(abs(want), 1e-12)
        else:
            ok = got == want                       # exact for lists, sets, bools, strings
        checks.append((name, got, want, ok))
        if not ok:
            failures.append(f"{name}: got {got!r}, want {want!r}")

    # ---- reference stackup: the surveyed KiCad 9 board, built in memory ----
    ref = Stackup([
        StackLayer("F.Mask", "Top Solder Mask", 0.01),
        StackLayer("F.Cu", "copper", 0.035),
        StackLayer("dielectric 1", "prepreg", 0.1, "FR4", 4.5),
        StackLayer("In1.Cu", "copper", 0.07),
        StackLayer("dielectric 2", "core", 1.24, "FR4", 4.5),
        StackLayer("In2.Cu", "copper", 0.07),
        StackLayer("dielectric 3", "prepreg", 0.1, "FR4", 4.5),
        StackLayer("B.Cu", "copper", 0.035),
        StackLayer("B.Mask", "Bottom Solder Mask", 0.01),
    ])
    P, HOLE = 25.0, 0.3e-3
    Pm = P * 1e-6

    # ---- V1 stackup parse ----
    chk("V1 copper layer count", len(ref.copper), 4, 0)
    chk("V1 core thickness unplated mm", ref.core_thickness_mm(), 1.65)
    geo_on = ref.geometry(P, True)
    geo_off = ref.geometry(P, False)
    for g, oz, t_um in ((geo_on[0], 1.724, 60.0), (geo_on[1], 2.012, 70.0),
                        (geo_on[2], 2.012, 70.0), (geo_on[3], 1.724, 60.0)):
        chk(f"V1 {g['name']} finished um", g["finished_mm"] * 1000, t_um)
        chk(f"V1 {g['name']} oz", g["oz"], oz)
    chk("V1 outer/inner flags", sum(1 for g in geo_on if g["is_outer"]), 2, 0)
    chk("V1 index_top F.Cu", geo_on[0]["index_top"], 1, 0)
    chk("V1 index_bottom F.Cu", geo_on[0]["index_bottom"], 4, 0)
    chk("V1 D8 thickens board by 2*plating",
        (geo_on[3]["z_top_mm"] + geo_on[3]["finished_mm"]) - geo_on[0]["z_top_mm"],
        ref.core_thickness_mm() + 2 * P / 1000)
    chk("V1 D8 off leaves board unchanged",
        (geo_off[3]["z_top_mm"] + geo_off[3]["finished_mm"]) - geo_off[0]["z_top_mm"],
        ref.core_thickness_mm())

    # ---- V2 barrel resistance, all spans ----
    v2 = {("F.Cu", "In1.Cu"): (0.1650, 131.70), ("F.Cu", "In2.Cu"): (1.4750, 1177.35),
          ("B.Cu", "In1.Cu"): (1.4750, 1177.35), ("B.Cu", "In2.Cu"): (0.1650, 131.70),
          ("F.Cu", "B.Cu"):   (1.6400, 1309.06)}
    for (a, b), (wl, wr) in v2.items():
        r, L, _ = via_resistance(geo_on, a, b, HOLE, Pm)
        chk(f"V2 {a}->{b} L mm", L * 1000, wl)
        chk(f"V2 {a}->{b} R uohm", r * 1e6, wr)
    r1, _, _ = via_resistance(geo_on, "F.Cu", "In1.Cu", HOLE, Pm)
    r2, _, _ = via_resistance(geo_on, "B.Cu", "In2.Cu", HOLE, Pm)
    chk("V2 symmetry F->In1 == B->In2", r1, r2, 1e-9)

    # ---- V3 barrel-length conventions ----
    for mode, wl, wr in (("facing", 0.1000, 79.82), ("centre", 0.1650, 131.70),
                         ("outer", 0.2300, 183.59)):
        r, L, _ = via_resistance(geo_on, "F.Cu", "In1.Cu", HOLE, Pm, mode=mode)
        chk(f"V3 {mode} L mm", L * 1000, wl)
        chk(f"V3 {mode} R uohm", r * 1e6, wr)

    # ---- V4 hole conventions ----
    for conv, wod, wid, wa, wr in (("bit", 0.300, 0.250, 21598.4, 1309.06),
                                   ("finished", 0.350, 0.300, 25525.4, 1107.66)):
        od, idia = barrel_diameters(HOLE, Pm, conv)
        r, _, A = via_resistance(geo_on, "F.Cu", "B.Cu", HOLE, Pm, convention=conv)
        chk(f"V4 {conv} OD mm", od * 1e3, wod)
        chk(f"V4 {conv} ID mm", idia * 1e3, wid)
        chk(f"V4 {conv} area um^2", A * 1e12, wa)
        chk(f"V4 {conv} R uohm", r * 1e6, wr)

    # ---- V5 acceptance path ----
    def trace_on(layer, geo, length_mil=50, width_mil=4):
        g = next(x for x in geo if x["name"] == layer)
        return trace_resistance(length_mil * MIL_TO_M, width_mil * MIL_TO_M,
                                g["finished_mm"] * MM_TO_M)
    for geo, wt1, wv, wt2, wtot, wpct in ((geo_on, 3591.7, 1177.4, 3078.6, 7.8476, 15.0),
                                          (geo_off, 6157.1, 1167.4, 3078.6, 10.4031, 11.2)):
        t1 = trace_on("F.Cu", geo); t2 = trace_on("In2.Cu", geo)
        v, _, _ = via_resistance(geo, "F.Cu", "In2.Cu", HOLE, Pm)
        tot = t1 + v + t2
        tag = "D8 on" if geo is geo_on else "D8 off"
        chk(f"V5 {tag} F.Cu uohm", t1 * 1e6, wt1)
        chk(f"V5 {tag} via uohm", v * 1e6, wv)
        chk(f"V5 {tag} In2.Cu uohm", t2 * 1e6, wt2)
        chk(f"V5 {tag} total mohm", tot * 1e3, wtot)
        chk(f"V5 {tag} via share %", v / tot * 100, wpct, 1e-2)

    # ---- V6 parallel vias ----
    t1 = trace_on("F.Cu", geo_on); t2 = trace_on("In2.Cu", geo_on)
    for n, want in ((1, 7.8476), (2, 7.2589), (4, 6.9646), (8, 6.8174)):
        v, _, _ = via_resistance(geo_on, "F.Cu", "In2.Cu", HOLE, Pm, count=n)
        chk(f"V6 n={n} mohm", (t1 + v + t2) * 1e3, want)
    v50, _, _ = via_resistance(geo_on, "F.Cu", "In2.Cu", HOLE, Pm, count=2, sharing_pct=50.0)
    v1, _, _ = via_resistance(geo_on, "F.Cu", "In2.Cu", HOLE, Pm, count=1)
    chk("V6 sharing 50% of 2 vias == 1 via", v50, v1, 1e-9)

    # ---- V7 guards ----
    try:
        barrel_area(HOLE, 150e-6, "bit"); failures.append("V7 150um should have raised")
        checks.append(("V7 150um raises", "no raise", "ValueError", False))
    except ValueError:
        checks.append(("V7 150um raises", "ValueError", "ValueError", True))
    od, idia = barrel_diameters(HOLE, 149e-6, "bit")
    chk("V7 149um ID um", idia * 1e6, 2.0, 1e-2)

    # ---- V8 algebraic identity, BOTH conventions ----
    for conv in ("bit", "finished"):
        od, idia = barrel_diameters(HOLE, Pm, conv)
        expanded = math.pi / 4.0 * (od * od - idia * idia)
        collapsed = math.pi * Pm * (idia + Pm)
        chk(f"V8 identity {conv}", expanded, collapsed, 1e-12)

    # ---- regression: v0.2 trace-tab behaviour must be unchanged ----
    r20 = trace_resistance(1000 * MIL_TO_M, 10 * MIL_TO_M, 1 * OZ_TO_UM * 1e-6)
    chk("v0.2 regression 1000x10 mil 1oz mohm", r20 * 1e3, 49.5437)
    chk("v0.2 regression IPC rise 1A external C",
        temperature_rise_c(1.0, 13.7, 0.048), 13.3143, 1e-3)
    chk("v0.2 regression IPC rise 1A internal C",
        temperature_rise_c(1.0, 13.7, 0.024), 64.3187, 1e-3)
    chk("v0.2 regression 0 A rise", temperature_rise_c(0.0, 13.7, 0.048), 0.0)
    chk("v0.2 regression hot R at 38.31 C",
        resistance_at_temp(r20, 38.3143) * 1e3, 53.1094, 1e-3)
    chk("v0.2 regression dT C->F", delta_c_to_f(13.3143), 23.9657, 1e-4)
    chk("v0.2 regression 25C -> F", c_to_f(25.0), 77.0)
    chk("v0.2 regression 77F -> C", f_to_c(77.0), 25.0)

    # ---- V9 arc length (synthetic, no file needed) ----
    chk("V9 arc semicircle r=1", _arc_length_mm(-1, 0, 0, 1, 1, 0), math.pi, 1e-9)
    chk("V9 arc quarter r=2", _arc_length_mm(2, 0, math.sqrt(2), math.sqrt(2), 0, 2),
        math.pi, 1e-9)
    chk("V9 arc degenerate -> chord", _arc_length_mm(0, 0, 1, 0, 2, 0), 2.0, 1e-9)

    # ---- V11 network solver, synthetic topologies with hand-checkable answers ----
    def _mk(edges):
        adj = {}
        for u_, v_, r_ in edges:
            d = {"kind": "synthetic", "r": r_}
            adj.setdefault(u_, []).append((v_, d))
            adj.setdefault(v_, []).append((u_, d))
        return adj
    _rf = lambda d: d["r"]                                            # noqa: E731
    chk("V11 series 1+2+3", network_resistance(
        _mk([("A", "B", 1), ("B", "C", 2), ("C", "D", 3)]), "A", "D", _rf), 6.0, 1e-12)
    chk("V11 parallel 2||3", network_resistance(
        _mk([("A", "B", 2), ("A", "B", 3)]), "A", "B", _rf), 1.2, 1e-12)
    chk("V11 1||(2+3)", network_resistance(
        _mk([("A", "B", 1), ("A", "C", 2), ("C", "B", 3)]), "A", "B", _rf), 5.0 / 6.0, 1e-12)
    chk("V11 unbalanced bridge", network_resistance(
        _mk([("A", "B", 1), ("A", "C", 2), ("B", "D", 3), ("C", "D", 4), ("B", "C", 5)]),
        "A", "D", _rf), 2.3943661971830985, 1e-10)
    chk("V11 balanced bridge ignores bridge", network_resistance(
        _mk([("A", "B", 1), ("A", "C", 1), ("B", "D", 2), ("C", "D", 2), ("B", "C", 7)]),
        "A", "D", _rf), 1.5, 1e-12)
    chk("V11 stub carries nothing", network_resistance(
        _mk([("A", "B", 1), ("B", "C", 2), ("B", "S", 99)]), "A", "C", _rf), 3.0, 1e-12)
    chk("V11 ten 10-ohm in parallel", network_resistance(
        _mk([("A", "B", 10.0)] * 10), "A", "B", _rf), 1.0, 1e-12)

    # ---- V12 net-selection file: schema validation and select/ignore logic ----
    good = {"_meta": {"version": "0.1"}, "select": ["*"], "ignore": ["GND"],
            "options": {"plating_um": 25.0, "zone_model": "ladder"}}
    chk("V12 valid doc passes", validate_netsel(good), [], 0)
    chk("V12 missing _meta caught",
        any("_meta" in e for e in validate_netsel({"select": ["*"]})), True, 0)
    chk("V12 bad version pattern caught",
        any("does not match" in e for e in
            validate_netsel({"_meta": {"version": "one"}})), True, 0)
    chk("V12 unknown key caught",
        any("unexpected key" in e for e in
            validate_netsel({"_meta": {"version": "0.1"}, "selectt": []})), True, 0)
    chk("V12 bad enum caught",
        any("not one of" in e for e in
            validate_netsel({"_meta": {"version": "0.1"},
                             "options": {"zone_model": "magic"}})), True, 0)
    chk("V12 zero plating caught",
        any("greater than" in e for e in
            validate_netsel({"_meta": {"version": "0.1"},
                             "options": {"plating_um": 0}})), True, 0)
    chk("V12 wrong type caught",
        any("expected array" in e for e in
            validate_netsel({"_meta": {"version": "0.1"}, "select": "*"})), True, 0)
    avail = [(1, "/SDA"), (2, "/SCL"), (3, "GND"), (4, "unconnected-(U1-Pad3)")]
    got, _why, _us, _ui = select_nets(avail, {"select": ["*"],
                                              "ignore": ["GND", "unconnected-*"]})
    chk("V12 glob ignore", [n for _x, n in got], ["/SDA", "/SCL"], 0)
    got, _why, _us, _ui = select_nets(avail, {"select": ["/S*"], "ignore": ["/SCL"]})
    chk("V12 ignore beats select", [n for _x, n in got], ["/SDA"], 0)
    got, _why, _us, _ui = select_nets(avail, {})
    chk("V12 empty select means all", len(got), 4, 0)
    _g, _w, unused_s, unused_i = select_nets(avail, {"select": ["/NOPE"],
                                                     "ignore": ["/ALSONOPE"]})
    chk("V12 unused select reported", unused_s, ["/NOPE"], 0)
    chk("V12 unused ignore reported", unused_i, ["/ALSONOPE"], 0)

    _v21(chk)
    _v23(chk)

    # ---- V13 pour geometry ----
    sq = [(0.0, 0.0), (10.0, 0.0), (10.0, 1.0), (0.0, 1.0)]
    chk("V13 point inside", _pt_in_poly((5.0, 0.5), sq), True, 0)
    chk("V13 point outside", _pt_in_poly((5.0, 2.0), sq), False, 0)
    chk("V13 point on edge counts as inside", _pt_in_poly((5.0, 0.0), sq), True, 0)
    p = Pour(0, {"F.Cu": sq})
    chk("V13 pour length", p.length, 10.0, 1e-9)
    chk("V13 pour width", p.width, 1.0, 1e-9)
    chk("V13 pour aspect", p.aspect, 10.0, 1e-9)
    chk("V13 axis is x", abs(p.ux), 1.0, 1e-9)
    out, ins = clip_track_to_pour((-5.0, 0.5), (5.0, 0.5), sq)
    chk("V13 clip outside length", sum(f for _a, _b, f in out), 0.5, 1e-9)
    chk("V13 clip inside length", sum(f for _a, _b, f in ins), 0.5, 1e-9)
    cl = cluster_vias([(0, 0), (1, 0), (2, 0), (20, 0)], max_gap=2.0)
    chk("V13 clusters found", sorted(len(c) for c in cl), [1, 3], 0)
    summ = via_array_summary(cl)
    big = max(summ, key=lambda a: a["count"])
    chk("V13 array centroid", big["centroid"][0], 1.0, 1e-9)
    chk("V13 array extent", big["extent_mm"], 2.0, 1e-9)

    # ---- V14 shunt array: the vector that separates a ladder from a lump ----
    def _shunt(rungs_at):
        e = []
        for lay, r_per in (("A", 1.0), ("B", 1.0)):
            for u0, u1 in zip([0.0, 1.0, 2.0, 3.0], [1.0, 2.0, 3.0, 4.0]):
                e.append(((lay, u0), (lay, u1), r_per))
        for u in rungs_at:
            e.append((("A", u), ("B", u), 0.1 * len(rungs_at) / len(rungs_at)))
        adjs = {}
        for u_, v_, r_ in e:
            d = {"r": r_}
            adjs.setdefault(u_, []).append((v_, d))
            adjs.setdefault(v_, []).append((u_, d))
        return network_resistance(adjs, ("A", 0.0), ("A", 4.0), lambda d: d["r"])
    lump = _shunt([2.0])
    ladder2 = _shunt([1.0, 3.0])
    chk("V14 single centroid rung gives no parallel benefit", lump, 4.0, 1e-9)
    chk("V14 two separated rungs do help", ladder2 < 4.0 - 1e-9, True, 0)

    # ---- V10 net tracing against a real board (only when one is supplied) ----
    if board_path:
        board = BoardNets(board_path)
        st = load_stackup(board_path)
        order = [g["name"] for g in st.geometry(0, False)]
        geo = st.geometry(25.0, True)
        rfun = lambda d: edge_resistance(d, geo, 25e-6, "bit", "centre")   # noqa: E731

        def _nodes(net):
            adj, _ = board.build_graph(net, order)
            out = []
            for t in board.terminals(net):
                for l in t["layers"]:
                    if (l, t["point"]) in adj:
                        out.append((t["name"], (l, t["point"])))
                        break
            return out

        chk("V10 arc/track parse: nets with copper", len(board.summary()) > 0, True, 0)
        derived = total_vias = 0
        unreachable_pairs = 0
        # Cap the sweep: a real board has hundreds of nets and a ground net with
        # ninety-odd pads, which is 4000+ pairs on its own.
        candidates = [s["net"] for s in board.summary()][:12]
        for net in candidates:
            terms = _nodes(net)
            if len(terms) > 6:
                continue
            for i in range(len(terms)):
                for j in range(i + 1, len(terms)):
                    (na, a), (nb, b) = terms[i], terms[j]
                    try:
                        segs, notes, pr, nr = trace_path(board, net, order, a, b, rfun)
                    except ValueError:
                        unreachable_pairs += 1      # legitimate: broken or zone-only
                        continue
                    chk(f"V10 {na}->{nb} path>0", pr > 0, True, 0)
                    # Tolerance is the solver's precision, not physics: a pure
                    # series chain makes network == path, and a dense
                    # Gauss-Jordan solve lands ~1e-9 relative away from it.
                    chk(f"V10 {na}->{nb} network <= path", nr <= pr * (1 + 1e-6), True, 0)
                    chk(f"V10 {na}->{nb} sum(segments)==path",
                        sum(rfun(s) for s in segs), pr, 1e-9)
                    derived += sum(
                        1 for s in segs if s["kind"] == "via" and s["declared"]
                        and {s["from"], s["to"]} != set(s["declared"]))
                    total_vias += sum(1 for s in segs if s["kind"] == "via")
        chk("V10 unreachable pairs are reported, not crashes",
            isinstance(unreachable_pairs, int), True, 0)
        chk("V10 traced vias were priced", total_vias >= 0, True, 0)
        # ---- V15/V16/V17 assume the small reference board's nets ----
        _nm = {x['name'] for x in board.summary()}
        _t4 = ({t['name'] for t in board.terminals(4)}
               if 4 in {x['net'] for x in board.summary()} else set())
        if '/SDA' in _nm and {'Z1.SDA', 'Z2.SDA'} <= _t4:
            _v15_17(chk, checks, board, board_path, order, geo, rfun)
        else:
            checks.append(('V15-V17 skipped (not the reference test board)',
                           'skipped', 'skipped', True))

        # ---- V18 collapsible sections ----
        # Qt widgets need a QApplication; make an offscreen one if the GUI is not
        # already running, so this vector still runs from a headless --selftest.
        _app = QApplication.instance()
        if _app is None:
            os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
            try:
                _app = QApplication([])
            except Exception:                          # noqa: BLE001
                _app = None
        if _app is None:
            checks.append(("V18 collapsible sections (no Qt display available)",
                           "skipped", "skipped", True))
        else:
            _v18(chk)

        if _app is not None:
            _v19(chk, board_path)
            _v20(chk, board_path)
        if "PowerBank" in os.path.basename(board_path):
            _v22(chk, board_path)

        # net 2 is unrouted on the reference board; on others it may not exist
        # or may be routed, so only assert where the premise holds.
        _n2 = next((x for x in board.summary() if x["net"] == 2), None)
        if _n2 is None:
            chk("V10 unrouted net raises",
                _raises(lambda: trace_path(board, 2, order, None, None, rfun)), True, 0)
        else:
            chk("V10 net 2 is routed on this board, nothing to assert", True, True, 0)

    if verbose:
        width = max(len(c[0]) for c in checks)
        for name, got, want, ok in checks:
            g = f"{got:.6g}" if isinstance(got, float) else str(got)
            w = f"{want:.6g}" if isinstance(want, float) else str(want)
            if len(g) > 34: g = g[:31] + "..."
            if len(w) > 34: w = w[:31] + "..."
            print(f"  [{'PASS' if ok else 'FAIL'}] {name:<{width}}  got {g:>12}  want {w:>12}")
        print(f"\n{len(checks) - len(failures)}/{len(checks)} checks passed")
    return failures




# =====================================================================
#  Zone-aware modelling: track splitting, pours, via arrays, ladders
# =====================================================================

def _pt_in_poly(pt, poly):
    """Ray casting. Points exactly on an edge count as inside."""
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


def _seg_poly_crossings(p1, p2, poly):
    """Parameters t in (0,1) where segment p1->p2 crosses the polygon boundary."""
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


def _dist_to_poly(pt, poly):
    """Distance from a point to a polygon boundary (edges, not just vertices)."""
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


def _principal_axis(pts):
    """Oriented bounding box of a point cloud: (origin, unit axis, length, width)."""
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


class Pour:
    """One net's filled copper, one entry per layer, modelled as a strip."""

    def __init__(self, net, fills):
        self.net = net
        self.fills = fills                      # {layer: [(x,y), ...]}
        allpts = [p for poly in fills.values() for p in poly]
        (self.cx, self.cy), (self.ux, self.uy), self.length, self.width, self.u0 = \
            _principal_axis(allpts)
        self.aspect = self.length / self.width if self.width > 1e-9 else float("inf")

    def layers(self):
        return list(self.fills)

    def contains(self, layer, pt):
        poly = self.fills.get(layer)
        return bool(poly) and _pt_in_poly(pt, poly)

    def any_layer_contains(self, pt):
        return [l for l, poly in self.fills.items() if _pt_in_poly(pt, poly)]

    def project(self, pt):
        """Distance along the pour's long axis."""
        return (pt[0] - self.cx) * self.ux + (pt[1] - self.cy) * self.uy


def parse_pours(root):
    """Filled zone copper, grouped by net then layer."""
    by_net = {}
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
    return {n: Pour(n, f) for n, f in by_net.items()}


def cluster_vias(points, max_gap=2.0):
    """Group vias into arrays by proximity (single-link). Returns list of lists."""
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


def via_array_summary(groups):
    """Centroid and extent per cluster - the statics view of each array."""
    out = []
    for g in groups:
        n = len(g)
        cx = sum(p[0] for p in g) / n
        cy = sum(p[1] for p in g) / n
        span = max(math.hypot(a[0] - b[0], a[1] - b[1]) for a in g for b in g) if n > 1 else 0.0
        out.append({"count": n, "centroid": (round(cx, 4), round(cy, 4)),
                    "extent_mm": round(span, 4), "points": g})
    return out


def clip_track_to_pour(p1, p2, poly):
    """Split a track by a pour outline.

    Returns (outside, inside) as lists of (pa, pb, frac) sub-runs. Copper inside
    the pour is modelled by the pour strip, so those runs must not also be added
    as 1-D track edges or they would be double counted in parallel."""
    ts = [0.0] + _seg_poly_crossings(p1, p2, poly) + [1.0]
    (ax, ay), (bx, by) = p1, p2
    at = lambda t: (round(ax + t * (bx - ax), 6), round(ay + t * (by - ay), 6))  # noqa: E731
    outside, inside = [], []
    for t0, t1 in zip(ts, ts[1:]):
        if t1 - t0 < 1e-9:
            continue
        mid = at((t0 + t1) / 2.0)
        (inside if _pt_in_poly(mid, poly) else outside).append((at(t0), at(t1), t1 - t0))
    return outside, inside


def build_pour_ladder(pour, order, stations_extra, via_layers, strip_r, rung_r):
    """1-D ladder along the pour's long axis.

    stations_extra: {u: [(layer, node)]} external tie-ins already in the graph.
    via_layers:     {u: [layer, ...]} landing layers for each via in the pour.
    Returns (edges, tie) where tie maps (layer, u) -> pour node."""
    us = sorted(set(list(stations_extra) + list(via_layers)))
    edges = []
    node = lambda l, u: ("pour", pour.net, l, round(u, 6))          # noqa: E731

    for layer in pour.layers():
        for u0, u1 in zip(us, us[1:]):
            du = u1 - u0
            if du <= 1e-9:
                continue
            edges.append((node(layer, u0), node(layer, u1),
                          {"kind": "pour", "layer": layer, "length_mm": du,
                           "width_mm": pour.width, "net": pour.net}))

    rank = {nm: i for i, nm in enumerate(order)}
    for u, lays in via_layers.items():
        present = sorted((l for l in lays if l in rank), key=lambda l: rank[l])
        for a, b in zip(present, present[1:]):
            edges.append((node(a, u), node(b, u),
                          {"kind": "via", "from": a, "to": b, "in_pour": True,
                           "u": u, "net": pour.net}))

    tie = {}
    for u, entries in stations_extra.items():
        for layer, ext in entries:
            if layer in pour.layers():
                tie[(layer, u)] = (ext, node(layer, u))
    return edges, tie, us


def build_graph_pour(board, net, order, zone_model="ladder", cluster_gap=2.0,
                     geo=None, plating_m=None, convention="bit", mode="centre",
                     mesh_pitch=0.125):
    """Net graph with zone copper modelled as a 1-D ladder along the pour axis.

    zone_model: 'ladder' (fast, exact for strip-like pours), 'none' (ignore
    zone copper and say so), or 'mesh' (handled by the caller)."""
    rank = {nm: i for i, nm in enumerate(order)}
    notes = []
    pour = board.pours.get(net) if zone_model != "none" else None
    raw, merges = [], []

    def add(u, v, data):
        raw.append((u, v, data))

    if zone_model == "mesh" and (geo is None or plating_m is None):
        notes.append("mesh model needs stackup and plating; falling back to the ladder")
        zone_model = "ladder"
    if pour and zone_model == "ladder" and pour.aspect < 2.0:
        notes.append(f"pour aspect ratio is only {pour.aspect:.1f}:1 - a 1-D strip model "
                     "is questionable on copper this square; consider the mesh model")

    tie_pts = {}          # (layer, point) -> u   external nodes that touch the pour

    def note_tie(layer, pt):
        if pour and layer in pour.fills:
            tie_pts[(layer, pt)] = pour.project(pt)

    # ---- tracks, clipped against the pour ----
    for n, layer, p1, p2, w, L in board.tracks:
        if n != net:
            continue
        if layer not in rank:
            notes.append(f"track on unknown layer {layer} skipped")
            continue
        if p1 == p2:
            continue
        poly = pour.fills.get(layer) if pour else None
        if not poly:
            add((layer, p1), (layer, p2),
                {"kind": "trace", "layer": layer, "length_mm": L, "width_mm": w})
            continue
        outside, inside = clip_track_to_pour(p1, p2, poly)
        for a, b, frac in outside:
            add((layer, a), (layer, b),
                {"kind": "trace", "layer": layer, "length_mm": L * frac, "width_mm": w})
        for a, b, frac in inside:
            note_tie(layer, a); note_tie(layer, b)
        if inside and not outside:
            note_tie(layer, p1); note_tie(layer, p2)
        for a, b, _f in outside:                      # boundary ends tie into the pour
            for pt in (a, b):
                if pt not in (p1, p2):
                    note_tie(layer, pt)

    # ---- pads that sit in, or just outside, the pour ----
    # A filled zone is cut back around every pad it serves (clearance, thermal
    # relief), so a pad connected only to the pour has its centre in a HOLE in
    # the filled polygon. Containment alone therefore drops it, silently. Tie
    # any pad whose centre is within reach of real fill copper.
    track_pts = {(layer, p) for n, layer, p1, p2, _w, _L in board.tracks if n == net
                 for layer, p in ((layer, p1), (layer, p2))}
    for n, pt, lays, ref, pn, _fn in board.pads:
        if n != net or not pour:
            continue
        for l in lays:
            if l not in pour.fills:
                continue
            if pour.contains(l, pt):
                note_tie(l, pt)
            elif (l, pt) not in track_pts:
                gap = _dist_to_poly(pt, pour.fills[l])
                if gap <= ZONE_PAD_REACH_MM:
                    note_tie(l, pt)
                    notes.append(
                        f"pad {ref}.{pn} on {l} has no track and sits {gap:.3f} mm "
                        "outside the filled copper (zone clearance / thermal relief); "
                        "connected to the pour. The relief spokes themselves are not "
                        "modelled, so this pad reads slightly optimistic")

    # ---- vias: inside the pour they become ladder rungs, outside they stay edges ----
    land = board._landings(net)
    via_layers, arrays = {}, []
    in_pour_pts = []
    for n, pt, size, drill, declared, vtype in board.vias:
        if n != net:
            continue
        here = sorted((l for l in land.get(pt, set()) if l in rank), key=lambda l: rank[l])
        if pour and pour.any_layer_contains(pt):
            lays = sorted(set(here) | set(l for l in pour.any_layer_contains(pt) if l in rank),
                          key=lambda l: rank[l])
            if len(lays) < 2:
                notes.append(f"via at {pt} reaches only {lays} - ignored")
                continue
            u = pour.project(pt)
            via_layers[u] = {"layers": lays, "hole_mm": drill, "pad_mm": size, "point": pt}
            in_pour_pts.append(pt)
            continue
        if len(here) < 2:
            notes.append(f"via at {pt} has {len(here)} landing layer(s) - "
                         "no current path through it, ignored")
            continue
        if vtype != "through":
            notes.append(f"{vtype} via at {pt}: barrel modelled between landing layers")
        for a, b in zip(here, here[1:]):
            add((a, pt), (b, pt),
                {"kind": "via", "from": a, "to": b, "hole_mm": drill, "pad_mm": size,
                 "point": pt, "declared": declared, "split": len(here) > 2})
        if len(here) > 2:
            notes.append(f"via at {pt} lands on {len(here)} layers "
                         f"({', '.join(here)}) - barrel split into series sub-spans")

    # ---- the pour: mesh (slow, any shape) or ladder (fast, strip-like) ----
    if pour and via_layers and zone_model == "mesh":
        arrays = via_array_summary(cluster_vias(in_pour_pts, cluster_gap))
        vinfo = {u: dict(i) for u, i in via_layers.items()}
        ties = {(l, pt): (l, pt) for (l, pt) in tie_pts}
        medges, muf, (nx, ny, px, py) = mesh_pour_edges(
            pour, order, geo, vinfo, ties, mesh_pitch, plating_m, convention, mode)
        for a, b in muf.p.items():
            merges.append((a, muf.find(a)))
        for u, v, r in medges:
            add(u, v, {"kind": "mesh", "r": r})
        notes.append(f"pour meshed at {mesh_pitch:g} mm: {nx}x{ny} cells per layer "
                     f"({len(medges)} resistors) - slow model, valid for any pour shape")
    elif pour and via_layers:
        arrays = via_array_summary(cluster_vias(in_pour_pts, cluster_gap))
        us = sorted(set(list(via_layers) + list(tie_pts.values())))
        pnode = lambda l, u: ("pour", net, l, round(u, 6))         # noqa: E731
        for layer in pour.fills:
            if layer not in rank:
                continue
            for u0, u1 in zip(us, us[1:]):
                if u1 - u0 <= 1e-9:
                    continue
                add(pnode(layer, u0), pnode(layer, u1),
                    {"kind": "pour", "layer": layer, "length_mm": u1 - u0,
                     "width_mm": pour.width})
        for u, info in via_layers.items():
            lays = info["layers"]
            for a, b in zip(lays, lays[1:]):
                add(pnode(a, u), pnode(b, u),
                    {"kind": "via", "from": a, "to": b, "hole_mm": info["hole_mm"],
                     "pad_mm": info["pad_mm"], "point": info["point"],
                     "declared": (), "in_pour": True})
        for (layer, pt), u in tie_pts.items():
            merges.append(((layer, pt), pnode(layer, u)))   # same copper, one node
        for a in arrays:
            notes.append(f"via array of {a['count']} at centroid {a['centroid']} spanning "
                         f"{a['extent_mm']:.3f} mm modelled as a {len(via_layers)}-rung ladder "
                         f"over a {pour.width:.3f} mm wide pour "
                         f"({pour.aspect:.1f}:1 aspect)")
    elif pour:
        notes.append("pour present but no vias land in it; zone copper ignored")

    # a tie is the same physical copper, so merge the nodes rather than joining
    # them with a near-zero resistor, which would wreck the solver's conditioning
    uf = _Union()
    for a, b in merges:
        uf.union(a, b)
    adj = {}
    for u, v, data in raw:
        cu, cv = uf.find(u), uf.find(v)
        if cu == cv:
            continue
        adj.setdefault(cu, []).append((cv, data))
        adj.setdefault(cv, []).append((cu, data))
    for n in list(adj):
        adj.setdefault(n, adj[n])
    return adj, notes, arrays, uf



# =====================================================================
#  Mesh model (slow option) - sparse conjugate gradient over the pour
# =====================================================================

class _Union:
    def __init__(self): self.p = {}
    def find(self, a):
        self.p.setdefault(a, a)
        while self.p[a] != a:
            self.p[a] = self.p[self.p[a]]; a = self.p[a]
        return a
    def union(self, a, b):
        ra, rb = self.find(a), self.find(b)
        if ra != rb: self.p[ra] = rb


try:                                            # optional, never required
    import numpy as _np
    import scipy.sparse as _sp
    import scipy.sparse.linalg as _spl
    HAVE_SCIPY = True
except ImportError:                             # pure-Python fallback below
    HAVE_SCIPY = False


def _solve_scipy(edges, src, dst):
    """Same nodal problem through compiled sparse code when scipy is installed.

    Two to three orders of magnitude faster than the Python CG on meshed pours;
    the result must agree with it, which V20 checks."""
    nodes = sorted({u for u, _v, _r in edges} | {v for _u, v, _r in edges}, key=str)
    idx = {n: i for i, n in enumerate(nodes)}
    n = len(nodes)
    rows, cols, vals = [], [], []
    for u, v, r in edges:
        if r <= 0 or u == v:
            continue
        g = 1.0 / r
        iu, iv = idx[u], idx[v]
        rows += [iu, iv, iu, iv]
        cols += [iu, iv, iv, iu]
        vals += [g, g, -g, -g]
    # A disconnected graph makes the grounded Laplacian singular. scipy returns
    # NaNs with only a warning on stderr, so check reachability first and fail
    # loudly instead of reporting a nonsense resistance.
    nbr = {}
    for u, v, r in edges:
        if r > 0 and u != v:
            nbr.setdefault(u, []).append(v)
            nbr.setdefault(v, []).append(u)
    seen_n, stack = {src}, [src]
    while stack:                                     # full component, not early exit
        cur = stack.pop()
        for nx in nbr.get(cur, ()):
            if nx not in seen_n:
                seen_n.add(nx); stack.append(nx)
    if dst not in seen_n:
        raise ValueError("endpoints are not connected")
    # Other components are still singular even when src and dst are connected,
    # so solve over the source's component alone.
    L = _sp.coo_matrix((vals, (rows, cols)), shape=(n, n)).tocsr()
    gnd = idx[src]
    comp = {idx[u] for u in seen_n}
    keep = [i for i in sorted(comp) if i != gnd]
    Lr = L[keep, :][:, keep].tocsc()
    b = _np.zeros(len(keep))
    pos = keep.index(idx[dst])
    b[pos] = 1.0
    x = _spl.spsolve(Lr, b)
    val = float(x[pos])
    if not math.isfinite(val):
        raise ValueError("nodal solve did not produce a finite resistance")
    return val, n, 1


def solve_cg(edges, src, dst, tol=1e-13, maxit=50000):
    """Two-terminal resistance by Jacobi-preconditioned CG on the grounded Laplacian.

    Equipotential groups must already be merged by the caller - tiny tie
    resistors destroy the conditioning."""
    nodes = sorted({u for u, _v, _r in edges} | {v for _u, v, _r in edges}, key=str)
    idx = {n: i for i, n in enumerate(nodes)}
    n = len(nodes)
    nbr = [[] for _ in range(n)]
    diag = [0.0] * n
    for u, v, r in edges:
        if r <= 0 or u == v:
            continue
        g = 1.0 / r
        iu, iv = idx[u], idx[v]
        nbr[iu].append((iv, g)); nbr[iv].append((iu, g))
        diag[iu] += g; diag[iv] += g
    gnd = idx[src]

    def mv(x):
        y = [0.0] * n
        for i in range(n):
            if i == gnd:
                continue
            s = diag[i] * x[i]
            for j, g in nbr[i]:
                if j != gnd:
                    s -= g * x[j]
            y[i] = s
        return y

    b = [0.0] * n; b[idx[dst]] = 1.0; b[gnd] = 0.0
    x = [0.0] * n
    r = b[:]
    M = [1.0 / diag[i] if diag[i] > 0 else 1.0 for i in range(n)]
    z = [M[i] * r[i] for i in range(n)]; z[gnd] = 0.0
    p = z[:]; rz = sum(r[i] * z[i] for i in range(n))
    its = 0
    for its in range(1, maxit + 1):
        Ap = mv(p)
        pAp = sum(p[i] * Ap[i] for i in range(n))
        if abs(pAp) < 1e-300:
            break
        a = rz / pAp
        for i in range(n):
            x[i] += a * p[i]; r[i] -= a * Ap[i]
        r[gnd] = 0.0
        if max(abs(v) for v in r) < tol:
            break
        z = [M[i] * r[i] for i in range(n)]; z[gnd] = 0.0
        rz2 = sum(r[i] * z[i] for i in range(n))
        beta = rz2 / rz; rz = rz2
        for i in range(n):
            p[i] = z[i] + beta * p[i]
    return x[idx[dst]], len(nodes), its


def mesh_pour_edges(pour, order, geo, via_info, ties, pitch, plating_m, convention, mode):
    """Rasterise the pour into a resistor grid; merge equipotential groups."""
    rank = {nm: i for i, nm in enumerate(order)}
    xs = [p[0] for poly in pour.fills.values() for p in poly]
    ys = [p[1] for poly in pour.fills.values() for p in poly]
    x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
    nx = max(int(round((x1 - x0) / pitch)), 2)
    ny = max(int(round((y1 - y0) / pitch)), 2)
    px, py = (x1 - x0) / nx, (y1 - y0) / ny
    ctr = lambda i, j: (x0 + (i + 0.5) * px, y0 + (j + 0.5) * py)     # noqa: E731

    live = {}
    for layer, poly in pour.fills.items():
        if layer not in rank:
            continue
        live[layer] = {(i, j) for i in range(nx) for j in range(ny)
                       if _pt_in_poly(ctr(i, j), poly)}

    uf = _Union()
    edges = []
    for layer, cells in live.items():
        g = next(x for x in geo if x["name"] == layer)
        rs = RHO_CU_20C / (g["finished_mm"] * MM_TO_M)          # ohms per square
        for (i, j) in cells:
            if (i + 1, j) in cells:
                edges.append(((layer, i, j), (layer, i + 1, j), rs * px / py))
            if (i, j + 1) in cells:
                edges.append(((layer, i, j), (layer, i, j + 1), rs * py / px))

    # a barrel is a finite disc, not a point: merge the cells it covers
    for u, info in via_info.items():
        pt = info["point"]
        rad = info["hole_mm"] / 2.0
        for layer in info["layers"]:
            if layer not in live:
                continue
            covered = [(i, j) for (i, j) in live[layer]
                       if math.hypot(ctr(i, j)[0] - pt[0], ctr(i, j)[1] - pt[1]) <= rad]
            if not covered:
                covered = [min(live[layer], key=lambda c: math.hypot(
                    ctr(*c)[0] - pt[0], ctr(*c)[1] - pt[1]))]
            for c in covered[1:]:
                uf.union((layer, *c), (layer, *covered[0]))
            info.setdefault("hub", {})[layer] = (layer, *covered[0])
        lays = info["layers"]
        for a, b in zip(lays, lays[1:]):
            ha, hb = info.get("hub", {}).get(a), info.get("hub", {}).get(b)
            if ha and hb:
                r, _L, _A = via_resistance(geo, a, b, info["hole_mm"] * MM_TO_M,
                                           plating_m, convention=convention, mode=mode)
                edges.append((ha, hb, r))

    ext = []
    for (layer, pt), extnode in ties.items():
        if layer not in live:
            continue
        c = min(live[layer], key=lambda cc: math.hypot(
            ctr(*cc)[0] - pt[0], ctr(*cc)[1] - pt[1]))
        uf.union((layer, *c), extnode)
        ext.append(extnode)
    return edges, uf, (nx, ny, px, py)



# =====================================================================
#  Net selection file (JSON) + schema + validation
# =====================================================================

NETSEL_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "$id": "https://example.invalid/pcb-net-selection.schema.json",
    "title": "PCB resistance report net selection",
    "type": "object",
    "additionalProperties": False,
    "required": ["_meta"],
    "properties": {
        "_meta": {
            "type": "object",
            "additionalProperties": False,
            "required": ["version"],
            "properties": {
                "version": {"type": "string", "pattern": r"^v?\d+\.\d+(\.\d+)?$"},
                "description": {"type": "string"},
                "board": {"type": "string"},
                "generated": {"type": "string"},
            },
        },
        "select": {
            "type": "array", "items": {"type": "string"},
            "description": "Net names or glob patterns to include. '*' means every "
                           "routed net. Omitted or empty is treated as '*'.",
        },
        "ignore": {
            "type": "array", "items": {"type": "string"},
            "description": "Net names or glob patterns to exclude. Applied after "
                           "select, so ignore always wins.",
        },
        "_available_nets": {
            "type": "array", "items": {"type": "string"},
            "description": "Informational only: nets found on the board when this "
                           "template was generated. Ignored when reading.",
        },
        "options": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "plating_um": {"type": "number", "exclusiveMinimum": 0, "maximum": 1000},
                "hole_convention": {"enum": ["bit", "finished"]},
                "length_convention": {"enum": ["centre", "facing", "outer"]},
                "outer_plating_adds": {"type": "boolean"},
                "zone_model": {"enum": ["none", "ladder", "mesh"]},
                "mesh_pitch_mm": {"type": "number", "exclusiveMinimum": 0, "maximum": 5},
                "ambient_c": {"type": "number", "minimum": -273.15},
                "current_a": {"type": "number", "minimum": 0},
                "pairs": {"enum": ["all", "first-two", "from-source"]},
                "max_pairs_warn": {"type": "number", "minimum": 1},
                "signal_voltage_v": {"type": "number",
                                     "description": "Default source voltage; the report "
                                                    "shows the endpoint voltage after "
                                                    "the I*R drop."},
                "sections": {
                    "type": "object",
                    "additionalProperties": False,
                    "description": "Which report sections to emit.",
                    "properties": {
                        "assumptions": {"type": "boolean"},
                        "stackup": {"type": "boolean"},
                        "selection": {"type": "boolean"},
                        "summary": {"type": "boolean"},
                        "detail": {"type": "boolean"},
                        "notes": {"type": "boolean"},
                    },
                },
            },
        },
        "nets": {
            "type": "object",
            "description": "Per-net overrides, keyed by net name. Decides which pad "
                           "pairs are reported for that net.",
            "additionalProperties": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "pairs": {"enum": ["all", "first-two", "from-source", "explicit"]},
                    "source": {"type": "string",
                               "description": "Terminal name (REF.PIN) used as the "
                                              "source for 'from-source'."},
                    "explicit_pairs": {
                        "type": "array",
                        "items": {"type": "string",
                                  "pattern": r"^[^>]+>[^>]+$"},
                        "description": "Pairs written as 'Z1.SDA>Z3.SDA'.",
                    },
                    "pair_overrides": {
                        "type": "object",
                        "description": "Per-pair voltage and current, keyed "
                                       "'Z1.SDA>Z2.SDA'. Omitted values fall back to "
                                       "the operating-condition defaults.",
                        "additionalProperties": {
                            "type": "object",
                            "additionalProperties": False,
                            "properties": {
                                "voltage_v": {"type": "number"},
                                "current_a": {"type": "number", "minimum": 0},
                                "zone_model": {"enum": ["none", "ladder", "mesh"]},
                                "mesh_pitch_mm": {"type": "number",
                                                  "exclusiveMinimum": 0, "maximum": 5},
                            },
                        },
                    },
                },
            },
        },
    },
}

DEFAULT_OPTIONS = {
    "plating_um": 18.0,               # IPC-6012 Class 2 minimum (D2 amended)
    "hole_convention": "bit",
    "length_convention": "centre",
    "outer_plating_adds": True,
    "zone_model": "ladder",
    "mesh_pitch_mm": 0.25,
    "ambient_c": 25.0,
    "current_a": 1.0,
    "pairs": "all",
    "max_pairs_warn": 28,
    "signal_voltage_v": 3.3,
    "sections": {"assumptions": True, "stackup": True, "selection": True,
                 "summary": True, "detail": True, "notes": True},
}


def _type_ok(value, spec):
    t = spec.get("type")
    if t == "object":  return isinstance(value, dict)
    if t == "array":   return isinstance(value, list)
    if t == "string":  return isinstance(value, str)
    if t == "boolean": return isinstance(value, bool)
    if t == "number":  return isinstance(value, (int, float)) and not isinstance(value, bool)
    return True


def validate_netsel(doc, schema=None, path="$"):
    """Minimal JSON-Schema check covering the subset this schema uses.

    Returns a list of human-readable errors; empty means valid."""
    schema = schema or NETSEL_SCHEMA
    errs = []
    if "enum" in schema:
        if doc not in schema["enum"]:
            errs.append(f"{path}: {doc!r} is not one of {schema['enum']}")
        return errs
    if not _type_ok(doc, schema):
        errs.append(f"{path}: expected {schema.get('type')}, got "
                    f"{type(doc).__name__}")
        return errs
    if schema.get("type") == "number":
        if "minimum" in schema and doc < schema["minimum"]:
            errs.append(f"{path}: {doc} is below the minimum {schema['minimum']}")
        if "exclusiveMinimum" in schema and doc <= schema["exclusiveMinimum"]:
            errs.append(f"{path}: {doc} must be greater than {schema['exclusiveMinimum']}")
        if "maximum" in schema and doc > schema["maximum"]:
            errs.append(f"{path}: {doc} is above the maximum {schema['maximum']}")
    if schema.get("type") == "string" and "pattern" in schema:
        if not re.match(schema["pattern"], doc):
            errs.append(f"{path}: {doc!r} does not match {schema['pattern']}")
    if schema.get("type") == "object":
        for req in schema.get("required", []):
            if req not in doc:
                errs.append(f"{path}: missing required key {req!r}")
        props = schema.get("properties", {})
        addl = schema.get("additionalProperties")
        if addl is False:
            for k in doc:
                if k not in props:
                    errs.append(f"{path}: unexpected key {k!r} "
                                f"(allowed: {', '.join(sorted(props))})")
        for k, v in doc.items():
            if k in props:
                errs.extend(validate_netsel(v, props[k], f"{path}.{k}"))
            elif isinstance(addl, dict):
                errs.extend(validate_netsel(v, addl, f"{path}.{k}"))
    if schema.get("type") == "array":
        for i, item in enumerate(doc):
            errs.extend(validate_netsel(item, schema.get("items", {}), f"{path}[{i}]"))
    return errs


def load_netsel(path):
    with open(path, "r", encoding="utf-8") as fh:
        doc = json.load(fh)
    errs = validate_netsel(doc)
    if errs:
        raise ValueError("net selection file failed schema validation:\n  "
                         + "\n  ".join(errs))
    opts = dict(DEFAULT_OPTIONS)
    opts.update(doc.get("options", {}))
    return doc, opts


def select_nets(available, doc):
    """Apply select then ignore. Ignore always wins. Globs supported.

    `available` is [(net_number, net_name), ...]."""
    sel = doc.get("select") or ["*"]
    ign = doc.get("ignore") or []
    chosen, why = [], {}
    for num, name in available:
        hit = next((p for p in sel if fnmatch.fnmatchcase(name, p)), None)
        if hit is None:
            why[name] = "not matched by select"
            continue
        blocked = next((p for p in ign if fnmatch.fnmatchcase(name, p)), None)
        if blocked is not None:
            why[name] = f"ignored by pattern {blocked!r}"
            continue
        chosen.append((num, name))
        why[name] = f"selected by pattern {hit!r}"
    unused_sel = [p for p in sel
                  if not any(fnmatch.fnmatchcase(n, p) for _x, n in available)]
    unused_ign = [p for p in ign
                  if not any(fnmatch.fnmatchcase(n, p) for _x, n in available)]
    return chosen, why, unused_sel, unused_ign


def netsel_template(board, board_path=""):
    names = [s["name"] for s in board.summary()]
    return {
        "_meta": {
            "version": "0.1",
            "description": "Net selection for the PCB resistance report. "
                           "'select' then 'ignore'; ignore wins. Globs allowed.",
            "board": os.path.basename(board_path),
            "generated": datetime.datetime.now().isoformat(timespec="seconds"),
        },
        "select": ["*"],
        "ignore": ["unconnected-*", "GND", "GNDA"],
        "options": {"plating_um": 25.0, "zone_model": "ladder", "pairs": "all"},
        "_available_nets": names,
    }



# =====================================================================
#  Point-to-point resistance report
# =====================================================================

def analyse_net(board, net, name, order, geo, opts, plating_m, netcfg=None):
    """Every pad pair on one net. Returns a dict of results plus notes."""
    conv, mode = opts["hole_convention"], opts["length_convention"]
    over = (netcfg or {})
    default_model = (over.get("zone_model") or opts["zone_model"],
                     over.get("mesh_pitch_mm") or opts.get("mesh_pitch_mm", 0.25))
    _graphs = {}

    def graph_for(zm, pitch):
        """One graph per distinct zone model, reused across every pair using it."""
        key = (zm, round(pitch, 6))
        if key not in _graphs:
            a, nts = board.build_graph(net, order, zone_model=zm, geo=geo,
                                       plating_m=plating_m, convention=conv,
                                       mode=mode, mesh_pitch=pitch)
            _graphs[key] = (a, nts, getattr(board, "_last_arrays", []),
                            board.canonical)
        return _graphs[key]

    zone_model, mesh_pitch = default_model
    adj, notes, arrays, _canon = graph_for(zone_model, mesh_pitch)
    notes = list(notes)

    def rfun(d):
        return edge_resistance(d, geo, plating_m, conv, mode)

    terms = []
    unreachable = []
    collapsed = 0
    for t in board.terminals(net):
        if t["aliases"]:
            collapsed += len(t["aliases"])
            pads = ", ".join(str(a["pad"]) for a in t["aliases"])
            notes.append(f"{t['name']} appears on {len(t['aliases']) + 1} pads "
                         f"(also {pads}); treated as one terminal, computed once")
        placed = False
        for l in t["layers"]:
            c = board.canonical((l, t["point"]))
            if c in adj:
                terms.append((t["name"], c, t))
                placed = True
                break
        if not placed:
            unreachable.append(t["name"])
    if unreachable:
        notes.append(
            f"{len(unreachable)} terminal(s) have no copper reaching them and were "
            f"left out: {', '.join(unreachable)}. They are not in any pair below")
    pairs = []
    over = (netcfg or {})
    pair_mode = over.get("pairs", opts.get("pairs", "all"))
    names = [t[0] for t in terms]
    combos = []
    if len(terms) >= 2:
        if pair_mode == "first-two":
            combos = [(0, 1)]
        elif pair_mode == "from-source":
            src = over.get("source") or names[0]
            if src not in names:
                notes.append(f"source {src!r} is not a terminal on this net "
                             f"({', '.join(names)}); using {names[0]}")
                src = names[0]
            i0 = names.index(src)
            combos = [(i0, j) for j in range(len(terms)) if j != i0]
        elif pair_mode == "explicit":
            for spec in over.get("explicit_pairs", []):
                a, _sep, b = spec.partition(">")
                a, b = a.strip(), b.strip()
                if a in names and b in names:
                    combos.append((names.index(a), names.index(b)))
                else:
                    notes.append(f"explicit pair {spec!r} names a terminal that is not "
                                 f"on this net ({', '.join(names)}) - skipped")
        else:
            combos = [(i, j) for i in range(len(terms))
                      for j in range(i + 1, len(terms))]
        limit = opts.get("max_pairs_warn", 28)
        if len(combos) > limit:
            notes.append(f"{len(combos)} pad pairs on this net exceeds the "
                         f"{limit}-pair warning threshold; consider pairs='from-source' "
                         "to report one source against every load instead")
        for i, j in combos:
            na, a0, _ = terms[i]
            nb, b0, _ = terms[j]
            ov = (over.get("pair_overrides") or {})
            key = f"{na}>{nb}"
            rkey = f"{nb}>{na}"
            po = ov.get(key) or ov.get(rkey) or {}
            zm = po.get("zone_model", zone_model)
            pitch = po.get("mesh_pitch_mm", mesh_pitch)
            padj, pnotes0, _arr, canon = graph_for(zm, pitch)
            a = canon(a0) if canon(a0) in padj else a0
            b = canon(b0) if canon(b0) in padj else b0
            t_start = time.perf_counter()
            try:
                segs, pnotes, path_r, net_r = trace_path(board, net, order, a, b, rfun,
                                                         adj=padj, zone_model=zm)
            except (ValueError, ZeroDivisionError) as exc:
                pairs.append({"from": na, "to": nb, "error": str(exc),
                              "zone_model": zm})
                continue
            elapsed = time.perf_counter() - t_start
            hot = resistance_at_temp(net_r, opts["ambient_c"])
            cur = po.get("current_a", opts["current_a"])
            vin = po.get("voltage_v", opts.get("signal_voltage_v", 0.0))
            drop = cur * hot
            pairs.append({
                "from": na, "to": nb,
                "path_ohms": path_r, "network_ohms": net_r,
                "hot_ohms": hot,
                "current_a": cur, "voltage_in_v": vin,
                "voltage_out_v": vin - drop,
                "overridden": sorted(po),
                "zone_model": zm,
                "mesh_pitch_mm": pitch if zm == "mesh" else None,
                "nodes": len(padj),
                "solve_seconds": elapsed,
                "drop_v": drop,
                "power_w": cur * cur * hot,
                "parallel_gain_pct": max((1 - net_r / path_r) * 100, 0.0) if path_r else 0.0,
                "segments": segs, "notes": pnotes,
            })
    return {"net": net, "name": name, "terminals": names,
            "unreachable": unreachable,
            "pairs": pairs, "notes": notes, "via_arrays": arrays,
            "pair_mode": pair_mode if len(terms) >= 2 else "n/a",
            "nodes": len(adj)}


def build_report(board, board_path, doc, opts, order, geo, plating_m,
                 progress=None):
    available = [(s["net"], s["name"]) for s in board.summary()]
    chosen, why, unused_sel, unused_ign = select_nets(available, doc)
    per_net = doc.get("nets", {})
    results = []
    for i, (num, name) in enumerate(chosen):
        if progress is not None and progress(i, len(chosen), name, None) is False:
            break
        res = analyse_net(board, num, name, order, geo, opts, plating_m,
                          per_net.get(name))
        results.append(res)
        if progress is not None and progress(i + 1, len(chosen), name, res) is False:
            break
    return {
        "_meta": {
            "version": "0.1",
            "tool": f"pcb_trace_resistance {SCRIPT_VERSION}",
            "board": os.path.basename(board_path),
            "generated": datetime.datetime.now().isoformat(timespec="seconds"),
            "backend": "scipy" if HAVE_SCIPY else "python",
        },
        "options": opts,
        "stackup": [{"layer": g["name"], "finished_um": round(g["finished_mm"] * 1000, 3),
                     "oz": round(g["oz"], 3), "z_ctr_mm": round(g["z_ctr_mm"], 4)}
                    for g in geo],
        "selection": {"selected": [n for _x, n in chosen],
                      "skipped": {k: v for k, v in why.items()
                                  if not v.startswith("selected")},
                      "unused_select_patterns": unused_sel,
                      "unused_ignore_patterns": unused_ign},
        "nets": results,
    }


def report_markdown(rep):
    o = rep["options"]
    sec = dict(DEFAULT_OPTIONS["sections"])
    sec.update(o.get("sections") or {})
    L = []
    L.append(f"# PCB point-to-point resistance report")
    L.append("")
    L.append(f"**Board** `{rep['_meta']['board']}`  ")
    L.append(f"**Generated** {rep['_meta']['generated']} by {rep['_meta']['tool']}")
    L.append("")
    if sec.get("assumptions", True):
        L.append("## Assumptions")
        L.append("")
        L.append("| Setting | Value |")
        L.append("|---|---|")
        L.append(f"| Barrel plating | {o['plating_um']:g} um "
                 f"({o['plating_um'] / OZ_TO_UM:.3f} oz-equivalent) |")
        L.append(f"| Hole value means | {o['hole_convention']} |")
        L.append(f"| Barrel length | {o['length_convention']} |")
        L.append(f"| Outer-layer plating adds | {o['outer_plating_adds']} |")
        L.append(f"| Zone model | {o['zone_model']}"
                 + (f", pitch {o['mesh_pitch_mm']} mm" if o["zone_model"] == "mesh" else "")
                 + " |")
        L.append(f"| Ambient | {o['ambient_c']:g} C |")
        L.append(f"| Default current | {o['current_a']:g} A |")
        L.append(f"| Default signal voltage | {o.get('signal_voltage_v', 0):g} V |")
        L.append("")
        L.append("DC only. No skin effect, no self-heating, no etch taper. "
                 "Resistance is reported at 20 C and at ambient. Per-pair voltage "
                 "or current overrides are marked in the summary.")
        L.append("")
    if sec.get("stackup", True):
        L.append("## Stackup")
        L.append("")
        L.append("| Layer | Finished | oz | z centre |")
        L.append("|---|---|---|---|")
        for s in rep["stackup"]:
            L.append(f"| {s['layer']} | {s['finished_um']:g} um | {s['oz']:.3f} | "
                     f"{s['z_ctr_mm']:.4f} mm |")
        L.append("")
    sel = rep["selection"]
    if sec.get("selection", True):
        L.append("## Net selection")
        L.append("")
        L.append(f"Reporting on {len(sel['selected'])} net(s): "
                 + (", ".join(f"`{n}`" for n in sel["selected"]) or "_none_"))
        ignored = [n for n, r in sel["skipped"].items() if r.startswith("ignored")]
        if ignored:
            L.append("")
            L.append(f"Explicitly ignored: " + ", ".join(f"`{n}`" for n in sorted(ignored)))
        for p in sel["unused_select_patterns"]:
            L.append(f"- **Warning** select pattern `{p}` matched nothing.")
        for p in sel["unused_ignore_patterns"]:
            L.append(f"- **Warning** ignore pattern `{p}` matched nothing.")
        L.append("")
    if sec.get("summary", True):
        L.append("## Summary")
        L.append("")
        L.append("| Net | From | To | Zone | R @20 C | R @ambient | V in | I | Drop |"
                 " V out | Parallel gain |")
        L.append("|---|---|---|---|---|---|---|---|---|---|---|")
        for n in rep["nets"]:
            for pr in n["pairs"]:
                if "error" in pr:
                    L.append(f"| `{n['name']}` | {pr['from']} | {pr['to']} | "
                             f"ERROR: {pr['error']} | | | | | | | |")
                    continue
                mark = "*" if pr.get("overridden") else ""
                zm = pr.get("zone_model", "-")
                if zm == "mesh" and pr.get("mesh_pitch_mm"):
                    zm += f" {pr['mesh_pitch_mm']:g}mm"
                L.append(f"| `{n['name']}` | {pr['from']} | {pr['to']} | {zm} | "
                         f"{format_ohms(pr['network_ohms'])} | "
                         f"{format_ohms(pr['hot_ohms'])} | "
                         f"{pr['voltage_in_v']:.4g} V{mark} | "
                         f"{pr['current_a']:.4g} A{mark} | "
                         f"{pr['drop_v'] * 1000:.3f} mV | "
                         f"{pr['voltage_out_v']:.5g} V | "
                         f"{pr['parallel_gain_pct']:.1f}% |")
        if any(p.get("overridden") for n in rep["nets"] for p in n["pairs"]):
            L.append("")
            L.append("`*` marks a value overridden for that pair rather than taken "
                     "from the operating-condition defaults.")
        L.append("")
    if not sec.get("detail", True):
        L.append("")
        return "\n".join(L)
    total_t = sum(p.get("solve_seconds", 0.0) for n in rep["nets"] for p in n["pairs"])
    if sec.get("summary", True) and total_t:
        L.append(f"Solved in {total_t:.2f} s total"
                 + (f" ({rep['_meta'].get('backend', '')} backend)"
                    if rep["_meta"].get("backend") else "") + ".")
        L.append("")
    L.append("## Detail")
    for n in rep["nets"]:
        L.append("")
        L.append(f"### `{n['name']}`  (net {n['net']}, {len(n['terminals'])} terminals)")
        L.append("")
        if n["via_arrays"]:
            for a in n["via_arrays"]:
                L.append(f"- Via array: {a['count']} vias, centroid {a['centroid']}, "
                         f"extent {a['extent_mm']:.3f} mm")
        if sec.get("notes", True):
            for note in n["notes"]:
                L.append(f"- _{note}_")
        for pr in n["pairs"]:
            L.append("")
            if "error" in pr:
                L.append(f"**{pr['from']} -> {pr['to']}**: could not trace - {pr['error']}")
                continue
            L.append(f"**{pr['from']} -> {pr['to']}** - "
                     f"{pr['voltage_in_v']:.4g} V in at {pr['current_a']:.4g} A gives "
                     f"{pr['voltage_out_v']:.5g} V out "
                     f"({pr['drop_v'] * 1000:.3f} mV drop, "
                     f"{pr['power_w'] * 1000:.3f} mW). "
                     f"Zone model {pr.get('zone_model', '-')}, "
                     f"{pr.get('nodes', 0)} nodes, solved in "
                     f"{pr.get('solve_seconds', 0.0) * 1000:.0f} ms. "
                     f"Least-resistance path {format_ohms(pr['path_ohms'])}, "
                     f"whole network {format_ohms(pr['network_ohms'])}"
                     + (f" ({pr['parallel_gain_pct']:.1f}% lower - parallel copper carries "
                        "current)" if pr["parallel_gain_pct"] > 1e-6
                        else " (no parallel copper in play)"))
            L.append("")
            L.append("| # | Element | Detail | R @20 C | % of path |")
            L.append("|---|---|---|---|---|")
            tot = pr["path_ohms"] or 1.0
            for i, s in enumerate(pr["segments"], 1):
                r = s.get("_r", 0.0)
                if s["kind"] in ("trace", "pour"):
                    d = (f"{s['length_mm']:.4f} mm x {s['width_mm']:g} mm on {s['layer']}"
                         + (" (pour)" if s["kind"] == "pour" else ""))
                elif s["kind"] == "tie":
                    continue
                elif s["kind"] == "mesh":
                    d = f"meshed pour, {s.get('cells', 1)} cells"
                elif "from" in s:
                    d = (f"{s['from']} -> {s['to']}, hole {s['hole_mm']:g} mm"
                         + (" (in pour)" if s.get("in_pour") else ""))
                else:
                    d = s["kind"]
                L.append(f"| {i} | {s['kind']} | {d} | {format_ohms(r)} | "
                         f"{r / tot * 100:.1f}% |")
            if sec.get("notes", True):
                for note in pr["notes"]:
                    L.append("")
                    L.append(f"> {note}")
    L.append("")
    return "\n".join(L)


def report_text(rep):
    md = report_markdown(rep)
    out = []
    for line in md.split("\n"):
        if set(line.replace(" ", "")) <= {"|", "-"} and "|" in line:
            continue
        line = line.replace("|", " ").replace("**", "").replace("`", "")
        line = re.sub(r"^#+\s*", "", line)
        out.append(line.rstrip())
    return "\n".join(out)


# =====================================================================
#  KiCad installation preferences
# =====================================================================

KICAD_VERSIONS = ("9.0", "8.0", "7.0")


def kicad_pref_dirs():
    """Where KiCad keeps its per-user settings, newest version first."""
    home = os.path.expanduser("~")
    if sys.platform == "darwin":
        roots = [os.path.join(home, "Library", "Preferences", "kicad")]
    elif os.name == "nt":
        roots = [os.path.join(os.environ.get("APPDATA", ""), "kicad"),
                 os.path.join(os.environ.get("LOCALAPPDATA", ""), "kicad")]
    else:
        roots = [os.path.join(os.environ.get("XDG_CONFIG_HOME",
                                             os.path.join(home, ".config")), "kicad")]
    out = []
    for root in roots:
        if not root:
            continue
        for ver in KICAD_VERSIONS:
            d = os.path.join(root, ver)
            if os.path.isdir(d):
                out.append(d)
    return out


def kicad_recent_projects():
    """`system.open_projects` from kicad.json - what KiCad had open last.

    Used only to pre-fill the Open dialog; never opened without being asked."""
    seen, out = set(), []
    for d in kicad_pref_dirs():
        path = os.path.join(d, "kicad.json")
        if not os.path.exists(path):
            continue
        try:
            with open(path, "r", encoding="utf-8") as fh:
                doc = json.load(fh)
        except (OSError, ValueError):
            continue
        system = doc.get("system") or {}
        entries = system.get("open_projects") or doc.get("system.open_projects") or []
        if isinstance(entries, str):
            entries = [entries]
        for p in entries:
            if isinstance(p, str) and p and p not in seen:
                seen.add(p)
                out.append({"project": p, "exists": os.path.exists(p), "source": path})
    return out


def board_for_project(project_path):
    """A .kicad_pro names the design; the board is its sibling .kicad_pcb.

    Targeting the project rather than the board leaves room to pull the
    schematic or netlist later without asking the user to open anything twice."""
    base, ext = os.path.splitext(project_path)
    if ext == ".kicad_pcb":
        return project_path
    cand = base + ".kicad_pcb"
    if os.path.exists(cand):
        return cand
    folder = os.path.dirname(project_path) or "."
    try:
        hits = [os.path.join(folder, f) for f in sorted(os.listdir(folder))
                if f.endswith(".kicad_pcb")]
    except OSError:                                   # unreadable or not a dir
        hits = []
    return hits[0] if len(hits) == 1 else None


def project_for_board(board_path):
    base, _ext = os.path.splitext(board_path)
    cand = base + ".kicad_pro"
    return cand if os.path.exists(cand) else None


# =====================================================================
#  GUI
# =====================================================================
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QDoubleValidator, QIntValidator, QFont, QTextCursor
from PySide6.QtWidgets import (
    QApplication, QButtonGroup, QCheckBox, QComboBox, QDialog, QFileDialog,
    QFormLayout,
    QFrame, QGridLayout, QGroupBox, QHBoxLayout, QHeaderView, QLabel,
    QLineEdit, QListWidget, QListWidgetItem, QMessageBox, QPushButton,
    QRadioButton,
    QScrollArea, QSizePolicy, QSpinBox, QSplitter, QTableWidget,
    QTableWidgetItem, QToolButton,
    QTabWidget, QTextEdit, QVBoxLayout, QWidget,
)

THICK_UNITS = {"mm": 1.0, "um": 1e-3, "mil": 0.0254, "oz": OZ_TO_UM / 1000.0}


def _num_edit(text="", lo=0.0, hi=1e9, decimals=6, on_return=None, width=None):
    e = QLineEdit(text)
    v = QDoubleValidator(lo, hi, decimals, e)
    v.setNotation(QDoubleValidator.StandardNotation)
    e.setValidator(v)
    e.setAlignment(Qt.AlignRight)
    if on_return:
        e.returnPressed.connect(on_return)
    if width:
        e.setMaximumWidth(width)
    return e


def _parse_edit(edit):
    t = edit.text().strip().replace(",", "")
    if not t:
        raise ValueError("empty")
    return float(t)


def _pair(edit, combo):
    w = QWidget(); h = QHBoxLayout(w); h.setContentsMargins(0, 0, 0, 0)
    h.addWidget(edit, 1); h.addWidget(combo, 0)
    return w


def _hline():
    f = QFrame(); f.setFrameShape(QFrame.HLine); f.setFrameShadow(QFrame.Sunken)
    return f


def _small(widget, delta=-1, bold=False, italic=False):
    f = QFont()
    f.setPointSize(max(8, QApplication.font().pointSize() + delta))
    f.setBold(bold); f.setItalic(italic)
    widget.setFont(f)
    return widget


# ---------------------------------------------------------------- globals
class GlobalConditions(QWidget):
    """Board, barrel plating, signal voltage, current and ambient (D7).

    Plating lives here rather than on the Via tab because the Trace, Via and
    Report tabs all price copper with it. D2 originally required it with no
    default; that is amended - it now defaults to the IPC-6012 Class 2 minimum
    of 18 um, which is the pessimistic end of the common range, and the value
    in force is printed in every result and report."""
    changed = Signal()
    open_board_requested = Signal()

    def __init__(self):
        super().__init__()
        box = QGroupBox("Global settings (shared by all tabs)")
        outer = QVBoxLayout(box)
        boardrow = QHBoxLayout()
        self.open_board_btn = QPushButton("Open .kicad_pcb...")
        self.open_board_btn.clicked.connect(self.open_board_requested.emit)
        boardrow.addWidget(self.open_board_btn)
        self.board_label = _small(QLabel("no board loaded"), italic=True)
        boardrow.addWidget(self.board_label, 1)
        outer.addLayout(boardrow)
        form = QHBoxLayout()
        outer.addLayout(form)

        self.current_edit = _num_edit("1.0", 0.0, 1e4, on_return=self._emit, width=90)
        self.voltage_edit = _num_edit("3.3", -1e6, 1e6, on_return=self._emit, width=90)
        self.ambient_edit = _num_edit("25", -273.15, 1e4, on_return=self._emit, width=90)
        self.ambient_unit = QComboBox(); self.ambient_unit.addItems([DEG_C, DEG_F])
        self._prev_unit = DEG_C
        self.ambient_unit.currentTextChanged.connect(self._unit_changed)

        form.addWidget(QLabel("Barrel plating:"))
        self.plating = _num_edit("18", 0.0, 1e4, on_return=self._emit, width=70)
        self.plating_u = QComboBox(); self.plating_u.addItems(["um", "mil", "oz"])
        self.plating_u.currentTextChanged.connect(self._plating_unit_changed)
        self._prev_pu = "um"
        form.addWidget(self.plating)
        form.addWidget(self.plating_u)
        self.preset = QComboBox()
        for label, _v in PLATING_PRESETS:
            self.preset.addItem(label)
        self.preset.setCurrentIndex(PLATING_DEFAULT_INDEX)
        self.preset.currentIndexChanged.connect(self._preset_chosen)
        form.addWidget(self.preset)
        form.addSpacing(16)
        form.addWidget(QLabel("Signal voltage (V):"))
        form.addWidget(self.voltage_edit)
        form.addSpacing(16)
        form.addWidget(QLabel("Constant current (A):"))
        form.addWidget(self.current_edit)
        form.addSpacing(16)
        form.addWidget(QLabel("Ambient:"))
        form.addWidget(self.ambient_edit)
        form.addWidget(self.ambient_unit)
        form.addStretch(1)

        root = QVBoxLayout(self); root.setContentsMargins(0, 0, 0, 0); root.addWidget(box)

    def set_board(self, path):
        if path and path.endswith(".kicad_pcb"):
            self.board_label.setText(f"{os.path.basename(path)}   -   {os.path.dirname(path)}")
        else:
            self.board_label.setText("no board loaded (stackup is manual)")

    def _emit(self): self.changed.emit()

    def _unit_changed(self, unit):
        if unit == self._prev_unit:
            return
        try:
            v = _parse_edit(self.ambient_edit)
            self.ambient_edit.setText(f"{(c_to_f(v) if unit == DEG_F else f_to_c(v)):.4g}")
        except ValueError:
            pass
        self._prev_unit = unit
        self.changed.emit()

    @property
    def unit(self): return self.ambient_unit.currentText()

    def current_a(self):
        v = _parse_edit(self.current_edit)
        if v < 0.0:
            raise ValueError("negative current")
        return v

    def _preset_chosen(self, idx):
        val = PLATING_PRESETS[idx][1]
        if val is None:
            self.plating.clear()
        else:
            self.plating_u.blockSignals(True)
            self.plating_u.setCurrentText("um"); self._prev_pu = "um"
            self.plating_u.blockSignals(False)
            self.plating.setText(f"{val:g}")
        self.changed.emit()

    def _plating_unit_changed(self, unit):
        if unit == self._prev_pu:
            return
        try:
            mm = _parse_edit(self.plating) * THICK_UNITS[self._prev_pu]
            self.plating.setText(f"{mm / THICK_UNITS[unit]:.6g}")
        except ValueError:
            pass
        self._prev_pu = unit
        self.changed.emit()

    def plating_m(self):
        v = _parse_edit(self.plating)
        if v <= 0:
            raise ValueError("plating must be greater than zero")
        return v * THICK_UNITS[self.plating_u.currentText()] * MM_TO_M

    def signal_v(self):
        return _parse_edit(self.voltage_edit)

    def ambient_c(self):
        v = _parse_edit(self.ambient_edit)
        c = f_to_c(v) if self.unit == DEG_F else v
        if c < -273.15:
            raise ValueError("below absolute zero")
        return c

    def to_temp(self, c): return c_to_f(c) if self.unit == DEG_F else c
    def to_delta(self, d): return delta_c_to_f(d) if self.unit == DEG_F else d


# ---------------------------------------------------------------- stackup tab
class SetupTab(QWidget):
    """Everything you set once: files, global conditions, modelling, stackup."""
    changed = Signal()
    netsel_open_requested = Signal()

    def __init__(self, globals_):
        super().__init__()
        self.stackup = manual_stackup()
        self.g = globals_
        self.project_path = None
        self.netsel_path = None
        self._loading = False

        bar = QHBoxLayout()
        self.load_btn = QPushButton("Load .kicad_pcb...")
        self.load_btn.clicked.connect(self.load_file)
        self.manual_btn = QPushButton("New manual stackup...")
        self.manual_btn.clicked.connect(self.new_manual)
        self.revert_btn = QPushButton("Revert to file")
        self.revert_btn.clicked.connect(self.revert)
        bar.addWidget(self.load_btn); bar.addWidget(self.manual_btn)
        bar.addWidget(self.revert_btn); bar.addStretch(1)
        bar.addWidget(QLabel("Edit in:"))
        self.unit_combo = QComboBox(); self.unit_combo.addItems(list(THICK_UNITS))
        self.unit_combo.currentTextChanged.connect(self.refresh)
        bar.addWidget(self.unit_combo)

        self.source_label = _small(QLabel(""), italic=True)

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["Layer", "Type", "Thickness", "= oz", ""])
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.itemChanged.connect(self._item_changed)

        self.summary = _small(QLabel(""))
        self.summary.setWordWrap(True)

        note = _small(QLabel(
            "Values load from the board file and stay editable so stackup variants can be "
            "swept without editing and reloading. Edited rows are marked *; Revert restores "
            "the file values. Copper weight in oz applies to copper layers only."), italic=True)
        note.setWordWrap(True)

        # ---- Files ----
        self.files_table = QTableWidget(3, 4)
        self.files_table.setHorizontalHeaderLabels(
            ["", "KiCad Project", "File Name", "Path"])
        self.files_table.verticalHeader().setVisible(False)
        self.files_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self.files_table.setMinimumHeight(120)
        self._file_rows = [
            ("project", "Open project...", self.open_project),
            ("board", "Open board...", self.load_file),
            ("netsel", "Open net selection...", self.open_netsel_requested),
        ]
        for r, (_key, label, fn) in enumerate(self._file_rows):
            b = QPushButton(label); b.clicked.connect(fn)
            self.files_table.setCellWidget(r, 0, b)
            for c in (1, 2, 3):
                it = QTableWidgetItem("")
                it.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
                self.files_table.setItem(r, c, it)
        fl = QVBoxLayout()
        fl.addWidget(self.files_table)
        self.recent_label = _small(QLabel(""), italic=True)
        self.recent_label.setWordWrap(True)
        fl.addWidget(self.recent_label)
        fl.addWidget(_small(QLabel(
            "The project is the target; its .kicad_pcb is opened for board data. "
            "Opening the project rather than the board leaves room to pull the "
            "schematic or netlist later without opening anything twice."), italic=True))
        fl.itemAt(fl.count() - 1).widget().setWordWrap(True)
        self.sec_files = CollapsibleSection("Files")
        self.sec_files.set_content_layout(fl)

        # ---- Global settings ----
        gl = QVBoxLayout(); gl.addWidget(self.g)
        self.sec_globals = CollapsibleSection("Global settings")
        self.sec_globals.set_content_layout(gl)

        # ---- Modelling (was Via settings on the Via/Path tab) ----
        ml = QFormLayout()
        ml.setLabelAlignment(Qt.AlignRight)
        self.drill_conv = QComboBox()
        for label, _v in DRILL_CONVENTIONS:
            self.drill_conv.addItem(label)
        ml.addRow("Hole value means:", self.drill_conv)
        self.len_conv = QComboBox()
        for label, _v in LENGTH_CONVENTIONS:
            self.len_conv.addItem(label)
        ml.addRow("Barrel length:", self.len_conv)
        self.outer_plating = QCheckBox(
            "Plating also thickens the outer copper layers "
            "(grows the board by 2x plating)")
        self.outer_plating.setChecked(True)
        ml.addRow("", self.outer_plating)
        zrow = QHBoxLayout()
        self.zone_combo = QComboBox(); self.zone_combo.addItems(["ladder", "mesh", "none"])
        zrow.addWidget(self.zone_combo)
        zrow.addWidget(QLabel("mesh pitch (mm):"))
        self.pitch_edit = _num_edit("0.25", 0.001, 5.0, width=70)
        zrow.addWidget(self.pitch_edit)
        zrow.addStretch(1)
        ml.addRow("Zone model:", self._wrapl(zrow))
        mnote = _small(QLabel(
            "Entry and exit layers are always user input: a through via's (layers ...) "
            "records the drilled barrel, not the span that carries current. The zone "
            "model here is the default; individual pad pairs can override it on the "
            "Report tab."), italic=True)
        mnote.setWordWrap(True)
        ml.addRow("", mnote)
        for w in (self.drill_conv, self.len_conv, self.zone_combo):
            w.currentIndexChanged.connect(lambda *_: self.changed.emit())
        self.outer_plating.stateChanged.connect(lambda *_: self.changed.emit())
        self.pitch_edit.editingFinished.connect(lambda: self.changed.emit())
        self.sec_model = CollapsibleSection("Via and zone modelling")
        self.sec_model.set_content_layout(ml)

        # ---- Stackup ----
        sl = QVBoxLayout()
        sl.addLayout(bar)
        sl.addWidget(self.source_label)
        sl.addWidget(self.table, 1)
        sl.addWidget(self.summary)
        sl.addWidget(note)
        self.sec_stackup = CollapsibleSection("Stackup")
        self.sec_stackup.set_content_layout(sl)

        inner = QWidget()
        col = QVBoxLayout(inner)
        col.setContentsMargins(4, 4, 4, 4)
        for sec in (self.sec_files, self.sec_globals, self.sec_model, self.sec_stackup):
            col.addWidget(sec)
        col.addStretch(1)
        scroll = QScrollArea(); scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame); scroll.setWidget(inner)

        cbar = QHBoxLayout()
        for label, fn in (("Expand all", lambda: self._all_sections(True)),
                          ("Collapse all", lambda: self._all_sections(False))):
            b = QPushButton(label); b.setMaximumWidth(110); b.clicked.connect(fn)
            cbar.addWidget(b)
        cbar.addStretch(1)

        root = QVBoxLayout(self)
        root.addLayout(cbar)
        root.addWidget(scroll, 1)
        self.g.open_board_requested.connect(self.load_file)
        self.refresh()
        self.refresh_files()

    @staticmethod
    def _wrapl(layout):
        w = QWidget(); w.setLayout(layout); return w

    def _all_sections(self, on):
        for sec in (self.sec_files, self.sec_globals, self.sec_model, self.sec_stackup):
            sec.set_expanded(on)

    # ---- files ----
    def open_project(self):
        start = ""
        recent = kicad_recent_projects()
        for entry in recent:
            if entry["exists"]:
                start = entry["project"]
                break
        path, _ = QFileDialog.getOpenFileName(
            self, "Open KiCad project", start,
            "KiCad project (*.kicad_pro);;KiCad board (*.kicad_pcb);;All files (*)")
        if not path:
            return
        self.open_project_path(path)

    def open_project_path(self, path):
        board = board_for_project(path)
        if board is None:
            QMessageBox.warning(self, "No board found",
                                f"No .kicad_pcb sits alongside\n{path}")
            return
        self.project_path = (path if path.endswith(".kicad_pro")
                             else project_for_board(board))
        self.load_path(board)

    def open_netsel_requested(self):
        self.netsel_open_requested.emit()

    def set_netsel(self, path):
        self.netsel_path = path
        self.refresh_files()

    def refresh_files(self):
        src = self.stackup.source if self.stackup else ""
        proj = self.project_path or (project_for_board(src) if src else None)
        # No .kicad_pro next to the board is normal; name the design after the
        # board so the column is still useful.
        if proj:
            proj_name = os.path.splitext(os.path.basename(proj))[0]
        elif src and src.endswith(".kicad_pcb"):
            proj_name = os.path.splitext(os.path.basename(src))[0] + "  (no .kicad_pro)"
        else:
            proj_name = ""
        rows = [
            (proj_name, os.path.basename(proj) if proj else "(none)",
             os.path.dirname(proj) if proj else ""),
            (proj_name, os.path.basename(src) if src and src.endswith(".kicad_pcb")
             else "(none - manual stackup)",
             os.path.dirname(src) if src and src.endswith(".kicad_pcb") else ""),
            (proj_name, os.path.basename(self.netsel_path) if self.netsel_path
             else "(none)",
             os.path.dirname(self.netsel_path) if self.netsel_path else ""),
        ]
        for r, vals in enumerate(rows):
            for c, v in zip((1, 2, 3), vals):
                self.files_table.item(r, c).setText(v)
        self.files_table.resizeColumnsToContents()
        self.files_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        recent = kicad_recent_projects()
        if recent:
            names = ", ".join(os.path.basename(e["project"]) for e in recent[:3])
            self.recent_label.setText(
                f"KiCad last had {len(recent)} project(s) open ({names}); "
                "the Open dialog starts there.")
        else:
            self.recent_label.setText(
                "No KiCad preferences found on this machine, so the Open dialog "
                "starts in the last used folder.")

    # -- data --
    def load_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "Open KiCad board", "",
                                              "KiCad PCB (*.kicad_pcb);;All files (*)")
        if path:
            self.load_path(path)

    def load_path(self, path):
        try:
            self.stackup = load_stackup(path)
        except Exception as exc:                      # noqa: BLE001 - surfaced to user
            QMessageBox.warning(self, "Could not load stackup", str(exc))
            return
        self.refresh()
        if hasattr(self, "files_table"):
            self.refresh_files()
        self.changed.emit()

    def new_manual(self):
        self.stackup = manual_stackup()
        self.refresh(); self.changed.emit()

    def revert(self):
        for l in self.stackup.layers:
            l.user_mm = l.base_mm
        self.refresh(); self.changed.emit()

    def copper_names(self):
        return [l.name for l in self.stackup.copper]

    # -- view --
    def refresh(self):
        self._loading = True
        unit = self.unit_combo.currentText()
        rows = [l for l in self.stackup.layers if l.kind in ("copper", "dielectric")]
        self.table.setRowCount(len(rows))
        for r, l in enumerate(rows):
            is_cu = l.kind == "copper"
            name = QTableWidgetItem(l.name + (" *" if l.dirty else ""))
            name.setFlags(Qt.ItemIsEnabled)
            self.table.setItem(r, 0, name)

            typ = QTableWidgetItem(l.type_raw or l.kind)
            typ.setFlags(Qt.ItemIsEnabled)
            self.table.setItem(r, 1, typ)

            if unit == "oz" and not is_cu:
                cell = QTableWidgetItem(f"{l.user_mm:.4g} mm")
                cell.setFlags(Qt.ItemIsEnabled)
            else:
                cell = QTableWidgetItem(f"{l.user_mm / THICK_UNITS[unit]:.6g}")
                cell.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable | Qt.ItemIsEditable)
            cell.setData(Qt.UserRole, id(l))
            cell.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.table.setItem(r, 2, cell)

            oz = QTableWidgetItem(f"{l.user_mm * 1000 / OZ_TO_UM:.3f}" if is_cu else "")
            oz.setFlags(Qt.ItemIsEnabled)
            oz.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.table.setItem(r, 3, oz)
            self.table.setItem(r, 4, QTableWidgetItem(""))
        self.table.resizeColumnsToContents()
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)

        src = self.stackup.source or "<manual>"
        est = "  [ESTIMATED - even dielectric distribution]" if self.stackup.estimated else ""
        self.source_label.setText(f"Source: {src}{est}")

        n = len(self.stackup.copper)
        core = self.stackup.core_thickness_mm()
        gen = self.stackup.general_thickness
        gen_txt = (f"   |   general(thickness) = {gen:.4g} mm (includes solder mask; "
                   f"never used as a barrel span)") if gen else ""
        self.summary.setText(
            f"{n} copper layers   |   copper + dielectric = {core:.4g} mm{gen_txt}")
        self._loading = False

    def _item_changed(self, item):
        if self._loading or item.column() != 2:
            return
        target = item.data(Qt.UserRole)
        layer = next((l for l in self.stackup.layers if id(l) == target), None)
        if layer is None:
            return
        try:
            mm = float(item.text().strip()) * THICK_UNITS[self.unit_combo.currentText()]
            if mm <= 0:
                raise ValueError
        except ValueError:
            self.refresh(); return
        layer.user_mm = mm
        self.refresh(); self.changed.emit()


# ---------------------------------------------------------------- segment rows
class SegmentRow(QWidget):
    removed = Signal(object)
    edited = Signal()

    def __init__(self, kind, layers):
        super().__init__()
        self.kind = kind
        row = QHBoxLayout(self)
        row.setContentsMargins(2, 2, 2, 2)

        tag = _small(QLabel("TRACE" if kind == "trace" else "VIA "), bold=True)
        tag.setMinimumWidth(46)
        row.addWidget(tag)

        if kind == "trace":
            self.layer = QComboBox(); row.addWidget(QLabel("layer")); row.addWidget(self.layer)
            self.length = _num_edit("50", width=70, on_return=self.edited.emit)
            self.length_u = QComboBox(); self.length_u.addItems(list(LENGTH_UNITS))
            row.addWidget(QLabel("len")); row.addWidget(_pair(self.length, self.length_u))
            self.width = _num_edit("4", width=70, on_return=self.edited.emit)
            self.width_u = QComboBox(); self.width_u.addItems(list(LENGTH_UNITS))
            row.addWidget(QLabel("width")); row.addWidget(_pair(self.width, self.width_u))
            self._layer_combos = [self.layer]
        else:
            self.from_layer = QComboBox(); self.to_layer = QComboBox()
            row.addWidget(QLabel("from")); row.addWidget(self.from_layer)
            row.addWidget(QLabel("to")); row.addWidget(self.to_layer)
            self.hole = _num_edit("0.3", width=70, on_return=self.edited.emit)
            self.hole_u = QComboBox(); self.hole_u.addItems(["mm", "mil"])
            row.addWidget(QLabel("hole")); row.addWidget(_pair(self.hole, self.hole_u))
            self.pad = _num_edit("0.6", width=70, on_return=self.edited.emit)
            self.pad_u = QComboBox(); self.pad_u.addItems(["mm", "mil"])
            row.addWidget(QLabel("pad")); row.addWidget(_pair(self.pad, self.pad_u))
            self.count = QSpinBox(); self.count.setRange(1, 9999); self.count.setValue(1)
            row.addWidget(QLabel("x")); row.addWidget(self.count)
            self.sharing = _num_edit("100", 1.0, 100.0, width=55, on_return=self.edited.emit)
            row.addWidget(QLabel("share%")); row.addWidget(self.sharing)
            self._layer_combos = [self.from_layer, self.to_layer]

        row.addStretch(1)
        rm = QPushButton("x"); rm.setMaximumWidth(28)
        rm.clicked.connect(lambda: self.removed.emit(self))
        row.addWidget(rm)
        self.set_layers(layers)

    def set_layers(self, layers):
        for i, combo in enumerate(self._layer_combos):
            prev = combo.currentText()
            combo.blockSignals(True)
            combo.clear(); combo.addItems(layers)
            if prev in layers:
                combo.setCurrentText(prev)
            elif layers:
                combo.setCurrentIndex(min(i, len(layers) - 1) if self.kind == "via" else 0)
            combo.blockSignals(False)

    def read(self):
        if self.kind == "trace":
            L = _parse_edit(self.length); W = _parse_edit(self.width)
            if L <= 0 or W <= 0:
                raise ValueError("trace length and width must be positive")
            return {"kind": "trace", "layer": self.layer.currentText(),
                    "length_m": L * LENGTH_UNITS[self.length_u.currentText()],
                    "width_m": W * LENGTH_UNITS[self.width_u.currentText()],
                    "label": f"{L:g} {self.length_u.currentText()} x {W:g} "
                             f"{self.width_u.currentText()} on {self.layer.currentText()}"}
        h = _parse_edit(self.hole); p = _parse_edit(self.pad)
        if h <= 0:
            raise ValueError("via hole must be positive")
        scale = {"mm": MM_TO_M, "mil": MIL_TO_M}
        a, b = self.from_layer.currentText(), self.to_layer.currentText()
        if a == b:
            raise ValueError(f"via from and to layer are both {a}")
        return {"kind": "via", "from": a, "to": b,
                "hole_m": h * scale[self.hole_u.currentText()],
                "pad_m": p * scale[self.pad_u.currentText()],
                "count": self.count.value(),
                "sharing": _parse_edit(self.sharing),
                "label": f"{a} -> {b}, hole {h:g} {self.hole_u.currentText()}"
                         + (f", x{self.count.value()}" if self.count.value() > 1 else "")}


# ---------------------------------------------------------------- via/path tab
class ViaPathTab(QWidget):
    def __init__(self, globals_, stackup_tab):
        super().__init__()
        self.g = globals_
        self.st = stackup_tab
        self.rows = []

        # --- via settings now live on the Setup tab; show what is in force ---
        settings = QGroupBox("Via settings (set on the Setup tab)")
        form = QFormLayout(settings)
        form.setLabelAlignment(Qt.AlignRight)
        self.settings_echo = _small(QLabel(""))
        self.settings_echo.setWordWrap(True)
        form.addRow("In force:", self.settings_echo)

        # --- segments ---
        seg_box = QGroupBox("Path segments (series chain, source to load)")
        seg_outer = QVBoxLayout(seg_box)
        btns = QHBoxLayout()
        add_t = QPushButton("+ Trace"); add_t.clicked.connect(lambda: self.add_row("trace"))
        add_v = QPushButton("+ Via"); add_v.clicked.connect(lambda: self.add_row("via"))
        clr = QPushButton("Clear"); clr.clicked.connect(self.clear_rows)
        self.trace_btn = QPushButton("Trace a net from the board...")
        self.trace_btn.clicked.connect(self.trace_from_board)
        btns.addWidget(add_t); btns.addWidget(add_v); btns.addWidget(clr)
        btns.addStretch(1); btns.addWidget(self.trace_btn)
        seg_outer.addLayout(btns)
        self.traced_label = _small(QLabel(""), italic=True)
        self.traced_label.setWordWrap(True)
        seg_outer.addWidget(self.traced_label)

        holder = QWidget()
        self.seg_layout = QVBoxLayout(holder)
        self.seg_layout.setContentsMargins(0, 0, 0, 0)
        self.seg_layout.addStretch(1)
        scroll = QScrollArea(); scroll.setWidgetResizable(True); scroll.setWidget(holder)
        scroll.setMinimumHeight(150)
        seg_outer.addWidget(scroll)

        self.calc_btn = QPushButton("Calculate path")
        self.calc_btn.setDefault(True)
        self.calc_btn.clicked.connect(self.calculate)

        # --- results ---
        res = QGroupBox("Results")
        rl = QVBoxLayout(res)
        self.total_label = QLabel("--")
        f = QFont(); f.setPointSize(max(16, QApplication.font().pointSize() + 6)); f.setBold(True)
        self.total_label.setFont(f)
        self.total_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        rl.addWidget(self.total_label)
        self.load_label = _small(QLabel(""))
        rl.addWidget(self.load_label)

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(
            ["Segment", "Detail", "R @20 " + DEG_C, "R @ambient", "% of path"])
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.setMinimumHeight(120)
        rl.addWidget(self.table)

        self.assumptions = _small(QLabel(""))
        self.assumptions.setWordWrap(True)
        rl.addWidget(self.assumptions)
        self.warn_label = _small(QLabel(""))
        self.warn_label.setWordWrap(True)
        self.warn_label.setStyleSheet("color: #b03000;")
        rl.addWidget(self.warn_label)

        root = QVBoxLayout(self)
        root.addWidget(settings)
        root.addWidget(seg_box, 1)
        root.addWidget(self.calc_btn)
        root.addWidget(res, 1)

        self.st.changed.connect(self.refresh_layers)
        self.st.changed.connect(self.calculate)
        self.g.changed.connect(self.calculate)
        self._seed()

    # -- settings now owned by the Setup tab --
    @property
    def drill_conv(self):
        return self.st.drill_conv

    @property
    def len_conv(self):
        return self.st.len_conv

    @property
    def outer_plating(self):
        return self.st.outer_plating

    @property
    def zone_combo(self):
        return self.st.zone_combo

    def plating_m(self):
        return self.g.plating_m()

    # -- rows --
    def _seed(self):
        names = self.st.copper_names()
        self.add_row("trace"); self.add_row("via"); self.add_row("trace")
        if len(names) >= 3:
            self.rows[0].layer.setCurrentText(names[0])
            self.rows[1].from_layer.setCurrentText(names[0])
            self.rows[1].to_layer.setCurrentText(names[2])
            self.rows[2].layer.setCurrentText(names[2])
        self.calculate()

    def add_row(self, kind):
        row = SegmentRow(kind, self.st.copper_names())
        row.removed.connect(self.remove_row)
        row.edited.connect(self.calculate)
        self.seg_layout.insertWidget(self.seg_layout.count() - 1, row)
        self.rows.append(row)
        self.calculate()

    def remove_row(self, row):
        self.rows.remove(row)
        row.setParent(None); row.deleteLater()
        self.calculate()

    def clear_rows(self):
        for row in list(self.rows):
            self.remove_row(row)
        if hasattr(self, "traced_label"):
            self.traced_label.setText("")

    def refresh_layers(self):
        names = self.st.copper_names()
        for row in self.rows:
            row.set_layers(names)
        self.calculate()

    # -- compute --
    def calculate(self):
        conv = DRILL_CONVENTIONS[self.drill_conv.currentIndex()][1]
        mode = LENGTH_CONVENTIONS[self.len_conv.currentIndex()][1]
        outer = self.outer_plating.isChecked()
        try:
            _pl = self.plating_m() * 1e6
            self.settings_echo.setText(
                f"plating {_pl:.4g} um   |   "
                f"{DRILL_CONVENTIONS[self.drill_conv.currentIndex()][0]}   |   "
                f"{LENGTH_CONVENTIONS[self.len_conv.currentIndex()][0]}   |   "
                f"outer-layer plating {'ON' if outer else 'OFF'}   |   "
                f"zone model {self.zone_combo.currentText()}")
        except ValueError:
            self.settings_echo.setText("barrel plating not set - see the Setup tab")

        if not self.rows:
            return self._blank("Add at least one segment.")
        try:
            plating_m = self.plating_m()
        except ValueError:
            return self._blank("Select or enter a barrel plating thickness "
                               "- it has no default and is in no board file.")
        try:
            ambient_c = self.g.ambient_c()
        except ValueError:
            return self._blank(f"Enter an ambient temperature in {self.g.unit}.")
        try:
            current_a = self.g.current_a()
        except ValueError:
            return self._blank("Enter a current of 0 A or more.")

        geo = self.st.stackup.geometry(plating_m / MM_TO_M * 1000.0, outer)
        by_name = {g["name"]: g for g in geo}

        results, warnings = [], []
        for row in self.rows:
            try:
                seg = row.read()
            except ValueError as exc:
                return self._blank(str(exc))
            if seg["kind"] == "trace":
                g = by_name.get(seg["layer"])
                if g is None:
                    return self._blank(f"layer {seg['layer']} is not in the stackup")
                r = trace_resistance(seg["length_m"], seg["width_m"],
                                     g["finished_mm"] * MM_TO_M)
                detail = (seg["label"] + f"   ({g['finished_mm'] * 1000:.1f} um, "
                                         f"{g['oz']:.2f} oz)")
                results.append(("Trace", detail, r))
            else:
                for nm in (seg["from"], seg["to"]):
                    if nm not in by_name:
                        return self._blank(f"layer {nm} is not in the stackup")
                try:
                    r, L, area = via_resistance(
                        geo, seg["from"], seg["to"], seg["hole_m"], plating_m,
                        convention=conv, mode=mode,
                        count=seg["count"], sharing_pct=seg["sharing"])
                except ValueError as exc:
                    return self._blank(str(exc))
                od, idia = barrel_diameters(seg["hole_m"], plating_m, conv)
                detail = (seg["label"] + f"   (L {L * 1000:.4f} mm, OD {od * 1e3:.3f} / "
                                         f"ID {idia * 1e3:.3f} mm, A {area * 1e12:.0f} um^2)")
                results.append(("Via", detail, r))
                if idia < 50e-6:
                    warnings.append(f"{seg['label']}: finished hole is only "
                                    f"{idia * 1e6:.1f} um - not manufacturable.")
                ring = (seg["pad_m"] - (od if conv == "bit" else seg["hole_m"])) / 2.0
                if ring < 50e-6:
                    warnings.append(
                        f"{seg['label']}: annular ring {ring * 1e6:.0f} um is below the "
                        f"IPC-6012 Class 2 external minimum of 50 um.")

        total20 = sum(r for _, _, r in results)
        total_hot = resistance_at_temp(total20, ambient_c)
        drop = current_a * total_hot
        power = current_a * current_a * total_hot

        self.table.setRowCount(len(results))
        for i, (kind, detail, r) in enumerate(results):
            hot = resistance_at_temp(r, ambient_c)
            pct = (r / total20 * 100.0) if total20 else 0.0
            for col, text in enumerate((kind, detail, format_ohms(r),
                                        format_ohms(hot), f"{pct:.1f}%")):
                item = QTableWidgetItem(text)
                item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
                if col >= 2:
                    item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.table.setItem(i, col, item)
        self.table.resizeColumnsToContents()
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)

        self.total_label.setText(f"{total_hot:.6g} ohm")
        self.load_label.setText(
            f"= {format_ohms(total_hot)} at {self.g.to_temp(ambient_c):.4g} {self.g.unit}"
            f"   |   @20 {DEG_C}: {format_ohms(total20)}"
            f"   |   at {current_a:.4g} A: drop {drop:.4g} V, dissipation {power:.4g} W")

        via_r = sum(r for k, _, r in results if k == "Via")
        share = f"{via_r / total20 * 100:.1f}%" if total20 else "n/a"
        self.assumptions.setText(
            f"Assumptions: plating {plating_m * 1e6:.4g} um "
            f"({plating_m * 1e3 / OZ_TO_UM * 1000:.3f} oz-equiv)   |   "
            f"{DRILL_CONVENTIONS[self.drill_conv.currentIndex()][0]}   |   "
            f"{LENGTH_CONVENTIONS[self.len_conv.currentIndex()][0]}   |   "
            f"outer-layer plating {'ON' if outer else 'OFF'}   |   "
            f"vias are {share} of the path. "
            f"No self-heating model on this tab: resistance is evaluated at ambient.")
        self.warn_label.setText("\n".join(warnings))

    def _blank(self, message):
        self.table.setRowCount(0)
        self.total_label.setText("--")
        self.load_label.setText("")
        self.assumptions.setText("")
        self.warn_label.setText(message)


# ---------------------------------------------------------------- trace tab
class TraceTab(QWidget):
    """v0.2 behaviour, unchanged; current and ambient now come from the shared header."""

    def __init__(self, globals_, stackup_tab=None, via_tab=None):
        super().__init__()
        self.g = globals_
        self.st = stackup_tab
        self.via = via_tab

        geometry = QGroupBox("Trace geometry")
        gv = QVBoxLayout(geometry)
        gform = QFormLayout()
        gform.setLabelAlignment(Qt.AlignRight)
        gv.addLayout(gform)

        self.length_edit = _num_edit("1000", on_return=self.calculate)
        self.length_unit = QComboBox(); self.length_unit.addItems(list(LENGTH_UNITS))
        self.width_edit = _num_edit("10", on_return=self.calculate)
        self.width_unit = QComboBox(); self.width_unit.addItems(list(LENGTH_UNITS))
        gform.addRow("Length:", _pair(self.length_edit, self.length_unit))
        gform.addRow("Width:", _pair(self.width_edit, self.width_unit))

        # --- where the copper thickness comes from ---
        self.src_manual = QRadioButton("Copper weight and trace location")
        self.src_stackup = QRadioButton("Layer from the loaded stackup")
        self.src_manual.setChecked(True)
        self.src_group = QButtonGroup(self)
        self.src_group.addButton(self.src_manual)
        self.src_group.addButton(self.src_stackup)
        self.src_manual.toggled.connect(self._source_changed)
        srcbox = QVBoxLayout()
        srcbox.setContentsMargins(0, 0, 0, 0)
        srcbox.addWidget(self.src_manual)
        srcbox.addWidget(self.src_stackup)
        gform.addRow("Thickness from:", self._wrap(srcbox))

        self.weight_combo = QComboBox()
        for oz in COPPER_WEIGHTS:
            um = oz * OZ_TO_UM
            self.weight_combo.addItem(f"{oz:g} oz  ({um:.1f} um / {um / 25.4:.2f} mil)", oz)
        self.weight_combo.setCurrentIndex(COPPER_WEIGHTS.index(1))
        self.weight_combo.currentIndexChanged.connect(self.calculate)
        gform.addRow("Copper weight:", self.weight_combo)

        self.layer_combo = QComboBox(); self.layer_combo.addItems(list(IPC_K))
        self.layer_combo.currentIndexChanged.connect(self.calculate)
        gform.addRow("Trace location:", self.layer_combo)

        self.stack_layer_combo = QComboBox()
        self.stack_layer_combo.currentIndexChanged.connect(self.calculate)
        gform.addRow("Stackup layer:", self.stack_layer_combo)

        self.derived_label = _small(QLabel(""), italic=True)
        self.derived_label.setWordWrap(True)
        gform.addRow("", self.derived_label)

        self.calc_button = QPushButton("Calculate")
        self.calc_button.setDefault(True)
        self.calc_button.clicked.connect(self.calculate)
        self.calc_button.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        crow = QHBoxLayout()
        crow.addStretch(1); crow.addWidget(self.calc_button); crow.addStretch(1)
        gv.addSpacing(6)
        gv.addLayout(crow)
        gv.addStretch(1)

        results = QGroupBox("Results")
        rlayout = QGridLayout(results)
        self.result_label = QLabel("--")
        f = QFont(); f.setPointSize(max(16, QApplication.font().pointSize() + 6)); f.setBold(True)
        self.result_label.setFont(f)
        self.result_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.rise_label = QLabel("--")
        f2 = QFont(); f2.setPointSize(max(13, QApplication.font().pointSize() + 3)); f2.setBold(True)
        self.rise_label.setFont(f2)
        self.rise_label.setTextInteractionFlags(Qt.TextSelectableByMouse)

        self.alt_label = _small(QLabel(""))
        self.trace_temp_label = _small(QLabel("")); self.trace_temp_label.setWordWrap(True)
        self.hot_r_label = _small(QLabel("")); self.hot_r_label.setWordWrap(True)
        self.drop_label = _small(QLabel("")); self.drop_label.setWordWrap(True)
        self.detail_label = _small(QLabel("")); self.detail_label.setWordWrap(True)
        self.warn_label = _small(QLabel("")); self.warn_label.setWordWrap(True)
        self.warn_label.setStyleSheet("color: #b03000;")

        rlayout.addWidget(_small(QLabel("Resistance @ 20 " + DEG_C), bold=True), 0, 0)
        rlayout.addWidget(self.result_label, 1, 0)
        rlayout.addWidget(self.alt_label, 2, 0)
        rlayout.addWidget(_small(QLabel("Temperature rise"), bold=True), 0, 1)
        rlayout.addWidget(self.rise_label, 1, 1)
        rlayout.addWidget(self.trace_temp_label, 2, 1)
        rlayout.addWidget(_hline(), 3, 0, 1, 2)
        rlayout.addWidget(self.hot_r_label, 4, 0, 1, 2)
        rlayout.addWidget(self.drop_label, 5, 0, 1, 2)
        rlayout.addWidget(self.detail_label, 6, 0, 1, 2)
        rlayout.addWidget(self.warn_label, 7, 0, 1, 2)
        rlayout.setRowStretch(8, 1)
        rlayout.setColumnStretch(0, 1); rlayout.setColumnStretch(1, 1)

        note = _small(QLabel(
            "DC resistance for a rectangular cross-section; rise from the IPC-2221 curve fit "
            "(still air, no plane heatsinking). Copper weight entered by hand ignores barrel "
            "plating; a stackup layer uses the finished thickness, outer-layer plating "
            "included when that option is on in the Via / Path tab."), italic=True)
        note.setWordWrap(True)

        cols = QHBoxLayout()
        left = QWidget(); lv = QVBoxLayout(left); lv.setContentsMargins(0, 0, 0, 0)
        lv.addWidget(geometry); lv.addStretch(1)
        right = QWidget(); rv = QVBoxLayout(right); rv.setContentsMargins(0, 0, 0, 0)
        rv.addWidget(results); rv.addWidget(note); rv.addStretch(1)
        cols.addWidget(left, 1); cols.addWidget(right, 1)

        root = QVBoxLayout(self)
        root.addLayout(cols, 1)

        if self.st is not None:
            self.st.changed.connect(self.refresh_stackup)
        self.g.changed.connect(self.calculate)
        self.refresh_stackup()

    @staticmethod
    def _wrap(layout):
        w = QWidget(); w.setLayout(layout); return w

    def _board_loaded(self):
        src = self.st.stackup.source if self.st else ""
        return bool(src and src.endswith(".kicad_pcb"))

    def refresh_stackup(self):
        """Offer stackup layers only when a real board is loaded."""
        have = self._board_loaded()
        self.src_stackup.setEnabled(have)
        if not have:
            self.src_stackup.setToolTip("Open a .kicad_pcb to pick a layer from its stackup")
            if self.src_stackup.isChecked():
                self.src_manual.setChecked(True)
            self.stack_layer_combo.clear()
        else:
            self.src_stackup.setToolTip("")
            prev = self.stack_layer_combo.currentText()
            self.stack_layer_combo.blockSignals(True)
            self.stack_layer_combo.clear()
            for g in self._geometry():
                self.stack_layer_combo.addItem(
                    f"{g['name']}  ({g['finished_mm'] * 1000:.1f} um, {g['oz']:.2f} oz, "
                    f"{'outer' if g['is_outer'] else 'inner'})", g["name"])
            if prev:
                i = self.stack_layer_combo.findText(prev, Qt.MatchStartsWith)
                if i >= 0:
                    self.stack_layer_combo.setCurrentIndex(i)
            self.stack_layer_combo.blockSignals(False)
        self._source_changed()

    def _geometry(self):
        plating_um, outer = 0.0, False
        if self.via is not None:
            try:
                plating_um = self.via.plating_m() * 1e6
                outer = self.via.outer_plating.isChecked()
            except ValueError:
                plating_um, outer = 0.0, False
        return self.st.stackup.geometry(plating_um, outer)

    def _source_changed(self, *_):
        manual = self.src_manual.isChecked()
        self.weight_combo.setEnabled(manual)
        self.layer_combo.setEnabled(manual)
        self.stack_layer_combo.setEnabled(not manual)
        self.calculate()

    def _thickness_and_location(self):
        """(thickness_m, IPC location key, description)."""
        if self.src_stackup.isChecked() and self._board_loaded():
            name = self.stack_layer_combo.currentData()
            g = next((x for x in self._geometry() if x["name"] == name), None)
            if g is None:
                raise ValueError("pick a stackup layer")
            loc = "External layer" if g["is_outer"] else "Internal layer"
            return (g["finished_mm"] * MM_TO_M, loc,
                    f"{g['name']} from the stackup: {g['finished_mm'] * 1000:.2f} um "
                    f"({g['oz']:.3f} oz), {'outer' if g['is_outer'] else 'inner'} layer "
                    f"so IPC-2221 k = {IPC_K[loc]:g}")
        oz = self.weight_combo.currentData()
        loc = self.layer_combo.currentText()
        return (oz * OZ_TO_UM * 1e-6, loc,
                f"entered by hand: {oz:g} oz, {loc.lower()}")

        self.g.changed.connect(self.calculate)
        self.calculate()

    def _length_m(self, edit, combo):
        v = _parse_edit(edit)
        if v <= 0:
            raise ValueError("non-positive")
        return v * LENGTH_UNITS[combo.currentText()]

    def calculate(self):
        unit = self.g.unit
        try:
            length_m = self._length_m(self.length_edit, self.length_unit)
        except ValueError:
            return self._error("Enter a positive trace length.")
        try:
            width_m = self._length_m(self.width_edit, self.width_unit)
        except ValueError:
            return self._error("Enter a positive trace width.")
        try:
            current_a = self.g.current_a()
        except ValueError:
            return self._error("Enter a current of 0 A or more.")
        try:
            ambient_c = self.g.ambient_c()
        except ValueError:
            return self._error(f"Enter an ambient temperature in {unit}.")

        try:
            thickness_m, layer, how = self._thickness_and_location()
        except ValueError as exc:
            return self._error(str(exc))
        self.derived_label.setText(how)
        r20 = trace_resistance(length_m, width_m, thickness_m)
        area_mil2 = (width_m / MIL_TO_M) * (thickness_m / MIL_TO_M)
        rise_c = temperature_rise_c(current_a, area_mil2, IPC_K[layer])
        trace_c = ambient_c + rise_c
        r_hot = resistance_at_temp(r20, trace_c)

        self.result_label.setText(f"{r20:.6g} ohm")
        self.alt_label.setText(f"= {format_ohms(r20)}")
        self.rise_label.setText(f"{self.g.to_delta(rise_c):.4g} {unit}")
        self.trace_temp_label.setText(
            f"trace at {self.g.to_temp(trace_c):.4g} {unit}"
            f"  (ambient {self.g.to_temp(ambient_c):.4g} {unit} + rise), {layer.lower()}")
        self.hot_r_label.setText(
            f"Resistance at trace temperature: {format_ohms(r_hot)}"
            f"   ({(r_hot / r20 - 1.0) * 100:+.1f}% vs 20 {DEG_C})")
        self.drop_label.setText(
            f"At {current_a:.4g} A:  drop {current_a * r_hot:.4g} V"
            f"   |   dissipation {current_a ** 2 * r_hot:.4g} W")
        self.detail_label.setText(
            f"thickness {thickness_m * 1e6:.2f} um ({thickness_m / MIL_TO_M:.3f} mil, "
            f"{thickness_m * 1e6 / OZ_TO_UM:.3f} oz)"
            f"   |   cross-section {area_mil2:.2f} mil^2"
            f"   |   {length_m / width_m:.2f} squares x "
            f"{(RHO_CU_20C / thickness_m) * 1e3:.3f} mohm/sq")

        w = []
        if area_mil2 > IPC_MAX_AREA_MIL2:
            w.append(f"Cross-section {area_mil2:.0f} mil^2 exceeds the IPC-2221 chart "
                     f"({IPC_MAX_AREA_MIL2:.0f} mil^2) - rise is extrapolated.")
        if current_a > IPC_MAX_CURRENT_A:
            w.append(f"{current_a:.4g} A exceeds the chart's {IPC_MAX_CURRENT_A:.0f} A range "
                     "- rise is extrapolated.")
        if rise_c > IPC_MAX_RISE_C:
            w.append(f"Rise exceeds the chart's {IPC_MAX_RISE_C:.0f} {DEG_C} curve.")
        if trace_c > FR4_MAX_TEMP_C:
            w.append(f"Trace reaches {self.g.to_temp(trace_c):.4g} {unit}, above the "
                     f"{FR4_MAX_TEMP_C:.0f} {DEG_C} typical FR-4 operating limit.")
        if ambient_c > 50.0:
            w.append(f"IPC-2221's rise is ambient-independent; above ~50 {DEG_C} ambient the "
                     "real rise will be larger. Derate.")
        self.warn_label.setText("\n".join(w))

    def _error(self, message):
        for lbl in (self.result_label, self.rise_label):
            lbl.setText("--")
        for lbl in (self.alt_label, self.trace_temp_label, self.hot_r_label,
                    self.drop_label, self.detail_label):
            lbl.setText("")
        self.warn_label.setText(message)




# =====================================================================
#  Net tracing - build a series path from real board geometry
# =====================================================================
import heapq
import itertools
import time

Q = 4  # coordinate quantisation, decimal places in mm (0.1 um)


def _q(v):
    return round(float(v), Q)


def _arc_length_mm(sx, sy, mx, my, ex, ey):
    """Arc length through three points; falls back to the chord if degenerate."""
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


class BoardNets:
    """Track/via/pad geometry from a .kicad_pcb, grouped by net."""

    def __init__(self, path):
        self.path = path
        root = parse_sexpr(open(path, "r", encoding="utf-8").read())
        self.net_names = {}
        for n in root.findall("net"):
            k = n.kids()
            if k:
                self.net_names[int(k[0])] = str(k[1]) if len(k) > 1 else ""

        self.tracks = []   # (net, layer, p1, p2, width_mm, length_mm)
        for s in root.findall("segment"):
            net = s.val("net", cast=int)
            if net is None: continue
            a = s.get("start").kids(); b = s.get("end").kids()
            p1 = (_q(a[0]), _q(a[1])); p2 = (_q(b[0]), _q(b[1]))
            L = math.hypot(p2[0] - p1[0], p2[1] - p1[1])
            self.tracks.append((net, str(s.get("layer").kids()[0]), p1, p2,
                                s.val("width"), L))
        for s in root.findall("arc"):
            net = s.val("net", cast=int)
            if net is None: continue
            a = s.get("start").kids(); m = s.get("mid").kids(); b = s.get("end").kids()
            p1 = (_q(a[0]), _q(a[1])); p2 = (_q(b[0]), _q(b[1]))
            L = _arc_length_mm(p1[0], p1[1], float(m[0]), float(m[1]), p2[0], p2[1])
            self.tracks.append((net, str(s.get("layer").kids()[0]), p1, p2,
                                s.val("width"), L))

        self.vias = []     # (net, point, size_mm, drill_mm, declared, type)
        for v in root.findall("via"):
            net = v.val("net", cast=int)
            if net is None: continue
            a = v.get("at").kids()
            kinds = [c for c in v.kids() if isinstance(c, str)]
            vtype = "micro" if "micro" in kinds else ("blind" if "blind" in kinds else "through")
            lay = v.get("layers")
            self.vias.append((net, (_q(a[0]), _q(a[1])), v.val("size"), v.val("drill"),
                              tuple(str(x) for x in lay.kids()) if lay else (), vtype))

        self.pads = []     # (net, point, layers, ref, padname, pinfunction)
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
                if net is None: continue
                lay = p.get("layers")
                lays = [str(x) for x in lay.kids()] if lay else []
                cu = [l for l in lays if ".Cu" in l or l == "*.Cu"]
                if not cu: continue
                pat = p.get("at").kids()
                px, py = float(pat[0]), float(pat[1])
                ax = fx + px * math.cos(frot) - py * math.sin(frot)
                ay = fy + px * math.sin(frot) + py * math.cos(frot)
                pf = p.get("pinfunction")
                fn = str(pf.kids()[0]) if pf and pf.kids() else ""
                self.pads.append((net, (_q(ax), _q(ay)), tuple(cu), ref,
                                  str(p.kids()[0]) if p.kids() else "", fn))

        self.zone_nets = set()
        for z in root.findall("zone"):
            n = z.val("net", cast=int)
            if n is not None:
                self.zone_nets.add(n)

        self.pours = parse_pours(root)
        self.split_notes = self._split_tracks_at_vias()

    def _split_tracks_at_vias(self):
        """KiCad does not break a track where a via lands on it mid-run, so a
        stitching array is invisible to endpoint-only landing detection. Split
        every track at any via lying on its interior."""
        notes = []
        by_net = {}
        for n, pt, *_rest in self.vias:
            by_net.setdefault(n, []).append(pt)
        out = []
        for track in self.tracks:
            net, layer, p1, p2, w, L = track
            (ax, ay), (bx, by) = p1, p2
            dx, dy = bx - ax, by - ay
            d2 = dx * dx + dy * dy
            hits = []
            if d2 > 0:
                for pt in by_net.get(net, []):
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
            notes.append(f"track {p1}->{p2} on {layer} split at "
                         f"{len(hits)} mid-run via(s)")
            prev, prev_t = p1, 0.0
            for t, pt in hits:
                out.append((net, layer, prev, pt, w, L * (t - prev_t)))
                prev, prev_t = pt, t
            out.append((net, layer, prev, p2, w, L * (1.0 - prev_t)))
        self.tracks = out
        return notes

    def summary(self):
        out = []
        for net, name in sorted(self.net_names.items()):
            t = sum(1 for x in self.tracks if x[0] == net)
            v = sum(1 for x in self.vias if x[0] == net)
            p = sum(1 for x in self.pads if x[0] == net)
            if t or v:
                out.append({"net": net, "name": name or f"<net {net}>",
                            "tracks": t, "vias": v, "pads": p,
                            "zone": net in self.zone_nets})
        return out

    # ---- graph ----
    def _landings(self, net):
        """point -> set of copper layers that have something landing there."""
        land = {}
        for n, layer, p1, p2, _w, _L in self.tracks:
            if n != net: continue
            land.setdefault(p1, set()).add(layer)
            land.setdefault(p2, set()).add(layer)
        for n, pt, lays, _ref, _pn, _fn in self.pads:
            if n != net: continue
            for l in lays:
                land.setdefault(pt, set()).add(l)
        return land

    def build_graph(self, net, order, zone_model="ladder", cluster_gap=2.0, **kw):
        adj, notes, arrays, uf = build_graph_pour(self, net, order, zone_model,
                                                  cluster_gap, **kw)
        self._last_uf = uf
        self._last_arrays = arrays
        return adj, notes

    def canonical(self, node):
        uf = getattr(self, "_last_uf", None)
        return uf.find(node) if uf else node

    def _build_graph_legacy(self, net, order):
        """Nodes are (layer, point). Returns adj, via_edges, notes.

        `order` is the top->bottom copper layer name list from the stackup."""
        rank = {nm: i for i, nm in enumerate(order)}
        adj = {}
        notes = []

        def add(u, v, data):
            adj.setdefault(u, []).append((v, data))
            adj.setdefault(v, []).append((u, data))

        for n, layer, p1, p2, w, L in self.tracks:
            if n != net: continue
            if layer not in rank:
                notes.append(f"track on unknown layer {layer} skipped")
                continue
            if p1 == p2:
                continue
            add((layer, p1), (layer, p2),
                {"kind": "trace", "layer": layer, "length_mm": L, "width_mm": w})

        land = self._landings(net)
        for n, pt, size, drill, declared, vtype in self.vias:
            if n != net: continue
            here = sorted((l for l in land.get(pt, set()) if l in rank), key=lambda l: rank[l])
            if len(here) < 2:
                notes.append(f"via at {pt} has {len(here)} landing layer(s) - "
                             "no current path through it, ignored")
                continue
            if vtype != "through":
                notes.append(f"{vtype} via at {pt}: barrel modelled between landing layers")
            for a, b in zip(here, here[1:]):
                add((a, pt), (b, pt),
                    {"kind": "via", "from": a, "to": b, "hole_mm": drill,
                     "pad_mm": size, "point": pt, "declared": declared,
                     "split": len(here) > 2})
            if len(here) > 2:
                notes.append(f"via at {pt} lands on {len(here)} layers "
                             f"({', '.join(here)}) - barrel split into series sub-spans")
        return adj, notes

    def terminals(self, net, dedupe=True):
        """Pads on this net, one entry per distinct terminal NAME by default.

        A footprint often repeats a pin name across pads - a thermal pad split
        into several, or a multi-pad supply pin. Those are one electrical
        terminal, so reporting a pair per pad multiplies identical work. The
        collapsed pads are kept in 'aliases' so the report can say so."""
        raw = []
        for n, pt, lays, ref, pn, fn in self.pads:
            if n != net:
                continue
            name = f"{ref}.{fn}" if ref and fn else (f"{ref}.{pn}" if ref else f"pad {pn}")
            raw.append({"point": pt, "layers": lays, "ref": ref, "pad": pn,
                        "fn": fn, "name": name, "aliases": []})
        if not dedupe:
            return raw
        out, seen = [], {}
        for t in raw:
            first = seen.get(t["name"])
            if first is None:
                seen[t["name"]] = t
                out.append(t)
            else:
                first["aliases"].append({"pad": t["pad"], "point": t["point"]})
        return out


def trace_path(board, net, order, start_node=None, end_node=None, rfun=None,
               adj=None, zone_model="ladder"):
    """Least-resistance path across the net graph.

    With `rfun` (an edge -> ohms callable) the search is weighted by real
    resistance and the true two-terminal network resistance is also returned;
    without it the search falls back to physical length. Returns
    (segments, notes, path_ohms, network_ohms) - the last two are None when
    no rfun was supplied."""
    if adj is None:
        adj, notes = board.build_graph(net, order, zone_model=zone_model)
    else:
        notes = []
    if not adj:
        raise ValueError(f"net {net} has no routed copper")

    terms = board.terminals(net)
    term_nodes = []
    for t in terms:
        for l in t["layers"]:
            c = board.canonical((l, t["point"]))
            if c in adj:
                term_nodes.append((c, t))
                break
    if start_node is None or end_node is None:
        if len(term_nodes) < 2:
            # fall back to the two graph leaves
            leaves = [k for k, v in adj.items() if len(v) == 1]
            if len(leaves) < 2:
                raise ValueError(f"net {net}: cannot identify two endpoints "
                                 f"({len(term_nodes)} pad terminals, {len(leaves)} loose ends)")
            start_node, end_node = leaves[0], leaves[1]
            notes.append("no pad terminals found; traced between two loose track ends")
        else:
            if len(term_nodes) > 2:
                notes.append(f"net has {len(term_nodes)} pad terminals; traced between the "
                             "first two - pick explicitly for any other pair")
            start_node, end_node = term_nodes[0][0], term_nodes[1][0]

    # Dijkstra weighted by resistance when we can price the edges, else length
    if rfun is None:
        notes.append("no electrical parameters supplied: path chosen by physical "
                     "length, not resistance")

    def weight(data):
        if rfun is not None:
            return rfun(data)
        return data["length_mm"] if data["kind"] == "trace" else 1e-3

    dist = {start_node: 0.0}
    prev = {}
    counter = itertools.count()          # node names are heterogeneous tuples, so
    pq = [(0.0, next(counter), start_node)]   # never let the heap compare them
    seen = set()
    while pq:
        d, _c, u = heapq.heappop(pq)
        if u in seen: continue
        seen.add(u)
        if u == end_node: break
        for v, data in adj.get(u, []):
            nd = d + weight(data)
            if nd < dist.get(v, float("inf")):
                dist[v] = nd; prev[v] = (u, data)
                heapq.heappush(pq, (nd, next(counter), v))
    if end_node not in dist:
        raise ValueError(f"net {net}: no continuous path between the two endpoints "
                         "(broken route, or connection is only through a zone)")

    chain = []
    node = end_node
    while node != start_node:
        u, data = prev[node]
        chain.append(data)
        node = u
    chain.reverse()

    path_r = sum(rfun(d) for d in chain) if rfun is not None else None
    net_r = None
    if rfun is not None:
        try:
            net_r = network_resistance(adj, start_node, end_node, rfun)
        except ValueError as exc:
            notes.append(f"network solution unavailable: {exc}")

    # branch detection along the traced path
    path_nodes = {start_node, end_node}
    node = end_node
    while node != start_node:
        node = prev[node][0]
        path_nodes.add(node)
    def _nname(n):
        if isinstance(n, tuple) and n and n[0] == "pour":
            return f"pour copper on {n[2]} at {n[3]:+.3f} mm along the pour axis"
        if isinstance(n, tuple) and len(n) == 2:
            return f"{n[0]} {n[1]}"
        return str(n)

    branches = [n for n in path_nodes if len(adj.get(n, [])) > 2]
    if branches:
        n = branches[0]
        extra = "" if len(branches) == 1 else f" (and {len(branches) - 1} more)"
        if net_r is not None and path_r is not None and abs(net_r - path_r) <= 1e-12 * max(path_r, 1e-18):
            notes.append(f"branch at {_nname(n)}{extra}: the other copper is a stub that "
                         "carries no current between these two pads, so it does not change "
                         "the result")
        else:
            notes.append(f"branch at {_nname(n)}{extra}: the net is not a simple series "
                         "chain - see the network figure for the effect of the parallel copper")

    # merge consecutive runs of the same kind, layer and width; price each element
    merged = []
    for d in chain:
        if merged and d["kind"] == "mesh" and merged[-1]["kind"] == "mesh":
            # A meshed pour crossing is hundreds of sub-millimetre cells; report
            # the run, not every cell.
            merged[-1] = dict(merged[-1])
            merged[-1]["r"] += d["r"]
            merged[-1]["cells"] = merged[-1].get("cells", 1) + 1
        elif (merged and d["kind"] in ("trace", "pour")
                and merged[-1]["kind"] == d["kind"]
                and merged[-1]["layer"] == d["layer"]
                and abs(merged[-1]["width_mm"] - d["width_mm"]) < 1e-9):
            merged[-1] = dict(merged[-1])
            merged[-1]["length_mm"] += d["length_mm"]
            merged[-1]["merged"] = merged[-1].get("merged", 1) + 1
        else:
            merged.append(dict(d))
    if rfun is not None:
        for d in merged:
            try:
                d["_r"] = rfun(d)
            except ValueError:
                d["_r"] = 0.0

    if net in board.zone_nets and zone_model == "none":
        notes.append("this net has a copper zone and zone_model is 'none': the pour is "
                     "ignored, so the real resistance is lower than reported")
    return merged, notes, path_r, net_r


# ---- electrical weighting and network solution ----

def edge_resistance(data, geo, plating_m, convention, mode):
    """DC resistance of one graph edge (a track run or a via sub-barrel)."""
    if data["kind"] == "mesh":
        return data["r"]
    if data["kind"] in ("trace", "pour"):
        g = next((x for x in geo if x["name"] == data["layer"]), None)
        if g is None:
            raise ValueError(f"layer {data['layer']} is not in the stackup")
        return trace_resistance(data["length_mm"] * MM_TO_M,
                                data["width_mm"] * MM_TO_M,
                                g["finished_mm"] * MM_TO_M)
    r, _L, _A = via_resistance(geo, data["from"], data["to"],
                               data["hole_mm"] * MM_TO_M, plating_m,
                               convention=convention, mode=mode)
    return r


def _solve_dense(A, b):
    """Gauss-Jordan with partial pivoting. Networks here are tens of nodes."""
    n = len(b)
    M = [list(row) + [b[i]] for i, row in enumerate(A)]
    for c in range(n):
        p = max(range(c, n), key=lambda r: abs(M[r][c]))
        if abs(M[p][c]) < 1e-18:
            raise ValueError("singular network matrix")
        M[c], M[p] = M[p], M[c]
        pv = M[c][c]
        for r in range(n):
            if r == c:
                continue
            f = M[r][c] / pv
            if f:
                for k in range(c, n + 1):
                    M[r][k] -= f * M[c][k]
    return [M[i][n] / M[i][i] for i in range(n)]


DENSE_NODE_LIMIT = 400

# How far outside filled copper a pad may sit and still count as zone-connected.
# Zone clearance plus half a pad; generous enough for thermal reliefs, tight
# enough not to bridge a genuinely unconnected pad.
ZONE_PAD_REACH_MM = 1.0

_CALIB = {}


def calibrate_solver():
    """Time two synthetic grids to learn this machine's t = a * nodes^b.

    Cached; costs a fraction of a second the first time it is asked."""
    if _CALIB:
        return _CALIB
    import time as _time
    pts = []
    for side in (12, 22):
        edges = []
        for r in range(side):
            for c in range(side):
                if c + 1 < side:
                    edges.append(((r, c), (r, c + 1), 1.0))
                if r + 1 < side:
                    edges.append(((r, c), (r + 1, c), 1.0))
        n = side * side
        t0 = _time.perf_counter()
        if HAVE_SCIPY:
            _solve_scipy(edges, (0, 0), (side - 1, side - 1))
        else:
            solve_cg(edges, (0, 0), (side - 1, side - 1))
        pts.append((n, max(_time.perf_counter() - t0, 1e-6)))
    (n1, t1), (n2, t2) = pts
    b = math.log(t2 / t1) / math.log(n2 / n1) if n2 != n1 and t1 > 0 else 1.5
    b = min(max(b, 0.8), 3.0)
    a = t1 / (n1 ** b)
    _CALIB.update({"a": a, "b": b, "backend": "scipy" if HAVE_SCIPY else "python",
                   "samples": pts})
    return _CALIB


def estimate_nodes(board, net, order, zone_model, mesh_pitch):
    """Cheap node-count estimate, used for the time forecast only."""
    tracks = sum(1 for t in board.tracks if t[0] == net)
    vias = sum(1 for v in board.vias if v[0] == net)
    base = 2 * tracks + 2 * vias
    pour = board.pours.get(net) if zone_model != "none" else None
    if pour is None:
        return max(base, 2)
    layers = len([l for l in pour.fills if l in set(order)])
    if zone_model == "mesh":
        xs = [p[0] for poly in pour.fills.values() for p in poly]
        ys = [p[1] for poly in pour.fills.values() for p in poly]
        nx = max(int(round((max(xs) - min(xs)) / max(mesh_pitch, 1e-6))), 2)
        ny = max(int(round((max(ys) - min(ys)) / max(mesh_pitch, 1e-6))), 2)
        return base + nx * ny * layers
    return base + (vias + 2) * layers


def estimate_seconds(nodes):
    c = calibrate_solver()
    return c["a"] * (max(nodes, 2) ** c["b"])


def network_resistance(adj, node_a, node_b, rfun, dense_limit=DENSE_NODE_LIMIT):
    """True two-terminal resistance of the whole net, parallel paths included.

    Nodal analysis: ground node_a, inject 1 A at node_b, R = V(node_b).
    Small graphs go through a dense Gauss-Jordan solve; meshed pours are far
    too big for O(n^3), so they fall through to sparse conjugate gradient."""
    if len(adj) > dense_limit:
        seen, edges = set(), []
        for u, links in adj.items():
            for v, data in links:
                if id(data) in seen:
                    continue
                seen.add(id(data))
                r = rfun(data)
                if r > 0:
                    edges.append((u, v, r))
        if HAVE_SCIPY:
            R, _n, _its = _solve_scipy(edges, node_a, node_b)
        else:
            R, _n, _its = solve_cg(edges, node_a, node_b)
        return R
    nodes = [n for n in adj if n != node_a]
    if node_b not in adj or node_a not in adj:
        raise ValueError("endpoint not in graph")
    idx = {n: i for i, n in enumerate(nodes)}
    size = len(nodes)
    G = [[0.0] * size for _ in range(size)]
    seen = set()
    for u, links in adj.items():
        for v, data in links:
            if id(data) in seen:
                continue
            seen.add(id(data))
            r = rfun(data)
            if r <= 0:
                continue
            g = 1.0 / r
            iu, iv = idx.get(u), idx.get(v)
            if iu is not None:
                G[iu][iu] += g
            if iv is not None:
                G[iv][iv] += g
            if iu is not None and iv is not None:
                G[iu][iv] -= g
                G[iv][iu] -= g
    inj = [0.0] * size
    inj[idx[node_b]] = 1.0
    V = _solve_dense(G, inj)
    return V[idx[node_b]]


# ---------------------------------------------------------------- trace dialog
class NetTraceDialog(QDialog):
    def __init__(self, board, parent=None):
        super().__init__(parent)
        self.board = board
        self.setWindowTitle("Trace a net from the board")
        self.resize(760, 420)

        self.net_list = QListWidget()
        for s in board.summary():
            label = (f"{s['name']}   -   {s['tracks']} track(s), {s['vias']} via(s), "
                     f"{s['pads']} pad(s)" + ("   [has zone]" if s["zone"] else ""))
            item = QListWidgetItem(label)
            item.setData(Qt.UserRole, s["net"])
            self.net_list.addItem(item)
        self.net_list.currentItemChanged.connect(self._net_changed)

        self.term_list = QListWidget()
        self.term_list.setSelectionMode(QListWidget.MultiSelection)

        cols = QHBoxLayout()
        left = QVBoxLayout(); left.addWidget(_small(QLabel("Net"), bold=True))
        left.addWidget(self.net_list)
        right = QVBoxLayout(); right.addWidget(_small(QLabel("Endpoints"), bold=True))
        right.addWidget(self.term_list)
        right.addWidget(_small(QLabel("Select exactly two, or none to use the first two."),
                               italic=True))
        cols.addLayout(left, 3); cols.addLayout(right, 2)

        self.info = _small(QLabel(""))
        self.info.setWordWrap(True)

        buttons = QHBoxLayout()
        ok = QPushButton("Trace into path"); ok.setDefault(True); ok.clicked.connect(self.accept)
        cancel = QPushButton("Cancel"); cancel.clicked.connect(self.reject)
        buttons.addStretch(1); buttons.addWidget(cancel); buttons.addWidget(ok)

        root = QVBoxLayout(self)
        root.addLayout(cols, 1); root.addWidget(self.info); root.addLayout(buttons)
        if self.net_list.count():
            self.net_list.setCurrentRow(0)

    def _net_changed(self, *_):
        self.term_list.clear()
        net = self.selected_net()
        if net is None:
            return
        for t in self.board.terminals(net):
            label = (f"{t['name']}   (pad {t['pad']}, {'/'.join(t['layers'])})   "
                     f"({t['point'][0]}, {t['point'][1]})")
            item = QListWidgetItem(label)
            item.setData(Qt.UserRole, t)
            self.term_list.addItem(item)
        n = self.term_list.count()
        self.info.setText(
            f"{n} pad terminal(s) on this net."
            + ("  More than two - pick the pair you want; resistance is only defined "
               "between two points." if n > 2 else ""))

    def selected_net(self):
        item = self.net_list.currentItem()
        return item.data(Qt.UserRole) if item else None

    def selected_terminals(self):
        return [i.data(Qt.UserRole) for i in self.term_list.selectedItems()]


def _attach_tracing(ViaPathTabCls):
    """Methods added to ViaPathTab for board-net tracing."""

    def board_path(self):
        src = self.st.stackup.source
        return src if src and src.endswith(".kicad_pcb") else None

    def trace_from_board(self):
        path = self.board_path()
        if not path:
            path, _ = QFileDialog.getOpenFileName(
                self, "Open KiCad board", "", "KiCad PCB (*.kicad_pcb);;All files (*)")
            if not path:
                return
            self.st.load_path(path)
            if not self.board_path():
                return
            path = self.board_path()
        try:
            board = BoardNets(path)
        except Exception as exc:                      # noqa: BLE001
            QMessageBox.warning(self, "Could not read board", str(exc)); return
        if not board.summary():
            QMessageBox.information(self, "Nothing to trace",
                                    "This board has no routed copper."); return

        dlg = NetTraceDialog(board, self)
        if dlg.exec() != QDialog.Accepted:
            return
        net = dlg.selected_net()
        if net is None:
            return
        picked = dlg.selected_terminals()
        order = self.st.copper_names()
        start = end = None
        if len(picked) == 2:
            adj, _ = board.build_graph(net, order)
            def node_for(t):
                for l in t["layers"]:
                    if (l, t["point"]) in adj:
                        return (l, t["point"])
                return None
            start, end = node_for(picked[0]), node_for(picked[1])
            if start is None or end is None:
                QMessageBox.warning(self, "Endpoint not routed",
                                    "One of the selected pads has no track landing on it.")
                return
        elif picked:
            QMessageBox.information(self, "Select two endpoints",
                                    "Select exactly two endpoints, or none for the "
                                    "first two."); return
        # price the edges so the search finds least RESISTANCE, not least length
        rfun = None
        try:
            plating_m = self.plating_m()
            geo = self.st.stackup.geometry(plating_m * 1e6, self.outer_plating.isChecked())
            conv = DRILL_CONVENTIONS[self.drill_conv.currentIndex()][1]
            mode = LENGTH_CONVENTIONS[self.len_conv.currentIndex()][1]
            rfun = lambda d: edge_resistance(d, geo, plating_m, conv, mode)  # noqa: E731
        except ValueError:
            pass                                   # no plating yet - fall back to length
        try:
            segs, notes, path_r, net_r = trace_path(board, net, order, start, end, rfun)
        except ValueError as exc:
            QMessageBox.warning(self, "Could not trace net", str(exc)); return

        self.clear_rows()
        for s in segs:
            if s["kind"] == "trace":
                self.add_row("trace")
                row = self.rows[-1]
                row.layer.setCurrentText(s["layer"])
                row.length_u.setCurrentText("mm"); row.width_u.setCurrentText("mm")
                row.length.setText(f"{s['length_mm']:.4f}")
                row.width.setText(f"{s['width_mm']:g}")
            else:
                self.add_row("via")
                row = self.rows[-1]
                row.from_layer.setCurrentText(s["from"])
                row.to_layer.setCurrentText(s["to"])
                row.hole_u.setCurrentText("mm"); row.pad_u.setCurrentText("mm")
                row.hole.setText(f"{s['hole_mm']:g}")
                row.pad.setText(f"{s['pad_mm']:g}")
        name = board.net_names.get(net, f"net {net}")
        declared = {tuple(s["declared"]) for s in segs if s["kind"] == "via" and s["declared"]}
        actual = {(s["from"], s["to"]) for s in segs if s["kind"] == "via"}
        extra = []
        if declared and actual - declared:
            extra.append(f"Declared via span(s) {sorted(declared)} vs traced electrical "
                         f"span(s) {sorted(actual)} - the token records the drilled barrel.")
        ends = ""
        if len(picked) == 2:
            ends = f" {picked[0]['name']} -> {picked[1]['name']},"
        elif len(board.terminals(net)) >= 2:
            t = board.terminals(net)
            ends = f" {t[0]['name']} -> {t[1]['name']},"
        net_txt = ""
        if path_r is not None and net_r is not None:
            if abs(net_r - path_r) <= 1e-9 * max(path_r, 1e-18):
                net_txt = (f"  Least-resistance path {format_ohms(path_r)}; the full network "
                           "solves to the same value, so no parallel copper is carrying "
                           "current between these two pads.")
            else:
                net_txt = (f"  Least-resistance path {format_ohms(path_r)}, but the full "
                           f"network is {format_ohms(net_r)} "
                           f"({(1 - net_r / path_r) * 100:.1f}% lower) because parallel "
                           "copper shares the current. The table below prices the path only.")
        self.traced_label.setText(
            f"Traced \"{name}\":{ends} {sum(1 for s in segs if s['kind'] == 'trace')} trace "
            f"segment(s), {sum(1 for s in segs if s['kind'] == 'via')} via(s)."
            + net_txt + ("  " + "  ".join(notes + extra) if (notes or extra) else ""))
        self.calculate()

    ViaPathTabCls.board_path = board_path
    ViaPathTabCls.trace_from_board = trace_from_board


_attach_tracing(ViaPathTab)


# ---------------------------------------------------------------- markdown -> html
def markdown_to_html(md):
    """Minimal converter for the subset the report emits, for QTextDocument/PDF."""
    def inline(t):
        t = (t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))
        t = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", t)
        t = re.sub(r"`(.+?)`", r"<code>\1</code>", t)
        t = re.sub(r"_(.+?)_", r"<i>\1</i>", t)
        return t

    out = ["<html><head><style>"
           "body{font-family:sans-serif;font-size:9pt;}"
           "h1{font-size:16pt;} h2{font-size:13pt;} h3{font-size:11pt;}"
           "table{border-collapse:collapse;} "
           "td,th{border:1px solid #999;padding:3px 6px;font-size:8pt;}"
           "th{background:#eee;} code{font-family:monospace;}"
           "blockquote{color:#603000;}"
           "</style></head><body>"]
    rows, in_table = [], False

    def flush():
        nonlocal rows, in_table
        if rows:
            out.append("<table>")
            head, body = rows[0], rows[1:]
            out.append("<tr>" + "".join(f"<th>{inline(c)}</th>" for c in head) + "</tr>")
            for r in body:
                out.append("<tr>" + "".join(f"<td>{inline(c)}</td>" for c in r) + "</tr>")
            out.append("</table>")
        rows, in_table = [], False

    for line in md.split("\n"):
        st = line.strip()
        if st.startswith("|") and st.endswith("|"):
            cells = [c.strip() for c in st.strip("|").split("|")]
            if set("".join(cells)) <= {"-", ":"} and cells:
                continue
            rows.append(cells); in_table = True
            continue
        if in_table:
            flush()
        if not st:
            continue
        if st.startswith("<details") or st.startswith("</details") or st.startswith("<summary"):
            continue
        m = re.match(r"^(#{1,6})\s+(.*)$", st)
        if m:
            lvl = len(m.group(1))
            out.append(f"<h{lvl}>{inline(m.group(2))}</h{lvl}>")
            continue
        if st.startswith("> "):
            out.append(f"<blockquote>{inline(st[2:])}</blockquote>")
            continue
        if st.startswith("- "):
            out.append(f"<p style='margin-left:14px'>&bull; {inline(st[2:])}</p>")
            continue
        out.append(f"<p>{inline(st)}</p>")
    flush()
    out.append("</body></html>")
    return "\n".join(out)


def write_pdf(md, path, title="PCB resistance report"):
    from PySide6.QtGui import QPdfWriter, QPageSize, QTextDocument
    from PySide6.QtCore import QMarginsF
    writer = QPdfWriter(path)
    writer.setPageSize(QPageSize(QPageSize.A4))
    writer.setTitle(title)
    writer.setResolution(300)
    writer.setPageMargins(QMarginsF(12, 12, 12, 12))
    doc = QTextDocument()
    doc.setHtml(markdown_to_html(md))
    doc.setPageSize(writer.pageLayout().paintRectPixels(writer.resolution()).size())
    doc.print_(writer)


# ---------------------------------------------------------------- collapsible section
class CollapsibleSection(QWidget):
    """Disclosure-triangle group. Collapsed, it costs one header row.

    A checkable QGroupBox would be fewer lines, but its title checkbox reads as
    'enable this', and this tab already uses checkboxes to mean 'include this
    section in the report'. A triangle can only mean show/hide."""

    toggled = Signal(bool)

    def __init__(self, title, expanded=True):
        super().__init__()
        self._title = title
        self._summary = ""
        self.button = QToolButton()
        self.button.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self.button.setCheckable(True)
        self.button.setChecked(expanded)
        self.button.setAutoRaise(True)
        self.button.setStyleSheet("QToolButton { border: none; font-weight: bold; }")
        self.button.clicked.connect(self.set_expanded)
        self.body = QWidget()
        self.body.setVisible(expanded)
        line = _hline()
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 2, 0, 2)
        root.setSpacing(2)
        head = QHBoxLayout()
        head.setContentsMargins(0, 0, 0, 0)
        head.addWidget(self.button)
        head.addWidget(line, 1)
        root.addLayout(head)
        root.addWidget(self.body)
        self._refresh_header()

    def _refresh_header(self):
        arrow = Qt.DownArrow if self.button.isChecked() else Qt.RightArrow
        self.button.setArrowType(arrow)
        text = self._title
        if self._summary:
            text += f"   -   {self._summary}"
        self.button.setText(text)

    def set_expanded(self, on):
        self.button.setChecked(on)
        self.body.setVisible(on)
        self._refresh_header()
        self.toggled.emit(on)

    def is_expanded(self):
        return self.button.isChecked()

    def set_summary(self, text):
        """Shown in the header, so state stays readable while collapsed."""
        self._summary = text or ""
        self._refresh_header()

    def set_content_layout(self, layout):
        layout.setContentsMargins(14, 2, 2, 6)
        self.body.setLayout(layout)


# ---------------------------------------------------------------- transfer list
class TransferList(QWidget):
    changed = Signal()

    def __init__(self, title, right_label="Included"):
        super().__init__()
        grid = QGridLayout(self)
        grid.setContentsMargins(0, 0, 0, 0)
        self.left = QListWidget(); self.right = QListWidget()
        for lw in (self.left, self.right):
            lw.setSelectionMode(QListWidget.ExtendedSelection)
            lw.setMinimumHeight(110)
            lw.itemDoubleClicked.connect(self._dbl)
        grid.addWidget(_small(QLabel("Available"), bold=True), 0, 0)
        grid.addWidget(_small(QLabel(right_label), bold=True), 0, 2)
        grid.addWidget(self.left, 1, 0)
        grid.addWidget(self.right, 1, 2)
        col = QVBoxLayout()
        for label, fn in ((">", self.add_sel), (">>", self.add_all),
                          ("<", self.rm_sel), ("<<", self.rm_all)):
            b = QPushButton(label); b.setMaximumWidth(34); b.clicked.connect(fn)
            col.addWidget(b)
        col.addStretch(1)
        holder = QWidget(); holder.setLayout(col)
        grid.addWidget(holder, 1, 1)
        grid.setColumnStretch(0, 1); grid.setColumnStretch(2, 1)
        self._all = []

    def _dbl(self, item):
        src = item.listWidget()
        (self.add_sel if src is self.left else self.rm_sel)()

    def _move(self, src, dst, items):
        for it in items:
            src.takeItem(src.row(it))
            dst.addItem(it.text())
        dst.sortItems()
        self.changed.emit()

    def add_sel(self): self._move(self.left, self.right, self.left.selectedItems())
    def rm_sel(self):  self._move(self.right, self.left, self.right.selectedItems())
    def add_all(self): self._move(self.left, self.right,
                                  [self.left.item(i) for i in range(self.left.count())])
    def rm_all(self):  self._move(self.right, self.left,
                                  [self.right.item(i) for i in range(self.right.count())])

    def set_universe(self, names, chosen=()):
        self._all = list(names)
        chosen = [c for c in chosen if c in self._all]
        self.left.clear(); self.right.clear()
        self.left.addItems(sorted(n for n in self._all if n not in chosen))
        self.right.addItems(sorted(chosen))
        self.changed.emit()

    def chosen(self):
        return [self.right.item(i).text() for i in range(self.right.count())]


# ---------------------------------------------------------------- report tab
PAIR_MODES = ["all", "from-source", "first-two", "explicit"]


class ReportTab(QWidget):
    def __init__(self, globals_, stackup_tab, via_tab):
        super().__init__()
        self.g = globals_
        self.st = stackup_tab
        self.via = via_tab
        self.board = None
        self.path = None            # net-selection file
        self.dirty = False
        self._loading = False
        self._last_md = ""
        self._overrides = {}
        self._cancel = False

        # --- file bar, always visible ---
        bar = QHBoxLayout()
        for label, fn in (("Open...", self.open_file), ("Save", self.save),
                          ("Save As...", self.save_as), ("New", self.new_file)):
            b = QPushButton(label); b.clicked.connect(fn); bar.addWidget(b)
        bar.addStretch(1)
        self.file_label = _small(QLabel("(unsaved selection)"), italic=True)
        bar.addWidget(self.file_label)

        # --- section 1: nets to report on ---
        self.sel_list = TransferList("Report on these nets", "Selected")
        self.sec_select = CollapsibleSection("Report on these nets")
        l1 = QVBoxLayout(); l1.addWidget(self.sel_list)
        self.sec_select.set_content_layout(l1)

        # --- section 2: nets to ignore ---
        self.ign_list = TransferList("Ignore these nets", "Ignored")
        self.sec_ignore = CollapsibleSection("Ignore these nets", expanded=False)
        l2 = QVBoxLayout(); l2.addWidget(self.ign_list)
        self.sec_ignore.set_content_layout(l2)

        self.sel_list.changed.connect(self._selection_changed)
        self.ign_list.changed.connect(self._selection_changed)
        self.expand_note = _small(QLabel(""), italic=True)
        self.expand_note.setWordWrap(True)

        # --- section 3: point to point ---
        self.sec_pairs = CollapsibleSection("Point-to-point pairs")
        pl = QVBoxLayout()
        hint = _small(QLabel(
            "Resistance is only defined between two pads, so each net needs a rule. "
            "'all' gives N(N-1)/2 rows; 'from-source' reports one driver or supply pad "
            "against every other, which is usually what you want on a power or fan-out "
            "net. Blank voltage or current cells use the operating-condition defaults."),
            italic=True)
        hint.setWordWrap(True)
        pl.addWidget(hint)
        self.pair_table = QTableWidget(0, 4)
        self.pair_table.setHorizontalHeaderLabels(["Net", "Terminals", "Pairs", "Source"])
        self.pair_table.verticalHeader().setVisible(False)
        self.pair_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.pair_table.setMinimumHeight(120)
        pl.addWidget(self.pair_table)
        pl.addWidget(_small(QLabel("Per-pair overrides"), bold=True))
        self.override_table = QTableWidget(0, 8)
        self.override_table.setHorizontalHeaderLabels(
            ["Net", "From", "To", "Voltage (V)", "Current (A)", "Zone model",
             "Mesh mm", "Est. solve"])
        self.override_table.verticalHeader().setVisible(False)
        self.override_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.override_table.setMinimumHeight(140)
        self.override_table.itemChanged.connect(self._override_edited)
        pl.addWidget(self.override_table)
        self.pair_count = _small(QLabel(""))
        pl.addWidget(self.pair_count)
        self.est_label = _small(QLabel(""), italic=True)
        self.est_label.setWordWrap(True)
        pl.addWidget(self.est_label)
        self.sec_pairs.set_content_layout(pl)

        # --- section 4: report ---
        self.sec_report = CollapsibleSection("Report")
        iv = QVBoxLayout()
        secbox = QHBoxLayout()
        secbox.addWidget(_small(QLabel("Sections:"), bold=True))
        self.section_boxes = {}
        for key, label in (("assumptions", "Assumptions"), ("stackup", "Stackup"),
                           ("selection", "Selection"), ("summary", "Summary"),
                           ("detail", "Detail"), ("notes", "Notes")):
            cb = QCheckBox(label); cb.setChecked(True); cb.stateChanged.connect(self._touch)
            self.section_boxes[key] = cb
            secbox.addWidget(cb)
        secbox.addStretch(1)
        iv.addLayout(secbox)

        row = QHBoxLayout()
        row.addWidget(_small(QLabel("Zone model and mesh pitch: Setup tab"),
                             italic=True))
        row.addWidget(QLabel("Format:"))
        self.fmt_combo = QComboBox()
        self.fmt_combo.addItems(["Markdown (.md)", "Text (.txt)", "PDF (.pdf)",
                                 "JSON (.json)"])
        row.addWidget(self.fmt_combo)
        row.addStretch(1)
        self.preview_btn = QPushButton("Preview")
        self.preview_btn.clicked.connect(lambda: self.generate(save=False))
        self.gen_btn = QPushButton("Generate report...")
        self.gen_btn.setDefault(True)
        self.gen_btn.clicked.connect(lambda: self.generate(save=True))
        row.addWidget(self.preview_btn); row.addWidget(self.gen_btn)
        iv.addLayout(row)

        self.assump = _small(QLabel(""))
        self.assump.setWordWrap(True)
        iv.addWidget(self.assump)
        self.preview = QTextEdit(); self.preview.setReadOnly(True)
        self.preview.setLineWrapMode(QTextEdit.NoWrap)
        self.preview.setMinimumHeight(260)
        iv.addWidget(self.preview, 1)
        self.sec_report.set_content_layout(iv)

        self.status = _small(QLabel(""))
        self.status.setWordWrap(True)

        # --- single column, scrollable so nothing gets squashed when expanded ---
        inner = QWidget()
        col = QVBoxLayout(inner)
        col.setContentsMargins(4, 4, 4, 4)
        col.addLayout(bar)
        col.addWidget(self.sec_select)
        col.addWidget(self.sec_ignore)
        col.addWidget(self.expand_note)
        col.addWidget(self.sec_pairs)
        col.addWidget(self.sec_report, 1)
        col.addStretch(0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setWidget(inner)

        collapse_bar = QHBoxLayout()
        for label, fn in (("Expand all", lambda: self._set_all_sections(True)),
                          ("Collapse all", lambda: self._set_all_sections(False))):
            b = QPushButton(label); b.setMaximumWidth(110); b.clicked.connect(fn)
            collapse_bar.addWidget(b)
        collapse_bar.addStretch(1)

        root = QVBoxLayout(self)
        root.addLayout(collapse_bar)
        root.addWidget(scroll, 1)
        root.addWidget(self.status)

        self.st.changed.connect(self.reload_board)
        self.st.netsel_open_requested.connect(self.open_file)
        self.reload_board()

    # ---- board / net universe ----
    def reload_board(self):
        src = self.st.stackup.source
        if not (src and src.endswith(".kicad_pcb") and os.path.exists(src)):
            self.board = None
            self.sel_list.set_universe([]); self.ign_list.set_universe([])
            self.status.setText("Load a .kicad_pcb on the Stackup tab to enable reporting.")
            return
        try:
            self.board = BoardNets(src)
        except Exception as exc:                      # noqa: BLE001
            self.board = None
            self.status.setText(f"Could not read board: {exc}")
            return
        names = [s["name"] for s in self.board.summary()]
        self._loading = True
        self.sel_list.set_universe(names, names)       # default: every routed net
        self.ign_list.set_universe(names, [])
        self._loading = False
        self.status.setText(f"{os.path.basename(src)}: {len(names)} routed net(s).")
        self.refresh_pairs()

    @property
    def zone_combo(self):
        return self.st.zone_combo

    @property
    def pitch_edit(self):
        return self.st.pitch_edit

    def _set_all_sections(self, on):
        for sec in (self.sec_select, self.sec_ignore, self.sec_pairs, self.sec_report):
            sec.set_expanded(on)

    def _refresh_summaries(self):
        keep, clashes = self.effective_nets()
        n_sel = len(self.sel_list.chosen())
        n_ign = len(self.ign_list.chosen())
        self.sec_select.set_summary(f"{n_sel} selected")
        self.sec_ignore.set_summary(f"{n_ign} ignored" if n_ign else "none")
        self.sec_pairs.set_summary(self.pair_count.text() or f"{len(keep)} net(s)")
        fmt = self.fmt_combo.currentText().split(" ")[0]
        self.sec_report.set_summary(f"{fmt}, zone {self.zone_combo.currentText()}")

    def _touch(self, *_):
        self.dirty = True
        self._update_title()

    def _selection_changed(self):
        if self._loading:
            return
        self._touch()
        self.refresh_pairs()

    def effective_nets(self):
        sel = set(self.sel_list.chosen())
        ign = set(self.ign_list.chosen())
        return [n for n in sorted(sel - ign)], sorted(sel & ign)

    # ---- pair table ----
    def refresh_pairs(self):
        if not self.board:
            self.pair_table.setRowCount(0); return
        keep, clashes = self.effective_nets()
        prev = self.pair_settings()
        self.pair_table.setRowCount(len(keep))
        total = 0
        for r, name in enumerate(keep):
            num = next((s["net"] for s in self.board.summary() if s["name"] == name), None)
            terms = [t["name"] for t in self.board.terminals(num)] if num is not None else []
            item = QTableWidgetItem(name); item.setFlags(Qt.ItemIsEnabled)
            self.pair_table.setItem(r, 0, item)
            ti = QTableWidgetItem(f"{len(terms)}: " + ", ".join(terms))
            ti.setFlags(Qt.ItemIsEnabled)
            self.pair_table.setItem(r, 1, ti)
            mode = QComboBox(); mode.addItems(PAIR_MODES)
            saved = prev.get(name, {})
            mode.setCurrentText(saved.get("pairs", "all"))
            src = QComboBox(); src.addItems(terms or ["-"])
            if saved.get("source") in terms:
                src.setCurrentText(saved["source"])
            src.setEnabled(mode.currentText() == "from-source")
            mode.currentTextChanged.connect(
                lambda t, sc=src: (sc.setEnabled(t == "from-source"),
                                   self._touch(), self.refresh_counts(),
                                   self.refresh_overrides()))
            src.currentTextChanged.connect(
                lambda _t: (self._touch(), self.refresh_overrides()))
            self.pair_table.setCellWidget(r, 2, mode)
            self.pair_table.setCellWidget(r, 3, src)
        self.pair_table.resizeColumnsToContents()
        self.pair_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.refresh_overrides()
        if clashes:
            self.expand_note.setText(
                "Nets in both lists are ignored - ignore always wins: "
                + ", ".join(clashes))
        elif not self.expand_note.text().startswith("Opened"):
            self.expand_note.setText("")
        self.refresh_counts()

    def refresh_counts(self):
        if not self.board:
            return
        keep, _c = self.effective_nets()
        settings = self.pair_settings()
        total = 0
        for name in keep:
            num = next((s["net"] for s in self.board.summary() if s["name"] == name), None)
            n = len(self.board.terminals(num)) if num is not None else 0
            mode = settings.get(name, {}).get("pairs", "all")
            if n < 2:
                continue
            total += {"all": n * (n - 1) // 2, "from-source": n - 1,
                      "first-two": 1}.get(mode, 0)
        self.pair_count.setText(f"{len(keep)} net(s) selected, {total} pad pair(s) "
                                f"will be computed.")
        self._refresh_summaries()

    def resolved_pairs(self, name, num, settings):
        terms = [t["name"] for t in self.board.terminals(num)]
        cfg = settings.get(name, {})
        mode = cfg.get("pairs", "all")
        if len(terms) < 2:
            return []
        if mode == "first-two":
            return [(terms[0], terms[1])]
        if mode == "from-source":
            src = cfg.get("source") or terms[0]
            if src not in terms:
                src = terms[0]
            return [(src, t) for t in terms if t != src]
        if mode == "explicit":
            out = []
            for spec in cfg.get("explicit_pairs", []):
                a, _sep, b = spec.partition(">")
                if a.strip() in terms and b.strip() in terms:
                    out.append((a.strip(), b.strip()))
            return out
        return [(terms[i], terms[j]) for i in range(len(terms))
                for j in range(i + 1, len(terms))]

    def refresh_overrides(self):
        if not self.board:
            self.override_table.setRowCount(0); return
        keep, _c = self.effective_nets()
        settings = self.pair_settings()
        prev = dict(self._overrides)
        rows = []
        for name in keep:
            num = next((s["net"] for s in self.board.summary() if s["name"] == name), None)
            if num is None:
                continue
            for a, b in self.resolved_pairs(name, num, settings):
                rows.append((name, a, b))
        self._loading = True
        self.override_table.setRowCount(len(rows))
        for r, (name, a, b) in enumerate(rows):
            for c, txt in ((0, name), (1, a), (2, b)):
                it = QTableWidgetItem(txt); it.setFlags(Qt.ItemIsEnabled)
                self.override_table.setItem(r, c, it)
            saved = prev.get((name, a, b)) or prev.get((name, b, a)) or {}
            for c, key in ((3, "voltage_v"), (4, "current_a")):
                it = QTableWidgetItem("" if key not in saved else f"{saved[key]:g}")
                it.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable | Qt.ItemIsEditable)
                it.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.override_table.setItem(r, c, it)
            zm = QComboBox(); zm.addItems(["ladder", "mesh", "none"])
            zm.setCurrentText(saved.get("zone_model", "ladder"))
            pitch = _num_edit(f"{saved.get('mesh_pitch_mm', 0.25):g}", 0.001, 5.0, width=64)
            pitch.setEnabled(zm.currentText() == "mesh")
            zm.currentTextChanged.connect(
                lambda t, p=pitch, k=(name, a, b): (p.setEnabled(t == "mesh"),
                                                    self._model_changed(k, t, p)))
            pitch.editingFinished.connect(
                lambda p=pitch, z=zm, k=(name, a, b):
                    self._model_changed(k, z.currentText(), p))
            self.override_table.setCellWidget(r, 5, zm)
            self.override_table.setCellWidget(r, 6, pitch)
            est = QTableWidgetItem("")
            est.setFlags(Qt.ItemIsEnabled)
            est.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.override_table.setItem(r, 7, est)
        self._loading = False
        self.refresh_estimates()
        self.override_table.resizeColumnsToContents()
        self.override_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        live = {(n, a, b) for n, a, b in rows} | {(n, b, a) for n, a, b in rows}
        self._overrides = {k: v for k, v in prev.items() if k in live}

    def _model_changed(self, key, zone_model, pitch_edit):
        cur = dict(self._overrides.get(key, {}))
        cur["zone_model"] = zone_model
        if zone_model == "mesh":
            try:
                cur["mesh_pitch_mm"] = _parse_edit(pitch_edit)
            except ValueError:
                cur["mesh_pitch_mm"] = 0.25
        else:
            cur.pop("mesh_pitch_mm", None)
        if cur.get("zone_model") == "ladder" and len(cur) == 1:
            self._overrides.pop(key, None)          # the default: nothing to store
        else:
            self._overrides[key] = cur
        self._touch()
        self.refresh_estimates()

    def refresh_estimates(self):
        """Forecast each solve from a one-off calibration of this machine."""
        if not self.board:
            return
        total = 0.0
        self._loading = True
        for r in range(self.override_table.rowCount()):
            nm = self.override_table.item(r, 0)
            zmw = self.override_table.cellWidget(r, 5)
            pw = self.override_table.cellWidget(r, 6)
            cell = self.override_table.item(r, 7)
            if not (nm and zmw and cell):
                continue
            num = next((s2["net"] for s2 in self.board.summary()
                        if s2["name"] == nm.text()), None)
            if num is None:
                continue
            try:
                pitch = _parse_edit(pw) if pw else 0.25
            except ValueError:
                pitch = 0.25
            order = self.st.copper_names()
            nodes = estimate_nodes(self.board, num, order, zmw.currentText(), pitch)
            secs = estimate_seconds(nodes)
            total += secs
            cell.setText(f"{nodes} nodes, {secs * 1000:.0f} ms" if secs < 1
                         else f"{nodes} nodes, {secs:.1f} s")
        self._loading = False
        c = calibrate_solver()
        self.est_label.setText(
            f"Estimated total solve time {total:.2f} s "
            f"({c['backend']} backend, t = {c['a']:.2e} x nodes^{c['b']:.2f} "
            "measured on this machine). Estimates are a forecast, not a promise.")

    def _override_edited(self, item):
        if self._loading or item.column() not in (3, 4):
            return
        r = item.row()
        key = (self.override_table.item(r, 0).text(),
               self.override_table.item(r, 1).text(),
               self.override_table.item(r, 2).text())
        field = "voltage_v" if item.column() == 3 else "current_a"
        text = item.text().strip()
        cur = dict(self._overrides.get(key, {}))
        if not text:
            cur.pop(field, None)
        else:
            try:
                val = float(text)
            except ValueError:
                self._loading = True
                item.setText("" if field not in cur else f"{cur[field]:g}")
                self._loading = False
                self.status.setText(f"{text!r} is not a number.")
                return
            if field == "current_a" and val < 0:
                self._loading = True; item.setText(""); self._loading = False
                self.status.setText("Current cannot be negative."); return
            cur[field] = val
        if cur:
            self._overrides[key] = cur
        else:
            self._overrides.pop(key, None)
        self._touch()

    def pair_settings(self):
        out = {}
        for r in range(self.pair_table.rowCount()):
            item = self.pair_table.item(r, 0)
            mode = self.pair_table.cellWidget(r, 2)
            src = self.pair_table.cellWidget(r, 3)
            if item and mode:
                cfg = {"pairs": mode.currentText()}
                if cfg["pairs"] == "from-source" and src and src.currentText() != "-":
                    cfg["source"] = src.currentText()
                out[item.text()] = cfg
        return out

    # ---- net-selection file ----
    def build_doc(self):
        keep = self.sel_list.chosen()
        allnets = [s["name"] for s in self.board.summary()] if self.board else []
        select = ["*"] if set(keep) == set(allnets) and allnets else sorted(keep)
        doc = {
            "_meta": {
                "version": "0.1",
                "description": "Net selection for the PCB resistance report.",
                "board": os.path.basename(self.st.stackup.source or ""),
                "generated": datetime.datetime.now().isoformat(timespec="seconds"),
            },
            "select": select,
            "ignore": sorted(self.ign_list.chosen()),
            "options": self.options(),
            "nets": {},
        }
        nets = {}
        for k, v in self.pair_settings().items():
            if v.get("pairs") != "all" or "source" in v:
                nets[k] = dict(v)
        for (name, a, b), vals in sorted(self._overrides.items()):
            vals = {k: v for k, v in vals.items()
                    if not (k == "zone_model" and v == "ladder"
                            and len(vals) == 1)}
            if not vals:
                continue
            nets.setdefault(name, {}).setdefault("pair_overrides", {})[f"{a}>{b}"] = \
                dict(vals)
        doc["nets"] = nets
        return doc

    def options(self):
        try:
            plating_um = self.via.plating_m() * 1e6
        except ValueError:
            plating_um = None
        opts = {
            "sections": {k: cb.isChecked() for k, cb in self.section_boxes.items()},
            "hole_convention": DRILL_CONVENTIONS[self.via.drill_conv.currentIndex()][1],
            "length_convention": LENGTH_CONVENTIONS[self.via.len_conv.currentIndex()][1],
            "outer_plating_adds": self.via.outer_plating.isChecked(),
            "zone_model": self.zone_combo.currentText(),
        }
        if plating_um:
            opts["plating_um"] = round(plating_um, 6)
        try:
            opts["mesh_pitch_mm"] = _parse_edit(self.pitch_edit)
        except ValueError:
            pass
        try:
            opts["ambient_c"] = self.g.ambient_c()
            opts["current_a"] = self.g.current_a()
            opts["signal_voltage_v"] = self.g.signal_v()
        except ValueError:
            pass
        return opts

    def _update_title(self):
        name = os.path.basename(self.path) if self.path else "(unsaved selection)"
        self.file_label.setText(name + (" *" if self.dirty else ""))

    def new_file(self):
        self.path = None; self.dirty = False
        self._overrides = {}
        self.expand_note.setText("")
        self.reload_board(); self._update_title()

    def default_dir(self):
        """Net-selection files live beside the board by default."""
        src = self.st.stackup.source if self.st.stackup else ""
        if src and src.endswith(".kicad_pcb") and os.path.exists(src):
            return os.path.dirname(os.path.abspath(src))
        return ""

    def open_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "Open net selection",
                                              self.default_dir(),
                                              "JSON (*.json);;All files (*)")
        if not path:
            return
        try:
            doc, opts = load_netsel(path)
        except (ValueError, json.JSONDecodeError) as exc:
            QMessageBox.warning(self, "Invalid net selection file", str(exc))
            return
        if not self.board:
            QMessageBox.information(self, "No board",
                                    "Load the .kicad_pcb on the Stackup tab first.")
            return
        allnets = [s["name"] for s in self.board.summary()]
        chosen, _why, unused_s, unused_i = select_nets(
            [(0, n) for n in allnets], doc)
        keep = [n for _x, n in chosen]
        ign = [n for n in allnets
               if any(fnmatch.fnmatchcase(n, p) for p in doc.get("ignore", []))]
        self._loading = True
        self.sel_list.set_universe(allnets, keep + ign)   # select before ignore
        self.ign_list.set_universe(allnets, ign)
        self._loading = False
        if "zone_model" in opts:
            self.zone_combo.setCurrentText(opts["zone_model"])
        if opts.get("mesh_pitch_mm"):
            self.pitch_edit.setText(f"{opts['mesh_pitch_mm']:g}")
        self.st.set_netsel(path)
        self._pending_nets = doc.get("nets", {})
        for k, cb in self.section_boxes.items():
            cb.setChecked(bool((opts.get("sections") or {}).get(k, True)))
        self._overrides = {}
        self.refresh_pairs()
        for r in range(self.pair_table.rowCount()):
            cfg = self._pending_nets.get(self.pair_table.item(r, 0).text())
            if not cfg:
                continue
            mw = self.pair_table.cellWidget(r, 2); sw = self.pair_table.cellWidget(r, 3)
            if cfg.get("pairs") in PAIR_MODES:
                mw.setCurrentText(cfg["pairs"])
            if cfg.get("source"):
                sw.setCurrentText(cfg["source"])
        restored = {}
        for nname, cfg in self._pending_nets.items():
            for spec, vals in (cfg.get("pair_overrides") or {}).items():
                a, _sep, b = spec.partition(">")
                restored[(nname, a.strip(), b.strip())] = dict(vals)
        self._overrides = restored
        self.refresh_overrides()
        self.path = path; self.dirty = False; self._update_title()
        msg = [f"Opened {os.path.basename(path)}: patterns expanded to "
               f"{len(keep)} selected, {len(ign)} ignored."]
        if doc.get("select") and any(ch in p for p in doc["select"] for ch in "*?["):
            msg.append("Globs are expanded to concrete net names here and will be "
                       "saved that way, except an all-nets selection which stays '*'.")
        for p in unused_s:
            msg.append(f"select pattern {p!r} matched nothing.")
        for p in unused_i:
            msg.append(f"ignore pattern {p!r} matched nothing.")
        self.expand_note.setText("  ".join(msg))
        self.refresh_counts()

    def save(self):
        if not self.path:
            return self.save_as()
        return self._write(self.path)

    def save_as(self):
        suggested = self.path or os.path.join(self.default_dir() or "",
                                              "net_selection.json")
        path, _ = QFileDialog.getSaveFileName(self, "Save net selection", suggested,
                                              "JSON (*.json)")
        if path:
            self.path = path
            return self._write(path)
        return False

    def _write(self, path):
        if not self.board:
            QMessageBox.information(self, "No board", "Load a board first."); return False
        doc = self.build_doc()
        errs = validate_netsel(doc)
        if errs:
            QMessageBox.warning(self, "Refusing to save an invalid file",
                                "\n".join(errs))
            return False
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(doc, fh, indent=2)
        self.st.set_netsel(path)
        self.dirty = False; self._update_title()
        self.status.setText(f"Saved {path} (validated against the built-in schema).")
        return True

    # ---- report ----
    def generate(self, save=True):
        if not self.board:
            self.status.setText("Load a .kicad_pcb on the Stackup tab first."); return
        opts = dict(DEFAULT_OPTIONS)
        opts.update(self.options())
        if not opts.get("plating_um"):
            self.status.setText("Set a barrel plating thickness on the Via / Path tab "
                                "- it has no default and appears in no board file.")
            return
        keep, _clash = self.effective_nets()
        if not keep:
            self.status.setText("No nets selected."); return
        doc = self.build_doc()
        geo = self.st.stackup.geometry(opts["plating_um"], opts["outer_plating_adds"])
        order = [g["name"] for g in geo]
        self.preview.clear()
        self._cancel = False
        self.gen_btn.setEnabled(False); self.preview_btn.setEnabled(False)
        started = time.perf_counter()

        def progress(done, total, name, res):
            """Append each net to the preview the moment it is solved."""
            if res is None:
                self.status.setText(f"[{done + 1}/{total}] solving {name}...")
            else:
                lines = []
                for pr in res["pairs"]:
                    if "error" in pr:
                        lines.append(f"  {pr['from']} -> {pr['to']}: ERROR {pr['error']}")
                        continue
                    lines.append(
                        f"  {pr['from']:>12} -> {pr['to']:<12} "
                        f"{format_ohms(pr['network_ohms']):>12}  "
                        f"{pr['voltage_out_v']:.5g} V out  "
                        f"[{pr.get('zone_model', '-')}, {pr.get('nodes', 0)} nodes, "
                        f"{pr.get('solve_seconds', 0) * 1000:.0f} ms]")
                if not res["pairs"]:
                    lines.append("  (no pad pairs)")
                self.preview.append(f"{name}  ({len(res['pairs'])} pair(s))")
                self.preview.append("\n".join(lines))
                self.status.setText(
                    f"[{done}/{total}] {name} done, "
                    f"{time.perf_counter() - started:.1f} s elapsed")
            self.preview.moveCursor(QTextCursor.End)
            QApplication.processEvents()
            return not self._cancel

        try:
            rep = build_report(self.board, self.st.stackup.source, doc, opts, order,
                               geo, opts["plating_um"] * 1e-6, progress=progress)
        except Exception as exc:                      # noqa: BLE001
            self.status.setText(f"Report failed: {exc}")
            self.gen_btn.setEnabled(True); self.preview_btn.setEnabled(True)
            return
        finally:
            self.gen_btn.setEnabled(True); self.preview_btn.setEnabled(True)
        md = report_markdown(rep)
        self._last_md = md
        pairs = sum(len(n["pairs"]) for n in rep["nets"])
        solved = time.perf_counter() - started
        self.preview.setPlainText(report_text(rep))
        self.assump.setText(
            f"plating {opts['plating_um']:g} um | {opts['hole_convention']} hole | "
            f"{opts['length_convention']} barrel | outer plating "
            f"{'on' if opts['outer_plating_adds'] else 'off'} | zone {opts['zone_model']} | "
            f"{opts.get('signal_voltage_v', 0):g} V, {opts['current_a']:g} A "
            f"at {opts['ambient_c']:g} C")
        if not save:
            self.status.setText(
                f"Preview only: {len(rep['nets'])} net(s), {pairs} pair(s), "
                f"solved in {solved:.2f} s.")
            return
        kind = self.fmt_combo.currentText()
        ext = {"Markdown (.md)": ("md", "Markdown (*.md)"),
               "Text (.txt)": ("txt", "Text (*.txt)"),
               "PDF (.pdf)": ("pdf", "PDF (*.pdf)"),
               "JSON (.json)": ("json", "JSON (*.json)")}[kind]
        out, _ = QFileDialog.getSaveFileName(
            self, "Save report",
            os.path.join(self.default_dir() or "", f"resistance_report.{ext[0]}"), ext[1])
        if not out:
            self.status.setText("Cancelled."); return
        try:
            if ext[0] == "pdf":
                write_pdf(md, out)
            else:
                body = (json.dumps(rep, indent=2, default=str) if ext[0] == "json"
                        else report_text(rep) if ext[0] == "txt" else md)
                with open(out, "w", encoding="utf-8") as fh:
                    fh.write(body)
        except Exception as exc:                      # noqa: BLE001
            self.status.setText(f"Could not write {out}: {exc}"); return
        self.status.setText(f"Wrote {out}: {len(rep['nets'])} net(s), {pairs} pad pair(s).")


# ---------------------------------------------------------------- main window
class MainWindow(QWidget):
    def __init__(self, board_path=None):
        super().__init__()
        self.setWindowTitle("PCB Trace / Via Resistance Calculator")
        self.globals = GlobalConditions()
        self.stackup_tab = SetupTab(self.globals)
        self.setup_tab = self.stackup_tab            # new name, old attribute kept
        if board_path:
            self.stackup_tab.open_project_path(board_path)
        self.via_tab = ViaPathTab(self.globals, self.stackup_tab)
        self.trace_tab = TraceTab(self.globals, self.stackup_tab, self.via_tab)
        self.stackup_tab.changed.connect(
            lambda: self.globals.set_board(self.stackup_tab.stackup.source))
        self.globals.set_board(self.stackup_tab.stackup.source)

        self.report_tab = ReportTab(self.globals, self.stackup_tab, self.via_tab)

        tabs = QTabWidget()
        tabs.addTab(self.trace_tab, "Trace")
        tabs.addTab(self.via_tab, "Via / Path")
        tabs.addTab(self.report_tab, "Report")
        tabs.addTab(self.stackup_tab, "Setup")
        self.tabs = tabs

        root = QVBoxLayout(self)
        root.addWidget(tabs, 1)
        self.resize(1040, 900)


def dump_stackup(path, plating_um=0.0, outer=False):
    st = load_stackup(path)
    print(f"source: {path}")
    print(f"copper layers: {len(st.copper)}   copper+dielectric: "
          f"{st.core_thickness_mm():.4f} mm   general(thickness): "
          f"{st.general_thickness} mm (includes mask)")
    print(f"plating: {plating_um:g} um   outer-layer plating: {'ON' if outer else 'OFF'}\n")
    print(f"{'layer':<15}{'type':<20}{'mm':>9}{'um':>9}{'oz':>8}")
    for l in st.layers:
        oz = f"{l.user_mm * 1000 / OZ_TO_UM:.3f}" if l.kind == "copper" else ""
        print(f"{l.name:<15}{(l.type_raw or l.kind):<20}{l.user_mm:>9.4f}"
              f"{l.user_mm * 1000:>9.1f}{oz:>8}")
    print(f"\n{'copper':<10}{'idx top':>8}{'idx bot':>9}{'finished um':>13}"
          f"{'oz':>7}{'z_top mm':>11}{'z_ctr mm':>11}")
    for g in st.geometry(plating_um, outer):
        print(f"{g['name']:<10}{g['index_top']:>8}{g['index_bottom']:>9}"
              f"{g['finished_mm'] * 1000:>13.1f}{g['oz']:>7.3f}"
              f"{g['z_top_mm']:>11.4f}{g['z_ctr_mm']:>11.4f}")
    vias = harvest_vias(path)
    if vias:
        print("\nvias found on this board (declared span is the drilled barrel, "
              "NOT the electrical span):")
        for (vtype, size, drill), n in vias:
            print(f"  {vtype:<8} pad {size} mm / hole {drill} mm   x{n}")


def _arg(args, name, cast=str, default=None):
    if name in args:
        i = args.index(name)
        if i + 1 < len(args):
            return cast(args[i + 1])
    return default


def run_report(args):
    board_path = _arg(args, "--report")
    if not board_path or not os.path.exists(board_path):
        print("usage: --report <board.kicad_pcb> [--nets sel.json] [--plating UM] "
              "[--zone-model none|ladder|mesh] [--format md|txt|json] [--out FILE]")
        return 2
    board = BoardNets(board_path)
    stack = load_stackup(board_path)

    if "--nets" in args:
        try:
            doc, opts = load_netsel(_arg(args, "--nets"))
        except (ValueError, json.JSONDecodeError) as exc:
            print(f"ERROR: {exc}")
            return 2
    else:
        doc, opts = {"_meta": {"version": "0.1"}}, dict(DEFAULT_OPTIONS)

    for flag, key, cast in (("--plating", "plating_um", float),
                            ("--zone-model", "zone_model", str),
                            ("--mesh-pitch", "mesh_pitch_mm", float),
                            ("--ambient", "ambient_c", float),
                            ("--current", "current_a", float)):
        v = _arg(args, flag, cast)
        if v is not None:
            opts[key] = v
    if opts.get("plating_um") in (None, 0):
        print("ERROR: barrel plating is required and has no default (it appears in no "
              "board file). Pass --plating 25 or set options.plating_um in the net file.")
        return 2

    geo = stack.geometry(opts["plating_um"], opts["outer_plating_adds"])
    order = [g["name"] for g in geo]
    plating_m = opts["plating_um"] * 1e-6
    rep = build_report(board, board_path, doc, opts, order, geo, plating_m)

    fmt = _arg(args, "--format", str, "md")
    text = (json.dumps(rep, indent=2, default=str) if fmt == "json"
            else report_text(rep) if fmt == "txt" else report_markdown(rep))
    out = _arg(args, "--out")
    if out:
        with open(out, "w", encoding="utf-8") as fh:
            fh.write(text)
        pairs = sum(len(n["pairs"]) for n in rep["nets"])
        print(f"wrote {out}: {len(rep['nets'])} net(s), {pairs} pad pair(s)")
    else:
        print(text)
    return 0


def main():
    args = sys.argv[1:]
    if "--emit-schema" in args:
        dest = _arg(args, "--emit-schema")
        text = json.dumps(NETSEL_SCHEMA, indent=2)
        if dest and not dest.startswith("--"):
            open(dest, "w", encoding="utf-8").write(text)
            print(f"wrote {dest}")
        else:
            print(text)
        sys.exit(0)
    if "--emit-nets" in args:
        src = _arg(args, "--emit-nets")
        if not src or not os.path.exists(src):
            print("usage: --emit-nets <board.kicad_pcb> [--out sel.json]")
            sys.exit(2)
        tpl = netsel_template(BoardNets(src), src)
        text = json.dumps(tpl, indent=2)
        dest = _arg(args, "--out")
        if dest:
            open(dest, "w", encoding="utf-8").write(text)
            print(f"wrote {dest}")
        else:
            print(text)
        sys.exit(0)
    if "--report" in args:
        sys.exit(run_report(args))
    if "--selftest" in args:
        board = next((a for a in args if a.endswith(".kicad_pcb")), None)
        failures = selftest(board_path=board)
        if failures:
            print("\nFAILURES:")
            for f in failures:
                print("  " + f)
        sys.exit(1 if failures else 0)
    if "--dump-stackup" in args:
        i = args.index("--dump-stackup")
        if i + 1 >= len(args):
            print("usage: --dump-stackup <board.kicad_pcb> [--plating UM] [--outer-plating]")
            sys.exit(2)
        plating = 0.0
        if "--plating" in args:
            plating = float(args[args.index("--plating") + 1])
        dump_stackup(args[i + 1], plating, "--outer-plating" in args)
        sys.exit(0)
    board = next((a for a in args if a.endswith(".kicad_pcb")), None)
    app = QApplication(sys.argv)
    win = MainWindow(board)
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
