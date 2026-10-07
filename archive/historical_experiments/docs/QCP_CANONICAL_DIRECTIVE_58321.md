# QCP CANONICAL DIRECTIVE 58321 (CONSOLIDATED)

**ID:** 58321
**STATUS:** ACTIVE — CUMULATIVE DIRECTIVE — SINGLE SOURCE OF TRUTH
**SCOPE:** Milestone 3 — Portfolio Intelligence & Relative-Value Alpha Factory
**CAPITAL STATE:** `REAL CAPITAL = LOCKED` / `LIVE EXECUTION = DISABLED`

---

## CONTENTS

| § | Section |
|---|---|
| §0 | Document control and consolidation record |
| §1 | Role and mission |
| §2 | Core objective |
| §3 | Governing principles |
| §4 | Approved research scope |
| §5 | Data certification and scope |
| §6 | Execution and controls |
| §7 | **Repository truth — measured discovery record** |
| §8 | Hard scope boundary |
| §9 | No feature creep rule |
| §10 | Portfolio Intelligence Engine |
| §11 | Relative-Value Alpha Factory |
| §12 | Testing requirements |
| §13 | Qualification integration and lifecycle |
| §14 | Adversarial research battery |
| §15 | Stop conditions (consolidated) |
| §16 | Safety and capital firewall |
| §17 | Required deliverables — merged manifest |
| §18 | **Execution manifest — single source of truth** |
| §19 | Global execution rules |
| §20 | Completion gate and end states |
| §21 | Mandatory response format |
| §22 | Final report requirements |
| §23 | Current research state (reference) |
| §24 | Final command |

---

## §0. DOCUMENT CONTROL AND CONSOLIDATION RECORD

This document supersedes and replaces four previously overlapping directive sets. It is the only
authoritative execution directive for Milestone 3.

### §0.1 Duplication removed

| Content block | Previously appeared | Consolidated to |
|---|---|---|
| Deliverable / file manifest | Deliverables manifest (×2) | **§17** |
| Execution manifest | Placeholder-command manifest, execution-order manifest, discovery-first manifest (×3) | **§18** |
| Stop conditions | Scope & stop conditions §9–14; repo stop condition; capital stop condition | **§15** |
| Completion states | Final report states; absolute end state; completion gate; checklist | **§20** |
| Capital firewall rules | Safety block; capital stop condition; global rule R5; blocked actions | **§16** |
| Forward-paper protection | Forward paper daemon block; forward paper protection; Phase 11 | **§16.4** |
| Scope boundary / out-of-scope | Scope boundary §1–2; feature creep rule §3; blocked actions | **§8, §9** |
| Research method / adversarial battery | Experimental method §8; adversarial battery Workstream 5 | **§14** |
| Qualification lifecycle | Qualification integration Workstream 4; promotion boundary §7 | **§13** |
| Discovery-first rule | Canonical interpretation §18; global discovery rule | **§18.0** |

### §0.2 Command substitution record

All placeholder commands (`<CANONICAL_DATA_QUALITY_RUNNER>`,
`<PORTFOLIO_ALLOCATOR_AUDIT_RUNNER>`, `<CANONICAL_STATISTICAL_QUALIFICATION_RUNNER>`) have been
**removed** and replaced with repository-verified discovery steps in §18. No command may be
executed unless it was discovered from repository truth.

### §0.3 Repository discoveries that changed this directive

Directive revision was driven by measured repository state, not assumption. Full detail in §7.
The three findings that materially altered the original directive:

1. **The RV engine already exists.** `research/discovery_lab/family_09_relative_value.py`
   implements cross-asset spread mean-reversion for SOL/ETH, SOL/BTC, ETH/BTC with causal
   rolling z-scores, DEV/VAL/OOS partitioning and friction modelling. The instruction to
   "create `relative_value_engine.py`" is downgraded to **EXTEND** (§11).
2. **The portfolio layer already exists.** `portfolio_engine/portfolio_intelligence.py` already
   enforces the 3.00% heat ceiling, drawdown throttling and correlation concentration. The
   instruction to "create the allocator" is downgraded to **EXTEND AS A GENERIC LAYER** (§10).
3. **The requested 2021–2026 window is not uniformly certified.** SOL history begins
   **2020-08-14/15**, not 2021; SOL 15m terminates at **2023-01-01**; all 5m/1m datasets cover
   **~35 days only**. A single common certified window for the three required pairs exists only
   on **1D and 4H: 2020-08-15 → 2026-09-01** (§5.3).

---

## §1. ROLE AND MISSION

Act as the central strategic decision authority for the **Quantitative Crypto Platform (QCP)**.

Build QCP as a professional quantitative crypto trading platform / autonomous trading operating
system capable of discovering multiple independent alpha families; qualifying them through
progressively stronger evidence; allocating capital dynamically according to expected net edge,
risk, capacity, correlation and portfolio state; executing with institutional-quality controls;
preserving capital through explicit fail-closed mechanisms; continuously measuring performance,
degradation, attribution and opportunity cost; retiring weak or degraded alpha and replacing it
with new research; and eventually supporting multiple crypto assets and multiple market
environments.

Long-term architecture:

**Market → Data → Market Intelligence → Alpha Discovery → Alpha Qualification → Expected Net Edge
→ Capital Allocation → Execution → Trade Management → Result → Telemetry → Attribution →
Degradation → Research → New Alpha → Re-allocation**

Live capital remains **0 and locked**. No implementation in this directive may bypass the capital
firewall.

---

## §2. CORE OBJECTIVE

The objective is not to maximize backtest returns. The objective is to build the infrastructure
and evidence chain required to determine:

1. what alpha exists;
2. whether it survives realistic costs and adverse execution;
3. whether it is genuinely distinct;
4. whether it remains healthy in forward paper;
5. how much capital it can responsibly absorb;
6. how it interacts with other alpha;
7. when it should be reduced, suspended or retired;
8. what research should replace degraded capacity.

The six sets represent **six timeframe / market-resolution environments**, not six strategies.
Multiple alpha families should ultimately operate within those environments.

Approved long-term alpha universe: directional; relative value / statistical arbitrage;
cross-exchange arbitrage; funding / basis arbitrage; triangular arbitrage; market making;
microstructure; ML / black-box; HFT where the economics and infrastructure justify it.

Research autonomy is permitted, but optimization must remain bounded by causal attribution,
reproducibility, evidence quality, data quality and economic plausibility.

### §2.1 Milestone 3 immediate objective

Build and validate two foundational capabilities, and only these two:

1. **Portfolio Intelligence & Dynamic Capital Allocation** (generic infrastructure).
2. **Relative-Value / Statistical-Arbitrage Alpha Factory** (research infrastructure).

The goal is NOT to manufacture profitable-looking backtests. The goal is to create reusable
research and portfolio infrastructure capable of discovering, rejecting, ranking, sizing and
monitoring alpha candidates using realistic economics and independent evidence.

---

## §3. GOVERNING PRINCIPLES

1. **Evidence > hours.**
2. Repository truth is authoritative for code, tests, commits and generated artifacts.
3. Permanent pillar documents are authoritative for constitution and roadmap.
4. Daily logs establish chronology.
5. Development evidence must never be promoted to validation, OOS or capital qualification without the required evidence.
6. Dev ≠ Validation ≠ OOS.
7. Win rate ≠ expectancy.
8. Positive Development Net R ≠ validated strategy.
9. Never invent metrics.
10. Never accept AI-generated claims without inspectable evidence.
11. Closed trade = terminal state.
12. READY must reset whenever its invalidating conditions occur.
13. Directional geometry is mandatory.
14. Data starvation is not strategy failure.
15. Computational failure is not a zero-trade result.
16. Preserve causal attribution.
17. Every material research result must be reproducible.
18. Capital must remain isolated from research until explicitly qualified.
19. Portfolio allocation must be generic infrastructure, not hard-coded to one alpha or asset.
20. Arbitrary thresholds must eventually be empirically justified.
21. The system must fail closed on uncertainty, stale data, degraded execution, broken lineage or capital-control failure.
22. Do not optimize solely for historical return; optimize for durable net edge and capital efficiency.
23. **Evidence outranks backtest returns. Reproducibility outranks narrative. Net edge outranks gross return. Risk-adjusted performance outranks raw P&L. Capital preservation outranks deployment.**
24. **A failed strategy is a successful research outcome if QCP correctly proves that the strategy should not receive capital.**

---

## §4. APPROVED RESEARCH SCOPE

### §4.1 Portfolio Intelligence and Dynamic Allocation

Implement generic portfolio infrastructure capable of evaluating candidate alphas using: expected
net edge; confidence; realized expectancy; drawdown; volatility; tail risk; correlation;
concentration; liquidity; execution quality; capacity; turnover; friction; model health;
degradation; capital constraints.

The allocator must not contain permanent special treatment for SOL Set2 or any other single
candidate.

### §4.2 Relative Value Alpha Factory

Build a research-grade relative-value engine supporting, at minimum:

- BTC/ETH
- SOL/ETH
- SOL/BTC

USDT is the common quote environment, **not** a substitute for the cross-asset pair relationship.
`BTC/USDT vs ETH/USDT vs SOL/USDT` is explicitly **NOT** a valid cross-asset cointegration
formulation and must not be used as the pair universe.

Research must distinguish: spread construction; hedge-ratio estimation; stationarity /
mean-reversion properties; entry; exit; stop / invalidation; costs; slippage; latency; funding;
borrow; position sizing; regime behaviour.

### §4.3 Existing Directional Alpha (preservation only)

Candidate #001 remains a Development candidate: **Supertrend 6/5 + Stochastic 25/5/3**. Its
mathematically repaired, hyper-strict / opportunity-starved behaviour must not be artificially
loosened merely to increase trade count.

### §4.4 Market-Neutral Basis / Funding

Maintain the basis/funding research path: **Long spot + short perpetual**. Current research
assumptions: 32 bps round-trip friction; 5 bps spot taker fee; 5 bps perpetual taker fee; 3 bps
spot slippage; 3 bps perpetual slippage; 6% APR borrow financing; 8-hour funding accrual; basis
convergence. An 8% APY hurdle may be used where explicitly defined by the research specification,
but thresholds must ultimately be justified by evidence.
---

## §5. DATA CERTIFICATION AND SCOPE

### §5.1 Certification rule

Data must be certified before it becomes qualification evidence. Required controls: OHLC validity;
timestamp ordering; duplicate detection; missing-bar detection; zero-volume inspection; outlier /
spike detection; dataset hashing; lineage tracking; source identification; coverage period;
timeframe; asset; completeness; warning / rejection state.

Required data verdicts (`market_data/data_quality_engine.py`):

- `CERTIFIED_CLEAN`
- `USABLE_WITH_WARNINGS`
- `REJECTED_CORRUPT`

**Important distinction:** the existing `scratch/dataset_manifests.json` carries a
`certification_status` of `RESEARCH_ELIGIBLE` and a `research_eligibility` flag. That is a
*manifest eligibility* flag, NOT a `DataQualityEngine` verdict. Milestone 3 must reconcile these
two concepts: a dataset may be manifest-eligible while still carrying missing bars that the
quality engine would rate `USABLE_WITH_WARNINGS`. Both must be recorded. Never silently treat
manifest eligibility as equivalent to `CERTIFIED_CLEAN`.

### §5.2 Measured dataset availability matrix

Measured from `scratch/dataset_manifests.json` (24 datasets, all manifest-eligible, SHA-256
hashed, generated 2026-09-15T13:41:22Z).

