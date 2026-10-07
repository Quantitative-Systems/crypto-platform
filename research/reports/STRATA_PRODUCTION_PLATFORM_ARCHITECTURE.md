# STRATA Digital Trading Platform — Institutional Architecture & Operations Manual

## 0. Product Identity & Architectural Charter

**Product Name:** STRATA Digital Trading Platform  
**Descriptor:** Institutional Multi-Timeframe Algorithmic Trading Infrastructure  
**Core Domain:** Continuous 24/7/365 Systematic Crypto Asset Trading  

The STRATA Platform operationalizes the empirically validated and certified Phase Q.2 / Phase R market model into an institutional-grade, multi-account, multi-environment trading platform. 

```
                    STRATA DIGITAL TRADING PLATFORM

                         Market Data (WebSocket)
                                   │
                                   ▼
                        7-TF Market State Engine
                                   │
                                   ▼
                       Strategy Decision Engine
                                   │
                                   ▼
                         Risk & Circuit Breakers
                                   │
                                   ▼
                           Execution Gateway
                                   │
              ┌────────────────────┼────────────────────┐
              ▼                    ▼                    ▼
       Virtual Paper          Broker Demo           Live Gateway
       ($0.00 Capital)      (Exchange Testnet)   (Cryptographic Gate)
              │                    │                    │
              └────────────────────┼────────────────────┘
                                   ▼
                            Broker Accounts
                                   │
                                   ▼
                        State Reconciliation
                                   │
                                   ▼
                           Position Manager
                                   │
                                   ▼
                        Immutable SHA-256 Ledger
                                   │
              ┌────────────────────┼────────────────────┐
              ▼                    ▼                    ▼
          Monitoring        Alert Router         Drift Monitor
                                                        │
                                                        ▼
                                                Research Pipeline
```

---

## 1. Execution Environments & Capital Gating Strata

Execution proceeds across five strictly defined and mathematically isolated tiers:

| Environment | Real Capital | Routing Venue | Safety Barrier | Order Constraints |
| :--- | :--- | :--- | :--- | :--- |
| **`SHADOW`** | **$0.00** | Simulated In-Memory | Fail-Closed | Zero real capital. Live ticks matched against virtual book. |
| **`PAPER`** | **$0.00** | Simulated Ledger | Fail-Closed | Full simulated order book with modeled adverse spread & slippage. |
| **`BROKER_DEMO`** | **$0.00** | Exchange Testnet | Fail-Closed | Real testnet API keys (e.g. Binance Futures Testnet). Zero capital. |
| **`MICRO_LIVE`** | **Micro (<$1k)** | Exchange Production | Cryptographic Gate | Strict bounds: Max $100 notional, max 0.1% risk, max 1 position. |
| **`CONTROLLED_LIVE`**| **Certified** | Exchange Production | Multi-Sig Hardware Gate | Standard governor limits (1% risk, 3% heat). Dual authorization. |

### Non-Negotiable Safety Invariant
The platform boots into **`PAPER`** mode by default with **`$0.00`** Real Capital. Any attempt to route live orders without a verified cryptographic passkey (`PLATFORM_LIVE_AUTH_TOKEN`) triggers `FatalSafetyError` and causes the application to immediately fail closed to paper execution.

---

## 2. Platform Core Subsystems

### 2.1 Multi-Broker & Multi-Account Manager (`accounts/`)
- Manages isolated account configs (`ACC_PAPER_PRIMARY`, `ACC_BINANCE_DEMO`, `ACC_BINANCE_MICRO_LIVE`).
- Isolates API credentials via environment variables (`BINANCE_TESTNET_API_KEY`, etc.).
- Never logs, serializes, or exposes private API keys.

### 2.2 Universe & Admission Gate (`instrument/universe_manager.py`)
- Enforces the 11-step institutional admission gate before any instrument can be traded.
- Enforces the `AssetClass.CRYPTO` invariant (base leg must be cryptocurrency).
- Tracks tick size, lot step, min notional, and typical spread.

### 2.3 Automated Circuit Breakers (`execution/risk/circuit_breakers.py`)
Four automated hardware/software breakers evaluate before every single order:
1. **MaxDrawdownBreaker:** Halts new trade entries if session drawdown reaches 4.0%.
2. **ConsecutiveLossBreaker:** Enforces a 4-hour cooldown if 3 consecutive losses occur.
3. **StaleDataBreaker:** Halts immediately if market data stream latency exceeds 30 seconds.
4. **ReconciliationDiscrepancyBreaker:** Halts instantly on any broker state discrepancy.

### 2.4 State Checkpointing & Restart Recovery (`execution/state/`)
- Periodically checkpoints system state to `research/results/state/platform_checkpoint.json`.
- Uses SHA-256 integrity hashing to detect any disk corruption or tampering.
- On platform restart, recovers active positions, simulated equity, and sync timestamps seamlessly.

### 2.5 Degradation to Research Candidate Pipeline (`validation/research_candidate_pipeline.py`)
- Real-time drift monitor compares rolling forward metrics against frozen Q.2 baselines.
- When degradation is detected (`DRIFT` or `CRITICAL_DRIFT`), generates a structured research proposal in `research/candidates/` for offline laboratory investigation.
- **Strict Rule:** Never retunes or mutates live strategy logic autonomously.

### 2.6 Institutional Web Terminal (`web/server.py`)
- Served via async `aiohttp.web` on port `8080`.
- 14 dedicated tabs: Cockpit, Markets, 7-TF Matrix, Opportunities, Positions, Orders, Accounts, Risk, Performance, Drift, Decision Ledger, Reconciliation, System Telemetry, Settings.
- Interactive Trade Explainer modal providing detailed "Why Trade?" and "Why No Trade?" causal rationales for every evaluated candle.

---

## 3. Operational Command Reference

### Starting the Platform
```powershell
# Default Paper Execution Mode
python main.py --mode PAPER --port 8080

# Alternative via Unified CLI
python cli.py start --mode PAPER --port 8080
```

### Health & Contract Audit
```powershell
python cli.py health
python cli.py verify-contract
```

### Reconcile Internal & Broker State
```powershell
python cli.py reconcile
```

### Inspect Accounts & Alerts
```powershell
python cli.py accounts
python cli.py alerts
```

### Full Test Pass & Replay Verification
```powershell
pytest tests/
python -m research.experiments.run_phase_r_replay_regression
```
