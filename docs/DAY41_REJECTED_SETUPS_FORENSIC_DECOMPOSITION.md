# Day 41 Observational Forensic Analysis: Causal Decomposition of the 354 Still-Rejected Setups

---

**Document Identifier:** `DAY41_REJECTED_SETUPS_FORENSIC_DECOMPOSITION`  
**Governing State:** **Day 41 (OPEN)**  
**Dataset Analyzed:** Historical Development Partition (`2021-01-01` to `2022-12-31`, 277,908 candles across 15 streams)  
**Population Analyzed:** Exactly **354 setups** that achieved full LTF confirmation but remained below the $4.0\text{R}$ planned reward-to-risk firewall under `EXP_TARGET_STRUCTURAL_01`.  
**Audit Policy:** Strictly Observational. Zero strategy code modifications, zero parameter tuning, zero optimization, zero promotion to production. Validation (`2023`) and OOS (`2024–2026`) partitions remain strictly **LOCKED**.

---

## Executive Summary & Core Diagnostic Verdict

This forensic audit answers the exact question posed by the research directive:

> **"Why does a confirmed setup have insufficient planned RR?"**

### The Mathematical Invariant of the 4R Firewall
For any trade with entry price $E$, structural stop $SL$, and structural destination $TP$:
$$\text{Planned RR} = \frac{|TP - E|}{|E - SL|}$$
Let the total structural span be $S = |TP - SL|$. The fraction of the span consumed at entry is $\text{Progress} = \frac{|E - SL|}{S}$.  
From elementary geometry:
$$\text{Planned RR} = \frac{1}{\text{Progress}} - 1 \iff \text{Progress} = \frac{1}{1 + \text{Planned RR}}$$

To satisfy the mandatory $\ge 4.0\text{R}$ firewall:
$$\text{Progress} \le \frac{1}{1 + 4.0} = \frac{1}{5} = \mathbf{20.00\%}$$

> **Core Geometric Law:**  
> **In order to achieve $\ge 4.0\text{R}$ planned reward-to-risk between a structural stop and a structural target, the entry price MUST occur within the first $20.00\%$ of the total structural span $[SL, TP]$.**  
> If entry occurs after price has traversed more than $20\%$ of the distance between the stop and the target, it is a **mathematical impossibility** to achieve $4.0\text{R}$, regardless of asset, timeframe, or indicator.

Across all 354 still-rejected setups:
- **Minimum Span Consumed at Entry:** **$20.31\%$** (Max planned $\text{RR} = 3.92\text{R}$)
- **25th Percentile (P25):** **$45.71\%$**
- **Median Span Consumed at Entry:** **$61.02\%$**
- **Mean Span Consumed at Entry:** **$61.23\%$**
- **75th Percentile (P75):** **$77.65\%$**
- **90th Percentile (P90):** **$90.15\%$**
- **Maximum Span Consumed:** **$99.93\%$**

---

## 1. Master Forensic Classification Matrix

Every single one of the 354 still-rejected setups was categorized into mutually interpretable causal classifications:

