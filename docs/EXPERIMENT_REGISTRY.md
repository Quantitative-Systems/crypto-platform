# Institutional Research Experiment Registry

Permanent institutional audit ledger tracking all research cycles against certified baselines.
Enforces the mandatory research governance rule: **no unrecorded experiments, no loose parameter tweaks, no unverified memory claims.**

---

## Registry Index

| Experiment ID | Branch | Partition | Sample ($N$) | Net R | Expectancy | PF | Result / Gate | Next Action |
| :--- | :--- | :--- | :---: | :---: | :---: | :---: | :---: | :--- |
| `ANCHOR_2` | `feat/exp-anchor2-expansion` | Dev 2021–2022 | 23 | $-4.1741\text{R}$ | $-0.1815\text{R}$ | 0.5712 | `BASELINE_CERTIFIED` | Branching to Cycle #1 & Cycle #2 |
| `HYP_ENTRY_DISPLACEMENT_POLARITY_01` | `feat/exp-anchor2-expansion` | Dev 2021–2022 | 12 | $-0.0685\text{R}$ | $-0.0057\text{R}$ | 0.9850 | `RESULT_B_IMPROVEMENT` | Retained, not promoted to control |
| `HYP_COMPOSITE_POLARITY_BREAKEVEN_01` | `feat/exp-composite-polarity-breakeven` | Dev 2021–2022 | 13 | $+0.9615\text{R}$ | $+0.0740\text{R}$ | 1.2583 | `RESULT_B_CONTROLLED_INTERACTION` | Present raw results for independent audit; STOP |

---

## 1. Canonical Baseline: `ANCHOR_2`

- **EXPERIMENT_ID**: `CANONICAL_ANCHOR_2_DEV_2021_2022`
- **PARENT_BASELINE**: None (Origin Certified Baseline)
- **HYPOTHESIS**: HTF/MTF structural orderflow with structural forward expansion fallback ($1.0\times$ dealing range width)
- **MECHANISM**: Fallback targeting when dealing range target price is obstructed or undefined
- **BRANCH**: `feat/exp-anchor2-expansion`
- **COMMIT**: `ada37f7`
- **DATASET**: 15 streams (BTC, ETH, SOL across SET_1 to SET_5), Binance public historical depth
- **PARTITION**: Strict Development Partition (`2021-01-01` to `2022-12-31`). Validation (`2023`) and OOS (`2024–2026`) locked.
- **FROZEN_VARIABLES**: Risk ceiling 1%, initial stop loss, adverse-first collision resolution, maker 2 bps, taker 5 bps, slippage 5 bps
- **CHANGED_VARIABLES**: Forward expansion fallback enabled
- **WATERFALL**:
  - Total Candidates: 1,489
  - HTF Approved: 1,489
  - MTF Retested: 412
  - LTF Confirmed: 35
  - Target Resolved: 35
  - Risk Approved: 23
  - Executed Trades: 23
  - Closed Trades: 23
- **TRADE_ATTRIBUTION**: Baseline reference (3 Wins / 20 Losses)
- **INTERACTION**: N/A (Root Baseline)
- **CONVEXITY**:
  - Trade #05: $+1.8596\text{R}$
  - Trade #10: $+1.8315\text{R}$
  - Target hits: 0/23
- **RESULT**: Net $-4.1741\text{R}$, Expectancy $-0.1815\text{R}$, PF $0.5712$, Max DD $4.7820\text{R}$
- **DECISION_GATE**: `BASELINE_CERTIFIED`
- **NEXT_ALLOWED_ACTION**: Isolated single-variable research branches

---

## 2. Research Cycle #1: `HYP_ENTRY_DISPLACEMENT_POLARITY_01`

