# QCP FORENSIC REPORT: BOUNDED STRUCTURAL + REGIME EDGE RESEARCH

**Execution Timestamp:** `2026-09-18T11:38:53.310189+00:00 UTC`  
**Population:** `BTC/USDT, ETH/USDT, SOL/USDT` across `SET_2, SET_3, SET_4`  
**Data Partition:** `DEV (2021-01-01 to 2022-12-31)`  
**Research Governor:** `min_rr_firewall = 4.0`, `risk <= 1.0%`  

---

## 1. EXECUTIVE SUMMARY & OBJECTIVE CLASSIFICATION

In accordance with Directive Section 12, no hypothesis is ranked as an arbitrary 'winner'. Each mechanism is evaluated objectively against economic expectancy, trade statistical validity, and friction survivability.

| Hypothesis ID | Mechanism Family | Classification | Trades | Win Rate | Net R | PF | Expectancy (R) | Friction Drag |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **H_STRUCT_01** | FVG Tap + Breakout Close + Structur... | **`FAIL`** | 77 | 24.68% | -22.64R | 0.71 | -0.294R | 1478.2% |
| **H_STRUCT_02** | FVG Tap + Displacement Confirmation... | **`INCONCLUSIVE`** | 14 | 28.57% | -6.68R | 0.55 | -0.477R | 180.0% |
| **H_STRUCT_03** | Liquidity Sweep + Sweep Reclaim + S... | **`FAIL`** | 11053 | 23.07% | -3624.04R | 0.66 | -0.328R | 212.8% |
| **H_STRUCT_04** | Liquidity Sweep + CHoCH Confirmatio... | **`FAIL`** | 31 | 19.35% | -7.41R | 0.57 | -0.239R | 106.2% |
| **H_STRUCT_05** | Breakout Retest + Breakout Close + ... | **`FAIL`** | 65 | 24.62% | -24.45R | 0.59 | -0.376R | 166.0% |

---

## 2. COMPLETE CONVERSION FUNNEL ANALYSIS

Every candidate opportunity is traced across the full 8-stage causal pipeline:
`OBSERVATIONS → REGIME → SETUP → ENTRY → GEOMETRY → FIREWALL → EXECUTION → EXIT`

| Hypothesis | Observations | Regime Valid | Setup Valid | Entry Valid | Geometry Valid | Firewall Rejections | Executed Trades |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **H_STRUCT_01** | 968083 | 173484 | 316960 | 437721 | 5323 | 5246 | **77** |
| **H_STRUCT_02** | 968083 | 173484 | 316960 | 49738 | 770 | 757 | **14** |
| **H_STRUCT_03** | 968083 | 967633 | 36119 | 252309 | 15075 | 4031 | **11053** |
| **H_STRUCT_04** | 968083 | 967633 | 36119 | 78103 | 139 | 109 | **31** |
| **H_STRUCT_05** | 968083 | 173484 | 53641 | 437721 | 5352 | 5293 | **65** |

### Funnel Drop-off Insights:
- **H_STRUCT_01**: Setup conversion: `182.7%` of regime bars. Firewall pass rate: `1.4%` (5246 rejections due to R:R < 4.0).
- **H_STRUCT_02**: Setup conversion: `182.7%` of regime bars. Firewall pass rate: `1.7%` (757 rejections due to R:R < 4.0).
- **H_STRUCT_03**: Setup conversion: `3.7%` of regime bars. Firewall pass rate: `73.3%` (4031 rejections due to R:R < 4.0).
- **H_STRUCT_04**: Setup conversion: `3.7%` of regime bars. Firewall pass rate: `21.6%` (109 rejections due to R:R < 4.0).
- **H_STRUCT_05**: Setup conversion: `30.9%` of regime bars. Firewall pass rate: `1.1%` (5293 rejections due to R:R < 4.0).

---

## 3. FRICTION CONSUMPTION BREAKDOWN

| Hypothesis | Gross R | Total Fees + Slippage (R) | Net R | Friction Drag Ratio | Exit Reasons |
| :--- | :---: | :---: | :---: | :---: | :--- |
| **H_STRUCT_01** | +1.64R | 24.28R | -22.64R | 1478.2% | `STOP_LOSS: 55, TAKE_PROFIT: 11, TIME_STOP: 11` |
| **H_STRUCT_02** | -2.39R | 4.29R | -6.68R | 180.0% | `TIME_STOP: 3, STOP_LOSS: 10, TAKE_PROFIT: 1` |
| **H_STRUCT_03** | -1158.49R | 2465.55R | -3624.04R | 212.8% | `STOP_LOSS: 8242, TAKE_PROFIT: 363, TIME_STOP: 2448` |
| **H_STRUCT_04** | -3.59R | 3.82R | -7.41R | 106.2% | `TRAILING_STOP: 24, STOP_LOSS: 6, TAKE_PROFIT: 1` |
| **H_STRUCT_05** | -9.19R | 15.26R | -24.45R | 166.0% | `STOP_LOSS: 45, TIME_STOP: 15, TAKE_PROFIT: 5` |

---

## 4. DIVERSITY & TRADE CORRELATION ANALYSIS

Measures pairwise Jaccard trade overlap (%) across the five structural mechanisms to determine whether edges are genuinely independent alpha sources or related variants.