| Symbol | TF | Rows | Missing intervals | Start | End |
|---|---|---|---|---|---|
| BTC/USDT | 1m | 50,000 | 0 | 2026-07-30 | 2026-09-03 |
| BTC/USDT | 5m | 50,000 | 0 | 2026-03-14 | 2026-09-03 |
| BTC/USDT | 15m | 316,482 | 30 | 2017-08-17 | 2026-09-01 |
| BTC/USDT | 1h | 79,134 | 14 | 2017-08-17 | 2026-09-01 |
| BTC/USDT | 4h | 19,800 | 1 | 2017-08-17 | 2026-09-01 |
| BTC/USDT | 1d | 3,303 | 0 | 2017-08-17 | 2026-09-01 |
| BTC/USDT | 1w | 473 | 0 | 2017-08-14 | 2026-08-31 |
| BTC/USDT | 1M | 110 | 0 | 2017-08-01 | 2026-09-01 |
| ETH/USDT | 1m | 50,000 | 0 | 2026-07-30 | 2026-09-03 |
| ETH/USDT | 5m | 50,000 | 0 | 2026-03-14 | 2026-09-03 |
| ETH/USDT | 15m | 316,482 | 30 | 2017-08-17 | 2026-09-01 |
| ETH/USDT | 1h | 79,134 | 14 | 2017-08-17 | 2026-09-01 |
| ETH/USDT | 4h | 19,800 | 1 | 2017-08-17 | 2026-09-01 |
| ETH/USDT | 1d | 3,303 | 0 | 2017-08-17 | 2026-09-01 |
| ETH/USDT | 1w | 473 | 0 | 2017-08-14 | 2026-08-31 |
| ETH/USDT | 1M | 110 | 0 | 2017-08-01 | 2026-09-01 |
| SOL/USDT | 1m | 50,000 | 0 | 2026-07-30 | 2026-09-03 |
| SOL/USDT | 5m | 50,000 | 0 | 2026-03-14 | 2026-09-03 |
| SOL/USDT | 15m | 71,000 | 8 | 2020-12-21 | **2023-01-01** |
| SOL/USDT | 1h | 52,997 | 3 | 2020-08-14 | 2026-09-01 |
| SOL/USDT | 4h | 13,254 | 0 | 2020-08-14 | 2026-09-01 |
| SOL/USDT | 1d | 2,209 | 0 | 2020-08-15 | 2026-09-01 |
| SOL/USDT | 1w | 316 | 0 | 2020-08-17 | 2026-08-31 |
| SOL/USDT | 1M | 73 | 0 | 2020-09-01 | 2026-09-01 |

### §5.3 What this means for Relative-Value research scope

- **BTC/ETH** pair: certified on 15m, 1h, 4h, 1d, 1w, 1M from **2017-08-17**.
- **SOL/ETH** and **SOL/BTC** pairs: constrained by SOL history — certified from **2020-08-14/15**
on 1h, 4h, 1d (and 15m only from 2020-12-21 to 2023-01-01).
- **Common certified window for all three required pairs:** **1D and 4H only, 2020-08-15 → 2026-09-01.**
- **5m and 1m are NOT usable** for any pair research: all three assets cover a ~35-day window
(2026-03-14 / 2026-07-30 → 2026-09-03), which is insufficient for cointegration estimation or
for z-score lookback windows. They may be used only for execution-microstructure calibration.
- **SOL 15m is truncated at 2023-01-01** and therefore cannot support any claim of post-2023 15m
coverage. This is a known, documented limitation.

### §5.4 Mandatory period reporting

No research result may claim 2021–2026 coverage unless certified data actually covers that period.
Every result must report, explicitly and separately:

```
REQUESTED PERIOD
CERTIFIED PERIOD
UNAVAILABLE PERIOD
REASON
```

For the three required RV pairs on 1D/4H the honest reporting is:
- Requested: 2021-01-01 → 2026-09-01
- Certified: 2020-08-15 → 2026-09-01 (BTC/ETH actually extends to 2017-08-17)
- Unavailable: none for 1D/4H within the requested window; unavailable for 15m post-2023-01-01 and
  for all 5m/1m pair research
- Reason: SOL series inception 2020-08-14; SOL 15m cache truncation; 50k-row REST caps on 5m/1m

### §5.5 Prohibitions

Do not fabricate a period. Do not fill missing historical data with synthetic candles. Do not
silently substitute another dataset. Known historical cache limitations (24 cache files; Sets 1–4
strongest coverage; 4H/1H/15m gaps; Set5/Set6 lacking 2021–2023 depth) remain explicit. Set 6
suspension caused by insufficient local historical depth is a **data-coverage limitation**, not a
strategy failure.

Sampling, labels and execution semantics must remain causal. No HTF lookahead. No favorable-first
same-bar collision handling. Execution must use the canonical adverse-first collision policy
`CollisionPolicy.ADVERSE_FIRST`. Entry-on-close semantics, slippage, fees and standardized R
accounting must remain consistent across research and replay paths.
---

## §6. EXECUTION AND CONTROLS

### §6.1 Unified execution semantics

Execution semantics must be unified across: research simulator; strategy generator; replayers;
paper execution; forward-paper daemon; eventual production execution.

### §6.2 Forward-paper daemon requirements

`production/forward_paper_daemon.py` must support: closed-candle confirmation; duplicate-bar
protection; missing-bar detection; stale-data inhibit; state recovery; position recovery;
structured heartbeat; clean shutdown.

### §6.3 The 7-Dimensional Portfolio Risk Firewall has veto authority

Implemented in `risk_engine/portfolio_risk_firewall.py` as `PortfolioRiskFirewall.evaluate_order()`
returning a `FirewallDecision` with `FirewallAction.APPROVE | APPROVE_REDUCED_RISK | REJECT` and a
`risk_multiplier`. Measured thresholds (`FirewallThresholds`):

**Market** — 3.0× gross leverage ceiling; 50% single-asset concentration ceiling; 3.0% total heat
ceiling; 2.5 max directional beta.

**Liquidity** — reject if spread > 0.15%; order > 5% of top-of-book depth; estimated impact > 15 bps.

**Correlation** — reject if correlated same-direction heat > 1.8%; clustering threshold 0.80.

**Execution** — reject if feed stale > 30 s; latency > 2000 ms; trailing slippage > 10 bps.

**Exchange** — veto on API error rate > 2%; abnormal funding > 25 bps (0.25% per 8 h).

**Model** — reject if drift score > 0.40; rolling expectancy < −0.15 R.

**Tail** — circuit-break at 6% account drawdown; 1-hour flash crash < −8%; VaR95 > 2.5%.

These thresholds are implementation controls, not proof of optimality. They must not be presented
as empirically optimal unless later research establishes that.

### §6.4 Existing portfolio control layer (discovered)

`portfolio_engine/portfolio_intelligence.py` implements `PortfolioIntelligenceEngine` with:
`MAX_PORTFOLIO_HEAT_PCT = 3.00`; `BASE_TARGET_RISK_PCT = 0.60`; drawdown risk multipliers 1.00 / 0.50
/ 0.25 / 0.00 at <5% / 5–15% / 15–25% / >25%; a 50% sizing discount when already holding 2
correlated same-direction positions; hard rejection at 3 correlated same-direction positions; and
heat-budget scaling with a 0.20% minimum viable risk.

Supporting modules: `portfolio_engine/allocator/volatility_target_sizer.py`
(`VolatilityTargetSizer`), `portfolio_engine/allocator/drawdown_dampener.py` (`DrawdownDampener`),
`portfolio_engine/contracts/portfolio_state.py` (`PortfolioRiskConfig`, `PortfolioState`,
`AssetExposure`, `AllocatedTradePlan`), `portfolio_engine/hedging_engine.py`,
`portfolio_engine/portfolio_coordinator.py`, and `capital_intelligence/alpha_capital_intelligence.py`.

**Known limitation to be corrected, not ignored:** `PortfolioIntelligenceEngine.PAIRWISE_CORRELATIONS`
is a hard-coded dict (BTC/ETH 0.78, BTC/SOL 0.68, ETH/SOL 0.74). Milestone 3's allocator must
derive covariance from data/config rather than hard-coded constants, without deleting the existing
engine or its tested behaviour.
---

## §7. REPOSITORY TRUTH — MEASURED DISCOVERY RECORD

Everything in this section was measured, not assumed. It is the authoritative preflight baseline
for Milestone 3 and must be re-measured at execution time before any file is created.

### §7.1 Environment (measured)

| Item | Measured value |
|---|---|
| Repository root | `/home/mrcn2/crypto-platform` |
| Branch | `main` |
| Commit | `0b76ca8f8e1e4a2b70ed01450d189c0965e0c90f` |
| Working tree | **DIRTY** — see §7.2 |
| Python | 3.12.3 (`requires-python >= 3.12`) |
| pytest | 9.1.1 (pinned; `minversion = "9.0"`) |
| numpy | 2.2.6 (only runtime dependency) |
| declared packages | `numpy==2.2.6`; dev: `pytest==9.1.1`, `anyio==4.13.0` |

### §7.2 Measured preflight test baseline

Canonical invocation discovered from `pyproject.toml [tool.pytest.ini_options]`
(`testpaths = ["tests"]`, `python_files = ["test_*.py"]`):

```bash
python3 -m pytest -q
```

**Observed result: `487 passed in 124.93s (0:02:04)`.** Zero failures, zero errors, zero skips.

This confirms the previously reported 487/487 figure. The baseline is GREEN. Test file count is 98.

### §7.3 Measured working-tree state (BLOCKING for any "clean commit" gate)

The repository is **not clean**. `git status --short` shows 9 modified tracked files and
approximately 30 untracked files, comprising the entirety of the Milestone 2 deliverable set that
was never committed:

**Modified:** `market_data/binance_fetcher.py`; `production/paper_execution_harness.py`;
`research/results/DAILY_DECISION_RECORD.json`; `research/results/HTF_TREND_CONTINUATION_V1.json`;
`research/results/PAPER_TRADING_SIMULATION_AUDIT.json`;
`research/results/telemetry/forward_execution_telemetry.jsonl`; `scratch/dataset_manifests.json`;
`tests/unit/production/test_paper_engine_and_telemetry.py`

**Untracked (Milestone 2 infrastructure — must be preserved, not discarded):**
`market_data/data_quality_engine.py`; `production/forward_paper_daemon.py`;
`production/paper_daemon_state.json`; `production/qualification/{model_reality_engine,
performance_truth_engine, statistical_qualification_gate}.py`; `production/run_forward_burn_in.py`;
`research/arbitrage/`; `research/experiments/run_executable_funding_audit.py`;
`research/experiments/run_statistical_qualification_audit.py`;
`research/results/{COMPARATIVE_FORWARD_PAPER_OBSERVATION, EXECUTABLE_FUNDING_ARBITRAGE_AUDIT,
FORWARD_PAPER_DAEMON_AUDIT, PERFORMANCE_TRUTH_RECONCILIATION, STATISTICAL_QUALIFICATION_AUDIT}.json`;
`research/results/PAPER_AUDIT_{BTCUSDT,ETHUSDT,SOLUSDT}.json`;
`research/results/paper_state_{btcusdt,ethusdt,sol,solusdt}.json`;
`research/run_forensic_reconciliation_and_comparative_paper.py`; `risk_engine/portfolio_risk_firewall.py`;
`tests/integration/test_forward_daemon_oat.py`;
`tests/unit/market_data/test_data_quality_engine.py`;
`tests/unit/production/test_{forward_paper_daemon, model_reality_engine, performance_truth_engine,
statistical_qualification_gate}.py`; `tests/unit/research/test_{basis_funding_engine,
executable_funding_research}.py`; `tests/unit/risk_engine/test_portfolio_risk_firewall_7d.py`

**Consequence for this directive:** the previously stated rule *"Commit only if repository state is
clean"* must be reinterpreted. The correct rule is: **preserve and commit the uncommitted Milestone
2 baseline first, or explicitly carry it forward**, then commit Milestone 3 separately. Deleting,
reverting or stashing-away the untracked Milestone 2 files would destroy uncommitted evidence and
is prohibited by §16.5.

### §7.4 Measured test layout and conventions

```
tests/
├── unit/
│   ├── execution_gateway/  market_data/  market_intelligence/  platform_core/
│   ├── portfolio_engine/   production/   research/  risk_engine/
│   ├── strategy/           strategy_engine/
│   └── test_*.py  (flat: alpha_capital_intelligence, canonical_registry, capital_feasibility,
│                   continuous_evolution, coordinator, decision_record, family_09_relative_value,
│                   keyzone_engine, liquidity_engine, market_memory, market_state, phase_engine,
│                   portfolio_intelligence, raw_swing_engine, regime_engine, structure_builder_engine,
│                   structure_engine, trade_management_lifecycle, trend_engine, validation_engine)
└── integration/            (flat: test_24_7_live_trading_loop, test_canonical_conformance,
                             test_canonical_statemachine, test_forward_daemon_oat,
                             test_product_01_pipeline, test_product_03_pipeline,
                             test_product_04_matrix, test_replayer_reference_equivalence,
                             test_synthetic_conformance, test_universal_broker_loop)
```

