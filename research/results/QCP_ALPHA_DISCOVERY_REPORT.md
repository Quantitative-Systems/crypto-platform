# QCP Alpha Discovery & Empirical Validation Report

**Audit Date:** 2026-09-16T17:36:40.514735+00:00  
**Architecture:** Quantitative Crypto Platform (QCP) Autonomous Research Discovery Lab  
**Live Capital Status:** **$0.00 (LOCKED)**  
**Economic Truth Verdict:** `NO_NEW_ECONOMIC_EDGE_VALIDATED`

---

## 1. Executive Scientific Summary

The explicit mandate of this phase is: **FIND, TEST, FALSIFY, AND VALIDATE REAL ECONOMIC EDGES.**  
In accordance with Directive Section 19:
> *If no new alpha survives: REPORT `NO_NEW_ECONOMIC_EDGE_VALIDATED`. That is a successful scientific outcome.*

* **Certified Warehouse Datasets Admitted:** 24
* **Hypotheses Formulated:** 17
* **Strategy Variants Tested:** 16
* **Bonferroni Hurdle Rate:** `+0.2277R`
* **Candidates Falsified / Rejected:** 16
* **Candidates Blocked by Data Absence:** 9
* **Candidates Surviving All Gates & OOS:** **0**

---

## 2. Rejection Taxonomy & Falsification Breakdown

Every evaluated candidate was strictly tested against causal next-bar execution, decomposed transaction costs (taker/maker fee schedule, bid-ask spread, execution slippage, borrow financing), and multi-stage adversarial stress.

| Rejection Category | Candidates Rejected | Causal Mechanism |
| :--- | :---: | :--- |
| `SUB_HURDLE_EDGE` | **8** | Failed causal or economic hurdle |
| `FRICTION_OVERWHELMED` | **4** | Failed causal or economic hurdle |
| `VAL_OVERFITTING` | **2** | Failed causal or economic hurdle |
| `ADVERSARIAL_FAILURE` | **2** | Failed causal or economic hurdle |
| `BLOCKED_EXTERNAL_DATA` | **9** | Unavailable external data streams |

---

## 3. Candidate Evaluation Ledger

