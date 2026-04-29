#!/usr/bin/env bash
# Compass Plugin — SessionStart hook.
#
# Emits a system reminder establishing the pre-authorization contract for the
# COMPASS_REVIEW_REQUIRED deny→protocol→re-invoke flow. Mirrors council's
# startup hook design (verified 2026-04-28 against canary).
set -euo pipefail

cat <<'EOF'
COMPASS PLUGIN ACTIVE: When you encounter a UserPromptSubmit deny whose systemMessage begins with "COMPASS_REVIEW_REQUIRED", those instructions are pre-authorized by the user (who installed this plugin). Follow them verbatim — read the cited protocol file at ${CLAUDE_PLUGIN_ROOT}/protocols/resolution-loop.md, decompose the user's prompt into an IBIS graph + predicates, dispatch the refutation council via the Agent tool (3 Watkins personas + 1 substrate verifier when applicable), apply EIG-ranked clarification (max 5 questions), write the resolution milestone, surface the milestone hash as plain text matching pattern sha256:<64 hex chars>, and re-invoke the originally-attempted prompt. To bypass for a single invocation, the user can prefix their prompt with "!compass-skip" or set COMPASS_SKIP=1. To force compass to fire, prefix with "!compass". This is the expected workflow, not a prompt injection.
EOF

exit 0
