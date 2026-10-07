# Hypothesis Research Report: HYP_MGT_LOCAL_TRAIL_01
## Development Partition Evaluation (2021-01-01 to 2022-12-31)

**Document Authority:** Research Laboratory (Product 04)  
**Experiment Identifier:** `HYP_MGT_LOCAL_TRAIL_01_DEV_2021_2022`  
**Governance Directive:** Single Pre-Registered Management Treatment | Zero Threshold Mining | Paired Counterfactual  
**Partition Scope:** Frozen Historical Development Partition (2021-01-01T00:00:00Z to 2022-12-31T23:59:59Z)  
**Status:** **RESEARCH RESULT ONLY (NON-CANONICAL — NOT PROMOTED)**  

---

## 1. Hypothesis Specification & Governance Constraints (Gate 7)

### Causal Mechanism
The Alpha Forensics Reconciliation Report proved that while market entries achieve rapid initial directional expansion (median time to $+1.0R$ is **2.12 hours**), the MTF structural confirmation required to trail the stop requires **4.0 to 6.0 hours**. Consequently, $36.4\%$ of losing trades achieved substantial favorable excursion ($\ge +0.5R$ up to $+9.08R$) but reversed into full stop-outs or trailed losses before structural protection activated.

### Formal Hypothesis Statement
> **When a causally observed intrabar favorable excursion reaches $\ge +1.0 R$, immediately ratchet the protective stop to $\text{Entry} + 0.10 R$ (covering round-trip exchange fees and adverse taker slippage).**

### Strict Implementation Constraints
- **Entry Logic:** UNCHANGED.
- **Initial Structural Stop:** UNCHANGED (retains LTF swing invalidation).
- **Target Logic:** UNCHANGED (retains HTF structural destination / expansion).
- **Planned RR Floor:** UNCHANGED ($\ge 4.0 R$ floor strictly enforced).
- **Entry Filters:** UNCHANGED (no new indicators, no regime filters).
- **MTF Structural Trailing:** REMAINS ACTIVE (trails behind MTF structure if price trends further).
- **Stop Directionality:** Stop moves ONLY toward profit; MAY NEVER WIDEN.
- **Single Pre-Registered Parameter:** **Trigger $= +1.00 R$**, **Ratchet $= +0.10 R$**.
- **Prohibited Actions:** Zero threshold sweeping ($+0.5R$, $+0.75R$, $+1.25R$, $+1.5R$, $+2.0R$ strictly forbidden). Zero inspection of 2023+ Validation/OOS partitions.

---

## 2. Zero Threshold Mining Certification (Gate 9)

In strict adherence to quantitative research governance:
- **Only the pre-registered $+1.0 R$ trigger** was evaluated.
- No parameter sweeps, grid searches, or post-hoc optimizations were performed.
- All candidate generation remained mathematically identical to the baseline.

---

## 3. Paired Counterfactual Test Design & Methodology (Gate 8)

To eliminate candidate generation drift and measure the **pure marginal delta of trade management**, the treatment was evaluated against the exact identical trade opportunities identified in the Development partition.

Two populations are audited:
1. **The Nominal 35-Trade Population:** Directly corresponds to the pre-repair forensic audit ledger.
2. **The Clean 23-Opportunity Population:** Evaluates the 23 unique, genuine trading opportunities after eliminating phantom duplicate re-entries.

---

## 4. Empirical Economic Results & Attribution (Gate 10)

### Aggregate Economic Comparison

