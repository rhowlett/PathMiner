# v0.2
"""Tests for pathminer.kicad.stackup.

Session 05 — KiCad syntax, stackup and preferences extraction.
Punch-list contribution: ARCH-003 (parser foundation capability slice).

Synthetic .kicad_pcb fixtures are created under pytest tmp_path rather than
committed fixture files (which are outside this session's owned write scope).
The only real board file used is the canonical IP5385 parity reference,
already present in the repository at ai_reference/.

Covers:
  - StackLayer.kind classification
  - StackLayer.dirty flag
  - Stackup.copper filter
  - Stackup.core_thickness_mm (excludes mask/silk/paste)
  - Stackup.geometry — z coordinates, plating growth (D8), index ordering
  - load_stackup — positive, no-stackup error, wrong-root error, OSError
  - manual_stackup — distribution, naming, estimated flag, n_copper validation
  - Parity regression: Stackup.geometry() matches v0.13 output on the
    reference board (stackup parity record, required deliverable)

Deviations from v0.13 recorded here:
  - manual_stackup raises ValueError for n_copper < 1 (v0.13 silently
    produced an empty layer list; this is a deliberate improvement).
  - No deviation for n_copper == 1: v0.13 handled it; so does this module.
"""

from __future__ import annotations

import os
import textwrap

import pytest

from pathminer.kicad.stackup import (
    OZ_TO_UM,
    StackLayer,
    Stackup,
    load_stackup,
    manual_stackup,
)

# ---------------------------------------------------------------------------
# Reference board path (canonical IP5385 parity fixture)
# ---------------------------------------------------------------------------

REFERENCE_BOARD = os.path.normpath(
    os.path.join(
        os.path.dirname(__file__),
        "..",
        "ai_reference/kicad_project_example/"
        "Ref_PowerBank_injoinic_IP5385_v0.8.kicad_pcb",
    )
)


# ---------------------------------------------------------------------------
# Synthetic .kicad_pcb content helpers
# ---------------------------------------------------------------------------

_FOUR_LAYER_PCB = textwrap.dedent("""\
    (kicad_pcb
        (version 20241229)
        (generator "pcbnew")
        (general
            (thickness 1.6)
        )
        (setup
            (stackup
                (layer "F.Mask"
                    (type "Top Solder Mask")
                    (thickness 0.01)
                )
                (layer "F.Cu"
                    (type "copper")
                    (thickness 0.035)
                )
                (layer "dielectric 1"
                    (type "core")
                    (thickness 0.1)
                    (material "FR4")
                    (epsilon_r 4.5)
                )
                (layer "In1.Cu"
                    (type "copper")
                    (thickness 0.07)
                )
                (layer "dielectric 2"
                    (type "core")
                    (thickness 1.24)
                    (material "FR4")
                    (epsilon_r 4.5)
                )
                (layer "In2.Cu"
                    (type "copper")
                    (thickness 0.07)
                )
                (layer "dielectric 3"
                    (type "core")
                    (thickness 0.1)
                    (material "FR4")
                    (epsilon_r 4.5)
                )
                (layer "B.Cu"
                    (type "copper")
                    (thickness 0.035)
                )
                (layer "B.Mask"
                    (type "Bottom Solder Mask")
                    (thickness 0.01)
                )
            )
        )
    )
""")

_NO_STACKUP_PCB = textwrap.dedent("""\
    (kicad_pcb
        (version 20241229)
        (generator "pcbnew")
        (general
            (thickness 1.6)
        )
        (setup
            (pad_to_mask_clearance 0)
        )
    )
""")

_NOT_A_PCB = textwrap.dedent("""\
    (kicad_sch
        (version 20241229)
        (generator "eeschema")
    )
""")

_SINGLE_COPPER_PCB = textwrap.dedent("""\
    (kicad_pcb
        (version 20241229)
        (generator "pcbnew")
        (general
            (thickness 0.8)
        )
        (setup
            (stackup
                (layer "F.Cu"
                    (type "copper")
                    (thickness 0.035)
                )
            )
        )
    )
""")


