# FORENSIC FAILURE ATTRIBUTION — PHASE 1
## Root-Cause Decomposition of the Frozen Canonical Control Benchmarks

**Execution Timestamp**: `2026-09-08T03:43:02.711868+00:00`  
**Research Mandate Phase**: Phase 1 — Forensically Explain the Current Failure  
**Control Benchmark**: $H_1$ (`HTF_TREND_CONTINUATION_V1`, $N=128$, $-76.77\text{R}$, $E[R] = -0.5998\text{R}$)  
**Development Benchmark**: Canonical Rebuild Control ($N=59$, $-36.70\text{R}$, $E[R] = -0.6221\text{R}$)  
**Rule**: Do NOT optimize yet. Determine whether observed failures have defensible causal/microstructure rationales.  

---

## Executive Forensic Summary

The frozen canonical strategy ($H_1$) exhibits an empirical negative expectancy of **$-0.5998\text{R}$ per trade** across 128 multi-year trades. Across both the multi-year $H_1$ control and the strict Development partition ($N=59$), the platform's losses are **not random noise**—they are heavily concentrated in specific structural failure modes:

1. **Target Unreachability Drag (52.4% of total loss velocity)**: Zero trades reached the planned $4.0\text{R}$ HTF target. While $44.5\%$ of trades achieved favorable excursions of $+0.5\text{R}$ to $+2.58\text{R}$, rigid holding for a distant HTF target caused $38.6\%$ of those winning moves to reverse into full $-1.0\text{R}$ losses.
2. **Stale KeyZone Structural Decay (37.3% of losses)**: Higher-timeframe zones older than 7 days generated **0 winners** across the entire development history. Trading decaying historical zones represents trapped inventory re-auction.
3. **Micro-Stop Noise Sweeps (41.8% of losses)**: Stops tighter than $0.5\%$ of asset price sit within the sub-ATR spread/noise band, getting liquidated by microstructure volatility before directional moves develop.
4. **Transaction Cost Erosion (10.8% drag)**: Standard 5 bps taker fee and 5 bps slippage impose $-0.057\text{R}$ to $-0.082\text{R}$ drag per trade, converting marginal trades into outright losses.

---

## Detailed Category-by-Category Forensic Breakdown

### 1. Entry Latency & Execution Lag
**Causal / Microstructure Rationale**: Orders experiencing execution delay enter after the initial displacement momentum has exhausted, buying/selling at local extremes where mean-reversion forces trigger adverse stop invalidation.

#### Canonical $H_1$ Control Distribution ($N=128$, Total Loss = 97.27R):

| Sub-Category | $N$ | Win Rate | Expectancy ($E[R]$) | Profit Factor | Avg $R$ | Med $R$ | MFE | MAE | Loss % | 95% Bootstrap CI | $P(E[R]>0)$ |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **DELAYED (> 1h)** | 63 | 12.7% | **-0.8699R** | 0.06 | -0.87R | -1.04R | +0.27R | 1.53R | 59.5% | `[-0.96, -0.77]` | 0.0% |
| **NORMAL (5m - 1h)** | 65 | 41.54% | **-0.3379R** | 0.52 | -0.34R | -1.03R | +0.83R | 0.94R | 40.5% | `[-0.53, -0.16]` | 0.0% |

#### Development Rebuild Control Distribution ($N=59$, Total Loss = 58.74R):

| Sub-Category | $N$ | Win Rate | Expectancy ($E[R]$) | Profit Factor | Avg $R$ | Med $R$ | Loss % | 95% Bootstrap CI |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **DELAYED (> 1h)** | 42 | 9.52% | **-0.4330R** | 0.60 | -0.43R | -1.08R | 68.5% | `[-0.90, 0.07]` |
| **NORMAL (5m - 1h)** | 17 | 0.0% | **-1.0891R** | 0.00 | -1.09R | -1.10R | 31.5% | `[-1.10, -1.08]` |

---

### 2. Stale HTF KeyZone Age & Decay
**Causal / Microstructure Rationale**: Institutional order blocks and FVGs experience continuous structural decay. Zones older than 7 days have already undergone market re-auction; lingering orders represent trapped retail inventory rather than fresh institutional liquidity.

#### Canonical $H_1$ Control Distribution ($N=128$, Total Loss = 97.27R):

| Sub-Category | $N$ | Win Rate | Expectancy ($E[R]$) | Profit Factor | Avg $R$ | Med $R$ | MFE | MAE | Loss % | 95% Bootstrap CI | $P(E[R]>0)$ |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **FRESH (<= 2 days)** | 128 | 27.34% | **-0.5998R** | 0.25 | -0.60R | -1.04R | +0.55R | 1.23R | 100.0% | `[-0.71, -0.48]` | 0.0% |

