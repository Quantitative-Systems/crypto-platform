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
| **Software Integrity** | 🟢 Operational | **539 / 539 automated unit, integration, and regression tests passing cleanly.** |
| **Universal Market Data Fabric** | 🟢 Operational | Multi-venue (Binance/OKX/Bybit/Coinbase), multi-instrument (Spot/Perp), L2 depth, funding, and liquidations. |
| **Continuous Regime Engine** | 🟢 Active | 5D classification: Trend (ADX/EMA), Vol (ATR percentile), Liq (depth ratio), Funding, and Correlation. |
| **Autonomous Research Factory** | 🟢 Operational | Multi-tier hypothesis generation across Directional, RV, Carry, Microstructure, and ML rankers. |
| **Universal Alpha Genome** | 🟢 Certified | Standardized machine-readable specification contract with SHA-256 evidence hashing. |
| **Adversarial Falsification Engine** | 🟢 Active | Causal lookahead detection, 2x friction shock, top 5% windfall removal, and latency ladder. |
| **Execution & Capacity Engine** | 🟢 Active | Almgren-Chriss square-root impact modeling, net edge decay curves, and AUM scaling limits. |
| **Alpha Exposure Graph** | 🟢 Audited | Factor decomposition (BTC, Vol, Liq Beta) and active concurrent downside correlation clustering. |
| **Generic Capital Allocator** | 🟢 Governed | Uncertainty-adjusted allocation with regularized covariance shrinkage and 3.00% portfolio heat ceiling. |
| **Autonomous Risk Governor** | 🟢 Enforced | Pre-trade veto authority: spread blowout, liquidity collapse, and portfolio heat governor. |
| **Stress & Shock Simulation Lab** | 🟢 Passed | 5 / 5 catastrophic shock scenarios survived (Flash crash, liquidation cascade, spread blowout). |
| **Economic Truth Engine** | 🟢 Operational | Full P&L return attribution (Alpha, Beta, Carry, Frictions, Slippage) and degradation diagnosis. |
| **Alpha Lifecycle Manager** | 🟢 Active | Automated state transitions, performance degradation detection, and replacement triggers. |
| **Autonomous Platform Orchestrator**| 🟢 Operational | End-to-end autonomous quantitative execution CLI & daemon (`autonomous_platform_orchestrator.py`). |
| **Forward Paper Daemon** | 🟢 Active | Autonomous daemon running 24/7 on public Binance data feed (`production_live_state.db`). |
| **Capital Firewall** | 🟢 Locked | **Live Capital = $0.00.** Live order submission disabled; exchange API credentials disconnected. |

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
| `FAM06_SOL_USDT_4h` | Volatility Squeeze | SOL/USDT | 4H | 146 | +13.89R | +0.10R [-0.15, 0.34] | 1.17 | 13.93R | 0.148 | -0.654 | 8.4% | 🟡 `SUB_THRESHOLD` |
| `FAM06_ETH_USDT_4h` | Volatility Squeeze | ETH/USDT | 4H | 171 | +2.99R | +0.02R [-0.21, 0.25] | 1.03 | 18.50R | 0.053 | -0.706 | 8.7% | 🔴 `FALSIFIED` |
| `FAM06_BTC_USDT_4h` | Volatility Squeeze | BTC/USDT | 4H | 171 | -0.29R | -0.00R [-0.22, 0.22] | 1.00 | 25.28R | 0.051 | -0.579 | 9.4% | 🔴 `FALSIFIED` |
| `FAM-10-FUNDINGCARRY` | Dynamic Basis Carry | Multi | 8H funding | 0 | 0.0R | 0.0R | 0.0 | - | - | - | 0.0% | 🔴 `FALSIFIED_V1` |
| `RV_LONG_HORIZON_COINTEGRATION_V1` | Cross-Asset RV | Pairs | 1D & 4H | 0 | 0.0R | 0.0R | 0.0 | - | - | 0.0% | 🔴 `FALSIFIED_V1` |

### Pairwise Daily Return Correlation Matrix

