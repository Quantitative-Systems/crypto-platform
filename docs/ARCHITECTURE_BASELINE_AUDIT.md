# Quantitative Architecture Baseline & Trade Frequency Audit

---

**Document Identifier:** `ARCHITECTURE_BASELINE_AUDIT`  
**Classification:** Institutional Quantitative Research  
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
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
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

## 3. Aggregation by Asset Universe

| Asset | Candidates | LTF Confirmed | Planned RR $\ge$ 4R | Executed Trades | Win Rate | Realized Net R | Expectancy | Profit Factor |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **BTC/USDT** | 475 | 135 | 4 | **4** | 25.0% | +0.2008R | +0.0502R | 1.13 |
| **ETH/USDT** | 482 | 116 | 3 | **3** | 66.7% | -0.6089R | -0.2030R | 0.15 |
| **SOL/USDT** | 505 | 140 | 4 | **4** | 50.0% | **+1.8226R** | +0.4557R | **2.72** |

#### Analysis:
- **Balanced Candidate Generation:** Candidates are evenly split across the universe (SOL $34.5\%$, ETH $33.0\%$, BTC $32.5\%$).
- **Profit Concentration in Solana:** SOL generated $+1.8226\text{R}$ ($PF = 2.72$) led by the $+2.80\text{R}$ trend-runner on SET 4. BTC contributed $+0.20\text{R}$, while ETH lost $-0.61\text{R}$.

---

## 4. Aggregation by Calendar Year

| Year | Market Context | Candles | Executed Trades | Win Rate | Realized Net R | Expectancy | Profit Factor | Top Trade |
| :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| **2021** | Bull Market Expansion & High Volatility | 138,954 | **3** | 66.7% (2W / 1L) | **+2.1975R** | +0.7325R | **4.20** | SOL Trade #3 (+2.80R) |
| **2022** | Bear Market Grind & Deleveraging | 138,954 | **8** | 37.5% (3W / 5L) | **-0.7830R** | -0.0979R | 0.70 | BTC Trade #5 (+1.69R) |

---

## 5. Opportunity Frequency & Commercial Velocity Metrics

| Metric | Whole Portfolio (3 Assets) | Per Asset (Average) | Per Active Stream (SET 4) |
| :--- | :---: | :---: | :---: |
| **Annualized Trade Frequency** | **$5.50$ trades / year** | $1.83$ trades / year | $3.00$ trades / year |
| **Monthly Trade Frequency** | **$0.458$ trades / month** | $0.153$ trades / month | $0.250$ trades / month |
| **Candles per Executed Trade** | **$25,264$ candles / trade** | $50,528$ candles / trade | $23,338$ candles / trade |
| **Trade Yield per 1,000 Candles**| **$0.0396$ trades / 1k bars** | $0.0198$ trades / 1k bars | $0.0428$ trades / 1k bars |
| **Candidate-to-Trade Conversion**| **$0.75\%$** ($11 / 1,462$) | $0.75\%$ | $0.86\%$ ($9 / 1,050$) |
| **LTF-to-Trade Conversion** | **$2.81\%$** ($11 / 391$) | $2.81\%$ | $3.11\%$ ($9 / 289$) |

---

## 6. Full Funnel Drop-off Attribution

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

## 7. Master Architectural Conclusions

1. **The Strategy Pipeline is Functionally Sound Upstream:**
   Market structure, HTF keyzones, MTF realignment, MTF retest, and LTF entry displacement generate plenty of structural candidates ($391$ confirmed opportunities). The system is not suffering from an upstream signal failure.
2. **The 4R Firewall is Working Correctly:**
   The firewall prevents the execution of trades with planned $\text{RR} < 4.0\text{R}$. Given that $76.5\%$ of generated candidates had planned $\text{RR} < 1.0\text{R}$, the firewall is protecting the portfolio from low-reward setups.
3. **The Target Selection Engine is the Structural Chokepoint:**
   The destination engine's policy of sorting candidates by closest proximity causes it to pick micro internal keyzones sitting adjacent to price. This collapses the planned RR geometry ($52.7\%$ are $<0.5\text{R}$) and starves the platform of trade executions across SET 1, SET 2, and SET 3.
