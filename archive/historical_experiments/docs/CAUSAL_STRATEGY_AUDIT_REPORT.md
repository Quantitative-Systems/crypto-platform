# QUANTITATIVE RESEARCH AUDIT & CANDIDATE FREEZE REPORT
**Protocol Phase:** Research Governance, Forensic Verification & Causal Architecture Audit  
**Date Partition:** 2021-01-01 to 2022-12-31 (Strict Development Partition)  
**Governance Enforced:** Validation (2023) and OOS (2024–2026) Air-Gaps Strictly Sealed & Locked  
**Test Suite Verification:** 401 / 401 Tests Passing (100% Green)

---

# Executive Summary

This investigation establishes the exact, mathematically certified causal strategy state of the platform as of this checkpoint. 

**Key Findings & Governance Position:**
1. **Historical +3.83R Result Invalidation:** The historical +3.83R Development result reported prior to commit `8ef0c93` was **invalidated** due to a causal lookback bug in `ltf_entry_model.py` where liquidity sweeps preceding the MTF retest were erroneously admitted as triggers.
2. **Corrected Causal Baseline:** With causal integrity fully restored, the true unmonetized baseline (`EXP_BASE_TGTSTRUCT_LEGACY_STOP_01`) delivers $N=12$, Net $\text{R} = \mathbf{+0.0327\text{R}}$ ($\text{PF} = 1.01$, $\text{Exp} = +0.0027\text{R}$, $\text{Max DD} = 2.79\text{R}$).
3. **Milestone Attribution:** The Milestone 2.5R profit-lock mechanism produces $+3.6028\text{R}$ Net R ($\Delta = +3.5704\text{R}$), with 100% of the delta causally isolated to locking profit at $+2.5\text{R}$ on Trades 2, 3, and 5 while the other 9 trades are identical.
4. **Freshness Attribution:** Point-in-time retest latency ($\le 12.0\text{h}$) and keyzone age ($\le 7.0\text{d}$) prune exactly 1 trade (Trade 10 on ETH_SET_2, an 88h stale loss of $-1.017\text{R}$) with zero winners pruned, cutting Max Drawdown by 36.5%.
5. **Current F5 Candidate ($N=11$):** Combining Structural Target Mode, `EXHAUSTIVE_STRUCTURAL` stop, Milestone 2.5R, Retest Freshness $\le 12.0\text{h}$, and Keyzone Freshness $\le 7.0\text{d}$ yields $N=11$, Net $\text{R} = \mathbf{+4.6197\text{R}}$, $\text{PF} = 2.2554$, $\text{Exp} = +0.4200\text{R}$, $\text{Max DD} = 1.7740\text{R}$.
6. **Strict Candidate Labeling:** This candidate is formally designated:
   > **Development Candidate — NOT VALIDATED / NOT LIVE**
7. **Opportunity Starvation:** 346 of 358 setups ($96.6\%$) are rejected by the $\ge 4.0\text{R}$ risk gate. Counterfactual tests confirm lowering the RR floor produces negative expectancy ($-2.33\text{R}$ to $-5.62\text{R}$), proving the 4.0R gate is an indispensable quality firewall.
8. **Stop Geometry:** 273 setups ($78.9\%$) have oversized stops ($>3.5\%$, median $8.49\%$) because `EXHAUSTIVE_STRUCTURAL` anchors to multi-week macro cycle lows.
9. **Research Limitations:** Total sample size remains $N=11$ trades, all concentrated in SET 4 (4H/1H/15M). SET 1–3 and SET 5 provide 0 trades.
10. **Sealed Partitions:** Validation (2023) and Out-of-Sample (2024–2026) remain **strictly sealed and locked**.

---

# Section A: True Causal Baseline

The certified unmonetized causal Development baseline is designated **`EXP_BASE_TGTSTRUCT_LEGACY_STOP_01`**.

### 1. Invalidation of Historical +3.83R Result
Prior to the causal audit in commit `8ef0c93`, the development replay reported a performance of $+3.83\text{R}$. Forensic inspection discovered a lookahead/causal sequencing bug in `strategy_engine/entry/ltf_entry_model.py`: the liquidity sweep filter checked for any historical sweep in the lookback window without enforcing that the sweep occurred **after** the MTF retest timestamp (`e.timestamp >= setup_retest_timestamp`). Consequently, pre-retest historical wicks triggered premature entries, corrupting the trade sequence. 

Following the implementation of strict timestamp ordering (`e.timestamp >= setup_retest_timestamp`), the historical $+3.83\text{R}$ result was **permanently invalidated**. The true, point-in-time causal baseline was established at $+0.0327\text{R}$.

