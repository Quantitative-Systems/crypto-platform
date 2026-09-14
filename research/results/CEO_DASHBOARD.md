# PROJECT TOP1 — CEO RESEARCH & TRADING OS DASHBOARD
**Generated:** 2026-09-14 12:15:17 UTC
**Research OS Status:** OPERATIONAL | RISK ENGINE: CERTIFIED (1.000% Max SL Loss)

---

## 1. Candidate Pipeline
| Pipeline Stage | Count | Notes |
| :--- | :---: | :--- |
| **Total Candidates** | **3** | All registered candidates |
| Research / Development | 3 | Active hypothesis formulation |
| Promising | 0 | Passed In-Sample development gates |
| Validation | 0 | Undergoing parameter & cost robustness |
| Out-of-Sample (OOS) | 0 | Gated OOS verification |
| Robust | 0 | Passed multi-asset & subperiod stability |
| Paper | 0 | Simulated forward paper trading |
| **Qualified** | **0** | Eligible for capital allocation |
| Live Capital | 0 | Deployed in production (Capital Barrier) |
| Failed / Degraded | 0 | Archived negative benchmarks |

---

## 2. Strategy Candidate Performance Ledger
| Strategy ID | Version | Family | Status | Net R | Exp (R) | PF | Win Rate | Max DD (R) | Trades | Verdict |
| :--- | :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| **CANDIDATE-001** | 1.0.0-FROZEN | MTF_CONTINUATION | `RESEARCH` | +35.79R | +1.43R | 3.94 | 44.0% | 2.91R | 25 | Frozen benchmark. Opportunity starved (25 trades total across 18 sets, 10 sets with 0 trades). |
| **EXP-001A-GEOM** | 0.1.0-DRAFT | MTF_CONTINUATION | `RESEARCH` | +0.00R | +0.00R | N/A | 0.0% | 0.00R | 0 | Pre-registered hypothesis for Discovery Lab: test reducing 6R hurdle to 3R to unlock viable setups. |
| **EXP-001B-STOCH** | 0.1.0-DRAFT | TREND_PULLBACK | `RESEARCH` | +0.00R | +0.00R | N/A | 0.0% | 0.00R | 0 | Pre-registered hypothesis: decouple HTF from deep oversold condition, allowing trend persistence. |

---

## 3. Robustness & Portability Telemetry
- **Sizing & Risk Integrity:** CERTIFIED. Sizing accounts for Binance VIP-0 taker fees (0.075%) and slippage/spread (0.035%).
- **Causality & Lookahead:** ZERO LOOKAHEAD. Multi-timeframe synchronization uses closed bars (`bisect_right(close_times, t) - 1`).
- **Collision Handling:** ADVERSE-FIRST PRIORITY enforced. Stop-loss triggers precede target milestones on simultaneous intrabar breaches.
- **OOS Isolation:** LOCKED. Development and Out-of-Sample datasets partitioned 70/30 chronologically.

---

## 4. Production Readiness & Capital Engine
- **Live Capital Status:** LOCKED (Phase K/L Capital Barrier Active).
- **Prerequisite for Capital Deployment:** Only strategies in `QUALIFIED` status with $\ge 30$ development trades, verified OOS survival, and multi-asset portability may enter the capital engine.
