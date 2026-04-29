# Compass Plugin

Intent-resolution gate for Claude Code. Sits in front of every UserPromptSubmit; when a heuristic detects abstractness, it denies until the user's intent is decomposed into an IBIS graph, refuted by a Watkins-discipline council, optionally substrate-verified (Dafny / Lean 4), and resolved with a content-addressed milestone — or the iteration budget is hit and the synthesis surfaces explicitly.

## Architecture

Compass is the platonic form of the council plugin. Where council reviews specs and diffs *before* tools fire, Compass reviews the *intent itself* before any spec is written. Both share the same gate-with-receipt mechanic via `jtech-substrate-core`.

Pipeline:
1. **UserPromptSubmit intercept** — `compass-trigger.sh` → `lib/trigger.py`
2. **Decompose** — IBIS graph (Issues / Positions / Arguments / Resolutions) + predicate set
3. **Ambiguity detection** — N parallel re-decompositions; consistency check
4. **Substrate triage** — NL-only / Dafny / Lean 4 (TLA+ / Z3 deferred to v2)
5. **Refutation council** — 3 Watkins personas + 1 substrate verifier slot
6. **EIG-ranked clarification** — bounded by 5 questions/session
7. **Resolve or refute** — write resolution milestone, re-invoke; or surface the gap

## Installation

1. Clone this repository:

   ```bash
   git clone https://github.com/YOUR_USERNAME/compass.git
   cd compass
   ```

2. Register it as a directory plugin in your Claude Code config:

   ```json
   {
     "extraKnownMarketplaces": {
       "compass": {
         "source": {"source": "directory", "path": "/path/to/where/you/cloned/compass"}
       }
     }
   }
   ```

3. Enable it in `~/.claude/settings.json`:

   ```json
   {"enabledPlugins": {"compass@compass": true}}
   ```

## Bypass & Logs

- `!compass-skip` prefix on a prompt — bypass for one invocation.
- `!compass` prefix — force compass to fire even when the heuristic wouldn't trigger.
- `COMPASS_SKIP=1` env var — bypass for the entire session.

**Data storage.** By default, Compass stores resolution milestones and logs (`.bypass-log`, `.shadow-log`) under `~/.compass/runs/`. Log files are auto-capped at 1 MB (last 500 lines retained) to prevent unbounded growth. Override the location with the `COMPASS_RUNS_DIR` environment variable.

## Status

v0.1.0 — under development. Open empirical question (same as council's): whether Compass adds *measurable signal* over a single Claude reviewer is not yet established. v1 ships the mechanism; signal-quality measurement is deferred.

## Testing

```bash
bash tests/run.sh                              # unit + smoke, no LLM
CI_RUN_LLM_TESTS=1 bash tests/schema/run.sh    # LLM-touching schema tests
```

## Honest claims (Watkins-discipline)

- Compass detects specific classes of incompleteness via a stated rubric and refutes with structured deny payloads. It does NOT promise "semantic perfection" of arbitrary requests.
- Self-critique without an external oracle regresses (Huang et al., ICLR 2024). The substrate verifier slot (Dafny / Lean) is the load-bearing oracle when one applies; without one, the 3-Watkins ensemble is variance-reduction over a stated rubric, not signal beyond it.
- Multi-agent debate alone does not add signal. Refutation against a verifier does.
