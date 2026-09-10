# Day 41 Forensic Audit: Full Current-Architecture Baseline & Trade-Frequency Analysis

---

**Document Identifier:** `DAY41_CURRENT_ARCHITECTURE_FULL_BASELINE_AUDIT`  
**Governing State:** **Day 41 (OPEN)**  
**Dataset Scope:** Historical Development Partition (`2021-01-01T00:00:00Z` to `2022-12-31T23:59:59Z`, 277,908 market candles)  
**Universe Audited:** BTC/USDT, ETH/USDT, SOL/USDT across all 5 Canonical Timeframe Sets (15 Streams)  
**Replay Dataset:** Repaired Composite Baseline (`scratch/composite_01_dev_results_repaired_terminal.json`)  
**Audit Policy:** Strictly Read-Only. Strategy code frozen, zero parameter sweeps, zero target redesigns, Validation (`2023`) and OOS (`2024–2026`) partitions strictly **LOCKED**.

---

## Executive Summary & Core Quantitative Verdicts

Across 2 full calendar years ($277,908$ candles) on Bitcoin, Ethereum, and Solana:

1. **Overall Baseline Performance:**
   $$\text{Trades} = 11 \quad|\quad \text{Win Rate} = 45.45\% \quad|\quad \text{Profit Factor} = 1.4326 \quad|\quad \text{Realized Net R} = +1.4145\text{R} \quad|\quad \text{Max DD} = 2.1316\text{R}$$
2. **Frequency & Commercial Velocity:**
   - **$5.50$ trades per year** across the entire 3-asset portfolio ($0.458$ trades per month).
   - **$0.0396$ trades per 1,000 candles** evaluated.
   - For an institutional account risking 1% per trade, $+1.4145\text{R}$ equates to approximately $+1.41\%$ unleveraged portfolio gain over 24 months. While positive and containing an encouraging expectancy ($+0.1286\text{R}$), this trade density is **too sparse to establish statistical significance ($p > 0.05$) or commercially viable capital velocity**.
3. **The Core Architectural Bottleneck Discovered:**
   - The strategy generated **1,462 candidate setups**.
   - **785** achieved active MTF causal retest.
   - **391** achieved full LTF liquidity sweep + displacement polarity confirmation.
   - Out of the 391 LTF-confirmed setups, **364 ($93.09\%$) were annihilated by the planned $\text{RR} < 4.0\text{R}$ firewall**.
   - The median planned RR across all confirmed setups was **$0.47\text{R}$** (Mean: $0.80\text{R}$, 75th percentile: $0.97\text{R}$). **$76.5\%$ of all confirmed setups had planned $\text{RR} < 1.0\text{R}$**.
4. **Timeframe Set Contribution:**
   - **SET 4 (4H -> 1H -> 15M, Intraday):** Contributed **9 out of 11 executed trades ($81.8\%$)** and $+2.0819\text{R}$ net profit.
   - **SET 2 (1W -> 1D -> 4H, Position):** Contributed **2 trades ($18.2\%$)** and $-0.6674\text{R}$ net profit.
   - **SET 1 (1M -> 1W -> 1D, Macro):** Contributed **0 trades** ($4$ LTF confirmations, $0$ reached 4R).
   - **SET 3 (1D -> 4H -> 1H, Swing):** Contributed **0 trades** ($83$ LTF confirmations, $0$ reached 4R).
   - **SET 5 (15M -> 5M -> 1M, Scalping):** Fails closed causally ($0$ trades, historical depth unavailable).

---

## 1. The 15-Stream Performance & Funnel Matrix

The complete breakdown across all 15 operational streams (`3 assets × 5 timeframe sets`) from the certified terminal replay:

