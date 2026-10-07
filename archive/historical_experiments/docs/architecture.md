# Platform Architecture

The Crypto Quantitative Systems Platform enforces strict domain boundaries to ensure deterministic computation, causal isolation, and modular testability.

## Architectural Layers

```text
             ┌─────────────────────┐
             │     MARKET DATA     │
             └──────────┬──────────┘
                        ↓
             ┌─────────────────────┐
             │ P01 MARKET STATE    │
             └──────────┬──────────┘
                        ↓
             ┌─────────────────────┐
             │ P02 STRATEGY        │
             └──────────┬──────────┘
                        ↓
             ┌─────────────────────┐
             │ P03 RISK            │
             └──────────┬──────────┘
                        ↓
             ┌─────────────────────┐
             │ P04 RESEARCH        │
             └──────────┬──────────┘
                        ↓
             ┌─────────────────────┐
             │ P05 PORTFOLIO       │
             └──────────┬──────────┘
                        ↓
             ┌─────────────────────┐
             │ P06 EXECUTION       │
             └──────────┬──────────┘
                        ↓
             ┌─────────────────────┐
             │ P07 OPERATIONS      │
             └─────────────────────┘
```

## Immutable Engineering Laws

### LAW 01 — Temporal Causality
At timestamp `T`, no component may consume information that was unavailable at `T`. Historical future information must never leak into a historical decision.

### LAW 02 — Deterministic Reproducibility
For identical input data and configuration:
`P(D, Config) Run A ≡ P(D, Config) Run B`
The same historical dataset must produce the same state and decision outputs.

### LAW 03 — Domain Isolation
Higher-level systems may consume lower-level contracts. Lower-level systems must never depend on higher-level decisions. Market intelligence does not know about account balances. Strategy does not calculate portfolio risk.

### LAW 04 — State Provenance
Every important decision must be traceable to its originating market events (e.g., BOS, CHOCH, Liquidity Sweep). The system should be able to answer: "Why did this trade exist?"

### LAW 05 — Fail Closed
When information is ambiguous, incomplete or invalid, `NO_TRADE` is preferable to an unsupported assumption. Rejection states are legitimate outputs.

### LAW 06 — Rejected Information Is Still Research Data
Rejected setups are not discarded. These observations become vital research telemetry.

### LAW 07 — Hypotheses Must Remain Isolated
A strategy hypothesis must be independently measurable. No hidden cross-contamination of rules, parameters or outcome attribution.

### LAW 08 — No Optimization Before Evidence
The platform does not add indicators, filters or parameters simply because a backtest looks weak. Changes require explicit out-of-sample justification.