- **EXPERIMENT_ID**: `CANONICAL_POLARITY_01_DEV_2021_2022`
- **PARENT_BASELINE**: `ANCHOR_2`
- **HYPOTHESIS**: Requiring LTF trigger candle close to align with trade direction filters low-conviction counter-trend entries without impairing genuine displacement
- **MECHANISM**: Entry displacement polarity validation (`close > open` for LONG, `close < open` for SHORT)
- **BRANCH**: `feat/exp-anchor2-expansion`
- **COMMIT**: `4c613fa`
- **DATASET**: Same 15 streams, certified Binance cache
- **PARTITION**: Development Partition (`2021-01-01` to `2022-12-31`)
- **FROZEN_VARIABLES**: Dealing range target geometry, initial stop loss, risk sizing (1%), fees (2/5 bps), slippage (5 bps), adverse-first collision
- **CHANGED_VARIABLES**: `enforce_displacement_polarity = True`
- **WATERFALL**:
  - Total Candidates: 1,489
  - HTF Approved: 1,489
  - MTF Retested: 412
  - LTF Confirmed: 35
  - Displacement Polarity Passed: 17 (18 rejected at entry qualification)
  - Risk Approved: 12 (11 filtered vs baseline)
  - Executed Trades: 12
  - Closed Trades: 12
