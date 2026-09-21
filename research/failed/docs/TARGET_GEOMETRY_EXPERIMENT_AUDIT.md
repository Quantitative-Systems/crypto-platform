# Research Audit: Structural Target Geometry Experiment (Experiment B)
## Development Partition (2021-01-01 to 2022-12-31)

**Document Identifier:** `TARGET_GEOMETRY_EXPERIMENT_AUDIT`  
**Classification:** Institutional Quantitative Research  
**Experiment Identifier:** `EXP_TARGET_STRUCTURAL_01` (Experiment B)  
**Control Baseline:** Corrected Canonical H0 Control (`CLOSEST_OBJECTIVE`, N=29)  
**Treatment:** Structural Target Geometry (`STRUCTURAL_OBJECTIVE`, N=41)  
**Dataset Partition:** Historical Development Partition Only (2021-01-01T00:00:00Z to 2022-12-31T23:59:59Z, 277,908 candles)  
**Universe Audited:** BTC/USDT, ETH/USDT, SOL/USDT across all 5 Canonical Timeframe Sets (15 Streams)  
**Execution Physics:** Adverse-First Intrabar Collision, 2 bps Maker, 5 bps Taker, 5 bps Adverse Slippage  
**Validation & OOS Partitions:** Strictly Air-Gapped and LOCKED (2023, 2024–2026)  

---

## Executive Summary & Formal Verdict

Pursuant to the **Controlled Research Directive**, Experiment B was executed as an isolated single-variable experiment against the corrected canonical H0 baseline. The specific objective was to test whether the canonical closest-target selection rule (`CLOSEST_OBJECTIVE`) was mismatched with the structural potential captured by the canonical entry model, and whether prioritizing macro structural targets (`STRUCTURAL_OBJECTIVE`: Weak Swings and Liquidity Pools) improves trade monetization.

### Primary Experimental Conclusion:
In accordance with the pre-registered Decision Rules, Experiment B is classified as:

$$\mathbf{B3 \text{ — NEGATIVE (REJECT TREATMENT)}}$$

**Key Findings:**
1. **Target Reachability Collapsed:** Requiring price to reach the macro Weak Swing moved targets from an average planned RR of $7.61\text{R}$ out to $9.12\text{R}$ ($+19.8\%$). Because targets were placed significantly farther away, the target reach rate collapsed from **$6.90\%$ (2 hits) down to $2.44\%$ (1 hit)**.
2. **Net Return and Expectancy Deteriorated Materially:** Net realized return declined from **$-15.52\text{R}$ to $-27.66\text{R}$** ($\Delta = -12.14\text{R}$), expectancy degraded from **$-0.5351\text{R}$ to $-0.6746\text{R}$** ($\Delta = -0.1395\text{R}$), and Profit Factor fell from **$0.3871$ to $0.1905$**.
3. **Winner Truncation (The 4.13R Loss on Trade 20):** In H0, Trade 20 on BTC targeted an opposing keyzone at $47,350$ and hit it cleanly for **$+5.70\text{R}$**. In the Treatment, prioritizing a distant liquidity pool moved the target down to $40,753$. Price achieved $+6.95\text{R}$ MFE (surpassing the H0 target), but reversed before reaching the new distant target, trailing out for only **$+1.57\text{R}$**—destroying $+4.13\text{R}$ of realized gain.
4. **Qualification of Low-Quality Extensions:** By pushing targets farther into macro space, 12 additional setups qualified past the $4.0\text{R}$ firewall (41 vs 29). Out of these 12 additional trades, 11 were full stop-out losses ($-1.08\text{R}$ each) and only 1 produced a small profit ($+0.83\text{R}$), introducing an incremental **$-11.0\text{R}$ net drag**.
5. **Core Mechanistic Diagnosis:** The platform's monetization problem is **NOT target selection**. Price regularly produces substantial favorable excursion (average MFE $+1.57\text{R}$ to $+1.58\text{R}$, with 19 trades reaching $\ge +1.0\text{R}$ and 11 reaching $\ge +2.0\text{R}$). The failure is **Trade Management & Trailing Latency**: 9 trades reached $\ge +2.0\text{R}$ and 5 reached $\ge +3.0\text{R}$ (peaking up to $+6.25\text{R}$), yet ended in full losses because the trailing stop lagged by 4 to 6 hours.