| Strategy | `FAM-07-MTFCONT_SOLUSDT_Set2` | `FAM06_SOL_USDT_4h` | `FAM06_ETH_USDT_4h` | `FAM06_BTC_USDT_4h` |
| :--- | :---: | :---: | :---: | :---: |
| `FAM-07-MTFCONT_SOLUSDT_Set2` | 1.0000 | 0.1480 | 0.0528 | **0.0508** |
| `FAM06_SOL_USDT_4h` | 0.1480 | 1.0000 | 0.1741 | 0.1560 |
| `FAM06_ETH_USDT_4h` | 0.0528 | 0.1741 | 1.0000 | 0.1764 |
| `FAM06_BTC_USDT_4h` | **0.0508** | 0.1560 | 0.1764 | 1.0000 |

### Pairwise Downside Correlation Forensic Audit
* **The Naive Calculation:** Comparing days where either strategy had negative return yields negative correlation (-0.57 to -0.70) because non-overlapping zero-return days are correlated against negative returns ($(x - \bar{x})(0 - \bar{y}) < 0$).
* **The True Co-Exposure Calculation:** Restricting analysis strictly to days where both strategies held active market positions reveals downside correlation is near-zero to non-negative (-0.09 to -0.13), confirming that Family 06 does not provide an active hedge during stress.

---

## Performance Truth & Historical Reconciliation

The master ledger explicitly reconciles the performance figures appearing across research documents:

| Methodology | Strategy | Dataset Window | Risk Sizing Model | Total Net R | Profit Factor | Max Drawdown |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| **Canonical Warehouse Backtest** | `FAM-07-MTFCONT_SOLUSDT_Set2` | 2021-01-01 to 2026-06-30 | Fixed 1.0R non-compounding | **+107.41R** | 1.451 | 12.07R |
| **Event-Driven Paper Simulation** | `FAM-07-MTFCONT_SOLUSDT_Set2` | 2024-01-01 to 2026-09-01 | Dynamic 0.60% compounding | **+222.92R** | 5.235 | 4.73% |

* **Reconciliation Explanation:** +107.41R is the full 5.5-year multi-partition (DEV + VAL + OOS) non-compounding canonical backtest in `StrategyExecutor`. +222.92R is the compounding event-driven forward paper simulation in `PaperExecutionHarness` evaluated over the 2024–2026 momentum cycle.

---

## Generic Capital Allocator & Portfolio Protection

Full empirical results documented in [`research/results/MULTI_ALPHA_PORTFOLIO_ALLOCATION_AUDIT.json`](file:///home/mrcn2/crypto-platform/research/results/MULTI_ALPHA_PORTFOLIO_ALLOCATION_AUDIT.json):

### Sizing Calculation Hierarchy
Every alpha slot passes through a fully auditable calculation pipeline:
$$\text{Raw Edge } (E) \xrightarrow{-1.96 \cdot \text{SE}} E_{\text{adj}} \xrightarrow{\text{Risk Parity}} w_{\text{raw}} \xrightarrow{\text{Covariance Shrinkage}} w_{\text{cov}} \xrightarrow{\text{Drawdown Throttle}} w_{\text{dd}} \xrightarrow{\text{Cap Constraints}} w_{\text{final}}$$

* **Fail-Closed Gatekeeper:** The allocator evaluated Family 06 BTC ($E_{\text{net}} \le 0$) and Family 06 ETH ($E_{\text{adj}} \le 0$) and strictly **allocated $0.00 capital**, protecting the portfolio.
* **Capital Protection Proof:** If an unconstrained portfolio had blindly added Family 06 to SOL Set 2, portfolio Sharpe would have degraded from 1.45 to **1.04**, and Max Drawdown would have escalated from 12.07R to **21.17R**. The allocator's risk gate prevented this degradation.

### Historical Multi-Alpha Portfolio Backtest (Causal Reality)

| Portfolio Specification | Total Net R | Maximum Drawdown | Annualized Sharpe | Calmar Ratio | Profit Factor | Status |
| :--- | :---: | :---: | :---: | :---: | :---: | :--- |
| **Standalone `SOL_SET2_MTFCONT`** | **+107.41R** | **12.07R** | **1.45** | **8.90** | **1.353** | 🟢 Optimal Baseline |
| **Unconstrained Multi-Alpha Portfolio**<br>*(SOL Set 2 + ETH Squeeze + BTC Squeeze)* | **+122.99R** | **21.17R** | **1.04** | **5.81** | **1.229** | 🔴 Degraded Edge |
| **Allocated Constrained Portfolio**<br>*(Allocator filtered BTC/ETH to $0.00)* | **+107.41R** | **12.07R** | **1.45** | **8.90** | **1.353** | 🟢 Capital Protected |

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
