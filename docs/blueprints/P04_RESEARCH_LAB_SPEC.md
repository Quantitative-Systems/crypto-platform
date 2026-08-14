# Product 04 — Research & Backtesting Laboratory Architecture Specification

**STATUS:** DRAFT
**PHASE:** PRODUCT 04

## 1. Chronological Market Replayer
The cornerstone of the Research Laboratory is a point-in-time causal feed architecture designed to guarantee **zero lookahead bias** through stringent state isolation.

### 1.1 Causal Feed Architecture & Timestamps
- The system replays historical market data in an event-driven, chronological sequence.
- **Timestamp Resolution & Availability:** A candle covering the temporal period `[T_start, T_end)` is definitively closed at `T_end`. The completed bar becomes visible and actionable to the execution engine strictly at `T_end + 1ms`. Under no circumstances can a candle's closing data be read at `T_start` or anytime prior to `T_end + 1ms`.
- **Rolling Metric Isolation:** Indicators and rolling metrics (e.g., True Range, volume profiles, swing pivots) are computed strictly upon the event boundary of a candle close. They are calculated exclusively using historical candles where `candle.close_timestamp < current_execution_timestamp` to prevent forward data leakage.

### 1.2 Multi-Timeframe Bar Alignment Engine
The engine processes canonical timeframe sets hierarchically to guarantee chronological precision.
- **Set 1:** 1 Minute (1M) → 1 Week (1W) → 1 Day (1D)
- **Set 2:** 1 Week (1W) → 1 Day (1D) → 4 Hours (4H)
- **Set 3:** 1 Day (1D) → 4 Hours (4H) → 1 Hour (1H)
- **Set 4:** 4 Hours (4H) → 1 Hour (1H) → 15 Minutes (15M)
Higher timeframe structures are strictly synthesized and resolved from the aggregation of fully closed, granular lower-timeframe sub-bars to prevent future leakage. No arbitrary timeframes are permitted.

### 1.3 Intrabar Ambiguity Resolution (Pessimistic Execution)
- **Simultaneous Target Hit Dilemma:** During backtesting, if a single bar's `High` breaches a Take Profit (TP) and its `Low` breaches a Stop Loss (SL) without sufficient intrabar tick data to prove chronological ordering, the engine must enforce **Pessimistic Execution**.
- The engine enforces a worst-case scenario axiom: the Stop Loss is definitively assumed to trigger *before* the Take Profit, resolving the trade as a maximum loss. Assuming favorable intrabar pathing is strictly prohibited unless validated by raw order-book tick data.

---

## 2. Realistic Transaction-Cost & Friction Model
To accurately model production-grade execution decay, a punitive friction model is enforced across all trades.

### 2.1 Maker vs. Taker Fee Schedule
- Simulated orders strictly categorize execution:
  - **Taker Orders:** Market orders, Stop-Market orders. Subject to maximum exchange Taker fees (e.g., 0.05%).
  - **Maker Orders:** Limit orders placed outside the immediate bid/ask spread. Subject to Maker fees (e.g., 0.02% or rebate).

### 2.2 Slippage and Order Fill Simulation
- **Dynamic Slippage for Market/Stop Orders:** Market execution suffers dynamic slippage calculated as a function of the execution bar's volatility and volume. Formula: `Realized_Slippage_bps = Base_bps_Slippage + (Volatility_Multiplier * (TrueRange / ClosePrice))`.
- **Limit Order Fill Mechanics (Queue Pessimism):** Limit orders are only filled if the market price trades *strictly through* the limit price. A mere touch of the limit price (where `High` or `Low` == `Limit Price`) registers as a **No-Fill (0%)** to conservatively model queue position failure.

### 2.3 Spread Expansion Handling
- **Volatile Extremes:** During low liquidity or high volatility environments (e.g., gaps, session opens), the modeled bid-ask spread expands proportionally to the rate of price change. Market orders executing during these regimes incur exponentially worse fills.

---

## 3. 24-Baseline Research Matrix & Isolation
The research laboratory tests hypotheses systematically without parameter optimization.

### 3.1 Strict Matrix Isolation
- **Matrix Constraints:** 2 Hypotheses (Pullback, Continuation) × 4 Timeframe Sets (S1, S2, S3, S4) × 3 Assets (BTC, ETH, SOL) = 24 isolated streams.
- **Memory Quarantine:** Each of the 24 pipelines spins up an isolated state machine, memory space, and ledger. Data structures are strictly siloed at runtime, guaranteeing zero cross-contamination of positions, state variables, or signals across assets and timeframes.

### 3.2 Dynamic Data Boundaries (Train / Validation / OOS)
- Date boundaries for Train (In-Sample), Validation, and Out-Of-Sample (OOS) are **dynamically configurable** via a central test harness configuration file. They are never hardcoded in scripts to prevent accidental developer lookahead bias.
- **Out-Of-Sample (OOS) Quarantine:** OOS partitions remain locked/encrypted until explicitly triggered. The OOS test is a singular, one-way operation. Strategy failure on OOS implies instant, permanent strategy rejection.

---

## 4. Research Metrics & Statistical Proof
Quantitative performance is evaluated via unyielding mathematical determinism.

### 4.1 Explicit Metric Formulas & Zero-Division Safety
All metrics explicitly map edge cases to ensure computational stability:
- **Expectancy Per Trade:** `E = (WinRate * AvgWin) - (LossRate * AvgLoss)`. *Zero-Safety:* If `Total Trades == 0`, `E = 0.0`.
- **Profit Factor:** `PF = Gross Profits / ABS(Gross Losses)`. *Zero-Safety:* If `Gross Losses == 0` and `Gross Profits > 0`, `PF = 999.0` (Cap). If `Gross Profits == 0`, `PF = 0.0`.
- **Max Drawdown:** `MDD = Max((Peak_i - Trough_j) / Peak_i)`. Calculated on closed equity. Largest peak-to-trough equity drop.
- **Sharpe Ratio:** `SR = (Annualized Return - RiskFreeRate) / Annualized Standard Deviation`. *Zero-Safety:* If `Standard Deviation == 0`, `SR = 0.0`.
- **Sortino Ratio:** `Sortino = (Annualized Return - RiskFreeRate) / Downside Standard Deviation`. *Zero-Safety:* If `Downside SD == 0`, `Sortino = 0.0`.
- **Win/Loss R:R Distribution:** An array tracking `Realized_Risk:Reward` per trade, serialized for histogram rendering.

---

## 5. Reproducible Experiment Artifacts
Experiment traces must be strictly immutable and reproducible for institutional auditing.

### 5.1 Export Schema
- Runs are serialized strictly into `JSON` or `Parquet` schemas, persisting to `research/results/`.
- **Trace Logs:** Micro-state progression recording chronological signals, timestamp exactness, and bar-close triggers.
- **Execution Logs:** Exact simulated fill prices, decomposed slippage penalties (base vs. dynamic), and applied Maker/Taker fees per trade.
- **Metric Summaries:** Final computed performance matrices (Expectancy, Drawdown, Profit Factor) aggregated across the Train/Val/OOS boundaries.
