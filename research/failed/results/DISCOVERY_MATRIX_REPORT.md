# QCP Empirical Discovery Matrix Report

## Hypothesis Leaderboard (Ranked by Profit Factor)

| Hypothesis | Trades | Win Rate | PF | Avg Win | Avg Loss | Gross R | Net R | Firewall |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| H_MOM_BREAKOUT_1_5R | 3161 | 39.1% | 1.01 | 1.49R | 0.95R | 10.29R | -224.08R | 1.5R |
| H_TREND_PB_DYN_2R | 3843 | 40.3% | 0.96 | 1.34R | 0.94R | -78.42R | -529.67R | 2.0R |
| H_TREND_PB_ENGULF_4R | 1479 | 38.5% | 0.92 | 1.47R | 1.00R | -73.72R | -318.50R | 4.0R |
| H_CANONICAL_V21_DYN_2R | 152 | 37.5% | 0.92 | 1.55R | 1.02R | -8.08R | -37.06R | 2.0R |
| H_CANONICAL_V21_4R | 136 | 37.5% | 0.89 | 1.56R | 1.04R | -9.45R | -39.84R | 4.0R |
| H_CANONICAL_V21_2R | 150 | 37.3% | 0.87 | 1.53R | 1.04R | -12.24R | -43.67R | 2.0R |


## Analysis
This run systematically swept through canonical and alternative Strategy Grammar configurations.
We varied the `min_rr_firewall` (4R vs 2R vs 1.5R) and TP methodology to discover edges mathematically capable of 60%+ win rates.