| Hypothesis | H_STRUCT_01 | H_STRUCT_02 | H_STRUCT_03 | H_STRUCT_04 | H_STRUCT_05 |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **H_STRUCT_01** | 100.0% | 2.3% | 0.0% | 0.0% | 0.7% |
| **H_STRUCT_02** | 2.3% | 100.0% | 0.0% | 0.0% | 0.0% |
| **H_STRUCT_03** | 0.0% | 0.0% | 100.0% | 0.0% | 0.0% |
| **H_STRUCT_04** | 0.0% | 0.0% | 0.0% | 100.0% | 0.0% |
| **H_STRUCT_05** | 0.7% | 0.0% | 0.0% | 0.0% | 100.0% |

---

## 5. DETAILED HYPOTHESIS FORENSICS

### H_STRUCT_01: FVG Tap + Breakout Close + Structural SL + Structural TP + Trail None
- **Official Verdict:** `FAIL`
- **Rationale:** Negative or uncompetitive economic edge (Net R: -22.64R, PF: 0.71).
- **Total Trades:** 77 (Wins: 19, Losses: 58)
- **Win Rate:** 24.68% | **Profit Factor:** 0.71
- **Expectancy:** -0.294R per trade
- **Max Drawdown:** 29.96R
- **Trades by Asset:** `{"BTC/USDT": 27, "ETH/USDT": 40, "SOL/USDT": 10}`
- **Trades by Timeframe:** `{"4h": 8, "1h": 14, "15m": 55}`

### H_STRUCT_02: FVG Tap + Displacement Confirmation + FVG Invalidation SL + Liquidity Target TP + Trail None
- **Official Verdict:** `INCONCLUSIVE`
- **Rationale:** Insufficient trade count (14 < 15) across DEV matrix.
- **Total Trades:** 14 (Wins: 4, Losses: 10)
- **Win Rate:** 28.57% | **Profit Factor:** 0.55
- **Expectancy:** -0.477R per trade
- **Max Drawdown:** 13.17R
- **Trades by Asset:** `{"BTC/USDT": 4, "ETH/USDT": 9, "SOL/USDT": 1}`
- **Trades by Timeframe:** `{"4h": 4, "1h": 1, "15m": 9}`

### H_STRUCT_03: Liquidity Sweep + Sweep Reclaim + Setup Invalidation SL + Structural TP + Trail None
- **Official Verdict:** `FAIL`
- **Rationale:** Negative or uncompetitive economic edge (Net R: -3624.04R, PF: 0.66).
- **Total Trades:** 11053 (Wins: 2550, Losses: 8503)
- **Win Rate:** 23.07% | **Profit Factor:** 0.66
- **Expectancy:** -0.328R per trade
- **Max Drawdown:** 3667.99R
- **Trades by Asset:** `{"BTC/USDT": 4731, "ETH/USDT": 4444, "SOL/USDT": 1878}`
- **Trades by Timeframe:** `{"4h": 684, "1h": 2716, "15m": 7653}`

### H_STRUCT_04: Liquidity Sweep + CHoCH Confirmation + Structural SL + HTF Structure TP + Trail BOS
- **Official Verdict:** `FAIL`
- **Rationale:** Negative or uncompetitive economic edge (Net R: -7.41R, PF: 0.57).
- **Total Trades:** 31 (Wins: 6, Losses: 25)
- **Win Rate:** 19.35% | **Profit Factor:** 0.57
- **Expectancy:** -0.239R per trade
- **Max Drawdown:** 12.36R
- **Trades by Asset:** `{"BTC/USDT": 20, "ETH/USDT": 8, "SOL/USDT": 3}`
- **Trades by Timeframe:** `{"4h": 2, "1h": 17, "15m": 12}`

### H_STRUCT_05: Breakout Retest + Breakout Close + Setup Invalidation SL + Liquidity Target TP + Trail None
- **Official Verdict:** `FAIL`
- **Rationale:** Negative or uncompetitive economic edge (Net R: -24.45R, PF: 0.59).
- **Total Trades:** 65 (Wins: 16, Losses: 49)
- **Win Rate:** 24.62% | **Profit Factor:** 0.59
- **Expectancy:** -0.376R per trade
- **Max Drawdown:** 34.57R
- **Trades by Asset:** `{"BTC/USDT": 24, "ETH/USDT": 31, "SOL/USDT": 10}`
- **Trades by Timeframe:** `{"4h": 7, "1h": 17, "15m": 41}`

---

## 6. SCIENTIFIC CONCLUSIONS & CANDIDATE RECOMMENDATIONS

1. **Structural Edge vs Indicator Comparison:**
   Structural mechanisms (FVGs, Liquidity Sweeps, and Breakout Retests) exhibit distinct funnel characteristics compared to Supertrend/Stochastic. Specifically, structural geometries create wider native risk distributions and higher natural R-multiples.
2. **Firewall Impact:**
   The strict 4.0 R:R research firewall acts as an uncompromising filter, eliminating marginal trades.
3. **Future Research Hypotheses (`FUTURE_HYPOTHESIS`):**
   - Registration of dynamic volatility-scaled structural targets.
   - Multi-stage partial exits on structural liquidity sweeps.