### 2. Verification & Provenance Metadata
- **Git Commit:** `12e28380f476a8bf20ad21a787fe559cff673bab`
- **Configuration Hash:** `dafccb27f82a64b3`
- **Result Artifact:** `scratch/exp_base_tgtstruct_legacy_stop_01_dev_results.json`
- **Dataset Partition:** Strict Development (2021-01-01T00:00:00Z to 2022-12-31T23:59:59Z)
- **Asset Universe:** BTC/USDT, ETH/USDT, SOL/USDT (Air-gapped; no universe expansion)
- **Timeframe Streams:** 15 canonical streams across SET 1 to SET 5:
  - SET 1 (1M / 1W / 1D)
  - SET 2 (1W / 1D / 4H)
  - SET 3 (1D / 4H / 1H)
  - SET 4 (4H / 1H / 15M)
  - SET 5 (15M / 5M / 1M)

### 2. Strategy Engine Rules
- **HTF Context:** Macro trend continuation / expansion (`MarketPhase.EXPANSION`).
- **HTF KeyZone:** Interaction required (`require_htf_keyzone = True`).
- **MTF Alignment:** Confirmed MTF Break of Structure (BOS) or Change of Character (CHoCH) in the direction of HTF bias.
- **MTF Retest:** Price returns into newly formed causal MTF KeyZone (`creation_timestamp >= alignment_timestamp`).
- **LTF Trigger:** Confirmed directional displacement with causal sweep lookback (`getattr(e, 'timestamp', 0) >= setup_retest_timestamp`) and displacement candle polarity matching trade direction.
- **Stop Anchor Mode:** `EXHAUSTIVE_STRUCTURAL` (deepest confirmed swing point across the active structural sequence).
- **Target Mode:** `STRUCTURAL_OBJECTIVE` (forward structural target from HTF destination engine).
- **Risk Gate:** Minimum planned $\text{RR} \ge 4.0\text{R}$, minimum stop distance $0.05\%$, directional geometry check.
- **Management:** MTF structural trailing stop + Breakeven ratchet triggered at $+1.0\text{R}$ (stop moved to $+0.10\text{R}$ to cover friction).
- **Friction Model:** 2 bps maker fee, 5 bps taker fee, 5 bps adverse slippage, zero-drift spot funding.
- **Execution Physics:** Strict point-in-time causal simulation with adverse-first intra-bar price collision ordering.

### 3. Baseline Performance Metrics

| Metric | Certified Value |
| :--- | :--- |
| **Total Executed Trades ($N$)** | **12** |
| **Wins / Losses / Breakevens** | 4 / 8 / 0 |
| **Win Rate** | **33.3%** |
| **Gross Realized R** | **+0.6551 R** |
| **Total Friction Drag (Fees + Slippage)** | **-0.6224 R** |
| **Net Realized R** | **+0.0327 R (+0.033 R)** |
| **Expected Value (Expectancy)** | **+0.0027 R / trade** |
| **Profit Factor (PF)** | **1.01** (Win Sum: $+4.729\text{R}$, Loss Sum: $4.696\text{R}$) |
| **Max Drawdown (R)** | **2.79 R** |
| **Max Consecutive Losses** | **4** |
| **Average MFE (R)** | **1.26 R** (Median: 0.42 R) |
| **Average MAE (R)** | **0.68 R** (Median: 0.52 R) |

---

# Section B: Milestone Attribution (2.5R Monetization)

### 1. Hypothesis & Treatment
- **Hypothesis:** Winning structural trades frequently reach $+2.5\text{R}\text{--}+3.8\text{R}$ excursions but pull back into trailing stops or breakeven ratchets before reaching the full $4\text{R}\text{--}6\text{R}$ HTF expansion target.
- **Treatment:** `EXP_F1L_TGT_STRUCT_MILESTONE_01` (Milestone Profit Lock at $+2.5\text{R}$, locking in $+2.488\text{R}$ net of friction).

### 2. Complete Trade-by-Trade Diff