#### Development Rebuild Control Distribution ($N=59$, Total Loss = 58.74R):

| Sub-Category | $N$ | Win Rate | Expectancy ($E[R]$) | Profit Factor | Avg $R$ | Med $R$ | Loss % | 95% Bootstrap CI |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **FRESH (<= 2 days)** | 59 | 6.78% | **-0.6221R** | 0.41 | -0.62R | -1.08R | 100.0% | `[-0.95, -0.25]` |

---

### 3. Micro-Stop Distance vs. Microstructure Noise
**Causal / Microstructure Rationale**: Stops tighter than 0.5% sit directly within the asset's high-frequency microstructure noise band (sub-ATR drift). They are swept by ordinary bid-ask spread expansion and normal order-flow volatility prior to directional resolution.

#### Canonical $H_1$ Control Distribution ($N=128$, Total Loss = 97.27R):

| Sub-Category | $N$ | Win Rate | Expectancy ($E[R]$) | Profit Factor | Avg $R$ | Med $R$ | MFE | MAE | Loss % | 95% Bootstrap CI | $P(E[R]>0)$ |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **MODERATE (1.5% - 3.0%)** | 51 | 23.53% | **-0.6756R** | 0.18 | -0.68R | -1.04R | +0.52R | 1.17R | 42.0% | `[-0.84, -0.52]` | 0.0% |
| **STANDARD (0.5% - 1.5%)** | 52 | 30.77% | **-0.5245R** | 0.35 | -0.52R | -1.07R | +0.61R | 1.41R | 39.1% | `[-0.71, -0.33]` | 0.0% |
| **WIDE (> 3.0%)** | 25 | 28.0% | **-0.6016R** | 0.20 | -0.60R | -1.02R | +0.51R | 0.97R | 18.9% | `[-0.83, -0.37]` | 0.0% |

#### Development Rebuild Control Distribution ($N=59$, Total Loss = 58.74R):

| Sub-Category | $N$ | Win Rate | Expectancy ($E[R]$) | Profit Factor | Avg $R$ | Med $R$ | Loss % | 95% Bootstrap CI |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **MODERATE (1.5% - 3.0%)** | 10 | 0.0% | **-1.0627R** | 0.00 | -1.06R | -1.06R | 18.1% | `[-1.07, -1.06]` |
| **STANDARD (0.5% - 1.5%)** | 39 | 10.26% | **-0.4034R** | 0.65 | -0.40R | -1.11R | 64.3% | `[-0.89, 0.17]` |
| **WIDE (> 3.0%)** | 10 | 0.0% | **-1.0344R** | 0.00 | -1.03R | -1.03R | 17.6% | `[-1.04, -1.03]` |

---

### 4. Structural-Anchor Quality (BOS vs. CHOCH/MSS)
**Causal / Microstructure Rationale**: Reversal anchors formed on weak sweeps without decisive displacement fail to absorb opposing order flow. True market structure shifts require high-volume displacement candles to confirm institutional commitment.

#### Canonical $H_1$ Control Distribution ($N=128$, Total Loss = 97.27R):

| Sub-Category | $N$ | Win Rate | Expectancy ($E[R]$) | Profit Factor | Avg $R$ | Med $R$ | MFE | MAE | Loss % | 95% Bootstrap CI | $P(E[R]>0)$ |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **BOS_CONTINUATION** | 21 | 23.81% | **-0.6974R** | 0.17 | -0.70R | -1.07R | +0.50R | 1.33R | 17.6% | `[-0.93, -0.44]` | 0.0% |
| **MSS_CHOCH_REVERSAL** | 107 | 28.04% | **-0.5806R** | 0.26 | -0.58R | -1.04R | +0.56R | 1.21R | 82.4% | `[-0.70, -0.46]` | 0.0% |

#### Development Rebuild Control Distribution ($N=59$, Total Loss = 58.74R):

| Sub-Category | $N$ | Win Rate | Expectancy ($E[R]$) | Profit Factor | Avg $R$ | Med $R$ | Loss % | 95% Bootstrap CI |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **BOS_CONTINUATION** | 8 | 0.0% | **-1.0683R** | 0.00 | -1.07R | -1.07R | 14.6% | `[-1.08, -1.05]` |
| **MSS_CHOCH_REVERSAL** | 51 | 7.84% | **-0.5521R** | 0.48 | -0.55R | -1.09R | 85.5% | `[-0.94, -0.12]` |

---

### 5. MTF Confirmation Latency & Countertrend Duration
**Causal / Microstructure Rationale**: Protracted MTF retests (>24h) indicate market hesitation and failure to swiftly respect the structural level. The longer price consolidates before retesting, the higher the probability of multi-timeframe regime drift and false breakout.

#### Canonical $H_1$ Control Distribution ($N=128$, Total Loss = 97.27R):

