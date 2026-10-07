# Independent Adversarial Validation & Multiple-Testing Audit Report

**Status:** Certified Independent Quantitative Audit
**Streams Audited:** 40
**Hypotheses Space:** 40

## 1. Classification Summary by Tier

| Institutional Tier | Count | Description |
|---|---|---|
| **ELITE** | **6** | High positive expectancy, confirmed OOS, high cost resilience, low concentration, statistical significance. |
| **ROBUST** | **10** | Positive expectancy, surviving bootstrap, FDR, OOS, and cost stress. |
| **CONDITIONAL** | **11** | Positive signal but wider confidence intervals or sensitive to multiple-testing penalty. |
| **INSUFFICIENT_DATA** | **4** | Opportunity scarcity (N < 25), primarily macro Set 1. |
| **UNSTABLE** | **3** | Edge collapses when top winners are removed or fails OOS. |
| **ECONOMICALLY_UNTRADABLE** | **6** | Friction exceeds edge; break-even friction multiple < 1.0x (e.g. Set 5). |

## 2. Stream-by-Stream Independent Audit Scorecard

| Stream ID | Set | Phase | Trades | Classification | Boot E[R] (95% CI) | Break-Even Friction | Ex-Top2 E[R] | Top 2 Conc % | Target Struct % |
|---|---|---|---|---|---|---|---|---|---|
| `BTC_SET_2_HYP_B_CONTINUATION` | SET_2 | CONTINUATION | 301 | **ELITE** | +1.3645R [+0.86, +1.88] | 40.1x | +1.2535R | 7.4% | 84.7% |
| `ETH_SET_2_HYP_A_PULLBACK` | SET_2 | PULLBACK | 272 | **ELITE** | +1.3061R [+0.89, +1.79] | 38.0x | +1.1932R | 7.0% | 87.9% |
| `ETH_SET_2_HYP_B_CONTINUATION` | SET_2 | CONTINUATION | 298 | **ELITE** | +1.0802R [+0.79, +1.37] | 31.7x | +1.0000R | 5.9% | 84.9% |
| `SOL_SET_3_HYP_A_PULLBACK` | SET_3 | PULLBACK | 707 | **ELITE** | +0.8743R [+0.62, +1.19] | 26.2x | +0.8460R | 3.1% | 86.0% |
| `ETH_SET_3_HYP_A_PULLBACK` | SET_3 | PULLBACK | 1006 | **ELITE** | +0.6807R [+0.51, +0.87] | 20.5x | +0.6436R | 3.8% | 86.9% |
| `BTC_SET_3_HYP_A_PULLBACK` | SET_3 | PULLBACK | 989 | **ELITE** | +0.6259R [+0.46, +0.82] | 18.9x | +0.6007R | 2.4% | 80.5% |
| `BTC_SET_2_HYP_A_PULLBACK` | SET_2 | PULLBACK | 276 | **ROBUST** | +0.8073R [+0.49, +1.16] | 24.1x | +0.6337R | 15.6% | 81.2% |
| `SOL_SET_2_HYP_B_CONTINUATION` | SET_2 | CONTINUATION | 162 | **ROBUST** | +0.7324R [+0.24, +1.31] | 22.2x | +0.6454R | 9.0% | 80.2% |
| `SOL_SET_2_HYP_A_PULLBACK` | SET_2 | PULLBACK | 161 | **ROBUST** | +0.6967R [+0.39, +1.01] | 20.9x | +0.6127R | 9.0% | 76.4% |
| `SOL_SET_4_HYP_B_CONTINUATION` | SET_4 | CONTINUATION | 493 | **ROBUST** | +0.4507R [+0.27, +0.67] | 13.8x | +0.4028R | 5.3% | 84.6% |
| `SOL_SET_3_HYP_B_CONTINUATION` | SET_3 | CONTINUATION | 678 | **ROBUST** | +0.4343R [+0.29, +0.58] | 13.5x | +0.4069R | 3.7% | 78.2% |
| `BTC_SET_3_HYP_B_CONTINUATION` | SET_3 | CONTINUATION | 1074 | **ROBUST** | +0.4206R [+0.29, +0.56] | 13.0x | +0.3998R | 2.5% | 78.0% |
| `SOL_SET_4_HYP_A_PULLBACK` | SET_4 | PULLBACK | 364 | **ROBUST** | +0.4116R [+0.15, +0.70] | 12.7x | +0.3665R | 4.8% | 69.2% |
| `ETH_SET_4_HYP_B_CONTINUATION` | SET_4 | CONTINUATION | 433 | **ROBUST** | +0.3782R [+0.14, +0.63] | 11.7x | +0.3189R | 6.0% | 83.4% |
| `ETH_SET_3_HYP_B_CONTINUATION` | SET_3 | CONTINUATION | 970 | **ROBUST** | +0.3681R [+0.24, +0.50] | 11.6x | +0.3295R | 4.9% | 79.7% |
| `ETH_SET_4_HYP_A_PULLBACK` | SET_4 | PULLBACK | 389 | **ROBUST** | +0.2530R [+0.03, +0.52] | 8.2x | +0.2134R | 5.0% | 73.3% |
| `BNB_SET_1_HYP_B_CONTINUATION` | SET_1 | CONTINUATION | 32 | **CONDITIONAL** | +1.4700R [+0.77, +2.16] | 43.1x | +1.0711R | 25.7% | 81.2% |
| `ETH_SET_1_HYP_B_CONTINUATION` | SET_1 | CONTINUATION | 35 | **CONDITIONAL** | +1.4357R [+0.93, +2.01] | 42.3x | +1.1736R | 21.0% | 94.3% |
| `BNB_SET_4_HYP_A_PULLBACK` | SET_4 | PULLBACK | 39 | **CONDITIONAL** | +1.3446R [+0.47, +2.40] | 39.2x | +1.0661R | 18.8% | 61.5% |
| `SOL_SET_5_HYP_B_CONTINUATION` | SET_5 | CONTINUATION | 42 | **CONDITIONAL** | +0.7109R [-0.08, +1.70] | 20.8x | +0.5018R | 18.3% | 78.6% |
| `BNB_SET_5_HYP_A_PULLBACK` | SET_5 | PULLBACK | 43 | **CONDITIONAL** | +0.4832R [-0.15, +1.16] | 14.9x | +0.2656R | 26.4% | 58.1% |
| `BTC_SET_4_HYP_B_CONTINUATION` | SET_4 | CONTINUATION | 38 | **CONDITIONAL** | +0.4662R [-0.37, +1.47] | 14.4x | +0.0853R | 37.1% | 78.9% |
| `BTC_SET_5_HYP_A_PULLBACK` | SET_5 | PULLBACK | 50 | **CONDITIONAL** | +0.4250R [-0.17, +1.08] | 13.1x | +0.2573R | 17.1% | 86.0% |
| `BNB_SET_2_HYP_A_PULLBACK` | SET_2 | PULLBACK | 33 | **CONDITIONAL** | +0.3937R [+0.03, +0.77] | 12.1x | +0.0990R | 38.3% | 78.8% |
| `BTC_SET_1_HYP_A_PULLBACK` | SET_1 | PULLBACK | 29 | **CONDITIONAL** | +0.3393R [-0.07, +0.77] | 10.9x | +0.0721R | 40.6% | 89.7% |
| `BNB_SET_2_HYP_B_CONTINUATION` | SET_2 | CONTINUATION | 50 | **CONDITIONAL** | +0.3308R [-0.18, +0.93] | 10.8x | +0.0305R | 45.0% | 92.0% |
| `BNB_SET_3_HYP_B_CONTINUATION` | SET_3 | CONTINUATION | 83 | **CONDITIONAL** | +0.3241R [-0.06, +0.77] | 10.4x | +0.1205R | 25.5% | 67.5% |
| `SOL_SET_1_HYP_A_PULLBACK` | SET_1 | PULLBACK | 14 | **INSUFFICIENT_DATA** | +3.7439R [+0.25, +9.36] | 106.3x | +0.1867R | 88.6% | 100.0% |
| `BNB_SET_1_HYP_A_PULLBACK` | SET_1 | PULLBACK | 13 | **INSUFFICIENT_DATA** | +1.1888R [+0.26, +2.03] | 35.3x | +0.4334R | 49.9% | 61.5% |
| `ETH_SET_1_HYP_A_PULLBACK` | SET_1 | PULLBACK | 22 | **INSUFFICIENT_DATA** | -0.0904R [-0.65, +0.60] | 0.0x | -0.5035R | 74.5% | 95.5% |
| `SOL_SET_1_HYP_B_CONTINUATION` | SET_1 | CONTINUATION | 12 | **INSUFFICIENT_DATA** | -0.3177R [-0.75, +0.20] | 0.0x | -0.6251R | 76.7% | 75.0% |
| `BTC_SET_1_HYP_B_CONTINUATION` | SET_1 | CONTINUATION | 35 | **UNSTABLE** | +0.1597R [-0.30, +0.73] | 5.8x | -0.0617R | 34.5% | 60.0% |
| `BNB_SET_4_HYP_B_CONTINUATION` | SET_4 | CONTINUATION | 69 | **UNSTABLE** | +0.1135R [-0.23, +0.47] | 4.2x | -0.0136R | 16.7% | 87.0% |
| `BTC_SET_5_HYP_B_CONTINUATION` | SET_5 | CONTINUATION | 48 | **UNSTABLE** | +0.0351R [-0.61, +0.67] | 1.8x | -0.1482R | 29.4% | 70.8% |
| `BTC_SET_4_HYP_A_PULLBACK` | SET_4 | PULLBACK | 68 | **ECONOMICALLY_UNTRADABLE** | -0.0028R [-0.38, +0.40] | 1.0x | -0.1292R | 21.3% | 83.8% |
| `ETH_SET_5_HYP_B_CONTINUATION` | SET_5 | CONTINUATION | 72 | **ECONOMICALLY_UNTRADABLE** | -0.0312R [-0.35, +0.34] | 0.0x | -0.1908R | 34.6% | 87.5% |
| `BNB_SET_3_HYP_A_PULLBACK` | SET_3 | PULLBACK | 75 | **ECONOMICALLY_UNTRADABLE** | -0.0547R [-0.34, +0.23] | 0.0x | -0.1696R | 28.6% | 97.3% |
| `BNB_SET_5_HYP_B_CONTINUATION` | SET_5 | CONTINUATION | 53 | **ECONOMICALLY_UNTRADABLE** | -0.1210R [-0.59, +0.34] | 0.0x | -0.3121R | 32.0% | 88.7% |
| `ETH_SET_5_HYP_A_PULLBACK` | SET_5 | PULLBACK | 41 | **ECONOMICALLY_UNTRADABLE** | -0.2164R [-0.55, +0.16] | 0.0x | -0.4520R | 50.6% | 70.7% |
| `SOL_SET_5_HYP_A_PULLBACK` | SET_5 | PULLBACK | 39 | **ECONOMICALLY_UNTRADABLE** | -0.2435R [-0.74, +0.33] | 0.0x | -0.5014R | 48.9% | 79.5% |
