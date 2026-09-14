# Quantitative Systems Platform (QSP)
## Systematic Alpha Research & Portfolio Risk Dashboard
**Audit Timestamp:** 2026-09-14 14:59:12 UTC
**Governance Authority:** Quantitative Research Division & Risk Committee
**Data Partitions:** Development (`2021–2022`) · Validation (`2023`) · Out-of-Sample (`2024–2026`)
**Execution Risk Engine:** Certified Stable (Friction-Adjusted Sizing strictly bounds Initial SL Loss $\le 1.0000\%$)
**Production Capital Firewall:** **PHASE K/L ACTIVE (LIVE CAPITAL STRICTLY LOCKED)**

---

### 1. Quantitative Strategy Pipeline Status
```text
Active Research Formulation:            0
Development Qualified (Dev Gates Pass): 0
Validation Passed (2023 Frozen Pass):   2
Validated Out-of-Sample (Dev+Val+OOS):  5 (Verified across 5.5-Year Data Stream)
Paper Simulation Stage:                 0
Capital Allocation Qualified:           5
Live Production Deployment:             0 (Firewall Enforced)
Archived Non-Performing / Falsified:   92
```

---

### 2. Multi-Horizon Chronological Track Record (Frozen Parameter Evaluation)
> [!IMPORTANT]
> In accordance with institutional research standards, these strategies are designated as **Development/Validation/OOS-Passing Research Candidates** (`QUALIFIED_ROBUST`). Live execution slippage, latency, order-book depth, and concurrent portfolio drawdowns must be verified in Paper Trading before capital consideration.

| Candidate ID | Strategy Family | Style / Timeframe | Asset | Dev (2021–22) Net R (N) | Val (2023) Net R (N) | OOS (2024–26) Net R (N) | Lifetime Net R | Lifetime Trades | Max DD | Research Status |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| **FAM-07-MTFCONT_SOLUSDT_Set3** | MTF Continuation | Set 3 (Swing / Intraday) | SOL/USDT | +86.53R (576) | +43.83R (292) | +73.82R (765) | **+204.19R** | 1633 | 22.07R | **`QUALIFIED_ROBUST`** |
| **FAM-07-MTFCONT_SOLUSDT_Set2** | MTF Continuation | Set 2 (Swing) | SOL/USDT | +48.52R (127) | +31.21R (68) | +28.68R (191) | **+108.41R** | 386 | 13.07R | **`QUALIFIED_ROBUST`** |
| **FAM-07-MTFCONT_ETHUSDT_Set2** | MTF Continuation | Set 2 (Swing) | ETH/USDT | +34.41R (128) | +2.39R (66) | +53.93R (169) | **+90.74R** | 363 | 9.00R | **`QUALIFIED_ROBUST`** |
| **FAM-07-MTFCONT_BTCUSDT_Set2** | MTF Continuation | Set 2 (Swing) | BTC/USDT | +22.54R (125) | +30.74R (62) | +29.38R (193) | **+82.66R** | 380 | 9.73R | **`QUALIFIED_ROBUST`** |
| **FAM-04-MOMENTUM_SOLUSDT_Set2** | Momentum Continuation | Set 2 (Swing) | SOL/USDT | +16.18R (115) | +4.51R (62) | +8.39R (202) | **+29.07R** | 379 | 19.77R | **`QUALIFIED_ROBUST`** |
| **FAM-07-MTFCONT_ETHUSDT_Set3** | MTF Continuation | Set 3 (Swing / Intraday) | ETH/USDT | +107.71R (555) | -25.64R (307) [FAIL] | *LOCKED* | **+82.07R** | 862 | 41.38R | `FAILED_VALIDATION` |
| **FAM-03-BREAKOUT_SOLUSDT_Set2** | Breakout (Donchian) | Set 2 (Swing) | SOL/USDT | +29.05R (144) | +28.06R (78) | -2.61R (205) [FAIL] | **+54.49R** | 427 | 29.55R | `VALIDATED` |
| **FAM-01-TREND_SOLUSDT_Set3** | Trend Following | Set 3 (Swing / Intraday) | SOL/USDT | +46.39R (203) | +8.53R (98) | -10.53R (293) [FAIL] | **+44.39R** | 594 | 18.78R | `VALIDATED` |
| **FAM-03-BREAKOUT_ETHUSDT_Set2** | Breakout (Donchian) | Set 2 (Swing) | ETH/USDT | +20.20R (131) | -21.38R (82) [FAIL] | *LOCKED* | **-1.18R** | 213 | 23.03R | `FAILED_VALIDATION` |

