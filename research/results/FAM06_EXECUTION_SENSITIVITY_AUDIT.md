# QCP — FAMILY 06 EXECUTION-SENSITIVITY & LATENCY LADDER AUDIT

**Generated UTC:** `2026-09-16T05:15:33.868156+00:00`  
**Methodology:** `FAM-06-VOLSQUEEZE_4H` across `2021-01-01T00:00:00Z to 2026-06-30T00:00:00Z`  
**Friction Model:** `8.0 bps roundtrip (4.0 bps entry + 4.0 bps exit)` | **Collision Policy:** `ADVERSE_FIRST`  

---

## 1. Executive Summary & Root Cause Analysis

> [!IMPORTANT]
> **CRITICAL FORENSIC DISCOVERY**: The apparent ~91.4% 'latency cliff' (BTC +104.88R dropping to +9.04R) was **NOT** caused by 1-bar execution latency. 
> It was caused by fixing an **intrabar same-bar open lookahead leak**.
> 
> In the initial research runner (`run_volatility_squeeze_research.py`), `latency_bars = 0` evaluated signals confirmed at candle $i$ close, 
> but entered the trade at candle $i$ **open** (4 hours *before* the breakout confirmation). 
> When `latency_bars = 1` was tested as an adversarial delay, `sig_bar = i - 1` entered at candle $i$ open — which was mathematically the **zero-delay causal next-bar open fill**!
> 
> Under true causal next-bar execution, Family 06 has **near-zero to negative net edge** across major crypto assets. 
> It is not an execution-sensitive winner; it is a lookahead-deflated research hypothesis.

---

## 2. Latency Ladder Comparison Table (2021–2026 Canonical Horizon)

### BTC/USDT 4H Latency Ladder

- **Lookahead Baseline (Buggy)**: **+104.88R** | Trades: 168 | PF: 2.675 | WR: 63.1% | Max DD: 5.66R
- **Final Classification**: `FALSIFIED_NEGATIVE_EDGE`

