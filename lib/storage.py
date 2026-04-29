"""Compass-local resolution storage (analog of council's milestone storage).

Compass uses its own runs directory and env override (COMPASS_RUNS_DIR)
so council and Compass don't collide on storage paths. Same canonical
file layout: runs/<repo-slug-or-'compass'>/<UTC-date>/<hash>.json.

Per the architect's analysis, repo_slug from council was deliberately
NOT extracted to substrate-core in v0.1.0 — Compass may not need
per-repo namespacing at all (intent resolution is often session-scoped,
not project-scoped). For v0.1.0 we use a fixed 'compass' slug; if real
per-repo namespacing becomes needed in v1.1+, lift council's repo_slug
into the substrate (T1 trigger).
"""
import datetime as _dt
import json
import os
from pathlib import Path
from typing import Any, Dict, Optional

DEFAULT_SLUG = "compass"


def runs_root() -> Path:
    """Resolve the resolution storage root.

    Order:
      1. $COMPASS_RUNS_DIR — explicit override
      2. ~/.compass/runs — global default (decoupled from plugin install dir)
    """
    override = os.environ.get("COMPASS_RUNS_DIR")
    if override:
        return Path(override)
    return Path.home() / ".compass" / "runs"


def _cap_log_file(log_path: Path, max_bytes: int = 1024 * 1024, keep_lines: int = 500) -> None:
    """Trim a log file in place once it crosses max_bytes, keeping the last keep_lines."""
    if log_path.exists() and log_path.stat().st_size > max_bytes:
        try:
            lines = log_path.read_text(encoding="utf-8").splitlines()
            log_path.write_text("\n".join(lines[-keep_lines:]) + "\n", encoding="utf-8")
        except OSError:
            pass


def resolution_path(slug: str, date: str, resolution_hash: str) -> Path:
    return runs_root() / slug / date / f"{resolution_hash}.json"


def write_resolution(
    resolution: Dict[str, Any],
    slug: str = DEFAULT_SLUG,
    date: Optional[str] = None,
) -> Path:
    if "resolution_hash" not in resolution:
        raise ValueError("resolution missing 'resolution_hash' field")
    if date is None:
        date = _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%d")
    path = resolution_path(slug, date, resolution["resolution_hash"])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(resolution, indent=2, sort_keys=True, ensure_ascii=False),
        encoding="utf-8",
    )
    return path


def find_resolution(resolution_hash: str, slug: str = DEFAULT_SLUG) -> Optional[Path]:
    base = runs_root() / slug
    if not base.exists():
        return None
    matches = list(base.glob(f"*/{resolution_hash}.json"))
    if not matches:
        return None
    matches.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return matches[0]


def append_bypass_log(slug: str = DEFAULT_SLUG, reason: str = "user_skip") -> None:
    base = runs_root() / slug
    base.mkdir(parents=True, exist_ok=True)
    log_path = base / ".bypass-log"
    _cap_log_file(log_path)
    ts = _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    with log_path.open("a", encoding="utf-8") as f:
        f.write(f"{ts}\treason={reason}\n")


def append_shadow_log(
    prompt: str,
    score: float,
    slug: str = DEFAULT_SLUG,
) -> None:
    """Append a near-miss to the shadow log for FN-observability.

    Compass is deliberately token-free at trigger time, so prompts that
    score below ABSTRACTNESS_THRESHOLD leave no trace by default. The
    Watkins-Failure-Modes member of the v0.1.0 dogfood council flagged
    this as a data-loss-class blind spot (confidence 0.78): a heuristic
    that drifts will silently un-gate prompts and we can't tell.

    The shadow log captures prompts in the band [SHADOW_BAND_LOW,
    ABSTRACTNESS_THRESHOLD) — close enough to the threshold that a
    miscalibration could matter — without changing fire/no-fire
    semantics. Reviewing this log periodically is the v1.1 calibration
    input.

    Format: tab-separated `timestamp\tscore=<float>\tprompt=<excerpt>`,
    append-only with size-capped rotation: once the file exceeds 1 MB
    we trim it in place to the last 500 lines (see _cap_log_file). The
    calibration signal lives in the recency of near-misses, not the
    full historical record, so a sliding window is acceptable.
    """
    base = runs_root() / slug
    base.mkdir(parents=True, exist_ok=True)
    log_path = base / ".shadow-log"
    _cap_log_file(log_path)
    ts = _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    excerpt = prompt[:200].replace("\n", " ").replace("\t", " ")
    with log_path.open("a", encoding="utf-8") as f:
        f.write(f"{ts}\tscore={score:.3f}\tprompt={excerpt}\n")
