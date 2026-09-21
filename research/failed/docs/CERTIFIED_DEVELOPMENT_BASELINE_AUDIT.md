# Authoritative Alpha Forensics & Baseline Certification Report (2021–2022 Development Partition)

**Certification Date:** 2026-09-09  
**Status:** 🟢 **CERTIFIED CAUSAL LEDGER (INFRASTRUCTURE & ACCOUNTING VERIFIED)**  
**Dataset Partition:** Development (2021-01-01T00:00:00Z to 2022-12-31T23:59:59Z)  
**Partition Lock:** 2023 Validation & 2024–2026 Out-of-Sample partitions remain strictly **LOCKED**  
**Replayer Fix Commit:** `6382061` (merged to `feat/exp-anchor2-expansion` via `ada37f7`)  
**Test Suite Verification:** 359 / 359 tests passed (100% green)

---

## Executive Summary & Research Gate Decision

Following the discovery of the replayer loop defect (where exited trade plans re-entered the risk firewall, generating 12 phantom duplicate trades), an infrastructure patch was applied to `main`:
1. Active trade exits (`MTF_TRAIL_EXIT`, `LTF_SL_EXIT`, `TP_EXIT`) now strictly precede new candidate entry evaluations.
2. An explicit invariant was enforced: if a trade plan ID already exists in `ledger.trades`, it can **never** re-enter candidate risk evaluation or execution.
3. Exited plans transition to a terminal status (`CLOSED`).
4. A dedicated regression test (`test_terminal_candidate_never_reenters_regression_invariant`) was committed and passed.

Following this repair, both **Canonical H0 Control** and the **ANCHOR_2 Treatment** were replayed across the entire 15-stream matrix over the 2-year Development Partition (2021–2022).

### Primary Accounting Findings
- **Zero Duplicate Trade IDs:** Both H0 and ANCHOR_2 ledgers contain 100% unique trade IDs with zero phantom re-entries.
- **Canonical H0 Control Population:** Exactly **$N=8$ genuine trades**, generating **$-5.1331\text{R}$** net realized loss (0 wins, 8 losses).
- **ANCHOR_2 Treatment Population:** Exactly **$N=23$ genuine trades**, generating **$-4.1741\text{R}$** net realized loss (3 wins, 20 losses).
- **Edge Status:** 🔴 **UNPROVEN / NEGATIVE EXPECTANCY**. While ANCHOR_2 increases target resolution and delivers 3 multi-R winners ($+2.80\text{R}, +1.69\text{R}, +1.06\text{R}$), overall strategy expectancy remains negative ($-0.1815\text{R}$).

---

## 1. Certified Performance Summary (H0 vs ANCHOR_2)

