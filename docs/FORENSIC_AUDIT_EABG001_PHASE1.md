# QCP Repository Forensic Audit — EABG-001, Phase 1

**Directive:** EABG-001 (Economic-First Autonomous Build Governor)
**Platform:** Quantitative Crypto Platform (QCP)
**Audit type:** Read-only forensic classification of the repository as it exists at `main` / `8b85fcb`
**Machine-readable twin:** [`research/results/FORENSIC_AUDIT_EABG001_FINDINGS.json`](../research/results/FORENSIC_AUDIT_EABG001_FINDINGS.json)
**Capital impact:** none. Live capital remains `$0.00`, fail-closed. No strategy was promoted. No history was rewritten.

---

## 1. Why this audit stopped the build loop

EABG-001 permits halting the loop at any of: unsafe architecture, unavailable data, contradictory
requirements, corrupted evidence, test failure, unknown financial behaviour, security failure, OOS leakage.
**Three such conditions are present in this repository:**

| Stop condition | Triggering fact |
| :--- | :--- |
| **Contradictory evidence** | One strategy ID (`FAM-07-MTFCONT_SOLUSDT_Set2`) is simultaneously recorded as **+278.32% equity, PF 5.24, `FORWARD_HEALTHY`** and as **0 wins / 14 losses, −0.9066R expectancy, bootstrap P(edge>0) = 0.0%, statistically insignificant**. |
| **Corrupted evidence** | The forward telemetry store is **53% duplicate records** (2,302 rows / 1,074 unique trades, max repetition 20), and that same store was consumed to produce the +278% headline. |
| **Unsafe architecture** | The canonical strategy factory **defaults to `QUALIFIED_ROBUST`**, and the Promotion Governor is **not imported by any capital path**, so the lifecycle cannot veto anything. |

Per the directive, the correct response is to halt and quarantine — not to keep building. This document
reports the classification; the repair sequence follows in §7.

---

## 2. What was verified (ground truth, not claims)

| Item | Verified value | How verified |
| :--- | :--- | :--- |
| HEAD / branch | `8b85fcb` on `main` | `git log`, `git status` |
| M2 baseline | `7d96b77` (`feat(milestone-2): preserve verified milestone 2 baseline…`), **ancestor of HEAD** | `git merge-base --is-ancestor` |
| Tracked / untracked / modified | 1,065 / 65 / 8 | `git ls-files`, `git status --short` |
| Files on disk (excl. git, caches) | 1,234 | filesystem walk |
| Test collection | **593 tests in 137 files** | `pytest --collect-only -q` |
| Test execution | **593 passed, 0 failed, 98.97s** | `pytest tests/ -q` |
| Split | unit 492, integration 69, comprehensive 32 (7 files) | per-file collection counts |
| Certified warehouse | 24 datasets = **3 assets** (BTC, ETH, SOL) × 8 timeframes, OHLCV only | `market_data/cache`, `scratch/dataset_manifests.json` |
| Live capital | `$0.00`, order submission disabled, firewall fail-closed | `capital_barrier.py`, architecture manifest, discovery report |
| Audit ledger | 487 records, **SHA-256 chain verified intact** | `AuditLogger().verify_ledger_integrity() == True` |

**Reported numbers in the repository do not agree with each other:** README badge `556`, forensic inventory
`586`, actual `593`.

---

## 3. Findings

Severity reflects risk to capital, evidence integrity, or truthful reporting. Full evidence paths and
required actions are in the companion JSON.

### CRITICAL

**F-01 — Contradictory evidence for one strategy ID.**
`PAPER_TRADING_SIMULATION_AUDIT.json` (2026-09-15, window 2024-01-01 → 2026-09-01) reports 365 trades,
70.14% win rate, PF 5.24, +222.92R, equity 1,000 → 3,783.17, status `FORWARD_HEALTHY`.
`HTF_TREND_CONTINUATION_V1.json` (re-evaluated 2026-09-17, DEV 2021–2022) reports 14 trades, **0 wins**,
−0.9066R expectancy, Sharpe −10.26, bootstrap P(edge>0) = 0.0%, and explicitly lists
`DIM_10_EXECUTION_REALISM: Strategy has not completed Paper/Shadow validation`.
No reconciliation artifact exists. Both are cited inside the same repository as evidence.

