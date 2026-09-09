# v0.1
"""Tests for pathminer.kicad.board / pathminer.kicad.source / pathminer.models.board.

Session 06 — BoardSource and file-backed board model.
Punch-list responsibility: ARCH-003 (closure owner); contributes a
resolution slice to DATA-004.

Covers:
  - pathminer.kicad.board.parse_board: nets, tracks (line + arc, true
    length), vias, pads, pours, zone_nets, stackup, mid-run via split
    diagnostics, stackup-absent fallback, malformed-file failure.
  - pathminer.kicad.source.FileBoardSource: BoardSource protocol
    conformance, per-net filtering, stable REF.PAD lookup (`pad`),
    terminal dedupe/aliasing (`terminals`), and drift diagnostics
    (`check_drift` / `resolve`, `PadNotFoundError`, `NetDriftError`).
  - pathminer.models.board: `ref_pad_name` naming rule, dataclass
    equality/immutability.
  - Real-board regression: the canonical IP5385 reference board parses
    through FileBoardSource and reproduces known REF.PAD/net/alias facts.

Synthetic fixtures live under tests/fixtures/kicad/ (in this session's
owned write scope, unlike the tmp_path-only fixtures of Session 05):
  - board_min.kicad_pcb       — positive-path board: 2 nets, 2 footprints
                                 (one with an aliased REF.PAD), a track
                                 split by a mid-run via, an arc, and a
                                 filled zone (pour).
  - board_no_stackup.kicad_pcb — board_min with the (setup (stackup ...))
                                 block removed, to exercise the manual
                                 stackup fallback.
  - board_rerouted.kicad_pcb  — board_min with net 1 renamed
                                 "SIG_A" -> "SIG_A_MOVED", REF.PAD
                                 identities unchanged, to exercise net
                                 drift.
"""

from __future__ import annotations

import os

import pytest

from pathminer.kicad.board import ParsedBoard, parse_board
from pathminer.kicad.source import FileBoardSource
from pathminer.models.board import (
    BoardSource,
    Net,
    NetDriftError,
    PadDrift,
    PadNotFoundError,
    Pour,
    Terminal,
    TerminalAlias,
    ref_pad_name,
)

FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures", "kicad")
BOARD_MIN = os.path.join(FIXTURES, "board_min.kicad_pcb")
BOARD_NO_STACKUP = os.path.join(FIXTURES, "board_no_stackup.kicad_pcb")
BOARD_REROUTED = os.path.join(FIXTURES, "board_rerouted.kicad_pcb")

REFERENCE_BOARD = os.path.normpath(
    os.path.join(
        os.path.dirname(__file__),
        "..",
        "ai_reference/kicad_project_example/"
        "Ref_PowerBank_injoinic_IP5385_v0.8.kicad_pcb",
    )
)


# ---------------------------------------------------------------------------
# ref_pad_name
# ---------------------------------------------------------------------------


class TestRefPadName:
    def test_prefers_pin_function(self):
        assert ref_pad_name("Q3", "1", "S") == "Q3.S"

    def test_falls_back_to_pad_name(self):
        assert ref_pad_name("U9", "5", "") == "U9.5"

    def test_no_ref_uses_placeholder(self):
        assert ref_pad_name("", "7", "") == "pad 7"

    def test_no_ref_ignores_pin_function(self):
        # Matches v0.13: `ref and fn` requires a truthy ref first.
        assert ref_pad_name("", "7", "S") == "pad 7"


# ---------------------------------------------------------------------------
# parse_board — positive path
# ---------------------------------------------------------------------------


class TestParseBoardPositive:
    @classmethod
    @pytest.fixture(scope="class")
    def parsed(cls) -> ParsedBoard:
        return parse_board(BOARD_MIN)

    def test_returns_parsed_board(self, parsed):
        assert isinstance(parsed, ParsedBoard)
        assert parsed.path == BOARD_MIN

    def test_net_names(self, parsed):
        assert parsed.net_names == {0: "", 1: "SIG_A", 2: "GND"}

    def test_line_track_true_length(self, parsed):
        lines = [t for t in parsed.tracks if t.shape == "line"]
        # The 20mm run from (10,10)->(30,10) is split at the via at (20,10).
        assert len(lines) == 2
        assert lines[0].start == (10.0, 10.0)
        assert lines[0].end == (20.0, 10.0)
        assert lines[0].length_mm == pytest.approx(10.0)
        assert lines[1].end == (30.0, 10.0)
        assert lines[1].length_mm == pytest.approx(10.0)
        assert all(t.net == 1 and t.layer == "F.Cu" for t in lines)

    def test_arc_true_length_not_chord(self, parsed):
        arcs = [t for t in parsed.tracks if t.shape == "arc"]
        assert len(arcs) == 1
        arc = arcs[0]
        chord = ((arc.end[0] - arc.start[0]) ** 2 + (arc.end[1] - arc.start[1]) ** 2) ** 0.5
        assert arc.length_mm > chord  # true arc length, not the straight chord

    def test_via(self, parsed):
        assert len(parsed.vias) == 1
        via = parsed.vias[0]
        assert via.at == (20.0, 10.0)
        assert via.via_type == "through"
        assert via.declared_layers == ("F.Cu", "B.Cu")

    def test_pads(self, parsed):
        assert len(parsed.pads) == 4
        u1_pads = [p for p in parsed.pads if p.ref == "U1"]
        assert {p.net for p in u1_pads} == {1, 2}

    def test_pours(self, parsed):
        assert set(parsed.pours) == {2}
        pour = parsed.pours[2]
        assert isinstance(pour, Pour)
        assert pour.layers() == ["F.Cu"]
        assert len(pour.fills["F.Cu"]) == 4

    def test_zone_nets(self, parsed):
        assert parsed.zone_nets == {2}

    def test_stackup_from_file(self, parsed):
        assert parsed.stackup.estimated is False
        assert [l.name for l in parsed.stackup.copper] == ["F.Cu", "B.Cu"]

    def test_split_note_recorded(self, parsed):
        assert any("split at 1 mid-run via" in n for n in parsed.notes)


