# v0.1
"""pathminer.kicad.stackup — copper layer and dielectric stackup reader.

Extracted from tools/pcb_trace_resistance.py v0.13.

Reads a stackup from a parsed .kicad_pcb S-expression tree or constructs a
manual fallback.  Does not import Qt, wx, or pathminer.core.

Constants
---------
OZ_TO_UM : float
    Copper weight conversion factor: 1 oz/ft² = 34.798 µm nominal.
    Source: IPC-4562A / industry convention used throughout v0.13.

Public surface
--------------
StackLayer          — single layer (copper, dielectric, mask, …)
Stackup             — ordered layer stack with geometry helpers
load_stackup(path) -> Stackup
    Parse a .kicad_pcb file and return the board stackup.
manual_stackup(...) -> Stackup
    Construct an evenly distributed fallback stackup (D6 manual mode).

Design notes (originally documented in v0.3 source, D1–D8)
-----------------------------------------------------------
D6  Manual fallback distributes dielectric evenly; the result is marked
    ``estimated=True`` so callers can warn.
D8  Plating grows outer layers AWAY from the core when ``outer_adds=True``
    in ``Stackup.geometry()``, thickening the board by 2×plating.  Inner
    layers are foil only.

KiCad parsing notes
-------------------
Layer ordinals in a .kicad_pcb are NOT stack order.  Physical order comes
only from the ``(stackup)`` block's own sequence.  The ``(stackup)`` block
is optional; when absent ``load_stackup`` raises ValueError.
"""

from __future__ import annotations

from pathminer.kicad.sexpr import Node, parse_sexpr

# Copper weight to thickness conversion factor (IPC-4562A nominal).
OZ_TO_UM: float = 34.798

# Layer-type strings that represent copper foil.
_COPPER_TYPES: frozenset[str] = frozenset({"copper"})


class StackLayer:
    """A single layer in the physical board stackup.

    Attributes
    ----------
    name : str
        KiCad layer name (e.g. ``"F.Cu"``, ``"In1.Cu"``, ``"B.Cu"``).
    type_raw : str
        Raw ``(type ...)`` value from the stackup block (e.g. ``"copper"``,
        ``"core"``, ``"prepreg"``, ``"soldermask"``).
    base_mm : float
        Original thickness in mm as read from the file (or constructed).
    user_mm : float
        User-editable thickness.  Initially equal to *base_mm*.
    material : str | None
        Material string if present in the file (e.g. ``"FR4"``, ``"Copper"``).
    epsilon_r : float | None
        Relative permittivity if present in the file.
    """

    def __init__(
        self,
        name: str,
        type_raw: str,
        thickness_mm: float,
        material: str | None = None,
        epsilon_r: float | None = None,
    ) -> None:
        self.name = name
        self.type_raw = type_raw
        self.base_mm = thickness_mm
        self.user_mm = thickness_mm
        self.material = material
        self.epsilon_r = epsilon_r

    @property
    def kind(self) -> str:
        """Normalised layer kind: ``"copper"``, ``"mask"``, ``"silk"``,
        ``"paste"``, or ``"dielectric"``."""
        t = (self.type_raw or "").lower()
        if t in _COPPER_TYPES:
            return "copper"
        if "mask" in t:
            return "mask"
        if "silk" in t:
            return "silk"
        if "paste" in t:
            return "paste"
        return "dielectric"

    @property
    def dirty(self) -> bool:
        """True when *user_mm* differs from *base_mm* by more than floating-
        point noise."""
        return abs(self.user_mm - self.base_mm) > 1e-12

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"StackLayer({self.name!r}, kind={self.kind!r}, "
            f"user_mm={self.user_mm})"
        )


