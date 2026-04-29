"""Heuristic abstractness detector for the Compass trigger.

The detector is the load-bearing trigger for whether Compass fires. It
must err conservative (under-fire) in v0.1.0 — false positives kill flow,
false negatives just make Compass invisible (recoverable via !compass
force prefix). Calibration data from the first 20-30 dogfood sessions
will tighten the threshold.

The score is a float in [0.0, 1.0]. ABSTRACTNESS_THRESHOLD = 0.6 fires
the gate. Implementation is intentionally simple: keyword/phrase scoring
with no LLM call (so the trigger has zero token cost on every prompt).
"""
import re
from typing import List, Tuple

ABSTRACTNESS_THRESHOLD = 0.6

# Strong signals — high abstractness. Order is significant: longer phrases
# match before shorter ones.
_STRONG_SIGNALS: List[Tuple[str, float]] = [
    (r"\bhow\s+should\s+(?:i|we)\b", 0.45),
    # v1.1 fix: explicitly handle "what is" alongside "what's"/"whats" — caught
    # during the v0.1.0 dogfood when "What is the right way..." scored 0.35
    # despite being clearly abstract.
    (r"\bwhat(?:'?s|\s+is)\s+the\s+best\s+way\b", 0.55),
    (r"\bhelp\s+me\s+(?:think|figure|design|architect|brainstorm)\b", 0.55),
    (r"\bwhat(?:'?s|\s+is)\s+the\s+right\s+way\b", 0.50),
    (r"\bhow\s+do\s+(?:i|we)\s+(?:approach|design|architect|think\s+about)\b", 0.50),
    (r"\bdesign\s+(?:a|an|the)\b", 0.40),
    (r"\barchitect\s+(?:a|an|the)\b", 0.40),
    (r"\bthink\s+(?:through|about)\b", 0.35),
    (r"\bhigh-level\b", 0.30),
    (r"\bopen-ended\b", 0.30),
    (r"\bbrainstorm\b", 0.55),
]

# Weak signals — additive, smaller weight.
_WEAK_SIGNALS: List[Tuple[str, float]] = [
    (r"\bshould\b", 0.10),
    (r"\bcould\b", 0.10),
    (r"\bmight\b", 0.10),
    (r"\bsystem\b", 0.10),
    (r"\bapproach\b", 0.10),
    (r"\bstrategy\b", 0.15),
    (r"\bplan\b", 0.10),
    (r"\bbest\b", 0.10),
    (r"\bgeneral(?:ly)?\b", 0.05),
]

# Concrete signals — REDUCE abstractness when present.
_CONCRETE_SIGNALS: List[Tuple[str, float]] = [
    (r"\bfix\s+(?:the|this)\s+\w+", -0.30),
    (r"\b(?:add|remove|delete|update|rename)\s+(?:the|this|a)\s+\w+", -0.30),
    (r"\brun\s+\w+", -0.25),
    (r"`[^`]+`", -0.10),
    (r"\.(py|js|ts|md|json|sh|rs|go|c|cpp|h)\b", -0.15),
    (r"\bline\s+\d+", -0.20),
]


def detect_abstractness(prompt: str) -> float:
    """Return abstractness score in [0.0, 1.0]."""
    if not prompt or not prompt.strip():
        return 0.0
    p = prompt.lower()
    score = 0.0
    for pat, weight in _STRONG_SIGNALS:
        if re.search(pat, p):
            score += weight
    for pat, weight in _WEAK_SIGNALS:
        if re.search(pat, p):
            score += weight
    for pat, weight in _CONCRETE_SIGNALS:
        if re.search(pat, p):
            score += weight
    # Length bonus: very long prompts often carry undeclared assumptions
    word_count = len(p.split())
    if word_count > 200:
        score += 0.10
    return max(0.0, min(1.0, score))