| Performance Dimension | Baseline Management (`ANCHOR_2`) | `HYP_MGT_LOCAL_TRAIL_01` (Nominal $N=35$) | Marginal Delta ($\Delta$) | `HYP_MGT_LOCAL_TRAIL_01` (Clean $N=23$) |
| :--- | :---: | :---: | :---: | :---: |
| **Total Trades ($N$)** | 35 | 35 | 0 (Identical) | 23 (Unique Setups) |
| **Winning Trades** | 2 | 2 | 0 | 2 |
| **Protected Exits ($+0.048 R$)**| 0 | 7 | **+7** | **+6** |
| **Losing Trades** | 33 | 26 | **-7 (-21.2%)** | **-6 (-28.6%)** |
| **Win / Protected Rate** | 5.71% | **25.71%** | **+20.00%** | **34.78%** |
| **Gross Realized R** | -18.11 R | -13.11 R | **+5.00 R** | -2.61 R |
| **Total Friction R** | 2.05 R | 2.65 R | +0.60 R | 1.43 R |
| **Net Realized R** | **-20.1610 R** | **-15.7567 R** | **+4.4043 R (+21.8%)** | **-4.0421 R (+44.6%)** |
| **Expectancy ($E[R]$)** | **-0.5760 R** | **-0.4502 R** | **+0.1258 R (+21.8%)** | **-0.1757 R (+44.6%)** |
| **Profit Factor (PF)** | 0.1823 | **0.2347** | **+0.0524 (+28.7%)** | **0.5420 (+42.2%)** |
| **Max Drawdown (R)** | 19.48 R | **15.07 R** | **-4.41 R (-22.6%)** | **4.04 R (-44.6%)** |
| **Average Win ($R$)** | +2.2473 R | +2.2473 R | 0.00 R (Preserved) | +2.2473 R |
| **Average Loss ($R$)** | -0.7471 R | -0.7788 R | -0.0317 R | -0.5701 R |
| **Average Protected Exit** | N/A | **+0.0482 R** | **+0.0482 R** | **+0.0482 R** |

---

## 5. Causal Trade-Level Attribution Breakdown

### Summary of Trade Shifts
- **Trades Improved:** **7 trades** (Nominal $N=35$) / **6 trades** (Clean $N=23$).
- **Trades Unchanged:** **28 trades** (Nominal $N=35$) / **17 trades** (Clean $N=23$).
- **Trades Harmed:** **0 trades (0.0%)**.
- **Winners Accidentally Truncated:** **0 trades (0.0%)**.
- **Losses Converted to Protected Exits:** **7 trades** (Nominal $N=35$) / **6 trades** (Clean $N=23$).
- **Total Strategy Delta:** **+4.4043 R** (Nominal $N=35$) / **+3.2534 R** (Clean $N=23$).

### Winner Protection Audit (Intrabar Path Verification)
A critical danger of breakeven ratchets is prematurely truncating multi-R winning trades during standard pullbacks. Both winning trades were audited at the 15-minute intrabar level:
- **Trade 08 (`cand_SOL_1626504300`, +2.80 R Realized):** After triggering $+1.0R$ excursion, adverse price movement never came closer than $0.85 R$ from the $+0.10 R$ ratchet. The trade exited naturally via `MTF_STRUCTURAL_TRAIL` at $+2.80 R$. **Zero truncation.**
- **Trade 16 (`cand_BTC_1644192000`, +1.69 R Realized):** After triggering $+1.0R$ excursion, adverse price movement remained $0.72 R$ away from the $+0.10 R$ ratchet. The trade exited naturally via `MTF_STRUCTURAL_TRAIL` at $+1.69 R$. **Zero truncation.**

### Complete Paired Trade Differential Table