| Stream ID | Style Name | Status | Candles | Cands | HTF Qual | MTF Align | MTF Retest | LTF Conf | Tgt Res | RR $\ge$ 4R | Trades | Win% | Net R | Profit Factor | Max DD |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **BTC_SET_1** | 1M/1W/1D | OK | 731 | 1 | 1 | 1 | 1 | 1 | 1 | 0 | **0** | 0.0% | +0.0000R | 0.00 | 0.0000R |
| **ETH_SET_1** | 1M/1W/1D | OK | 731 | 12 | 12 | 10 | 10 | 3 | 3 | 0 | **0** | 0.0% | +0.0000R | 0.00 | 0.0000R |
| **SOL_SET_1** | 1M/1W/1D | OK | 731 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | **0** | 0.0% | +0.0000R | 0.00 | 0.0000R |
| **BTC_SET_2** | 1W/1D/4H | OK | 4,381 | 35 | 35 | 35 | 18 | 10 | 10 | 0 | **0** | 0.0% | +0.0000R | 0.00 | 0.0000R |
| **ETH_SET_2** | 1W/1D/4H | OK | 4,381 | 16 | 16 | 15 | 8 | 4 | 3 | 2 | **2** | 50.0% | -0.6674R | 0.07 | 0.7156R |
| **SOL_SET_2** | 1W/1D/4H | OK | 4,381 | 9 | 9 | 8 | 5 | 1 | 1 | 0 | **0** | 0.0% | +0.0000R | 0.00 | 0.0000R |
| **BTC_SET_3** | 1D/4H/1H | OK | 17,508 | 123 | 123 | 113 | 60 | 30 | 30 | 0 | **0** | 0.0% | +0.0000R | 0.00 | 0.0000R |
| **ETH_SET_3** | 1D/4H/1H | OK | 17,508 | 112 | 112 | 101 | 46 | 26 | 24 | 0 | **0** | 0.0% | +0.0000R | 0.00 | 0.0000R |
| **SOL_SET_3** | 1D/4H/1H | OK | 17,508 | 104 | 104 | 93 | 56 | 27 | 27 | 0 | **0** | 0.0% | +0.0000R | 0.00 | 0.0000R |
| **BTC_SET_4** | 4H/1H/15M | OK | 70,016 | 316 | 316 | 251 | 189 | 94 | 94 | 4 | **4** | 25.0% | +0.2008R | 1.13 | 1.1478R |
| **ETH_SET_4** | 4H/1H/15M | OK | 70,016 | 342 | 342 | 280 | 179 | 83 | 82 | 1 | **1** | 100.0%| +0.0585R | $\infty$ | 0.0000R |
| **SOL_SET_4** | 4H/1H/15M | OK | 70,016 | 392 | 392 | 304 | 213 | 112 | 112 | 4 | **4** | 50.0% | **+1.8226R**| 2.72 | 0.6857R |
| **BTC_SET_5** | 15M/5M/1M | FAIL_CLOSED | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | **0** | 0.0% | +0.0000R | 0.00 | 0.0000R |
| **ETH_SET_5** | 15M/5M/1M | FAIL_CLOSED | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | **0** | 0.0% | +0.0000R | 0.00 | 0.0000R |
| **SOL_SET_5** | 15M/5M/1M | FAIL_CLOSED | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | **0** | 0.0% | +0.0000R | 0.00 | 0.0000R |
| **TOTAL** | — | — | **277,908** | **1,462** | **1,462** | **1,211** | **785** | **391** | **387** | **11** | **11** | **45.5%** | **+1.4145R** | **1.43** | **2.1316R** |

---

## 2. Multi-Dimensional Aggregations

### A. Aggregation by Timeframe Set

| Timeframe Set | Execution Style | Candidates | LTF Confirmed | Planned RR $\ge$ 4R | Executed Trades | Win Rate | Realized Net R | Expectancy | Profit Factor |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **SET 1** | 1M / 1W / 1D (Macro) | 13 | 4 | 0 | **0** | 0.0% | +0.0000R | +0.0000R | 0.00 |
| **SET 2** | 1W / 1D / 4H (Position) | 60 | 15 | 2 | **2** | 50.0% | -0.6674R | -0.3337R | 0.07 |
| **SET 3** | 1D / 4H / 1H (Swing) | 339 | 83 | 0 | **0** | 0.0% | +0.0000R | +0.0000R | 0.00 |
| **SET 4** | 4H / 1H / 15M (Intraday)| 1,050 | 289 | 9 | **9** | 44.4% | **+2.0819R** | +0.2313R | **1.82** |
| **SET 5** | 15M / 5M / 1M (Scalping)| 0 | 0 | 0 | **0** | 0.0% | +0.0000R | +0.0000R | 0.00 |

