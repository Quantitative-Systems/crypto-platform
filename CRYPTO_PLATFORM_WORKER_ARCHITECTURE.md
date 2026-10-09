# Crypto Platform — Worker & Background Workload Architecture

## 1. Workload Classification Matrix

To optimize compute efficiency, prevent memory leaks, and protect quantitative invariants, platform workloads are decoupled into six operational classes:

| Class | Workload Name | Component / File | Trigger Mechanism | Execution Frequency | Compute Profile |
| :---: | :--- | :--- | :--- | :--- | :--- |
| **A** | **Market Data Ingestion** | `market_data/stream/binance_ws.py` | WebSocket streaming | Continuous (ms ticks) | Low CPU, I/O bound (~25 MB) |
| **A** | **Candle Aggregation Engine** | `market_data/engine/continuous_candle_engine.py` | Tick event | Continuous (Real-time) | Low CPU, memory buffer |
| **B** | **Decision Cycle Evaluation** | `execution/autonomous_supervisor.py` | Closed candle event | Event-driven (Every 15m/3m bar) | Moderate CPU burst (~100ms) |
| **B** | **Trailing Stop Execution** | `execution/position_lifecycle_monitor.py` | Price change tick | Event-driven | Minimal CPU (<1ms) |
| **C** | **State Reconciliation Audit** | `execution/audit/reconciliation_engine.py` | Scheduled timer | Periodic (Every 60s) | Low CPU (<10ms) |
| **C** | **Strategy Drift Monitor** | `execution/monitoring/drift_monitor.py` | Scheduled timer | Periodic (Every 5 mins) | Low CPU (statistical test) |
| **C** | **State Checkpointer** | `execution/state/state_persistence.py` | Scheduled timer | Periodic (Every 60s) + on shutdown | Atomic disk write |
| **D** | **Strategy Spec Parsing** | `strategy/lab/strategy_lab.py` | User API request | On-demand (Web/Android) | Low CPU (<50ms) |
| **D** | **Candidate Evaluation** | `strategy/lab/evaluation_pipeline.py` | User API request | On-demand | High CPU (1-3s batch run) |
| **E** | **Research Walk-Forward** | `research/experiments/` | CLI script / Researcher | Offline manual batch | High CPU / Memory intensive |
| **F** | **Replay Regression Test** | `run_phase_r_replay_regression.py` | GitHub Actions / Pre-push | CI build trigger | Moderate CPU (~3s, 9,608 trades) |

---

## 2. Worker Lifecycle & Concurrency Model

All continuous and periodic services execute within a single coordinated `asyncio` event loop managed by `AutonomousTradingSupervisor` in `main.py`:

```mermaid
graph TD
    subgraph Main Event Loop (asyncio)
        TASK_WS["Task 1: Binance WebSocket Ingestion<br/>(aiohttp ClientSession)"]
        TASK_CANDLE["Task 2: Continuous Candle Engine<br/>(Closed-Bar Aggregator)"]
        TASK_SUPER["Task 3: Autonomous Supervisor Loop<br/>(Decision & Execution Coordinator)"]
        TASK_WEB["Task 4: REST API Server<br/>(aiohttp Web App on port 8080)"]
        TASK_RECON["Task 5: Periodic Reconciliation<br/>(60-second Interval)"]
        TASK_DRIFT["Task 6: Statistical Drift Monitor<br/>(300-second Interval)"]
    end

    TASK_WS -->|Raw Ticks| TASK_CANDLE
    TASK_CANDLE -->|Closed 15m/3m Bar Event| TASK_SUPER
    TASK_SUPER -->|Simulated Orders| TASK_RECON
    TASK_SUPER -->|Decision Outcomes| TASK_DRIFT
```

---

## 3. Strict Boundary: Research Isolation vs. Frozen Production Strategy

> [!CAUTION]
> Strategy research executed via `/api/strategy-lab/*` or offline scripts **CANNOT AND MUST NOT** modify the live or paper trading engine's strategy parameters.

1. **Read-Only Production Strategy:**
   - The production structural strategy (`Phase R`) is immutable and enforced by `FROZEN_GUARD`.
2. **Candidate Isolation Sandbox:**
   - When a user prompts the Strategy Lab or triggers an evaluation, the spec runs in an isolated `StrategySpecification` sandbox against cached historical data.
   - Evaluated models are saved to `research/leaderboard/` as candidate proposals with versioned identifiers.
   - Candidates are **never** auto-promoted into the execution engine without explicit human code review and research contract amendment.
