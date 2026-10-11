# Crypto Platform — Cloud Deployment Forensic Audit

**Audit Date:** 2026-10-08T21:15:00+05:30  
**Repository:** `C:\Users\nares\Workspace\crypto-platform`  
**Engineer:** Autonomous Cloud & Release Engineer  
**Frozen Research Hash:** `8fbc923a104e7688c3a9f0e4b8592c30dfb0b9a67a84511d5e49f8721c432098`  

---

## 1. Executive Forensic Architecture Overview

The **Crypto Platform** codebase is a high-performance quantitative trading, research, and execution platform comprising:
1. A **Python 3.12 quantitative core** (`Phase Q.2`, `Phase R`, `FractalStateEngine`, 7-timeframe candle engine).
2. An **aiohttp async REST & WebSocket backend service** (`web/server.py`, `main.py`, `cli.py`).
3. A **native Android client application** (`mobile/android/`) built with Kotlin and Jetpack Compose (Material 3).
4. Containerization and deployment definitions in `deploy/` (`Dockerfile`, `docker-compose.yml`, `Caddyfile`, `nginx.conf`).

---

## 2. Component Forensic Classification

Every component in the repository is classified into the architectural categories below:

| Component / Subsystem | Path / Entrypoint | Category | Classification Rationale |
| :--- | :--- | :--- | :--- |
| **Public Website & Static Terminal** | `web/static/public_website.html`, `web/static/app_terminal.html` | **A** | **Vercel-compatible**: Pure static HTML/CSS/JS frontend with modern client-side rendering. Can be deployed to Vercel CDN or any static edge host. |
| **REST & WebSocket API Server** | `web/server.py`, `web/security_middleware.py` | **B** | **Persistent cloud service required**: Async `aiohttp` server maintaining live memory state, rate limiting, and persistent WebSocket subscribers. Incompatible with serverless stateless function timeouts. |
| **Autonomous Supervisor & Live Feed** | `main.py`, `execution/autonomous_supervisor.py`, `market_data/binance_fetcher.py` | **C** | **Background worker required**: 24/7 market data WebSocket ingestion, closed-candle aggregation across 7 timeframes, and automated Phase R signal evaluation. |
| **Decision Ledger & Storage** | `accounts/account_manager.py`, `execution/decision_ledger.py`, `market_data/cache/` | **D** | **Database required**: SQLite database and immutable append-only JSONL decision journals. Requires persistent filesystem volume in cloud staging. |
| **Local Development Harnesses** | `examples/`, `scratch/`, Windows PowerShell helper scripts | **E** | **Local development only**: One-off verification scripts, developer exploratory runs, and local mock testing. |
| **Android Native Mobile Client** | `mobile/android/` (`io.cryptoplatform.app`) | **F** | **Android-only**: Native Jetpack Compose mobile app, Gradle build configuration, and Android resources. Consumes the Cloud Staging API. |
| **GitHub CI/CD Automation** | `.github/workflows/` | **G** | **CI-only**: Headless automated verification pipelines for Python regressions, contract verification, and Android APK compilation. |

---

## 3. Deployment Constraints & Invariants

1. **Vercel Integration Boundary:**
   - Vercel is well-suited for static assets (`web/static/`) or edge documentation.
   - Vercel **CANNOT** host the Python trading engine due to serverless execution limits (10-60 second execution cap, lack of persistent in-memory state, and inability to maintain permanent background WebSocket connections to crypto exchanges).
   - Therefore, the persistent backend API and background supervisor must run in a containerized environment (e.g. Render, Railway, Fly.io, or AWS ECS/GCP Cloud Run with CPU always-allocated), while Vercel or native hosting handles static frontend distribution.

2. **Zero Real Capital Invariant:**
   - Cloud staging environment variables must enforce:
     ```
     PLATFORM_ENV=STAGING
     PLATFORM_LIVE_CAPITAL_USD=0.0
     LIVE_ORDERS_ENABLED=false
     ```
   - No production exchange API keys or private keys are permitted in cloud environment variables or container configurations.

3. **Android Client Cloud Consumption:**
   - Android client communicates with the staging backend via standard HTTPS REST endpoints (`/api/markets`, `/api/strategies`, `/api/backtests`, `/api/risk`, `/api/health`).
   - Dynamic environment endpoint configuration (`DEBUG`, `STAGING`, `RELEASE`) ensures seamless connectivity without hardcoded `localhost` limitations.