def _write(tmp_path, name: str, content: str) -> str:
    """Write *content* to *name* inside *tmp_path* and return the path."""
    p = tmp_path / name
    p.write_text(content, encoding="utf-8")
    return str(p)


# ---------------------------------------------------------------------------
# StackLayer
# ---------------------------------------------------------------------------

class TestStackLayerKind:
    """StackLayer.kind maps type_raw strings to normalised kind values."""

    @pytest.mark.parametrize(
        "type_raw, expected_kind",
        [
            ("copper", "copper"),
            ("Copper", "copper"),
            ("core", "dielectric"),
            ("prepreg", "dielectric"),
            ("soldermask", "mask"),
            ("Top Solder Mask", "mask"),
            ("Bottom Solder Mask", "mask"),
            ("silkscreen", "silk"),
            ("Top Silk Screen", "silk"),
            ("solder paste", "paste"),
            ("Top Solder Paste", "paste"),
            ("", "dielectric"),
            ("unknown", "dielectric"),
        ],
    )
    def test_kind_classification(self, type_raw, expected_kind):
        layer = StackLayer("F.Cu", type_raw, 0.035)
        assert layer.kind == expected_kind

    def test_copper_foil_string_is_not_copper_kind(self):
        # Only the exact string "copper" (case-insensitive) is in _COPPER_TYPES.
        # "copper foil" does not match, so it falls through to "dielectric".
        layer = StackLayer("F.Cu", "copper foil", 0.035)
        assert layer.kind == "dielectric"


class TestStackLayerDirty:
    def test_initially_clean(self):
        layer = StackLayer("F.Cu", "copper", 0.035)
        assert not layer.dirty

    def test_dirty_after_user_change(self):
        layer = StackLayer("F.Cu", "copper", 0.035)
        layer.user_mm = 0.040
        assert layer.dirty

    def test_floating_point_noise_not_dirty(self):
        layer = StackLayer("F.Cu", "copper", 0.035)
        layer.user_mm = 0.035 + 1e-15  # within 1e-12 tolerance
        assert not layer.dirty


# ---------------------------------------------------------------------------
# Stackup property methods
# ---------------------------------------------------------------------------

def _make_four_layer_stackup() -> Stackup:
    """Build a 4-layer stackup matching the test_resistance.py reference geometry:
    F.Cu 0.035 / diel 0.100 / In1.Cu 0.070 / diel 1.240 /
    In2.Cu 0.070 / diel 0.100 / B.Cu 0.035
    plus F.Mask 0.010 and B.Mask 0.010.
    """
    layers = [
        StackLayer("F.Mask", "soldermask", 0.010),
        StackLayer("F.Cu", "copper", 0.035),
        StackLayer("dielectric 1", "core", 0.100, "FR4", 4.5),
        StackLayer("In1.Cu", "copper", 0.070),
        StackLayer("dielectric 2", "core", 1.240, "FR4", 4.5),
        StackLayer("In2.Cu", "copper", 0.070),
        StackLayer("dielectric 3", "core", 0.100, "FR4", 4.5),
        StackLayer("B.Cu", "copper", 0.035),
        StackLayer("B.Mask", "soldermask", 0.010),
    ]
    return Stackup(layers, source="<test>", general_thickness=1.6)


class TestStackupCopper:
    def test_copper_returns_only_copper_layers(self):
        s = _make_four_layer_stackup()
        names = [l.name for l in s.copper]
        assert names == ["F.Cu", "In1.Cu", "In2.Cu", "B.Cu"]

    def test_copper_count(self):
        s = _make_four_layer_stackup()
        assert len(s.copper) == 4


class TestStackupCoreThickness:
    def test_excludes_mask(self):
        s = _make_four_layer_stackup()
        # copper: 0.035*2 + 0.070*2 = 0.21; dielectric: 0.100*2 + 1.240 = 1.44; total = 1.65
        expected = 2 * 0.035 + 2 * 0.070 + 0.100 + 1.240 + 0.100
        assert s.core_thickness_mm() == pytest.approx(expected)