| Metric | Canonical H0 Control | ANCHOR_2 Treatment | Delta ($\Delta$) | Status / Interpretation |
| :--- | :--- | :--- | :--- | :--- |
| **Total Executed Trades ($N$)** | **8** | **23** | $+15$ trades | Structural target resolution expanded candidate survival |
| **Unique Candidate IDs** | **8 (100%)** | **23 (100%)** | $+15$ | 0 duplicate candidates; 0 phantom re-entries |
| **Wins / Losses** | 0W / 8L | 3W / 20L | $+3\text{W}$ | First multi-R trend captures unlocked |
| **Win Rate (%)** | 0.00% | **13.04%** | $+13.04\%$ | Modest win rate characteristic of high-RR trend systems |
| **Gross Realized R** | $-4.6086\text{R}$ | **$-3.1011\text{R}$** | $+1.5075\text{R}$ | Gross economic improvement |
| **Friction Drag ($R$)** | $0.5245\text{R}$ | **$1.0730\text{R}$** | $+0.5485\text{R}$ | Realistic fees (2/5 bps) + adverse slippage (5 bps) |
| **Net Realized R** | **$-5.1331\text{R}$** | **$-4.1741\text{R}$** | $+0.9590\text{R}$ | Net drawdown reduced by $\approx 1.0\text{R}$ |
| **Expectancy ($E[R]$)** | **$-0.6416\text{R}$** | **$-0.1815\text{R}$** | $+0.4601\text{R}$ | Expectancy improved by $+0.46\text{R}$ per trade |
| **Profit Factor (PF)** | 0.0000 | **0.5712** | $+0.5712$ | Wins offset $>57\%$ of losses |
| **Max Drawdown ($R$)** | $5.1331\text{R}$ | **$4.7820\text{R}$** | $-0.3511\text{R}$ | Peak-to-trough drawdown |
| **Max Consecutive Losses** | 8 | **7** | $-1$ | Clustering observed in macro regimes |
| **Average MFE ($R$)** | $+0.8643\text{R}$ | **$+0.9747\text{R}$** | $+0.1104\text{R}$ | Clean directional excursion expansion |
| **Median MFE ($R$)** | $+0.7512\text{R}$ | **$+0.6316\text{R}$** | $-0.1196\text{R}$ | Median remains in favorable territory |
| **Average MAE ($R$)** | $1.5025\text{R}$ | **$0.8082\text{R}$** | $-0.6943\text{R}$ | Significant reduction in adverse drawdown |
| **Median MAE ($R$)** | $1.7347\text{R}$ | **$0.5580\text{R}$** | $-1.1767\text{R}$ | Adverse pressure halved under ANCHOR_2 |

---

## 2. The Reconciled Alpha Waterfall

Evaluating 277,908 total historical market candles across all 15 streams on the 2021–2022 Development partition:

```text
TOTAL MARKET BARS EVALUATED: 277,908 (100.0%)
   │
   ▼
[1] HTF QUALIFIED CANDIDATES: 1,424 (0.51% of bars)
   │  [Survival: 100.0% | Drop: 0.0%]
   ▼
[2] MTF ALIGNED CANDIDATES: 1,173 (0.42% of bars)
   │  [Survival: 82.37% | Drop: 17.63% due to MTF counter-trend]
   ▼
[3] MTF RETESTED CANDIDATES: 754 (0.27% of bars)
   │  [Survival: 64.28% | Drop: 35.72% without zone retest]
   ▼
[4] LTF TRIGGERS CONFIRMED: 735 (0.26% of bars)
   │  [Survival: 97.48% | Drop: 2.52% without LTF sweep/displacement]
   ▼
[5] TARGET RESOLVED CANDIDATES (ENTERED):
   │  ├── Canonical H0:      11 candidates (1.50% survival from Step 4)
   │  └── ANCHOR_2 Fallback: 30 candidates (4.08% survival from Step 4)
   ▼
[6] RISK FIREWALL EVALUATED & APPROVED:
   │  ├── Canonical H0:      11 approved (100.0% survival)
   │  └── ANCHOR_2:          30 approved (100.0% survival)
   ▼
[7] PENDING LIMIT ORDER FILLS:
   │  ├── Canonical H0:      8 filled (72.7% fill rate) | 3 expired unfilled
   │  └── ANCHOR_2:          23 filled (76.7% fill rate) | 7 expired unfilled
   ▼
[8] GENUINE EXECUTED TRADES IN LEDGER:
   │  ├── Canonical H0:      8 executed trades (0 phantom duplicates)
   │  └── ANCHOR_2:          23 executed trades (0 phantom duplicates)
```

---

## 3. Clean Excursion Analysis (MFE & MAE Decomposition)