**Layout note:** `tests/integration/` is currently flat with no subdirectories except
`strategy_engine/`. The manifest's `tests/integration/test_portfolio_allocation.py` and
`tests/integration/test_relative_value_research.py` conform to the existing flat convention.
`tests/unit/portfolio_engine/` and `tests/unit/research/` already exist, so the manifest's unit-test
paths conform as well. **No parallel test architecture is required.**

### §7.5 Measured artifact and documentation conventions

- Research artifacts are written to `research/results/` (**164 existing entries**), as UPPERCASE
  `*_AUDIT.json` / `*.json` files (e.g. `FORWARD_PAPER_DAEMON_AUDIT.json`,
  `STATISTICAL_QUALIFICATION_AUDIT.json`, `COMPARATIVE_FORWARD_PAPER_OBSERVATION.json`).
- Documentation lives in `docs/` as UPPERCASE `*_AUDIT.md` / `*_REPORT.md` files, alongside
  lowercase pillar docs (`architecture.md`, `strategy.md`, `risk-model.md`,
  `research-methodology.md`, `research_governance.md`, `research_index.md`, `research_status.md`).
- Both manifest conventions (`research/results/*_AUDIT.json` and
  `research/results/*_WALKTHROUGH.md`) align with existing practice. **No deviation is required.**
- `research/discovery_lab/` already contains 20+ modules; `research/experiments/` already contains
  runners. New runners must match those conventions.

### §7.6 Measured existing-capability inventory (reuse map)

This map is mandatory input to §10 and §11. **Capability already present must be EXTENDED, not
duplicated.**

| Capability | Existing implementation | Measured status | Milestone 3 action |
|---|---|---|---|
| Portfolio heat ceiling / drawdown throttle / correlation concentration | `portfolio_engine/portfolio_intelligence.py` (`PortfolioIntelligenceEngine`) | Present, tested (`tests/unit/test_portfolio_intelligence.py`) | **EXTEND** — add generic alpha-slot layer; do not fork |
| Volatility-targeted sizing | `portfolio_engine/allocator/volatility_target_sizer.py` | Present | **REUSE** |
| Drawdown dampening | `portfolio_engine/allocator/drawdown_dampener.py` | Present | **REUSE** |
| Portfolio state / risk config contracts | `portfolio_engine/contracts/portfolio_state.py` | Present | **EXTEND** |
| 7-D portfolio risk firewall (veto authority) | `risk_engine/portfolio_risk_firewall.py` | Present (untracked), tested (`test_portfolio_risk_firewall_7d.py`) | **REUSE — never bypass** |
| Corporate/alpha capital feasibility | `capital_intelligence/alpha_capital_intelligence.py`, `generate_capital_feasibility_matrix.py` | Present, tested | **REUSE** |
| Cross-asset RV spread engine | `research/discovery_lab/family_09_relative_value.py` (`RelativeValueAlphaEngine`) | Present, tested (`tests/unit/test_family_09_relative_value.py`) | **EXTEND** — see §11.2 gaps |
| Adversarial battery | `research/discovery_lab/adversarial_researcher.py` (`AdversarialResearcher.run_adversarial_battery` → `ADVERSARIAL_STRESS_BATTERY.json`) | Present | **REUSE** |
| Friction stress / walk-forward / reproducibility / parameter-landscape / portfolio-correlation audits | `research/discovery_lab/audit_{friction_stress, walk_forward, reproducibility, parameter_landscape, portfolio_correlation, execution_forensics}.py` | Present | **REUSE** |
| OOS partitioning | `research/discovery_lab/oos_manager.py`, `run_validation_and_oos.py` | Present | **REUSE** |
| Data quality & lineage | `market_data/data_quality_engine.py` (`DataQualityEngine`, `DataQualityReport`, `DataCertificationVerdict`) | Present (untracked), tested | **REUSE — extend to emit lineage artifacts** |
| Dataset manifests + hashes | `scratch/dataset_manifests.json` (24 datasets, SHA-256) | Present | **REUSE — relocate/copy into `research/discovery_lab/data_manifest.json`** |
| Statistical qualification gate | `production/qualification/statistical_qualification_gate.py` (`StatisticalQualificationGatekeeper`, `StrategyLifecycleTier`, `QualificationHurdles`) | Present (untracked), tested | **REUSE — feed RV candidates in** |
| Forward qualification | `production/qualification/forward_qualification_engine.py` (`ForwardQualificationEngine`) | Present | **REUSE** |
| Performance truth reconciliation | `production/qualification/performance_truth_engine.py` | Present (untracked), tested | **REUSE** |
| Model-vs-reality delta | `production/qualification/model_reality_engine.py` | Present (untracked), tested | **REUSE** |
| Forward paper daemon | `production/forward_paper_daemon.py`, `run_forward_burn_in.py` | Present (untracked), tested | **PRESERVE — do not reset** |
| Strategy lifecycle registry | `research/discovery_lab/strategy_registry.py` (`StrategyStatus`: RESEARCH, FAILED, FALSIFIED, PROMISING, VALIDATION, OOS, ROBUST, FRAGILE, PAPER, QUALIFIED, LIVE, DEGRADED, RETIRED) | Present | **EXTEND** — add RV candidate records |
| Funding / basis research | `research/arbitrage/basis_funding_engine.py`, `executable_funding_research.py` | Present (untracked), tested | **PRESERVE** |

### §7.7 Measured qualification gate thresholds (existing)

`ProductionQualificationHurdles` as implemented: `min_forward_trades = 100`; `min_forward_days =
60.0`; `bootstrap_iterations = 2000`; `confidence_level_pct = 95.0`;
`min_expectancy_ci_lower_bound_r = 0.15`; `max_forward_drawdown_pct = 5.91` (1.25× historical 4.73%);
`max_friction_error_bps = 3.0`; `max_consecutive_losses = 8`; `min_win_rate_pct = 55.0`.
Existing lifecycle tiers: `HISTORICAL_ROBUST`, `FORWARD_HEALTHY`, `PRODUCTION_QUALIFIED`,
`DEGRADED_OR_DISQUALIFIED`.

**Reconciliation note:** the working directive asked for the eight-state chain `DISCOVERED →
RESEARCHED → HISTORICALLY_TESTED → ADVERSARIAL_TESTED → QUALIFIED_ROBUST → FORWARD_PAPER →
FORWARD_HEALTHY → PRODUCTION_QUALIFIED`. The repo has **two different existing state machines**
(4-tier qualification tiers, 13-state strategy registry). Milestone 3 must **map** the eight-state
chain onto these existing machines via an explicit, documented mapping table — **not** create a
third state machine.

---

## §8. HARD SCOPE BOUNDARY

### §8.1 In scope

**Portfolio Intelligence** — generic alpha-slot representation; expected-net-edge ranking;
uncertainty/confidence adjustment; volatility-aware sizing; covariance/correlation awareness;
concentration control; portfolio heat control; drawdown throttling; degradation throttling;
capacity constraints; lifecycle-aware eligibility; fail-closed allocation; integration with the
existing risk firewall; deterministic allocation outputs; allocation audit artifacts.

**Relative-Value Alpha Factory** — BTC/ETH, SOL/ETH, SOL/BTC; baseline Engle-Granger; Johansen where
statistically appropriate; hedge-ratio estimation; spread construction; z-score; half-life;
entry/exit logic; realistic friction; adverse-first execution; historical backtest; out-of-sample
evaluation where data permits; adversarial stress testing; data lineage; reproducible research
artifacts; candidate classification.

**Verification** — unit tests; integration tests; data-quality checks; research execution;
adversarial testing; full regression suite; artifact inspection; final repository health check.

### §8.2 Explicitly out of scope

Unless required solely to make an in-scope component function correctly, do NOT implement,
research, optimize or deploy:

**Trading expansion** — HFT strategy development; market-making engine; ML alpha discovery;
deep-learning models; reinforcement learning; new momentum families; new directional strategy
families; Set 5/6 expansion; options strategies; derivatives portfolio expansion; cross-exchange
arbitrage; triangular arbitrage; latency-arbitrage systems; liquidation hunting; execution
optimization for real capital.

**Production** — live trading; exchange API credentials; real orders; withdrawals; real-money
deployment; production capital allocation; automated capital unlocking; changing the Capital
Firewall; bypassing the Statistical Qualification Gate; reducing qualification requirements.

**Unnecessary infrastructure** — do NOT create a second risk engine; second performance engine;
second data-quality engine; second execution engine; second candidate registry; second telemetry
framework; duplicate portfolio-risk logic; duplicate statistical-testing infrastructure.

Reuse and extend existing canonical components.

---

## §9. NO FEATURE CREEP RULE

If a potentially valuable feature outside this scope is discovered: **DO NOT implement it.**
Record it under `FUTURE_RESEARCH_BACKLOG` with: feature name; reason it may matter; dependency;
estimated value; reason it is deferred. Then continue the current milestone. A potentially
interesting feature is NOT permission to expand scope.

Additional parameter-scope rules: use a small, transparent baseline parameter set. Do NOT conduct a
massive parameter sweep. Do NOT perform brute-force optimization. Do NOT select parameters because
they maximize historical returns. Any parameter used in the baseline must be documented. If
optimization is required later, record it as `FUTURE_RESEARCH_BACKLOG`.
---

## §10. PORTFOLIO INTELLIGENCE ENGINE

### §10.1 Deliverable

Create `portfolio_engine/capital_allocator.py` as a **GENERIC portfolio infrastructure component**.
It must sit **above** the existing `PortfolioIntelligenceEngine` and **below** the
7-D `PortfolioRiskFirewall`, and it must not duplicate either.

It must NOT be hard-coded to SOL Set 2, or to any single asset, strategy or pair.

### §10.2 Required inputs per alpha slot

strategy identifier; asset; timeframe/environment; expected gross edge; expected net edge;
confidence interval; historical expectancy; forward expectancy; volatility; drawdown; capacity;
execution quality; friction estimate; model-reality delta; correlation/covariance exposure;
lifecycle state; qualification state; degradation state.

### §10.3 Allocation logic

**A. Expected Net Edge.** Use net rather than gross expectancy. Account for fees, spread,
slippage, financing, expected market impact and execution uncertainty.

**B. Statistical Confidence.** Penalize uncertain candidates. A high historical expectancy with a
weak confidence interval must not automatically receive high capital.

**C. Volatility.** Normalize risk contribution rather than allocating equal notional.

**D. Covariance.** Construct portfolio covariance/correlation across active alpha slots. Do not
treat BTC, ETH and SOL strategies as independent merely because they have different symbols.
Covariance must be **computed from data or supplied configuration**, not read from the existing
hard-coded `PAIRWISE_CORRELATIONS` dict. The hard-coded dict may remain as a documented fallback
only, and any fallback use must be flagged in the audit artifact.

**E. Concentration.** Respect the existing portfolio risk firewall. Hard cap
`portfolio heat <= 3.00%`. Do not bypass the existing veto layer.

**F. Drawdown Throttling.** Implement deterministic capital throttling when portfolio drawdown
rises. The allocator may **reduce** exposure. It must **NEVER increase risk merely because the
strategy recently lost money** (no martingale, no loss-chasing, no recovery sizing).

**G. Strategy Degradation.** Allocation must respond to expectancy decay, friction
deterioration, execution deterioration, drawdown deterioration, regime deterioration and capacity
deterioration. A degraded alpha must automatically lose allocation.

**H. Lifecycle Awareness.** At minimum distinguish `RESEARCH`, `HISTORICAL_ROBUST`,
`FORWARD_HEALTHY`, `PRODUCTION_QUALIFIED` (mapped onto the existing state machines per §7.7).
Only appropriately qualified states may be eligible for production allocation. **Research candidates
must never receive production capital.**

### §10.4 Allocator boundary (non-negotiable)

The allocator must calculate **hypothetical allocation decisions** only. It must NOT place orders;
modify real account balances; unlock capital; or modify existing global capital limits.

The existing hard safety constraint remains `MAX PORTFOLIO HEAT <= 3.00%`. The allocator is
**subordinate** to the existing risk firewall. If allocator output conflicts with the firewall:

```
RISK FIREWALL WINS
```

Always.

### §10.5 Fail-closed requirement

The allocator must fail **CLOSED**. Invalid or incomplete information must never result in a larger
allocation. Missing data, NaN/inf values, malformed covariance matrices, absent lifecycle state,
absent capacity estimate and absent friction estimate must all produce **zero or reduced**
allocation with an explicit recorded reason — never a default full allocation.

---

## §11. RELATIVE-VALUE ALPHA FACTORY

### §11.1 Deliverables and research-only status

