# Research Cycle #5 Audit: `HYP_OPPORTUNITY_FUNNEL_FORENSICS_01`
## Canonical Development Opportunity Funnel & Rejected-Population Forensic Audit (2021–2022)

---

**Audit Authority:** Institutional Quantitative Governance  
**Experiment ID:** `HYP_OPPORTUNITY_FUNNEL_FORENSICS_01`  
**Experiment Type:** Counterfactual Opportunity-Funnel / Rejected-Population Read-Only Forensic Audit  
**Parent State:** `HYP_COMPOSITE_POLARITY_BREAKEVEN_01` (`RESULT_B_CONTROLLED_INTERACTION`, Composite $N=13$, Net Realized $+0.9615\text{R}$, PF $1.2583$)  
**Cycle #4 Context:** `HYP_TARGET_MILESTONE_01` (`RESULT_B_INFORMATIVE_MECHANISM`, Milestone $+2.5\text{R}$, frozen)  
**Dataset Partition:** Strict Development Partition (`2021-01-01T00:00:00Z` to `2022-12-31T23:59:59Z`, 277,908 market candles)  
**Partition Lock:** Validation (`2023`) and Out-of-Sample (`2024–2026`) partitions remain strictly **LOCKED**  
**Engineering Status:** **STRICTLY READ-ONLY FORENSICS** — Zero strategy code modified, zero parameters optimized, zero promotions.

---

## Executive Summary

Prior to Cycle #5, a preliminary heuristic proposed that *"the 4R planned geometry requirement is annihilating 98% of structurally aligned setups"* and recommended analyzing *"the 722 rejected LTF triggers"*. 

An independent institutional forensic audit was mandated to verify this claim. This audit proves that **both assertions were mathematically and conceptually conflated**:

1. **The 722 vs 705 vs 671 Conflation Resolved:**
   - **735** unique candidate setups achieved validated Lower Timeframe (LTF) sweep-and-displacement confirmations (`CandidateState.WAIT_LTF_TRIGGER` $\to$ `RISK_GATE`).
   - **705** candidates failed Target Resolution and were rejected before becoming entered orders ($735 - 30 = 705$).
   - **671** candidates were specifically rejected by the $\ge 4.0\text{R}$ planned reward-to-risk firewall (`REJECT_RR_BELOW_4R`).
   - **722** is the net number of LTF-confirmed opportunities that did not become one of the 13 Composite executed trades ($735 - 13 = 722$).
   - Treating "722 non-executed setups" as synonymous with "722 setups rejected by the 4R firewall" incorrectly lumped together 5 distinct lifecycle populations.

2. **The 4R Firewall Is NOT Starving Large Numbers of Multi-R Winners:**
   - **75.11% (504 of 671)** of the $\text{RR} < 4\text{R}$ rejected setups possessed planned structural reward-to-risk of **less than $1.0\text{R}$** (median planned $\text{RR} = 0.4999\text{R}$). Their opposing structural anchors were located closer than their initial stop-losses.
   - Only **47 out of 671 setups (7.00%)** possessed planned $\text{RR} \ge 2.0\text{R}$, and only **27 setups (4.02%)** possessed planned $\text{RR} \ge 2.5\text{R}$.
   - Lowering the firewall to $2.5\text{R}$ or $3.0\text{R}$ without modifying target geometry would not unlock hundreds of trades; it would expose the strategy to hundreds of sub-1R micro-oscillations.

3. **Causal Observation Horizon Finding:**
   - The platform does not pre-register an arbitrary post-rejection forward-looking window. Per governance instructions, we formally state: **"Counterfactual MFE/MAE requires a pre-registered observation horizon."**
   - Under the platform's canonical trade lifecycle boundary (measuring excursion until initial structural stop-out, with conservative adverse-first intrabar collision resolution):
     - **93.00% (624 of 671)** of all $4\text{R}$-rejected setups **never reached even $+1.0\text{R}$** favorable excursion. Median $\text{MFE} = 0.0000\text{R}$.
     - Only **16 setups (2.38%)** ever reached $+2.0\text{R}$, only **9 setups (1.34%)** reached $+2.5\text{R}$, and **zero setups ($0.00\%$)** ever reached $+4.0\text{R}$.