**F-02 — Corrupted forward telemetry store.**
`research/results/telemetry/forward_execution_telemetry.jsonl`: 2,302 records, 1,074 unique `trade_id`,
maximum repetition 20 → **53% duplicates**. The platform's own earlier audit already recorded
`contamination_detected: true`, `verdict: FAIL_INTERRUPTED_AND_CONTAMINATED`. The simulation audit's
`total_trades` (365) equals the duplicate count reported for that store, and its first sample `trade_id`
(`POS_FAM-07-MTFCONT_SOLUSDT_Set2_1704110400`) is the first row of the contaminated store. Any realized
expectancy, win rate, profit factor or equity curve derived from this store is inadmissible.

**F-03 — Telemetry isolation is fail-open and uncommitted.**
`ExecutionTelemetryLogger.__init__` defaults `log_dir` to `research/results/telemetry` — the forward
directory — when no argument is given. `forward_paper_daemon.py:139` calls it with no argument. The only
isolation guard is an **uncommitted** working-tree change in `paper_execution_harness.py`. No record carries
an environment, run or session tag (0 of 2,302). One forgotten argument reproduces F-02.

**F-04 — Lifecycle state is asserted by literal default.**
`create_fam07_spec()` defaults `lifecycle_state = QUALIFIED_ROBUST`; the paper harness, the forward daemon
and the burn-in runner all rely on that default and carry the literal note
`"Primary robust research candidate (+107.41R aggregate, 100% stress pass)"`. Separately,
`web_app/api_server.py:71-74` registers three strategies directly as `HISTORICAL_ROBUST` at import time, and
`register_strategy()` (`promotion_governor.py:185`) accepts any `initial_state` with **no proof check**. The
governor's headline invariant — "no manual bypass permitted under any circumstances" — is therefore false in
the platform's own code paths.

**F-05 — Promotion Governor is not wired to capital.**
The only non-test consumers are `web_app/api_server.py` (display) and `simulation/full_system_simulator.py`.
`production/decision_record_engine.py`, `production/paper_execution_harness.py`,
`production/forward_paper_daemon.py` and `portfolio_engine/capital_allocator.py` never consult it. A strategy
with no promotion record at all can reach sizing. The nine-verdict lifecycle currently has no veto power.
### HIGH

**F-06 — The 17 "release gates" are file-existence checks.**
Every gate in `production/release_gates_auditor.py` reduces to `Path.exists()`. `GATE-03 "Tests Pass"` passes
if `tests/TEST_REGISTRY.json` exists. `GATE-07 "Telemetry Isolated"` passes despite F-02. `GATE-08 "Restart
Recovery Verified"` passes while the daemon is dead and unsupervised. The artifact
`research/results/QCP_SYSTEM_BUILD_COMPLETE_AUDIT.md` therefore certifies **architecture presence**, and its
`final_certified_state: BUILD COMPLETE` / `17 / 17` wording is not a correctness or economic certification.

**F-07 — Test registry declares coverage that does not exist.**
`tests/TEST_REGISTRY.json` declares 16 categories; **14 of them do not exist on disk**
(`contract, property, simulation, replay, failure_injection, latency, data_corruption, restart_recovery,
duplicate_events, reconciliation, risk_firewall, security_rbac, multi_tenant, end_to_end`). Only `unit` and
`integration` are real. Statements such as "100% test registry mapped" and "586/586 passing" were not
supported by the repository state.

**F-08 — Seven of ten "research universe" assets have no data.**
`ASSET_UNIVERSE_REGISTRY.json` reports `research_universe_count: 10`, but BNB, XRP, ADA, DOGE, AVAX, LINK
and LTC each carry `data_quality_certified: false` alongside `research_eligibility: true`, and no warehouse
dataset exists for them. `evaluate_eligibility()` never inspects data availability, and **no registered asset
has ever been rejected** — the hurdle has never demonstrated discrimination. All ranking, volume, depth,
venue and spread inputs are literals (`HARDCODED_UNSOURCED`), which contradicts the platform's own provenance
taxonomy.

**F-09 — Evidence artifacts are overwritten in place.**
`research/results/HTF_TREND_CONTINUATION_V1.json` (tracked) has had `code_commit` and
`evaluation_timestamp_utc` rewritten in place rather than producing a new versioned artifact.
`DAILY_DECISION_RECORD.json` is opened with `mode="w"` (overwrite). The working tree simultaneously modifies
`CERTIFIED_RESEARCH_UNIVERSE.json`, `QCP_ALPHA_DISCOVERY_REPORT.{json,md}`, `research_vault.db` and
`scratch/dataset_manifests.json`. The dataset manifests were re-stamped with new `download_timestamp_utc`
values while `sha256` stayed identical — content is unchanged, but lineage metadata moved, so a reader cannot
tell "re-derived identically" from "rewritten".

