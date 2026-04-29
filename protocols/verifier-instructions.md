# Verifier Invocation Instructions

Per-substrate guidance for Phase 5 of the resolution loop. The verifier is `lib/verifier.py:run_verifier(substrate, spec_text)`.

## NL substrate

The NL verifier is a deterministic completeness checklist. It checks for:
- **Goal**: tokens like `goal:`, `objective:`, `achieve`, `build`, `implement`, `create`, `produce`, `generate`, `compute`, `calculate`
- **Success criterion**: tokens like `success:`, `done when`, `complete when`, `verify`, `test`
- **Constraint**: tokens like `constraint:`, `must not`, `cannot`, `forbidden`, `invariant`

Generate the spec_text by serializing the IBIS resolution + predicates as structured Markdown:

```
Goal: <issue.content of the root Issue>
Success: <evidence_required of all predicates>
Constraint: <text of all `must not` / `cannot` predicates>
```

If any of the three sections is missing, the verifier returns `status: "fail"` with a list of missing sections.

The NL verifier's authority is rubric-only. The substrate-verifier persona (Slot 4) treats `pass` as `confidence ≤ 0.5`.

## Dafny substrate

The Dafny verifier shells out to `dafny verify <tempfile>`. Skipped gracefully if `dafny` is not on PATH.

Generate spec_text as a Dafny method:

```dafny
method <method_name>(<params>)
  requires <precondition_predicates>
  ensures <postcondition_predicates>
{
  // implementation skeleton
}
```

Each predicate with `verifiable: true` and `substrate_hint: "dafny"` becomes a `requires` or `ensures` clause depending on whether it constrains input or output.

`pass` from Dafny is the strongest signal in v0.1.0. The substrate-verifier persona may use confidence up to 0.85.

## Lean 4 substrate

The Lean 4 verifier shells out to `lean <tempfile>`. Skipped gracefully if `lean` is not on PATH.

Generate spec_text as a Lean 4 theorem:

```lean
theorem <theorem_name> : <type_signature_derived_from_predicates> := by
  sorry  -- placeholder; presence of `sorry` will cause Lean to fail
```

For v0.1.0 we generate the theorem statement only; we do NOT attempt to discharge the proof. A `sorry` in the body causes Lean to emit a warning that the verifier translates as `status: "fail"`. To get a `pass`, the protocol must include lemma application via Lean's tactic library — that's v1.1+ territory (Lean Copilot integration).

In v0.1.0, `lean4` substrate selection is mostly aspirational — most theorem statements derived from predicates won't actually prove without manual tactic work. Document this in the synthesis narrative.

## Subprocess budgets

| Substrate | Timeout | What happens on timeout |
|---|---|---|
| `nl` | none (pure Python) | not applicable |
| `dafny` | 30s | `status: "timeout"` |
| `lean4` | 60s | `status: "timeout"` |

Timeouts are treated as `concern` not `blocking` — the predicates may be decidable in principle but exceed practical bounds.

## When the binary is absent

`shutil.which()` checks PATH. If absent:
- `dafny` absent → `status: "skipped"`, `error: "dafny binary not found on PATH"`
- `lean` absent → `status: "skipped"`, `error: "lean binary not found on PATH"`

The substrate-verifier persona must acknowledge this in its narrative — "no formal evidence; council operates on rubric only" — and downgrade confidence to ≤ 0.3.

NL substrate is always available (no external binary).

## Honesty discipline

The substrate verifier is the load-bearing oracle when one applies. Without it, the 3 Watkins personas are doing rubric-bound ensembling, not external-oracle refutation. The literature (Huang et al. ICLR 2024) is unambiguous: self-critique without an external verifier regresses. Surface this in the resolution narrative whenever `nl` is selected or `skipped` fires.