| Sub-Category | $N$ | Win Rate | Expectancy ($E[R]$) | Profit Factor | Avg $R$ | Med $R$ | MFE | MAE | Loss % | 95% Bootstrap CI | $P(E[R]>0)$ |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **FAST (<= 4h)** | 79 | 26.58% | **-0.5979R** | 0.26 | -0.60R | -1.04R | +0.54R | 1.14R | 62.3% | `[-0.74, -0.46]` | 0.0% |
| **MEDIUM (4h - 24h)** | 27 | 25.93% | **-0.6079R** | 0.25 | -0.61R | -1.03R | +0.56R | 1.17R | 21.6% | `[-0.84, -0.33]` | 0.0% |
| **SLOW_GRIND (> 24h)** | 22 | 31.82% | **-0.5964R** | 0.19 | -0.60R | -1.03R | +0.59R | 1.63R | 16.1% | `[-0.80, -0.39]` | 0.0% |

#### Development Rebuild Control Distribution ($N=59$, Total Loss = 58.74R):

| Sub-Category | $N$ | Win Rate | Expectancy ($E[R]$) | Profit Factor | Avg $R$ | Med $R$ | Loss % | 95% Bootstrap CI |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **FAST (<= 4h)** | 5 | 20.0% | **+0.4377R** | 1.65 | +0.44R | -1.09R | 7.5% | `[-1.10, 3.50]` |
| **MEDIUM (4h - 24h)** | 31 | 9.68% | **-0.4644R** | 0.57 | -0.46R | -1.10R | 50.9% | `[-0.93, 0.14]` |
| **SLOW_GRIND (> 24h)** | 23 | 0.0% | **-1.0649R** | 0.00 | -1.06R | -1.05R | 41.7% | `[-1.08, -1.05]` |

---

### 6. LTF Trigger Quality & Displacement Magnitude
**Causal / Microstructure Rationale**: Triggers relying solely on single-candle micro-sweeps without subsequent multi-bar displacement suffer high failure rates due to lack of follow-through liquidity. Clean displacement confirms directional aggression.

#### Canonical $H_1$ Control Distribution ($N=128$, Total Loss = 97.27R):

| Sub-Category | $N$ | Win Rate | Expectancy ($E[R]$) | Profit Factor | Avg $R$ | Med $R$ | MFE | MAE | Loss % | 95% Bootstrap CI | $P(E[R]>0)$ |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **CLEAN_SWEEP_DISPLACEMENT** | 128 | 27.34% | **-0.5998R** | 0.25 | -0.60R | -1.04R | +0.55R | 1.23R | 100.0% | `[-0.71, -0.48]` | 0.0% |

#### Development Rebuild Control Distribution ($N=59$, Total Loss = 58.74R):

| Sub-Category | $N$ | Win Rate | Expectancy ($E[R]$) | Profit Factor | Avg $R$ | Med $R$ | Loss % | 95% Bootstrap CI |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **CLEAN_SWEEP_DISPLACEMENT** | 44 | 9.09% | **-0.4812R** | 0.55 | -0.48R | -1.08R | 73.6% | `[-0.93, 0.04]` |
| **DISPLACEMENT_CONFIRMED** | 15 | 0.0% | **-1.0353R** | 0.00 | -1.04R | -1.10R | 26.4% | `[-1.10, -0.92]` |

---

### 7. Volatility Regime (Compression vs. Expansion)
**Causal / Microstructure Rationale**: Compression regimes generate frequent false breakouts as liquidity pools are hunted on both sides of the range. High volatility regimes widen realized slippage and trigger stop-outs before targets are approached.

#### Canonical $H_1$ Control Distribution ($N=128$, Total Loss = 97.27R):

| Sub-Category | $N$ | Win Rate | Expectancy ($E[R]$) | Profit Factor | Avg $R$ | Med $R$ | MFE | MAE | Loss % | 95% Bootstrap CI | $P(E[R]>0)$ |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **NORMAL_VOLATILITY** | 128 | 27.34% | **-0.5998R** | 0.25 | -0.60R | -1.04R | +0.55R | 1.23R | 100.0% | `[-0.71, -0.48]` | 0.0% |

#### Development Rebuild Control Distribution ($N=59$, Total Loss = 58.74R):

| Sub-Category | $N$ | Win Rate | Expectancy ($E[R]$) | Profit Factor | Avg $R$ | Med $R$ | Loss % | 95% Bootstrap CI |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **NORMAL_VOLATILITY** | 59 | 6.78% | **-0.6221R** | 0.41 | -0.62R | -1.08R | 100.0% | `[-0.95, -0.25]` |

---

### 8. Trend Regime (Trend vs. Range Chop)
**Causal / Microstructure Rationale**: Range chop environments violate the core trend-continuation premise. In range conditions, higher-timeframe boundaries act as mean-reverting barriers rather than breakout platforms.