---

## 1. Experimental Methodology & Single-Variable Invariance

Experiment B maintained strict single-variable isolation. All upstream and downstream architectural invariants remained bit-for-bit identical to the frozen H0 baseline:

| System Layer | Frozen Invariant Implementation | State in Experiment B |
| :--- | :--- | :--- |
| **HTF Directional Bias** | `LanguageCoordinator` BOS/CHOCH trend filter | **Frozen (Identical)** |
| **HTF KeyZone Requirement** | Unmitigated Order Blocks / FVGs on HTF close | **Frozen (Identical)** |
| **MTF Structural Alignment** | Causal Market Structure Shift (MSS) | **Frozen (Identical)** |
| **MTF Causal Retest** | Price interaction with post-alignment MTF zone | **Frozen (Identical)** |
| **LTF Entry Model** | Micro sweep + directional displacement | **Frozen (Identical)** |
| **LTF Structural SL** | Immediate micro invalidation pivot (`min_stop` 0.1%) | **Frozen (Identical)** |
| **Account Risk Ceiling** | Dynamic position sizing $\le 1.0\%$ equity risk | **Frozen (Identical)** |
| **Capital Firewall** | Planned Risk-to-Reward $\ge 4.0\text{R}$ threshold | **Frozen (Identical)** |
| **Execution Collision** | Strict `ADVERSE_FIRST` intrabar collision policy | **Frozen (Identical)** |
| **Microstructure Friction** | 2 bps maker, 5 bps taker, 5 bps adverse slippage | **Frozen (Identical)** |
| **Trade Management** | Monotonic MTF structural swing trailing | **Frozen (Identical)** |
| **Exclusions** | No Breakeven, No Profit Locks, No Partial Exits | **Frozen (Enforced)** |
| **Target Ranking Rule** | `CLOSEST_OBJECTIVE` vs `STRUCTURAL_OBJECTIVE` | **ISOLATED VARIABLE** |

