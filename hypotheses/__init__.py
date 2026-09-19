"""
hypotheses — QCP Hypothesis Research Registry + Research Laboratory package.

Two governance layers live here:

1. Registry (ID governance, permanent, never removed):
       from hypotheses.hypothesis_governance import HypothesisRegistry
       registry = HypothesisRegistry()

2. Research laboratory (hypothesis -> research -> candidates -> tests ->
   results lifecycle, promotion gates, indexes):
       from hypotheses.governance import create_hypothesis, ...
       from hypotheses.verify_lab import verify_lab

Hierarchy: HYPOTHESIS -> RESEARCH -> CANDIDATES -> TESTS -> RESULTS/EVIDENCE.
Positive Development evidence never auto-promotes a candidate to
VALIDATION_CANDIDATE / VALIDATED / capital eligibility.
"""
__version__ = "1.0.0"

