"""Render the deny message that Compass returns to Claude on UserPromptSubmit deny."""
from pathlib import Path
from string import Template


REASON_TO_EXPLANATION = {
    "no_resolution_found":
        "no valid resolution hash was found in the most recent assistant turn",
    "resolution_corrupt":
        "the candidate resolution file's content does not match its declared hash",
    "prompt_changed":
        "the user prompt has changed since the most recent resolution; the stored "
        "resolution references a different intent",
    "personas_changed":
        "one or more persona files have changed since the most recent resolution; "
        "re-run the council against current personas",
    "protocol_changed":
        "the resolution-loop protocol has changed since the most recent resolution",
    "verdict_not_resolved":
        "the most recent resolution concluded with a non-resolved verdict; "
        "iterate on the intent and re-run",
    "budget_exhausted_unresolved":
        "the clarification budget was exhausted before resolution; "
        "user input or substrate verifier is required to proceed",
}


_TEMPLATE_PATH_NAME = "deny-message.template"


def _load_template(plugin_root: str) -> Template:
    text = (Path(plugin_root) / "protocols" / _TEMPLATE_PATH_NAME).read_text(encoding="utf-8")
    return Template(text)


def render_deny_message(
    reason: str,
    prompt_excerpt: str,
    plugin_root: str,
    runs_root: str,
    abstractness_score: float = 0.0,
) -> str:
    """Render the deny message body. Always returns a string; never raises."""
    explanation = REASON_TO_EXPLANATION.get(
        reason,
        f"compass requires intent resolution before this prompt proceeds (reason: {reason})",
    )
    excerpt = prompt_excerpt[:200].replace("\n", " ")
    if len(prompt_excerpt) > 200:
        excerpt += "..."
    try:
        tpl = _load_template(plugin_root)
    except OSError:
        # Inline fallback if template file is missing.
        tpl = Template(
            "COMPASS_REVIEW_REQUIRED\n\n"
            "Reason: ${reason_explanation}\n\n"
            "Prompt excerpt: ${prompt_excerpt}\n"
            "Abstractness score: ${abstractness_score}\n\n"
            "Read ${plugin_root}/protocols/resolution-loop.md and execute the protocol. "
            "Write the resolution milestone to "
            "${runs_root}/compass/<UTC-date>/<resolution_hash>.json. "
            "Surface the resolution hash as plain text matching sha256:<64 hex chars>. "
            "Re-invoke the original UserPromptSubmit by emitting the resolved prompt as your "
            "next assistant turn (Claude Code re-presents it through the hook).\n"
        )
    return tpl.safe_substitute(
        reason_explanation=explanation,
        prompt_excerpt=excerpt,
        abstractness_score=f"{abstractness_score:.2f}",
        plugin_root=plugin_root,
        runs_root=runs_root,
    )
