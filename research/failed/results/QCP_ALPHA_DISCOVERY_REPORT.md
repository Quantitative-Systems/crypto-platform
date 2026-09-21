# QCP Alpha Discovery & Empirical Validation Report

**Audit Date:** 2026-09-18T09:51:46.084463+00:00  
**Architecture:** Quantitative Crypto Platform (QCP) Autonomous Research Discovery Lab  
**Live Capital Status:** **$0.00 (LOCKED)**  
**Economic Truth Verdict:** `NO_NEW_ECONOMIC_EDGE_VALIDATED`

---

## 1. Executive Scientific Summary

The explicit mandate of this phase is: **FIND, TEST, FALSIFY, AND VALIDATE REAL ECONOMIC EDGES.**  
In accordance with Directive Section 19:
> *If no new alpha survives: REPORT `NO_NEW_ECONOMIC_EDGE_VALIDATED`. That is a successful scientific outcome.*

* **Certified Warehouse Datasets Admitted:** 80
* **Hypotheses Formulated:** 61
* **Strategy Variants Tested:** 116
* **Bonferroni Hurdle Rate:** `+0.2475R`
* **Candidates Falsified / Rejected:** 116
* **Candidates Blocked by Data Absence:** 32
* **Candidates Surviving All Gates & OOS:** **0**

---

## 2. Rejection Taxonomy & Falsification Breakdown

Every evaluated candidate was strictly tested against causal next-bar execution, decomposed transaction costs (taker/maker fee schedule, bid-ask spread, execution slippage, borrow financing), and multi-stage adversarial stress.

| Rejection Category | Candidates Rejected | Causal Mechanism |
| :--- | :---: | :--- |
| `Insufficient trades (81 < 100)` | **6** | Failed causal or economic hurdle |
| `Insufficient trades (84 < 100)` | **3** | Failed causal or economic hurdle |
| `Insufficient trades (0 < 100)` | **29** | Failed causal or economic hurdle |
| `VAL_OVERFITTING` | **12** | Failed causal or economic hurdle |
| `Insufficient trades (74 < 100)` | **3** | Failed causal or economic hurdle |
| `Insufficient trades (89 < 100)` | **3** | Failed causal or economic hurdle |
| `FRICTION_OVERWHELMED` | **3** | Failed causal or economic hurdle |
| `Insufficient trades (96 < 100)` | **6** | Failed causal or economic hurdle |
| `Insufficient trades (95 < 100)` | **5** | Failed causal or economic hurdle |
| `SUB_HURDLE_EDGE` | **28** | Failed causal or economic hurdle |
| `Insufficient trades (97 < 100)` | **3** | Failed causal or economic hurdle |
| `Insufficient trades (80 < 100)` | **3** | Failed causal or economic hurdle |
| `Insufficient trades (82 < 100)` | **3** | Failed causal or economic hurdle |
| `Insufficient trades (93 < 100)` | **3** | Failed causal or economic hurdle |
| `Insufficient trades (90 < 100)` | **3** | Failed causal or economic hurdle |
| `Insufficient trades (91 < 100)` | **3** | Failed causal or economic hurdle |
| `BLOCKED_EXTERNAL_DATA` | **32** | Unavailable external data streams |

---

## 3. Candidate Evaluation Ledger

