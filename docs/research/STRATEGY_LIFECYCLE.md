# Crypto Trading Platform — Strategy Lifecycle & Governance

**Document Version:** 1.0.0  
**Classification:** Research, Validation & Operational Governance  

---

## 1. End-to-End Strategy State Machine

A trading strategy progresses through strict, unidirectional evidence tiers:

```
┌────────────────────────────────────────────────────────┐
│ 1. HYPOTHESIS & CODE GENERATION                        │
│    Subclasses BaseStrategy; specifies parameter schema │
└───────────────────────────┬────────────────────────────┘
                            │
                            ▼
┌────────────────────────────────────────────────────────┐
│ 2. HORIZON ECONOMIC SCREEN                             │
│    Cost/Stop Ratio must be <= 0.33                     │
└───────────────────────────┬────────────────────────────┘
                            │
                            ▼
┌────────────────────────────────────────────────────────┐
│ 3. CAUSAL WALK-FORWARD RESEARCH                        │
│    DEV (2021-22) -> VAL (2023-24) -> OOS (2024-26)    │
└───────────────────────────┬────────────────────────────┘
                            │
                            ▼
┌────────────────────────────────────────────────────────┐
│ 4. G1–G7 PROMOTION GATES                               │
│    Trade count, positive expectancy, profit factor,    │
│    drawdown, walk-forward ratio, cost shock, G7 Sharpe │
└───────────────────────────┬────────────────────────────┘
                            │
                            ▼
┌────────────────────────────────────────────────────────┐
│ 5. FORWARD PAPER TRADING (30–90 Days)                  │
│    Consumes live WebSocket feeds; commits to SQLite    │
└───────────────────────────┬────────────────────────────┘
                            │
                            ▼ [EXPLICIT HUMAN AUTHORIZATION REQUIRED]
┌────────────────────────────────────────────────────────┐
│ 6. CONTROLLED LIVE TRADING                             │
│    Real capital deployment; strict hard stops          │
└───────────────────────────┬────────────────────────────┘
                            │
                            ▼ [Trailing Drawdown or Alpha Decay]
┌────────────────────────────────────────────────────────┐
│ 7. DEGRADATION RETIREMENT                              │
│    Replaced by active Challenger; archived to failed/  │
└────────────────────────────────────────────────────────┘
```

---

## 2. Autonomous Discovery vs Live Deployment Boundary

> [!WARNING]
> **AUTONOMOUS EXECUTION BOUNDARY:**  
> The autonomous strategy discovery loop can discover hypotheses, run walk-forward backtests, evaluate G1-G7 gates, and deploy candidates **STRICTLY TO FORWARD PAPER TRADING**.  
> **Under NO circumstances may an autonomous loop activate live capital execution.**  
> Live deployment requires:
> 1. Complete paper trading performance report over at least 30 days.
> 2. Signed deployment authorization by the Risk Officer.
> 3. Verified exchange API credentials with non-custodial permissions audited.

---

## 3. Champion vs Challenger Framework

Every active production strategy pair is tracked in the `ExperimentRegistry`:
* **Champion:** The currently active strategy algorithm receiving paper or live capital allocation.
* **Challenger:** A newly discovered candidate running in parallel forward paper simulation.
* **Promotion Rule:** If a Challenger demonstrates statistically superior Sharpe ratio and lower max drawdown over a trailing 60-day paper window, it is submitted for formal Champion promotion review.
* **Decay Rule:** If a Champion breaches its trailing drawdown cap or experiences sustained negative expectancy over 3 consecutive rolling months, it is demoted, its capital is reclaimed, and it is archived to `research/failed/`.