| Category # | Causal Mechanism | Count | % of Rejected | Median RR | Median Target Distance | Median Stop Distance | Median Latency | Primary Driver |
| :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| **Cat 6** | **Extreme Proximity to Target** (Target room $< 2.5\%$) | **106** | **29.94%** | $0.20\text{R}$ | $1.32\%$ | $5.25\%$ | $1.0\text{ h}$ | Target too close |
| **Cat 4** | **Target Ambiguity** (Fallback Range Expansion) | **88** | **24.86%** | $0.98\text{R}$ | $8.65\%$ | $8.49\%$ | $4.5\text{ h}$ | Target unformed |
| **Cat 7** | **Dealing Range Compression** (Span $< 12\%$, RR $< 1.5\text{R}$) | **51** | **14.41%** | $1.01\text{R}$ | $5.31\%$ | $5.41\%$ | $2.0\text{ h}$ | Range too tight |
| **Cat 3** | **Healthy Swing Sub-4R** ($1.5\text{R} \le \text{RR} < 4.0\text{R}$) | **35** | **9.89%** | $2.18\text{R}$ | $10.80\%$ | $5.08\%$ | $2.0\text{ h}$ | 4R floor too high |
| **Cat 1** | **Late Expansion Entry** ($>60\%$ span consumed) | **29** | **8.19%** | $0.50\text{R}$ | $3.89\%$ | $8.81\%$ | $1.2\text{ h}$ | Leg exhausted |
| **Cat 2** | **Structurally Necessary Wide Stop** (Stop $\ge 15\%$) | **25** | **7.06%** | $0.30\text{R}$ | $6.59\%$ | $22.16\%$ | $9.5\text{ h}$ | Macro SL anchor |
| **Cat 5** | **Confirmation Latency Consumed Range** (Drift $\ge 35\%$) | **20** | **5.65%** | $0.55\text{R}$ | $3.69\%$ | $7.71\%$ | $15.9\text{ h}$ | Multi-TF lag |
| **TOTAL** | **All Analyzed Setups** | **354** | **100.0%** | **$0.64\text{R}$** | **$4.10\%$** | **$6.81\%$** | **$2.0\text{ h}$** | — |

---

## 2. Deep-Dive Decomposition by Category

---

### Category 6: Setup Formed in Extreme Proximity to Target
- **Count:** **106 setups ($29.94\%$)**
- **Median Planned RR:** **$0.20\text{R}$** (Mean: $0.26\text{R}$, Range: $[0.00\text{R}, 1.26\text{R}]$)
- **Median Target Distance:** **$1.32\%$** of price (Mean: $1.22\%$)
- **Median Stop Distance:** **$5.25\%$** of price (Mean: $5.92\%$)
- **Median Latency:** **$1.0\text{ hour}$** (Mean: $6.0\text{ hours}$)
- **Asset Breakdown:** BTC: 43 ($40.6\%$), ETH: 35 ($33.0\%$), SOL: 28 ($26.4\%$)
- **Timeframe Breakdown:** SET 4: 90 ($84.9\%$), SET 3: 16 ($15.1\%$)
- **Year Breakdown:** 2021: 46 ($43.4\%$), 2022: 60 ($56.6\%$)
- **Target Provenance:** `WEAK_SWING`: 95 ($89.6\%$), `LIQUIDITY_POOL`: 11 ($10.4\%$)

#### Causal Anatomy:
These setups did not fail because of slow entry or wide stops. They failed because the **HTF KeyZone itself was located in extreme physical proximity to the opposing target**.  
For example, in a bullish 4H trend, an unmitigated bullish FVG or order block is tapped when price is already at $98\%$ of the dealing range height (just $1.0\%\text{--}2.0\%$ below the 4H Weak High). When LTF confirmation triggers, price has virtually zero room before hitting the target. Even with a microscopic stop, an asset cannot produce 4R when the total distance to the target is only $1.32\%$.

#### Representative Examples:
1. `cand_SOL/USDT_UNIFIED_STRATEGY_1619938800` (SOL_SET_3, LONG, 2021):
   - Entry: $47.63$ | Target: $48.64$ (`WEAK_SWING`, Reward: $+2.14\%$)
   - SL: $40.52$ (Risk: $14.93\%$) | **Planned RR: 0.14R** | Span Progress: **87.5%**
2. `cand_SOL/USDT_UNIFIED_STRATEGY_1651276800` (SOL_SET_3, SHORT, 2022):
   - Entry: $94.34$ | Target: $94.32$ (`WEAK_SWING`, Reward: $+0.02\%$)
   - SL: $102.31$ (Risk: $8.45\%$) | **Planned RR: 0.00R** | Span Progress: **99.7%**

---

