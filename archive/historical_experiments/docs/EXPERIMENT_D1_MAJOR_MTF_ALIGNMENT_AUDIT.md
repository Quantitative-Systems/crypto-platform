# EXPERIMENT D1: CONTROLLED MTF MAJOR SWING ALIGNMENT AUDIT
**Experiment ID**: `EXP_MTF_MAJOR_ALIGNMENT_01`  
**Execution Environment**: Strict Forward Causal Simulation Replay (No Post-Hoc Trade Deletions)  
**Partition**: Development (2021-01-01 to 2022-12-31 UTC)  
**Universe**: BTC/USDT, ETH/USDT, SOL/USDT across 15 Multi-Timeframe Streams (`SET_1` through `SET_5`)  
**Status**: COMPLETED — SINGLE-VARIABLE HYPOTHESIS EVALUATED  
**Date**: September 2026  

---

## 1. Executive Summary & Epistemic Calibration

This audit reports the empirical findings from **Experiment D1 (`EXP_MTF_MAJOR_ALIGNMENT_01`)**, executed as a single-variable controlled experiment within the canonical multi-timeframe strategy architecture.

Following critical methodological scrutiny, this experiment was conducted **not** under the premise that `INTERNAL_CHOCH` was the proven root cause of strategy failure, but as a **tightly controlled hypothesis test** to determine whether rejecting minor sub-structure shifts (`INTERNAL_CHOCH`) in favor of major swing structural events (`EXTERNAL_CHOCH`, `MSS`, `EXTERNAL_BOS`) improves the early-excursion profile and realized expectancy of the strategy funnel.

```
                   FROZEN ARCHITECTURAL PIPELINE (D1)
HTF DIRECTION ──► MTF SETUP ──► [MAJOR MTF ALIGNMENT ONLY] ──► CAUSAL RETEST
                                          │
                                 REJECT: INTERNAL_CHOCH
                                 ALLOW:  EXTERNAL_CHOCH, MSS, EXTERNAL_BOS
                                          │
                                          ▼
   LTF ENTRY ──► LOCAL SL ──► CLOSEST_OBJECTIVE ──► C1 MILESTONE (+1.5R/0.0R)
```

### Key Quantitative Findings

| Metric | H0 (Canonical Baseline) | C1 (Cost-Covering Milestone) | D1 (Major MTF Alignment Only) | Delta (D1 vs C1) |
| :--- | :---: | :---: | :---: | :---: |
| **Total Executed Trades** | 29 | 29 | **24** | -5 trades (-17.2%) |
| **Win Rate** | 6.90% | 24.14% | **25.00%** | +0.86% |
| **Net Realized R** | -15.5185R | -6.1605R | **-2.8752R** | **+3.2853R** |
| **Expectancy ($E[R]$)** | -0.5351R | -0.2124R | **-0.1198R** | **+0.0926R** |
| **Profit Factor** | 0.3871 | 0.6141 | **0.7732** | +0.1591 |
| **Max Drawdown** | 15.5185R | 8.7582R | **7.6622R** | -1.0960R |
| **Median MFE ($R$)** | 0.8185R | 0.7778R | **0.7248R** | -0.0530R |
| **Median MAE ($R$)** | 1.2308R | 1.2014R | **1.1632R** | -0.0382R |
| **Observed Winners Preserved** | 2 / 2 (100%) | 2 / 2 (100%) | **2 / 2 (100%)** | 0 lost |
| **Full Initial SL Exits** | 20 (69.0%) | 13 (44.8%) | **10 (41.7%)** | -3 stop-outs |
| **Breakeven Trailed Exits** | 0 (0.0%) | 7 (24.1%) | **6 (25.0%)** | -1 BE exit |
| **MTF Trailed Scratches** | 7 (24.1%) | 7 (24.1%) | **6 (25.0%)** | -1 scratch |

### Epistemic Summary