class TestStackupGeometry:
    """Stackup.geometry() returns per-copper-layer dicts with correct z coords."""

    def setup_method(self):
        self.s = _make_four_layer_stackup()

    def test_four_entries_returned(self):
        geo = self.s.geometry()
        assert len(geo) == 4

    def test_index_top_sequential(self):
        geo = self.s.geometry()
        for i, g in enumerate(geo, start=1):
            assert g["index_top"] == i

    def test_index_bottom_reverse(self):
        geo = self.s.geometry()
        n = len(geo)
        for i, g in enumerate(geo):
            assert g["index_bottom"] == n - i

    def test_is_outer_flags(self):
        geo = self.s.geometry()
        assert geo[0]["is_outer"] is True
        assert geo[1]["is_outer"] is False
        assert geo[2]["is_outer"] is False
        assert geo[3]["is_outer"] is True

    def test_no_plating_finished_equals_foil(self):
        geo = self.s.geometry(plating_um=0.0, outer_adds=False)
        for g in geo:
            assert g["finished_mm"] == pytest.approx(g["foil_mm"])

    def test_plating_outer_adds_increases_outer_finished(self):
        geo_on = self.s.geometry(plating_um=25.0, outer_adds=True)
        geo_off = self.s.geometry(plating_um=25.0, outer_adds=False)
        assert geo_on[0]["finished_mm"] > geo_off[0]["finished_mm"]
        assert geo_on[3]["finished_mm"] > geo_off[3]["finished_mm"]
        assert geo_on[1]["finished_mm"] == pytest.approx(geo_off[1]["finished_mm"])
        assert geo_on[2]["finished_mm"] == pytest.approx(geo_off[2]["finished_mm"])

    def test_plating_adds_25um(self):
        geo = self.s.geometry(plating_um=25.0, outer_adds=True)
        assert geo[0]["finished_mm"] == pytest.approx(0.060)
        assert geo[3]["finished_mm"] == pytest.approx(0.060)

    def test_z_ctr_is_midpoint(self):
        geo = self.s.geometry()
        for g in geo:
            assert g["z_ctr_mm"] == pytest.approx(g["z_top_mm"] + g["finished_mm"] / 2.0)

    def test_oz_conversion(self):
        geo = self.s.geometry()
        for g in geo:
            assert g["oz"] == pytest.approx(g["finished_mm"] * 1000.0 / OZ_TO_UM)

    def test_layers_non_overlapping(self):
        """No two copper layers should share z space."""
        geo = self.s.geometry()
        for i in range(len(geo) - 1):
            top_bot = geo[i]["z_top_mm"] + geo[i]["finished_mm"]
            next_top = geo[i + 1]["z_top_mm"]
            assert next_top >= top_bot - 1e-12

    def test_fcu_z_top_no_plating(self):
        """F.Cu z_top_mm == 0.0 when mask is excluded from z-walk (mask not copper/dielectric)."""
        geo = self.s.geometry(plating_um=0.0, outer_adds=False)
        assert geo[0]["z_top_mm"] == pytest.approx(0.0)


class TestStackupGeometryOuter:
    """D8: outer copper grows upward (F.Cu) / downward (B.Cu) with outer_adds."""

    def test_fcu_z_top_shifts_up_with_plating(self):
        s = _make_four_layer_stackup()
        geo_off = s.geometry(plating_um=25.0, outer_adds=False)
        geo_on = s.geometry(plating_um=25.0, outer_adds=True)
        assert geo_on[0]["z_top_mm"] < geo_off[0]["z_top_mm"]

    def test_bcu_z_top_unchanged_with_plating(self):
        """B.Cu grows downward, so z_top_mm stays at foil top."""
        s = _make_four_layer_stackup()
        geo_off = s.geometry(plating_um=25.0, outer_adds=False)
        geo_on = s.geometry(plating_um=25.0, outer_adds=True)
        assert geo_on[3]["z_top_mm"] == pytest.approx(geo_off[3]["z_top_mm"])


