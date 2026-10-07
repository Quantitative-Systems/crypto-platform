# Phase R — Forward Shadow/Paper Validation Protocol

**Protocol Status:** ACTIVE / STRICTLY OBSERVED  
**Capital Boundary:** `$0.00` Real Capital  
**Validation Universe:** `BTCUSDT`, `ETHUSDT`, `SOLUSDT`, `BNBUSDT`

---

## 1. Objective

To observe the frozen Q.2 model operating forward in time against live market telemetry, recording causal paper execution performance without in-sample contamination, hindsight bias, or retrospective modification.

---

## 2. Invariants & Rules of Engagement

1. **Model Freeze:** Zero modifications to the `FractalStateEngine`, `confidence_score` weights, `0.50` threshold gate, $\ge 4.0\text{R}$ floor, or risk limits.
2. **Execution Realism:**
   - Next-bar open execution with modeled adverse spread (1.5 bps) and slippage (4.0 bps).
   - Taker fees charged on both entry and exit (10.0 bps each way).
   - Intrabar collision policy: Adverse-first (stop-loss hit takes precedence over take-profit if both touched in same bar).
3. **Reconciliation Auditing:** The system performs automatic hourly and restart reconciliation of all candidates, decisions, orders, fills, and ledger hashes.
4. **Drift Monitoring:** Every completed paper trade is logged into the `RealtimeDriftMonitor`.
   - If rolling expectancy drops below $0.0\text{R}$ or drawdown exceeds $15.0\text{R}$, the system automatically enters `CRITICAL_DRIFT` and halts trade generation.

---

## 3. Forward Graduation Criteria (Pre-Requisites for Future Capital Consideration)

Live capital deployment will NOT be evaluated until all following forward criteria are satisfied:
1. Minimum **100 completed forward paper trades** executed across Sets 2, 3, and 4.
2. Realized forward expectancy $\ge +0.50\text{R}$.
3. Realized forward profit factor $\ge 2.0$.
4. Zero reconciliation discrepancies detected across the entire forward validation window.
5. Max forward drawdown $\le 12.0\text{R}$.
6. Zero execution safety violations.
