# Crypto Platform — Target System Architecture

## 1. Architectural Philosophy & Guarantees

The target architecture for the **Crypto Platform** establishes a unified, modular monolith with one shared backend, one canonical API contract, one persistent data store, one protected quantitative core, and two specialized client interfaces:
1. **Desktop Web Workstation:** Optimized for deep analytical research, complex strategy configuration, backtest exploration, and detailed operational blotters.
2. **Native Android Application:** Optimized for mobile monitoring, push telemetry, market watchlists, quick strategy inspection, and emergency operational controls.

```mermaid
graph TD
    subgraph Client Presentation Tier
        WEB["Desktop Web Workstation<br/>(web/static/app_terminal.html)"]
        AND["Native Android Mobile App<br/>(Jetpack Compose Material 3)"]
    end

    subgraph API Gateway & Authentication Boundary
        GW["Canonical REST API & WebSocket Gateway<br/>(aiohttp / port 8080)"]
        AUTH["Auth & Multi-Tenant Session Service<br/>(PBKDF2-HMAC-SHA256)"]
        RATELIM["Sliding-Window Rate Limiter & Security Headers"]
    end

    subgraph Core Domain Services (Protected Modular Monolith)
        SUPER["Autonomous Trading Supervisor<br/>(Persistent Asyncio Loop)"]
        MKT["Market Data Ingestion & 7-TF Candle Engine<br/>(1M, 1W, 1D, 4H, 1H, 15M, 3M)"]
        DEC["Phase R Decision Engine<br/>(Frozen Q.2 Contract: 8fbc923a...)"]
        RISK["Risk Governor & Circuit Breakers<br/>(Floor >=4R, Risk <=1%, Heat <=3%)"]
        EXEC["Paper Execution Simulator<br/>(Causal Next-Bar-Open, Adverse Intrabar)"]
        LAB["Strategy Lab & Research Pipeline<br/>(Historical Replay: 9,608 Invariant)"]
    end

    subgraph Canonical Persistent Storage
        DB[("Unified SQLite Database<br/>(WAL Mode / data/crypto_platform.db)")]
        CHECKPOINT[("Atomic Checkpoints & State Envelopes<br/>(data/checkpoints/)")]
        LEDGER[("Append-Only Decision Ledger<br/>(data/logs/)")]
        CACHE[("Historical Market Cache<br/>(market_data/cache/)")]
    end

    WEB -->|HTTPS / WSS| GW
    AND -->|HTTPS / WSS| GW
    GW --> RATELIM
    RATELIM --> AUTH
    AUTH --> SUPER
    SUPER --> MKT
    SUPER --> DEC
    SUPER --> RISK
    SUPER --> EXEC
    SUPER --> LAB
    
    AUTH --> DB
    SUPER --> DB
    SUPER --> CHECKPOINT
    DEC --> LEDGER
    MKT --> CACHE
```

---

## 2. Component Boundaries & Responsibilities

### Tier 1: Client Interfaces (Two Interfaces to One Platform)
- **Web Application (`web/static/`):** Served via Vercel Edge CDN or backend static route. Pure vanilla HTML5/CSS/JavaScript communicating over authenticated REST and WebSockets. Owns zero trading mathematics or risk calculations.
- **Native Android Application (`mobile/android/`):** Kotlin/Compose app targeting Android 8.0+ (API 26..34). Communicates with backend using `CryptoApiClient`. Stores session tokens and tenant configurations in hardware-backed `SecureStorage`. Client-side rules provide UI safety checks, but server-side boundaries remain authoritative.

### Tier 2: Shared API Gateway & Security Boundary
- **`web/server.py`:** Authoritative REST API exposing versioned endpoints (`/api/*`), load-balancer health probes (`/health`, `/ready`, `/version`), and real-time WebSockets.
- **`web/security_middleware.py`:** OWASP security headers (DENY, nosniff), preflight CORS options, and client IP rate limiting.
- **`core/auth/`:** User registration, password verification, tenant isolation, and session issuance.

### Tier 3: Shared Domain Services (The Protected Core)
- **`execution/autonomous_supervisor.py`:** The heart of the platform. Runs an uninterrupted event loop coordinating data ingestion, candle engines, decision evaluations, order intents, simulated fills, and state reconciliation.
- **`market_model/`:** Canonical multi-timeframe market state generator implementing the 7-timeframe ladder (1M down to 3M) across 5 overlapping sets.
- **`strategy/`:** Registry of 11 canonical strategy families with strict target floor ($\ge 4.0\text{R}$) and risk governance.
- **`execution/safety/safety_gate.py`:** Absolute boundary enforcing `$0.00` real capital and `HARD_DISABLED_FAIL_CLOSED` live trading.

### Tier 4: Canonical Persistent Data Tier
- **Relational Storage (`data/crypto_platform.db`):** Authoritative SQLite database operating in Write-Ahead Logging (WAL) mode. Stores users, password hashes, salt, sessions, preferences, registered accounts, and strategy metadata.
- **State Checkpoints (`data/checkpoints/`):** Atomic JSON checkpoint with SHA-256 envelope for zero-loss restart recovery of simulated equity and open positions.
- **Append-Only Decision Ledger (`data/logs/`):** Cryptographically verifiable chronological record of every `TRADE` and `NO_TRADE` decision with causal attribution.

---

## 3. Dependency Direction & Invariants

1. **Unidirectional Dependency:**
   - Presentation Tier $\to$ API Gateway $\to$ Domain Services $\to$ Storage Layer.
   - Domain services never import presentation components (no web or Android references in `execution/` or `research/`).
2. **Zero Quantitative Duplication:**
   - Neither the web app nor the Android app implements candle formation, fractal calculations, confidence scoring, or position sizing. All quantitative results originate from the shared backend.
3. **Fail-Closed Safety Invariant:**
   - If an unexpected payload, unverified user, or unrecognized order is encountered, the platform defaults to `REJECT` and emits an operational alert.
   - Real capital remains permanently `$0.00`.

---

## 4. Deployment Topology & Failure Boundaries

```
                 Internet Ingress
                        │
         ┌──────────────┴──────────────┐
         ▼                             ▼
   [ Vercel Edge CDN ]         [ Cloud Container Service ]
   - Static Web Terminal       - Python 3.12 Backend API
   - Global Asset Delivery     - Persistent Supervisor Loop
   - Reverse Proxy (/api/*)    - Market Data WSS Connection
                               - Local Persistent Volume (/app/data)
                                       │
                               ┌───────┴───────┐
                               ▼               ▼
                        SQLite Database   Decision Logs
                        (crypto_platform) (JSONL / Checks)
```

### Failure Isolation:
- **Client Offline:** If Android or Web disconnects, the persistent backend supervisor continues streaming candles, executing paper trailing stops, and recording decisions without interruption.
- **Backend Reboot:** On startup, `StatePersistenceManager` loads the last SHA-256 validated checkpoint, restores simulated equity and positions, reconciles against broker state, and continues cleanly.
- **Network Outage to Exchange:** Binance WebSocket client automatically reconnects with exponential backoff; watchdog trips circuit breaker to prevent out-of-sync executions.