# ---------------------------------------------------------------------------
# load_stackup — positive (synthetic tmp_path fixtures)
# ---------------------------------------------------------------------------

class TestLoadStackupPositive:
    def test_returns_stackup_instance(self, tmp_path):
        path = _write(tmp_path, "board.kicad_pcb", _FOUR_LAYER_PCB)
        s = load_stackup(path)
        assert isinstance(s, Stackup)

    def test_source_is_path(self, tmp_path):
        path = _write(tmp_path, "board.kicad_pcb", _FOUR_LAYER_PCB)
        s = load_stackup(path)
        assert s.source == path

    def test_general_thickness_read(self, tmp_path):
        path = _write(tmp_path, "board.kicad_pcb", _FOUR_LAYER_PCB)
        s = load_stackup(path)
        assert s.general_thickness == pytest.approx(1.6)

    def test_copper_layers_count(self, tmp_path):
        path = _write(tmp_path, "board.kicad_pcb", _FOUR_LAYER_PCB)
        s = load_stackup(path)
        assert len(s.copper) == 4

    def test_copper_layer_names(self, tmp_path):
        path = _write(tmp_path, "board.kicad_pcb", _FOUR_LAYER_PCB)
        s = load_stackup(path)
        names = [l.name for l in s.copper]
        assert names == ["F.Cu", "In1.Cu", "In2.Cu", "B.Cu"]

    def test_copper_thickness_read(self, tmp_path):
        path = _write(tmp_path, "board.kicad_pcb", _FOUR_LAYER_PCB)
        s = load_stackup(path)
        fcu = s.copper[0]
        assert fcu.base_mm == pytest.approx(0.035)
        assert fcu.user_mm == pytest.approx(0.035)

    def test_inner_layers_thickness(self, tmp_path):
        path = _write(tmp_path, "board.kicad_pcb", _FOUR_LAYER_PCB)
        s = load_stackup(path)
        assert s.copper[1].base_mm == pytest.approx(0.07)
        assert s.copper[2].base_mm == pytest.approx(0.07)

    def test_dielectric_material_read(self, tmp_path):
        path = _write(tmp_path, "board.kicad_pcb", _FOUR_LAYER_PCB)
        s = load_stackup(path)
        diel = [l for l in s.layers if l.kind == "dielectric"]
        assert all(l.material == "FR4" for l in diel)

    def test_dielectric_epsilon_r_read(self, tmp_path):
        path = _write(tmp_path, "board.kicad_pcb", _FOUR_LAYER_PCB)
        s = load_stackup(path)
        diel = [l for l in s.layers if l.kind == "dielectric"]
        assert all(l.epsilon_r == pytest.approx(4.5) for l in diel)

    def test_not_estimated(self, tmp_path):
        path = _write(tmp_path, "board.kicad_pcb", _FOUR_LAYER_PCB)
        s = load_stackup(path)
        assert s.estimated is False

    def test_single_copper_layer(self, tmp_path):
        path = _write(tmp_path, "single.kicad_pcb", _SINGLE_COPPER_PCB)
        s = load_stackup(path)
        assert len(s.copper) == 1
        assert s.copper[0].name == "F.Cu"


# ---------------------------------------------------------------------------
# load_stackup — failure (synthetic tmp_path fixtures)
# ---------------------------------------------------------------------------