`research/discovery_lab/relative_value_engine.py` and
`research/discovery_lab/relative_value_config.py` are **RESEARCH ONLY**. They must not connect to
live capital. They must integrate with the existing discovery/qualification architecture rather than
becoming isolated experimental scripts.

### §11.2 EXTEND, do not duplicate — measured capability gap in the existing engine

`research/discovery_lab/family_09_relative_value.py` already provides: pair definition for SOL/ETH,
SOL/BTC, ETH/BTC; timestamp alignment (`align_pair_candles`); causal rolling mean/std; z-score
entry/exit; catastrophic-divergence stop; max-holding-bar exit; DEV/VAL/OOS partitioning; and a
friction parameter (default `0.003` round trip across both legs).

**Measured gaps that Milestone 3 must close:**

1. **No hedge ratio.** The spread is the raw log ratio `log(p_a / p_b)` — i.e. an **implicit unit
   hedge ratio**. There is no regression-based or rolling hedge-ratio estimation.
2. **No Engle-Granger test.** No cointegration test, no residual stationarity test, no p-value.
3. **No Johansen test.** No rank, eigenvector, trace or max-eigenvalue statistics.
4. **No half-life estimation.** No Ornstein-Uhlenbeck / AR(1) mean-reversion half-life.
5. **No data-quality gating.** The engine loads candles directly via
   `strategy_candidate_v2.data_audit.load_candles` with **no** `DataQualityEngine` verdict check.
6. **No lineage recording.** No dataset hash, no parameter set hash, no code version recorded.
7. **No BTC/ETH pair.** The engine uses ETH/BTC; the directive requires **BTC/ETH** (same economic
   relationship, opposite leg convention — must be reconciled explicitly, not silently).
8. **Friction is a single scalar.** No separate entry fee, exit fee, spread crossing, slippage,
   financing, holding cost or market impact decomposition.
9. **No lifecycle/qualification integration.** Results are written to
   `FAMILY_09_RELATIVE_VALUE_RESEARCH.json` and never enter the qualification chain.
10. **No capacity estimate, no beta/exposure decomposition, no regime tagging.**

Milestone 3 must deliver these gaps as an **extension** — the canonical implementation path may
satisfy the manifest through the existing module plus a documented compatibility layer, and any
deviation must be recorded in the walkthrough.

### §11.3 Relative-value universe

```
BTC/ETH
SOL/ETH
SOL/BTC
```

on timeframes:

```
1D
4H
```

Do NOT automatically expand to additional pairs or timeframes. USDT may be the common pricing
currency. Do not treat `BTC/USDT`, `ETH/USDT` and `SOL/USDT` as cross-asset pairs.

### §11.4 Statistical methods

**1. Engle-Granger.** For candidate pair relationships calculate: hedge ratio; residual/spread;
stationarity test; p-value; stability diagnostics.

**2. Johansen.** Where the data structure supports it, calculate: cointegration rank; eigenvectors;
trace statistics; maximum-eigenvalue statistics. **Do not use Johansen merely because it is
available. Report whether its assumptions are appropriate.**

**3. Spread construction.** Support static hedge ratio; rolling hedge ratio; appropriately
controlled dynamic hedge ratio. Do not introduce excessive parameter optimization.

**4. Mean reversion.** Calculate: spread z-score; rolling mean; rolling standard deviation;
half-life; entry threshold; exit threshold; stop/invalidation condition. Parameters must be explicit
and auditable.

### §11.5 Cointegration discipline

The engine must **discover** whether each relationship is stable rather than assuming these pairs
are cointegrated. A non-cointegrated pair is a valid research finding. If a pair fails
the stationarity requirement, it must be classified accordingly (e.g. `FALSIFIED` or
`INSUFFICIENT_DATA`) rather than traded anyway with loosened thresholds.

### §11.6 Anti-overfitting rules

The research engine must prevent: future leakage; lookahead bias; overlapping-information leakage;
parameter selection on the test period; survivorship assumptions; favorable-first same-bar
execution; unrealistic fills; friction omission.

Use causal rolling calculations. Separate `TRAIN / RESEARCH` from `OUT-OF-SAMPLE` where the
available data permits it. **Do not optimize until the baseline has been evaluated.**

### §11.7 Execution economics

Every RV backtest must account for executable economics, modelled **separately**: entry fees; exit
fees; spread crossing; slippage; financing where applicable; position holding cost; turnover;
market impact where capacity requires it.

Do NOT hard-code a universal friction assumption and call it reality. The friction model must be
explicit. Run at least:

```
BASE        realistic estimated friction
STRESS-1    2x friction
STRESS-2    additional entry/exit latency
STRESS-3    adverse execution / collision ordering
STRESS-4    outlier / windfall removal
```

### §11.8 Required backtest outputs

Evaluate and report: trade count; net R; expectancy; profit factor; Sharpe; Sortino; maximum
drawdown; recovery; win rate; turnover; average holding period; friction drag; capacity estimate;
exposure; correlation to existing directional alpha; regime distribution. Plus: data period actually
available; observations; cointegration evidence; half-life; and final classification.

### §11.9 CRITICAL — relative value does NOT automatically mean market neutral

Verify actual portfolio beta/exposure. Measure: gross exposure; net exposure; BTC beta; ETH beta;
SOL beta; market correlation; residual exposure. **A strategy may only be called market-neutral if
the evidence supports that claim.**

### §11.10 Baseline integrity checks (must pass before results are accepted)

```
NO LOOKAHEAD
CAUSAL FEATURES
ADVERSE-FIRST EXECUTION
REALISTIC FRICTION
VALID R ACCOUNTING
CERTIFIED DATA
```

If any check fails: `BASELINE_RESEARCH = INVALID`. Repair before proceeding.

---

## §12. TESTING REQUIREMENTS

### §12.1 Portfolio allocator tests

Required at `tests/unit/portfolio_engine/test_capital_allocator.py` plus
`tests/integration/test_portfolio_allocation.py`. Minimum coverage:

1. Single-alpha allocation
2. Multiple independent alphas
3. Highly correlated alphas
4. Opposing exposures
5. High-volatility candidate
6. Low-confidence candidate
7. High-friction candidate
8. Drawdown throttling
9. Portfolio heat ceiling
10. Concentration ceiling
11. Degraded-alpha throttling
12. Research candidate rejection
13. Forward-only candidate rejection
14. Capital-qualified candidate allocation
15. Missing-data fail-closed behaviour
16. NaN/invalid covariance fail-closed behaviour
17. Negative expected net edge rejection
18. Capacity constraint
19. Extreme correlation stress
20. Existing 7-D firewall veto

Plus: positive edge; zero/negative edge; uncertainty; volatility; correlation; covariance; invalid
input; NaN/inf values; fail-closed behaviour. The allocator must fail CLOSED — invalid or
incomplete information must never result in larger allocation.

**Integration test scenario** — must exercise simultaneously: SOL directional, BTC/ETH relative
value, SOL/ETH relative value, SOL/BTC relative value. The integration test must verify that
**portfolio-level risk is different from simply summing individual strategy risk**, and that:
research candidates cannot receive production capital; covariance affects allocation; correlated
exposure is penalized; portfolio heat remains <= 3%; concentration limits remain active;
negative-edge candidates are rejected; degraded candidates are throttled; invalid inputs fail
closed; **firewall veto overrides allocator output**.

### §12.2 Relative-value tests

Required at `tests/unit/research/test_relative_value_engine.py` plus
`tests/integration/test_relative_value_research.py`. Minimum coverage: pair construction; hedge
ratio; spread calculation; z-score; half-life; Engle-Granger; Johansen; entry; exit; no-lookahead
behaviour; missing data; insufficient observations; invalid numerical values; friction calculation;
R calculation. Integration must verify: data validation; pair creation; signal generation;
execution simulation; R accounting; result generation; lineage recording; candidate classification.
---

## §13. QUALIFICATION INTEGRATION AND LIFECYCLE

### §13.1 Required logical progression

Every discovered RV candidate must enter the existing lifecycle:

```
DISCOVERED
  → RESEARCHED
  → HISTORICALLY_TESTED
  → ADVERSARIAL_TESTED
  → QUALIFIED_ROBUST
  → FORWARD_PAPER
  → FORWARD_HEALTHY
  → PRODUCTION_QUALIFIED
```

**Do not skip states.** A positive backtest does NOT equal qualification. A statistically
significant historical result does NOT equal forward health. Forward health does NOT equal
production qualification. **Production capital remains locked.**

### §13.2 Mapping onto existing state machines (MANDATORY)

The repository already implements two state machines (§7.7). Milestone 3 must produce an explicit
mapping table, not a third state machine:

| Directive stage | Maps to existing `StrategyStatus` | Maps to existing `StrategyLifecycleTier` |
|---|---|---|
| `DISCOVERED` | `RESEARCH` | *(none — below tier)* |
| `RESEARCHED` | `RESEARCH` / `PROMISING` | *(none — below tier)* |
| `HISTORICALLY_TESTED` | `VALIDATION` / `OOS` | *(none — below tier)* |
| `ADVERSARIAL_TESTED` | `ROBUST` / `FRAGILE` / `FALSIFIED` | *(none — below tier)* |
| `QUALIFIED_ROBUST` | `QUALIFIED` | `HISTORICAL_ROBUST` |
| `FORWARD_PAPER` | `PAPER` | `HISTORICAL_ROBUST` (paper running) |
| `FORWARD_HEALTHY` | `PAPER` | `FORWARD_HEALTHY` |
| `PRODUCTION_QUALIFIED` | `QUALIFIED` | `PRODUCTION_QUALIFIED` |

This table must be verified against the actual enum members at implementation time and corrected if
mismatched. It must be emitted inside the qualification audit artifact.

### §13.3 Promotion boundary

A positive backtest is NOT a promotion event. A statistically significant historical relationship is
NOT production qualification. A robust historical RV candidate is NOT automatically forward healthy.

No RV candidate may enter production allocation; enter live execution; unlock capital; or bypass the
Statistical Qualification Gate during this milestone. **All new RV candidates remain `RESEARCH_ONLY`**
unless they independently satisfy the existing lifecycle architecture.

Categories must never be collapsed:

```
implemented ≠ tested ≠ researched ≠ historically robust ≠ forward healthy
            ≠ production qualified ≠ falsified
```

---

## §14. ADVERSARIAL RESEARCH BATTERY

### §14.1 Trigger

Any RV candidate showing positive baseline economics must **automatically** enter adversarial
testing. Positive baseline results alone never constitute qualification.

### §14.2 Required stress dimensions

```
BASELINE
2X FRICTION
LATENCY
ADVERSE EXECUTION
OUTLIER REMOVAL
PARAMETER PERTURBATION
REGIME STABILITY
```

Where applicable also test: increased spread; slippage; adverse-first collision; rolling-window
stability; calendar-quarter stability; trade-order permutation where statistically meaningful; data
perturbation; capacity constraints; execution degradation.

### §14.3 Reuse mandate

The repository already implements an adversarial framework (§7.6):
`research/discovery_lab/adversarial_researcher.py` writing `ADVERSARIAL_STRESS_BATTERY.json`,
supported by `audit_friction_stress.py`, `audit_walk_forward.py`, `audit_reproducibility.py`,
`audit_parameter_landscape.py`, `audit_portfolio_correlation.py` and `audit_execution_forensics.py`.
**Reuse this framework.** Only create new adversarial infrastructure if the capability is genuinely
absent, and record that determination in the walkthrough.

### §14.4 Permitted classifications

```
ROBUST
FRAGILE
LATENCY_SENSITIVE
FRICTION_SENSITIVE
OUTLIER_DEPENDENT
REGIME_DEPENDENT
FALSIFIED
INSUFFICIENT_DATA
```

Do not promote a candidate merely because its headline return is large.

### §14.5 Positive-result scepticism stop condition

If a candidate produces unusually high returns, DO NOT optimize it further automatically; increase
leverage; reduce friction assumptions; increase allocation; unlock capital; or call it
production-ready.

Instead: 1) flag it for forensic review; 2) verify data lineage; 3) verify no lookahead; 4) verify
execution semantics; 5) verify friction; 6) verify OOS behaviour; 7) run adversarial tests;
8) classify it. **A large return is a trigger for scepticism, not automatic promotion.**

### §14.6 Negative-result stop condition

