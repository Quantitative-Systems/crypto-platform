# Open-Source Research Notes: Hummingbot & VectorBT

## 1. Hummingbot
- **Repository:** [`hummingbot/hummingbot`](https://github.com/hummingbot/hummingbot)
- **License:** Apache-2.0 (Permissive)
- **Core Paradigm:** High-frequency market-making, cross-exchange arbitrage, and Strategy V2 Controller/Executor pattern.

### Key Architectural Strengths
1. **Strategy V2 Framework (Controllers vs. Executors):**
   - **Controllers:** High-level decision engines that determine market bias, inventory limits, and broad trading parameters.
   - **Executors:** Discrete, self-contained execution workers (`PositionExecutor`, `ArbitrageExecutor`, `DCAExecutor`, `GridExecutor`) responsible for the lifecycle of a specific trade setup.
   - Once a Controller triggers an entry, a `PositionExecutor` autonomously manages the order entry, trailing stop, take-profit, and emergency timeout.
2. **Arbitrage & Market Neutral Domains:**
   - Gold standard implementation of:
     - Spot-Perpetual Basis Arbitrage (Cash-and-Carry)
     - Cross-Exchange Spread Arbitrage
     - Funding Rate Harvesting
   - Hummingbot proves that non-directional arbitrage strategies require completely separate accounting, inventory tracking, and risk models compared to directional strategies.

---

## 2. VectorBT
- **Repository:** [`polakowo/vectorbt`](https://github.com/polakowo/vectorbt)
- **License:** Apache-2.0 (Core)
- **Core Paradigm:** High-throughput vectorized matrix simulation accelerated via NumPy broadcasting and Numba JIT compilation.

### Key Architectural Strengths
1. **Hyper-Fast Parameter Sweeps:**
   - By structuring backtests as multidimensional arrays (Time $\times$ Assets $\times$ Parameters), VectorBT evaluates tens of thousands of parameter combinations in seconds.
2. **Parameter Stability & Plateau Heatmaps:**
   - Evaluates performance across continuous parameter grids (e.g. Stop Distance vs. EMA Period).
   - Demonstrates that an institutional edge is characterized by a **broad, flat plateau of positive expectancy**, whereas curve-fitted noise appears as an isolated sharp spike surrounded by negative returns.
3. **Monte Carlo Permutation Testing:**
   - Shuffles trade sequences and samples with replacement to estimate drawdown probability distributions and value-at-risk (VaR).

---

## 3. Synthesis for Crypto-Platform
- **Adopt from Hummingbot:** Separate research domains for Arbitrage (`research/arbitrage/`), Hedging (`research/hedging/`), and Market-Neutral (`research/market_neutral/`).
- **Adopt from VectorBT:** Monte Carlo robustness testing and parameter stability scoring across parameter neighborhoods.
