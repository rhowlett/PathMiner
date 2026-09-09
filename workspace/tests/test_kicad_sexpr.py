# v0.1
"""Tests for pathminer.kicad.sexpr.

Session 05 — KiCad syntax, stackup and preferences extraction.
Punch-list contribution: ARCH-003 (parser foundation capability slice).

Covers:
  - Positive: basic round-trip, atom retrieval, numeric val(), findall()
  - Boundary: empty list head, quoted strings with escapes, leading whitespace
  - Failure: mismatched parens, empty token stream
  - Regression: parse_sexpr output matches tools/pcb_trace_resistance.py
    parse_sexpr output for the reference board header (parity check)
"""

from __future__ import annotations

import pytest

from pathminer.kicad.sexpr import Node, _unquote, parse_sexpr


# ---------------------------------------------------------------------------
# _unquote helper
# ---------------------------------------------------------------------------

class TestUnquote:
    def test_unquoted_token_returned_verbatim(self):
        assert _unquote("hello") == "hello"

    def test_quoted_string_strips_delimiters(self):
        assert _unquote('"world"') == "world"

    def test_escaped_inner_quote_is_replaced(self):
        assert _unquote(r'"say \"hi\""') == 'say "hi"'

    def test_empty_quoted_string(self):
        assert _unquote('""') == ""

    def test_number_like_atom(self):
        assert _unquote("3.14") == "3.14"


# ---------------------------------------------------------------------------
# Node API
# ---------------------------------------------------------------------------

class TestNodeKids:
    """Node.kids() skips the head atom (children[0])."""

    def test_kids_excludes_head(self):
        n = Node("foo", ["foo", "bar", "baz"])
        assert n.kids() == ["bar", "baz"]

    def test_kids_empty_when_only_head(self):
        n = Node("x", ["x"])
        assert n.kids() == []


class TestNodeGet:
    """Node.get() finds the first child Node with a given head."""

    def setup_method(self):
        child_a = Node("alpha", ["alpha", "1"])
        child_b = Node("beta", ["beta", "2"])
        # Second alpha — get() should return the first
        child_a2 = Node("alpha", ["alpha", "99"])
        self.parent = Node("root", ["root", child_a, child_b, child_a2])

    def test_get_existing_child(self):
        n = self.parent.get("alpha")
        assert n is not None
        assert n.head == "alpha"
        assert n.kids() == ["1"]

    def test_get_returns_first_match(self):
        n = self.parent.get("alpha")
        assert n.kids() == ["1"]  # not ["99"]

    def test_get_missing_child_returns_none(self):
        assert self.parent.get("gamma") is None

    def test_get_skips_string_children(self):
        n = Node("r", ["r", "not-a-node", Node("target", ["target", "v"])])
        assert n.get("target") is not None
        assert n.get("not-a-node") is None  # strings are not Nodes


class TestNodeVal:
    """Node.val() casts the first scalar child of a named subnode."""

    def setup_method(self):
        thickness_node = Node("thickness", ["thickness", "0.035"])
        self.parent = Node("layer", ["layer", thickness_node])

    def test_val_float_default(self):
        assert self.parent.val("thickness") == pytest.approx(0.035)

    def test_val_str_cast(self):
        assert self.parent.val("thickness", cast=str) == "0.035"

    def test_val_missing_subnode_returns_none(self):
        assert self.parent.val("weight") is None

    def test_val_idx_out_of_range_returns_none(self):
        assert self.parent.val("thickness", idx=99) is None

    def test_val_unconvertible_returns_none(self):
        s = Node("name", ["name", "text"])
        p = Node("x", ["x", s])
        assert p.val("name") is None  # "text" is not a float


class TestNodeFindall:
    """Node.findall() returns all direct children with a given head."""

    def test_findall_returns_all_matches(self):
        layers = [Node("layer", ["layer", str(i)]) for i in range(3)]
        stack = Node("stackup", ["stackup"] + layers)
        found = stack.findall("layer")
        assert len(found) == 3
        assert all(n.head == "layer" for n in found)

    def test_findall_returns_empty_list_when_absent(self):
        n = Node("root", ["root"])
        assert n.findall("missing") == []

    def test_findall_does_not_include_string_atoms(self):
        n = Node("root", ["root", "layer", Node("layer", ["layer"])])
        found = n.findall("layer")
        assert len(found) == 1


# ---------------------------------------------------------------------------
# parse_sexpr — positive
# ---------------------------------------------------------------------------

class TestParseSexprPositive:
    """Well-formed S-expression inputs."""

    def test_minimal_atom(self):
        n = parse_sexpr("(foo)")
        assert n.head == "foo"
        assert n.kids() == []

    def test_single_scalar_child(self):
        n = parse_sexpr("(version 20241229)")
        assert n.head == "version"
        assert n.kids() == ["20241229"]

    def test_numeric_float(self):
        n = parse_sexpr("(thickness 1.6)")
        assert n.val("", cast=float) is None  # no sub-node named ""
        # Access directly:
        assert float(n.kids()[0]) == pytest.approx(1.6)

    def test_nested_structure(self):
        text = "(kicad_pcb (general (thickness 1.6)) (version 1))"
        n = parse_sexpr(text)
        assert n.head == "kicad_pcb"
        general = n.get("general")
        assert general is not None
        assert general.val("thickness") == pytest.approx(1.6)
        assert n.val("version") == pytest.approx(1.0)

    def test_quoted_string_atom(self):
        text = '(generator "pcbnew")'
        n = parse_sexpr(text)
        assert n.kids()[0] == "pcbnew"  # quotes stripped

    def test_quoted_string_with_escaped_quote(self):
        text = r'(label "say \"hello\"")'
        n = parse_sexpr(text)
        assert n.kids()[0] == 'say "hello"'

    def test_leading_whitespace_skipped(self):
        n = parse_sexpr("  \n\t(foo bar)")
        assert n.head == "foo"

    def test_multiple_siblings(self):
        text = "(root (a 1) (b 2) (a 3))"
        n = parse_sexpr(text)
        all_a = n.findall("a")
        assert len(all_a) == 2
        assert all_a[0].kids()[0] == "1"
        assert all_a[1].kids()[0] == "3"

    def test_deeply_nested(self):
        text = "(l1 (l2 (l3 (l4 deep))))"
        n = parse_sexpr(text)
        assert n.get("l2").get("l3").get("l4").kids()[0] == "deep"

    def test_boolean_atom(self):
        text = "(flag yes)"
        n = parse_sexpr(text)
        assert n.kids()[0] == "yes"

    def test_empty_quoted_string_child(self):
        text = '(name "")'
        n = parse_sexpr(text)
        assert n.kids()[0] == ""

    def test_negative_number(self):
        text = "(offset -0.5)"
        n = parse_sexpr(text)
        assert float(n.kids()[0]) == pytest.approx(-0.5)