### MFE Bucket Distribution ($N=23$ Clean Trades)
| MFE Bucket | Trade Count ($N$) | % of Total | Total Realized $R$ | Expectancy ($E[R]$) | Win Rate (%) | Primary Exit Mechanisms |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **$< 0.5\text{R}$** | **10** | **43.48%** | $-3.5153\text{R}$ | $-0.3515\text{R}$ | 0.0% | MTF Structural Trail (10) |
| **$0.5\text{R}$–$<1.0\text{R}$** | **5** | **21.74%** | $-3.3853\text{R}$ | $-0.6771\text{R}$ | 0.0% | MTF Trail (3), Initial SL (2) |
| **$1.0\text{R}$–$<1.5\text{R}$** | **3** | **13.04%** | $-1.6102\text{R}$ | $-0.5367\text{R}$ | 0.0% | MTF Structural Trail (3) |
| **$1.5\text{R}$–$<2.0\text{R}$** | **3** | **13.04%** | $-0.1585\text{R}$ | $-0.0528\text{R}$ | 33.3% | MTF Trail (2), Initial SL (1) |
| **$2.0\text{R}$–$<3.0\text{R}$** | **0** | **0.00%** | $0.0000\text{R}$ | $0.0000\text{R}$ | 0.0% | None |
| **$3.0\text{R}$–$<4.0\text{R}$** | **2** | **8.70%** | **$+4.4952\text{R}$** | **$+2.2476\text{R}$** | **100.0%** | MTF Structural Trail (2) |
| **$\ge 4.0\text{R}$** | **0** | **0.00%** | $0.0000\text{R}$ | $0.0000\text{R}$ | 0.0% | None |

### Decomposition of Losses ($N=20$ Losses Total)
- **Immediate Invalidation Losses ($\text{MFE} < 0.5\text{R}$):**  
  **10 out of 20 losses ($50.0\%$)** failed to achieve even $+0.5\text{R}$ excursion.  
  *Causal Meaning:* In half the losses, entry was immediately hostile; price did not expand structurally in the setup direction before invalidating.
- **Monetization Giveback Losses ($\text{MFE} \ge 1.0\text{R}$):**  
  **4 out of 20 losses ($20.0\%$)** reached between $+1.00\text{R}$ and $+1.97\text{R}$ excursion but fully gave back their gains and closed as losses.  
  *Causal Meaning:* In one-fifth of losses, the strategy was directionally correct and reached substantial profit, but MTF trailing latency allowed the excursion to reverse into a loss.

---

## 4. Target Reachability Analysis

| Target Horizon | Probability of Reach ($\%$) | Count Reaching | Realized Converted Wins |
| :--- | :--- | :--- | :--- |
| **Reaching $\ge +0.5\text{R}$** | **56.52%** | 13 / 23 | 3 |
| **Reaching $\ge +1.0\text{R}$** | **34.78%** | 8 / 23 | 3 |
| **Reaching $\ge +2.0\text{R}$** | **8.70%** | 2 / 23 | 2 |
| **Reaching $\ge +3.0\text{R}$** | **8.70%** | 2 / 23 | 2 |
| **Reaching $\ge +4.0\text{R}$** | **0.00%** | 0 / 23 | 0 |
| **Reaching Planned Structural Target** | **0.00%** | **0 / 23** | **0** |

### Critical Target Geometry Finding
- **Mean Planned Target:** **$6.78\text{R}$** (Range: $4.13\text{R}$ to $12.94\text{R}$).
- **Maximum Realized MFE:** **$+3.78\text{R}$**.
- **Target Reachability Verdict:** **`USUALLY_UNREACHABLE` ($0/23$ hits)**.  
  Because structural targets require $+5\text{R}$ to $+13\text{R}$, **100% of trades** rely entirely on MTF Structural Trailing for exit resolution. Zero trades ever monetize via fixed target limit orders.

---

## 5. Timeframe & Asset Attribution