- **TRADE_ATTRIBUTION**:
  - 10 baseline losses filtered ($+5.17\text{R}$ saved)
  - 1 baseline win filtered ($-1.06\text{R}$ sacrificed: Trade #17)
  - Efficiency Ratio: $4.86\text{x}$ ($+5.17\text{R} / 1.06\text{R}$)
- **INTERACTION**: Single-branch evaluation
- **CONVEXITY**: Top winners #05 ($+1.8596\text{R}$) and #10 ($+1.8315\text{R}$) 100% preserved
- **RESULT**: Net $-0.0685\text{R}$ (vs $-4.1741\text{R}$), Expectancy $-0.0057\text{R}$, PF $0.9850$, Max DD $3.30\text{R}$
- **DECISION_GATE**: `RESULT_B_IMPROVEMENT_BUT_INSUFFICIENT`
- **NEXT_ALLOWED_ACTION**: Retain for composite interaction research; do NOT promote to `H1_CONTROL`

---

## 3. Research Cycle #2: `HYP_MGT_BREAKEVEN_1R_01`

- **EXPERIMENT_ID**: `CANONICAL_BREAKEVEN_1R_DEV_2021_2022`
- **PARENT_BASELINE**: `ANCHOR_2`
- **HYPOTHESIS**: Causally moving stop loss to $+0.10\text{R}$ upon reaching $+1.0\text{R}$ favorable excursion prevents complete capital giveback on trades showing structural promise
- **MECHANISM**: Single-variable $+1.0\text{R} \to +0.10\text{R}$ monotonic breakeven ratchet
- **BRANCH**: `feat/exp-breakeven-1r`
- **COMMIT**: `07752e5`
- **DATASET**: Same 15 streams, certified Binance cache
- **PARTITION**: Development Partition (`2021-01-01` to `2022-12-31`)
- **FROZEN_VARIABLES**: Entry criteria, candidate discovery, dealing range target geometry, initial stop loss, risk sizing (1%), fees, slippage, adverse-first collision
- **CHANGED_VARIABLES**: `enable_breakeven_1r = True`, `breakeven_trigger_r = 1.0`, `breakeven_stop_r = 0.10`
- **WATERFALL**:
  - Exact $23 / 23$ candidate and execution lifecycle match to baseline
  - Executed Trades: 23
  - Closed Trades: 23
- **TRADE_ATTRIBUTION**:
  - 5 baseline full-R losses converted to breakeven ($+3.0279\text{R}$ saved)
  - 0 baseline wins sacrificed ($0.0000\text{R}$ lost)
  - Efficiency Ratio: $\infty$ (Zero winner sacrifice)
- **INTERACTION**: Single-branch evaluation
- **CONVEXITY**: Top winners #05 ($+1.8596\text{R}$) and #10 ($+1.8315\text{R}$) exit at identical structural trail points untouched by breakeven stop
- **RESULT**: Net $-1.1462\text{R}$ (vs $-4.1741\text{R}$), Expectancy $-0.0498\text{R}$, PF $0.8339$, Max DD $2.0877\text{R}$ (cut by $56.3\%$)
- **DECISION_GATE**: `RESULT_B_IMPROVEMENT_BUT_INSUFFICIENT`
- **NEXT_ALLOWED_ACTION**: Retain for composite interaction research; do NOT promote to `H1_CONTROL`

---

## 4. Research Cycle #3: `HYP_COMPOSITE_POLARITY_BREAKEVEN_01`

- **EXPERIMENT_ID**: `CANONICAL_COMPOSITE_01_DEV_2021_2022`
- **PARENT_BASELINE**: `ANCHOR_2` (Controlled interaction between Cycle #1 and Cycle #2)
- **HYPOTHESIS**: Simultaneous application of entry displacement polarity filter and +1.0R breakeven ratchet operates without destructive interference, combining pre-entry loss avoidance with post-entry excursion protection.
- **MECHANISM**: Dual-mechanism composition:
  1. Entry Gate: `enforce_displacement_polarity = True` (rejects counter-directional LTF trigger candles)
  2. Lifecycle Manager: `enable_breakeven_1r = True`, `trigger_r = 1.0`, `stop_r = 0.10`
- **BRANCH**: `feat/exp-composite-polarity-breakeven`
- **COMMIT**: Pending commit on `feat/exp-composite-polarity-breakeven`
- **DATASET**: Canonical 15 streams, certified Binance cache (restored 79,134-candle dataset)
- **PARTITION**: Strict Development Partition (`2021-01-01` to `2022-12-31`). Validation (`2023`) and OOS (`2024–2026`) locked.
- **FROZEN_VARIABLES**: Dealing range target geometry, initial stop loss, risk sizing (1%), fees (2 bps maker / 5 bps taker), slippage (5 bps), adverse-first collision resolution.
- **CHANGED_VARIABLES**: Both `enforce_displacement_polarity = True` and `enable_breakeven_1r = True`.
- **WATERFALL**:
  - Total Candidates: 1,489
  - HTF Context Approved: 1,489
  - MTF Retested: 412
  - LTF Confirmed: 35
  - Risk Approved: 13
  - Executed Trades: 13 (0 new/unmatched trades vs 23 baseline opportunities)
  - Closed Trades: 13
- **TRADE_ATTRIBUTION**:
  - Population: $N=13$ executed trades (5W / 8L)
  - Filtered Opportunities: 10 baseline opportunities filtered by Polarity (counterfactual accounting contribution $0.0\text{R}$)
  - Protected Trades: 3 trades converted from losses to small wins by Breakeven ratchet (#03, #14, #20)
  - Unchanged Trades: 10 trades (#01, #05, #09, #10, #11, #15, #18, #19, #21, #23)
- **INTERACTION**:
  - Total $\Delta P$: $+4.1056\text{R}$
  - Total $\Delta BE$: $+3.0279\text{R}$
  - Linear Sum: $+7.1336\text{R}$
  - Total $\Delta C$: $+5.1357\text{R}$
  - Interaction $I_{total}$: $-1.9979\text{R}$ (`REDUNDANT_SUBADDITIVE`)
  - Redundancy Attribution: Trade #08 ($-1.0985\text{R}$), Trade #17 ($-0.7674\text{R}$), Trade #14 ($-0.1319\text{R}$) were double-saved across branches.
- **CONVEXITY**:
  - Trade #05: $+2.8010\text{R}$ (100% identical to baseline, zero runner clipping)
  - Trade #10: $+1.6942\text{R}$ (100% identical to baseline, zero runner clipping)
- **RESULT**: Net $+0.9615\text{R}$ (vs $-4.1741\text{R}$ baseline), Expectancy $+0.0740\text{R}$, PF $1.2583$, Win Rate $38.46\%$, Max DD $2.5845\text{R}$, Max Consecutive Losses 3.
- **DECISION_GATE**: `RESULT_B_CONTROLLED_INTERACTION`
- **NEXT_ALLOWED_ACTION**: Submit raw results and 23-opportunity matrix for independent user audit. STOP. No target modifications, no parameter tuning, no unfreezing of Validation or OOS.