| Candidate ID | Family | Symbol | DEV Net E[R] | VAL Net E[R] | OOS Net E[R] | Verdict | Rejection Reason |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :--- |
| `CAND-RELATIVE_VALUE-ADAUSDT-TRND-01_SET2` | `RELATIVE_VALUE` | ADA/USDT | -0.249R | -0.873R | -0.060R | 🔴 FALSIFIED | Insufficient trades (81 < 100) |
| `CAND-RELATIVE_VALUE-ADAUSDT-TRND-01_SET3` | `RELATIVE_VALUE` | ADA/USDT | -0.092R | -0.355R | +0.073R | 🔴 FALSIFIED | Insufficient trades (84 < 100) |
| `CAND-RELATIVE_VALUE-ADAUSDT-VOL-01_SET3` | `RELATIVE_VALUE` | ADA/USDT | +0.000R | +0.000R | +0.000R | 🔴 FALSIFIED | Insufficient trades (0 < 100) |
| `CAND-RELATIVE_VALUE-ADAUSDT-TRND-02_SET4` | `RELATIVE_VALUE` | ADA/USDT | +0.320R | -0.612R | +0.035R | 🔴 FALSIFIED | VAL_OVERFITTING: Validation net expectancy (-0.612R) non-positive |
| `CAND-RELATIVE_VALUE-AVAXUSDT-TRND-01_SET2` | `RELATIVE_VALUE` | AVAX/USDT | +0.317R | +0.314R | +0.047R | 🔴 FALSIFIED | Insufficient trades (74 < 100) |
| `CAND-RELATIVE_VALUE-AVAXUSDT-TRND-01_SET3` | `RELATIVE_VALUE` | AVAX/USDT | +0.024R | +0.106R | +0.021R | 🔴 FALSIFIED | Insufficient trades (89 < 100) |
| `CAND-RELATIVE_VALUE-AVAXUSDT-VOL-01_SET3` | `RELATIVE_VALUE` | AVAX/USDT | +0.000R | +0.000R | +0.000R | 🔴 FALSIFIED | Insufficient trades (0 < 100) |
| `CAND-RELATIVE_VALUE-AVAXUSDT-TRND-02_SET4` | `RELATIVE_VALUE` | AVAX/USDT | -0.009R | -0.325R | +0.158R | 🔴 FALSIFIED | FRICTION_OVERWHELMED: Gross profit wiped out by decomposed taker fees & slippage |
| `CAND-RELATIVE_VALUE-BNBUSDT-TRND-01_SET2` | `RELATIVE_VALUE` | BNB/USDT | +0.012R | +0.183R | +0.172R | 🔴 FALSIFIED | Insufficient trades (96 < 100) |
| `CAND-RELATIVE_VALUE-BNBUSDT-TRND-01_SET3` | `RELATIVE_VALUE` | BNB/USDT | +0.316R | -0.248R | +0.208R | 🔴 FALSIFIED | Insufficient trades (95 < 100) |
| `CAND-RELATIVE_VALUE-BNBUSDT-VOL-01_SET3` | `RELATIVE_VALUE` | BNB/USDT | +0.000R | +0.000R | +0.000R | 🔴 FALSIFIED | Insufficient trades (0 < 100) |
| `CAND-RELATIVE_VALUE-BNBUSDT-TRND-02_SET4` | `RELATIVE_VALUE` | BNB/USDT | -0.110R | +0.083R | -0.120R | 🔴 FALSIFIED | SUB_HURDLE_EDGE: DEV net expectancy (-0.110R) below hurdle (+0.10R) |
| `CAND-RELATIVE_VALUE-DOGEUSDT-TRND-01_SET2` | `RELATIVE_VALUE` | DOGE/USDT | +0.237R | -0.564R | +0.016R | 🔴 FALSIFIED | Insufficient trades (97 < 100) |
| `CAND-RELATIVE_VALUE-DOGEUSDT-TRND-01_SET3` | `RELATIVE_VALUE` | DOGE/USDT | +0.067R | -0.600R | +0.195R | 🔴 FALSIFIED | SUB_HURDLE_EDGE: DEV net expectancy (0.067R) below hurdle (+0.10R) |
| `CAND-RELATIVE_VALUE-DOGEUSDT-VOL-01_SET3` | `RELATIVE_VALUE` | DOGE/USDT | +0.000R | +0.000R | +0.000R | 🔴 FALSIFIED | Insufficient trades (0 < 100) |
| `CAND-RELATIVE_VALUE-DOGEUSDT-TRND-02_SET4` | `RELATIVE_VALUE` | DOGE/USDT | +0.051R | -0.186R | +0.183R | 🔴 FALSIFIED | SUB_HURDLE_EDGE: DEV net expectancy (0.051R) below hurdle (+0.10R) |
| `CAND-RELATIVE_VALUE-ETHUSDT-TRND-01_SET2` | `RELATIVE_VALUE` | ETH/USDT | +0.320R | -0.063R | +0.236R | 🔴 FALSIFIED | Insufficient trades (80 < 100) |
| `CAND-RELATIVE_VALUE-ETHUSDT-TRND-01_SET3` | `RELATIVE_VALUE` | ETH/USDT | +0.500R | -0.255R | -0.091R | 🔴 FALSIFIED | Insufficient trades (82 < 100) |
| `CAND-RELATIVE_VALUE-ETHUSDT-VOL-01_SET3` | `RELATIVE_VALUE` | ETH/USDT | +0.000R | +0.000R | +0.000R | 🔴 FALSIFIED | Insufficient trades (0 < 100) |
| `CAND-RELATIVE_VALUE-ETHUSDT-TRND-02_SET4` | `RELATIVE_VALUE` | ETH/USDT | -0.043R | -0.149R | -0.056R | 🔴 FALSIFIED | SUB_HURDLE_EDGE: DEV net expectancy (-0.043R) below hurdle (+0.10R) |
| `CAND-RELATIVE_VALUE-LINKUSDT-TRND-01_SET2` | `RELATIVE_VALUE` | LINK/USDT | +0.036R | -0.355R | -0.204R | 🔴 FALSIFIED | SUB_HURDLE_EDGE: DEV net expectancy (0.036R) below hurdle (+0.10R) |
| `CAND-RELATIVE_VALUE-LINKUSDT-TRND-01_SET3` | `RELATIVE_VALUE` | LINK/USDT | -0.161R | -0.240R | -0.179R | 🔴 FALSIFIED | Insufficient trades (93 < 100) |
| `CAND-RELATIVE_VALUE-LINKUSDT-VOL-01_SET3` | `RELATIVE_VALUE` | LINK/USDT | +0.000R | +0.000R | +0.000R | 🔴 FALSIFIED | Insufficient trades (0 < 100) |
| `CAND-RELATIVE_VALUE-LINKUSDT-TRND-02_SET4` | `RELATIVE_VALUE` | LINK/USDT | -0.385R | -0.192R | -0.047R | 🔴 FALSIFIED | SUB_HURDLE_EDGE: DEV net expectancy (-0.385R) below hurdle (+0.10R) |
| `CAND-RELATIVE_VALUE-LTCUSDT-TRND-01_SET2` | `RELATIVE_VALUE` | LTC/USDT | -0.096R | +0.158R | -0.332R | 🔴 FALSIFIED | Insufficient trades (90 < 100) |
| `CAND-RELATIVE_VALUE-LTCUSDT-TRND-01_SET3` | `RELATIVE_VALUE` | LTC/USDT | -0.584R | +0.146R | -0.329R | 🔴 FALSIFIED | Insufficient trades (91 < 100) |
| `CAND-RELATIVE_VALUE-LTCUSDT-VOL-01_SET3` | `RELATIVE_VALUE` | LTC/USDT | +0.000R | +0.000R | +0.000R | 🔴 FALSIFIED | Insufficient trades (0 < 100) |
| `CAND-RELATIVE_VALUE-LTCUSDT-TRND-02_SET4` | `RELATIVE_VALUE` | LTC/USDT | -0.290R | +0.104R | +0.254R | 🔴 FALSIFIED | Insufficient trades (81 < 100) |
| `CAND-RELATIVE_VALUE-SOLUSDT-TRND-01_SET2` | `RELATIVE_VALUE` | SOL/USDT | -0.146R | -0.171R | -0.325R | 🔴 FALSIFIED | Insufficient trades (96 < 100) |
| `CAND-RELATIVE_VALUE-SOLUSDT-TRND-01_SET3` | `RELATIVE_VALUE` | SOL/USDT | -0.043R | -0.157R | -0.123R | 🔴 FALSIFIED | SUB_HURDLE_EDGE: DEV net expectancy (-0.043R) below hurdle (+0.10R) |
| `CAND-RELATIVE_VALUE-SOLUSDT-VOL-01_SET3` | `RELATIVE_VALUE` | SOL/USDT | +0.000R | +0.000R | +0.000R | 🔴 FALSIFIED | Insufficient trades (0 < 100) |
| `CAND-RELATIVE_VALUE-SOLUSDT-TRND-02_SET4` | `RELATIVE_VALUE` | SOL/USDT | +0.123R | -0.540R | -0.163R | 🔴 FALSIFIED | VAL_OVERFITTING: Validation net expectancy (-0.540R) non-positive |
| `CAND-RELATIVE_VALUE-XRPUSDT-TRND-01_SET2` | `RELATIVE_VALUE` | XRP/USDT | +0.302R | -0.836R | -0.343R | 🔴 FALSIFIED | VAL_OVERFITTING: Validation net expectancy (-0.836R) non-positive |
| `CAND-RELATIVE_VALUE-XRPUSDT-TRND-01_SET3` | `RELATIVE_VALUE` | XRP/USDT | +0.148R | -0.803R | -0.232R | 🔴 FALSIFIED | VAL_OVERFITTING: Validation net expectancy (-0.803R) non-positive |
| `CAND-RELATIVE_VALUE-XRPUSDT-VOL-01_SET3` | `RELATIVE_VALUE` | XRP/USDT | +0.000R | +0.000R | +0.000R | 🔴 FALSIFIED | Insufficient trades (0 < 100) |
| `CAND-RELATIVE_VALUE-XRPUSDT-TRND-02_SET4` | `RELATIVE_VALUE` | XRP/USDT | -0.189R | -0.060R | -0.080R | 🔴 FALSIFIED | SUB_HURDLE_EDGE: DEV net expectancy (-0.189R) below hurdle (+0.10R) |
| `CAND-DIRECTIONAL-ADAUSDT-TRND-01_SET2` | `DIRECTIONAL` | ADA/USDT | -0.249R | -0.873R | -0.060R | 🔴 FALSIFIED | Insufficient trades (81 < 100) |
| `CAND-DIRECTIONAL-ADAUSDT-TRND-01_SET3` | `DIRECTIONAL` | ADA/USDT | -0.092R | -0.355R | +0.073R | 🔴 FALSIFIED | Insufficient trades (84 < 100) |
| `CAND-DIRECTIONAL-ADAUSDT-VOL-01_SET3` | `DIRECTIONAL` | ADA/USDT | +0.000R | +0.000R | +0.000R | 🔴 FALSIFIED | Insufficient trades (0 < 100) |
| `CAND-DIRECTIONAL-ADAUSDT-TRND-02_SET4` | `DIRECTIONAL` | ADA/USDT | +0.320R | -0.612R | +0.035R | 🔴 FALSIFIED | VAL_OVERFITTING: Validation net expectancy (-0.612R) non-positive |
| `CAND-DIRECTIONAL-AVAXUSDT-TRND-01_SET2` | `DIRECTIONAL` | AVAX/USDT | +0.317R | +0.314R | +0.047R | 🔴 FALSIFIED | Insufficient trades (74 < 100) |
| `CAND-DIRECTIONAL-AVAXUSDT-TRND-01_SET3` | `DIRECTIONAL` | AVAX/USDT | +0.024R | +0.106R | +0.021R | 🔴 FALSIFIED | Insufficient trades (89 < 100) |
| `CAND-DIRECTIONAL-AVAXUSDT-VOL-01_SET3` | `DIRECTIONAL` | AVAX/USDT | +0.000R | +0.000R | +0.000R | 🔴 FALSIFIED | Insufficient trades (0 < 100) |
| `CAND-DIRECTIONAL-AVAXUSDT-TRND-02_SET4` | `DIRECTIONAL` | AVAX/USDT | -0.009R | -0.325R | +0.158R | 🔴 FALSIFIED | FRICTION_OVERWHELMED: Gross profit wiped out by decomposed taker fees & slippage |
| `CAND-DIRECTIONAL-AVAXUSDT-TRND-01_SET2` | `DIRECTIONAL` | AVAX/USDT | +0.317R | +0.314R | +0.047R | 🔴 FALSIFIED | Insufficient trades (74 < 100) |
| `CAND-DIRECTIONAL-AVAXUSDT-TRND-01_SET3` | `DIRECTIONAL` | AVAX/USDT | +0.024R | +0.106R | +0.021R | 🔴 FALSIFIED | Insufficient trades (89 < 100) |
| `CAND-DIRECTIONAL-AVAXUSDT-VOL-01_SET3` | `DIRECTIONAL` | AVAX/USDT | +0.000R | +0.000R | +0.000R | 🔴 FALSIFIED | Insufficient trades (0 < 100) |
| `CAND-DIRECTIONAL-AVAXUSDT-TRND-02_SET4` | `DIRECTIONAL` | AVAX/USDT | -0.009R | -0.325R | +0.158R | 🔴 FALSIFIED | FRICTION_OVERWHELMED: Gross profit wiped out by decomposed taker fees & slippage |
| `CAND-DIRECTIONAL-BNBUSDT-TRND-01_SET2` | `DIRECTIONAL` | BNB/USDT | +0.012R | +0.183R | +0.172R | 🔴 FALSIFIED | Insufficient trades (96 < 100) |
| `CAND-DIRECTIONAL-BNBUSDT-TRND-01_SET3` | `DIRECTIONAL` | BNB/USDT | +0.316R | -0.248R | +0.208R | 🔴 FALSIFIED | Insufficient trades (95 < 100) |
| `CAND-DIRECTIONAL-BNBUSDT-VOL-01_SET3` | `DIRECTIONAL` | BNB/USDT | +0.000R | +0.000R | +0.000R | 🔴 FALSIFIED | Insufficient trades (0 < 100) |
| `CAND-DIRECTIONAL-BNBUSDT-TRND-02_SET4` | `DIRECTIONAL` | BNB/USDT | -0.110R | +0.083R | -0.120R | 🔴 FALSIFIED | SUB_HURDLE_EDGE: DEV net expectancy (-0.110R) below hurdle (+0.10R) |
| `CAND-DIRECTIONAL-BTCUSDT-TRND-01_SET2` | `DIRECTIONAL` | BTC/USDT | +0.005R | +0.584R | -0.121R | 🔴 FALSIFIED | Insufficient trades (95 < 100) |
| `CAND-DIRECTIONAL-BTCUSDT-TRND-01_SET3` | `DIRECTIONAL` | BTC/USDT | -0.200R | +0.437R | -0.154R | 🔴 FALSIFIED | SUB_HURDLE_EDGE: DEV net expectancy (-0.200R) below hurdle (+0.10R) |
| `CAND-DIRECTIONAL-BTCUSDT-VOL-01_SET3` | `DIRECTIONAL` | BTC/USDT | +0.000R | +0.000R | +0.000R | 🔴 FALSIFIED | Insufficient trades (0 < 100) |
| `CAND-DIRECTIONAL-BTCUSDT-TRND-02_SET4` | `DIRECTIONAL` | BTC/USDT | -0.109R | -0.160R | -0.166R | 🔴 FALSIFIED | SUB_HURDLE_EDGE: DEV net expectancy (-0.109R) below hurdle (+0.10R) |
| `CAND-DIRECTIONAL-DOGEUSDT-TRND-01_SET2` | `DIRECTIONAL` | DOGE/USDT | +0.237R | -0.564R | +0.016R | 🔴 FALSIFIED | Insufficient trades (97 < 100) |
| `CAND-DIRECTIONAL-DOGEUSDT-TRND-01_SET3` | `DIRECTIONAL` | DOGE/USDT | +0.067R | -0.600R | +0.195R | 🔴 FALSIFIED | SUB_HURDLE_EDGE: DEV net expectancy (0.067R) below hurdle (+0.10R) |
| `CAND-DIRECTIONAL-DOGEUSDT-VOL-01_SET3` | `DIRECTIONAL` | DOGE/USDT | +0.000R | +0.000R | +0.000R | 🔴 FALSIFIED | Insufficient trades (0 < 100) |
| `CAND-DIRECTIONAL-DOGEUSDT-TRND-02_SET4` | `DIRECTIONAL` | DOGE/USDT | +0.051R | -0.186R | +0.183R | 🔴 FALSIFIED | SUB_HURDLE_EDGE: DEV net expectancy (0.051R) below hurdle (+0.10R) |
| `CAND-DIRECTIONAL-DOGEUSDT-TRND-01_SET2` | `DIRECTIONAL` | DOGE/USDT | +0.237R | -0.564R | +0.016R | 🔴 FALSIFIED | Insufficient trades (97 < 100) |
| `CAND-DIRECTIONAL-DOGEUSDT-TRND-01_SET3` | `DIRECTIONAL` | DOGE/USDT | +0.067R | -0.600R | +0.195R | 🔴 FALSIFIED | SUB_HURDLE_EDGE: DEV net expectancy (0.067R) below hurdle (+0.10R) |
| `CAND-DIRECTIONAL-DOGEUSDT-VOL-01_SET3` | `DIRECTIONAL` | DOGE/USDT | +0.000R | +0.000R | +0.000R | 🔴 FALSIFIED | Insufficient trades (0 < 100) |
| `CAND-DIRECTIONAL-DOGEUSDT-TRND-02_SET4` | `DIRECTIONAL` | DOGE/USDT | +0.051R | -0.186R | +0.183R | 🔴 FALSIFIED | SUB_HURDLE_EDGE: DEV net expectancy (0.051R) below hurdle (+0.10R) |
| `CAND-DIRECTIONAL-ETHUSDT-TRND-01_SET2` | `DIRECTIONAL` | ETH/USDT | +0.320R | -0.063R | +0.236R | 🔴 FALSIFIED | Insufficient trades (80 < 100) |
| `CAND-DIRECTIONAL-ETHUSDT-TRND-01_SET3` | `DIRECTIONAL` | ETH/USDT | +0.500R | -0.255R | -0.091R | 🔴 FALSIFIED | Insufficient trades (82 < 100) |
| `CAND-DIRECTIONAL-ETHUSDT-VOL-01_SET3` | `DIRECTIONAL` | ETH/USDT | +0.000R | +0.000R | +0.000R | 🔴 FALSIFIED | Insufficient trades (0 < 100) |
| `CAND-DIRECTIONAL-ETHUSDT-TRND-02_SET4` | `DIRECTIONAL` | ETH/USDT | -0.043R | -0.149R | -0.056R | 🔴 FALSIFIED | SUB_HURDLE_EDGE: DEV net expectancy (-0.043R) below hurdle (+0.10R) |
| `CAND-DIRECTIONAL-LINKUSDT-TRND-01_SET2` | `DIRECTIONAL` | LINK/USDT | +0.036R | -0.355R | -0.204R | 🔴 FALSIFIED | SUB_HURDLE_EDGE: DEV net expectancy (0.036R) below hurdle (+0.10R) |
| `CAND-DIRECTIONAL-LINKUSDT-TRND-01_SET3` | `DIRECTIONAL` | LINK/USDT | -0.161R | -0.240R | -0.179R | 🔴 FALSIFIED | Insufficient trades (93 < 100) |
| `CAND-DIRECTIONAL-LINKUSDT-VOL-01_SET3` | `DIRECTIONAL` | LINK/USDT | +0.000R | +0.000R | +0.000R | 🔴 FALSIFIED | Insufficient trades (0 < 100) |
| `CAND-DIRECTIONAL-LINKUSDT-TRND-02_SET4` | `DIRECTIONAL` | LINK/USDT | -0.385R | -0.192R | -0.047R | 🔴 FALSIFIED | SUB_HURDLE_EDGE: DEV net expectancy (-0.385R) below hurdle (+0.10R) |
| `CAND-DIRECTIONAL-LINKUSDT-TRND-01_SET2` | `DIRECTIONAL` | LINK/USDT | +0.036R | -0.355R | -0.204R | 🔴 FALSIFIED | SUB_HURDLE_EDGE: DEV net expectancy (0.036R) below hurdle (+0.10R) |
| `CAND-DIRECTIONAL-LINKUSDT-TRND-01_SET3` | `DIRECTIONAL` | LINK/USDT | -0.161R | -0.240R | -0.179R | 🔴 FALSIFIED | Insufficient trades (93 < 100) |
| `CAND-DIRECTIONAL-LINKUSDT-VOL-01_SET3` | `DIRECTIONAL` | LINK/USDT | +0.000R | +0.000R | +0.000R | 🔴 FALSIFIED | Insufficient trades (0 < 100) |
| `CAND-DIRECTIONAL-LINKUSDT-TRND-02_SET4` | `DIRECTIONAL` | LINK/USDT | -0.385R | -0.192R | -0.047R | 🔴 FALSIFIED | SUB_HURDLE_EDGE: DEV net expectancy (-0.385R) below hurdle (+0.10R) |
| `CAND-DIRECTIONAL-LTCUSDT-TRND-01_SET2` | `DIRECTIONAL` | LTC/USDT | -0.096R | +0.158R | -0.332R | 🔴 FALSIFIED | Insufficient trades (90 < 100) |
| `CAND-DIRECTIONAL-LTCUSDT-TRND-01_SET3` | `DIRECTIONAL` | LTC/USDT | -0.584R | +0.146R | -0.329R | 🔴 FALSIFIED | Insufficient trades (91 < 100) |
| `CAND-DIRECTIONAL-LTCUSDT-VOL-01_SET3` | `DIRECTIONAL` | LTC/USDT | +0.000R | +0.000R | +0.000R | 🔴 FALSIFIED | Insufficient trades (0 < 100) |
| `CAND-DIRECTIONAL-LTCUSDT-TRND-02_SET4` | `DIRECTIONAL` | LTC/USDT | -0.290R | +0.104R | +0.254R | 🔴 FALSIFIED | Insufficient trades (81 < 100) |
| `CAND-DIRECTIONAL-SOLUSDT-TRND-01_SET2` | `DIRECTIONAL` | SOL/USDT | -0.146R | -0.171R | -0.325R | 🔴 FALSIFIED | Insufficient trades (96 < 100) |
| `CAND-DIRECTIONAL-SOLUSDT-TRND-01_SET3` | `DIRECTIONAL` | SOL/USDT | -0.043R | -0.157R | -0.123R | 🔴 FALSIFIED | SUB_HURDLE_EDGE: DEV net expectancy (-0.043R) below hurdle (+0.10R) |
| `CAND-DIRECTIONAL-SOLUSDT-VOL-01_SET3` | `DIRECTIONAL` | SOL/USDT | +0.000R | +0.000R | +0.000R | 🔴 FALSIFIED | Insufficient trades (0 < 100) |
| `CAND-DIRECTIONAL-SOLUSDT-TRND-02_SET4` | `DIRECTIONAL` | SOL/USDT | +0.123R | -0.540R | -0.163R | 🔴 FALSIFIED | VAL_OVERFITTING: Validation net expectancy (-0.540R) non-positive |
| `CAND-DIRECTIONAL-SOLUSDT-TRND-01_SET2` | `DIRECTIONAL` | SOL/USDT | -0.146R | -0.171R | -0.325R | 🔴 FALSIFIED | Insufficient trades (96 < 100) |
| `CAND-DIRECTIONAL-SOLUSDT-TRND-01_SET3` | `DIRECTIONAL` | SOL/USDT | -0.043R | -0.157R | -0.123R | 🔴 FALSIFIED | SUB_HURDLE_EDGE: DEV net expectancy (-0.043R) below hurdle (+0.10R) |
| `CAND-DIRECTIONAL-SOLUSDT-VOL-01_SET3` | `DIRECTIONAL` | SOL/USDT | +0.000R | +0.000R | +0.000R | 🔴 FALSIFIED | Insufficient trades (0 < 100) |
| `CAND-DIRECTIONAL-SOLUSDT-TRND-02_SET4` | `DIRECTIONAL` | SOL/USDT | +0.123R | -0.540R | -0.163R | 🔴 FALSIFIED | VAL_OVERFITTING: Validation net expectancy (-0.540R) non-positive |
| `CAND-DIRECTIONAL-XRPUSDT-TRND-01_SET2` | `DIRECTIONAL` | XRP/USDT | +0.302R | -0.836R | -0.343R | 🔴 FALSIFIED | VAL_OVERFITTING: Validation net expectancy (-0.836R) non-positive |
| `CAND-DIRECTIONAL-XRPUSDT-TRND-01_SET3` | `DIRECTIONAL` | XRP/USDT | +0.148R | -0.803R | -0.232R | 🔴 FALSIFIED | VAL_OVERFITTING: Validation net expectancy (-0.803R) non-positive |
| `CAND-DIRECTIONAL-XRPUSDT-VOL-01_SET3` | `DIRECTIONAL` | XRP/USDT | +0.000R | +0.000R | +0.000R | 🔴 FALSIFIED | Insufficient trades (0 < 100) |
| `CAND-DIRECTIONAL-XRPUSDT-TRND-02_SET4` | `DIRECTIONAL` | XRP/USDT | -0.189R | -0.060R | -0.080R | 🔴 FALSIFIED | SUB_HURDLE_EDGE: DEV net expectancy (-0.189R) below hurdle (+0.10R) |
| `CAND-DIRECTIONAL-ADAUSDT-TRND-01_SET2` | `DIRECTIONAL` | ADA/USDT | -0.249R | -0.873R | -0.060R | 🔴 FALSIFIED | Insufficient trades (81 < 100) |
| `CAND-DIRECTIONAL-ADAUSDT-TRND-01_SET3` | `DIRECTIONAL` | ADA/USDT | -0.092R | -0.355R | +0.073R | 🔴 FALSIFIED | Insufficient trades (84 < 100) |
| `CAND-DIRECTIONAL-ADAUSDT-VOL-01_SET3` | `DIRECTIONAL` | ADA/USDT | +0.000R | +0.000R | +0.000R | 🔴 FALSIFIED | Insufficient trades (0 < 100) |
| `CAND-DIRECTIONAL-ADAUSDT-TRND-02_SET4` | `DIRECTIONAL` | ADA/USDT | +0.320R | -0.612R | +0.035R | 🔴 FALSIFIED | VAL_OVERFITTING: Validation net expectancy (-0.612R) non-positive |
| `CAND-DIRECTIONAL-LTCUSDT-TRND-01_SET2` | `DIRECTIONAL` | LTC/USDT | -0.096R | +0.158R | -0.332R | 🔴 FALSIFIED | Insufficient trades (90 < 100) |
| `CAND-DIRECTIONAL-LTCUSDT-TRND-01_SET3` | `DIRECTIONAL` | LTC/USDT | -0.584R | +0.146R | -0.329R | 🔴 FALSIFIED | Insufficient trades (91 < 100) |
| `CAND-DIRECTIONAL-LTCUSDT-VOL-01_SET3` | `DIRECTIONAL` | LTC/USDT | +0.000R | +0.000R | +0.000R | 🔴 FALSIFIED | Insufficient trades (0 < 100) |
| `CAND-DIRECTIONAL-LTCUSDT-TRND-02_SET4` | `DIRECTIONAL` | LTC/USDT | -0.290R | +0.104R | +0.254R | 🔴 FALSIFIED | Insufficient trades (81 < 100) |
| `CAND-DIRECTIONAL-XRPUSDT-TRND-01_SET2` | `DIRECTIONAL` | XRP/USDT | +0.302R | -0.836R | -0.343R | 🔴 FALSIFIED | VAL_OVERFITTING: Validation net expectancy (-0.836R) non-positive |
| `CAND-DIRECTIONAL-XRPUSDT-TRND-01_SET3` | `DIRECTIONAL` | XRP/USDT | +0.148R | -0.803R | -0.232R | 🔴 FALSIFIED | VAL_OVERFITTING: Validation net expectancy (-0.803R) non-positive |
| `CAND-DIRECTIONAL-XRPUSDT-VOL-01_SET3` | `DIRECTIONAL` | XRP/USDT | +0.000R | +0.000R | +0.000R | 🔴 FALSIFIED | Insufficient trades (0 < 100) |
| `CAND-DIRECTIONAL-XRPUSDT-TRND-02_SET4` | `DIRECTIONAL` | XRP/USDT | -0.189R | -0.060R | -0.080R | 🔴 FALSIFIED | SUB_HURDLE_EDGE: DEV net expectancy (-0.189R) below hurdle (+0.10R) |
| `CAND-DIRECTIONAL-ETHUSDT-TRND-01_SET2` | `DIRECTIONAL` | ETH/USDT | +0.320R | -0.063R | +0.236R | 🔴 FALSIFIED | Insufficient trades (80 < 100) |
| `CAND-DIRECTIONAL-ETHUSDT-TRND-01_SET3` | `DIRECTIONAL` | ETH/USDT | +0.500R | -0.255R | -0.091R | 🔴 FALSIFIED | Insufficient trades (82 < 100) |
| `CAND-DIRECTIONAL-ETHUSDT-VOL-01_SET3` | `DIRECTIONAL` | ETH/USDT | +0.000R | +0.000R | +0.000R | 🔴 FALSIFIED | Insufficient trades (0 < 100) |
| `CAND-DIRECTIONAL-ETHUSDT-TRND-02_SET4` | `DIRECTIONAL` | ETH/USDT | -0.043R | -0.149R | -0.056R | 🔴 FALSIFIED | SUB_HURDLE_EDGE: DEV net expectancy (-0.043R) below hurdle (+0.10R) |
| `CAND-DIRECTIONAL-BNBUSDT-TRND-01_SET2` | `DIRECTIONAL` | BNB/USDT | +0.012R | +0.183R | +0.172R | 🔴 FALSIFIED | Insufficient trades (96 < 100) |
| `CAND-DIRECTIONAL-BNBUSDT-TRND-01_SET3` | `DIRECTIONAL` | BNB/USDT | +0.316R | -0.248R | +0.208R | 🔴 FALSIFIED | Insufficient trades (95 < 100) |
| `CAND-DIRECTIONAL-BNBUSDT-VOL-01_SET3` | `DIRECTIONAL` | BNB/USDT | +0.000R | +0.000R | +0.000R | 🔴 FALSIFIED | Insufficient trades (0 < 100) |
| `CAND-DIRECTIONAL-BNBUSDT-TRND-02_SET4` | `DIRECTIONAL` | BNB/USDT | -0.110R | +0.083R | -0.120R | 🔴 FALSIFIED | SUB_HURDLE_EDGE: DEV net expectancy (-0.110R) below hurdle (+0.10R) |
| `CAND-DIRECTIONAL-BTCUSDT-TRND-01_SET2` | `DIRECTIONAL` | BTC/USDT | +0.005R | +0.584R | -0.121R | 🔴 FALSIFIED | Insufficient trades (95 < 100) |
| `CAND-DIRECTIONAL-BTCUSDT-TRND-01_SET3` | `DIRECTIONAL` | BTC/USDT | -0.200R | +0.437R | -0.154R | 🔴 FALSIFIED | SUB_HURDLE_EDGE: DEV net expectancy (-0.200R) below hurdle (+0.10R) |
| `CAND-DIRECTIONAL-BTCUSDT-VOL-01_SET3` | `DIRECTIONAL` | BTC/USDT | +0.000R | +0.000R | +0.000R | 🔴 FALSIFIED | Insufficient trades (0 < 100) |
| `CAND-DIRECTIONAL-BTCUSDT-TRND-02_SET4` | `DIRECTIONAL` | BTC/USDT | -0.109R | -0.160R | -0.166R | 🔴 FALSIFIED | SUB_HURDLE_EDGE: DEV net expectancy (-0.109R) below hurdle (+0.10R) |
| `CAND-HYP-OPP-CARRY-ADAUSDT` | `CARRY` | ADA/USDT | N/A | N/A | N/A | 🟡 BLOCKED | Required historical datasets (L2 book / funding / liquidations) not warehoused locally |
| `CAND-HYP-OPP-CARRY-AVAXUSDT` | `CARRY` | AVAX/USDT | N/A | N/A | N/A | 🟡 BLOCKED | Required historical datasets (L2 book / funding / liquidations) not warehoused locally |
| `CAND-HYP-OPP-CARRY-BNBUSDT` | `CARRY` | BNB/USDT | N/A | N/A | N/A | 🟡 BLOCKED | Required historical datasets (L2 book / funding / liquidations) not warehoused locally |
| `CAND-HYP-OPP-CARRY-BTCUSDT` | `CARRY` | BTC/USDT | N/A | N/A | N/A | 🟡 BLOCKED | Required historical datasets (L2 book / funding / liquidations) not warehoused locally |
| `CAND-HYP-OPP-CARRY-DOGEUSDT` | `CARRY` | DOGE/USDT | N/A | N/A | N/A | 🟡 BLOCKED | Required historical datasets (L2 book / funding / liquidations) not warehoused locally |
| `CAND-HYP-OPP-CARRY-ETHUSDT` | `CARRY` | ETH/USDT | N/A | N/A | N/A | 🟡 BLOCKED | Required historical datasets (L2 book / funding / liquidations) not warehoused locally |
| `CAND-HYP-OPP-CARRY-LINKUSDT` | `CARRY` | LINK/USDT | N/A | N/A | N/A | 🟡 BLOCKED | Required historical datasets (L2 book / funding / liquidations) not warehoused locally |
| `CAND-HYP-OPP-CARRY-LTCUSDT` | `CARRY` | LTC/USDT | N/A | N/A | N/A | 🟡 BLOCKED | Required historical datasets (L2 book / funding / liquidations) not warehoused locally |
| `CAND-HYP-OPP-CARRY-SOLUSDT` | `CARRY` | SOL/USDT | N/A | N/A | N/A | 🟡 BLOCKED | Required historical datasets (L2 book / funding / liquidations) not warehoused locally |
| `CAND-HYP-OPP-CARRY-XRPUSDT` | `CARRY` | XRP/USDT | N/A | N/A | N/A | 🟡 BLOCKED | Required historical datasets (L2 book / funding / liquidations) not warehoused locally |
| `CAND-HYP-OPP-LIQ-ADAUSDT` | `EVENT_DRIVEN` | ADA/USDT | N/A | N/A | N/A | 🟡 BLOCKED | Required historical datasets (L2 book / funding / liquidations) not warehoused locally |
| `CAND-HYP-OPP-LIQ-AVAXUSDT` | `EVENT_DRIVEN` | AVAX/USDT | N/A | N/A | N/A | 🟡 BLOCKED | Required historical datasets (L2 book / funding / liquidations) not warehoused locally |
| `CAND-HYP-OPP-LIQ-BNBUSDT` | `EVENT_DRIVEN` | BNB/USDT | N/A | N/A | N/A | 🟡 BLOCKED | Required historical datasets (L2 book / funding / liquidations) not warehoused locally |
| `CAND-HYP-OPP-LIQ-BTCUSDT` | `EVENT_DRIVEN` | BTC/USDT | N/A | N/A | N/A | 🟡 BLOCKED | Required historical datasets (L2 book / funding / liquidations) not warehoused locally |
| `CAND-HYP-OPP-LIQ-DOGEUSDT` | `EVENT_DRIVEN` | DOGE/USDT | N/A | N/A | N/A | 🟡 BLOCKED | Required historical datasets (L2 book / funding / liquidations) not warehoused locally |
| `CAND-HYP-OPP-LIQ-ETHUSDT` | `EVENT_DRIVEN` | ETH/USDT | N/A | N/A | N/A | 🟡 BLOCKED | Required historical datasets (L2 book / funding / liquidations) not warehoused locally |
| `CAND-HYP-OPP-LIQ-LINKUSDT` | `EVENT_DRIVEN` | LINK/USDT | N/A | N/A | N/A | 🟡 BLOCKED | Required historical datasets (L2 book / funding / liquidations) not warehoused locally |
| `CAND-HYP-OPP-LIQ-LTCUSDT` | `EVENT_DRIVEN` | LTC/USDT | N/A | N/A | N/A | 🟡 BLOCKED | Required historical datasets (L2 book / funding / liquidations) not warehoused locally |
| `CAND-HYP-OPP-LIQ-SOLUSDT` | `EVENT_DRIVEN` | SOL/USDT | N/A | N/A | N/A | 🟡 BLOCKED | Required historical datasets (L2 book / funding / liquidations) not warehoused locally |
| `CAND-HYP-OPP-LIQ-XRPUSDT` | `EVENT_DRIVEN` | XRP/USDT | N/A | N/A | N/A | 🟡 BLOCKED | Required historical datasets (L2 book / funding / liquidations) not warehoused locally |
| `CAND-HYP-OPP-MICRO-ADAUSDT` | `MICROSTRUCTURE` | ADA/USDT | N/A | N/A | N/A | 🟡 BLOCKED | Required historical datasets (L2 book / funding / liquidations) not warehoused locally |
| `CAND-HYP-OPP-MICRO-AVAXUSDT` | `MICROSTRUCTURE` | AVAX/USDT | N/A | N/A | N/A | 🟡 BLOCKED | Required historical datasets (L2 book / funding / liquidations) not warehoused locally |
| `CAND-HYP-OPP-MICRO-BNBUSDT` | `MICROSTRUCTURE` | BNB/USDT | N/A | N/A | N/A | 🟡 BLOCKED | Required historical datasets (L2 book / funding / liquidations) not warehoused locally |
| `CAND-HYP-OPP-MICRO-BTCUSDT` | `MICROSTRUCTURE` | BTC/USDT | N/A | N/A | N/A | 🟡 BLOCKED | Required historical datasets (L2 book / funding / liquidations) not warehoused locally |
| `CAND-HYP-OPP-MICRO-DOGEUSDT` | `MICROSTRUCTURE` | DOGE/USDT | N/A | N/A | N/A | 🟡 BLOCKED | Required historical datasets (L2 book / funding / liquidations) not warehoused locally |
| `CAND-HYP-OPP-MICRO-ETHUSDT` | `MICROSTRUCTURE` | ETH/USDT | N/A | N/A | N/A | 🟡 BLOCKED | Required historical datasets (L2 book / funding / liquidations) not warehoused locally |
| `CAND-HYP-OPP-MICRO-LINKUSDT` | `MICROSTRUCTURE` | LINK/USDT | N/A | N/A | N/A | 🟡 BLOCKED | Required historical datasets (L2 book / funding / liquidations) not warehoused locally |
| `CAND-HYP-OPP-MICRO-LTCUSDT` | `MICROSTRUCTURE` | LTC/USDT | N/A | N/A | N/A | 🟡 BLOCKED | Required historical datasets (L2 book / funding / liquidations) not warehoused locally |
| `CAND-HYP-OPP-MICRO-SOLUSDT` | `MICROSTRUCTURE` | SOL/USDT | N/A | N/A | N/A | 🟡 BLOCKED | Required historical datasets (L2 book / funding / liquidations) not warehoused locally |
| `CAND-HYP-OPP-MICRO-XRPUSDT` | `MICROSTRUCTURE` | XRP/USDT | N/A | N/A | N/A | 🟡 BLOCKED | Required historical datasets (L2 book / funding / liquidations) not warehoused locally |
| `CAND-HYP-OPP-VOLSQZ-AVAXUSDT-0001` | `DIRECTIONAL` | AVAX/USDT | N/A | N/A | N/A | 🟡 BLOCKED | Required historical datasets (L2 book / funding / liquidations) not warehoused locally |
| `CAND-HYP-OPP-VOLSQZ-LTCUSDT-0002` | `DIRECTIONAL` | LTC/USDT | N/A | N/A | N/A | 🟡 BLOCKED | Required historical datasets (L2 book / funding / liquidations) not warehoused locally |