1. **Material Improvement, But Still Negative**: D1 cuts the remaining loss of C1 by more than half (improving Net R from $-6.1605\text{R}$ to $-2.8752\text{R}$ and Expectancy from $-0.2124\text{R}$ to $-0.1198\text{R}$). Profit factor rises to $0.7732$.
2. **Gemini's Predicted "-0.59R" Refuted by Causal Physics**: Gemini's post-hoc filtering assumption claimed that rejecting `INTERNAL_CHOCH` would delete 8 losing trades and yield $-0.59\text{R}$ on $N=21$. In actual forward causal replay, the state machine behaves causally: rejecting `INTERNAL_CHOCH` did not delete 8 trades. Instead, two setups simply waited for subsequent major alignment (`EXTERNAL_BOS`) and still entered, resulting in $N=24$ and Net R = $-2.8752\text{R}$. This demonstrates why forward causal simulation is non-negotiable.
3. **The Core Upstream Problem Survives**: D1 does **not** cure the fundamental entry-funnel excursion problem: **$45.8\%$ (11/24) of trades still fail before reaching $+0.5\text{R}$**, and **$54.2\%$ (13/24) fail before reaching $+1.0\text{R}$**. The median MFE remains low ($0.7248\text{R}$).
4. **Conclusion**: D1 is an informative, supportive structural refinement, but the strategy does not yet possess positive expectancy. In accordance with strict research protocol, **Experiment D1 remains in Development and is NOT authorized for 2023 Validation.**

---

## 2. Forensic Corrections & Epistemic Audit of Prior Claims

Before detailing D1, we document the resolution of the methodological critiques raised during the review:

### A. The "100% RANGE_CHOP" Discovery Debunked as a Dataclass Default
* **Initial Claim**: The D0 report claimed that "100% of C1 losses occurred in RANGE_CHOP."
* **Code Provenance Audit**: Direct inspection of `research/simulation/trade_ledger.py` (line 52) and `research/replayer/causal_replayer.py` (lines 279–295) revealed that `SimulatedTrade` declares a hardcoded default field:
  ```python
  trend_regime: str = "RANGE_CHOP"
  ```
  Because `enable_regime_filter=False` was set in the canonical baseline replay, `CausalReplayer` never passed or populated a calculated `trend_regime` into `SimulatedTrade`. Consequently, every trade in the ledger inherited `"RANGE_CHOP"` by default.
* **Correction**: The market environment was **not** empirically verified to be 100% range chop. In fact, `structural_provenance["htf_phase"]` records `MarketPhase.EXPANSION` for multiple trades. The claim of "100% range chop failure" was a software artifact, not market truth.

### B. LTF Trigger Semantics: Resolution of Contradiction on Trade 16
* **Initial Contradiction**: The D0 ledger listed Trade 16 as having `LTF Trigger: SWEEP_AND_DISP` while simultaneously showing `Sweep: No Sweep`.
* **Root Cause**: The audit script had used ad-hoc string matching (`"SWEEP" in ltf_trigger_reason`) rather than inspecting the true state-machine trigger provenance emitted by `LTFEntryModel.evaluate_details()`.
* **Resolved Engine Provenance**: In the causal engine:
  - `LTFEntryModel` evaluates `SYNTHETIC_SWEEP_AND_DISPLACEMENT` first. If confirmed, it records `reversal_reason = "LTF_SWEEP_AND_DISPLACEMENT_CONFIRMED"`.
  - If no sweep occurred, it falls back to `DirectionalDisplacementReversal`, recording `reversal_reason = "BULLISH_DISPLACEMENT_CONFIRMED"` or `"BEARISH_DISPLACEMENT_CONFIRMED"`.
  - In D1, exactly **6 of 24 trades (25.0%)** entered via genuine causal sweeps, while **18 of 24 trades (75.0%)** entered via single-candle directional displacement without prior sweep.

### C. Disentangling Class H: Separating H1 and H2
* **Initial Conflation**: The original draft lumped `INTERNAL_CHOCH` and MTF displacement $<2.0\%$ into a single bucket ("Class H").
* **Separation**: These are independent dimensions:
  - **H1 (Minor Sub-Structure Alignment: `INTERNAL_CHOCH`)**: 7 trades in C1 (now isolated in D1).
  - **H2 (Weak MTF Displacement $<2.0\%$)**: 7 trades in C1.
  - Crucially, multiple `EXTERNAL_CHOCH` trades had weak displacement (e.g., T27 at 1.06%, T28 at 0.62%), while several `INTERNAL_CHOCH` trades had strong displacement (e.g., T24 at 3.26%, T22 at 3.07%). They are separate research hypotheses.

