# Crypto Trading Platform — Technical Architecture & Subsystem Specification

**Document Version:** 1.0.0  
**Target Environment:** Production Non-Custodial Multi-Tenant Quantitative Crypto Trading Platform  
**System Classification:** Asynchronous Event-Driven Quantitative Trading System  

---

## 1. High-Level Subsystem Architecture

The platform architecture strictly separates data planes, research evaluation, risk gating, order management, execution routing, and account state reconciliation.

```
                  ┌────────────────────────────────────────┐
                  │      Public & Private Market Data      │
                  │   Binance (Spot/Futures), Bybit, CCXT  │
                  └───────────────────┬────────────────────┘
                                      │ WebSocket / REST
                                      ▼
                  ┌────────────────────────────────────────┐
                  │       Real-Time Market Data Stream      │
                  │     crypto_platform.market_data        │
                  │  (Monotonic checks, Gap detection,     │
                  │   Heartbeats, Tickers & Candles)       │
                  └───────────────────┬────────────────────┘
                                      │ Events (TickerEvent, CandleEvent)
                                      ▼
                  ┌────────────────────────────────────────┐
                  │            Strategy Engine             │
                  │    crypto_platform.strategy_engine     │
                  │  (Trend, MeanRev, Mom, StatArb, Carry) │
                  └───────────────────┬────────────────────┘
                                      │ Emits OrderIntent (No venue keys)
                                      ▼
                  ┌────────────────────────────────────────┐
                  │       22-Boundary Risk Firewall        │
                  │      crypto_platform.risk_engine       │
                  │  (Fail-Closed, Leverage, KillSwitches, │
                  │   Circuit Breakers, Stale Telemetry)   │
                  └───────────────────┬────────────────────┘
                                      │ Approved RiskDecision
                                      ▼
                  ┌────────────────────────────────────────┐
                  │      Order Management System (OMS)     │
                  │    crypto_platform.order_management    │
                  │  (Deterministic cID, Legal Lifecycle, │
                  │   Positions Ledger, Fill Tracking)     │
                  └─────────┬────────────────────┬─────────┘
                            │                    │
            PAPER Plane     │                    │ DEMO / LIVE-CANARY Planes
            ▼               │                    ▼
┌───────────────────────────┴───────┐   ┌───────────────────────────────────┐
│     Microstructure Simulator      │   │         Exchange Adapters         │
│  crypto_platform.paper_trading    │   │ crypto_platform.exchange_adapters │
│ (Spread crossing, Maker/Taker fees│   │  (Non-custodial, Token Bucket,    │
│  Slippage, SQLite Ledger)         │   │   REST Signer, Order Router)      │
└───────────────────────────────────┘   └─────────────────┬─────────────────┘
                                                          │
                                                          ▼
                                        ┌───────────────────────────────────┐
                                        │    State Reconciliation Engine    │
                                        │    crypto_platform.reconciliation │
                                        │ (500ms-5s Loop, Ghost Orders,     │
                                        │  Automated Local State Restore)   │
                                        └─────────────────┬─────────────────┘
                                                          │
                                                          ▼
                                        ┌───────────────────────────────────┐
                                        │       LIVE-CANARY Harness         │
                                        │    crypto_platform.live_canary    │
                                        │ (14-Step Verifier, Micro-Capital  │
                                        │  Limits, Fail-Closed Failsafe)    │
                                        └───────────────────────────────────┘
```

---

## 2. Four Operating Planes Specification

1. **`PAPER`**: Local event-driven forward paper trading driven by live production WebSocket feeds with zero broker execution risk.
2. **`DEMO`**: Exchange sandbox / testnet execution using broker testnet REST/WebSocket endpoints and simulated testnet funds.
3. **`LIVE-CANARY`**: Controlled micro-capital real-money trading using production exchange gateways under strict risk firewall limits, non-custodial API key verification, and two-phase arming.
4. **`LIVE`**: Unrestricted full-capital production trading — **permanently locked by platform governance invariants**.

---

## 3. Core Subsystems

### 3.1 Market Data (`crypto_platform.market_data`)
* **Realtime Stream Manager:** Asynchronous WebSocket client (`PublicWebSocketClient`) connecting to Binance and Bybit public feeds.
* **Integrity Guardrails:** Sequence ID continuity, heartbeat ping/pong, timestamp inversion rejection, and stale data alarms (> 5000ms).
* **Canonical Schemas:** Normalizes raw exchange payloads into immutable `TickerEvent`, `CandleEvent`, and `OrderBookEvent`.

