# STRATA Digital Trading Platform — Real User Acceptance Test Plan

**Document Version:** `1.0.0-PROD-VAL`  
**Target Environment:** `PAPER` / `DEMO` / `TESTNET` (Strict Fail-Closed Real Capital = `$0.00`)  
**Product Scope:** Public Website, Institutional Web Terminal, REST APIs, Autonomous Agent, KING Engine Guard  
**Applicability:** Human Quality Assurance Engineers, Institutional Operators, and Security Auditors.

---

## Pre-Flight Requirements & Test Environment Setup

1. **Local Server Execution:**
   ```bash
   python main.py
   ```
   *Expected Console Output:*
   ```text
   ======================================================================
   STRATA DIGITAL TRADING PLATFORM — AUTONOMOUS CRYPTO ENGINE
   ======================================================================
   [STARTUP] Pre-flight security validation passed.
   [SECURITY] LIVE TRADING FAIL-CLOSED ENFORCED. REAL CAPITAL = $0.00.
   [SUPERVISOR] Running on http://127.0.0.1:8080
   ```

2. **Browser Requirements:** Chrome / Firefox / Safari (latest versions). Clean incognito profile recommended to avoid cached authentication cookies.

---

## 30-Step Comprehensive Acceptance Checklist

| # | Action / Step | UI Interaction / URL | Expected Behavior | Verification Criteria | Status |
|---|---|---|---|---|---|
| **01** | Open Public Website | Navigate to `http://localhost:8080/` | Public marketing landing page loads with STRATA dark glassmorphism theme. Zero broken assets. | Clean typography, no console 404 errors, navigation bar visible. | [ ] PASS |
| **02** | User Registration | Click `Get Started` or navigate to `/pricing` -> Register Modal | Modal prompts for email and password. Password confirmation enforced. | POST `/api/auth/register` returns `200 OK` with user payload. | [ ] PASS |
| **03** | User Login | Enter registered credentials on `/app` or login modal | Auth service issues session JWT token; redirected to Web Terminal Cockpit. | Token stored in secure storage; UI transitions to `/dashboard`. | [ ] PASS |
| **04** | User Logout | Click `Logout` in user profile dropdown | Session invalidated on backend, redirected to public login. | Token cleared; subsequent API calls return `401 Unauthorized`. | [ ] PASS |
| **05** | Re-Authenticate | Log back in with valid credentials | User state reloaded cleanly; active dashboard tab restored. | Session re-established; user profile shows authenticated state. | [ ] PASS |
| **06** | Open Master Cockpit | Select `Overview` / `Dashboard` tab | Cockpit displays telemetry, balance, equity curve, capital safety banner. | Top red banner displays: `REAL CAPITAL: $0.00 | LIVE TRADING: LOCKED`. | [ ] PASS |
| **07** | Inspect KING Engine | Navigate to `KING` / `/king` view | 7-Timeframe ladder visualizer rendered (1M -> 1W -> 1D -> 4H -> 1H -> 15M -> 3M). | 5 Overlapping sets displayed with causal state markers. | [ ] PASS |
| **08** | Verify KING Protected Status | Check KING contract panel | Contract Hash: `8fbc923a104e7688c3a9f0e4b8592c30dfb0b9a67a84511d5e49f8721c432098` shown as `VERIFIED_IMMUTABLE`. | No parameter edit controls exist; edge is locked. | [ ] PASS |
| **09** | Add Demo / Testnet Broker | Navigate to `Brokers` -> `Add Broker Account` | Modal opens offering `BINANCE_TESTNET`, `BYBIT_TESTNET`, `MT5_DEMO`. | Live environment options visibly greyed out and locked. | [ ] PASS |
| **10** | Verify Broker Account | Input mock/testnet API key & secret, click `Connect` | Account created under `DEMO` status; capability discovery matrix populated. | Balance, tick size, min lot, precision displayed accurately. | [ ] PASS |
| **11** | Select Trading Style | Open `Agent Orchestration` -> Style selector | Options: `CONSERVATIVE`, `BALANCED`, `AGGRESSIVE`, `AUTONOMOUS`. | Style update reflected in agent state card immediately. | [ ] PASS |
| **12** | Inspect Risk Constraints | Navigate to `Risk & Governance` tab | Hard constraints displayed: Trade Risk $\le 1\%$, Asset Heat $\le 1\%$, Portfolio Heat $\le 3\%$, Target $\ge 4.0\text{R}$. | Form validation rejects any input violating frozen limits. | [ ] PASS |
| **13** | Activate Paper Mode | Select `PAPER` execution toggle | Supervisor initiates paper order routing loop; mock balance tracks simulated fills. | Environment indicator shows green `PAPER` badge. | [ ] PASS |
| **14** | Activate Demo / Testnet Mode | Select `DEMO / TESTNET` execution toggle | Supervisor connects to testnet venue gateway; live orders strictly prevented. | Environment badge updates to amber `TESTNET`. | [ ] PASS |
| **15** | Observe Real-Time Market Data | Navigate to `Markets` tab | Live websocket ticker and closed candles for BTCUSDT update periodically. | Freshness counter < 2000ms; health status indicates `DATA_HEALTHY`. | [ ] PASS |
| **16** | Observe Decision Pipeline | Navigate to `Opportunities` / `Decision Ledger` | Decision cards populate with causal reasons ("Why Trade" vs "Why No Trade"). | Detailed attribution: Confidence score, hypothesis, fractal state. | [ ] PASS |
| **17** | Observe Order Blotter | Navigate to `Orders` tab | Orders table lists lifecycle state: `INTENT` -> `SUBMITTED` -> `FILLED`. | 22 Lineage fields tracked per order record (SHA-256 hash intact). | [ ] PASS |
| **18** | Observe Position Blotter | Navigate to `Positions` tab | Active positions displayed with entry price, stop-loss, and $\ge 4.0\text{R}$ target. | Real-time mark-to-market P&L calculation updates dynamically. | [ ] PASS |
| **19** | Observe Performance Analytics | Navigate to `Performance` tab | Equity chart, Sharpe ratio, Profit Factor, Expectancy ($R$), Max DD. | Values accurately reflect realized closed positions. | [ ] PASS |
| **20** | Trigger Emergency Halt | Click prominent red `EMERGENCY HALT` button | Master kill-switch activated immediately. Modal confirms halt status. | Agent transitions to `EMERGENCY_HALTED`; all open intents canceled. | [ ] PASS |
| **21** | Verify No New Orders During Halt | Attempt to trigger manual cycle or signal | Platform rejects new order generation; log displays `EMERGENCY_HALTED`. | No new rows in order blotter; fail-closed behavior confirmed. | [ ] PASS |
| **22** | Operator Resume Platform | Enter confirmation key and click `Resume Operations` | Agent exits safe mode, transitions to `OBSERVING` state. | Telemetry reflects `RUNNING`; normal candidate scanning resumes. | [ ] PASS |
| **23** | Verify Recovery from Pause | Observe subsequent candle evaluation | Pipeline processes closed candle without state corruption or orphan orders. | State persistence logs confirm clean resumption. | [ ] PASS |
| **24** | Simulate Broker Disconnect | Cut testnet network or simulate 503 HTTP | Watchdog detects timeout/feed loss; raises `BROKER_DISCONNECTED` alert. | Telemetry status degrades to `BROKER_UNAVAILABLE`. | [ ] PASS |
| **25** | Verify Alert Notification | Open `Alerts` flyout / check notifications | System displays Red Banner & Warning Alert: `BROKER_DISCONNECTED`. | Alert message is sanitized (zero API secrets exposed). | [ ] PASS |
| **26** | Restore Broker Connection | Re-enable broker mock/network | Feed reconnects; `BROKER_CONNECTED` notification issued. | System marks health as `RECOVERED`. | [ ] PASS |
| **27** | Run Startup / Runtime Reconciliation | Navigate to `Reconciliation` tab or click `Audit Now` | `AutonomousReconciliationEngine` executes cross-ledger integrity audit. | Report shows `is_reconciled: true`; zero ghost/orphan positions. | [ ] PASS |
| **28** | Verify Notification Routing | Check operational event stream in `/api/alerts` | All major lifecycle events logged (startup, order, fill, recon). | Notifications categorized by severity (`INFO`, `WARNING`, `CRITICAL`). | [ ] PASS |
| **29** | Multi-Tenant Logout | Log out of Tenant A user account | Redirected to login; token invalidated. | Storage flushed; no Tenant A data visible. | [ ] PASS |
| **30** | Confirm Tenant Isolation | Register/Login as Tenant B | Tenant B terminal loads with clean, isolated accounts, orders, and positions. | Complete isolation confirmed: zero leakage from Tenant A. | [ ] PASS |

---

## Acceptance Sign-Off

- **Lead QA Engineer:** ____________________  **Date:** _______________  **Verdict:** `[ PASS / FAIL ]`  
- **Lead Risk Officer:** ____________________  **Date:** _______________  **Verdict:** `[ PASS / FAIL ]`  
- **Lead Platform Architect:** ______________  **Date:** _______________  **Verdict:** `[ PASS / FAIL ]`
