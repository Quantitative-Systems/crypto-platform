# Crypto Platform — Release Notes

## Version 2.4.0 — Release Preparation & Cloud Staging Readiness

### Overview
Version 2.4.0 consolidates the entire repository into a professional, release-ready quantitative platform. It introduces full local end-to-end verification across the authoritative Python backend, institutional Web Workstation, and native Android application, while establishing strict cloud deployment and persistence safety boundaries.

---

### Key Capabilities & Enhancements

#### 1. Core Platform & Invariants
- **Frozen Contract Guard**: SHA-256 seal `8fbc923a104e7688c3a9f0e4b8592c30dfb0b9a67a84511d5e49f8721c432098` 100% verified.
- **Fail-Closed Safety Barrier**: Real capital permanently held at `$0.00`; live exchange execution hard-locked and disabled.
- **Continuous 7-Timeframe Ladder**: Real-time candle engine spanning `1M → 1W → 1D → 4H → 1H → 15M → 3M`.
- **5 Overlapping Timeframe Sets**: Authoritative 5-set ladder parity across backend, REST APIs, Web, and Android (`SET_1` to `SET_5`).
- **Telemetry Upgrades**: Standardized production metrics (`uptime_seconds`, `memory_mb`, `event_loop_lag_ms`, `open_positions`, `closed_positions`, `orders_count`, `decisions_count`, `real_capital_authorized_usd`).

#### 2. Institutional Web Workstation
- **Dynamic Endpoint Integration**: `getApiBase()` / `apiFetch()` dynamically routes all 21 REST endpoints and `/ws/market-state` WebSocket connections.
- **Endpoint Configurator**: Interactive "Authoritative Backend Endpoint" UI in the Settings tab for targeting local, staging, or custom host instances.
- **Financial Terminal Aesthetic**: Institutional light-theme workstation with real-time status pills, active order blotters, and 5-set ladder inspectors.

#### 3. Native Android Application (Kotlin / Jetpack Compose)
- **Shared API Parity**: Consumes authoritative market state, five-set ladders, backtest results, and risk limits.
- **Build Variants**:
  - `debug`: Loopback development (`http://10.0.2.2:8080`).
  - `staging`: Configured for cloud staging (`https://crypto-platform-staging.onrender.com`).
  - `release`: Production configuration with Proguard/R8 minification enabled.
- **Runtime Endpoint Override**: Users can override the backend URL at runtime via the Account/Settings screen.
- **Built Artifacts**: Verified `app-debug.apk` (17.58 MB) and `app-staging.apk` (16.87 MB).

#### 4. Storage & Persistence Safety
- **SQLite WAL & Migrations**: Schema v4 with 4 atomic migrations and idempotent retry guarantees.
- **Dual Checkpoints**: Dual-file JSON snapshots in `data/checkpoints` and `research/results`.
- **Idempotency Guard**: Orders across process restarts are validated against historical transaction hashes to eliminate duplicate execution.

---

### Verification Summary
- **Python Regression Suite:** 300 / 300 tests passed.
- **Production Server Verification:** 100% passed (`test_production_server_api_websocket_and_restart_persistence`).
- **Persistence & Recovery Suite:** 23 / 23 passed.
- **Android Unit Tests:** `BUILD SUCCESSFUL` (0 errors across `CapitalSafetyTest` and `FiveSetArchitectureTest`).
- **Platform Health CLI:** 9 / 9 checks passed (`python cli.py health`).

---

### Known Limitations & Deployment Realities
1. **Cloud Persistence Constraint:** Free-tier cloud providers (Render) use ephemeral filesystems. 24/7 continuous worker state requires an external managed database or a paid persistent disk plan.
2. **Idle Sleep / Cold Starts:** Free Render web services spin down after 15 minutes of inactivity with ~30-60 second wake-up times. Active WebSocket connections keep the instance awake.
3. **Live Trading Guard:** Live exchange order submission remains disabled by design until multi-signature hardware authorization and regulatory licensing are established.