If every RV candidate fails, STOP. Do NOT loosen thresholds; reduce friction; increase leverage;
change execution assumptions; search until something becomes profitable; or manufacture another pair
universe. Record the result as `RELATIVE_VALUE BASELINE FALSIFIED / DEFERRED`, identify the next
bottleneck, and report `COMPLETE_NO_SURVIVORS`.

**A falsified hypothesis is a successful research outcome.**

---

## §15. STOP CONDITIONS (CONSOLIDATED)

This section merges all previously duplicated stop conditions into one authoritative list.

### §15.1 Stop condition — Portfolio Engine

Stop portfolio-engine development when ALL are true: generic allocator exists; existing risk
architecture is integrated; expected-net-edge logic works; uncertainty adjustment works;
covariance/correlation logic works; volatility-aware sizing works; concentration limits work; heat
limit works; drawdown throttling works; degradation throttling works; capacity constraints work;
lifecycle filtering works; fail-closed behaviour is tested; integration tests pass; audit artifact is
generated.

**Then STOP ADDING PORTFOLIO FEATURES.** Do not continue into portfolio optimization research.

### §15.2 Stop condition — Relative-Value Engine

Stop RV-engine development when ALL are true: three required pairs are supported; 1D and 4H are
supported; data-quality validation is integrated; Engle-Granger is implemented; Johansen is
implemented where applicable; hedge ratio is auditable; spread construction is causal; z-score is
implemented; half-life is implemented; entry/exit rules are explicit; realistic friction is
included; adverse-first execution is respected; baseline backtest runs; OOS evaluation runs where
data permits; adversarial tests run; candidate classifications are produced; lineage artifact is
generated; results are reproducible.

**Then STOP ADDING RV FEATURES.** Do not immediately build another alpha family.

### §15.3 Stop condition — Testing

Testing is complete only when all new targeted tests pass, portfolio+RV integration passes, and the
complete repository suite passes. If failures occur: diagnose; repair; rerun targeted; rerun
integration; rerun full regression. **Do not suppress or skip failing tests. Do not weaken assertions
merely to obtain a green suite.**

### §15.4 Stop condition — Research

Research is complete when the requested baseline and adversarial experiments have been executed on
the certified data. Required matrix:

```
Pairs:      BTC/ETH, SOL/ETH, SOL/BTC
Timeframes: 1D, 4H
Tests:      Baseline, OOS where possible, 2x friction, latency,
            adverse execution, outlier removal, parameter perturbation, regime stability
```

Once this matrix is complete: **STOP.** The result may be robust, fragile, regime-dependent,
friction-sensitive, latency-sensitive, outlier-dependent or falsified. **All are acceptable
outcomes.**

### §15.5 Stop condition — Capital

This is absolute. Regardless of every positive result produced during this milestone:

```
REAL CAPITAL = LOCKED
LIVE ORDERS = DISABLED
EXCHANGE CREDENTIALS = ABSENT
```

No code created in this milestone may unlock capital. No candidate may receive real capital. No
automated promotion to live execution is permitted.

### §15.6 Stop condition — Repository

Before declaring completion, `git status --short` must be inspected and the final diff reviewed.
Verify: no accidental files; no credentials; no generated secrets; no temporary debugging artifacts;
no broken imports; no untracked critical artifacts; no accidental deletion of existing research
evidence. Only commit when the repository is in a reproducible milestone state.

**Per §7.3, the pre-existing untracked Milestone 2 files must be preserved and committed as the
baseline, not discarded.**

### §15.7 Stop condition — Scope

After all required deliverables have been implemented, tested, audited, and the completion manifest
verified: **STOP ENGINEERING THIS MILESTONE.** Do not automatically begin HFT; ML; market making;
additional arbitrage families; additional RV pairs; Set 5/6 optimization; live trading; capital
deployment; or another architecture rewrite.

Produce the final report, identify exactly **ONE** next bottleneck, then stop.

---

## §16. SAFETY AND CAPITAL FIREWALL

### §16.1 Non-negotiable rules

- No exchange API credentials.
- No live order submission.
- No withdrawal capability.
- No production capital allocation.
- No bypassing StatisticalQualificationGate.
- No bypassing PortfolioRiskFirewall.
- No changing capital limits merely to make tests pass.
- No promoting research candidates to production.
- No deleting failed research results.
- No rewriting historical results to improve presentation.
- Real capital remains: `LOCKED`

### §16.2 Security verification

Discover the repository's existing security / firewall verification procedures and run them. At
minimum inspect `git status --short` and search production configuration/code for exchange
credentials and live-order paths. Verify:

```
NO LIVE API KEYS
NO SECRET MATERIAL
NO LIVE ORDER PATH
BROKER = SIMULATED
CAPITAL FIREWALL = LOCKED
```

If any unexpected credential or live-order path is discovered: `SECURITY_STOP = TRUE`. Stop milestone
execution immediately and report the exact issue.

### §16.3 Safety overrides completion

If any of the following occurs — live credentials detected; live order path becomes reachable;
capital firewall compromised; forward state corrupted; data provenance becomes unknowable;
reproducibility fails materially; unresolved regression compromises existing behaviour — then STOP,
set `completion_status = BLOCKED`, and report the exact reason.

### §16.4 Forward paper protection

The existing SOL Set 2 forward-paper daemon (`production/forward_paper_daemon.py`) observation stream
must NOT be reset, contaminated, rewritten or optimized against.

Do not: reset its state; rewrite its historical observations; inject backtest trades; inject
synthetic forward trades; or modify the historical benchmark to improve results. Do not restart or
reset the forward state merely to produce a cleaner report.

It must remain operational and continue collecting: trades; expectancy; drawdown; slippage;
friction; spread; holding time; reality deltas; market regime; data quality; heartbeat; operational
errors. The forward observation stream is evidence and must remain causally isolated.

Verification entry points: `research/results/FORWARD_PAPER_DAEMON_AUDIT.json`,
`tests/integration/test_forward_daemon_oat.py`,
`tests/unit/production/test_forward_paper_daemon.py`. Confirm daemon state exists; heartbeat exists;
forward observations remain separate; SOL Set 2 state remains intact; no backtest trades were
injected; capital remains locked.

### §16.5 Evidence preservation

Do not erase historical evidence merely to make the repository look clean. Do not delete failed
research merely because it is unattractive. Do not overwrite prior evidence without preserving
lineage. Do not revert, stash or discard the uncommitted Milestone 2 artifacts identified in §7.3.

---

## §17. REQUIRED DELIVERABLES — MERGED MANIFEST

This section merges the two previously duplicated deliverable manifests and reconciles each item
against measured repository state (§7).

**Canonical-location rule:** the paths below are the CANONICAL expected locations. Do not create
alternative duplicate files merely because a similarly named component already exists. If an
equivalent implementation already exists, **extend it** and satisfy the canonical deliverable path
through the existing implementation plus a clearly documented compatibility layer. Where the existing
repository structure makes a different location technically necessary, preserve the existing
architecture and document the deviation in `QCP_MILESTONE_3_WALKTHROUGH.md`.

### §17.1 Portfolio Intelligence

| # | Required deliverable | Measured status | Action |
|---|---|---|---|
| A1 | `portfolio_engine/capital_allocator.py` | Directory + sibling modules exist; no generic net-edge allocator | **CREATE (extending existing `portfolio_engine` package)** |
| A2 | `tests/unit/portfolio_engine/test_capital_allocator.py` | Dir exists; file does not | **CREATE** |
| A3 | `tests/integration/test_portfolio_allocation.py` | Dir exists; file does not | **CREATE** |
| A4 | `research/results/PORTFOLIO_ALLOCATOR_AUDIT.json` | Does not exist | **CREATE** |

A1 must contain: alpha-slot input contract; expected-net-edge calculation; uncertainty/confidence
adjustment; volatility normalization; covariance/correlation adjustment; concentration control;
portfolio heat control; drawdown throttling; degradation throttling; capacity constraint; lifecycle
eligibility; deterministic allocation output; fail-closed behaviour. It must NOT contain
strategy-specific assumptions such as hard-coded SOL Set 2 allocation logic.

A4 must contain: allocator version; inputs; allocation outputs; portfolio heat; concentration;
covariance/correlation information; drawdown state; degradation state; capacity state; rejected
candidates; veto reasons; fail-closed tests; timestamp; code version/commit where available. It must
be machine-readable.

### §17.2 Relative Value Alpha Factory

| # | Required deliverable | Measured status | Action |
|---|---|---|---|
| B1 | `research/discovery_lab/relative_value_engine.py` | Equivalent capability exists as `family_09_relative_value.py` | **EXTEND existing module; add canonical path as documented compatibility layer (§11.2)** |
| B2 | `research/discovery_lab/relative_value_config.py` | Configuration is currently inline in the module + its `__main__` block | **CREATE** |
| B3 | `tests/unit/research/test_relative_value_engine.py` | Dir exists; `tests/unit/test_family_09_relative_value.py` exists flat | **CREATE (may extend existing flat test)** |
| B4 | `tests/integration/test_relative_value_research.py` | Does not exist | **CREATE** |

B1 must support BTC/ETH, SOL/ETH, SOL/BTC on 1D and 4H, with: pair construction; hedge-ratio
estimation; Engle-Granger; Johansen where applicable; spread generation; z-score; half-life; entry
logic; exit logic; invalidation/stop logic; turnover calculation; friction modelling; adverse-first
execution; R accounting; capacity estimation; regime tagging; reproducible configuration.

B2 must explicitly define: pairs; timeframes; lookback periods; hedge-ratio method; z-score
parameters; half-life parameters; entry threshold; exit threshold; stop/invalidation; friction
assumptions; slippage assumptions; fee assumptions; execution policy; research/OOS boundaries.
**No unexplained magic numbers.**

### §17.3 Data lineage

| # | Required deliverable | Measured status | Action |
|---|---|---|---|
| C1 | `research/results/DATA_LINEAGE_AUDIT.json` | Does not exist | **CREATE** |
| C2 | `research/discovery_lab/data_manifest.json` | Equivalent data exists at `scratch/dataset_manifests.json` (24 datasets, SHA-256) | **CREATE the canonical manifest from measured source (not by inventing data)** |

C1 must record, for every research dataset: asset; pair; timeframe; start; end; observation count;
expected observation count; missing bars; duplicate bars; OHLC anomalies; quality verdict; dataset
hash; source identifier. This artifact determines which historical periods may legitimately be
researched.

C2 must describe the exact datasets consumed by the RV research runner. The research engine must not
silently discover and substitute arbitrary datasets.

### §17.4 Research runners

| # | Required deliverable | Measured status | Action |
|---|---|---|---|
| D1 | `research/experiments/run_relative_value_baseline.py` | `research/experiments/` exists; a `__main__` baseline exists inside `family_09_relative_value.py` | **CREATE — use or extend the repository-native experiment-runner pattern** |
| D2 | `research/experiments/run_relative_value_adversarial.py` | `adversarial_researcher.py` exists in `discovery_lab` | **CREATE — must reuse the existing adversarial framework (§14.3)** |
| D1b | `research/experiments/run_data_lineage_audit.py` | Does not exist | **CREATE only if no canonical data-quality runner is discovered** |
| D1c | `research/experiments/run_portfolio_allocator_audit.py` | Does not exist | **CREATE** |

D1 must execute the defined baseline across BTC/ETH, SOL/ETH, SOL/BTC on 1D and 4H using only
certified data, and must produce deterministic results. D2 must execute BASELINE, 2X FRICTION,
LATENCY, ADVERSE EXECUTION, OUTLIER REMOVAL, PARAMETER PERTURBATION and REGIME STABILITY.

### §17.5 Research audit artifacts

| # | Required deliverable | Action |
|---|---|---|
| E1 | `research/results/RELATIVE_VALUE_BASELINE_AUDIT.json` | **CREATE** |
| E2 | `research/results/RELATIVE_VALUE_ADVERSARIAL_AUDIT.json` | **CREATE** |
| F1 | `research/results/RELATIVE_VALUE_QUALIFICATION_AUDIT.json` | **CREATE** |
| G1 | `research/results/QCP_MILESTONE_3_AUDIT.json` | **CREATE** |
| H1 | `research/results/QCP_MILESTONE_3_WALKTHROUGH.md` | **CREATE** |
| I1 | `research/results/QCP_MILESTONE_3_TEST_REPORT.json` | **CREATE** |

E1 must record, per pair/timeframe: dataset; observations; test statistics; p-values; hedge ratio;
spread characteristics; half-life; trades; win rate; expectancy; net R; profit factor; Sharpe;
Sortino; maximum drawdown; turnover; friction drag; capacity; regime distribution; OOS result where
available; classification.