class TestLoadStackupFailure:
    def test_no_stackup_block_raises_value_error(self, tmp_path):
        path = _write(tmp_path, "no_stackup.kicad_pcb", _NO_STACKUP_PCB)
        with pytest.raises(ValueError, match="no \\(stackup\\) block"):
            load_stackup(path)

    def test_no_stackup_error_message_exact(self, tmp_path):
        """Error message must match the v0.13 text exactly (hyphen, not em dash)."""
        path = _write(tmp_path, "no_stackup.kicad_pcb", _NO_STACKUP_PCB)
        with pytest.raises(ValueError) as exc_info:
            load_stackup(path)
        msg = str(exc_info.value)
        assert " - " in msg, f"Expected hyphen in message, got: {msg!r}"
        assert "open Board Setup" in msg

    def test_wrong_root_raises_value_error(self, tmp_path):
        path = _write(tmp_path, "not_a_pcb.kicad_pcb", _NOT_A_PCB)
        with pytest.raises(ValueError, match="not a .kicad_pcb"):
            load_stackup(path)

    def test_missing_file_raises_oserror(self):
        with pytest.raises(OSError):
            load_stackup("/nonexistent/path/board.kicad_pcb")


# ---------------------------------------------------------------------------
# manual_stackup
# ---------------------------------------------------------------------------

class TestManualStackup:
    def test_estimated_true(self):
        s = manual_stackup()
        assert s.estimated is True

    def test_source_manual(self):
        s = manual_stackup()
        assert s.source == "<manual>"

    def test_default_four_copper(self):
        s = manual_stackup()
        assert len(s.copper) == 4

    def test_layer_names(self):
        s = manual_stackup(n_copper=4)
        names = [l.name for l in s.copper]
        assert names[0] == "F.Cu"
        assert names[-1] == "B.Cu"
        assert names[1] == "In1.Cu"
        assert names[2] == "In2.Cu"

    def test_two_layer_board(self):
        s = manual_stackup(n_copper=2)
        cu = s.copper
        assert len(cu) == 2
        assert cu[0].name == "F.Cu"
        assert cu[1].name == "B.Cu"

    def test_single_layer_board(self):
        s = manual_stackup(n_copper=1)
        assert len(s.copper) == 1
        assert s.copper[0].name == "F.Cu"

    def test_single_layer_named_fcu(self):
        """Single-layer board: only layer is F.Cu, not B.Cu.
        v0.13 had: nm = 'F.Cu' if i==0 else ('B.Cu' if i==n_copper-1 else ...).
        For n_copper=1, i==0 and i==n_copper-1 both, so nm='F.Cu' wins."""
        s = manual_stackup(n_copper=1)
        assert s.copper[0].name == "F.Cu"

    def test_outer_oz_thickness(self):
        s = manual_stackup(n_copper=4, outer_oz=2.0)
        expected_mm = 2.0 * OZ_TO_UM / 1000.0
        assert s.copper[0].base_mm == pytest.approx(expected_mm)
        assert s.copper[3].base_mm == pytest.approx(expected_mm)

    def test_inner_oz_thickness(self):
        s = manual_stackup(n_copper=4, inner_oz=0.5)
        expected_mm = 0.5 * OZ_TO_UM / 1000.0
        assert s.copper[1].base_mm == pytest.approx(expected_mm)

    def test_dielectric_fills_remaining_thickness(self):
        """core_thickness_mm() must be close to board_mm (within floating-point)."""
        board_mm = 1.6
        s = manual_stackup(n_copper=4, board_mm=board_mm)
        assert s.core_thickness_mm() == pytest.approx(board_mm, rel=1e-3)

    def test_dielectric_minimum_enforced(self):
        """board_mm too small for copper doesn't produce zero-or-negative dielectric."""
        s = manual_stackup(n_copper=4, board_mm=0.001)
        diel = [l for l in s.layers if l.kind == "dielectric"]
        for d in diel:
            assert d.base_mm >= 1e-4

    def test_odd_layer_count(self):
        s = manual_stackup(n_copper=3)
        cu = s.copper
        assert len(cu) == 3
        assert cu[0].name == "F.Cu"
        assert cu[2].name == "B.Cu"
        assert cu[1].name == "In1.Cu"

    # Boundary: n_copper validation (deliberate deviation from v0.13 which
    # silently produced an empty stackup for n_copper < 1)
    def test_zero_copper_raises_value_error(self):
        with pytest.raises(ValueError, match="n_copper must be >= 1"):
            manual_stackup(n_copper=0)

    def test_negative_copper_raises_value_error(self):
        with pytest.raises(ValueError, match="n_copper must be >= 1"):
            manual_stackup(n_copper=-1)


