# QCP Platform — All-Horizon Edge Report

_Generated 2026-09-21T16:20:14 · 113 books measured · 1 promoted · sweep 146.0s_

> Every figure below is computed from the local price/funding cache with full transaction costs, next-bar-open fills and adverse-first stop resolution. Out-of-sample data is never used for selection.

## 1. Horizon economics (the gate that decides everything)

| Horizon | Clocks (HTF/MTF/LTF) | Style | Median ATR (bps) | Stop (bps) | Cost (bps) | Cost/Stop | Verdict |
|---|---|---|---|---|---|---|---|
| **SCALP** | 15m/5m/1m | seconds-minutes | 8.4 | 17 | 5 | 0.298 | TRADABLE |
| **INTRADAY** | 4h/1h/15m | hours | 49.5 | 99 | 5 | 0.051 | TRADABLE |
| **SWING** | 1d/4h/1h | days | 115.3 | 288 | 22 | 0.076 | TRADABLE |
| **POSITION** | 1w/1d/4h | weeks-months | 251.8 | 755 | 22 | 0.029 | TRADABLE |
| **INVEST** | 1M/1w/1d | months-years | 683.4 | 2734 | 22 | 0.008 | TRADABLE |
| **CARRY** | 1d/1d/1d | weeks-months | — | — | 49 | — | market-neutral (vs funding yield) |

`Median ATR` is measured live from the cache; the cost column is the all-in roundtrip cost from `costs.CostModel`. Where **Cost/Stop** exceeds 1/3, the horizon cannot be traded with those fills no matter how good the signal looks.

## 2. Verdicts across all books

| Verdict | Count |
|---|---|
| REJECTED_G2 | 73 |
| REJECTED_G7 | 13 |
| REJECTED_G1 | 12 |
| REJECTED_DATA | 10 |
| REJECTED_G5 | 3 |
| REJECTED_G3 | 1 |
| PROMOTABLE_PAPER_ONLY | 1 |

## 3. Promoted books

| Horizon | Family | Symbol | DEV exp | DEV n | VAL exp | VAL n | OOS exp | OOS n | Shock exp | WFR | Verdict |
|---|---|---|---|---|---|---|---|---|---|---|---|
| POSITION | trend_breakout | BNBUSDT | +0.593 | 61 | +0.237 | 19 | +0.627 | 16 | +0.590 | 1.0 | PROMOTABLE_PAPER_ONLY |

## 4. Where the edge died

- **SCALP** (10 books): Promoted 0; died of data 0, alpha 0, stats 0, walk-forward 0, cost-shock 0.
- **INTRADAY** (15m clock, 40 books): median 1R = 113bps vs 5bps roundtrip (cost/stop = 0.044). Promoted 0; died of data 0, alpha 34, stats 1, walk-forward 0, cost-shock 0.
- **SWING** (1h clock, 30 books): median 1R = 277bps vs 22bps roundtrip (cost/stop = 0.079). Promoted 0; died of data 1, alpha 23, stats 0, walk-forward 0, cost-shock 3.
- **POSITION** (4h clock, 21 books): median 1R = 568bps vs 22bps roundtrip (cost/stop = 0.039). Promoted 1; died of data 1, alpha 14, stats 0, walk-forward 0, cost-shock 0.
- **INVEST** (1d clock, 2 books): median 1R = 1921bps vs 22bps roundtrip (cost/stop = 0.011). Promoted 0; died of data 0, alpha 2, stats 0, walk-forward 0, cost-shock 0.
- **CARRY** (10 books): Promoted 0; died of data 10, alpha 0, stats 0, walk-forward 0, cost-shock 0.

## 5. Full verdict matrix

