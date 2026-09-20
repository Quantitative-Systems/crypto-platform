# Repository Reorganization Plan — Architecture V2

Date: 2026-09-19 · Commit base: a742bc3 (v0.5.0) · Scope: platform-wide
consolidation. No strategy logic changes. No new research. H-FRACTAL-01
remains registered-but-locked.

## 1. Current architecture (forensic inventory)

| Top-level | Purpose (verified by imports/git) | Class | Destination |
|---|---|---|---|
| `platform_core/` | runtime core (registries, genome, provenance) | RUNTIME | keep |
| `market_intelligence/` | regime/structure/liquidity engines | RUNTIME | keep |
| `market_data/` | ingestion, certification, warehouse | RUNTIME | keep |
| `portfolio_engine/` | portfolio construction | RUNTIME | keep |
| `risk_engine/` | risk coordination, sizing, validators | RUNTIME | keep |
| `trade_management/` | lifecycle + trailing mgmt | RUNTIME | keep |
| `config/` | assets, timeframe sets | RUNTIME | keep |
| `backtesting/` | replay/friction/analytics engine (imported by research + production) | RUNTIME | keep |
| `simulation/` | full-system simulator | RUNTIME | keep |
| `capital_intelligence/` | capital feasibility/execution capacity | RUNTIME | keep |
| `production/` | live/paper deployment, qualification gates, reconciliation | RUNTIME (DEPLOY/LIVE) | keep |
| `strategy/` | canonical HTF/MTF/LTF strategy source (imported by config, trade_management, backtesting) | RUNTIME | keep |
| `strategy_engine/` | canonical research signal engine (imported by production + risk_engine) | RUNTIME | keep |
| `strategy_candidate/` | candidate harness (imported by production/paper_execution_harness + research) | RUNTIME/RESEARCH | keep (active) |
| `strategy_candidate_v2/` | v2 candidate engine; core (`data_audit`, `fast_indicators`, `run_backtest`, runners) imported by research + production; 12 debug fixture/test files dead | MIXED | keep core; archive debug files |
| `research/` | research execution infrastructure (discovery_lab, experiments, lifecycle, results, engines) | RESEARCH-ENGINE | keep |
| `hypotheses/` | OLD hypothesis registry (governance, registry.yaml, active/H-FRACTAL-01) | RESEARCH | merge into new lab root |
| `qcp/` | v2 research lab wrapper (governance code + 6 hypotheses) | RESEARCH | migrate to `hypotheses/`, remove wrapper |
| `scratch/` | 326 files: audit/analysis scripts + experiment results | EVIDENCE/SCRATCH | canonical results → `proofs/research/`; rest → `archive/migration/scratch/` (dir now runtime-only, gitignored) |
| `tests/` | test suite (unit, integration, comprehensive + 4 loose root tests) | TESTING | keep; consolidate loose tests into `tests/unit/` |
| `docs/` | research docs, audits, registries | DOCS | keep; absorb root docs |

Root loose files classified:
- `CANONICAL_STRATEGY_CONFORMANCE_AUDIT.md`, `FORENSIC_FAILURE_ANALYSIS.md`,
  `RESEARCH_INTEGRITY_AUDIT.md` → `proofs/research/` (audit evidence)
- `CAPABILITY_REGISTRY.json` → **kept at repository root** (runtime input:
  read by `production/autonomous_platform_orchestrator.py` and rewritten on
  orchestrator runs; NOT a static evidence artifact)
- `walkthrough.md` → `docs/`
- `output.txt` → `archive/migration/` (unreferenced terminal dump)
- `debug_funding{,2,3,4}.py`, `fetch_funding_data.py`, `patch_grammar.py`,
  `update_grammar.py`, `test_df_times.py`, `test_funding.py`,
  `test_keys.py`, `test_ma.py`, `test_raw.py` →
  `archive/obsolete_implementations/root_scripts/` (one-off debug scripts,
  no imports reference them)
- `production_live_state.db` → keep (live operation state, referenced by
  `production/run_live_24_7.py`)
- Legacy `risk/` (single `risk_engine.py`, superseded by `risk_engine/`) →
  `archive/legacy/risk/`

## 2. Target architecture

```
crypto-platform/
├── platform_core/  market_intelligence/  portfolio_engine/  risk_engine/
├── trade_management/  market_data/  config/  backtesting/  simulation/
├── capital_intelligence/  strategy/  strategy_engine/
├── strategy_candidate/  strategy_candidate_v2/   # active runtime/research harnesses
├── production/                                    # deploy + live operation
├── research/                                      # research execution engine
├── hypotheses/      ← SINGLE discovery/research lab (was qcp/hypotheses + old registry)
├── tests/           ← shared testing infrastructure
├── deployed_strategies/  ← qualified strategy vault (empty until qualification)
├── proofs/          ← evidence vault (research/tests/deployments/work/failures)
├── bin/             ← operational tooling
├── archive/         ← legacy, obsolete, migration snapshots
├── docs/
└── project files (README, LICENSE, SECURITY, CONTRIBUTING, pyproject.toml,
                    CHANGELOG, requirements.txt)
```

