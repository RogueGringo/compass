"""Tests for the EIG ranker."""
from lib.eig import CLARIFICATION_BUDGET, rank_clarifications
from lib.ibis import IBISGraph, IBISNode, NodeType


def test_empty_graph_returns_empty():
    g = IBISGraph()
    assert rank_clarifications(g) == []


def test_resolved_issues_excluded():
    g = IBISGraph()
    g.add_node(IBISNode(id="i1", node_type=NodeType.ISSUE, content="x"))
    g.add_node(IBISNode(id="r1", node_type=NodeType.RESOLUTION, parent_id="i1", content="x"))
    assert rank_clarifications(g) == []


def test_budget_caps_results():
    g = IBISGraph()
    for i in range(CLARIFICATION_BUDGET + 3):
        g.add_node(IBISNode(id=f"i{i}", node_type=NodeType.ISSUE, content="x"))
    ranked = rank_clarifications(g)
    assert len(ranked) == CLARIFICATION_BUDGET


def test_verifiability_boost_orders_predicates_first():
    g = IBISGraph()
    g.add_node(IBISNode(
        id="i_vague", node_type=NodeType.ISSUE,
        content="What should we do here?",
    ))
    g.add_node(IBISNode(
        id="i_verifiable", node_type=NodeType.ISSUE,
        content="The function must always return a non-null value, never panic, and must guarantee termination.",
    ))
    ranked = rank_clarifications(g)
    assert ranked[0].issue.id == "i_verifiable"


def test_more_positions_higher_score():
    g = IBISGraph()
    g.add_node(IBISNode(id="i1", node_type=NodeType.ISSUE, content="x"))
    g.add_node(IBISNode(id="i2", node_type=NodeType.ISSUE, content="x"))
    g.add_node(IBISNode(
        id="p1", node_type=NodeType.POSITION, parent_id="i1", content="x", confidence=0.3,
    ))
    g.add_node(IBISNode(
        id="p2", node_type=NodeType.POSITION, parent_id="i1", content="x", confidence=0.3,
    ))
    g.add_node(IBISNode(
        id="p3", node_type=NodeType.POSITION, parent_id="i2", content="x", confidence=0.9,
    ))
    ranked = rank_clarifications(g)
    # i1 has more positions and lower-confidence ones — should rank higher
    by_id = {r.issue.id: r.score for r in ranked}
    assert by_id["i1"] > by_id["i2"]
