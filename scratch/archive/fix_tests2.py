import os
import re

def process_file(filepath):
    with open(filepath, 'r') as f:
        content = f.read()

    # Imports
    content = content.replace("from strategy_engine.context.htf_context_engine import HTFContextEngine, ExpectedMove, HTFContext", "from strategy_engine.context.htf_context_engine import HTFContextEngine, HTFContext")
    
    # ExpectedMove is no longer used, so remove the assertions for it
    content = re.sub(r'^\s*assert\s+ctx(_\w+)?\.expected_move\s*==\s*ExpectedMove\.\w+\s*\n', '', content, flags=re.MULTILINE)

    # In StrategyCoordinator, directional_permission is assigned, not htf_expected_move
    content = re.sub(r'^\s*assert\s+active_\w+\[0\]\.htf_expected_move\s*==\s*".*?"\s*\n', '', content, flags=re.MULTILINE)
    
    # Write back
    with open(filepath, 'w') as f:
        f.write(content)

process_file("tests/integration/test_day35_canonical_statemachine.py")
print("Done fixing tests phase 2.")