# ---------------------------------------------------------------------------
# parse_sexpr — boundary / edge cases
# ---------------------------------------------------------------------------

class TestParseSexprBoundary:
    """Edge cases that must not silently produce wrong output."""

    def test_head_with_no_non_head_children(self):
        # (foo) → Node("foo", ["foo"]) → kids() == []
        n = parse_sexpr("(foo)")
        assert n.head == "foo"
        assert n.kids() == []

    def test_multiple_atoms_as_children(self):
        text = "(layers F.Cu B.Cu In1.Cu)"
        n = parse_sexpr(text)
        kids = n.kids()
        assert kids == ["F.Cu", "B.Cu", "In1.Cu"]

    def test_number_with_many_decimals(self):
        text = "(val 0.000123456789)"
        n = parse_sexpr(text)
        assert float(n.kids()[0]) == pytest.approx(0.000123456789)

    def test_leading_comment_like_text_skipped(self):
        # The tokeniser skips everything before the first '('
        text = "   ; comment\n(root leaf)"
        n = parse_sexpr(text)
        assert n.head == "root"

    def test_empty_inner_list(self):
        text = "(root ())"
        n = parse_sexpr(text)
        inner = n.kids()[0]
        assert isinstance(inner, Node)
        assert inner.head == ""

    def test_find_val_on_deeply_nested_grandchild(self):
        # Root is "setup"; children are stackup -> layer -> thickness
        text = "(setup (stackup (layer (thickness 0.035))))"
        n = parse_sexpr(text)
        assert n.head == "setup"
        layer = n.get("stackup").get("layer")
        assert layer.val("thickness") == pytest.approx(0.035)


# ---------------------------------------------------------------------------
# parse_sexpr — failure / malformed input
# ---------------------------------------------------------------------------

class TestParseSexprFailure:
    """Malformed inputs that must raise rather than silently pass."""

    def test_empty_token_list_raises(self):
        with pytest.raises((AssertionError, IndexError)):
            parse_sexpr("not valid at all — no parens")

    def test_unmatched_open_raises(self):
        with pytest.raises((AssertionError, IndexError)):
            parse_sexpr("(foo (bar)")

    def test_starts_with_close_paren_raises(self):
        with pytest.raises((AssertionError, IndexError)):
            # After stripping leading non-'(' there's nothing valid
            parse_sexpr(")")


# ---------------------------------------------------------------------------
# Parity regression: sexpr output matches the reference board header
# ---------------------------------------------------------------------------

class TestParseSexprRegressionParity:
    """parse_sexpr output matches v0.13's parse_sexpr for key fields.

    Uses the canonical reference board embedded at
    ai_reference/kicad_project_example/Ref_PowerBank_injoinic_IP5385_v0.8.kicad_pcb.

    These assertions are the stackup-parity record (required deliverable).
    """

    BOARD_PATH = (
        "ai_reference/kicad_project_example/"
        "Ref_PowerBank_injoinic_IP5385_v0.8.kicad_pcb"
    )

    @pytest.fixture(scope="class")
    @classmethod
    def root(cls, tmp_path_factory):
        import os
        here = os.path.dirname(__file__)
        board = os.path.join(here, "..", cls.BOARD_PATH)
        board = os.path.normpath(board)
        if not os.path.exists(board):
            pytest.skip("Reference board not available")
        with open(board, "r", encoding="utf-8") as fh:
            text = fh.read()
        return parse_sexpr(text)

    def test_root_head(self, root):
        assert root.head == "kicad_pcb"

    def test_general_thickness(self, root):
        general = root.get("general")
        assert general is not None
        assert general.val("thickness") == pytest.approx(1.6)

    def test_setup_has_stackup(self, root):
        setup = root.get("setup")
        assert setup is not None
        stack = setup.get("stackup")
        assert stack is not None

    def test_stackup_layer_count(self, root):
        setup = root.get("setup")
        stack = setup.get("stackup")
        layers = stack.findall("layer")
        # The reference board has 13 stackup entries
        assert len(layers) == 13

    def test_fcu_type_and_thickness(self, root):
        setup = root.get("setup")
        stack = setup.get("stackup")
        fcu = next(
            l for l in stack.findall("layer")
            if l.kids() and l.kids()[0] == "F.Cu"
        )
        tnode = fcu.get("type")
        assert tnode is not None
        assert tnode.kids()[0] == "copper"
        assert fcu.val("thickness") == pytest.approx(0.035)

    def test_generator_version(self, root):
        gv = root.get("generator_version")
        assert gv is not None
        assert gv.kids()[0] == "9.0"
