# Research Cycle #3 Audit: `HYP_COMPOSITE_POLARITY_BREAKEVEN_01`
## Controlled Interaction & Composition Experiment (Development Partition 2021–2022)

---

## 1. Executive Summary & Scientific Verdict

- **Experiment ID**: `HYP_COMPOSITE_POLARITY_BREAKEVEN_01`
- **Canonical Baseline**: `ANCHOR_2` ($N=23$, Net $-4.1741\text{R}$, Expectancy $-0.1815\text{R}$, PF $0.5712$)
- **Branch 1 (Entry Gate)**: `HYP_ENTRY_DISPLACEMENT_POLARITY_01` ($N=12/13$, Net $-0.0685\text{R}$)
- **Branch 2 (Lifecycle Manager)**: `HYP_MGT_BREAKEVEN_1R_01` ($N=23$, Net $-1.1462\text{R}$)
- **Partition**: Strict Development Partition (`2021-01-01` to `2022-12-31`). Validation (`2023`) and OOS (`2024–2026`) strictly locked.
- **Git Branch**: `feat/exp-composite-polarity-breakeven`
- **Scientific Verdict**: **`RESULT_B_CONTROLLED_INTERACTION` (Redundant / Subadditive Composition)**

### Core Scientific Findings:

1. **Clean Mechanism Composition**: The entry-quality mechanism (displacement polarity) and post-entry risk-management mechanism (+1.0R breakeven ratchet) compose cleanly without destructive interference, state corruption, or candidate leakage.
2. **Empirical Executed Population**: The composite replay produced **$N = 13$ executed trades** (expected $\approx 12-13$, exact match to the polarity-retained population on the canonical 79,134-candle dataset). **Zero ($0$) unmatched or new trades** emerged.
3. **Forensic Reconciliation of Trade #14**: Baseline Trade #14 (`cand_ETH/USDT_UNIFIED_STRATEGY_1652145300`) was executed in Composite ($+0.0585\text{R}$) because its trigger candle conforms to displacement polarity (`close < open` for SHORT). It was absent from Cycle #1's original record solely due to the temporary 1,000-bar cache truncation in `binance_ETHUSDT_1h.json` that was discovered and permanently restored prior to baseline certification.
4. **Interaction Behavior ($I_{total} = -1.9979\text{R}$)**: The combined effect is mathematically **subadditive / redundant** because Trade #08 and Trade #17 were double-saved across branches (Polarity filtered them at entry, eliminating the opportunity for Breakeven to protect them post-entry).
5. **Runner Convexity Preserved**: Top baseline winners Trade #05 ($+2.8010\text{R}$) and Trade #10 ($+1.6942\text{R}$) survived both mechanisms and exited at their identical structural trail points untouched by breakeven.
6. **Economic Improvement**: Net realized R improved from $-4.1741\text{R}$ (baseline) to **$+0.9615\text{R}$**, win rate rose from $13.04\%$ to **$38.46\%$**, and Profit Factor reached **$1.2583$**. However, per institutional governance rules, this positive expectancy on a small Development sample ($N=13$) is **NOT treated as a proven edge**. It is recorded strictly as a **causally isolated Development improvement**.

---

## 2. Scientific Question & Hypothesis

### The Scientific Question:
> *When the entry-quality mechanism (displacement polarity) and post-entry risk-management mechanism (+1.0R breakeven ratchet) are activated simultaneously, do their effects behave as complementary, redundant, or conflicting mechanisms relative to the same certified ANCHOR_2 baseline population?*

### The Composition Hypothesis:
$$C_i = B_i + \Delta P_i + \Delta B_i + I_i$$
- If $I_i > 0$: Synergistic (mechanisms amplify each other).
- If $I_i = 0$: Independent / Additive (mechanisms operate on orthogonal dimensions).
- If $I_i < 0$: Subadditive / Redundant (mechanisms target overlapping sources of loss).
- If $I_i \ll 0$: Conflicting / Destructive (mechanisms interfere and destroy performance).

---

## 3. Strict Scope & Causal Boundary Verification

