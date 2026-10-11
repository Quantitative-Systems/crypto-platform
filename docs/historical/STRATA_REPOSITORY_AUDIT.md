# STRATA Digital Trading Platform — Repository Forensic Audit

**Audit Date:** 2026-10-07  
**Platform Version:** 1.0.0 (STRATA Institutional Baseline)  
**Security Classification:** ZERO LEAKED CREDENTIALS / NON-CUSTODIAL FAIL-CLOSED  

---

## 1. Executive Summary & Inventory Overview

The repository comprises the complete, unified algorithmic trading platform, encompassing:
1. Historical research archives and certification proofs (Phases P, Q, Q.1, Q.2).
2. The scale-invariant 7-timeframe Market Model and FractalStateEngine.
3. The production execution spine, multi-tier safety barrier, and continuous candle aggregator.
4. Multi-account, multi-broker, and circuit breaker governance.
5. Automated restart recovery, event-driven alerting, and offline research candidate pipeline.
6. The institutional web terminal dashboard and REST API gateway.

---

## 2. Comprehensive Directory & File Classification

| Directory / File | Category | Status | Operational Role / Description |
| :--- | :--- | :--- | :--- |
| `main.py` | **CORE** | Active | Primary production entrypoint (args: `--mode`, `--symbols`, `--port`, `--equity`) |
| `cli.py` | **CORE** | Active | Unified CLI interface (`health`, `status`, `accounts`, `reconcile`, `verify-contract`, etc.) |
| `config/` | **CORE** | Active | Asset specifications and canonical timeframe sets configuration |
| `config.example.json` | **CORE** | Active | Example static platform configuration template |
| `.env.example` | **CORE** | Active | Safe environment variable template with zero hardcoded credentials |
| `.gitignore` | **CORE** | Active | Strict exclusion of bytecodes, local logs, secrets, and ephemeral runtime outputs |
| `pyproject.toml` | **CORE** | Active | Python packaging metadata, pytest configuration, tool settings |
| `requirements.txt` | **CORE** | Active | Minimal production dependency declarations (`aiohttp`, `numpy`, `pytest`) |
| `accounts/` | **ACCOUNT** | Active | Multi-account manager & config (`ACC_PAPER_PRIMARY`, `ACC_BINANCE_DEMO`, etc.) |
| `execution/safety/` | **RISK / EXECUTION** | Active | `PlatformSafetyGate`: 5-tier cryptographic gating & micro-live constraints |
| `execution/adapters/` | **BROKER / EXECUTION**| Active | `ExecutionGateway`, `ShadowAdapter`, `PaperAdapter`, `BrokerDemoAdapter`, `LiveAdapter` |
| `execution/decision/` | **EXECUTION** | Active | `PhaseRDecisionEngine`, target geometry enforcement ($\ge 4.0\text{R}$), immutable ledger |
| `execution/position/` | **EXECUTION** | Active | `PositionLifecycleMonitor`: Trailing stops, breakeven (+2R), and terminal states |
| `execution/reconciliation_engine.py` | **EXECUTION** | Active | `AutonomousReconciliationEngine`: 3-way internal vs broker state auditor |
| `execution/risk/circuit_breakers.py`| **RISK** | Active | 4 automated circuit breakers (Drawdown, Consecutive Losses, Stale Data, Reconcile) |
| `execution/state/` | **CORE** | Active | `StatePersistenceManager`: SHA-256 state checkpointing & restart recovery |
| `execution/autonomous_supervisor.py`| **CORE** | Active | Master 24/7/365 supervisor orchestrating all pipeline components |
| `instrument/` | **DATA / ACCOUNT** | Active | `PlatformUniverseManager`: 11-step institutional admission gate & crypto invariant |
| `market_data/realtime/` | **DATA** | Active | `BinanceRealtimeWSClient` & continuous 7-timeframe `ContinuousCandleEngine` |
| `market_data/cache/` | **DATA** | Certified | Historical cached klines for offline seeding and causal regression replay |
| `market_data/` (root) | **DATA** | Active | Data acquisition governor, data quality certifier, universal data fabric |
| `market_model/` | **CORE** | Frozen | Invariant 3-domain Market Model: Structure, Key Zones/Levels, Phase |
| `market_model/fractal_state_engine.py`| **CORE** | Frozen | Certified multi-timeframe state aggregator (Sets 1 to 5) |
| `strategy/` | **CORE** | Frozen | Strategy families (F01–F11), observation registry, hypothesis evaluators |
| `validation/realtime_drift_monitor.py`| **RISK** | Active | Real-time statistical drift monitor vs frozen Q.2 reference distributions |
| `validation/research_candidate_pipeline.py`| **RESEARCH** | Active | Generates offline research proposals on detected drift (live code remains frozen) |
| `notifications/` | **CORE** | Active | `AlertRouter`: Sanitized event dispatch (Console, Ring buffer, File, Webhook) |
| `web/` | **UI** | Active | Async `PhaseRWebServer` & institutional trading terminal UI (14 views) |
| `research/contracts/` | **RESEARCH** | Frozen | `PHASE_R_FROZEN_Q2_CONTRACT.json` & `FrozenContractGuard` (SHA-256 seal) |
| `research/experiments/` | **RESEARCH** | Active | Forensic certification scripts & `run_phase_r_replay_regression.py` |
| `research/reports/` | **DOCUMENTATION** | Active | Authoritative architectural, safety, audit, and empirical validation reports |
| `research/results/` | **RESEARCH** | Active | Machine-readable status JSONs, replay metrics, and research proofs |
| `tests/` | **TEST** | Active | 172 automated unit & integration tests (100% passing) |
| `deploy/` | **DEPLOYMENT** | Active | Systemd service unit (`crypto-platform.service`) with security sandboxing |
| `docs/` & `examples/` | **DOCUMENTATION** | Active | Reference guides and documentation assets |
| `scratch/` | **TEMPORARY** | Ignored | Ephemeral scratch directory (excluded by `.gitignore`) |
| `.archive/` | **OBSOLETE** | Archived | Historical research drafts and deprecated iterations |

---

## 3. Security Audit & Zero-Secret Verification

- **Automated Regex Scan:** Searched for `api_key`, `secret`, `private_key`, `token`, `password`, `bearer`.
- **Verdict:** **ZERO hardcoded secrets or production private keys found.**
- **Network Boundaries:** Live trading adapter is hard-disabled (`$0.00` capital). Real capital routing requires explicit environment-based cryptographic tokens.