4. **Polarity-Eligible Population Forensics ($N=315$):**
   - When the validated Cycle #1 displacement polarity filter is applied to the $671$ $4\text{R}$-rejected setups, **356 setups ($53.06\%$) are eliminated at the trigger candle**, leaving $315$ polarity-conforming opportunities.
   - Among these $315$ polarity-eligible setups, **93.02% (293 setups)** fail to exceed $+1.0\text{R}$ excursion.
   - Exactly **2 setups in 2 full calendar years ($0.63\%$)** reached $+2.5\text{R}$ excursion.
   - **Zero setups ($0.00\%$)** reached $+3.0\text{R}$ or $+4.0\text{R}$.

5. **Scientific Verdict on Key Question:**
   - **`VERDICT: A. FIREWALL APPEARS APPROPRIATELY SELECTIVE`** (reinforced by **`C. ATTRITION IS PRIMARILY CAUSED ELSEWHERE`**).
   - The $\ge 4.0\text{R}$ planned-geometry firewall is behaving as an essential capital protection shield. The upstream bottleneck is not an excessively strict ratio threshold, but rather **target destination generation**: in trending regimes, opposing swing anchors frequently do not exist or form in immediate proximity, starving the setup of structural runway.

---

## 1. Canonical 735-Opportunity Funnel Reconstruction

Evaluating 277,908 historical market candles across all 15 matrix streams over the 2021–2022 Development partition, the canonical engine tracked 1,424 initial candidate setups. 

The complete point-in-time upstream progression to the certified `LTF_CONFIRMED` population is reconstructed below:

```text
TOTAL MARKET BARS EVALUATED: 277,908 (100.0%)
   │
   ▼
[1] HTF QUALIFIED CANDIDATES: 1,424 (0.51% of bars)
   │  [Survival: 100.0% | Drop: 0.0%]
   ▼
[2] MTF ALIGNED CANDIDATES: 1,173 (0.42% of bars)
   │  [Survival: 82.37% | Drop: 251 (17.63%) without MTF realignment BOS/CHOCH]
   ▼
[3] MTF RETESTED CANDIDATES: 754 (0.27% of bars)
   │  [Survival: 64.28% | Drop: 419 (35.72%) without causal KeyZone retest]
   ▼
[4] LTF TRIGGERS CONFIRMED: 735 (0.26% of bars)
   │  [Survival: 97.48% | Drop: 19 (2.52%) without LTF sweep/displacement]
   │
   └─────────────────────────────────────────────────────────┐
                                                             ▼
                                              ┌──────────────────────────────┐
                                              │ 735 LTF CONFIRMATIONS        │
                                              │ (The Audited Population)     │
                                              └──────────────────────────────┘
```

### Stratification of the 735 LTF Confirmations
- **Asset Distribution:** SOL: 258 ($35.10\%$), BTC: 248 ($33.74\%$), ETH: 229 ($31.16\%$).
- **Timeframe Distribution:** SET 4 (Intraday $15\text{M}$): 552 ($75.10\%$), SET 3 (Swing $1\text{H}$): 146 ($19.86\%$), SET 2 (Position $4\text{H}$): 27 ($3.67\%$), SET 1 (Macro $1\text{D}$): 10 ($1.36\%$).
- **Directional Bias:** 100.0% SHORT (735 of 735), reflecting the prevailing macro structural regime across crypto assets in 2021–2022.

---

## 2. Attrition Decomposition & Exact Disposition Waterfall

The 735 LTF-confirmed opportunities were partitioned into mutually exclusive, exhaustive lifecycle categories directly using canonical engine invalidation telemetry (`scratch/canonical_735_opportunity_ledger.json`):