### D. Re-Calibrating the $N_{\text{winners}}=2$ Finding
* **Epistemic Constraint**: Observing that the two winners (BTC T08: `EXTERNAL_CHOCH`, BTC T14: `MSS`) came from major swings proves only that *the two observed winners did not originate from `INTERNAL_CHOCH`*. With $N=2$, this cannot establish that major shifts universally produce alpha.
* **Counter-Examples**:
  - **Trade 04 / T06** (`EXTERNAL_CHOCH`, 2.83% displacement, MFE $+3.35\text{R}$) failed to reach target and was stopped on MTF trailing at $-0.09\text{R}$.
  - **Trade 18 / T22** (`INTERNAL_CHOCH` in C1, `EXTERNAL_BOS` in D1, 3.07% displacement, MFE $+1.83\text{R}$) reached substantial excursion despite origin.

---

## 3. Controlled Experiment D1 Specification

To ensure scientific validity, exactly **one variable** was altered relative to the frozen C1 control.

### Invariant Control Parameters (Frozen)
1. **Universe**: BTC/USDT, ETH/USDT, SOL/USDT.
2. **Timeframe Sets**: `SET_1` (1M/1W/1D), `SET_2` (1W/1D/4H), `SET_3` (1D/4H/1H), `SET_4` (4H/1H/15m), `SET_5` (15m/5m/1m - fail closed).
3. **Partition**: 2021-01-01 00:00:00 to 2022-12-31 23:59:59 UTC (Strict Development Partition).
4. **HTF Context**: Causal HTF trend, directional bias, and KeyZone interaction.
5. **MTF Retest**: Causal KeyZone collision and retest timing.
6. **LTF Entry Model**: Multi-model priority hierarchy (`LTFEntryModel`).
7. **SL Geometry**: Local LTF structural invalidation price.
8. **Target Geometry**: `CLOSEST_OBJECTIVE` (HTF destination).
9. **Exit Management**: Candidate Management C1 (+1.5R cost-covering breakeven milestone).
10. **Execution Mechanics**: 2 bps maker, 5 bps taker, 5 bps adverse slippage, `ADVERSE_FIRST` intrabar collision policy.
11. **Locks**: Validation 2023 strictly locked. OOS 2024–2026 strictly locked.

### Single-Variable Treatment
* **Control**: Permitted MTF alignment events: `["INTERNAL_CHOCH", "EXTERNAL_CHOCH", "MSS", "EXTERNAL_BOS"]`.
* **Treatment (D1)**: Permitted MTF alignment events: `["EXTERNAL_CHOCH", "MSS", "EXTERNAL_BOS"]`.
  - In `strategy_engine/hypotheses/unified_strategy.py` (`WAIT_MTF_ALIGNMENT`):
    ```python
    if self.enable_major_mtf_only and "INTERNAL_CHOCH" in str(event.event_type):
        continue
    ```

---

## 4. Full Causal Replay: Complete 24-Trade Ledger

The table below presents all 24 executed trades produced by the forward causal simulation of Experiment D1:

| # | UTC Entry | Symbol | Stream ID | Dir | Net R | MFE ($R$) | MAE ($R$) | MTF Structural Event | LTF Trigger Reason | Exit Reason |
| :-: | :--- | :--- | :--- | :-: | :---: | :---: | :---: | :--- | :--- | :--- |
| **00** | 2021-02-07 00:45 | SOL/USDT | `SOL_SET_4` | LONG | **-1.0615R** | 0.00R | 1.39R | `EXTERNAL_CHOCH` | `BULLISH_DISPLACEMENT_CONFIRMED` | `INITIAL_LTF_SL` |
| **01** | 2021-02-18 15:45 | SOL/USDT | `SOL_SET_4` | LONG | **-1.0846R** | 0.47R | 1.20R | `MSS` | `BULLISH_DISPLACEMENT_CONFIRMED` | `INITIAL_LTF_SL` |
| **02** | 2021-03-05 06:00 | ETH/USDT | `ETH_SET_3` | LONG | **-1.1043R** | 0.03R | 1.74R | `MSS` | `BULLISH_DISPLACEMENT_CONFIRMED` | `INITIAL_LTF_SL` |
| **03** | 2021-04-23 20:00 | BTC/USDT | `BTC_SET_4` | SHRT | **-1.0911R** | 0.00R | 1.37R | `EXTERNAL_BOS` | `BEARISH_DISPLACEMENT_CONFIRMED` | `INITIAL_LTF_SL` |
| **04** | 2021-04-28 17:45 | SOL/USDT | `SOL_SET_4` | LONG | **-0.0933R** | 3.35R | 0.24R | `EXTERNAL_CHOCH` | `BULLISH_DISPLACEMENT_CONFIRMED` | `MTF_STRUCTURAL_TRAIL` |
| **05** | 2021-05-12 13:00 | BTC/USDT | `BTC_SET_4` | SHRT | **+4.1077R** | 5.21R | 0.65R | `EXTERNAL_CHOCH` | `BEARISH_DISPLACEMENT_CONFIRMED` | `HTF_TP` |
| **06** | 2021-05-14 09:00 | SOL/USDT | `SOL_SET_3` | SHRT | **+0.0000R** | 5.04R | 1.81R | `MSS` | `BEARISH_DISPLACEMENT_CONFIRMED` | `BREAKEVEN_TRAIL` |
| **07** | 2021-06-08 17:30 | ETH/USDT | `ETH_SET_4` | SHRT | **+0.0000R** | 2.10R | 2.06R | `MSS` | `BEARISH_DISPLACEMENT_CONFIRMED` | `BREAKEVEN_TRAIL` |
| **08** | 2021-08-08 20:45 | SOL/USDT | `SOL_SET_4` | SHRT | **-0.1190R** | 0.93R | 0.87R | `MSS` | `LTF_SWEEP_AND_DISP_CONFIRMED` | `MTF_STRUCTURAL_TRAIL` |
| **09** | 2021-08-09 10:00 | BTC/USDT | `BTC_SET_3` | SHRT | **-0.4625R** | 0.00R | 0.57R | `EXTERNAL_CHOCH` | `LTF_SWEEP_AND_DISP_CONFIRMED` | `MTF_STRUCTURAL_TRAIL` |
| **10** | 2021-12-08 18:00 | BTC/USDT | `BTC_SET_3` | SHRT | **+5.6955R** | 5.93R | 0.46R | `MSS` | `LTF_SWEEP_AND_DISP_CONFIRMED` | `HTF_TP` |
| **11** | 2021-12-30 08:00 | SOL/USDT | `SOL_SET_3` | SHRT | **+0.0000R** | 1.54R | 0.86R | `EXTERNAL_CHOCH` | `BEARISH_DISPLACEMENT_CONFIRMED` | `BREAKEVEN_TRAIL` |
| **12** | 2022-01-26 13:00 | SOL/USDT | `SOL_SET_2` | SHRT | **-1.0793R** | 1.25R | 1.20R | `EXTERNAL_BOS` | `LTF_SWEEP_AND_DISP_CONFIRMED` | `INITIAL_LTF_SL` |
| **13** | 2022-01-27 16:00 | SOL/USDT | `SOL_SET_2` | SHRT | **-0.2804R** | 0.48R | 0.35R | `EXTERNAL_BOS` | `LTF_SWEEP_AND_DISP_CONFIRMED` | `MTF_STRUCTURAL_TRAIL` |
| **14** | 2022-01-31 01:00 | SOL/USDT | `SOL_SET_2` | SHRT | **+0.0000R** | 1.82R | 1.95R | `EXTERNAL_BOS` | `BEARISH_DISPLACEMENT_CONFIRMED` | `BREAKEVEN_TRAIL` |
| **15** | 2022-02-09 23:00 | SOL/USDT | `SOL_SET_3` | LONG | **-0.0000R** | 2.19R | 0.49R | `EXTERNAL_BOS` | `BULLISH_DISPLACEMENT_CONFIRMED` | `BREAKEVEN_TRAIL` |
| **16** | 2022-02-10 03:00 | SOL/USDT | `SOL_SET_4` | LONG | **-1.1180R** | 0.00R | 1.85R | `MSS` | `BULLISH_DISPLACEMENT_CONFIRMED` | `INITIAL_LTF_SL` |
| **17** | 2022-02-15 14:00 | SOL/USDT | `SOL_SET_3` | LONG | **-1.1137R** | 0.00R | 2.08R | `MSS` | `LTF_SWEEP_AND_DISP_CONFIRMED` | `INITIAL_LTF_SL` |
| **18** | 2022-08-14 11:30 | SOL/USDT | `SOL_SET_4` | SHRT | **-0.1120R** | 1.83R | 1.12R | `EXTERNAL_BOS` | `BEARISH_DISPLACEMENT_CONFIRMED` | `MTF_STRUCTURAL_TRAIL` |
| **19** | 2022-08-19 12:00 | SOL/USDT | `SOL_SET_3` | SHRT | **-0.6926R** | 0.52R | 0.92R | `MSS` | `BEARISH_DISPLACEMENT_CONFIRMED` | `MTF_STRUCTURAL_TRAIL` |
| **20** | 2022-08-20 23:30 | ETH/USDT | `ETH_SET_4` | SHRT | **-1.0793R** | 0.42R | 1.05R | `EXTERNAL_BOS` | `BEARISH_DISPLACEMENT_CONFIRMED` | `INITIAL_LTF_SL` |
| **21** | 2022-10-18 10:00 | BTC/USDT | `BTC_SET_3` | LONG | **-0.0000R** | 1.69R | 0.90R | `EXTERNAL_BOS` | `BULLISH_DISPLACEMENT_CONFIRMED` | `BREAKEVEN_TRAIL` |
| **22** | 2022-12-07 19:45 | ETH/USDT | `ETH_SET_4` | SHRT | **-1.0960R** | 0.10R | 2.10R | `EXTERNAL_CHOCH` | `BEARISH_DISPLACEMENT_CONFIRMED` | `INITIAL_LTF_SL` |
| **23** | 2022-12-31 08:45 | SOL/USDT | `SOL_SET_4` | SHRT | **-1.0909R** | 0.00R | 1.23R | `EXTERNAL_CHOCH` | `BEARISH_DISPLACEMENT_CONFIRMED` | `INITIAL_LTF_SL` |