| Candidate ID | Family | Symbol | DEV Net E[R] | VAL Net E[R] | OOS Net E[R] | Verdict | Rejection Reason |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :--- |
| `CAND-RELATIVE_VALUE-ETHUSDT-RV_Z1.5_T2.0` | `RELATIVE_VALUE` | ETH/USDT | -0.185R | +0.092R | -0.076R | 🔴 FALSIFIED | SUB_HURDLE_EDGE: DEV net expectancy (-0.185R) below hurdle (+0.10R) |
| `CAND-RELATIVE_VALUE-ETHUSDT-RV_Z2.0_T2.5` | `RELATIVE_VALUE` | ETH/USDT | -0.175R | +0.251R | -0.001R | 🔴 FALSIFIED | SUB_HURDLE_EDGE: DEV net expectancy (-0.175R) below hurdle (+0.10R) |
| `CAND-RELATIVE_VALUE-SOLUSDT-RV_Z1.5_T2.0` | `RELATIVE_VALUE` | SOL/USDT | -0.231R | -0.163R | -0.033R | 🔴 FALSIFIED | SUB_HURDLE_EDGE: DEV net expectancy (-0.231R) below hurdle (+0.10R) |
| `CAND-RELATIVE_VALUE-SOLUSDT-RV_Z2.0_T2.5` | `RELATIVE_VALUE` | SOL/USDT | -0.148R | -0.132R | -0.139R | 🔴 FALSIFIED | SUB_HURDLE_EDGE: DEV net expectancy (-0.148R) below hurdle (+0.10R) |
| `CAND-DIRECTIONAL-BTCUSDT-TREND_CONT_FAST` | `DIRECTIONAL` | BTC/USDT | -0.036R | +0.015R | -0.008R | 🔴 FALSIFIED | FRICTION_OVERWHELMED: Gross profit wiped out by decomposed taker fees & slippage |
| `CAND-DIRECTIONAL-BTCUSDT-TREND_CONT_SLOW` | `DIRECTIONAL` | BTC/USDT | +0.003R | -0.097R | -0.004R | 🔴 FALSIFIED | SUB_HURDLE_EDGE: DEV net expectancy (0.003R) below hurdle (+0.10R) |
| `CAND-DIRECTIONAL-ETHUSDT-TREND_CONT_FAST` | `DIRECTIONAL` | ETH/USDT | -0.022R | -0.214R | -0.104R | 🔴 FALSIFIED | FRICTION_OVERWHELMED: Gross profit wiped out by decomposed taker fees & slippage |
| `CAND-DIRECTIONAL-ETHUSDT-TREND_CONT_SLOW` | `DIRECTIONAL` | ETH/USDT | +0.115R | -0.101R | -0.070R | 🔴 FALSIFIED | VAL_OVERFITTING: Validation net expectancy (-0.101R) non-positive |
| `CAND-DIRECTIONAL-SOLUSDT-TREND_CONT_FAST` | `DIRECTIONAL` | SOL/USDT | +0.086R | +0.071R | -0.043R | 🔴 FALSIFIED | SUB_HURDLE_EDGE: DEV net expectancy (0.086R) below hurdle (+0.10R) |
| `CAND-DIRECTIONAL-SOLUSDT-TREND_CONT_SLOW` | `DIRECTIONAL` | SOL/USDT | +0.193R | +0.174R | -0.043R | 🔴 FALSIFIED | ADVERSARIAL_FAILURE: FAIL_TOP5_WINDFALL_REMOVAL |
| `CAND-DIRECTIONAL-SOLUSDT-TREND_CONT_FAST` | `DIRECTIONAL` | SOL/USDT | +0.086R | +0.071R | -0.043R | 🔴 FALSIFIED | SUB_HURDLE_EDGE: DEV net expectancy (0.086R) below hurdle (+0.10R) |
| `CAND-DIRECTIONAL-SOLUSDT-TREND_CONT_SLOW` | `DIRECTIONAL` | SOL/USDT | +0.193R | +0.174R | -0.043R | 🔴 FALSIFIED | ADVERSARIAL_FAILURE: FAIL_TOP5_WINDFALL_REMOVAL |
| `CAND-DIRECTIONAL-ETHUSDT-TREND_CONT_FAST` | `DIRECTIONAL` | ETH/USDT | -0.022R | -0.214R | -0.104R | 🔴 FALSIFIED | FRICTION_OVERWHELMED: Gross profit wiped out by decomposed taker fees & slippage |
| `CAND-DIRECTIONAL-ETHUSDT-TREND_CONT_SLOW` | `DIRECTIONAL` | ETH/USDT | +0.115R | -0.101R | -0.070R | 🔴 FALSIFIED | VAL_OVERFITTING: Validation net expectancy (-0.101R) non-positive |
| `CAND-DIRECTIONAL-BTCUSDT-TREND_CONT_FAST` | `DIRECTIONAL` | BTC/USDT | -0.036R | +0.015R | -0.008R | 🔴 FALSIFIED | FRICTION_OVERWHELMED: Gross profit wiped out by decomposed taker fees & slippage |
| `CAND-DIRECTIONAL-BTCUSDT-TREND_CONT_SLOW` | `DIRECTIONAL` | BTC/USDT | +0.003R | -0.097R | -0.004R | 🔴 FALSIFIED | SUB_HURDLE_EDGE: DEV net expectancy (0.003R) below hurdle (+0.10R) |
| `CAND-HYP-OPP-CARRY-BTCUSDT` | `CARRY` | BTC/USDT | N/A | N/A | N/A | 🟡 BLOCKED | Required historical datasets (L2 book / funding / liquidations) not warehoused locally |
| `CAND-HYP-OPP-CARRY-ETHUSDT` | `CARRY` | ETH/USDT | N/A | N/A | N/A | 🟡 BLOCKED | Required historical datasets (L2 book / funding / liquidations) not warehoused locally |
| `CAND-HYP-OPP-CARRY-SOLUSDT` | `CARRY` | SOL/USDT | N/A | N/A | N/A | 🟡 BLOCKED | Required historical datasets (L2 book / funding / liquidations) not warehoused locally |
| `CAND-HYP-OPP-LIQ-BTCUSDT` | `EVENT_DRIVEN` | BTC/USDT | N/A | N/A | N/A | 🟡 BLOCKED | Required historical datasets (L2 book / funding / liquidations) not warehoused locally |
| `CAND-HYP-OPP-LIQ-ETHUSDT` | `EVENT_DRIVEN` | ETH/USDT | N/A | N/A | N/A | 🟡 BLOCKED | Required historical datasets (L2 book / funding / liquidations) not warehoused locally |
| `CAND-HYP-OPP-LIQ-SOLUSDT` | `EVENT_DRIVEN` | SOL/USDT | N/A | N/A | N/A | 🟡 BLOCKED | Required historical datasets (L2 book / funding / liquidations) not warehoused locally |
| `CAND-HYP-OPP-MICRO-BTCUSDT` | `MICROSTRUCTURE` | BTC/USDT | N/A | N/A | N/A | 🟡 BLOCKED | Required historical datasets (L2 book / funding / liquidations) not warehoused locally |
| `CAND-HYP-OPP-MICRO-ETHUSDT` | `MICROSTRUCTURE` | ETH/USDT | N/A | N/A | N/A | 🟡 BLOCKED | Required historical datasets (L2 book / funding / liquidations) not warehoused locally |
| `CAND-HYP-OPP-MICRO-SOLUSDT` | `MICROSTRUCTURE` | SOL/USDT | N/A | N/A | N/A | 🟡 BLOCKED | Required historical datasets (L2 book / funding / liquidations) not warehoused locally |

---

## 4. Ranked Next Research Queue (Governed by Research Governor)