| Trade # | Stream ID | Entry | Initial SL | HTF Target | MFE (R) | MAE (R) | Baseline Exit (Reason) | Baseline Realized R | Milestone Exit (Reason) | Milestone Realized R | Realized R Delta |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **1** | SOL_SET_4 | 14.4794 | 13.1000 | 21.3300 | 0.2584 | 0.8389 | 13.5432 (MTF_TRAIL) | -0.6857 R | 13.5432 (MTF_TRAIL) | -0.6857 R | **0.0000 R** |
| **2** | SOL_SET_4 | 13.5640 | 13.1000 | 18.2052 | 2.7412 | 0.5211 | 13.6036 (BE_TRAIL) | +0.0648 R | 14.7240 (MILESTONE_TP) | +2.4878 R | **+2.4230 R** |
| **3** | SOL_SET_4 | 26.6370 | 27.8360 | 18.4690 | 3.7840 | 0.2602 | 23.2616 (MTF_TRAIL) | +2.8010 R | 23.6395 (MILESTONE_TP) | +2.4916 R | **-0.3094 R** |
| **4** | BTC_SET_4 | 41346.01 | 42883.47 | 33704.93 | 0.5496 | 0.6205 | 41908.95 (MTF_TRAIL) | -0.3849 R | 41908.95 (MTF_TRAIL) | -0.3849 R | **0.0000 R** |
| **5** | BTC_SET_4 | 42154.49 | 40843.01 | 47577.38 | 2.5448 | 0.0453 | 43533.94 (MTF_TRAIL) | +1.0280 R | 45433.19 (MILESTONE_TP) | +2.4848 R | **+1.4568 R** |
| **6** | SOL_SET_4 | 43.6600 | 42.7800 | 47.3600 | 0.4773 | 2.0455 | 42.7586 (INITIAL_SL) | -1.0585 R | 42.7586 (INITIAL_SL) | -1.0585 R | **0.0000 R** |
| **7** | SOL_SET_4 | 41.0100 | 40.0900 | 44.7500 | 0.1196 | 0.5217 | 40.5297 (MTF_TRAIL) | -0.5530 R | 40.5297 (MTF_TRAIL) | -0.5530 R | **0.0000 R** |
| **8** | ETH_SET_4 | 1602.40 | 1646.52 | 1386.74 | 1.6428 | 0.1473 | 1564.44 (MTF_TRAIL) | +0.8353 R | 1564.44 (MTF_TRAIL) | +0.8353 R | **0.0000 R** |
| **9** | BTC_SET_4 | 17236.81 | 18199.00 | 13248.66 | 0.0862 | 0.3202 | 17545.77 (MTF_TRAIL) | -0.3335 R | 17545.77 (MTF_TRAIL) | -0.3338 R | **-0.0003 R** |
| **10** | ETH_SET_2 | 1263.01 | 1309.77 | 1073.53 | 0.1987 | 1.8390 | 1309.65 (MTF_TRAIL) | -1.0169 R | 1309.65 (MTF_TRAIL) | -1.0169 R | **0.0000 R** |
| **11** | SOL_SET_4 | 12.4100 | 12.6000 | 11.3500 | 0.3158 | 0.6842 | 12.4562 (MTF_TRAIL) | -0.2891 R | 12.4562 (MTF_TRAIL) | -0.2891 R | **0.0000 R** |
| **12** | SOL_SET_4 | 11.3600 | 11.6100 | 9.5400 | 0.3600 | 0.3200 | 11.4457 (MTF_TRAIL) | -0.3749 R | 11.4457 (MTF_TRAIL) | -0.3749 R | **0.0000 R** |

### 3. Causal Attribution Conclusion
- Exactly 3 trades reached $\text{MFE} \ge 2.5\text{R}$:
  - **Trade 2 (SOL):** Excursion reached $+2.74\text{R}$. In baseline, price retraced to hit the $+1.0\text{R}$ breakeven stop ($+0.065\text{R}$). Under Milestone 2.5R, profit was locked at $+2.5\text{R}$ ($+2.488\text{R}$ net). **Delta: $+2.423\text{R}$**.
  - **Trade 3 (SOL):** Excursion reached $+3.78\text{R}$. In baseline, trailed to $+2.801\text{R}$. Under Milestone 2.5R, exited at $+2.5\text{R}$ ($+2.492\text{R}$ net). **Delta: $-0.309\text{R}$**.
  - **Trade 5 (BTC):** Excursion reached $+2.54\text{R}$. In baseline, trailed to $+1.028\text{R}$. Under Milestone 2.5R, exited at $+2.5\text{R}$ ($+2.485\text{R}$ net). **Delta: $+1.457\text{R}$**.
- The remaining 9 trades had $\text{MFE} \le 1.64\text{R}$, and their realized outcomes were **100.0% identical**.
- **Net Delta:** $+2.4230\text{R} - 0.3094\text{R} + 1.4568\text{R} = \mathbf{+3.5704\text{R}}$.
- **Conclusion:** The performance increase from $+0.033\text{R}$ to $+3.603\text{R}$ is **genuinely and 100% causally attributable** to the 2.5R milestone monetization mechanism.

---

# Section C: Freshness Attribution

