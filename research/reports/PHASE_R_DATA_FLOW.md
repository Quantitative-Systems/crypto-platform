# Phase R — End-to-End Data & Execution Flow Architecture

```text
               BINANCE PUBLIC WEBSOCKET (kline_15m)
                               │
                               ▼
               BinanceRealtimeWSClient (aiohttp)
               ├── Heartbeat / Ping-Pong
               ├── Timestamp Monotonicity Audit
               ├── Deduplication & Sequence Check
               └── Data Health (HEALTHY / DEGRADED / STALE / INVALID)
                               │
                       [Closed Candle]
                               ▼
               ContinuousCandleEngine (7-Timeframe)
               ├── Causal Array Maintenance
               ├── Seeded from Disk Cache (market_data/cache/)
               └── 1M → 1W → 1D → 4H → 1H → 15M → 3M
                               │
                               ▼
               FractalStateEngine (Frozen Q.2)
               ├── Directed Hierarchy Graph
               ├── Cross-Timeframe Alignment & Bias
               └── Dealing Range Location (Discount / Premium)
                               │
                               ▼
               MTFStrategyCoordinator (Sets 1–5, Pullback & Continuation)
               ├── Structural Breaks (BOS / CHOCH)
               └── Destination Key Zones
                               │
                               ▼
               PhaseRDecisionEngine
               ├── Frozen Confidence Calculation (0.35 + 0.25 + 0.20 + 0.15 + 0.05)
               ├── Geometry Validation (Long: T > E > S; Short: T < E < S)
               ├── Minimum Floor (>= 4.0R Destination)
               ├── Capital Policy (Sets 1 & 5: $0; Sets 2–4: Shadow Eligible)
               └── Frozen Risk Governors (Trade <= 1%, Heat <= 3%)
                               │
               ┌───────────────┴───────────────┐
               ▼                               ▼
          [NO_TRADE]                        [TRADE]
               │                               │
               │                    OrderIntent (Size <= 1%)
               │                               │
               │                               ▼
               │                    ShadowAdapter (Simulated Fill)
               │                    ├── Spread Crossing (1.5 bps)
               │                    ├── Adverse Slippage (4.0 bps)
               │                    └── Taker Fee (10.0 bps)
               │                               │
               │                               ▼
               │                    PositionLifecycleMonitor
               │                    ├── MTF Structural Trailing Stop
               │                    └── Target Hit Exit (>= 4R)
               │                               │
               └───────────────┬───────────────┘
                               │
                               ▼
               LiveDecisionLedger (Append-Only JSONL)
                               │
                               ▼
               AutonomousReconciliationEngine & RealtimeDriftMonitor
                               │
                               ▼
               Web Application Server (aiohttp.web Dashboard & REST API)
```