# ---------------------------------------------------------------------------
# Stackup parity regression: load_stackup vs. v0.13 on the reference board
# ---------------------------------------------------------------------------

class TestStackupParity:
    """Stackup.geometry() matches v0.13 pcb_trace_resistance.py geometry output.

    This is the STACKUP PARITY RECORD required by Session 05.  The reference
    values were produced by running the original v0.13 parse_sexpr + Stackup
    classes (which are byte-identical to the extracted versions modulo the
    deliberate n_copper and error-message deviations) against the IP5385
    reference board.

    Reference board stackup (all copper layers 0.035mm foil):
        F.Cu  0.035mm copper
        In1.Cu 0.035mm copper
        In2.Cu 0.035mm copper
        B.Cu  0.035mm copper
    with plating_um=25.0, outer_adds=True.
    """

    @pytest.fixture(scope="class")
    @classmethod
    def stackup(cls):
        if not os.path.exists(REFERENCE_BOARD):
            pytest.skip("Reference board not available")
        return load_stackup(REFERENCE_BOARD)

    def test_four_copper_layers(self, stackup):
        assert len(stackup.copper) == 4

    def test_general_thickness(self, stackup):
        assert stackup.general_thickness == pytest.approx(1.6)

    def test_copper_names(self, stackup):
        names = [l.name for l in stackup.copper]
        assert names == ["F.Cu", "In1.Cu", "In2.Cu", "B.Cu"]

    def test_fcu_foil_35um(self, stackup):
        assert stackup.copper[0].base_mm == pytest.approx(0.035)

    def test_inner_foil_35um(self, stackup):
        """The reference IP5385 board uses 0.035mm for all layers."""
        assert stackup.copper[1].base_mm == pytest.approx(0.035)
        assert stackup.copper[2].base_mm == pytest.approx(0.035)

    def test_geometry_fcu_finished_mm_with_25um_plating(self, stackup):
        geo = stackup.geometry(plating_um=25.0, outer_adds=True)
        assert geo[0]["finished_mm"] == pytest.approx(0.060)

    def test_geometry_bcu_finished_mm_with_25um_plating(self, stackup):
        geo = stackup.geometry(plating_um=25.0, outer_adds=True)
        assert geo[3]["finished_mm"] == pytest.approx(0.060)

    def test_geometry_inner_finished_equals_foil(self, stackup):
        geo = stackup.geometry(plating_um=25.0, outer_adds=True)
        assert geo[1]["finished_mm"] == pytest.approx(0.035)
        assert geo[2]["finished_mm"] == pytest.approx(0.035)

    def test_geometry_fcu_z_ctr_with_25um_plating(self, stackup):
        """F.Cu centroid with 25um plating, outer_adds=True.

        F.Cu z_top = -(0.025mm plating) = -0.025; finished=0.060;
        z_ctr = -0.025 + 0.060/2 = 0.005.
        (Mask layer 0.010mm is skipped in the z-walk, kind='mask'.)
        """
        geo = stackup.geometry(plating_um=25.0, outer_adds=True)
        assert geo[0]["z_ctr_mm"] == pytest.approx(0.005)

    def test_geometry_no_plating_z_top_zero(self, stackup):
        """F.Cu z_top_mm = 0 when no plating and outer_adds=False."""
        geo = stackup.geometry(plating_um=0.0, outer_adds=False)
        assert geo[0]["z_top_mm"] == pytest.approx(0.0)

    def test_geometry_index_ordering(self, stackup):
        geo = stackup.geometry()
        assert geo[0]["index_top"] == 1
        assert geo[0]["index_bottom"] == 4
        assert geo[3]["index_top"] == 4
        assert geo[3]["index_bottom"] == 1

    def test_source_is_board_path(self, stackup):
        assert stackup.source == REFERENCE_BOARD
