# Quantitative Crypto Platform (QCP)

[![Python](https://img.shields.io/badge/Python-3.12%2B-3776AB.svg?style=flat&logo=python&logoColor=white)](https://www.python.org/)
[![Test Suite](https://img.shields.io/badge/Tests-517%20Passing-brightgreen.svg)]()
[![Asset Universe](https://img.shields.io/badge/Assets-BTC%20%7C%20ETH%20%7C%20SOL-blue.svg)]()
[![Temporal Partitioning](https://img.shields.io/badge/Partitions-Dev%20(2021--22)%20%7C%20Val%20(2023)%20%7C%20OOS%20(2024--26)-orange.svg)]()
[![Risk Engine](https://img.shields.io/badge/Risk-7D%20Firewall%20%7C%203.0%25%20Max%20Heat-red.svg)]()
[![Production Status](https://img.shields.io/badge/Capital%20Firewall-FAIL--CLOSED%20%7C%20%240.00%20LIVE-inactive.svg)]()

> **An autonomous quantitative research, alpha evaluation, risk governance, and systematic capital platform for crypto markets.**
>
> *QCP is designed to discover, validate, deploy, monitor, retire, and replace systematic quantitative trading strategies across multiple independent market mechanisms—governed by empirical evidence and fail-closed capital protection.*

---

## Executive Summary

The **Quantitative Crypto Platform (QCP)** bridges the chasm between theoretical backtested edge and executable exchange economics. 

Rather than relying on single-strategy curve-fitting or opaque black boxes, QCP enforces a rigorous institutional lifecycle:
1. **Causal Multi-Timeframe Strategy Generation:** Closed candles only, next-bar open execution, and `ADVERSE_FIRST` intrabar collision handling.
2. **Exchange Economics First:** Explicit deduction of taker fees ($0.05\%$), bid-ask spread ($0.02\%$), dynamic slippage ($0.03\% \times 2$), margin borrow financing ($6.0\%$ APR), and execution latency.
3. **Adversarial Falsification:** Candidates must survive $2.0\times$ friction, top 5% windfall trade removal, 1-bar execution delay, and out-of-sample chronological partitions.
4. **Alpha Diversity & Independence:** Compares competing alpha mechanisms using pairwise daily return correlation, downside return correlation, running drawdown correlation, and intrabar exposure overlap.
5. **Generic Capital Allocator:** Dynamic portfolio risk allocation driven by net edge, statistical uncertainty discounting (SE), regularized covariance shrinkage, and a strict $3.00\%$ portfolio heat ceiling.
6. **Continuous Forward Paper Burn-In:** 24/7 autonomous paper daemon consuming real public exchange streams with zero live credentials and live capital locked at $\$0.00$.

---

## Operational Governance Ledger

| System Layer | Status | Verified Operational Evidence |
| :--- | :---: | :--- |
| **Software Integrity** | 🟢 Operational | **517 / 517 automated unit, integration, and regression tests passing cleanly.** |
| **Data Warehouse & Lineage** | 🟢 Certified | 5.5-year canonical datasets (BTC, ETH, SOL) verified with SHA-256 provenance hashes and 0 gaps. |
| **Execution Semantics** | 🟢 Locked | Canonical causal contract: next-bar open fill, `ADVERSE_FIRST` stop/target collision policy. |
| **Risk Firewall & Killswitch** | 🟢 Locked | 7-dimensional risk firewall active: 1.0% max loss per trade, 3.0% max portfolio heat, auto drawdown throttle. |
| **Capital Firewall** | 🟢 Locked | **Live Capital = $0.00.** Live order submission disabled; exchange API credentials disconnected. |
| **Forward Paper Daemon** | 🟢 Active | Autonomous daemon running 24/7 on public Binance data feed (`production_live_state.db`). |
| **Primary Baseline Candidate** | 🟡 Forward Burn-In | `FAM-07-MTFCONT_SOLUSDT_Set2`: +107.41R historical baseline; burn-in daemon collecting live observations. |
| **Qualified Independent Alpha 1** | 🟢 Qualified Robust | `FAM06_BTC_USDT_4h`: **+104.88R net, PF 2.67.** Return correlation vs SOL Set 2: **+0.046** (near-orthogonal). |
| **Qualified Independent Alpha 2** | 🟢 Qualified Robust | `FAM06_ETH_USDT_4h`: **+103.31R net, PF 2.62.** Return correlation vs SOL Set 2: **+0.139**, Downside corr: **-0.632**. |
| **Relative Value Spread (`FAM-09`)** | 🔴 Falsified | All 6 cross-asset cointegration streams failed qualification; archived in Strategy Graveyard. |
| **Dynamic Funding Carry (`FAM-10`)** | 🔴 Falsified | Sub-hurdle net carry (<11% APR funding fails to clear 6% borrow + 32 bps friction); archived in Graveyard. |
| **Generic Capital Allocator** | 🟢 Audited | Fully transparent calculation trace; demonstrates +78.7% Sharpe improvement in multi-alpha portfolio. |
| **Production Qualification** | 🔴 Not Reached | Real capital deployment requires extensive forward paper trade verification. |

---

## The Closed Research-to-Capital Loop

QCP operates as a continuous, evidence-governed closed loop where empirical outcomes systematically inform research hypotheses without compromising calendar firewalls or curve-fitting:

```text
                     ┌────────────────────────────────────────┐
                     ▼                                        │
             [ DATA INGESTION ]                               │
         Timestamp & Gap Integrity                            │
                     │                                        │
                     ▼                                        │
             [ RESEARCH LAB ]                                 │
     Hypothesis & Alpha Genome Generation                     │
                     │                                        │
                     ▼                                        │
         [ CAUSAL DEVELOPMENT ]                               │
     In-Sample (2021-2022) Falsification                      │
                     │                                        │
                     ▼                                        │
        [ CHRONOLOGICAL VALIDATION ]                          │
        Validation (2023) - Frozen Rules                      │
                     │                                        │
                     ▼                                        │
          [ OUT-OF-SAMPLE (OOS) ]                             │
       OOS (2024-2026) - Blind Testing                        │
                     │                                        │
                     ▼                                        │
         [ ADVERSARIAL STRESS TEST ]                          │
      Friction 2x, Outliers, Latency Delay                    │
                     │                                        │
                     ▼                                        │
       [ ALPHA INDEPENDENCE TESTING ]                         │
    Correlation, Downside Tail, Concurrency                   │
                     │                                        │
                     ▼                                        │
       [ CAPITAL ALLOCATION AUCTION ]                         │
    Uncertainty Discount, Covariance Shrinkage                │
                     │                                        │
                     ▼                                        │
          [ DETERMINISTIC RISK GATE ]                         │
       Portfolio Heat <= 3.0%, Drawdown Halts                 │
                     │                                        │
                     ▼                                        │
          [ FORWARD PAPER DAEMON ]                            │
       Continuous Live Observation & Telemetry                │
                     │                                        │
                     ▼                                        │
          [ CONTINUOUS EVOLUTION ]                            │
       Edge Health Clock & Research Graveyard ────────────────┘
```

---

## Authoritative Alpha Independence Matrix

From [`research/results/ALPHA_INDEPENDENCE_MATRIX.json`](file:///home/mrcn2/crypto-platform/research/results/ALPHA_INDEPENDENCE_MATRIX.json) and [`research/results/ALPHA_INDEPENDENCE_MATRIX.md`](file:///home/mrcn2/crypto-platform/research/results/ALPHA_INDEPENDENCE_MATRIX.md):

| Alpha ID | Mechanism | Asset | TF | Trades | Net R | E[R] (95% CI) | PF | Max DD | Return Corr vs SOL Set 2 | Downside Corr | Overlap % | Status |
| :--- | :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| `FAM-07-MTFCONT_SOLUSDT_Set2` | Trend Continuation | SOL/USDT | Set 2 (1W/1D/4H) | 387 | +107.41R | +0.28R [0.12, 0.44] | 1.45 | 12.07R | 1.000 | 1.000 | 100.0% | 🟡 `FORWARD_HEALTHY` |
| `FAM06_SOL_USDT_4h` | Volatility Squeeze | SOL/USDT | 4H | 140 | +93.03R | +0.66R [0.39, 0.94] | 2.81 | 5.04R | 0.199 | -0.537 | 9.7% | 🟢 `QUALIFIED_ROBUST` |
| `FAM06_ETH_USDT_4h` | Volatility Squeeze | ETH/USDT | 4H | 164 | +103.31R | +0.63R [0.37, 0.89] | 2.62 | 5.65R | **0.139** | **-0.632** | **9.3%** | 🟢 `QUALIFIED_ROBUST` |
| `FAM06_BTC_USDT_4h` | Volatility Squeeze | BTC/USDT | 4H | 168 | +104.88R | +0.62R [0.37, 0.88] | 2.67 | 5.66R | **0.046** | **-0.512** | **9.1%** | 🟢 `QUALIFIED_ROBUST` |
| `FAM-10-FUNDINGCARRY` | Dynamic Basis Carry | Multi | 8H funding | 0 | 0.0R | 0.0R | 0.0 | - | - | - | 0.0% | 🔴 `FALSIFIED` |
| `RV_LONG_HORIZON_COINTEGRATION_V1` | Cross-Asset RV | Pairs | 1D & 4H | 0 | 0.0R | 0.0R | 0.0 | - | - | 0.0% | 🔴 `FALSIFIED` |

### Pairwise Daily Return Correlation Matrix

| Strategy | `FAM-07-MTFCONT_SOLUSDT_Set2` | `FAM06_SOL_USDT_4h` | `FAM06_ETH_USDT_4h` | `FAM06_BTC_USDT_4h` |
| :--- | :---: | :---: | :---: | :---: |
| `FAM-07-MTFCONT_SOLUSDT_Set2` | 1.0000 | 0.1994 | 0.1388 | **0.0461** |
| `FAM06_SOL_USDT_4h` | 0.1994 | 1.0000 | 0.1427 | 0.1122 |
| `FAM06_ETH_USDT_4h` | 0.1388 | 0.1427 | 1.0000 | 0.1647 |
| `FAM06_BTC_USDT_4h` | **0.0461** | 0.1122 | 0.1647 | 1.0000 |

### Pairwise Downside Correlation Matrix (Stress Days)

| Strategy | `FAM-07-MTFCONT_SOLUSDT_Set2` | `FAM06_SOL_USDT_4h` | `FAM06_ETH_USDT_4h` | `FAM06_BTC_USDT_4h` |
| :--- | :---: | :---: | :---: | :---: |
| `FAM-07-MTFCONT_SOLUSDT_Set2` | 1.0000 | **-0.5369** | **-0.6316** | **-0.5125** |
| `FAM06_SOL_USDT_4h` | -0.5369 | 1.0000 | -0.4503 | -0.3871 |
| `FAM06_ETH_USDT_4h` | -0.6316 | -0.4503 | 1.0000 | -0.4019 |
| `FAM06_BTC_USDT_4h` | -0.5125 | -0.3871 | -0.4019 | 1.0000 |

> **Key Scientific Discovery:** The downside correlation between Family 07 Trend Continuation and Family 06 Volatility Squeeze is **negative (-0.512 to -0.632)**. During trend-following drawdown periods (chop/contraction), the squeeze mechanism is either flat or capturing short impulses. Simultaneous position concurrency is under **10%**, providing genuine economic diversification.

---

## Generic Capital Allocator & Multi-Alpha Portfolio Synergy

Full empirical results documented in [`research/results/MULTI_ALPHA_PORTFOLIO_ALLOCATION_AUDIT.json`](file:///home/mrcn2/crypto-platform/research/results/MULTI_ALPHA_PORTFOLIO_ALLOCATION_AUDIT.json):

### Sizing Calculation Hierarchy
Every alpha slot passes through a fully auditable calculation pipeline:
$$\text{Raw Edge } (E) \xrightarrow{-1.96 \cdot \text{SE}} E_{\text{adj}} \xrightarrow{\text{Risk Parity}} w_{\text{raw}} \xrightarrow{\text{Covariance Shrinkage}} w_{\text{cov}} \xrightarrow{\text{Drawdown Throttle}} w_{\text{dd}} \xrightarrow{\text{Cap Constraints}} w_{\text{final}}$$

* **Single-Strategy Ceiling Proof:** When SOL Set 2 was allocated alone, raw proposed risk was $3.00\%$. The allocator constrained it strictly to the $1.50\%$ single-strategy policy ceiling (`is_capped_by_strategy_ceiling: true`).
* **Asset Concentration Limit:** Two strategies on SOL/USDT compete for the $1.50\%$ single-asset ceiling, preventing correlated exposure clustering.
* **Portfolio Heat Constraint:** When SOL Set 2, ETH Squeeze, and BTC Squeeze compete, unconstrained risk demand ($4.28\%$) is scaled dynamically to satisfy the $3.00\%$ aggregate portfolio heat limit.

### Historical Multi-Alpha Portfolio Backtest (2021–2026)

| Portfolio Specification | Total Net R | Maximum Drawdown | Annualized Sharpe | Calmar Ratio | Sharpe Improvement | Calmar Improvement |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Standalone `SOL_SET2_MTFCONT`** | +107.41R | 12.07R | 1.45 | 8.90 | Baseline | Baseline |
| **Multi-Alpha Diversified Portfolio**<br>*(SOL Set 2 + ETH Squeeze + BTC Squeeze)* | **+312.81R** | **15.05R** | **2.59** | **20.79** | **+78.7%** | **+133.6%** |

---

## Continuous Forward Paper Daemon

Located in [`production/run_forward_burn_in.py`](file:///home/mrcn2/crypto-platform/production/run_forward_burn_in.py):
* **Feed:** Continuous polling of Binance Public REST API (no private keys, read-only market data).
* **Execution Engine:** Causal paper replayer enforcing bar-close confirmation, next-bar open fills, and realistic taker friction.
* **Fault Tolerance:** Gap detection, automatic restart recovery, monotonic timestamp verification, and state persistence in `production_live_state.db`.
* **Telemetry & Governance:** Machine-readable health reports emitted every minute to [`research/results/FORWARD_PAPER_DAEMON_AUDIT.json`](file:///home/mrcn2/crypto-platform/research/results/FORWARD_PAPER_DAEMON_AUDIT.json).

---

## Strategy Graveyard (Preserved Research Failures)

Failed hypotheses are preserved as permanent institutional research memory to prevent curve-fitted resurrection:

```text
======================= STRATEGY GRAVEYARD =======================
1. RV_LONG_HORIZON_COINTEGRATION_V1
   - Specification: BTC/ETH, SOL/ETH, SOL/BTC on 1D and 4H (2021-2026)
   - Falsification: Non-stationary ADF/Johansen statistics, OU half-lives > 1,700 bars.
   - Status: FALSIFIED / PERMANENT RESEARCH MEMORY

2. FAM-10-FUNDINGCARRY
   - Specification: Spot-perp basis carry entered when funding >= 15% APR.
   - Falsification: Average funding (0.66%-7.20% APR) failed to clear 6% margin borrow + 32 bps friction.
   - Status: FALSIFIED / IDLE IN SUB-HURDLE REGIMES

3. INTRADAY HIGH-FREQUENCY SETS (Sets 4, 5, 6)
   - Specification: Intraday and scalping timeframes (15m, 5m, 1m).
   - Falsification: Extreme execution latency sensitivity and transaction fee erosion.
   - Status: FALSIFIED UNDER RETAIL/INSTITUTIONAL TAKER ECONOMICS
==================================================================
```

---

## Core Architecture & Directory Layout

```text
crypto-platform/
├── platform_core/             # Canonical strategy specs, lifecycle states, and constants
├── capital_intelligence/      # Expected net edge economics, confidence bounds, and capacity
├── market_intelligence/       # Regime classification, volatility clustering, and market memory
├── portfolio_engine/          # Generic capital allocator, covariance shrinkage, and hedging
├── risk_engine/               # 7D risk firewall, position sizing, and drawdown coordination
├── trade_management/          # 5-stage trade lifecycle, order precision, and fail-safes
├── execution_gateway/         # Pluggable broker connectors and execution simulators
├── research/                  # Quantitative discovery lab, accounting, and analytics
│   ├── arbitrage/             # Dynamic funding carry and basis carry engines
│   ├── discovery_lab/         # Multi-family strategy specs (FAM-06, FAM-07) and OOS manager
│   ├── experiments/           # Research runners for volatility squeeze, funding, and portfolio
│   └── results/               # Authoritative matrices, decision records, and audit reports
├── production/                # Forward paper daemon burn-in harness and state machines
├── tests/                     # 517 automated unit, integration, and regression tests
└── README.md                  # Comprehensive system documentation
```

---

## Quickstart & Reproducibility

### 1. Installation & Environment Setup
```bash
git clone https://github.com/Quantitative-Systems/crypto-platform.git
cd crypto-platform
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Run the Full Test Suite
Verify that all 517 automated tests pass with zero regressions:
```bash
PYTHONPATH=. pytest -q
```
*Expected output: 517 passed in ~110 seconds.*

### 3. Run the Alpha Independence Audit
```bash
PYTHONPATH=. python3 research/experiments/run_alpha_independence_audit.py
```

### 4. Run the Multi-Alpha Portfolio Diversification Audit
```bash
PYTHONPATH=. python3 research/experiments/run_multi_alpha_portfolio_audit.py
```

### 5. Inspect Forward Paper Burn-In Telemetry
```bash
cat research/results/FORWARD_PAPER_DAEMON_AUDIT.json
cat research/results/DAILY_DECISION_RECORD.json
```

---

## Data Integrity & Risk Disclaimer

This platform and its codebase are provided strictly for quantitative research, algorithmic simulation, and systematic risk governance.

All backtest metrics, out-of-sample evaluations, and adversarial stress tests are **empirical research observations**, not guarantees of future performance. Real-world execution is subject to latency, unmodeled queue priority, partial fills, API outages, liquidity evaporation, and counterparty risks.

**Production status is LIVE LOCKED.** Real capital ($0.00 deployed) must never be allocated until predefined paper-trading gates and multi-engine forward milestones are independently verified.
