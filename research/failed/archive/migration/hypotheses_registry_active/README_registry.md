# QCP Hypothesis Research Registry

> **"QCP researches hypotheses; it does not assume them to be true."**

---

## 1. Why Hypotheses Exist

A hypothesis is a precisely formulated, falsifiable question about a potential market mechanism.
Hypotheses exist to impose scientific discipline on research: every idea must be stated formally,
every test must have pre-registered acceptance and rejection criteria, every result — positive or
negative — must be permanently preserved.

A hypothesis is **NOT**:
- A strategy.
- Evidence of profitability.
- A validated edge.
- A deployment candidate.

A positive Development result is **not** proof of anything. A negative result is **equally
valuable research output** — it eliminates dead ends and prevents capital allocation to
mechanisms that do not work.

---

## 2. How to Create a New Hypothesis

1. **Copy the template**: `hypotheses/HYPOTHESIS_TEMPLATE.md`
2. **Assign a stable ID**: `H-<FAMILY>-<NUMBER>` (e.g. `H-FRACTAL-02`). IDs are never reused.
3. **Create a directory**: `hypotheses/proposed/H-FAMILY-NN-short-slug/`
4. **Populate three files**:
   - `hypothesis.md` — filled template
   - `experiment_plan.md` — detailed experimental design
   - `status.yaml` — machine-readable lifecycle state
5. **Register in `registry.yaml`** by adding an entry under `hypotheses:`.
6. **Verify** with: `python -m hypotheses.hypothesis_governance validate H-FAMILY-NN`

Required evidence before a hypothesis can leave `PROPOSED`:
- A documented market observation or forensic signal that motivates the question.
- A clearly stated null hypothesis.
- At least one concrete falsification criterion that would definitively reject the hypothesis.

---

## 3. Required Evidence

| Stage | Evidence Required |
|---|---|
| PROPOSED → FORMALIZED | Written observation, null hypothesis, falsification criterion |
| FORMALIZED → IMPLEMENTATION_READY | Experimental design, data partition assignments, metrics pre-registered |
| IMPLEMENTATION_READY → DEVELOPMENT_TEST | Implementation verified, causality audit signed off |
| DEVELOPMENT_TEST → FORENSIC_REVIEW | Development results recorded, reproducibility manifest present |
| FORENSIC_REVIEW → VALIDATION_CANDIDATE | Forensic review signed (no causality violations, no data leakage) |
| VALIDATION_CANDIDATE → VALIDATION | Governance approval (do not touch Validation partition without explicit authorization) |
| VALIDATION → OOS | Validation results positive under pre-registered thresholds |
| OOS → QUALIFIED | OOS positive; multi-period robustness confirmed |

---

## 4. Lifecycle

```
PROPOSED
   ↓
FORMALIZED
   ↓
IMPLEMENTATION_READY
   ↓
DEVELOPMENT_TEST
   ↓
FORENSIC_REVIEW
   ↓
VALIDATION_CANDIDATE
   ↓
VALIDATION
   ↓
OOS
   ↓
QUALIFIED  /  REJECTED  /  INVALIDATED  /  ARCHIVED
```

Filesystem location and `registry.yaml` status **must remain consistent**.
`hypothesis_governance.py` enforces valid transitions and prevents silent state skipping.

Terminal states: `QUALIFIED`, `REJECTED`, `INVALIDATED`, `ARCHIVED`.

---

## 5. Falsification Requirements

Every hypothesis **must** specify:

1. **Null hypothesis** — the default assumption the research seeks to challenge.
2. **Falsification criteria** — concrete, pre-registered thresholds that, if met, require rejection.
3. **Possible outcome classes** — at minimum: strong support, partial support, no support,
   invalidation.

A hypothesis with no falsification criterion is not a hypothesis — it is a belief.
Accepting a hypothesis without meeting pre-registered acceptance criteria is data snooping.

---

## 6. Relationship Between Hypotheses, Experiments, Strategies, and Results

```
Hypothesis (this registry)
    │
    ├── One or more Experiments (research/experiments/)
    │       │
    │       └── Result records (research/lifecycle/experiment_ledger.py)
    │
    ├── Forensic Review (documented in hypothesis.md)
    │
    └── Decision → Strategy Candidate (only if QUALIFIED)
```

Hypotheses are not strategies. A qualified hypothesis may become an **implementation candidate**,
but it still requires:
- Production-equivalent execution testing (paper trading / burn-in).
- Risk firewall clearance.
- Explicit governance approval for capital deployment.

---

## 7. Research Governance Rules

