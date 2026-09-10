# v0.1
"""Automatic resistance-model selection policy (project specification S8.7).

Session 07 — PWR-002 policy slice (contribution; the whole punch item, which
also covers the UI reason/override wiring, closes in a later session). This is
the explainable engine behind ``Auto``:

    * a net with no filled zone       -> ``point_to_point`` (series/routed chain);
    * a long strip-like stitched pour -> ``ladder`` (the fast approximation);
    * a square, split, perforated, or thermally-relieved pour -> ``mesh``.

The policy never *silently* uses a questionable ladder (PWR-002 Done-when:
"square/complex pours warn or escalate rather than silently using a questionable
ladder"). A square pour (aspect below :data:`~pathminer.analysis.builders.ladder.LADDER_MIN_ASPECT`)
or a pour flagged complex is escalated to the mesh with a stated reason. A user
override is honoured but keeps an ``overridden`` marker and any applicable
warning (S8.7: "A user override is permitted but shall retain an override marker
and any applicable warning").

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
    "ModelChoice",
    "select_model",
    "select_model_for_pour",
]

# The models this session's builders can emit; also the accepted overrides.
MODELS: Tuple[str, ...] = ("point_to_point", "ladder", "mesh")


@dataclass(frozen=True)
class ModelChoice:
    """An explainable model decision.

    ``model`` is the chosen model (one of :data:`MODELS`); ``reason`` explains
    *why*; ``warnings`` lists any caveat that still applies (kept even when the
    user overrode the automatic choice); ``overridden`` and ``requested`` record
    a user override; ``aspect`` is the pour aspect ratio the decision used (or
    ``None`` when there is no pour).
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
) -> ModelChoice:
    """Choose a resistance model and explain the choice.

    Parameters
    ----------
    has_pour:
        Whether the net has any filled copper. ``False`` selects
        ``point_to_point`` (there is no pour to strip or mesh).
    aspect:
        The pour's length:width ratio (from :class:`PourGeometry`). Required to
        distinguish a strip-like pour (ladder) from a square one (mesh) when
        ``has_pour`` is true; ``None`` is treated as "unknown", which escalates
        to the mesh rather than guessing a ladder.
    complex_pour:
        Set when the fill is split, perforated, or thermally relieved so the 1-D
        strip assumption cannot hold. Forces the mesh (S8.7).
    override:
        A user-forced model (one of :data:`MODELS`). Honoured, but the result is
        marked ``overridden`` and keeps any warning the automatic policy raised.
    min_aspect:
        The ladder's minimum acceptable aspect ratio (defaults to v0.13's 2:1).

    Raises ``ValueError`` for an unknown ``override``.
    """
    if override is not None and override not in MODELS:
        raise ValueError(
            f"unknown model override {override!r}; expected one of {MODELS}"
        )

    warnings: list[str] = []

    # ---- the automatic recommendation ----
    if not has_pour:
        auto = "point_to_point"
        auto_reason = (
            "no filled zone on this net: a manual/routed series chain has no "
            "pour to model, so the point-to-point builder applies"
        )
    else:
        low_aspect = aspect is not None and aspect < min_aspect
        if low_aspect:
            warnings.append(low_aspect_warning(aspect))
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

    # ---- apply a user override, keeping the marker and any warning ----
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
) -> ModelChoice:
    """Convenience wrapper: derive ``has_pour``/``aspect`` from a *pour* object.

    *pour* is any object with ``.net`` and ``.fills`` (e.g.
    ``pathminer.models.board.Pour``), or ``None`` for a net with no filled
    copper. A pour whose fill is empty is treated as no pour.
    """
    if pour is None:
        return select_model(
            has_pour=False, override=override, min_aspect=min_aspect
        )
    try:
        aspect = pour_geometry(pour).aspect
    except ValueError:
        # Empty fill: nothing to model as a pour.
        return select_model(
            has_pour=False, override=override, min_aspect=min_aspect
        )
    return select_model(
        has_pour=True,
        aspect=aspect,
        complex_pour=complex_pour,
        override=override,
        min_aspect=min_aspect,
    )
