# QCP Relative Value Cointegration Audit
**Directive**: EABG-001  
**Platform**: Quantitative Crypto Platform (QCP)  
**Status**: Completed Econometric Falsification Audit  
**Artifact Path**: `research/results/RELATIVE_VALUE_COINTEGRATION_AUDIT.json`  
**Capital Allocation**: $0.00 (Fail-Closed Governance Firewall)

---

## Executive Summary

Under **Directive EABG-001**, the platform conducted an exhaustive econometric and causal backtest evaluation of the **Relative Value / Statistical Arbitrage Strategy Family (FAM-09)** across the three primary pairs:
- **BTC/ETH** (1d and 4h timeframes)
- **SOL/ETH** (1d and 4h timeframes)
- **SOL/BTC** (1d and 4h timeframes)

### Key Verdict: 6 / 6 Configurations FALSIFIED

> [!IMPORTANT]
> **Zero Curve-Fitting Guarantee**: In accordance with the core development loop (`BUILD -> TEST -> FALSIFY -> DIAGNOSE -> IMPROVE`), none of the relative value pairs exhibited statistical cointegration or stationarity. The spreads wander over extended horizons, leading to persistent divergence and catastrophic friction bleed. All 6 candidate configurations are decisively classified as **`FALSIFIED`** and routed to the Strategy Graveyard. **$0.00 capital allocated.**

---

## Econometric Methodology

Every candidate was evaluated using rigorous statistical and causal procedures:
1. **Engle-Granger Two-Step Cointegration Test**: Augmented Dickey-Fuller (ADF) unit root test performed on the residuals of the price series. Significance hurdle: $p < 0.05$.
2. **Hedge Ratio Estimation**: Dual modeling via Ordinary Least Squares (OLS) and Total Least Squares (TLS / Orthogonal Regression) to account for observation error in both legs.
3. **Ornstein-Uhlenbeck (OU) Mean-Reversion Modeling**: Continuous-time process parameterization estimating equilibrium half-life ($\tau = \frac{\ln(2)}{\theta}$). Maximum viable trading hurdle: $\tau \le 45.0$ bars.
4. **Friction Shock Analysis**: Baseline 32.0 bps roundtrip friction (16 bps per leg for entry + exit) and 2x stress friction (64.0 bps total).
5. **Partition Validation**: Strict temporal separation:
   - **DEV**: 2020-08-15 to 2022-12-31 (In-Sample discovery)
   - **VAL**: 2023-01-01 to 2023-12-31 (Validation)
   - **OOS**: 2024-01-01 to 2026-09-01 (Out-of-Sample verification)

---

## Candidate Econometric & Performance Matrix

| Candidate ID | Pair | Timeframe | Bars | EG p-value | ADF Stat | OU Half-Life | DEV Net R | OOS Net R | 2x Friction Net R | Economic Verdict |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `FAM-09-RV_BTC/ETH_1d` | BTC/ETH | 1d | 3,303 | **0.4231** | -1.98 | 345.2 bars | -10.62R | -12.75R | -28.28R | **FALSIFIED** |
| `FAM-09-RV_BTC/ETH_4h` | BTC/ETH | 4h | 19,800 | **0.4332** | -1.94 | 2,162.2 bars | -25.38R | -17.23R | -76.18R | **FALSIFIED** |
| `FAM-09-RV_SOL/ETH_1d` | SOL/ETH | 1d | 2,209 | **0.2394** | -2.61 | 114.2 bars | -20.21R | -14.07R | -41.25R | **FALSIFIED** |
| `FAM-09-RV_SOL/ETH_4h` | SOL/ETH | 4h | 13,254 | **0.2719** | -2.49 | 750.6 bars | -13.77R | -62.17R | -95.03R | **FALSIFIED** |
| `FAM-09-RV_SOL/BTC_1d` | SOL/BTC | 1d | 2,209 | **0.4988** | -1.72 | 272.4 bars | -65.96R | +1.83R | -63.01R | **FALSIFIED** |
| `FAM-09-RV_SOL/BTC_4h` | SOL/BTC | 4h | 13,254 | **0.5250** | -1.63 | 1,794.6 bars | -34.81R | -6.72R | -84.78R | **FALSIFIED** |

---

## Detailed Econometric Diagnostics by Pair