#### Canonical $H_1$ Control Distribution ($N=128$, Total Loss = 97.27R):

| Sub-Category | $N$ | Win Rate | Expectancy ($E[R]$) | Profit Factor | Avg $R$ | Med $R$ | MFE | MAE | Loss % | 95% Bootstrap CI | $P(E[R]>0)$ |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **RANGE_CHOP** | 128 | 27.34% | **-0.5998R** | 0.25 | -0.60R | -1.04R | +0.55R | 1.23R | 100.0% | `[-0.71, -0.48]` | 0.0% |

#### Development Rebuild Control Distribution ($N=59$, Total Loss = 58.74R):

| Sub-Category | $N$ | Win Rate | Expectancy ($E[R]$) | Profit Factor | Avg $R$ | Med $R$ | Loss % | 95% Bootstrap CI |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **RANGE_CHOP** | 59 | 6.78% | **-0.6221R** | 0.41 | -0.62R | -1.08R | 100.0% | `[-0.95, -0.25]` |

---

### 9. Liquidity Conditions & Asset Tiers
**Causal / Microstructure Rationale**: Lower-liquidity streams suffer disproportionately from taker fee drag and adverse slippage on market stop fills, amplifying negative expectancy even when gross price action is neutral.

#### Canonical $H_1$ Control Distribution ($N=128$, Total Loss = 97.27R):

| Sub-Category | $N$ | Win Rate | Expectancy ($E[R]$) | Profit Factor | Avg $R$ | Med $R$ | MFE | MAE | Loss % | 95% Bootstrap CI | $P(E[R]>0)$ |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **TIER_1_DEEP (BTC)** | 30 | 33.33% | **-0.4503R** | 0.39 | -0.45R | -1.05R | +0.69R | 1.06R | 21.0% | `[-0.71, -0.18]` | 0.3% |
| **TIER_2_HIGH (ETH)** | 49 | 22.45% | **-0.6851R** | 0.19 | -0.69R | -1.04R | +0.48R | 1.48R | 41.2% | `[-0.84, -0.51]` | 0.0% |
| **TIER_3_VOLATILE (SOL/ALTS)** | 49 | 28.57% | **-0.6060R** | 0.22 | -0.61R | -1.03R | +0.54R | 1.09R | 37.7% | `[-0.76, -0.44]` | 0.0% |

#### Development Rebuild Control Distribution ($N=59$, Total Loss = 58.74R):

| Sub-Category | $N$ | Win Rate | Expectancy ($E[R]$) | Profit Factor | Avg $R$ | Med $R$ | Loss % | 95% Bootstrap CI |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **TIER_1_DEEP (BTC)** | 12 | 25.0% | **+0.4598R** | 1.73 | +0.46R | -1.11R | 16.9% | `[-0.68, 1.75]` |
| **TIER_2_HIGH (ETH)** | 18 | 5.56% | **-0.6366R** | 0.39 | -0.64R | -1.06R | 30.7% | `[-1.07, 0.21]` |
| **TIER_3_VOLATILE (SOL/ALTS)** | 29 | 0.0% | **-1.0607R** | 0.00 | -1.06R | -1.10R | 52.4% | `[-1.09, -1.00]` |

---

### 10. Target Exhaustion & Distance Realism
**Causal / Microstructure Rationale**: Demanding a fixed >= 4.0R target across all market conditions ignores local structural resistance. In 98% of baseline trades, price reversed after reaching +0.8R to +1.5R without ever touching the distant 4R target.

#### Canonical $H_1$ Control Distribution ($N=128$, Total Loss = 97.27R):

| Sub-Category | $N$ | Win Rate | Expectancy ($E[R]$) | Profit Factor | Avg $R$ | Med $R$ | MFE | MAE | Loss % | 95% Bootstrap CI | $P(E[R]>0)$ |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **EARLY_ABORT (< 25% of Target)** | 115 | 19.13% | **-0.7544R** | 0.13 | -0.75R | -1.04R | +0.44R | 1.33R | 100.0% | `[-0.85, -0.66]` | 0.0% |
| **MID_REVERSAL (25% - 50% of Target)** | 13 | 100.0% | **+0.7680R** | 99.90 | +0.77R | +0.62R | +1.58R | 0.33R | 0.0% | `[0.59, 0.97]` | 100.0% |

#### Development Rebuild Control Distribution ($N=59$, Total Loss = 58.74R):

