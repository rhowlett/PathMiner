# v0.1
"""pathminer.kicad.sexpr — minimal S-expression parser for .kicad_pcb files.

Extracted from tools/pcb_trace_resistance.py v0.13.

This module has no dependencies on pathminer.core, Qt, or wx.  It is a pure
reader; it does not write or modify S-expression data.

Public surface
--------------
Node            — tree node produced by parse_sexpr
parse_sexpr(text) -> Node
    Parse a KiCad S-expression string and return the root Node.

Grammar handled
---------------
The KiCad S-expression dialect used in .kicad_pcb, .kicad_pro and .kicad_sch
files is a Lisp-like nested list where every list starts with a head atom:

    ( kicad_pcb (version 20240108) (generator "pcbnew") ... )

Atoms are either quoted strings (with backslash-escaped inner quotes) or
unquoted tokens (numbers, identifiers, booleans).  Lists are recursively
nested.  The tokeniser regex handles the full grammar observed in KiCad 9.

Notes from KiCad 9 observations (originally documented in v0.3 source)
-----------------------------------------------------------------------
- Layer ordinals are NOT stack order (F.Cu=0, In1.Cu=4, In2.Cu=6, B.Cu=2).
  Physical order comes only from the (stackup) block's own sequence.
- KiCad 9 writes `uuid`, not `tstamp`.
- The (stackup) block is optional; absent, the caller must use manual mode.
"""

import re

# Tokeniser for the KiCad S-expression dialect.
# Groups: open-paren | close-paren | quoted-string (escaped) | bare atom
_TOK = re.compile(r'\(|\)|"(?:[^"\\]|\\.)*"|[^\s()]+')


def _unquote(t: str) -> str:
    """Strip surrounding double-quotes and unescape inner escaped quotes."""
    return t[1:-1].replace('\\"', '"') if t.startswith('"') else t


class Node:
    """A node in the parsed S-expression tree.

    Every KiCad S-expression list is represented as a Node whose *head* is
    the first atom and whose *children* list includes that head atom at
    index 0 (mirroring the raw token stream).  Use ``kids()`` to iterate
    over the remaining children and skip the duplicated head.

    Attributes
    ----------
    head : str
        The first atom of the list (e.g. ``"kicad_pcb"``, ``"layer"``).
    children : list
        All items in the list including the head atom at index 0.  Items
        are either ``str`` atoms or nested ``Node`` instances.
    """

    __slots__ = ("head", "children")

    def __init__(self, head: str, children: list) -> None:
        self.head = head
        self.children = children  # children[0] IS the head atom

    def kids(self) -> list:
        """Return children after the head atom."""
        return self.children[1:]

    def get(self, name: str) -> "Node | None":
        """Return the first direct child Node with the given head, or None."""
        for c in self.kids():
            if isinstance(c, Node) and c.head == name:
                return c
        return None

    def val(self, name: str, idx: int = 0, cast=float):
        """Return a cast scalar from the first child with the given head.

        Returns None when the child is absent, the index is out of range,
        or the value cannot be cast.
        """
        n = self.get(name)
        if n is None:
            return None
        vals = n.kids()
        if idx >= len(vals):
            return None
        try:
            return cast(vals[idx])
        except (TypeError, ValueError):
            return None

    def findall(self, name: str) -> list:
        """Return all direct child Nodes with the given head."""
        return [c for c in self.kids() if isinstance(c, Node) and c.head == name]

    def __repr__(self) -> str:  # pragma: no cover
        return f"Node({self.head!r}, {len(self.children)} children)"


def parse_sexpr(text: str) -> Node:
    """Parse a KiCad S-expression string and return the root Node.

    Parameters
    ----------
    text:
        Full text of a .kicad_pcb (or similar) file, or any well-formed
        KiCad S-expression fragment starting with ``(``.

    Returns
    -------
    Node
        The root node.  For a .kicad_pcb file this has ``head == "kicad_pcb"``.

    Raises
    ------
    AssertionError
        If the token stream does not begin with ``(`` or the S-expression is
        malformed (unmatched parentheses).
    IndexError
        If the token list is empty or exhausted before the expression closes.
    """
    toks = _TOK.findall(text)
    pos = 0

    def _parse() -> Node:
        nonlocal pos
        assert toks[pos] == "(", f"expected '(' at position {pos}, got {toks[pos]!r}"
        pos += 1
        items: list = []
        while toks[pos] != ")":
            if toks[pos] == "(":
                items.append(_parse())
            else:
                items.append(_unquote(toks[pos]))
                pos += 1
        pos += 1  # consume ')'
        head = items[0] if items and isinstance(items[0], str) else ""
        return Node(head, items)

    # Skip any leading non-'(' tokens (e.g. BOM markers)
    while pos < len(toks) and toks[pos] != "(":
        pos += 1
    return _parse()
