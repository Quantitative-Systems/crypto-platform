# Quantitative Systems Platform (QSP)
## Architectural Research Specification: Unresolved Trading Styles (Sets 1, 4, 5, 6)

**Author:** Quantitative Systems Platform (QSP) Research Division  
**Classification:** Institutional Research Mandate & Engineering Roadmap  
**Target Timeframe Sets:** Set 1 (Macro), Set 4 (Intraday), Set 5 (Short-Term Intraday), Set 6 (Scalping)  

---

### Executive Overview
The initial 8-family autonomous discovery sweep successfully identified robust cross-horizon candidates on **Set 2 (Swing: 1W $\to$ 1D $\to$ 4H)** and **Set 3 (Swing/Intraday: 1D $\to$ 4H $\to$ 1H)**. However, four styles remain unresolved due to either economic friction erosion, natural trade frequency constraints, or historical data caching boundaries.

This specification details the quantitative hypotheses, economic rationales, and engineering implementations required to systematically resolve each missing style.

---

### 1. Set 1 — Macro / Position (1M $\to$ 1W $\to$ 1D)

#### The Problem
In the 2021–2022 Development horizon, secular crypto macro trends produced only 5 to 15 genuine structural turning points per asset. Forcing a strategy to generate $\ge 100$ trades on 1D/1W within 24 months creates an unnatural distortion, forcing the strategy to trade noise and destroying macro trend-following expectancy.

#### Quantitative Hypothesis & Solution
1. **Cumulative Observation Horizon:** 
   - Macro strategies must evaluate trade frequency across the full 2017–2026 institutional history ($N \ge 100$ cumulative observations across 9.5 years, or $\sim 10–12$ high-conviction trades per year per asset).
2. **Cross-Sectional Momentum & Relative Strength:**
   - Instead of single-asset time-series trend rules, deploy a multi-asset cross-sectional momentum ranking (SOL/BTC, ETH/BTC, SOL/ETH relative strength ratios).
3. **Macro Volatility Envelope:**
   - HTF: Monthly structural pivot filter.
   - MTF: Weekly 200 EMA / 50 EMA Golden/Death cross bias.
   - LTF: Daily 20-day breakout with volatility-scaled trailing stops (3.0 ATR) and 4.0R asymmetric target geometry.

---

### 2. Set 4 — Intraday (4H $\to$ 1H $\to$ 15M)

#### The Problem
Breakout strategies on 15M generate abundant trade frequency ($>2,000$ trades in 2 years). However, the average price excursion on a 15M bar ($\approx 0.35\%–0.50\%$) is comparable in magnitude to round-trip execution friction:
$$\text{Friction Drag} = \text{Taker Fee } (0.075\% \times 2) + \text{Slippage } (0.03\% \times 2) + \text{Spread } (0.01\%) = 0.220\%$$
Consequently, friction consumes $40\%–65\%$ of gross theoretical edge, causing the strategy to collapse under cost stress.

#### Quantitative Hypothesis & Solution
1. **Dynamic Volatility Expansion Filter:**
   - Impose an entry precondition: $\frac{ATR_{14}(15M)}{\text{Close}} \ge 0.60\%$. Rejects low-volatility churn where spread and commissions dominate.
2. **Institutional Session Volume Filter:**
   - Constrain entry signals to high-liquidity market sessions: London Open (`07:00–10:00 UTC`) and New York Open (`13:00–16:00 UTC`), filtering out low-volume Asian chop.
3. **Target Geometry Expansion:**
   - Expand reward-to-risk geometry from $2.0R$ to $\ge 3.0R$, ensuring winning trades generate at least $1.5\%–2.5\%$ price movement to easily dwarf friction.

---

### 3. Sets 5 & 6 — Short-Term Intraday (1H $\to$ 15M $\to$ 5M) & Scalping (15M $\to$ 5M $\to$ 1M)

#### The Problem
The local data store currently caches 50,000 candles for `5m` and `1m`, covering recent 2026 market data. Historical 2021–2022 5m and 1m Kline data is absent. Per Directive §20.C, this is classified as an **Infrastructure Limitation**.

#### Engineering Implementation
1. **High-Speed Bulk Ingestion Engine (`data_ingestion/backfill_binance_klines.py`):**
   - Download official monthly Binance Public Data Archive ZIPs (`https://data.binance.vision/data/spot/monthly/klines/{SYMBOL}/{TIMEFRAME}/{SYMBOL}-{TIMEFRAME}-{YEAR}-{MONTH}.zip`).
   - Multi-threaded asynchronous streaming extraction directly to partitioned Parquet files (`data/historical/{symbol}_{timeframe}.parquet`).
   - Ingests 5.5 years of 5M and 1M candles for BTC, ETH, and SOL in under 5 minutes without REST API rate-limiting.
2. **Scalping Microstructure Architecture:**
   - Maker-order limit execution models (negative taker fee / maker rebates) or volume-weighted order book imbalance (OVI) signals to operate viably at 1M/5M frequencies.
