import re

# 1. Fix test_canonical_refinements.py (the profit lock test intrabar collision)
path1 = "tests/unit/strategy_engine/test_canonical_refinements.py"
with open(path1, "r") as f:
    text1 = f.read()

# Replace low=104.0 with low=105.0 in Bar 2
text1 = text1.replace("low=104.0, close=111.0", "low=105.0, close=111.0")

with open(path1, "w") as f:
    f.write(text1)
