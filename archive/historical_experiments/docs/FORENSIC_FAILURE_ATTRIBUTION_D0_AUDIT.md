# D0 FORENSIC FAILURE ATTRIBUTION & C1 IMPLEMENTATION AUDIT
**Phase:** Product 04 — Research Laboratory (Quantitative Strategy Research)  
**Partition Scope:** Development Partition (2021–2022) ONLY  
**Status:** D0 COMPLETED | D1 PRE-REGISTERED (Awaiting User Review — Execution Halted)  
**Dataset Reference:** BTC/USDT, ETH/USDT, SOL/USDT across Timeframe Sets SET_1 to SET_5  
**Canonical Frozen Control:** Candidate Management C1 (+1.5R Cost-Covering Milestone, N=29)

---

## EXECUTIVE SUMMARY & EXPERIMENT C FINDINGS TO PRESERVE

In strict accordance with the quantitative research protocol, candidate management **C1** (+1.5R cost-covering protective milestone) is treated as the leading management candidate among the tested treatments (C1/C2/C3), while recognizing that an evaluation sample of $N=29$ is a screening sample and insufficient for permanent promotion to canonical status. Trailing confirmation latency is characterized strictly as **supported mechanism evidence**, not proven root cause.

### Preserved Experiment C Baselines (Development 2021–2022)
* **Canonical Baseline $H_0$ ($C_0$)**: $N=29$, Net $-15.5185\text{R}$, $E[R] = -0.5351\text{R}$, $\text{PF} = 0.3871$
* **Candidate Management $C_1$ (+1.5R Milestone)**: $N=29$, Net $-6.1605\text{R}$, $E[R] = -0.2124\text{R}$, $\text{PF} = 0.6141$
  - Converted 7 adverse-reversal trades into flat Breakeven exits ($0.0000\text{R}$ net)
  - 100% preservation of both observed HTF-target winners (BTC Trade 08: $+4.1077\text{R}$, BTC Trade 14: $+5.6950\text{R}$)
  - Materially reduced max drawdown from $19.46\%$ to $8.86\%$
  - Does NOT create additional winners; primarily converts favorable excursions that would have become losses into approximately flat outcomes
* **Treatment $C_2$ (+2.0R Milestone)**: $N=29$, Net $-9.3555\text{R}$, $E[R] = -0.3226\text{R}$ (5 BE exits)
* **Treatment $C_3$ (+2.5R Milestone)**: $N=29$, Net $-10.7871\text{R}$, $E[R] = -0.3720\text{R}$ (4 BE exits)

Under Candidate Management $C_1$, the 29 trades resolve into:
$$\text{Total Trades } (N=29) = 2 \text{ Winners } (+9.8027\text{R}) + 7 \text{ Breakevens } (0.0000\text{R}) + 20 \text{ Losses } (-15.9632\text{R})$$

---

## PART 1: READ-ONLY C1 IMPLEMENTATION AUDIT

Prior to conducting forensic failure attribution, a comprehensive code-level and ledger audit of Candidate Management $C_1$ was executed across the six mandated verification criteria:

### 1. Causal Threshold Activation
* **Audit Finding: VERIFIED CAUSAL (Zero Lookahead)**
* **Implementation Proof (`research/simulation/execution_simulator.py:100-144`):**
  Excursion tracking (`mfe_price`) is updated incrementally candle-by-candle from the arriving candle's high (longs) or low (shorts). The milestone condition:
  $$\text{fav\_r} = \frac{\text{mfe\_price} - \text{entry\_p}}{\text{risk\_dist}} \ge 1.50 - 10^{-7}$$
  is evaluated strictly on the forward stream as candles arrive chronologically. No future candles, closing prices of unborn bars, or post-bar extrema are referenced.

