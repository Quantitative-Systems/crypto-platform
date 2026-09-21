# QCP Certified 10-Asset Universe Specification
**Directive**: EABG-001  
**Platform**: Quantitative Crypto Platform (QCP)  
**Status**: Canonical Specification  
**Registry Reference**: `platform_core/asset_universe_registry.py`  
**Registry JSON**: `research/results/ASSET_UNIVERSE_REGISTRY.json`  
**Capital Allocation**: $0.00 (Fail-Closed Governance Firewall)

---

## Executive Summary: Objective Universe Selection

Under **Directive EABG-001**, the platform expands its research horizon from the initial 3-asset baseline (`BTC`, `ETH`, `SOL`) to an objectively selected **10-Asset Research Universe**.

The platform rejects arbitrary selection by name recognition. Instead, membership in the QCP Universe is governed by quantitative, measurable hurdles covering liquidity, historical depth, multi-venue availability, derivatives support, and survivorship bias controls.

```
                         UNIVERSE GOVERNANCE FUNNEL
                                      
                         [ ALL CRYPTO ASSETS (10,000+) ]
                                      │
                                      ▼  Market Cap <= 20 & Volume >= $50M/day
                         [ LIQUID CANDIDATES (Top 20) ]
                                      │
                                      ▼  History >= 730d & Venues >= 2 & Perp Derivs
                         [ CERTIFIED RESEARCH UNIVERSE (10) ]
                                      │
                                      ▼  Cross-Asset & Causal OOS Validation
                         [ CANDIDATE STRATEGIES ]
                                      │
                                      ▼  Forward Paper Burn-In (Zero Duplicates)
                         [ FORWARD QUALIFIED (3 Assets: BTC, ETH, SOL) ]
                                      │
                                      ▼  Production Signoff ($0.00 Live Capital)
                         [ PRODUCTION TRADING UNIVERSE (0 Live Capital) ]
```

> [!IMPORTANT]
> **Core Invariant: Asset Universe $\ne$ Trading Universe**:
> The 10 assets represent the **Certified Research Universe** for empirical hypothesis testing, cross-asset generalization, and factor decomposition. Only assets with fully validated strategies and forward paper burn-in qualify for the **Trading Universe**. Currently, **7 of the 10 assets remain strictly in `RESEARCH_CANDIDATE` status and are `PRODUCTION_BLOCKED`.**

---

## Objective Eligibility Hurdles

An asset is eligible for inclusion in the Research Universe only if it satisfies all seven quantitative criteria:

| Metric | Minimum Hurdle | Rationale |
| :--- | :--- | :--- |
| **Market Cap Rank** | $\le 20$ | Ensures substantial institutional float and global market recognition. |
| **Median Daily Volume** | $\ge \$50,000,000$ USD | Prevents illiquidity traps; ensures minimal market impact for simulated order sizing. |
| **Historical Data Depth** | $\ge 730$ Days (2 Years) | Mandatory for multi-year partition testing (`DEV` vs `VAL` vs `OOS`). |
| **Primary Venues** | $\ge 2$ Tier-1 Exchanges | Multi-venue availability (Binance, OKX, Bybit, Coinbase) ensures spatial price discovery. |
| **Perpetual Derivatives** | Required (Active Funding) | Enables directional delta-hedging, funding carry, and basis modeling. |
| **Typical Spread** | $\le 12.0$ bps | Tight top-of-book spreads guarantee that transaction costs do not dominate small edges. |
| **Survivorship Status** | `ACTIVE` (Audited History) | Delisted and halted coins are tracked to eliminate survivorship bias in historical backtests. |

---

## The Canonical 10-Asset Universe

