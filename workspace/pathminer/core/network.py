# v0.1
"""pathminer.core.network — the common typed resistor network (ARCH-004).

Session 07 (ARCH-004 closure owner). This module defines the single network
type that every resistance builder emits and the solver consumes:

    * :class:`Node`          — a hashable node key (alias for ``Hashable``).
    * :class:`Provenance`    — where an edge's resistance came from and the
                               assumptions behind it (project specification
                               S7.2 / DATA-007).
    * :class:`Edge`          — one priced resistor with its kind and provenance.
    * :class:`ResistorNetwork` — nodes, edges, equipotential merges, and a
                               two-terminal solve.
    * :class:`TwoTerminalResult` — the solver-result record.

ARCH-004 Done-when: "point-to-point, ladder, and mesh builders all emit the
same network type." The three builders in ``pathminer.analysis.builders`` each
return a :class:`ResistorNetwork`; the equality of that return type is what
closes ARCH-004.

Relationship to the solver (Session 04)
---------------------------------------
``pathminer.core.solver`` already consolidates the dense / pure-Python-CG /
SciPy backends behind ``two_terminal_resistance`` and consumes a backend-
neutral edge list ``[(u, v, r), ...]``. Its docstring names *this* layer as the
one responsible for building those edge lists "from an adjacency map, merging
equipotential groups, pricing edges." :class:`ResistorNetwork` is exactly that:
builders price edges (via ``pathminer.core.resistance``) and record physical
copper ties as :meth:`~ResistorNetwork.merge` operations, and
:meth:`~ResistorNetwork.edge_list` collapses each merged group to a single node
*before* the solve.

Merging rather than tie-resistors is deliberate and preserves v0.13 numerical
behavior: v0.13's ``build_graph_pour`` unions physically-continuous copper into
one node ("a tie is the same physical copper, so merge the nodes rather than
joining them with a near-zero resistor, which would wreck the solver's
conditioning"). This layer keeps that contract.

Layer contract (ARCH-002): pure mathematics — no KiCad, Qt, wx, or file I/O,
and no upward pathminer imports. Only ``pathminer.core`` is imported.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Hashable, List, Mapping, Optional, Sequence, Set, Tuple

from .solver import DENSE_NODE_LIMIT, HAVE_SCIPY, two_terminal_resistance

__all__ = [
    "Node",
    "Provenance",
    "Edge",
    "TwoTerminalResult",
    "ResistorNetwork",
]


# A node key is any hashable value. Builders use ints for point-to-point series
# chains and descriptive tuples for pour strips (``("pour", net, layer, u)``)
# and mesh cells (``(layer, i, j)``) — matching v0.13's node naming so behavior
# stays auditable against the baseline.
Node = Hashable


# ---------------------------------------------------------------------------
# Provenance and edges
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Provenance:
    """Where one edge's resistance came from and the assumptions behind it.

    Project specification S7.2 requires every edge to "retain geometry and
    provenance sufficient to report its resistance/impedance, current, voltage
    drop, loss, and source assumptions." DATA-007 enumerates the *origin*
    categories a value may carry (board-derived, project default,
    library-derived, user override, run override); this session's builders emit
    board-derived geometry, so ``origin`` defaults to ``"board-derived"``.

    ``model`` names the builder that emitted the edge (``"point_to_point"``,
    ``"ladder"``, ``"mesh"``) and ``detail`` carries the geometry used to price
    it (layer, length, width, via span, barrel length/area, …). ``detail`` is a
    plain mapping so a report can render the effective value and its origin
    without re-deriving anything.
    """

    origin: str = "board-derived"
    model: str = ""
    detail: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Edge:
    """One priced resistor between two node keys.

    ``resistance`` is in ohms and must be finite and positive for a real edge;
    validation of that is the solver's single responsibility (see
    :meth:`ResistorNetwork.edge_list`), so error messages stay identical across
    every backend. ``kind`` is a short tag (``"trace"``, ``"via"``, ``"pour"``,
    ``"mesh"``, ``"bridge"``, …) matching the edge types in S7.2.
    """

    u: Node
    v: Node
    resistance: float
    kind: str = "resistor"
    provenance: Provenance = field(default_factory=Provenance)


@dataclass(frozen=True)
class TwoTerminalResult:
    """Result of a two-terminal solve on a :class:`ResistorNetwork`.

    Carries the scalar resistance plus enough metadata to report the solve
    (project specification S7.5: "solver backend, graph size, …"):

        ``resistance``  two-terminal resistance in ohms (``Req = V(sink)`` with
                        the source grounded and 1 A injected at the sink);
        ``source`` / ``sink``  the *canonical* node keys actually solved between
                        (after equipotential merges);
        ``backend``     the resolved backend (``"dense"``, ``"cg"``, or
                        ``"scipy"`` — ``"auto"`` is resolved to the concrete
                        choice using the same crossover as the dispatcher);
        ``node_count``  number of distinct nodes in the solved edge list;
        ``edge_count``  number of edges that survived equipotential merges.
    """

    resistance: float
    source: Node
    sink: Node
    backend: str
    node_count: int
    edge_count: int


# ---------------------------------------------------------------------------
# The network
# ---------------------------------------------------------------------------


class ResistorNetwork:
    """A resistor network of nodes, priced edges, and equipotential merges.

    Builders add edges with :meth:`add_edge` and record physically-continuous
    copper with :meth:`merge`. :meth:`edge_list` produces the backend-neutral
    ``[(u, v, r), ...]`` the solver consumes, with each merged group collapsed
    to one canonical node and any resulting self-edge dropped — exactly v0.13's
    ``build_graph_pour`` behavior. :meth:`two_terminal` runs the solve.

    ``notes`` collects advisory strings a builder wants to surface (e.g. a
    low-aspect ladder warning), and ``terminals`` maps human-readable terminal
    labels to node keys so a caller need not know a builder's internal node
    naming.
    """

    def __init__(self, name: str = "") -> None:
        self.name = name
        self._edges: List[Edge] = []
        self._parent: Dict[Node, Node] = {}
        self.notes: List[str] = []
        self.terminals: Dict[str, Node] = {}

    # -- union-find over equipotential nodes --------------------------------

    def _find(self, a: Node) -> Node:
        parent = self._parent
        parent.setdefault(a, a)
        root = a
        while parent[root] != root:
            root = parent[root]
        while parent[a] != root:          # path compression
            parent[a], a = root, parent[a]
        return root

    def canonical(self, node: Node) -> Node:
        """The representative node for *node* after all merges."""
        return self._find(node)

    def merge(self, a: Node, b: Node) -> None:
        """Declare *a* and *b* the same physical copper (one electrical node).

        Used for zone/track ties and via-covered mesh cells. Merging avoids the
        near-zero tie resistor that would wreck the solver's conditioning
        (v0.13 contract). *b* becomes the group representative.
        """
        ra, rb = self._find(a), self._find(b)
        if ra != rb:
            self._parent[ra] = rb

    # -- construction --------------------------------------------------------

    def add_edge(
        self,
        u: Node,
        v: Node,
        resistance: float,
        kind: str = "resistor",
        provenance: Optional[Provenance] = None,
    ) -> Edge:
        """Add one priced resistor and return the :class:`Edge`.

        Nodes are registered so :meth:`canonical` and :meth:`nodes` see them
        even before a solve. Resistance validity (finite, positive) is *not*
        checked here: the solver's shared ``_prepare`` is the single validator,
        so ``build → solve`` raises the same named errors as a raw edge list.
        """
        if provenance is None:
            provenance = Provenance(model=self.name)
        self._find(u)
        self._find(v)
        edge = Edge(u, v, float(resistance), kind, provenance)
        self._edges.append(edge)
        return edge

    @classmethod
    def from_edges(
        cls,
        edges: Sequence[Tuple[Node, Node, float]],
        kind: str = "resistor",
        name: str = "",
    ) -> "ResistorNetwork":
        """Build a network from a plain ``[(u, v, r), ...]`` edge list.

        Convenience for callers/tests that already hold priced edges; the
        result solves identically to passing the same list to
        ``pathminer.core.solver.two_terminal_resistance``.
        """
        net = cls(name=name)
        for u, v, r in edges:
            net.add_edge(u, v, r, kind=kind)
        return net

    # -- views ---------------------------------------------------------------

    @property
    def edges(self) -> Tuple[Edge, ...]:
        """Every added edge, in insertion order (before merges are applied)."""
        return tuple(self._edges)

    def nodes(self) -> Set[Node]:
        """The set of canonical nodes referenced by the network's edges."""
        out: Set[Node] = set()
        for e in self._edges:
            out.add(self._find(e.u))
            out.add(self._find(e.v))
        return out

    @property
    def node_count(self) -> int:
        return len(self.nodes())

    @property
    def edge_count(self) -> int:
        """Edges that survive equipotential merges (collapsed edges excluded)."""
        return sum(1 for e in self._edges if self._find(e.u) != self._find(e.v))

    def edge_list(self) -> List[Tuple[Node, Node, float]]:
        """Backend-neutral ``[(u, v, r), ...]`` with merged groups collapsed.

        Each endpoint is mapped through :meth:`canonical`; an edge whose two
        endpoints belong to the same merged group is dropped (it would be a
        self-loop). Insertion order is preserved for deterministic output.
        """
        out: List[Tuple[Node, Node, float]] = []
        for e in self._edges:
            cu, cv = self._find(e.u), self._find(e.v)
            if cu == cv:
                continue
            out.append((cu, cv, e.resistance))
        return out

    # -- solve ---------------------------------------------------------------

    def two_terminal(
        self,
        source: Node,
        sink: Node,
        backend: str = "auto",
        dense_limit: int = DENSE_NODE_LIMIT,
    ) -> TwoTerminalResult:
        """Two-terminal resistance between *source* and *sink*.

        *source* and *sink* are mapped through :meth:`canonical` first, so a
        caller may pass any pre-merge node key (e.g. a tie's external node)
        and still address the right electrical node. Delegates the numerics to
        ``pathminer.core.solver.two_terminal_resistance`` — every backend
        validates identically and agrees on the same network (ARCH-006).
        """
        edges = self.edge_list()
        src, dst = self._find(source), self._find(sink)
        resistance = two_terminal_resistance(
            edges, src, dst, backend=backend, dense_limit=dense_limit
        )
        node_count = len({u for u, _v, _r in edges} | {v for _u, v, _r in edges})
        resolved = backend
        if resolved == "auto":
            resolved = "dense" if node_count <= dense_limit else (
                "scipy" if HAVE_SCIPY else "cg"
            )
        return TwoTerminalResult(
            resistance=resistance,
            source=src,
            sink=dst,
            backend=resolved,
            node_count=node_count,
            edge_count=len(edges),
        )