E2 must record, per candidate: baseline result; 2x friction result; latency result; adverse execution
result; outlier-removal result; parameter perturbation result; regime result; degradation/failure
mode; final classification (§14.4).

F1 must record, per candidate: candidate ID; family; pair; timeframe; lifecycle state (mapped per
§13.2); historical result; adversarial result; data-quality state; qualification state; promotion
blockers; recommended next state. **No candidate may bypass the existing qualification lifecycle.**

G1 is the authoritative machine-readable completion artifact and must contain the keys:
`milestone, scope, repository_version, test_results, portfolio_allocator, relative_value,
data_lineage, adversarial_results, qualification_results, capital_firewall, forward_paper_status,
failed_items, blocked_items, future_backlog, completion_status, next_bottleneck`. Its final
`completion_status` must be one of `COMPLETE_SURVIVORS`, `COMPLETE_NO_SURVIVORS`, `BLOCKED`.

I1 must record: targeted test count/passed/failed; integration test count/passed/failed; full-suite
count/passed/failed; runtime; final status. **All numbers must come from actual execution.**

H1 must be human-readable, free of marketing language, and must not describe an unqualified strategy
as production-ready. It must cover: what was discovered; what already existed; what was reused; what
was implemented; what was tested; what research was run; what survived; what failed; why candidates
failed; portfolio allocator behaviour; data limitations; qualification status; capital status; exact
next bottleneck; and any deviations from canonical paths.

### §17.6 Reproducibility requirement

Every generated research result must make it possible to determine:

```
WHAT DATA?  WHAT CODE?  WHAT PARAMETERS?  WHAT EXECUTION MODEL?
WHAT FRICTION?  WHAT TIME PERIOD?  WHAT RANDOM SEED?  WHAT RESULT?
```

Where applicable include: git commit; dataset hash; configuration hash; random seed; execution
timestamp. If deterministic, record `DETERMINISTIC = TRUE`. If nondeterministic, record
`DETERMINISTIC = FALSE` and why.

### §17.7 Required completion checklist

A file existing at the expected path does NOT constitute completion. Each deliverable must be
`IMPLEMENTED + TESTED + INTEGRATED WHERE REQUIRED + EXECUTED WHERE REQUIRED + AUDITED`. If a file
exists but its required behaviour is not verified: `DELIVERABLE = INCOMPLETE`. If a requested
experiment cannot run because certified data is unavailable: `DELIVERABLE = BLOCKED_BY_DATA`. Do not
fabricate the missing result.

```
[ ] portfolio_engine/capital_allocator.py
[ ] tests/unit/portfolio_engine/test_capital_allocator.py
[ ] tests/integration/test_portfolio_allocation.py
[ ] research/discovery_lab/relative_value_engine.py
[ ] research/discovery_lab/relative_value_config.py
[ ] tests/unit/research/test_relative_value_engine.py
[ ] tests/integration/test_relative_value_research.py
[ ] research/discovery_lab/data_manifest.json
[ ] research/experiments/run_relative_value_baseline.py
[ ] research/experiments/run_relative_value_adversarial.py
[ ] research/results/DATA_LINEAGE_AUDIT.json
[ ] research/results/PORTFOLIO_ALLOCATOR_AUDIT.json
[ ] research/results/RELATIVE_VALUE_BASELINE_AUDIT.json
[ ] research/results/RELATIVE_VALUE_ADVERSARIAL_AUDIT.json
[ ] research/results/RELATIVE_VALUE_QUALIFICATION_AUDIT.json
[ ] research/results/QCP_MILESTONE_3_AUDIT.json
[ ] research/results/QCP_MILESTONE_3_TEST_REPORT.json
[ ] research/results/QCP_MILESTONE_3_WALKTHROUGH.md
[ ] All new unit tests pass
[ ] All new integration tests pass
[ ] Full repository regression passes
[ ] Data lineage verified
[ ] Research reproducibility verified
[ ] No lookahead verified
[ ] Adverse-first execution verified
[ ] Existing forward-paper stream preserved
[ ] Capital Firewall verified
[ ] No live credentials
[ ] No live execution
[ ] No production capital allocation
```

---

## §18. EXECUTION MANIFEST — SINGLE SOURCE OF TRUTH

This section replaces **all three** previously duplicated execution manifests. It is the only
authoritative execution sequence. It contains **no placeholder commands**. Every command below is
either measured from repository truth (§7) or is a discovery step that determines the command.

### §18.0 Global discovery-first rule

At every phase:

```
DISCOVER → IDENTIFY CANONICAL PATH → REUSE → IMPLEMENT GAP → TEST → AUDIT
```

Never:

```
ASSUME PATH → INVENT COMMAND → CREATE DUPLICATE → DECLARE COMPLETE
```

If a referenced command, file, module, runner or test does not exist: 1) search for its equivalent;
2) inspect neighbouring implementation patterns; 3) identify the canonical replacement;
4) document the substitution; 5) only create a new component when no suitable existing capability
exists. **Every substituted command or implementation path must be recorded in the final walkthrough.**

**Execution-order rule:** the sequence in §18.17 is fixed. No new major workstream may be inserted
into it without an explicit future directive.

---

### §18.1 PHASE 0 — Repository preflight and discovery

**Do not begin by assuming commands, paths, runners or test locations.** First discover.

**Step 0.1 — Record pre-modification state.**

```bash
git status --short
git rev-parse HEAD
git rev-parse --abbrev-ref HEAD
```

Record the exact commit in the milestone audit. **Required result:** repository state recorded before
modifications. **Measured baseline expectation (§7.3): the tree is DIRTY with untracked Milestone 2
artifacts — record it, do not clean it.**

**Step 0.2 — Discover the environment and tooling.**

```bash
ls -la
find . -maxdepth 1 -type d -not -path './.git' | sort
for f in pyproject.toml pytest.ini setup.cfg tox.ini noxfile.py Makefile conftest.py requirements.txt; do [ -f "$f" ] && echo "=== $f ===" && cat "$f"; done
python3 --version
python3 -m pytest --version
```

Also search for CI workflows, existing test scripts and existing research scripts. Determine:
repository root; branch; commit; clean/dirty state; Python environment; package manager; dependency
manager; test framework; test configuration; canonical test invocation; research execution
conventions. **Output:** record the actual repository-native commands discovered.

**Measured result (§7.1):** no `pytest.ini`, `tox.ini`, `noxfile.py` or `Makefile` exists. Test
configuration lives in `pyproject.toml` `[tool.pytest.ini_options]` with `testpaths = ["tests"]`.
Python 3.12.3, pytest 9.1.1.

**Step 0.3 — Discover the baseline test command and run it.**

The repository-native equivalent of the canonical invocation is:

```bash
python3 -m pytest -q
```

(Equivalently `PYTHONPATH=. pytest -q`. The `testpaths` setting means no path argument is required.)

Record: total tests; passed; failed; skipped; runtime.

**Measured baseline (§7.2): `487 passed in 124.93s (0:02:04)`.**

**STOP CONDITION.** If the pre-existing suite is failing before new implementation begins:
`BASELINE = BLOCKED`. Do not attribute pre-existing failures to the new milestone. Investigate
sufficiently to establish baseline state, then proceed only if the failure is understood and does
not compromise the requested work.

---

### §18.2 PHASE 1 — Data certification discovery

**Step 1.1 — Discover existing data infrastructure.** Search the repository for existing data
manifests; cache indexes; lineage tools; hashing utilities; OHLC validators; dataset certification
scripts; research data loaders.

```bash
find market_data scratch -maxdepth 3 -iname '*manifest*' -o -iname '*lineage*' -o -iname '*quality*' | sort
grep -rln --include='*.py' -E 'DataQualityEngine|audit_candles|sha256_dataset_hash|CERTIFIED_CLEAN' . | grep -v '.git/'
```

**Measured result (§7.6):** a canonical data-quality **library** already exists at
`market_data/data_quality_engine.py` (`DataQualityEngine.audit_candles` → `DataQualityReport` with
verdict, SHA-256 dataset hash, gaps, completeness, anomalies). A certified dataset manifest already
exists at `scratch/dataset_manifests.json` (24 datasets, SHA-256 checksums, missing-interval counts).
**No canonical data-quality *runner* was identified.**

**Step 1.2 — Determine the canonical runner.** If discovery finds a canonical data-quality/lineage
runner, invoke it. If none exists, inspect neighbouring patterns in `research/experiments/` and create
`research/experiments/run_data_lineage_audit.py` that *consumes* `DataQualityEngine` and the existing
manifest — it must not reimplement either.

```bash
python3 research/experiments/run_data_lineage_audit.py
```

**Step 1.3 — Verify and inspect the lineage artifact.**

```bash
test -f research/results/DATA_LINEAGE_AUDIT.json && echo PRESENT
python3 -c "import json;d=json.load(open('research/results/DATA_LINEAGE_AUDIT.json'));print(json.dumps(d,indent=2)[:2000])"
```

**Required result:** every dataset used by RV research must carry source; symbol; timeframe; start;
end; observation count; missing-bar information; quality verdict; dataset hash.

**STOP CONDITION.** If a required dataset is `REJECTED_CORRUPT`, do not research it. If a requested
period is unavailable: `DATA_SCOPE = LIMITED`. Continue only with certified data.

**Measured expectation (§5.2):** all 24 datasets are manifest-eligible. The binding constraint is
not corruption but **coverage**: SOL begins 2020-08-14/15; SOL 15m ends 2023-01-01; 5m/1m cover
~35 days. The certified RV research window is therefore **1D and 4H, 2020-08-15 → 2026-09-01**.

---

### §18.3 PHASE 2 — Portfolio allocator implementation

**Step 2.1 — Discover existing portfolio infrastructure before writing anything.**

```bash
find portfolio_engine capital_intelligence risk_engine -type f -name '*.py' | sort
grep -rn --include='*.py' -E 'class .*Allocat|PortfolioIntelligenceEngine|NetEdge|CapitalFeasib|PAIRWISE_CORRELATIONS|MAX_PORTFOLIO_HEAT' . | grep -v '.git/'
find tests -iname '*portfolio*' -o -iname '*allocator*' -o -iname '*capital*' | sort
```

Map: **existing capability → missing capability → implementation location.** Do not create a new
allocator until this map exists.

**Measured result (§7.6):** the following already exist and must be extended, not duplicated —
`PortfolioIntelligenceEngine` (heat ceiling, drawdown scaling, correlation concentration),
`VolatilityTargetSizer`, `DrawdownDampener`, `PortfolioState`/`PortfolioRiskConfig`,
`PortfolioHedgingEngine`, `PortfolioCoordinator`, `PortfolioRiskFirewall`,
`alpha_capital_intelligence`, plus existing tests `tests/unit/test_portfolio_intelligence.py` and
`tests/unit/test_capital_feasibility.py`.

**Measured gap:** no generic per-alpha-slot allocator driven by expected net edge, confidence
interval, data-derived covariance, capacity and lifecycle state.

**Step 2.2 — Implement only the missing generic capability** at
`portfolio_engine/capital_allocator.py`, per §10. Add targeted tests and integration tests per
§12.1. After every material implementation: **test → inspect failure → repair → rerun.** Do not
batch large unverified changes.

**Step 2.3 — Run targeted unit tests.**

```bash
python3 -m pytest -v tests/unit/portfolio_engine/test_capital_allocator.py
```

**Required result:** 100% pass.

**STOP CONDITION.** If a unit test fails: 1) diagnose; 2) repair; 3) rerun the targeted suite. **Do
not proceed to integration testing until the targeted suite passes.**

**Step 2.4 — Run portfolio integration tests.**

```bash
python3 -m pytest -v tests/integration/test_portfolio_allocation.py
```

**Required result:** 100% pass.

**Step 2.5 — Generate the allocator audit artifact.**

```bash
python3 research/experiments/run_portfolio_allocator_audit.py
test -f research/results/PORTFOLIO_ALLOCATOR_AUDIT.json && echo PRESENT
```

---

### §18.4 PHASE 3 — Relative-value implementation

**Step 3.1 — Discover existing RV infrastructure before creating anything.**

```bash
find research/discovery_lab -type f -name '*.py' | sort
grep -rln --include='*.py' -iE 'cointegrat|hedge_ratio|half_life|engle|johansen|z_score|RelativeValue|stat_arb' . | grep -v '.git/'
find tests -iname '*relative*' -o -iname '*family_09*' | sort
```