#### Analysis:
- **SET 4 is the Engine of the Platform:** $71.8\%$ of candidates, $73.9\%$ of LTF confirmations, and **$81.8\%$ of executed trades** reside on SET 4. It generated $+2.0819\text{R}$ net profit with a $1.82$ profit factor.
- **SET 3 is Completely Sterilized:** Despite generating 339 candidates and 83 valid LTF confirmations, **exactly 0 trades executed**. Every single one failed the 4R firewall because targets were too close.
- **SET 1 is Naturally Sparse:** Macro candles (monthly HTF, weekly MTF, daily LTF) inherently produce very few setups (only 13 candidates over 2 years). None qualified at 4R.

---

### B. Aggregation by Asset Universe

| Asset | Candidates | LTF Confirmed | Planned RR $\ge$ 4R | Executed Trades | Win Rate | Realized Net R | Expectancy | Profit Factor |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **BTC/USDT** | 475 | 135 | 4 | **4** | 25.0% | +0.2008R | +0.0502R | 1.13 |
| **ETH/USDT** | 482 | 116 | 3 | **3** | 66.7% | -0.6089R | -0.2030R | 0.15 |
| **SOL/USDT** | 505 | 140 | 4 | **4** | 50.0% | **+1.8226R** | +0.4557R | **2.72** |

#### Analysis:
- **Balanced Candidate Generation:** Candidates are evenly split across the universe (SOL $34.5\%$, ETH $33.0\%$, BTC $32.5\%$).
- **Profit Concentration in Solana:** SOL generated $+1.8226\text{R}$ ($PF = 2.72$) led by the $+2.80\text{R}$ trend-runner on SET 4. BTC contributed $+0.20\text{R}$, while ETH lost $-0.61\text{R}$.

---

### C. Aggregation by Calendar Year

| Year | Market Context | Candles | Executed Trades | Win Rate | Realized Net R | Expectancy | Profit Factor | Top Trade |
| :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| **2021** | Bull Market Expansion & High Volatility | 138,954 | **3** | 66.7% (2W / 1L) | **+2.1975R** | +0.7325R | **4.20** | SOL Trade #3 (+2.80R) |
| **2022** | Bear Market Grind & Deleveraging | 138,954 | **8** | 37.5% (3W / 5L) | **-0.7830R** | -0.0979R | 0.70 | BTC Trade #5 (+1.69R) |

#### Analysis:
- In 2021, the strategy executed only 3 trades, but capitalized heavily on upward and downward expansion trends ($+2.20\text{R}$).
- In 2022, trade count increased to 8, but choppy compression resulted in a slight loss ($-0.78\text{R}$).

---

## 3. Opportunity Frequency & Commercial Velocity Metrics

| Metric | Whole Portfolio (3 Assets) | Per Asset (Average) | Per Active Stream (SET 4) |
| :--- | :---: | :---: | :---: |
| **Annualized Trade Frequency** | **$5.50$ trades / year** | $1.83$ trades / year | $3.00$ trades / year |
| **Monthly Trade Frequency** | **$0.458$ trades / month** | $0.153$ trades / month | $0.250$ trades / month |
| **Candles per Executed Trade** | **$25,264$ candles / trade** | $50,528$ candles / trade | $23,338$ candles / trade |
| **Trade Yield per 1,000 Candles**| **$0.0396$ trades / 1k bars** | $0.0198$ trades / 1k bars | $0.0428$ trades / 1k bars |
| **Candidate-to-Trade Conversion**| **$0.75\%$** ($11 / 1,462$) | $0.75\%$ | $0.86\%$ ($9 / 1,050$) |
| **LTF-to-Trade Conversion** | **$2.81\%$** ($11 / 391$) | $2.81\%$ | $3.11\%$ ($9 / 289$) |

