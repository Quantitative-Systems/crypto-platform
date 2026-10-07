# Crypto Trading Platform — Systematic Risk Management Specification

**Document Version:** 1.0.0  
**Classification:** Core System Risk Engine Standard  

---

## 1. The Supreme Fail-Closed Invariant

The Risk Engine operates as an independent, decoupled gatekeeper between Strategy Intents and Order Execution.
Strategies emit suggestions (`OrderIntent`); the Risk Firewall evaluates and approves, modifies, or rejects them.

> [!IMPORTANT]
> **FAIL-CLOSED INVARIANT:**  
> On any telemetry gap, missing price, stale data, unexpected exception, or boundary violation:  
> **EXPECTED RESULT = NO NEW ORDER.**

---

## 2. 22 Pre-Trade Risk Boundaries

| # | Boundary Name | Rule Code | Evaluation Logic | Default Threshold |
|---|---|---|---|---|
| 1 | **Global Kill Switch** | `GLOBAL_KILL_SWITCH_ACTIVE` | Checks global kill switch registry | Active flag |
| 2 | **Tenant Kill Switch** | `TENANT_KILL_SWITCH_ACTIVE` | Checks tenant kill switch registry | Active flag |
| 3 | **Account Kill Switch** | `ACCOUNT_KILL_SWITCH_ACTIVE` | Checks account kill switch registry | Active flag |
| 4 | **Venue Kill Switch** | `VENUE_KILL_SWITCH_ACTIVE` | Checks venue kill switch registry | Active flag |
| 5 | **Strategy Kill Switch** | `STRATEGY_KILL_SWITCH_ACTIVE` | Checks strategy kill switch registry | Active flag |
| 6 | **Instrument Kill Switch** | `INSTRUMENT_KILL_SWITCH_ACTIVE` | Checks instrument kill switch registry | Active flag |
| 7 | **Venue Disconnect** | `EXCHANGE_DISCONNECTED` | Checks if exchange websocket/REST is live | Disconnected flag |
| 8 | **Reconciliation Integrity** | `RECONCILIATION_OUT_OF_SYNC` | Freezes account if discrepancies detected | Out-of-sync flag |
| 9 | **Unknown Order State** | `UNKNOWN_ORDER_STATE_PENDING` | Freezes account if any orders are UNKNOWN | Active unknown orders |
| 10 | **Duplicate Order Detection** | `DUPLICATE_ORDER` | Checks intent ID in deduplication cache | 5,000ms window |
| 11 | **Runaway Rate Limit** | `RUNAWAY_RATE_LIMIT` | Counts orders generated in last 1,000ms | Max 5 orders/second |
| 12 | **Missing Telemetry** | `MISSING_MARKET_DATA` | Rejects order if ticker is None | None ticker |
| 13 | **Stale Market Data** | `STALE_MARKET_DATA` | Age of latest market ticker > threshold | Max 5,000ms |
| 14 | **Clock Drift Protection** | `CLOCK_DRIFT_EXCEEDED` | Difference between server & venue clock | Max 3,000ms |
| 15 | **Stale Signal Age** | `STALE_SIGNAL` | Age of strategy intent > threshold | Max 2,000ms |
| 16 | **Daily Loss Limit** | `DAILY_LOSS_LIMIT_BREACH` | Account drawdown from 00:00 UTC | Max 5.0% daily loss |
| 17 | **HWM Drawdown Limit** | `DRAWDOWN_LIMIT_BREACH` | Account drawdown from all-time peak | Max 12.0% HWM drawdown |
| 18 | **Order Notional Limits** | `MAX_NOTIONAL_BREACH` | Order size in USD > max limit | Max $50,000 / Min $5 |
| 19 | **Position Size Limit** | `MAX_POSITION_SIZE_BREACH` | Net position notional in USD after fill | Max $100,000 per coin |
| 20 | **Portfolio Exposure Limit** | `MAX_PORTFOLIO_EXPOSURE_BREACH` | Gross sum of all open positions in USD | Max $250,000 |
| 21 | **Gross Leverage Cap** | `LEVERAGE_LIMIT_BREACH` | Gross portfolio notional / equity | Max 2.0x leverage |
| 22 | **Asset Concentration Limit** | `CONCENTRATION_LIMIT_BREACH` | Single coin notional / total equity | Max 35.0% in one asset |

---

## 3. Account Circuit Breaker State Machine

Each account is continuously guarded by an `AccountCircuitBreaker`:

```
               ┌──────────┐
               │  NORMAL  │
               └────┬─────┘
                    │ Daily loss >= 3.0%
                    ▼
               ┌──────────┐
               │ DE-RISK  │  (Throttles order sizes by 50%)
               └────┬─────┘
                    │ Daily loss >= 5.0%
                    ▼
          ┌───────────────────┐
          │   CIRCUIT_TRIP    │  (Halts all new orders until 00:00 UTC)
          └─────────┬─────────┘
                    │ HWM Drawdown >= 12.0%
                    ▼
          ┌───────────────────┐
          │     SAFE_MODE     │  (Systemic freeze; requires manual admin reset)
          └───────────────────┘
```