Map: **existing capability → reusable component → missing capability.**

**Measured result (§7.6, §11.2):** `research/discovery_lab/family_09_relative_value.py` already
implements `RelativeValueAlphaEngine` with pairs SOL/ETH, SOL/BTC, ETH/BTC; causal rolling z-score;
entry/exit/stop/max-hold; DEV/VAL/OOS partitioning; friction parameter. Tests exist at
`tests/unit/test_family_09_relative_value.py`.

**Measured gaps (§11.2):** no hedge ratio; no Engle-Granger; no Johansen; no half-life; no
data-quality gating; no lineage recording; **no BTC/ETH pair** (engine uses ETH/BTC); scalar friction
only; no lifecycle integration; no capacity/beta/regime analysis.

**Step 3.2 — Implement only the missing pieces** per §11. Add `relative_value_config.py` to
centralize configuration (no unexplained magic numbers). Reuse `DataQualityEngine` for gating and
`strategy_candidate_v2.data_audit.load_candles` for loading.

**Step 3.3 — Reconciled pair convention.** The directive requires `BTC/ETH`; the existing engine
names the same relationship `ETH/BTC`. Choose one canonical leg ordering, document the reconciliation
explicitly in the walkthrough, and ensure the hedge-ratio sign convention is tested. **Do not
silently emit both as if they were different pairs.**

**Step 3.4 — Run RV unit tests.**

```bash
python3 -m pytest -v tests/unit/research/test_relative_value_engine.py
```

**Required result:** 100% pass.

**Step 3.5 — Run RV integration tests.**

```bash
python3 -m pytest -v tests/integration/test_relative_value_research.py
```

**Required result:** 100% pass.

---

### §18.5 PHASE 4 — Baseline RV research

**Step 4.1 — Discover the canonical research execution framework.** Search for experiment runners;
discovery-lab runners; baseline runners; result serializers; audit JSON generators; reproducibility
utilities; experiment configuration patterns. Determine the canonical way QCP launches research.
Do not assume a filename means the runner must be created.

```bash
find research/experiments -type f -name '*.py' | sort
find research/discovery_lab -maxdepth 1 -name 'run_*.py' | sort
```

**Step 4.2 — Execute the baseline.**

```bash
python3 research/experiments/run_relative_value_baseline.py
```

The runner must evaluate BTC/ETH, SOL/ETH, SOL/BTC on 1D and 4H using certified data only, per §5.3.

**Step 4.3 — Verify and inspect the baseline artifact.**

```bash
test -f research/results/RELATIVE_VALUE_BASELINE_AUDIT.json && echo PRESENT
python3 -c "import json;print(len(json.load(open('research/results/RELATIVE_VALUE_BASELINE_AUDIT.json')).get('results',[])))"
```

The artifact must contain an explicit result for every attempted pair/timeframe combination,
including combinations that produced zero trades or failed cointegration.

**Step 4.4 — Baseline integrity checks.** The runner must verify before accepting results:
`NO LOOKAHEAD`, `CAUSAL FEATURES`, `ADVERSE-FIRST EXECUTION`, `REALISTIC FRICTION`, `VALID R
ACCOUNTING`, `CERTIFIED DATA`. If any check fails: `BASELINE_RESEARCH = INVALID`. Repair before
proceeding.

---

### §18.6 PHASE 5 — Adversarial RV research

**Step 5.1 — Discover the existing adversarial framework** (see §14.3). Reuse it.

```bash
find research/discovery_lab -name 'audit_*.py' -o -name 'adversarial_*.py' | sort
```

**Step 5.2 — Execute the adversarial battery.**

```bash
python3 research/experiments/run_relative_value_adversarial.py
```

**Step 5.3 — Verify the adversarial artifact.**

```bash
test -f research/results/RELATIVE_VALUE_ADVERSARIAL_AUDIT.json && echo PRESENT
```

Every baseline survivor must have an adversarial result. Every RV candidate must receive a
classification from §14.4.

---

### §18.7 PHASE 6 — Qualification integration

**Step 6.1 — Discover the qualification framework before integrating.**

```bash
find production/qualification -type f -name '*.py' | sort
grep -rn --include='*.py' -E 'StrategyLifecycleTier|QualificationHurdles|StatisticalQualificationGate|ForwardQualification' . | grep -v '.git/'
find research/experiments -iname '*qualification*' | sort
```

**Measured result (§7.6, §7.7):** `StatisticalQualificationGatekeeper` exists with
`StrategyLifecycleTier` and `QualificationHurdles`; `ForwardQualificationEngine` exists; a runner
exists at `research/experiments/run_statistical_qualification_audit.py`. `StrategyRegistry` provides
a 13-state lifecycle.

**Step 6.2 — Map, then integrate.** Emit the §13.2 mapping table. Route RV baseline and adversarial
results into the existing gate. **Do not create a third state machine.**

**Step 6.3 — Execute the qualification audit.** Use the discovered runner:

```bash
python3 research/experiments/run_statistical_qualification_audit.py
```

**Step 6.4 — Verify non-conflation.** Confirm `RESEARCH_ONLY`, `HISTORICALLY_ROBUST`,
`FORWARD_HEALTHY` and `PRODUCTION_QUALIFIED` are not conflated. **Every new RV candidate must remain
capital-ineligible unless independently qualified.**

---

### §18.8 PHASE 7 — Portfolio + RV end-to-end test

**Step 7.1 — Run both integration suites together.**

```bash
python3 -m pytest -v tests/integration/test_portfolio_allocation.py tests/integration/test_relative_value_research.py
```

**Step 7.2 — End-to-end scenario.** Create and execute
`tests/integration/test_portfolio_rv_end_to_end.py` if a dedicated end-to-end assertion file is
required:

```bash
python3 -m pytest -v tests/integration/test_portfolio_rv_end_to_end.py
```

The simulation must contain: existing SOL Set 2 directional alpha; BTC/ETH RV candidate; SOL/ETH RV
candidate; SOL/BTC RV candidate — using research/synthetic candidate objects where necessary.

**Required assertions:** research candidates cannot receive production capital; covariance affects
allocation; correlated exposure is penalized; portfolio heat remains <= 3%; concentration limits
remain active; negative-edge candidates are rejected; degraded candidates are throttled; allocator
recognises lifecycle states; allocator respects capacity; invalid inputs fail closed; **firewall veto
overrides allocator output.**

**This integration test must NOT unlock live capital.**

---

### §18.9 PHASE 8 — Reproducibility

**Step 8.1 — Execute the same canonical workflow twice.**

```bash
python3 research/experiments/run_relative_value_baseline.py
cp research/results/RELATIVE_VALUE_BASELINE_AUDIT.json /tmp/qcp/run1.json
python3 research/experiments/run_relative_value_baseline.py
cp research/results/RELATIVE_VALUE_BASELINE_AUDIT.json /tmp/qcp/run2.json
```

**Step 8.2 — Compare deterministic fields.**

```bash
diff /tmp/qcp/run1.json /tmp/qcp/run2.json && echo 'DETERMINISTIC: RUN1 == RUN2'
```

Where the engine is intended to be deterministic, `RUN 1 == RUN 2` must hold for: trade count; net R;
expectancy; drawdown; Sharpe; signal timestamps; candidate classification. Where hashes exist,
compare them too.

**Compare:** candidate counts; trade counts; metrics; qualification states; artifact hashes.

If results differ: `REPRODUCIBILITY = FAILED`. Investigate before declaring completion. **Do not
declare reproducibility merely because both runs complete successfully.** Any unexplained difference
is a blocking research-quality issue.

---

### §18.10 PHASE 9 — Full regression

```bash
python3 -m pytest -q
```

This is mandatory after all implementation and research integration work. **Record the ACTUAL output.
Do not report an estimated test count.**

**If regression fails — for every failure:** 1) capture the failure; 2) identify root cause;
3) repair implementation/test; 4) run the affected targeted test; 5) run the affected integration
test; 6) run the complete regression again. Repeat until `FULL REGRESSION = PASS` or until a genuine
external blocker prevents completion. **Do not skip failing tests. Do not weaken assertions. Do not
delete tests.**

**Reference point:** the measured pre-milestone baseline was `487 passed`. The post-milestone count
must be strictly greater if new tests were added.

---

### §18.11 PHASE 10 — Security and capital firewall verification

Discover the repository's existing security/firewall verification commands and tests, then run them.

```bash
git status --short
grep -rn --include='*.py' -iE 'api_key|api_secret|secret_key|private_key|withdraw|place_order.*live|live_trading\s*=\s*True' production execution_gateway config 2>/dev/null | head -40
python3 -m pytest -v tests/unit/risk_engine/ tests/integration/test_forward_daemon_oat.py
```

Also inspect any repository-native security checks if they exist (e.g. `SECURITY.md` procedures).

**Verify:**

```
NO LIVE API KEYS
NO SECRET MATERIAL
NO LIVE ORDER PATH
BROKER = SIMULATED
CAPITAL FIREWALL = LOCKED
LIVE CAPITAL = 0
LIVE EXECUTION DISABLED
FAIL-CLOSED BEHAVIOUR INTACT
```

Do not create credentials or modify production connectivity. If any unexpected credential or
live-order path is discovered: `SECURITY_STOP = TRUE` — stop immediately and report the exact issue.

---

### §18.12 PHASE 11 — Forward paper verification

Discover the existing forward-paper verification entry point, then verify.

```bash
test -f research/results/FORWARD_PAPER_DAEMON_AUDIT.json && echo PRESENT
python3 -m pytest -v tests/integration/test_forward_daemon_oat.py tests/unit/production/test_forward_paper_daemon.py
python3 -c "import json;d=json.load(open('research/results/FORWARD_PAPER_DAEMON_AUDIT.json'));print(json.dumps(d,indent=2)[:1500])"
```

Confirm: daemon state exists; heartbeat exists; forward observations remain separate; SOL Set 2 state
remains intact; no backtest trades were injected; closed-candle behaviour; stale-data inhibition;
duplicate protection; missing-bar protection; state recovery; position recovery; clean shutdown;
capital remains locked.

**Do NOT restart or reset the forward state merely to produce a cleaner report.** Do not enable live
execution.

---

### §18.13 PHASE 12 — Artifact completeness

Discover repository conventions for research artifacts, then verify every required artifact exists
and is internally consistent.

```bash
for f in \
  portfolio_engine/capital_allocator.py \
  tests/unit/portfolio_engine/test_capital_allocator.py \
  tests/integration/test_portfolio_allocation.py \
  research/discovery_lab/relative_value_engine.py \
  research/discovery_lab/relative_value_config.py \
  research/discovery_lab/data_manifest.json \
  tests/unit/research/test_relative_value_engine.py \
  tests/integration/test_relative_value_research.py \
  research/experiments/run_relative_value_baseline.py \
  research/experiments/run_relative_value_adversarial.py \
  research/results/DATA_LINEAGE_AUDIT.json \
  research/results/PORTFOLIO_ALLOCATOR_AUDIT.json \
  research/results/RELATIVE_VALUE_BASELINE_AUDIT.json \
  research/results/RELATIVE_VALUE_ADVERSARIAL_AUDIT.json \
  research/results/RELATIVE_VALUE_QUALIFICATION_AUDIT.json \
  research/results/QCP_MILESTONE_3_AUDIT.json \
  research/results/QCP_MILESTONE_3_TEST_REPORT.json \
  research/results/QCP_MILESTONE_3_WALKTHROUGH.md ; do
  [ -f "$f" ] && echo "PRESENT  $f" || echo "MISSING  $f"
done
```

Also validate JSON parseability of every generated artifact:

```bash
for f in research/results/*AUDIT.json; do python3 -c "import json,sys;json.load(open(sys.argv[1]));print('VALID',sys.argv[1])" "$f" || echo "INVALID $f"; done
```

Check: timestamps; source commit; configuration; dataset hashes; test results; research results;
qualification; reproducibility; capital state. **A missing required artifact means
`MILESTONE = INCOMPLETE`.**

---

### §18.14 PHASE 13 — Final repository audit

```bash
git status --short
git diff --stat
git status --short | wc -l
```

Inspect the final diff for unintended modifications. Verify no: credentials; secrets; temporary
files; debugging files; accidental deletions; duplicated architecture; generated junk; unrelated
feature work; broken imports; accidental live-execution changes; contradictory documentation.

