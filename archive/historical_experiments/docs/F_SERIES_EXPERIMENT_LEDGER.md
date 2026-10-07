# F-Series Experiment Ledger (Development Partition 2021-2022)

| ID | Hypothesis | Control | N | Net R | E[R] | PF | DD | WR | Decision |
|:---|:---|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---|
| RECERT | Reproducibility: composite base + STRUCTURAL_OBJECTIVE hierarchy on current working tree | Stored certified `EXP_TARGET_STRUCTURAL_01` | 79 | -16.54R | -0.209 | 0.568 | 18.4R | 38% | **DRIFT DETECTED** |
| LEGACY_STOP | Same config + EXHAUSTIVE_STRUCTURAL stop anchor (legacy pre-repair semantics) | Stored certified file | ? | ? | ? | ? | ? | ? | PENDING |
| F1L | Legacy base + milestone 2.5R monetization | LEGACY_STOP | ? | ? | ? | ? | ? | ? | PENDING |
| F2L | Legacy base + HTF keyzone freshness 7d | LEGACY_STOP | ? | ? | ? | ? | ? | ? | PENDING |
| F2BL | Legacy base + HTF keyzone freshness 30d | LEGACY_STOP | ? | ? | ? | ? | ? | ? | PENDING |
| F4L | Legacy base + retest latency 12h | LEGACY_STOP | ? | ? | ? | ? | ? | ? | PENDING |

## Pre-registration notes

- **LEGACY_STOP**: hypothesis — the local-swing stop anchor produces micro stops swept by noise; the exhaustive structural stop (min/max over all confirmed pivots) was the certified configuration's geometry. Test: restore via flag, expect N≈20, Net R≈+3.83R.
- **F1L**: winners generate MFE 3.7–4.9R but MTF trail gives back ~45%; a pre-registered +2.5R limit exit should monetize the excursion. Projected +0.65R on the 4 ≥2.5R-MFE trades (causal replay may differ).
- **F2L**: Phase-10.2 showed monotonic improvement of a 7d zone-age gate with 0 winner loss at 100% (all 4 winners < 5.3d). On the certified base, 3 losers had 12.6–73.7d zones (−3.11R).
- **F4L**: D1-lineage retest-freshness improved expectancy; winners' retest latency is 1.2–8.5h (< 12h), losers include a 40h-latency scratch.