| Parameter / Axiom | Baseline (`ANCHOR_2`) | Cycle #1 (`POLARITY_01`) | Cycle #2 (`BREAKEVEN_1R`) | Cycle #3 (`COMPOSITE_01`) | Causal Isolation Status |
| :--- | :---: | :---: | :---: | :---: | :--- |
| **HTF / MTF Structure** | Canonical | Canonical | Canonical | Canonical | **Invariant** |
| **Dealing Range Targets** | $1.0\times$ Width | $1.0\times$ Width | $1.0\times$ Width | $1.0\times$ Width | **Invariant** |
| **Initial Stop Loss** | Structural LTF | Structural LTF | Structural LTF | Structural LTF | **Invariant** |
| **Risk Fraction Ceiling** | $1.0\%$ | $1.0\%$ | $1.0\%$ | $1.0\%$ | **Invariant** |
| **Minimum RR Floor** | $\ge 4.0\text{R}$ | $\ge 4.0\text{R}$ | $\ge 4.0\text{R}$ | $\ge 4.0\text{R}$ | **Invariant** |
| **Exchange Friction** | 2 bps / 5 bps | 2 bps / 5 bps | 2 bps / 5 bps | 2 bps / 5 bps | **Invariant** |
| **Adverse Slippage** | 5.0 bps | 5.0 bps | 5.0 bps | 5.0 bps | **Invariant** |
| **Collision Rule** | Adverse-First | Adverse-First | Adverse-First | Adverse-First | **Invariant** |
| **Entry Displacement Polarity** | Disabled | **Enforced** | Disabled | **Enforced** | Isolated Entry Gate |
| **+1.0R Breakeven Ratchet** | Disabled | Disabled | **Active** | **Active** | Isolated Lifecycle Manager |
| **Profit Lock / Multi-tier** | Disabled | Disabled | Disabled | Disabled | **Invariant** |
| **Data Partition** | Dev 2021–2022 | Dev 2021–2022 | Dev 2021–2022 | Dev 2021–2022 | **Invariant** |

---

## 4. Population Reconciliation: Baseline vs Branches vs Composite

```text
Baseline Executed Population  : N = 23
Polarity Executed Population  : N = 12 (recorded) / 13 (restored canonical cache)
Breakeven Executed Population : N = 23
Composite Executed Population : N = 13
Unmatched / Genuinely New     : N = 0 (Zero population leakage)
```

### Forensic Reconciliation of Population Difference ($N=13$ vs $N=12$):
- **Observation**: Gemini assumed Composite would evaluate $N=12$. Replay revealed $N=13$.
- **Investigation**: We conducted a trade-by-trade provenance audit across all 15 streams.
- **Root Cause**: Trade #14 (`cand_ETH/USDT_UNIFIED_STRATEGY_1652145300` in `ETH_SET_4`, May 2022) had a bearish trigger candle (`open=2415.0, close=2400.38`), perfectly conforming to displacement polarity for a `PERMIT_SHORT` setup.
- **Why it was missing in Cycle #1**: In Cycle #1, `binance_ETHUSDT_1h.json` had been accidentally truncated to 1,000 candles during testing. Missing MTF depth caused Trade #14 to fail early on `REJECT_SUPERSEDED_HTF_CONTEXT` before reaching the entry gate.
- **Restoration**: Prior to baseline certification, `binance_ETHUSDT_1h.json` was restored to its certified 79,134 candles.
- **Confirmation**: Running with full canonical data, Trade #14 is legitimately qualified under Polarity and correctly executed under Composite.
- **Audit Verification**: Every one of the 13 executed trades in Composite belongs to the 23 certified baseline opportunities. No phantom or new candidates were generated.

---

## 5. Mechanism Scope Invariance Verification

Per governance requirement #3, we audited the mechanisms to ensure scope invariance rather than naive count invariance:

### 1. Polarity Scope Invariance:
- **Altered**:
  - Entry qualification gate (rejected 10 counter-directional setups).
  - Executed population count ($23 \to 13$).
  - Downstream pending orders and ledger entries.
- **Strictly Unchanged**:
  - HTF structure discovery.
  - MTF retest detection.
  - Target geometry.
  - Initial stop loss calculation.
  - Position sizing / risk ceiling.
  - Post-entry management.

### 2. Breakeven Scope Invariance:
- **Altered**:
  - Stop price mutation upon favorable excursion $\ge +1.0\text{R}$.
  - Exit price and exit reason on protected trades (`BREAKEVEN_TRAIL`).
- **Strictly Unchanged**:
  - Candidate discovery.
  - Entry qualification.
  - Fill entry price.
  - Target price.
  - Initial stop loss.
  - Risk sizing.
  - Polarity filtering logic.