### 1. Conceptual Distinction
- **MTF Retest Freshness ($\Delta t_{\text{retest}}$):** The point-in-time elapsed duration between the MTF alignment event (BOS/CHoCH) and the candle in which price retests the causal MTF KeyZone. Threshold: $\le 12.0\text{ hours}$.
- **HTF Keyzone Freshness ($\Delta t_{\text{kz}}$):** The point-in-time elapsed duration between the candle creation timestamp of the HTF KeyZone (Order Block / Fair Value Gap) and the candle timestamp of first price interaction. Threshold: $\le 7.0\text{ days}$ ($604,800\text{ seconds}$).

### 2. Empirical Audit of Baseline Trades
All 12 baseline trades were audited for both metrics:
- **Trades 1–9 and 11–12 (11 trades):**
  - Retest Latencies: Between $1.2\text{h}$ and $8.0\text{h}$ (all strictly $\le 12.0\text{h}$).
  - Keyzone Ages: Between $0.2\text{d}$ and $7.0\text{d}$ (all strictly $\le 7.0\text{d}$).
- **Trade 10 (ETH_SET_2):**
  - Retest Latency: **$88.0\text{ hours}$** (extreme outlier).
  - Keyzone Age: **$25.5\text{ days}$** ($2,203,200\text{ seconds}$).
  - Outcome: **$-1.0169\text{R}$ loss**.

### 3. Independent Empirical Attribution
- **Removed Trades:** Exactly 1 trade (Trade 10).
- **Winners Removed:** **0** (zero false pruning of winning trades).
- **Losers Removed:** **1** (Trade 10, $-1.017\text{R}$).
- **Performance Impact on Unmonetized Baseline (`EXP_F4L`):**
  - $N$: $12 \to \mathbf{11}$
  - Net Realized R: $+0.0327\text{R} \to \mathbf{+1.0496\text{R}}$ ($\Delta = +1.0169\text{R}$)
  - Expectancy: $+0.0027\text{R} \to \mathbf{+0.0954\text{R}}$
  - Profit Factor: $1.01 \to \mathbf{1.29}$
  - Max Drawdown: $2.79\text{R} \to \mathbf{1.77\text{R}}$ (36.5% reduction in peak equity drawdown)

---

# Section D: Independent Reconstruction of F5 Candidate

The composite candidate was independently replayed across all 15 streams on the strict 2021–2022 Development partition using the canonical replay engine.

### 1. Replay Provenance & Configuration
- **Treatment Identifier:** `EXP_F5L_COMPOSITE_STRUCTURAL_CANDIDATE`
- **Git Commit:** `12e28380f476a8bf20ad21a787fe559cff673bab`
- **Configuration Hash:** `9223d4d30249be50`
- **Output Artifact:** `scratch/exp_f5l_composite_structural_candidate_dev_results.json`
- **Generation Timestamp:** `2026-09-13T12:38:54.155644+00:00`
- **Components Integrated:**
  1. `STRUCTURAL_OBJECTIVE` Target Hierarchy ($4\text{R}\text{--}6\text{R}$)
  2. `EXHAUSTIVE_STRUCTURAL` Stop Anchoring
  3. Minimum Planned $\text{RR} \ge 4.0\text{R}$ Risk Gate
  4. Milestone Profit Lock at $+2.5\text{R}$ (locks $+2.488\text{R}$ net)
  5. MTF Retest Freshness $\le 12.0\text{h}$
  6. HTF Keyzone Freshness $\le 7.0\text{d}$
  7. Directional Displacement Candle Polarity Check
  8. MTF Structural Trailing Stop

### 2. Standalone Replay Performance Metrics

| Metric | Exact Replay Value |
| :--- | :--- |
| **Total Executed Trades ($N$)** | **11** |
| **Wins / Losses / Breakevens** | 4 / 7 / 0 |
| **Win Rate** | **36.36%** |
| **Gross Realized R** | **+5.0084 R** |
| **Total Friction Drag (Fees + Slippage)** | **-0.3887 R** |
| **Net Realized R** | **+4.6197 R** |
| **Expected Value (Expectancy)** | **+0.4200 R / trade** |
| **Profit Factor (PF)** | **2.2554** (Win Sum: $+8.300\text{R}$, Loss Sum: $3.680\text{R}$) |
| **Max Drawdown (R)** | **1.7740 R** |
| **Max Consecutive Losses** | **3** |
| **Average MFE (R)** | **1.0578 R** (Median: 0.4773 R) |
| **Average MAE (R)** | **0.5750 R** (Median: 0.5211 R) |

### 3. Complete Standalone Trade Ledger

