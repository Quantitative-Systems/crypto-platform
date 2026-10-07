# Crypto Platform Deployment & Operations Guide

## 1. Overview & Operational Principles

The Crypto Platform is an institutional-grade algorithmic trading and research platform designed with strict **fail-closed security boundaries**, non-custodial risk controls, and automated state reconciliation.

### Operating Modes & Environment Planes

| Environment | Supported Venues | Real Capital | Execution Model | Description |
|:---|:---|:---|:---|:---|
| `PAPER` | Binance / OKX / Deribit | **$0.00** | Simulated order book fills with fees & slippage | Forward-paper testing on live WebSocket market data feeds. |
| `DEMO` | Binance Testnet / Bybit Testnet | **$0.00** (Testnet assets only) | Broker Testnet API order routing + state reconciliation | Live broker integration verification, order submission, latency, and fills. |
| `LIVE` | Strictly Prohibited | **$0.00** | **FAIL-CLOSED LOCK** | Architecture enforces `live_capital_usd == 0.0`. Live trading cannot be activated. |

> [!CAUTION]
> **FAIL-CLOSED LIVE TRADING LOCK**: The platform raises an unrecoverable `RuntimeError` on startup if `PLATFORM_ENV=LIVE` or if `PLATFORM_LIVE_CAPITAL_USD > 0.0`. Live trading is completely locked by construction.

---

## 2. System Requirements & Prerequisites

### Hardware
* **CPU**: 4+ Cores (x86_64 or ARM64)
* **RAM**: 8 GB minimum (16 GB recommended for multi-stream historical warmups)
* **Disk**: 20 GB SSD storage (for SQLite state ledgers and historical cache)
* **Network**: Low-latency outbound Internet access (ports 443 HTTPS, 9443/443 WSS)

### Software
* Linux (Debian 12+, Ubuntu 22.04+, RHEL 9+) or macOS Sonoma+
* Python 3.12+ (or Docker Engine 24.0+ & Docker Compose 2.20+)
* SQLite 3.38+

---

## 3. Configuration & Secrets Management

Configuration is handled through environment variables, loaded automatically from a `.env` file or process environment via `crypto_platform.config.settings.PlatformSettings`.

### 1. Copy Configuration Template
```bash
cp .env.example .env
chmod 600 .env
```

### 2. Configuration Parameters

```ini
# Environment Mode: PAPER | DEMO (LIVE is strictly locked)
PLATFORM_ENV=PAPER

# Strictly enforced $0.00 live capital
PLATFORM_LIVE_CAPITAL_USD=0.0

# Logging level: DEBUG | INFO | WARNING | ERROR
PLATFORM_LOG_LEVEL=INFO

# State Persistence paths
PLATFORM_DB_PATH=research/paper_trading.db
PLATFORM_CACHE_DIR=market_data/cache

# Broker / Exchange Demo API Credentials (Testnet only)
BINANCE_API_KEY=""
BINANCE_API_SECRET=""
BINANCE_TESTNET=true

BYBIT_API_KEY=""
BYBIT_API_SECRET=""
BYBIT_TESTNET=true
```

> [!IMPORTANT]
> **Security Audit on Credentials**:
> * All exchange adapters enforce **read + trade only** permissions.
> * If an API key possesses **withdrawal permissions**, the adapter instantly rejects it with `PermissionSecurityError`.
> * Never commit `.env` or credentials to git.

---

## 4. Bare Metal / VM Deployment

