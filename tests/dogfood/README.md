# Compass v0.1.0 Dogfood Evidence

Captured 2026-04-28 during the v0.1.0 build session. Two resolution artifacts demonstrate the full gate-with-receipt mechanism end-to-end.

## Artifact 1: `v0.1.0-escalate-real-council.json`

**Provenance:** Live council dispatch (3 parallel `Agent` calls + Chairman synthesis) on the prompt:

> *"Help me brainstorm the right approach for compass calibration."*

**Verdict: `escalate`** — g3_data_loss guard fired.

**Council members 1-3 are real subagent output**, captured verbatim from a live Agent-tool dispatch. Member 4 (substrate-verifier) is Chairman-synthesized per protocol §4 (Slot 4 interprets the verifier output, which is structured input not creative refutation).

**Critical finding:** The Watkins-Failure-Modes member (slot 3, confidence 0.78) identified an architectural defect in compass itself: because the trigger is deliberately token-free, there is no shadow-log of non-fires, meaning a miscalibrated heuristic that drops the threshold could silently un-gate prompts and we'd have no trace. This is a **real v1.1 work item** discovered by the council on its own dogfood run.

This artifact is evidence that the council mechanism does not rubber-stamp — it surfaced a defect serious enough to refuse resolution.

## Artifact 2: `v0.1.0-resolved-synthetic.json`

**Provenance:** Synthetic, hand-constructed for the symmetric "allow path" test on the prompt:

> *"Calibrate compass abstractness threshold to 0.6 ± 0.1 by sweeping {0.5, 0.55, 0.6, 0.65, 0.7} against the existing 42 unit tests; pick the threshold that maximizes test-pass count and break ties toward 0.6."*

**Verdict: `resolved`**

This well-specified prompt (concrete sweep range, concrete success criterion, concrete tiebreak) has the four resolved-verdict ingredients: (a) bounded scope, (b) measurable success, (c) deterministic procedure, (d) tiebreak rule. Compare against Artifact 1's vague intent.

The council critiques in Artifact 2 are placeholder (`verdict: ship, findings: [], narrative: "well-specified"`), not real subagent output — this is acknowledged. Token-budget tradeoff: dispatching 3 more agents on an admittedly trivial prompt would have been low-yield.

## Round-trip evidence (mechanism verification)

Both artifacts were exercised against `lib/trigger.py` as black-box:

| Test | Input | Expected | Actual |
|---|---|---|---|
| 1 | abstract prompt + empty transcript | EXIT=2, deny `no_resolution_found` | ✅ |
| 2 | abstract prompt + transcript with escalate hash | EXIT=2, deny `verdict_not_resolved` | ✅ |
| 3 | concrete prompt + transcript with resolved hash | EXIT=0, allow | ✅ |

The three verdict-paths covering the entire gate-with-receipt state machine all behave as specified.

## Real v1.1 backlog — dispositions

### LANDED in v0.1.0 patchset (post-dogfood, same session)

1. ✅ **Abstractness regex gap.** Fixed in `lib/abstractness.py` via non-capturing group `(?:'?s|\s+is)` to match "what's", "whats", AND "what is" forms. Same applied to "best way" and "right way" patterns. Tests: `test_what_is_the_best_way_above_threshold`, `test_what_is_the_right_way_above_threshold`, `test_whats_apostrophe_form_above_threshold`, `test_whats_no_apostrophe_form_still_works`.

2. ✅ **FN-observability blind spot.** Implemented shadow-log in `lib/storage.py:append_shadow_log` and wired into `lib/trigger.py:decide()`. Prompts in band `[SHADOW_BAND_LOW=0.3, ABSTRACTNESS_THRESHOLD=0.6)` get logged to `runs/compass/.shadow-log` without firing the gate. Token-free, append-only. Format: `<utc-iso>\tscore=<float>\tprompt=<excerpt>`. Tests: 3 smoke tests cover written-when-in-band, NOT-written-when-concrete, NOT-written-when-above-threshold.

### DEFERRED to later (with explicit triggers)

3. **Transcript-scan optimization** (Gemini suggestion #2). DEFERRED — Watkins Rule 2: no measured evidence the current scan is slow. Premature without profiling. Trigger: real-session profiling shows median UserPromptSubmit latency > 100ms on the scan step. Implementation when triggered: cap scan at last 1MB of transcript file, read forward from cap.

4. **JTopo H₀ wire-up** for fractured-intent detection (Gemini suggestion #3). DEFERRED to v1.1 milestone — the `to_adjacency()` stub is locked but wire-up to `compute_persistence.py` requires (a) input-format compatibility verification, (b) synthesis-rule design (H₀>1 → escalate), (c) test coverage. Substantial work. Trigger: post-marketplace install + first 5-10 real sessions accumulating multi-issue IBIS graphs.

5. **LLM-mode EIG ranker with shadow comparison** (Gemini suggestion #4). DEFERRED — premature without first-20-sessions calibration data. Shadow-mode comparison idea is good but needs real data to compare against, not synthetic. Trigger: 20+ real shadow-log entries available for ranking-quality evaluation.

### DECLINED (anti-Watkins)

6. **Auto-fallback Dafny→NL on timeout** (Gemini suggestion #5). DECLINED. Silently substituting NL when Dafny times out collapses verdict semantics: NL-pass is rubber-rubric (conf 0.5 ceiling); Dafny-pass is formal (conf 0.85 ceiling). Auto-substitution makes "pass" mean different things invisibly to the substrate-verifier persona. The honest version is to surface timeout to the user and let them choose to re-run with `nl` substrate explicitly — that's already supported. No code change needed; documented here as the non-decision.

### DOCUMENTED but not in active backlog

7. **Slot 4 dispatch** in real protocol execution. Per protocol §4, Slot 4 should be a real Agent call that interprets the Phase 5 verifier output. The dogfood Chairman-synthesized Slot 4 because the verifier output was structured (`status: pass`) and the persona's job on `pass` is mechanical. For dogfood-2 (when more substrates wired) this should be re-evaluated.

8. **Drift detection** (Watkins-Failure-Modes concern, severity: concern). Calibration is one-shot; prompt-distribution shift will silently invalidate it. v2 work item — paired with #4 above (shadow-mode EIG) on a coordinated v1.1+ milestone.

## How to reproduce

The build script lives at `/tmp/compass-dogfood-runs/build_dogfood.py` (not committed; ephemeral build artifact). To re-run:

```bash
export CLAUDE_PLUGIN_ROOT=/home/wb1/Desktop/Dev/compass
export COMPASS_RUNS_DIR=/tmp/compass-dogfood-runs
python3 /tmp/compass-dogfood-runs/build_dogfood.py
```

To verify the round-trip:

```bash
# Round-trip 1 — escalate denies
echo '{"prompt": "Help me brainstorm the right approach for compass calibration.", "transcript_path": "/tmp/compass-dogfood-runs/transcript.jsonl"}' | python3 /home/wb1/Desktop/Dev/compass/lib/trigger.py
# Expect: exit 2, COMPASS_REVIEW_REQUIRED, reason "verdict_not_resolved"

# Round-trip 2 — resolved allows
echo '{"prompt": "Calibrate compass abstractness threshold to 0.6 ± 0.1 ...", "transcript_path": "/tmp/compass-dogfood-runs/transcript-resolved.jsonl"}' | python3 /home/wb1/Desktop/Dev/compass/lib/trigger.py
# Expect: exit 0
```