Consolidation, not multiplication: every existing top-level runtime dir is
retained because it provides a distinct runtime responsibility verified by
live imports. No new platform folders invented.

## 3. Migration operations

### 3.1 Research lab unification (`qcp/` → `hypotheses/`)
- `git mv qcp/hypotheses/*` (6 hypothesis dirs, HYPOTHESES_LIST.md,
  CANDIDATES_LIST.md, README.md, MIGRATION_LOG.md, governance*.py,
  index_*.py, verify_lab.py, migrate_history.py, seed_fractal01.py,
  __init__.py) → `hypotheses/`
- Old-registry files retained alongside: `hypothesis_governance.py`,
  `registry.yaml`, `HYPOTHESIS_TEMPLATE.md` (registry vs lab lifecycle:
  different governance layers)
- Old `hypotheses/active/H-FRACTAL-01-cross-scale-mechanism-transfer/`
  (pre-lab registry hypothesis.md + status.yaml) → archived under
  `archive/migration/hypotheses_registry_active/`; its content is already
  represented by lab `hypotheses/H-FRACTAL-01/`
- `qcp/__init__.py` + `qcp/hypotheses/__init__.py` consolidated into a
  single `hypotheses/__init__.py`; `qcp/` removed
- Import updates: `tests/unit/research/test_qcp_lab_governance.py`
  `qcp.hypotheses.*` → `hypotheses.*`; `migrate_history.py` `__main__`
  invocation unchanged (relative imports)
- `LAB_ROOT` in `governance_core.py` resolves relative to the module file,
  so it automatically becomes `hypotheses/` — no code change needed
- pyproject package `include` list extended with the retained runtime
  packages

### 3.2 Evidence vault (`proofs/`)
- Create `proofs/{research,tests,deployments,work,failures}`
- Move canonical experiment result JSONs from `scratch/` →
  `proofs/research/` (canonical H0, profit lock, H_MOM, milestone 2.5R,
  composite 01, EXP_TARGET_STRUCTURAL, breakeven 1r, plus certified
  summary result JSONs)
- Root audit reports → `proofs/research/`
- Provenance: lab records store `original_path` at the ORIGINAL location —
  preserved by design; `proofs/research/MANIFEST.md` maps old → new path

### 3.3 Deployed strategy vault (`deployed_strategies/`)
- Create with `README.md` documenting admission requirements (full
  qualification chain: DEV → forensic review → VAL → OOS → qualification
  gate → deployment approval). NO strategies enter: no candidate has
  passed qualification; DEV ≠ winner enforced by governance.

### 3.4 Operational tooling (`bin/`)
- `bin/status`, `bin/test`, `bin/backtest`, `bin/research`, `bin/verify`,
  `bin/audit`, `bin/deploy` — thin Python executables delegating to
  existing entrypoints (production/cli_launcher, pytest, lab verifier).
  No research outputs inside bin/.

### 3.5 Archive
- `archive/legacy/risk/` ← old `risk/`
- `archive/obsolete_implementations/root_scripts/` ← root debug/one-off scripts
- `archive/obsolete_implementations/strategy_candidate_v2_debug/` ←
  debug_fixture*.py, debug_test_a.py, exit_test.py, fixture_test.py,
  smoke_test.py, test_*.py from v2 (verified unreferenced)
- `archive/migration/scratch/` ← all remaining `scratch/` content
  (analysis scripts, non-canonical results — preserved wholesale,
  nothing deleted)
- `archive/migration/hypotheses_registry_active/` ← old registry active dir
- Negative/rejected/invalidated research is NOT archived: it lives in
  hypothesis/candidate/test lineage inside `hypotheses/`

### 3.6 Tests
- Move loose root tests `tests/test_bias_causality.py`,
  `test_market_regime.py`, `test_regime_engine.py`,
  `test_structural_components.py` → `tests/unit/` (matches their content)
- Existing `unit/ integration/ comprehensive/` retained (no folder
  multiplication); `system/ backtests/ regression/ forensic/ fixtures/`
  NOT created until such tests exist

## 4. Deletion candidates (verified)
- `__pycache__/` dirs — untracked build artifacts, removable
- **Nothing else is deleted.** Policy: archive over delete. Duplicates
  were already removed in the prior phase (sha256-verified).

## 5. Dependency/import impact
- `qcp.hypotheses.*` imports → `hypotheses.*` (tests only; runtime code
  never imported qcp)
- `hypotheses` package init merge (old registry docstring + lab package)
- No other cross-package paths change (retained dirs keep their names)
- pytest testpaths unchanged (`tests`)

## 6. Verification plan
1. `import hypotheses` + lab verifier at new location → CLEAN
2. Structural governance test suite (13 tests) → pass
3. Broader collectible test suite smoke run
4. `grep -r 'import qcp'` → zero hits outside archive
5. Research provenance: every lab test's original_path resolvable
   (original, proofs, or archive location documented)
6. `git status` review: only expected moves; no unexplained deletions
7. Single commit: `refactor(repo): consolidate platform research and
   strategy architecture`
