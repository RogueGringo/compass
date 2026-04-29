"""Compass resolution record — analog of council's milestone.

Resolution bundle shape:
  {
    "schema_version": "1",
    "timestamp_utc": "ISO-8601 Z",
    "input": {
      "prompt_hash": "sha256:...",
      "prompt_excerpt": "first 500 chars",
      "abstractness_score": 0.0
    },
    "decomposition": {
      "ibis": {...},               # IBISGraph.to_dict()
      "predicates": [...],
      "ambiguity_score": 0.0
    },
    "substrate": {
      "selected": "nl|dafny|lean4",
      "rationale": "..."
    },
    "council": {
      "members": [
        {
          "slot": 1,
          "subagent_type": "...",
          "persona_file": "personas/...",
          "persona_hash": "sha256:...",
          "critique": {...},        # critique.schema.json
          "status": "ok|failed|malformed|timeout"
        }, ...
      ],
      "protocol_file": "protocols/resolution-loop.md",
      "protocol_hash": "sha256:..."
    },
    "verifier": {
      "substrate": "...",
      "status": "pass|fail|timeout|skipped|error",
      "output": "..."
    },
    "synthesis": {
      "verdict": "resolved|iterate|escalate",
      "open_issues": [...],
      "clarifications_used": 0,
      "clarification_budget_exhausted": false
    },
    "resolution_hash": "sha256:..."
  }

`resolution_hash` is computed over every field except itself, using
RFC 8785 canonical JSON via jtech_substrate_core.sha256_canonical_json.
"""
from typing import Any, Dict

from jtech_substrate_core import sha256_canonical_json


def compute_resolution_hash(bundle: Dict[str, Any]) -> str:
    """Compute the hash for a resolution bundle.

    Excludes the resolution_hash field itself if present.
    """
    hashable = {k: v for k, v in bundle.items() if k != "resolution_hash"}
    return sha256_canonical_json(hashable)


def build_resolution(bundle: Dict[str, Any]) -> Dict[str, Any]:
    """Return a copy of bundle with resolution_hash attached."""
    if "resolution_hash" in bundle:
        bundle = {k: v for k, v in bundle.items() if k != "resolution_hash"}
    return {**bundle, "resolution_hash": compute_resolution_hash(bundle)}


def validate_resolution_hash(resolution: Dict[str, Any]) -> bool:
    declared = resolution.get("resolution_hash")
    if not isinstance(declared, str) or not declared.startswith("sha256:"):
        return False
    return declared == compute_resolution_hash(resolution)