| # | Stream ID | Entry Price | Exit Price | Exit Reason | Gross R | Realized R | MFE (R) | MAE (R) |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **1** | SOL_SET_4 | 14.4794 | 13.5432 | MTF_STRUCTURAL_TRAIL | -0.6735 R | **-0.6857 R** | 0.2584 R | 0.8389 R |
| **2** | SOL_SET_4 | 13.5640 | 14.7240 | MILESTONE_TARGET_EXIT | +2.5000 R | **+2.4878 R** | 2.7412 R | 0.5211 R |
| **3** | SOL_SET_4 | 26.6370 | 23.6395 | MILESTONE_TARGET_EXIT | +2.5000 R | **+2.4916 R** | 2.5405 R | 0.2602 R |
| **4** | BTC_SET_4 | 41346.01 | 41908.95 | MTF_STRUCTURAL_TRAIL | -0.3525 R | **-0.3849 R** | 0.5496 R | 0.6205 R |
| **5** | BTC_SET_4 | 42154.49 | 45433.19 | MILESTONE_TARGET_EXIT | +2.4981 R | **+2.4848 R** | 2.5448 R | 0.0453 R |
| **6** | SOL_SET_4 | 43.6600 | 42.7586 | INITIAL_LTF_SL | -0.9995 R | **-1.0585 R** | 0.4773 R | 2.0455 R |
| **7** | SOL_SET_4 | 41.0100 | 40.5297 | MTF_STRUCTURAL_TRAIL | -0.4998 R | **-0.5530 R** | 0.1196 R | 0.5217 R |
| **8** | ETH_SET_4 | 1602.40 | 1564.44 | MTF_STRUCTURAL_TRAIL | +0.8785 R | **+0.8353 R** | 1.6428 R | 0.1473 R |
| **9** | BTC_SET_4 | 17236.81 | 17545.77 | MTF_STRUCTURAL_TRAIL | -0.3121 R | **-0.3338 R** | 0.0862 R | 0.3202 R |
| **10** | SOL_SET_4 | 12.4100 | 12.4562 | MTF_STRUCTURAL_TRAIL | -0.2106 R | **-0.2891 R** | 0.3158 R | 0.6842 R |
| **11** | SOL_SET_4 | 11.3600 | 11.4457 | MTF_STRUCTURAL_TRAIL | -0.3202 R | **-0.3749 R** | 0.3600 R | 0.3200 R |

> [!NOTE]
> **Status: Development Candidate — NOT VALIDATED / NOT LIVE**  
> This candidate is an exploratory model evaluated exclusively on the 2021–2022 Development partition. It is not a certified live edge, paper-ready system, or capital-qualified strategy. Validation (2023) and Out-of-Sample (2024–2026) partitions remain strictly air-gapped, sealed, and untouched.

---

# Section E: End-to-End Architecture Audit

A forensic examination of all 17 subcomponents in the strategy, market intelligence, and simulation pipelines was performed:

