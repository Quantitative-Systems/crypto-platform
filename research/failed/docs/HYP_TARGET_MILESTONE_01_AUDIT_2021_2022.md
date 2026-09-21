# Research Audit: Cycle #4 — Pre-Flight & Experiment: Target Monetization / Exhaustion Research

**Experiment ID:** `HYP_TARGET_MILESTONE_01`  
**Parent Baseline:** `HYP_COMPOSITE_POLARITY_BREAKEVEN_01` (`COMPOSITE_01`)  
**Evaluation Partition:** Strict Development (`2021-01-01` through `2022-12-31`)  
**Validation Partition (2023):** LOCKED  
**Out-of-Sample Partition (2024–2026):** LOCKED  
**Status:** `RESULT_B_INFORMATIVE_MECHANISM` (Meaningful Development improvement and clean causal isolation; convexity truncation on runaway trend prevents unqualified promotion)

---

## 1. Governance Status & Scope Restrictions

- **Cycle #3 Baseline Frozen:** The Composite baseline (`HYP_COMPOSITE_POLARITY_BREAKEVEN_01`) achieved:
  - $N = 13$
  - Net Realized $\text{R} = +0.9615\text{R}$
  - Expectancy $= +0.0740\text{R}$
  - Profit Factor $= 1.2583$
  - Max Drawdown $= 2.5845\text{R}$
  - Target Hits $= 0/13$
- **Frozen Invariants:** All upstream components remain frozen:
  - Displacement polarity entry filter (`close > open` for LONG, `close < open` for SHORT)
  - $+1.0\text{R} \to +0.10\text{R}$ breakeven stop ratchet
  - Entry qualification, HTF context, MTF retest, LTF confirmation
  - Initial stop loss geometry and risk ceiling ($1.0\%$)
  - Planned structural target geometry and $\text{RR} \ge 4.0\text{R}$ firewall
  - Execution mechanics: 2 bps maker, 5 bps taker, 5 bps market slippage, adverse-first same-bar collision resolution
- **Methodological Guardrails:**
  - $0/13$ structural target hits does not prove target geometry is an "illusion" or error.
  - $+2.5\text{R}$ is treated strictly as a pre-registered hypothesis ablation, not an empirically optimized threshold.
  - No parameter sweeps were conducted ($2.0\text{R}, 2.25\text{R}, 2.75\text{R}, 3.0\text{R}$ were strictly excluded).

---

## 2. Phase 1 — Target / Excursion Forensic Pre-Audit

A read-only forensic analysis was performed on all 13 trades of the frozen `COMPOSITE_01` baseline prior to any execution changes.

### 13-Trade Excursion and Giveback Distribution