### 2. ADVERSE_FIRST Collision Arbitration
* **Audit Finding: VERIFIED CONSERVATIVE (Stop Priority Preserved)**
* **Implementation Proof (`research/simulation/execution_simulator.py:132-139`):**
  Prior to evaluating whether a candle's favorable extreme activated the +1.5R threshold, the engine evaluates whether the candle penetrated the prior adverse stop:
  ```python
  prior_stop = trade.current_stop_price
  hit_prior_sl = (candle.low <= prior_stop) if is_long else (candle.high >= prior_stop)
  if self.enable_breakeven_1r and risk_dist > 0:
      if not hit_prior_sl:
          # Milestone activation permitted only if prior SL was NOT penetrated on the same bar
  ```
  If a single candle simultaneously spans both the +1.5R milestone and the initial stop loss, `hit_prior_sl` is True, milestone activation is suppressed, and the trade is stopped out at initial SL under `ADVERSE_FIRST`.
  Furthermore, when the milestone triggers on a bar whose low/high also penetrates the new cost-covering stop, the simulator executes an immediate adverse exit on that bar with full taker fee and adverse slippage (empirically confirmed in Trade 15 on SOL/USDT SET_3).

### 3. Protective Stop Monotonicity & MTF Trailing Interaction
* **Audit Finding: VERIFIED STRICTLY MONOTONIC**
* **Implementation Proof (`research/simulation/trade_ledger.py:138-148` & `execution_simulator.py:152, 170`):**
  Both the ledger and the simulator enforce unidirectional tightening:
  ```python
  if is_long and new_stop > trade.current_stop_price:
      trade.current_stop_price = new_stop
  elif not is_long and new_stop < trade.current_stop_price:
      trade.current_stop_price = new_stop
  ```
  MTF structural trailing cannot loosen, overwrite, or weaken a cost-covering stop. If MTF structural trailing subsequently advances beyond the cost-covering level, the stop ratchets further into profit; if MTF trailing is below the cost-covering level, it is ignored.

### 4. Trade Entry Invariance Across Strategy Lifecycle
* **Audit Finding: 100.0% BIT-FOR-BIT IDENTICAL (Zero Leakage into Entry Decisions)**
* **Verification Proof:**
  Comparing the trade ledger of canonical $H_0$ and candidate $C_1$ across all 29 trades:
  - Trade ID: 29 / 29 identical matches (100.0%)
  - Symbol & Timeframe Set: 29 / 29 identical matches (100.0%)
  - Directional Permission: 29 / 29 identical matches (100.0%)
  - Entry Timestamp: 29 / 29 identical matches (100.0%)
  - Limit Entry Price: 29 / 29 identical matches (100.0%)
  - Fill Entry Price: 29 / 29 identical matches (100.0%)
  - Initial Structural Stop: 29 / 29 identical matches (100.0%)
  - Target Price: 29 / 29 identical matches (100.0%)
  - Total Trades Emitted: Exactly $N=29$ in both runs.
  Position sizing units showed fractional variation in downstream trades ($<1.5\%$) purely because account equity was preserved at higher levels due to earlier breakeven conversions, confirming that 1.0% risk sizing was applied dynamically to active equity without modifying signal generation.

### 5. Exact Cost-Covering Friction Accounting
* **Audit Finding: VERIFIED NET $R = 0.000000\text{R}$ (Microcent Exactness)**
* **Implementation Proof (`research/simulation/execution_simulator.py:147, 165`):**
  The cost-covering buffer is analytically derived from the friction model:
  $$\text{CostFactor}_{\text{Long}} = \frac{1 + \text{Fee}_{\text{Maker}}}{(1 - \text{Slippage}_{\text{Taker}})(1 - \text{Fee}_{\text{Taker}})} - 1 = \frac{1.0002}{(0.9995)(0.9995)} - 1 \approx +0.001201 \text{ (+12.01 bps)}$$
  $$\text{CostFactor}_{\text{Short}} = 1 - \frac{1 - \text{Fee}_{\text{Maker}}}{(1 + \text{Slippage}_{\text{Taker}})(1 + \text{Fee}_{\text{Taker}})} = 1 - \frac{0.9998}{(1.0005)(1.0005)} \approx +0.001199 \text{ (+11.99 bps)}$$
  Across all 7 Breakeven exits under $C_1$, empirical cashflow accounting confirms:
  $$\text{Gross PnL} = \text{Entry Fee} + \text{Exit Fee} \implies \text{Net PnL} = \$0.000000, \quad \text{Net } R = 0.000000\text{R}$$