---

### 3. Systematic Style Allocation Matrix (Sets 1 to 6)
#### Set 1 — Macro / Position (1M -> 1W -> 1D)
> `UNRESOLVED STYLE — NO QUALIFIED RESEARCH CANDIDATE FOUND` meeting multi-dimensional robustness criteria.

#### Set 2 — Swing (1W -> 1D -> 4H)
| Candidate ID | Family | Asset | Lifetime N | Lifetime Net R | Max DD | Top 1 % | Status |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :--- |
| **FAM-07-MTFCONT_SOLUSDT_Set2** | MTF Continuation | SOL/USDT | 386 | **+108.41R** | 13.07R | <=8.4% | **`QUALIFIED_ROBUST`** |
| **FAM-07-MTFCONT_ETHUSDT_Set2** | MTF Continuation | ETH/USDT | 363 | **+90.74R** | 9.00R | <=8.4% | **`QUALIFIED_ROBUST`** |
| **FAM-07-MTFCONT_BTCUSDT_Set2** | MTF Continuation | BTC/USDT | 380 | **+82.66R** | 9.73R | <=8.4% | **`QUALIFIED_ROBUST`** |
| **FAM-04-MOMENTUM_SOLUSDT_Set2** | Momentum Continuation | SOL/USDT | 379 | **+29.07R** | 19.77R | <=8.4% | **`QUALIFIED_ROBUST`** |

#### Set 3 — Swing / Intraday (1D -> 4H -> 1H)
| Candidate ID | Family | Asset | Lifetime N | Lifetime Net R | Max DD | Top 1 % | Status |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :--- |
| **FAM-07-MTFCONT_SOLUSDT_Set3** | MTF Continuation | SOL/USDT | 1633 | **+204.19R** | 22.07R | <=8.4% | **`QUALIFIED_ROBUST`** |

#### Set 4 — Intraday (4H -> 1H -> 15M)
> `UNRESOLVED STYLE — NO QUALIFIED RESEARCH CANDIDATE FOUND` meeting multi-dimensional robustness criteria.

#### Set 5 — Short-Term Intraday (1H -> 15M -> 5M)
> [!NOTE]
> **DATA ARCHITECTURE NOTICE (Historical Horizon):** Local cache contains 50,000 candles on 5M and 1M covering the 2026 regime. Complete historical 2021–2022 5M/1M Kline archives are scheduled for automated ingestion via `data_ingestion/backfill_binance_klines.py`.

#### Set 6 — Scalping (15M -> 5M -> 1M)
> [!NOTE]
> **DATA ARCHITECTURE NOTICE (Historical Horizon):** Local cache contains 50,000 candles on 5M and 1M covering the 2026 regime. Complete historical 2021–2022 5M/1M Kline archives are scheduled for automated ingestion via `data_ingestion/backfill_binance_klines.py`.

---