### Step 1: Clone and Set Up Virtual Environment
```bash
git clone https://github.com/Quantitative-Systems/crypto-platform.git
cd crypto-platform

python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### Step 2: Verify Platform Health Check
Run the platform health pre-flight check to validate settings, database access, market data cache, and broker endpoints:
```bash
python3 -m crypto_platform.cli health
```
Expected output:
```json
{
  "status": "HEALTHY",
  "live_trading_locked": true,
  "live_capital_usd": 0.0,
  "environment": "PAPER",
  "checks": {
    "settings_validation": "PASSED",
    "database_connectivity": "PASSED",
    "market_data_cache": "PASSED (90 files)",
    "broker_testnet_endpoints": {
      "rest": "https://testnet.binancefuture.com",
      "ws": "wss://stream.binancefuture.com/ws"
    }
  }
}
```

### Step 3: Run Test Suite
Confirm all 168+ unit, integration, and contract tests pass:
```bash
pytest -v
```

### Step 4: Run Forward-Paper Session
Run the forward-paper trading engine across promoted books with live market data:
```bash
python3 -m crypto_platform.cli forward-paper --duration-hours 24
```

### Step 5: Run Demo Broker Integration
Run a demo trading session against broker testnet / sandbox:
```bash
# Binance Futures Testnet (mock or real testnet credentials)
python3 -m crypto_platform.cli demo --venue binance --mock

# Bybit Linear UTA Testnet
python3 -m crypto_platform.cli demo --venue bybit --mock
```

---

## 5. Container Deployment (Docker & Compose)

The repository provides a multi-stage `Dockerfile` (running unprivileged user `platform`) and a complete `docker-compose.yml`.

### Build Container
```bash
docker compose build
```

### Run Platform Services

1. **Forward-Paper Service (in background)**:
   ```bash
   docker compose up -d forward-paper
   ```

2. **Check Logs**:
   ```bash
   docker compose logs -f forward-paper
   ```

3. **Run Pre-Flight Health Check**:
   ```bash
   docker compose run --rm health-check
   ```

4. **Run Broker Demo Harness**:
   ```bash
   docker compose run --rm demo-trading
   ```

---

## 6. Broker / Exchange Adapter Integration

The adapter framework in `crypto_platform/exchange_adapters/` implements clean, unified abstractions:

```
[ Strategy Signal ]
        │
        ▼
[ Risk Engine ] (Concentration, Max Drawdown, Leverage Limits)
        │
        ▼
[ Order Management System (OMS) ] (Idempotency, State Transitions)
        │
        ▼
[ Exchange Adapter (BaseExchangeAdapter) ]
   ├── TokenBucketRateLimiter (Per-venue rate limiting)
   ├── Non-Custodial Permission Guard (Rejects withdrawal keys)
   └── Venues:
        ├── BinanceAdapter (testnet.binancefuture.com)
        ├── BybitAdapter (api-testnet.bybit.com)
        └── CCXTAdapter (Unified multi-venue gateway)
        │
        ▼
[ State Reconciliation Engine ] (Periodic poll: balance, open orders, positions)
```

### Integrating a Real Testnet Account
1. Create a Testnet account at [Binance Futures Testnet](https://testnet.binancefuture.com/) or [Bybit Testnet](https://testnet.bybit.com/).
2. Generate API key and secret with **Futures Trading** permissions (do NOT check withdrawal permissions).
3. Place them in `.env`:
   ```bash
   BINANCE_API_KEY="your_testnet_key"
   BINANCE_API_SECRET="your_testnet_secret"
   BINANCE_TESTNET=true
   ```
4. Run live demo session without `--mock`:
   ```bash
   python3 -m crypto_platform.cli demo --venue binance
   ```

---

## 7. State Persistence & Crash Recovery

* **Ledger Database**: All orders, fills, positions, and balances are written atomically to SQLite (`research/paper_trading.db`).
* **Funnel Snapshots**: Periodic JSON state snapshots are flushed to `research/results/crypto_platform/forward_paper_summary.json`.
* **Restart Recovery**:
  * On platform launch, `DemoTradingHarness.reconcile()` queries the exchange adapter for open orders and positions.
  * `StateReconciliationEngine` checks for mismatches between the local OMS state and the exchange remote state.
  * Any unacknowledged or orphaned orders are cancelled or synchronized before strategy execution begins.

---

## 8. Monitoring & Observability

The platform provides structured JSON output and telemetry:
* **Funnel Statistics**: Counts for unclosed candles, closed candles, strategy evaluations, signals, risk checks, orders, fills, and slippage.
* **Health Check**: Run `python3 -m crypto_platform.cli health` as an automated liveness probe in Kubernetes or Docker.
* **Audit Trail**: Every risk check, order status update, fill, and reconciliation event is recorded in the audit log.