---

## 4. Ranked Next Research Queue (Governed by Research Governor)

Research priority is dynamically computed using multi-factor utility (Magnitude 35%, Data Readiness 25%, Portfolio Diversification 20%, Novelty 10%, Computational Cost -10%).

| Priority Rank | Hypothesis ID | Target Family | Asset | Priority Score | Scoring Components |
| :---: | :--- | :---: | :---: | :---: | :--- |
| **#1** | `HYP-OPP-RV-ADABTC` | `RELATIVE_VALUE` | ADA/USDT | `0.732` | magnitude: 0.72, data_readiness: 1.0, diversification: 1.0, novelty: 0.4, cost: 0.1 |
| **#2** | `HYP-OPP-RV-AVAXBTC` | `RELATIVE_VALUE` | AVAX/USDT | `0.732` | magnitude: 0.72, data_readiness: 1.0, diversification: 1.0, novelty: 0.4, cost: 0.1 |
| **#3** | `HYP-OPP-RV-BNBBTC` | `RELATIVE_VALUE` | BNB/USDT | `0.732` | magnitude: 0.72, data_readiness: 1.0, diversification: 1.0, novelty: 0.4, cost: 0.1 |
| **#4** | `HYP-OPP-RV-DOGEBTC` | `RELATIVE_VALUE` | DOGE/USDT | `0.732` | magnitude: 0.72, data_readiness: 1.0, diversification: 1.0, novelty: 0.4, cost: 0.1 |
| **#5** | `HYP-OPP-RV-ETHBTC` | `RELATIVE_VALUE` | ETH/USDT | `0.732` | magnitude: 0.72, data_readiness: 1.0, diversification: 1.0, novelty: 0.4, cost: 0.1 |
| **#6** | `HYP-OPP-RV-LINKBTC` | `RELATIVE_VALUE` | LINK/USDT | `0.732` | magnitude: 0.72, data_readiness: 1.0, diversification: 1.0, novelty: 0.4, cost: 0.1 |
| **#7** | `HYP-OPP-RV-LTCBTC` | `RELATIVE_VALUE` | LTC/USDT | `0.732` | magnitude: 0.72, data_readiness: 1.0, diversification: 1.0, novelty: 0.4, cost: 0.1 |
| **#8** | `HYP-OPP-RV-SOLBTC` | `RELATIVE_VALUE` | SOL/USDT | `0.732` | magnitude: 0.72, data_readiness: 1.0, diversification: 1.0, novelty: 0.4, cost: 0.1 |
| **#9** | `HYP-OPP-RV-XRPBTC` | `RELATIVE_VALUE` | XRP/USDT | `0.732` | magnitude: 0.72, data_readiness: 1.0, diversification: 1.0, novelty: 0.4, cost: 0.1 |
| **#10** | `HYP-OPP-VOLSQZ-ADAUSDT` | `DIRECTIONAL` | ADA/USDT | `0.690` | magnitude: 1.0, data_readiness: 1.0, diversification: 0.3, novelty: 0.4, cost: 0.1 |
| **#11** | `HYP-OPP-TREND-AVAXUSDT` | `DIRECTIONAL` | AVAX/USDT | `0.690` | magnitude: 1.0, data_readiness: 1.0, diversification: 0.3, novelty: 0.4, cost: 0.1 |
| **#12** | `HYP-OPP-VOLSQZ-AVAXUSDT` | `DIRECTIONAL` | AVAX/USDT | `0.690` | magnitude: 1.0, data_readiness: 1.0, diversification: 0.3, novelty: 0.4, cost: 0.1 |
| **#13** | `HYP-OPP-VOLSQZ-BNBUSDT` | `DIRECTIONAL` | BNB/USDT | `0.690` | magnitude: 1.0, data_readiness: 1.0, diversification: 0.3, novelty: 0.4, cost: 0.1 |
| **#14** | `HYP-OPP-VOLSQZ-BTCUSDT` | `DIRECTIONAL` | BTC/USDT | `0.690` | magnitude: 1.0, data_readiness: 1.0, diversification: 0.3, novelty: 0.4, cost: 0.1 |
| **#15** | `HYP-OPP-TREND-DOGEUSDT` | `DIRECTIONAL` | DOGE/USDT | `0.690` | magnitude: 1.0, data_readiness: 1.0, diversification: 0.3, novelty: 0.4, cost: 0.1 |
| **#16** | `HYP-OPP-VOLSQZ-DOGEUSDT` | `DIRECTIONAL` | DOGE/USDT | `0.690` | magnitude: 1.0, data_readiness: 1.0, diversification: 0.3, novelty: 0.4, cost: 0.1 |
| **#17** | `HYP-OPP-VOLSQZ-ETHUSDT` | `DIRECTIONAL` | ETH/USDT | `0.690` | magnitude: 1.0, data_readiness: 1.0, diversification: 0.3, novelty: 0.4, cost: 0.1 |
| **#18** | `HYP-OPP-TREND-LINKUSDT` | `DIRECTIONAL` | LINK/USDT | `0.690` | magnitude: 1.0, data_readiness: 1.0, diversification: 0.3, novelty: 0.4, cost: 0.1 |
| **#19** | `HYP-OPP-VOLSQZ-LINKUSDT` | `DIRECTIONAL` | LINK/USDT | `0.690` | magnitude: 1.0, data_readiness: 1.0, diversification: 0.3, novelty: 0.4, cost: 0.1 |
| **#20** | `HYP-OPP-VOLSQZ-LTCUSDT` | `DIRECTIONAL` | LTC/USDT | `0.690` | magnitude: 1.0, data_readiness: 1.0, diversification: 0.3, novelty: 0.4, cost: 0.1 |
| **#21** | `HYP-OPP-TREND-SOLUSDT` | `DIRECTIONAL` | SOL/USDT | `0.690` | magnitude: 1.0, data_readiness: 1.0, diversification: 0.3, novelty: 0.4, cost: 0.1 |
| **#22** | `HYP-OPP-VOLSQZ-SOLUSDT` | `DIRECTIONAL` | SOL/USDT | `0.690` | magnitude: 1.0, data_readiness: 1.0, diversification: 0.3, novelty: 0.4, cost: 0.1 |
| **#23** | `HYP-OPP-VOLSQZ-XRPUSDT` | `DIRECTIONAL` | XRP/USDT | `0.690` | magnitude: 1.0, data_readiness: 1.0, diversification: 0.3, novelty: 0.4, cost: 0.1 |
| **#24** | `HYP-OPP-TREND-ADAUSDT` | `DIRECTIONAL` | ADA/USDT | `0.689` | magnitude: 0.998, data_readiness: 1.0, diversification: 0.3, novelty: 0.4, cost: 0.1 |
| **#25** | `HYP-OPP-TREND-LTCUSDT` | `DIRECTIONAL` | LTC/USDT | `0.650` | magnitude: 0.887, data_readiness: 1.0, diversification: 0.3, novelty: 0.4, cost: 0.1 |
| **#26** | `HYP-OPP-TREND-XRPUSDT` | `DIRECTIONAL` | XRP/USDT | `0.650` | magnitude: 0.885, data_readiness: 1.0, diversification: 0.3, novelty: 0.4, cost: 0.1 |
| **#27** | `HYP-OPP-TREND-ETHUSDT` | `DIRECTIONAL` | ETH/USDT | `0.646` | magnitude: 0.873, data_readiness: 1.0, diversification: 0.3, novelty: 0.4, cost: 0.1 |
| **#28** | `HYP-OPP-TREND-BNBUSDT` | `DIRECTIONAL` | BNB/USDT | `0.643` | magnitude: 0.865, data_readiness: 1.0, diversification: 0.3, novelty: 0.4, cost: 0.1 |
| **#29** | `HYP-OPP-TREND-BTCUSDT` | `DIRECTIONAL` | BTC/USDT | `0.575` | magnitude: 0.671, data_readiness: 1.0, diversification: 0.3, novelty: 0.4, cost: 0.1 |
| **#30** | `HYP-OPP-CARRY-ADAUSDT` | `CARRY` | ADA/USDT | `0.440` | magnitude: 0.6, data_readiness: 0.0, diversification: 1.0, novelty: 0.4, cost: 0.1 |
| **#31** | `HYP-OPP-CARRY-AVAXUSDT` | `CARRY` | AVAX/USDT | `0.440` | magnitude: 0.6, data_readiness: 0.0, diversification: 1.0, novelty: 0.4, cost: 0.1 |
| **#32** | `HYP-OPP-CARRY-BNBUSDT` | `CARRY` | BNB/USDT | `0.440` | magnitude: 0.6, data_readiness: 0.0, diversification: 1.0, novelty: 0.4, cost: 0.1 |
| **#33** | `HYP-OPP-CARRY-BTCUSDT` | `CARRY` | BTC/USDT | `0.440` | magnitude: 0.6, data_readiness: 0.0, diversification: 1.0, novelty: 0.4, cost: 0.1 |
| **#34** | `HYP-OPP-CARRY-DOGEUSDT` | `CARRY` | DOGE/USDT | `0.440` | magnitude: 0.6, data_readiness: 0.0, diversification: 1.0, novelty: 0.4, cost: 0.1 |
| **#35** | `HYP-OPP-CARRY-ETHUSDT` | `CARRY` | ETH/USDT | `0.440` | magnitude: 0.6, data_readiness: 0.0, diversification: 1.0, novelty: 0.4, cost: 0.1 |
| **#36** | `HYP-OPP-CARRY-LINKUSDT` | `CARRY` | LINK/USDT | `0.440` | magnitude: 0.6, data_readiness: 0.0, diversification: 1.0, novelty: 0.4, cost: 0.1 |
| **#37** | `HYP-OPP-CARRY-LTCUSDT` | `CARRY` | LTC/USDT | `0.440` | magnitude: 0.6, data_readiness: 0.0, diversification: 1.0, novelty: 0.4, cost: 0.1 |
| **#38** | `HYP-OPP-CARRY-SOLUSDT` | `CARRY` | SOL/USDT | `0.440` | magnitude: 0.6, data_readiness: 0.0, diversification: 1.0, novelty: 0.4, cost: 0.1 |
| **#39** | `HYP-OPP-CARRY-XRPUSDT` | `CARRY` | XRP/USDT | `0.440` | magnitude: 0.6, data_readiness: 0.0, diversification: 1.0, novelty: 0.4, cost: 0.1 |
| **#40** | `HYP-OPP-LIQ-ADAUSDT` | `EVENT_DRIVEN` | ADA/USDT | `0.422` | magnitude: 0.55, data_readiness: 0.0, diversification: 1.0, novelty: 0.4, cost: 0.1 |
| **#41** | `HYP-OPP-LIQ-AVAXUSDT` | `EVENT_DRIVEN` | AVAX/USDT | `0.422` | magnitude: 0.55, data_readiness: 0.0, diversification: 1.0, novelty: 0.4, cost: 0.1 |
| **#42** | `HYP-OPP-LIQ-BNBUSDT` | `EVENT_DRIVEN` | BNB/USDT | `0.422` | magnitude: 0.55, data_readiness: 0.0, diversification: 1.0, novelty: 0.4, cost: 0.1 |
| **#43** | `HYP-OPP-LIQ-BTCUSDT` | `EVENT_DRIVEN` | BTC/USDT | `0.422` | magnitude: 0.55, data_readiness: 0.0, diversification: 1.0, novelty: 0.4, cost: 0.1 |
| **#44** | `HYP-OPP-LIQ-DOGEUSDT` | `EVENT_DRIVEN` | DOGE/USDT | `0.422` | magnitude: 0.55, data_readiness: 0.0, diversification: 1.0, novelty: 0.4, cost: 0.1 |
| **#45** | `HYP-OPP-LIQ-ETHUSDT` | `EVENT_DRIVEN` | ETH/USDT | `0.422` | magnitude: 0.55, data_readiness: 0.0, diversification: 1.0, novelty: 0.4, cost: 0.1 |
| **#46** | `HYP-OPP-LIQ-LINKUSDT` | `EVENT_DRIVEN` | LINK/USDT | `0.422` | magnitude: 0.55, data_readiness: 0.0, diversification: 1.0, novelty: 0.4, cost: 0.1 |
| **#47** | `HYP-OPP-LIQ-LTCUSDT` | `EVENT_DRIVEN` | LTC/USDT | `0.422` | magnitude: 0.55, data_readiness: 0.0, diversification: 1.0, novelty: 0.4, cost: 0.1 |
| **#48** | `HYP-OPP-LIQ-SOLUSDT` | `EVENT_DRIVEN` | SOL/USDT | `0.422` | magnitude: 0.55, data_readiness: 0.0, diversification: 1.0, novelty: 0.4, cost: 0.1 |
| **#49** | `HYP-OPP-LIQ-XRPUSDT` | `EVENT_DRIVEN` | XRP/USDT | `0.422` | magnitude: 0.55, data_readiness: 0.0, diversification: 1.0, novelty: 0.4, cost: 0.1 |
| **#50** | `HYP-OPP-MICRO-ADAUSDT` | `MICROSTRUCTURE` | ADA/USDT | `0.385` | magnitude: 0.5, data_readiness: 0.0, diversification: 1.0, novelty: 0.4, cost: 0.3 |
| **#51** | `HYP-OPP-MICRO-AVAXUSDT` | `MICROSTRUCTURE` | AVAX/USDT | `0.385` | magnitude: 0.5, data_readiness: 0.0, diversification: 1.0, novelty: 0.4, cost: 0.3 |
| **#52** | `HYP-OPP-MICRO-BNBUSDT` | `MICROSTRUCTURE` | BNB/USDT | `0.385` | magnitude: 0.5, data_readiness: 0.0, diversification: 1.0, novelty: 0.4, cost: 0.3 |
| **#53** | `HYP-OPP-MICRO-BTCUSDT` | `MICROSTRUCTURE` | BTC/USDT | `0.385` | magnitude: 0.5, data_readiness: 0.0, diversification: 1.0, novelty: 0.4, cost: 0.3 |
| **#54** | `HYP-OPP-MICRO-DOGEUSDT` | `MICROSTRUCTURE` | DOGE/USDT | `0.385` | magnitude: 0.5, data_readiness: 0.0, diversification: 1.0, novelty: 0.4, cost: 0.3 |
| **#55** | `HYP-OPP-MICRO-ETHUSDT` | `MICROSTRUCTURE` | ETH/USDT | `0.385` | magnitude: 0.5, data_readiness: 0.0, diversification: 1.0, novelty: 0.4, cost: 0.3 |
| **#56** | `HYP-OPP-MICRO-LINKUSDT` | `MICROSTRUCTURE` | LINK/USDT | `0.385` | magnitude: 0.5, data_readiness: 0.0, diversification: 1.0, novelty: 0.4, cost: 0.3 |
| **#57** | `HYP-OPP-MICRO-LTCUSDT` | `MICROSTRUCTURE` | LTC/USDT | `0.385` | magnitude: 0.5, data_readiness: 0.0, diversification: 1.0, novelty: 0.4, cost: 0.3 |
| **#58** | `HYP-OPP-MICRO-SOLUSDT` | `MICROSTRUCTURE` | SOL/USDT | `0.385` | magnitude: 0.5, data_readiness: 0.0, diversification: 1.0, novelty: 0.4, cost: 0.3 |
| **#59** | `HYP-OPP-MICRO-XRPUSDT` | `MICROSTRUCTURE` | XRP/USDT | `0.385` | magnitude: 0.5, data_readiness: 0.0, diversification: 1.0, novelty: 0.4, cost: 0.3 |
| **#60** | `HYP-OPP-VOLSQZ-AVAXUSDT-0001` | `DIRECTIONAL` | AVAX/USDT | `0.276` | magnitude: 0.589, data_readiness: 0.0, diversification: 0.3, novelty: 0.4, cost: 0.3 |
| **#61** | `HYP-OPP-VOLSQZ-LTCUSDT-0002` | `DIRECTIONAL` | LTC/USDT | `0.236` | magnitude: 0.474, data_readiness: 0.0, diversification: 0.3, novelty: 0.4, cost: 0.3 |

---

## 5. Production Capital Gate Enforcement
- **Live Capital:** `$0.00`
- **Order Submission:** `DISABLED`
- **Status:** Fail-Closed Capital Firewall actively prevents live order routing.
