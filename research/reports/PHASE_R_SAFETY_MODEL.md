# Phase R — Capital Safety & Security Model

**Status:** HARD-LOCKED  
**Authorized Live Capital:** `$0.00`  
**Live Adapter Status:** `HARD_DISABLED_FAIL_CLOSED`

---

## 1. Zero-Capital Hardware & Software Barrier

The platform implements multiple independent layers of protection ensuring that under no circumstance can real orders reach an exchange:

1. **Software Barrier (`FrozenContractGuard`):**  
   Whenever an execution action or capital allocation is evaluated, `FROZEN_GUARD.assert_capital_safety(0.0, False)` is invoked. Any positive value raises `FrozenContractViolationError` and halts execution.
2. **Adapter Isolation (`LiveAdapter`):**  
   The `LiveAdapter` class unconditionally raises `FatalSafetyError` on `submit_order()` and `close_position()`. It possesses no network endpoints for order placement.
3. **Execution Mode (`SHADOW_PAPER`):**  
   The application exclusively instantiates `ShadowAdapter` or `PaperAdapter`, which route orders to internal in-memory simulators.
4. **Credential Isolation:**  
   No API keys, private keys, or signing secrets are stored in code, configuration files, or logs. Market data is read via public WebSocket streams (`wss://stream.binance.com:9443/stream`).

---

## 2. Risk & Target Geometry Invariants

* **Minimum Destination Floor:** $\ge 4.0\text{R}$ required. No artificial extension allowed.
* **Target Geometry Invariant:**
  * Long: $\text{Target} > \text{Entry} > \text{Stop}$
  * Short: $\text{Target} < \text{Entry} < \text{Stop}$
* **Max Risk Per Trade:** $\le 1.0\%$ of simulated equity.
* **Max Asset Heat:** $\le 1.0\%$ of simulated equity.
* **Max Total Portfolio Heat:** $\le 3.0\%$ of simulated equity.
* **Drawdown Circuit Breakers:** Tier 1 ($5\%$ DD $\rightarrow 50\%$ size haircut), Tier 2 ($10\%$ DD $\rightarrow 75\%$ size haircut), Circuit Breaker ($15\%$ DD $\rightarrow$ trading halted).
* **Unknown State & Stale Data Policy:** Any corrupted, stale, or unknown state produces `NO_TRADE`.