---

## 4. Full Funnel Drop-off Attribution

Tracing every step of the funnel across the 2-year Development dataset:

```text
1,462 CANDIDATES SPAWNED
  │
  ├── 251 dropped: MTF structural alignment failed (17.17%)
  ▼
1,211 MTF ALIGNED
  │
  ├── 426 dropped: Price never retested causal MTF KeyZone (35.18%)
  ▼
  785 ACTIVE MTF RETESTS
  │
  ├── 394 dropped: LTF sweep + displacement polarity failed (50.19%)
  ▼
  391 LTF CONFIRMED OPPORTUNITIES
  │
  ├── 4 dropped: Missing structural anchors / target unresolvable (1.02%)
  ▼
  387 TARGET RESOLVED
  │
  ├── 364 ANNIHILATED: Planned RR < 4.0R Firewall (94.06% of resolved)
  ├──   5 dropped: Superseded by fresher HTF context (1.29%)
  ├──   5 dropped: Invalid anchor geometry (1.29%)
  ├──   2 dropped: Opposing MTF structure conflict (0.52%)
  ▼
   11 EXECUTED TRADES (2.81% of LTF confirmed)
```

---

## 5. Planned RR Distribution & Geometric Chokepoint Analysis

For the 387 candidates reaching the Risk Gate with a valid target price:

### Statistical Distribution:
- **Mean Planned RR:** $0.80\text{R}$
- **Median Planned RR:** **$0.47\text{R}$**
- **25th Percentile (P25):** $0.20\text{R}$
- **75th Percentile (P75):** $0.97\text{R}$
- **90th Percentile (P90):** $1.69\text{R}$
- **Max Planned RR:** $7.28\text{R}$

### Planned RR Histogram:

```text
┌──────────────────┬───────┬─────────┬────────────────────────────────────────┐
│ Planned RR Range │ Count │ Percent │ Visual Histogram                       │
├──────────────────┼───────┼─────────┼────────────────────────────────────────┤
│ < 0.5R           │   204 │  52.71% │ █████████████████████████████████████▌ │
│ 0.5R – 1.0R      │    92 │  23.77% │ ███████████████▌                       │
│ 1.0R – 1.5R      │    43 │  11.11% │ ███████                                │
│ 1.5R – 2.0R      │    17 │   4.39% │ ███                                    │
│ 2.0R – 2.5R      │     9 │   2.33% │ █▌                                     │
│ 2.5R – 3.0R      │     6 │   1.55% │ █                                      │
│ 3.0R – 3.5R      │     3 │   0.78% │ ▌                                      │
│ 3.5R – 4.0R      │     2 │   0.52% │ ▎                                      │
│ >= 4.0R          │    11 │   2.84% │ █                                      │
└──────────────────┴───────┴─────────┴────────────────────────────────────────┘
```

### Target Provenance Breakdown:
- **Weak Swings:** 125 candidates ($32.0\%$)
- **Opposing KeyZones:** 106 candidates ($27.1\%$)
- **Forward Structural Expansion:** 77 candidates ($19.7\%$)
- **Liquidity Pools:** 76 candidates ($19.4\%$)
- **None:** 7 candidates ($1.8\%$)

---

## 6. Dissecting the Bottleneck: Why Are There Only 11 Trades?

The empirical data provides a definitive answer to the user's question:

### Is the strategy naturally selective, or is target selection suppressing opportunities?

1. **The Strategy Pipeline Is NOT Overly Selective Upstream:**
   - The strategy generated **1,462 candidates** ($5.26$ per 1k bars).
   - It identified **391 verified structural entries** with confirmed LTF sweep and directional displacement.
   - That represents roughly **16 LTF triggers per month** across the portfolio.
2. **The Bottleneck Is 100% Concentrated at Target Resolution & Planned RR:**
   - **$93.09\%$ of all LTF confirmed setups were killed by `REJECT_RR_BELOW_4R`**.
   - $76.5\%$ of confirmed setups were assigned target prices with planned $\text{RR} < 1.0\text{R}$.
   - The median target distance was only **$0.47\text{R}$**!

