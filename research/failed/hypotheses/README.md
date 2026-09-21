# QCP — Hypothesis-Centered Research Laboratory

> **Rule: QCP researches hypotheses; it does not assume them to be true.**
> **Rule: POSITIVE DEVELOPMENT RESULT ≠ WINNER.**

Hierarchy:

```text
HYPOTHESIS  — research head / concept
  └─ RESEARCH    — observations + positive/negative evidence ledgers
  └─ CANDIDATES  — concrete mechanism/configuration/asset/timeframe combos
       └─ TESTS  — one controlled investigation, one exact configuration
            └─ RESULTS / EVIDENCE — provenance-rich evidence
```

Layout per hypothesis `<HYPOTHESIS-ID>/`:

```text
<hypothesis-id>/
  hypothesis.md        — definition, question, null, falsification criteria
  candidates.md        — candidate index for this hypothesis
  candidates/<CANDIDATE-ID>/
    candidate.md
    tests/<TEST-ID>/
      test_plan.md
      config.yaml
      results.json
      report.md
  research/
    observations.md
    positive_evidence.md
    negative_evidence.md
```

Global indexes (this directory):

- `HYPOTHESES_LIST.md` — every hypothesis
- `CANDIDATES_LIST.md` — every candidate

Status models are enforced by `governance.py`.
Indexes are generated/validated by `governance.py` — never hand-edit counts.

Separation rules:

- (A) Cross-scale mechanism transfer (`H-FRACTAL-01`) and
  (B) Multi-timeframe confirmation/confluence (`H-FRACTAL-02` placeholder)
  are SEPARATE hypotheses. Never merge.
- Do NOT create a new hypothesis for a different asset/timeframe/parameter.
  Those are candidate/test dimensions.
- Negative evidence is preserved. Nothing is silently deleted.
- Migration is NON-DESTRUCTIVE: original artifacts stay in place;
  `qcp/hypotheses/*/candidates/*/tests/*/results.json` stores a
  provenance pointer + aggregate summary, never a silent copy that
  diverges. Full ledgers remain at `original_path`.

Promotion guards (enforced in code + tests):

- Development `POSITIVE_SIGNAL` NEVER auto-promotes a candidate to
  `VALIDATED` / `VALIDATION_CANDIDATE` / qualified / production / capital.
- Only explicit governance authorization with VAL (+ adversarial) and
  untouched-OOS evidence may advance lifecycle.