### 3.2 Strategy Engine (`crypto_platform.strategy_engine`)
* **Decoupled Plugin Architecture:** Subclasses `BaseStrategy`. Strategies consume market events and emit `OrderIntent` objects.
* **Zero Exchange Access:** Strategies never possess venue credentials or direct network access to brokers.
* **Supported Plugins:**
  - `TrendBreakoutStrategy`: Donchian channel breakouts with ATR volatility bounds.
  - `MeanReversionStrategy`: Rolling price z-score fading with trend protection.
  - `MomentumStrategy`: Time-series and cross-sectional momentum ranking.
  - `PairsTradingStrategy`: Cointegration spread mean-reversion with z-score collars.
  - `FundingCarryStrategy`: Delta-hedged perpetual funding rate harvest with regime exits.
  - `VolatilityExpansionStrategy`: ATR expansion breakout with dynamic trailing stops.
  - `SystematicInvestingStrategy`: Dollar-cost averaging (DCA) accumulation with value filter.

### 3.3 Risk Engine (`crypto_platform.risk_engine`)
* **Fail-Closed Invariant:** The Risk Engine is an independent, non-bypassable gatekeeper. On any violation or unhandled exception, it fails closed: `EXPECTED RESULT = NO NEW ORDER`.
* **22 Pre-Trade Boundaries:**
  1. Maximum Order Notional
  2. Maximum Position Notional
  3. Maximum Portfolio Exposure
  4. Gross Leverage Caps (2.0x max)
  5. Asset Concentration Limits (35% max in single coin)
  6. Daily Loss Limits (Circuit Breaker)
  7. Drawdown Limits (Safe Mode lock)
  8. Stale Market Data (> 2000ms)
  9. Stale Signals (> 2000ms)
  10. Missing Telemetry
  11. Clock Drift Protection (> 1500ms)
  12. Venue Disconnect Detection
  13. Duplicate Order Intent Detection
  14. Runaway Order Rate Limits
  15. Unknown Order State Freezing
  16. Reconciliation Integrity Freezing
  17. Global / Emergency Kill Switch
  18. Tenant-Level Kill Switch
  19. Account-Level Kill Switch
  20. Venue-Level Kill Switch
  21. Strategy-Level Kill Switch
  22. Instrument-Level Kill Switch

### 3.4 Order Management System (`crypto_platform.order_management`)
* **State Machine:** Strictly enforces legal lifecycle transitions:
  `CREATED -> RISK_CHECKED -> SUBMITTED -> ACKNOWLEDGED -> PARTIALLY_FILLED -> FILLED`
  and terminal states `REJECTED`, `CANCELLED`, `EXPIRED`, `FAILED`, `UNKNOWN`.
* **Idempotency:** Generates deterministic, venue-specific `client_order_id` (cID) to eliminate double execution under network retries.

### 3.5 Paper Trading Engine (`crypto_platform.paper_trading`)
* **Microstructure Simulator:** Evaluates price crossing, realistic maker (2 bps) vs taker (6 bps) fee schedules, liquidity-based slippage, and post-only order rejections.
* **Durable SQLite Persistence:** Commits all simulated orders, fills, positions, cash balances, equity points, and audit logs to disk with WAL mode for zero data loss across daemon restarts.

### 3.6 State Reconciliation Engine (`crypto_platform.reconciliation`)
* **Continuous Auditing:** Audits internal positions and open orders against exchange truth every 5 seconds (500ms in live canary).
* **Fail-Safe Freezing:** Discrepancies (ghost orders or size mismatches) immediately trip the Risk Firewall to block new order generation.
* **Safe State Restoration:** Restores local state from exchange ground truth without placing duplicate orders.

### 3.7 Security & Vault (`crypto_platform.security`)
* **Non-Custodial Guarantee:** Platform never touches customer custodial funds. API keys require zero withdrawal permissions.
* **AES-256-GCM Vault:** Envelope encryption using PBKDF2 HMAC-SHA256 key derivation with tenant-isolated salt and authenticated tags.

### 3.8 LIVE-CANARY Subsystem (`crypto_platform.live_canary`)
* **Execution Harness:** Controls micro-capital deployment through an explicit state machine (`DISARMED` -> `ARMED` -> `ACTIVE` -> `HALTED`).
* **14-Step Broker Pre-Flight Verifier:** Verifies authentication, balance, symbols, position mode, leverage, margin mode, min notional, market data, order permissions, strict withdrawal disability, clock drift, reconciliation clean slate, and emergency kill trip.
* **Failsafe Halting:** Sub-10ms emergency kill switch trips global firewall, cancels all broker orders, and blocks automatic restarts.