### 1. BTC / ETH (1d & 4h)
- **Hedge Ratio ($\beta$)**: OLS $\beta = 0.8277$, TLS $\beta = 0.8924$.
- **Cointegration Failure**: The Engle-Granger p-value of **0.4231** on 1d and **0.4332** on 4h fails the 5% rejection hurdle. The spread is non-stationary and exhibits random-walk drift.
- **Ornstein-Uhlenbeck Half-Life**: 345.2 daily bars and 2,162.2 4h bars. The mean-reversion speed is far too sluggish to support profitable statistical arbitrage.
- **Friction Drag**: Double-leg transaction costs (32 bps) overwhelm any localized mean-reversion, generating -10.62R in DEV and -12.75R in OOS.
- **Falsification Verdict**: Non-stationary residual series; failed friction stress test.

### 2. SOL / ETH (1d & 4h)
- **Hedge Ratio ($\beta$)**: OLS $\beta = 2.0786$, TLS $\beta = 2.5619$.
- **Cointegration Failure**: Engle-Granger p-value of **0.2394** (1d) and **0.2719** (4h). High idiosyncratic variance in SOL (ecosystem growth, FTX collapse recovery) breaks long-term statistical cointegration with ETH.
- **Ornstein-Uhlenbeck Half-Life**: 114.2 daily bars and 750.6 4h bars.
- **Out-of-Sample Degradation**: Massive breakdown during 2024–2026 OOS period (-62.17R on 4h), reflecting structural SOL outperformance that burned mean-reversion short spread positions.
- **Falsification Verdict**: Structural decoupling; fatal trend-divergence losses.

### 3. SOL / BTC (1d & 4h)
- **Hedge Ratio ($\beta$)**: OLS $\beta = 1.6739$, TLS $\beta = 2.3495$.
- **Cointegration Failure**: Engle-Granger p-value of **0.4988** (1d) and **0.5250** (4h). Zero cointegrating vector exists between SOL and BTC across the multi-year sample.
- **Ornstein-Uhlenbeck Half-Life**: 272.4 daily bars and 1,794.6 4h bars.
- **Friction Stress Shock**: Yields -63.01R on 1d and -84.78R on 4h under 64 bps friction.
- **Falsification Verdict**: Complete non-stationarity; severe friction sensitivity.

---

## Strategy Graveyard Entry

Pursuant to QCP Governance Rules, all 6 candidates have been permanently entered into the immutable Strategy Graveyard:

```json
{
  "graveyard_entries": [
    {
      "strategy_id": "FAM-09-RV_BTC/ETH_1d",
      "verdict": "FALSIFIED",
      "primary_cause": "Non-stationary spread (EG p=0.4231 > 0.05), OU half-life 345 bars"
    },
    {
      "strategy_id": "FAM-09-RV_BTC/ETH_4h",
      "verdict": "FALSIFIED",
      "primary_cause": "Non-stationary spread (EG p=0.4332 > 0.05), OU half-life 2162 bars"
    },
    {
      "strategy_id": "FAM-09-RV_SOL/ETH_1d",
      "verdict": "FALSIFIED",
      "primary_cause": "Structural decoupling (EG p=0.2394 > 0.05), OOS -14.07R"
    },
    {
      "strategy_id": "FAM-09-RV_SOL/ETH_4h",
      "verdict": "FALSIFIED",
      "primary_cause": "Structural decoupling (EG p=0.2719 > 0.05), OOS -62.17R"
    },
    {
      "strategy_id": "FAM-09-RV_SOL/BTC_1d",
      "verdict": "FALSIFIED",
      "primary_cause": "Non-stationary spread (EG p=0.4988 > 0.05), DEV -65.96R"
    },
    {
      "strategy_id": "FAM-09-RV_SOL/BTC_4h",
      "verdict": "FALSIFIED",
      "primary_cause": "Non-stationary spread (EG p=0.5250 > 0.05), OU half-life 1794 bars"
    }
  ]
}
```

---

## Governance Decision & Allocation Impact

1. **Capital Allocation**: **`$0.00`** (No capital may be allocated to any FAM-09 strategy).
2. **Promotion Gate**: Promotion Governor has blocked all FAM-09 candidates from advancing to `CANDIDATE`, `HISTORICALLY_ROBUST`, or `PRODUCTION_ELIGIBLE`.
3. **Research Loop Verdict**: The hypothesis that crypto asset pairs maintain stationary cointegrated relationships viable for simple spread trading is **empirically rejected**. Future relative value research must explore sub-hourly microstructure cointegration (triangular arbitrage / funding basis) or dynamically time-varying Kalman filters rather than static rolling Z-scores.
