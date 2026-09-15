# Quantitative Crypto Platform (QCP)

[![Python](https://img.shields.io/badge/Python-3.12%2B-3776AB.svg?style=flat&logo=python&logoColor=white)](https://www.python.org/)
[![Test Suite](https://img.shields.io/badge/Tests-428%20Passing-brightgreen.svg)]()
[![Asset Universe](https://img.shields.io/badge/Assets-BTC%20%7C%20ETH%20%7C%20SOL-blue.svg)]()
[![Temporal Partitioning](https://img.shields.io/badge/Partitions-Dev%20(2021--22)%20%7C%20Val%20(2023)%20%7C%20OOS%20(2024--26)-orange.svg)]()
[![Risk Engine](https://img.shields.io/badge/Risk-1.0%25%20Friction--Adjusted%20Loss%20Ceiling-red.svg)]()
[![Production Status](https://img.shields.io/badge/Production-LIVE%20LOCKED-inactive.svg)]()

> **An autonomous quantitative research and systematic capital platform for crypto markets.**
>
> *Crypto markets serve as the initial proving ground for a broader autonomous systematic capital platform.*

---

## Executive Summary

The **Quantitative Crypto Platform (QCP)** is an autonomous quantitative research, alpha evaluation, risk governance, and systematic capital allocation platform.

Designed from first principles to address the fundamental gap between *backtested mathematical edge* and *executable exchange economics*, QSP integrates causal multi-timeframe strategy generation, friction-aware order simulation, Bayesian confidence estimation, square-root market impact modeling, adversarial falsification, and closed-loop research evolution.

### Operational Governance State

* **Software Status:** `Implemented / Tested` (428 automated unit, integration, and regression tests passing).
* **Research Status:** `Development / Validation / OOS Qualified` (Control portfolio frozen; zero parameter adjustments).
* **Forward Status:** `Paper-Testing` (Live API credentials permanently disconnected).
* **Production Status:** `LIVE LOCKED` (Real capital deployment requires passing all forward paper gates).
* **Strategy Family 9:** `RESEARCH / OOS OBSERVATION` (Cross-asset relative value observation; pending multi-pair qualification).
* **Defensive Hedging Engine:** `PROTECTION MODULE — UNQUALIFIED FOR LIVE USE` (Pending forward paper-testing).

---

## The Closed Research-to-Capital Loop

QSP operates as a continuous, evidence-governed closed loop where empirical outcomes systematically inform research hypotheses without compromising calendar firewalls or curve-fitting:

```text
                     ┌────────────────────────────────────────┐
                     ▼                                        │
             [ DATA INGESTION ]                               │
         Timestamp & Gap Integrity                           │
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
          [ TRADE ECONOMICS GATE ]                            │
     Expected Net Edge > +0.05R Verification                  │
                     │                                        │
                     ▼                                        │
       [ CAPITAL ALLOCATION AUCTION ]                         │
    Feasibility, Capacity & Correlation Sizing                │
                     │                                        │
                     ▼                                        │
          [ DETERMINISTIC RISK GATE ]                         │
       Portfolio Heat <= 3.0%, Drawdown Halts                 │
                     │                                        │
                     ▼                                        │
          [ PAPER EXECUTION HARNESS ]                         │
       Simulated Fills & Telemetry Capture                    │
                     │                                        │
                     ▼                                        │
          [ CONTINUOUS EVOLUTION ]                            │
       Edge Health Clock & Hypothesis Ticket ─────────────────┘
```

---

## Core Engineering & Research Principles

1. **Evidence Over Assumptions:** Backtested metrics are treated as preliminary research hypotheses, never as proofs of future profitability.
2. **Causal Integrity:** Zero lookahead bias, strict bar-close confirmation, point-in-time multi-timeframe forward-filling, and adverse-first intra-candle order collision (stop loss checked before take profit if high/low span both levels in the same bar).
3. **Exchange Economics First:** True alpha exists only after deducting exchange taker fees, bid-ask spread, adverse slippage, borrowing/funding drag, latency slippage, and market impact.
4. **Adversarial Falsification:** Promising strategies are subjected to active attempts at invalidation ($2.0\times$ friction, windfall trade removal, 1-bar execution delay, and sub-period splits) before being considered for forward testing.
5. **Capital Feasibility Awareness:** Sizing models must respect real-world exchange lot steps and minimum notional thresholds, evaluating whether an account size ($10, $100, $1,000) distorts risk beyond acceptable boundaries.
6. **Deterministic Risk Invariants:** Hard boundaries are enforced in deterministic software: maximum $1.0000\%$ equity risk at stop loss, maximum $3.00\%$ total portfolio heat, and automated drawdown scaling.
7. **Failure Memory as an Asset:** Failed hypotheses, starved strategies, and decayed alphas are permanently archived in the Strategy Graveyard to prevent the recurrence of known dead ends.
8. **Separation of Research AI from Execution:** Artificial Intelligence operates solely as a research scientist (analyzing data, formulating hypotheses, diagnosing telemetry). The live execution and risk layers remain strictly deterministic.
9. **Production Lock:** Real capital deployment is locked until strategies complete formal forward paper-trading gates.

---

## Architecture & Subsystems

```text
crypto-platform/
├── platform_core/             # System constants, canonical registry, and lifecycle states
├── capital_intelligence/      # Net edge economics, confidence, capacity, and feasibility
├── market_intelligence/       # Regime detection, volatility clustering, and market memory
├── portfolio_engine/          # Portfolio construction, correlation sizing, and hedging
├── risk_engine/               # Loss bounds, position sizing, and drawdown coordination
├── trade_management/          # 5-stage trade lifecycle, order precision, and fail-safes
├── execution_gateway/         # Broker abstraction, CCXT connectors, and order management
├── research/                  # Quantitative discovery lab, accounting, and analytics
│   ├── discovery_lab/         # Multi-family generators, OOS manager, and adversarial tester
│   ├── analytics/             # Standardized R-multiple accounting and statistical metrics
│   └── results/               # Comprehensive matrices, decision records, and audit dashboards
├── tests/                     # 428 automated unit, integration, and regression tests
└── README.md                  # System documentation
```

### 1. Alpha & Capital Intelligence Layer

Located in [`capital_intelligence/`](file:///home/mrcn2/crypto-platform/capital_intelligence/):

* **Net Edge Engine (`NetEdgeEngine`):** Converts nominal strategy signals into Expected Net Edge by explicitly deducting all six sources of execution drag:
  $$\text{Expected Net Edge (R)} = \text{Gross Alpha (R)} - \frac{\text{Fees}_{\text{RT}} + \text{Spread} + \text{Slippage}_{\text{RT}} + \text{Market Impact} + \text{Funding} + \text{Latency}}{\text{Stop Distance (\%)}}$$
  Enforces the **Trade Economics Gate**: emits a deterministic `NO_TRADE` whenever $\text{Expected Net Edge} \le +0.05\text{R}$.
* **Alpha Confidence Engine (`AlphaConfidenceEngine`):** Replaces point estimates with Bayesian standard errors ($\text{SE} = \sigma / \sqrt{N}$) and $95\%$ confidence bounds ($\bar{R} \pm 1.96 \cdot \text{SE}$). Enforces sample-size penalties ($N < 100$) so low-$N$ outliers cannot receive capital.
* **Alpha Capacity Engine (`AlphaCapacityEngine`):** Models capital elasticity across account sizes from $\$10$ to $\$10,000,000$ using the square-root law of market impact ($\text{Impact} = 0.5 \cdot \sigma_{\text{daily}} \cdot \sqrt{\text{Order Size} / \text{ADV}}$).
* **Alpha Selection Engine (`AlphaSelectionEngine`):** Runs an internal capital auction that scores and ranks competing trade opportunities:
  $$\text{Score} = \text{Net Edge} \times \text{Confidence} \times \text{Regime Fit} \times (1 - \text{Portfolio Correlation Penalty})$$
* **Factor Attribution Engine (`FactorAttributionEngine`):** Decomposes trade outcomes into five structural factors: Trend Beta, Momentum, Volatility Expansion, Carry/Funding, and Microstructure.
* **Alpha Health & Edge Decay Clock (`AlphaHealthEngine`):** Continuously monitors rolling 30-trade expectancy against historical baselines, assigning health states: `NORMAL` ($\ge 85$), `WATCH` ($70–85$), `REDUCE` ($50–70$), `QUARANTINE` ($30–50$), or `RETIRE` ($< 30$).
* **Capital Feasibility Engine (`CapitalFeasibilityEngine`):** Evaluates account capital against Binance Spot and USD-M Futures exchange rules (lot steps, min notionals). Flags severe risk distortion on micro-capital accounts ($< \$100$).

### 2. Research & Discovery Lab

Located in [`research/discovery_lab/`](file:///home/mrcn2/crypto-platform/research/discovery_lab/):

* **Multi-Family Strategy Generator (`StrategyExecutor`):** Evaluates 8 core quantitative strategy families (Trend Following, Pullback, Donchian Breakouts, Momentum, Mean Reversion, Volatility Expansion, MTF Continuation, and Regime-Adaptive).
* **Temporal OOS Manager (`OOSManager`):** Enforces cryptographic chronological separation between Development (2021–2022), Validation (2023), and Out-of-Sample (2024–2026).
* **Adversarial Researcher (`AdversarialResearcher`):** Deliberately subjects qualified strategies to 4 stress attacks: $2.0\times$ friction, top 5% windfall removal, 1-bar execution latency, and calendar sub-period splits.
* **Market Memory & Alpha Genome (`market_memory.py`):** Represents every strategy as a 9-dimensional genetic fingerprint to measure distance and avoid disguised beta.
* **Strategy Graveyard (`StrategyGraveyard`):** Permanently archives all falsified strategies and dead hypotheses with post-mortem documentation.

### 3. Market Intelligence Layer

Located in [`market_intelligence/`](file:///home/mrcn2/crypto-platform/market_intelligence/):

* **Regime Engine (`MarketRegimeEngine`):** Classifies market structure into Trend (Bull/Bear/Neutral via EMA alignment and ADX), Volatility (Normal/Elevated/Compression via ATR percentiles and Bollinger Band width), and Liquidity regimes. Computes conditional edge probabilities: $P(\text{Strategy Edge} \mid \text{Regime})$.
* **Market Memory Store (`MarketMemoryStore`):** Records macro market events, regime transitions, and conditional strategy performance matrices over multi-year horizons.

### 4. Portfolio Intelligence & Hedging

Located in [`portfolio_engine/`](file:///home/mrcn2/crypto-platform/portfolio_engine/):

* **Portfolio Intelligence Engine (`PortfolioIntelligenceEngine`):** Computes rolling asset correlation matrices and applies correlation discount factors ($30\%$ risk reduction if correlation $> 0.65$). Enforces a maximum portfolio heat ceiling of $\le 3.00\%$.
* **Relative Value & Hedging (`PortfolioHedgingEngine`):** Evaluates net portfolio crypto beta ($\beta_{\text{net}} = \sum w_i \beta_i$). In hostile regimes where $\beta_{\text{net}} > 2.0$, calculates protective short hedges, automatically falling back to trade rejection or position reduction if small account size makes the hedge unexecutable.

### 5. Deterministic Risk Engine

Located in [`risk_engine/`](file:///home/mrcn2/crypto-platform/risk_engine/):

* **Friction-Adjusted Position Sizing:** Position sizing strictly accounts for entry taker fee ($0.05\%$), exit taker fee ($0.05\%$), dynamic slippage ($0.03\% \times 2$), and bid-ask spread ($0.02\%$):
  $$\text{Loss at Stop} = (\text{Entry Price} - \text{Stop Price}) \times \text{Size} + \text{Round-Trip Friction} \le 1.0000\% \text{ of Equity}$$
* **Mathematical Invariant:** Zero tolerance for risk distortion beyond account limits.

### 6. Trade Lifecycle & Execution Gateway

Located in [`trade_management/`](file:///home/mrcn2/crypto-platform/trade_management/) and [`execution_gateway/`](file:///home/mrcn2/crypto-platform/execution_gateway/):

* **5-Stage Trade Lifecycle (`TradeLifecycleEngine`):** Pre-entry checks, entry precision, post-entry verification, multi-stage take profit and trailing stops, and emergency disconnection fail-safes.
* **Paper Execution Harness:** Deterministic simulation capturing bid/ask spread, modeled slippage, execution latency, and fees.
* **Broker Abstraction:** Pluggable gateway architecture supporting CCXT-compatible exchanges with fail-closed safety semantics.

### 7. Continuous Evolution Engine

Located in [`research/discovery_lab/continuous_evolution_engine.py`](file:///home/mrcn2/crypto-platform/research/discovery_lab/continuous_evolution_engine.py):

* **Telemetric Feedback Loop:** Captures forward execution metrics and evaluates degradation against baseline historical distributions.
* **Governance Rule:** Detection of degradation triggers **quarantine and automated hypothesis generation**, never direct automatic parameter optimization or curve-fitting.

---

## Comprehensive 6-Set Multi-Asset Empirical Backtest Matrix

Evaluated systematically with the certified `StrategyExecutor` across all available historical bars (Lifetime, Development 2021–2022, Validation 2023, Out-of-Sample 2024–2026). Full JSON data: [`MULTISET_COMPREHENSIVE_BACKTEST_MATRIX.json`](file:///home/mrcn2/crypto-platform/research/results/MULTISET_COMPREHENSIVE_BACKTEST_MATRIX.json).

| Set | Timeframe Triad | Operational Style | Asset | Lifetime N | Lifetime Net R | Win Rate | Dev (2021-22) | Val (2023) | OOS (2024-26) | Max DD | Empirical Diagnosis |
| :--- | :--- | :--- | :---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | :--- |
| **Set 1** | 1M → 1w → 1d | Macro / Position | BTC | 99 | **+32.38R** | 39.4% | +0.1R | +4.7R | +9.5R | 6.00R | 🟢 Low-turnover macro edge ($N < 100$, natural market limit). |
| | | | ETH | 91 | **+27.98R** | 38.5% | +11.3R | -1.3R | +9.8R | 8.00R | 🟢 Reliable trend capture, low opportunity density (12–40 trades/epoch). |
| | | | SOL | 49 | **+19.41R** | 40.8% | +3.9R | +9.9R | +5.6R | 4.60R | 🟢 Consistent positive drift; small sample size ($N=49$). |
| **Set 2** | 1w → 1d → 4h | Swing | BTC | 589 | **+169.04R** | 40.4% | +21.5R | +30.7R | +29.4R | 9.73R | 🟢 **Core Bedrock**: Stable across all 3 epochs; Max DD 9.73R. |
| | | | ETH | 576 | **+167.08R** | 39.6% | +33.4R | +2.4R | +53.9R | 11.00R | 🟢 Strong OOS expansion; Max DD 11.00R. |
| | | | SOL | 387 | **+107.41R** | 38.5% | +47.5R | +31.2R | +28.7R | 13.07R | 🟢 **100% Adversarial Robustness**: Survived all attack vectors. |
| **Set 3** | 1d → 4h → 1h | Swing / Intraday | BTC | 2,489 | **+212.25R** | 37.3% | +56.0R | +7.9R | **-12.0R** | 38.09R | 🟡 **Edge Decay in OOS**: Deterioration detected in 2024–2026. |
| | | | ETH | 2,559 | **+366.89R** | 37.6% | +107.7R | -25.6R | +89.2R | 44.04R | 🟡 High lifetime alpha, but severe cyclical drawdowns (-25.6R in Val). |
| | | | SOL | 1,741 | **+209.86R** | 35.6% | +86.5R | +43.8R | +73.8R | 22.07R | 🟢 Exceptional continuity; highly sensitive to execution latency. |
| **Set 4** | 4h → 1h → 15m | Intraday | BTC | 10,682 | **-1,394.41R** | 34.9% | -88.0R | -274.4R | -563.0R | 1405.76R | 🔴 **Friction Collapse**: Over 10k trades; 0.16% round-trip friction erases edge. |
| | | | ETH | 11,164 | **-717.21R** | 35.2% | +144.6R | -302.1R | -280.8R | 733.55R | 🔴 **Friction Bleed**: Dev winner (+144.6R) collapsed in Val/OOS. |
| | | | SOL | 2,533 | **+127.34R** | 35.1% | +117.5R | 0.0R | 0.0R | 24.06R | 🟡 15m historical data limited in early cache; Dev positive. |
| **Set 5** | 1h → 15m → 5m | Short-Term Intraday | BTC | 2,108 | **-994.33R** | 29.5% | 0.0R | 0.0R | -994.3R | 993.33R | 🔴 **Noise & Fee Dominated**: Microstructure noise swamps signal. |
| | | | ETH | 2,028 | **-766.15R** | 32.1% | 0.0R | 0.0R | -766.2R | 766.86R | 🔴 **Fatal Microstructure Bleed**: Taker fees absorb gross profit. |
| | | | SOL | 992 | **-264.09R** | 36.1% | 0.0R | 0.0R | -264.1R | 264.99R | 🔴 Negative net edge after exchange economics. |
| **Set 6** | 15m → 5m → 1m | Scalping | BTC | 2,813 | **-2,148.04R** | 6.3% | 0.0R | 0.0R | -2,148.0R | 2147.04R | 🔴 **Extreme Execution Hazard**: 1m stops are too tight for exchange spread/slip. |
| | | | ETH | 2,456 | **-1,667.65R** | 13.0% | 0.0R | 0.0R | -1,667.7R | 1666.92R | 🔴 Complete failure under taker fee economics. |
| | | | SOL | 1,266 | **-793.59R** | 17.1% | 0.0R | 0.0R | -793.6R | 793.29R | 🔴 Unexecutable under standard retail or institutional API latency. |

---

## Adversarial Research & Candidate Classifications

Every qualified candidate was audited by the [AdversarialResearcher](file:///home/mrcn2/crypto-platform/research/discovery_lab/adversarial_researcher.py) to assess survival under simulated operational degradation. Full JSON data: [`ADVERSARIAL_STRESS_BATTERY.json`](file:///home/mrcn2/crypto-platform/research/results/ADVERSARIAL_STRESS_BATTERY.json).

| Strategy ID | Family | Asset | Set | Total N | Lifetime Net R | Adversarial Survival | Classification & Status |
| :--- | :--- | :---: | :---: | ---: | ---: | :---: | :--- |
| `FAM-07-MTFCONT_SOLUSDT_Set2` | MTF Continuation | SOL | Set 2 | 387 | **+107.41R** | **100.0%** (4/4 passed) | 🟢 **Strongest Surviving Candidate** under the current adversarial battery. |
| `FAM-07-MTFCONT_ETHUSDT_Set2` | MTF Continuation | ETH | Set 2 | 576 | **+167.08R** | **75.0%** (3/4 passed) | 🟡 **Conditional / Fat-Tail Sensitive** (Fails if top 5% windfall trades are removed). |
| `FAM-07-MTFCONT_BTCUSDT_Set2` | MTF Continuation | BTC | Set 2 | 589 | **+169.04R** | **75.0%** (3/4 passed) | 🟡 **Conditional / Fat-Tail Sensitive** (Fails if top 5% windfall trades are removed). |
| `FAM-07-MTFCONT_SOLUSDT_Set3` | MTF Continuation | SOL | Set 3 | 1,741 | **+209.86R** | **50.0%** (2/4 passed) | 🟡 **Execution-Sensitive / Latency Fragile** (1-bar fill delay turns edge negative). |
| `FAM-04-MOMENTUM_SOLUSDT_Set2` | Momentum Continuation | SOL | Set 2 | 115 | **+29.07R** | **25.0%** (1/4 passed) | 🔴 **Falsified & Archived** (Collapsed under 2x fees, latency, and outlier removal). |

### Candidates Explicitly Not Qualified for Deployment
* **Set 1 Candidates:** Positive drift, but lower-turnover research layer with insufficient sample size ($N < 100$) for statistical confidence.
* **BTC Set 3:** Experienced Out-of-Sample deterioration in 2024–2026 ($-12.0\text{R}$).
* **ETH Set 3:** Experienced severe cyclical drawdown in 2023 ($-25.6\text{R}$).
* **Sets 4, 5, and 6:** Currently uneconomic due to friction erosion on high-frequency signals. Not deployment candidates.

---

## Daily Multi-Set Decision Record Engine

The platform executes a deterministic 10-level hierarchy before considering any trade:

1. **Level 1 — Data Trust:** Validates timestamp monotonicity, zero gap corruption, and latency $\le 30$ seconds. (If failed: `NO_TRADE`).
2. **Level 2 — Market Tradability:** Validates spread $\le 0.15\%$ and depth metrics. (If failed: `NO_TRADE`).
3. **Level 3 — Qualified Alpha:** Confirms the candidate is registered in the Canonical Registry. (If failed: `NO_TRADE`).
4. **Level 4 — Net Edge Economics:** Verifies that Expected Net Edge $> +0.05\text{R}$ after all frictions. (If failed: `NO_TRADE`).
5. **Level 5 — Capital Feasibility:** Checks account capital against minimum lot sizes and liquidation buffer. (If failed: `NO_TRADE`).
6. **Level 6 — Portfolio Construction:** Enforces maximum portfolio heat ceiling $\le 3.0\%$ and applies correlation discounts. (If failed: `NO_TRADE`).
7. **Level 7 — Hedging Check:** Evaluates net crypto beta and market regime. (Triggers `HEDGE` or `REDUCE`).
8. **Level 8 — Deterministic Output:** Emits machine-readable decisions to [`DAILY_DECISION_RECORD.json`](file:///home/mrcn2/crypto-platform/research/results/DAILY_DECISION_RECORD.json) (`NO_TRADE / TRADE / REDUCE / HEDGE / QUARANTINE`).

---

## Role of Artificial Intelligence in QSP

Artificial Intelligence functions as an **Autonomous Research Scientist**, not a discretionary trader.

### Permitted AI Functions:
* Analyzing historical telemetry and cross-asset correlations.
* Formulating new strategy hypotheses and economic rationale.
* Designing adversarial test batteries to falsify surviving candidates.
* Diagnosing root causes when strategy degradation is detected.
* Recommending capital allocation adjustments based on objective health indices.

### Prohibited AI Actions:
* AI is strictly prohibited from placing direct unhedged market orders on live exchanges.
* AI cannot modify live strategy parameters without completing formal development, validation, and OOS qualification.
* AI cannot bypass deterministic risk invariants or capital feasibility limits.

---

## Capital Feasibility: Sizing Reality Across Account Tiers

Empirical evaluation against real Binance Spot and USD-M Futures exchange rules (saved in [`CAPITAL_FEASIBILITY_MATRIX.md`](file:///home/mrcn2/crypto-platform/research/results/CAPITAL_FEASIBILITY_MATRIX.md)):

* **$10 Account:** Mathematically viable in backtest theory, but **unexecutable in reality** on BTC/ETH due to the $\$5.00$ minimum notional and minimum lot sizes ($0.001$ BTC $\approx \$65.00$ notional requires $6.5\times$ leverage and incurs a $20.0\%$ equity loss at stop, creating an unacceptable $33\times$ risk distortion). SOL Set 3 is the only candidate viable with manageable distortion.
* **$100 Account:** Viable for SOL Set 2 and Set 3 with minor distortion ($1.1\times$ to $1.4\times$).
* **$500–$1,000 Account:** **Clean execution across all candidates.** Zero leverage required ($<1.0\times$), zero risk distortion, fee drag $<2\%$ of risk, and Gambler's Ruin probability $<0.1\%$.

---

## Quickstart & Verification

### 1. Environment Setup
```bash
# Clone repository
git clone https://github.com/Quantitative-Systems/crypto-platform.git
cd crypto-platform

# Create virtual environment (Python 3.12+)
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Run the Full Test Suite
Verify that all 428 automated tests pass:
```bash
pytest -q
```
*Expected output: 428 passed in ~90 seconds.*

### 3. Run the Multi-Set Backtest Battery
```bash
python3 research/discovery_lab/run_multiset_comprehensive_backtest.py
```

### 4. Run the Adversarial Researcher
```bash
python3 research/discovery_lab/adversarial_researcher.py
```

### 5. Generate the Daily Decision Record
```bash
python3 production/decision_record_engine.py
```

### 6. Inspect Results
```bash
cat research/results/CEO_DASHBOARD.md
cat research/results/DAILY_DECISION_RECORD.json
```

---

## Data Integrity & Research Disclaimer

This platform and its codebase are provided strictly for quantitative research, algorithmic simulation, and systematic risk governance.

All backtest metrics, out-of-sample evaluations, and adversarial stress tests are **empirical research observations**, not guarantees of future performance. Real-world execution is subject to:
* Data feed latency and clock desynchronization.
* Unmodeled exchange queue priority and partial fills.
* Exchange API outages and connectivity drops.
* Sudden liquidity evaporation during flash events.
* Variations in exchange fee tiers and margin interest rates.

**Production status is LIVE LOCKED.** Real capital must never be deployed until predefined paper-trading gates are independently verified.
