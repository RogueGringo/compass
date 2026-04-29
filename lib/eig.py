"""Expected-Information-Gain ranker for Compass clarification.

BED-LLM-style: rank open Issues by how much resolving them would reduce
the residual ambiguity in the rest of the graph. v0.1.0 uses a
deterministic proxy: per-Issue score combines (a) ambiguity contribution
(number of Positions × inverse confidence), (b) downstream impact
(number of dependent Arguments), and (c) a verifiability boost when the
Issue mentions formally checkable predicates.

Real BED-LLM Bayesian scoring is v1.1+ (requires LLM call per Issue;
v0.1.0 keeps the trigger and ranker token-free).
"""
from dataclasses import dataclass
from typing import List

from .ibis import IBISGraph, IBISNode


# Words/phrases that suggest a verifiable predicate (Dafny / Lean fits)
_VERIFIABILITY_HINTS = [
    "must", "always", "never", "for all", "exists", "guarantee",
    "invariant", "precondition", "postcondition", "type", "termination",
    "memory-safe", "thread-safe", "ordering", "monotonic",
]

CLARIFICATION_BUDGET = 5  # max questions/session


@dataclass
class RankedIssue:
    issue: IBISNode
    score: float


def _verifiability_boost(issue: IBISNode) -> float:
    text = issue.content.lower()
    matches = sum(1 for hint in _VERIFIABILITY_HINTS if hint in text)
    return 0.15 * min(matches, 3)


def _ambiguity_contribution(graph: IBISGraph, issue: IBISNode) -> float:
    positions = graph.positions_for(issue.id)
    if not positions:
        return 1.0  # no positions = maximally underspecified
    avg_conf = sum(p.confidence for p in positions) / len(positions)
    # More positions and lower confidence = more ambiguous
    return min(1.0, len(positions) * 0.25) * (1.0 - avg_conf * 0.5)


def _downstream_impact(graph: IBISGraph, issue: IBISNode) -> float:
    positions = graph.positions_for(issue.id)
    arg_count = sum(len(graph.arguments_for(p.id)) for p in positions)
    return min(1.0, arg_count * 0.10)


def rank_clarifications(graph: IBISGraph) -> List[RankedIssue]:
    """Rank open Issues descending by EIG-proxy score.

    Returns at most CLARIFICATION_BUDGET ranked issues. Caller is
    responsible for tracking session-level question count separately.
    """
    open_issues = graph.open_issues()
    ranked: List[RankedIssue] = []
    for issue in open_issues:
        score = (
            _ambiguity_contribution(graph, issue)
            + _downstream_impact(graph, issue)
            + _verifiability_boost(issue)
        )
        ranked.append(RankedIssue(issue=issue, score=score))
    ranked.sort(key=lambda r: r.score, reverse=True)
    return ranked[:CLARIFICATION_BUDGET]
