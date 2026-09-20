# Deployed Strategies Vault

This directory is the **production strategy vault**. It may contain ONLY
strategies that have completed the FULL authorized qualification chain:

```
HYPOTHESIS -> CANDIDATE -> DEVELOPMENT TEST -> FORENSIC REVIEW
    -> VALIDATION -> OOS -> QUALIFICATION -> DEPLOYED STRATEGY -> LIVE
```

## Admission requirements

A deployed strategy directory must contain sufficient provenance and
configuration to identify:

- strategy ID
- source hypothesis (hypotheses/<HYPOTHESIS-ID>/)
- source candidate (hypotheses/<HYPOTHESIS-ID>/candidates/<CANDIDATE-ID>/)
- qualification evidence (production/qualification gate artifacts)
- validation evidence (VAL partition, NOT Development)
- OOS evidence (out-of-sample partition)
- approved configuration (frozen strategy config)
- risk configuration (risk_engine limits, sizing, exposure caps)
- deployment state (paper / live, activation date, approval record)
- deployment provenance (commit, data versions, engine version)

## Hard rule

**A Development or Validation result NEVER automatically enters this
directory.** Positive DEV evidence only creates/supports a candidate for
further investigation (see `hypotheses/README.md` and the governance
promotion gates). No candidate in the current research lab has passed
qualification, therefore this vault is intentionally empty.
