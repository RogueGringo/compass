"""Tests for IBISGraph data structure."""
import pytest

from lib.ibis import IBISGraph, IBISNode, NodeType


def _make_issue(id_: str, content: str = "x") -> IBISNode:
    return IBISNode(id=id_, node_type=NodeType.ISSUE, content=content)


def _make_position(id_: str, parent: str, content: str = "x") -> IBISNode:
    return IBISNode(id=id_, node_type=NodeType.POSITION, parent_id=parent, content=content)


def _make_argument(id_: str, parent: str, content: str = "x") -> IBISNode:
    return IBISNode(id=id_, node_type=NodeType.ARGUMENT, parent_id=parent, content=content)


def _make_resolution(id_: str, parent: str, content: str = "x") -> IBISNode:
    return IBISNode(id=id_, node_type=NodeType.RESOLUTION, parent_id=parent, content=content)


def test_empty_graph_well_formed_and_resolved():
    g = IBISGraph()
    assert g.well_formed() is True
    assert g.fully_resolved() is True
    assert g.open_issues() == []


def test_single_issue_unresolved():
    g = IBISGraph()
    g.add_node(_make_issue("i1"))
    assert g.well_formed() is True
    assert g.fully_resolved() is False
    assert len(g.open_issues()) == 1


def test_resolved_issue_closes():
    g = IBISGraph()
    g.add_node(_make_issue("i1"))
    g.add_node(_make_resolution("r1", "i1"))
    assert g.fully_resolved() is True
    assert g.open_issues() == []


def test_duplicate_id_rejected():
    g = IBISGraph()
    g.add_node(_make_issue("i1"))
    with pytest.raises(ValueError, match="duplicate"):
        g.add_node(_make_issue("i1"))


def test_orphan_parent_rejected():
    g = IBISGraph()
    with pytest.raises(ValueError, match="unknown parent_id"):
        g.add_node(_make_position("p1", "i_missing"))


def test_position_must_have_issue_parent():
    g = IBISGraph()
    g.add_node(_make_issue("i1"))
    g.add_node(_make_position("p1", "i1"))
    # Now try to make a position whose parent is another position — well-formed should fail
    g.add_node(IBISNode(id="p2", node_type=NodeType.POSITION, parent_id="p1", content="x"))
    assert g.well_formed() is False


def test_argument_must_have_position_parent():
    g = IBISGraph()
    g.add_node(_make_issue("i1"))
    g.add_node(IBISNode(id="a1", node_type=NodeType.ARGUMENT, parent_id="i1", content="x"))
    assert g.well_formed() is False


def test_to_dict_round_trip_shape():
    g = IBISGraph()
    g.add_node(_make_issue("i1"))
    g.add_node(_make_position("p1", "i1"))
    d = g.to_dict()
    assert "nodes" in d
    assert len(d["nodes"]) == 2
    assert d["nodes"][0]["node_type"] == "issue"
    assert d["nodes"][1]["node_type"] == "position"


def test_to_adjacency_locked_shape():
    """JTopo bridge stub — dict shape MUST NOT change without bumping
    jtech_substrate_core's experimental contract."""
    g = IBISGraph()
    g.add_node(_make_issue("i1"))
    g.add_node(_make_position("p1", "i1"))
    g.add_node(_make_argument("a1", "p1"))
    adj = g.to_adjacency()
    assert set(adj.keys()) == {"nodes", "edges"}
    assert len(adj["nodes"]) == 3
    assert len(adj["edges"]) == 2
    for node in adj["nodes"]:
        assert set(node.keys()) == {"id", "type", "weight"}
    for edge in adj["edges"]:
        assert set(edge.keys()) == {"src", "dst", "relation"}


def test_to_adjacency_empty_graph_returns_empty_arrays():
    g = IBISGraph()
    adj = g.to_adjacency()
    assert adj == {"nodes": [], "edges": []}


def test_open_issues_excludes_resolved():
    g = IBISGraph()
    g.add_node(_make_issue("i1"))
    g.add_node(_make_issue("i2"))
    g.add_node(_make_resolution("r1", "i1"))
    open_ids = [i.id for i in g.open_issues()]
    assert open_ids == ["i2"]