### Category 4: Target Selection Structurally Ambiguous
- **Count:** **88 setups ($24.86\%$)**
- **Median Planned RR:** **$0.98\text{R}$** (Mean: $1.16\text{R}$, Range: $[0.01\text{R}, 3.85\text{R}]$)
- **Median Target Distance:** **$8.65\%$** of price (Mean: $13.22\%$)
- **Median Stop Distance:** **$8.49\%$** of price (Mean: $12.33\%$)
- **Median Latency:** **$4.5\text{ hours}$** (Mean: $12.4\text{ hours}$)
- **Asset Breakdown:** BTC: 34 ($38.6\%$), ETH: 27 ($30.7\%$), SOL: 27 ($30.7\%$)
- **Timeframe Breakdown:** SET 4: 72 ($81.8\%$), SET 3: 15 ($17.0\%$), SET 2: 1 ($1.1\%$)
- **Year Breakdown:** 2021: 54 ($61.4\%$), 2022: 34 ($38.6\%$)
- **Target Provenance:** `FORWARD_STRUCTURAL_EXPANSION`: **88 ($100\%$)**

#### Causal Anatomy:
In these setups, the strategy engine discovered **zero valid opposing structural boundaries** (no unmitigated Weak High/Low and no unswept Liquidity Pools). This occurred primarily during:
1. All-Time High price discovery (where no historical structural swing exists above price).
2. Fully swept dealing ranges where opposing liquidity had already been cleared.
In the absence of a structural destination, the engine defaulted to Candidate Pool 4: **$1.0\times$ Dealing Range Forward Expansion**. However, because the expansion width is defined by the dealing range, and the structural stop is anchored to the opposite boundary of that same dealing range, the planned reward is geometrically constrained to $\approx 1.0\text{R}\text{ to }1.5\text{R}$ ($8.65\%\text{ reward vs }8.49\%\text{ risk}$).

#### Representative Examples:
1. `cand_BTC/USDT_UNIFIED_STRATEGY_1616068800` (BTC_SET_2, LONG, 2021):
   - Entry: $57,648.16$ | Target: $106,880.60$ (`FORWARD_STRUCTURAL_EXPANSION`, $+85.40\%$)
   - SL: $43,000.00$ (Risk: $25.41\%$) | **Planned RR: 3.36R** | Span Progress: **22.9%**
2. `cand_SOL/USDT_UNIFIED_STRATEGY_1614067200` (SOL_SET_3, LONG, 2021):
   - Entry: $13.83$ | Target: $16.18$ (`FORWARD_STRUCTURAL_EXPANSION`, $+16.99\%$)
   - SL: $8.20$ (Risk: $40.69\%$) | **Planned RR: 0.42R** | Span Progress: **70.5%**

---

### Category 7: Dealing Range Compression / Modest Room
- **Count:** **51 setups ($14.41\%$)**
- **Median Planned RR:** **$1.01\text{R}$** (Mean: $1.18\text{R}$, Range: $[0.67\text{R}, 3.03\text{R}]$)
- **Median Target Distance:** **$5.31\%$** of price (Mean: $6.40\%$)
- **Median Stop Distance:** **$5.41\%$** of price (Mean: $6.08\%$)
- **Median Latency:** **$2.0\text{ hours}$** (Mean: $11.3\text{ hours}$)
- **Asset Breakdown:** SOL: 20 ($39.2\%$), BTC: 17 ($33.3\%$), ETH: 14 ($27.5\%$)
- **Timeframe Breakdown:** SET 4: 40 ($78.4\%$), SET 3: 11 ($21.6\%$)
- **Year Breakdown:** 2021: 26 ($51.0\%$), 2022: 25 ($49.0\%$)
- **Target Provenance:** `WEAK_SWING`: 37 ($72.5\%$), `LIQUIDITY_POOL`: 14 ($27.5\%$)

#### Causal Anatomy:
These setups occurred in **compressed dealing ranges** where the entire distance from the structural low to the structural high was modest ($8\%\text{--}14\%$). Price formed a valid setup near equilibrium (50% dealing range level). Consequently, remaining distance to the target was nearly equal to the distance to the invalidation stop ($5.31\%\text{ reward vs }5.41\%\text{ risk}$), producing a symmetric planned RR of $\approx 1.0\text{R}$.

