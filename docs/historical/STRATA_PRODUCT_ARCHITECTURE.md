# STRATA — Product Architecture Specification

## 1. Executive Mission & Identity
**STRATA** is an institutional-grade **Autonomous Crypto Trading Platform** designed to engineer, test, govern, and execute quantitative cryptocurrency trading strategies.
- **Repository Identity**: `crypto-platform` (unmodified).
- **Product Identity**: `STRATA` — Autonomous Crypto Trading Platform.
- **Ethical & Operational Boundary**: STRATA is positioned strictly around quantitative research, automated risk invariants, causal execution, and strategy falsification. It does **not** make claims of guaranteed profits, automated wealth creation, or risk-free operation.

---

## 2. High-Level Architectural Topology

```text
                                     STRATA
                                       │
                ┌──────────────────────┼──────────────────────┐
                │                      │                      │
             WEBSITE                WEB APP                ANDROID
          (Public/Info)         (Institutional)         (Mobile Touch)
                │                      │                      │
                └──────────────────────┼──────────────────────┘
                                       │
                                STRATA PLATFORM
                               (FastAPI/aiohttp)
                                       │
                ┌──────────────────────┼──────────────────────┐
                │                      │                      │
            KING CORE              STRATA LAB              USER LAB
          (Domain A: Q.2)      (Domain B: Built-in)   (Domain C: Custom)
                │                      │                      │
                └──────────────────────┼──────────────────────┘
                                       │
                             AUTONOMOUS AGENT
                           (Execution Orchestrator)
                                       │
                                RISK GOVERNOR
                       (≤1% Risk | ≤3% Heat | ≥4R Floor)
                                       │
                               EXECUTION GATEWAY
                       (Paper / Demo / Micro / Live)
                                       │
                             USER BROKER ACCOUNTS
                           (Binance / Bybit / MT5)
                                       │
                            POSITIONS / LEDGER / DATA
                                       │
                               RESEARCH LOOP
                          (Continuous Evolution)
```

---

## 3. Subsystem Breakdown

### 3.1 Domain A: Protected KING Engine (`execution/king/`)
- **Foundation**: Frozen Phase Q.2 / Phase R market intelligence.
- **Contract Guardian**: `KingEngineProtectionGuard` enforces SHA-256 contract hash `8fbc923a104e7688c3a9f0e4b8592c30dfb0b9a67a84511d5e49f8721c432098`.
- **Invariants**: 7-timeframe fractal hierarchy (1M → 1W → 1D → 4H → 1H → 15M → 3M), $\ge 4.0\text{R}$ reward-to-risk floor, closed-candle causality, confidence threshold $\ge 0.60$.
- **Capital Authorization**: $\$0.00$ fail-closed until multi-signature live approval.

### 3.2 Domain B: STRATA Built-In Library (`strategy/library/`)
- Independently researched algorithmic crypto strategies:
  - Trend following (`f10_structure_momentum_phase`)
  - Pullback / Breakout / Mean Reversion / Regime-Adaptive
- Strict requirement: Every strategy must maintain an independent audit trail and lifecycle state before eligibility.

### 3.3 Domain C: User Strategy Lab (`strategy/lab/`)
- Natural Language Strategy Compiler: Converts natural language trading rules into deterministic `StrategySpecification` structures.
- Falsification & Stress Testing: Rejects invalid or unverified strategies (`NOT_READY` verdict) prior to paper simulation.

### 3.4 Strata Autonomous Agent (`execution/agent/strata_autonomous_agent.py`)
- **Role**: Continuous orchestration layer running the control loop:
  $$\text{OBSERVE} \longrightarrow \text{UNDERSTAND} \longrightarrow \text{SELECT} \longrightarrow \text{VALIDATE} \longrightarrow \text{MONITOR} \longrightarrow \text{MANAGE}$$
- **Safety Boundary**: The Agent is **not** a trading strategy. It cannot alter the KING engine, bypass risk limits, remove the $\ge 4\text{R}$ floor, or deploy untested code to live accounts.

### 3.5 Risk Governor & Capital Invariants (`risk/`)
- **Single Trade Risk**: $\le 1.00\%$ of account equity (user selectable down to $0.10\%$).
- **Single Asset Exposure**: $\le 1.00\%$ base-asset risk.
- **Total Portfolio Heat**: $\le 3.00\%$ aggregate exposure.
- **Circuit Breakers**: Immediate halt on drawdown breaches, broker desynchronization, or data feed staleness.

### 3.6 Multi-Tenant Account & Broker Center (`core/tenancy/`, `accounts/`, `broker/`)
- Multi-tenant data segregation with `TenantContext` and `TenantScopedStore`.
- Universal `BaseBrokerAdapter` interfacing with Binance, Bybit, and MetaTrader 5 (MT5).
- Zero broker credential leakage to client surfaces.

---

## 4. Execution Environments
1. **SHADOW**: Real-time ticker evaluation, zero order placement.
2. **PAPER**: Simulated exchange matching with realistic slippage and fee modeling.
3. **DEMO**: Execution against exchange testnets (e.g., Binance Futures Testnet).
4. **MICRO-LIVE**: Constrained live trading with micro-notional sizes ($10–$50).
5. **CONTROLLED-LIVE**: Full live production execution (strictly gated, requiring explicit authorization).

---

## 5. Resilience & Fault Recovery
- High-availability watchdog thread monitoring WebSocket and order streams.
- State checkpointing to local SQLite/WAL storage.
- Auto-reconciliation upon restart: cancels unknown ghost orders, queries exchange positions, and enforces risk limits before resuming.
