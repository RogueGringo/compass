"""Substrate verifiers for Compass — NL / Dafny / Lean 4.

Three concrete branches in run_verifier(). No ABC, no registry — when
T4 fires (TLA+ or Z3 added), refactor to a registry pattern. Until then
the if-chain is the honest shape (B-borrowing for v1: interface names
are pre-aligned for mechanical refactor, but no formal Protocol class).

The Dafny / Lean 4 branches shell out to subprocess. They check for the
binary on PATH first via shutil.which() and gracefully return
status='skipped' when absent — this means Compass works even when no
formal tool is installed, just with the NL substrate as the only
verifier.
"""
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import TypedDict


class VerifierResult(TypedDict):
    substrate: str
    status: str  # "pass" | "fail" | "timeout" | "skipped" | "error"
    output: str
    error: str


_DAFNY_TIMEOUT_S = 30
_LEAN_TIMEOUT_S = 60


def run_verifier(substrate: str, spec_text: str) -> VerifierResult:
    """Dispatch to the appropriate substrate verifier."""
    if substrate == "nl":
        return _verify_nl(spec_text)
    if substrate == "dafny":
        return _verify_dafny(spec_text)
    if substrate == "lean4":
        return _verify_lean4(spec_text)
    return {
        "substrate": substrate,
        "status": "error",
        "output": "",
        "error": f"unknown substrate: {substrate}",
    }


def _verify_nl(spec_text: str) -> VerifierResult:
    """NL verifier: deterministic completeness checklist over the spec text.

    No external process. Heuristic checks for:
      - Goal predicate (something the spec is supposed to achieve)
      - Success criterion (what 'done' looks like)
      - Constraint statement (at least one)
    """
    text = spec_text.lower()
    # "must" / "should" are ambiguous — they appear in both goals and constraints.
    # Goal markers must explicitly signal the achievement clause.
    has_goal = any(
        k in text
        for k in (
            "goal:", "objective:", "achieve", "build", "implement", "create",
            "produce", "generate", "compute", "calculate",
        )
    )
    has_criterion = any(
        k in text for k in ("success:", "done when", "complete when", "verify", "test")
    )
    has_constraint = any(
        k in text for k in ("constraint:", "must not", "cannot", "forbidden", "invariant")
    )
    missing = []
    if not has_goal:
        missing.append("goal predicate")
    if not has_criterion:
        missing.append("success criterion")
    if not has_constraint:
        missing.append("explicit constraint")
    if missing:
        return {
            "substrate": "nl",
            "status": "fail",
            "output": "",
            "error": f"NL spec missing: {', '.join(missing)}",
        }
    return {
        "substrate": "nl",
        "status": "pass",
        "output": "NL completeness checklist satisfied",
        "error": "",
    }


def _verify_dafny(spec_text: str) -> VerifierResult:
    """Dafny verifier: shell out to `dafny verify`. Skipped if dafny absent."""
    if shutil.which("dafny") is None:
        return {
            "substrate": "dafny",
            "status": "skipped",
            "output": "",
            "error": "dafny binary not found on PATH",
        }
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".dfy", delete=False, encoding="utf-8"
    ) as f:
        f.write(spec_text)
        spec_path = f.name
    try:
        proc = subprocess.run(
            ["dafny", "verify", spec_path],
            capture_output=True,
            text=True,
            timeout=_DAFNY_TIMEOUT_S,
        )
        return {
            "substrate": "dafny",
            "status": "pass" if proc.returncode == 0 else "fail",
            "output": proc.stdout,
            "error": proc.stderr,
        }
    except subprocess.TimeoutExpired:
        return {
            "substrate": "dafny",
            "status": "timeout",
            "output": "",
            "error": f"dafny verify exceeded {_DAFNY_TIMEOUT_S}s",
        }
    finally:
        Path(spec_path).unlink(missing_ok=True)


def _verify_lean4(spec_text: str) -> VerifierResult:
    """Lean 4 verifier: write to a temp file, run `lean`. Skipped if absent."""
    if shutil.which("lean") is None:
        return {
            "substrate": "lean4",
            "status": "skipped",
            "output": "",
            "error": "lean binary not found on PATH",
        }
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".lean", delete=False, encoding="utf-8"
    ) as f:
        f.write(spec_text)
        spec_path = f.name
    try:
        proc = subprocess.run(
            ["lean", spec_path],
            capture_output=True,
            text=True,
            timeout=_LEAN_TIMEOUT_S,
        )
        return {
            "substrate": "lean4",
            "status": "pass" if proc.returncode == 0 else "fail",
            "output": proc.stdout,
            "error": proc.stderr,
        }
    except subprocess.TimeoutExpired:
        return {
            "substrate": "lean4",
            "status": "timeout",
            "output": "",
            "error": f"lean exceeded {_LEAN_TIMEOUT_S}s",
        }
    finally:
        Path(spec_path).unlink(missing_ok=True)
