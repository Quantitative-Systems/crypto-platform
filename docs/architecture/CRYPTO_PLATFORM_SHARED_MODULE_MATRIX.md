# Crypto Platform — Shared Module Mapping Matrix

## 1. Product Capability Cross-Platform Matrix

This matrix maps every core capability of the **Crypto Platform** across the shared domain service, API endpoints, database ownership, Desktop Web Workstation screen, Native Android Mobile screen, existing test coverage, and implementation status.

| Capability / Module | Domain Service | API Endpoint(s) | Database / Persistence | Desktop Web Screen (`app_terminal.html`) | Native Android Screen (`mobile/android/`) | Test Coverage | Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :---: |
| **1. Authentication & Session** | `AuthService` (`core/auth/`) | `/api/auth/register`<br/>`/api/auth/login`<br/>`/api/auth/me` | In-Memory Dict $\to$ SQLite `users`, `sessions` | Header / Login Modal | `AccountScreen.kt` | `test_auth_service.py`<br/>`test_cloud_staging_smoke.py` | `PARTIALLY_IMPLEMENTED` (DB migration needed) |
| **2. Overview & Cockpit** | `AutonomousTradingSupervisor` | `/api/king/overview`<br/>`/api/telemetry` | `platform_checkpoint.json` | Tab 1: **Overview** (`#page-overview`) | `HomeScreen.kt` (Dashboard) | `test_cloud_staging_smoke.py` | `IMPLEMENTED` |
| **3. Markets & Watchlists** | `UniverseManager`<br/>`ContinuousCandleEngine` | `/api/markets`<br/>`/api/markets/{sym}`<br/>`/api/markets/watchlist` | SQLite `user_watchlists`<br/>`market_data/cache/` | Tab 2: **Markets & Tickers** (`#page-markets`) | `MarketsScreen.kt` | `test_cloud_staging_smoke.py` | `IMPLEMENTED` |
| **4. Market Detail & Candlesticks** | `ContinuousCandleEngine`<br/>`MarketStateGenerator` | `/api/markets/{sym}` | Ephemeral Candle Cache | Interactive Canvas Chart / Metrics | `MarketDetailScreen.kt` (Native Canvas) | Unit tests in candle engine | `IMPLEMENTED` |
| **5. 7-Timeframe Visualizer** | `MarketStateGenerator` (`market_model/`) | `/api/king/overview`<br/>`/api/markets/{sym}` | `StructureSnapshot` Memory | Tab 4: **Engine Core** (`#page-king`) | `MarketDetailScreen.kt` (7-TF Ladder Component) | `test_canonical_pipeline_integration.py` | `IMPLEMENTED` |
| **6. Opportunity Pipeline** | `PhaseRDecisionEngine` | `/api/king/overview`<br/>`/api/decisions` | Memory + Decision Ledger | Tab 3: **Opportunity Pipeline** (`#page-opportunities`) | `HomeScreen.kt` (Active Signal Card) | `test_phase_r_replay_regression.py` | `IMPLEMENTED` |
| **7. Strategy Catalog** | `FAMILY_REGISTRY` (`strategy/`) | `/api/strategies` | SQLite `strategy_configs` | Tab 5: **Strategy Library** (`#page-strategies`) | `StrategiesScreen.kt` | `test_strategy_families.py` | `IMPLEMENTED` (Android uses static fallback) |
| **8. Strategy Lab / Research** | `StrategyLab` (`strategy/lab/`) | `/api/strategy-lab/parse`<br/>`/api/strategy-lab/evaluate` | `research/results/` | Tab 6: **Strategy Research & AI** (`#page-strategy-lab`) | `ResearchScreen.kt` (NL Spec Prompt) | `test_strategy_lab.py` | `IMPLEMENTED` |
| **9. Backtest Repository** | `BenchmarkReplay`<br/>`RESEARCH_PIPELINE` | `/api/backtests` | `RESEARCH_LEADERBOARD.json` | Tab 7: **Backtest Repository** (`#page-backtesting`) | `BacktestScreen.kt` | `test_cloud_staging_smoke.py` | `IMPLEMENTED` |
| **10. Forward Shadow Validation** | `ForwardValidationEngine` | `/api/forward-validation` | `data/checkpoints/` | Tab 8: **Forward Validation** (`#page-forward`) | `ForwardValidationScreen.kt` | `test_cloud_staging_smoke.py` | `IMPLEMENTED` |
| **11. Position Blotter** | `PositionLifecycleMonitor` | `/api/positions` | Checkpoint + SQLite `positions` | Tab 11: **Position Blotter** (`#page-positions`) | `TradingBlotterScreen.kt` | `test_cloud_staging_smoke.py` | `IMPLEMENTED` (Android needs response parsing) |
| **12. Order Blotter** | `AutonomousTradingSupervisor` | `/api/orders` | Checkpoint + Order Log | Tab 12: **Order Blotter** (`#page-orders`) | `TradingBlotterScreen.kt` | `test_cloud_staging_smoke.py` | `IMPLEMENTED` |
| **13. Risk Center & Heat** | `CompositeCircuitBreakerManager` | `/api/risk` | In-memory Governor | Tab 13: **Risk Center & Heat** (`#page-risk`) | `RiskScreen.kt` | `test_risk_governance.py` | `IMPLEMENTED` |
| **14. Performance Analytics** | `AutonomousTradingSupervisor` | `/api/telemetry`<br/>`/api/risk` | Equity Timeseries | Tab 14: **Performance** (`#page-performance`) | `PerformanceScreen.kt` | `test_cloud_staging_smoke.py` | `IMPLEMENTED` |
| **15. Strategy Drift Monitor** | `RealtimeDriftMonitor` | `/api/drift` | Statistical Event Log | Tab 15: **Strategy Drift** (`#page-drift`) | `MonitoringScreen.kt` | `test_drift_monitor.py` | `IMPLEMENTED` |
| **16. Operational Alerts** | `AlertRouter` (`notifications/`) | `/api/alerts` | Memory FIFO Queue (50 items) | Tab 16: **Alerts** (`#page-alerts`) | `MonitoringScreen.kt` | `test_alert_router.py` | `IMPLEMENTED` (Android uses static fallback) |
| **17. Append-Only Ledger** | `LiveDecisionLedger` | `/api/decisions` | `data/logs/` JSONL Ledger | Tab 17: **Decision Ledger** (`#page-ledger`) | *Desktop Only* (High-density JSON cards) | `test_decision_ledger.py` | `IMPLEMENTED` (Web Only) |
| **18. Account & Venues** | `AccountManager` | `/api/accounts`<br/>`/api/brokers` | SQLite `accounts` | Tab 9 & 10: **Accounts & Brokers** | `AccountScreen.kt` | `test_account_manager.py` | `IMPLEMENTED` |
| **19. Emergency Controls** | `SAFETY_GATE` / Supervisor | `/api/system/halt`<br/>`/api/agent/pause` | Volatile Memory Gate | Topbar Buttons (`#btn-emergency`) | Bottom Sheet / Header Button | `test_safety_gate.py` | `IMPLEMENTED` |

---

## 2. Gaps and Synchronization Opportunities

1. **Android Data Binding Enhancements:**
   - In `mobile/android/.../AppRepositories.kt`:
     - Update `StrategyRepository.getStrategies()` to parse the real `/api/strategies` array rather than returning `staticCatalog`.
     - Update `TradingRepository.getPositions()` to parse the real `/api/positions` payload.
     - Update `MonitoringRepository.getAlerts()` to fetch from `/api/alerts`.
2. **Web Desktop Unique Features:**
   - Tab 17 (**Append-Only Ledger**) provides full JSON attribution inspectability, ideal for desktop monitors with high horizontal width. Mobile clients consume summary alerts and signals.
3. **Android Mobile Unique Features:**
   - Hardware Keystore storage for encrypted credentials, offline local watchlist caching, and touch-optimized candlestick scrubbing.
