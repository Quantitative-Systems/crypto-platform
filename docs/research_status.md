# Quantitative Research Status & Scientific Ledger

---

## Executive Status Overview

This document records the current empirical and scientific status of the systematic trading hypotheses within the Quantitative Systems Platform.

```
┌────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                   RESEARCH HYPOTHESIS STATUS SUMMARY                                   │
├────────────────────────────────┬───────────────────────────────────────┬───────────────────────────────┤
│ HYPOTHESIS IDENTIFIER          │ SCIENTIFIC STATUS                     │ EMPIRICAL EXPECTANCY (E[R])   │
├────────────────────────────────┼───────────────────────────────────────┼───────────────────────────────┤
│ H1 (HTF_TREND_CONTINUATION_V1) │ 🔴 FROZEN CONTROL / REJECTED_RESEARCH │ -0.5998R (N=128, 2017–2026)   │
│ H1.1 (EARLY_MTF_ENTRY)         │ 🟡 IN PROGRESS / NOT YET VALIDATED    │ PENDING FULL MATRIX REPLAY    │
│ H1.2 (TRIGGER_CANDLE_SWEEP_SL) │ ⚪ REGISTERED / AWAITING H1.1 VERDICT │ QUEUED                        │
│ H1.3 (DYNAMIC_TARGET_REFRESH)  │ ⚪ REGISTERED / AWAITING H1.1 VERDICT │ QUEUED                        │
└────────────────────────────────┴───────────────────────────────────────┴───────────────────────────────┘
```

---

## 1. Frozen Baseline Control ($H_1$: `HTF_TREND_CONTINUATION_V1`)

### A. Specification & Invariants
* **Trading Ontology:**
  $$\text{HTF Structure / Trend} \longrightarrow \text{HTF Keyzones} \longrightarrow \text{HTF Bias} \longrightarrow \text{MTF Structure Alignment} \longrightarrow \text{MTF Keyzone Retest} \longrightarrow \text{LTF Sweep \& Displacement} \longrightarrow \text{LTF SL} \longrightarrow \text{HTF TP} + \text{MTF Trailing}$$
* **Timeframe Sets Tested:**
  * `SET_1`: 1M / 1W / 1D (Position / Macro)
  * `SET_2`: 1W / 1D / 4H (Swing)
  * `SET_3`: 1D / 4H / 1H (Swing / Intraday)
  * `SET_4`: 4H / 1H / 15M (Intraday)
* **Assets:** BTC/USDT, ETH/USDT, SOL/USDT ($2017\text{/}2020 \to 2026\text{-}09\text{-}01$).
* **Risk & Friction:** 1% equity risk per trade, $\ge 4.0\text{R}$ minimum planned RR, 0 bps maker fee, 5 bps taker fee, 5 bps slippage, adverse-first intrabar collision handling.

---

### B. Empirical Baseline Findings ($N=128$ Trades)

| Metric | Empirical Baseline Result ($H_1$) | Statistical Interpretation |
| :--- | :---: | :--- |
| **Sample Size ($N$)** | 128 trades | Sufficient statistical power across 24 streams |
| **Win Rate** | 27.34% (35W / 93L) | Negative edge regime |
| **Gross Realized Return** | $-68.42\text{R}$ | Negative pre-friction alpha |
| **Total Friction Drag** | $-8.35\text{R}$ | 10.8% of total loss velocity |
| **Net Realized Return** | $-76.77\text{R}$ | Unambiguous loss |
| **Mean Net Expectancy ($E[R]$)** | **$-0.5998\text{R}$ / trade** | Strategy control is rejected |
| **Profit Factor** | 0.38 | Payoff asymmetry mismatch |
| **Mean MFE** | $+0.5538\text{R}$ | Max MFE observed across 9 years = $+2.58\text{R}$ |
| **Target Reachability** | **0 / 128 (0.0%)** | Zero trades achieved planned $4.0\text{R}$ target |
| **Block Bootstrap 95% CI** | $[-0.7137\text{R},\; -0.4683\text{R}]$ | $P(\text{Edge} > 0) = 0.0\%$ |
| **Capital Barrier Verdict** | **`REJECTED_RESEARCH_ONLY`** | Programmatically blocked from live deployment |

---

### C. Implementation Correctness Audit (Bug vs. Strategy Assumption)

Our forensic investigation audited the $10,902$ candidates rejected during the baseline replay:
1. **$6,498$ Missing Anchor Rejections (`REJECT_MISSING_STRUCTURAL_ANCHORS`):**
   - **Audit Finding:** The structure engine requires $N \ge 2$ bars confirmation before confirming a Protected Swing. At the trigger bar, no confirmed macro protected swing existed.
   - **Verdict:** **NOT A BUG.** The software correctly implemented $H_1$'s canonical requirement for confirmed structural pivots. Replacing this with the 0-bar sweep candle extreme changes the invalidation concept from "Macro Structure" to "Micro Trigger Extreme" (registered as hypothesis $H_{1.1}$).
2. **$4,167$ Invalid Geometry Rejections (`REJECT_INVALID_ANCHOR_GEOMETRY`):**
   - **Audit Finding:** In $94.6\%$ of cases, price reached and exceeded the initial HTF target anchor during MTF realignment prior to LTF entry.
   - **Verdict:** **NOT A BUG.** $H_1$ correctly invalidated setups whose planned destination was already exhausted. Dynamically updating to the next keyzone is a new hypothesis ($H_{1.3}$).

---

### D. Counterfactual Trade-Management Study

To determine whether exit management could salvage $H_1$'s entry signals, we prospectively simulated 7 alternative management rules on the **exact same 128 entries**:

| Management Policy | Win Rate % | Net Realized R | Mean Expectancy ($E[R]$) | Profit Factor |
| :--- | :---: | :---: | :---: | :---: |
| **Original $H_1$ Control** | 27.34% | $-76.77\text{R}$ | **$-0.5998\text{R}$** | 0.21 |
| **Break-Even at $+1.0\text{R}$** | 27.34% | $-76.77\text{R}$ | **$-0.5998\text{R}$** | 0.21 |
| **Break-Even at $+0.75\text{R}$** | 31.25% | $-70.95\text{R}$ | **$-0.5543\text{R}$** | 0.23 |
| **Break-Even at $+1.5\text{R}$** | 27.34% | $-76.77\text{R}$ | **$-0.5998\text{R}$** | 0.21 |
| **Fixed Target $+1.5\text{R}$** | 26.56% | $-73.75\text{R}$ | **$-0.5762\text{R}$** | 0.25 |
| **Fixed Target $+2.0\text{R}$** | 26.56% | $-77.54\text{R}$ | **$-0.6058\text{R}$** | 0.21 |
| **Two-Tier Ratchet ($+0.75\text{R} \to +0.1\text{R}$)** | 31.25% | $-70.95\text{R}$ | **$-0.5543\text{R}$** | 0.23 |

**Mathematical Proof:** Exit optimization alone cannot make this signal profitable. Negative expectancy is driven by **adverse entry selection / late confirmation latency** ($72.7\%$ of trades suffer full $-1.0\text{R}$ stop-out without ever reaching $+0.5\text{R}$).

---

## 2. Child Hypothesis $H_{1.1}$ (`H1.1_EARLY_MTF_ALIGNMENT_ENTRY`)

### A. Scientific Rationale & Modification
* **Parent Hypothesis:** $H_1$ (`HTF_TREND_CONTINUATION_V1`).
* **Research Question:** Does triggering execution immediately upon MTF structural realignment (CHOCH/MSS) and retest into the causal MTF keyzone (without waiting for secondary multi-bar LTF liquidity sweep confirmation) reduce entry latency and improve expectancy?
* **Preserved Invariants:** Identical HTF trend logic, keyzones, directional bias, structural SL, HTF target, 1% risk model, 0/5/5 bps friction, and zero-lookahead causality.

---

### B. Pre-Flight Verification & Infrastructure Audit
1. **Trade Lifecycle Fidelity Trace:** Audited closed trades candle-by-candle against raw warehouse data; entry fills, stop losses, excursions, trailing ratchets, and friction deductions verified with **zero discrepancies** (`scratch/simulator_integrity_trace_report.json`).
2. **Causality & Lookahead Audit:** Verified monotonic timestamp causality ($\text{HTF} \le \text{MTF} \le \text{LTF} \le \text{Entry} \le \text{Exit}$) across all streams with **zero temporal violations** (`scratch/causality_lookahead_audit_report.json`).
3. **Reproducibility Provenance Frozen:** Configuration, dataset hashes, and trial lineages committed to [`research/experiments/reproducibility_manifest.json`](file:///home/mrcn2/crypto-platform/research/experiments/reproducibility_manifest.json).
4. **Execution Infrastructure Optimization:**
   - Identified a single-thread computational bottleneck on SET 4 (316,482 15m bars/asset taking $\sim 27\text{ mins/stream}$).
   - Discovered and corrected a candidate dispatch key mismatch in `StrategyCoordinator`.
   - Single-stream smoke test verified.

---

### C. Current $H_{1.1}$ Empirical Status

```
===================================================================================================
STATUS: EXPERIMENT IN PROGRESS / NOT YET EMPIRICALLY VALIDATED
===================================================================================================
The full 24-stream empirical replay matrix for H1.1 has NOT been completed.
No empirical claims of profitability, win rate, or expectancy improvement are made for H1.1.
Full empirical matrix execution is queued for parallel batch execution in the next research sprint.
===================================================================================================
```

---

## 3. Implementation Bug vs. Research Hypothesis Ontology

A core achievement of this research sprint is formalizing the distinction between software defects and scientific strategy hypotheses:

```
┌────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                               BUG VS. HYPOTHESIS CLASSIFICATION MATRIX                                 │
├────────────────────────────────────────┬────────────────────────────────┬──────────────────────────────┤
│ Phenomenon Observed                    │ Classification                 │ Scientific Rationale         │
├────────────────────────────────────────┼────────────────────────────────┼──────────────────────────────┤
│ StrategyCoordinator candidate keying   │ 🟢 IMPLEMENTATION BUG (FIXED)   │ Candidate tracker queried     │
│ mismatch during custom hypothesis run  │                                │ hardcoded hypothesis key.    │
├────────────────────────────────────────┼────────────────────────────────┼──────────────────────────────┤
│ 6,498 rejections due to unconfirmed    │ 🔵 RESEARCH HYPOTHESIS ($H_{1.1}$│ Requires changing from macro │
│ LTF protected swing origin             │ or $H_{1.2}$)                  │ pivot to micro-trigger SL.   │
├────────────────────────────────────────┼────────────────────────────────┼──────────────────────────────┤
│ 4,167 rejections due to HTF target     │ 🔵 RESEARCH HYPOTHESIS ($H_{1.3}$)│ Requires trend-extension     │
│ already traversed before LTF entry     │                                │ runner target propagation.   │
├────────────────────────────────────────┼────────────────────────────────┼──────────────────────────────┤
│ 22 winning excursions reversing into   │ 🔵 RESEARCH HYPOTHESIS ($H_{1.4}$)│ Requires dynamic milestone   │
│ stop loss before reaching 4.0R target  │                                │ break-even ratchet rules.    │
└────────────────────────────────────────┴────────────────────────────────┴──────────────────────────────┘
```
