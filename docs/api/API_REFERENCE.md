# Crypto Platform — Canonical API Contract Specification

**API Version:** `v1.0.0-staging`  
**Base URL (Local):** `http://127.0.0.1:8080` (or `http://10.0.2.2:8080` for Android Emulator)  
**Base URL (Staging):** `https://crypto-platform-staging.onrender.com`  
**Security Headers:** `Authorization: Bearer <session_token>`, `Content-Type: application/json`

---

## 1. Unified Status & Classification Overview

Every API endpoint across the Crypto Platform is strictly classified as:
- **`IMPLEMENTED`**: Route active, handler fully functional, backed by domain services, integration-tested.
- **`PARTIALLY_IMPLEMENTED`**: Route active, but returns static mock/catalog or lacks persistent DB backing.
- **`PLANNED`**: Identified as required for full desktop workstation or mobile operation, but route not yet wired.

---

## 2. Comprehensive Endpoint Catalog

### Category 1: Health, Readiness & Version Probes

| Route | Method | Classification | Description | Request Body | Response Payload Summary |
| :--- | :---: | :---: | :--- | :--- | :--- |
| `/health` | GET | `IMPLEMENTED` | Cloud liveness & capital safety check | None | `{"status": "HEALTHY", "real_capital_authorized": 0.0, "live_trading_status": "DISABLED_FAIL_CLOSED"}` |
| `/ready` | GET | `IMPLEMENTED` | Supervisor loop & watchdog readiness probe | None | `{"status": "READY", "supervisor_running": true, "reconciliation_intact": true}` |
| `/version` | GET | `IMPLEMENTED` | Platform version and frozen research contract hash | None | `{"platform": "Crypto Platform", "king_contract_hash": "8fbc923a...", "contract_status": "VERIFIED_IMMUTABLE"}` |
| `/api/telemetry` | GET | `IMPLEMENTED` | Real-time system telemetry, uptime, memory, and style | None | `{"uptime_seconds": 3600, "active_symbols": 4, "agent_style": "AUTONOMOUS", "real_capital_authorized": 0.0}` |

---

### Category 2: Authentication & Multi-Tenancy

| Route | Method | Classification | Description | Request Body | Response Payload Summary |
| :--- | :---: | :---: | :--- | :--- | :--- |
| `/api/auth/register` | POST | `PARTIALLY_IMPLEMENTED` | Registers user (In-memory storage) | `{"email": str, "password": str, "name": str}` | `{"token": str, "user": {"user_id": str, "tenant_id": str}}` |
| `/api/auth/login` | POST | `PARTIALLY_IMPLEMENTED` | Verifies credentials & issues session token | `{"email": str, "password": str}` | `{"token": str, "user": {"user_id": str, "tenant_id": str}}` |
| `/api/auth/logout` | POST | `PARTIALLY_IMPLEMENTED` | Revokes active bearer session | None | `{"status": "logged_out"}` |
| `/api/auth/me` | GET | `PARTIALLY_IMPLEMENTED` | Returns authenticated user & tenant profile | None (Auth header) | `{"user_id": str, "email": str, "tenant_id": str, "role": str}` |

*Note: Classified as PARTIALLY_IMPLEMENTED because user accounts currently reside in memory (`AuthService._users_by_email`) rather than persistent SQLite.*

---

### Category 3: Market Universe & Multi-Timeframe State

| Route | Method | Classification | Description | Request Body | Response Payload Summary |
| :--- | :---: | :---: | :--- | :--- | :--- |
| `/api/king/overview` | GET | `IMPLEMENTED` | Master overview, 7-timeframe ladder status, active opportunity | None | `{"engine": "KING_CORE", "ladder": {"1M": "BULL", ...}, "active_opportunity": {...}}` |
| `/api/markets` | GET | `IMPLEMENTED` | Admitted perpetual universe & watchlist | None | `{"all_assets": ["BTCUSDT", ...], "priority_assets": [...], "watchlist": [...]}` |
| `/api/markets/{symbol}`| GET | `IMPLEMENTED` | Specific asset quotes, 24h delta, indicators | None | `{"symbol": "BTCUSDT", "price": 64850.0, "timeframes": {...}}` |
| `/api/markets/watchlist`| POST | `IMPLEMENTED` | Toggle symbol on user watchlist | `{"symbol": "BTCUSDT"}` | `{"status": "updated", "watchlist": ["BTCUSDT", ...]}` |

---

### Category 4: Strategy Catalogue & Strategy Lab (Research)