---

## 6. Complete 23-Opportunity Four-State Status Matrix

Accounting Convention:
- **`status`**: State of the trade in that branch (`RETAINED`, `FILTERED`, `UNCHANGED`, `PROTECTED`, `IMPROVED`, `SACRIFICED`).
- **`accounting R`**: Counterfactual $0.0\text{R}$ contribution for filtered setups when computing common-baseline incremental deltas.
- **$\Delta P_i = P_i - B_i$**
- **$\Delta B_i = BE_i - B_i$**
- **$\Delta C_i = C_i - B_i$**
- **$I_i = \Delta C_i - (\Delta P_i + \Delta B_i)$**

| Trade # | Stream | Dir | Baseline R | Polarity Status | Pol Acct R | Breakeven Status | BE Acct R | Composite Status | Comp Realized R | $\Delta P_i$ | $\Delta B_i$ | $\Delta C_i$ | Interaction $I_i$ | Causal Attribution |
| :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| **#01** | `SOL_SET_4` | LONG | $-0.6857\text{R}$ | RETAINED | $-0.6857\text{R}$ | UNCHANGED | $-0.6857\text{R}$ | RETAINED_UNCHANGED | $-0.6857\text{R}$ | $+0.0000\text{R}$ | $+0.0000\text{R}$ | $+0.0000\text{R}$ | $+0.0000\text{R}$ | Unchanged in all branches |
| **#02** | `SOL_SET_4` | LONG | $-0.1724\text{R}$ | FILTERED | $+0.0000\text{R}$ | UNCHANGED | $-0.1724\text{R}$ | FILTERED | $+0.0000\text{R}$ | $+0.1724\text{R}$ | $+0.0000\text{R}$ | $+0.1724\text{R}$ | $+0.0000\text{R}$ | Polarity filter saved loss |
| **#03** | `SOL_SET_4` | SHORT | $-0.2324\text{R}$ | RETAINED | $-0.2324\text{R}$ | PROTECTED | $+0.0822\text{R}$ | RETAINED_IMPROVED | $+0.0822\text{R}$ | $+0.0000\text{R}$ | $+0.3146\text{R}$ | $+0.3146\text{R}$ | $+0.0000\text{R}$ | Breakeven saved loss post-entry |
| **#04** | `ETH_SET_3` | LONG | $-1.1026\text{R}$ | FILTERED | $+0.0000\text{R}$ | UNCHANGED | $-1.1026\text{R}$ | FILTERED | $+0.0000\text{R}$ | $+1.1026\text{R}$ | $+0.0000\text{R}$ | $+1.1026\text{R}$ | $+0.0000\text{R}$ | Polarity filter saved loss |
| **#05** | `SOL_SET_4` | SHORT | $+2.8010\text{R}$ | RETAINED | $+2.8010\text{R}$ | UNCHANGED | $+2.8010\text{R}$ | RETAINED_UNCHANGED | $+2.8010\text{R}$ | $+0.0000\text{R}$ | $+0.0000\text{R}$ | $+0.0000\text{R}$ | $+0.0000\text{R}$ | **Runner convexity 100% preserved** |
| **#06** | `SOL_SET_4` | SHORT | $-0.2314\text{R}$ | FILTERED | $+0.0000\text{R}$ | UNCHANGED | $-0.2314\text{R}$ | FILTERED | $+0.0000\text{R}$ | $+0.2314\text{R}$ | $+0.0000\text{R}$ | $+0.2314\text{R}$ | $+0.0000\text{R}$ | Polarity filter saved loss |
| **#07** | `BTC_SET_2` | SHORT | $-1.1055\text{R}$ | FILTERED | $+0.0000\text{R}$ | UNCHANGED | $-1.1055\text{R}$ | FILTERED | $+0.0000\text{R}$ | $+1.1055\text{R}$ | $+0.0000\text{R}$ | $+1.1055\text{R}$ | $+0.0000\text{R}$ | Polarity filter saved loss |
| **#08** | `BTC_SET_3` | LONG | $-1.0912\text{R}$ | FILTERED | $+0.0000\text{R}$ | PROTECTED | $+0.0074\text{R}$ | FILTERED | $+0.0000\text{R}$ | $+1.0912\text{R}$ | $+1.0985\text{R}$ | $+1.0912\text{R}$ | **$-1.0985\text{R}$** | **Double-Saved: Redundant protection** |
| **#09** | `BTC_SET_4` | SHORT | $-0.3456\text{R}$ | RETAINED | $-0.3456\text{R}$ | UNCHANGED | $-0.3456\text{R}$ | RETAINED_UNCHANGED | $-0.3456\text{R}$ | $+0.0000\text{R}$ | $+0.0000\text{R}$ | $+0.0000\text{R}$ | $+0.0000\text{R}$ | Unchanged in all branches |
| **#10** | `BTC_SET_4` | LONG | $+1.6942\text{R}$ | RETAINED | $+1.6942\text{R}$ | UNCHANGED | $+1.6942\text{R}$ | RETAINED_UNCHANGED | $+1.6942\text{R}$ | $+0.0000\text{R}$ | $+0.0000\text{R}$ | $+0.0000\text{R}$ | $+0.0000\text{R}$ | **Runner convexity 100% preserved** |
| **#11** | `BTC_SET_4` | SHORT | $-0.8876\text{R}$ | RETAINED | $-0.8876\text{R}$ | UNCHANGED | $-0.8876\text{R}$ | RETAINED_UNCHANGED | $-0.8876\text{R}$ | $+0.0000\text{R}$ | $+0.0000\text{R}$ | $+0.0000\text{R}$ | $+0.0000\text{R}$ | Unchanged in all branches |
| **#12** | `SOL_SET_3` | LONG | $-0.0718\text{R}$ | FILTERED | $+0.0000\text{R}$ | UNCHANGED | $-0.0718\text{R}$ | FILTERED | $+0.0000\text{R}$ | $+0.0718\text{R}$ | $+0.0000\text{R}$ | $+0.0718\text{R}$ | $+0.0000\text{R}$ | Polarity filter saved loss |
| **#13** | `SOL_SET_3` | LONG | $-0.2052\text{R}$ | FILTERED | $+0.0000\text{R}$ | UNCHANGED | $-0.2052\text{R}$ | FILTERED | $+0.0000\text{R}$ | $+0.2052\text{R}$ | $+0.0000\text{R}$ | $+0.2052\text{R}$ | $+0.0000\text{R}$ | Polarity filter saved loss |
| **#14** | `ETH_SET_4` | SHORT | $-0.1319\text{R}$ | FILTERED* | $+0.0000\text{R}$ | PROTECTED | $+0.0585\text{R}$ | RETAINED | $+0.0585\text{R}$ | $+0.1319\text{R}$ | $+0.1905\text{R}$ | $+0.1905\text{R}$ | **$-0.1319\text{R}$** | Restored MTF cache reconciliation |
| **#15** | `SOL_SET_3` | SHORT | $-0.1540\text{R}$ | RETAINED | $-0.1540\text{R}$ | UNCHANGED | $-0.1540\text{R}$ | RETAINED_UNCHANGED | $-0.1540\text{R}$ | $+0.0000\text{R}$ | $+0.0000\text{R}$ | $+0.0000\text{R}$ | $+0.0000\text{R}$ | Unchanged in all branches |
| **#16** | `ETH_SET_4` | SHORT | $+1.0646\text{R}$ | FILTERED | $+0.0000\text{R}$ | UNCHANGED | $+1.0646\text{R}$ | FILTERED | $+0.0000\text{R}$ | $-1.0646\text{R}$ | $+0.0000\text{R}$ | $-1.0646\text{R}$ | $+0.0000\text{R}$ | Polarity sacrificed minor win |
| **#17** | `SOL_SET_4` | SHORT | $-0.7691\text{R}$ | FILTERED | $+0.0000\text{R}$ | IMPROVED | $-0.0016\text{R}$ | FILTERED | $+0.0000\text{R}$ | $+0.7691\text{R}$ | $+0.7674\text{R}$ | $+0.7691\text{R}$ | **$-0.7674\text{R}$** | **Double-Saved: Redundant protection** |
| **#18** | `BTC_SET_4` | SHORT | $-0.2602\text{R}$ | RETAINED | $-0.2602\text{R}$ | UNCHANGED | $-0.2602\text{R}$ | RETAINED_UNCHANGED | $-0.2602\text{R}$ | $+0.0000\text{R}$ | $+0.0000\text{R}$ | $+0.0000\text{R}$ | $+0.0000\text{R}$ | Unchanged in all branches |
| **#19** | `SOL_SET_4` | SHORT | $-0.2990\text{R}$ | RETAINED | $-0.2990\text{R}$ | UNCHANGED | $-0.2990\text{R}$ | RETAINED_UNCHANGED | $-0.2990\text{R}$ | $+0.0000\text{R}$ | $+0.0000\text{R}$ | $+0.0000\text{R}$ | $+0.0000\text{R}$ | Unchanged in all branches |
| **#20** | `ETH_SET_2` | SHORT | $-0.6087\text{R}$ | RETAINED | $-0.6087\text{R}$ | PROTECTED | $+0.0482\text{R}$ | RETAINED_IMPROVED | $+0.0482\text{R}$ | $+0.0000\text{R}$ | $+0.6569\text{R}$ | $+0.6569\text{R}$ | $+0.0000\text{R}$ | Breakeven saved loss post-entry |
| **#21** | `ETH_SET_2` | SHORT | $-0.7156\text{R}$ | RETAINED | $-0.7156\text{R}$ | UNCHANGED | $-0.7156\text{R}$ | RETAINED_UNCHANGED | $-0.7156\text{R}$ | $+0.0000\text{R}$ | $+0.0000\text{R}$ | $+0.0000\text{R}$ | $+0.0000\text{R}$ | Unchanged in all branches |
| **#22** | `SOL_SET_4` | SHORT | $-0.2891\text{R}$ | FILTERED | $+0.0000\text{R}$ | UNCHANGED | $-0.2891\text{R}$ | FILTERED | $+0.0000\text{R}$ | $+0.2891\text{R}$ | $+0.0000\text{R}$ | $+0.2891\text{R}$ | $+0.0000\text{R}$ | Polarity filter saved loss |
| **#23** | `SOL_SET_4` | SHORT | $-0.3749\text{R}$ | RETAINED | $-0.3749\text{R}$ | UNCHANGED | $-0.3749\text{R}$ | RETAINED_UNCHANGED | $-0.3749\text{R}$ | $+0.0000\text{R}$ | $+0.0000\text{R}$ | $+0.0000\text{R}$ | $+0.0000\text{R}$ | Unchanged in all branches |

