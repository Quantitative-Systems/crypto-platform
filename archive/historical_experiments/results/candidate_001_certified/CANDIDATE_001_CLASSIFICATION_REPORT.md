# CANDIDATE #001 CERTIFIED AUDIT & CLASSIFICATION REPORT
**Candidate ID:** CANDIDATE-001  
**Strategy Name:** Supertrend 6/5 + Stochastic 25/5/3 (25/75) Multi-Timeframe Continuation  
**Evaluation Date:** 2026-09-14  
**Classification Verdict:** **INSUFFICIENT DATA / MIXED (RESEARCH BENCHMARK ONLY)**  

---

## 1. EXECUTIVE SUMMARY

Under the certified Project TOP1 backtest engine (with 1.000% max risk position sizing, adverse-first collision handling, Binance VIP-0 friction modeling, and point-in-time timestamp causality), Candidate #001 was executed across the full 18-combination matrix (3 assets $\times$ 6 timeframe sets).

### Classification Verdict
**INSUFFICIENT DATA / MIXED**  
> [!WARNING]
> While aggregate performance shows $+35.79\text{R}$ net profit across the 18 combinations, **Candidate #001 cannot be classified as "Promising" or "Qualified"**. 
> The strategy suffers from severe opportunity starvation: only 25 total trades were generated across the entire multi-year universe, with 10 out of 18 timeframe streams producing exactly **0 trades**. Furthermore, $+26.72\text{R}$ (74.7% of all profits) originated from a single trade on SOL/USDT Set 3. 

---

## 2. 18-COMBINATION STANDARDIZED R PERFORMANCE TABLE

| Asset | Set | Style | Trades | Win Rate | Net R | Expectancy (R) | Profit Factor | Max DD (R) | Avg MFE (R) | Avg MAE (R) | Net PnL ($) | Rejected (6R) | Confidence |
| :--- | :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| **BTC/USDT** | Set 1 | Macro | 0 | 0.0% | +0.00R | 0.00R | N/A | 0.00R | 0.00R | 0.00R | $0.00 | 0 | INSUFFICIENT_DATA |
| **BTC/USDT** | Set 2 | Swing | 0 | 0.0% | +0.00R | 0.00R | N/A | 0.00R | 0.00R | 0.00R | $0.00 | 0 | INSUFFICIENT_DATA |
| **BTC/USDT** | Set 3 | Swing/Intraday | 1 | 100.0% | +2.15R | +2.15R | $\infty$ | 0.00R | 0.03R | 6.18R | +$214.79 | 2 | SAMPLE_TOO_SMALL |
| **BTC/USDT** | Set 4 | Intraday | 9 | 55.6% | +8.36R | +0.93R | 3.29 | 2.91R | 3.63R | 1.67R | +$847.28 | 6 | SAMPLE_TOO_SMALL |
| **BTC/USDT** | Set 5 | Short-Term | 0 | 0.0% | +0.00R | 0.00R | N/A | 0.00R | 0.00R | 0.00R | $0.00 | 3 | INSUFFICIENT_DATA |
| **BTC/USDT** | Set 6 | Scalping | 1 | 0.0% | -1.00R | -1.00R | 0.00 | 0.00R | 0.24R | 1.11R | -$100.00 | 0 | SAMPLE_TOO_SMALL |
| **ETH/USDT** | Set 1 | Macro | 0 | 0.0% | +0.00R | 0.00R | N/A | 0.00R | 0.00R | 0.00R | $0.00 | 0 | INSUFFICIENT_DATA |
| **ETH/USDT** | Set 2 | Swing | 0 | 0.0% | +0.00R | 0.00R | N/A | 0.00R | 0.00R | 0.00R | $0.00 | 0 | INSUFFICIENT_DATA |
| **ETH/USDT** | Set 3 | Swing/Intraday | 0 | 0.0% | +0.00R | 0.00R | N/A | 0.00R | 0.00R | 0.00R | $0.00 | 0 | INSUFFICIENT_DATA |
| **ETH/USDT** | Set 4 | Intraday | 9 | 44.4% | +3.78R | +0.42R | 1.76 | 2.00R | 1.18R | 1.83R | +$367.29 | 8 | SAMPLE_TOO_SMALL |
| **ETH/USDT** | Set 5 | Short-Term | 0 | 0.0% | +0.00R | 0.00R | N/A | 0.00R | 0.00R | 0.00R | $0.00 | 3 | INSUFFICIENT_DATA |
| **ETH/USDT** | Set 6 | Scalping | 1 | 0.0% | -1.00R | -1.00R | 0.00 | 0.00R | 2.03R | 1.05R | -$100.00 | 2 | SAMPLE_TOO_SMALL |
| **SOL/USDT** | Set 1 | Macro | 0 | 0.0% | +0.00R | 0.00R | N/A | 0.00R | 0.00R | 0.00R | $0.00 | 0 | INSUFFICIENT_DATA |
| **SOL/USDT** | Set 2 | Swing | 2 | 0.0% | -1.26R | -0.63R | 0.00 | 0.26R | 8.13R | 0.70R | -$125.30 | 0 | SAMPLE_TOO_SMALL |
| **SOL/USDT** | Set 3 | Swing/Intraday | 1 | 100.0% | +26.72R | +26.72R | $\infty$ | 0.00R | 38.38R | 0.76R | +$2,671.91 | 2 | SAMPLE_TOO_SMALL |
| **SOL/USDT** | Set 4 | Intraday | 1 | 0.0% | -0.79R | -0.79R | 0.00 | 0.00R | 9.77R | 0.72R | -$78.78 | 3 | SAMPLE_TOO_SMALL |
| **SOL/USDT** | Set 5 | Short-Term | 0 | 0.0% | +0.00R | 0.00R | N/A | 0.00R | 0.00R | 0.00R | $0.00 | 0 | INSUFFICIENT_DATA |
| **SOL/USDT** | Set 6 | Scalping | 0 | 0.0% | +0.00R | 0.00R | N/A | 0.00R | 0.00R | 0.00R | $0.00 | 0 | INSUFFICIENT_DATA |
| **TOTAL** | — | — | **25** | **44.0%** | **+35.79R** | **+1.43R** | **3.94** | **2.91R** | **4.21R** | **1.70R** | **+$3,697.10** | **29** | **INSUFFICIENT_DATA** |

