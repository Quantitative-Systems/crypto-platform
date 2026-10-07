# QCP Phase D -- H_STRUCT_01 Forensic Execution + Geometry Sensitivity Report

**Generated**: 2026-09-18T13:26:45.681932+00:00
**Hypothesis**: H_STRUCT_01 -- FVG Tap + Breakout Close + Structural SL + Structural TP + Trail None
**Population**: BTC/USDT, ETH/USDT, SOL/USDT x SET_2, SET_3, SET_4 x DEV partition (2021-2022)
**Binding Research Firewall**: min_rr >= 4.0R (not relaxed)

> GOVERNANCE: No result in this report is declared profitable or superior. All findings are forensic observations for continued research scoping.

## D-0 -- Control Reproduction (Taker / 4R)

| Metric | Value |
|--------|-------|
| Total Trades | 77 |
| Total Gross R | +1.6425R |
| Total Net R | -22.6365R |
| Expectancy | -0.293981R/trade |
| Win Rate | 24.68% |
| Profit Factor | 0.7130 |
| Max Drawdown | 29.9631R |
| Total Friction | +24.2790R (1478.2% of gross) |
| Fee R | +0.0000R |
| Borrow R | +0.0000R |

**Funnel:**
| Stage | Count |
|-------|-------|
| Observations | 968083 |
| Regime Valid | 173484 |
| Setup Valid | 316960 |
| Entry Valid | 437721 |
| Geometry Valid | 5323 |
| Firewall Rejections | 5246 |
| Executed | 77 |

**Exit Reasons:**
| Reason | Count |
|--------|-------|
| STOP_LOSS | 55 |
| TAKE_PROFIT | 11 |
| TIME_STOP | 11 |

## D-1 -- Geometry Sensitivity (Taker Fill, Varying Target R)

Firewall fixed at 4.0R. Targets below 4R pass when structural geometry already exceeds firewall.

| Target R | Trades | Gross R | Net R | Expectancy | WR% | PF | MaxDD | Friction R | Friction% |
|----------|--------|---------|-------|------------|-----|----|-------|------------|-----------|
| 1.5R | 77 | +1.6425 | -22.6365 | -0.293981 | 24.7% | 0.713 | 29.9631 | +24.2790 | 1478.2% |
| 2.0R | 77 | +1.6425 | -22.6365 | -0.293981 | 24.7% | 0.713 | 29.9631 | +24.2790 | 1478.2% |
| 2.5R | 77 | +1.6425 | -22.6365 | -0.293981 | 24.7% | 0.713 | 29.9631 | +24.2790 | 1478.2% |
| 3.0R | 77 | +1.6425 | -22.6365 | -0.293981 | 24.7% | 0.713 | 29.9631 | +24.2790 | 1478.2% |
| 4.0R | 77 | +1.6425 | -22.6365 | -0.293981 | 24.7% | 0.713 | 29.9631 | +24.2790 | 1478.2% |

## D-2 -- Execution Friction Decomposition (Fixed 4R, Varying Fill Model)

| Fill Model | Trades | Gross R | Net R | Expectancy | WR% | PF | Fee R | Borrow R | Friction R | Friction% |
|------------|--------|---------|-------|------------|-----|----|-------|----------|------------|-----------|
| TAKER | 77 | +1.6425 | -22.6365 | -0.293981 | 24.7% | 0.713 | +0.0000 | +0.0000 | +24.2790 | 1478.2% |
| MAKER_TOUCH | 84 | +9.0295 | -9.4783 | -0.112837 | 25.0% | 0.878 | +0.0000 | +0.0000 | +18.5078 | 205.0% |
| MAKER_CONSERVATIVE | 93 | +18.2591 | -5.4172 | -0.058250 | 25.8% | 0.937 | +0.0000 | +0.0000 | +23.6763 | 129.7% |

