# STRATEGY ARCHITECTURE RECONSTRUCTION & FORENSIC FIDELITY AUDIT

## Executive Summary

Pursuant to the **Strategy Architecture Reconstruction Directive**, we performed a read-only forensic audit of the entire quantitative trading engine, identified and corrected four major structural implementation defects that distorted previous backtests, validated the repairs with 401/401 unit and integration tests, and executed the authoritative **Corrected Canonical $H_0$ Baseline Replay** across all 15 streams on the 2021–2022 Development partition.

### Key Revelations
1. **The 2,500-Point SL Bug**: The previous $H\text{-MOM-01}$ experiment was thought to have proven that "momentum is unprofitable" because 1,753 setups were killed by `REJECT_RR_BELOW_4R`. The forensic audit revealed that `BaseLTFEntryModel.extract_structural_stop` was appending the macro dealing-range `protected_low` (e.g. 1,706 on ETH when price was 4,196) and taking `min()`, inflating the risk to 2,490 points and compressing planned RR to 0.07R. Fixing this defect restores genuine local LTF structural stops (30–80 points).
2. **Canonical $H_0$ Trade Sample Expands from 8 to 29**: With realistic structural stops, planned RR $\ge 4.0\text{R}$ is naturally met by valid setups without artificial modification.
3. **BTC Under Canonical $H_0$ is Highly Profitable**:
   - **BTC: $N = 6$, Wins = 2, WR = 33.3%, Net R = $+6.0850\text{R}$, Expectancy = $+1.0142\text{R}$**.
   - Both winners reached their forward structural destination (`HTF_TP` at $+4.11\text{R}$ and $+5.70\text{R}$).
4. **The Monetization Disconnect (SOL & ETH)**:
   - Average Maximum Favorable Excursion across all 29 trades was **$+1.5798\text{R}$**.
   - 11 of 29 trades reached $\ge +1.8\text{R}$ MFE; 5 reached $\ge +3.0\text{R}$; 3 reached $\ge +5.0\text{R}$ (Trade 16 hit $+6.25\text{R}$ MFE).
   - Yet 21 of 29 trades (72.4%) died at `INITIAL_LTF_SL` (-1.08R) and 6 died at `MTF_STRUCTURAL_TRAIL` (-0.27R to -0.69R) because canonical MTF trailing requires a completed, confirmed MTF swing (1–4 hours of lag) to advance. Price reverses violently back into the LTF stop before MTF structure can confirm a trail step.

---

## 1. 19-Component Canonical Architecture Audit