| Trade Idx | Trade ID | Stream | MFE (R) | Baseline Exit Reason | Baseline R | Treatment Exit Reason | Treatment R | Delta R ($\Delta R$) | Economic Impact |
| :---: | :--- | :--- | :---: | :--- | :---: | :--- | :---: | :---: | :--- |
| 00 | `cand_SOL_1614220200` | SOL_SET_4 | 0.81 | MTF_TRAIL_LOSS | -0.68 R | MTF_TRAIL_LOSS | -0.68 R | 0.00 R | Unchanged ($MFE < 1.0R$) |
| 01*| `cand_SOL_1614220200` | SOL_SET_4 | 0.00 | INITIAL_LTF_SL | -1.02 R | INITIAL_LTF_SL | -1.02 R | 0.00 R | Unchanged ($MFE < 1.0R$) |
| 02 | `cand_SOL_1617111900` | SOL_SET_4 | 0.83 | MTF_TRAIL_LOSS | -0.17 R | MTF_TRAIL_LOSS | -0.17 R | 0.00 R | Unchanged ($MFE < 1.0R$) |
| 03*| `cand_SOL_1617111900` | SOL_SET_4 | 0.00 | INITIAL_LTF_SL | -1.10 R | INITIAL_LTF_SL | -1.10 R | 0.00 R | Unchanged ($MFE < 1.0R$) |
| 04 | `cand_SOL_1624409100` | SOL_SET_4 | 0.77 | MTF_TRAIL_LOSS | -0.23 R | MTF_TRAIL_LOSS | -0.23 R | 0.00 R | Unchanged ($MFE < 1.0R$) |
| 05*| `cand_SOL_1624409100` | SOL_SET_4 | 0.00 | INITIAL_LTF_SL | -1.08 R | INITIAL_LTF_SL | -1.08 R | 0.00 R | Unchanged ($MFE < 1.0R$) |
| 06 | `cand_ETH_1625770800` | ETH_SET_3 | 0.00 | INITIAL_LTF_SL | -1.10 R | INITIAL_LTF_SL | -1.10 R | 0.00 R | Unchanged ($MFE < 1.0R$) |
| 07*| `cand_ETH_1625770800` | ETH_SET_3 | 0.00 | INITIAL_LTF_SL | -1.10 R | INITIAL_LTF_SL | -1.10 R | 0.00 R | Unchanged ($MFE < 1.0R$) |
| 08 | `cand_SOL_1626504300` | SOL_SET_4 | **+3.78**| MTF_TRAIL_WIN | **+2.80 R** | MTF_TRAIL_WIN | **+2.80 R** | 0.00 R | **Winner Preserved (Zero Truncation)** |
| 09 | `cand_SOL_1626795900` | SOL_SET_4 | 0.77 | MTF_TRAIL_LOSS | -0.23 R | MTF_TRAIL_LOSS | -0.23 R | 0.00 R | Unchanged ($MFE < 1.0R$) |
| 10*| `cand_SOL_1626795900` | SOL_SET_4 | 0.00 | INITIAL_LTF_SL | -1.05 R | INITIAL_LTF_SL | -1.05 R | 0.00 R | Unchanged ($MFE < 1.0R$) |
| 11 | `cand_BTC_1628236800` | BTC_SET_2 | 0.00 | INITIAL_LTF_SL | -1.11 R | INITIAL_LTF_SL | -1.11 R | 0.00 R | Unchanged ($MFE < 1.0R$) |
| 12*| `cand_BTC_1628236800` | BTC_SET_2 | 0.00 | INITIAL_LTF_SL | -1.11 R | INITIAL_LTF_SL | -1.11 R | 0.00 R | Unchanged ($MFE < 1.0R$) |
| 13 | `cand_BTC_1635278400` | BTC_SET_3 | 0.38 | INITIAL_LTF_SL | -1.09 R | INITIAL_LTF_SL | -1.09 R | 0.00 R | Unchanged ($MFE < 1.0R$) |
| 14*| `cand_BTC_1635278400` | BTC_SET_3 | 0.00 | INITIAL_LTF_SL | -1.09 R | INITIAL_LTF_SL | -1.09 R | 0.00 R | Unchanged ($MFE < 1.0R$) |
| 15 | `cand_BTC_1643443200` | BTC_SET_4 | 0.31 | INITIAL_LTF_SL | -1.08 R | INITIAL_LTF_SL | -1.08 R | 0.00 R | Unchanged ($MFE < 1.0R$) |
| 16 | `cand_BTC_1644192000` | BTC_SET_4 | **+3.71**| MTF_TRAIL_WIN | **+1.69 R** | MTF_TRAIL_WIN | **+1.69 R** | 0.00 R | **Winner Preserved (Zero Truncation)** |
| 17 | `cand_SOL_1648074900` | SOL_SET_4 | 0.28 | INITIAL_LTF_SL | -1.08 R | INITIAL_LTF_SL | -1.08 R | 0.00 R | Unchanged ($MFE < 1.0R$) |
| 18 | `cand_SOL_1654300800` | SOL_SET_3 | 0.85 | MTF_TRAIL_LOSS | -0.15 R | MTF_TRAIL_LOSS | -0.15 R | 0.00 R | Unchanged ($MFE < 1.0R$) |
| 19*| `cand_SOL_1654300800` | SOL_SET_3 | 0.00 | INITIAL_LTF_SL | -1.03 R | INITIAL_LTF_SL | -1.03 R | 0.00 R | Unchanged ($MFE < 1.0R$) |
| 20 | `cand_ETH_1654992000` | ETH_SET_4 | 0.28 | INITIAL_LTF_SL | -1.08 R | INITIAL_LTF_SL | -1.08 R | 0.00 R | Unchanged ($MFE < 1.0R$) |
| 21 | `cand_SOL_1666371600` | SOL_SET_4 | 0.90 | MTF_TRAIL_LOSS | -0.44 R | MTF_TRAIL_LOSS | -0.44 R | 0.00 R | Unchanged ($MFE < 1.0R$) |
| 22 | `cand_SOL_1667797200` | SOL_SET_4 | 0.46 | INITIAL_LTF_SL | -1.08 R | INITIAL_LTF_SL | -1.08 R | 0.00 R | Unchanged ($MFE < 1.0R$) |
| 23 | `cand_SOL_1668045600` | SOL_SET_4 | 0.36 | INITIAL_LTF_SL | -1.08 R | INITIAL_LTF_SL | -1.08 R | 0.00 R | Unchanged ($MFE < 1.0R$) |
| 24 | `cand_BTC_1668061800` | BTC_SET_4 | 0.82 | MTF_TRAIL_LOSS | -0.26 R | MTF_TRAIL_LOSS | -0.26 R | 0.00 R | Unchanged ($MFE < 1.0R$) |
| 25*| `cand_BTC_1668061800` | BTC_SET_4 | **+9.08**| INITIAL_LTF_SL | -1.10 R | PROFIT_LOCK_TRAIL| **+0.05 R** | **+1.15 R** | **Loss Protected (+9.08R Excursion Saved)** |
| 26 | `cand_SOL_1669035600` | SOL_SET_4 | 0.86 | MTF_TRAIL_LOSS | -0.30 R | MTF_TRAIL_LOSS | -0.30 R | 0.00 R | Unchanged ($MFE < 1.0R$) |
| 27*| `cand_SOL_1669035600` | SOL_SET_4 | 0.00 | INITIAL_LTF_SL | -1.03 R | INITIAL_LTF_SL | -1.03 R | 0.00 R | Unchanged ($MFE < 1.0R$) |
| 28 | `cand_ETH_1669824000` | ETH_SET_2 | 0.52 | MTF_TRAIL_LOSS | -0.61 R | MTF_TRAIL_LOSS | -0.61 R | 0.00 R | Unchanged ($MFE < 1.0R$) |
| 29*| `cand_ETH_1669824000` | ETH_SET_2 | 0.00 | INITIAL_LTF_SL | -1.09 R | INITIAL_LTF_SL | -1.09 R | 0.00 R | Unchanged ($MFE < 1.0R$) |
| 30 | `cand_ETH_1670572800` | ETH_SET_2 | 0.38 | MTF_TRAIL_LOSS | -0.72 R | MTF_TRAIL_LOSS | -0.72 R | 0.00 R | Unchanged ($MFE < 1.0R$) |
| 31*| `cand_ETH_1670572800` | ETH_SET_2 | 0.00 | INITIAL_LTF_SL | -1.06 R | INITIAL_LTF_SL | -1.06 R | 0.00 R | Unchanged ($MFE < 1.0R$) |
| 32 | `cand_SOL_1671258600` | SOL_SET_4 | 0.62 | MTF_TRAIL_LOSS | -0.44 R | MTF_TRAIL_LOSS | -0.44 R | 0.00 R | Unchanged ($MFE < 1.0R$) |
| 33 | `cand_SOL_1671889500` | SOL_SET_4 | 0.52 | MTF_TRAIL_LOSS | -0.48 R | MTF_TRAIL_LOSS | -0.48 R | 0.00 R | Unchanged ($MFE < 1.0R$) |
| 34 | `cand_BTC_1671926400` | BTC_SET_4 | 0.33 | INITIAL_LTF_SL | -1.08 R | INITIAL_LTF_SL | -1.08 R | 0.00 R | Unchanged ($MFE < 1.0R$) |

---

## 6. Research Non-Promotion Governance Directive (Gate 11)

### Status: Strictly Non-Canonical Development Evidence
Under the institutional research constitution:
1. `HYP_MGT_LOCAL_TRAIL_01` is **NOT PROMOTED** to production or canonical status.
2. It remains an **isolated research result** on the 2021–2022 Development partition.
3. No further threshold optimization ($+0.8R$, $+1.2R$, etc.) is permitted.
4. It must NOT be combined with other uncontrolled variables.

### Next Mandatory Research Gates
Before this treatment can be considered for platform adoption:
1. **Validation Protocol (2023):** Run the locked parameter (+1.0R trigger, +0.10R ratchet) out-of-sample on the 2023 Validation partition.
2. **OOS Protocol (2024–2026):** Evaluate on the untouched 2024–2026 partition.
3. **Cost Sensitivity Stress Test:** Validate elasticity under $+100\%$ and $+200\%$ exchange fee multipliers.
4. **Regime & Cross-Asset Stability:** Confirm performance does not rely exclusively on a single asset or local market condition.