### Exact Code Differentiation:
The only operational difference between Control and Treatment resides in candidate target ranking in [`strategy_engine/context/htf_destination_engine.py`](file:///home/mrcn2/crypto-platform/strategy_engine/context/htf_destination_engine.py):

- **Control (`CLOSEST_OBJECTIVE`):**
  Forward structural candidates (Opposing KeyZones, Liquidity Pools, Weak Swings) are sorted strictly by linear price proximity to entry:
  ```python
  candidates.sort(key=lambda x: abs(x[0] - ref_price))
  ```
- **Treatment (`STRUCTURAL_OBJECTIVE`):**
  Forward structural candidates are sorted by structural hierarchy tier first, then proximity within tier:
  ```python
  tier_priority = {
      DestinationType.WEAK_SWING: 1,       # Opposing external directional swing
      DestinationType.LIQUIDITY_POOL: 2,   # Unswept external liquidity pool
      DestinationType.OPPOSING_KEYZONE: 3, # Internal supply/demand obstacle
  }
  candidates.sort(key=lambda x: (tier_priority.get(x[1], 99), abs(x[0] - ref_price)))
  ```

---

## 2. Quantitative Results Comparison (H0 vs EXP_TARGET_STRUCTURAL_01)

Across the entire 2-year Development partition ($277,908$ candles across 15 streams):

### A. Comprehensive Funnel Comparison
| Funnel Stage | H0 Control (Closest) | Treatment (Structural) | Absolute Delta ($\Delta$) | Analysis & Notes |
| :--- | :---: | :---: | :---: | :--- |
| **Total Candidates Evaluated** | 924 | 924 | 0 | Identical market candidate discovery |
| **Reached MTF Retest** | 483 | 483 | 0 | Identical setup progression |
| **Reached Risk Gate (LTF Confirmed)**| 111 | 153 | +42 | Distant targets expand planned RR $\ge 4.0\text{R}$ |
| **Rejected by 4R Firewall** | 372 | 330 | -42 | Fewer setups rejected due to farther target |
| **Approved Setups** | 111 | 153 | +42 | 37.8% expansion in approved setups |
| **Executed Trades ($N$)** | **29** | **41** | **+12** | **+41.4% execution volume** |
| **Unfilled Limit Orders** | 82 | 112 | +30 | Limit order placed but price moved away |

---

### B. Performance & Economic Returns
| Performance Metric | H0 Control (Closest) | Treatment (Structural) | Absolute Delta ($\Delta$) | Economic Impact |
| :--- | :---: | :---: | :---: | :--- |
| **Executed Trades ($N$)** | **29** | **41** | **+12** | Higher trade sample |
| **Winning Trades ($W$)** | **2** | **3** | **+1** | 1 additional win (SOL Trade 12, +0.83R) |
| **Losing Trades ($L$)** | **27** | **38** | **+11** | 11 additional losses (-1.08R each) |
| **Breakeven Trades ($BE$)** | 0 | 0 | 0 | Invariant: zero breakeven rule |
| **Win Rate (%)** | **6.90%** | **7.32%** | **+0.42%** | Statistically equivalent |
| **Gross Realized Return** | **-13.1600R** | **-24.3768R** | **-11.2168R** | Deep negative degradation |
| **Total Friction Cost** | **2.3586R** | **3.2829R** | **+0.9243R** | Higher trading activity fee drag |
| **Net Realized Return** | **-15.5185R** | **-27.6596R** | **-12.1411R** | **Severe capital impairment** |
| **Expectancy ($E[R]$)** | **-0.5351R** | **-0.6746R** | **-0.1395R** | **Expectancy worsened by 26.1%** |
| **Profit Factor (PF)** | **0.3871** | **0.1905** | **-0.1966** | **Profit factor cut in half** |
| **Max Drawdown ($R$)** | **15.5185R** | **27.6596R** | **+12.1411R** | Monotonic equity decay |
| **Max Consecutive Losses** | **14** | **21** | **+7** | Extended adverse loss streak |

---

### C. Excursion Distribution (MFE / MAE)
| Excursion Metric | H0 Control (Closest) | Treatment (Structural) | Delta ($\Delta$) | Analysis |
| :--- | :---: | :---: | :---: | :--- |
| **Average MFE ($R$)** | **+1.5798R** | **+1.5667R** | -0.0131R | Essentially identical potential |
| **Median MFE ($R$)** | **+0.8185R** | **+0.9226R** | +0.1041R | Substantial directional run |
| **Average MAE ($R$)** | **1.5162R** | **1.3877R** | -0.1285R | Slightly tighter initial adverse push |
| **Median MAE ($R$)** | **1.2308R** | **1.2044R** | -0.0264R | Stop breach dominates exits |
| **Trades Reaching $\ge +1.0\text{R}$** | **13 (44.8%)** | **19 (46.3%)** | **+6** | Favorable movement is common |
| **Trades Reaching $\ge +2.0\text{R}$** | **8 (27.6%)** | **11 (26.8%)** | **+3** | Significant impulse generation |
| **Trades Reaching $\ge +3.0\text{R}$** | **5 (17.2%)** | **7 (17.1%)** | **+2** | Strong multi-R excursions |
| **Trades Reaching $\ge +4.0\text{R}$** | **4 (13.8%)** | **5 (12.2%)** | **+1** | Meets or exceeds planned 4R |
| **Trades Reaching $\ge +5.0\text{R}$** | **4 (13.8%)** | **4 (9.8%)** | 0 | Major macro trend runners |

---

### D. Target Interaction & Reachability Analysis
| Metric | H0 Control (Closest) | Treatment (Structural) | Delta ($\Delta$) | Interpretation |
| :--- | :---: | :---: | :---: | :--- |
| **Target Reach Count** | **2** | **1** | **-1** | Target hits dropped by 50% |
| **Target Reach Rate (%)** | **6.90%** | **2.44%** | **-4.46%** | Structural targets rarely reached |
| **Reach Rate Given MFE $\ge +1\text{R}$**| **15.38%** (2/13) | **5.26%** (1/19) | **-10.12%** | Converts excursion to target 3x worse |
| **Reach Rate Given MFE $\ge +2\text{R}$**| **25.00%** (2/8) | **9.09%** (1/11) | **-15.91%** | Strong impulses fail before target |
| **Reach Rate Given MFE $\ge +3\text{R}$**| **40.00%** (2/5) | **14.29%** (1/7) | **-25.71%** | 6 out of 7 +3R runs missed target |
| **Average Planned RR** | **7.61R** | **9.12R** | **+1.51R** | Targets pushed 19.8% farther out |
| **Median Planned RR** | **6.52R** | **7.10R** | **+0.58R** | Higher structural RR expectation |
| **Average Target Distance in R** | **0.1149** | **0.1446** | **+0.0297** | Target distance expanded |

---

### E. Exit Mechanism Attribution Breakdown
| Exit Mechanism | H0 Trades ($N$) | H0 Realized R | Treatment Trades ($N$) | Treatment Realized R | Net Delta ($\Delta R$) |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **`INITIAL_LTF_SL`** | 21 (72.4%) | -22.88R | **27 (65.9%)** | **-29.38R** | **-6.50R** |
| **`MTF_STRUCTURAL_TRAIL`** | 6 (20.7%) | -2.44R | **13 (31.7%)** | **-2.39R** | +0.05R |
| **`HTF_TP`** | 2 (6.9%) | **+9.80R** | **1 (2.4%)** | **+4.11R** | **-5.69R** |
| **`EMERGENCY`** | 0 | 0.00R | 0 | 0.00R | 0.00R |
| **TOTAL** | **29** | **-15.52R** | **41** | **-27.66R** | **-12.14R** |

---

## 3. The Core Diagnostic: Excursion vs Monetization Failure

The critical analytical question in quantitative trade design is:
> *Does price fail to move in our direction, or does the strategy fail to monetize the movement that occurs?*

In the Structural Target Geometry treatment, **9 separate trades achieved an MFE $\ge +2.0\text{R}$, yet ended in a realized loss**:

| Trade # | Stream ID | Direction | Entry Price | Planned RR | Peak MFE ($R$) | Exit Mechanism | Net Realized $R$ | Favorable Excursion Dissipated |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Trade 8** | SOL_SET_4 | LONG | $36.24$ | $11.8\text{R}$ | **$+3.35\text{R}$** | `INITIAL_LTF_SL` | **$-1.09\text{R}$** | **$4.44\text{R}$ dissipated** |
| **Trade 9** | SOL_SET_3 | LONG | $43.25$ | $5.5\text{R}$ | **$+2.79\text{R}$** | `MTF_STRUCTURAL_TRAIL` | **$-0.27\text{R}$** | **$3.06\text{R}$ dissipated** |
| **Trade 11** | SOL_SET_3 | SHORT | $43.87$ | $5.4\text{R}$ | **$+5.04\text{R}$** | `INITIAL_LTF_SL` | **$-1.06\text{R}$** | **$6.10\text{R}$ dissipated** |
| **Trade 13** | SOL_SET_4 | SHORT | $30.33$ | $27.2\text{R}$ | **$+4.96\text{R}$** | `INITIAL_LTF_SL` | **$-1.10\text{R}$** | **$6.06\text{R}$ dissipated** |
| **Trade 15** | ETH_SET_4 | SHORT | $1846.19$ | $6.4\text{R}$ | **$+2.10\text{R}$** | `MTF_STRUCTURAL_TRAIL` | **$-0.43\text{R}$** | **$2.53\text{R}$ dissipated** |
| **Trade 16** | SOL_SET_4 | LONG | $33.20$ | $7.4\text{R}$ | **$+3.00\text{R}$** | `INITIAL_LTF_SL` | **$-1.11\text{R}$** | **$4.11\text{R}$ dissipated** |
| **Trade 23** | SOL_SET_3 | SHORT | $142.46$ | $8.0\text{R}$ | **$+6.25\text{R}$** | `MTF_STRUCTURAL_TRAIL` | **$-0.31\text{R}$** | **$6.56\text{R}$ dissipated** |
| **Trade 31** | SOL_SET_3 | LONG | $135.77$ | $4.8\text{R}$ | **$+2.19\text{R}$** | `INITIAL_LTF_SL` | **$-1.10\text{R}$** | **$3.29\text{R}$ dissipated** |
| **Trade 32** | ETH_SET_4 | SHORT | $2377.47$ | $5.4\text{R}$ | **$+3.57\text{R}$** | `MTF_STRUCTURAL_TRAIL` | **$-0.98\text{R}$** | **$4.55\text{R}$ dissipated** |

### Why Did Pushing Targets to Weak Swings Fail?
1. **Microstructure Impulse Decay:** In cryptocurrency spot and perp markets, directional impulses rarely traverse 8R to 25R in an uninterrupted linear flight. Price expands, sweeps immediate liquidity, stalls at internal supply/demand boundaries, and pulls back sharply.
2. **The Destination Mirage:** By prioritizing the macro Weak Swing over intermediate Opposing KeyZones, the strategy ignored the immediate resistance level where price was overwhelmingly likely to pause or reverse.
3. **Trailing Stop Confirmation Lag:** The MTF structural trail requires a full 3-bar confirmed swing to advance. In SET 3 ($4\text{h}$) and SET 4 ($1\text{h}$), this creates **$3 \text{ to } 12 \text{ hours}$ of confirmation latency**. By the time the MTF swing confirms, the entire $+3.0\text{R}$ to $+6.25\text{R}$ impulse has completely retraced, knocking out the position at the initial stop or a trailed loss.

---

## 4. Multi-Asset Attribution Breakdown

| Asset | Control Trades | Control Net R | Control Expectancy | Treatment Trades | Treatment Net R | Treatment Expectancy | Impact Verdict |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| **BTC/USDT** | **6** | **+6.0850R** | **+1.0142R** | **8** | **+0.7703R** | **+0.0963R** | **Net gain collapsed by -5.31R** |
| **ETH/USDT** | 4 | -3.7085R | -0.9271R | 7 | -6.8912R | -0.9845R | 3 additional stop-outs (-3.18R) |
| **SOL/USDT** | 19 | -17.8950R | -0.9418R | 26 | -21.5387R | -0.8284R | 7 additional stop-outs (-3.64R) |

- **BTC Suffered Heavily:** On BTC, H0 was solidly profitable ($+6.08\text{R}$, $33.3\%$ WR). In the Treatment, BTC net profit dropped to $+0.77\text{R}$ because Trade 28's $+5.70\text{R}$ target win was converted to a $+1.57\text{R}$ trail exit, while two new BTC entries resulted in losses.
- **ETH and SOL Remained Ineffective:** ETH dropped from $-3.71\text{R}$ to $-6.89\text{R}$ (0% win rate across 7 trades). SOL executed 26 trades and produced $-21.54\text{R}$ net return.

---

## 5. Timeframe Set Attribution Breakdown

| Timeframe Set | Control Trades | Control Net R | Treatment Trades | Treatment Net R | Dominant Mechanism |
| :--- | :---: | :---: | :---: | :---: | :--- |
| **SET 1 (1M $\to$ 1w $\to$ 1d)** | 0 | 0.00R | 0 | 0.00R | Zero 1M keyzones interacted |
| **SET 2 (1w $\to$ 1d $\to$ 4h)** | 3 | -2.42R | 3 | -2.42R | Identical 3 position losses |
| **SET 3 (1d $\to$ 4h $\to$ 1h)** | **12** | **-3.65R** | **16** | **-10.29R** | **Severe degradation (-6.64R)** |
| **SET 4 (4h $\to$ 1h $\to$ 15m)** | **14** | **-9.45R** | **22** | **-14.95R** | **Severe degradation (-5.50R)** |
| **SET 5 (15m $\to$ 5m $\to$ 1m)** | 0 | 0.00R | 0 | 0.00R | Fail-closed (data depth) |

- The entire trade volume of the strategy resides in **SET 3** (Intermediate Swing) and **SET 4** (Intraday Momentum).
- In both SET 3 and SET 4, moving targets farther away expanded trade counts (SET 3: $12 \to 16$; SET 4: $14 \to 22$) but exacerbated drawdown.

---

## 6. Target Provenance Breakdown

| Target Provenance Source | Control Trades ($N$) | Control Net R | Control Avg MFE | Treatment Trades ($N$) | Treatment Net R | Treatment Avg MFE |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **`WEAK_SWING`** | 5 | -4.65R | +1.78R | **29** | **-26.02R** | **+1.42R** |
| **`LIQUIDITY_POOL`** | 18 | -11.09R | +1.43R | **12** | **-1.64R** | **+1.93R** |
| **`OPPOSING_KEYZONE`** | 6 | **+0.22R** | **+1.85R** | **0** | **0.00R** | N/A |

### Critical Provenance Insight:
- In H0, `OPPOSING_KEYZONE` targets were the **only profitable target class** ($+0.22\text{R}$ net, including Trade 28 at $+5.70\text{R}$).
- In Treatment, `OPPOSING_KEYZONE` targets were completely **bypassed** (0 trades) because `WEAK_SWING` was prioritized over them.
- `WEAK_SWING` targets absorbed 29 trades and generated **$-26.02\text{R}$ of destruction**.

---

## 7. Formal Classification & Research Decision

In accordance with the pre-registered governance decision matrix:

| Classification | Pre-Registered Standard | Empirical Reality | Status |
| :--- | :--- | :--- | :---: |
| **B1 — Strongly Supportive** | Expectancy materially improves | Expectancy declined from -0.54R to -0.67R | **FALSIFIED** |
| **B2 — Mixed** | Target reachability improves | Target reachability fell from 6.90% to 2.44% | **FALSIFIED** |
| **B3 — Negative** | Structural targets worsen expectancy / create unacceptable behavior | **Expectancy worsened, net R collapsed, target hits halved** | **SUPPORTED (VERDICT)** |
| **B4 — Inconclusive** | Differences too small / sparse sample | Sample expanded from 29 to 41; deltas are large and clear | **FALSIFIED** |

### Formal Research Verdict:
$$\mathbf{DECISION: \quad B3 \text{ — NEGATIVE (REJECT TREATMENT)}}$$

1. **Reject `EXP_TARGET_STRUCTURAL_01`:** Do not promote `STRUCTURAL_OBJECTIVE` target selection to the canonical strategy.
2. **Preserve H0 as Frozen Control:** The corrected Canonical H0 (`CLOSEST_OBJECTIVE`, N=29) remains the authoritative baseline control.
3. **Implication for Experiment C:** The data definitively proves that the failure of the platform is **NOT** that price fails to reach distant structural objectives; the failure is that the **trade management mechanism cannot capture and monetize the $+1.5\text{R} \text{ to } +6.25\text{R}$ excursions that price routinely provides**.
4. **Execution Gate:** In strict adherence to directive instructions, **zero subsequent strategy code has been altered**. We await formal user review of this report before proceeding to **Experiment C (Trade Management & Monetization)**.