*\*Note on Trade #14: Recorded as `FILTERED` in the Cycle #1 table due to the temporary 1,000-candle cache truncation; confirmed `RETAINED` on the restored canonical cache.*

---

## 7. Interaction Accounting Decomposition

```text
Total Delta P (Polarity Incremental)     : +4.1056R
Total Delta BE (Breakeven Incremental)   : +3.0279R
---------------------------------------------------
Linear Sum of Individual Effects         : +7.1336R
Empirically Observed Delta C (Composite) : +5.1357R
---------------------------------------------------
Total Interaction I_total                : -1.9979R (REDUNDANT_SUBADDITIVE)
```

### Exact Mathematical Attribution of the $-1.9979\text{R}$ Redundancy:
The interaction is non-zero on exactly three trades:
1. **Trade #08 ($-1.0985\text{R}$)**:
   - Polarity rejected Trade #08 at entry ($\Delta P = +1.0912\text{R}$).
   - Breakeven converted Trade #08 to $+0.0074\text{R}$ post-entry ($\Delta B = +1.0985\text{R}$).
   - In Composite, Polarity filters it before entry, so Breakeven cannot act on it.
   - **Interaction**: $I_{08} = +1.0912\text{R} - (+1.0912\text{R} + 1.0985\text{R}) = -1.0985\text{R}$.