**F-10 — Forward-paper infrastructure is not durable.**
No forward paper process is running. `paper_daemon_state.json` last saved **2026-09-16T13:54:34Z** (last
heartbeat 13:54:17Z) — stopped for over 20 hours. There is **no systemd unit, supervisor, container runtime
or healthcheck** anywhere in the repository. Measured state: equity 985.5759 (from 1,000), 2 closed trades,
3 recorded data gaps, realized expectancy −1.202R. Two closed trades cannot support any validation claim,
and the observation window currently restarts at the operator's discretion.

**F-11 — Governance ledger is chained but semantically contaminated.**
`platform_audit_ledger.jsonl` holds 487 hash-chained records and the chain verifies intact. However it mixes
**test-generated** identities — `FAM-07-TEST` (60), `FAM-TEST-ALPHA` (51), `FAM-FAIL-ALPHA` (48),
`FAM-SHORTCUT` (34), `FAM-WINDFALL-FAIL` (34), `FAM-ILLEGAL-SHORTCUT` (6) — with real research events, and
**0 of 487 records carry any environment/run context**. Tamper-evidence works; provenance does not.

**F-12 — The decision hierarchy is not as documented.**
The docstring of `decision_record_engine.py` lists a 10-level hierarchy whose Level 3 is
*"Is there qualified alpha? (Verified against Canonical Registry)"*. The implementation flows from Level 2
straight into the net-edge gate using **caller-supplied** `gross_alpha_r` (default `0.22`), `entry_price`
(default `100.0`) and `sl_price` (default `95.0`), with no `EvidenceRecord` or `ProvenanceClass` assertion
anywhere. The `TRADE` / `+0.243R` verdict currently in `DAILY_DECISION_RECORD.json` was produced by a
non-live caller. `platform_core/evidence_provenance.py` was written to prevent exactly this, and is not
enforced on the path that matters.

### MEDIUM

**F-13 — Prior inventory is stale and misclassifies artifacts.** It catalogues 1,226 entries against 1,234
files; 9 newer files are uncatalogued (including `ASSET_UNIVERSE_REGISTRY.json`,
`RELATIVE_VALUE_COINTEGRATION_AUDIT.{json,md}`, `platform_core/asset_universe_registry.py`,
`docs/ECONOMIC_PURPOSE_SPECIFICATION.md`); and 5 **untracked** artifacts are labelled `VERIFIED_M2` although
they exist in no commit (`QCP_SYSTEM_BUILD_COMPLETE_AUDIT.{json,md}`, `STRATEGY_GRAVEYARD.json`,
`FORENSIC_BLOCKS_MASTER_AUDIT.json`, `telemetry/simulations/forward_execution_telemetry.jsonl`).

**F-14 — Data lineage is incomplete.** Manifests live in `scratch/dataset_manifests.json`, not under
`market_data/`; 15 of 24 warehouse files are untracked; coverage is OHLCV-only for three assets; the 1m
dataset spans only 2026-07-30 → 2026-09-03. Funding, open interest, liquidations, order-book depth and
cross-venue feeds are *missing and explicitly marked blocked* — compliant behaviour, but it means
microstructure relative value, funding, market making and cross-venue families cannot be certified on
current data.

**F-15 — Registry claims contradict evidence.** `CAPABILITY_REGISTRY.json` reports `DIRECTIONAL:
FORWARD_VALIDATED` and `RELATIVE_VALUE: HISTORICALLY_VALIDATED (+0.06R sub-threshold edge)`; `README.md`
reports **0 validated alpha strategies**; and the new `RELATIVE_VALUE_COINTEGRATION_AUDIT.md` reports FAM-09
**6/6 FALSIFIED** with a permanent capital ban.
---

## 4. File classification (Directive §REPOSITORY SAFETY)

The prior inventory's category counts are largely **reasonable** and its per-file records are real
(1,226 entries with `sha256`, line and byte counts). Two corrections are required:

| Governance category | Prior count | Audit position |
| :--- | :--- | :--- |
| `VERIFIED_M2` | 857 | Acceptable **except** 5 entries that exist in no commit and must be reclassified as `UNVERSIONED_ARTIFACT`: `QCP_SYSTEM_BUILD_COMPLETE_AUDIT.{json,md}`, `STRATEGY_GRAVEYARD.json`, `FORENSIC_BLOCKS_MASTER_AUDIT.json`, `telemetry/simulations/forward_execution_telemetry.jsonl`. |
| `USEFUL_NEW_ARCHITECTURE` | 39 | Acceptable. These are the genuinely new, tested modules (foundation, execution OS, venues, registry, promotion governor, lifecycle, hedging, risk budget allocator, release auditor, comprehensive tests). They are **unvalidated economically** and **uncommitted**, which must be stated wherever they are described. |
| `EXPERIMENTAL` | 4 | Acceptable (`options_pricer`, `avellaneda_stoikov`, `full_system_simulator`, derivatives/MM test). Quarantine from any capital or claim pathway. |
| `OUT_OF_SCOPE_FOR_CURRENT_MILESTONE` | 7 | Acceptable (`billing`, `multi_tenancy`, `observability`, `security`, `disaster_recovery`, `web_app`). Support systems only; the web UI additionally carries F-04's fiat promotion seeding and must not display unvalidated strategies as robust. |
| `DUPLICATE` | 0 | Accepted. |
| `BROKEN` | 0 | Accepted for syntax/behaviour: 593/593 tests pass. Note that "not broken" ≠ "validated". |
| `UNKNOWN` | 319 | Mostly `scratch/` diagnostics. Acceptable, but 9 files created after the inventory ran are **not catalogued at all** (F-13). |

**No file was deleted, moved or quarantined by this audit.** Quarantine is recorded as instructions (§6), not
as filesystem mutation, so that the directive's "never rewrite historical evidence" rule is respected.

---

## 5. Verified strengths (must not be destroyed)

**P-01 — Tests.** 593/593 pass deterministically in 98.97s; M2 baseline `7d96b77` remains an ancestor of HEAD.

**P-02 — FAM-09 relative value research is genuinely well executed.** `research/discovery_lab/relative_value_engine.py`
implements a causal rolling OLS hedge ratio using a strictly past window (`log_a[i-w:i]`), point-in-time
z-scores, previous-bar signal timing (`sig_idx = i - 1 - latency_bars`), adverse-first simulation, decomposed
two-leg friction (32 bps baseline / 64 bps stress), and DEV/VAL/OOS chronological partitions with a
conservative verdict rule (falsify only when *both* Engle-Granger and Johansen fail, or OOS ≤ 0, or
expectancy < 0.10R). Six of six configurations were falsified **and recorded as falsified** in
`STRATEGY_GRAVEYARD.json` with permanent capital bans, including the one configuration whose OOS was *positive*
(+1.83R on SOL/BTC 1d) — the platform correctly refused to keep it. This is the directive's loop working as intended.

**P-03 — Capital firewall.** `$0.00` live capital, paper-only order submission, a real `CapitalBarrier` module
with tiered evaluation; no live credentials or live order paths found.

**P-04 — Small-account safety.** `CapitalFeasibilityEngine` + `NetEdgeEngine` exist and gate the decision path;
`$100` is reported as `DISTORTED (~5.7x)` and refused, and the engine is designed to answer
`NO_TRADE / INSUFFICIENT CAPITAL` rather than manufacture an opportunity. Tests cover this.

**P-05 — Tamper-evidence mechanics.** The SHA-256 hash-chained audit ledger verifies intact from genesis to
head.

**P-06 — Evidence provenance taxonomy.** `ProvenanceClass` distinguishes measured-certified data from
model-derived, synthetic and hardcoded values; `REQUIRED_ECONOMIC_METRICS` and the promotion gate are a sound
design. The defect is enforcement (F-05, F-12), not design.
---

## 6. Quarantine decisions issued by this audit

These are recorded instructions; they are deliberately **not** applied as filesystem mutations.