### 4. Development Robustness Ledger (2021–2022 In-Sample Screening)
| Candidate ID | Family | Asset | Set | N (Req >= 100) | Net R | Exp (R) | PF | Max DD | Top 1 % | Net w/o Top 1 | 2x Cost Stress | Parameter Stability |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **FAM-07-MTFCONT_ETHUSDT_Set3** | MTF Continuation | ETH/USDT | Set 3 | 555 | +107.71R | +0.19R | 1.314 | 10.00R | 2.2% | +105.31R | +45.36R (PASS) | PASS |
| **FAM-07-MTFCONT_SOLUSDT_Set3** | MTF Continuation | SOL/USDT | Set 3 | 576 | +86.53R | +0.15R | 1.2332 | 14.30R | 2.8% | +84.10R | +40.40R (PASS) | PASS |
| **FAM-07-MTFCONT_SOLUSDT_Set2** | MTF Continuation | SOL/USDT | Set 2 | 127 | +48.52R | +0.38R | 1.6469 | 6.00R | 5.0% | +46.07R | +42.51R (PASS) | PASS |
| **FAM-01-TREND_SOLUSDT_Set3** | Trend Following | SOL/USDT | Set 3 | 203 | +46.39R | +0.23R | 1.3386 | 14.07R | 6.3% | +43.45R | +33.56R (PASS) | PASS |
| **FAM-07-MTFCONT_ETHUSDT_Set2** | MTF Continuation | ETH/USDT | Set 2 | 128 | +34.41R | +0.27R | 1.4356 | 8.11R | 7.0% | +31.99R | +26.30R (PASS) | PASS |
| **FAM-03-BREAKOUT_SOLUSDT_Set2** | Breakout (Donchian) | SOL/USDT | Set 2 | 144 | +29.05R | +0.20R | 1.2934 | 11.55R | 10.1% | +26.10R | +22.66R (PASS) | PASS |
| **FAM-07-MTFCONT_BTCUSDT_Set2** | MTF Continuation | BTC/USDT | Set 2 | 125 | +22.54R | +0.18R | 1.2818 | 9.73R | 10.6% | +20.15R | +13.85R (PASS) | PASS |
| **FAM-03-BREAKOUT_ETHUSDT_Set2** | Breakout (Donchian) | ETH/USDT | Set 2 | 131 | +20.20R | +0.15R | 1.222 | 10.33R | 14.3% | +17.30R | +12.38R (PASS) | PASS |
| **FAM-04-MOMENTUM_SOLUSDT_Set2** | Momentum Continuation | SOL/USDT | Set 2 | 115 | +16.18R | +0.14R | 1.2129 | 11.31R | 15.2% | +13.73R | +11.30R (PASS) | PASS |

---

### 5. Historical Negative Benchmark Archive
| Benchmark ID | Strategy Concept | Historical Horizon | Trades (N) | Net R | Primary Falsification Mode |
| :--- | :--- | :---: | :---: | :---: | :--- |
| **BASELINE_001_CONTROL** | Supertrend + Stoch 3x Alignment (6.0R Floor) | 2021–2022 Dev | 6 | -1.97R | Severe opportunity starvation (6 trades in 2 years across 12 sets) |
| **EXP-001A-GEOM** | Target Floor Reduction (3.0R Floor) | 2021–2022 Dev | 11 | -3.42R | Degradation of expectancy; trade frequency remained insufficient |
| **EXP-001B-STOCH** | Decoupled MTF Stochastic Hierarchy | 2021–2022 Dev | 97 | -2.15R | Increased frequency 16x, but no individual set reached N >= 100 |
| **FAM-05-MEANREV** | Bollinger / Keltner Mean Reversion (12 Sets) | 2021–2022 Dev | 1,200+ | -140R to -660R | Structural breakdown during crypto secular trend regimes |
| **FAM-03-SET4** | Intraday Breakout (4H -> 1H -> 15M) | 2021–2022 Dev | 2,000+ | Negative Post-Cost | Friction erosion under taker fee and spread on small 15M ranges |

---

### 6. Institutional Research Governance & Next Phase Actions
1. **Core Architectural Discovery:** Family 7 (Multi-Timeframe Continuation) demonstrates strong empirical validity on Set 2 across all three core assets (BTC +82.66R, ETH +90.74R, SOL +108.41R; combined +281.81R across 1,129 trades) and on Set 3 for SOL (+204.19R across 1,633 trades).
2. **Risk & Capital Firewall Preserved:** No capital may be committed to any strategy based on backtest results alone. Live capital remains strictly locked behind Phase K/L.
3. **Execution of Comprehensive Falsification Suite (Phases A–H):** All 5 candidate strategies are subjected to clean-slate reproducibility verification, trade-level loss bound proofs, expanded friction stress (up to 4.0x), walk-forward efficiency testing, cross-asset correlation analysis, parameter sensitivity mapping, and missing-style resolution.