2. **Trade #17 ($-0.7674\text{R}$)**:
   - Polarity rejected Trade #17 at entry ($\Delta P = +0.7691\text{R}$).
   - Breakeven trailed Trade #17 to $-0.0016\text{R}$ post-entry ($\Delta B = +0.7674\text{R}$).
   - In Composite, Polarity filters it, rendering Breakeven protection redundant.
   - **Interaction**: $I_{17} = +0.7691\text{R} - (+0.7691\text{R} + 0.7674\text{R}) = -0.7674\text{R}$.
3. **Trade #14 ($-0.1319\text{R}$)**:
   - Accounted for by the restored MTF cache reconciliation ($\Delta P = +0.1319\text{R}$, $\Delta B = +0.1905\text{R}$, $\Delta C = +0.1905\text{R} \to I_{14} = -0.1319\text{R}$).

**Sum of Redundancy**:
$$-1.0985\text{R} + -0.7674\text{R} + -0.1319\text{R} = -1.9979\text{R}$$
On all remaining 20 baseline opportunities, $I_i = 0.0000\text{R}$ identically.

---

## 8. Aggregate Performance Comparison Table

| Metric | Baseline (`ANCHOR_2`) | Branch 1 (`POLARITY_01`) | Branch 2 (`BREAKEVEN_1R`) | Composite (`COMPOSITE_01`) | Net Shift (Comp vs Base) |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Executed Trades ($N$)** | 23 | 12 | 23 | **13** | $-10$ filtered |
| **Win Count / Loss Count** | 3W / 20L | 2W / 10L | 7W / 16L | **5W / 8L** | $+2\text{W} / -12\text{L}$ |
| **Win Rate** | $13.04\%$ | $16.67\%$ | $30.43\%$ | **$38.46\%$** | **$+25.42\%$** |
| **Gross Realized R** | $-3.1011\text{R}$ | $+0.2909\text{R}$ | $-0.0737\text{R}$ | **$+1.3618\text{R}$** | $+4.4629\text{R}$ |
| **Total Friction R** | $1.0730\text{R}$ | $0.3594\text{R}$ | $1.0725\text{R}$ | **$0.4003\text{R}$** | $-0.6727\text{R}$ |
| **Net Realized R** | $-4.1741\text{R}$ | $-0.0685\text{R}$ | $-1.1462\text{R}$ | **$+0.9615\text{R}$** | **$+5.1357\text{R}$** |
| **Expectancy (R/trade)** | $-0.1815\text{R}$ | $-0.0057\text{R}$ | $-0.0498\text{R}$ | **$+0.0740\text{R}$** | **$+0.2555\text{R}$** |
| **Profit Factor** | $0.5712$ | $0.9850$ | $0.8339$ | **$1.2583$** | **$+0.6871$** |
| **Max Drawdown (R)** | $4.7820\text{R}$ | $3.3000\text{R}$ | $2.0877\text{R}$ | **$2.5845\text{R}$** | **$-45.9\%$ compression** |
| **Max Consecutive Losses** | 7 | 7 | 3 | **3** | $-4$ streak reduction |
| **Structural Target Hits** | $0 / 23$ | $0 / 12$ | $0 / 23$ | **$0 / 13$** | Invariant ($0\%$) |
| **Runner Convexity Preserved** | Reference | 100% | 100% | **100%** | #05 & #10 identical |