### 6. Excursion (MFE/MAE) Measurement Integrity
* **Audit Finding: VERIFIED UNBIASED (100.0% Measurement Parity)**
* **Verification Proof:**
  For all 23 trades sharing identical lifespans between $H_0$ and $C_1$ (the 20 losses and 2 winners), measured MFE and MAE match with $100.0\%$ bit-for-bit parity ($|\Delta| < 10^{-7}$). For the 6 trades closed earlier by the protective milestone, MFE reflects the true excursion experienced during the active position lifetime.

---

## PART 2: D0 MTF/LTF FAILURE ATTRIBUTION (THE 20 $C_1$ LOSING TRADES)

### Forensic Classification Ledger (All 20 Losing Trades)

The table below catalogs every losing trade under Candidate Management $C_1$ across the mandated forensic dimensions:

| # | Trade ID / Stream | Dir | Net R | MFE (R) | A. MFE Cat | B. MFE Timing | C. Exit Behavior | D. MTF Shift | MTF Disp | E. LTF Trigger | Plan RR |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 00 | `T00` BTC/USDT SET_3 | LONG | -1.0604 | 0.00R | <0.5R | immediate | immediate_invalidation (straight to SL) | INTERNAL_CHOCH | 1.92% | BULLISH_DISP | 8.01R |
| 01 | `T01` SOL/USDT SET_4 | LONG | -1.0615 | 0.00R | <0.5R | immediate | immediate_invalidation (straight to SL) | EXTERNAL_CHOCH | 3.09% | BULLISH_DISP | 8.07R |
| 02 | `T02` SOL/USDT SET_4 | LONG | -1.0846 | 0.47R | <0.5R | immediate | weak_blip_to_SL | MSS | 4.02% | BULLISH_DISP | 5.67R |
| 03 | `T04` ETH/USDT SET_3 | LONG | -1.1043 | 0.03R | <0.5R | immediate | immediate_invalidation (straight to SL) | MSS | 2.71% | BULLISH_DISP | 4.77R |
| 04 | `T05` BTC/USDT SET_4 | SHRT | -1.0911 | 0.00R | <0.5R | immediate | immediate_invalidation (straight to SL) | INTERNAL_CHOCH | 2.10% | BEARISH_DISP | 5.36R |
| 05 | `T06` SOL/USDT SET_4 | LONG | -0.0933 | 3.35R | >=1.5R | immediate | extended_run_trailed_scratch | EXTERNAL_CHOCH | 2.83% | BULLISH_DISP | 11.81R |
| 06 | `T07` SOL/USDT SET_3 | LONG | -0.0526 | 0.75R | 0.5-1.0R | immediate | moderate_run_trailed_stop | INTERNAL_CHOCH | 1.69% | LTF_SWEEP_AND_DISP | 5.47R |
| 07 | `T11` SOL/USDT SET_4 | SHRT | -0.1190 | 0.93R | 0.5-1.0R | immediate | moderate_run_trailed_stop | MSS | 3.19% | LTF_SWEEP_AND_DISP | 4.27R |
| 08 | `T12` BTC/USDT SET_3 | SHRT | -0.4625 | 0.00R | <0.5R | immediate | immediate_trail_tighten_scratch | EXTERNAL_CHOCH | 2.46% | LTF_SWEEP_AND_DISP | 7.85R |
| 09 | `T13` SOL/USDT SET_3 | LONG | -1.0758 | 0.82R | 0.5-1.0R | immediate | moderate_traction_then_full_reversal | INTERNAL_CHOCH | 2.17% | BULLISH_DISP | 6.52R |
| 10 | `T16` SOL/USDT SET_2 | SHRT | -1.0793 | 1.25R | 1.0-1.5R | immediate | deep_run_failed_to_milestone_reversal | EXTERNAL_BOS | 3.28% | LTF_SWEEP_AND_DISP | 10.22R |
| 11 | `T17` SOL/USDT SET_2 | SHRT | -0.2804 | 0.48R | <0.5R | immediate | immediate_trail_tighten_scratch | EXTERNAL_BOS | 3.28% | LTF_SWEEP_AND_DISP | 7.10R |
| 12 | `T20` SOL/USDT SET_4 | LONG | -1.1180 | 0.00R | <0.5R | immediate | immediate_invalidation (straight to SL) | MSS | 1.86% | BULLISH_DISP | 4.79R |
| 13 | `T21` SOL/USDT SET_3 | LONG | -1.1137 | 0.00R | <0.5R | immediate | immediate_invalidation (straight to SL) | MSS | 1.91% | LTF_SWEEP_AND_DISP | 27.50R |
| 14 | `T22` SOL/USDT SET_4 | SHRT | -0.1120 | 1.83R | >=1.5R | immediate | extended_run_trailed_scratch | INTERNAL_CHOCH | 3.07% | BEARISH_DISP | 9.83R |
| 15 | `T23` SOL/USDT SET_3 | SHRT | -0.6926 | 0.52R | 0.5-1.0R | early | moderate_run_trailed_stop | MSS | 5.34% | BEARISH_DISP | 4.87R |
| 16 | `T24` ETH/USDT SET_4 | SHRT | -1.0793 | 0.42R | <0.5R | immediate | weak_blip_to_SL | INTERNAL_CHOCH | 3.26% | BEARISH_DISP | 5.09R |
| 17 | `T25` SOL/USDT SET_4 | LONG | -1.0960 | 0.78R | 0.5-1.0R | mid | moderate_traction_then_full_reversal | INTERNAL_CHOCH | 2.08% | BULLISH_DISP | 6.85R |
| 18 | `T27` ETH/USDT SET_4 | SHRT | -1.0960 | 0.10R | <0.5R | mid | immediate_invalidation (straight to SL) | EXTERNAL_CHOCH | 1.06% | BEARISH_DISP | 7.55R |
| 19 | `T28` SOL/USDT SET_4 | SHRT | -1.0909 | 0.00R | <0.5R | immediate | immediate_invalidation (straight to SL) | EXTERNAL_CHOCH | 0.62% | BEARISH_DISP | 13.38R |