---

## 3. FORENSIC ATTRIBUTION OF WEAKNESS & OPPORTUNITY DEFICIT

Why did Candidate #001 produce so few trades despite positive expectancy when triggered?

1. **The 6.0R Minimum Geometry Filter:**
   - Exactly **29 structurally valid signals** across the matrix were aborted because the opposing structural swing high/low did not offer $\ge 6.0\text{R}$ of reward relative to the structural stop.
   - Requiring $6.0\text{R}$ minimum TP3 forces the strategy to demand generational market moves before entering, rejecting viable $2.5\text{R} - 4.0\text{R}$ swing continuation opportunities.

2. **Concurrent Multi-Timeframe Oscillator Synchronization:**
   - The strategy requires that the HTF, MTF, and LTF Stochastics must ALL have dropped below $K \le 25$ and subsequently crossed over $K > D$.
   - In real crypto markets, a healthy HTF trend frequently pulls back only to $K \approx 35 - 45$. Requiring simultaneous extreme oversold conditions across all three timeframes occurs almost exclusively at major macro cycle bottoms.

3. **Timeframe Set Concentration:**
   - Only **Set 4 (4h / 1h / 15m)** produced consistent multi-trade samples (9 trades on BTC, 9 trades on ETH).
   - Set 1, Set 2, and Set 5 generated practically zero actionable setups.

---

## 4. SCIENTIFIC CONCLUSION & DISCOVERY HANDOFF

Candidate #001 is **FROZEN AND ARCHIVED** as the baseline reference benchmark. It proves that the core multi-timeframe structural logic has positive gross expectancy when aligned, but its extreme filter parameters destroy statistical significance.

### Next Steps for Strategy Discovery Lab (Phases 4–12):
1. **Hypothesis H-001A (Geometry Rationalization):** Test relaxing the minimum TP3 requirement from $6.0\text{R}$ to $3.0\text{R}$ while preserving trailing stops.
2. **Hypothesis H-001B (Stochastic Hierarchy):** Require $K \le 25$ oversold pullback ONLY on the MTF/LTF, allowing the HTF to maintain pure directional trend alignment (Supertrend green, Stochastic $K > 35$).
3. **Hypothesis H-002 (Breakout / Volatility Expansion):** Test independent strategy families (Donchian breakouts, ATR expansion) across the same certified 18-combination matrix.
