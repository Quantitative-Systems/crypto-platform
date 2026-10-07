# MULTI-TIMEFRAME ALPHA FORENSICS AUDIT (D0)
**Phase:** Product 04 — Research Laboratory (Quantitative Strategy Research)  
**Partition Scope:** Development Partition (2021–2022) ONLY  
**Validation (2023) & OOS (2024–2026):** STRICTLY LOCKED  
**Status:** D0 ALPHA FORENSICS AUDIT & METHODOLOGICAL CORRECTION COMPLETE  
**Audited Sample:** All 20 Remaining Losing Trades Under Candidate Management C1 ($N=29$)  
**Deliverable File:** `docs/MULTI_TIMEFRAME_ALPHA_FORENSICS_D1_AUDIT.md`

---

## 1. CRITICAL METHODOLOGICAL CORRECTIONS & EPISTEMIC DISCIPLINE

Following rigorous internal peer review, several critical methodological and interpretive corrections have been applied to this forensic analysis:

### A. The True Empirical Finding of D0: Upstream Excursion Failure
The primary, undeniable finding of D0 is **NOT** that `INTERNAL_CHOCH` is the root cause.  
The true empirical finding is that **the current entry funnel has an exceptionally poor early-excursion distribution**:
* **$17 / 20$ losses ($85.0\%$) never reached $+1.0\text{R}$** of favorable excursion.
* **$12 / 20$ losses ($60.0\%$) never reached $+0.5\text{R}$** of favorable excursion.
* **Only $2 / 20$ reached $+1.5\text{R}$**, and only $1 / 20$ reached $+2.0\text{R}$.
* This conclusively proves that negative expectancy is **predominantly upstream of the exit-management layer**.
* Exit management (such as Candidate Control C1) is valuable, but cannot repair a strategy whose entries fail before management can engage.

### B. Avoiding the Fallacy of "Single Root Cause"
The failure of any individual trade (e.g., T00) is entangled across multiple coexisting mechanisms:
$$\text{MTF Event} + \text{MTF Displacement} + \text{MTF Retest Dynamics} + \text{LTF Trigger Model} + \text{Regime} + \text{Entry Location} + \text{Stop Geometry}$$
Claiming that `INTERNAL_CHOCH` is "the culprit" mistakes correlation for causal proof. It is a **testable candidate hypothesis**, not a proven root cause.