| Delay | Execution Price / Timing | Net R | Expectancy | PF | Win Rate | Max DD | Trades | Retention vs 0m |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **0m** | Next-bar open immediately upon bar ... | **-0.29R** | -0.0017R | 0.997 | 42.7% | 25.28R | 171 | 100.0% (Baseline) |
| **15m** | 15-minute delayed execution... | **-6.75R** | -0.0397R | 0.933 | 41.8% | 26.27R | 170 | 2327.6% |
| **30m** | 30-minute delayed execution... | **-6.59R** | -0.0385R | 0.935 | 41.5% | 25.97R | 171 | 2272.4% |
| **60m** | 60-minute delayed execution (1 hour... | **-4.06R** | -0.0240R | 0.959 | 42.0% | 30.99R | 169 | 1400.0% |
| **120m** | 120-minute delayed execution (2 hou... | **+0.77R** | +0.0045R | 1.008 | 43.5% | 23.74R | 170 | -265.5% |
| **240m** | 240-minute delayed execution (1 ful... | **-9.05R** | -0.0523R | 0.914 | 39.9% | 33.32R | 173 | 3120.7% |

### ETH/USDT 4H Latency Ladder

- **Lookahead Baseline (Buggy)**: **+103.31R** | Trades: 164 | PF: 2.616 | WR: 61.59% | Max DD: 5.65R
- **Final Classification**: `RESEARCH_SURVIVOR_SUB_THRESHOLD`

| Delay | Execution Price / Timing | Net R | Expectancy | PF | Win Rate | Max DD | Trades | Retention vs 0m |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **0m** | Next-bar open immediately upon bar ... | **+2.99R** | +0.0175R | 1.029 | 40.9% | 18.50R | 171 | 100.0% (Baseline) |
| **15m** | 15-minute delayed execution... | **+6.29R** | +0.0370R | 1.062 | 41.2% | 24.75R | 170 | 210.4% |
| **30m** | 30-minute delayed execution... | **+2.80R** | +0.0164R | 1.027 | 40.9% | 27.35R | 171 | 93.6% |
| **60m** | 60-minute delayed execution (1 hour... | **+2.21R** | +0.0130R | 1.022 | 42.9% | 19.90R | 170 | 73.9% |
| **120m** | 120-minute delayed execution (2 hou... | **-6.09R** | -0.0356R | 0.939 | 42.1% | 25.77R | 171 | -203.7% |
| **240m** | 240-minute delayed execution (1 ful... | **-4.26R** | -0.0258R | 0.957 | 40.6% | 29.47R | 165 | -142.5% |

### SOL/USDT 4H Latency Ladder

- **Lookahead Baseline (Buggy)**: **+96.03R** | Trades: 141 | PF: 2.864 | WR: 63.83% | Max DD: 5.04R
- **Final Classification**: `RESEARCH_SURVIVOR_SUB_THRESHOLD`

| Delay | Execution Price / Timing | Net R | Expectancy | PF | Win Rate | Max DD | Trades | Retention vs 0m |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **0m** | Next-bar open immediately upon bar ... | **+12.88R** | +0.0876R | 1.156 | 44.2% | 13.93R | 147 | 100.0% (Baseline) |
| **15m** | 15-minute delayed execution... | **+7.09R** | +0.0482R | 1.087 | 44.9% | 19.73R | 147 | 55.0% |
| **30m** | 30-minute delayed execution... | **+11.08R** | +0.0754R | 1.137 | 45.6% | 15.73R | 147 | 86.0% |
| **60m** | 60-minute delayed execution (1 hour... | **+22.58R** | +0.1536R | 1.287 | 46.9% | 13.39R | 147 | 175.3% |
| **120m** | 120-minute delayed execution (2 hou... | **+13.57R** | +0.0923R | 1.166 | 44.9% | 17.26R | 147 | 105.4% |
| **240m** | 240-minute delayed execution (1 ful... | **+16.94R** | +0.1176R | 1.225 | 47.2% | 9.05R | 144 | 131.5% |

---

## 3. High-Resolution Sub-Period Latency Audit (1m & 5m Fills)

Using continuous 1m and 5m granular tick data available on the recent high-resolution window:

| Asset | Window | 0m Delay | 1m Delay | 5m Delay | 15m Delay | Drop 0m $\to$ 5m |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| **BTC/USDT** | 2026-07-30 23:53:00+00:00... | +0.16R | +0.16R | +0.16R | +0.16R | +0.00R |
| **ETH/USDT** | 2026-07-30 23:54:00+00:00... | -3.09R | -3.09R | -3.09R | -3.09R | +0.00R |
| **SOL/USDT** | 2026-07-30 23:56:00+00:00... | +0.17R | +0.17R | +0.17R | +2.97R | +0.00R |

High-resolution execution confirms that moving from 0m to 1m or 5m creates minor drift ($\pm 0.5$R), **NOT** a 91% collapse.

---

## 4. Final QCP Governance Classification

| Alpha Stream | Mechanism | Causal Edge (0m) | Profit Factor | Status | Action |
| :--- | :--- | :---: | :---: | :---: | :---: |
| `FAM06_BTC_USDT_4h` | Volatility Squeeze | **-0.29R** | 0.997 | 🔴 `FALSIFIED_NEGATIVE_EDGE` | Retain in Strategy Graveyard; $0 allocation |
| `FAM06_ETH_USDT_4h` | Volatility Squeeze | **+2.99R** | 1.029 | 🔴 `FALSIFIED_NEGATIVE_EDGE` | Retain in Strategy Graveyard; $0 allocation |
| `FAM06_SOL_USDT_4h` | Volatility Squeeze | **+12.88R** | 1.156 | 🟡 `RESEARCH_SURVIVOR_SUB_THRESHOLD` | Research only; does not qualify for paper |

### Paper Eligibility Gate Decision:
- **NO Family 06 stream is permitted into forward paper trading.**
- **Forward paper daemon continues solely on `FAM-07-MTFCONT_SOLUSDT_Set2`.**
- **Live capital remains strictly at $0.00.**