**Causal note**: Changing entry fill model changes `entry_fill` => recomputes `risk_per_unit = |entry_fill - stop|` => recomputes planned R:R => firewall may accept/reject different trades. Gross R differences between models reflect both fill-price improvement AND different trade populations passing the firewall.

## D-3 -- Combined Matrix (Geometry x Fill Model)

| Fill Model | Target | Trades | Net R | WR% | PF | Friction R | Friction% |
|------------|--------|--------|-------|-----|----|------------|-----------|
| TAKER | 1.5R | 77 | -22.6365 | 24.7% | 0.713 | +24.2790 | 1478.2% |
| TAKER | 2.0R | 77 | -22.6365 | 24.7% | 0.713 | +24.2790 | 1478.2% |
| TAKER | 2.5R | 77 | -22.6365 | 24.7% | 0.713 | +24.2790 | 1478.2% |
| TAKER | 3.0R | 77 | -22.6365 | 24.7% | 0.713 | +24.2790 | 1478.2% |
| TAKER | 4.0R | 77 | -22.6365 | 24.7% | 0.713 | +24.2790 | 1478.2% |
| MAKER_TOUCH | 1.5R | 84 | -9.4783 | 25.0% | 0.878 | +18.5078 | 205.0% |
| MAKER_TOUCH | 2.0R | 84 | -9.4783 | 25.0% | 0.878 | +18.5078 | 205.0% |
| MAKER_TOUCH | 2.5R | 84 | -9.4783 | 25.0% | 0.878 | +18.5078 | 205.0% |
| MAKER_TOUCH | 3.0R | 84 | -9.4783 | 25.0% | 0.878 | +18.5078 | 205.0% |
| MAKER_TOUCH | 4.0R | 84 | -9.4783 | 25.0% | 0.878 | +18.5078 | 205.0% |
| MAKER_CONSERVATIVE | 1.5R | 93 | -5.4172 | 25.8% | 0.937 | +23.6763 | 129.7% |
| MAKER_CONSERVATIVE | 2.0R | 93 | -5.4172 | 25.8% | 0.937 | +23.6763 | 129.7% |
| MAKER_CONSERVATIVE | 2.5R | 93 | -5.4172 | 25.8% | 0.937 | +23.6763 | 129.7% |
| MAKER_CONSERVATIVE | 3.0R | 93 | -5.4172 | 25.8% | 0.937 | +23.6763 | 129.7% |
| MAKER_CONSERVATIVE | 4.0R | 93 | -5.4172 | 25.8% | 0.937 | +23.6763 | 129.7% |

## Forensic Interpretation

### 1. Control Reproduction Verdict

D-0 executed **77 trades** with total net R = **-22.6365R**. Compare against Phase C STRUCTURAL_REGIME_RESEARCH_REPORT.md H_STRUCT_01 row.

### 2. Gross Edge Characterisation

- Gross R pool: **+1.6425R** across 77 trades
- Friction consumed: **+24.2790R** (1478.2% of gross abs)
- Net R remaining: **-22.6365R**
- WARNING: Friction consumed > 50% of gross -- edge is friction-sensitive.

### 3. Geometry Sensitivity Observation

If trade count is approximately constant across D-1 target levels (1.5R-4R), structural geometry is the binding constraint -- almost all candidates exceed even the lowest target. If trade count drops sharply as target increases, target proximity is limiting -- few setups offer enough room for higher targets.

### 4. Execution Model Sensitivity

From D-2: if Net R differs meaningfully between fill models beyond what fee arithmetic alone predicts, fill-price changes are shifting trades in/out of the firewall -- the entry price is influencing the population of valid trades, not just the net P&L of the same trade set.

### 5. Research Governance Statement

> This Phase D forensic study does NOT declare any configuration a winner. Results are forensic inputs to the Research Governor for scoping H_STRUCT_01 further research: (a) refinement into a distinct hypothesis, (b) dismissal as insufficient gross edge, or (c) continuation into VAL/OOS partitions.
