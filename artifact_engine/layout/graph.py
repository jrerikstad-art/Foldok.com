"""
Deterministic layered graph layout (Sugiyama-style, simplified).
Produces stable coordinates for engineering block diagrams.
"""
from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass
class GraphNode:
    id: str
    label: str
    width: float = 160.0
    height: float = 52.0
    rank: int = 0
    order: int = 0
    x: float = 0.0
    y: float = 0.0
    type: str = "component"


@dataclass
class GraphEdge:
    source: str
    target: str
    label: str = ""


@dataclass
class GraphLayoutResult:
    nodes: List[GraphNode]
    edges: List[GraphEdge]
    width: float
    height: float
    ranks: int


def _node_id(n: dict) -> Optional[str]:
    return n.get("name") or n.get("id") or None


def _endpoint_id(ref: str) -> str:
    """Strip pin suffix: 'pump.inn' → 'pump'."""
    return (ref or "").split(".")[0]


class LayeredGraphLayout:
    """
    Deterministic hierarchical layout.
    Orientation: "TB" (top-bottom) or "LR" (left-right).
    """

    def __init__(
        self,
        node_width: float = 160.0,
        node_height: float = 52.0,
        rank_sep: float = 80.0,
        node_sep: float = 40.0,
        margin: float = 40.0,
        orientation: str = "TB",
    ):
        self.node_width = node_width
        self.node_height = node_height
        self.rank_sep = rank_sep
        self.node_sep = node_sep
        self.margin = margin
        self.orientation = (orientation or "TB").upper()
        if self.orientation not in ("TB", "LR"):
            self.orientation = "TB"

    def layout(self, nodes: List[dict], edges: List[dict]) -> GraphLayoutResult:
        if not nodes:
            return GraphLayoutResult([], [], self.margin * 2, self.margin * 2, 0)

        node_map: Dict[str, GraphNode] = {}
        for n in nodes:
            nid = _node_id(n)
            if not nid or nid in node_map:
                continue
            node_map[nid] = GraphNode(
                id=nid,
                label=n.get("label") or nid,
                width=float(n.get("width") or self.node_width),
                height=float(n.get("height") or self.node_height),
                type=n.get("type") or n.get("role") or "component",
            )

        if not node_map:
            return GraphLayoutResult([], [], self.margin * 2, self.margin * 2, 0)

        graph_edges: List[GraphEdge] = []
        successors: Dict[str, List[str]] = defaultdict(list)
        predecessors: Dict[str, List[str]] = defaultdict(list)

        for e in edges or []:
            src = _endpoint_id(e.get("from") or e.get("source") or "")
            tgt = _endpoint_id(e.get("to") or e.get("target") or "")
            if src in node_map and tgt in node_map and src != tgt:
                graph_edges.append(GraphEdge(src, tgt, e.get("label") or ""))
                if tgt not in successors[src]:
                    successors[src].append(tgt)
                if src not in predecessors[tgt]:
                    predecessors[tgt].append(src)

        # Stable adjacency order
        for nid in node_map:
            successors[nid].sort()
            predecessors[nid].sort()

        ranks = self._assign_ranks(node_map, successors, predecessors)
        order = self._order_ranks(node_map, ranks, successors, predecessors)
        self._assign_coordinates(node_map, ranks, order)

        max_x = max(
            (n.x + n.width for n in node_map.values()),
            default=self.margin,
        ) + self.margin
        max_y = max(
            (n.y + n.height for n in node_map.values()),
            default=self.margin,
        ) + self.margin

        # Stable node list order: rank, order, id
        ordered_nodes = sorted(
            node_map.values(),
            key=lambda n: (n.rank, n.order, n.id),
        )

        return GraphLayoutResult(
            nodes=ordered_nodes,
            edges=graph_edges,
            width=max_x,
            height=max_y,
            ranks=(max(ranks.values()) + 1) if ranks else 0,
        )

    def _assign_ranks(
        self,
        nodes: Dict[str, GraphNode],
        successors: Dict[str, List[str]],
        predecessors: Dict[str, List[str]],
    ) -> Dict[str, int]:
        roots = sorted(nid for nid in nodes if not predecessors[nid])
        if not roots:
            roots = [sorted(nodes.keys())[0]]

        rank: Dict[str, int] = {nid: -1 for nid in nodes}
        queue: deque[str] = deque()
        for r in roots:
            rank[r] = 0
            queue.append(r)

        max_iters = len(nodes) * len(nodes) + 5
        iters = 0
        while queue and iters < max_iters:
            iters += 1
            u = queue.popleft()
            for v in successors[u]:
                candidate = rank[u] + 1
                if candidate > rank[v]:
                    rank[v] = candidate
                    queue.append(v)

        for nid in nodes:
            if rank[nid] < 0:
                rank[nid] = 0

        for nid, r in rank.items():
            nodes[nid].rank = r
        return rank

    def _order_ranks(
        self,
        nodes: Dict[str, GraphNode],
        ranks: Dict[str, int],
        successors: Dict[str, List[str]],
        predecessors: Dict[str, List[str]],
    ) -> Dict[int, List[str]]:
        max_rank = max(ranks.values()) if ranks else 0
        order: Dict[int, List[str]] = defaultdict(list)

        for nid in sorted(ranks, key=lambda x: (ranks[x], x)):
            order[ranks[nid]].append(nid)

        for _ in range(2):
            for r in range(1, max_rank + 1):
                order[r] = self._barycenter_sort(
                    order[r], order.get(r - 1, []), predecessors,
                )
            for r in range(max_rank - 1, -1, -1):
                order[r] = self._barycenter_sort(
                    order[r], order.get(r + 1, []), successors,
                )

        for r, nids in order.items():
            for i, nid in enumerate(nids):
                nodes[nid].order = i
        return order

    def _barycenter_sort(
        self,
        current: List[str],
        reference: List[str],
        links: Dict[str, List[str]],
    ) -> List[str]:
        ref_pos = {nid: i for i, nid in enumerate(reference)}
        fallback = {nid: i for i, nid in enumerate(current)}

        def key(nid: str) -> tuple:
            connected = [ref_pos[n] for n in links[nid] if n in ref_pos]
            if not connected:
                return (float(fallback[nid]), nid)
            return (sum(connected) / len(connected), nid)

        return sorted(current, key=key)

    def _assign_coordinates(
        self,
        nodes: Dict[str, GraphNode],
        ranks: Dict[str, int],
        order: Dict[int, List[str]],
    ) -> None:
        max_rank = max(ranks.values()) if ranks else 0

        for r in range(max_rank + 1):
            nids = order.get(r, [])
            if not nids:
                continue

            # Center pack: start at margin (deterministic left/top align)
            cursor = self.margin
            for nid in nids:
                node = nodes[nid]
                if self.orientation == "TB":
                    node.x = cursor
                    node.y = self.margin + r * (self.node_height + self.rank_sep)
                    cursor += node.width + self.node_sep
                else:  # LR — ranks flow left→right
                    node.x = self.margin + r * (self.node_width + self.rank_sep)
                    node.y = cursor
                    cursor += node.height + self.node_sep
