# QCP Comprehensive Economic Forensic Audit

**Audit Date:** 2026-09-17
**Objective:** EABG-002/003 — Economic Bottleneck Discovery
**Status:** COMPLETE

---

## 1. Executive Summary

This forensic audit was triggered to determine the true economic research state of the Quantitative Crypto Platform (QCP). Following the completion of the `EABG-002` (10-Asset Discovery) and `EABG-003` (Time-Series Momentum) milestones, it was critical to assess whether the platform's inability to find surviving alphas was a failure of **Architecture**, a failure of **Data Integrity**, or a failure of **Signal Quality**.

The audit concludes: **The architecture is sound, and the friction models are accurate. The primary structural bottleneck is Signal/Edge Quality.** 

Simple heuristics (trend, mean reversion, breakouts, TSMOM) do not generate sufficient gross return to overcome the institutional friction models enforced by the platform.

---

## 2. Evidence Integrity & Reconciliation

We audited the most contradictory claims currently residing in the repository.

### FAM-07-MTFCONT_SOLUSDT_Set2
* **Headline Claim:** `+278.32%` return, `5.24` Profit Factor (Reported as FORWARD_HEALTHY).
* **Forensic Reality:** The telemetry store (`forward_execution_telemetry.jsonl`) was contaminated by historical simulation trades that were duplicated up to 20x due to a fail-open execution path. 
* **True Performance:** The genuine DEV partition yields a `-0.9066R` expectancy (0 wins in 14 trades). The genuine forward paper results yield a `-1.202R` expectancy.
* **Verdict:** The headline is INADMISSIBLE. The strategy is **FRAGILE / NEGATIVE**.

### Friction Model Validation
* **Contradiction:** Audit logs cited a `32 bps` friction model, but `FrictionModel` in `backtesting/friction_model.py` defaults to `23 bps` roundtrip (11.5 bps per leg).
* **Reconciliation:** The `32 bps` figure applies to **Relative Value pairs trading** (4 total legs executed at 8 bps each). The `23 bps` model applies to standard directional trades (2 total legs). Both models are mathematically accurate, adversarial, and enforced correctly by the `EconomicEvaluationEngine`.

---

## 3. The 10-Asset / TSMOM Graveyard

Recent discovery pipelines confirmed the lack of heuristic edge:
- **EABG-002 (10-Asset Discovery):** 240 hypotheses tested. **240 falsified.** 0 survivors.
- **EABG-003 (TSMOM):** 320 hypotheses tested. **320 falsified.** 
  - 298 falsified immediately in Phase 1 (Baseline) due to lacking sufficient trades ($N<30$) or exhibiting a negative net edge even before stress testing.

Furthermore, **FAM-09 Relative Value** was falsified because 6 out of 6 hypotheses failed basic Engle-Granger/Johansen cointegration tests, showing massive half-lives that make pairs trading impossible.

---

## 4. The Structural Bottleneck

The structural bottleneck is **Signal/Edge Quality vs. Friction**.

1. **Architecture Is Not To Blame:** The `EconomicEvaluationEngine` correctly prevents look-ahead bias (signals trigger next-bar-open) and enforces adverse-first stop-loss rules. It is an honest mirror.
2. **Friction Is Institutional Reality:** The 23-32 bps roundtrip cost represents reality. QCP is doing its job by rejecting alphas that cannot cover this cost.
3. **The Heuristic Ceiling:** Simple technical heuristics extracted from OHLCV data on 4H/1D timeframes lack the predictive power to overcome a 23bps hurdle. 

---

## 5. Strategic Direction: The Next Experiment

**We must stop building generic directional heuristics.** 

Since high structural friction destroys low-frequency heuristic edge, the next experiment must exploit different structural properties. 

**Recommended Next Experiment (EABG-004):**
Develop an alpha discovery pipeline that targets:
1. **Market Microstructure:** Utilizing order book imbalance or tick-level delta rather than 4H OHLCV data.
2. **Market Making:** Earning the spread instead of paying it (requires shift in engine assumptions).
3. **Yield / Funding Arbitrage:** Exploiting perpetual funding rates directly.