**Do not erase historical evidence merely to make the repository look clean.** Per §7.3 the
untracked Milestone 2 artifacts (§7.3) must be preserved.

---

### §18.15 PHASE 14 — Final audit generation

Generate **after** final verification so they reflect actual final state:

```
research/results/QCP_MILESTONE_3_AUDIT.json
research/results/QCP_MILESTONE_3_TEST_REPORT.json
research/results/QCP_MILESTONE_3_WALKTHROUGH.md
```

The master audit must contain: `repository_commit, baseline_tests, final_tests, data_status,
portfolio_status, rv_status, adversarial_status, qualification_status, forward_paper_status,
capital_firewall_status, security_status, deliverable_status, completion_status, blocking_issues,
future_backlog, next_bottleneck`.

---

### §18.16 PHASE 15 — Final regression and reporting

Rediscover the final canonical regression invocation if repository state changed, then run it against
the frozen final code state:

```bash
python3 -m pytest -q
git status --short
git rev-parse HEAD
```

**The final report must quote the observed results, not expected results.** Do not report an
expected count. Do not claim 100% unless every test actually passed.

If failures occur: 1) identify root cause; 2) repair; 3) rerun targeted tests; 4) rerun full
regression; 5) repeat until clean or provide a precise blocking report.

---

### §18.17 EXECUTION ORDER — FIXED SEQUENCE

```
  0. Repository baseline and discovery
        ↓
  1. Data certification and lineage
        ↓
  2. Portfolio allocator implementation
        ↓
  3. Portfolio tests
        ↓
  4. RV engine implementation
        ↓
  5. RV tests
        ↓
  6. Baseline RV research
        ↓
  7. Adversarial RV research
        ↓
  8. Qualification integration
        ↓
  9. Portfolio + RV end-to-end integration
        ↓
 10. Reproducibility verification
        ↓
 11. Security / capital firewall verification
        ↓
 12. Forward-paper preservation verification
        ↓
 13. Full regression
        ↓
 14. Artifact completeness
        ↓
 15. Final repository audit
        ↓
 16. Final audit artifacts
        ↓
 17. FINAL REGRESSION
        ↓
 18. FINAL REPORT
        ↓
 STOP
```

No new major workstream may be inserted into this sequence without an explicit future directive.

---

## §19. GLOBAL EXECUTION RULES

**Rule 1 — Never fake success.** A green-looking audit JSON does not override failing tests. A
passing test does not override invalid research. A positive backtest does not override data-quality
failure.

**Rule 2 — Never silently substitute.** Do not substitute datasets, symbols, timeframes, execution
models, friction assumptions or statistical methods without recording the deviation.

**Rule 3 — Never optimize toward a desired result.** If the RV research produces 0 survivors,
report `COMPLETE_NO_SURVIVORS`. That is preferable to introducing unplanned optimization.

**Rule 4 — Never promote because of headline performance.** A candidate with enormous historical
returns must still pass: DATA, CAUSALITY, EXECUTION, FRICTION, OOS, ADVERSARIAL, STATISTICAL,
FORWARD, RISK.

**Rule 5 — Safety overrides completion.** If live credentials are detected; a live order path becomes
reachable; the capital firewall is compromised; the forward state is corrupted; data provenance
becomes unknowable; reproducibility fails materially; or an unresolved regression compromises
existing behaviour — then STOP, set `completion_status = BLOCKED`, and report the exact reason.

**Rule 6 — Autonomy means evidence-driven execution.** Continue through implementation, testing,
research, repair, reproducibility and audit without waiting for manual approval for ordinary
engineering decisions. Stop and report only when a blocker would require: live credentials; live
capital; bypassing a safety control; unverifiable external data; destructive repository action; or an
unresolved ambiguity that materially changes research validity.

**Blocked actions (explicit):** do not deploy live capital; request or store live credentials; bypass
the capital firewall; loosen Candidate #001 merely to increase opportunity; relabel Development
evidence as Validation/OOS; use contaminated lookahead data; use favorable-first same-bar execution;
claim unavailable historical coverage; treat data starvation as strategy failure; hard-code the
allocator to SOL Set2; treat cross-asset RV as BTC/USDT vs ETH/USDT vs SOL/USDT cointegration;
optimize thresholds solely to historical performance; overwrite prior evidence without preserving
lineage; delete failed research merely because it is unattractive; report invented metrics; stop
after the first passing test; assume a placeholder command or guessed path is valid.

---

## §20. COMPLETION GATE AND END STATES

### §20.1 Final completion gate

The milestone may be declared COMPLETE only when every item is true:

```
[✓] Scope respected
[✓] Portfolio allocator implemented
[✓] Portfolio allocator tested
[✓] RV engine implemented
[✓] RV engine tested
[✓] Certified data verified
[✓] Baseline research executed
[✓] Adversarial research executed
[✓] Portfolio/RV integration tested
[✓] Full regression passes
[✓] Audit artifacts generated
[✓] Results independently inspected
[✓] No unsupported claims
[✓] Capital firewall intact
[✓] Forward paper preserved
[✓] Repository health verified
```

If any item fails: `MILESTONE = NOT COMPLETE`. Do not report completion prematurely.

### §20.2 Permitted final states

Exactly one of:

```
COMPLETE_SURVIVORS
COMPLETE_NO_SURVIVORS
BLOCKED
```

- **STATE A — COMPLETE_SURVIVORS.** Required engineering work complete. At least one research
candidate survived the defined battery. Candidate remains research/forward-only unless independently
qualified.
- **STATE B — COMPLETE_NO_SURVIVORS.** Required engineering work complete. All RV candidates failed
or were insufficiently supported. **This is an acceptable research outcome.**
- **STATE C — BLOCKED.** Required engineering work cannot be completed because of missing certified
data; infrastructure dependency; unresolved test failure; reproducibility failure; or repository
integrity issue. Provide the exact blocker. **Do not compensate for the blocker by changing scope.**

### §20.3 Prohibited completion language

Never report `"mostly complete"`, `"essentially complete"`, `"ready for production"` or
`"production ready"` as a substitute for the defined states.

### §20.4 After the stop condition

The forward-paper system may continue operating independently after the milestone completes. The
engineering milestone itself stops.

Produce a `NEXT_BOTTLENECK` section identifying exactly **ONE** highest-value next action based on
evidence. Do not provide a ten-feature wishlist. **Do not begin the next workstream automatically.
Wait for the next strategic decision.**

**Evidence determines the next phase.**

---

## §21. MANDATORY RESPONSE FORMAT

Every autonomous execution cycle must report:

**DISCOVERY** — repository state; current commit; relevant directories; existing implementations
found; existing tests found; existing runners found; available datasets; data coverage; gaps
discovered.

**PLAN** — files to create; files to modify; files deliberately left untouched; dependencies; tests
to run; research to execute; expected artifacts.

**IMPLEMENTATION** — exact changes made; why each change was necessary; reuse decisions;
compatibility considerations.

**TESTING** — tests executed; counts; failures; repairs; rerun results.

**RESEARCH** — datasets; periods; configurations; baseline results; adversarial results;
qualification status.

**AUDIT** — reproducibility; lineage; risk controls; capital firewall; artifact completeness;
unresolved issues.

**FINAL STATE** — implementation status; test status; research status; qualification status; capital
status; exact next action.

---

## §22. FINAL REPORT REQUIREMENTS

### A. Engineering
Files created; files modified; architecture changes; integration points.

### B. Testing
Targeted tests; integration tests; complete regression result; failures repaired.

### C. Portfolio Intelligence
Allocator methodology; risk controls; covariance behaviour; fail-closed behaviour.

### D. Relative-Value Research
Per pair: data period actually available; observations; cointegration evidence; half-life; trades;
net R; expectancy; Sharpe; drawdown; friction; capacity; adversarial results; final classification.

### E. Data Integrity
Report any dataset limitations explicitly.

### F. Qualification
Clearly state which candidates are: research-only; historically robust; forward healthy; production
qualified; falsified. **Never collapse these categories.**

### G. Capital
Explicitly confirm: `REAL CAPITAL = LOCKED` / `LIVE EXECUTION = DISABLED`.

### H. Next Bottleneck
Identify the single highest-value remaining bottleneck based on evidence. Do not invent a new feature
roadmap merely to continue development.

### Reporting standard for every material result
Asset; timeframe / set; date range; data source; trade count; win rate; expectancy; total R; profit
factor; drawdown; loss streak; friction drag; robustness results; failure modes; qualification state;
capital state. **Do not report stale narrative figures when repository-generated artifacts provide
corrected values.**

---

## §23. CURRENT RESEARCH STATE (REFERENCE)

Milestone 2 infrastructure has been implemented and tested. **Measured test suite: 487 / 487 passing**
(verified at execution time: `487 passed in 124.93s`).

Implemented infrastructure: `PerformanceTruthEngine`; continuous forward-paper daemon; multi-asset
comparative forward paper; 7-D Portfolio Risk Firewall; market-neutral basis/funding engine; Data
Quality & Lineage Engine; alpha contracts for major approved alpha families; capital firewall.

Historical forward-paper audit corrected an earlier false 0.00% drawdown interpretation. The true
realized maximum drawdown was **4.73% / $166.96** from a peak of **$3,532.47** to a trough of
**$3,365.50** across the relevant 48-trade sequence.

### Comparative paper period 2024-01-01 → 2026-09-01

**SOL Set2** — 365 trades; 70.14% win rate; 5.2351 R profit factor; +222.92R; +0.611R expectancy;
+$2,783.17 on $1,000; 4.73% true maximum drawdown; maximum loss streak 12; 2.93% friction drag /
$108.44; annualized Sharpe 34.36; forward state `FORWARD_HEALTHY`; allocation `PERMIT CONTINUED PAPER`.

**ETH Set2** — 333 trades; 68.17% win rate; 4.7662 R profit factor; +192.83R; +0.579R expectancy;
+$2,160.33 on $1,000; 6.93% maximum drawdown; maximum loss streak 24; 3.64% friction drag; annualized
Sharpe 31.98; forward state `FORWARD_HEALTHY`; allocation `NO CAPITAL (REFERENCE ONLY)`.

**BTC Set2** — 374 trades; 71.39% win rate; 5.0426 R profit factor; +211.56R; +0.566R expectancy;
+$2,537.20 on $1,000; 7.77% maximum drawdown; maximum loss streak 20; 6.18% friction drag; annualized
Sharpe 34.93; forward state `FORWARD_HEALTHY`; allocation `NO CAPITAL (REFERENCE ONLY)`.

These results demonstrate research / forward-paper health under the specified framework. **They do not
authorize live capital.**

### Current failure decomposition

**Robust research survivor: `FAM-07-MTFCONT_SOLUSDT_Set2`** — 2× friction: +44.8R; windfall removal:
+18.7R; 1-bar latency: +42.2R; positive across 100% of calendar quarters.

**Fragile / windfall-dependent: `FAM-07-MTFCONT_ETHUSDT_Set2`** — failed outlier removal: −1.6R.

**Fragile / windfall-dependent: `FAM-07-MTFCONT_BTCUSDT_Set2`** — failed outlier removal: −7.3R.

**Fragile / latency-sensitive: `FAM-07-MTFCONT_SOLUSDT_Set3`** — failed 1-bar latency: −40.8R.

**Falsified / deprioritised: `FAM-04-MOMENTUM_SOLUSDT_Set2`** — collapsed under multiple adversarial
conditions; must not be treated as robust.

H-MOM-01 remains useful falsification evidence: 3,838 candidates; 1,753 rejected by ≥4R geometry;
18 executed; 0 target hits; −3.6141R. **Do not reinterpret opportunity starvation as proof that strict
geometry should be loosened.**

Historical research result previously described as approximately +281.81R was corrected to
**+278.81R across 1,129 trades** (BTC +81.66R, ETH +89.74R, SOL +107.41R). Underlying artifacts and
research code are authoritative.

---

## §24. FINAL COMMAND

Execute the defined scope autonomously.

```
Inspect → Implement → Test → Research → Audit → Repair → Re-test → Verify → Report
```

Do not ask for approval between ordinary implementation steps. Do not expand scope. Do not optimize
merely because a result is interesting. Do not deploy capital. Stop when the completion gates in §20
are satisfied.

**Final state: capital remains locked at 0, live execution remains disabled, and the milestone ends
with an auditable repository state.**

**The milestone is complete when the evidence is complete — not when there are more features to
build.**