| Horizon | Family | Symbol | DEV exp | DEV n | VAL exp | VAL n | OOS exp | OOS n | Shock exp | WFR | Verdict |
|---|---|---|---|---|---|---|---|---|---|---|---|
| CARRY | funding_carry | ADAUSDT | +14.410 | 8 | +6.210 | 3 | +5.260 | 3 | +0.000 | 1.0 | REJECTED_G1 |
| CARRY | funding_carry | AVAXUSDT | +7.583 | 8 | +5.093 | 4 | +5.298 | 3 | +0.000 | 1.0 | REJECTED_G1 |
| CARRY | funding_carry | BNBUSDT | +5.910 | 10 | +5.278 | 4 | +1.423 | 4 | +0.000 | 1.0 | REJECTED_G1 |
| CARRY | funding_carry | BTCUSDT | +9.695 | 8 | +5.769 | 3 | +6.198 | 3 | +0.000 | 1.0 | REJECTED_G1 |
| CARRY | funding_carry | DOGEUSDT | +9.039 | 8 | +8.302 | 4 | +4.692 | 3 | +0.000 | 1.0 | REJECTED_G1 |
| CARRY | funding_carry | ETHUSDT | +14.056 | 8 | +5.989 | 4 | +4.856 | 3 | +0.000 | 1.0 | REJECTED_G1 |
| CARRY | funding_carry | LINKUSDT | +10.914 | 8 | +10.473 | 4 | +7.473 | 3 | +0.000 | 1.0 | REJECTED_G1 |
| CARRY | funding_carry | LTCUSDT | +14.026 | 8 | +8.311 | 3 | +5.545 | 3 | +0.000 | 1.0 | REJECTED_G1 |
| CARRY | funding_carry | SOLUSDT | +8.565 | 7 | +6.364 | 3 | +4.655 | 3 | +0.000 | 1.0 | REJECTED_G1 |
| CARRY | funding_carry | XRPUSDT | +15.432 | 8 | +8.632 | 4 | +5.375 | 3 | +0.000 | 1.0 | REJECTED_G1 |
| INTRADAY | grid_range | ADAUSDT | +0.325 | 71 | +0.458 | 18 | -0.163 | 21 | -0.179 | 0.5 | REJECTED_G2 |
| INTRADAY | grid_range | AVAXUSDT | +0.069 | 111 | +0.086 | 16 | -0.106 | 41 | -0.130 | 0.5 | REJECTED_G2 |
| INTRADAY | grid_range | BNBUSDT | +0.069 | 75 | -0.373 | 28 | -0.213 | 23 | -0.245 | 0.0 | REJECTED_G2 |
| INTRADAY | grid_range | BTCUSDT | -0.007 | 463 | +0.095 | 83 | +0.111 | 106 | +0.069 | 0.0 | REJECTED_G2 |
| INTRADAY | grid_range | DOGEUSDT | +0.075 | 89 | +0.132 | 32 | -0.110 | 27 | -0.144 | 0.5 | REJECTED_G2 |
| INTRADAY | grid_range | ETHUSDT | +0.040 | 483 | -0.102 | 107 | +0.044 | 113 | +0.012 | 0.5 | REJECTED_G2 |
| INTRADAY | grid_range | LINKUSDT | +0.246 | 109 | -0.161 | 28 | -0.378 | 49 | -0.402 | 0.0 | REJECTED_G2 |
| INTRADAY | grid_range | LTCUSDT | +0.213 | 110 | +0.073 | 34 | -0.259 | 48 | -0.290 | 0.5 | REJECTED_G2 |
| INTRADAY | grid_range | SOLUSDT | +0.120 | 154 | -0.086 | 55 | -0.263 | 55 | -0.278 | 0.0 | REJECTED_G2 |
| INTRADAY | grid_range | XRPUSDT | +0.126 | 64 | -0.244 | 24 | -0.238 | 20 | -0.272 | 0.0 | REJECTED_G2 |
| INTRADAY | mean_revert | ADAUSDT | +0.111 | 91 | +0.144 | 44 | +0.267 | 29 | +0.244 | 1.0 | REJECTED_G7 |
| INTRADAY | mean_revert | AVAXUSDT | -0.048 | 413 | -0.128 | 154 | -0.058 | 166 | -0.081 | 1.0 | REJECTED_G2 |
| INTRADAY | mean_revert | BNBUSDT | +0.021 | 417 | -0.117 | 144 | -0.045 | 144 | -0.081 | 0.0 | REJECTED_G2 |
| INTRADAY | mean_revert | BTCUSDT | -0.081 | 2378 | -0.162 | 830 | -0.010 | 754 | -0.038 | 1.0 | REJECTED_G2 |
| INTRADAY | mean_revert | DOGEUSDT | +0.028 | 113 | -0.035 | 49 | -0.326 | 42 | -0.350 | 0.0 | REJECTED_G2 |
| INTRADAY | mean_revert | ETHUSDT | -0.100 | 2876 | -0.017 | 1030 | -0.079 | 1003 | -0.102 | 1.0 | REJECTED_G2 |
| INTRADAY | mean_revert | LINKUSDT | +0.015 | 311 | -0.118 | 125 | +0.171 | 120 | +0.146 | 0.5 | REJECTED_G2 |
| INTRADAY | mean_revert | LTCUSDT | -0.018 | 79 | -0.008 | 34 | +0.294 | 30 | +0.271 | 0.5 | REJECTED_G2 |
| INTRADAY | mean_revert | SOLUSDT | -0.013 | 481 | -0.083 | 172 | -0.061 | 206 | -0.078 | 1.0 | REJECTED_G2 |
| INTRADAY | mean_revert | XRPUSDT | -0.004 | 109 | -0.210 | 41 | -0.068 | 50 | -0.097 | 1.0 | REJECTED_G2 |
| INTRADAY | trend_breakout | ADAUSDT | +0.074 | 151 | -0.165 | 44 | +0.086 | 44 | +0.072 | 0.5 | REJECTED_G2 |
| INTRADAY | trend_breakout | AVAXUSDT | +0.147 | 138 | -0.151 | 47 | -0.311 | 46 | -0.329 | 0.0 | REJECTED_G2 |
| INTRADAY | trend_breakout | BNBUSDT | +0.085 | 136 | +0.088 | 50 | +0.041 | 39 | +0.016 | 1.0 | REJECTED_G7 |
| INTRADAY | trend_breakout | BTCUSDT | +0.188 | 871 | +0.165 | 313 | +0.050 | 307 | +0.021 | 1.0 | REJECTED_G7 |
| INTRADAY | trend_breakout | DOGEUSDT | +0.258 | 146 | -0.048 | 41 | +0.114 | 44 | +0.094 | 0.5 | REJECTED_G2 |
| INTRADAY | trend_breakout | ETHUSDT | +0.210 | 930 | +0.080 | 321 | +0.080 | 326 | +0.064 | 1.0 | REJECTED_G7 |
| INTRADAY | trend_breakout | LINKUSDT | +0.183 | 179 | +0.058 | 56 | -0.061 | 56 | -0.081 | 0.5 | REJECTED_G2 |
| INTRADAY | trend_breakout | LTCUSDT | -0.011 | 168 | +0.096 | 50 | -0.033 | 49 | -0.056 | 0.5 | REJECTED_G2 |
| INTRADAY | trend_breakout | SOLUSDT | +0.143 | 259 | +0.107 | 70 | +0.082 | 75 | +0.065 | 1.0 | REJECTED_G7 |
| INTRADAY | trend_breakout | XRPUSDT | +0.226 | 145 | +0.012 | 47 | -0.064 | 49 | -0.086 | 0.5 | REJECTED_G2 |
| INTRADAY | trend_rider | ADAUSDT | -0.006 | 945 | -0.057 | 340 | +0.070 | 287 | +0.051 | 0.5 | REJECTED_G2 |
| INTRADAY | trend_rider | AVAXUSDT | +0.024 | 728 | -0.017 | 225 | -0.125 | 239 | -0.148 | 0.0 | REJECTED_G2 |
| INTRADAY | trend_rider | BNBUSDT | -0.037 | 1423 | +0.007 | 492 | -0.029 | 421 | -0.065 | 0.5 | REJECTED_G2 |
| INTRADAY | trend_rider | BTCUSDT | +0.062 | 2963 | -0.056 | 941 | -0.034 | 946 | -0.063 | 0.0 | REJECTED_G2 |
| INTRADAY | trend_rider | DOGEUSDT | +0.038 | 685 | -0.012 | 242 | -0.039 | 213 | -0.069 | 0.0 | REJECTED_G2 |
| INTRADAY | trend_rider | ETHUSDT | +0.062 | 4431 | +0.015 | 1432 | -0.065 | 1525 | -0.088 | 0.5 | REJECTED_G2 |
| INTRADAY | trend_rider | LINKUSDT | +0.028 | 525 | +0.015 | 196 | +0.067 | 186 | +0.043 | 1.0 | REJECTED_G3 |
| INTRADAY | trend_rider | LTCUSDT | -0.035 | 1625 | -0.058 | 545 | -0.063 | 519 | -0.092 | 1.0 | REJECTED_G2 |
| INTRADAY | trend_rider | SOLUSDT | +0.065 | 804 | -0.103 | 267 | -0.107 | 268 | -0.123 | 0.0 | REJECTED_G2 |
| INTRADAY | trend_rider | XRPUSDT | +0.060 | 554 | +0.070 | 177 | -0.050 | 178 | -0.076 | 0.5 | REJECTED_G2 |
| INVEST | invest_dca | PORTFOLIO | +0.009 | 2881 | +0.060 | 961 | -0.016 | 962 | +0.000 | 0.5 | REJECTED_G2 |
| INVEST | xs_momentum | PORTFOLIO | +0.177 | 223 | -0.044 | 75 | +0.112 | 75 | +0.000 | 0.5 | REJECTED_G2 |
| POSITION | trend_breakout | ADAUSDT | +0.432 | 55 | +0.576 | 24 | +0.265 | 19 | +0.243 | 1.0 | REJECTED_G7 |
| POSITION | trend_breakout | AVAXUSDT | +0.557 | 45 | -0.133 | 18 | +0.439 | 11 | +0.423 | 0.5 | REJECTED_G1 |
| POSITION | trend_breakout | BNBUSDT | +0.593 | 61 | +0.237 | 19 | +0.627 | 16 | +0.590 | 1.0 | PROMOTABLE_PAPER_ONLY |
| POSITION | trend_breakout | BTCUSDT | +0.845 | 69 | -0.136 | 21 | +0.344 | 24 | +0.304 | 0.5 | REJECTED_G2 |
| POSITION | trend_breakout | DOGEUSDT | +0.422 | 79 | +0.199 | 38 | -0.012 | 33 | -0.031 | 0.5 | REJECTED_G2 |
| POSITION | trend_breakout | ETHUSDT | +0.576 | 96 | -0.064 | 33 | +0.369 | 36 | +0.342 | 0.5 | REJECTED_G2 |
| POSITION | trend_breakout | LINKUSDT | +0.171 | 90 | -0.188 | 39 | +0.091 | 38 | +0.071 | 0.5 | REJECTED_G2 |
| POSITION | trend_breakout | LTCUSDT | +0.296 | 60 | -0.220 | 20 | +0.418 | 17 | +0.397 | 0.5 | REJECTED_G2 |
| POSITION | trend_breakout | SOLUSDT | +0.667 | 66 | -0.394 | 22 | +0.053 | 22 | +0.027 | 0.5 | REJECTED_G2 |
| POSITION | trend_breakout | XRPUSDT | +0.286 | 80 | +0.260 | 31 | +0.049 | 35 | +0.021 | 1.0 | REJECTED_G7 |
| POSITION | trend_rider | ADAUSDT | +0.243 | 186 | +0.022 | 62 | -0.176 | 66 | -0.198 | 0.5 | REJECTED_G2 |
| POSITION | trend_rider | AVAXUSDT | +0.349 | 115 | +0.014 | 54 | +0.117 | 38 | +0.098 | 1.0 | REJECTED_G7 |
| POSITION | trend_rider | BNBUSDT | +0.179 | 173 | -0.049 | 61 | +0.401 | 57 | +0.363 | 0.5 | REJECTED_G2 |
| POSITION | trend_rider | BTCUSDT | +0.149 | 174 | -0.014 | 67 | +0.009 | 60 | -0.037 | 0.5 | REJECTED_G2 |
| POSITION | trend_rider | DOGEUSDT | +0.217 | 126 | +0.499 | 52 | +0.151 | 42 | +0.129 | 1.0 | REJECTED_G7 |
| POSITION | trend_rider | ETHUSDT | +0.264 | 180 | -0.193 | 64 | +0.037 | 59 | +0.008 | 0.5 | REJECTED_G2 |
| POSITION | trend_rider | LINKUSDT | +0.199 | 155 | -0.083 | 58 | +0.082 | 50 | +0.058 | 0.5 | REJECTED_G2 |
| POSITION | trend_rider | LTCUSDT | +0.229 | 168 | -0.229 | 62 | +0.031 | 49 | +0.006 | 0.5 | REJECTED_G2 |
| POSITION | trend_rider | SOLUSDT | +0.426 | 128 | +0.247 | 40 | -0.148 | 39 | -0.174 | 0.5 | REJECTED_G2 |
| POSITION | trend_rider | XRPUSDT | +0.106 | 153 | -0.046 | 57 | -0.001 | 52 | -0.027 | 0.0 | REJECTED_G2 |
| POSITION | xs_momentum | PORTFOLIO | +0.157 | 278 | +0.018 | 96 | +0.143 | 94 | +0.000 | 1.0 | REJECTED_G7 |
| SCALP | scalp_micro | ADAUSDT | +0.000 | 0 | +0.000 | 0 | +0.000 | 0 | +0.000 | - | REJECTED_DATA |
| SCALP | scalp_micro | AVAXUSDT | +0.000 | 0 | +0.000 | 0 | +0.000 | 0 | +0.000 | - | REJECTED_DATA |
| SCALP | scalp_micro | BNBUSDT | +0.000 | 0 | +0.000 | 0 | +0.000 | 0 | +0.000 | - | REJECTED_DATA |
| SCALP | scalp_micro | BTCUSDT | +0.000 | 0 | +0.000 | 0 | +0.000 | 0 | +0.000 | - | REJECTED_DATA |
| SCALP | scalp_micro | DOGEUSDT | +0.000 | 0 | +0.000 | 0 | +0.000 | 0 | +0.000 | - | REJECTED_DATA |
| SCALP | scalp_micro | ETHUSDT | +0.000 | 0 | +0.000 | 0 | +0.000 | 0 | +0.000 | - | REJECTED_DATA |
| SCALP | scalp_micro | LINKUSDT | +0.000 | 0 | +0.000 | 0 | +0.000 | 0 | +0.000 | - | REJECTED_DATA |
| SCALP | scalp_micro | LTCUSDT | +0.000 | 0 | +0.000 | 0 | +0.000 | 0 | +0.000 | - | REJECTED_DATA |
| SCALP | scalp_micro | SOLUSDT | +0.000 | 0 | +0.000 | 0 | +0.000 | 0 | +0.000 | - | REJECTED_DATA |
| SCALP | scalp_micro | XRPUSDT | +0.000 | 0 | +0.000 | 0 | +0.000 | 0 | +0.000 | - | REJECTED_DATA |
| SWING | mean_revert | ADAUSDT | -0.166 | 248 | -0.089 | 78 | -0.248 | 89 | -0.291 | 1.0 | REJECTED_G2 |
| SWING | mean_revert | AVAXUSDT | -0.077 | 63 | -0.224 | 14 | +0.248 | 35 | +0.195 | 0.5 | REJECTED_G1 |
| SWING | mean_revert | BNBUSDT | -0.153 | 299 | -0.167 | 114 | -0.387 | 115 | -0.481 | 1.0 | REJECTED_G2 |
| SWING | mean_revert | BTCUSDT | -0.160 | 515 | -0.152 | 237 | -0.254 | 215 | -0.339 | 1.0 | REJECTED_G2 |
| SWING | mean_revert | DOGEUSDT | -0.073 | 261 | -0.046 | 80 | -0.219 | 90 | -0.269 | 1.0 | REJECTED_G2 |
| SWING | mean_revert | ETHUSDT | -0.160 | 464 | -0.090 | 209 | -0.289 | 178 | -0.356 | 1.0 | REJECTED_G2 |
| SWING | mean_revert | LINKUSDT | -0.051 | 241 | -0.242 | 76 | -0.075 | 87 | -0.122 | 1.0 | REJECTED_G2 |
| SWING | mean_revert | LTCUSDT | -0.037 | 269 | -0.122 | 92 | +0.035 | 104 | -0.026 | 0.5 | REJECTED_G2 |
| SWING | mean_revert | SOLUSDT | -0.089 | 212 | -0.091 | 99 | -0.209 | 106 | -0.271 | 1.0 | REJECTED_G2 |
| SWING | mean_revert | XRPUSDT | -0.137 | 283 | -0.217 | 90 | -0.245 | 104 | -0.315 | 1.0 | REJECTED_G2 |
| SWING | trend_breakout | ADAUSDT | +0.167 | 241 | +0.403 | 92 | +0.086 | 94 | +0.040 | 1.0 | REJECTED_G7 |
| SWING | trend_breakout | AVAXUSDT | +0.194 | 139 | +0.084 | 55 | -0.130 | 43 | -0.173 | 0.5 | REJECTED_G2 |
| SWING | trend_breakout | BNBUSDT | +0.094 | 336 | -0.124 | 127 | -0.004 | 113 | -0.071 | 0.0 | REJECTED_G2 |
| SWING | trend_breakout | BTCUSDT | +0.282 | 214 | +0.198 | 78 | +0.032 | 81 | -0.044 | 1.0 | REJECTED_G5 |
| SWING | trend_breakout | DOGEUSDT | +0.142 | 149 | +0.245 | 62 | +0.003 | 52 | -0.034 | 1.0 | REJECTED_G5 |
| SWING | trend_breakout | ETHUSDT | +0.358 | 229 | +0.331 | 88 | +0.144 | 85 | +0.095 | 1.0 | REJECTED_G7 |
| SWING | trend_breakout | LINKUSDT | +0.118 | 140 | +0.270 | 50 | -0.027 | 48 | -0.064 | 0.5 | REJECTED_G2 |
| SWING | trend_breakout | LTCUSDT | -0.002 | 135 | -0.081 | 52 | -0.191 | 47 | -0.245 | 1.0 | REJECTED_G2 |
| SWING | trend_breakout | SOLUSDT | +0.194 | 201 | +0.115 | 69 | +0.167 | 71 | +0.127 | 1.0 | REJECTED_G7 |
| SWING | trend_breakout | XRPUSDT | -0.060 | 171 | +0.223 | 69 | -0.074 | 60 | -0.121 | 0.5 | REJECTED_G2 |
| SWING | trend_rider | ADAUSDT | +0.125 | 511 | +0.035 | 164 | +0.002 | 170 | -0.048 | 1.0 | REJECTED_G5 |
| SWING | trend_rider | AVAXUSDT | +0.139 | 520 | +0.162 | 183 | -0.278 | 185 | -0.332 | 0.5 | REJECTED_G2 |
| SWING | trend_rider | BNBUSDT | +0.037 | 450 | -0.002 | 151 | -0.100 | 152 | -0.190 | 0.0 | REJECTED_G2 |
| SWING | trend_rider | BTCUSDT | +0.005 | 775 | -0.139 | 275 | -0.137 | 278 | -0.228 | 0.0 | REJECTED_G2 |
| SWING | trend_rider | DOGEUSDT | +0.052 | 438 | -0.082 | 135 | -0.089 | 145 | -0.135 | 0.0 | REJECTED_G2 |
| SWING | trend_rider | ETHUSDT | +0.047 | 802 | -0.146 | 286 | -0.229 | 283 | -0.289 | 0.0 | REJECTED_G2 |
| SWING | trend_rider | LINKUSDT | +0.046 | 510 | +0.058 | 178 | -0.095 | 164 | -0.140 | 0.5 | REJECTED_G2 |
| SWING | trend_rider | LTCUSDT | -0.089 | 1669 | -0.123 | 562 | -0.158 | 535 | -0.226 | 1.0 | REJECTED_G2 |
| SWING | trend_rider | SOLUSDT | +0.135 | 488 | -0.132 | 168 | -0.168 | 171 | -0.224 | 0.0 | REJECTED_G2 |
| SWING | trend_rider | XRPUSDT | -0.022 | 435 | -0.070 | 135 | -0.016 | 148 | -0.070 | 1.0 | REJECTED_G2 |