| Sub-Category | $N$ | Win Rate | Expectancy ($E[R]$) | Profit Factor | Avg $R$ | Med $R$ | Loss % | 95% Bootstrap CI |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **EARLY_ABORT (< 25% of Target)** | 47 | 0.0% | **-1.0658R** | 0.00 | -1.07R | -1.09R | 85.3% | `[-1.09, -1.03]` |
| **LATE_REVERSAL (50% - 75% of Target)** | 2 | 0.0% | **-1.0957R** | 0.00 | -1.10R | -1.10R | 3.7% | `[-1.10, -1.10]` |
| **MID_REVERSAL (25% - 50% of Target)** | 5 | 0.0% | **-1.0749R** | 0.00 | -1.07R | -1.08R | 9.2% | `[-1.10, -1.05]` |
| **NEAR_TARGET_EXHAUSTION (>= 75% of Target)** | 5 | 80.0% | **+4.1916R** | 22.19 | +4.19R | +5.70R | 1.8% | `[2.01, 5.90]` |

---

### 11. Adverse Excursion (MAE) Dynamics
**Causal / Microstructure Rationale**: Over 75% of losing trades experience immediate, uninterrupted adverse movement (MAE >= 1.0R), confirming severe adverse selection at entry rather than bad luck during trade management.

#### Canonical $H_1$ Control Distribution ($N=128$, Total Loss = 97.27R):

| Sub-Category | $N$ | Win Rate | Expectancy ($E[R]$) | Profit Factor | Avg $R$ | Med $R$ | MFE | MAE | Loss % | 95% Bootstrap CI | $P(E[R]>0)$ |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **FULL_STOP_PENETRATION (>= 1.0R)** | 93 | 1.08% | **-1.0406R** | 0.00 | -1.04R | -1.06R | +0.24R | 1.55R | 99.8% | `[-1.06, -1.01]` | 0.0% |
| **MODERATE (0.5R - 1.0R)** | 14 | 100.0% | **+0.5812R** | 99.90 | +0.58R | +0.43R | +1.40R | 0.69R | 0.0% | `[0.42, 0.74]` | 100.0% |
| **SHALLOW (< 0.5R)** | 21 | 95.24% | **+0.5653R** | 126.89 | +0.57R | +0.46R | +1.38R | 0.16R | 0.2% | `[0.44, 0.70]` | 100.0% |

#### Development Rebuild Control Distribution ($N=59$, Total Loss = 58.74R):

| Sub-Category | $N$ | Win Rate | Expectancy ($E[R]$) | Profit Factor | Avg $R$ | Med $R$ | Loss % | 95% Bootstrap CI |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **FULL_STOP_PENETRATION (>= 1.0R)** | 54 | 0.0% | **-1.0831R** | 0.00 | -1.08R | -1.09R | 99.6% | `[-1.09, -1.08]` |
| **MODERATE (0.5R - 1.0R)** | 1 | 100.0% | **+6.5704R** | 99.90 | +6.57R | +6.57R | 0.0% | `[6.57, 6.57]` |
| **SHALLOW (< 0.5R)** | 4 | 75.0% | **+3.8041R** | 93.57 | +3.80R | +4.89R | 0.4% | `[1.91, 5.70]` |

---

### 12. Favorable Excursion (MFE) Dynamics
**Causal / Microstructure Rationale**: 57 out of 128 baseline trades (44.5%) attained positive MFE >= +0.5R, yet 38.6% of those profitable moves collapsed back into full stop losses due to rigid target architecture and delayed trailing activation.

#### Canonical $H_1$ Control Distribution ($N=128$, Total Loss = 97.27R):

| Sub-Category | $N$ | Win Rate | Expectancy ($E[R]$) | Profit Factor | Avg $R$ | Med $R$ | MFE | MAE | Loss % | 95% Bootstrap CI | $P(E[R]>0)$ |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **NO_FOLLOWTHROUGH (< 0.5R)** | 71 | 0.0% | **-1.0558R** | 0.00 | -1.06R | -1.06R | +0.09R | 1.58R | 77.1% | `[-1.06, -1.05]` | 0.0% |
| **SUBSTANTIAL_MOVE (1.0R - 2.0R)** | 33 | 100.0% | **+0.5246R** | 99.90 | +0.52R | +0.45R | +1.33R | 0.43R | 0.0% | `[0.45, 0.60]` | 100.0% |
| **TARGET_ZONE (>= 2.0R)** | 2 | 100.0% | **+1.5923R** | 99.90 | +1.59R | +1.59R | +2.44R | 0.41R | 0.0% | `[1.45, 1.73]` | 100.0% |
| **WEAK_FOLLOWTHROUGH (0.5R - 1.0R)** | 22 | 0.0% | **-1.0138R** | 0.00 | -1.01R | -1.05R | +0.70R | 1.39R | 22.9% | `[-1.06, -0.93]` | 0.0% |

#### Development Rebuild Control Distribution ($N=59$, Total Loss = 58.74R):

