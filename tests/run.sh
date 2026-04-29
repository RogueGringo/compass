#!/usr/bin/env bash
# Compass test runner. Mirrors council/tests/run.sh.
set -euo pipefail

cd "$(dirname "$0")/.."

echo "=== Unit tests ==="
python3 -m pytest tests/unit/ -v

echo ""
echo "=== Smoke tests ==="
if [ -d "tests/smoke" ] && [ -n "$(ls tests/smoke/test_*.py 2>/dev/null || true)" ]; then
    python3 -m pytest tests/smoke/ -v
else
    echo "(no smoke tests yet)"
fi

echo ""
echo "=== Schema tests ==="
if [ "${CI_RUN_LLM_TESTS:-}" = "1" ] && [ -d "tests/schema" ]; then
    python3 -m pytest tests/schema/ -v
else
    echo "Skipping schema tests: set CI_RUN_LLM_TESTS=1 to enable."
fi
