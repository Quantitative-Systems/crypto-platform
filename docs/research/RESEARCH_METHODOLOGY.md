# Crypto Trading Platform — Quantitative Research Methodology

**Version:** 1.0.0  
**Status:** Canonical Reference  
**Audience:** Quantitative Researchers, Risk Officers, System Architects  

---

## 1. Core Principles of Research Truth

The Crypto Trading Platform enforces a strict empirical standard: **historical backtests represent research hypotheses, not financial guarantees.** Real alpha can only be demonstrated through forward paper trading and verified live execution.

To guarantee that research results are untainted by statistical artifacts, all platform research pipelines enforce four fundamental safeguards:

1. **Strict Temporal Separation (Walk-Forward Validation):**  
   All historical evaluations divide available data chronologically into:
   * **Development (DEV):** 2021-01-01 to 2022-12-31 (In-sample exploration)
   * **Validation (VAL):** 2023-01-01 to 2024-05-31 (Hyperparameter calibration & screening)
   * **Out-of-Sample (OOS):** 2024-06-01 to 2026-03-31 (Final blind evaluation)
   
   Data from the OOS window is **never** accessible during indicator calculation, signal tuning, parameter optimization, or feature engineering.

2. **Causal Execution & Fill Semantics:**  
   * **Next-Bar-Open Fills:** Signals generated on the close of bar $t$ can only execute at the open of bar $t+1$. Zero intrabar lookahead.
   * **Adverse-First Collision Resolution:** When both a stop-loss and take-profit target fall within the high-low range of the same candle, the simulation resolves the stop-loss first (maximum adverse execution assumption).
   * **Explicit Transaction Frictions:** Every simulated trade deducts full taker fees (6 bps per leg on futures, 10 bps on spot) plus empirical slippage (3 bps on liquid pairs, up to 15 bps on illiquid pairs) and exchange maker/taker fee structures.

3. **Multi-Horizon Economic Feasibility:**  
   Before any strategy is evaluated for statistical predictability, its target trading horizon is evaluated against empirical bid-ask spread and transaction costs:
   $$\text{Cost/Stop Ratio} = \frac{\text{All-In Roundtrip Cost}}{\text{Median Stop Distance (1R)}}$$
   Where $\text{Cost/Stop Ratio} > 0.33$, the horizon is classified as **FEE_BLOCKED** and rejected without further modeling. Sub-15m taker scalping is empirically fee-blocked under standard commercial exchange fee tiers.

4. **Multi-Stage Promotion Gates (G1–G7):**  
   Every strategy book must clear seven sequential criteria to achieve `PROMOTABLE_PAPER_ONLY` status:
   * **G1 (Sample Size):** Minimum 30 independent closed trades in OOS window.
   * **G2 (Positive Expectancy):** Net expectancy $E(R) > 0.05R$ after full fees.
   * **G3 (Profit Factor):** Profit factor $\ge 1.25$ in both VAL and OOS.
   * **G4 (Drawdown Cap):** Maximum drawdown $\le 25\%$ across the lifetime of the strategy.
   * **G5 (Walk-Forward Ratio):** OOS expectancy $\ge 0.50 \times \text{DEV expectancy}$ (generalization stability).
   * **G6 (Cost Shock Resilience):** Net expectancy remains $> 0$ when transaction costs are multiplied by $1.5\times$.
   * **G7 (Portfolio Marginal Contribution):** Strategy must add marginal Sharpe ratio to the existing multi-book portfolio.

---

## 2. Forensic Bias Audit Checklist

The research engine automatically verifies each candidate against common quantitative pitfalls:

| Bias Type | Risk Description | Platform Safeguard |
|---|---|---|
| **Lookahead Bias** | Using future data (e.g. daily close before it occurs) | Next-bar open execution, causal lag shift on all indicators |
| **Survivorship Bias** | Testing only on surviving coins | Dataset spans point-in-time universe snapshot; de-listed coins retained |
| **Selection Bias** | Selecting best parameters from hundreds of trials | Strict DEV/VAL/OOS split; parameter perturbation test |
| **Data Leakage** | Scaling/normalizing using whole dataset statistics | Rolling z-scores and expanding quantiles only; no global parameters |
| **Overlapping Windows** | Multi-day indicators introducing serial correlation | Block-bootstrapped statistical tests; Purged k-fold cross-validation |
| **Unrealistic Liquidity** | Sizing larger than order-book depth | Participation cap $\le 1.5\%$ of 15m candle volume |
| **Unrealistic Fills** | Assuming midpoint execution | Limit orders require price crossing; Post-only rejections modeled |

---

## 3. Funding Rate & Basis Model Specifications

The platform models funding rate carry and calendar basis using explicit, parameterized mechanics:

$$\text{Net Carry Yield} = \sum_{t=1}^{N} \left[ F_t \cdot S_t \right] - C_{\text{entry}} - C_{\text{exit}} - C_{\text{borrow}} - C_{\text{rebalance}} \pm \Delta \text{Basis}$$

Where:
* $F_t$: 8-hour perpetual funding rate paid/received at 00:00, 08:00, 16:00 UTC.
* $S_t$: Spot/Perpetual hedge position size.
* $C_{\text{entry}}, C_{\text{exit}}$: Entry and exit taker/maker fees and slippage across both legs.
* $C_{\text{borrow}}$: Margin loan interest on spot collateral (typically 6%–12% APR).
* $C_{\text{rebalance}}$: Execution drag from re-aligning delta hedge during price trends.
* $\Delta \text{Basis}$: PnL impact from spot-perpetual basis divergence (expansion/contraction).

### Stress Testing Requirements
No carry book can be promoted solely on historical yield. Every candidate must undergo sensitivity testing under:
1. **Yield Compression:** 25%, 50%, and 75% reduction in funding rate APR.
2. **Regime Inversion:** Sustained backwardation (funding rate $< 0$).
3. **Basis Shock:** 50 bps adverse basis widening.
4. **Capital Allocation Cap:** Maximum 15%–25% portfolio weight to prevent single-strategy dominance.

---

## 4. Operational Classification of Strategy Results

The platform maintains four mutually exclusive performance states:

```
[ HISTORICAL RESEARCH ] 
       │
       ▼ (Passes G1-G7 + Stress Tests)
[ VALIDATED CANDIDATE ]
       │
       ▼ (Promoted by Discovery Engine)
[ FORWARD PAPER TRADING ] (Minimum 30-90 Days Live Market Feed)
       │
       ▼ (Explicit Human Authorization + Risk Sign-off)
[ CONTROLLED LIVE TRADING ] (Live Capital, Hard Stop Limits)
```

**Never** describe historical backtests as live profitability. All investor and customer materials must clearly display realized live performance metrics separately from historical simulations.
