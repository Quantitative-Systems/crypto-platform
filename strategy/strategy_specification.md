# PRODUCT 01: MASTER STRATEGY SPECIFICATION CONTRACT v2.0
### Wealth Multiplier Systems · Quantitative Systems Platform · Product 01: Crypto Platform

**Product ID:** `PRODUCT-01-CRYPTO-PLATFORM`  
**Parent Hierarchy:** Wealth Multiplier Systems $\longrightarrow$ Quantitative Systems Platform $\longrightarrow$ Product 01: Crypto Platform  
**Specification Standard:** `v2.0-UNIFIED-CANONICAL-LOCKED`  
**Architect Role:** Quantitative Systems Architect  

---

## PART A: PRODUCT DEFINITION & SCOPE

### 1. Mission Statement
The objective of Product 01 is to build a production-grade, research-first, autonomous quantitative cryptocurrency trading and portfolio engineering platform. Trading hypotheses are derived from a unified multi-timeframe market ontology, gated by deterministic Market Intelligence, verified through causal zero-lookahead backtesting, bounded by unbreakable mathematical Risk Firewalls, and falsified through rigorous empirical experimentation.

### 2. Primary Asset Universe
Trading execution is conducted across Tier-1 high-liquidity crypto majors:

$$\text{Primary Asset Universe} = \{\text{BTC/USDT}, \text{ETH/USDT}, \text{SOL/USDT}\}$$

### 3. Execution Scales (Five Canonical Timeframe Sets)
The market model is fractal. The exact same 3-timeframe unified strategy operates across five operational execution scales:

| Timeframe Set | Trading Horizon | HTF (Direction & Target) | MTF (Setup & Trailing) | LTF (Execution & SL) |
| :--- | :--- | :--- | :--- | :--- |
| **SET 1** | Macro / Investing | 1 Month (1M) | 1 Week (1W) | 1 Day (1D) |
| **SET 2** | Position / Swing | 1 Week (1W) | 1 Day (1D) | 4 Hour (4H) |
| **SET 3** | Swing Horizon | 1 Day (1D) | 4 Hour (4H) | 1 Hour (1H) |
| **SET 4** | Tactical Intraday | 4 Hour (4H) | 1 Hour (1H) | 15 Minute (15M) |
| **SET 5** | Intraday Scalping | 15 Minute (15M) | 5 Minute (5M) | 1 Minute (1M) |

### 4. 15-Stream Research Matrix
The baseline research population consists of:
$$1 \text{ Unified Strategy Hypothesis} \times 5 \text{ Timeframe Sets} \times 3 \text{ Primary Assets} = 15 \text{ Independent Research Streams}$$

Every stream maintains complete causal state isolation and independent lifecycle telemetry.

---

## PART B: UNIVERSAL MARKET ONTOLOGY

Every single timeframe ($1\text{M}, 1\text{W}, 1\text{D}, 4\text{H}, 1\text{H}, 15\text{M}, 5\text{M}, 1\text{M}$) processes price action through an identical, deterministic price action language:

$$\text{Market State}_T = \{ \text{Trend}, \text{Structure}, \text{Key Levels}, \text{Key Zones}, \text{Liquidity}, \text{Pullback}, \text{Continuation}, \text{Expansion}, \text{Reversal} \}$$

1. **Trend Direction:** Evaluates to `BULLISH` (Higher Highs / Higher Lows), `BEARISH` (Lower Highs / Lower Lows), or `RANGING` (horizontally bound).
2. **Break of Structure (BOS):** Candlestick body close beyond the previous structural swing high (bullish BOS) or swing low (bearish BOS), confirming trend continuation.
3. **Change of Character (CHOCH):** Candlestick body close beyond the opposing structural swing low (Bullish to Bearish) or swing high (Bearish to Bullish), confirming trend reversal / shift.
4. **Key Levels:** Horizontal Equal Highs (`EQH`) and Equal Lows (`EQL`) representing concentrated stop liquidity.
5. **Key Zones:** Order Blocks (`OB`) and Fair Value Gaps (`FVG`) representing institutional supply and demand footprints.
6. **Liquidity Sweeps:** Price wick piercing a mapped Key Level (`EQH`/`EQL`), sweeping stop liquidity, followed by an immediate candle body close back inside the structural boundary.

