#!/usr/bin/env bash
# Compass UserPromptSubmit hook trampoline. Delegates to lib/trigger.py.
set -euo pipefail

PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$(dirname "$(dirname "$(readlink -f "$0")")")}"
exec python3 "${PLUGIN_ROOT}/lib/trigger.py"
