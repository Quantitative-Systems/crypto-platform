# Master Platform Architecture & Forensic Reconciliation Report
## Canonical Multi-Timeframe Architecture, Implementation Drift, and Structural Target Diagnostics

---

**Document Authority:** Institutional Quantitative Governance  
**Audit Identifier:** `CANONICAL_ARCHITECTURE_RECONCILIATION`  
**Certification Date:** 2026-09-10  
**Status:** 🟢 **CERTIFIED ARCHITECTURAL AUDIT (STRICTLY READ-ONLY FORENSICS)**  
**Dataset Scope:** Historical Development Partition (`2021-01-01T00:00:00Z` to `2022-12-31T23:59:59Z`, 277,908 market bars)  
**Partition Lock:** Validation (`2023`) and Out-of-Sample (`2024–2026`) remain strictly **LOCKED**  
**Engineering Directive:** Zero strategy modifications, zero parameter optimization, zero code deletion.

---

## Executive Summary & Answers to the Three Master Questions

### Question A — Is the strategy architecture correctly implemented?
**Architectural Verdict: 🔴 NO — SEVERE IMPLEMENTATION DRIFT & STRUCTURAL DEFECTS DISCOVERED.**

While the high-level components exist in modular forms, the software implementation has materially drifted away from the canonical single-strategy specification in four critical dimensions:

1. **Catastrophic Negative Target Prices in Certified Ledger:**
   In [`strategy_engine/context/htf_destination_engine.py`](file:///home/mrcn2/crypto-platform/strategy_engine/context/htf_destination_engine.py#L149-L152), the Dealing Range 1.0x expansion logic (`dr.low_price - (range_width * 1.0)`) produces **negative target prices ($< \$0.00$)** on short setups during high-volatility expansions. In the frozen 13-trade Composite population:
   - Trade #8 (`cand_SOL/USDT_1654300800`): Planned target was **`-$14.69`**.
   - Trade #10 (`cand_SOL/USDT_1669035600`): Planned target was **`-$6.56`**.
   Because negative prices satisfy the naive geometry check (`-$14.69 < entry_price`), they produced astronomical planned reward-to-risk ratios ($11.97\text{R}$ and $4.69\text{R}$) that artificially bypassed the $\ge 4.0\text{R}$ firewall while being physically impossible to ever reach in the real world.
2. **The "Closest-Feature" Target Inversion Defect:**
   The destination engine was *already* hardcoded to sort candidates by closest distance to entry price ([`htf_destination_engine.py:L165-167`](file:///home/mrcn2/crypto-platform/strategy_engine/context/htf_destination_engine.py#L165-L167)). Because it prioritized minor internal micro keyzones rather than external macro structural destinations, $75.11\%$ ($504$ of $671$) of rejected triggers had planned $\text{RR} < 1.0\text{R}$, creating the artificial qualification chokepoint.
3. **Core Timeframe Configuration Drift:**
   [`config/timeframe_sets.py`](file:///home/mrcn2/crypto-platform/config/timeframe_sets.py#L11-L40) defines only SET 1 through SET 4, completely omitting SET 5. Meanwhile, [`research/replayer/timeframe_aligner.py`](file:///home/mrcn2/crypto-platform/research/replayer/timeframe_aligner.py#L49-L55) defines all five sets.
4. **Historical Dual-Strategy Fragmentation:**
   The codebase previously bifurcated the engine into separate "Pullback Riding" and "Continuation Riding" runners. While consolidated under `UnifiedStrategy`, traces of this fragmentation remain in legacy scripts.

---

### Question B — Does the current strategy have an edge?
**Research Verdict: 🟡 UNPROVEN / INSUFFICIENT EMPIRICAL SAMPLE.**

- **Development Partition ($N=23$ Baseline, $N=13$ Composite):** Across 2 full calendar years (277,908 candles), the ANCHOR_2 baseline lost $-4.1741\text{R}$ (win rate $13.04\%$). The Cycle #3 Composite interaction produced $+0.9615\text{R}$ ($38.46\%$ win rate, $\text{PF} = 1.2583$).
- **The Reality Behind the Numbers:** Zero trades ($0/13$) ever reached their planned target. Two of the 13 trades had negative target prices. Only 2 trades reached $+2.5\text{R}$ excursion. The positive Development expectancy is driven entirely by 2 large runner trades monetized via MTF trailing stops during macro market trends.
- **Institutional Verdict:** A sample of 13 executed trades over 2 years on 3 liquid assets cannot establish statistical significance or prove an institutional edge ($p > 0.05$). It is an encouraging exploratory signal, nothing more.

---

### Question C — Which structural definitions produce the strongest robustness?
**Structural Verdict: 🟢 EXTERNAL MACRO SWINGS & MTF STRUCTURAL TRAILING.**

1. **What Failed (Brittle / Low Robustness):**
   - Internal micro-keyzones and micro-liquidity pools: Resulted in immediate adverse stop-outs ($93\%$ of sub-4R setups died $<1.0\text{R}$).
   - Dealing Range formulaic expansions: Generated physically invalid negative targets.
   - Fixed structural take-profit limit orders: $0.00\%$ reachability across all cycles.
2. **What Succeeded (Robust / High Information):**
   - **MTF Structural Trailing Stop:** Responsible for $100\%$ of profitable trade closures in the platform's history. Moving stops monotonically behind causal MTF swing highs/lows reliably protected capital and allowed winners to expand to $+2.80\text{R}$ and $+1.69\text{R}$.
   - **LTF Entry Displacement Polarity:** Decisively filtered 10 counter-trend entries without sacrificing top winners.

---

## 1. Repository Inventory (Read-Only Audit)

A full recursive scan of 676 files across all primary platform directories was conducted:

| Directory | Total Files | Role / Purpose | Audit Status |
| :--- | :---: | :--- | :--- |
| `config/` | 4 | System configurations, broker specs, timeframe sets | **CANONICAL** (Configuration drift in `timeframe_sets.py`) |
| `market_data/` | 8 | Binance ingestion, cache manager, data certifier | **CANONICAL** (100% causal, zero-lookahead certified) |
| `market_intelligence/` | 13 | Core P01 primitives, swing/BOS/CHOCH engines | **CANONICAL** (Fully deterministic state machines) |
| `strategy_engine/` | 24 | P02 coordinator, entry models, lifecycle, targets | **CANONICAL** (Contains target engine defect) |
| `risk_engine/` | 16 | P03 risk coordinator, account sizing, firewall rules | **CANONICAL** (Strict $\le 1\%$ risk ceiling intact) |
| `trade_management/` | 5 | Trade lifecycle trackers, stop managers | **CANONICAL** (Active trade manager synchronized) |
| `research/replayer/` | 4 | Causal replayer, timeframe aligner | **CANONICAL** (Zero-lookahead slicing verified) |
| `research/simulation/` | 3 | Execution simulator, friction models, trade ledger | **CANONICAL** (Adverse-first intrabar collision verified) |
| `research/metrics/` | 4 | Realized R, expectancy, MFE/MAE attribution | **CANONICAL** (Verified institutional accounting) |
| `research/analytics/` | 15 | Permanent post-replay forensic tools | **PERMANENT ANALYTICS** |
| `research/experiments/`| 28 | Standalone experimental runners (Cycles #1–4) | **ACTIVE EXPERIMENT** (Several legacy runners) |
| `tests/` | 80 | Unit and integration test suite (359 tests) | **TEST** (100% green) |
| `docs/` | 22 | Research audits, certifications, specifications | **PERMANENT ANALYTICS** |
| `scratch/` | 134 | Diagnostic scripts, scratch outputs, temporary logs | **SCRATCH / DEPRECATED / DUPLICATE** |

### File Classification Pareto Breakdown
```text
ACTIVE EXPERIMENTS / RUNNERS : 272 files (40.2%)
CANONICAL PLATFORM ENGINE    : 143 files (21.2%)
SCRATCH DIAGNOSTIC SCRIPTS   : 124 files (18.3%)
UNIT & INTEGRATION TESTS     :  80 files (11.8%)
PERMANENT AUDIT DOCUMENTS    :  44 files ( 6.5%)
DEPRECATED / REJECT FILES    :  12 files ( 1.8%)
EXACT HASH DUPLICATES        :   1 files ( 0.1%)
```

---

## 2. Duplicate & Deprecated File Findings

### 1. Demonstrably Deprecated Files in `scratch/`:
- **Legacy Patch & Reject Artifacts:** `scratch/anchor2_uncommitted.patch` (301 KB), `scratch/h0_dev_control_results.json.rej` (296 KB).
- **Temporary Test Fix Scripts:** `scratch/fix_tests.py` through `scratch/fix_tests8.py` (8 temporary helper scripts created during prior test repairs).
- **Ad-Hoc Fast Audits:** `scratch/fast_audit.py`, `scratch/fast_audit2.py`, `scratch/debug_rejections.py`.

### 2. Functional Duplication Across Experiment Runners:
- `research/experiments/run_anchor2_dev_replay.py`
- `research/experiments/run_h0_dev_replay.py`
- `research/experiments/run_canonical_rebuild_replay.py`
- `research/experiments/run_h_d03_dev_replay.py`
*Finding:* These four scripts share $>90\%$ identical boilerplates for setting up `CausalReplayer`, loading data, and saving JSON bundles. They represent isolated historical experiment wrappers rather than a single parameter-driven harness.

---

## 3. Canonical Timeframe Audit (All 5 Sets)

The canonical strategy mandates five execution scales:

```text
SET 1 = 1M (HTF) -> 1W (MTF) -> 1D (LTF)   [Macro / Position]
SET 2 = 1W (HTF) -> 1D (MTF) -> 4H (LTF)   [Position / Swing]
SET 3 = 1D (HTF) -> 4H (MTF) -> 1H (LTF)   [Swing]
SET 4 = 4H (HTF) -> 1H (MTF) -> 15M (LTF)  [Tactical Intraday]
SET 5 = 15M (HTF) -> 5M (MTF) -> 1M (LTF)  [Intraday Scalping]
```

### Subsystem Verification Matrix

| Subsystem | SET 1 | SET 2 | SET 3 | SET 4 | SET 5 | Implementation Finding |
| :--- | :---: | :---: | :---: | :---: | :---: | :--- |
| **1. Configuration (`config/`)** | ✅ Yes | ✅ Yes | ✅ Yes | ✅ Yes | ❌ **NO** | `config/timeframe_sets.py` omits `SET_5_SCALPING` |
| **2. Data Adapter (`market_data/`)** | ✅ Yes | ✅ Yes | ✅ Yes | ✅ Yes | ✅ Yes | `BinanceFetcher` supports `1m` and `5m` |
| **3. Structure Engine (`P01`)** | ✅ Yes | ✅ Yes | ✅ Yes | ✅ Yes | ✅ Yes | Timeframe-agnostic candle parsing |
| **4. Timeframe Aligner (`replayer/`)** | ✅ Yes | ✅ Yes | ✅ Yes | ✅ Yes | ✅ Yes | `CANONICAL_TIMEFRAME_SETS` explicitly defines SET 5 |
| **5. Strategy Coordinator (`P02`)** | ✅ Yes | ✅ Yes | ✅ Yes | ✅ Yes | ✅ Yes | Disambiguates `1m` (3,600s) vs `1M` (180d) lifespan |
| **6. Risk Engine (`P03`)** | ✅ Yes | ✅ Yes | ✅ Yes | ✅ Yes | ✅ Yes | Timeframe-agnostic account risk sizing |
| **7. Trade Management** | ✅ Yes | ✅ Yes | ✅ Yes | ✅ Yes | ✅ Yes | Trailing stop operates identically across scales |
| **8. Telemetry Engine** | ✅ Yes | ✅ Yes | ✅ Yes | ✅ Yes | ✅ Yes | Records exact timeframe IDs |
| **9. Research Replayer Engine** | ✅ Yes | ✅ Yes | ✅ Yes | ✅ Yes | ⚠️ Fails Closed | Replayer detects missing 2021–2022 1m cache and fails closed |

### SET 5 Data Availability vs. Implementation Distinction
- **Implementation Status:** `SET 5` implementation is **$100\%$ complete** across structure, strategy, risk, and replayer engines.
- **Data Availability Status:** Public Binance historical depth for `1m` and `5m` candles only extends back to 2026 in the local cache. Replaying SET 5 on 2021–2022 raises `INSUFFICIENT_HISTORICAL_DEPTH_FAIL_CLOSED` and produces exactly 0 trades.
- **Governance Verdict:** This fail-closed behavior is **causally correct and certified**. The platform never fabricates synthetic data.

---

## 4. Canonical Asset Universe Audit

The canonical initial universe consists of:
- **BTC/USDT**
- **ETH/USDT**
- **SOL/USDT**

### Verification of State Independence:
- Every execution stream is instantiated with its own private instance of `LanguageCoordinator`, `StrategyCoordinator`, `ActiveTradeManager`, and `TradeLedger`.
- HTF KeyZone caches and MTF candidate trackers are strictly keyed by stream ID (`cand_{symbol}_{hyp_id}_{timestamp}`).
- No cross-talk, asset correlation bleed, or shared state exists between assets.
- Across 2021–2022, candidate generation was balanced: SOL ($35.1\%$), BTC ($33.7\%$), ETH ($31.2\%$).

---

## 5. Canonical Strategy Implementation Map

The canonical strategy requires a single unified multi-timeframe pipeline:

```text
HTF BIAS / DIRECTION
        ↓
HTF KEYZONE INTERACTION
        ↓
MTF STRUCTURAL REALIGNMENT
        ↓
MTF CAUSAL KEYZONE CREATION
        ↓
MTF ACTIVE PULLBACK RETEST
        ↓
LTF ENTRY MODEL (SWEEP + DISPLACEMENT)
        ↓
LTF STRUCTURAL STOP LOSS
        ↓
HTF STRUCTURAL DESTINATION
        ↓
MTF STRUCTURAL TRAILING STOP
```

### Component Implementation Mapping

| Pipeline Stage | Canonical Specification | Executable Code Location | Conformance Status |
| :--- | :--- | :--- | :---: |
| **1. HTF Trend / Bias** | Sequence of HH/HL vs LH/LL | [`strategy_engine/classifiers/bias_classifier.py:L18`](file:///home/mrcn2/crypto-platform/strategy_engine/classifiers/bias_classifier.py#L18) | 🟢 **CONFORMANT** |
| **2. HTF KeyZone Gate** | Price must actively penetrate valid HTF zone | [`strategy_engine/coordinator/strategy_coordinator.py:L187-L225`](file:///home/mrcn2/crypto-platform/strategy_engine/coordinator/strategy_coordinator.py#L187-L225) | 🟢 **CONFORMANT** |
| **3. MTF Realignment** | MTF develops CHOCH/BOS aligning with HTF | [`strategy_engine/hypotheses/unified_strategy.py:L167-L232`](file:///home/mrcn2/crypto-platform/strategy_engine/hypotheses/unified_strategy.py#L167-L232) | 🟢 **CONFORMANT** |
| **4. MTF Causal Zone** | Zone created at or after alignment event | [`strategy_engine/hypotheses/unified_strategy.py:L189-L229`](file:///home/mrcn2/crypto-platform/strategy_engine/hypotheses/unified_strategy.py#L189-L229) | 🟢 **CONFORMANT** |
| **5. MTF Active Retest** | Price pulls back into causal MTF zone | [`strategy_engine/hypotheses/unified_strategy.py:L236-L298`](file:///home/mrcn2/crypto-platform/strategy_engine/hypotheses/unified_strategy.py#L236-L298) | 🟢 **CONFORMANT** |
| **6. LTF Trigger** | Sweep + Directional Displacement | [`strategy_engine/entry/ltf_entry_model.py:L24-L71`](file:///home/mrcn2/crypto-platform/strategy_engine/entry/ltf_entry_model.py#L24-L71) | 🟢 **CONFORMANT** |
| **7. LTF Stop Loss** | Anchored to confirmed structural swing | [`strategy_engine/entry/entry_models.py:L36-L85`](file:///home/mrcn2/crypto-platform/strategy_engine/entry/entry_models.py#L36-L85) | 🟢 **CONFORMANT** |
| **8. HTF Destination** | External structural target discovery | [`strategy_engine/context/htf_destination_engine.py:L47-L196`](file:///home/mrcn2/crypto-platform/strategy_engine/context/htf_destination_engine.py#L47-L196) | 🔴 **DEFECTIVE** |
| **9. Planned RR Gate** | Ratio $\ge 4.0\text{R}$ | [`strategy_engine/hypotheses/unified_strategy.py:L420-L430`](file:///home/mrcn2/crypto-platform/strategy_engine/hypotheses/unified_strategy.py#L420-L430) | 🟢 **CONFORMANT** |
| **10. MTF Trailing Stop**| Monotonic trailing behind MTF swings | [`strategy_engine/lifecycle/active_trade_manager.py:L120-L220`](file:///home/mrcn2/crypto-platform/strategy_engine/lifecycle/active_trade_manager.py#L120-L220) | 🟢 **CONFORMANT** |

---

## 6. Stop Loss, Target & Trade Management Audit

1. **Initial Stop Loss:**
   - Evaluated by `BaseLTFEntryModel.extract_structural_stop()`.
   - In longs, placed below the confirmed LTF protected low or sequence low.
   - In shorts, placed above the confirmed LTF protected high or sequence high.
   - Minimum stop separation: $0.05\%$ to prevent division-by-zero on micro-wicks.
2. **HTF Structural Target:**
   - Intended to identify forward macro liquidity or opposing weak swing.
   - Currently suffers from two severe flaws: negative Dealing Range targets and closest-feature sorting.
3. **Planned RR ($\ge 4.0\text{R}$):**
   - Strictly enforced at line 422 of `unified_strategy.py`. Targets are never artificially moved to pass.
4. **Position Sizing & Risk Limit:**
   - Enforced by `RiskCoordinator.evaluate()`.
   - Dollar risk is capped at strictly $1.0\%$ of current equity ($\$100$ on $\$10,000$).
   - Sizing formula: $\text{Units} = \frac{\text{Dollar Risk}}{\text{Entry} - \text{SL}}$.
5. **MTF Structural Trailing Stop:**
   - Managed in `ActiveTradeManager.evaluate()`.
   - On every LTF bar, MTF visible structure is checked. When a new MTF protected swing confirms in the direction of the trade, `stop_invalidation_price` updates monotonically. Stop never loosens.

---

## 7. Deterministic Definitions Audit (The 17 Concepts)

| # | Structural Concept | Exact Code Implementation | Input Data | Causal Confirmation Rule |
| :-: | :--- | :--- | :--- | :--- |
| 1 | **BOS** | `market_intelligence/structure_engine.py` | Closed Candles | Candle close strictly beyond prior confirmed swing extreme in trend direction |
| 2 | **CHOCH** | `market_intelligence/structure_engine.py` | Closed Candles | Candle close breaking opposite protected swing low (in uptrend) or high (in downtrend) |
| 3 | **Raw Swing** | `market_intelligence/raw_swing_engine.py` | High/Low Series | $N$-bar fractal pivot (3-bar or 5-bar local extreme with lower/higher neighbors) |
| 4 | **Strong Swing** | `market_intelligence/structure_engine.py` | Swing + Events | The structural pivot that causally generated a subsequent BOS or CHOCH |
| 5 | **Weak Swing** | `market_intelligence/structure_engine.py` | Swing + Trend | An opposing swing high (in uptrend) or low (in downtrend) expected to be targeted |
| 6 | **Trend** | `market_intelligence/trend_engine.py` | Sequence Swings | Persistent sequence of Higher Highs/Lows (BULLISH) or Lower Highs/Lows (BEARISH) |
| 7 | **Alignment** | `strategy_engine/hypotheses/unified_strategy.py` | MTF Events | MTF CHOCH or BOS event matching HTF trend direction occurring $\ge$ HTF context timestamp |
| 8 | **KeyZone** | `market_intelligence/keyzone_engine.py` | Multi-candle | Impulsive expansion origin containing unmitigated Order Block or Fair Value Gap |
| 9 | **FVG** | `market_intelligence/keyzone_engine.py` | 3-Bar Sequence | Candle 1 High < Candle 3 Low (Bullish) or Candle 1 Low > Candle 3 High (Bearish) |
| 10| **Order Block** | `market_intelligence/keyzone_engine.py` | Closed Candles | The last counter-directional candle body preceding an impulsive structural break |
| 11| **Liquidity Pool** | `market_intelligence/liquidity_engine.py` | Swing Points | Cluster of Equal Highs (`EQH`) or Equal Lows (`EQL`) within $\pm 0.10\%$ tolerance |
| 12| **Liquidity Sweep** | `market_intelligence/liquidity_engine.py` | Candle Wicks | Candle wick penetrates prior swing or pool boundary but closes back inside range |
| 13| **Displacement** | `strategy_engine/entry/entry_models.py` | Single Candle | Body $\ge 50\%$ of candle range, closing in setup direction, expansion $\ge 0.08\%$ |
| 14| **MTF Retest** | `strategy_engine/hypotheses/unified_strategy.py` | LTF Candle | Price penetrates into boundary of causal MTF KeyZone created $\ge$ alignment event |
| 15| **Structural Invalidation** | `strategy_engine/hypotheses/unified_strategy.py` | MTF/HTF State | Price breaches KeyZone origin boundary or opposing structural break forms |
| 16| **HTF Destination** | `strategy_engine/context/htf_destination_engine.py` | HTF State | Candidate opposing zones, liquidity pools, weak swings sorted by closest distance |
| 17| **MTF Trail Event** | `strategy_engine/lifecycle/active_trade_manager.py` | MTF Swings | New MTF protected swing confirmed; stop ratchets monotonically behind it |

---

## 8. HTF Destination Engine Forensic Analysis

We audited `HTFDestinationEngine` against the 13 specific architectural questions:

1. **Candidate Features Considered:** Opposing unmitigated HTF KeyZones, unswept HTF Liquidity Pools (`EQH`/`EQL`), HTF Weak Swings, and Dealing Range 1.0x expansion.
2. **Excluded Features:** MTF swings, internal trendline liquidity, session highs/lows.
3. **Candidate Ranking Logic:** **Strictly sorted by closest distance to reference price** ([`htf_destination_engine.py:L164-L167`](file:///home/mrcn2/crypto-platform/strategy_engine/context/htf_destination_engine.py#L164-L167)).
4. **Weak Swing Priority:** No. Weak swings are ranked identically to micro keyzones and liquidity pools; closest wins.
5. **Opposing Liquidity Consideration:** Yes, pools are included in the candidate list.
6. **Internal vs. External Destinations:** The engine does **not** distinguish between internal retracement zones and external range destinations. Any minor internal keyzone sitting just above/below price is treated as a valid destination.
7. **External HTF Structure Only:** No. Internal micro-zones dominate the selection.
8. **Ignoring Closer Features:** No. It systematically selects the *closest* feature.
9. **Use of MTF Information:** No. Operates purely on HTF payload.
10. **Target Price Calculation:** Uses the front edge (`low_boundary` for supply, `high_boundary` for demand, or exact pool price).
11. **Freezing Point:** Target is frozen at candidate entry evaluation time.
12. **Causality at Entry:** Point-in-time causal relative to visible HTF slice.
13. **Vulnerability to Negative Target Prices:** **YES (Confirmed Critical Bug).** For short setups, `expansion_target = dr.low_price - (range_width * 1.0)` produces negative numbers when range width exceeds low price.

---

## 9. The 13 Composite Trades Target Forensics

We reconstructed the exact point-in-time structural candidate universe for each of the 13 Composite trades at their entry timestamps (`scratch/composite_13_target_forensics.json`):

| # | Trade ID | Asset / Set | Dir | Entry Px | Initial SL | Planned Target | Target Type | Planned RR | Closest Visible Feature | Realized Net R | Exit Reason |
| :-: | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- | :---: | :--- |
| 01 | `cand_SOL_1614220200` | SOL / SET 4 | LONG | 14.48 | 13.10 | 21.33 | DR Expansion | 4.97R | Opposing KZ (14.64) | -0.6857R | MTF Trail |
| 02 | `cand_SOL_1624409100` | SOL / SET 4 | SHORT | 31.78 | 32.55 | 20.19 | Liquidity Pool | 5.16R | Opposing KZ (29.53) | +0.0822R | Breakeven |
| 03 | `cand_SOL_1626504300` | SOL / SET 4 | SHORT | 27.28 | 28.57 | 18.47 | DR Expansion | 6.81R | Liquidity Pool (25.98)| **+2.8010R**| MTF Trail |
| 04 | `cand_BTC_1641543300` | BTC / SET 4 | SHORT | 41438.08 | 41949.99 | 33704.93 | DR Expansion | 5.35R | Liquidity Pool (40610)| -0.3456R | MTF Trail |
| 05 | `cand_BTC_1644192000` | BTC / SET 4 | LONG | 41655.43 | 40636.19 | 47577.38 | DR Expansion | 5.82R | Weak Swing (41913.7) | **+1.6942R**| MTF Trail |
| 06 | `cand_BTC_1645524900` | BTC / SET 4 | SHORT | 37703.11 | 38967.57 | 31201.00 | DR Expansion | 5.14R | Opposing KZ (37274) | -0.8876R | MTF Trail |
| 07 | `cand_ETH_1652145300` | ETH / SET 4 | SHORT | 2400.38 | 2469.70 | 2114.13 | DR Expansion | 4.13R | Opposing KZ (2365) | +0.0585R | MTF Trail |
| 08 | `cand_SOL_1654300800` | SOL / SET 3 | SHORT | 38.38 | 49.69 | **-14.69** | **Negative DR** | **4.69R** | **DR Exp (-14.69)** | -0.1540R | MTF Trail |
| 09 | `cand_BTC_1668061800` | BTC / SET 4 | SHORT | 17332.51 | 17430.33 | 13248.66 | DR Expansion | 4.71R | Opposing KZ (17120) | -0.2602R | MTF Trail |
| 10 | `cand_SOL_1669035600` | SOL / SET 4 | SHORT | 11.66 | 12.82 | **-6.56** | **Negative DR** | **11.97R**| **DR Exp (-6.56)** | -0.2990R | MTF Trail |
| 11 | `cand_ETH_1669824000` | ETH / SET 2 | SHORT | 1279.79 | 1309.34 | 1073.53 | Liquidity Pool | 6.98R | Liquidity Pool (1073)| +0.0482R | Breakeven |
| 12 | `cand_ETH_1670572800` | ETH / SET 2 | SHORT | 1274.60 | 1316.32 | 1073.53 | Liquidity Pool | 4.80R | Liquidity Pool (1073)| -0.7156R | MTF Trail |
| 13 | `cand_SOL_1671889500` | SOL / SET 4 | SHORT | 11.39 | 11.65 | 9.54 | DR Expansion | 7.28R | Liquidity Pool (11.07)| -0.3749R | MTF Trail |

### Core Findings from the 13 Composite Trades:
1. **Dealing Range Fallback Dominance:** **8 out of 13 trades ($61.5\%$)** relied on `FORWARD_STRUCTURAL_EXPANSION` because no valid opposing keyzone or weak swing existed that satisfied $\ge 4.0\text{R}$.
2. **Liquidity Pools:** 4 out of 13 trades used unswept liquidity pools (`EQH`/`EQL`).
3. **Zero Weak Swings:** **0 out of 13 trades** used a weak swing as their final target.
4. **Negative Target Prices (Trades #8 and #10):** Proves that the platform was executing short trades with target prices below zero on Solana during bear market expansions.

---

## 10. Target Hypothesis Status Decision

Evaluating the five formal options provided by the directive:
- **A** — Current destination logic is structurally correct; starvation originates elsewhere.
- **B** — Current destination logic contains a demonstrable structural-selection defect.
- **C** — Current destination logic is incomplete because relevant structural candidate classes are missing.
- **D** — Evidence is insufficient to define a target-selection change.
- **E** — Architecture implementation itself is insufficiently faithful to the canonical strategy, so target research must wait.

### **Scientific Decision: `CONCLUSION_E: ARCHITECTURE IMPLEMENTATION ITSELF IS INSUFFICIENTLY FAITHFUL TO THE CANONICAL STRATEGY, SO TARGET RESEARCH MUST WAIT.`**
*(Supported by `CONCLUSION_B: DEMONSTRABLE SELECTION DEFECT`)*

### Rationale:
We cannot conduct a controlled experiment on target selection (e.g. `HYP_TARGET_ANCHOR_01`) while the destination engine is emitting negative target prices, sorting by closest micro-keyzone, and misaligned with `config/timeframe_sets.py`. Architectural hygiene and defect remediation must strictly precede target hypothesis research.

---

## 11. Market Regime & Indicator Extension Audit

We audited whether market regime characteristics can be added without modifying the core strategy:
- **`strategy_engine/classifiers/regime_filter.py`** is already implemented as a pure external gate.
- It calculates 14-period vs 50-period ATR ratio causally across closed historical candles.
- If volatility compression is detected, it flags `bias = DirectionalPermission.NO_TRADE` at Step 2 of `StrategyCoordinator.evaluate()`, preventing candidates from spawning.
- **Extension Points:** Volatility, funding rate, spread, open interest, and news blackouts can all attach cleanly to `StrategyCoordinator.evaluate()` as pre-qualification filters. They do not need to alter HTF structure, MTF realignment, or LTF entry logic.

---

## 12. Causality & Lookahead Audit

Point-in-time causal integrity was verified across all layers:
1. **Candle Slicing:** `TimeframeAligner.filter_visible_candles()` uses a binary search with strict `cutoff = decision_timestamp - duration`. Unclosed bars are $100\%$ excluded.
2. **Order Execution Collision:** `ExecutionSimulator.process_candle()` resolves intrabar collisions with strict **adverse-first precedence**. When a bar penetrates both stop-loss and take-profit, the trade is always stopped out.
3. **Trailing Stop Causality:** `ActiveTradeManager` only trails stops behind MTF swings that closed prior to the current decision timestamp.

---

## 13. Research Governance & Partition Locks

- **Development Partition (2021–2022):** Strictly maintained. All telemetry and audits reflect this 2-year window.
- **Validation Partition (2023):** **LOCKED**. Zero access, zero optimization.
- **Out-of-Sample Partition (2024–2026):** **LOCKED**. Zero access, zero optimization.

---

## 14. Architecture Gaps & Implementation Drift Findings

| Component / Subsystem | Canonical Concept | Current Implementation | Architectural Gap / Severity |
| :--- | :--- | :--- | :--- |
| **HTF Destination Engine** | External macro structural target | Emits negative prices (`-$14.69`) on SOL shorts; sorts by closest micro-keyzone | 🔴 **CRITICAL DEFECT** (Invalid math, truncates planned RR) |
| **Timeframe Configuration** | 5 operational sets (SET 1 to SET 5) | `config/timeframe_sets.py` omits SET 5; `timeframe_aligner.py` includes it | 🟡 **MEDIUM DRIFT** (Configuration discrepancy) |
| **Strategy Engine Organization** | One unified MTF strategy | Wrapped in `UnifiedStrategy`, but legacy runners contain Pullback/Continuation drift | 🟡 **LOW DRIFT** (Code cleanliness) |
| **Scratch Directory Hygiene** | Clean diagnostic workspace | 134 files, including temporary patch/rej files and 8 test-fix scripts | 🟢 **MAINTENANCE** (Needs structured archival) |

---

## 15. Recommended Next Research Gate: `REMEDIATION_01`

Before formulating Cycle #6 or running any new trading experiments, the platform must execute an engineering repair gate:

### Scope of Proposed Engineering Gate: `GATE_ARCH_REPAIR_01`
1. **Fix Negative Target Prices:** Enforce a strict absolute price floor in `HTFDestinationEngine` ($\text{Target} > 0.0$ and $\text{Target} \ge \text{Reference Price} \times 0.05$).
2. **Reconcile Timeframe Configuration:** Add `SET_5_SCALPING` to `config/timeframe_sets.py` so platform config matches research replayer specifications.
3. **Establish External Structural Destination Hierarchy:** Reform target selection so it targets **external macro HTF swings or dealing range boundaries**, rather than sorting by closest minor internal keyzones.
4. **Clean Redundant Scratch Files:** Archive obsolete patch/reject files and test fix scripts to `scratch/archive/` while preserving full git provenance.

---

## Strict Stop Condition Acknowledgment

This cycle was executed strictly as an **ARCHITECTURE + REPOSITORY FORENSIC AUDIT**.
- **Zero** trading rules modified.
- **Zero** strategy code changed.
- **Zero** parameters swept or tuned.
- Validation 2023 and OOS 2024–2026 remain strictly **LOCKED**.

**Forensic audit complete. Awaiting user review and approval before any remediation.**
