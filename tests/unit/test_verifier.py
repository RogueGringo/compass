"""Tests for the substrate verifier dispatcher."""
from lib.verifier import run_verifier


def test_unknown_substrate_returns_error():
    r = run_verifier("typescript", "x")
    assert r["status"] == "error"
    assert "unknown substrate" in r["error"]


def test_nl_complete_spec_passes():
    spec = """
    Goal: count words in a file.
    Success: returns the integer count, matching `wc -w`.
    Constraint: must not modify the input file.
    """
    r = run_verifier("nl", spec)
    assert r["status"] == "pass"


def test_nl_missing_goal_fails():
    spec = "Verify the result is correct. Constraint: must not crash."
    r = run_verifier("nl", spec)
    assert r["status"] == "fail"
    assert "goal" in r["error"]


def test_nl_missing_criterion_fails():
    spec = "Goal: do the thing. Constraint: cannot use floats."
    r = run_verifier("nl", spec)
    assert r["status"] == "fail"


def test_nl_missing_constraint_fails():
    spec = "Goal: parse the file. Success: emits a JSON object."
    r = run_verifier("nl", spec)
    assert r["status"] == "fail"


def test_dafny_skipped_when_binary_absent():
    """If dafny is not installed, the adapter must return skipped, not crash."""
    r = run_verifier("dafny", "method M() {}")
    # Either 'skipped' (dafny absent) OR 'pass'/'fail' (dafny present); never 'error'
    assert r["status"] in ("skipped", "pass", "fail", "timeout")
    assert r["substrate"] == "dafny"


def test_lean4_skipped_when_binary_absent():
    """If lean is not installed, the adapter must return skipped, not crash."""
    r = run_verifier("lean4", "theorem t : True := trivial")
    assert r["status"] in ("skipped", "pass", "fail", "timeout")
    assert r["substrate"] == "lean4"


def test_verifier_result_shape():
    r = run_verifier("nl", "Goal: x. Success: y. Constraint: z.")
    assert set(r.keys()) == {"substrate", "status", "output", "error"}