# ---------------------------------------------------------------------------
# parse_board — boundary / failure
# ---------------------------------------------------------------------------


class TestParseBoardFailure:
    def test_missing_file_raises_oserror(self):
        with pytest.raises(OSError):
            parse_board("/nonexistent/path/board.kicad_pcb")

    def test_wrong_root_raises_value_error(self, tmp_path):
        bogus = tmp_path / "not_a_board.kicad_pcb"
        bogus.write_text('(kicad_sch (version 1))\n', encoding="utf-8")
        with pytest.raises(ValueError, match="not a .kicad_pcb file"):
            parse_board(str(bogus))

    def test_missing_stackup_falls_back_to_manual(self):
        parsed = parse_board(BOARD_NO_STACKUP)
        assert parsed.stackup.estimated is True
        assert any("estimated manual stackup" in n for n in parsed.notes)

    def test_missing_stackup_still_parses_geometry(self):
        # A board without a (stackup) block must still yield usable board
        # geometry -- only the stackup falls back (S8.2).
        parsed = parse_board(BOARD_NO_STACKUP)
        assert parsed.net_names == {0: "", 1: "SIG_A", 2: "GND"}
        assert len(parsed.pads) == 4


# ---------------------------------------------------------------------------
# FileBoardSource — BoardSource protocol conformance
# ---------------------------------------------------------------------------


class TestFileBoardSourceProtocol:
    @classmethod
    @pytest.fixture(scope="class")
    def source(cls) -> FileBoardSource:
        return FileBoardSource(BOARD_MIN)

    def test_isinstance_of_board_source_protocol(self, source):
        # BoardSource is a runtime_checkable Protocol (ARCH-003 Done-when:
        # "the same analysis accepts either adapter without branching").
        assert isinstance(source, BoardSource)

    def test_stackup_property(self, source):
        assert [l.name for l in source.stackup.copper] == ["F.Cu", "B.Cu"]

    def test_nets(self, source):
        assert source.nets() == [Net(0, ""), Net(1, "SIG_A"), Net(2, "GND")]

    def test_net_name_known_and_unknown(self, source):
        assert source.net_name(1) == "SIG_A"
        assert source.net_name(99) == "<net 99>"

    def test_tracks_filter_by_net(self, source):
        assert len(source.tracks()) == 3  # 2 line halves + 1 arc
        assert all(t.net == 1 for t in source.tracks(net=1))
        assert source.tracks(net=2) == []

    def test_vias_filter_by_net(self, source):
        assert len(source.vias(net=1)) == 1
        assert source.vias(net=2) == []

    def test_pads_filter_by_net(self, source):
        assert len(source.pads(net=1)) == 3  # U1.1, U2.1, U2.2
        assert len(source.pads(net=2)) == 1  # U1.2

    def test_pours_filter_by_net(self, source):
        assert set(source.pours()) == {2}
        assert source.pours(net=2)[2].net == 2
        assert source.pours(net=1) == {}


# ---------------------------------------------------------------------------
# FileBoardSource — stable REF.PAD lookup and terminal dedupe
# ---------------------------------------------------------------------------