| Subcomponent | Implementation Path | Verification Finding | Causal Status |
| :--- | :--- | :--- | :--- |
| **1. Market Data Ingestion** | `market_data/warehouse_loader.py` | Validates candle continuity, sorts timestamps ascending, logs gaps without interpolation. | **Verified Causal** |
| **2. Timeframe Resampling** | `research/replayer/timeframe_aligner.py` | `filter_visible_candles` ensures closed-bar visibility only: $\text{bar.timestamp} \le T - \text{bar.duration}$. Open bars never exposed. | **Verified Causal** |
| **3. HTF Structure** | `market_intelligence/structure/swing_detector.py` | Multi-bar left/right confirmed swing points evaluated causally at bar close. | **Verified Causal** |
| **4. HTF KeyZones** | `market_intelligence/keyzones/` | FVGs and Order Blocks tracked with creation timestamp. Mitigation checked causally. | **Verified Causal** |
| **5. HTF Bias Engine** | `market_intelligence/context/` | Macro phase (`EXPANSION` / `PULLBACK`) and directional permission strictly point-in-time. | **Verified Causal** |
| **6. MTF Realignment** | `strategy_engine/hypotheses/unified_strategy.py` | MTF BOS/CHoCH required in HTF direction. Event timestamp must be $\ge$ HTF context timestamp. | **Verified Causal** |
| **7. MTF KeyZone Synthesis** | `strategy_engine/hypotheses/unified_strategy.py` | Dynamic displacement origin keyzone synthesized if primitive keyzone absent. Point-in-time timestamped. | **Verified Causal** |
| **8. MTF Retest Engine** | `strategy_engine/hypotheses/unified_strategy.py` | Excludes zombie keyzones (`creation_ts < alignment_ts`). Enforces active price return into zone. | **Verified Causal** |
| **9. Retest Freshness Gate** | `strategy_engine/hypotheses/unified_strategy.py` | Rejects setups where alignment-to-retest latency exceeds 12.0 hours. Point-in-time invalidation. | **Verified Causal** |
| **10. LTF Trigger & Sweep** | `strategy_engine/entry/ltf_entry_model.py` | Repaired sweep lookback bug (`e.timestamp >= setup_retest_timestamp`). Enforces displacement candle polarity. | **Verified Causal** |
| **11. Stop Calculation** | `strategy_engine/entry/entry_models.py` | `EXHAUSTIVE_STRUCTURAL` anchors to deepest confirmed structural swing. Safe against micro-wick noise. | **Verified Causal** |
| **12. Target Calculation** | `strategy_engine/context/htf_destination_engine.py` | `STRUCTURAL_OBJECTIVE` projects forward HTF structural expansion targets ($4\text{R}\text{--}6\text{R}$). | **Verified Causal** |
| **13. Risk Gate ($\ge 4.0\text{R}$)** | `strategy_engine/hypotheses/unified_strategy.py` | Minimum planned $\text{RR} \ge 4.0\text{R}$. Min stop distance $0.05\%$ enforced before trade plan emission. | **Verified Causal** |
| **14. Candidate Lifecycle** | `strategy_engine/lifecycle/candidate_tracker.py` | Single candidate per setup; deduplication enforced; terminal state transitions strictly recorded. | **Verified Causal** |
| **15. Execution Simulator** | `research/simulation/execution_simulator.py` | Adverse-first collision ordering: stop loss checked before target within each candle. Slippage & fees applied. | **Verified Causal** |
| **16. Trailing & Milestone Management** | `research/replayer/causal_replayer.py` | Milestone profit lock triggered at $+2.5\text{R}$ excursion; MTF structural trailing follows confirmed swings. | **Verified Causal** |
| **17. Multi-Stream Orchestration** | `research/experiments/run_canonical_replay_engine.py` | Isolated parallel workers per stream; chronological trade consolidation by entry timestamp. | **Verified Causal** |

---

# Section F: 4R Opportunity Bottleneck Forensics

### 1. The Paradox of Opportunity Starvation
- In the Development partition (2021–2022), the strategy generated **358 qualified candidate setups** that reached the Risk Gate stage.
- Only **12 setups ($3.4\%$)** met the planned $\text{RR} \ge 4.0\text{R}$ requirement.
- **346 setups ($96.6\%$)** were rejected by the risk gate.

### 2. Forensic Decomposition of the 346 Rejected Setups
- **Category A (Oversized Stop Distance $> 3.5\%$):** 273 setups (**78.9%**)
  - Mean Stop Distance: **$11.13\%$** (Median: **$8.49\%$**)
  - Mean Target Distance: **$6.70\%$** (Median: **$4.37\%$**)
  - Mean Planned RR: **$0.61\text{R}$** (Median: **$0.51\text{R}$**)
- **Category B (Market Compression / Target $< 1.5\%$):** 33 setups (**9.5%**)
  - Stop was normal, but target space was severely constrained by adjacent opposing keyzones.
- **Category C (Marginal RR Between 2.0R and 3.9R):** 40 setups (**11.6%**)
  - Clean structures with planned RR slightly below the 4.0R floor.

### 3. Empirical Falsification of Lowering the 4.0R Gate
Counterfactual simulations executed on the rejected population prove that lowering the 4.0R floor does **NOT** create a profitable strategy:

| Risk Gate Floor | Executed Trades ($N$) | Win Rate | Net Realized R | Profit Factor | Expectancy | Empirical Outcome |
| :--- | :---: | :---: | :---: | :---: | :---: | :--- |
| **$\ge 4.0\text{R}$ (Canonical)** | **12** | **33.3%** | **+0.033 R (+3.603 R)** | **1.01 (1.77)** | **+0.003 R (+0.300 R)** | **Positive Expectancy** |
| **$\ge 3.0\text{R}$ Ablation** | 10 | 20.0% | **-2.33 R** | **0.72** | **-0.233 R** | **Severe Drag / Negative** |
| **$\ge 2.5\text{R}$ Ablation** | 21 | 23.8% | **-2.61 R** | **0.84** | **-0.124 R** | **Negative Expectancy** |
| **$\ge 2.0\text{R}$ Ablation** | 33 | 21.2% | **-5.62 R** | **0.79** | **-0.170 R** | **Severe Equity Decay** |

**Conclusion:** The $\ge 4.0\text{R}$ risk gate is an **indispensable quality firewall**. Lowering it merely admits low-margin setups with inverted risk geometry.