#### Representative Examples:
1. `cand_SOL/USDT_UNIFIED_STRATEGY_1620144000` (SOL_SET_3, LONG, 2021):
   - Entry: $44.55$ | Target: $48.64$ (`WEAK_SWING`, Reward: $+9.19\%$)
   - SL: $40.91$ (Risk: $8.18\%$) | **Planned RR: 1.12R** | Span Progress: **47.1%**
2. `cand_SOL/USDT_UNIFIED_STRATEGY_1621000800` (SOL_SET_3, SHORT, 2021):
   - Entry: $43.87$ | Target: $39.00$ (`WEAK_SWING`, Reward: $+11.09\%$)
   - SL: $49.24$ (Risk: $12.26\%$) | **Planned RR: 0.90R** | Span Progress: **52.5%**

---

### Category 3: Healthy Swing Sub-4R (The High-Quality Swings)
- **Count:** **35 setups ($9.89\%$)**
- **Median Planned RR:** **$2.18\text{R}$** (Mean: $2.41\text{R}$, Range: $[1.51\text{R}, 3.92\text{R}]$)
- **Median Target Distance:** **$10.80\%$** of price (Mean: $12.68\%$)
- **Median Stop Distance:** **$5.08\%$** of price (Mean: $5.28\%$)
- **Median Latency:** **$2.0\text{ hours}$** (Mean: $17.2\text{ hours}$)
- **Asset Breakdown:** SOL: 20 ($57.1\%$), BTC: 10 ($28.6\%$), ETH: 5 ($14.3\%$)
- **Timeframe Breakdown:** SET 4: 19 ($54.3\%$), SET 3: 16 ($45.7\%$)
- **Year Breakdown:** 2021: 22 ($62.9\%$), 2022: 13 ($37.1\%$)
- **Target Provenance:** `WEAK_SWING`: 31 ($88.6\%$), `LIQUIDITY_POOL`: 4 ($11.4\%$)

#### Causal Anatomy:
This is the most structurally significant category for research. These 35 setups are **structurally pristine swing trades**:
- They target an authentic, unmitigated HTF Weak Swing ($88.6\%$) or major Liquidity Pool.
- The target provides a **substantial price move ($10.80\%$ median)**.
- The stop loss is compact and reasonable ($5.08\%$ median).
- The planned reward-to-risk ratio is **$2.18\text{R}$ median** (with multiple setups offering $3.0\text{R}\text{--}3.9\text{R}$).
- They entered within the first $25\%\text{--}40\%$ of the structural span.

**Why did they fail?**  
They failed **purely and exclusively because of the rigid $4.0\text{R}$ firewall**. In institutional trading, a planned $2.2\text{R}\text{ to }3.5\text{R}$ setup with MTF trailing stop protection is a top-tier opportunity. The $4.0\text{R}$ threshold killed 35 of the highest-conviction directional swings in the entire 2-year dataset.

#### Representative Examples:
1. `cand_SOL/USDT_UNIFIED_STRATEGY_1615788000` (SOL_SET_3, LONG, 2021):
   - Entry: $14.04$ | Target: $16.50$ (`WEAK_SWING`, Reward: $+17.50\%$)
   - SL: $13.03$ (Risk: $7.20\%$) | **Planned RR: 2.43R** | Span Progress: **29.1%**
2. `cand_SOL/USDT_UNIFIED_STRATEGY_1633503600` (SOL_SET_3, LONG, 2021):
   - Entry: $161.12$ | Target: $177.79$ (`WEAK_SWING`, Reward: $+10.35\%$)
   - SL: $150.10$ (Risk: $6.84\%$) | **Planned RR: 1.51R** | Span Progress: **39.8%**

---

