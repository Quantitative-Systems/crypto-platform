# Relative Value Baseline Econometrics Evidence

**Platform:** Quantitative Crypto Platform (QCP)
**Experiment:** RELATIVE_VALUE_BASELINE_RESEARCH
**Generated UTC:** 2026-09-17T13:11:53.365784+00:00

## Summary
- **Total Candidates:** 6
- **Qualified Candidates:** 0
- **Falsified Candidates:** 5
- **Fragile Candidates:** 1

### BTC/ETH_1d (BTC/USDT / ETH/USDT)
- **Verdict:** `FALSIFIED_NO_COINTEGRATION`
  - Fails cointegration tests: Engle-Granger p=0.3787 (ADF=-2.12), Johansen Trace=7.77.

#### Cointegration Metrics
- Hedge Ratio (Beta): 0.8277
- Engle-Granger p-value: 0.3787
- Is Engle-Granger Cointegrated: False
- Johansen Trace Statistic: 7.7736
- Is Johansen Cointegrated: False
- Half-Life: 345.22 bars

#### OOS Sample Performance
- Total Trades: 33
- Win Rate: 51.52%
- Total Net R: 6.03
- Profit Factor: 1.40
- Max Drawdown R: 6.28
- Total Friction Drag R: 2.11

### BTC/ETH_4h (BTC/USDT / ETH/USDT)
- **Verdict:** `FALSIFIED_NO_COINTEGRATION`
  - Fails cointegration tests: Engle-Granger p=0.4547 (ADF=-1.87), Johansen Trace=7.51.

#### Cointegration Metrics
- Hedge Ratio (Beta): 0.8276
- Engle-Granger p-value: 0.4547
- Is Engle-Granger Cointegrated: False
- Johansen Trace Statistic: 7.5063
- Is Johansen Cointegrated: False
- Half-Life: 2162.21 bars

#### OOS Sample Performance
- Total Trades: 224
- Win Rate: 45.09%
- Total Net R: -24.50
- Profit Factor: 0.51
- Max Drawdown R: 25.08
- Total Friction Drag R: 14.34

### SOL/ETH_1d (SOL/USDT / ETH/USDT)
- **Verdict:** `FALSIFIED_NO_COINTEGRATION`
  - Fails cointegration tests: Engle-Granger p=0.2000 (ADF=-2.72), Johansen Trace=10.33.

#### Cointegration Metrics
- Hedge Ratio (Beta): 2.0786
- Engle-Granger p-value: 0.2000
- Is Engle-Granger Cointegrated: False
- Johansen Trace Statistic: 10.3255
- Is Johansen Cointegrated: False
- Half-Life: 114.24 bars

#### OOS Sample Performance
- Total Trades: 29
- Win Rate: 75.86%
- Total Net R: 29.03
- Profit Factor: 4.19
- Max Drawdown R: 3.11
- Total Friction Drag R: 1.86

### SOL/ETH_4h (SOL/USDT / ETH/USDT)
- **Verdict:** `FALSIFIED_NO_COINTEGRATION`
  - Fails cointegration tests: Engle-Granger p=0.2767 (ADF=-2.46), Johansen Trace=9.82.

#### Cointegration Metrics
- Hedge Ratio (Beta): 2.0788
- Engle-Granger p-value: 0.2767
- Is Engle-Granger Cointegrated: False
- Johansen Trace Statistic: 9.8164
- Is Johansen Cointegrated: False
- Half-Life: 750.55 bars

#### OOS Sample Performance
- Total Trades: 214
- Win Rate: 43.46%
- Total Net R: -47.58
- Profit Factor: 0.53
- Max Drawdown R: 49.81
- Total Friction Drag R: 13.70

### SOL/BTC_1d (SOL/USDT / BTC/USDT)
- **Verdict:** `FRAGILE_SLOW_MEAN_REVERSION`
  - Spread half-life (272.4 bars) exceeds threshold (45.0 bars).

#### Cointegration Metrics
- Hedge Ratio (Beta): 1.6739
- Engle-Granger p-value: 0.4954
- Is Engle-Granger Cointegrated: False
- Johansen Trace Statistic: 15.6623
- Is Johansen Cointegrated: True
- Half-Life: 272.43 bars

#### OOS Sample Performance
- Total Trades: 28
- Win Rate: 57.14%
- Total Net R: 2.23
- Profit Factor: 1.09
- Max Drawdown R: 7.42
- Total Friction Drag R: 1.79

### SOL/BTC_4h (SOL/USDT / BTC/USDT)
- **Verdict:** `FALSIFIED_NO_COINTEGRATION`
  - Fails cointegration tests: Engle-Granger p=0.5318 (ADF=-1.61), Johansen Trace=15.14.

#### Cointegration Metrics
- Hedge Ratio (Beta): 1.6754
- Engle-Granger p-value: 0.5318
- Is Engle-Granger Cointegrated: False
- Johansen Trace Statistic: 15.1368
- Is Johansen Cointegrated: False
- Half-Life: 1794.59 bars

#### OOS Sample Performance
- Total Trades: 197
- Win Rate: 51.27%
- Total Net R: -13.70
- Profit Factor: 0.81
- Max Drawdown R: 14.59
- Total Friction Drag R: 12.61

