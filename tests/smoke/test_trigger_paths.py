"""Smoke tests for the Compass trigger entry-point.

Exercise the four critical decision paths:
  1. Skip prefix → allow with bypass log
  2. Below-threshold prompt → allow without bypass log
  3. Force prefix + no resolution → deny with COMPASS_REVIEW_REQUIRED
  4. COMPASS_SKIP env → allow with bypass log

Each test invokes lib.trigger.decide() directly (no subprocess). The
underlying hook protocol (read_hook_stdin / emit_*) is exercised by
substrate-core's test suite.
"""
import pytest

from lib.trigger import decide


@pytest.fixture
def tmp_runs(tmp_path, monkeypatch):
    """Isolate runs/ to a tempdir for each test."""
    monkeypatch.setenv("COMPASS_RUNS_DIR", str(tmp_path))
    yield tmp_path


def test_skip_prefix_allows_and_logs(tmp_runs):
    payload = {"prompt": "!compass-skip just run pytest", "transcript_path": ""}
    decision = decide(payload)
    assert decision["action"] == "allow"
    assert decision["reason"] == "compass_skip"
    log = tmp_runs / "compass" / ".bypass-log"
    assert log.exists()
    assert "user_skip" in log.read_text()


def test_compass_skip_env_allows(tmp_runs, monkeypatch):
    monkeypatch.setenv("COMPASS_SKIP", "1")
    payload = {"prompt": "design a system", "transcript_path": ""}
    decision = decide(payload)
    assert decision["action"] == "allow"
    assert decision["reason"] == "compass_skip"


def test_below_threshold_concrete_allows(tmp_runs):
    payload = {
        "prompt": "Run `pytest tests/unit/test_x.py` and report the result.",
        "transcript_path": "",
    }
    decision = decide(payload)
    assert decision["action"] == "allow"
    assert decision["reason"] == "below_threshold"


def test_force_prefix_denies_when_no_resolution(tmp_runs):
    payload = {"prompt": "!compass do the thing", "transcript_path": ""}
    decision = decide(payload)
    assert decision["action"] == "deny"
    assert decision["reason"] == "no_resolution_found"
    assert "COMPASS_REVIEW_REQUIRED" in decision["message"]


def test_above_threshold_denies_when_no_resolution(tmp_runs):
    payload = {
        "prompt": "How should I architect this system to handle scale?",
        "transcript_path": "",
    }
    decision = decide(payload)
    assert decision["action"] == "deny"
    assert decision["reason"] == "no_resolution_found"


def test_skip_takes_priority_over_force(tmp_runs):
    """!compass-skip should win over !compass (skip is more specific)."""
    payload = {"prompt": "!compass-skip help me design something", "transcript_path": ""}
    decision = decide(payload)
    assert decision["action"] == "allow"
    assert decision["reason"] == "compass_skip"


def test_empty_prompt_below_threshold_allows(tmp_runs):
    payload = {"prompt": "", "transcript_path": ""}
    decision = decide(payload)
    assert decision["action"] == "allow"
    assert decision["reason"] == "below_threshold"


def test_resolution_hash_in_transcript_allows(tmp_runs):
    """A valid resolution hash in the transcript + matching milestone file → allow."""
    import datetime as _dt
    import json

    from lib.resolution import build_resolution
    from lib.storage import write_resolution

    prompt = "How should I architect this system?"

    # Create a valid resolution
    bundle = {
        "schema_version": "1",
        "timestamp_utc": "2026-04-28T12:00:00Z",
        "input": {
            "prompt_hash": _hash(prompt),
            "prompt_excerpt": prompt,
            "abstractness_score": 0.7,
        },
        "decomposition": {"ibis": {"nodes": []}, "predicates": [], "ambiguity_score": 0.0},
        "substrate": {"selected": "nl", "rationale": "default"},
        "council": {"members": [], "protocol_file": "x", "protocol_hash": _hash("p")},
        "verifier": {"substrate": "nl", "status": "pass", "output": "", "error": ""},
        "synthesis": {
            "verdict": "resolved",
            "open_issues": [],
            "clarifications_used": 0,
            "clarification_budget_exhausted": False,
        },
    }
    resolution = build_resolution(bundle)
    write_resolution(resolution)

    # Build a transcript that contains the resolution hash in the most recent assistant turn
    transcript = tmp_runs / "transcript.jsonl"
    transcript.write_text(json.dumps({
        "type": "assistant",
        "message": {
            "content": [{"type": "text", "text": f"Resolution: {resolution['resolution_hash']}"}],
        },
    }) + "\n")

    payload = {"prompt": prompt, "transcript_path": str(transcript)}
    decision = decide(payload)
    assert decision["action"] == "allow"
    assert decision["reason"] == "resolution_valid"


