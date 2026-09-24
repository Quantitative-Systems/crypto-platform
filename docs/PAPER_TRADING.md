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

### Crash Recovery & Reconnection Safety
When `ForwardPaperTradingDaemon` restarts:
1. It queries the local SQLite database for the account ID.
2. Rehydrates active open positions and loads the last recorded equity and peak equity.
3. Explicitly unsubscribes prior daemon callbacks via `disconnect_market_data()` before attaching the newly rehydrated daemon, preventing duplicate callback executions and duplicate SQLite ledger writes.
4. Resumes streaming from the live WebSocket without duplicating orders or resetting performance curves.

---

## 4. Execution Commands & Telemetry Artifacts

Forward paper trading can be run via two supported CLI commands:

```bash
# 1. Forward Paper Soak Test (Multi-strategy soak with controlled restart audit and public Binance feed)
python3 -m crypto_platform.cli soak --duration 10

# 2. Forward Paper Trading Daemon (Dedicated forward paper session with real-time public feeds)
python3 -m crypto_platform.cli forward-paper --duration 10

# 3. Reconcile and compare backtest, validation, OOS, and forward-paper evidence
python3 -m crypto_platform.cli compare
```

### Telemetry Artifacts
- `research/results/crypto_platform/soak_test_summary.json`: Multi-strategy soak run status, events processed, restart audit verification, and zero live capital invariant check.
- `research/results/crypto_platform/forward_paper_summary.json`: Forward paper session metrics, latency, reconnect count, and open positions.
- `research/results/crypto_platform/backtest_vs_oos_vs_paper.json`: Quantitative multi-tier reconciliation across DEV, VAL, OOS, FORWARD PAPER, and LIVE tiers.
- `research/results/crypto_platform/profitability_validation_report.md`: Institutional profitability audit report.