---

## 5. Causal Lifecycle Attribution: C1 vs. D1

Comparing the C1 ledger ($N=29$) with the D1 ledger ($N=24$) reveals how the causal state machine responded to the rejection of `INTERNAL_CHOCH`:

### Trades Eliminated in D1 (5 Trades)
1. **BTC/USDT `BTC_SET_3` (2021-01-19 15:31)**:
   - C1: `INTERNAL_CHOCH` $\rightarrow$ `INITIAL_LTF_SL` ($-1.0604\text{R}$, MFE $0.00\text{R}$).
   - D1: Candidate ignored `INTERNAL_CHOCH`; no subsequent major alignment occurred. **Eliminated (Saved $1.06\text{R}$)**.
2. **SOL/USDT `SOL_SET_3` (2021-05-18 18:02)**:
   - C1: `INTERNAL_CHOCH` $\rightarrow$ `MTF_STRUCTURAL_TRAIL` ($-0.0526\text{R}$, MFE $0.75\text{R}$).
   - D1: Ignored; no major alignment occurred. **Eliminated (Saved $0.05\text{R}$)**.
3. **SOL/USDT `SOL_SET_3` (2021-09-04 21:49)**:
   - C1: `INTERNAL_CHOCH` $\rightarrow$ `INITIAL_LTF_SL` ($-1.0758\text{R}$, MFE $0.82\text{R}$).
   - D1: Ignored; no major alignment occurred. **Eliminated (Saved $1.08\text{R}$)**.