class Stackup:
    """Ordered physical board stackup.

    Attributes
    ----------
    layers : list[StackLayer]
        All layers in physical top-to-bottom order (copper, dielectric, mask,
        silk, paste).
    source : str
        Human-readable provenance string: file path or ``"<manual>"``.
    general_thickness : float | None
        ``(general (thickness ...))`` value from the board file, which includes
        solder mask and is therefore never a bare copper barrel span.
    estimated : bool
        True when the stackup was constructed by :func:`manual_stackup` rather
        than read from a board file.
    """

    def __init__(
        self,
        layers: list[StackLayer],
        source: str = "",
        general_thickness: float | None = None,
        estimated: bool = False,
    ) -> None:
        self.layers = layers
        self.source = source
        self.general_thickness = general_thickness
        self.estimated = estimated

    @property
    def copper(self) -> list[StackLayer]:
        """Copper layers only, in physical top-to-bottom order."""
        return [l for l in self.layers if l.kind == "copper"]

    def core_thickness_mm(self) -> float:
        """Sum of copper and dielectric thicknesses; excludes mask/silk/paste."""
        return sum(
            l.user_mm for l in self.layers if l.kind in ("copper", "dielectric")
        )

    def geometry(
        self, plating_um: float = 0.0, outer_adds: bool = False
    ) -> list[dict]:
        """Return per-copper-layer geometry dicts, top-to-bottom.

        Dielectric interfaces are fixed.  When *outer_adds* is True the outer
        copper layers grow AWAY from the core, thickening the board by
        ``2 × plating_um / 1000`` mm (D8).

        Each dict contains:

        - ``"name"``        — layer name string
        - ``"index_top"``   — 1-based index from top copper layer
        - ``"index_bottom"``— 1-based index from bottom copper layer
        - ``"is_outer"``    — True for top and bottom layers
        - ``"foil_mm"``     — unplated foil thickness in mm
        - ``"finished_mm"`` — final finished thickness in mm (foil + plating)
        - ``"oz"``          — finished thickness in oz/ft²
        - ``"z_top_mm"``    — z coordinate of the top surface (from board top)
        - ``"z_ctr_mm"``    — z coordinate of the copper centroid
        """
        # Walk copper+dielectric layers to assign z-coordinates.
        z = 0.0
        spans: dict[int, tuple[float, float]] = {}
        for layer in self.layers:
            if layer.kind in ("copper", "dielectric"):
                spans[id(layer)] = (z, z + layer.user_mm)
                z += layer.user_mm

        copper_layers = self.copper
        out: list[dict] = []
        n = len(copper_layers)
        p = plating_um / 1000.0  # µm → mm

        for i, layer in enumerate(copper_layers):
            z_top, z_bot = spans[id(layer)]
            is_outer = i == 0 or i == n - 1
            t = layer.user_mm + (p if (is_outer and outer_adds) else 0.0)
            if is_outer and outer_adds:
                if i == 0:
                    z_top = z_bot - t  # top layer grows upward
                # bottom layer z_top stays; it grows downward
            out.append(
                {
                    "name": layer.name,
                    "index_top": i + 1,
                    "index_bottom": n - i,
                    "is_outer": is_outer,
                    "foil_mm": layer.user_mm,
                    "finished_mm": t,
                    "oz": t * 1000.0 / OZ_TO_UM,
                    "z_top_mm": z_top,
                    "z_ctr_mm": z_top + t / 2.0,
                }
            )
        return out

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"Stackup(source={self.source!r}, "
            f"{len(self.copper)} copper layers, estimated={self.estimated})"
        )


def load_stackup(path: str) -> Stackup:
    """Parse a .kicad_pcb file and return its board stackup.

    Parameters
    ----------
    path:
        Absolute or relative path to a ``.kicad_pcb`` file.

    Returns
    -------
    Stackup
        The stackup as defined in the ``(setup (stackup ...))`` block.

    Raises
    ------
    ValueError
        If the file is not a ``.kicad_pcb`` file, or if it contains no
        ``(stackup)`` block.  The error message guides the user to open
        Board Setup > Physical Stackup and save to generate the block.
    OSError
        If the file cannot be read.
    """
    text = open(path, "r", encoding="utf-8").read()
    root = parse_sexpr(text)
    if root.head != "kicad_pcb":
        raise ValueError("not a .kicad_pcb file")

    general = root.get("general")
    gthick = general.val("thickness") if general else None

    setup = root.get("setup")
    stack = setup.get("stackup") if setup else None
    if stack is None:
        raise ValueError(
            "no (stackup) block in this board - "
            "open Board Setup > Physical Stackup and save"
        )

    layers: list[StackLayer] = []
    for ln in stack.findall("layer"):
        vals = ln.kids()
        name: str = vals[0] if vals and isinstance(vals[0], str) else "?"
        tnode = ln.get("type")
        type_raw: str = tnode.kids()[0] if tnode and tnode.kids() else ""
        th = ln.val("thickness") or 0.0
        mnode = ln.get("material")
        mat: str | None = mnode.kids()[0] if mnode and mnode.kids() else None
        layers.append(StackLayer(name, type_raw, th, mat, ln.val("epsilon_r")))

    return Stackup(layers, source=path, general_thickness=gthick)


def manual_stackup(
    n_copper: int = 4,
    board_mm: float = 1.6,
    outer_oz: float = 1.0,
    inner_oz: float = 1.0,
) -> Stackup:
    """Construct an evenly distributed fallback stackup (D6 manual mode).

    The dielectric is distributed evenly across the inner gaps.  The result
    is marked ``estimated=True`` so callers can warn users that board-file
    values are preferred.

    Parameters
    ----------
    n_copper:
        Number of copper layers.  Must be ≥ 1; raises ``ValueError`` otherwise.
    board_mm:
        Target board thickness in mm.
    outer_oz:
        Copper weight for the top and bottom layers (oz/ft²).
    inner_oz:
        Copper weight for all inner layers (oz/ft²).

    Returns
    -------
    Stackup
        Manual stackup with ``source="<manual>"`` and ``estimated=True``.

    Raises
    ------
    ValueError
        If *n_copper* is less than 1.
    """
    if n_copper < 1:
        raise ValueError(f"n_copper must be >= 1, got {n_copper}")
    layers: list[StackLayer] = []
    cu_mm = []
    for i in range(n_copper):
        oz = outer_oz if i in (0, n_copper - 1) else inner_oz
        cu_mm.append(oz * OZ_TO_UM / 1000.0)

    n_diel = max(n_copper - 1, 0)
    diel = max((board_mm - sum(cu_mm)) / n_diel, 1e-4) if n_diel else 0.0

    for i in range(n_copper):
        if i == 0:
            nm = "F.Cu"
        elif i == n_copper - 1:
            nm = "B.Cu"
        else:
            nm = f"In{i}.Cu"
        layers.append(StackLayer(nm, "copper", cu_mm[i]))
        if i < n_copper - 1:
            layers.append(StackLayer(f"dielectric {i + 1}", "core", diel, "FR4", 4.5))

    return Stackup(layers, source="<manual>", estimated=True)