### Timeframe Performance Matrix
| Timeframe Set | Horizons | Total Trades ($N$) | Win Rate (%) | Net Realized $R$ | Expectancy ($E[R]$) | Profit Factor | Avg MFE | Avg MAE |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **SET 1** | 1M $\rightarrow$ 1W $\rightarrow$ 1D | 0 | 0.0% | $0.0000\text{R}$ | $0.0000\text{R}$ | 0.00 | 0.0R | 0.0R |
| **SET 2** | 1W $\rightarrow$ 1D $\rightarrow$ 4H | 3 | 0.0% | $-2.4299\text{R}$ | $-0.8100\text{R}$ | 0.00 | $+0.91\text{R}$ | $2.02\text{R}$ |
| **SET 3** | 1D $\rightarrow$ 4H $\rightarrow$ 1H | 5 | 0.0% | $-2.6248\text{R}$ | $-0.5250\text{R}$ | 0.00 | $+0.62\text{R}$ | $1.18\text{R}$ |
| **SET 4** | 4H $\rightarrow$ 1H $\rightarrow$ 15M | **15** | **20.0%** | **$+0.8805\text{R}$** | **$+0.0587\text{R}$** | **1.1882** | **$+1.11\text{R}$** | **$0.44\text{R}$** |
| **SET 5** | 15M $\rightarrow$ 5M $\rightarrow$ 1M | 0 | — | $0.0000\text{R}$ | — | — | — | — |

> **Cautionary Note on SET 4 vs SET 2/3:** While SET 4 generated positive net expectancy ($+0.88\text{R}, \text{PF}=1.19$) and SET 2/3 produced 100% losses ($-5.05\text{R}$), this does not prove intraday has edge over position trading. SET 2/3 exhibited significantly larger initial SL distances and higher MAE ($1.50\text{R}$ vs $0.44\text{R}$), indicating that higher timeframe structural stops may have different risk-geometry interactions.

### Asset Performance Matrix
| Asset | Total Trades ($N$) | Win Rate (%) | Net Realized $R$ | Expectancy ($E[R]$) | Profit Factor | Avg MFE | Avg MAE |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **BTC** | 6 | 16.67% | $-1.9959\text{R}$ | $-0.3327\text{R}$ | 0.4591 | $+1.06\text{R}$ | $1.08\text{R}$ |
| **ETH** | 5 | 20.00% | $-1.4943\text{R}$ | $-0.2989\text{R}$ | 0.4160 | $+1.35\text{R}$ | $1.32\text{R}$ |
| **SOL** | 12 | 8.33% | **$-0.6839\text{R}$** | **$-0.0570\text{R}$** | **0.8037** | $+0.78\text{R}$ | $0.46\text{R}$ |

---

## 6. Complete Clean Trade Attribution Table ($N=23$)

Every trade executed in the certified Development partition with zero lookahead, adverse-first collision resolution, and 2 bps maker / 5 bps taker fees + 5 bps adverse slippage:

| # | Trade ID | Stream | Asset | Dir | Entry Time (UTC) | Planned RR | Target R | MFE ($R$) | MAE ($R$) | Exit Reason | Net Realized R |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `cand_SOL/USDT_UNIFIED_STRATEGY_1614220200` | SOL_SET_4 | SOL | LONG | 2021-02-26 21:00 | 4.97 | 4.97R | 0.26R | 0.84R | MTF_STRUCTURAL_TRAIL | **-0.6857R** |
| 2 | `cand_SOL/USDT_UNIFIED_STRATEGY_1617111900` | SOL_SET_4 | SOL | LONG | 2021-03-31 14:30 | 4.78 | 4.78R | 0.61R | 0.40R | MTF_STRUCTURAL_TRAIL | **-0.1724R** |
| 3 | `cand_SOL/USDT_UNIFIED_STRATEGY_1624409100` | SOL_SET_4 | SOL | SHORT | 2021-06-24 00:15 | 5.16 | 5.16R | 1.14R | 0.24R | MTF_STRUCTURAL_TRAIL | **-0.2324R** |
| 4 | `cand_ETH/USDT_UNIFIED_STRATEGY_1625770800` | ETH_SET_3 | ETH | LONG | 2021-07-08 23:00 | 8.18 | 8.18R | 0.79R | 1.70R | INITIAL_LTF_SL | **-1.1026R** |
| 5 | `cand_SOL/USDT_UNIFIED_STRATEGY_1626504300` | SOL_SET_4 | SOL | SHORT | 2021-07-18 23:30 | 6.81 | 6.81R | **3.78R** | 0.26R | MTF_STRUCTURAL_TRAIL | **+2.8010R** |
| 6 | `cand_SOL/USDT_UNIFIED_STRATEGY_1626795900` | SOL_SET_4 | SOL | SHORT | 2021-07-20 17:30 | 5.08 | 5.08R | 0.27R | 0.43R | MTF_STRUCTURAL_TRAIL | **-0.2314R** |
| 7 | `cand_BTC/USDT_UNIFIED_STRATEGY_1628236800` | BTC_SET_2 | BTC | SHORT | 2021-08-07 00:00 | 10.28 | 10.28R | 0.66R | 1.77R | INITIAL_LTF_SL | **-1.1055R** |
| 8 | `cand_BTC/USDT_UNIFIED_STRATEGY_1635278400` | BTC_SET_3 | BTC | LONG | 2021-10-27 00:00 | 8.58 | 8.58R | 1.54R | 2.93R | INITIAL_LTF_SL | **-1.0912R** |
| 9 | `cand_BTC/USDT_UNIFIED_STRATEGY_1641543300` | BTC_SET_4 | BTC | SHORT | 2022-01-08 21:15 | 5.35 | 5.35R | 0.23R | 0.60R | MTF_STRUCTURAL_TRAIL | **-0.3456R** |
| 10 | `cand_BTC/USDT_UNIFIED_STRATEGY_1644192000` | BTC_SET_4 | BTC | LONG | 2022-02-07 01:15 | 5.82 | 5.82R | **3.71R** | 0.06R | MTF_STRUCTURAL_TRAIL | **+1.6942R** |
| 11 | `cand_BTC/USDT_UNIFIED_STRATEGY_1645524900` | BTC_SET_4 | BTC | SHORT | 2022-02-23 04:45 | 5.14 | 5.14R | 0.03R | 0.88R | MTF_STRUCTURAL_TRAIL | **-0.8876R** |
| 12 | `cand_SOL/USDT_UNIFIED_STRATEGY_1649116800` | SOL_SET_3 | SOL | LONG | 2022-04-11 01:00 | 10.67 | 10.67R | 0.29R | 0.92R | MTF_STRUCTURAL_TRAIL | **-0.0718R** |
| 13 | `cand_SOL/USDT_UNIFIED_STRATEGY_1649638800` | SOL_SET_3 | SOL | LONG | 2022-04-11 06:00 | 5.40 | 5.40R | 0.42R | 0.16R | MTF_STRUCTURAL_TRAIL | **-0.2052R** |
| 14 | `cand_ETH/USDT_UNIFIED_STRATEGY_1652145300` | ETH_SET_4 | ETH | SHORT | 2022-05-11 05:00 | 4.13 | 4.13R | **1.91R** | 0.56R | MTF_STRUCTURAL_TRAIL | **-0.1319R** |
| 15 | `cand_SOL/USDT_UNIFIED_STRATEGY_1654300800` | SOL_SET_3 | SOL | SHORT | 2022-06-04 11:00 | 4.69 | 4.69R | 0.07R | 0.20R | MTF_STRUCTURAL_TRAIL | **-0.1540R** |
| 16 | `cand_ETH/USDT_UNIFIED_STRATEGY_1661040900` | ETH_SET_4 | ETH | SHORT | 2022-08-22 05:15 | 5.62 | 5.62R | **1.97R** | 0.04R | MTF_STRUCTURAL_TRAIL | **+1.0646R** |
| 17 | `cand_SOL/USDT_UNIFIED_STRATEGY_1666371600` | SOL_SET_4 | SOL | SHORT | 2022-10-22 12:00 | 12.94 | 12.94R | **1.00R** | 0.76R | MTF_STRUCTURAL_TRAIL | **-0.7691R** |
| 18 | `cand_BTC/USDT_UNIFIED_STRATEGY_1668061800` | BTC_SET_4 | BTC | SHORT | 2022-11-11 06:30 | 4.71 | 4.71R | 0.21R | 0.25R | MTF_STRUCTURAL_TRAIL | **-0.2602R** |
| 19 | `cand_SOL/USDT_UNIFIED_STRATEGY_1669035600` | SOL_SET_4 | SOL | SHORT | 2022-11-21 22:00 | 11.97 | 11.97R | 0.46R | 0.30R | MTF_STRUCTURAL_TRAIL | **-0.2990R** |
| 20 | `cand_ETH/USDT_UNIFIED_STRATEGY_1669824000` | ETH_SET_2 | ETH | SHORT | 2022-12-09 04:00 | 6.98 | 6.98R | **1.36R** | 2.33R | MTF_STRUCTURAL_TRAIL | **-0.6087R** |
| 21 | `cand_ETH/USDT_UNIFIED_STRATEGY_1670572800` | ETH_SET_2 | ETH | SHORT | 2022-12-10 12:00 | 4.80 | 4.80R | 0.71R | 1.96R | MTF_STRUCTURAL_TRAIL | **-0.7156R** |
| 22 | `cand_SOL/USDT_UNIFIED_STRATEGY_1671258600` | SOL_SET_4 | SOL | SHORT | 2022-12-18 12:00 | 5.58 | 5.58R | 0.63R | 0.68R | MTF_STRUCTURAL_TRAIL | **-0.2891R** |
| 23 | `cand_SOL/USDT_UNIFIED_STRATEGY_1671889500` | SOL_SET_4 | SOL | SHORT | 2022-12-25 16:00 | 7.28 | 7.28R | 0.36R | 0.32R | MTF_STRUCTURAL_TRAIL | **-0.3749R** |

