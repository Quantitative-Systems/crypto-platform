# Open-Source Research Notes: Jesse & NautilusTrader

## 1. Jesse Framework
- **Repository:** [`jesse-ai/jesse`](https://github.com/jesse-ai/jesse)
- **License:** MIT (Permissive)
- **Core Paradigm:** Event-driven, 1-minute resolution multi-timeframe simulation with zero lookahead guarantees.

### Key Architectural Strengths
1. **Intraday Multi-Timeframe Consolidation:**
   - In Jesse, strategies can define routes across multiple timeframes (e.g. 1h, 4h, 1d).
   - Higher timeframe indicators and states are **only updated upon candle close** of that higher timeframe. If the backtest is currently at 14:15, a 4h candle closing at 16:00 cannot expose its high, low, or close to the strategy.
   - This exact causal pattern matches our `DiscoveryResearchRunner` memoization by closed timestamp.
2. **Deterministic Position Sizing & Invalidation:**
   - Jesse enforces position sizing as: `qty = (account_balance * risk_percent) / (entry_price - stop_loss)`.
   - Slippage and exchange fees are accounted for immediately upon order fill.
3. **Genetic Algorithm & Optuna Integration:**
   - Built-in parameter search utilizing genetic algorithms to discover robust parameter spaces while penalizing drawdown and trade infrequency.

---

## 2. NautilusTrader
- **Repository:** [`nautechsystems/nautilus_trader`](https://github.com/nautechsystems/nautilus_trader)
- **License:** LGPL-3.0 (Weak Copyleft)
- **Core Paradigm:** Institutional-grade hybrid architecture (compiled Rust core with Python strategy runtime), microsecond event-driven simulation, and strict order state machines.

### Key Architectural Strengths
1. **Institutional Order State Machine:**
   - Orders progress through explicit deterministic states: `PENDING_NEW -> SUBMITTED -> ACCEPTED -> PARTIALLY_FILLED -> FILLED / CANCELED / EXPIRED`.
   - Models simulated latency (e.g. 5ms to 50ms exchange wire latency) so orders cannot fill instantly at the same tick timestamp they were submitted.
2. **Pre-Trade Risk Engine:**
   - Decoupled from strategy logic. Before any order reaches the simulated or live exchange, it passes through risk filters:
     - Maximum order size
     - Maximum position leverage
     - Maximum allowable account drawdown
     - Order throttle limits (rate limiting)
3. **Derivatives Cash-Flow Accounting:**
   - Tracks cash flow for linear and inverse contracts, margin collateral maintenance, unrealized PnL mark-to-market calculations, and periodic 8-hour funding rate debits/credits.

---

## 3. Synthesis for Crypto-Platform
- **Adopt from Jesse:** The clean MIT-licensed position sizing and causal multi-timeframe candle close discipline.
- **Adopt from NautilusTrader:** The institutional concept of an independent Pre-Trade Risk Engine and deterministic order lifecycle modeling.
