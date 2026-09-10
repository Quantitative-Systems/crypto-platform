import os
import re

def process_file(filepath):
    with open(filepath, 'r') as f:
        content = f.read()

    # Imports
    content = content.replace("from strategy_engine.hypotheses.pullback_riding import PullbackRidingHypothesis", "from strategy_engine.hypotheses.unified_strategy import UnifiedStrategy")
    content = content.replace("from strategy_engine.hypotheses.continuation_riding import ContinuationRidingHypothesis", "from strategy_engine.hypotheses.unified_strategy import UnifiedStrategy")
    
    # Class names
    content = content.replace("PullbackRidingHypothesis", "UnifiedStrategy")
    content = content.replace("ContinuationRidingHypothesis", "UnifiedStrategy")

    # Hypothesis IDs
    content = content.replace('"HYP_A_PULLBACK_RIDING"', '"UNIFIED_STRATEGY"')
    content = content.replace('"HYP_B_CONTINUATION_RIDING"', '"UNIFIED_STRATEGY"')

    # Fix loops that test both, we only need to test UnifiedStrategy once
    # For example: for HypClass, hyp_id in [(PullbackRidingHypothesis, "HYP_A_PULLBACK_RIDING"), (ContinuationRidingHypothesis, "HYP_B_CONTINUATION_RIDING")]:
    content = content.replace('for HypClass, hyp_id in [(UnifiedStrategy, "UNIFIED_STRATEGY"), (UnifiedStrategy, "UNIFIED_STRATEGY")]:', 'for HypClass, hyp_id in [(UnifiedStrategy, "UNIFIED_STRATEGY")]:')
    
    # Write back
    with open(filepath, 'w') as f:
        f.write(content)

process_file("tests/integration/test_canonical_conformance.py")
process_file("tests/integration/test_day35_canonical_statemachine.py")
process_file("scratch/compute_gate2_forensics.py")
process_file("scratch/run_funnel_diagnostic.py")
print("Done refactoring tests.")