---

## 7. Forensic Decomposition & Strategic Next Steps

Now that accounting truth is certified ($N=23$ unique trades, zero phantom duplicates), we examine where economic value is lost.

### What is Definitely Proven
1. **Infrastructure Integrity:** The replayer terminal state and duplicate execution defect is permanently fixed and validated by 359 passing tests.
2. **Deterministic Reproducibility:** Exact trade counts ($N=8$ for H0, $N=23$ for ANCHOR_2) are reproducible from raw candles.
3. **Zero Lookahead:** All visible horizons are strictly point-in-time; order collision is resolved adverse-first.
4. **Target Over-Extension:** Planned targets demanding $\ge 5.0\text{R}$ are **never hit** ($0/23$ trades). Price regularly achieves $+1\text{R}$ to $+3.78\text{R}$, but the target engine projects unrealistic levels ($+6.78\text{R}$ average, up to $+12.94\text{R}$), preventing any trade from capturing liquidity via limit profit targets.
5. **Entry Invalidation vs Monetization Split:**
   - **$50.0\%$ of losses ($10/20$)** are **Entry Invalidation** ($\text{MFE} < 0.5\text{R}$).
   - **$20.0\%$ of losses ($4/20$)** are **Monetization Giveback** ($\text{MFE} \ge 1.0\text{R}$).
   - **$30.0\%$ of losses ($6/20$)** are intermediate structural failures ($0.5\text{R} \le \text{MFE} < 1.0\text{R}$).

### What Remains Uncertain
- Whether the poor performance in SET 2/3 ($-5.05\text{R}$ across 8 trades) is caused by timeframe horizon per se or by large structural stop distance interacting with volatility regimes.
- Whether entry filtering (e.g. displacement candle polarity) or profit monetization (e.g. realistic target placement or trailing ratchet) represents the higher-leverage causal path.

### Proposed Next Isolated Hypothesis
Before modifying entry logic or changing stop loss rules, the single most empirically defensible leakage point is:
**HYP_TARGET_REALISM_01**:  
*Hypothesis:* Structural forward expansion targets projected at $\ge 5\text{R}$ create an unreachable destination trap where $0/23$ trades take profit. Replacing or capping structural target projections at a realistic exhaustion bound (or implementing a structural interim monetization tier at $+2.0\text{R}$ to $+3.0\text{R}$) will retain excursions that currently turn into giveback losses.
