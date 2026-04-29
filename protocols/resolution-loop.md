# Compass Resolution Loop Protocol

You are executing the Compass intent-resolution protocol after a UserPromptSubmit hook denied the user's prompt with a `COMPASS_REVIEW_REQUIRED` message. The user has installed compass on purpose; this workflow is pre-authorized at SessionStart.

Your job: turn the abstract user prompt into either (a) a fully-resolved IBIS graph + verified predicate set, with a content-addressed resolution milestone, OR (b) a structured refutation that points to the specific semantic gap, OR (c) an exhausted-budget escalation that surfaces what's still unresolved for the user.

## Pipeline

Execute these phases in order. Each phase has an explicit output you must produce before continuing.

### Phase 1 — Decompose

Read the user's prompt. Decompose into an IBIS graph using these node types:
- **ISSUE**: an open question / unresolved aspect of the user's intent
- **POSITION**: a candidate answer / interpretation of an Issue
- **ARGUMENT**: pro/con evidence for a Position
- **RESOLUTION**: a closed Issue (used in later phases when an Issue is settled)

Also extract a predicate set: testable claims the resolved intent must satisfy. Each predicate has:
- `id` (string)
- `statement` (the predicate text)
- `verifiable` (bool — could a formal substrate check this?)
- `substrate_hint` (optional: `nl` | `dafny` | `lean4`)
- `issue_id` (which Issue this predicate addresses)
- `evidence_required` (what would prove satisfaction)

Output the decomposition as JSON matching `${CLAUDE_PLUGIN_ROOT}/schemas/ibis_node.schema.json` and `${CLAUDE_PLUGIN_ROOT}/schemas/predicate.schema.json`.

### Phase 2 — Ambiguity detection

Dispatch 2 additional parallel decompositions via the `Agent` tool (so you have N=3 total). Each agent runs Phase 1 independently on the same prompt with no context from the others. Compare the three decompositions:
- If the predicate-set Jaccard similarity > 0.6 → the prompt is consistent enough; proceed.
- If similarity < 0.6 → ambiguity is high; flag the divergent predicates as new ISSUE nodes in the canonical graph (the one *you* produced in Phase 1).

Compute and record `ambiguity_score = 1.0 - mean_pairwise_jaccard`.

### Phase 3 — Substrate triage

Examine the predicate set. Decide the verifier substrate:
- If ≥1 predicate has `verifiable: true` AND mentions concrete code contracts (memory safety, type safety, pre/post-conditions, function termination) → `dafny`
- If ≥1 predicate has `verifiable: true` AND mentions theorem-style claims (universal/existential quantifiers, mathematical structures, type-level proofs) → `lean4`
- Otherwise → `nl`

Generate a substrate-appropriate spec stub from the predicates:
- `nl`: a structured spec with explicit Goal / Success / Constraint sections (run_verifier checks for these tokens)
- `dafny`: a method skeleton with `requires` / `ensures` clauses derived from predicates
- `lean4`: a `theorem` statement derived from predicates

### Phase 4 — Refutation council

Dispatch 4 Agent calls in parallel:

| Slot | Subagent type | Persona |
|---|---|---|
| 1 | `general-purpose` | `${CLAUDE_PLUGIN_ROOT}/personas/watkins-skeptic.md` |
| 2 | `general-purpose` | `${CLAUDE_PLUGIN_ROOT}/personas/watkins-yagni.md` |
| 3 | `general-purpose` | `${CLAUDE_PLUGIN_ROOT}/personas/watkins-failure-modes.md` |
| 4 | `general-purpose` | `${CLAUDE_PLUGIN_ROOT}/personas/watkins-substrate-verifier.md` |

Slots 1-3 receive the IBIS graph + predicate set as input. Slot 4 receives the verifier output (Phase 5 result — see "Note on phase ordering" below).