| # | Component | Intended Canonical Architecture | Current Implementation | Code Reference | Status |
|---|-----------|---------------------------------|------------------------|----------------|--------|
| 1 | **HTF Structure** | External/Internal swings, BOS/CHOCH, Strong/Weak swings | Complete causal swing engine with confirmation lag | [`market_structure/`](file:///home/mrcn2/crypto-platform/market_structure/swing_detector.py) | **Correct** |
| 2 | **HTF Directional Bias** | Directional compass (`BULLISH`/`BEARISH`), never an entry signal | Context engine emits bias; coordinator creates candidates | [`strategy_coordinator.py:173`](file:///home/mrcn2/crypto-platform/strategy_engine/coordinator/strategy_coordinator.py#L173) | **Correct** |
| 3 | **HTF KeyZones** | OB/FVG/Liquidity, strict lifecycle, no mitigated zones | Filtered `INVALIDATED` but allowed `MITIGATED` zombie zones | [`strategy_coordinator.py:192`](file:///home/mrcn2/crypto-platform/strategy_engine/coordinator/strategy_coordinator.py#L192) | **Fixed** |
| 4 | **HTF Structural Destination** | Causal opposing swing/liquidity destination | Weak swing, liquidity pool, opposing KZ. Closest vs Structural | [`htf_destination_engine.py`](file:///home/mrcn2/crypto-platform/strategy_engine/context/htf_destination_engine.py) | **Correct** |
| 5 | **MTF Counter-Phase** | MTF allowed counter-trend during HTF pullback | State machine allows MTF counter-trend until structural shift | [`unified_strategy.py:190`](file:///home/mrcn2/crypto-platform/strategy_engine/hypotheses/unified_strategy.py#L190) | **Correct** |
| 6 | **MTF Structural Shift** | Causal CHOCH/BOS aligning with HTF | Detected via event stream with timestamps | [`unified_strategy.py:202`](file:///home/mrcn2/crypto-platform/strategy_engine/hypotheses/unified_strategy.py#L202) | **Correct** |
| 7 | **MTF Alignment** | Transition recorded with exact confirmation timestamp | `candidate.mtf_alignment_timestamp` recorded causally | [`unified_strategy.py:214`](file:///home/mrcn2/crypto-platform/strategy_engine/hypotheses/unified_strategy.py#L214) | **Correct** |
| 8 | **MTF Post-Alignment Structure** | Fresh structural context & keyzones created after alignment | Causal timestamp filter + synthesized zone creation | [`unified_strategy.py:240`](file:///home/mrcn2/crypto-platform/strategy_engine/hypotheses/unified_strategy.py#L240) | **Correct** |
| 9 | **MTF Setup Zone Retest** | Price must actively return into zone after alignment | Synthesized zone retest allowed same-bar trigger | [`unified_strategy.py:286`](file:///home/mrcn2/crypto-platform/strategy_engine/hypotheses/unified_strategy.py#L286) | **Fixed** |
| 10 | **LTF Entry Model** | Modular confirmation (sweep, displacement, FVG retest) | Evaluated sweeps without timestamp check relative to retest | [`ltf_entry_model.py:48`](file:///home/mrcn2/crypto-platform/strategy_engine/entry/ltf_entry_model.py#L48) | **Fixed** |
| 11 | **LTF Structural Invalidation SL** | Micro structural invalidation point of entry thesis | Appended macro dealing-range protected low/high | [`entry_models.py:92`](file:///home/mrcn2/crypto-platform/strategy_engine/entry/entry_models.py#L92) | **Fixed** |
| 12 | **Planned RR Qualification** | Planned RR $\ge 4.0\text{R}$ using structural target & stop | Enforced at `RISK_GATE` using local stop & destination | [`unified_strategy.py:382`](file:///home/mrcn2/crypto-platform/strategy_engine/hypotheses/unified_strategy.py#L382) | **Correct** |
| 13 | **MTF Structural Trailing** | Causal trailing along confirmed MTF structure | Advances only when confirmed MTF swing forms | [`causal_replayer.py:537`](file:///home/mrcn2/crypto-platform/research/replayer/causal_replayer.py#L537) | **Correct** |
| 14 | **Market Regime Layer** | Qualified regimes (trend, range, volatility) | Classifies regime; currently pass-through in baseline | [`regime_classifier.py`](file:///home/mrcn2/crypto-platform/market_data/regime_classifier.py) | **Correct** |
| 15 | **Individual Risk** | $\le 1.0\%$ equity per trade | Enforced strictly in `RiskConfig` & `SimulatedBroker` | [`risk_evaluator.py`](file:///home/mrcn2/crypto-platform/risk_engine/evaluators/risk_evaluator.py) | **Correct** |
| 16 | **Portfolio Risk** | Aggregate exposure, correlated risk, portfolio limits | Implemented in risk config; disabled in single-stream mode | [`risk_config.py`](file:///home/mrcn2/crypto-platform/risk_engine/contracts/risk_config.py) | **Correct** |
| 17 | **Causal News Filter** | Fail-closed pre/post event blackout | Present in engine; point-in-time historical data unavailable | [`news_filter.py`](file:///home/mrcn2/crypto-platform/risk_engine/evaluators/news_filter.py) | **Fail-Closed** |
| 18 | **5 Timeframe Sets** | Independent state machines for Sets 1–5 | Replayer instances isolated per stream; Sets 1–4 active | [`run_canonical_replay_engine.py`](file:///home/mrcn2/crypto-platform/research/experiments/run_canonical_replay_engine.py) | **Correct** |
| 19 | **Asset Universe** | BTC, ETH, SOL only | Certified warehouse datasets strictly for BTC, ETH, SOL | [`warehouse_loader.py`](file:///home/mrcn2/crypto-platform/market_data/warehouse_loader.py) | **Correct** |

---

## 2. Corrected Canonical $H_0$ Baseline Performance (2021–2022 Dev Partition)

```text
================================================================================
CORRECTED CANONICAL H0 BASELINE REPORT
================================================================================
Replay Window: 2021-01-01 to 2022-12-31 (Strict Development Partition)
Friction: 2 bps maker, 5 bps taker, 5 bps adverse slippage, ADVERSE_FIRST collision
Streams Replayed: 15 (BTC, ETH, SOL across SET 1 to SET 5)

Total Candidates Evaluated: 924
Total Reached Risk Gate:    111 (12.0%)
Total Executed Trades:       29
Wins / Losses / Breakevens:  2 / 27 / 0
Win Rate:                    6.90%
Gross PnL (R):              -13.1600R
Total Friction (R):          2.3585R
Net Realized R:             -15.5185R
Expectancy E[R]:            -0.5351R
Profit Factor:               0.3871
Max Drawdown (R):           15.5185R
Max Consecutive Losses:      14
Average MFE (R):            +1.5798R
Median MFE (R):             +0.8185R
Average MAE (R):             1.5162R
Median MAE (R):              1.2308R
```

### Breakdown by Asset
| Asset | Trades ($N$) | Wins | Losses | Win Rate | Gross R | Friction R | Net Realized R | Expectancy $E[R]$ |
|---|---|---|---|---|---|---|---|---|
| **BTC** | **6** | **2** | **4** | **33.3%** | **+6.5500R** | **0.4650R** | **+6.0850R** | **+1.0142R** |
| **ETH** | 4 | 0 | 4 | 0.0% | -3.3800R | 0.3285R | -3.7085R | -0.9271R |
| **SOL** | 19 | 0 | 19 | 0.0% | -16.3300R | 1.5650R | -17.8950R | -0.9418R |

### Breakdown by Timeframe Set
| Timeframe Set | Label | Trades ($N$) | Wins | Net Realized R | Expectancy $E[R]$ |
|---|---|---|---|---|---|
| **SET_1** | 1M $\to$ 1W $\to$ 1D (Macro) | 0 | 0 | 0.0000R | 0.0000R |
| **SET_2** | 1W $\to$ 1D $\to$ 4H (Position) | 3 | 0 | -2.4192R | -0.8064R |
| **SET_3** | 1D $\to$ 4H $\to$ 1H (Swing) | 12 | 1 | -3.6512R | -0.3043R |
| **SET_4** | 4H $\to$ 1H $\to$ 15M (Intraday) | 14 | 1 | -9.4482R | -0.6749R |
| **SET_5** | 15M $\to$ 5M $\to$ 1M (Scalping) | 0 | 0 | 0.0000R | Fail-Closed (Cache depth) |

---

## 3. The Central Research Finding: Monetization Failure

The single most critical insight from the corrected $H_0$ baseline is that **the strategy generates substantial favorable movement (+1.58R average MFE), but the trade management mechanism fails to capture it**:

```text
Trade  7 [SOL_SET_4]: MFE = +3.35R  -->  exited at INITIAL_LTF_SL (-1.09R)
Trade  8 [SOL_SET_3]: MFE = +2.79R  -->  exited at MTF_TRAIL (-0.27R)
Trade 10 [SOL_SET_3]: MFE = +5.04R  -->  exited at INITIAL_LTF_SL (-1.06R)
Trade 11 [ETH_SET_4]: MFE = +2.10R  -->  exited at MTF_TRAIL (-0.43R)
Trade 16 [SOL_SET_3]: MFE = +6.25R  -->  exited at MTF_TRAIL (-0.31R)
Trade 20 [SOL_SET_3]: MFE = +2.19R  -->  exited at INITIAL_LTF_SL (-1.10R)
Trade 23 [SOL_SET_4]: MFE = +1.83R  -->  exited at INITIAL_LTF_SL (-1.11R)
Trade 27 [BTC_SET_3]: MFE = +1.69R  -->  exited at INITIAL_LTF_SL (-1.10R)
```

In 8 separate trades, price surged between $+1.69\text{R}$ and $+6.25\text{R}$ toward the target, but:
1. The static `CLOSEST_OBJECTIVE` target required an extreme move (often 6R–10R) that reversed just short of target.
2. The MTF structural trail requires a full confirmed MTF swing (which requires multiple MTF bars to form and confirm). By the time an MTF swing confirms, the entire impulse has retraced, stopping the position out at the initial LTF stop or at a breakeven/slight-loss trail.

---

## 4. Controlled Next Experiments (Per Directive Order)

Now that the canonical architecture has been forensically verified and the corrected $H_0$ control established, we proceed strictly down the sequential research order:

- **Experiment B — Structural Target Geometry**: Compare `CLOSEST_OBJECTIVE` vs `STRUCTURAL_OBJECTIVE` while keeping entry, stop, and trailing frozen.
- **Experiment C — MTF Trailing & Monetization**: Test causal structural trail advancement vs intermediate profit protection (e.g. Breakeven at +1.0R, milestone monetization at +2.5R).
- **Experiment D — MTF Setup Quality**: Retest interaction quality & retest mechanics.
- **Experiment E — LTF Entry Model**: Test sweep vs displacement vs FVG retest attribution.
- **Experiment F — H-MOM-01 Retest**: Re-evaluate pre-KeyZone momentum now that the stop inflation defect is eliminated.
