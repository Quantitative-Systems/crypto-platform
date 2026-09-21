# QCP Strategy Grammar v2.0 Architecture

> **Mission**: A commercially deployable crypto market platform capable of researching, qualifying, allocating, risk-managing, executing, monitoring, and continuously researching multiple independent market-edge mechanisms.

## Core Tenets
1. **Hypothesis-Driven, Not Blind Data-Mining**: We test explicit structural market physics (Trend, Mean Reversion, Volatility Contraction), not random parameter sets.
2. **Causal Fidelity First**: No future leak. Executions occur on the open *after* the signal is generated. Stops take priority over targets (adverse-first execution).
3. **Decoupled Mechanics**: Signal Generation (Alpha) is strictly decoupled from Position Sizing (Risk) and Market Orders (Execution).
4. **Governance & Survivorship**: The platform automatically quarantines failing alpha logic. A strategy is not "good" because it backtests well once; it must survive Out-Of-Sample (OOS) Walk-Forward Optimization.

## 1. Multi-Timeframe Structural Foundation (The Grammar)

A valid market edge consists of a coordinated alignment across three temporal layers.

### **Sets (Holding Periods)**
- **Set 1**: 1 Month (HTF) → 1 Week (MTF) → 1 Day (LTF) [Macro Investing]
- **Set 2**: 1 Week (HTF) → 1 Day (MTF) → 4 Hour (LTF) [Core Swing]
- **Set 3**: 1 Day (HTF) → 4 Hour (MTF) → 1 Hour (LTF) [Standard Swing]
- **Set 4**: 4 Hour (HTF) → 1 Hour (MTF) → 15 Minute (LTF) [Short Swing]
- **Set 5**: 1 Hour (HTF) → 15 Minute (MTF) → 5 Minute (LTF) [Active Intraday]
- **Set 6**: 15 Minute (HTF) → 5 Minute (MTF) → 1 Minute (LTF) [Scalping]

### **Layer 1: HTF Bias (Market Context)**
*Sets the permitted trading direction.*
- **Trend Following**: EMA alignments, MACD expansion, directional DMI.
- **Mean Reversion**: Extreme RSI deviation, Bollinger Band excursions.
- **Volatility Regimes**: ATR expansion/contraction.
- *Rule*: If HTF is Bullish, MTF and LTF may only execute Longs.

### **Layer 2: MTF Setup (The Opportunity)**
*Defines the structural zone of interest.*
- **Pullback / Retracement**: Price returns to a mean (EMA, VWAP) within a trend.
- **Breakout / Squeeze**: Volatility contraction followed by directional expansion.
- **Structural Taps**: Price mitigating a Fair Value Gap (FVG) or Order Block.

### **Layer 3: LTF Entry (The Trigger)**
*The final timing mechanism for capital deployment.*
- **Momentum Displacement**: Engulfing candles, sudden volume profile shifts.
- **Rejection Signatures**: Pinbars, wicks at key structural boundaries.
- **Oscillator Hooks**: RSI/Stochastic crossing back in the direction of the HTF bias.

## 2. Platform Architecture Layers

### Layer A: The Signal Library (`alpha_signal_library.py`)
Encodes the raw math for Bias, Setup, and Entry mechanisms. Returns `-1`, `0`, or `1` state arrays based on strict causal data (data available at bar close).

### Layer B: The Combinatorial Engine (`strategy_grammar.py`)
Permutes valid combinations of HTF/MTF/LTF logic. Applies Regime Filters (e.g., Do not trade a Breakout setup in a Mean-Reverting regime).

### Layer C: The Evaluation Engine (`economic_evaluation_engine.py`)
Uses the `CausalTripleBarrierBacktester` to evaluate signals with strict risk geometry (SL, TP, Time Stop). Applies Maker/Taker fees and borrowing costs. 

### Layer D: The Discovery & Governance Lab (`empirical_alpha_discovery_engine.py`)
Sweeps the parameter space (ATR Multiplier, R:R, lookbacks) over In-Sample (DEV) data. Projects the optimal parameter set into Out-Of-Sample (VAL/OOS) windows. Strategies that fail OOS are quarantined.

## 3. Data Integrity & Validation

- Missing data is fatal. We do not forward-fill missing OHLCV bars for alpha generation, as this destroys causal integrity.
- Alpha models demanding unrecorded data (e.g., L2 Order Book) are registered but flagged as `DATA_UNAVAILABLE`.