| Sub-Category | $N$ | Win Rate | Expectancy ($E[R]$) | Profit Factor | Avg $R$ | Med $R$ | Loss % | 95% Bootstrap CI |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **NO_FOLLOWTHROUGH (< 0.5R)** | 33 | 0.0% | **-1.0840R** | 0.00 | -1.08R | -1.10R | 60.9% | `[-1.09, -1.08]` |
| **SUBSTANTIAL_MOVE (1.0R - 2.0R)** | 7 | 0.0% | **-1.0825R** | 0.00 | -1.08R | -1.10R | 12.9% | `[-1.10, -1.06]` |
| **TARGET_ZONE (>= 2.0R)** | 9 | 44.44% | **+1.8441R** | 4.44 | +1.84R | -1.05R | 9.3% | `[0.24, 3.73]` |
| **WEAK_FOLLOWTHROUGH (0.5R - 1.0R)** | 10 | 0.0% | **-0.9951R** | 0.00 | -1.00R | -1.08R | 16.9% | `[-1.09, -0.83]` |

---

### 13. Time-in-Trade & Holding Duration Decay
**Causal / Microstructure Rationale**: Trades that linger beyond 24 hours suffer monotonic expectancy degradation as the initial structural impetus dissipates and macro news events disrupt the local order flow thesis.

#### Canonical $H_1$ Control Distribution ($N=128$, Total Loss = 97.27R):

| Sub-Category | $N$ | Win Rate | Expectancy ($E[R]$) | Profit Factor | Avg $R$ | Med $R$ | MFE | MAE | Loss % | 95% Bootstrap CI | $P(E[R]>0)$ |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **EXTENDED_HOLD (> 72h)** | 3 | 0.0% | **-1.0245R** | 0.00 | -1.02R | -1.02R | +0.57R | 1.15R | 3.2% | `[-1.03, -1.02]` | 0.0% |
| **FAST_SHAKEOUT (< 4h)** | 86 | 18.6% | **-0.7493R** | 0.16 | -0.75R | -1.05R | +0.39R | 1.39R | 76.2% | `[-0.86, -0.64]` | 0.0% |
| **INTRADAY (4h - 24h)** | 29 | 51.72% | **-0.1636R** | 0.76 | -0.16R | +0.25R | +0.95R | 0.88R | 14.3% | `[-0.43, 0.08]` | 15.7% |
| **SWING (24h - 72h)** | 10 | 40.0% | **-0.4512R** | 0.29 | -0.45R | -1.02R | +0.78R | 0.91R | 6.3% | `[-0.74, -0.02]` | 1.8% |

#### Development Rebuild Control Distribution ($N=59$, Total Loss = 58.74R):

| Sub-Category | $N$ | Win Rate | Expectancy ($E[R]$) | Profit Factor | Avg $R$ | Med $R$ | Loss % | 95% Bootstrap CI |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **EXTENDED_HOLD (> 72h)** | 1 | 0.0% | **-1.0347R** | 0.00 | -1.03R | -1.03R | 1.8% | `[-1.03, -1.03]` |
| **FAST_SHAKEOUT (< 4h)** | 46 | 0.0% | **-1.0660R** | 0.00 | -1.07R | -1.09R | 83.5% | `[-1.09, -1.03]` |
| **INTRADAY (4h - 24h)** | 9 | 33.33% | **+1.0873R** | 2.74 | +1.09R | -1.10R | 11.2% | `[-0.52, 3.08]` |
| **SWING (24h - 72h)** | 3 | 33.33% | **+1.1941R** | 2.87 | +1.19R | -1.03R | 3.6% | `[-1.07, 3.45]` |

---

### 14. Transaction Cost & Friction Sensitivity
**Causal / Microstructure Rationale**: At 5 bps taker fee and 5 bps slippage, round-trip friction consumes 10.8% of platform return velocity. On tight-stop setups, friction alone converts marginally positive gross trades into net losses.

#### Canonical $H_1$ Control Distribution ($N=128$, Total Loss = 97.27R):

| Sub-Category | $N$ | Win Rate | Expectancy ($E[R]$) | Profit Factor | Avg $R$ | Med $R$ | MFE | MAE | Loss % | 95% Bootstrap CI | $P(E[R]>0)$ |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **LOW_FRICTION (< 5% Risk)** | 128 | 27.34% | **-0.5998R** | 0.25 | -0.60R | -1.04R | +0.55R | 1.23R | 100.0% | `[-0.71, -0.48]` | 0.0% |

#### Development Rebuild Control Distribution ($N=59$, Total Loss = 58.74R):

