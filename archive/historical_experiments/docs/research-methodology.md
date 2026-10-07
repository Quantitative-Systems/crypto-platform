# Product 04: Research & Validation Methodology

Product 04 serves as the scientific laboratory for the entire platform. Its purpose is to answer a single empirical question: **Does the formalized strategy hypothesis possess a statistically defensible edge across realistic market conditions?**

## The Anti-Overfitting Doctrine
The platform explicitly guards against the primary failure mode of quantitative systems: curve-fitting. The research pipeline is governed by a strict sequential mandate:

`Baseline Measurement → Observe Failure Modes → Form Hypothesis → Change Single Variable → Out-of-Sample (OOS) Test → Accept/Reject`

We **do not** add arbitrary indicators or tune parameters merely to elevate backtest returns.

## Research Baseline Matrix
The platform's initial research evaluates two core strategy hypotheses across four timeframe combinations and three distinct underlying assets, establishing 24 independent baseline configurations.

**Hypotheses:**
1. Pullback Riding
2. Continuation Riding

**Timeframe Sets:**
1. 1M → 1W → 1D
2. 1W → 1D → 4H
3. 1D → 4H → 1H
4. 4H → 1H → 15M

**Assets:**
`BTC/USDT`, `ETH/USDT`, `SOL/USDT`

## Realistic Friction Modeling
A structural edge only exists if it survives transaction friction. The execution simulator incorporates:
- **Taker/Maker Fees**: Accurate institutional or retail-tier exchange cost assumptions.
- **Spread & Slippage**: Mathematical penalties applied to structural stop-loss and market-entry events.

## Walk-Forward Validation
The platform rejects simple in-sample backtesting. Models are trained and tested using rolling Out-of-Sample (OOS) windows to ensure stability across shifting market regimes.

## Performance Attribution & Metrics
Beyond basic Win Rate and Net Profit, the platform evaluates strategies on a multidimensional basis:
- **Expectancy & Profit Factor**
- **Maximum Drawdown & Recovery Factor**
- **Average R (Reward)**
- **Sharpe & Sortino Ratios**
- **Exit Attribution**: Separating outcomes driven by HTF Take Profit exits, MTF Structural Trailing exits, and LTF Stop-Loss failures.
- **Risk Rejection Attribution**: Quantifying setups that were valid structurally but correctly blocked by Product 03 capital controls.