1. **Do not modify existing experiment results.**
2. **Do not promote a hypothesis to VALIDATION merely because Development is positive.**
3. **Do not treat positive R, high win rate, high PF, or attractive equity curves as proof.**
4. **Do not unlock OOS or live capital without full QUALIFIED status.**
5. **Do not combine Experiment A (cross-scale transfer) and Experiment B (MTF confirmation) — they test different questions.**
6. **Every experiment must record**: repository commit, experiment ID, data version, partition,
   asset universe, timeframe set, bar horizon, fees, slippage, collision semantics, re-entry
   semantics, risk model, and (where applicable) random seed and configuration hash.
7. **Negative results must never be deleted.** They are permanent research assets.
8. **Hypothesis IDs are never reused.** Once assigned, an ID is permanently associated with
   its hypothesis, even after rejection or archival.

---

## 8. How an Accepted Hypothesis Becomes an Implementation Candidate

1. Hypothesis reaches `QUALIFIED` status via the full lifecycle.
2. A formal proposal is written linking hypothesis ID, experiment IDs, and result artifacts.
3. The proposal is reviewed against the existing canonical strategy governance.
4. If approved, a `strategy_candidate` directory is created (outside this registry).
5. Paper-trading burn-in is conducted under the existing forward-paper daemon.
6. Capital is deployed only after burn-in passes all release gates.

---

## 9. How Rejected Hypotheses Are Preserved

Rejected hypotheses move to `hypotheses/rejected/` and their `status.yaml` records:
- `status: REJECTED` or `status: INVALIDATED`
- `decision_date`
- `decision_rationale`
- `related_experiments` (all experiment IDs)
- `final_metrics` (summary statistics from the last evaluation)

The `hypothesis.md` and `experiment_plan.md` are preserved in full.
The `registry.yaml` entry is updated but **never removed**.

---

## 10. Why Negative Results Must Never Be Deleted

Negative results:
- Prevent the same dead-end idea from being re-investigated (saving research capital).
- Provide calibration data for understanding mechanism boundaries.
- Are required for honest multiple-hypothesis testing correction (Bonferroni).
- Constitute the empirical record that distinguishes a research program from speculation.

If a negative result is deleted, the registry loses the ability to prevent future researchers
from repeating failed experiments. The cost of a failed experiment is paid once; deleting
the result means paying it again.

---

## 11. Architecture

```
hypotheses/
├── README.md                          ← This file
├── registry.yaml                      ← Machine-readable central registry (never reuse IDs)
├── HYPOTHESIS_TEMPLATE.md             ← Template for new hypotheses
├── hypothesis_governance.py           ← Lifecycle engine + CLI commands
│
├── proposed/                          ← Ideas not yet formalized
├── active/                            ← Formalized; under development
│   └── H-FRACTAL-01-cross-scale.../  ← One directory per hypothesis
│       ├── hypothesis.md
│       ├── experiment_plan.md
│       └── status.yaml
├── testing/                           ← In DEVELOPMENT_TEST or FORENSIC_REVIEW
├── validated/                         ← Passed VALIDATION gate
├── rejected/                          ← REJECTED or INVALIDATED (permanent)
└── archived/                          ← Superseded but not invalidated
```

Python module: `hypotheses.hypothesis_governance`
- Integrates with existing `research.lifecycle.experiment_ledger` for cross-references.
- Reads `research.timeframe_sets` for timeframe set metadata (by ID, no style assumptions).

---

## 12. Tests

Tests are located in `tests/unit/research/test_h_fractal_01_registry.py`.

Coverage includes:
- Valid hypothesis creation and ID format enforcement
- Unique ID prevention (no duplicates)
- Invalid lifecycle transitions (e.g. PROPOSED → OOS)
- Valid lifecycle transitions (step-by-step)
- Registry YAML synchronization
- Missing required field detection
- Malformed hypothesis detection
- Experiment-to-hypothesis cross-references
- Preservation of rejected hypotheses (immutability)
- Prevention of accidental VALIDATION/OOS promotion without authorization
- H-FRACTAL-01 specific assertions

Run: `PYTHONPATH=. pytest tests/unit/research/test_h_fractal_01_registry.py -v`

---

## 13. Future Usage

When the next research command is issued:

1. A new hypothesis ID is assigned: `H-FRACTAL-02`, `H-MOMENTUM-01`, etc.
2. A directory is created in `hypotheses/proposed/`.
3. The template is filled out.
4. `hypothesis_governance.py validate` is run.
5. Research proceeds through the lifecycle with evidence at each gate.

H-FRACTAL-01 is the **first registered hypothesis** in this registry. Its status is `ACTIVE`
(lifecycle state: `FORMALIZED`). No testing has begun. No results exist. This is intentional.

---

*Last updated: 2026-09-19*
*Registry version: 1.0.0*
