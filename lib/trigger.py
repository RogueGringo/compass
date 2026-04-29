"""Compass UserPromptSubmit gate — entry point.

Called by hooks/compass-trigger.sh as a Python script. Reads the
UserPromptSubmit payload from stdin, decides allow/deny via decide(),
and emits the appropriate hook response via jtech-substrate-core.
"""
import os
import sys
from pathlib import Path
from typing import Any, Dict

# Bootstrap: ensure substrate-core and lib/ are on sys.path even when
# trigger.py is invoked directly as a script (not as lib.trigger).
_PLUGIN_ROOT = Path(__file__).resolve().parents[1]
if str(_PLUGIN_ROOT) not in sys.path:
    sys.path.insert(0, str(_PLUGIN_ROOT))
_SUBSTRATE = _PLUGIN_ROOT.parent / "core"
if _SUBSTRATE.exists() and str(_SUBSTRATE) not in sys.path:
    sys.path.insert(0, str(_SUBSTRATE))

from jtech_substrate_core import emit_allow, emit_deny, read_hook_stdin

from lib.abstractness import ABSTRACTNESS_THRESHOLD, detect_abstractness
from lib.deny import render_deny_message
from lib.storage import (
    DEFAULT_SLUG,
    append_bypass_log,
    append_shadow_log,
    find_resolution,
    runs_root,
)


FORCE_PREFIX = "!compass"
SKIP_PREFIX = "!compass-skip"

# v1.1: Bottom of the shadow-log band. Prompts scoring in
# [SHADOW_BAND_LOW, ABSTRACTNESS_THRESHOLD) get logged for calibration
# review without firing the gate. Addresses the v0.1.0 dogfood
# Failure-Modes finding (FN-observability blind spot, conf 0.78).
SHADOW_BAND_LOW = 0.3


def _allow(reason: str) -> Dict[str, Any]:
    return {"action": "allow", "reason": reason}


def _deny(reason: str, prompt: str, abstractness: float) -> Dict[str, Any]:
    plugin_root = os.environ.get("CLAUDE_PLUGIN_ROOT") or str(_PLUGIN_ROOT)
    msg = render_deny_message(
        reason=reason,
        prompt_excerpt=prompt,
        plugin_root=plugin_root,
        runs_root=str(runs_root()),
        abstractness_score=abstractness,
    )
    return {"action": "deny", "reason": reason, "message": msg}


def decide(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Top-level decision function. Pure-ish: depends on env, fs."""
    prompt = payload.get("prompt", "") or ""

    # Skip path: !compass-skip prefix or COMPASS_SKIP=1 env
    if prompt.startswith(SKIP_PREFIX) or os.environ.get("COMPASS_SKIP") == "1":
        try:
            append_bypass_log(reason="user_skip")
        except OSError:
            pass  # logging is best-effort
        return _allow("compass_skip")

    # Force path: !compass prefix (but not !compass-skip)
    forced = prompt.startswith(FORCE_PREFIX) and not prompt.startswith(SKIP_PREFIX)

    abstractness = detect_abstractness(prompt)

    # Heuristic gate: only fire if forced or above threshold.
    # Below threshold, log near-misses to .shadow-log for FN-observability
    # (addresses v0.1.0 dogfood data-loss finding).
    if not forced and abstractness < ABSTRACTNESS_THRESHOLD:
        if abstractness >= SHADOW_BAND_LOW:
            try:
                append_shadow_log(prompt, abstractness)
            except OSError:
                pass  # best-effort logging
        return _allow("below_threshold")

    # Compass should fire — check for valid resolution milestone in transcript
    transcript_path = payload.get("transcript_path", "") or ""
    candidate_hash = _scan_transcript_for_resolution(transcript_path)
    if not candidate_hash:
        return _deny("no_resolution_found", prompt, abstractness)

    resolution_path = find_resolution(candidate_hash)
    if not resolution_path:
        return _deny("no_resolution_found", prompt, abstractness)

    try:
        import json
        resolution = json.loads(resolution_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return _deny("resolution_corrupt", prompt, abstractness)

    from lib.resolution import validate_resolution_hash

    if not validate_resolution_hash(resolution):
        return _deny("resolution_corrupt", prompt, abstractness)

    # Verify the prompt matches the recorded one (within reasonable tolerance)
    recorded_hash = resolution.get("input", {}).get("prompt_hash", "")
    from jtech_substrate_core import sha256_text

    current_hash = sha256_text(prompt)
    if recorded_hash and recorded_hash != current_hash:
        return _deny("prompt_changed", prompt, abstractness)

    if resolution.get("synthesis", {}).get("verdict") != "resolved":
        return _deny("verdict_not_resolved", prompt, abstractness)

    return _allow("resolution_valid")


def _scan_transcript_for_resolution(transcript_path: str) -> str:
    """Scan the transcript for the most recent sha256:<64 hex> emitted by the assistant.

    Mirrors council's transcript scanner pattern but without importing it
    (compass keeps its own copy until T1 fires for transcript scanning).
    """
    import json
    import re

    if not transcript_path:
        return ""
    p = Path(transcript_path)
    if not p.exists():
        return ""
    pattern = re.compile(r"\bsha256:[0-9a-f]{64}\b")
    last_hash = ""
    try:
        with p.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except ValueError:
                    continue
                if rec.get("type") != "assistant":
                    continue
                content = rec.get("message", {}).get("content", [])
                if not isinstance(content, list):
                    continue
                for block in content:
                    if not isinstance(block, dict):
                        continue
                    if block.get("type") != "text":
                        continue
                    text = block.get("text", "")
                    matches = pattern.findall(text)
                    if matches:
                        last_hash = matches[-1]
    except OSError:
        return ""
    return last_hash


def main():
    payload = read_hook_stdin()
    decision = decide(payload)
    if decision["action"] == "allow":
        emit_allow()
    emit_deny(decision["message"])


if __name__ == "__main__":
    main()
