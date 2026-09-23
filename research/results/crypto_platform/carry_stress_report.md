# Funding Carry Strategy — Stress Test & Sensitivity Audit Report

**Audit Generated:** 2026-09-23 08:20:01 UTC  
**Tested Assets:** BTCUSDT, ETHUSDT, SOLUSDT, BNBUSDT, ADAUSDT  
**Strategy Classification:** Market-Neutral Delta-Hedged Funding Harvest (CARRY)  

---

## 1. Executive Summary & Forensic Warning

> [!WARNING]
> In historical backtesting, the funding carry strategy accounted for **71.6% of total portfolio returns** (+41.3% net).
> However, funding carry is **NOT risk-free alpha**. When institutional crowding compresses funding yields or when market
> regimes flip into sustained negative funding (backwardation), net yield decays rapidly under margin and rebalancing drag.

---

## 2. Scenario Stress Matrix Results

| Scenario ID | Description | Avg Net Return (%) | Total Trades | Win Rate | Viability Status |
|---|---|---|---|---|---|
| **S0_BASELINE** | Historical baseline funding with standard maker/taker frictions | **+55.93%** | 128 | 62.5% | `ROBUST` |
| **S1_COMPRESSION_25** | 25% funding yield compression (institutional crowding) | **+39.08%** | 98 | 64.3% | `ROBUST` |
| **S2_COMPRESSION_50** | 50% funding yield compression (moderate bear/low volatility regime) | **+22.89%** | 60 | 83.3% | `ROBUST` |
| **S3_COMPRESSION_75** | 75% funding yield compression (severe prolonged bear chop) | **+7.47%** | 45 | 57.8% | `SURVIVES` |
| **S4_ZERO_FUNDING** | Zero funding rate environment (flat markets with zero demand for leverage) | **+0.00%** | 0 | 0.0% | `FAILS_STRESS` |
| **S5_NEGATIVE_REGIME** | Negative funding regime (shorts pay longs, e.g. -10% APR average) | **+3.13%** | 57 | 28.1% | `SURVIVES` |
| **S6_ELEVATED_FRICTIONS** | Double taker fees + 2x slippage + 30 bps adverse basis divergence | **+30.58%** | 128 | 42.2% | `ROBUST` |
| **S7_BORROW_AND_REBALANCE_DRAG** | 8% margin borrow rate + 20 bps/month hedge rebalance drag | **+22.36%** | 128 | 34.4% | `ROBUST` |
| **S8_COMPOUND_CATASTROPHIC_STRESS** | 50% compression + 50 bps basis shock + 8% borrow drag + 2x fees | **-7.53%** | 60 | 23.3% | `FAILS_STRESS` |

---

## 3. Key Forensic Findings & Capital Recommendations

1. **Funding Yield Sensitivity:**
   - Under **25% to 50% yield compression**, the strategy remains comfortably profitable (net positive alpha after full taker fees).
   - Under **75% compression**, returns decay near zero; trading must be paused when trailing 7-day APR drops below 4.0%.
2. **Negative Funding Regimes:**
   - In sustained bear regimes where perpetuals trade at a discount (funding < 0), the strategy correctly exits via the `FUND_NEGATIVE` exit rule, bounding losses to initial entry/exit roundtrip fees.
3. **Borrow Costs & Margin Requirements:**
   - A margin borrow rate exceeding 8% APR consumes ~30% of gross carry yield, demonstrating that uncollateralized or highly leveraged carry is dangerous.
4. **Capital Allocation Policy:**
   - The Carry book must be capped at **max 15% to 25% of total portfolio capital**, never 70%+, ensuring portfolio diversification across uncorrelated directional books.

---
*Report generated autonomously by the Crypto Trading Platform Research Engine.*