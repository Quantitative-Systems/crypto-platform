# Crypto Quantitative Trading & Research Platform

[![Python](https://img.shields.io/badge/Python-3.12%2B-3776AB.svg?style=flat&logo=python&logoColor=white)](https://www.python.org/)
[![Tests](https://img.shields.io/badge/Tests-Passing-brightgreen.svg)]()
[![Asset Coverage](https://img.shields.io/badge/Assets-BTC%20%7C%20ETH%20%7C%20SOL-blue.svg)]()
[![Data Partitioning](https://img.shields.io/badge/Partitions-Dev%20(2021--22)%20%7C%20Val%20(2023)%20%7C%20OOS%20(2024--26)-orange.svg)]()
[![Risk Engine](https://img.shields.io/badge/Risk-1.0%25%20Friction--Adjusted%20Ceiling-red.svg)]()

A modular, high-performance platform for quantitative cryptocurrency research, multi-timeframe strategy simulation, automated risk governance, and exchange execution.

Designed from first principles to prevent data leakage and curve-fitting, the platform combines strict point-in-time backtesting, friction-aware order modeling, an automated multi-strategy discovery engine, and standardized R-multiple accounting across crypto spot and perpetual futures markets.

---

## Key Highlights

* **Multi-Timeframe Architecture:** Supports six operational trading styles from macro position trading down to short-term intraday and scalping across major pairs (`BTC/USDT`, `ETH/USDT`, `SOL/USDT`).
* **Causal Backtest Engine:** Zero lookahead bias, strict bar-close confirmation, and adverse-first intra-candle order collision (stop loss checked before take profit if high/low span both levels in the same bar).
* **Friction-Adjusted Risk Engine:** Standardized R-multiple accounting where position sizing strictly caps initial capital risk to $\le 1.0\%$ of equity, inclusive of exchange taker fees ($0.075\%$), dynamic slippage ($0.03\%$), and bid-ask spread ($0.01\%$).
* **Automated Strategy Discovery Lab:** Evaluates 8 fundamental strategy families across market regimes with a strict minimum evidence threshold ($\ge 100$ independent trades per asset/timeframe unit).
* **Multi-Dimensional Robustness Firewalls:**
  * **Profit Concentration Firewall:** Automatically tests if performance depends on outlier winners (Top 1 trade must contribute $\le 50\%$ of Net R; edge must remain positive after removing top 1 and top 5 winners).
  * **Cost Stress Testing:** Requires positive expectancy under $2\times$ baseline fees and slippage ($0.15\%$ taker fee, $0.06\%$ slippage, $0.02\%$ spread).
  * **Parameter Sensitivity:** Validates strategy stability under $\pm 20\%$ parameter shifts.
* **Temporal Data Partitioning:** Strict calendar isolation dividing historical data into **Development (2021–2022)**, **Validation (2023)**, and **Out-of-Sample (2024–2026)** to ensure strategies generalize across bull, bear, and choppy regimes.
* **Live & Paper Trading Interfaces:** Clean broker abstraction with CCXT exchange connectivity, order lifecycle management, and telemetry reconciliation.

---

## Trading Styles & Timeframe Structure

The platform organizes multi-timeframe analysis into 6 nested timeframe sets:

| Set | Operational Style | Higher Timeframe (Trend / Bias) | Middle Timeframe (Setup / Pullback) | Lower Timeframe (Entry Trigger) | Typical Holding Horizon |
| :---: | :--- | :---: | :---: | :---: | :---: |
| **Set 1** | Macro / Position | Monthly (`1M`) | Weekly (`1W`) | Daily (`1D`) | Multi-week to months |
| **Set 2** | Swing | Weekly (`1W`) | Daily (`1D`) | 4-Hour (`4H`) | Days to weeks |
| **Set 3** | Swing / Intraday | Daily (`1D`) | 4-Hour (`4H`) | 1-Hour (`1H`) | 1 to 5 days |
| **Set 4** | Intraday | 4-Hour (`4H`) | 1-Hour (`1H`) | 15-Minute (`15M`) | Intraday (hours) |
| **Set 5** | Short-Term Intraday | 1-Hour (`1H`) | 15-Minute (`15M`) | 5-Minute (`5M`) | Minutes to hours |
| **Set 6** | Scalping | 15-Minute (`15M`) | 5-Minute (`5M`) | 1-Minute (`1M`) | Minutes |

*Note: For strategy qualification, each asset/set unit is evaluated independently. Sample sizes are never artificially pooled across pairs to satisfy statistical significance requirements.*

---

## Repository Structure

```text
crypto-platform/
├── backtesting/               # Simulation engines, order matching, and replay logic
├── config/                    # Asset parameters, exchange settings, and risk limits
├── market_data/               # Historical candle ingestion, caching, and data pipelines
├── market_intelligence/       # Technical indicators, regime classifiers, and structural analysis
├── production/                # Live daemons, order management, SQLite WAL persistence, telemetry
├── research/                  # Quantitative research laboratory
│   ├── analytics/             # Standardized R-multiple accounting and statistical tests
│   ├── discovery_lab/         # Multi-family strategy generator and autonomous research runner
│   └── results/               # CEO dashboard, qualification ledgers, and experiment reports
├── risk_engine/               # Friction-adjusted position sizing, drawdown ceilings, and risk checks
├── strategy_engine/           # Canonical strategy state machines, entry models, and exit logic
├── tests/                     # Unit, integration, and regression test suites
└── README.md                  # System documentation
```

---

## Strategy Discovery Families

The platform systematically evaluates eight distinct quantitative strategy families:

1. **Trend Following:** Multi-timeframe trend alignment with trailing trend stops.
2. **Trend + Pullback:** Trend continuation following intermediate pullbacks into support/resistance or moving averages.
3. **Breakout (Donchian / Channel):** Structural range expansion beyond multi-period high/low channels.
4. **Momentum Continuation:** Trend strength confirmation using RSI / MACD momentum filters.
5. **Mean Reversion:** Counter-trend entries into overbought/oversold boundaries (empirically audited and falsified in trending regimes).
6. **Volatility Expansion:** Volatility breakout triggers following Bollinger Band / ATR squeezes.
7. **Multi-Timeframe Continuation:** Higher timeframe trend direction + intermediate alignment + lower timeframe channel breakout.
8. **Regime-Adaptive Systems:** Volatility and trend regime switching between trend-following and defensive modes.

---

## Risk Governance & Trade Accounting

### 1. Friction-Adjusted Position Sizing
Traditional backtest models frequently under-size risk by calculating position size solely from nominal stop distance, leaving the portfolio vulnerable to fee and slippage drag on stopouts. This platform uses certified friction-adjusted sizing:

$$\text{Effective Risk Per Unit} = |P_{\text{entry}} - P_{\text{stop}}| + \left( P_{\text{entry}} \times f_{\text{entry}} \right) + \left( P_{\text{stop}} \times f_{\text{exit}} \right)$$

$$\text{Position Size} = \frac{\text{Equity} \times \text{Risk Ceiling}}{\text{Effective Risk Per Unit}}$$

Where:
* $\text{Risk Ceiling} \le 1.0\%$ of total account equity.
* $f_{\text{entry}}, f_{\text{exit}}$ incorporate taker fee ($0.075\%$), dynamic slippage ($0.03\%$), and bid-ask spread ($0.01\%$).
* **Guaranteed Invariant:** Maximum dollar loss at stop loss is mathematically capped at $\le 1.0000\%$ of equity.

### 2. Standardized R-Multiple Accounting
Every trade's performance is measured in normalized R-multiples:
$$R = \frac{\text{Net Dollar P&L}}{\text{Initial Dollar Risk}}$$
This normalizes returns across varying volatilities, market caps, and time horizons, enabling clean portfolio-level aggregation.

---

## Research Workflow & Verification Pipeline

```mermaid
flowchart TD
    A[Market Data Ingestion] --> B[Data Integrity & Gap Validation]
    B --> C[Hypothesis Formulation & Economic Rationale]
    C --> D[Causal Backtest Simulation (Dev: 2021-2022)]
    D --> E{Dev Qualification Gates}
    E -->|N < 100 or Neg Expectancy| F[Archived in Failure Registry]
    E -->|Passed N, PF, DD, Fees, Sizing| G[Profit Concentration & Cost Stress Firewalls]
    G -->|Outlier Dependent or Cost Fragile| F
    G -->|Robust Multi-Dimensional Edge| H[PROMISING CANDIDATE]
    H --> I[Validation Partition (2023) - Frozen Rules]
    I -->|Maintains Edge & Low DD| J[Out-of-Sample Partition (2024-2026)]
    I -->|Fails Validation| F
    J -->|Positive Expectancy across all 3 Epochs| K[QUALIFIED ROBUST STRATEGY]
    J -->|Fails OOS| F
    K --> L[Paper Trading Simulation]
    L -->|Execution & Slippage Verified| M[Production Capital Allocation]
```

### Automatic Rejection Gates
Candidates are immediately rejected or archived upon encountering:
* Negative expectancy after realistic exchange fees and slippage.
* Fewer than 100 naturally occurring trades in the Development horizon.
* Profit concentration where the top 1 winner contributes $>50\%$ of Net R, or where removing top 1/top 5 winners destroys the edge.
* Drawdown exceeding the $25\text{R}$ risk ceiling.
* Failure under $2\times$ fee and slippage stress testing.
* Parameter instability under $\pm 20\%$ perturbations.

---

## Research Findings & Discovered Portfolio (2021–2026)

Across 5.5 years of crypto market data spanning bull runs (2021), bear markets (2022), chop/recovery (2023), and new cycle expansions (2024–2026), the autonomous discovery engine evaluated 96 candidate units and qualified **5 robust strategy instances**:

| Strategy Instance | Style | Pair | Dev (2021–22) Net R (N) | Val (2023) Net R (N) | OOS (2024–26) Net R (N) | Lifetime Net R | Lifetime N | Max DD | Status |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| **MTF Continuation** | Set 3 (1D/4H/1H) | SOL/USDT | +86.53R (576) | +43.83R (292) | +73.82R (765) | **+204.19R** | 1,633 | 22.07R | **`QUALIFIED_ROBUST`** |
| **MTF Continuation** | Set 2 (1W/1D/4H) | SOL/USDT | +48.52R (127) | +31.21R (68) | +28.68R (191) | **+108.41R** | 386 | 13.07R | **`QUALIFIED_ROBUST`** |
| **MTF Continuation** | Set 2 (1W/1D/4H) | ETH/USDT | +34.41R (128) | +2.39R (66) | +53.93R (169) | **+90.74R** | 363 | 9.00R | **`QUALIFIED_ROBUST`** |
| **MTF Continuation** | Set 2 (1W/1D/4H) | BTC/USDT | +22.54R (125) | +30.74R (62) | +29.38R (193) | **+82.66R** | 380 | 9.73R | **`QUALIFIED_ROBUST`** |
| **Momentum Continuation** | Set 2 (1W/1D/4H) | SOL/USDT | +16.18R (115) | +4.51R (62) | +8.39R (202) | **+29.07R** | 379 | 19.77R | **`QUALIFIED_ROBUST`** |

### Key Empirical Findings:
1. **Set 2 Swing Convergence:** Multi-timeframe continuation (Higher Timeframe Trend + Middle Timeframe Trend Alignment + Lower Timeframe 10-bar Donchian Breakout, 1.5 ATR stop, 2.5R target) produced positive returns across **BTC, ETH, and SOL** simultaneously without asset-specific curve-fitting. Combined Set 2 Net R: **+281.80R across 1,129 trades**, with maximum drawdown $\le 13.07\text{R}$.
2. **Profit Concentration Verified:** In all qualified strategies, the top 1 winner accounted for $\le 8.4\%$ of Net R. Removing the top 1 winner leaves $>90\%$ of net returns intact.
3. **Falsified Strategies:**
   * **Mean Reversion:** Counter-trend mean reversion suffered severe losses ($-140\text{R}$ to $-660\text{R}$) due to sustained trending momentum blowing through counter-trend stops.
   * **Over-Constrained 3-Timeframe State Machines:** Strategies requiring synchronous multi-timeframe oversold/overbought oscillators suffered from opportunity starvation ($<10$ trades in 2 years).
   * **Intraday Breakouts:** High trade frequency ($>2,000$ trades on 15M) suffered from fee erosion, failing the $2\times$ cost stress test.

---

## Quickstart & Installation

### 1. Prerequisites
* Python 3.12 or higher
* Linux x86_64 / macOS environment
* Git

### 2. Setup Virtual Environment
```bash
# Clone repository
git clone https://github.com/Quantitative-Systems/crypto-platform.git
cd crypto-platform

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Run Test Suite
Verify that the complete unit and integration test suite passes:
```bash
pytest -q
```

### 4. Run Backtests & Research Lab
```bash
# Run the autonomous strategy discovery sweep on Development data (2021-2022)
python3 research/discovery_lab/autonomous_researcher.py

# Run chronological Validation (2023) and Out-of-Sample (2024-2026) testing
python3 research/discovery_lab/run_validation_and_oos.py

# Sync strategy library and generate executive dashboard
python3 research/discovery_lab/sync_dashboard_and_registry.py

# View updated executive research dashboard
cat research/results/CEO_DASHBOARD.md
```

---

## Risk Disclosure & Disclaimer

This platform and its codebase are provided strictly for quantitative research, backtesting, and algorithmic simulation purposes. Cryptocurrency trading involves substantial risk of financial loss. Past backtested performance, whether in-sample or out-of-sample, is no guarantee of future live execution results. Always paper-trade and independently audit execution latency, order fills, and exchange fee schedules before deploying capital.
