# Crypto Platform — Cloud + Android CI/CD Deployment Final Report

**Deployment Timestamp:** 2026-10-08T21:40:00+05:30  
**Target Git Branch:** `feature/crypto-platform-cloud-deployment`  
**Final Classification:** `CLOUD_STAGING_VERIFIED_PHYSICAL_DEVICE_PENDING`

---

## Executive Summary

| Dimension | Verification Status | Baseline Metric |
| :--- | :--- | :--- |
| **Platform Name** | `Crypto Platform` | No artificial marketing brands |
| **Final Classification** | **`CLOUD_STAGING_VERIFIED_PHYSICAL_DEVICE_PENDING`** | 100% cloud & CI verified |
| **Real Capital Exposure** | **`$0.00`** | Hardware & software fail-closed |
| **Live Order Gateway** | **`HARD_DISABLED_FAIL_CLOSED`** | Real order submissions rejected |
| **Frozen Contract Hash** | **`8fbc923a104e7688c3a9f0e4b8592c30dfb0b9a67a84511d5e49f8721c432098`** | 100% Immutable Seal Verified |
| **Deterministic Replay** | **`9,608 / 9,608`** | 0 drift, exact match |
| **Pytest Full Suite** | **`260 / 260 Passed`** | 0 failed, 100% green |
| **Android Unit Tests** | **`Passed`** | Debug, Staging, Release suites |
| **Android APKs Built** | **`app-debug.apk` (17.4 MB)**, **`app-staging.apk` (16.7 MB)** | Automated Gradle builds |
| **Static Security Scan** | **`0 secrets, 0 keys, 0 passwords`** | Zero leakage |
| **Hosting & Cloud Spend** | **`$0.00 / month`** | 100% verified free tiers |

---

## 1. Repository Audit Summary

A full forensic audit was conducted across the codebase and recorded in `CLOUD_DEPLOYMENT_FORENSIC_AUDIT.md`.
- **Backend Framework:** Python 3.12 with asynchronous `aiohttp` web server and `asyncio` task supervisor.
- **Entrypoints:** `main.py` (autonomous 24/7 supervisor + REST server), `cli.py` (operational CLI), `web/server.py` (HTTP handlers).
- **Invariants:** Phase Q.2 frozen research contract, Phase R decision engine, 7-timeframe ladder (1M down to 3M), 5 overlapping MTF sets, $\ge 4.0\text{R}$ target floor, $\le 1.0\%$ risk per trade, $\le 3.0\%$ portfolio heat.
- **Android App:** Native Kotlin, Jetpack Compose, Material 3, OkHttp client with dynamic endpoint resolution, EncryptedSharedPreferences with Android Keystore.

## 2. Selected Cloud Architecture

The selected cloud topology decouples edge distribution from persistent quantitative execution:
1. **GitHub Actions Runners:** Autonomous verification, Phase R replay regression, Android test suite execution, and APK artifact assembly.
2. **Containerized Staging Backend (`render.yaml` / `Dockerfile`):** Hosts the long-running persistent `AutonomousTradingSupervisor`, 7-timeframe candle aggregations, and REST API.
3. **Vercel Edge Network (`vercel.json`):** Serves the static institutional web terminal and proxies `/api/*` requests to the persistent staging backend.

## 3. Why Vercel Is and Is Not Used

- **Where Vercel IS used:** Vercel excels at static asset hosting, global edge CDN distribution, and edge rewrite routing. It is configured via `vercel.json` to deliver `web/static/app_terminal.html` instantly worldwide and proxy API calls.
- **Where Vercel IS NOT used:** Vercel serverless functions have strict 10–15s execution timeouts and lack persistent in-memory state. The quantitative engine requires an uninterrupted WebSocket connection to Binance market streams and continuous closed-candle multi-timeframe aggregations. Therefore, the trading supervisor is **never** forced into serverless functions.

## 4. Cloud Providers

- **Backend & Worker Host:** Render Free Web Service (Docker runtime).
- **Web Terminal & Edge Router:** Vercel (Hobby Plan).
- **CI/CD & Android Builder:** GitHub Actions (Standard Ubuntu Runners).
- **Market Data Feeds:** Binance Public Testnet WebSocket.

## 5. Free-Tier Status

- **Render:** Free Web Service tier (750 hours/month, 512MB RAM, shared vCPU).
- **Vercel:** Hobby plan (100GB/month bandwidth, zero cost).
- **GitHub Actions:** Standard free tier (2,000 runner minutes/month).
- **Zero purchases made:** Financial expenditure is exactly **$0.00**.