class TestStableTerminalLookup:
    @classmethod
    @pytest.fixture(scope="class")
    def source(cls) -> FileBoardSource:
        return FileBoardSource(BOARD_MIN)

    def test_pad_by_ref_pad_name(self, source):
        t = source.pad("U1.1")
        assert isinstance(t, Terminal)
        assert t.net == 1
        assert t.point == (10.0, 10.0)
        assert t.aliases == ()

    def test_pad_pin_function_form(self, source):
        # Q3.S-style lookup: pin function wins over bare pad name.
        t = source.pad("U2.S")
        assert t.ref == "U2"
        assert t.pin_function == "S"

    def test_pad_collapses_repeated_pin_function_into_aliases(self, source):
        # U2 has two physical pads (names "1" and "2") both pinfunction
        # "S" on the same net -- one electrical terminal, one alias.
        t = source.pad("U2.S")
        assert len(t.aliases) == 1
        assert t.aliases[0] == TerminalAlias(pad_name="2", point=(32.0, 10.0))

    def test_pad_not_found_raises_named_error(self, source):
        with pytest.raises(PadNotFoundError):
            source.pad("U9.99")

    def test_pad_not_found_is_a_key_error(self, source):
        # PadNotFoundError doubles as KeyError for callers using dict-style
        # exception handling around board lookups.
        with pytest.raises(KeyError):
            source.pad("nope")

    def test_terminals_dedupe_true_by_default(self, source):
        terms = source.terminals(net=1)
        names = {t.ref_pad for t in terms}
        assert names == {"U1.1", "U2.S"}

    def test_terminals_dedupe_false_returns_one_row_per_pad(self, source):
        terms = source.terminals(net=1, dedupe=False)
        assert len(terms) == 3
        assert all(t.aliases == () for t in terms)

    def test_terminals_unknown_net_is_empty(self, source):
        assert source.terminals(net=999) == []


# ---------------------------------------------------------------------------
# FileBoardSource — drift diagnostics (S12.3, DATA-004 resolution slice)
# ---------------------------------------------------------------------------


class TestDriftDiagnostics:
    def test_check_drift_no_drift(self):
        source = FileBoardSource(BOARD_MIN)
        drift = source.check_drift("U1.1", "SIG_A")
        assert drift == PadDrift("U1.1", "SIG_A", "SIG_A", False)

    def test_check_drift_detects_renamed_net(self):
        source = FileBoardSource(BOARD_REROUTED)
        drift = source.check_drift("U1.1", "SIG_A")
        assert drift.drifted is True
        assert drift.current_net == "SIG_A_MOVED"

    def test_check_drift_missing_pad_raises_pad_not_found(self):
        source = FileBoardSource(BOARD_MIN)
        with pytest.raises(PadNotFoundError):
            source.check_drift("U9.99", "SIG_A")

    def test_resolve_without_expected_net_just_looks_up(self):
        source = FileBoardSource(BOARD_MIN)
        assert source.resolve("U1.1") == source.pad("U1.1")

    def test_resolve_matching_net_succeeds(self):
        source = FileBoardSource(BOARD_MIN)
        assert source.resolve("U1.1", expected_net="SIG_A").ref_pad == "U1.1"

    def test_resolve_drifted_net_raises_named_error(self):
        source = FileBoardSource(BOARD_REROUTED)
        with pytest.raises(NetDriftError) as excinfo:
            source.resolve("U1.1", expected_net="SIG_A")
        assert excinfo.value.drift.ref_pad == "U1.1"
        assert excinfo.value.drift.expected_net == "SIG_A"
        assert excinfo.value.drift.current_net == "SIG_A_MOVED"

    def test_rerouted_board_same_ref_pad_still_resolves_geometry(self):
        # ARCH-003 Done-when (via DATA-004): "a rerouted board resolves the
        # same paths or produces a named drift error." Here: same REF.PAD
        # still finds the same physical terminal even though the net name
        # changed -- the drift is reported, not silently swallowed, and
        # is not a broken-identity (PadNotFoundError) failure.
        before = FileBoardSource(BOARD_MIN).pad("U1.1")
        after = FileBoardSource(BOARD_REROUTED).pad("U1.1")
        assert before.point == after.point
        assert before.ref == after.ref == "U1"


# ---------------------------------------------------------------------------
# Real-board regression (IP5385 canonical parity fixture)
# ---------------------------------------------------------------------------


class TestRealBoardRegression:
    @classmethod
    @pytest.fixture(scope="class")
    def source(cls) -> FileBoardSource:
        return FileBoardSource(REFERENCE_BOARD)

    def test_parses_without_error(self, source):
        assert isinstance(source, BoardSource)

    def test_stackup_is_four_layer_and_not_estimated(self, source):
        assert source.stackup.estimated is False
        assert [l.name for l in source.stackup.copper] == [
            "F.Cu",
            "In1.Cu",
            "In2.Cu",
            "B.Cu",
        ]

    def test_known_terminal_resolves(self, source):
        # C53 has no pinfunction: REF.PAD falls back to the bare pad name.
        t = source.pad("C53.1")
        assert t.net == 33
        assert t.aliases == ()

    def test_known_terminal_with_pinfunction_and_aliases(self, source):
        # U9 (SQJ409EP-T2 MOSFET) has three physical "S" (source) pads
        # collapsed into one REF.PAD terminal (S7.1 collapsed-terminal
        # example).
        t = source.pad("U9.S")
        assert t.net == 94
        assert t.pin_function == "S"
        assert len(t.aliases) >= 1

    def test_unknown_ref_pad_raises_named_error(self, source):
        with pytest.raises(PadNotFoundError):
            source.pad("ZZ999.1")

    def test_has_pours_from_filled_zones(self, source):
        assert len(source.pours()) > 0

    def test_net_name_matches_declared_net(self, source):
        assert source.net_name(3) == "GNDREF"
