# CRYPTO PLATFORM — ANDROID-FIRST ARCHITECTURE SPECIFICATION

**Document Version:** 1.0.0  
**Target Platform:** Android (API Level 26+ / Android 8.0 Oreo through Android 14 / API 34)  
**Package Namespace:** `io.cryptoplatform.app`  
**Application Identity:** Crypto Platform  
**Operational Status:** Fail-Closed Research Core Protected &bull; Real Capital: $0.00  

---

## 1. Executive Architecture Summary

Crypto Platform is an Android-first crypto trading and quantitative research application. The application rejects consumer SaaS marketing pages and web-centric presentation in favor of a clean, information-dense financial research and trading application.

The platform couples a high-performance Android client container with the deterministic, frozen quantitative trading engine:
1. **Multi-Timeframe Structural Model:** 7-timeframe fractal ladder ($1\text{M} \to 1\text{W} \to 1\text{D} \to 4\text{H} \to 1\text{H} \to 15\text{M} \to 3\text{M}$).
2. **Deterministic Risk Governor:** Hard-coded invariant ceiling of $\le 1.0\%$ risk per trade, $\le 3.0\%$ portfolio heat, and $\ge 4.0\text{R}$ target floor.
3. **Fail-Closed Execution:** Real capital authorized is locked at `$0.00`, with live order routing disabled.
4. **Android Native Container:** Native Android wrapper (`MainActivity.java`, `WebAppInterface.java`) managing WebView hardware acceleration, sandboxed storage, and haptic emergency halts.

---

## 2. Directory & Component Layout

```
crypto-platform/
├── mobile/
│   └── android/
│       ├── AndroidManifest.xml                  # Manifest with network & vibration permissions
│       ├── app/
│       │   ├── build.gradle                     # Gradle configuration (compileSdk 34, minSdk 26)
│       │   └── src/main/java/io/cryptoplatform/app/
│       │       ├── MainActivity.java            # Native container activity & WebView client
│       │       └── WebAppInterface.java         # JS Bridge: emergency halt, haptics, status
│       └── assets/
│           └── www/
│               └── index.html                   # Complete Android Light UI application client
├── web/
│   ├── server.py                                # REST API harness & Android preview server
│   └── static/
│       ├── public_website.html                  # Minimal Engineering & Admin web interface
│       └── app_terminal.html                    # Desktop development & reconciliation workstation
└── tests/
    ├── unit/test_mobile_architecture.py         # Mobile layout, manifest, security tests
    └── integration/test_product_acceptance_programmatic.py # End-to-end acceptance suite
```

---

## 3. Visual Design System

The application strictly implements a professional financial workstation aesthetic designed for daily operational usage:

* **Color Palette:**
  * Background Page: `#f8fafc` (Slate 50)
  * Surface / Card Background: `#ffffff`
  * Text Heading: `#0f172a` (Slate 900)
  * Text Body: `#334155` (Slate 700)
  * Text Muted / Labels: `#64748b` (Slate 500)
  * Primary Action / Brand: `#2563eb` (Professional Blue)
  * Secondary / Data Visuals: `#0284c7` (Sky Blue)
  * Positive / Fill: `#059669` (Emerald Green)
  * Alert / Invalidation / Halt: `#dc2626` (Crimson Red)
  * Warning / In-Progress: `#d97706` (Amber)
  * Borders & Dividers: `#e2e8f0` / `#cbd5e1`
* **Typography:** Clean system sans-serif (`Inter`, `Roboto`, system default) with tabular monospace numerals (`JetBrains Mono`, `Consolas`).
* **Density:** Restrained padding (8–12px), compact financial tables, minimal micro-shadows, zero decorative gradients, and zero neon/cyberpunk elements.

---

## 4. Primary Navigation Architecture

The mobile interface is structured around a responsive dual navigation system:
1. **Top Bar & Sub-Tabs Strip:** Horizontal quick-switch pills exposing all 9 primary functional modules plus Market Detail.
2. **Bottom Navigation Bar:** 5 primary touch anchors (`Home`, `Markets`, `Strategies`, `Research`, `Trading`, `Account`).

### Screen Inventory & Functional Specifications

