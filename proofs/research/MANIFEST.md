# Proofs / Research — Evidence Manifest

Evidence artifacts moved out of the former `scratch/` directory during the
Architecture V2 reorganization (2026-09-19). The research lab's test
records in `hypotheses/` reference these files by their ORIGINAL path
(`scratch/<name>`); provenance is preserved — this manifest maps each
original path to its current location.

Rule: results JSONs matching canonical/EXP/milestone/composite/breakeven/
certified patterns were classified as research EVIDENCE. All remaining
scratch content (analysis scripts, non-canonical results) was archived
wholesale to `archive/migration/scratch/` — nothing was deleted.

| original path | current path |
|---|---|
| `scratch/canonical_h0_dev_results.json` | `proofs/research/canonical_h0_dev_results.json` |
| `scratch/canonical_profit_lock_0.5r_0.25r_dev_results.json` | `proofs/research/canonical_profit_lock_0.5r_0.25r_dev_results.json` |
| `scratch/canonical_h_mom_01_dev_results.json` | `proofs/research/canonical_h_mom_01_dev_results.json` |
| `scratch/milestone_2_5r_dev_results.json` | `proofs/research/milestone_2_5r_dev_results.json` |
| `scratch/composite_01_dev_results_repaired_terminal.json` | `proofs/research/composite_01_dev_results_repaired_terminal.json` |
| `scratch/exp_base_tgtstruct_legacy_stop_01_dev_results.json` | `proofs/research/exp_base_tgtstruct_legacy_stop_01_dev_results.json` |
| `scratch/breakeven_1r_dev_results.json` | `proofs/research/breakeven_1r_dev_results.json` |
| `scratch/<canonical*|exp_*|milestone_*|composite_*|breakeven_*|*certified*|*summary*|anchor2_*>.json` (61 files) | `proofs/research/<same name>` |
| `CANONICAL_STRATEGY_CONFORMANCE_AUDIT.md` (repo root) | `proofs/research/CANONICAL_STRATEGY_CONFORMANCE_AUDIT.md` |
| `FORENSIC_FAILURE_ANALYSIS.md` (repo root) | `proofs/research/FORENSIC_FAILURE_ANALYSIS.md` |
| `RESEARCH_INTEGRITY_AUDIT.md` (repo root) | `proofs/research/RESEARCH_INTEGRITY_AUDIT.md` |

Directory roles:
- `research/` — research experiment evidence (results, ledgers, audits)
- `tests/` — test-run evidence tied to hypothesis tests
- `deployments/` — deployment/qualification evidence (empty; no strategy
  has qualified)
- `work/` — working evidence: terminal captures, tuning, validation runs
- `failures/` — failure post-mortems and negative-result supporting files