### Why Are the Targets So Close?
The destination engine was hardcoded to sort candidates by **closest distance to entry**:
```python
candidates.sort(key=lambda x: x[0])  # Closest target to entry
```
Because the engine treats minor internal KeyZones and local micro-swings as valid HTF destinations, it systematically anchors planned targets to the nearest micro-zone sitting just 0.3R to 0.8R away from entry, rather than identifying true macro swing destinations. This artificially forces planned RR into the $0.2\text{R}$ to $0.8\text{R}$ bracket, where the 4R firewall rightfully rejects them.

---

## 7. SET 5 Disambiguation & Fail-Closed Status

- **Configuration:** `SET_5_SCALPING` is fully registered across `config/timeframe_sets.py` and `timeframe_aligner.py` (`15M -> 5M -> 1m`).
- **Data Availability:** Public Binance API historical depth for 1m and 5m candles only extends back to 2026 in the local cache.
- **Fail-Closed Verification:** Replaying SET 5 on 2021–2022 raises `INSUFFICIENT_HISTORICAL_DEPTH_FAIL_CLOSED` and produces exactly 0 trades.
- **Integrity Rule:** The platform strictly refused to fabricate synthetic 1m/5m data or contaminate Development with post-2023 data.

---

## 8. Summary Table: Where Did the 11 Trades Come From?

```
┌──────────────────────────────────────────────────────────────────────────────────┐
│                      FINAL BASELINE DISTRIBUTION (11 TRADES)                     │
├──────────────┬──────────────┬──────────────┬──────────────────┬──────────────────┤
│ Stream       │ Trades Count │ Win / Loss   │ Realized Net R   │ Dominant Exit    │
├──────────────┼──────────────┼──────────────┼──────────────────┼──────────────────┤
│ ETH_SET_2    │ 2 trades     │ 1W / 1L      │ -0.6674R         │ MTF Trail / BE   │
│ BTC_SET_4    │ 4 trades     │ 1W / 3L      │ +0.2008R         │ MTF Trail        │
│ ETH_SET_4    │ 1 trade      │ 1W / 0L      │ +0.0585R         │ MTF Trail        │
│ SOL_SET_4    │ 4 trades     │ 2W / 2L      │ +1.8226R         │ MTF Trail        │
│ All Others   │ 0 trades     │ —            │ +0.0000R         │ Zero RR >= 4R    │
├──────────────┼──────────────┼──────────────┼──────────────────┼──────────────────┤
│ TOTAL        │ 11 trades    │ 5W / 6L      │ +1.4145R         │ 100% Monetized   │
│              │              │              │                  │ via MTF Trailing │
└──────────────┴──────────────┴──────────────┴──────────────────┴──────────────────┘
```

---

## Master Architectural Conclusions for Day 41

1. **The Strategy Pipeline is Functionally Sound Upstream:**
   Market structure, HTF keyzones, MTF realignment, MTF retest, and LTF entry displacement generate plenty of structural candidates ($391$ confirmed opportunities). The system is not suffering from an upstream signal failure.
2. **The 4R Firewall is Working Correctly:**
   The firewall prevents the execution of trades with planned $\text{RR} < 4.0\text{R}$. Given that $76.5\%$ of generated candidates had planned $\text{RR} < 1.0\text{R}$, the firewall is protecting the portfolio from low-reward setups.
3. **The Target Selection Engine is the Structural Chokepoint:**
   The destination engine's policy of sorting candidates by closest proximity causes it to pick micro internal keyzones sitting adjacent to price. This collapses the planned RR geometry ($52.7\%$ are $<0.5\text{R}$) and starves the platform of trade executions across SET 1, SET 2, and SET 3.
4. **Current Status:**
   We have established a complete, transparent, and certified baseline. **Day 41 remains strictly open.**

---
*Report certified under Day 41 Quantitative Governance.*