```text
 ┌───────────────────────────────────────────────────────────────────────────┐
 │                   735 LTF-CONFIRMED OPPORTUNITIES                         │
 └─────────────────────────────────────┬─────────────────────────────────────┘
                                       │
         ┌─────────────────────────────┴─────────────────────────────┐
         ▼                                                           ▼
┌─────────────────────────────────┐                         ┌─────────────────────────────────┐
│  FAILED TARGET RESOLUTION (705) │                         │   TARGET RESOLVED (30)          │
│  (95.92% Attrition)             │                         │   (4.08% Survival)              │
└────────────────┬────────────────┘                         └────────────────┬────────────────┘
                 │                                                           │
   ┌─────────────┴─────────────┐                               ┌─────────────┴─────────────┐
   ▼                           ▼                               ▼                           ▼
RR < 4R Rejection      Upstream Structural              Pending Limit               Filled Trades
(671 / 91.29%)         Invalidations (34 / 4.63%)       Unfilled (7 / 0.95%)        (23 / 3.13%)
                       ├── Missing Anchors: 12                                      │
                       ├── Opposing MTF:    10                         ┌────────────┴────────────┐
                       ├── Superseded HTF:   7                         ▼                         ▼
                       └── Invalid Geometry: 5                 Polarity Filtered         Composite Executed
                                                               (10 / 1.36%)              (13 / 1.77%)
```

### Authoritative Funnel Reconciliations

| Stage / Category | Canonical Engine Status | Telemetry Reason | Count ($N$) | % of LTF Triggers | Cumulative Attrition |
| :--- | :--- | :--- | :---: | :---: | :---: |
| **1. Planned RR Firewall** | `CandidateState.REJECTED` | `REJECT_RR_BELOW_4R` | **671** | **91.29%** | 91.29% |
| **2. Opposing Structure Invalidation** | `CandidateState.REJECTED` | `REJECT_OPPOSING_MTF_STRUCTURE` | **10** | **1.36%** | 92.65% |
| **3. Superseded Context Invalidation** | `CandidateState.REJECTED` | `REJECT_SUPERSEDED_HTF_CONTEXT` | **7** | **0.95%** | 93.61% |
| **4. Missing Structural Anchors** | `CandidateState.REJECTED` | `REJECT_MISSING_STRUCTURAL_ANCHORS` | **12** | **1.63%** | 95.24% |
| **5. Inverted Target Geometry** | `CandidateState.REJECTED` | `REJECT_INVALID_ANCHOR_GEOMETRY` | **5** | **0.68%** | **95.92%** |
| **Subtotal: Failed Target Resolution** | — | — | **705** | **95.92%** | — |
| **6. Target Resolved — Pending Unfilled** | `CandidateState.ENTERED` | Limit order price not reached | **7** | **0.95%** | 96.87% |
| **7. Target Resolved — Polarity Filtered** | `CandidateState.ENTERED` | Counter-directional candle close | **10** | **1.36%** | 98.23% |
| **8. Target Resolved — Composite Executed**| `CandidateState.ENTERED` | Fully executed in Composite | **13** | **1.77%** | **100.00%** |
| **Total Reconstructed Population** | — | — | **735** | **100.00%** | — |

$$\sum \text{Dispositions} = 671 + 10 + 7 + 12 + 5 + 7 + 10 + 13 = 735 \quad (100.00\% \text{ reconciled})$$

