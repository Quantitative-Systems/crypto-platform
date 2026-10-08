# Crypto Platform — Staging Environment Specification

## 1. Staging Purpose & Guarantees

The **STAGING Environment** is a persistent, cloud-hosted validation deployment designed to test real-world network latency, background worker persistence, mobile API connectivity, and multi-timeframe state generation without risking capital.

### Non-Negotiable Operational Guarantees:
- **Real Capital Exposure:** Strictly `$0.00`
- **Execution Mode:** `PAPER` and `BINANCE_TESTNET`
- **Exchange Credentials:** Public Testnet keys only (or pure simulated matching)
- **Live Order Gate:** `HARD_DISABLED_FAIL_CLOSED`
- **Target Geometry Floor:** $\ge 4.0\text{R}$ minimum reward-to-risk ratio
- **Max Risk Per Trade:** $\le 1.0\%$ of simulated equity
- **Max Portfolio Heat:** $\le 3.0\%$ aggregate exposure

---

## 2. Infrastructure & Service Topology

| Component | Provider / Host | Details |
| :--- | :--- | :--- |
| **Backend Service** | Render Free Web Service | Docker container (`Dockerfile`), 512MB RAM, shared vCPU |
| **Ingress Domain** | `https://crypto-platform-staging.onrender.com` | Automated SSL termination, HTTP/2 & WebSocket support |
| **Web Terminal** | Vercel Edge / Render Static | Reverse proxies `/api/*` to staging backend |
| **Worker Process** | Same container | Runs `AutonomousTradingSupervisor` in persistent asyncio loop |
| **Data Feeds** | Binance Testnet Public WSS | Streams live testnet prices for BTCUSDT, ETHUSDT, SOLUSDT, BNBUSDT |

---

## 3. Configuration Reference

Staging environment variables are derived from `.env.staging.example`:

```bash
# Environment Identity
ENVIRONMENT=STAGING
PLATFORM_ENV=staging

# Network & Server
PORT=8080
HOST=0.0.0.0
CORS_ALLOWED_ORIGINS=*

# Safety Boundaries
REAL_CAPITAL_AUTHORIZED_USD=0.00
LIVE_TRADING_ENABLED=false
STRATA_LIVE_KEY_HASH=fail_closed_testnet_mode_active

# Trading Simulation
DEFAULT_SIMULATED_EQUITY=100000.00
ACTIVE_SYMBOLS=BTCUSDT,ETHUSDT,SOLUSDT,BNBUSDT
MIN_FRACTAL_CONFIDENCE=0.50
TARGET_FLOOR_R=4.0
MAX_RISK_PER_TRADE_PCT=1.0
MAX_PORTFOLIO_HEAT_PCT=3.0
```

---

## 4. API Endpoints Available in Staging

| Endpoint | HTTP Method | Description |
| :--- | :--- | :--- |
| `/health` | GET | Cloud load-balancer liveness check |
| `/ready` | GET | Readiness probe checking supervisor loop & watchdog |
| `/version` | GET | Platform version & frozen research contract SHA-256 seal |
| `/api/auth/register` | POST | Register staging test account |
| `/api/auth/login` | POST | Login and receive bearer token |
| `/api/auth/me` | GET | Session details and assigned user role |
| `/api/king/overview` | GET | Master quantitative overview & 7-timeframe status |
| `/api/markets` | GET | Admitted crypto perpetual universe |
| `/api/markets/{symbol}` | GET | Symbol-specific candle telemetry & indicators |
| `/api/strategies` | GET | Strategy library registry catalog |
| `/api/strategy-lab/parse` | POST | Natural language strategy parser |
| `/api/backtests` | GET | Historical backtest catalog and replay benchmarks |
| `/api/forward-validation` | GET | Walk-forward validation results |
| `/api/positions` | GET | Active & closed simulated paper positions |
| `/api/orders` | GET | Simulated order blotter |
| `/api/risk` | GET | Real-time risk governor & portfolio heat metrics |
| `/api/telemetry` | GET | Platform telemetry, uptime, memory, and execution mode |
| `/api/reconciliation` | GET | Invariant state reconciliation audit |
| `/api/drift` | GET | Statistical strategy drift detection |
| `/api/alerts` | GET | Operational alerts feed |
| `/api/system/halt` | POST | Emergency platform pause switch |

---

## 5. Maintenance & State Reset

If the staging database or in-memory simulation needs to be refreshed:
1. Re-deploy or restart the Render service.
2. The supervisor automatically re-seeds its 7-timeframe market state cache from the canonical seed dataset on boot.
3. Verify state integrity via CLI:
   ```bash
   python cli.py reconcile
   python cli.py health
   ```