---

## PART C: 3-TIMEFRAME RESPONSIBILITY ALLOCATION

```text
  HTF (Higher Timeframe) ──► DIRECTION & DESTINATION
  • Determines Directional Bias (BULLISH / BEARISH).
  • Sets Contextual Market Phase (PULLBACK vs CONTINUATION).
  • Maps Structural Target Objective (TP = HTF Weak Swing High/Low).
  • Identifies active HTF KeyZones.
  • NEVER executes orders; NEVER calculates entry stops.

  MTF (Middle Timeframe) ──► SETUP, NAVIGATION & TRAILING
  • Validates MTF Structural Realignment with HTF Direction (CHOCH / BOS).
  • Identifies causally created MTF KeyZones (OB / FVG).
  • Confirms MTF KeyZone Retest / Mitigation.
  • Manages dynamic monotonic structural trailing during active trade lifecycle.

  LTF (Lower Timeframe) ──► EXECUTION & INITIAL INVALIDATION
  • Confirms micro execution trigger: Liquidity Sweep + Displacement + Body Close.
  • Sets Initial Invalidation Stop Loss (SL = LTF Protected Swing).
  • NEVER overrides HTF directional bias; NEVER sets macro targets.
```

---

## PART D: HYPOTHESIS FACTORY & IMMUTABLE REGISTRY

All quantitative strategy variations are treated as versioned hypotheses within family classifications:
1. **`H1_TREND_CONTINUATION`**: Canonical structural trend continuation (Control).
2. **`H2_VOLATILITY_EXPANSION`**: Volatility-gated trend continuation ($ATR > 1.2 \times ATR_{20}$).
3. **`H3_REGIME_FILTERED`**: Regime-filtered trend continuation ($ADX > 25.0$).
4. **`H4_LIQUIDITY_DISPLACEMENT`**: Prior session/swing liquidity-sweep conditioned continuation.
5. **`H5_MOMENTUM_EXPANSION`**: Displacement impulse candle body ratio ($> 70\%$).

All hypothesis trials are logged permanently in [`HypothesisRegistry`](file:///home/mrcn2/crypto-platform/research/experiments/hypothesis_registry.py) to prevent Multiple Hypothesis Testing (MHT) data snooping.

---

## PART E: 7-DIMENSION INSTITUTIONAL CAPITAL BARRIER

No strategy hypothesis can transition from Research to Live Capital unless it clears all 7 mandatory dimensions:

1. **Dimension 1 (Data Lake Validity):** Dataset must be in `CERTIFIED` or `RESEARCH_ELIGIBLE` state with zero lookahead.
2. **Dimension 2 (Alpha Expectancy):** Positive net realized expectancy ($E[R] > 0.0\text{R}$) post-friction across OOS.
3. **Dimension 3 (Statistical Significance):** Bootstrap 95% Confidence Lower Bound $> 0.0\text{R}$, sample size $N \ge 30$ independent trades, survives Holm-Bonferroni trial penalty.
4. **Dimension 4 (Walk-Forward Efficiency):** Walk-Forward Overfitting Ratio $WFR \ge 0.70$ across rolling train/test windows.
5. **Dimension 5 (Cost Shock Robustness):** Strategy edge survives a $+50\%$ transaction cost shock.
6. **Dimension 6 (Parameter Stability):** Parameter perturbation sensitivity variance $< 30\%$.
7. **Dimension 7 (Risk Limits):** Maximum Drawdown $\le 20.0\%$.

> **Inviolable Governance Rule:** If ANY dimension fails, the system returns `REJECTED_RESEARCH_ONLY / NO CAPITAL`.
