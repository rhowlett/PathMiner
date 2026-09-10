# v0.1
"""Automatic resistance-model selection policy (project specification S8.7).

Session 07 — PWR-002 policy slice (contribution; the whole punch item, which
also covers the UI reason/override wiring, closes in a later session). This is
the explainable engine behind ``Auto``. Per S8.7 it distinguishes four cases:

    * a manually declared trace/via series chain      -> ``point_to_point``;
    * a routed net (traces/vias) without zones         -> ``routed_graph``;
    * a long strip-like stitched pour                  -> ``ladder``;
    * a square, split, perforated, or thermally-relieved pour -> ``mesh``.

Absence of a zone does **not** establish a series topology: a zone-less net may
still be a branching routed graph, which needs a routed-graph builder. That
builder does not exist in this session (only point-to-point, ladder, and mesh
are implemented), so a routed net is reported as :data:`ROUTED_GRAPH` with a
warning that the analysis is unsupported until its builder lands, rather than
being silently modelled as a single series chain. The caller states which
no-zone case it has via ``series_chain``.

The policy never *silently* uses a questionable ladder (PWR-002 Done-when:
"square/complex pours warn or escalate rather than silently using a questionable
ladder"). A square pour (aspect below
:data:`~pathminer.analysis.builders.ladder.LADDER_MIN_ASPECT`), a complex pour,
or one of unknown geometry is escalated to the mesh with a stated reason. A user
override is honoured but keeps an ``overridden`` marker and **every applicable
warning** — including the reason the strip assumption is invalid for a complex
or unknown-geometry pour (S8.7: "A user override is permitted but shall retain
an override marker and any applicable warning").

Layer contract (ARCH-002): analysis layer — imports ``pathminer.core`` and its
sibling builders only; no Qt, no wx.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple

from .builders.ladder import LADDER_MIN_ASPECT, low_aspect_warning
from .builders.pour import pour_geometry

__all__ = [
    "MODELS",
    "ROUTED_GRAPH",
    "COMPLEX_POUR_WARNING",
    "UNKNOWN_GEOMETRY_WARNING",
    "ROUTED_UNSUPPORTED_WARNING",
    "ModelChoice",
    "select_model",
    "select_model_for_pour",
]

# The models this session's builders can emit; also the accepted overrides.
MODELS: Tuple[str, ...] = ("point_to_point", "ladder", "mesh")

# An automatic-only outcome for a routed, zone-less net: no builder exists for
# it in this session, so it is never a valid override target.
ROUTED_GRAPH: str = "routed_graph"

# Caveats that must survive a user override (S8.7).
COMPLEX_POUR_WARNING: str = (
    "pour is split / perforated / thermally-relieved, so the 1-D strip "
    "assumption does not hold; the mesh model is recommended"
)
UNKNOWN_GEOMETRY_WARNING: str = (
    "pour geometry is unknown, so the 1-D strip assumption cannot be justified; "
    "the mesh model is recommended"
)
ROUTED_UNSUPPORTED_WARNING: str = (
    "this is a routed net without zones, not a declared series chain; "
    "routed-graph resistance analysis is not yet implemented, and a "
    "point-to-point series model would ignore any parallel copper"
)


@dataclass(frozen=True)
class ModelChoice:
    """An explainable model decision.

    ``model`` is the chosen model — one of :data:`MODELS`, or :data:`ROUTED_GRAPH`
    for a zone-less routed net whose builder does not yet exist. ``reason``
    explains *why*; ``warnings`` lists every caveat that still applies (kept even
    when the user overrode the automatic choice); ``overridden`` and
    ``requested`` record a user override; ``aspect`` is the pour aspect ratio the
    decision used (or ``None`` when there is no pour).
    """

    model: str
    reason: str
    warnings: Tuple[str, ...] = ()
    overridden: bool = False
    requested: Optional[str] = None
    aspect: Optional[float] = None


def select_model(
    *,
    has_pour: bool,
    aspect: Optional[float] = None,
    complex_pour: bool = False,
    override: Optional[str] = None,
    min_aspect: float = LADDER_MIN_ASPECT,
    series_chain: bool = False,
) -> ModelChoice:
    """Choose a resistance model and explain the choice.

    Parameters
    ----------
    has_pour:
        Whether the net has any filled copper. ``False`` means there is no pour
        to strip or mesh; the choice then depends on ``series_chain``.
    aspect:
        The pour's length:width ratio (from :class:`PourGeometry`). Required to
        distinguish a strip-like pour (ladder) from a square one (mesh) when
        ``has_pour`` is true; ``None`` is treated as "unknown", which escalates
        to the mesh (with a retained warning) rather than guessing a ladder.
    complex_pour:
        Set when the fill is split, perforated, or thermally relieved so the 1-D
        strip assumption cannot hold. Forces the mesh and records a warning that
        survives an override (S8.7).
    override:
        A user-forced model (one of :data:`MODELS`). Honoured, but the result is
        marked ``overridden`` and keeps every applicable warning. Note
        :data:`ROUTED_GRAPH` is not a valid override (no builder exists).
    min_aspect:
        The ladder's minimum acceptable aspect ratio (defaults to v0.13's 2:1).
    series_chain:
        Only consulted when ``has_pour`` is false. ``True`` means the caller has
        a manually declared trace/via series chain → ``point_to_point``.
        ``False`` (the default) means a routed net → :data:`ROUTED_GRAPH`
        (unsupported), because absence of a zone does not establish a series
        topology.

    Raises ``ValueError`` for an unknown ``override``.
    """
    if override is not None and override not in MODELS:
        raise ValueError(
            f"unknown model override {override!r}; expected one of {MODELS}"
        )

    warnings: list[str] = []

    # ---- the automatic recommendation ----
    if not has_pour:
        if series_chain:
            auto = "point_to_point"
            auto_reason = (
                "no filled zone and a manually declared series chain: the "
                "point-to-point series builder applies"
            )
        else:
            auto = ROUTED_GRAPH
            auto_reason = (
                "no filled zone, but a routed net rather than a declared series "
                "chain: routed-graph analysis is required and is not yet "
                "implemented (no routed-graph builder in this build)"
            )
            warnings.append(ROUTED_UNSUPPORTED_WARNING)
    else:
        low_aspect = aspect is not None and aspect < min_aspect
        # Collect every applicable caveat first, so it survives an override
        # regardless of which model the automatic policy ends up choosing.
        if aspect is None:
            warnings.append(UNKNOWN_GEOMETRY_WARNING)
        elif low_aspect:
            warnings.append(low_aspect_warning(aspect))
        if complex_pour:
            warnings.append(COMPLEX_POUR_WARNING)

        if complex_pour:
            auto = "mesh"
            auto_reason = (
                "pour is split / perforated / thermally-relieved, so the 1-D "
                "strip assumption does not hold; meshing the actual copper"
            )
        elif aspect is None:
            auto = "mesh"
            auto_reason = (
                "pour geometry is unknown, so the strip assumption cannot be "
                "justified; meshing the actual copper"
            )
        elif low_aspect:
            auto = "mesh"
            auto_reason = (
                f"pour aspect ratio {aspect:.1f}:1 is below {min_aspect:.1f}:1 - "
                "too square for a 1-D strip; escalating to the mesh"
            )
        else:
            auto = "ladder"
            auto_reason = (
                f"pour is strip-like (aspect {aspect:.1f}:1 >= {min_aspect:.1f}:1); "
                "the fast 1-D ladder is justified"
            )

    # ---- apply a user override, keeping the marker and every applicable warning ----
    if override is not None:
        reason = f"user override: {override} (auto would have chosen {auto})"
        return ModelChoice(
            model=override,
            reason=reason,
            warnings=tuple(warnings),
            overridden=True,
            requested=override,
            aspect=aspect,
        )

    return ModelChoice(
        model=auto,
        reason=auto_reason,
        warnings=tuple(warnings),
        overridden=False,
        requested=None,
        aspect=aspect,
    )


def select_model_for_pour(
    pour: Optional[object],
    *,
    complex_pour: bool = False,
    override: Optional[str] = None,
    min_aspect: float = LADDER_MIN_ASPECT,
    series_chain: bool = False,
) -> ModelChoice:
    """Convenience wrapper: derive ``has_pour``/``aspect`` from a *pour* object.

    *pour* is any object with ``.net`` and ``.fills`` (e.g.
    ``pathminer.models.board.Pour``), or ``None`` for a net with no filled
    copper. A pour whose fill is empty is treated as no pour. For the no-pour
    cases, ``series_chain`` selects between a manual series chain
    (``point_to_point``) and a routed net (:data:`ROUTED_GRAPH`, unsupported) —
    absence of a zone alone does not imply a series topology.
    """
    if pour is None:
        return select_model(
            has_pour=False,
            override=override,
            min_aspect=min_aspect,
            series_chain=series_chain,
        )
    try:
        aspect = pour_geometry(pour).aspect
    except ValueError:
        # Empty fill: nothing to model as a pour.
        return select_model(
            has_pour=False,
            override=override,
            min_aspect=min_aspect,
            series_chain=series_chain,
        )
    return select_model(
        has_pour=True,
        aspect=aspect,
        complex_pour=complex_pour,
        override=override,
        min_aspect=min_aspect,
    )
