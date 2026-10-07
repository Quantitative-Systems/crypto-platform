# Phase R — Production Trading Application Architecture

**Version:** `1.0.0-phase-r`  
**Execution Mode:** `SHADOW_PAPER`  
**Capital Authorization:** `$0.00` Real Capital

---

## 1. System Architecture Overview

Phase R establishes the production autonomous trading organism for the `crypto-platform` codebase. It takes the forensically certified Q.2 universal fractal state engine and multi-timeframe strategy coordinator and integrates them into an end-to-end, 24/7/365 real-time autonomous system.

```text
┌────────────────────────────────────────────────────────────────────────┐
│                        PHASE R APPLICATION SYSTEM                      │
├────────────────────────────────────────────────────────────────────────┤
│ 1. INGESTION LAYER                                                     │
│    BinanceRealtimeWSClient (WebSocket + REST Fallback Polling)         │
│    Data Health Auditing (HEALTHY, DEGRADED, STALE, INVALID)            │
├────────────────────────────────────────────────────────────────────────┤
│ 2. CANDLE & TIMEFRAME ENGINE                                           │
│    ContinuousCandleEngine (Causal 7-TF Assembly: 1M..3M)               │
│    Deterministic Restart Recovery via Local Cache Seeding              │
├────────────────────────────────────────────────────────────────────────┤
│ 3. STATE & DECISION NERVOUS SYSTEM                                     │
│    FractalStateEngine (Causal Directed State Graph)                    │
│    MTFStrategyCoordinator (HTF Bias -> MTF Setup -> LTF Entry)         │
│    PhaseRDecisionEngine (Frozen Weights: 0.35+0.25+0.20+0.15+0.05)      │
│    Target Geometry Hard Validator (>= 4.0R Destination Floor)          │
├────────────────────────────────────────────────────────────────────────┤
│ 4. RISK & EXECUTION BARRIER                                            │
│    FrozenContractGuard (Runtime Assertions on Invariants)              │
│    PortfolioRiskGovernor (Trade <= 1%, Asset <= 1%, Heat <= 3%)        │
│    ShadowAdapter (Zero Real Capital, Adverse Spread & Slippage)        │
│    LiveAdapter (HARD-DISABLED / FAIL-CLOSED)                           │
├────────────────────────────────────────────────────────────────────────┤
│ 5. OBSERVABILITY, AUDIT & TERMINAL                                     │
│    PositionLifecycleMonitor (Structural Trailing Stops & Exits)        │
│    LiveDecisionLedger (Cryptographic Append-Only Ledger)               │
│    AutonomousReconciliationEngine (Conservation Audit)                 │
│    RealtimeDriftMonitor (Statistical Degradation Detector)             │
│    PhaseRWebServer (Async aiohttp REST API & Institutional Web UI)      │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Key Package Structure

* `market_data/realtime/`:
  * `binance_ws_client.py`: WebSocket ingestion client with health states.
  * `candle_engine.py`: Continuous 7-timeframe aggregator with provenance.
* `research/contracts/`:
  * `PHASE_R_FROZEN_Q2_CONTRACT.json`: Machine-readable immutable research contract.
  * `frozen_contract_guard.py`: Runtime invariant guard.
* `execution/adapters/`:
  * `execution_adapters.py`: Multi-mode adapter hierarchy with hard live barrier.
* `execution/decision/`:
  * `phase_r_decision_engine.py`: Deterministic decision engine.
* `execution/`:
  * `reconciliation_engine.py`: Conservation invariant auditor.
  * `autonomous_supervisor.py`: 24/7 autonomous coordinator.
* `validation/`:
  * `realtime_drift_monitor.py`: Real-time performance and regime monitor.
* `web/`:
  * `server.py`: Async web server and real-time dashboard terminal.
* `main.py`: Production application entrypoint.