def test_shadow_log_written_when_in_band(tmp_runs):
    """v1.1: prompts in [SHADOW_BAND_LOW, ABSTRACTNESS_THRESHOLD) get logged."""
    # This prompt scores in the shadow band: weak signals only, no strong matches
    payload = {
        "prompt": "I should figure out the best plan for this approach to the system",
        "transcript_path": "",
    }
    decision = decide(payload)
    assert decision["action"] == "allow"
    assert decision["reason"] == "below_threshold"

    log = tmp_runs / "compass" / ".shadow-log"
    assert log.exists(), "shadow log not written despite shadow-band score"
    content = log.read_text()
    assert "score=" in content
    assert "prompt=" in content


def test_shadow_log_NOT_written_when_clearly_concrete(tmp_runs):
    """Below SHADOW_BAND_LOW: pure noise, don't log."""
    payload = {
        "prompt": "Run pytest tests/unit/test_x.py at line 42",
        "transcript_path": "",
    }
    decision = decide(payload)
    assert decision["action"] == "allow"
    log = tmp_runs / "compass" / ".shadow-log"
    # Either no log file at all, or a log file that's empty (depending on
    # whether something else wrote first; in this isolated tmp_runs nothing did)
    if log.exists():
        assert log.read_text() == "", "shadow log should be empty for clearly concrete prompts"


def test_shadow_log_NOT_written_when_above_threshold(tmp_runs):
    """Above threshold: deny path, no shadow log."""
    payload = {
        "prompt": "Help me brainstorm the right approach for this design.",
        "transcript_path": "",
    }
    decision = decide(payload)
    assert decision["action"] == "deny"
    log = tmp_runs / "compass" / ".shadow-log"
    if log.exists():
        # Above-threshold prompts should not be in shadow log
        assert "Help me brainstorm" not in log.read_text()


def test_prompt_changed_denies(tmp_runs):
    """If a resolution exists but the prompt has changed, deny with prompt_changed."""
    import json

    from lib.resolution import build_resolution
    from lib.storage import write_resolution

    original_prompt = "How should I architect this system?"
    bundle = {
        "schema_version": "1",
        "timestamp_utc": "2026-04-28T12:00:00Z",
        "input": {
            "prompt_hash": _hash(original_prompt),
            "prompt_excerpt": original_prompt,
            "abstractness_score": 0.7,
        },
        "decomposition": {"ibis": {"nodes": []}, "predicates": [], "ambiguity_score": 0.0},
        "substrate": {"selected": "nl", "rationale": "default"},
        "council": {"members": [], "protocol_file": "x", "protocol_hash": _hash("p")},
        "verifier": {"substrate": "nl", "status": "pass", "output": "", "error": ""},
        "synthesis": {
            "verdict": "resolved",
            "open_issues": [],
            "clarifications_used": 0,
            "clarification_budget_exhausted": False,
        },
    }
    resolution = build_resolution(bundle)
    write_resolution(resolution)

    transcript = tmp_runs / "transcript.jsonl"
    transcript.write_text(json.dumps({
        "type": "assistant",
        "message": {
            "content": [{"type": "text", "text": f"Resolution: {resolution['resolution_hash']}"}],
        },
    }) + "\n")

    different_prompt = "How should I think about this completely different system instead?"
    payload = {"prompt": different_prompt, "transcript_path": str(transcript)}
    decision = decide(payload)
    assert decision["action"] == "deny"
    assert decision["reason"] == "prompt_changed"


def _hash(text: str) -> str:
    from jtech_substrate_core import sha256_text
    return sha256_text(text)
