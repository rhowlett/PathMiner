# v0.1
"""Tests for pathminer.analysis.model_selection (Session 07, PWR-002 slice).

The Auto policy (project specification S8.7) must be explainable and must never
silently use a questionable ladder (PWR-002 Done-when: "square/complex pours
warn or escalate rather than silently using a questionable ladder"). These
tests cover:

    * no zone + declared series chain -> point_to_point;
    * no zone + routed net -> routed_graph, reported unsupported (no builder);
    * strip-like pour -> ladder, no warning;
    * square / unknown / complex pour -> mesh, with a stated reason and a warning;
    * a user override honoured but marked, with every applicable warning retained
      (square, complex, unknown, and routed-unsupported cases);
    * an unknown override rejected;
    * the pour-object convenience wrapper.
"""

from __future__ import annotations

import pytest

from pathminer.analysis.builders.ladder import LADDER_MIN_ASPECT
from pathminer.analysis.model_selection import (
    MODELS,
    ROUTED_GRAPH,
    ModelChoice,
    select_model,
    select_model_for_pour,
)


class _Pour:
    def __init__(self, net, fills):
        self.net = net
        self.fills = fills


def _rect(x0, y0, x1, y1):
    return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]


# ---------------------------------------------------------------------------
# Automatic recommendations.
# ---------------------------------------------------------------------------


def test_no_zone_series_chain_selects_point_to_point():
    choice = select_model(has_pour=False, series_chain=True)
    assert isinstance(choice, ModelChoice)
    assert choice.model == "point_to_point"
    assert choice.warnings == ()
    assert not choice.overridden


def test_no_zone_routed_net_reports_unsupported():
    # Absence of a zone does NOT imply a series chain: a routed net has no
    # builder yet and must be reported, not silently modelled as series.
    choice = select_model(has_pour=False)          # series_chain defaults False
    assert choice.model == ROUTED_GRAPH
    assert choice.model not in MODELS              # not a buildable model
    assert choice.warnings                          # unsupported warning present
    assert "not yet implemented" in choice.reason


def test_routed_override_to_point_to_point_retains_unsupported_warning():
    # A user may force point-to-point on a routed net, but the caveat that this
    # is really a routed graph (parallel copper ignored) must survive.
    choice = select_model(has_pour=False, override="point_to_point")
    assert choice.model == "point_to_point"
    assert choice.overridden is True
    assert choice.requested == "point_to_point"
    assert choice.warnings                          # routed-unsupported caveat kept
    assert "auto would have chosen routed_graph" in choice.reason


def test_strip_like_pour_selects_ladder_without_warning():
    choice = select_model(has_pour=True, aspect=10.0)
    assert choice.model == "ladder"
    assert choice.warnings == ()
    assert "strip-like" in choice.reason
    assert choice.aspect == 10.0


def test_square_pour_escalates_to_mesh_with_warning():
    choice = select_model(has_pour=True, aspect=1.0)
    assert choice.model == "mesh"
    assert choice.warnings                       # a low-aspect warning is present
    assert "escalating to the mesh" in choice.reason


def test_complex_pour_selects_mesh_even_when_strip_like():
    choice = select_model(has_pour=True, aspect=20.0, complex_pour=True)
    assert choice.model == "mesh"
    assert "strip assumption does not hold" in choice.reason
    assert choice.warnings                          # complex caveat present


def test_unknown_aspect_with_pour_selects_mesh():
    choice = select_model(has_pour=True, aspect=None)
    assert choice.model == "mesh"
    assert "unknown" in choice.reason
    assert choice.warnings                          # unknown-geometry caveat present


@pytest.mark.parametrize("aspect,expected", [
    (LADDER_MIN_ASPECT, "ladder"),               # boundary: >= min -> ladder
    (LADDER_MIN_ASPECT - 0.01, "mesh"),          # just below -> mesh
])
def test_aspect_boundary_is_min_aspect(aspect, expected):
    assert select_model(has_pour=True, aspect=aspect).model == expected


# ---------------------------------------------------------------------------
# User override (S8.7: honoured, marked, warning retained).
# ---------------------------------------------------------------------------


def test_override_is_honoured_and_marked():
    choice = select_model(has_pour=True, aspect=10.0, override="mesh")
    assert choice.model == "mesh"
    assert choice.overridden is True
    assert choice.requested == "mesh"
    assert "auto would have chosen ladder" in choice.reason


def test_override_to_ladder_on_square_pour_retains_warning():
    # Forcing the fast ladder on a square pour must keep the caveat.
    choice = select_model(has_pour=True, aspect=1.0, override="ladder")
    assert choice.model == "ladder"
    assert choice.overridden is True
    assert choice.warnings                       # low-aspect warning retained
    assert "auto would have chosen mesh" in choice.reason


def test_override_to_ladder_on_complex_pour_retains_warning():
    # A strip-like BUT complex pour: forcing the ladder must keep the caveat
    # that the strip assumption is invalid, even though the aspect is fine.
    choice = select_model(has_pour=True, aspect=10.0, complex_pour=True,
                          override="ladder")
    assert choice.model == "ladder"
    assert choice.overridden is True
    assert choice.warnings                       # complex caveat retained
    assert any("does not hold" in w for w in choice.warnings)
    assert "auto would have chosen mesh" in choice.reason


def test_override_to_ladder_on_unknown_geometry_retains_warning():
    choice = select_model(has_pour=True, aspect=None, override="ladder")
    assert choice.model == "ladder"
    assert choice.overridden is True
    assert choice.warnings                       # unknown-geometry caveat retained
    assert any("cannot be justified" in w for w in choice.warnings)


def test_unknown_override_raises():
    with pytest.raises(ValueError, match="unknown model override"):
        select_model(has_pour=True, aspect=10.0, override="wishful")


def test_override_values_are_the_known_models():
    for model in MODELS:
        assert select_model(has_pour=True, aspect=5.0, override=model).model == model


# ---------------------------------------------------------------------------
# Pour-object convenience wrapper.
# ---------------------------------------------------------------------------


def test_select_for_strip_pour_picks_ladder():
    pour = _Pour(4, {"F.Cu": _rect(0, 0, 20, 2)})   # 10:1
    assert select_model_for_pour(pour).model == "ladder"


def test_select_for_square_pour_picks_mesh():
    pour = _Pour(4, {"F.Cu": _rect(0, 0, 5, 5)})    # 1:1
    choice = select_model_for_pour(pour)
    assert choice.model == "mesh"
    assert choice.warnings


def test_select_for_none_pour_series_chain_picks_point_to_point():
    assert select_model_for_pour(None, series_chain=True).model == "point_to_point"


def test_select_for_none_pour_defaults_to_routed_unsupported():
    # No zone and no series-chain claim: routed graph, reported unsupported.
    choice = select_model_for_pour(None)
    assert choice.model == ROUTED_GRAPH
    assert choice.warnings


def test_select_for_empty_fill_series_chain_picks_point_to_point():
    empty = _Pour(4, {"F.Cu": []})
    assert select_model_for_pour(empty, series_chain=True).model == "point_to_point"


def test_select_for_empty_fill_defaults_to_routed_unsupported():
    empty = _Pour(4, {"F.Cu": []})
    assert select_model_for_pour(empty).model == ROUTED_GRAPH


def test_select_for_pour_reports_aspect():
    pour = _Pour(4, {"F.Cu": _rect(0, 0, 20, 2)})
    choice = select_model_for_pour(pour)
    assert choice.aspect == pytest.approx(10.0, rel=1e-6)