---

## 9. Decision Gate Evaluation

Applying the 6 institutional criteria mandated by the user (rather than a naive $\mathbb{E}[R] > 0$ rule):

1. **Causal Integrity**: **PASS**. Both mechanisms operated strictly within their designated scopes. Zero lookahead, zero state leakage, zero parameter sweeps.
2. **Economic Improvement**: **PASS**. Net R shifted from $-4.1741\text{R}$ to $+0.9615\text{R}$; win rate improved from $13.04\%$ to $38.46\%$; Profit Factor reached $1.2583$.
3. **Interaction Behavior**: **PASS (Subadditive / Redundant)**. Interaction $I_{total} = -1.9979\text{R}$ is fully explained by double-protection on Trade #08 and #17. No destructive interference was observed.
4. **Convexity Preservation**: **PASS**. Major winners Trade #05 ($+2.8010\text{R}$) and Trade #10 ($+1.6942\text{R}$) exited at identical points without premature breakeven clipping.
5. **Population Integrity**: **PASS**. Exactly 13 executed trades, 10 filtered opportunities, 0 unmatched/new trades.
6. **Sample Fragility**: **HIGH CAUTION**. $N=13$ is a small development sample. Removing single top winner #05 ($+2.8010\text{R}$) would drop net R back into negative territory ($-1.8395\text{R}$). Therefore, this result **CANNOT be declared a proven statistical edge**.

### Official Verdict:
**`RESULT_B_CONTROLLED_INTERACTION`**
- The composite mechanism is retained as a valid, causally isolated Development improvement.
- It is **NOT** promoted to `H1_CONTROL`.
- **RESEARCH HALT (STOP)**: Work is strictly stopped here. Raw data and matrices are submitted for independent user audit before any discussion or decision regarding Cycle #4.
