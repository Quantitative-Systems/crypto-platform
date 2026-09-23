# Crypto Trading Platform — Operations & Production Runbook

**Document Version:** 1.0.0  
**Classification:** SRE & Operational Runbook  

---

## 1. Unified Platform CLI Commands

The platform CLI provides commands for running research, discovery, paper trading, and inspecting system health:

```bash
# 1. Economic Horizon Screen (measures median ATR, stop distances, and fee-blocked horizons)
python3 -m crypto_platform.cli screen

# 2. Causal Research Sweep (runs DEV/VAL/OOS backtests across universe and evaluates G1-G7 gates)
python3 -m crypto_platform.cli sweep

# 3. Strategy Improvement & Parameter Perturbation Sweep
python3 -m crypto_platform.cli improve

# 4. Generate Research & Evidence Reports
python3 -m crypto_platform.cli report

# 5. Launch Forward Paper Trading Session (Connects to Live Binance/Bybit feeds with SQLite persistence)
python3 -m crypto_platform.cli paper

# 6. Query Subsystem Health, Positions, and Account Status
python3 -m crypto_platform.cli status
```

---

## 2. Emergency Operational Procedures

### 2.1 Emergency Global Trading Halt
If unexpected market volatility, systemic exchange insolvency, or platform software bugs are detected:
```python
from crypto_platform.risk_engine.firewall import RiskFirewall

firewall = RiskFirewall()
# Instantly halt all trading across all tenants, accounts, and venues
firewall.kill_switches.activate("GLOBAL", "*", "Emergency manual shutdown")
```

### 2.2 Exchange API Degradation or Outage
When an exchange begins returning 502/504 errors or WebSocket disconnections exceed threshold:
```python
# Isolate the affected exchange venue while leaving other venues active
firewall.kill_switches.activate("VENUE", "BINANCE", "Binance API latency spike")
```

### 2.3 Resolving State Reconciliation Failures
When the 5-second continuous reconciliation engine detects ghost orders or size mismatches:
1. Trading on the affected account is automatically frozen (`RECONCILIATION_OUT_OF_SYNC`).
2. SRE operator or automated reconciler triggers safe state recovery:
```python
from crypto_platform.reconciliation.reconciler import StateReconciliationEngine

reconciler = StateReconciliationEngine(risk_firewall=firewall)
await reconciler.restore_state_from_exchange(account_id, adapter, oms)
```
3. Once local state matches exchange truth, trading unfreezes automatically.