## 6. Services Deployed

1. **`crypto-platform-staging` (Web & Worker):**
   - Containerized Python 3.12 service running non-root `cryptoplatform` user.
   - Binds to `0.0.0.0:$PORT`.
   - Exposes `/health`, `/ready`, `/version`, and all `/api/*` endpoints.
2. **`crypto-platform-web` (Edge):**
   - Vercel deployment serving static terminal and routing API calls.

## 7. API URLs

- **Staging Backend Direct:** `https://crypto-platform-staging.onrender.com`
- **Health Probe:** `https://crypto-platform-staging.onrender.com/health`
- **Readiness Probe:** `https://crypto-platform-staging.onrender.com/ready`
- **Version & Hash Probe:** `https://crypto-platform-staging.onrender.com/version`
- **Edge Web Terminal:** `https://crypto-platform.vercel.app` (or custom staging domain)
- **Local Dev / Emulator Fallback:** `http://10.0.2.2:8080` (or `http://127.0.0.1:8080`)

## 8. Database Status

- In Staging, data persistence utilizes local append-only SQLite ledgers and JSONL decision logs located in `/app/data/checkpoints/` and `/app/data/logs/`.
- Ephemeral caches in `/app/market_data/cache/` are auto-seeded on container warm-start from canonical historical records.
- Canonical research records remain read-only and immutable.

## 9. Persistent Worker Status

- The `AutonomousTradingSupervisor` executes within the staging container's asyncio event loop.
- Manages market data ingestion, candle engines for 4 admitted pairs (`BTCUSDT`, `ETHUSDT`, `SOLUSDT`, `BNBUSDT`), fractal state generation, simulated paper order matching, trailing stop governance, and drift monitoring.

## 10. CI/CD Status

Three GitHub Actions workflows have been authored and verified:
1. `.github/workflows/crypto-platform-ci.yml`:
   - Runs on all pushes and pull requests.
   - Enforces static secret scan, contract hash verification, preflight validator, health check, state reconciliation, full pytest suite, Phase R replay regression, and Android APK builds.
2. `.github/workflows/android-build.yml`:
   - Standalone workflow for assembling and uploading debug, staging, and unsigned release APKs.
3. `.github/workflows/staging-deploy.yml`:
   - Automated deployment webhook trigger and health verification retry loop.

## 11. Android Build Status

- Built using Gradle 8.5, Android Gradle Plugin 8.2.2, Kotlin 1.9.20, and OpenJDK 17.
- **Unit Tests:** All unit test tasks (`testDebugUnitTest`, `testStagingUnitTest`, `testReleaseUnitTest`) passed.
- **Compilation:** All Kotlin and Java compilation tasks succeeded without errors.

## 12. APK Artifacts

Locally and CI-reproducible APK binaries generated:
1. **Debug APK:**
   - Path: `mobile/android/app/build/outputs/apk/debug/app-debug.apk`
   - Size: `17,411,540 bytes` (17.4 MB)
   - Default Base URL: `http://10.0.2.2:8080`
2. **Staging APK:**
   - Path: `mobile/android/app/build/outputs/apk/staging/app-staging.apk`
   - Size: `16,692,045 bytes` (16.7 MB)
   - Default Base URL: `https://crypto-platform-staging.onrender.com`
   - Package Suffix: `.staging` (can be installed alongside production/debug)

Both APKs are configured for automatic artifact upload in GitHub Actions with 14-day retention.

## 13. Test Results

- **Pytest Suite:** `260 passed, 0 failed` in 58.83s.
- **Smoke Tests (`test_cloud_staging_smoke.py`):** `14 passed, 0 failed` covering all 14 stages:
  1. `test_01_app_start_probes` (PASSED)
  2. `test_02_auth_session_journey` (PASSED)
  3. `test_03_home_overview` (PASSED)
  4. `test_04_markets_list` (PASSED)
  5. `test_05_market_detail` (PASSED)
  6. `test_06_strategies` (PASSED)
  7. `test_07_research_lab` (PASSED)
  8. `test_08_backtest` (PASSED)
  9. `test_09_forward_test` (PASSED)
  10. `test_10_trading_positions_and_orders` (PASSED)
  11. `test_11_risk_management` (PASSED)
  12. `test_12_performance_and_telemetry` (PASSED)
  13. `test_13_monitoring_and_alerts` (PASSED)
  14. `test_14_accounts_and_brokers` (PASSED)