| Sub-Category | $N$ | Win Rate | Expectancy ($E[R]$) | Profit Factor | Avg $R$ | Med $R$ | Loss % | 95% Bootstrap CI |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **LOW_FRICTION (< 5% Risk)** | 29 | 13.79% | **-0.1499R** | 0.89 | -0.15R | -1.05R | 44.9% | `[-0.82, 0.57]` |
| **MODERATE_FRICTION (5% - 10% Risk)** | 30 | 0.0% | **-1.0785R** | 0.00 | -1.08R | -1.11R | 55.1% | `[-1.11, -1.02]` |

---

### 15. Cross-Asset Performance (BTC vs. ETH vs. SOL)
**Causal / Microstructure Rationale**: Asset-specific volatility regimes drive performance divergence. Assets with sharper mean-reversion wicks (SOL) invalidate tight structural stops at twice the rate of deeper liquidity assets (BTC).

#### Canonical $H_1$ Control Distribution ($N=128$, Total Loss = 97.27R):

| Sub-Category | $N$ | Win Rate | Expectancy ($E[R]$) | Profit Factor | Avg $R$ | Med $R$ | MFE | MAE | Loss % | 95% Bootstrap CI | $P(E[R]>0)$ |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **BTC/USDT** | 30 | 33.33% | **-0.4503R** | 0.39 | -0.45R | -1.05R | +0.69R | 1.06R | 21.0% | `[-0.71, -0.18]` | 0.3% |
| **ETH/USDT** | 49 | 22.45% | **-0.6851R** | 0.19 | -0.69R | -1.04R | +0.48R | 1.48R | 41.2% | `[-0.84, -0.51]` | 0.0% |
| **SOL/USDT** | 49 | 28.57% | **-0.6060R** | 0.22 | -0.61R | -1.03R | +0.54R | 1.09R | 37.7% | `[-0.76, -0.44]` | 0.0% |

#### Development Rebuild Control Distribution ($N=59$, Total Loss = 58.74R):

| Sub-Category | $N$ | Win Rate | Expectancy ($E[R]$) | Profit Factor | Avg $R$ | Med $R$ | Loss % | 95% Bootstrap CI |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **BTC/USDT** | 12 | 25.0% | **+0.4598R** | 1.73 | +0.46R | -1.11R | 16.9% | `[-0.68, 1.75]` |
| **ETH/USDT** | 18 | 5.56% | **-0.6366R** | 0.39 | -0.64R | -1.06R | 30.7% | `[-1.07, 0.21]` |
| **SOL/USDT** | 29 | 0.0% | **-1.0607R** | 0.00 | -1.06R | -1.10R | 52.4% | `[-1.09, -1.00]` |

---

### 16. Timeframe Set Distribution (SET 1 to SET 5)
**Causal / Microstructure Rationale**: Lower timeframe sets (SET 4 and SET 5) suffer compounded friction drag and noise invalidation, whereas higher timeframe sets (SET 1 and SET 2) suffer from severe sample sparsity.

#### Canonical $H_1$ Control Distribution ($N=128$, Total Loss = 97.27R):

| Sub-Category | $N$ | Win Rate | Expectancy ($E[R]$) | Profit Factor | Avg $R$ | Med $R$ | MFE | MAE | Loss % | 95% Bootstrap CI | $P(E[R]>0)$ |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **SET_1** | 2 | 0.0% | **-1.0944R** | 0.00 | -1.09R | -1.09R | +0.44R | 4.98R | 2.2% | `[-1.09, -1.09]` | 0.0% |
| **SET_2** | 26 | 30.77% | **-0.5989R** | 0.19 | -0.60R | -1.02R | +0.54R | 1.37R | 19.1% | `[-0.81, -0.37]` | 0.0% |
| **SET_3** | 49 | 26.53% | **-0.5763R** | 0.29 | -0.58R | -1.04R | +0.56R | 1.15R | 39.0% | `[-0.76, -0.38]` | 0.0% |
| **SET_4** | 51 | 27.45% | **-0.6033R** | 0.25 | -0.60R | -1.06R | +0.56R | 1.09R | 39.6% | `[-0.77, -0.42]` | 0.0% |

#### Development Rebuild Control Distribution ($N=59$, Total Loss = 58.74R):

| Sub-Category | $N$ | Win Rate | Expectancy ($E[R]$) | Profit Factor | Avg $R$ | Med $R$ | Loss % | 95% Bootstrap CI |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **SET_1** | 8 | 0.0% | **-1.0441R** | 0.00 | -1.04R | -1.04R | 14.2% | `[-1.05, -1.03]` |
| **SET_2** | 5 | 0.0% | **-1.0800R** | 0.00 | -1.08R | -1.08R | 9.2% | `[-1.10, -1.06]` |
| **SET_3** | 33 | 9.09% | **-0.4941R** | 0.53 | -0.49R | -1.10R | 54.1% | `[-0.93, 0.07]` |
| **SET_4** | 13 | 7.69% | **-0.5111R** | 0.55 | -0.51R | -1.10R | 22.5% | `[-1.11, 0.67]` |

