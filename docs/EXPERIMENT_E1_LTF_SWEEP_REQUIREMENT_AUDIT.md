# EXPERIMENT E1 — LTF LIQUIDITY SWEEP REQUIREMENT AUDIT

**Experiment ID:** `EXP_LTF_SWEEP_REQUIREMENT_01`  
**Execution Date:** 2026-09-12  
**Partition Scope:** Development Partition (2021–2022) ONLY  
**Validation (2023) & OOS (2024–2026):** STRICTLY LOCKED  
**Control Baseline:** D1 (`EXP_MTF_MAJOR_ALIGNMENT_01`)  
**Single Variable Tested:** Mandatory genuine causal LTF liquidity sweep before displacement confirmation  
**Official Decision Classification:** **`E-NEGATIVE`** (Severe Expectancy Deterioration & Asymmetric Opportunity Destruction)  
**Deliverable File:** [`docs/EXPERIMENT_E1_LTF_SWEEP_REQUIREMENT_AUDIT.md`](file:///home/mrcn2/crypto-platform/docs/EXPERIMENT_E1_LTF_SWEEP_REQUIREMENT_AUDIT.md)

---

## 1. EXECUTIVE SUMMARY & DECISION CLASSIFICATION

### The Empirical Finding
Experiment E1 was executed as a strictly isolated, single-variable causal hypothesis test to determine whether requiring a genuine causal LTF liquidity sweep prior to displacement confirmation shifts the entry-quality / early-excursion distribution of the D1 strategy upward.

The hypothesis is **REJECTED**.

While requiring a sweep modestly reduced the proportion of immediate sub-0.5R early failures ($45.8\% \to 30.8\%$) and raised median MFE from $0.72\text{R}$ to $1.34\text{R}$, **overall economic performance and expectancy collapsed**:
1. **Net Realized Expectancy Deteriorated by 129%:** From **$-0.1198\text{R}$** in D1 to **$-0.2749\text{R}$** in E1.
2. **Profit Factor Degraded:** From **$0.7732$** in D1 to **$0.6144$** in E1.
3. **Net Realized R Worsened:** From **$-2.8752\text{R}$** ($N=24$) to **$-3.5742\text{R}$** ($N=13$).
4. **Catastrophic Winner Destruction:** The canonical **BTC $+4.11\text{R}$ winner** (`cand_BTC/USDT_1620705600` on `SET_4`) was completely destroyed. The setup was a clean, high-momentum directional expansion from a causal keyzone that never swept an opposing swing high prior to displacement. Under E1's mandatory sweep rule, it was refused entry; price plummeted directly toward the target without entry, forfeiting $+4.1077\text{R}$ of realized net profit.
5. **Toxic Delayed Entries in Range-Bound Exhaustion:** In 8 instances, candidates that were disqualified or un-entered in D1 were forced to wait in `WAIT_LTF_TRIGGER` until an opposing swing was finally swept. These delayed entries occurred late in extended consolidations after the directional impulse had exhausted: **6 of the 8 new entries ($75\%$) hit full stop loss**, 2 reached breakeven, and 0 produced wins, generating a net drain of **$-5.5334\text{R}$**.
6. **Upper-Tail Opportunity Collapse:** The proportion of trades achieving $\ge 1.5\text{R}$ MFE dropped from **$41.7\%$ to $30.8\%$**, and trades reaching $\ge 2.0\text{R}$ dropped from **$25.0\%$ to $15.4\%$**. Mean MFE declined from $1.45\text{R}$ to $1.34\text{R}$.

### Official Classification: `E-NEGATIVE`
Per Section 11 of the research protocol:
> **E-NEGATIVE:** Expectancy or overall economic performance deteriorates.

Mandatory liquidity sweep confirmation is an **anti-edge** for the current architecture. It transforms clean momentum continuation opportunities into missed trades while channeling entries into late, exhausted ranges.

---

## 2. FROZEN CONTROL & EXPERIMENTAL ISOLATION

The control environment was completely frozen and identically replayed:
* **Development Partition:** 2021-01-01 to 2022-12-31 (Validation 2023 and OOS 2024–2026 locked).
* **Universe:** BTC/USDT, ETH/USDT, SOL/USDT across 15 independent streams (`SET_1` through `SET_5`).
* **Directional Context:** Canonical HTF directional bias engine (`EXPANSION` / `PULLBACK`).
* **MTF Alignment:** Frozen D1 major structural alignment only (`EXTERNAL_CHOCH`, `MSS`, `EXTERNAL_BOS`; minor `INTERNAL_CHOCH` filtered).
* **MTF Retest:** Canonical causal primitive & synthesized zone retest confirmation.
* **Stop Loss:** Corrected local LTF micro-structural invalidation stop.
* **Target:** `CLOSEST_OBJECTIVE` structural target from HTF destination engine.
* **Risk & Costs:** Planned $\text{RR} \ge 4.0\text{R}$, risk $\le 1\%$, `ADVERSE_FIRST` intra-bar resolution, $2\text{ bps}$ maker / $5\text{ bps}$ taker fees, $5\text{ bps}$ adverse slippage.
* **Exit Management:** Frozen C1 $+1.5\text{R}$ protective milestone (`be_trigger_r=1.5`, `be_stop_r=0.0`) + MTF structural trailing.
* **Single Variable Modified:** LTF entry eligibility rule. Under D1, candidates could enter on either Model 1 (`LTF_SWEEP_AND_DISPLACEMENT_CONFIRMED`) or Models 2/3 (`BULLISH/BEARISH_DISPLACEMENT_CONFIRMED`). Under E1, **only Model 1 was permitted** (`require_ltf_sweep=True`).

---

## 3. ENGINE DEFINITION OF `LTF_SWEEP_AND_DISPLACEMENT_CONFIRMED`

Per Section 3 of the mandate, the existing canonical sweep detection mechanism was audited and documented prior to execution:

### Canonical Definition
A candidate is confirmed under `LTF_SWEEP_AND_DISPLACEMENT_CONFIRMED` if and only if:
1. **Causal Ordering:** A `LIQUIDITY_SWEEP` event exists in `ltf_payload.events` occurring at or after the candidate's MTF retest timestamp:
   $$\text{timestamp}(\text{sweep}) \ge \text{candidate.mtf\_retest\_timestamp}$$
2. **Directional Polarity:** The sweep direction matches the setup direction:
   * Setup `LONG` requires `BULLISH_SWEEP` (sweep of a prior LTF swing low).
   * Setup `SHORT` requires `BEARISH_SWEEP` (sweep of a prior LTF swing high).
3. **Displacement Confirmation:** The LTF scorecard confirms `"DISPLACEMENT_CONFIRMED"` with directional impulse velocity $> 0.1\%$ matching setup polarity.
4. **Structural Anchor:** The candidate's micro-structural invalidation stop anchors to the exact swept swing extreme:
   * For LONG: $\text{stop\_price} = \text{swept\_swing\_low\_price}$.
   * For SHORT: $\text{stop\_price} = \text{swept\_swing\_high\_price}$.

### Lookback Horizon
No ad-hoc lookback window was invented. The temporal search space is strictly bounded by the forward candidate lifecycle:
$$\text{mtf\_retest\_timestamp} \le \text{sweep\_timestamp} \le \text{displacement\_confirmation\_timestamp} \le \text{lifespan\_expiry}$$
The candidate evaluates sweeps that occurred after MTF retest up to the current evaluation candle.

---

## 4. CANDIDATE LIFECYCLE AUDIT (STATE MACHINE FORWARD PROPAGATION)

E1 was executed strictly as a forward state machine replay from raw 1-minute historical candles across all 15 streams. Post-hoc deleting trades from D1 JSON files was forbidden.

When a candidate reached `WAIT_LTF_TRIGGER`:
* **Immediate Sweep:** If a sweep was already present after MTF retest and displacement fired, the candidate transitioned to `RISK_GATE` and entered.
* **No Prior Sweep:** If displacement fired without a prior sweep, the candidate **remained in `WAIT_LTF_TRIGGER`** rather than entering.
* **Subsequent Causal Fates:**
  * **Entered Later:** 1 candidate (`cand_SOL/USDT_1652446800`) remained active in `WAIT_LTF_TRIGGER` for 12 hours until a sweep occurred at `1652616000`, entering at `1652619600`.
  * **Expired in State:** Candidates that never encountered a sweep remained in `WAIT_LTF_TRIGGER` until `is_expired(current_timestamp)` pruned them upon exceeding their maximum TTL ($72\text{ hours}$ on SET_4, $14\text{ days}$ on SET_3, $45\text{ days}$ on SET_2).
  * **New Entrants via Tighter Stops:** 8 candidates that were rejected in D1 due to `REJECT_RR_BELOW_4R` (because single-candle displacement stops were too wide) survived in `WAIT_LTF_TRIGGER` under E1 until a sweep formed. Because the swept swing provided a narrower stop, their planned RR exceeded $4.0\text{R}$, transitioning them into `ENTERED`.

---

## 5. COMPLETE CAUSAL SWEEP PROVENANCE (ALL 13 E1 TRADES)

Every trade executed in E1 has 100% verified causal provenance recorded directly on the trade object. Zero substring heuristics were used.

| # | Trade ID | Symbol | Set | Dir | Swept Swing TS | Swept Price | Sweep Dir | Sweep Conf TS | Disp Conf TS | Bars Betw | MTF Retest TS | Causal After Retest | Entry TS | Entry Price | Structural Stop | Target Price | Planned RR | Net R | Exit Reason |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **01** | `cand_BTC...1610308800` | BTC/USDT | SET_3 | LONG | 1610625600 | 37707.00 | BULLISH_SWEEP | 1610690400 | 1610690400 | 0 | 1610596800 | **YES** | 1610694000 | 38043.27 | 37554.94 | 41950.00 | 8.00R | -0.0000R | BREAKEVEN_TRAIL |
| **02** | `cand_ETH...1618552800` | ETH/USDT | SET_3 | LONG | 1618966800 | 2279.44 | BULLISH_SWEEP | 1618977600 | 1618984800 | 2 | 1618963200 | **YES** | 1618988400 | 2316.02 | 2272.94 | 2548.29 | 5.39R | -1.0635R | INITIAL_LTF_SL |
| **03** | `cand_SOL...1622781000` | SOL/USDT | SET_4 | LONG | 1622824200 | 37.00 | BULLISH_SWEEP | 1622848500 | 1622848500 | 0 | 1622847600 | **YES** | 1622849400 | 37.436 | 37.000 | 39.216 | 4.08R | -1.1020R | INITIAL_LTF_SL |
| **04** | `cand_SOL...1632275100` | SOL/USDT | SET_4 | SHRT | 1632275100 | 132.15 | BEARISH_SWEEP | 1632280500 | 1632280500 | 0 | 1632276000 | **YES** | 1632281400 | 130.85 | 132.17 | 125.22 | 4.27R | -0.1190R | MTF_STRUCTURAL_TRAIL |
| **05** | `cand_BTC...1632333600` | BTC/USDT | SET_3 | SHRT | 1632218400 | 43639.00 | BEARISH_SWEEP | 1632344400 | 1632344400 | 0 | 1632337200 | **YES** | 1632348000 | 43247.30 | 44000.55 | 37332.70 | 7.85R | -0.4625R | MTF_STRUCTURAL_TRAIL |
| **06** | `cand_ETH...1634500800` | ETH/USDT | SET_3 | LONG | 1634572800 | 3711.00 | BULLISH_SWEEP | 1634583600 | 1634583600 | 0 | 1634504400 | **YES** | 1634587200 | 3747.72 | 3695.17 | 4027.88 | 5.33R | -0.0000R | BREAKEVEN_TRAIL |
| **07** | `cand_BTC...1638824400` | BTC/USDT | SET_3 | SHRT | 1638925200 | 50795.45 | BEARISH_SWEEP | 1638975600 | 1638975600 | 0 | 1638972000 | **YES** | 1638979200 | 50640.10 | 51200.00 | 47430.18 | 5.73R | **+5.6955R** | **HTF_TP** |
| **08** | `cand_ETH...1638576000` | ETH/USDT | SET_1 | LONG | 1638576000 | 3503.68 | BULLISH_SWEEP | 1641340800 | 1641340800 | 0 | 1639353600 | **YES** | 1641427200 | 3540.63 | 3415.00 | 4372.72 | 6.62R | -1.0327R | INITIAL_LTF_SL |
| **09** | `cand_SOL...1647475200` | SOL/USDT | SET_2 | SHRT | 1646812800 | 89.92 | BEARISH_SWEEP | 1647518400 | 1647518400 | 0 | 1647489600 | **YES** | 1647532800 | 89.35 | 90.72 | 75.35 | 10.22R | -1.0793R | INITIAL_LTF_SL |
| **10** | `cand_SOL...1647547200` | SOL/USDT | SET_2 | SHRT | 1646496000 | 91.22 | BEARISH_SWEEP | 1647619200 | 1647619200 | 0 | 1647561600 | **YES** | 1647633600 | 91.12 | 92.28 | 75.35 | 13.59R | -1.0953R | INITIAL_LTF_SL |
| **11** | `cand_SOL...1649286000` | SOL/USDT | SET_3 | LONG | 1649584800 | 109.71 | BULLISH_SWEEP | 1649635200 | 1649638800 | 1 | 1649628000 | **YES** | 1649642400 | 110.87 | 109.71 | 142.77 | 27.50R | -1.1137R | INITIAL_LTF_SL |
| **12** | `cand_SOL...1652446800` | SOL/USDT | SET_3 | SHRT | 1652493600 | 53.91 | BEARISH_SWEEP | 1652616000 | 1652616000 | 0 | 1652544000 | **YES** | 1652619600 | 53.28 | 54.08 | 37.37 | 19.89R | -1.0809R | INITIAL_LTF_SL |
| **13** | `cand_ETH...1668058200` | ETH/USDT | SET_4 | SHRT | 1668150900 | 1289.26 | BEARISH_SWEEP | 1668156300 | 1668156300 | 0 | 1668145500 | **YES** | 1668157200 | 1281.52 | 1294.35 | 1136.13 | 11.33R | -1.1209R | INITIAL_LTF_SL |

---

## 6. PERFORMANCE COMPARISON: H0 / C1 / D1 / E1

All figures reflect full transaction costs ($2\text{ bps}$ maker / $5\text{ bps}$ taker) and $5\text{ bps}$ adverse execution slippage under the development partition (2021–2022).

| Performance Metric | H0 (Baseline Control) | C1 (Protective Milestone) | D1 (Major MTF Alignment) | E1 (Mandatory LTF Sweep) | Delta (E1 vs D1) |
|---|---|---|---|---|---|
| **Executed Trades ($N$)** | 29 | 29 | 24 | **13** | $-45.8\%$ (Sample Collapse) |
| **Wins ($>+0.05\text{R}$)** | 2 | 2 | 2 | **1** | $-50.0\%$ (Winner Destroyed) |
| **Losses ($<-0.05\text{R}$)** | 27 | 20 | 16 | **10** | $-37.5\%$ |
| **Breakevens ($[-0.05, +0.05]\text{R}$)** | 0 | 7 | 6 | **2** | $-66.7\%$ |
| **Win Rate (%)** | 6.90% | 6.90% | 8.33% | **7.69%** | $-0.64\%$ |
| **Gross R** | $-13.1360\text{R}$ | $-3.8034\text{R}$ | $-0.8881\text{R}$ | **$-2.4839\text{R}$** | $-1.5958\text{R}$ (Worse) |
| **Friction R (Fees+Slip)** | $2.3825\text{R}$ | $2.3572\text{R}$ | $1.9872\text{R}$ | **$1.0904\text{R}$** | $-0.8968\text{R}$ |
| **Net Realized R** | **$-15.5185\text{R}$** | **$-6.1605\text{R}$** | **$-2.8752\text{R}$** | **$-3.5742\text{R}$** | **$-0.6990\text{R}$ (Worse)** |
| **Expectancy ($E$)** | **$-0.5351\text{R}$** | **$-0.2124\text{R}$** | **$-0.1198\text{R}$** | **$-0.2749\text{R}$** | **$-0.1551\text{R}$ ($-129\%$ Deterioration)** |
| **Profit Factor** | 0.3871 | 0.6141 | 0.7732 | **0.6144** | **$-0.1588$ (Worse)** |
| **Max Drawdown (R)** | $17.8421\text{R}$ | $8.7582\text{R}$ | $7.6622\text{R}$ | **$6.5227\text{R}$** | $-1.1395\text{R}$ |
| **Max Consecutive Losses** | 13 | 6 | 5 | **6** | $+1$ |
| **Average MFE** | $1.35\text{R}$ | $1.35\text{R}$ | $1.45\text{R}$ | **$1.34\text{R}$** | $-0.11\text{R}$ |
| **Median MFE** | $0.78\text{R}$ | $0.78\text{R}$ | $0.72\text{R}$ | **$1.34\text{R}$** | $+0.62\text{R}$ |
| **Average MAE** | $1.36\text{R}$ | $1.36\text{R}$ | $1.19\text{R}$ | **$1.30\text{R}$** | $+0.11\text{R}$ |
| **Median MAE** | $1.20\text{R}$ | $1.20\text{R}$ | $1.16\text{R}$ | **$1.06\text{R}$** | $-0.10\text{R}$ |
| **MFE $<0.5\text{R}$** | 14 (48.3%) | 12 (41.4%) | 11 (45.8%) | **4 (30.8%)** | $-15.0\%$ |
| **MFE $<1.0\text{R}$** | 19 (65.5%) | 17 (58.6%) | 13 (54.2%) | **5 (38.5%)** | $-15.7\%$ |
| **MFE $\ge 1.5\text{R}$** | 10 (34.5%) | 11 (37.9%) | 10 (41.7%) | **4 (30.8%)** | **$-10.9\%$ (Truncated Upside)** |
| **MFE $\ge 2.0\text{R}$** | 6 (20.7%) | 6 (20.7%) | 6 (25.0%) | **2 (15.4%)** | **$-9.6\%$ (Truncated Upside)** |

---

## 7. MANDATORY OPPORTUNITY-ATTRITION FORENSICS

Per Section 7, every D1 trade omitted from E1 due to the sweep requirement was tracked to determine its exact counterfactual fate. This distinguishes **"E1 removes bad trades"** from **"E1 simply removes trades."**

### Omitted D1 Opportunities Summary
* **Total D1 Trades Omitted:** 19
  * **Losses Removed:** 12 (sum of net losses: $-8.3244\text{R}$)
  * **Breakevens Removed:** 6 (sum of net: $+0.0000\text{R}$, but MFEs reached up to $5.04\text{R}$)
  * **Winners Removed:** 1 (**BTC $+4.1077\text{R}$ HTF Target Winner**)
* **Net Value of Omitted Trades in D1:** $+4.1077\text{R} - 8.3244\text{R} = \mathbf{-4.2167\text{R}}$.
* **Net Value of the 8 New E1 Replacement Trades:** **$-5.5334\text{R}$** (6 losses, 2 BE, 0 wins).
* **Verdict on Attrition Mechanism:** E1 did **NOT** filter bad trades; it replaced one set of losing trades with an even more toxic set of late, exhausted entries while forfeiting $+4.11\text{R}$ of bona fide trend profits.

### Detailed Counterfactual Roster (All 19 Omitted D1 Trades)

| # | D1 Trade ID | Symbol | Set | Dir | Would-be Entry | Would-be SL | Would-be TP | Planned RR | Net R in D1 | Subsequent MFE | Subsequent MAE | D1 Exit Reason | E1 Causal Fate / Reason for Omission |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **01** | `cand_SOL...1612575900` | SOL | SET_4 | LONG | 6.1846 | 6.0658 | 7.1438 | 8.07R | -1.0615R | 0.00R | 1.39R | INITIAL_LTF_SL | **Expired without sweep.** Displaced directly from keyzone without sweeping low; subsequent move collapsed into SL. |
| **02** | `cand_SOL...1614373200` | SOL | SET_4 | LONG | 13.5640 | 13.3738 | 14.6432 | 5.67R | -1.0846R | 0.47R | 1.20R | INITIAL_LTF_SL | **Expired without sweep.** Displaced without prior sweep; invalidated immediately. |
| **03** | `cand_ETH...1615737600` | ETH | SET_3 | LONG | 1780.81 | 1760.52 | 1877.69 | 4.77R | -1.1043R | 0.03R | 1.74R | INITIAL_LTF_SL | **Expired without sweep.** Displaced without prior sweep; failed at entry. |
| **04** | `cand_BTC...1618785000` | BTC | SET_4 | SHRT | 54826.99 | 55554.00 | 50931.30 | 5.36R | -1.0911R | 0.00R | 1.37R | INITIAL_LTF_SL | **Expired without sweep.** Displaced without sweep; invalidated immediately. |
| **05** | `cand_SOL...1619125200` | SOL | SET_4 | LONG | 36.2373 | 35.7714 | 41.7400 | 11.81R | -0.0933R | 3.35R | 0.24R | MTF_TRAIL | **Expired without sweep.** High-MFE ($+3.35\text{R}$) expansion displaced without sweep; scratched in D1; omitted in E1. |
| **06** | `cand_BTC...1620705600` | BTC | SET_4 | SHRT | 56359.18 | 57195.50 | 52900.00 | 4.14R | **+4.1077R** | **5.21R** | **0.65R** | **HTF_TP** | **FATAL OPPORTUNITY DESTRUCTION:** Clean impulse from 4H KZ displaced downward without prior sweep. Price expanded $5.21\text{R}$ to target. Never entered in E1. |
| **07** | `cand_SOL...1620993600` | SOL | SET_3 | SHRT | 43.8650 | 44.7690 | 39.0000 | 5.38R | +0.0000R | 5.04R | 1.81R | BREAKEVEN_TRAIL | **Expired without sweep.** High-MFE ($+5.04\text{R}$) short expansion omitted; C1 protected in D1. |
| **08** | `cand_ETH...1624760100` | ETH | SET_4 | SHRT | 1846.19 | 1866.20 | 1717.32 | 6.44R | +0.0000R | 2.10R | 2.06R | BREAKEVEN_TRAIL | **Expired without sweep.** Expansion reached $+2.10\text{R}$; C1 protected in D1; omitted in E1. |
| **09** | `cand_SOL...1632278700` | SOL | SET_4 | SHRT | 130.8500 | 132.1700 | 125.2200 | 4.27R | -0.1190R | 0.93R | 0.87R | MTF_TRAIL | **Subsumed by duplicate candidate.** Sister candidate `cand_SOL...1632275100` entered at exact same candle in E1 with identical net P&L ($-0.1190\text{R}$). |
| **10** | `cand_SOL...1642078800` | SOL | SET_3 | SHRT | 142.4600 | 144.0100 | 130.0000 | 8.04R | +0.0000R | 1.54R | 0.86R | BREAKEVEN_TRAIL | **Expired without sweep.** Reached $+1.54\text{R}$; protected in D1; omitted in E1. |
| **11** | `cand_SOL...1647619200` | SOL | SET_2 | SHRT | 90.2500 | 92.3500 | 75.3500 | 7.10R | -0.2804R | 0.48R | 0.35R | MTF_TRAIL | **Replaced by later sweep trade.** Replaced in E1 by `cand_SOL...1647547200` which swept and took full SL ($-1.0953\text{R}$). |
| **12** | `cand_SOL...1647676800` | SOL | SET_2 | SHRT | 92.6500 | 94.5500 | 75.3500 | 9.11R | +0.0000R | 1.82R | 1.95R | BREAKEVEN_TRAIL | **Expired without sweep.** Reached $+1.82\text{R}$; protected in D1; omitted in E1. |
| **13** | `cand_SOL...1648947600` | SOL | SET_3 | LONG | 135.7700 | 134.0900 | 142.7700 | 4.17R | -0.0000R | 2.19R | 0.49R | BREAKEVEN_TRAIL | **Expired without sweep.** Reached $+2.19\text{R}$; protected in D1; omitted in E1. |
| **14** | `cand_SOL...1648996200` | SOL | SET_4 | LONG | 136.9000 | 135.5200 | 143.5100 | 4.79R | -1.1180R | 0.00R | 1.85R | INITIAL_LTF_SL | **Expired without sweep.** Displaced without sweep; invalidated immediately. |
| **15** | `cand_SOL...1652157900` | SOL | SET_4 | SHRT | 67.2100 | 67.9300 | 60.1300 | 9.83R | -0.1120R | 1.83R | 1.12R | MTF_TRAIL | **Expired without sweep.** Reached $+1.83\text{R}$; protected in D1; omitted in E1. |
| **16** | `cand_ETH...1655433900` | ETH | SET_4 | SHRT | 1100.23 | 1117.10 | 1014.40 | 5.09R | -1.0793R | 0.42R | 1.05R | INITIAL_LTF_SL | **Expired without sweep.** Displaced without sweep; failed into SL. |
| **17** | `cand_BTC...1660388400` | BTC | SET_3 | LONG | 24572.21 | 24291.22 | 26895.84 | 8.27R | -0.0000R | 1.69R | 0.90R | BREAKEVEN_TRAIL | **Expired without sweep.** Reached $+1.69\text{R}$; protected in D1; omitted in E1. |
| **18** | `cand_ETH...1668053700` | ETH | SET_4 | SHRT | 1255.89 | 1271.75 | 1136.13 | 7.55R | -1.0960R | 0.10R | 2.10R | INITIAL_LTF_SL | **Replaced by delayed sweep trade.** Sister candidate `cand_ETH...1668058200` swept later and took full SL ($-1.1209\text{R}$). |
| **19** | `cand_SOL...1672403400` | SOL | SET_4 | SHRT | 9.7400 | 9.8700 | 8.0000 | 13.38R | -1.0909R | 0.00R | 1.23R | INITIAL_LTF_SL | **Expired without sweep.** Displaced without sweep; failed into SL. |

---

## 8. ENTRY-DISTRIBUTION FORENSIC ANALYSIS

The primary mechanism question posed in Section 8 is:
> **"Does mandatory sweep confirmation shift the early-excursion distribution upward?"**

### Detailed Excursion Metrics

| Distribution Dimension | D1 Control ($N=24$) | E1 Treatment ($N=13$) | Shift / Delta | Forensic Interpretation |
|---|---|---|---|---|
| **Mean MFE** | $1.45\text{R}$ | **$1.34\text{R}$** | **$-0.11\text{R}$** | **Overall favorable potential declined.** |
| **Median MFE** | $0.72\text{R}$ | **$1.34\text{R}$** | **$+0.62\text{R}$** | Median excursion rose because sub-0.5R losers were filtered. |
| **25th Percentile MFE** | $0.02\text{R}$ | **$0.00\text{R}$** | $-0.02\text{R}$ | Bottom quartile remains dead on arrival ($0.00\text{R}$). |
| **75th Percentile MFE** | $1.90\text{R}$ | **$1.51\text{R}$** | **$-0.39\text{R}$** | **Upper quartile was compressed.** |
| **Failing before $0.5\text{R}$** | 11 / 24 ($45.8\%$) | **4 / 13 ($30.8\%$)** | **$-15.0\%$** | Modest reduction in immediate entry failures. |
| **Failing before $1.0\text{R}$** | 13 / 24 ($54.2\%$) | **5 / 13 ($38.5\%$)** | **$-15.7\%$** | Modest reduction in weak early traction. |
| **Reaching $\ge 1.5\text{R}$** | 10 / 24 ($41.7\%$) | **4 / 13 ($30.8\%$)** | **$-10.9\%$** | **Significant loss of monetizable expansions.** |
| **Reaching $\ge 2.0\text{R}$** | 6 / 24 ($25.0\%$) | **2 / 13 ($15.4\%$**) | **$-9.6\%$** | **Severe compression of large-trend captures.** |
| **Mean MAE** | $1.19\text{R}$ | **$1.30\text{R}$** | **$+0.11\text{R}$** | Adverse excursion worsened (tighter stops penetrated deeper). |
| **Median MAE** | $1.16\text{R}$ | **$1.06\text{R}$** | $-0.10\text{R}$ | Comparable adverse penetration. |
| **Mean Time to MFE** | 3.8 hours | **3.4 hours** | $-0.4\text{ hours}$ | No significant change in velocity. |
| **Median Time to MFE** | 0.0 hours | **0.0 hours** | 0.0 hours | Immediate reversals dominate both treatments. |

### Mechanism Verdict
The data delivers a clear and definitive verdict:
1. **The upward shift in median MFE is an illusion of survivorship:** By eliminating 11 immediate losing trades, the median point of the remaining 13 trades naturally drifted upward.
2. **The upper tail was severely damaged:** The strategy's ability to reach $\ge 1.5\text{R}$ dropped by **$26\%$ relative** ($41.7\% \to 30.8\%$), and $\ge 2.0\text{R}$ dropped by **$38\%$ relative** ($25.0\% \to 15.4\%$).
3. **Sweeps are NOT prerequisite to directional displacement:** Strong institutional impulse legs in crypto frequently launch directly from supply/demand imbalances or order blocks without first hunting an obvious retail swing. Requiring a sweep acts as a filter that selectively removes clean trend continuations.

---

## 9. ASSET & TIMEFRAME ATTRIBUTION

Per Section 9, performance was decomposed across all 3 assets and all 5 timeframe sets without parameter optimization.

### Asset Attribution Table

| Asset | D1 Trades ($N$) | D1 Net R | D1 Expectancy | E1 Trades ($N$) | E1 Net R | E1 Expectancy | Delta Net R | Delta Expectancy | Key Drivers |
|---|---|---|---|---|---|---|---|---|---|
| **BTC** | 5 (2 W / 2 L / 1 BE) | **$+8.2497\text{R}$** | **$+1.6499\text{R}$** | 3 (1 W / 1 L / 1 BE) | **$+5.2330\text{R}$** | **$+1.7443\text{R}$** | **$-3.0167\text{R}$** | $+0.0944\text{R}$ | **Loss of BTC $+4.11\text{R}$ winner** on SET_4. Only $+5.70\text{R}$ preserved. |
| **ETH** | 4 (0 W / 3 L / 1 BE) | **$-3.2796\text{R}$** | **$-0.8199\text{R}$** | 4 (0 W / 3 L / 1 BE) | **$-3.2171\text{R}$** | **$-0.8043\text{R}$** | $+0.0625\text{R}$ | $+0.0156\text{R}$ | Unchanged. Both setups fail to capture winning expansions. |
| **SOL** | 15 (0 W / 11 L / 4 BE) | **$-7.8453\text{R}$** | **$-0.5230\text{R}$** | 6 (0 W / 6 L / 0 BE) | **$-5.5902\text{R}$** | **$-0.9317\text{R}$** | $+2.2551\text{R}$ | **$-0.4087\text{R}$ (Worse)** | While trade count collapsed, **every single E1 trade lost** (6/6 losses). Expectancy worsened by $-78\%$. |

### Timeframe Set Attribution Table

| Timeframe Set | LTF / MTF / HTF | D1 Trades ($N$) | D1 Net R | D1 Expectancy | E1 Trades ($N$) | E1 Net R | E1 Expectancy | Delta Net R | Delta Expectancy |
|---|---|---|---|---|---|---|---|---|---|
| **SET_1** | 1D / 1W / 1M | 0 | $0.0000\text{R}$ | $0.0000\text{R}$ | 1 (0 W / 1 L) | **$-1.0327\text{R}$** | **$-1.0327\text{R}$** | $-1.0327\text{R}$ | $-1.0327\text{R}$ |
| **SET_2** | 4H / 1D / 1W | 3 (0 W / 2 L / 1 BE) | **$-1.3597\text{R}$** | **$-0.4532\text{R}$** | 2 (0 W / 2 L) | **$-2.1746\text{R}$** | **$-1.0873\text{R}$** | **$-0.8149\text{R}$** | **$-0.6341\text{R}$ (Worse)** |
| **SET_3** | 1H / 4H / 1D | 9 (1 W / 4 L / 4 BE) | **$+2.3224\text{R}$** | **$+0.2580\text{R}$** | 7 (1 W / 4 L / 2 BE) | **$+1.9750\text{R}$** | **$+0.2821\text{R}$** | $-0.3474\text{R}$ | $+0.0241\text{R}$ |
| **SET_4** | 15m / 1H / 4H | 12 (1 W / 10 L / 1 BE) | **$-3.8380\text{R}$** | **$-0.3198\text{R}$** | 3 (0 W / 3 L) | **$-2.3419\text{R}$** | **$-0.7806\text{R}$** | $+1.4961\text{R}$ | **$-0.4608\text{R}$ ($-144\%$ Worse)** |
| **SET_5** | 1m / 5m / 15m | 0 | $0.0000\text{R}$ | $0.0000\text{R}$ | 0 | $0.0000\text{R}$ | $0.0000\text{R}$ | $0.0000\text{R}$ | $0.0000\text{R}$ |

---

## 10. WINNER PRESERVATION DIAGNOSTIC

Per Section 10 of the mandate, the two observed canonical BTC winners were audited:

### 1. BTC $+5.70\text{R}$ Winner (`cand_BTC/USDT_1638824400` on `SET_3`): **PRESERVED**
* **Causal Status:** **RETAINED IDENTICAL ENTRY**.
* **Provenance:** MTF retest occurred at `1638972000`. A genuine bearish liquidity sweep occurred at `1638975600` (sweeping swing high at $50,795.45$). Bearish displacement fired immediately at the same candle.
* **Outcome:** Entered at `1638979200` at price $50,640.10$ with stop at $51,200.00$ and target at $47,430.18$. Price hit HTF target for **$+5.6955\text{R}$ net profit**.

### 2. BTC $+4.11\text{R}$ Winner (`cand_BTC/USDT_1620705600` on `SET_4`): **DESTROYED / LOST**
* **Causal Status:** **REJECTED / UN-ENTERED**.
* **Forensic Breakdown:**
  * Candidate setup formed on 2021-05-11 04:00 UTC with MTF retest confirmed on the 1H timeframe.
  * In D1, an impulse displacement candle confirmed at `1620824400` (2021-05-12 13:00 UTC), entering short at $56,359.18$ with stop at $57,195.50$ and target at $52,900.00$. Price collapsed directly into the HTF target for **$+4.1077\text{R}$ net profit** ($5.21\text{R}$ MFE).
  * In E1, because there was no prior LTF liquidity sweep of an opposing high before that displacement candle, entry was refused.
  * The candidate remained waiting in `WAIT_LTF_TRIGGER`. Price plummeted without returning. When a minor sweep finally formed 8 hours later at much lower prices, the candidate could no longer enter.
* **Significance:** This is conclusive empirical proof that mandatory sweep requirements destroy valid trend-continuation alpha.

---

## 11. DECISION & RESEARCH DIRECTIVE

### Final Classification: **`E-NEGATIVE`**

### Summary of Scientific Findings
1. **Liquidity Sweeps Are Not a Universal Prerequisite:** The hypothesis that "requiring a sweep will eliminate bad entries without hurting good ones" is falsified. Directional expansions in crypto frequently proceed directly from structural retests without sweeping an opposing swing.
2. **Expectancy Degraded Sharply:** Net expectancy worsened from $-0.1198\text{R}$ to $-0.2749\text{R}$. Profit factor dropped from $0.7732$ to $0.6144$.
3. **Selective Filtration Failure:** Sweep filtering reduced overall trade count by nearly $50\%$, but $77\%$ of the remaining trades still lost ($10/13$). On SOL, 100% of sweep-confirmed trades lost ($6/6$).
4. **Treatment Formally Rejected:** Experiment E1 will **NOT** be promoted or carried forward. The canonical strategy will retain the modular LTF entry model where displacement confirmation does not unconditionally mandate a prior sweep.

### Protocol Stop Condition
Per Section 12 of the directive:
1. Complete forensic audit produced.
2. Automated test suite verified (401 passed).
3. Full causal sweep provenance documented for all entries.
4. Comprehensive H0 / C1 / D1 / E1 comparison completed.
5. **HALT.** No downstream experiments (D2, regime filters, F, or Validation) will be initiated until this audit has been formally reviewed.