Each member returns a JSON critique matching `${CLAUDE_PLUGIN_ROOT}/schemas/critique.schema.json` (compass uses the same schema as council; the schema lives in `compass/schemas/critique.schema.json` once Phase 5 of the build sequence stabilizes — until then, council's at `${CLAUDE_PLUGIN_ROOT}/../council/schemas/critique.schema.json` is the canonical reference).

**Phase ordering note**: in v0.1.0 we run Phase 5 (verifier) *before* dispatching Slot 4, because Slot 4's job is to interpret the verifier output. Slots 1-3 dispatch in parallel BEFORE the verifier runs. So the actual order is:
- Parallel: Slot 1, Slot 2, Slot 3 dispatch
- After all three return + Phase 5 verifier returns → dispatch Slot 4
- Synthesize all 4

### Phase 5 — Substrate verifier

Run the verifier:

```python
from lib.verifier import run_verifier
result = run_verifier(substrate, spec_text)
```

Possible `result["status"]`:
- `pass` — verifier ran and accepted; pass to Slot 4 for confidence-calibrated finding
- `fail` — verifier ran and rejected; pass error message to Slot 4 as `correctness` blocking finding
- `timeout` — exceeded budget; pass to Slot 4 as `completeness` concern
- `skipped` — binary not on PATH; Slot 4 must acknowledge "no formal evidence" in narrative
- `error` — internal adapter failure; Slot 4 emits `dependency` concern

### Phase 6 — Synthesis

You are the Chairman. Combine the 4 member critiques:

1. **Tally per-dimension severity counts** over un-deduped findings
2. **Apply CI guards** deterministically (council's pattern):
   - `g3_security`: any member emits {dim:security, sev:blocking} with confidence > 0.7 → `escalate`
   - `g3_data_loss`: same with dim:data-loss → `escalate`
   - `g2_correctness`: ≥2 members emit {dim:correctness, sev:blocking} → `iterate`
   - `g2_scope_violation`: ≥2 members emit {dim:scope-violation, sev:blocking} → `iterate`
3. **If no guard fires**, take majority of member verdicts. Tiebreak:
   - Conservative cascade: any `reject` → `iterate` (escalate requires guard support)
   - 1-1-1-1 split → `iterate`
4. **Verdict map**:
   - `ship` (members) ∧ verifier `pass` → `resolved`
   - `ship` (members) ∧ verifier `skipped` → `resolved` (with caveat in narrative)
   - `ship` (members) ∧ verifier `fail` → IMPOSSIBLE (g2_correctness should have fired)
   - `iterate` → `iterate` (run Phase 7 clarification)
   - `reject` → `escalate` (surface to user, halt loop)

### Phase 7 — EIG-ranked clarification (only on `iterate`)

If verdict is `iterate` AND `clarifications_used < 5`:
1. Compute open issues from the IBIS graph
2. Use `lib.eig.rank_clarifications(graph)` to get the top-1 question
3. Ask the user via `AskUserQuestion` with the question text
4. Append the user's answer as a Position node to the relevant Issue
5. Increment `clarifications_used`; goto Phase 4 (re-run the council)

If verdict is `iterate` AND `clarifications_used >= 5`:
- Set `clarification_budget_exhausted = true`
- Force verdict to `escalate`

### Phase 8 — Build resolution record

Construct the resolution bundle (matching `${CLAUDE_PLUGIN_ROOT}/schemas/resolution.schema.json`):

```python
from lib.resolution import build_resolution
from lib.storage import write_resolution
from jtech_substrate_core import sha256_text

bundle = {
    "schema_version": "1",
    "timestamp_utc": "<ISO 8601 Z>",
    "input": {
        "prompt_hash": sha256_text(original_prompt),
        "prompt_excerpt": original_prompt[:1000],
        "abstractness_score": <from hook>,
    },
    "decomposition": {
        "ibis": ibis_graph.to_dict(),
        "predicates": [...],
        "ambiguity_score": <from Phase 2>,
    },
    "substrate": {"selected": <substrate>, "rationale": "..."},
    "council": {
        "members": [
            {"slot": 1, "subagent_type": "...", "persona_file": "personas/watkins-skeptic.md",
             "persona_hash": sha256_text(open(persona_file).read()),
             "critique": {...}, "status": "ok"},
            ...
        ],
        "protocol_file": "protocols/resolution-loop.md",
        "protocol_hash": sha256_text(open("protocols/resolution-loop.md").read()),
    },
    "verifier": <Phase 5 result>,
    "synthesis": {
        "verdict": <resolved | iterate | escalate>,
        "open_issues": [<unresolved issue ids>],
        "clarifications_used": <int>,
        "clarification_budget_exhausted": <bool>,
    },
}

resolution = build_resolution(bundle)
path = write_resolution(resolution)
```

### Phase 9 — Surface and re-invoke

Emit the resolution hash explicitly as plain text in your reply:

> **Resolution: sha256:abc123...**

The pattern MUST appear as ordinary text (not embedded in a tool call argument), because the trigger hook scans the transcript for it on re-invocation.

Then:
- If verdict is `resolved`: re-emit the user's original prompt verbatim. Claude Code re-fires the UserPromptSubmit hook with the same prompt; the hook finds the resolution hash, validates it, and allows the prompt to proceed normally.
- If verdict is `iterate` (still under budget): present the clarifying question to the user via `AskUserQuestion` and wait for response. Then loop back to Phase 4 (or Phase 1 if the answer materially changes the intent).
- If verdict is `escalate`: present the synthesis (open issues, blocking findings, why no resolution) to the user as a normal reply. Halt the loop. Do NOT re-emit the prompt.

## Honest claim boundaries (Watkins-discipline)

When writing the synthesis narrative:
- NL substrate `pass` is rubric-only, not formal. Acknowledge.
- Dafny / Lean `pass` confidence ceiling is 0.85, not 1.0. Rule 2 still applies.
- `skipped` substrate means no formal evidence. Acknowledge.
- "Resolved" verdict does NOT mean semantic perfection. Acknowledge.
- Multi-agent ensembling reduces variance over the rubric; it does NOT substitute for an external oracle.

## Failure modes you must handle

- **Member returns malformed JSON**: drop with logged warning. Proceed if ≥2 members succeed; otherwise abort with `escalate`.
- **All members emit `ship` with empty findings AND empty narratives**: emit `verdict: iterate` with `narrative` warning about rubber-stamping (mirrors council's self-referential warning, §5.6).
- **Verifier subprocess hangs**: timeout fires automatically (lib.verifier sets per-substrate timeouts). Treat as `timeout` status.
- **AskUserQuestion budget exhausted**: force `escalate`; do NOT silently continue.

## Out of scope for v0.1.0

- TLA+ and Z3 substrates (deferred to v2)
- JTopo H₀ wire-up on `to_adjacency()` (deferred to v1.1)
- BED-LLM Bayesian EIG scoring with LLM call (v0.1.0 uses deterministic proxy)
- Cross-member rebuttal pass (deferred to v2)