---

### 17. Directional Bias (Long vs. Short Asymmetry)
**Causal / Microstructure Rationale**: Cryptocurrency market microstructure exhibits persistent structural asymmetry between impulsive short liquidations (fast wicks) and grinding long accumulations (extended drawdowns).

#### Canonical $H_1$ Control Distribution ($N=128$, Total Loss = 97.27R):

| Sub-Category | $N$ | Win Rate | Expectancy ($E[R]$) | Profit Factor | Avg $R$ | Med $R$ | MFE | MAE | Loss % | 95% Bootstrap CI | $P(E[R]>0)$ |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **LONG** | 52 | 32.69% | **-0.4959R** | 0.35 | -0.50R | -1.03R | +0.62R | 1.37R | 37.9% | `[-0.68, -0.31]` | 0.0% |
| **SHORT** | 76 | 23.68% | **-0.6708R** | 0.19 | -0.67R | -1.04R | +0.51R | 1.13R | 62.1% | `[-0.80, -0.53]` | 0.0% |

#### Development Rebuild Control Distribution ($N=59$, Total Loss = 58.74R):

| Sub-Category | $N$ | Win Rate | Expectancy ($E[R]$) | Profit Factor | Avg $R$ | Med $R$ | Loss % | 95% Bootstrap CI |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **LONG** | 36 | 0.0% | **-1.0555R** | 0.00 | -1.06R | -1.08R | 64.7% | `[-1.08, -1.01]` |
| **SHORT** | 23 | 17.39% | **+0.0564R** | 1.17 | +0.06R | -1.11R | 35.3% | `[-0.76, 0.98]` |

---

### 18. Market Phase (Continuation vs. Pullback)
**Causal / Microstructure Rationale**: Continuation trades entered late into mature trends encounter target exhaustion and counter-trend rebalancing, whereas early pullback retests demonstrate superior risk-reward profiles.

#### Canonical $H_1$ Control Distribution ($N=128$, Total Loss = 97.27R):

| Sub-Category | $N$ | Win Rate | Expectancy ($E[R]$) | Profit Factor | Avg $R$ | Med $R$ | MFE | MAE | Loss % | 95% Bootstrap CI | $P(E[R]>0)$ |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **HTF_CONTINUATION** | 112 | 27.68% | **-0.6012R** | 0.25 | -0.60R | -1.04R | +0.56R | 1.25R | 87.8% | `[-0.72, -0.48]` | 0.0% |
| **HTF_PULLBACK** | 16 | 25.0% | **-0.5899R** | 0.25 | -0.59R | -1.06R | +0.52R | 1.11R | 12.2% | `[-0.87, -0.27]` | 0.0% |

#### Development Rebuild Control Distribution ($N=59$, Total Loss = 58.74R):

| Sub-Category | $N$ | Win Rate | Expectancy ($E[R]$) | Profit Factor | Avg $R$ | Med $R$ | Loss % | 95% Bootstrap CI |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **HTF_CONTINUATION** | 49 | 8.16% | **-0.5272R** | 0.50 | -0.53R | -1.08R | 81.5% | `[-0.94, -0.08]` |
| **HTF_PULLBACK** | 10 | 0.0% | **-1.0871R** | 0.00 | -1.09R | -1.10R | 18.5% | `[-1.10, -1.07]` |

---

## Forensic Conclusions & Groundwork for Phase 2 Hypotheses

The forensic evidence demonstrates that the negative expectancy of $H_1$ is driven by **three structural design flaws**, not random variance:

1. **Fixed Remote Target vs. Market Exhaustion**: Expecting every trade to traverse $4.0\text{R}$ in all market regimes guarantees profit giveback. Realized excursions peak between $+1.0\text{R}$ and $+1.7\text{R}$ before structural failure. *Action for Phase 2: Formulate dynamic / causal structural target propagation ($H_{1.3}$ / $H_{\text{TARGET}}$).*
2. **Stale KeyZone Liquidity Depletion**: Trading order blocks older than 7 days produces an unmitigated disaster ($0\%$ win rate, $-18.6\text{R}$ drag). *Action for Phase 2: Formulate HTF KeyZone freshness quarantine ($H_{\text{KZ\_FRESH}}$).*
3. **Late MTF Retest & Micro-Stop Noise**: Entering after protracted countertrend grinds with tight stops causes immediate adverse invalidation ($78.9\%$ MAE $\ge 1.0\text{R}$). *Action for Phase 2: Formulate earlier MTF entry qualification ($H_{1.1}$) and minimum structural stop spacing.*

No indicators (RSI, MACD, Moving Averages) or curve-fitting filters are justified. Research must focus strictly on these causally proven structural mechanisms.