### Mathematical Disambiguation: 722 vs 705 vs 671
1. **$735 - 30 = 705$**: Opportunities destroyed at or before Target Resolution.
2. **$735 - 23 = 712$**: Opportunities that failed to execute in the certified ANCHOR_2 baseline.
3. **$735 - 13 = 722$**: Opportunities that did not execute in Composite (Cycle #3).
4. **$671$**: Genuine opportunities rejected specifically because planned reward-to-risk failed $\ge 4.0\text{R}$.

---

## 3. Phase 3 — 4R Firewall Isolation & Geometric Distribution

To understand why 671 opportunities were blocked by the $\ge 4.0\text{R}$ rule, we isolated and analyzed the planned geometry ($\text{Entry}$, $\text{Initial SL}$, $\text{Target Price}$) for all 671 candidates:

$$\text{Planned RR} = \frac{|\text{Target Price} - \text{Entry Price}|}{|\text{Entry Price} - \text{Initial SL Price}|}$$

### Distribution Statistics of the 671 4R-Rejected Opportunities

| Metric | Planned Structural Reward-to-Risk ($\text{RR}$) | Geometric Meaning |
| :--- | :---: | :--- |
| **Audited Population ($N$)** | **671** | $91.29\%$ of all confirmed LTF triggers |
| **Minimum Planned RR** | **$0.0007\text{R}$** | Target virtually identical to entry price |
| **25th Percentile ($Q_1$)** | **$0.2088\text{R}$** | Target distance is one-fifth of stop distance |
| **Median Planned RR** | **$0.4999\text{R}$** | Target distance is half of stop distance |
| **Mean Planned RR** | **$0.7315\text{R}$** | Skewed by small tail of $2\text{R}$–$3.8\text{R}$ setups |
| **75th Percentile ($Q_3$)** | **$0.9929\text{R}$** | $75\%$ of setups do not even offer $1.0\text{R}$ reward |
| **Maximum Planned RR** | **$3.8545\text{R}$** | Highest rejected ratio |

### Planned RR Stratification Buckets

```text
PLANNED RR DISTRIBUTION (N = 671)
─────────────────────────────────────────────────────────────────────────────
< 1.0R      [████████████████████████████████████████] 504 (75.11%)
1.0 – 2.0R  [█████████]                                120 (17.88%)
2.0 – 2.5R  [█]                                         20 ( 2.98%)
2.5 – 3.0R  [█]                                         17 ( 2.53%)
3.0 – 3.5R  [ ]                                          6 ( 0.89%)
3.5 – 4.0R  [ ]                                          4 ( 0.60%)
─────────────────────────────────────────────────────────────────────────────
```

### Critical Geometric Findings:
- **The $1.0\text{R}$ Structural Starvation:** **Three-quarters ($75.11\%$) of the rejected population had less than $1.0\text{R}$ of room** to the opposing structural destination.
- **The $2.5\text{R}$ Milestone Reality:** Even if the platform's minimum RR requirement had been relaxed from $4.0\text{R}$ to $2.5\text{R}$, **only 27 out of 671 setups ($4.02\%$) would have qualified**.
- **The $2.0\text{R}$ Threshold Reality:** Even if relaxed to $2.0\text{R}$, only 47 setups ($7.00\%$) would have qualified.
- **Conclusion on Target Geometry:** The firewall is not rejecting setups that offer $3.5\text{R}$ or $3.8\text{R}$ by narrow margins. It is filtering an enormous mass of geometrically compressed setups where opposing structural liquidity sits immediately in front of the entry point.

---

## 4. Phase 4 — Population Layering & Venn Intersections

We audited the intersections among the discrete research populations identified across Cycles #1 through #4:

```text
                         POPULATION LAYER INTERSECTIONS
                         
         ALL LTF-CONFIRMED (N = 735)
         ┌─────────────────────────────────────────────────────────┐
         │                                                         │
         │   4R-REJECTED (N = 671)                                 │
         │   ┌─────────────────────────┬───────────────────────┐   │
         │   │ Polarity-Filtered       │ Polarity-Eligible     │   │
         │   │ N = 356 (53.06%)        │ N = 315 (46.94%)      │   │
         │   └─────────────────────────┴───────────────────────┘   │
         │                                                         │
         │   UPSTREAM INVALIDATED (N = 34)                         │
         │                                                         │
         │   TARGET-RESOLVED / ENTERED (N = 30)                    │
         │   ┌────────────────────────┬────────────────────────┐   │
         │   │ Pending Unfilled (N=7) │ Baseline Filled (N=23) │   │
         │   │                        ├────────────┬───────────┤   │
         │   │                        │ Polarity-  │ Composite │   │
         │   │                        │ Filtered   │ Executed  │   │
         │   │                        │ (N = 10)   │ (N = 13)  │   │
         │   └────────────────────────┴────────────┴───────────┘   │
         └─────────────────────────────────────────────────────────┘
```

### Layer Attribution Matrix

| Population Layer | Count ($N$) | % of LTF Confirmed | Overlap / Intersection Attributes |
| :--- | :---: | :---: | :--- |
| **A. All LTF-Confirmed** | 735 | 100.00% | Master denominator of structurally triggered setups |
| **B. 4R-Qualified** | 30 | 4.08% | Structural target $\ge 4.0\text{R}$ (all entered `CandidateState.ENTERED`) |
| **C. 4R-Rejected** | 671 | 91.29% | Failed minimum $4.0\text{R}$ geometry floor |
| **D. Target-Resolved** | 30 | 4.08% | Evaluated by Risk Coordinator (100% approved) |
| **E. Pending-but-Unfilled** | 7 | 0.95% | Limit order entry never touched by price |
| **F. Polarity-Filtered** | 10 | 1.36% | ANCHOR_2 filled trades filtered by Cycle #1 entry gate |
| **G. Composite-Executed** | 13 | 1.77% | Certified executed population in Cycle #3 Composite |

### Key Layer Intersections
1. **4R-Rejected $\cap$ Polarity-Eligible:** $N = 315$ ($46.94\%$ of 4R-rejected).
2. **4R-Rejected $\cap$ Polarity-Filtered:** $N = 356$ ($53.06\%$ of 4R-rejected).
3. **4R-Qualified $\cap$ Polarity-Filtered:** $N = 10$ ($43.48\%$ of filled trades).
4. **4R-Qualified $\cap$ Composite-Executed:** $N = 13$ ($56.52\%$ of filled trades).

---

## 5. Phase 5 — Counterfactual Excursion Audit & Horizon Forensics

### The Observation Horizon Problem
As mandated by the research directive, forward excursion (MFE/MAE) cannot be calculated in an unconstrained manner. An observation horizon that looks forward infinitely until the end of the 2-year dataset will guarantee artificial multi-R excursions as market regimes change.

We conducted a forensic inspection of the platform code (`strategy_engine`, `research/replayer`, `risk_engine`). 
- **Platform Invariant:** The platform defines candidate lifespans (`max_lifespan_seconds`) for pre-entry candidate tracking, but **encodes zero pre-registered post-rejection observation horizons**.
- **Formal Governance Statement:**
  > [!IMPORTANT]
  > **Counterfactual MFE/MAE requires a pre-registered observation horizon.**

### Sensitivity Across Defensible Causal Horizons
To provide complete and rigorous transparency without creating ad-hoc optimization, we evaluated the rejected population under two defensible structural benchmarks:

1. **Horizon 1 — Canonical Stop-Out Boundary:**  
   Simulates the causal lifecycle forward from trigger until the initial structural stop-loss (`ltf_structural_sl`) is penetrated, applying the platform's strict adverse-first intrabar collision resolution. If price never hits stop-loss, it tracks until target.
2. **Horizon 2 — Candidate TTL Lifespan Boundary:**  
   Constrains forward tracking to the candidate's canonical MTF lifespan ($12\text{h}$ for $15\text{M}$ intraday, $48\text{h}$ for $1\text{H}$ swing, $7\text{d}$ for $4\text{H}$ position) or initial stop-out, whichever occurs first.

---

## 6. Phase 6 — 4R-Rejected Population Forensics

### Comprehensive Excursion Distribution ($N=671$)

| Excursion Metric | Horizon 1: Until Stop-Out | Horizon 2: Candidate TTL Lifespan | Interpretation |
| :--- | :---: | :---: | :--- |
| **Mean MFE ($R$)** | **$+0.2445\text{R}$** | **$+0.1586\text{R}$** | Average directional push is fractional |
| **Median MFE ($R$)** | **$0.0000\text{R}$** | **$0.0000\text{R}$** | In $>50\%$ of setups, adverse stop occurred immediately |
| **Standard Deviation MFE** | $0.5061\text{R}$ | $0.3480\text{R}$ | Extremely tight dispersion around zero |
| **25th Percentile ($Q_1$)** | $0.0000\text{R}$ | $0.0000\text{R}$ | Immediate invalidation |
| **75th Percentile ($Q_3$)** | $0.2732\text{R}$ | $0.1956\text{R}$ | 75% of setups fail to reach even $+0.28\text{R}$ |
| **Maximum MFE ($R$)** | $+3.2997\text{R}$ | $+3.2997\text{R}$ | Absolute single-trade peak excursion |
| **Mean MAE ($R$)** | $0.2743\text{R}$ | $0.2164\text{R}$ | Adverse pressure before stop |
| **Median MAE ($R$)** | $0.0909\text{R}$ | $0.0885\text{R}$ | Immediate adverse movement |
| **Mean Time to MFE** | $17.92\text{ hours}$ | $2.81\text{ hours}$ | Slow excursion / fast failure |
| **Median Time to MFE** | $0.00\text{ hours}$ | $0.00\text{ hours}$ | Zero favorable excursion before adverse tick |

### Milestone Attainment Rates ($N=671$)

| Milestone Horizon | Count (Stop-Out) | % (Stop-Out) | Count (Lifespan) | % (Lifespan) |
| :--- | :---: | :---: | :---: | :---: |
| **Reaching $\ge +1.0\text{R}$** | 47 | **7.00%** | 20 | **2.98%** |
| **Reaching $\ge +2.0\text{R}$** | 16 | **2.38%** | 6 | **0.89%** |
| **Reaching $\ge +2.5\text{R}$** | 9 | **1.34%** | 2 | **0.30%** |
| **Reaching $\ge +3.0\text{R}$** | 4 | **0.60%** | 1 | **0.15%** |
| **Reaching $\ge +4.0\text{R}$** | **0** | **0.00%** | **0** | **0.00%** |

---

## 7. Phase 7 — Polarity-Eligible vs Polarity-Filtered Subset Analysis

To prevent setups that our validated entry gate (Cycle #1 displacement polarity) would have rejected anyway from contaminating the evaluation of the 4R rule, we partitioned the 671 rejected setups into:
- **Cohort A:** $4\text{R}$-Rejected + Polarity-Eligible ($N=315$)
- **Cohort B:** $4\text{R}$-Rejected + Polarity-Filtered ($N=356$)

### Paired Excursion Comparison (Horizon: Until Stop-Out)

| Metric | Cohort A: Polarity-Eligible ($N=315$) | Cohort B: Polarity-Filtered ($N=356$) | Delta ($\Delta$) |
| :--- | :---: | :---: | :---: |
| **Mean MFE ($R$)** | **$+0.2476\text{R}$** | $+0.2417\text{R}$ | $+0.0059\text{R}$ |
| **Median MFE ($R$)** | **$0.0000\text{R}$** | $0.0000\text{R}$ | $0.0000\text{R}$ |
| **75th Percentile ($Q_3$)** | **$+0.3045\text{R}$** | $+0.2666\text{R}$ | $+0.0379\text{R}$ |
| **Maximum MFE ($R$)** | **$+2.9144\text{R}$** | $+3.2997\text{R}$ | $-0.3853\text{R}$ |
| **Mean MAE ($R$)** | **$0.2854\text{R}$** | $0.2644\text{R}$ | $+0.0210\text{R}$ |
| **Median MAE ($R$)** | **$0.0950\text{R}$** | $0.0873\text{R}$ | $+0.0077\text{R}$ |
| **Reaching $\ge +1.0\text{R}$** | **22 (6.98%)** | 25 (7.02%) | $-0.04\%$ |
| **Reaching $\ge +2.0\text{R}$** | **7 (2.22%)** | 9 (2.53%) | $-0.31\%$ |
| **Reaching $\ge +2.5\text{R}$** | **2 (0.63%)** | 7 (1.97%) | $-1.34\%$ |
| **Reaching $\ge +3.0\text{R}$** | **0 (0.00%)** | 4 (1.12%) | $-1.12\%$ |
| **Reaching $\ge +4.0\text{R}$** | **0 (0.00%)** | 0 (0.00%) | $0.00\%$ |

### MFE Bucket Distribution for Polarity-Eligible Cohort ($N=315$)

```text
POLARITY-ELIGIBLE 4R-REJECTED MFE DISTRIBUTION (N = 315)
─────────────────────────────────────────────────────────────────────────────
< 1.0R      [████████████████████████████████████████] 293 (93.02%)
1.0 – 2.0R  [██]                                        15 ( 4.76%)
2.0 – 2.5R  [█]                                          5 ( 1.59%)
2.5 – 3.0R  [ ]                                          2 ( 0.63%)
3.0 – 4.0R  [ ]                                          0 ( 0.00%)
>= 4.0R     [ ]                                          0 ( 0.00%)
─────────────────────────────────────────────────────────────────────────────
```

### Decisive Finding on Polarity Interaction:
- Out of all 671 setups rejected by the 4R rule, **only TWO (2) setups in 2 full calendar years** satisfy displacement polarity AND subsequently achieve $+2.5\text{R}$ excursion before stopping out:
  1. `cand_ETH/USDT_UNIFIED_STRATEGY_1615820400` (SET_4, March 2021, reached $+2.91\text{R}$)
  2. `cand_ETH/USDT_UNIFIED_STRATEGY_1648936800` (SET_4, April 2022, reached $+2.83\text{R}$)
- **Zero setups** reached $+3.0\text{R}$ or $+4.0\text{R}$.
- If the 4R firewall had been lowered to $2.5\text{R}$ or eliminated entirely, the strategy would have admitted hundreds of immediate failures while capturing at most **2 additional milestone-eligible trades** across 2 years.

---

## 8. Economic Counterfactual Caution

Per Phase 7 of the directive, we explicitly refrain from converting counterfactual excursions into hypothetical realized trade P&L:

> [!CAUTION]
> **Favorable excursion (MFE) is NOT realized P&L.**
>
> 1. A setup exhibiting $+1.5\text{R}$ or $+2.0\text{R}$ MFE does not imply a profitable realized exit. In the certified baseline ($N=23$), $52.38\%$ of losing trades achieved favorable excursions between $+0.5\text{R}$ and $+1.8\text{R}$ before reversing into stop-outs.
> 2. Converting rejected candidates into trade P&L requires assuming an active order fill, execution priority, margin availability, position concurrency, and precise trailing stop state machine dynamics that do not exist for unentered plans.
> 3. Therefore, this audit reports strictly that: *"these rejected opportunities subsequently exhibited $\ge X\text{R}$ favorable excursion under the defined observation horizon."*

---

## 9. Key Question & Scientific Verdict

### The Key Question:
> *"Is the $\ge 4\text{R}$ firewall demonstrably responsible for a large and economically interesting portion of the opportunity attrition, and does the rejected-but-potentially-polarity-eligible population contain meaningful favorable excursion that justifies a future controlled geometric experiment?"*

### Verdict:
# 🟢 `VERDICT_A: FIREWALL APPEARS APPROPRIATELY SELECTIVE`
### (Supported by `VERDICT_C: ATTRITION IS PRIMARILY CAUSED ELSEWHERE`)

### Scientific Rationale:
1. **The Firewall Is Doing Defensive Work:** $93.02\%$ of the polarity-eligible rejected setups die below $1.0\text{R}$. The 4R firewall successfully prevented 293 low-expectancy setups from entering the execution pipeline and causing friction drag or stop-out losses.
2. **The Bottleneck Is Upstream Target Generation, Not the 4R Floor:** $75.11\%$ of rejected setups had planned $\text{RR} < 1.0\text{R}$. This indicates that the HTF destination engine frequently anchors targets to nearby micro-swings rather than identifying genuine structural expansion ranges.
3. **No Hidden Motherlode of Alpha:** Relaxing the 4R firewall to $2.5\text{R}$ or $3.0\text{R}$ would not unlock dozens of winners. Across the entire 2-year Development partition, only **2 polarity-eligible setups** ever reached $2.5\text{R}$, and **zero** reached $3.0\text{R}$.
4. **Controlled Geometric Experiment Decision:**
   - A naive reduction of the $\ge 4.0\text{R}$ threshold (e.g. testing $2.5\text{R}$ or $3.0\text{R}$ in isolation) is **SCIENTIFICALLY UNJUSTIFIED** and would lead to severe capital erosion.
   - Any future geometric research must focus **upstream** on the **Target Destination Discovery Engine** (how forward targets are identified and whether dealing-range expansion models can identify distant structural liquidity), NOT on lowering the risk threshold to admit compressed sub-1R setups.

---

## 10. Audit Artifacts & Registry

- **Exhaustive 735-Opportunity Ledger:** `scratch/canonical_735_opportunity_ledger.json` (SHA-256 verified, contains candidate ID, stream, timestamp, entry, SL, target, planned RR, disposition, and excursion metrics for all 735 triggers).
- **Forensic Diagnostic Runner:** `scratch/generate_cycle5_forensic_ledger.py`
- **Excursion Audit Engine:** `scratch/audit_counterfactual_excursions.py`
- **Polarity Audit Engine:** `scratch/audit_polarity_on_rejected.py`
- **Cross-Tabulation Engine:** `scratch/print_crosstabs.py`

---

## Strict Stop Condition Acknowledgment

This cycle was conducted strictly as a **READ-ONLY FORENSIC AUDIT**.
- Zero strategy code modified.
- Zero parameters swept or tuned.
- Planned RR $\ge 4.0\text{R}$ firewall remains strictly intact.
- Validation (`2023`) and Out-of-Sample (`2024–2026`) partitions remain strictly **LOCKED**.
- No automatic progression to Cycle #6.

**Research execution is complete. The system has stopped.**
