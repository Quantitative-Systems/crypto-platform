# MASTER ENGINEERING REPORT — PHASE 10.3
## H_SL_ATR_01 — ATR Stop Distance Floor Sweep Evaluation

**Temporal Partition**: `2021-01-01` through `2022-12-31` (Strict Development Partition)  
**Benchmark Control**: `Phase 10.2 Research Control (H_KZ_FRESH_01 = 7d)`  
**Execution Timestamp**: `2026-09-07T16:07:13.025858+00:00`  
**Status**: RESEARCH ONLY — CANONICAL STRATEGY REMAINS FROZEN  
**Final Scientific Verdict**: **`UNSUPPORTED`**  

---

## Executive Summary

Phase 10.3 evaluates hypothesis **`H_SL_ATR_01`** (Minimum Stop Distance ATR Floor):
$$\text{stop\_distance} = |\text{entry\_price} - \text{stop\_invalidation\_price}| < \theta_{\text{ATR}} \times \text{ATR}_{14}$$

If $\text{stop\_distance} < \theta_{\text{ATR}} \times \text{ATR}_{14}$, the candidate setup is rejected with rejection reason `REJECT_SL_BELOW_ATR_FLOOR`.

The pre-registered six thresholds evaluated are: **0.50, 0.60, 0.70, 0.80, 0.90, and 1.00 ATR**, benchmarked directly against the frozen **Phase 10.2 research control (`H_KZ_FRESH_01 = 7d`)**.

### Key Audit Outcomes:
1. **Negative Regimes at Low Thresholds (0.50–0.70 ATR)**: While 0.50–0.70 ATR preserves 100% of winners, the strategy remains firmly in net negative performance ($-10.66\text{R}$, $-9.54\text{R}$, and $-2.96\text{R}$), with Profit Factor below 1.0 (0.67, 0.70, 0.88) and negative expectancy. It does not establish profitability.
2. **Catastrophic Winner Destruction at Higher Thresholds (0.90–1.00 ATR)**: At 0.90 ATR, **1 out of 4 winners (25%) is pruned**. At 1.00 ATR, **2 out of 4 winners (50%) are destroyed**. This violates the core mandate requiring improvement without unacceptable loss of winners.
3. **Knife-Edge Artifact at 0.80 ATR**: The single threshold that produces a nominally positive Net R ($+2.48\text{R}$, PF 1.13) sits directly on a precipitous cliff: Winner 1 has an initial stop distance of **0.85 ATR**, just 0.05 ATR away from elimination. Moreover, throughput drops by 44% (down to 22 trades across 15 streams in 24 months, or ~0.7 trades/stream/year), providing zero statistical significance.
4. **Engineering Decision**: Under Decision Rule 1, `H_SL_ATR_01` fails to improve the primary economic objective without unacceptable loss of winners or throughput. **`H_SL_ATR_01` is marked UNSUPPORTED and rejected.**

---

## 1. Comprehensive Sweep Matrix vs Phase 10.2 Control

| Configuration | Threshold | Trades | Setups (Uniq/Dup) | W / L | Win Rate | Gross R | Net R | Net R Delta | PF (Delta) | Max DD (Delta) | Exp / Trade | Winner Pres (%) | Losses Rem | Wins Rem | Rejections |
|---|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **CONTROL_7D** | None (Control) | 39 | 20 / 19 | 4 / 35 | 10.3% | -12.8176R | **-16.2248R** | **0.0000R** | 0.58 | 25.26R | -0.4160R | **100.0%** | 0 | 0 | 0 |
| **0.50_ATR** | 0.50 ATR | 34 | 18 / 16 | 4 / 30 | 11.8% | -7.8181R | **-10.6608R** | **+5.5640R** | 0.67 (+0.09) | 18.37R (-6.89R) | -0.3136R | **100.0%** | 5 | 0 | 5 |
| **0.60_ATR** | 0.60 ATR | 33 | 17 / 16 | 4 / 29 | 12.1% | -6.8186R | **-9.5444R** | **+6.6804R** | 0.70 (+0.12) | 17.25R (-8.01R) | -0.2892R | **100.0%** | 6 | 0 | 6 |
| **0.70_ATR** | 0.70 ATR | 27 | 15 / 12 | 4 / 23 | 14.8% | -0.8206R | **-2.9634R** | **+13.2614R** | 0.88 (+0.30) | 13.96R (-11.30R) | -0.1098R | **100.0%** | 12 | 0 | 12 |
| **0.80_ATR** | 0.80 ATR | 22 | 12 / 10 | 4 / 18 | 18.2% | 4.1819R | **2.4780R** | **+18.7028R** | 1.13 (+0.55) | 10.75R (-14.51R) | 0.1126R | **100.0%** | 17 | 0 | 17 |
| **0.90_ATR** | 0.90 ATR | 15 | 9 / 6 | 3 / 12 | 20.0% | 4.4518R | **3.2692R** | **+19.4940R** | 1.25 (+0.67) | 5.48R (-19.78R) | 0.2179R | **75.0%** | 23 | 1 | 24 |
| **1.00_ATR** | 1.00 ATR | 9 | 6 / 3 | 2 / 7 | 22.2% | 5.3337R | **4.5970R** | **+20.8218R** | 1.60 (+1.02) | 3.30R (-21.96R) | 0.5108R | **50.0%** | 28 | 2 | 30 |

---

## 2. Winner Preservation Audit Across ATR Thresholds

Mandate: Explicitly audit every single baseline winner against all six evaluated ATR thresholds.

