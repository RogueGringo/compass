"""Tests for the abstractness heuristic — calibration of trigger fire/no-fire."""
from lib.abstractness import ABSTRACTNESS_THRESHOLD, detect_abstractness


def test_empty_prompt_zero_score():
    assert detect_abstractness("") == 0.0
    assert detect_abstractness("   \n\t  ") == 0.0


def test_concrete_command_below_threshold():
    score = detect_abstractness("Run `pytest tests/unit/test_x.py`")
    assert score < ABSTRACTNESS_THRESHOLD


def test_concrete_edit_below_threshold():
    score = detect_abstractness("Add the function bar to lib/foo.py at line 42")
    assert score < ABSTRACTNESS_THRESHOLD


def test_strongly_abstract_above_threshold():
    score = detect_abstractness("How should I architect this system to handle scale?")
    assert score >= ABSTRACTNESS_THRESHOLD


def test_brainstorm_above_threshold():
    score = detect_abstractness("Help me brainstorm the right approach for this design.")
    assert score >= ABSTRACTNESS_THRESHOLD


def test_whats_apostrophe_form_above_threshold():
    score = detect_abstractness("What's the best way to think about this problem?")
    assert score >= ABSTRACTNESS_THRESHOLD


def test_concrete_signals_subtract():
    abstract = detect_abstractness("How should I design the system?")
    concrete = detect_abstractness("How should I design the system: fix the bug at lib/foo.py line 42")
    assert concrete < abstract


def test_score_capped_at_one():
    very_abstract = (
        "How should I architect a system to brainstorm the best general "
        "high-level approach for this open-ended design strategy?"
    )
    assert detect_abstractness(very_abstract) <= 1.0


def test_score_floored_at_zero():
    very_concrete = "rm -rf /tmp/foo.bar at line 100"
    assert detect_abstractness(very_concrete) >= 0.0


# v1.1 regression: "what is" alongside "what's" / "whats"
# Caught during v0.1.0 dogfood — see tests/dogfood/README.md backlog #1.

def test_what_is_the_best_way_above_threshold():
    score = detect_abstractness("What is the best way to think about this problem?")
    assert score >= ABSTRACTNESS_THRESHOLD


def test_what_is_the_right_way_above_threshold():
    score = detect_abstractness(
        "What is the right way to architect a solution for this?"
    )
    assert score >= ABSTRACTNESS_THRESHOLD


def test_whats_no_apostrophe_form_still_works():
    # Belt-and-suspenders: ensure the regex fix didn't break the no-apostrophe case
    score = detect_abstractness("Whats the right way to design a solution?")
    assert score >= ABSTRACTNESS_THRESHOLD
