# Crypto Platform — System Architecture Specification

## 1. Executive Overview

Crypto Platform is an institutional-grade quantitative digital asset trading, research, and execution platform. The system operates on **one unified, authoritative Python backend** coupled to two real-time clients:
1. **Institutional Web Workstation**: Responsive single-page workstation with live streaming telemetry, interactive 5-set ladder visualizers, and strategy research blotters.
2. **Native Android Application**: Kotlin and Jetpack Compose mobile client with real-time WebSocket market-state feeds, multi-timeframe ladders, and configurable backend endpoints.

Both clients consume the exact same authoritative data contracts and REST/WebSocket APIs. No secondary or divergent strategy logic exists in the clients.

---

## 2. High-Level System Architecture Diagram

```mermaid
graph TD
    subgraph MarketData [Market Data Ingestion]
        BinancePublic[Binance Public WS / REST] --> MarketService[MarketService]
        Cache[Historical Parquet/JSON Cache] --> MarketService
        MarketService --> CandleEngine[7-Timeframe Candle Engine<br/>1M → 1W → 1D → 4H → 1H → 15M → 3M]
    end

    subgraph CoreEngine [Authoritative Core Engine]
        CandleEngine --> Supervisor[AutonomousTradingSupervisor]
        Supervisor --> FiveSet[5 Overlapping Timeframe Sets<br/>Set 1 to Set 5]
        FiveSet --> DecisionEngine[Phase R Decision Engine<br/>Frozen Contract Hash: 8fbc923a...]
        DecisionEngine --> RiskGov[Risk Governor & Target Geometry<br/>Min Floor >= 4.0R | Max Risk <= 1.0%]
        RiskGov --> SafetyGate[Fail-Closed Safety Gate<br/>Real Capital: $0.00 | Live: Disabled]
    end

    subgraph Persistence [Durable Storage Layer]
        Supervisor <--> SQLiteWAL[SQLite WAL Database<br/>crypto_platform.db]
        Supervisor <--> Checkpoints[Dual JSON Checkpoints<br/>research/results]
    end

    subgraph ServerLayer [Institutional Server Layer]
        Supervisor --> WebServer[PhaseRWebServer<br/>Aiohttp Async Server]
        WebServer --> RateLimiter[Security Middleware<br/>Rate Limiting & Security Headers]
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

## 3. The 7-Timeframe Ladder & 5-Set Architecture

The market model evaluates price action across a continuous ladder of 7 timeframes:
$$\text{1M} \longrightarrow \text{1W} \longrightarrow \text{1D} \longrightarrow \text{4H} \longrightarrow \text{1H} \longrightarrow \text{15M} \longrightarrow \text{3M}$$

Each timeframe extracts:
- **Market Structure / Trend**: Directional bias (Bullish / Bearish / Sideways).
- **Key Zones / Levels**: High-liquidity support, resistance, and Fair Value Gaps (FVG).
- **Phase State**: `PULLBACK` or `CONTINUATION` (with internal transition states `CONSOLIDATION` and `UNCERTAIN`).

### The 5 Overlapping Operational Sets
To eliminate single-timeframe bias and preserve multi-horizon causal transmission, timeframes are evaluated in 5 overlapping triplets:

| Set Name | Timeframe Triplet | Operational Horizon | Primary Role |
| :--- | :--- | :--- | :--- |
| **SET 1** | `1M → 1W → 1D` | Macro Context | Long-term macro regime and multi-month structural trend. |
| **SET 2** | `1W → 1D → 4H` | Structural Foundation | Swing trend formation and multi-week institutional zones. |
| **SET 3** | `1D → 4H → 1H` | Intermediate Trend | Day-to-swing bias and intraday continuation alignment. |
| **SET 4** | `4H → 1H → 15M` | Operational Swing | Session-level structure and tactical entry geometry. |
| **SET 5** | `1H → 15M → 3M` | Tactical Execution | Microstructure confirmation and execution trigger. |

---

## 4. Frozen Quantitative Research Contract

The core strategy and research model is permanently sealed under SHA-256 hash:
```
8fbc923a104e7688c3a9f0e4b8592c30dfb0b9a67a84511d5e49f8721c432098
```

Enforced by `FrozenContractGuard`:
- **Real Capital Authorized:** Strictly `$0.00`.
- **Live Order Submission:** Permanently disabled and fail-closed (`LIVE_TRADING_ENABLED = false`).
- **Target Geometry:** Minimum destination target floor $\ge 4.0\text{R}$.
- **Risk Per Trade:** Capped at $\le 1.0\%$ of equity.
- **Portfolio Heat:** Capped at $\le 3.0\%$ aggregate exposure.
- **Base Asset Exposure:** Capped at $\le 1.0\%$ cumulative per asset.

---

## 5. Storage, Persistence & Crash Recovery

1. **SQLite Database (`data/db/crypto_platform.db`):**
   - Configured with `PRAGMA journal_mode=WAL` for concurrent non-blocking reads.
   - Versioned migrations (`v1` through `v4`) with idempotent retry semantics.
   - Stores users, sessions, accounts, paper orders, executions, and decision logs.
2. **Dual Checkpoints:**
   - Atomic dual JSON snapshots in `data/checkpoints/` and `research/results/`.
   - On startup, `RecoveryWatchdog` verifies checksums and performs state reconciliation.
   - Idempotency keys (`idempotency_key`) prevent duplicate order submission across restarts.

---

## 6. Client Ecosystem Parity

- **Web Workstation (`web/static/app_terminal.html`):**
  - Institutional light financial-workstation aesthetic.
  - Dynamically configurable backend endpoint (`getApiBase()`).
  - Native WebSocket reconnection loop with exponential backoff.
- **Native Android Client (`mobile/android`):**
  - Built with Kotlin 1.9 and Jetpack Compose (Material 3).
  - Explicit build flavors (`debug`, `staging`, `release`).
  - Runtime custom API endpoint override in the Account/Settings screen.
  - Cleartext HTTP allowed only for emulator loopback (`10.0.2.2`); HTTPS/WSS enforced for staging and release.