4. **SOL/USDT `SOL_SET_4` (2021-12-14 16:37)**:
   - C1: `INTERNAL_CHOCH` $\rightarrow$ `BREAKEVEN_TRAIL` ($+0.0000\text{R}$, MFE $1.95\text{R}$).
   - D1: Ignored; no major alignment occurred. **Eliminated (BE trade lost)**.
5. **SOL/USDT `SOL_SET_4` (2022-09-01 04:39)**:
   - C1: `INTERNAL_CHOCH` $\rightarrow$ `INITIAL_LTF_SL` ($-1.0960\text{R}$, MFE $0.78\text{R}$).
   - D1: Ignored; no major alignment occurred. **Eliminated (Saved $1.10\text{R}$)**.

**Total R preserved from eliminated trades**: $+1.0604 + 0.0526 + 1.0758 - 0.0000 + 1.0960 = \mathbf{+3.2848R}$.

### The Causal Persistence Phenomenon (Why N=24, Not N=21)
In C1, there were 7 trades that initially recorded `INTERNAL_CHOCH`. Why were only 5 eliminated?
* **Trade 03 (`BTC_SET_4`, 2021-04-23)**: In C1, this trade entered on an `INTERNAL_CHOCH`. When `INTERNAL_CHOCH` was rejected in D1, the candidate did not expire—it remained in `WAIT_MTF_ALIGNMENT`. An `EXTERNAL_BOS` immediately triggered on that MTF candle, satisfying the major-only requirement. The trade entered on the same setup and hit its initial stop loss ($-1.0911\text{R}$).
* **Trade 18 (`SOL_SET_4`, 2022-08-14)**: In C1, this trade entered on `INTERNAL_CHOCH` ($-0.1120\text{R}$). In D1, the candidate skipped the internal shift, aligned with `EXTERNAL_BOS`, and completed the exact same trailed scratch exit ($-0.1120\text{R}$).

This proves why theoretical/post-hoc deletion of trades is methodologically invalid: **in an event-driven state machine, rejecting one trigger allows later or coincident triggers to be captured causally.**

---

## 6. MFE Excursion Distribution: Entry Quality Remains Deficient

The user's primary observation from D0 was:
> *"The current entry funnel has a very poor early-excursion distribution... negative expectancy is predominantly upstream of the exit-management layer."*

Does D1 fix this upstream failure? Let us examine the empirical MFE distribution:

| MFE Bracket | C1 Distribution ($N=29$) | D1 Distribution ($N=24$) | Interpretation |
| :--- | :---: | :---: | :--- |
| **$< 0.5\text{R}$** | 12 / 29 (41.4%) | **11 / 24 (45.8%)** | **Unchanged/Worse**: Nearly half of all trades fail immediately without reaching $+0.5\text{R}$. |
| **$0.5\text{R} - 1.0\text{R}$** | 5 / 29 (17.2%) | **2 / 24 (8.3%)** | Filtered internal shifts had modest traction ($0.5-0.8\text{R}$) before stopping out. |
| **$1.0\text{R} - 1.5\text{R}$** | 1 / 29 (3.4%) | **1 / 24 (4.2%)** | Rarely stalls in this bracket. |
| **$1.5\text{R} - 2.0\text{R}$** | 5 / 29 (17.2%) | **4 / 24 (16.7%)** | Consistent capture of $+1.5\text{R}$ milestone. |
| **$\ge 2.0\text{R}$** | 6 / 29 (20.7%) | **6 / 24 (25.0%)** | Full preservation of all 6 large excursions ($\ge 2.0\text{R}$). |
| **Cumulative $< 1.0\text{R}$** | 17 / 29 (58.6%) | **13 / 24 (54.2%)** | **Majority still fail early.** |

