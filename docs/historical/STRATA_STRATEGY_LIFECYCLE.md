# STRATA — Strategy Lifecycle & Evidence Protocol

## 1. Overview
In STRATA, no strategy may trade capital based on backtest results alone. Every quantitative strategy must progress through a rigorous, formal 16-stage state machine before qualifying for live deployment.

---

## 2. The 16-Stage Lifecycle State Machine

```text
  [1] DRAFT
       │
  [2] FORMALIZED
       │
  [3] BACKTEST
       │
  [4] FALSIFICATION
       │
  [5] OUT_OF_SAMPLE (OOS)
       │
  [6] ADVERSARIAL
       │
  [7] ROBUSTNESS
       │
  [8] PAPER
       │
  [9] FORWARD
       │
 [10] QUALIFICATION
       │
 [11] DEPLOYABLE
       │
 [12] MONITORED
       │
       ├─────────────────────────────────┐
       ▼                                 ▼
 [13] DEGRADED                     [NORMAL RUN]
       │
 [14] QUARANTINED
       │
 [15] RESEARCH
       │
 [16] REPLACEMENT
```

---

## 3. Stage Definitions & Gate Requirements

| Stage | Name | Description | Gate Criteria / Requirement |
|:---:|:---|:---|:---|
| **1** | `DRAFT` | Initial natural language hypothesis or pseudocode draft. | Initial schema validation. |
| **2** | `FORMALIZED` | Converted to deterministic `StrategySpecification` with entry, stop, target. | Validated $\ge 4.0\text{R}$ minimum target floor. |
| **3** | `BACKTEST` | In-sample historical backtest across approved crypto instruments. | Expectancy $> 0.20\text{R}$, Profit Factor $> 1.5$. |
| **4** | `FALSIFICATION` | Active stress testing to break the strategy (shuffled fills, latency, wide spread). | Strategy survives hostile parameter perturbations. |
| **5** | `OUT_OF_SAMPLE` | Evaluation on unseen historical partitions not used during formulation. | Performance degradation $< 25\%$ compared to in-sample. |
| **6** | `ADVERSARIAL` | Testing under adverse market regimes (extreme drawdowns, liquidity shocks). | Max drawdown remains within predefined tolerance ($< 25\text{R}$). |
| **7** | `ROBUSTNESS` | Monte Carlo permutation of trade sequences and fill slippage. | $95\%$ bootstrap confidence interval remains positive. |
| **8** | `PAPER` | Real-time simulation on live market ticker streams with zero capital. | Continuous paper execution for minimum validation period. |
| **9** | `FORWARD` | Extended forward tracking on demo/testnet exchange environments. | Verified execution without ghost orders or desync. |
| **10** | `QUALIFICATION` | Formal quantitative audit of forward tracking telemetry. | Documented `StrategyEvidence` artifact with hash audit trail. |
| **11** | `DEPLOYABLE` | Certified as eligible for production account assignment. | Manual administrator or user confirmation required. |
| **12** | `MONITORED` | Active in production under continuous surveillance. | Live telemetry continuously streamed to `ResearchEvolutionEngine`. |
| **13** | `DEGRADED` | Performance decay detected (win-rate drops $> 2\sigma$, slippage surges). | Alert emitted; position sizing throttled by Autonomous Agent. |
| **14** | `QUARANTINED` | Execution halted; removed from live trade selection. | Automatic removal from active candidate pool. |
| **15** | `RESEARCH` | Offline forensic evaluation to determine failure causality. | Root cause analysis logged to research database. |
| **16** | `REPLACEMENT` | Strategy retired and superseded by updated lineage. | Archived in Strategy Knowledge Library; state locked. |

---

## 4. Evidence Persistence Invariant
Every stage transition logs an immutable `StrategyEvidence` record containing:
- Unique strategy ID and semantic version.
- Source code / specification SHA-256 hash.
- Verified test datasets and time intervals.
- Fee, slippage, and execution assumptions.
- Quantitative metrics (expectancy, profit factor, max drawdown, win rate, sample size).