| Symbol | Base | Category | Cap Rank | Daily Volume | History | Typical Spread | Governance Status | Economic Purpose |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **BTC/USDT** | BTC | Store of Value | #1 | $25.0B | 3,300d | 1.0 bps | `CERTIFIED_BENCHMARK` | Primary macro benchmark & store-of-value; deepest liquidity |
| **ETH/USDT** | ETH | Smart Contract L1 | #2 | $12.0B | 3,300d | 1.5 bps | `CERTIFIED_BENCHMARK` | Smart-contract ecosystem benchmark; DeFi reference rate |
| **SOL/USDT** | SOL | High-Beta L1 | #5 | $3.5B | 1,800d | 2.5 bps | `CERTIFIED_BENCHMARK` | High-throughput alternative L1; forward paper burn-in asset |
| **BNB/USDT** | BNB | Exchange Ecosystem | #4 | $1.0B | 2,500d | 3.0 bps | `RESEARCH_CANDIDATE` | Exchange token utility economics; token-burn factor tests |
| **XRP/USDT** | XRP | Payments | #7 | $1.5B | 2,600d | 2.0 bps | `RESEARCH_CANDIDATE` | Cross-border payments order flow; regulatory shock response |
| **ADA/USDT** | ADA | Smart Contract L1 | #10 | $400M | 2,400d | 3.5 bps | `RESEARCH_CANDIDATE` | PoS alternative L1; tests low-velocity trend continuation |
| **DOGE/USDT** | DOGE | Meme Speculation | #8 | $1.2B | 2,200d | 3.0 bps | `RESEARCH_CANDIDATE` | Speculative sentiment proxy; volume shock & tail risk tests |
| **AVAX/USDT** | AVAX | High-Beta L1 | #11 | $500M | 1,500d | 4.0 bps | `RESEARCH_CANDIDATE` | Subnet L1 architecture; high correlation to SOL/ETH beta |
| **LINK/USDT** | LINK | Oracle Infrastructure | #14 | $350M | 2,200d | 3.5 bps | `RESEARCH_CANDIDATE` | Oracle infrastructure; DeFi lead-lag relationship analysis |
| **LTC/USDT** | LTC | PoW Payment | #19 | $300M | 3,100d | 3.0 bps | `RESEARCH_CANDIDATE` | Legacy PoW payment asset; halving cycle lead/lag dynamics |

---

## Survivorship Bias Controls

A major defect in retail quantitative backtesting is analyzing only today's surviving assets, ignoring tokens that suffered 99% collapses or exchange delistings (e.g., LUNA, FTT, SRM).

The QCP Asset Universe Registry enforces survivorship-bias controls:
1. **Point-in-Time Universe Reconstruction**: Backtests must only consider assets that met the eligibility hurdles at the historical simulation timestamp.
2. **Delisting Audit**: Delisted tokens are permanently retained in the registry with `delisting_date_utc` and historical price archives preserved.
3. **No Retroactive Substitution**: If an asset falls out of the top 20, its historical performance is preserved; it is not silently replaced with a current top-performer.

---

## Data Stack Certification Requirements

For each of the 10 assets, the data architecture enforces a strict certification pipeline:
```
SOURCE (Exchange REST/WS)
  │
  ▼
INGESTION (Raw CSV/JSON)
  │
  ▼
NORMALIZATION (Exchange-Neutral Schema)
  │
  ▼
VALIDATION (High >= Low, Positive Prices)
  │
  ▼
TIMESTAMP INTEGRITY (Strict Monotonicity)
  │
  ▼
GAP AUDIT (Missing Bar Detection)
  │
  ▼
LINEAGE HASH (SHA-256 Checksum)
  │
  ▼
RESEARCH ELIGIBILITY CERTIFICATION
```

### Certified vs. Missing Data Rule
> [!CAUTION]
> **Zero Data Fabrication**: If an order book, liquidation stream, or funding rate history is unavailable for a candidate asset, it **must remain explicitly missing**. The platform is forbidden from interpolating, forward-filling, or synthetically manufacturing market data.

---

## Cross-Asset Generalization Rules

Every strategy family must be evaluated independently across the eligible assets:
1. **No Free Generalization**: A strategy that is profitable on `BTC/USDT` is assumed to be **untested and unviable** on `DOGE/USDT` or `BNB/USDT` until proven by independent causal backtesting.
2. **Cross-Asset Matrix Evaluation**:
   $$\text{Matrix} = 10 \text{ Assets} \times 11 \text{ Strategy Families} \times 3 \text{ Timeframe Sets} \times 2 \text{ Regimes} \times 2 \text{ Friction Tiers}$$
3. **Asset-Specific Capital Refusal**: The platform is engineered to output:
   $$\text{“We researched 10 assets. Evidence supports trading 2. The other 8 remain rejected.”}$$
   Refusing to trade unviable assets is a core capability of the autonomous governor.