| Screen ID | Title | Core Functions & Data Elements |
|---|---|---|
| `screen-home` | **Home** | Portfolio summary ($100k simulated), Today's P&L, Portfolio Risk (0.00% / 3.00%), Admitted asset quick tickers, Active Trade Opportunities, Active Strategies, System Status. |
| `screen-markets` | **Markets** | Admitted universe filter (All vs Watchlist/Priority), search bar, sortable table (Price, 24h Change, Market Structure), interactive watchlist toggle star. |
| `screen-market-detail` | **Market Detail** | Asset header, canvas-rendered financial chart, 7-timeframe ladder matrix (1M to 3M), Market Structure, Key Zone, Phase breakdown, trade opportunity parameters, simulated paper order button. |
| `screen-strategies` | **Strategies** | Strategy style filters (Swing, Intraday, Scalping, Position, Systematic, Research), lifecycle state pills, Multi-Timeframe Structural Strategy (research baseline), historical validation evidence. |
| `screen-research` | **Research** | Natural language strategy research assistant, structured specification generator (Market, Style, Direction, Model, Phase, Entry, Stop, Target, Risk, Timeframes, Validation Plan), Backtest & Forward triggers, safety reality notice. |
| `screen-backtest` | **Backtesting** | Configuration inputs (Asset, Timeframe Set, Risk Model, Execution assumptions), Historical simulation results (9,608 trades, 67.2% win rate, +0.8885R expectancy, PF 4.92, -10.89R max drawdown), Canvas equity curve. |
| `screen-forward` | **Forward Testing** | 5 distinct environments: Historical (9,608), OOS (1,665), Paper (Active), Demo (Ready), Live (Locked $0.00). Forward observations metrics, slippage drag, drift status. |
| `screen-trading` | **Trading** | Positions blotter (Active & Closed), Orders blotter, Order lifecycle visual, Broker connections (Binance, Bybit, MT5), Permanent LIVE TRADING LOCKED banner. |
| `screen-risk` | **Risk** | Protected invariant gauges (Single Trade $\le 1\%$, Heat $\le 3\%$, Asset $\le 1\%$, Floor $\ge 4\text{R}$), Drawdown status, Circuit breakers (Daily Loss, Consecutive Loss, Volatility Spike), Fail-closed status. |
| `screen-performance` | **Performance** | Cumulative realized R, win rate, daily/weekly/monthly P&L, execution drag, historical reference benchmarks, honest zero-data notices. |
| `screen-monitoring` | **Monitoring** | System health status matrix (Market Data, Decision Engine, Risk Engine, Reconciliation, Drift, Forward Testing, Live Capital), Live filterable alerts stream. |
| `screen-account` | **Account** | Operator profile, multi-tenant isolation ID, session token management, Register/Login/Logout modal, Security settings, Emergency Stop trigger. |

---

## 5. Native Android Bridge & Security Model

The Android native layer enforces strict operating system security parameters:
1. **Network Security:** `usesCleartextTraffic="false"` in `AndroidManifest.xml` prevents unencrypted HTTP transmission.
2. **File Isolation:** WebView disables local file system reading (`setAllowFileAccess(false)`, `setAllowUniversalAccessFromFileURLs(false)`).
3. **Native JavaScript Interface (`AndroidBridge`):**
   * `emergencyHalt()`: Fires native haptic feedback, triggers fail-closed platform pause, and displays confirmation toasts.
   * `isLiveTradingLocked()`: Returns immutable `true` assertion to client code.
   * `getAppEnvironment()`: Supplies device metadata and environment variables.

---

## 6. Reproducible Android Build Instructions

### Prerequisites
* JDK 17 or higher
* Android SDK Platform 34 (Android 14) and Android Build Tools 34.0.0
* Gradle 8.4+

### Build Commands
```bash
# Navigate to mobile project directory
cd mobile/android

# Build Debug APK
./gradlew assembleDebug

# Output APK Location:
# mobile/android/app/build/outputs/apk/debug/app-debug.apk

# Install on connected device or emulator
adb install -r app/build/outputs/apk/debug/app-debug.apk

# Launch Main Activity
adb shell am start -n io.cryptoplatform.app/.MainActivity
```