| Trade ID (and Anchor #) | Stream | Dir | MFE ($\text{R}$) | MAE ($\text{R}$) | Realized $\text{R}$ | Exit Reason | MFE Timestamp (UTC) | Exit Timestamp (UTC) | Peak Giveback ($\text{R}$) | Giveback % of MFE | $\ge 1\text{R}$ | $\ge 2\text{R}$ | $\ge 2.5\text{R}$ | $\ge 3\text{R}$ | Realized vs Excursion |
| :--- | :--- | :---: | :---: | :---: | :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| #01 (`cand_...1614220200`) | SOL_SET_4 | LONG | $0.2584$ | $0.8389$ | $-0.6857$ | MTF_STRUCTURAL_TRAIL | 2021-02-27 00:30 | 2021-02-27 09:00 | $0.9441$ | $365.4\%$ | No | No | No | No | Below All |
| #02 (`cand_...1624409100`) | SOL_SET_4 | SHORT | $1.1420$ | $0.2143$ | $+0.0822$ | BREAKEVEN_TRAIL | 2021-06-24 07:15 | 2021-06-24 14:00 | $1.0598$ | $92.8\%$ | Yes | No | No | No | Below $1\text{R}$ |
| #03 (Anchor #05) (`cand_...1626504300`) | SOL_SET_4 | SHORT | $3.7840$ | $0.2602$ | $+2.8010$ | MTF_STRUCTURAL_TRAIL | 2021-07-20 12:45 | 2021-07-20 15:45 | $0.9830$ | $26.0\%$ | Yes | Yes | Yes | Yes | $\ge 2.5\text{R}$, Below $3\text{R}$ |
| #04 (`cand_...1641543300`) | BTC_SET_4 | SHORT | $0.2339$ | $0.5963$ | $-0.3456$ | MTF_STRUCTURAL_TRAIL | 2021-01-08 15:15 | 2022-01-09 05:00 | $0.5795$ | $247.8\%$ | No | No | No | No | Below All |
| #05 (Anchor #10) (`cand_...1644192000`) | BTC_SET_4 | LONG | $3.7076$ | $0.0618$ | $+1.6942$ | MTF_STRUCTURAL_TRAIL | 2022-02-08 05:45 | 2022-02-08 08:45 | $2.0134$ | $54.3\%$ | Yes | Yes | Yes | Yes | $\ge 1\text{R}$, Below $2\text{R}$ |
| #06 (`cand_...1645524900`) | BTC_SET_4 | SHORT | $0.0268$ | $0.8829$ | $-0.8876$ | MTF_STRUCTURAL_TRAIL | 2022-02-23 03:15 | 2022-02-23 07:00 | $0.9144$ | $3412.0\%$ | No | No | No | No | Below All |
| #07 (`cand_...1652145300`) | ETH_SET_4 | SHORT | $0.8066$ | $0.0903$ | $+0.0585$ | MTF_STRUCTURAL_TRAIL | 2022-05-11 05:00 | 2022-05-11 05:00 | $0.7481$ | $92.7\%$ | No | No | No | No | Below All |
| #08 (`cand_...1654300800`) | SOL_SET_3 | SHORT | $0.0686$ | $0.1977$ | $-0.1540$ | MTF_STRUCTURAL_TRAIL | 2022-06-04 11:00 | 2022-06-04 20:00 | $0.2226$ | $324.5\%$ | No | No | No | No | Below All |
| #09 (`cand_...1668061800`) | BTC_SET_4 | SHORT | $0.2062$ | $0.2451$ | $-0.2602$ | MTF_STRUCTURAL_TRAIL | 2022-11-11 02:00 | 2022-11-11 08:15 | $0.4664$ | $226.2\%$ | No | No | No | No | Below All |
| #10 (`cand_...1669035600`) | SOL_SET_4 | SHORT | $0.4605$ | $0.2961$ | $-0.2990$ | MTF_STRUCTURAL_TRAIL | 2022-11-22 06:00 | 2022-11-22 09:15 | $0.7595$ | $164.9\%$ | No | No | No | No | Below All |
| #11 (`cand_...1669824000`) | ETH_SET_2 | SHORT | $1.0199$ | $0.5563$ | $+0.0482$ | BREAKEVEN_TRAIL | 2022-12-09 06:00 | 2022-12-09 06:00 | $0.9717$ | $95.3\%$ | Yes | No | No | No | Below $1\text{R}$ |
| #12 (`cand_...1670572800`) | ETH_SET_2 | SHORT | $0.7127$ | $1.9634$ | $-0.7156$ | MTF_STRUCTURAL_TRAIL | 2022-12-11 22:00 | 2022-12-13 06:00 | $1.4283$ | $200.4\%$ | No | No | No | No | Below All |
| #13 (`cand_...1671889500`) | SOL_SET_4 | SHORT | $0.3600$ | $0.3200$ | $-0.3749$ | MTF_STRUCTURAL_TRAIL | 2022-12-25 15:15 | 2022-12-25 17:45 | $0.7349$ | $204.1\%$ | No | No | No | No | Below All |

### Threshold Breakdown

- $\text{MFE} \ge 1.0\text{R}$: **4 / 13 (30.8%)** — Trades #02, #03, #05, #11
- $\text{MFE} \ge 2.0\text{R}$: **2 / 13 (15.4%)** — Trades #03, #05
- $\text{MFE} \ge 2.5\text{R}$: **2 / 13 (15.4%)** — Trades #03, #05
- $\text{MFE} \ge 3.0\text{R}$: **2 / 13 (15.4%)** — Trades #03, #05

---

## 3. Phase 2 — Runner Convexity Forensics

### Deep Audit of Runners

1. **Trade #03 (Anchor #05 — `cand_SOL/USDT_UNIFIED_STRATEGY_1626504300`):**
   - Stream: `SOL_SET_4` (SHORT)
   - Entry: 2021-07-19 02:30 UTC
   - Peak MFE: $+3.7840\text{R}$ at 2021-07-20 12:45 UTC
   - Baseline Realized R: $+2.8010\text{R}$ at 2021-07-20 15:45 UTC
   - Baseline Exit Mechanism: `MTF_STRUCTURAL_TRAIL`
   - Peak Giveback: $0.9830\text{R}$ ($25.98\%$ of MFE)
   - **Convexity Assessment:** The MTF structural trail performed exceptionally well. It captured $74.02\%$ of peak excursion and realized $+2.8010\text{R}$. A fixed milestone at $+2.5\text{R}$ would prematurely truncate this runner.

2. **Trade #05 (Anchor #10 — `cand_BTC/USDT_UNIFIED_STRATEGY_1644192000`):**
   - Stream: `BTC_SET_4` (LONG)
   - Entry: 2022-02-07 00:45 UTC
   - Peak MFE: $+3.7076\text{R}$ at 2022-02-08 05:45 UTC
   - Baseline Realized R: $+1.6942\text{R}$ at 2022-02-08 08:45 UTC
   - Baseline Exit Mechanism: `MTF_STRUCTURAL_TRAIL`
   - Peak Giveback: $2.0134\text{R}$ ($54.31\%$ of MFE)
   - **Convexity Assessment:** The MTF structural trail permitted a severe giveback of over $2.01\text{R}$ from a peak above $+3.70\text{R}$, exiting well below $+2.0\text{R}$. Here, structural trailing lagged market deceleration, failing to monetize significant favorable excursion.

### Structural Trail Functioning Across All Trades
- On sub-$1.5\text{R}$ excursions (#02, #07, #11), the combination of breakeven and structural trail successfully eliminates full-R losses (realizing $+0.08\text{R}, +0.06\text{R}, +0.05\text{R}$).
- In the runaway regime ($\text{MFE} > 3.7\text{R}$), structural trailing preserves meaningful profit ($+2.80\text{R}$ on SOL, $+1.69\text{R}$ on BTC), but exhibits substantial variance in giveback ($26\%$ vs $54\%$).
- Crucially, **there is a total void of trades between $1.15\text{R}$ and $3.70\text{R}$**. The distribution is strictly bimodal.

---

## 4. Phase 3 — Decision on Whether Milestone Experiment Was Justified

### Methodological Triad

- **OBSERVATION:**
  - In the frozen `COMPOSITE_01` Development replay, 0 of 13 trades achieved their planned structural target ($\text{RR} \ge 4\text{R}$).
  - Two trades achieved substantial excursion ($\text{MFE} > 3.7\text{R}$), but one gave back $2.0134\text{R}$ ($54.3\%$ of MFE) before structural trail triggered.
  - The excursion distribution is bimodal: 11 trades peaked below $1.15\text{R}$, while exactly 2 trades exceeded $3.70\text{R}$.
- **HYPOTHESIS:**
  - A pre-specified milestone monetization threshold at $+2.5\text{R}$ will causally monetize open excursion on high-excursion trades before large pullbacks occur, but at the cost of truncating outlier convexity on runaway trends.
- **EXPERIMENT:**
  - Test pre-registered `HYP_TARGET_MILESTONE_01` with an isolated $+2.5\text{R}$ limit exit mechanism against the frozen `COMPOSITE_01` baseline to quantify the exact economic trade-off: **Giveback Avoided vs. Convexity Truncated**.

**Verdict:** The experiment was justified because the empirical question is specific, causal, and testable without modifying upstream entry, sizing, or initial risk mechanics.

---

## 5. Pre-Registered Milestone Treatment: `HYP_TARGET_MILESTONE_01`

- **Parent Baseline:** `HYP_COMPOSITE_POLARITY_BREAKEVEN_01`
- **Milestone Threshold:** $+2.5\text{R}$ (pre-registered; zero parameter sweeping)
- **Causal Fill Logic:**
  - Limit order placed causally at $+2.5\text{R}$ profit price:
    - For LONG: $\text{Price} = \text{Entry} + 2.5 \times \text{Initial Risk}$
    - For SHORT: $\text{Price} = \text{Entry} - 2.5 \times \text{Initial Risk}$
  - Filled when candle high/low crosses milestone threshold.
  - Maker fee ($0.02\%$), zero slippage.
  - Adverse-first priority preserved: if adverse stop and milestone trigger on the same candle, stop is filled first.

---

## 6. Population Invariance Audit

| Audit Item | Baseline Composite | Milestone Treatment | Status |
| :--- | :---: | :---: | :---: |
| Candidate Population ($N$) | 13 | 13 | **PASS (Identical)** |
| Executed Trades ($N$) | 13 | 13 | **PASS (Identical)** |
| Trade Entry Timestamps | 13 matched | 13 matched | **PASS (Zero Drift)** |
| Initial Stop Loss Prices | 13 matched | 13 matched | **PASS (Zero Drift)** |
| Risk Sizing ($R_{\text{cash}}$) | 13 matched | 13 matched | **PASS (Zero Drift)** |
| Unmatched / Phantom Trades | 0 | 0 | **PASS (Zero)** |

---

## 7. Paired Attribution Ledger (All 13 Opportunities)

| Index | Trade ID | Stream | Dir | Baseline MFE | Baseline Exit Reason | Baseline Realized $\text{R}$ | Treatment Exit Reason | Treatment Realized $\text{R}$ | Delta $\text{R}$ | Reached $2.5\text{R}$? | Milestone Triggered? | Category |
| :---: | :--- | :--- | :---: | :---: | :--- | :---: | :--- | :---: | :---: | :---: | :---: | :--- |
| 1 | `cand_SOL/...1614220200` | SOL_SET_4 | LONG | $0.2584\text{R}$ | MTF_STRUCTURAL_TRAIL | $-0.6857\text{R}$ | MTF_STRUCTURAL_TRAIL | $-0.6857\text{R}$ | $0.0000\text{R}$ | No | No | UNCHANGED |
| 2 | `cand_SOL/...1624409100` | SOL_SET_4 | SHORT | $1.1420\text{R}$ | BREAKEVEN_TRAIL | $+0.0822\text{R}$ | BREAKEVEN_TRAIL | $+0.0822\text{R}$ | $0.0000\text{R}$ | No | No | UNCHANGED |
| 3 | `cand_SOL/...1626504300` | SOL_SET_4 | SHORT | $3.7840\text{R}$ | MTF_STRUCTURAL_TRAIL | $+2.8010\text{R}$ | MILESTONE_TARGET_EXIT | $+2.4916\text{R}$ | $-0.3094\text{R}$ | Yes | Yes | **HARMED (CONVEXITY TRUNCATED)** |
| 4 | `cand_BTC/...1641543300` | BTC_SET_4 | SHORT | $0.2339\text{R}$ | MTF_STRUCTURAL_TRAIL | $-0.3456\text{R}$ | MTF_STRUCTURAL_TRAIL | $-0.3456\text{R}$ | $0.0000\text{R}$ | No | No | UNCHANGED |
| 5 | `cand_BTC/...1644192000` | BTC_SET_4 | LONG | $3.7076\text{R}$ | MTF_STRUCTURAL_TRAIL | $+1.6942\text{R}$ | MILESTONE_TARGET_EXIT | $+2.4823\text{R}$ | $+0.7881\text{R}$ | Yes | Yes | **IMPROVED (GIVEBACK SAVED)** |
| 6 | `cand_BTC/...1645524900` | BTC_SET_4 | SHORT | $0.0268\text{R}$ | MTF_STRUCTURAL_TRAIL | $-0.8876\text{R}$ | MTF_STRUCTURAL_TRAIL | $-0.8875\text{R}$ | $+0.0001\text{R}$ | No | No | UNCHANGED |
| 7 | `cand_ETH/...1652145300` | ETH_SET_4 | SHORT | $0.8066\text{R}$ | MTF_STRUCTURAL_TRAIL | $+0.0585\text{R}$ | MTF_STRUCTURAL_TRAIL | $+0.0585\text{R}$ | $0.0000\text{R}$ | No | No | UNCHANGED |
| 8 | `cand_SOL/...1654300800` | SOL_SET_3 | SHORT | $0.0686\text{R}$ | MTF_STRUCTURAL_TRAIL | $-0.1540\text{R}$ | MTF_STRUCTURAL_TRAIL | $-0.1540\text{R}$ | $0.0000\text{R}$ | No | No | UNCHANGED |
| 9 | `cand_BTC/...1668061800` | BTC_SET_4 | SHORT | $0.2062\text{R}$ | MTF_STRUCTURAL_TRAIL | $-0.2602\text{R}$ | MTF_STRUCTURAL_TRAIL | $-0.2602\text{R}$ | $0.0000\text{R}$ | No | No | UNCHANGED |
| 10 | `cand_SOL/...1669035600` | SOL_SET_4 | SHORT | $0.4605\text{R}$ | MTF_STRUCTURAL_TRAIL | $-0.2990\text{R}$ | MTF_STRUCTURAL_TRAIL | $-0.2990\text{R}$ | $0.0000\text{R}$ | No | No | UNCHANGED |
| 11 | `cand_ETH/...1669824000` | ETH_SET_2 | SHORT | $1.0199\text{R}$ | BREAKEVEN_TRAIL | $+0.0482\text{R}$ | BREAKEVEN_TRAIL | $+0.0482\text{R}$ | $0.0000\text{R}$ | No | No | UNCHANGED |
| 12 | `cand_ETH/...1670572800` | ETH_SET_2 | SHORT | $0.7127\text{R}$ | MTF_STRUCTURAL_TRAIL | $-0.7156\text{R}$ | MTF_STRUCTURAL_TRAIL | $-0.7156\text{R}$ | $0.0000\text{R}$ | No | No | UNCHANGED |
| 13 | `cand_SOL/...1671889500` | SOL_SET_4 | SHORT | $0.3600\text{R}$ | MTF_STRUCTURAL_TRAIL | $-0.3749\text{R}$ | MTF_STRUCTURAL_TRAIL | $-0.3749\text{R}$ | $0.0000\text{R}$ | No | No | UNCHANGED |

---

## 8. Convexity Protection Analysis

The core governance requirement is to measure not just aggregate Net R, but the precise balance between giveback avoided and convexity surrendered.

```
                  +----------------------------------------------+
                  |         CONVEXITY ACCOUNTING LEDGER          |
                  +----------------------------------------------+
                  | Total R Gained (Trade #05 Giveback Saved)    | = +0.7881R
                  | Total R Sacrificed (Trade #03 Truncation)    | = -0.3094R
                  +----------------------------------------------+
                  | Net Delta R Across Population                | = +0.4788R
                  +----------------------------------------------+
```

### Detailed Breakdown of Affected Trades

1. **Trade #05 (`cand_BTC/USDT_UNIFIED_STRATEGY_1644192000`):**
   - Baseline Realized: $+1.6942\text{R}$ (exited via structural trail after giving back $2.0134\text{R}$ from $+3.7076\text{R}$ peak).
   - Milestone Realized: $+2.4823\text{R}$ (exited at $+2.5\text{R}$ limit price minus maker fee).
   - **Economic Gain:** $+0.7881\text{R}$ saved by capturing profit before the reversal.

2. **Trade #03 (`cand_SOL/USDT_UNIFIED_STRATEGY_1626504300`):**
   - Baseline Realized: $+2.8010\text{R}$ (exited via structural trail after orderly consolidation at peak $+3.7840\text{R}$).
   - Milestone Realized: $+2.4916\text{R}$ (exited at $+2.5\text{R}$ limit price minus maker fee).
   - **Convexity Sacrificed:** $-0.3094\text{R}$ clipped from the top winner.

3. **Remaining 11 Trades:**
   - Excursions peaked below $+2.5\text{R}$ (maximum MFE was $1.1420\text{R}$).
   - **Zero impact ($0.0000\text{R}$ delta)**. Full causal isolation preserved.

---

## 9. Headline Metrics & Baseline Comparison

| Metric | Composite Baseline (`COMPOSITE_01`) | Milestone Treatment (`MILESTONE_2_5R`) | Delta |
| :--- | :---: | :---: | :---: |
| Sample ($N$) | 13 | 13 | $0$ |
| Win Rate | $38.46\%$ ($5/13$) | $38.46\%$ ($5/13$) | $0.00\%$ |
| Gross Realized $\text{R}$ | $+1.3618\text{R}$ | $+1.7895\text{R}$ | $+0.4277\text{R}$ |
| Friction $\text{R}$ | $0.4003\text{R}$ | $0.3492\text{R}$ | $-0.0511\text{R}$ (maker exit savings) |
| **Net Realized $\text{R}$** | **$+0.9615\text{R}$** | **$+1.4403\text{R}$** | **$+0.4788\text{R}$** |
| **Expectancy** | **$+0.0740\text{R}$** | **$+0.1108\text{R}$** | **$+0.0368\text{R}$** |
| **Profit Factor** | **$1.2583$** | **$1.3869$** | **$+0.1286$** |
| Max Drawdown | $2.5845\text{R}$ | $2.5845\text{R}$ | $0.0000\text{R}$ |
| Max Consecutive Losses | 3 | 3 | $0$ |
| Milestone / Target Hits | $0 / 13$ ($0.0\%$) | $2 / 13$ ($15.4\%$) | $+2$ hits |

---

## 10. Phase 11 — Decision Gate & Institutional Classification

### Evaluation Criteria

- **RESULT A:** Strong Development evidence that the tested monetization mechanism improves economic conversion while preserving important convexity and all causal/population invariants.
- **RESULT B:** Meaningful Development improvement or informative mechanism evidence, but sample size or convexity limitations prevent promotion.
- **RESULT C:** Neutral / inconclusive.
- **RESULT D:** Harmful economic or convexity effect.
- **RESULT E:** Invalid experiment due to population, causal, lookahead, implementation, or reproducibility violation.

### Decision Gate Verdict: `RESULT_B_INFORMATIVE_MECHANISM`

**Justification:**
1. **Mathematical Improvement:** Net R improved from $+0.9615\text{R}$ to $+1.4403\text{R}$ ($+49.8\%$), expectancy rose to $+0.1108\text{R}$, and PF rose to $1.3869$.
2. **Convexity Truncation Identified:** On Trade #03, the milestone directly sacrificed $-0.3094\text{R}$ of runner convexity relative to the baseline MTF structural trail. While net delta across the two affected trades is positive ($+0.4788\text{R}$), a fixed milestone inherently places an artificial ceiling on runaway trades.
3. **Severe Sample Sparsity ($N=2$):** Only 2 trades reached $\ge 2.5\text{R}$ MFE in the entire 2-year Development partition. The aggregate gain is entirely attributable to a single trade (#05) avoiding a $2.01\text{R}$ giveback. An empirical sample of $N=2$ is far too sparse to justify promotion to canonical control or production readiness.
4. **Institutional Prudence:** Per governance rules, positive expectancy alone MUST NOT determine Result A. Because convexity truncation is real and the sample of high-excursion trades is small, `RESULT_B` is the only methodologically honest classification.

---

## 11. Strict Stop Condition Compliance

As mandated:
- **STOPPED.**
- No parameter sweeps or threshold adjustments ($2.0\text{R}, 2.25\text{R}, 2.75\text{R}, 3.0\text{R}$) were conducted.
- No target geometry was modified.
- No entry logic or polarity was modified.
- No breakeven logic was modified.
- Validation 2023 and OOS 2024–2026 partitions were **NOT inspected or touched**.
- Treatment was **NOT promoted to `H1_CONTROL`**.
- The target mechanism is **NOT declared "solved"**.