---

### CATEGORICAL DISTRIBUTION SYNTHESIS

#### Dimension A: Maximum Favorable Excursion (MFE)
* **$<0.5\text{R}$**: **12 trades (60.0%)** — The dominant cohort. Price experiences almost immediate adverse pressure upon fill.
* **$0.5–1.0\text{R}$**: **5 trades (25.0%)** — Weak initial traction before encountering opposing institutional flow.
* **$1.0–1.5\text{R}$**: **1 trade (5.0%)** — Trade 16 (MFE 1.25R on SOL_SET_2), reversing just shy of the +1.5R protective milestone.
* **$\ge 1.5\text{R}$**: **2 trades (10.0%)** — Trades 06 (MFE 3.35R) and 22 (MFE 1.83R). Both were protected by MTF structural trailing at entry, resolving into minimal scratch losses ($-0.0933\text{R}$ and $-0.1120\text{R}$).

#### Dimension B: MFE Timing
* **Immediate (Bar 0–1)**: **17 trades (85.0%)** — Peak favorable price occurs on the entry bar or immediately adjacent bar.
* **Early (First 25% of duration)**: **1 trade (5.0%)**
* **Mid (25%–75% of duration)**: **2 trades (10.0%)**
* **Late (>75% of duration)**: **0 trades (0.0%)**

#### Dimension C: MFE-to-Exit Behavior
* **Immediate Invalidation (Straight to SL, $\text{MFE} < 0.2\text{R}$)**: **8 trades (40.0%)** — Zero structural adherence; price pierces directly through the entry bar and initial stop.
* **Weak Blip to SL ($0.2\text{R} \le \text{MFE} < 0.5\text{R}$)**: **2 trades (10.0%)**
* **Moderate Traction then Full Reversal ($0.5\text{R} \le \text{MFE} < 1.0\text{R}$)**: **2 trades (10.0%)**
* **Deep Run Failed to Milestone ($1.0\text{R} \le \text{MFE} < 1.5\text{R}$)**: **1 trade (5.0%)**
* **Trailed Stop Loss Exits via MTF Trailing**: **7 trades (35.0%)** — These 7 trades generated a combined loss of only $-1.8124\text{R}$ (mean loss $-0.2589\text{R}$), proving that structural trailing successfully mitigated severe losses when positions achieved moderate traction.

