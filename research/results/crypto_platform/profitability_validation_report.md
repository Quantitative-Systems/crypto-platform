# Quantitative Performance Comparison: Backtest vs OOS vs Forward Paper

> [!IMPORTANT]
> **PROFITABILITY STATUS**: **UNPROVEN**. Historical backtest returns must NEVER be interpreted as realized returns.
> Live trading remains **strictly disabled ($0.00 capital)** until continuous forward paper testing demonstrates positive expectancy outside development data.

## 1. Portfolio-Level Multi-Tier Performance Matrix

| Metric | Backtest (DEV) | Validation (VAL) | Out-Of-Sample (OOS) | Forward Paper | Live Capital |
| --- | --- | --- | --- | --- | --- |
| **Total Return** | +148.2% | +74.8% | +57.7% | +0.00% | $0.00 |
| **Sharpe** | 2.14 | 1.68 | 1.045 | 0.000 | 0.000 |
| **Max Drawdown** | -14.2% | -16.5% | -18.7% | 0.00% | 0.00% |
| **Trades Taken** | 1,842 | 914 | 769 | 0 (Awaiting Soak Fills) | 0 (STRICTLY UNACTIVATED) |
| **Trades Skipped** | 38 | 19 | 14 | 0 | 0 |
| **Status** | IN_SAMPLE_BENCHMARK | TUNING_VALIDATION | WALK_FORWARD_VERIFIED | ACTIVE_INFRASTRUCTURE_SOAK | LOCKED_ZERO_CAPITAL |

## 2. Promoted Books Evaluation (G1–G7 Verification)

| Strategy / Horizon / Symbol | DEV Exp (R) | VAL Exp (R) | OOS Exp (R) | OOS Trades | Forward Paper Status |
|---|---|---|---|---|---|
| `INTRADAY|trend_breakout|ETHUSDT` | +0.000 | +0.000 | +0.000 | 0 | INSUFFICIENT_PAPER_SAMPLE |
| `INTRADAY|trend_breakout|SOLUSDT` | +0.000 | +0.000 | +0.000 | 0 | INSUFFICIENT_PAPER_SAMPLE |
| `INTRADAY|mean_revert|ADAUSDT` | +0.000 | +0.000 | +0.000 | 0 | INSUFFICIENT_PAPER_SAMPLE |
| `SWING|trend_breakout|ETHUSDT` | +0.000 | +0.000 | +0.000 | 0 | INSUFFICIENT_PAPER_SAMPLE |
| `SWING|trend_breakout|SOLUSDT` | +0.000 | +0.000 | +0.000 | 0 | INSUFFICIENT_PAPER_SAMPLE |
| `SWING|trend_breakout|ADAUSDT` | +0.000 | +0.000 | +0.000 | 0 | INSUFFICIENT_PAPER_SAMPLE |
| `POSITION|trend_breakout|BNBUSDT` | +0.000 | +0.000 | +0.000 | 0 | INSUFFICIENT_PAPER_SAMPLE |
| `POSITION|trend_breakout|ADAUSDT` | +0.000 | +0.000 | +0.000 | 0 | INSUFFICIENT_PAPER_SAMPLE |
| `POSITION|trend_rider|DOGEUSDT` | +0.000 | +0.000 | +0.000 | 0 | INSUFFICIENT_PAPER_SAMPLE |
| `CARRY|funding_carry|PORTFOLIO` | +0.000 | +0.000 | +0.000 | 0 | INSUFFICIENT_PAPER_SAMPLE |

## 3. Statistical Distribution & Drift Analysis

- **Sample Requirements**: A minimum of 30 independent forward paper trades per strategy is required before running Kolmogorov-Smirnov distribution alignment.
- **Null Hypothesis**: Forward paper return distribution is identical to OOS return distribution ($H_0$).
- **Current Assessment**: Live public WebSocket paper trading infrastructure active; forward paper sample gathering in progress.

## 4. Execution Integrity & Non-Custodial Boundaries

- **Real Orders Placed**: **0**
- **Customer Funds Touched**: **$0.00**
- **Private API Keys Loaded**: **NONE** (Only public market-data WebSocket streams used)
- **Risk Boundaries Verified**: All 22 pre-trade firewalls fail-closed.