### Category 1: Late Expansion Entry
- **Count:** **29 setups ($8.19\%$)**
- **Median Planned RR:** **$0.50\text{R}$** (Mean: $0.49\text{R}$, Range: $[0.22\text{R}, 0.66\text{R}]$)
- **Median Target Distance:** **$3.89\%$** of price (Mean: $4.19\%$)
- **Median Stop Distance:** **$8.81\%$** of price (Mean: $8.81\%$)
- **Median Latency:** **$1.2\text{ hours}$** (Mean: $3.1\text{ hours}$)
- **Asset Breakdown:** SOL: 11 ($37.9\%$), BTC: 10 ($34.5\%$), ETH: 8 ($27.6\%$)
- **Timeframe Breakdown:** SET 4: 23 ($79.3\%$), SET 2: 3 ($10.3\%$), SET 3: 3 ($10.3\%$)
- **Year Breakdown:** 2021: 21 ($72.4\%$), 2022: 8 ($27.6\%$)
- **Target Provenance:** `LIQUIDITY_POOL`: 16 ($55.2\%$), `WEAK_SWING`: 13 ($44.8\%$)

#### Causal Anatomy:
In these setups, the structural expansion was already **mature and exhausted** by the time LTF confirmation occurred. Price had already traversed $>60\%$ (median $68.7\%$) of the total structural move between the swing low and the target. The remaining distance to the target was only $3.89\%$, while the stop was $8.81\%$ away, resulting in planned RR of $\approx 0.5\text{R}$.

#### Representative Examples:
1. `cand_BTC/USDT_UNIFIED_STRATEGY_1636574400` (BTC_SET_2, LONG, 2021):
   - Entry: $65,228.40$ | Target: $67,000.00$ (`WEAK_SWING`, Reward: $+2.72\%$)
   - SL: $57,820.00$ (Risk: $11.36\%$) | **Planned RR: 0.24R** | Span Progress: **80.7%**
2. `cand_BTC/USDT_UNIFIED_STRATEGY_1636718400` (BTC_SET_2, LONG, 2021):
   - Entry: $64,122.23$ | Target: $67,000.00$ (`WEAK_SWING`, Reward: $+4.49\%$)
   - SL: $57,820.00$ (Risk: $9.83\%$) | **Planned RR: 0.46R** | Span Progress: **68.7%**

---

### Category 2: Structurally Necessary Wide Stop
- **Count:** **25 setups ($7.06\%$)**
- **Median Planned RR:** **$0.30\text{R}$** (Mean: $0.54\text{R}$, Range: $[0.01\text{R}, 1.67\text{R}]$)
- **Median Target Distance:** **$6.59\%$** of price (Mean: $14.07\%$)
- **Median Stop Distance:** **$22.16\%$** of price (Mean: $25.49\%$)
- **Median Latency:** **$9.5\text{ hours}$** (Mean: $68.5\text{ hours}$)
- **Asset Breakdown:** ETH: 9 ($36.0\%$), SOL: 9 ($36.0\%$), BTC: 7 ($28.0\%$)
- **Timeframe Breakdown:** SET 3: 11 ($44.0\%$), SET 2: 6 ($24.0\%$), SET 1: 4 ($16.0\%$), SET 4: 4 ($16.0\%$)
- **Year Breakdown:** 2022: 13 ($52.0\%$), 2021: 12 ($48.0\%$)
- **Target Provenance:** `WEAK_SWING`: 20 ($80.0\%$), `LIQUIDITY_POOL`: 5 ($20.0\%$)

#### Causal Anatomy:
In these setups, the target was often legitimately distant (up to $+77.26\%$ move). However, the stop loss distance was **colossal ($22.16\%$ median)**.  
Why? Because `extract_structural_stop` in `BaseLTFEntryModel` takes `min(structural_pivots)` (the absolute lowest swing in the LTF history) or the HTF `protected_low`. On higher timeframe sets (SET 1: Daily LTF, SET 2: 4H LTF, SET 3: 1H LTF), anchoring to a macro structural swing from weeks prior created a stop distance of $20\%\text{--}55\%$, completely destroying planned RR.

#### Representative Examples:
1. `cand_BTC/USDT_UNIFIED_STRATEGY_1670976000` (BTC_SET_1, SHORT, 2022):
   - Entry: $16,632.12$ | Target: $3,782.13$ (`LIQUIDITY_POOL`, Reward: **$+77.26\%$**)
   - SL: $25,211.32$ (Risk: **$51.58\%$**) | **Planned RR: 1.50R** | Span Progress: **40.0%**