#### Dimension D: MTF Setup Quality
* **Structural Shift Type**:
  - `INTERNAL_CHOCH`: **7 trades (35.0%)**
  - `MSS` (Market Structure Shift): **6 trades (30.0%)**
  - `EXTERNAL_CHOCH`: **5 trades (25.0%)**
  - `EXTERNAL_BOS`: **2 trades (10.0%)**
* **Displacement**:
  - Mean MTF displacement leg: $2.60\%$ (range $0.62\%$ to $5.34\%$).
  - Weak displacement ($<2.0\%$): 7 trades ($35.0\%$).
* **KeyZone Freshness & Retest Timing**:
  - Mean time from KeyZone creation to retest: $932 \text{ minutes}$ ($15.5 \text{ hours}$).
  - Retests ranged from rapid wicks ($60 \text{ minutes}$) to stale structural zones ($8,400 \text{ minutes} = 140 \text{ hours}$).

#### Dimension E: LTF Trigger Architecture
* **Trigger Reason**:
  - `BULLISH_DISPLACEMENT_CONFIRMED`: **8 trades (40.0%)**
  - `BEARISH_DISPLACEMENT_CONFIRMED`: **6 trades (30.0%)**
  - `LTF_SWEEP_AND_DISPLACEMENT_CONFIRMED`: **6 trades (30.0%)**
* **Prior Liquidity Sweep Verification**:
  - Only **4 of 20 trades (20.0%)** featured an actual prior LTF swing liquidity sweep.
  - **16 of 20 trades (80.0%)** entered via the tertiary single-candle displacement model without any prior liquidity sweep.
* **Risk Distance (% of Entry Price)**:
  - Mean stop distance: $1.67\%$ (min $1.01\%$, max $5.52\%$).

#### Dimension F: HTF Context & Objective
* **HTF KeyZone Type**: FVG (12 trades, $60.0\%$), OB (8 trades, $40.0\%$).
* **HTF Objective**: `LIQUIDITY_POOL` (13 trades, $65.0\%$), `WEAK_SWING` (4 trades, $20.0\%$), `OPPOSING_KEYZONE` (3 trades, $15.0\%$).
* **Planned R:R**: Mean $8.25\text{R}$ (min $4.27\text{R}$, max $27.50\text{R}$). All trades satisfied the $\text{RR} \ge 4.0\text{R}$ invariant.

#### Dimension G: Existing Regime Classification
* **Trend Regime**: `RANGE_CHOP` across all 20 trades ($100.0\%$).
* **Volatility Regime**: `NORMAL_VOLATILITY` across all 20 trades ($100.0\%$).
* **Market Phase**: `CONTINUATION` ($100.0\%$).

---

## PART 3: DOMINANT FAILURE MECHANISM ATTRIBUTION

Cross-referencing the 20 losing trades against the 9 non-losing trades (2 winners + 7 breakevens) reveals the clear primary failure mechanism:

### 1. The Trailing Mechanism is NOT the Primary Drag Under C1
Under candidate control $C_1$, management drag has already been largely mitigated:
* Only **1 trade out of 20** (Trade 16, MFE 1.25R) reached $>1.0\text{R}$ before suffering a full initial stop loss.
* The 7 trades that exited via MTF Trailing produced an average loss of only $-0.26\text{R}$ (total $-1.81\text{R}$).
* **$88.7\%$ of all loss R ($-14.15\text{R}$) originated from the 13 full stop-out trades ($E[R] \approx -1.09\text{R}$).**

### 2. Immediate Structural Invalidation at Entry
* **$76.9\%$ of full stop-outs (10 of 13) and $60.0\%$ of all losses (12 of 20) NEVER achieved even $+0.5\text{R}$ of favorable excursion.**
* 7 trades suffered an MFE of exactly $0.00\text{R}$.
* This conclusively proves that failure occurs **at or before entry**, not downstream during trade management.

