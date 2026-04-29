"""Tests for resolution-record hashing and validation."""
from lib.resolution import (
    build_resolution,
    compute_resolution_hash,
    validate_resolution_hash,
)


def _sample() -> dict:
    return {
        "schema_version": "1",
        "timestamp_utc": "2026-04-28T12:00:00Z",
        "input": {
            "prompt_hash": "sha256:" + "0" * 64,
            "prompt_excerpt": "test",
            "abstractness_score": 0.7,
        },
        "decomposition": {"ibis": {"nodes": []}, "predicates": [], "ambiguity_score": 0.0},
        "substrate": {"selected": "nl", "rationale": "default"},
        "council": {"members": [], "protocol_file": "x", "protocol_hash": "sha256:" + "1" * 64},
        "verifier": {"substrate": "nl", "status": "pass", "output": "", "error": ""},
        "synthesis": {
            "verdict": "resolved",
            "open_issues": [],
            "clarifications_used": 0,
            "clarification_budget_exhausted": False,
        },
    }


def test_hash_format():
    h = compute_resolution_hash(_sample())
    assert h.startswith("sha256:")
    assert len(h) == len("sha256:") + 64


def test_hash_stable_across_calls():
    bundle = _sample()
    assert compute_resolution_hash(bundle) == compute_resolution_hash(bundle)


def test_hash_independent_of_pre_existing_hash_field():
    bundle = _sample()
    h1 = compute_resolution_hash(bundle)
    bundle["resolution_hash"] = "sha256:" + "f" * 64  # spurious
    h2 = compute_resolution_hash(bundle)
    assert h1 == h2


def test_build_resolution_attaches_hash():
    bundle = _sample()
    built = build_resolution(bundle)
    assert built["resolution_hash"].startswith("sha256:")
    assert validate_resolution_hash(built)


def test_build_resolution_strips_existing_hash():
    bundle = _sample()
    bundle["resolution_hash"] = "sha256:" + "f" * 64
    built = build_resolution(bundle)
    assert built["resolution_hash"] != "sha256:" + "f" * 64


def test_validate_rejects_missing_hash():
    bundle = _sample()
    assert validate_resolution_hash(bundle) is False


def test_validate_rejects_malformed_hash():
    bundle = _sample()
    bundle["resolution_hash"] = "not-a-hash"
    assert validate_resolution_hash(bundle) is False


def test_mutation_breaks_hash():
    built = build_resolution(_sample())
    built["input"]["prompt_excerpt"] = "tampered"
    assert validate_resolution_hash(built) is False


def test_field_reorder_does_not_break_hash():
    """Canonical JSON sorts keys; reordering at runtime should not affect hash."""
    bundle1 = _sample()
    bundle2 = {k: bundle1[k] for k in reversed(list(bundle1.keys()))}
    assert compute_resolution_hash(bundle1) == compute_resolution_hash(bundle2)