### Distribution Verdict
* **Early Excursion Failure Persists**: While D1 filtered 3 full losses, **11 of the 24 remaining trades (45.8%) never reached even $+0.5\text{R}$** (7 trades had $\text{MFE} = 0.00\text{R}$).
* **Median MFE**: Decreased slightly from $0.7778\text{R}$ (C1) to $0.7248\text{R}$ (D1) because the eliminated trades included some that reached $+0.75\text{R}$ to $+0.82\text{R}$ before reversing.
* **Conclusion**: Major MTF alignment reduces catastrophic noise from sub-structure breaks, but **it does not resolve the poor early traction of the remaining setups**. The root of negative expectancy remains active in the remaining 24 trades.

---

## 7. Deep Analysis: Liquidity Sweep vs. Single-Candle Displacement in D1

In D1, we now have unambiguous causal provenance on the LTF entry mechanism:

| LTF Entry Model | Trades ($N=24$) | Winners ($>1\text{R}$) | BE Trailed | Scratches ($<0\text{R}$) | Full SL Exits | Net Realized R | Expectancy |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **LTF Sweep + Displacement** | 6 (25.0%) | 1 (T10: +5.70R) | 0 | 3 (-0.86R) | 2 (-2.19R) | **+2.6406R** | **+0.4401R** |
| **Single-Candle Displacement (No Sweep)** | 18 (75.0%) | 1 (T05: +4.11R) | 6 | 3 (-0.89R) | 8 (-8.72R) | **-5.5158R** | **-0.3064R** |

### Critical Observation
* When entries occurred with a confirmed **LTF liquidity sweep prior to displacement** (6 trades), the realized Net R was **positive (+2.64R)**, producing a positive sample expectancy of $+0.44\text{R}$.
* When entries occurred on **single-candle displacement without a prior sweep** (18 trades), 8 resulted in immediate initial stop-outs, producing a deeply negative Net R of **$-5.52\text{R}$**.
* **Epistemic Caution**: While this observation is mathematically striking, $N=6$ vs $N=18$ is a small sample. It provides strong support for testing LTF sweep confirmation in future research, but must not be treated as absolute proof without independent verification.

---

## 8. Success Criteria Evaluation & Verdict

### Pre-Registered Success Criteria

| Evaluation Criterion | Pre-Registered Standard | Observed Result | Status |
| :--- | :--- | :--- | :---: |
| **Primary Metric (Expectancy)** | Material improvement towards $E[R] \ge 0$ | Improved from $-0.2124\text{R}$ to $-0.1198\text{R}$ | **PARTIAL PASS (Still $<0$)** |
| **Net Realized R** | Reduction in drawdown / net loss | Improved from $-6.1605\text{R}$ to $-2.8752\text{R}$ (+3.29R) | **PASS** |
| **Structural Preservation** | Preserve BTC winners T08 and T14 | 100% preserved (+4.11R and +5.70R intact) | **PASS** |
| **Trade Count Stability** | Maintain sufficient sample ($N \ge 20$) | $N=24$ executed across 15 streams | **PASS** |
| **Excursion Distribution** | Shift MFE distribution upward | $<0.5\text{R}$ remains 45.8%; median MFE 0.72R | **FAIL** |
| **Validation Gate** | Must demonstrate $E[R] > 0$ before 2023 lock | Expectancy remains negative ($-0.1198\text{R}$) | **FAIL (DO NOT ADVANCE)** |

---

## 9. Final Research Directives & Next Steps

1. **Retain D1 as a Supported Development Baseline**:
   - `enable_major_mtf_only` is proven to reduce negative noise and eliminate 3 catastrophic full stop-outs without hurting large-excursion winners.
   - It is incorporated into the development code under `EXP_MTF_MAJOR_ALIGNMENT_01`.
2. **Strictly Enforce the Validation Lock**:
   - **Do NOT run 2023 Validation.**
   - Advancing a system with negative expectancy ($-0.1198\text{R}$) to Validation would violate scientific governance.
3. **Strictly Halt Execution on D2 and E1**:
   - As directed by the user, **D2 (MTF Retest Depth) and E1 (LTF Liquidity Sweep) are NOT executed.**
   - All empirical findings, causal ledger comparisons, and script modifications are now fully documented and submitted for user review.