| Route | Method | Classification | Description | Request Body | Response Payload Summary |
| :--- | :---: | :---: | :--- | :--- | :--- |
| `/api/strategies` | GET | `IMPLEMENTED` | Canonical catalog of 11 strategy families | None | `[{"id": "strat_01", "name": "...", "target_r": 4.0, ...}]` |
| `/api/strategy-lab/parse` | POST | `IMPLEMENTED` | Parse natural-language strategy specification | `{"prompt": str}` | `{"specification": {"universe": [...], "style": str, "target_r": 4.0}}` |
| `/api/strategy-lab/evaluate` | POST | `IMPLEMENTED` | Evaluate candidate spec against causal engine | `{"specification": {...}}` | `{"win_rate": 0.672, "expectancy_r": 0.888, "profit_factor": 4.92}` |
| `/api/strategy-lab/copilot` | POST | `IMPLEMENTED` | Strategy Copilot chat & refinement | `{"prompt": str}` | `{"response": str, "suggested_adjustments": {...}}` |

---

### Category 5: Backtesting & Forward Validation

| Route | Method | Classification | Description | Request Body | Response Payload Summary |
| :--- | :---: | :---: | :--- | :--- | :--- |
| `/api/backtests` | GET | `IMPLEMENTED` | Benchmark replay metrics (9,608 trades) & runs | None | `{"benchmark_king": {"total_trades": 9608, "expectancy_r": 0.8885}, "recent_runs": [...]}` |
| `/api/forward-validation`| GET | `IMPLEMENTED` | Walk-forward shadow validation telemetry | None | `{"status": "FORWARD_TESTING_ACTIVE", "runs": [...]}` |

---

### Category 6: Trading Operations & Execution Blotters

| Route | Method | Classification | Description | Request Body | Response Payload Summary |
| :--- | :---: | :---: | :--- | :--- | :--- |
| `/api/positions` | GET | `IMPLEMENTED` | Active & closed simulated paper positions | None | `{"active_positions": [...], "closed_positions": [...]}` |
| `/api/orders` | GET | `IMPLEMENTED` | Historical paper orders executed by simulator | None | `[{"order_id": str, "symbol": str, "fill_price": float, ...}]` |
| `/api/decisions` | GET | `IMPLEMENTED` | Append-only decision ledger (TRADE & NO_TRADE) | None | `[{"cycle_id": str, "decision": "TRADE", "attribution": {...}}]` |
| `/api/agent/style` | POST | `IMPLEMENTED` | Change execution style (SWING, INTRADAY, etc.) | `{"style": str}` | `{"status": "style_updated", "style": "SWING"}` |
| `/api/agent/pause` | POST | `IMPLEMENTED` | Pause automated cycle evaluations | None | `{"status": "paused"}` |
| `/api/agent/resume` | POST | `IMPLEMENTED` | Resume automated cycle evaluations | None | `{"status": "resumed"}` |
| `/api/system/halt` | POST | `IMPLEMENTED` | Emergency stop (halts all execution loops) | None | `{"status": "system_halted"}` |

---

### Category 7: Risk Management, Reconciliation & Monitoring

| Route | Method | Classification | Description | Request Body | Response Payload Summary |
| :--- | :---: | :---: | :--- | :--- | :--- |
| `/api/risk` | GET | `IMPLEMENTED` | Real-time portfolio heat, circuit breakers | None | `{"current_heat_pct": 0.0, "max_portfolio_heat_pct": 3.0, "circuit_breakers": {...}}` |
| `/api/reconciliation` | GET | `IMPLEMENTED` | Internal state vs broker reconciliation report | None | `{"is_reconciled": true, "discrepancies": [], "status": "RECONCILED"}` |
| `/api/drift` | GET | `IMPLEMENTED` | Statistical strategy drift & degradation metrics | None | `{"drift_detected": false, "p_value": 0.85, "z_score": 0.12}` |
| `/api/alerts` | GET | `IMPLEMENTED` | Recent operational, risk, and safety alerts | None | `[{"alert_id": str, "severity": "INFO", "title": str, "message": str}]` |
| `/api/accounts` | GET | `IMPLEMENTED` | Registered paper & sandbox broker accounts | None | `[{"account_id": "PAPER-001", "balance_usd": 100000.0, "type": "PAPER"}]` |
| `/api/brokers` | GET | `IMPLEMENTED` | Registered broker venue integrations | None | `[{"venue": "BINANCE", "mode": "TESTNET", "is_live": false}]` |

---

## 3. Standardized Error Envelope (RFC 7807)

All non-2xx responses adhere to the standard structured error format:

```json
{
  "type": "about:blank",
  "title": "Bad Request",
  "status": 400,
  "detail": "Invalid parameter 'symbol'. Admitted symbols: BTCUSDT, ETHUSDT, SOLUSDT, BNBUSDT.",
  "instance": "/api/markets/INVALID"
}
```

---

## 4. Machine-Readable OpenAPI 3.1 Definition

A complete OpenAPI 3.1 schema is maintained at `docs/api/openapi.yaml` describing all shared types, schemas, query parameters, and security schemes for code-generation in Kotlin (Android) and TypeScript/JavaScript (Web).