## 6. Portfolio simulation (all books, one account, paper)

| Metric | Value |
|---|---|
| final_equity | 1.0506 |
| total_return | 0.0506 |
| max_drawdown | 0.0213 |
| sharpe | 6.205 |
| trades_taken | 16 |
| trades_skipped | 0 |
| skip_reasons | {} |
| governor | {'equity': 1.050581, 'peak': 1.058199, 'drawdown': 0.0072, 'tripped': False, 'trip_reason': ''} |
| selected | ['POSITION|trend_breakout|BNBUSDT'] |
| dropped_g7 | ['INTRADAY|trend_breakout|BTCUSDT', 'INTRADAY|trend_breakout|ETHUSDT', 'INTRADAY|trend_breakout|SOLUSDT', 'INTRADAY|trend_breakout|BNBUSDT', 'INTRADAY|mean_revert|ADAUSDT', 'SWING|trend_breakout|ETHUSDT', 'SWING|trend_breakout|SOLUSDT', 'SWING|trend_breakout|ADAUSDT', 'POSITION|trend_breakout|XRPUSDT', 'POSITION|trend_breakout|ADAUSDT', 'POSITION|trend_rider|DOGEUSDT', 'POSITION|trend_rider|AVAXUSDT', 'POSITION|xs_momentum|PORTFOLIO'] |
| weights | {'POSITION|trend_breakout|BNBUSDT': 1.0} |