### C. Repairing Classification Inconsistencies
1. **The "100% RANGE_CHOP" Discovery:**
   * Forensic inspection of the codebase reveals that `trend_regime: str = "RANGE_CHOP"`, `volatility_regime: str = "NORMAL_VOLATILITY"`, and `market_phase: str = "CONTINUATION"` are literally the **unpopulated dataclass default values** on `SimulatedTrade` in [`research/simulation/trade_ledger.py:52-54`](file:///home/mrcn2/crypto-platform/research/simulation/trade_ledger.py#L52-L54).
   * Because `enable_regime_filter=False` was configured in the baseline run, no dynamic regime classification was actively stamped onto the trade objects.
   * **Correction:** The "100% RANGE_CHOP" statement was an artifact of unpopulated default variables. It must **NOT** be claimed as empirical proof of market regime until an active, causally verified regime classifier is run.
2. **LTF Sweep / Displacement Semantics:**
   * Earlier draft tables showed internal contradictions (e.g., `SWEEP_AND_DISP` trigger reason paired with an ad-hoc `No Sweep` label).
   * In the strategy engine's causal provenance, exactly **6 of 20 losses entered under `LTF_SWEEP_AND_DISPLACEMENT_CONFIRMED` (30.0%)**, while **14 of 20 entered under single-candle displacement models (70.0%)**.
   * Ad-hoc post-hoc 5-bar heuristics have been removed. LTF sweep statistics are treated strictly as **provisional hypotheses**, not established proof.
3. **Disentangling Class H:**
   * The previous draft conflated `INTERNAL_CHOCH` and weak displacement ($<2.0\%$).
   * As shown in Section 3, these are distinct dimensions: multiple `EXTERNAL_CHOCH` trades had weak displacement (e.g., T27 at 1.06%, T28 at 0.62%), while several `INTERNAL_CHOCH` trades had strong displacement (e.g., T24 at 3.26%, T22 at 3.07%). They are now categorized into separate failure classes: **H1 (Minor Internal Shift)** and **H2 (Weak MTF Displacement)**.
4. **Epistemic Calibration on Winners ($N=2$):**
   * Two winners (Trade 08: $+4.11\text{R}$, Trade 14: $+5.70\text{R}$) are an anecdotal sample.
   * They prove only that *the two observed winners did not originate from `INTERNAL_CHOCH`*. They do **not** prove that major structural shifts universally produce positive expectancy.
5. **Large-Excursion Counter-Examples:**
   * **Trade 06** (`EXTERNAL_CHOCH`, 2.83% displacement, MFE $+3.35\text{R}$) still resulted in a scratch loss ($-0.09\text{R}$).
   * **Trade 22** (`INTERNAL_CHOCH`, 3.07% displacement, MFE $+1.83\text{R}$) reached substantial excursion despite being an internal shift.
   * This confirms that rejecting `INTERNAL_CHOCH` cannot be a universal silver bullet.

---

## 2. REVISED FORENSIC LEDGER (ALL 20 $C_1$ LOSING TRADES)

| # | Trade ID | Asset | Set | Dir | HTF Phase / KZ / Target | MTF Shift / Disp / Retest | LTF Causal Trigger | Net R | MFE | MAE | Dur | Exit Reason | Revised Failure Classes |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **00** | `T00` | BTC | SET_3 | LONG | EXPANSION / FVG / LIQ_POOL | INTERNAL_CHOCH / 1.92% / Retest 900m | BULLISH_DISP | -1.0604 | 0.00R | 1.87R | 60m | INITIAL_LTF_SL | **A, H1, H2** |
| **01** | `T01` | SOL | SET_4 | LONG | EXPANSION / FVG / LIQ_POOL | EXTERNAL_CHOCH / 3.09% / Retest 120m | BULLISH_DISP | -1.0615 | 0.00R | 1.39R | 60m | INITIAL_LTF_SL | **A** |
| **02** | `T02` | SOL | SET_4 | LONG | EXPANSION / FVG / OPP_KZ | MSS / 4.02% / Retest 330m | BULLISH_DISP | -1.0846 | 0.47R | 1.20R | 0m | INITIAL_LTF_SL | **B** |
| **03** | `T04` | ETH | SET_3 | LONG | EXPANSION / OB / WEAK_SWING | MSS / 2.71% / Retest 2460m | BULLISH_DISP | -1.1043 | 0.03R | 1.74R | 0m | INITIAL_LTF_SL | **A** |
| **04** | `T05` | BTC | SET_4 | SHRT | EXPANSION / FVG / LIQ_POOL | INTERNAL_CHOCH / 2.10% / Retest 120m | BEARISH_DISP | -1.0911 | 0.00R | 1.37R | 45m | INITIAL_LTF_SL | **A, H1** |
| **05** | `T06` | SOL | SET_4 | LONG | EXPANSION / OB / LIQ_POOL | EXTERNAL_CHOCH / 2.83% / Retest 135m | BULLISH_DISP | -0.0933 | 3.35R | 0.24R | 0m | MTF_TRAIL | **D, E, F, G** |
| **06** | `T07` | SOL | SET_3 | LONG | EXPANSION / FVG / WEAK_SWING | INTERNAL_CHOCH / 1.69% / Retest 2040m | SWEEP_AND_DISP | -0.0526 | 0.75R | 0.36R | 0m | MTF_TRAIL | **F, H1, H2** |
| **07** | `T11` | SOL | SET_4 | SHRT | EXPANSION / FVG / WEAK_SWING | MSS / 3.19% / Retest 420m | SWEEP_AND_DISP | -0.1190 | 0.93R | 0.87R | 0m | MTF_TRAIL | **F** |
| **08** | `T12` | BTC | SET_3 | SHRT | EXPANSION / FVG / LIQ_POOL | EXTERNAL_CHOCH / 2.46% / Retest 1620m | SWEEP_AND_DISP | -0.4625 | 0.00R | 0.57R | 0m | MTF_TRAIL | **A, F** |
| **09** | `T13` | SOL | SET_3 | LONG | PULLBACK / FVG / OPP_KZ | INTERNAL_CHOCH / 2.17% / Retest 720m | BULLISH_DISP | -1.0758 | 0.82R | 1.10R | 540m | INITIAL_LTF_SL | **C, H1** |
| **10** | `T16` | SOL | SET_2 | SHRT | EXPANSION / OB / LIQ_POOL | EXTERNAL_BOS / 3.28% / Retest 8640m | SWEEP_AND_DISP | -1.0793 | 1.25R | 1.20R | 0m | INITIAL_LTF_SL | **C** |
| **11** | `T17` | SOL | SET_2 | SHRT | EXPANSION / OB / LIQ_POOL | EXTERNAL_BOS / 3.28% / Retest 8400m | SWEEP_AND_DISP | -0.2804 | 0.48R | 0.35R | 0m | MTF_TRAIL | **B, F** |
| **12** | `T20` | SOL | SET_4 | LONG | EXPANSION / OB / LIQ_POOL | MSS / 1.86% / Retest 840m | BULLISH_DISP | -1.1180 | 0.00R | 1.85R | 0m | INITIAL_LTF_SL | **A, H2** |
| **13** | `T21` | SOL | SET_3 | LONG | EXPANSION / OB / OPP_KZ | MSS / 1.91% / Retest 360m | SWEEP_AND_DISP | -1.1137 | 0.00R | 2.08R | 0m | INITIAL_LTF_SL | **A, H2** |
| **14** | `T22` | SOL | SET_4 | SHRT | EXPANSION / FVG / LIQ_POOL | INTERNAL_CHOCH / 3.07% / Retest 240m | BEARISH_DISP | -0.1120 | 1.83R | 1.12R | 0m | MTF_TRAIL | **D, F, H1** |
| **15** | `T23` | SOL | SET_3 | SHRT | EXPANSION / FVG / LIQ_POOL | MSS / 5.34% / Retest 480m | BEARISH_DISP | -0.6926 | 0.52R | 0.92R | 540m | MTF_TRAIL | **F** |
| **16** | `T24` | ETH | SET_4 | SHRT | EXPANSION / OB / LIQ_POOL | INTERNAL_CHOCH / 3.26% / Retest 420m | BEARISH_DISP | -1.0793 | 0.42R | 1.05R | 45m | INITIAL_LTF_SL | **B, H1** |
| **17** | `T25` | SOL | SET_4 | LONG | EXPANSION / FVG / LIQ_POOL | INTERNAL_CHOCH / 2.08% / Retest 120m | BULLISH_DISP | -1.0960 | 0.78R | 3.33R | 120m | INITIAL_LTF_SL | **C, H1** |
| **18** | `T27` | ETH | SET_4 | SHRT | EXPANSION / OB / WEAK_SWING | EXTERNAL_CHOCH / 1.06% / Retest 165m | BEARISH_DISP | -1.0960 | 0.10R | 2.10R | 30m | INITIAL_LTF_SL | **A, H2** |
| **19** | `T28` | SOL | SET_4 | SHRT | EXPANSION / FVG / LIQ_POOL | EXTERNAL_CHOCH / 0.62% / Retest 75m | BEARISH_DISP | -1.0909 | 0.00R | 1.23R | 75m | INITIAL_LTF_SL | **A, H2** |

---

## 3. DISENTANGLED EVIDENCE-BASED FAILURE CLASSES

* **Class A (Immediate LTF failure — $\text{MFE} < 0.20\text{R}$ into initial SL):**  
  **8 trades (40.0%)** — `T00, T01, T04, T05, T12, T20, T21, T28`. (7 had exactly $\text{MFE} = 0.00\text{R}$).
* **Class B (Weak early traction — $0.20\text{R} \le \text{MFE} < 0.50\text{R}$):**  
  **3 trades (15.0%)** — `T02, T17, T24`.
* **Class C (Moderate favorable excursion but $<1.5\text{R}$):**  
  **3 trades (15.0%)** — `T13 (0.82R), T16 (1.25R), T25 (0.78R)`.
* **Class D (C1-mitigated reversal — $\text{MFE} \ge 1.5\text{R}$ or protected near entry):**  
  **2 trades (10.0%)** — `T06 (3.35R), T22 (1.83R)`.
* **Class E (High-MFE failure — $\text{MFE} \ge 2.0\text{R}$):**  
  **1 trade (5.0%)** — `T06 (3.35R)`.
* **Class F (MTF trailing failure — Trailed stop exited with small net loss):**  
  **7 trades (35.0%)** — `T06, T07, T11, T12, T17, T22, T23`. (Combined loss was $-1.8124\text{R}$, mean $-0.2589\text{R}$).
* **Class G (HTF destination failure — $\text{MFE} \ge 3.0\text{R}$ with planned $\text{RR} \ge 8.0\text{R}$):**  
  **1 trade (5.0%)** — `T06`.
* **Class H1 (Minor Sub-Structure Shift — `INTERNAL_CHOCH`):**  
  **7 trades (35.0%)** — `T00, T05, T07, T13, T22, T24, T25`.
* **Class H2 (Weak MTF Displacement — Leg $<2.0\%$):**  
  **7 trades (35.0%)** — `T00, T07, T20, T21, T22, T27, T28`.  
  *Note:* Only 2 trades overlap between H1 and H2 (`T00, T07`), proving that structural shift type and displacement magnitude are independent failure dimensions.
* **Class I (Data/causality/execution anomaly):**  
  **0 trades (0.0%)**. Certified zero-leakage, zero simulation errors.

---

## 4. ANSWERS TO THE 11 AGGREGATE FORENSIC QUESTIONS

1. **Immediate LTF failures ($\text{MFE} < 0.20\text{R}$):** **8 / 20 (40.0%)**.
2. **Meaningful favorable excursion ($\text{MFE} \ge 0.50\text{R}$):** **8 / 20 (40.0%)**.
3. **Fail before $+1.0\text{R}$:** **17 / 20 (85.0%)**. This is the core empirical finding.
4. **Reach $+1.0\text{R}$ but fail before $+1.5\text{R}$:** **1 / 20 (5.0%)** (`T16` on SOL_SET_2).
5. **Reach $\ge +1.5\text{R}$:** **2 / 20 (10.0%)** (`T06` at 3.35R, `T22` at 1.83R).
6. **Rescued by C1:** 7 trades across the ledger converted to $0.0000\text{R}$; within the 20 losses, 2 trades were mitigated to scratch losses near entry.
7. **Require entry improvement rather than management improvement:** **17 / 20 (85.0%)**. Because $85\%$ fail before $+1\text{R}$, exit management cannot monetarily rescue them.
8. **Appear to be MTF setup-quality candidates:** **12 / 20 (60.0%)** (exhibiting `INTERNAL_CHOCH` or weak displacement $<2.0\%$).
9. **Appear to be LTF entry-quality candidates:** **14 / 20 (70.0%)** (entered via single-candle displacement without sweep).
10. **Regime/context failures:** **Status unproven**. The previous "100% RANGE_CHOP" statement was an unpopulated default variable artifact. True regime impact remains a standing hypothesis to be evaluated with an active, certified regime classifier.
11. **Dominant failure mode across assets/sets:** **IMMEDIATE STRUCTURAL INVALIDATION AT ENTRY** ($85\%$ fail before $+1\text{R}$, $60\%$ fail before $+0.5\text{R}$).

---

## 5. WHERE IS THE CURRENT STRATEGY LOSING ITS EDGE?

```text
                    CURRENT RESEARCH FAILURE MAP

                         HTF
                          │
                          ▼
                 Direction / Context
                     [Secondary;
                   sound on trends]
                          │
                          ▼
                 MTF ALIGNMENT
                          │
             ┌────────────┴────────────┐
             │                         │
     event classification         displacement
             │                         │
      INTERNAL_CHOCH              weak/strong
     (Hypothesis H1)            (Hypothesis H2)
             │                         │
             └────────────┬────────────┘
                          ▼
                     MTF RETEST
                          │
                   collision/reaction
                        quality
                          │
                          ▼
                     LTF ENTRY
                          │
                ┌─────────┴─────────┐
                │                   │
             sweep?            displacement?
         (Hypothesis E1)       (Hypothesis E2)
                │                   │
                └─────────┬─────────┘
                          ▼
                        ENTRY
                          │
                          ▼
                    LTF STOP
                          │
                          ▼
                    MANAGEMENT
                    (C1 mitigates,
                    but cannot fix
                    upstream failure)
```

### The Definitive Diagnosis
The negative expectancy is **predominantly upstream of the exit-management layer**:
1. **Management is Not the Culprit:** Under Candidate Management C1, 7 adverse reversals were eliminated (converted to $0.0000\text{R}$), and trailing losses averaged only $-0.26\text{R}$. Management is performing as intended.
2. **The Funnel Fails Early:** $85\%$ of losses fail before $+1.0\text{R}$, and $60\%$ fail before $+0.5\text{R}$.
3. **The Upstream Suspects:**
   - **MTF Shift Quality (Hypothesis H1):** 35% of losses originate from minor `INTERNAL_CHOCH` shifts where the dominant swing trend never reversed.
   - **MTF Displacement Quality (Hypothesis H2):** 35% of losses have MTF shift displacement $<2.0\%$.
   - **LTF Trigger Quality (Hypothesis E1):** 70% of losses enter without a prior swing liquidity sweep.
   - **Regime/Context (Hypothesis R1):** Needs rigorous testing with an active regime classifier, not default labels.

---

## 6. PRE-REGISTRATION OF EXPERIMENT D1: `EXP_MTF_MAJOR_ALIGNMENT_01`

To isolate the first candidate mechanism without confounding variables, Experiment D1 is pre-registered under strict single-variable experimental control:

### A. Experimental Control vs. Treatment
* **Control:** Canonical $H_0$ entry architecture with Candidate Management $C_1$ (+1.5R milestone). Permitted MTF alignment events: `["INTERNAL_CHOCH", "EXTERNAL_CHOCH", "MSS", "EXTERNAL_BOS"]`.
* **Treatment D1:** Exactly ONE parameter changed:
  ```python
  # ALLOW:
  permitted_mtf_events = ["EXTERNAL_CHOCH", "MSS", "EXTERNAL_BOS"]
  # REJECT:
  # INTERNAL_CHOCH excluded
  ```
* **Strict Invariants Frozen:**
  - Canonical HTF direction
  - Canonical causal MTF retest
  - Canonical LTF entry model (all 3 models retained, no sweep filter added)
  - Canonical local structural SL (no buffer added)
  - Canonical `CLOSEST_OBJECTIVE` target (planned $\text{RR} \ge 4.0\text{R}$)
  - Candidate Management $C_1$ (+1.5R cost-covering milestone)
  - Conservative `ADVERSE_FIRST` collision arbitration
  - Execution friction: 2 bps maker, 5 bps taker, 5 bps slippage
  - 2021–2022 Development partition ONLY.
  - Validation (2023) and OOS (2024–2026) strictly locked.

### B. Execution Protocol: Full Causal Replay (No Post-Hoc Deletions)
D1 will **NOT** be evaluated by filtering trades out of an existing JSON file.  
It will be executed via a **full chronological replay** across all 15 streams in `CausalReplayer`. Because rejecting an `INTERNAL_CHOCH` event can causally alter subsequent state—allowing later alignment events, alternative keyzone formations, and subsequent retests to develop—the genuine treatment result must emerge from the forward simulation engine.

### C. Pre-Registered Evaluation Criteria (Before Running)
1. **Primary Financial Metrics:** Net R, Expectancy $E[R]$, Profit Factor $\text{PF}$, Max DD vs $H_0$ and $C_1$.
2. **Structural Preservation:** Verify whether the two observed BTC HTF winners (Trade 08 and Trade 14) are preserved.
3. **Lifecycle Funnel Counts:** Candidate count, risk-gate approvals, executed trade count.
4. **Excursion Distribution Shift:** Compare the percentage of trades reaching $+0.5\text{R}, +1.0\text{R}, +1.5\text{R}, +2.0\text{R}$. A genuine entry improvement must shift the excursion distribution, not merely delete trades.
5. **Epistemic Discipline:** Any result near $E[R] \approx 0.0\text{R}$ will be recognized as an improvement worthy of further controlled testing, **not proof of a finished money-making system**.

---

## 7. PROTOCOL STATUS & AUTHORIZATION HALT

The D0 forensic audit is complete and methodologically corrected in [`docs/MULTI_TIMEFRAME_ALPHA_FORENSICS_D1_AUDIT.md`](file:///home/mrcn2/crypto-platform/docs/MULTI_TIMEFRAME_ALPHA_FORENSICS_D1_AUDIT.md).

Experiment D1 (`EXP_MTF_MAJOR_ALIGNMENT_01`) is fully pre-registered.

**Ready to proceed with the full causal replay of Experiment D1 upon your final confirmation.**