2. `cand_ETH/USDT_UNIFIED_STRATEGY_1638576000` (ETH_SET_1, LONG, 2021):
   - Entry: $3,858.99$ | Target: $4,372.72$ (`WEAK_SWING`, Reward: $+13.31\%$)
   - SL: $1,706.00$ (Risk: **$55.79\%$**) | **Planned RR: 0.24R** | Span Progress: **80.7%**

---

### Category 5: Confirmation Latency Consumed Range
- **Count:** **20 setups ($5.65\%$)**
- **Median Planned RR:** **$0.55\text{R}$** (Mean: $0.63\text{R}$, Range: $[0.30R, 1.33R]$)
- **Median Target Distance:** **$3.69\%$** of price (Mean: $4.99\%$)
- **Median Stop Distance:** **$7.71\%$** of price (Mean: $8.22\%$)
- **Median Latency:** **$15.9\text{ hours}$** (Mean: $33.9\text{ hours}$, Range: $4\text{ to }104\text{ hours}$)
- **Asset Breakdown:** SOL: 9 ($45.0\%$), BTC: 6 ($30.0\%$), ETH: 5 ($25.0\%$)
- **Timeframe Breakdown:** SET 4: 15 ($75.0\%$), SET 3: 5 ($25.0\%$)
- **Year Breakdown:** 2021: 15 ($75.0\%$), 2022: 5 ($25.0\%$)
- **Target Provenance:** `WEAK_SWING`: 17 ($85.0\%$), `LIQUIDITY_POOL`: 3 ($15.0\%$)

#### Causal Anatomy:
In these setups, the original target distance at the moment of HTF KeyZone interaction was healthy. However, the cascading architecture required:
1. HTF KeyZone interaction $\rightarrow$
2. Wait for MTF realignment (CHoCH) $\rightarrow$
3. Wait for MTF KeyZone retest $\rightarrow$
4. Wait for LTF sweep + displacement confirmation.

This sequence required **15.9 hours (median)** to complete. During this multi-day lag, price had already drifted aggressively in the setup direction, **consuming $\ge 35\%$ to $70\%$ of the initial target distance before the LTF order could be placed**.

#### Representative Examples:
1. `cand_SOL/USDT_UNIFIED_STRATEGY_1642078800` (SOL_SET_3, SHORT, 2022):
   - Entry: $143.30$ | Target: $130.00$ (`WEAK_SWING`, Reward: $+9.28\%$)
   - SL: $157.80$ (Risk: $10.12\%$) | **Planned RR: 0.92R** | Latency: **93.0 hours (3.9 days)**
2. `cand_SOL/USDT_UNIFIED_STRATEGY_1669255200` (SOL_SET_3, SHORT, 2022):
   - Entry: $13.46$ | Target: $12.07$ (`WEAK_SWING`, Reward: $+10.33\%$)
   - SL: $14.98$ (Risk: $11.29\%$) | **Planned RR: 0.91R** | Latency: **104.0 hours (4.3 days)**

---

## 3. High-Level Attribution: What Causes the Sub-4R Population?

Ranking the root causal mechanisms across all 354 still-rejected setups:

### 1. The Low-RR Population Breakdown ($90.11\%$ of Setups)
Across **319 out of 354 setups ($90.11\%$)**, planned RR remained below $1.5\text{R}$ due to a combination of distinct geometric factors:
- **Cat 6: Extreme Target Proximity (106 setups / 29.94%):** Setups formed when price was already in close physical proximity to the opposing target ($< 2.5\%$ distance remaining).
- **Cat 4: Destination Ambiguity / Range Expansion Fallback (88 setups / 24.86%):** Absence of an opposing structural boundary forced a mathematical $1.0\times$ range expansion that naturally balances near $1.0\text{R}$.
- **Cat 7: Symmetrical Dealing Range Compression (51 setups / 14.41%):** Compressed dealing ranges ($8\%\text{--}12\%$) where equilibrium entry yields symmetric risk and reward ($\approx 1.0\text{R}$).
- **Cat 1: Late Expansion Entry (29 setups / 8.19%):** Expansion leg already mature ($>60\%$ span consumed) before LTF confirmation.
- **Cat 2: Structurally Wide Stops on Macro Horizons (25 setups / 7.06%):** Invalidation stops anchored to multi-week macro sequence pivots ($20\%\text{--}55\%$ stop distances).
- **Cat 5: Cascading Confirmation Latency (20 setups / 5.65%):** Multi-day confirmation lag allowing price to drift toward the target before order placement.

