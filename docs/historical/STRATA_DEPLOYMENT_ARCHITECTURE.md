# STRATA — Production Deployment & Operations Architecture

## 1. Overview
STRATA is architected for 24/7/365 continuous deployment across containerized Linux environments (Docker / Kubernetes / Systemd) with zero-downtime health monitoring and automated recovery.

---

## 2. Containerized Deployment Topology (`docker-compose.yml`)

```text
                                [ INTERNET ]
                                      │
                                      ▼
                             [ REVERSE PROXY ]
                           (Nginx / Caddy TLS)
                                      │
                 ┌────────────────────┴────────────────────┐
                 │                                         │
                 ▼                                         ▼
         [ WEB API SERVICE ]                      [ WS TELEMETRY ]
        (FastAPI / aiohttp)                    (Live Order & Tickers)
                 │                                         │
                 └────────────────────┬────────────────────┘
                                      │
                                      ▼
                        [ AUTONOMOUS SUPERVISOR ]
                           (STRATA Trading Core)
                                      │
                 ┌────────────────────┼────────────────────┐
                 │                    │                    │
                 ▼                    ▼                    ▼
          [ POSTGRESQL ]           [ REDIS ]         [ LOCAL WAL ]
         (User & Audit)        (PubSub / Cache)     (SQLite State)
```

---

## 3. Production Service Components

### 3.1 Web & API Gateway (`web/server.py`)
- Handles HTTP requests for marketing pages, trading terminal, authentication, and REST APIs.
- Serves static assets for the web application and mobile client wrappers.
- Runs behind Nginx/Caddy with HTTP/2 and WebSocket upgrade support.

### 3.2 Trading Core Supervisor (`execution/agent/strata_autonomous_agent.py`)
- Independent background daemon running the 24/7 observation, state evaluation, and risk governance loop.
- Decoupled from HTTP serving threads to guarantee trading decisions are never blocked by heavy UI queries.

### 3.3 High-Availability Watchdog (`core/watchdog.py`)
- Monitors process heartbeats, memory usage, open WebSocket connections, and data freshness.
- Issues automated restart triggers if feed staleness exceeds tolerance (60 seconds).

---

## 4. Disaster Recovery & Auto-Reconciliation
1. **Cold-Start Sequence**:
   - Step 1: Verify `KingEngineProtectionGuard` contract hash and invariant limits.
   - Step 2: Load local SQLite WAL checkpoints for open position state.
   - Step 3: Query connected broker APIs to reconcile exchange positions against local ledger.
   - Step 4: Cancel dangling / unacknowledged orders.
   - Step 5: Resume market data polling in `SHADOW` / `PAPER` mode.
2. **Fail-Closed Principle**:
   - Any unresolvable ledger mismatch or network partition immediately sets engine state to `PAUSED` and emits emergency alerts.
   - Real capital remains locked at $\$0.00$.