| # | Subject | Quarantine action | Evidence preservation |
| :--- | :--- | :--- | :--- |
| Q1 | `FAM-07-MTFCONT_SOLUSDT_Set2` | Move to `UNTESTED`. Block any `TRADE` verdict, any allocation, and any `FORWARD_VALIDATED`/`HISTORICAL_ROBUST` label until re-derived (S2). | All existing artifacts left untouched; both contradictory measurements remain on disk. |
| Q2 | `PAPER_TRADING_SIMULATION_AUDIT.json` headline metrics | Re-label `NON_EVIDENCE_CONTAMINATED_SOURCE`. Not to be cited in any future claim, UI, or registry. | File unchanged; the label is recorded in this audit and the findings JSON. |
| Q3 | `research/results/telemetry/forward_execution_telemetry.jsonl` | Read-only quarantine + contamination manifest + session boundary; new forward records must be environment-tagged in a separated stream. | Append-only: the 2,302 historical rows are **never rewritten**. |
| Q4 | Asset universe `research_eligibility` | Require certified data. Result: `CERTIFIED_RESEARCH = 3` (BTC, ETH, SOL) and `METADATA_CANDIDATE = 7`. | Registry regenerated from data-derived membership, not literals. |
| Q5 | "BUILD COMPLETE" / "17 / 17 gates" wording | Re-label as `ARCHITECTURE_PRESENCE_CHECK`, explicitly not software, economic, production or commercial certification. | Artifacts kept for the record; wording corrected on next regeneration. |
| Q6 | `platform_audit_ledger.jsonl` | Keep chain integrity; tag all future events with `environment` and `run_id`; route test/simulation events to a separate ledger. | Existing 487 records untouched. |

---

## 7. Remediation sequence (bounded vertical slices)

Ordered so that safety and evidence integrity are repaired before any capability expansion. Each slice ends
with tests, an audit record, and a commit.

| Slice | Objective | Definition of done |
| :--- | :--- | :--- |
| **S1** | Telemetry isolation hardening + contamination quarantine record + session boundary | Default logger path is fail-closed; forward use is explicit opt-in; every record carries `environment` + `session_id`; quarantine manifest committed; 593/593 still pass |
| **S2** | Reconcile FAM-07 evidence from a de-duplicated, provenance-tagged store | A single immutable evidence artifact states the strategy's verdict with dataset hashes, partition, friction and duplicate-free trade count |
| **S3** | Wire the Promotion Governor into the capital path; remove fiat defaults | `create_fam07_spec` defaults to `RESEARCH`; web UI seeds nothing as robust; pre-trade check fails closed without a promotion proof |
| **S4** | Make the asset universe honest and reconcile registry claims | `ASSET_UNIVERSE_REGISTRY` = 3 certified / 7 candidates with provenance; `CAPABILITY_REGISTRY` demoted to match verdict artifacts |
| **S5** | Rebuild release gates as executable assertions | Gates run tests, verify dataset hashes, assert telemetry isolation by test, assert supervisor liveness |
| **S6** | Test registry ↔ reality | Registry generated from collection output; missing categories implemented or removed |
| **S7** | Write-once evidence artifact policy | Each evaluation writes a new hash-named artifact plus an append-only index; overwriting is prohibited by test |
| **S8** | Supervised 24/7 operation | Service unit + restart policy + liveness probe + clock validation + safe shutdown/resume, demonstrated by a kill-and-recover test |
| **S9** | Lineage relocation, artifact pinning, objective universe expansion | Lineage under `market_data/`, artifacts pinned, 10-asset expansion driven by a measured ranking with survivorship controls |

**Not authorised by this audit:** enabling live capital, promoting any strategy, claiming profitability,
or expanding the feature surface before S1–S3 are complete.

---

## 8. Limits of this audit (stated explicitly)

1. **Scope.** This is a repository-state audit plus targeted code/evidence inspection. It is **not** a
   re-execution of every backtest, and it is **not** an independent replication of any economic claim.
2. **Economic correctness.** The audit determines that *no* claim currently survives admissible evidence. It
   does not establish that any mechanism is permanently absent — only that the current artifacts do not
   support the claims attached to them.
3. **The F-01 contradiction is unresolved by design.** This audit does not choose between +278% and −0.9R; it
   establishes that both cannot be true and that no reconciliation exists. Resolution is slice S2.
4. **Tooling note.** Mid-audit the interactive shell session became unresponsive. All figures reported here
   were obtained from commands that completed and returned output before that point; the findings JSON was
   completed afterwards and verified by structural inspection (line-by-line read of the whole file) and by
   spot-checking the joins between sections, but a `python -m json.tool` parse and the S1 test run must be
   re-executed when the terminal is available. This limitation is recorded rather than glossed over.
5. **Classification status of this audit's own outputs:**
   `ARCHITECTURE:PASS (architecture presence)`, `SOFTWARE:593/593 PASS`,
   `ECONOMIC:NO VALIDATED EDGE`, `OOS:0 surviving`, `FORWARD:COMPROMISED (F-02/F-10)`,
   `PRODUCTION:BLOCKED`, `COMMERCIAL:BLOCKED`.