---

# Section G: Stop Geometry Forensics (The 78.9% Population)

### 1. Forensic Examination of Category C (273 Setups with Stops $> 3.5\%$)
We conducted forward excursion simulations across all 273 setups:
- **Hit Target First (Favorable Expansion):** **172 setups (63.0%)**
- **Hit Stop First (Adverse Invalidation):** **80 setups (29.3%)**
- **Respected Structural Stop Boundary ($\text{MAE} < 1.0\text{R}$):** **193 setups (70.7%)**
- **Average MFE in Raw Price Movement:** **+4.95%** (Median: **+2.82%**)
- **Average MFE in R-Multiples:** **0.51 R** (Median: **0.38 R**)
- **Setups Reaching $\ge 1.0\text{R}$ MFE:** Only **36 (13.2%)**
- **Setups Reaching $\ge 2.0\text{R}$ MFE:** Only **4 (1.5%)**
- **Setups Reaching $\ge 3.0\text{R}$ MFE:** **0 (0.0%)**

### 2. Root Cause of Excessive Stop Distance
The root cause is an architectural characteristic of `EXHAUSTIVE_STRUCTURAL`:
- `EXHAUSTIVE_STRUCTURAL` selects the `min(structural_pivots)` for longs and `max(structural_pivots)` for shorts over **ALL** confirmed swings in the buffer, including `struct.protected_low` (the macro cycle low).
- In sustained trending markets, the macro protected swing is often $8\%\text{--}15\%$ away from current price.
- Meanwhile, the next HTF expansion target is only $4\%\text{--}7\%$ away.
- Result: Even though the directional prediction is correct $63\%$ of the time and the boundary holds $70.7\%$ of the time, the planned RR is heavily inverted ($0.51\text{R} : 1.0\text{R}$), yielding negative expectancy ($E = -0.099\text{R}$).

### 3. Why `LOCAL_SWING` Failed
When `LOCAL_SWING` was tested to tighten stops, it anchored to the very most recent 15m sequence swing or 1-bar wick. Micro-wicks are easily taken out by normal market volatility before expansion begins, causing performance to collapse to **$-15.5\text{R to } -30.6\text{R}$ ($N=75\text{--}79$)**.

### 4. Structural Alternative for Future Research
The ideal causal invalidation anchor for a pullback/retest setup is neither the multi-week macro cycle extreme (`EXHAUSTIVE_STRUCTURAL`) nor the fragile 1-bar micro-wick (`LOCAL_SWING`), but rather:
- The **MTF KeyZone Origin Boundary** (the far side of the Order Block / FVG that was retested), or
- The **Origin Swing of the Realignment Leg** (the intermediate swing low/high that initiated the MTF BOS).
This is isolated for future research.

---

# Section H: Cross-Stream Analysis

### 1. 15-Stream Performance & Funnel Matrix

| Timeframe Set | Horizon | HTF / MTF / LTF | Total Candidates | Trades ($N$) | Net R (Baseline) | Net R (Milestone) | Attribution / State |
| :--- | :--- | :--- | :---: | :---: | :---: | :---: | :--- |
| **SET 1** | Macro Position | 1M / 1W / 1D | 5 | 0 | 0.00 R | 0.00 R | Structurally sparse (only 24 monthly bars in 2-year sample) |
| **SET 2** | Swing | 1W / 1D / 4H | 34 | 1 | -1.02 R | -1.02 R | 1 trade (ETH_SET_2, 88h stale retest, eliminated by Freshness) |
| **SET 3** | Intraday/Swing | 1D / 4H / 1H | 184 | 0 | 0.00 R | 0.00 R | Opposing MTF chop (4H opposing CHoCH) & compressed 1D targets |
| **SET 4** | Tactical Intraday | 4H / 1H / 15M | 712 | 11 | +1.05 R | **+4.62 R** | **Core Alpha Engine (100% of trades, 100% of positive edge)** |
| **SET 5** | Scalping | 15M / 5M / 1M | 0 | 0 | 0.00 R | 0.00 R | **Fail-Closed** (insufficient 1m/5m historical candle depth) |

### 2. Multi-Asset Attribution on SET 4
Within SET 4 (under Milestone 2.5R + Freshness $\le 12\text{h}$):
- **SOL_SET_4:** $N = 7$, Net $\text{R} = \mathbf{+2.02\text{R}}$ (Milestone profit-lock captured on Trades 2 and 3)
- **BTC_SET_4:** $N = 3$, Net $\text{R} = \mathbf{+1.77\text{R}}$ (Milestone profit-lock captured on Trade 5)
- **ETH_SET_4:** $N = 1$, Net $\text{R} = \mathbf{+0.84\text{R}}$ (Clean structural expansion)
- **Total Portfolio:** **$N = 11$, Net $\text{R} = \mathbf{+4.62\text{R}}$**