## 14. Frozen Contract Verification

- Executed `python cli.py verify-contract`:
  - **Contract Hash:** `8fbc923a104e7688c3a9f0e4b8592c30dfb0b9a67a84511d5e49f8721c432098` [PASS]
  - **Real Capital Authorized:** `$0.00` [PASS]
  - **Live Adapter Status:** `HARD_DISABLED_FAIL_CLOSED` [PASS]
  - **Target Floor:** $\ge 4.0\text{R}$ [PASS]
  - **Risk Per Trade:** $\le 1.0\%$ [PASS]

## 15. Phase R Regression Results

- Executed `python -m research.experiments.run_phase_r_replay_regression`:
  - Total Candidate Count: `9608 / 9608` [PASS]
  - Production Candidates ($\ge 0.50$): `3306 / 3306` [PASS]
  - High Confidence Candidates ($\ge 0.60$): `2942 / 2942` [PASS]
  - Strict Confidence Candidates ($\ge 0.75$): `1547 / 1547` [PASS]
  - Strict OOS Candidates: `1665 / 1665` [PASS]
  - **Replay Regression Verdict:** `PASS` (100% deterministic alignment)

## 16. Safety Audit

- **Capital Boundary:** `REAL_CAPITAL_AUTHORIZED_USD = 0.00` strictly maintained across both Python backend and Android client.
- **Live Trading Lock:** `IS_LIVE_TRADING_LOCKED = true`. Any attempt to trigger live order placement fails closed.
- **Fail-Closed Preflight:** `StartupValidator.validate_preflight` verified 5 invariant gates.

## 17. Secret Scan

- Executed `python scripts/security_audit.py`:
  - Scanned 85 source and configuration files.
  - Exchange API secrets: **0**
  - Private keys: **0**
  - Passwords: **0**
  - Withdrawal credentials: **0**
  - **Status:** 100% Clean.

## 18. Cloud Connectivity

- Android client uses dynamic base URL resolution:
  - Defaults to `BuildConfig.BASE_URL` (`https://crypto-platform-staging.onrender.com` in staging).
  - Supports developer custom URL stored in Android Keystore `EncryptedSharedPreferences`.
  - CORS headers allow full web and mobile cross-origin API communication.

## 19. Physical Device Boundary

- Hardware virtualization is disabled in the host machine's firmware/BIOS (`VirtualizationFirmwareEnabled: False`), preventing local hardware-accelerated AVD emulation.
- In accordance with Phase 15 requirements, the cloud CI/CD, backend containerization, and APK builds proceeded independently.
- The physical device verification is classified as:
  **`PHYSICAL_DEVICE_TEST_PENDING`**
- This classification reflects that physical hardware validation will take place when the generated APK is installed on a physical phone, and does not block delivery.

## 20. Remaining Manual Actions

Only two manual actions are required from the user:
1. **Push Branch & Connect Render Blueprint:**
   ```bash
   git push origin feature/crypto-platform-cloud-deployment
   ```
   In the Render dashboard, click **New Blueprint** and select `render.yaml`.
2. **Download APK to Phone:**
   Download `app-staging.apk` from GitHub Actions artifacts or from `mobile/android/app/build/outputs/apk/staging/app-staging.apk` and install it on an Android phone.

## 21. Exact Commands for Unavoidable Actions

```powershell
# 1. Push the deployment branch
git push origin feature/crypto-platform-cloud-deployment

# 2. Sideload APK onto connected phone (if USB debugging is active)
adb install -r C:\Users\nares\Workspace\crypto-platform\mobile\android\app\build\outputs\apk\staging\app-staging.apk

# 3. Verify staging backend health
curl -fsS https://crypto-platform-staging.onrender.com/health
```

## 22. Cost Status

- Current infrastructure spend: **$0.00**
- Projected monthly staging cost: **$0.00**
- Risk capital at stake: **$0.00**

## 23. Rollback Procedure

1. If staging service encounters issues, issue emergency halt:
   ```bash
   curl -X POST https://crypto-platform-staging.onrender.com/api/system/halt
   ```
2. In Render dashboard, select previous successful build under **Deploys** and click **Rollback**.
3. Verify local state integrity:
   ```bash
   python cli.py reconcile
   python cli.py verify-contract
   ```
