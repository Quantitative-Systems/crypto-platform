# Quantitative Research Artifacts & Evidence Index

---

## 1. Master Research Results Index

This index catalogs the primary empirical, forensic, and experimental artifacts generated across the platform, documenting their scientific authority, completeness, and role in the hypothesis lineage.

```
┌────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                   RESEARCH ARTIFACT TAXONOMY                                           │
├────────────────────────────────────────────────────────────────────────────────────────────────────────┤
│ 🟢 AUTHORITATIVE & COMPLETE  : Permanent baseline ground-truth or certified validation study.           │
│ 🟡 EXPERIMENTAL / IN PROGRESS : Active investigation, pre-flight test, or pending matrix replay.       │
│ ⚪ DEPRECATED / HISTORICAL    : Superseded legacy iteration preserved for auditability.                │
└────────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Authoritative Baseline Research Artifacts

### A. Baseline Control Matrix ($H_1$)
* **Location:** [`research/results/BASELINE_002_20260902_013354/MASTER_SUMMARY.json`](file:///home/mrcn2/crypto-platform/research/results/BASELINE_002_20260902_013354/MASTER_SUMMARY.json)
* **Authority:** `AUTHORITATIVE & COMPLETE` (The immutable scientific baseline control)
* **What it Proves:** The raw frozen specification of $H_1$ generates $-0.5998\text{R}$ net expectancy across 128 trades from 2017 to 2026 ($P(\text{Edge} > 0) = 0.0\%$).
* **Role:** Permanent negative-expectancy control benchmark against which all child hypotheses are evaluated.

### B. Implementation Correctness Audit
* **Location:** [`scratch/implementation_correctness_audit.json`](file:///home/mrcn2/crypto-platform/scratch/implementation_correctness_audit.json)
* **Authority:** `AUTHORITATIVE & COMPLETE`
* **What it Proves:** The $10,902$ anchor and target candidate rejections under $H_1$ were **not software defects**, but the faithful enforcement of canonical rules (multi-bar confirmed protected swings and immutable targets).
* **Role:** Establishes the ontological boundary between software bugs and research hypotheses.

### C. Counterfactual Trade-Management Simulation Matrix
* **Location:** [`scratch/counterfactual_trade_management_results.json`](file:///home/mrcn2/crypto-platform/scratch/counterfactual_trade_management_results.json)
* **Authority:** `AUTHORITATIVE & COMPLETE`
* **What it Proves:** Simulating 7 prospective trade-management policies (including break-even at $+0.75\text{R}, +1.0\text{R}, +1.5\text{R}$ and fixed targets) across the identical 128 $H_1$ entries yields negative expectancy ($-0.55\text{R}$ to $-0.61\text{R}$). Proves that exit management is not the primary driver of loss velocity.
* **Role:** Decomposes signal alpha from execution alpha.

### D. Trade Lifecycle Simulator Integrity Trace
* **Location:** [`scratch/simulator_integrity_trace_report.json`](file:///home/mrcn2/crypto-platform/scratch/simulator_integrity_trace_report.json)
* **Authority:** `AUTHORITATIVE & COMPLETE`
* **What it Proves:** Candle-by-candle independent reconstruction of representative trade lifecycles matches the execution simulator with **zero discrepancies** across entry fills, stop losses, excursions, trailing stops, and realized returns.
* **Role:** Certifies the simulator engine as a faithful research instrument.

### E. Causality & Zero-Lookahead Audit
* **Location:** [`scratch/causality_lookahead_audit_report.json`](file:///home/mrcn2/crypto-platform/scratch/causality_lookahead_audit_report.json)
* **Authority:** `AUTHORITATIVE & COMPLETE`
* **What it Proves:** Monotonic timestamp causality ($\text{HTF} \le \text{MTF} \le \text{LTF} \le \text{Entry} \le \text{Exit}$) verified across all trades with **zero temporal violations**.
* **Role:** Certifies that no future data leakage exists in the replayer.

### F. Research Reproducibility Manifest
* **Location:** [`research/experiments/reproducibility_manifest.json`](file:///home/mrcn2/crypto-platform/research/experiments/reproducibility_manifest.json)
* **Authority:** `AUTHORITATIVE & COMPLETE`
* **What it Proves:** Freezes dataset SHA256 hashes, friction parameters, risk rules, and git commit hashes for all experiments.
* **Role:** Guarantees bit-for-bit research reproducibility.

---

## 3. Child Hypothesis Experimental Artifacts ($H_{1.1}$)

### A. $H_{1.1}$ State Machine Specification
* **Location:** [`strategy_engine/hypotheses/h1_1_early_mtf_entry.py`](file:///home/mrcn2/crypto-platform/strategy_engine/hypotheses/h1_1_early_mtf_entry.py)
* **Authority:** `AUTHORITATIVE SPECIFICATION`
* **What it Defines:** Isolated state machine triggering execution on MTF realignment and retest into the causal MTF keyzone, bypassing LTF sweep latency.

### B. $H_{1.1}$ Experiment Runner
* **Location:** [`research/experiments/run_experiment_h1_1_canonical.py`](file:///home/mrcn2/crypto-platform/research/experiments/run_experiment_h1_1_canonical.py)
* **Authority:** `EXPERIMENTAL HARNESS`
* **Status:** Designed for multi-stream execution with dynamic hypothesis keying.

### C. $H_{1.1}$ Single-Stream Smoke Test
* **Location:** [`scratch/h1_1_smoke_test_result.json`](file:///home/mrcn2/crypto-platform/scratch/h1_1_smoke_test_result.json)
* **Authority:** `EXPERIMENTAL SMOKE TEST`
* **Status:** Used to benchmark single-stream throughput ($\sim 140\text{ candles/sec}$) on `BTC_SET_3`.

---

## 4. Analytical Tools & Core Modules

| Module Path | Primary Purpose | Scientific Role |
| :--- | :--- | :--- |
| [`research/analytics/h1_forensic_investigator.py`](file:///home/mrcn2/crypto-platform/research/analytics/h1_forensic_investigator.py) | Master forensic attribution parser | Decomposes $15,445$ candidates and $128$ trades |
| [`research/analytics/implementation_correctness_auditor.py`](file:///home/mrcn2/crypto-platform/research/analytics/implementation_correctness_auditor.py) | Causal anchor & target geometry auditor | Formalizes Bug vs. Hypothesis classification |
| [`research/analytics/counterfactual_trade_manager_simulator.py`](file:///home/mrcn2/crypto-platform/research/analytics/counterfactual_trade_manager_simulator.py) | Counterfactual policy simulator | Evaluates prospective management rules |
| [`research/analytics/regime_attribution_analyzer.py`](file:///home/mrcn2/crypto-platform/research/analytics/regime_attribution_analyzer.py) | Causal market regime partitioner | Quantifies performance by trend/volatility/phase |
| [`research/analytics/trade_lifecycle_forensic_tracer.py`](file:///home/mrcn2/crypto-platform/research/analytics/trade_lifecycle_forensic_tracer.py) | Independent candle-by-candle tracer | Validates simulator mathematical fidelity |
| [`research/analytics/causality_lookahead_auditor.py`](file:///home/mrcn2/crypto-platform/research/analytics/causality_lookahead_auditor.py) | Causal timestamp progression checker | Verifies zero-lookahead temporal integrity |
| [`platform_core/capital_barrier.py`](file:///home/mrcn2/crypto-platform/platform_core/capital_barrier.py) | 5-tier graduated risk governor | Gates hypotheses from live capital deployment |
| [`research/experiments/hypothesis_registry.py`](file:///home/mrcn2/crypto-platform/research/experiments/hypothesis_registry.py) | Immutable hypothesis lineage tracker | Tracks parent-child provenance and MHT trials |