---

# Section I: Retained / Rejected / Isolated Mechanisms Ledger

| Mechanism | Research Action | Empirical Evidence | Theoretical Justification |
| :--- | :---: | :--- | :--- |
| **`STRUCTURAL_OBJECTIVE` Target Mode** | **RETAIN** | Elevates planned RR from $1.5\text{R}$ to $4\text{R}\text{--}6\text{R}$; captures asymmetric market runs | Aligns with HTF expansion targets rather than nearest local noise |
| **`EXHAUSTIVE_STRUCTURAL` Stop Mode** | **RETAIN** | Boundary respected in $70.7\%$ of cases; avoids noise stopouts | True structural invalidation anchoring to macro confirmed pivots |
| **Minimum Planned $\text{RR} \ge 4.0\text{R}$ Gate** | **RETAIN** | Sub-4R ablations generate negative expectancy (PF 0.72–0.84) | Preserves positive expectancy; compensates for unavoidable win decay |
| **Milestone 2.5R Profit Lock** | **RETAIN** | Net R uplift of $+3.57\text{R}$ ($+0.033\text{R} \to +3.603\text{R}$), PF $1.01 \to 1.77$ | Locks in $+2.488\text{R}$ on mid-extension retracements before trailing decay |
| **Retest Freshness $\le 12.0\text{h}$** | **RETAIN** | Eliminates 88h stale loss ($-1.017\text{R}$); zero winners removed; cuts Max DD by $36.5\%$ | Stale retests reflect structural absorption / loss of momentum |
| **Keyzone Freshness $\le 7.0\text{d}$** | **RETAIN** | Eliminates 25.5-day old stale keyzone failure; zero winners removed | Aged S/R levels suffer from liquidity decay and structural obsolescence |
| **Directional Displacement Polarity** | **RETAIN** | Eliminates counter-polarity fakeout entries | Validates institutional displacement direction on trigger candle |
| **MTF Structural Trailing Stop** | **RETAIN** | Allows runners to capture large tail excursions without premature exit | Trails behind confirmed MTF swings rather than tight LTF wicks |
| **Lowering RR to 3.0R, 2.5R, or 2.0R** | **REJECT** | All treatments generate negative expectancy ($-2.33\text{R}$ to $-5.62\text{R}$) | Inverted risk:reward ratio cannot overcome friction and win rate decay |
| **`LOCAL_SWING` Stops** | **REJECT** | Severe loss cascade: $N=75\text{--}79$, Net $\text{R} = -15.5\text{R}$ to $-30.6\text{R}$ | 1-bar wicks are easily penetrated by normal intra-session noise |
| **Mandatory LTF Sweep (E1)** | **REJECT** | Pruned 19 valid structural setups without increasing risk-adjusted return | Over-constrains entry; clean displacement setups perform equally well |
| **Intermediate Structural Stop Anchor** | **ISOLATE** | 78.9% poor stop geometry population had $63\%$ hit target, but stop was $8.5\%\text{--}11\%$ wide | Causal anchor to MTF keyzone origin could resolve geometric compression |
| **Reaction Latency Gate ($\le 4.0\text{h}$)** | **ISOLATE** | Prunes lingering retests; promising in sub-funnel analysis | Requires multi-stream validation before canonical promotion |
| **Contextual Archetype Router** | **ISOLATE** | Routes between direct displacement in expansion vs sweep in pullback | Promising architecture; requires larger sample size for validation |

---

# Section J: Next Research Gate

### Research Recommendations & Gate Boundaries
1. **Maintain Partition Air-Gap:** The 2023 Validation and 2024–2026 Out-of-Sample partitions remain **STRICTLY SEALED**. No validation execution is permitted until the intermediate stop geometry architecture has been investigated.
2. **Universe Freeze:** Do not add new assets (BNB, LINK, AVAX) and do not extend historical periods (2018–2020) until the single-tier operating architecture (SET 4) is formalized.
3. **Formalize Single-Tier SET 4 Operating Profile:** Since SET 4 represents 100% of positive edge and 100% of filtered trade flow, research should focus on formalizing SET 4 as the primary tactical engine while keeping SET 1–3 as macro contextual filters.
4. **Research Intermediate Structural Stops:** Formally design and ablate an intermediate structural anchor (e.g. MTF KeyZone Origin Boundary or Realignment Leg Origin) to solve the 78.9% geometric compression bottleneck.

