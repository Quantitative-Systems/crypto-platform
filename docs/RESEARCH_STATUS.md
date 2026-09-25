# Crypto Platform — Empirical Research Status & Limitations

**Document Version:** 1.0.0  
**Status:** Canonical Quantitative Research Record  
**Date:** 2026-09-25  
**Audit Baseline:** `4b43b61` / `8436b84`  

---

> [!CAUTION]
> ### MANDATORY RESEARCH DISCLOSURE: PROFITABILITY UNPROVEN
> 1. **Historical Backtest ≠ Realized Alpha:** Positive historical, validation, or out-of-sample (OOS) simulation returns represent research hypotheses under specific modeling assumptions. They do **NOT** guarantee, imply, or predict future live profitability.
> 2. **Live Capital is $0.00:** The platform has deployed exactly **$0.00** in live real-money capital.
> 3. **Live Profitability is NOT Established:** Realized live performance track record is currently non-existent.
> 4. **Forward Paper Evidence in Progress:** Forward paper trading on live exchange WebSocket data is active but has not yet accumulated the minimum sample threshold (≥ 30 closed trades per promoted book) required for Kolmogorov-Smirnov distribution equivalence testing.
> 5. **LIVE-CANARY is DISARMED and LIVE is HARD-LOCKED.**

---

## 1. Temporal Partitions & Separation Methodology

All quantitative modeling enforces strict temporal partitioning to prevent lookahead and data leakage:

```
[ DEV: 2021-01-01 to 2022-12-31 ]  ──► In-Sample Feature Discovery & Signal Formulation
               │
[ VAL: 2023-01-01 to 2024-05-31 ]  ──► Hyperparameter Calibration & Threshold Screening
               │
[ OOS: 2024-06-01 to 2026-03-31 ]  ──► Final Blind Out-of-Sample Walk-Forward Evaluation
               │
[ FORWARD PAPER (Live Feeds) ]     ──► In Progress (Public WebSockets, Zero Capital)
               │
[ DEMO / TESTNET (Broker) ]        ──► Configured / Deterministic Mock Verified
               │
[ LIVE-CANARY ]                    ──► DISARMED ($0.00 Deployed)
               │
[ LIVE TRADING ]                   ──► HARD-LOCKED ($0.00 Deployed)
```

No data from VAL, OOS, or Forward Paper was accessible during signal design or indicator construction.

---

## 2. Portfolio-Level Multi-Tier Performance Matrix

The historical performance evaluation across the temporal tiers yielded the following results (extracted from `research/results/crypto_platform/profitability_validation_report.md`):

| Metric | Development (DEV) | Validation (VAL) | Out-Of-Sample (OOS) | Forward Paper | Live Canary / Live |
|---|---|---|---|---|---|
| **Temporal Window** | 2021-01 to 2022-12 | 2023-01 to 2024-05 | 2024-06 to 2026-03 | Live Stream | Production |
| **Total Net Return** | **+148.2%** | **+74.8%** | **+57.7%** | **+0.00%** | **$0.00 (Unactivated)** |
| **Sharpe Ratio** | 2.14 | 1.68 | 1.045 | 0.000 | 0.000 |
| **Max Drawdown** | -14.2% | -16.5% | -18.7% | 0.00% | 0.00% |
| **Trades Executed** | 1,842 | 914 | 769 | 0 (Soak in progress) | 0 |
| **Trades Skipped** | 38 | 19 | 14 | 0 | 0 |
| **Verification State** | `IN_SAMPLE_BENCHMARK` | `TUNING_VALIDATION` | `WALK_FORWARD_VERIFIED` | `ACTIVE_INFRASTRUCTURE_SOAK` | `DISARMED / LOCKED` |

### Key Observations:
- **Degradation across tiers:** Sharpe ratio decays predictably from DEV (2.14) to VAL (1.68) and OOS (1.045), reflecting natural model decay and real transaction friction impact.
- **Drawdown stability:** Maximum drawdown widened moderately from 14.2% in DEV to 18.7% in OOS, remaining within the G4 ceiling of 25%.
- **Forward Paper:** Live forward soak has executed 0 trades so far awaiting qualifying regime signals and fill accumulation.

---

## 3. Promoted Books Evaluation (G1–G7 Gates)

Ten strategy allocations were evaluated across time horizons and assets:

| Strategy ID | Horizon | Symbol | DEV Return | VAL Return | OOS Return | OOS Trades | Status |
|---|---|---|---|---|---|---|---|
| `INTRADAY|trend_breakout|ETHUSDT` | 15m | ETH/USDT | Positive | Positive | Positive | ≥ 30 | PROMOTED_PAPER |
| `INTRADAY|trend_breakout|SOLUSDT` | 15m | SOL/USDT | Positive | Positive | Positive | ≥ 30 | PROMOTED_PAPER |
| `INTRADAY|mean_revert|ADAUSDT` | 15m | ADA/USDT | Positive | Positive | Positive | ≥ 30 | PROMOTED_PAPER |
| `SWING|trend_breakout|ETHUSDT` | 1h | ETH/USDT | Positive | Positive | Positive | ≥ 30 | PROMOTED_PAPER |
| `SWING|trend_breakout|SOLUSDT` | 1h | SOL/USDT | Positive | Positive | Positive | ≥ 30 | PROMOTED_PAPER |
| `SWING|trend_breakout|ADAUSDT` | 1h | ADA/USDT | Positive | Positive | Positive | ≥ 30 | PROMOTED_PAPER |
| `POSITION|trend_breakout|BNBUSDT` | 4h | BNB/USDT | Positive | Positive | Positive | ≥ 30 | PROMOTED_PAPER |
| `POSITION|trend_breakout|ADAUSDT` | 4h | ADA/USDT | Positive | Positive | Positive | ≥ 30 | PROMOTED_PAPER |
| `POSITION|trend_rider|DOGEUSDT` | 4h | DOGE/USDT | Positive | Positive | Positive | ≥ 30 | PROMOTED_PAPER |
| `CARRY|funding_carry|PORTFOLIO` | 8h | Multi | Highly Positive | Positive | Positive | ≥ 30 | PROMOTED_PAPER |

---

## 4. Funding Carry Strategy: Stress Testing & Sensitivity Audit

In historical backtesting, the delta-neutral funding carry strategy generated **71.6% of total portfolio returns** (+41.3% net). To investigate whether this constituted artificial alpha or realistic yield, a forensic sensitivity stress test was executed across 8 stress scenarios (`research/results/crypto_platform/carry_stress_report.md`).

### Stress Scenario Matrix:

| Scenario | Shock Description | Avg Net Return | Win Rate | Viability Status |
|---|---|---|---|---|
| **S0_BASELINE** | Historical baseline funding with standard maker/taker frictions | **+55.93%** | 62.5% | `ROBUST` |
| **S1_COMPRESSION_25** | 25% funding yield compression (institutional crowding) | **+39.08%** | 64.3% | `ROBUST` |
| **S2_COMPRESSION_50** | 50% funding yield compression (moderate bear/low volatility regime) | **+22.89%** | 83.3% | `ROBUST` |
| **S3_COMPRESSION_75** | 75% funding yield compression (severe prolonged bear chop) | **+7.47%** | 57.8% | `SURVIVES` |
| **S4_ZERO_FUNDING** | Zero funding rate environment (flat markets, no leverage demand) | **+0.00%** | 0.0% | `FAILS_STRESS` |
| **S5_NEGATIVE_REGIME** | Negative funding regime (shorts pay longs; -10% APR average) | **+3.13%** | 28.1% | `SURVIVES` |
| **S6_ELEVATED_FRICTIONS** | Double taker fees + 2x slippage + 30 bps adverse basis divergence | **+30.58%** | 42.2% | `ROBUST` |
| **S7_BORROW_DRAG** | 8% margin borrow rate + 20 bps/month hedge rebalance drag | **+22.36%** | 34.4% | `ROBUST` |
| **S8_COMPOUND_CATASTROPHIC** | 50% compression + 50 bps basis shock + 8% borrow drag + 2x fees | **-7.53%** | 23.3% | `FAILS_STRESS` |

### Critical Research Takeaways:
1. **Compounding Vulnerability:** Under compound adverse conditions (Scenario S8: funding yield halved, 8% borrow cost, and doubled taker fees), the funding carry strategy fails, losing **-7.53%**.
2. **Yield Crowding:** As perpetual markets mature, funding rate APRs compress. At 75% compression, annualized net returns drop to +7.47%, barely exceeding risk-free US Treasury rates.
3. **Mandatory Capital Cap:** Because carry historical returns constituted over 70% of gross backtest alpha, allocating more than 25% of portfolio equity to carry creates unacceptable systemic concentration. Portfolio governance mandates a **hard 15%–25% capital ceiling** on the Carry book.

---

## 5. Directional Strategy Realities & Transaction Cost Drag

1. **Sub-15m High-Frequency Scalping is Unviable:**
   - Empirical analysis of 1-minute and 5-minute directional momentum signals revealed that standard retail exchange fee schedules (0.05%–0.06% taker) exhaust between 45% and 85% of gross trade expectancy.
   - Consequently, sub-15m horizons are **fee-blocked** and disallowed from production promotion.
2. **Thin Directional Contribution:**
   - Directional breakout and mean-reversion strategies contribute modest standalone Sharpe ratios (0.8–1.3 OOS).
   - Their primary portfolio value is non-correlation with the market-neutral funding carry book, dampening overall portfolio drawdown during violent market deleveraging events.

---

## 6. Forward Paper Verification Plan

Before any consideration of live capital deployment, the following empirical milestones must be satisfied:

1. **Trade Accumulation:** Continuous execution of at least 30 independent closed paper trades per promoted book.
2. **Distribution Alignment:** Passing the two-sample Kolmogorov-Smirnov test at $\alpha = 0.05$ comparing forward paper trade return distribution against OOS backtest distribution.
3. **Slippage & Rejection Tracking:** Tracking empirical fill slippage on live orderbook updates versus backtest assumed slippage (3 bps on liquid pairs).
4. **Broker Testnet Soak:** Validation on exchange testnet environments across simulated rate-limiting, order cancellations, and margin adjustments.

---

*This document represents an honest, empirical snapshot of the quantitative platform research state as of 2026-09-25.*
