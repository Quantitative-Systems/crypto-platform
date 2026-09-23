# Crypto Trading Platform — Forward Real-Time Paper Trading Engine

**Document Version:** 1.0.0  
**Classification:** Pre-Production Validation Standard  

---

## 1. Why Historical Backtests Are Never Enough

Historical backtests suffer from survivorship bias, idealized fill assumptions, and zero network latency. The Crypto Trading Platform requires every strategy candidate to spend a **minimum of 30 to 90 days in Forward Paper Trading** before any live capital allocation can be requested.

In Forward Paper Trading:
* Strategies consume **real-time live public market data** (via WebSocket streaming).
* Execution is evaluated bar-by-bar and tick-by-tick.
* Real network latencies, packet jitter, and broker reconnects are observed.

---

## 2. Microstructure Execution Fidelity

The `MicrostructurePaperSimulator` models real order book interactions:

1. **Spread Crossing:**
   * Market buy orders fill at the current best ask.
   * Market sell orders fill at the current best bid.
   * Limit orders only fill when market price trades completely through the limit price.

2. **Fee Schedules:**
   * Maker orders: 2 bps fee.
   * Taker orders: 6 bps fee on futures, 10 bps on spot.
   * Post-Only rejection: if a post-only limit order would cross the spread immediately, it is rejected without fill.

3. **Size-Dependent Slippage:**
   $$\text{Slippage (bps)} = \text{Base Slippage} \times \left(1.0 + 0.1 \times \frac{\text{Order Notional}}{\$10,000}\right)$$

---

## 3. Durable SQLite Persistence & Crash Recovery

All forward paper sessions are backed by `SQLitePaperLedger` running in WAL mode:

* **Orders Table:** Full history of working, filled, and cancelled simulated orders.
* **Fills Table:** Execution price, size, fee, timestamp, and maker/taker flag.
* **Positions Table:** Mark-to-market position size, entry price, and unrealized PnL.
* **Equity History Table:** Periodic equity snapshots, drawdown tracking, and cumulative fees.
* **Audit Log:** Records every risk firewall rejection, sequence gap, and reconnect event.

### Crash Recovery
When `ForwardPaperTradingDaemon` restarts:
1. It queries the local SQLite database for the account ID.
2. Rehydrates active open positions and loads the last recorded equity and peak equity.
3. Resumes streaming from the live WebSocket without duplicating orders or resetting performance curves.