| Winner Trade ID | Asset | TF Set | Entry Time (UTC) | Initial SL ATR Mult | Realized Net R | 0.50 ATR | 0.60 ATR | 0.70 ATR | 0.80 ATR | 0.90 ATR | 1.00 ATR |
|---|:---:|:---:|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| `cand_BTC/USDT_UNIFIED_STRATEGY_1638824400` | BTC | SET_3 | 2021/2022 | **0.85 ATR** | **+5.6957R** | PRESERVED | PRESERVED | PRESERVED | PRESERVED | **REJECTED** | **REJECTED** |
| `cand_BTC/USDT_UNIFIED_STRATEGY_1639026000` | BTC | SET_3 | 2021/2022 | **0.92 ATR** | **+4.0784R** | PRESERVED | PRESERVED | PRESERVED | PRESERVED | PRESERVED | **REJECTED** |
| `cand_BTC/USDT_UNIFIED_STRATEGY_1638824400` | BTC | SET_3 | 2021/2022 | **1.34 ATR** | **+5.6968R** | PRESERVED | PRESERVED | PRESERVED | PRESERVED | PRESERVED | PRESERVED |
| `cand_ETH/USDT_UNIFIED_STRATEGY_1655429400` | ETH | SET_4 | 2021/2022 | **1.16 ATR** | **+6.5704R** | PRESERVED | PRESERVED | PRESERVED | PRESERVED | PRESERVED | PRESERVED |

### Critical Forensic Observations on Winners:
- **Winner 1 (`cand_BTC...1638824400`, +5.70R)**: Stop distance = **0.85 ATR**. Eliminated at $\ge 0.90\text{ ATR}$.
- **Winner 2 (`cand_BTC...1639026000`, +4.08R)**: Stop distance = **0.92 ATR**. Eliminated at $\ge 1.00\text{ ATR}$.
- **Winner 3 (`cand_ETH...1655429400`, +6.57R)**: Stop distance = **1.16 ATR**. Preserved across all thresholds.
- **Winner 4 (`cand_BTC...1638824400`, +5.70R)**: Stop distance = **1.34 ATR**. Preserved across all thresholds.
- **Winner Loss Rate**: 0% loss up to 0.80 ATR $\rightarrow$ **25% loss at 0.90 ATR** $\rightarrow$ **50% loss at 1.00 ATR**.

---

## 3. Loss Removal & Throughput Audit

| Threshold | Losses Removed | Wins Removed | Total Trades Kept | Trade Throughput Retention | Net R Delta vs Control |
|:---:|:---:|:---:|:---:|:---:|:---:|
| **Control (0.00)** | 0 | 0 | 39 | 100.0% | +0.0000R |
| **0.50 ATR** | 5 | 0 | 34 | 87.2% | +5.5640R |
| **0.60 ATR** | 6 | 0 | 33 | 84.6% | +6.6804R |
| **0.70 ATR** | 12 | 0 | 27 | 69.2% | +13.2614R |
| **0.80 ATR** | 17 | 0 | 22 | 56.4% | +18.7028R |
| **0.90 ATR** | 23 | 1 | 15 | 38.5% | +19.4940R |
| **1.00 ATR** | 28 | 2 | 9 | 23.1% | +20.8218R |

---

## 4. Decision Rule Audit & Scientific Evaluation

### Rule 1: Economic Objective & Winner/Throughput Preservation
- **Condition**: The ATR floor must improve Net R, Profit Factor, and Expectancy without unacceptable loss of winners or throughput.
- **Finding**: **VIOLATED**. Low thresholds (0.50–0.70 ATR) remain net negative (Net R: -10.66R to -2.96R; PF: 0.67 to 0.88). High thresholds (0.90–1.00 ATR) destroy 25% to 50% of the strategy's winning alpha and decimate trade frequency to < 5 trades/year across 15 streams. The 0.80 ATR threshold sits on a brittle knife-edge next to Winner 1 (0.85 ATR) and reduces sample size to 22 trades.

### Rule 2: Pre-Registered Search Space
- **Condition**: Do not search for thresholds outside 0.50–1.00 ATR.
- **Finding**: **COMPLIANT**. Evaluation strictly examined 0.50, 0.60, 0.70, 0.80, 0.90, and 1.00 ATR.

### Rule 3: Rejection & Implementation Removal
- **Condition**: If tested ATR floors fail to provide a robust improvement over Phase 10.2 7d control, reject H_SL_ATR_01 and remove experimental implementation.
- **Finding**: **REJECTED**. The ATR stop floor is rejected as a candidate alpha gate.

### Rule 4 & 5: Baseline Invariance & Dataset Integrity
- Canonical strategy remains frozen.
- No 2023+ validation or 2024–2026 out-of-sample data was accessed.

---

## 5. Final Scientific Verdict

### **VERDICT: UNSUPPORTED**

The ATR stop distance floor (`H_SL_ATR_01`) is **NOT SUPPORTED** as an independent structural alpha filter. It exhibits the classic pathology of an artificial sample-truncation parameter:
1. **Insufficient Healing at Safe Multiples**: At safe multiples ($\le 0.70\text{ ATR}$) where winners are unharmed, the strategy remains deeply unprofitable.
2. **Destructive Interference at Tight Multiples**: As soon as the parameter reaches levels that eliminate enough losses to look superficially profitable ($\ge 0.90\text{ ATR}$), it begins destroying genuine winning trades and collapses execution throughput.
3. **Root Cause Diagnosis**: The failure mode identified in Phase 10.1 was that micro LTF pivots are noisy, NOT that a scalar ATR filter should reject valid setups. The proper architectural remedy is not a trade-rejection filter, but structural anchoring to higher-level swing pivots.

---

## 6. Execution Directives Completed
- `scratch/phase10_3_sl_atr_dev_results.json` created.
- `scratch/phase10_3_sl_atr_dev_results.md` created.
- No modification to the canonical baseline strategy.
- Experimental ATR floor implementation rejected.