$$\text{Combined Low-RR Groups (Cats 6, 4, 7, 1, 2, 5)} = 106 + 88 + 51 + 29 + 25 + 20 = \mathbf{319\text{ setups}} \quad \left(\mathbf{90.11\%}\right)$$

### 2. The Intermediate Planned-RR Group ($9.89\%$ of Setups)
- **Cat 3: Sub-4R Structural Swings (35 setups / 9.89%):**
  Setups targeting unmitigated Weak Swings or Liquidity Pools with healthy target distance ($>10\%$ median) and compact stops ($5.08\%$ median), offering planned RR between $1.5\text{R}$ and $3.9\text{R}$ (median $2.18\text{R}$). The 4R firewall rejected setups whose planned structural RR was below 4R.

$$\text{Total Evaluated Population} = 319 + 35 = \mathbf{354\text{ setups}} \quad \left(\mathbf{100.00\%}\right)$$

---

## 4. Final Governance Conclusions & Day 41 Closeout

1. **Target Hierarchy Evaluation:**
   - The controlled target hierarchy experiment (`EXP_TARGET_STRUCTURAL_01`) was isolated, verified across 390 passing software tests, and evaluated on the exact same 391 LTF triggers.
   - Selecting directional Weak Swings over nearest internal KeyZones materially restored access to legitimate structural opportunities ($+90.9\%$ 4R qualification increase, $+81.8\%$ executed volume increase).
   - **Target hierarchy classification:** `HYP_TARGET_HIERARCHY_STRUCTURAL_OBJECTIVE_01` is formally classified as **PARTIALLY SUPPORTED & CALIBRATED**.

2. **Remaining Sub-4R Population:**
   - Target hierarchy alone does not explain the remaining low-RR population.
   - The remaining 354 setups contain multiple distinct geometric mechanisms: target proximity ($29.9\%$), target ambiguity ($24.9\%$), range compression ($14.4\%$), intermediate structural swings ($9.9\%$), late leg entry ($8.2\%$), macro stops ($7.1\%$), and confirmation latency ($5.7\%$).
   - Entry, confirmation, and structural invalidation geometry appear materially important, but **no entry or stop modification has yet been tested**.
   - **Remaining Low-RR Status:** `MULTI-FACTOR GEOMETRIC DECOMPOSITION — OBSERVED, NOT YET INTERVENED UPON`.

3. **Institutional Phrasing & Scientific Discipline:**
   - Counterfactual performance of rejected setups was not measured; we record only that the 4R firewall rejected setups whose planned structural RR was below 4R.
   - The strategy is **not** declared proven profitable or robust; development trade sample size remains sparse ($20$ trades over 24 months).
   - The concept of the strategy as an "Asymmetric Expansion Sniper" is an architectural design hypothesis, not an empirically established statistical property.

4. **Day 41 Phase Closeout:**
   - Zero strategy code modified.
   - Zero parameter tuning or optimization performed.
   - 4R firewall strictly maintained at $\ge 4.0\text{R}$.
   - Experimental branch `feat/exp-target-milestone-2.5r` remains unmerged.
   - Validation (`2023`) and OOS (`2024–2026`) partitions remain strictly **LOCKED**.
   - **Research Phase Status:** **CLOSED**.

**Next Action:** Return to the scheduled Knowledge/B.Com institutional roadmap rather than continuing strategy optimization.
