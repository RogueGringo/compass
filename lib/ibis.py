"""IBIS graph data structure for Compass intent decomposition.

IBIS = Issue-Based Information System (Rittel & Webber). The graph
captures unresolved questions about user intent as a typed dependency
structure:

  - ISSUE: an open question / underspecification
  - POSITION: a candidate answer to an Issue
  - ARGUMENT: pro/con evidence for a Position
  - RESOLUTION: a closed Issue with selected Position

Closure rules (v0.1.0):
  - An Issue is "closed" iff a Resolution node references it
  - The graph is "fully resolved" iff every Issue has a Resolution
  - The graph is "well-formed" iff every Position has a parent Issue
    and every Argument has a parent Position

The to_adjacency() method is the JTopo bridge stub — locked dict shape
that v1.1's H₀ persistent homology wire-up will consume unchanged.
"""
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class NodeType(str, Enum):
    ISSUE = "issue"
    POSITION = "position"
    ARGUMENT = "argument"
    RESOLUTION = "resolution"


@dataclass
class IBISNode:
    id: str
    node_type: NodeType
    content: str
    parent_id: Optional[str] = None
    confidence: float = 1.0  # used by EIG ranker

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {
            "id": self.id,
            "node_type": self.node_type.value,
            "content": self.content,
        }
        if self.parent_id is not None:
            d["parent_id"] = self.parent_id
        d["confidence"] = self.confidence
        return d


@dataclass
class IBISGraph:
    nodes: List[IBISNode] = field(default_factory=list)

    def add_node(self, node: IBISNode) -> None:
        if any(n.id == node.id for n in self.nodes):
            raise ValueError(f"duplicate node id: {node.id}")
        if node.parent_id is not None:
            if not any(n.id == node.parent_id for n in self.nodes):
                raise ValueError(f"unknown parent_id: {node.parent_id}")
        self.nodes.append(node)

    def by_id(self, node_id: str) -> Optional[IBISNode]:
        for n in self.nodes:
            if n.id == node_id:
                return n
        return None

    def issues(self) -> List[IBISNode]:
        return [n for n in self.nodes if n.node_type == NodeType.ISSUE]

    def positions_for(self, issue_id: str) -> List[IBISNode]:
        return [
            n for n in self.nodes
            if n.node_type == NodeType.POSITION and n.parent_id == issue_id
        ]

    def arguments_for(self, position_id: str) -> List[IBISNode]:
        return [
            n for n in self.nodes
            if n.node_type == NodeType.ARGUMENT and n.parent_id == position_id
        ]

    def resolution_for(self, issue_id: str) -> Optional[IBISNode]:
        for n in self.nodes:
            if n.node_type == NodeType.RESOLUTION and n.parent_id == issue_id:
                return n
        return None

    def open_issues(self) -> List[IBISNode]:
        return [i for i in self.issues() if self.resolution_for(i.id) is None]

    def well_formed(self) -> bool:
        """Every Position has an Issue parent; every Argument has a Position parent."""
        for n in self.nodes:
            if n.node_type == NodeType.POSITION:
                p = self.by_id(n.parent_id) if n.parent_id else None
                if p is None or p.node_type != NodeType.ISSUE:
                    return False
            elif n.node_type == NodeType.ARGUMENT:
                p = self.by_id(n.parent_id) if n.parent_id else None
                if p is None or p.node_type != NodeType.POSITION:
                    return False
            elif n.node_type == NodeType.RESOLUTION:
                p = self.by_id(n.parent_id) if n.parent_id else None
                if p is None or p.node_type != NodeType.ISSUE:
                    return False
        return True

    def fully_resolved(self) -> bool:
        """True iff every Issue has a Resolution and graph is well-formed."""
        if not self.well_formed():
            return False
        return len(self.open_issues()) == 0

    def to_dict(self) -> Dict[str, Any]:
        return {"nodes": [n.to_dict() for n in self.nodes]}

    def to_adjacency(self) -> Dict[str, Any]:
        """JTopo bridge stub. LOCKED dict shape — v1.1 wire-up must not break it.

        Returns:
            {
              "nodes": [{"id": str, "type": str, "weight": float}, ...],
              "edges": [{"src": str, "dst": str, "relation": str}, ...]
            }
        """
        node_dicts = [
            {"id": n.id, "type": n.node_type.value, "weight": n.confidence}
            for n in self.nodes
        ]
        edges = [
            {"src": n.parent_id, "dst": n.id, "relation": "child_of"}
            for n in self.nodes
            if n.parent_id is not None
        ]
        return {"nodes": node_dicts, "edges": edges}