Research priority is dynamically computed using multi-factor utility (Magnitude 35%, Data Readiness 25%, Portfolio Diversification 20%, Novelty 10%, Computational Cost -10%).

| Priority Rank | Hypothesis ID | Target Family | Asset | Priority Score | Scoring Components |
| :---: | :--- | :---: | :---: | :---: | :--- |
| **#1** | `HYP-OPP-RV-ETHBTC` | `RELATIVE_VALUE` | ETH/USDT | `0.732` | magnitude: 0.72, data_readiness: 1.0, diversification: 1.0, novelty: 0.4, cost: 0.1 |
| **#2** | `HYP-OPP-RV-SOLBTC` | `RELATIVE_VALUE` | SOL/USDT | `0.732` | magnitude: 0.72, data_readiness: 1.0, diversification: 1.0, novelty: 0.4, cost: 0.1 |
| **#3** | `HYP-OPP-VOLSQZ-BTCUSDT` | `DIRECTIONAL` | BTC/USDT | `0.690` | magnitude: 1.0, data_readiness: 1.0, diversification: 0.3, novelty: 0.4, cost: 0.1 |
| **#4** | `HYP-OPP-VOLSQZ-ETHUSDT` | `DIRECTIONAL` | ETH/USDT | `0.690` | magnitude: 1.0, data_readiness: 1.0, diversification: 0.3, novelty: 0.4, cost: 0.1 |
| **#5** | `HYP-OPP-TREND-SOLUSDT` | `DIRECTIONAL` | SOL/USDT | `0.690` | magnitude: 1.0, data_readiness: 1.0, diversification: 0.3, novelty: 0.4, cost: 0.1 |
| **#6** | `HYP-OPP-VOLSQZ-SOLUSDT` | `DIRECTIONAL` | SOL/USDT | `0.690` | magnitude: 1.0, data_readiness: 1.0, diversification: 0.3, novelty: 0.4, cost: 0.1 |
| **#7** | `HYP-OPP-TREND-ETHUSDT` | `DIRECTIONAL` | ETH/USDT | `0.646` | magnitude: 0.873, data_readiness: 1.0, diversification: 0.3, novelty: 0.4, cost: 0.1 |
| **#8** | `HYP-OPP-TREND-BTCUSDT` | `DIRECTIONAL` | BTC/USDT | `0.575` | magnitude: 0.671, data_readiness: 1.0, diversification: 0.3, novelty: 0.4, cost: 0.1 |
| **#9** | `HYP-OPP-CARRY-BTCUSDT` | `CARRY` | BTC/USDT | `0.440` | magnitude: 0.6, data_readiness: 0.0, diversification: 1.0, novelty: 0.4, cost: 0.1 |
| **#10** | `HYP-OPP-CARRY-ETHUSDT` | `CARRY` | ETH/USDT | `0.440` | magnitude: 0.6, data_readiness: 0.0, diversification: 1.0, novelty: 0.4, cost: 0.1 |
| **#11** | `HYP-OPP-CARRY-SOLUSDT` | `CARRY` | SOL/USDT | `0.440` | magnitude: 0.6, data_readiness: 0.0, diversification: 1.0, novelty: 0.4, cost: 0.1 |
| **#12** | `HYP-OPP-LIQ-BTCUSDT` | `EVENT_DRIVEN` | BTC/USDT | `0.422` | magnitude: 0.55, data_readiness: 0.0, diversification: 1.0, novelty: 0.4, cost: 0.1 |
| **#13** | `HYP-OPP-LIQ-ETHUSDT` | `EVENT_DRIVEN` | ETH/USDT | `0.422` | magnitude: 0.55, data_readiness: 0.0, diversification: 1.0, novelty: 0.4, cost: 0.1 |
| **#14** | `HYP-OPP-LIQ-SOLUSDT` | `EVENT_DRIVEN` | SOL/USDT | `0.422` | magnitude: 0.55, data_readiness: 0.0, diversification: 1.0, novelty: 0.4, cost: 0.1 |
| **#15** | `HYP-OPP-MICRO-BTCUSDT` | `MICROSTRUCTURE` | BTC/USDT | `0.385` | magnitude: 0.5, data_readiness: 0.0, diversification: 1.0, novelty: 0.4, cost: 0.3 |
| **#16** | `HYP-OPP-MICRO-ETHUSDT` | `MICROSTRUCTURE` | ETH/USDT | `0.385` | magnitude: 0.5, data_readiness: 0.0, diversification: 1.0, novelty: 0.4, cost: 0.3 |
| **#17** | `HYP-OPP-MICRO-SOLUSDT` | `MICROSTRUCTURE` | SOL/USDT | `0.385` | magnitude: 0.5, data_readiness: 0.0, diversification: 1.0, novelty: 0.4, cost: 0.3 |

---

## 5. Production Capital Gate Enforcement
- **Live Capital:** `$0.00`
- **Order Submission:** `DISABLED`
- **Status:** Fail-Closed Capital Firewall actively prevents live order routing.
