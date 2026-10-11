# Crypto Platform

## Autonomous Systematic Digital Asset Trading, Research & Operations Platform

> **An institutional-grade quantitative trading platform featuring a scale-invariant causal Market Model, frozen research contract verification, fail-closed capital safety gates, authoritative REST & WebSocket services, an institutional Web Workstation, and a native Android application.**

[![Platform Health](https://img.shields.io/badge/platform%20health-9%2F9%20checks%20passed-brightgreen)](#quick-start--local-operations)
[![Python Tests](https://img.shields.io/badge/python%20tests-300%2F300%20passed%20(100%25)-brightgreen)](#testing--verification)
[![Android Tests](https://img.shields.io/badge/android%20tests-passing-brightgreen)](#android-native-application)
[![Frozen Contract](https://img.shields.io/badge/contract%20hash-8fbc923a...%20(VERIFIED)-blue)](#frozen-research-contract--alpha-core)
[![Live Capital](https://img.shields.io/badge/live%20capital-%240.00%20(FAIL--CLOSED)-red)](#capital-safety--risk-governance)
[![License](https://img.shields.io/badge/license-MIT-blue)](LICENSE)

---

## Table of Contents
1. [Overview & Problem Solved](#overview--problem-solved)
2. [Unified Product Architecture](#unified-product-architecture)
3. [The 7-Timeframe Ladder & 5 Overlapping Sets](#the-7-timeframe-ladder--5-overlapping-sets)
4. [Frozen Research Contract & Alpha Core](#frozen-research-contract--alpha-core)
5. [Client Workstations (Web & Android)](#client-workstations-web--android)
6. [Storage, Persistence & Crash Recovery](#storage-persistence--crash-recovery)
7. [Capital Safety & Risk Governance](#capital-safety--risk-governance)
8. [Quick Start & Local Operations](#quick-start--local-operations)
9. [Testing & Verification](#testing--verification)
10. [Android Native Application](#android-native-application)
11. [Deployment & Hosting Status](#deployment--hosting-status)
12. [Security Architecture & Secret Handling](#security-architecture--secret-handling)
13. [Documentation Index](#documentation-index)
14. [License & Disclaimer](#license--disclaimer)

---

## Overview & Problem Solved

Traditional retail and quantitative crypto tools suffer from three fundamental deficiencies:
1. **Disconnected Execution Models:** Research notebooks diverge from live execution bots, creating massive implementation shortfall and unmodeled friction.
2. **Single-Timeframe Curve-Fitting:** Strategies optimized on arbitrary candlestick intervals fail to account for higher-timeframe macroeconomic bias and lower-timeframe execution friction.
3. **Fragile Client Telemetry:** User interfaces rely on fabricated mock metrics or unauthenticated, unrecoverable states without dual-client parity.

**Crypto Platform solves these problems** by delivering **ONE single, authoritative Python backend** coupled to **two synchronized client workstations**:
- **Authoritative Single Source of Truth:** Business logic, market state generation, risk calculations, and decision ledgers reside exclusively in the backend.
- **Scale-Invariant Multi-Timeframe Spine:** Unidirectional causal transmission ladder ($1\text{M} \rightarrow 1\text{W} \rightarrow 1\text{D} \rightarrow 4\text{H} \rightarrow 1\text{H} \rightarrow 15\text{M} \rightarrow 3\text{M}$) organized into 5 overlapping sets.
- **Fail-Closed Hardware/Software Capital Guard:** Real capital is held at **$0.00**; live execution is disabled fail-closed.
- **Verified Dual-Client Parity:** Both the Web Workstation and native Android client connect to the identical REST API and streaming WebSocket contract.

---

## Unified Product Architecture

```mermaid
graph TD
    subgraph DataPipeline [Market Data Pipeline]
        BinanceWS[Binance Public WS / REST] --> MarketService[MarketService]
        Cache[Historical Parquet/JSON Cache] --> MarketService
        MarketService --> CandleEngine[7-Timeframe Candle Engine<br/>1M → 1W → 1D → 4H → 1H → 15M → 3M]
    end

    subgraph CoreEngine [Authoritative Backend Engine]
        CandleEngine --> Supervisor[AutonomousTradingSupervisor]
        Supervisor --> FiveSet[5 Overlapping Timeframe Sets<br/>Set 1 to Set 5]
        FiveSet --> DecisionEngine[Phase R Decision Engine<br/>Frozen Hash: 8fbc923a...]
        DecisionEngine --> RiskGov[Portfolio Risk Governor<br/>Min Floor >= 4.0R | Max Risk <= 1.0%]
        RiskGov --> SafetyGate[Fail-Closed Safety Gate<br/>Real Capital: $0.00 | Live: Disabled]
    end

    subgraph Persistence [Durable Storage]
        Supervisor <--> SQLiteWAL[SQLite WAL Database<br/>crypto_platform.db]
        Supervisor <--> Checkpoints[Dual JSON Checkpoints<br/>research/results]
    end

    subgraph ServerLayer [Institutional Server Layer]
        Supervisor --> WebServer[PhaseRWebServer<br/>Aiohttp Async Server]
        WebServer --> RateLimiter[Security Middleware<br/>Rate Limiting & Headers]
    end

    subgraph ClientLayer [Client Workstations]
        RateLimiter --> RestApi[REST API<br/>/api/health, /api/markets, etc.]
        RateLimiter --> WsStream[WebSocket Streaming<br/>/ws/market-state]
        RestApi --> WebUI[Web Workstation<br/>app_terminal.html]
        WsStream --> WebUI
        RestApi --> AndroidApp[Native Android App<br/>Kotlin / Jetpack Compose]
        WsStream --> AndroidApp
    end
```

---

## The 7-Timeframe Ladder & 5 Overlapping Sets

The platform enforces absolute separation between the **Canonical Market Model** (how price moves) and contextual setup filters:

```text
CANONICAL MARKET MODEL
├── HOW   = Market Structure & Trend (Swings, CHOCH/MSS, BOS)
├── WHERE = Key Zones & Levels (Order Blocks, FVGs, Liquidity Pools, Discount > 61.8%)
└── WHAT  = Phase State (PULLBACK vs. CONTINUATION)
```

Price action flows across a continuous 7-timeframe ladder:
$$\text{1M} \longrightarrow \text{1W} \longrightarrow \text{1D} \longrightarrow \text{4H} \longrightarrow \text{1H} \longrightarrow \text{15M} \longrightarrow \text{3M}$$

To eliminate single-timeframe myopia, timeframes are evaluated across **5 Overlapping Sets**:

| Set Name | Timeframes | Horizon | Role |
| :--- | :--- | :--- | :--- |
| **SET 1** | `1M → 1W → 1D` | Macro Context | Long-term macro regime and multi-month structural trend. |
| **SET 2** | `1W → 1D → 4H` | Structural Foundation | Swing trend formation and multi-week institutional zones. |
| **SET 3** | `1D → 4H → 1H` | Intermediate Trend | Day-to-swing bias and intraday continuation alignment. |
| **SET 4** | `4H → 1H → 15M` | Operational Swing | Session-level structure and tactical entry geometry. |
| **SET 5** | `1H → 15M → 3M` | Tactical Execution | Microstructure confirmation and execution trigger. |

---

## Frozen Research Contract & Alpha Core

The core strategy and research model is permanently sealed under SHA-256 hash:
```
8fbc923a104e7688c3a9f0e4b8592c30dfb0b9a67a84511d5e49f8721c432098
```

Enforced at startup and runtime by [`FrozenContractGuard`](file:///c:/Users/nares/Workspace/crypto-platform/research/contracts/frozen_contract_guard.py):
- **Capital Boundary:** Real capital permanently locked at `$0.00`.
- **Live Trading Adapter:** Permanently disabled and fail-closed (`LIVE_TRADING_ENABLED = false`).
- **Target Geometry:** Minimum destination target floor $\ge 4.0\text{R}$.
- **Risk Per Trade:** Capped at $\le 1.0\%$ of equity.
- **Portfolio Heat:** Capped at $\le 3.0\%$ aggregate exposure.
- **Base Asset Exposure:** Capped at $\le 1.0\%$ cumulative per asset.

Verify contract integrity at any time:
```bash
python cli.py verify-contract
```

---

## Client Workstations (Web & Android)

### 1. Institutional Web Workstation
Located in [`web/static/app_terminal.html`](file:///c:/Users/nares/Workspace/crypto-platform/web/static/app_terminal.html):
- **Master Cockpit (`/dashboard`):** Real-time equity curves, capital safety status pills, and system telemetry.
- **Markets & Feeds (`/markets`):** Multi-instrument universe monitoring across `BTCUSDT`, `ETHUSDT`, `SOLUSDT`, and `BNBUSDT`.
- **7-Timeframe Matrix (`/fractal-state`):** Interactive visualizer of market structure, key zones, and phase states.
- **5-Set Ladder Inspector:** Deep inspection of overlapping sets (`SET_1` through `SET_5`).
- **Configurable Backend Endpoint:** Built-in settings modal allowing dynamic runtime reconfiguration of REST and WebSocket endpoints (`getApiBase()`).

### 2. Native Android Application
Located in [`mobile/android`](file:///c:/Users/nares/Workspace/crypto-platform/mobile/android):
- Native Android UI built with **Kotlin 1.9** and **Jetpack Compose (Material 3)**.
- High-density financial information architecture with real-time WebSocket connection lifecycle handling.
- Dynamic backend endpoint override in the Account/Settings screen.
- Pre-compiled artifacts: `app-debug.apk` (17.58 MB) and `app-staging.apk` (16.87 MB).

---

## Storage, Persistence & Crash Recovery

- **SQLite Database (`data/db/crypto_platform.db`):**
  - Configured with `PRAGMA journal_mode=WAL` for concurrent, non-blocking reads.
  - 4 automated migrations (`v1` to `v4`) with atomic transactions.
  - Stores user sessions, broker configurations, paper accounts, orders, and execution ledgers.
- **Dual Checkpoints:**
  - Written atomically to `data/checkpoints/` and `research/results/`.
  - Validated by `RecoveryWatchdog` on boot to detect file corruption and replay state.
  - Idempotency keys (`idempotency_key`) ensure that duplicate candle delivery or unexpected process restarts never create duplicate orders or state corruption.

---

## Capital Safety & Risk Governance

```text
PORTFOLIO RISK CONSTRAINTS:
├── Single Trade Risk:        ≤ 1.0% Account Equity
├── Cumulative Asset Risk:    ≤ 1.0% Base Asset Exposure
├── Total Portfolio Heat:     ≤ 3.0% Concurrently
├── Target Destination Floor: ≥ 4.0R Minimum Planned R:R
└── Capital Authorization:    $0.00 (Hard Fail-Closed)
```

---

## Quick Start & Local Operations

### Prerequisites
- Python 3.11 or 3.12
- Git
- JDK 17+ and Android SDK (for mobile builds)

### 1. Installation
```bash
# Clone the repository
git clone https://github.com/Quantitative-Systems/crypto-platform.git
cd crypto-platform

# Create virtual environment
python -m venv .venv
# On Windows:
.venv\Scripts\activate
# On Linux/macOS:
# source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Environment Configuration
Copy the configuration template:
```bash
cp .env.example .env
```
Key configuration parameters in `.env`:
```ini
PLATFORM_ENV=PAPER
PLATFORM_LIVE_CAPITAL_USD=0.0
WEB_SERVER_HOST=0.0.0.0
WEB_SERVER_PORT=8080
STATE_PERSISTENCE_BACKEND=SQLITE_WAL
```

### 3. Verify Health & Contracts
```bash
# Verify frozen research contract integrity
python cli.py verify-contract

# Run complete platform health check (9/9 checks)
python cli.py health
```

### 4. Launch Autonomous Engine & Web Terminal
```bash
python main.py --host 0.0.0.0 --port 8080 --mode PAPER
```
Access the Web Terminal in your browser at:
`http://localhost:8080/dashboard`

---

## Testing & Verification

The repository maintains rigorous automated test suites across all domains:

```bash
# 1. Run full Python test suite (300 tests)
pytest -q

# 2. Run production server, REST API, WebSocket & restart persistence verification
pytest tests/integration/test_production_container_verification.py -v

# 3. Run durable persistence, SQLite WAL & restart recovery audit
pytest tests/unit/core/test_restart_recovery_audit.py tests/unit/core/test_durable_persistence.py -v

# 4. Run 5-set architecture parity test
pytest tests/unit/test_five_set_architecture_parity.py -v
```

---

## Android Native Application

### Build & Test via Gradle Wrapper
```bash
cd mobile/android

# Run Android unit tests
.\gradlew.bat testDebugUnitTest

# Assemble Debug APK (for local emulator development)
.\gradlew.bat assembleDebug

# Assemble Staging APK (targeting cloud staging)
.\gradlew.bat assembleStaging
```

Output APK artifacts:
- Debug: `mobile/android/app/build/outputs/apk/debug/app-debug.apk`
- Staging: `mobile/android/app/build/outputs/apk/staging/app-staging.apk`

---

## Deployment & Hosting Status

### Reality & Status Classification
| Layer | Status | Description |
| :--- | :--- | :--- |
| **Local Verification** | **VERIFIED (100%)** | All 300 Python tests, server boot, APIs, WebSockets, and Android builds passed. |
| **Source Code** | **STAGED / RELEASE-READY** | Consolidated repository structure and security-audited codebase. |
| **Public Staging** | **CONFIGURED (RENDER)** | `render.yaml` and `Dockerfile` configured; targeting `crypto-platform-staging.onrender.com`. |
| **Continuous Worker** | **LOCAL / VPS ONLY** | Free-tier cloud disks are ephemeral; 24/7 continuous persistence requires VPS or managed DB. |

### Docker Deployment
```bash
docker compose up -d
```
Container health probe: `python3 cli.py health || exit 1`.

---

## Security Architecture & Secret Handling

1. **Zero Committed Secrets:** Repository is audited; no private keys, passwords, or live credentials exist in Git.
2. **Scrubbing & Sanitization:** Alert routers and logging middleware scrub all credential patterns before dispatching logs or webhooks.
3. **Fail-Closed Boundary:** `StartupValidator` validates 5 pre-flight gates on boot and terminates immediately if live execution is requested without cryptographic keys.

---

## Documentation Index

Comprehensive engineering and operational documentation is organized in [`docs/`](docs/):

- **Architecture:**
  - [System Architecture Specification](docs/architecture/SYSTEM_ARCHITECTURE.md)
  - [Target Platform Architecture](docs/architecture/CRYPTO_PLATFORM_TARGET_ARCHITECTURE.md)
  - [Data Pipeline Architecture](docs/architecture/CRYPTO_PLATFORM_DATA_ARCHITECTURE.md)
  - [Worker Architecture](docs/architecture/CRYPTO_PLATFORM_WORKER_ARCHITECTURE.md)
  - [Mobile Architecture](docs/architecture/CRYPTO_PLATFORM_ANDROID_ARCHITECTURE.md)
  - [Security Architecture](docs/architecture/CRYPTO_PLATFORM_SECURITY_ARCHITECTURE.md)
- **API & Contracts:**
  - [REST & WebSocket API Reference](docs/api/API_REFERENCE.md)
  - [OpenAPI Specification](docs/api/openapi.yaml)
- **Operations & Runbooks:**
  - [Deployment Guide](docs/operations/DEPLOYMENT_GUIDE.md)
  - [Disaster Recovery SOP](docs/operations/DISASTER_RECOVERY.md)
  - [Rollback Guide](docs/operations/ROLLBACK_GUIDE.md)
  - [CI/CD Runbook](docs/operations/CI_CD_RUNBOOK.md)
  - [Android Release Runbook](docs/operations/ANDROID_RELEASE_RUNBOOK.md)
  - [Cloud Cost & Limits](docs/operations/CLOUD_COST_AND_LIMITS.md)
- **Research & Evidence:**
  - [Research Methodology](docs/research/RESEARCH_METHODOLOGY.md)
  - [Phase O Charter & Profitability Audit](docs/research/PHASE_O_OPERATIONAL_CHARTER_AND_PROFITABILITY_AUDIT.md)
- **Releases:**
  - [Release Notes (v2.4.0)](docs/releases/RELEASE_NOTES.md)
  - [Production Hardening Changelog](docs/releases/PRODUCTION_HARDENING_CHANGELOG.md)

---

## License & Disclaimer

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

**DISCLAIMER:** This software is engineered strictly for quantitative research, backtesting, and forward paper validation. It does not constitute financial, investment, or trading advice. Past performance, backtest simulations, and paper trading results do not guarantee future live performance. Cryptocurrency trading involves substantial risk of capital loss. Live real-money trading is permanently locked at **$0.00 capital**.