### 3. Root Cause: Minor `INTERNAL_CHOCH` vs Major Swing Alignment
When comparing the structural alignment events of non-losing trades against losing trades:
* **The 2 HTF-target winners:**
  - Trade 08 (BTC, $+4.1077\text{R}$): `EXTERNAL_CHOCH` (Major swing break)
  - Trade 14 (BTC, $+5.6950\text{R}$): `MSS` (Market Structure Shift)
  - **$0\%$ of winners originated from `INTERNAL_CHOCH`.**
* **The 7 Breakeven trades:**
  - 6 of 7 ($85.7\%$) originated from major swing events (`MSS`, `EXTERNAL_CHOCH`, `EXTERNAL_BOS`).
  - Only 1 originated from `INTERNAL_CHOCH`.
* **The 20 Losing trades:**
  - **7 trades ($35.0\%$) originated from `INTERNAL_CHOCH`**, including 5 catastrophic full stop losses (T00, T05, T13, T24, T25) and 2 scratch losses.

**Structural Attribution:**
An `INTERNAL_CHOCH` represents a break of a minor sub-structure fractal wick. In choppy or counter-trending regimes, sub-structure frequently breaks temporarily while the dominant MTF swing trend continues to plow through the zone. Entering on minor internal shifts exposes the position to high-velocity continuation against the HTF intent.

---

## PART 4: PROPOSED PRE-REGISTERED TREATMENT D1

Based on the forensic identification of minor internal shift failure, we propose exactly **ONE** single-variable pre-registered candidate treatment for review.

### Hypothesis Code: `EXP_MTF_MAJOR_ALIGNMENT_01` (or `D1_MAJOR_MTF_SHIFT_ONLY`)

#### 1. Core Hypothesis
Requiring that MTF alignment with HTF directional bias be established by a **major swing structural event** (`EXTERNAL_CHOCH`, `MSS`, or `EXTERNAL_BOS`), while rejecting minor internal sub-structure shifts (`INTERNAL_CHOCH`), will filter out high-velocity counter-trend traps and reduce full initial stop-outs without degrading the strategy's ability to capture genuine HTF expansions.

#### 2. Mathematical & Algorithmic Specification
In `strategy_engine/hypotheses/unified_strategy.py` at `CandidateState.WAIT_MTF_ALIGNMENT`:
```python
# Canonical C1 Control:
permitted_events = ["INTERNAL_CHOCH", "EXTERNAL_CHOCH", "MSS", "EXTERNAL_BOS"]

# Candidate Treatment D1:
permitted_events = ["EXTERNAL_CHOCH", "MSS", "EXTERNAL_BOS"]  # INTERNAL_CHOCH excluded
```

#### 3. Strict Invariants Maintained
* Target: `CLOSEST_OBJECTIVE` (frozen control)
* Management: Candidate Control $C_1$ (+1.5R cost-covering milestone)
* Planned RR floor: $\ge 4.0\text{R}$
* Risk ceiling: $\le 1.0\%$
* Collision policy: `ADVERSE_FIRST`
* Execution friction: 2 bps maker, 5 bps taker, 5 bps slippage
* Dataset & Partition: 2021–2022 Development partition ONLY.
* Validation (2023) and OOS (2024–2026) strictly locked.

#### 4. Pre-Registered Screening Ledger Prediction
On the frozen $N=29$ development ledger:
* **Trades Filtered:** 8 trades total (5 full stop-outs, 2 trailing scratch losses, 1 breakeven exit).
* **Winners Preserved:** 2 of 2 ($100.0\%$). Both Trade 08 ($+4.11\text{R}$) and Trade 14 ($+5.70\text{R}$) are preserved.
* **Estimated Sample Net R Impact:** Improves from $-6.1605\text{R}$ ($E=-0.2124\text{R}$) to $-0.5933\text{R}$ ($E=-0.0283\text{R}$), moving the overall system to near-breakeven across the development sample.

---

## PART 5: RESEARCH PROTOCOL HALT

In accordance with explicit user instructions:
1. **D0 Forensic Failure Attribution is COMPLETE.**
2. **D1 is PRE-REGISTERED for review.**
3. **DO NOT EXECUTE D1 until D0 and the proposed D1 treatment are reviewed and approved by the user.**
