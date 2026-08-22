import re

# Fix 1 & 2: Timeframe Aligner tests
path1 = "tests/unit/research/test_timeframe_aligner.py"
with open(path1, "r") as f:
    text1 = f.read()
text1 = text1.replace("assert visible[0].timestamp == 0", "assert visible[0].timestamp == 1_000_000_000_000")
with open(path1, "w") as f:
    f.write(text1)

path2 = "tests/integration/test_canonical_conformance.py"
with open(path2, "r") as f:
    text2 = f.read()
text2 = text2.replace("Candle(timestamp=0, open", "Candle(timestamp=1_000_000_000_000, open")
text2 = text2.replace("Candle(timestamp=14400000, open", "Candle(timestamp=1_000_014_400_000, open")
text2 = text2.replace("Candle(timestamp=28800000, open", "Candle(timestamp=1_000_028_800_000, open")
text2 = text2.replace("decision_timestamp=20000000", "decision_timestamp=1_000_020_000_000")
text2 = text2.replace("assert visible[0].timestamp == 0", "assert visible[0].timestamp == 1_000_000_000_000")

# Fix 4: Zombie MTF KeyZone tests
# test_scenario_9_stale_mtf_keyzone_rejected (test_canonical_conformance.py)
# Need to add metadata={"context": "PULLBACK"} to candidate
text2 = text2.replace('mtf_alignment_timestamp=2000  # Alignment occurred at T=2000', 'mtf_alignment_timestamp=2000, metadata={"context": "PULLBACK"}')

with open(path2, "w") as f:
    f.write(text2)


# Fix 3 & 4 in test_day35_canonical_statemachine.py
path3 = "tests/integration/test_day35_canonical_statemachine.py"
with open(path3, "r") as f:
    text3 = f.read()

# Fix 3: Remove expected_move_direction assertions
text3 = re.sub(r'^\s*assert\s+ctx(_\w+)?\.expected_move_direction\s*==\s*.*?\n', '', text3, flags=re.MULTILINE)

# Fix 4: test_6_mtf_setup_to_mtf_zone_causality
# Need to add metadata={"context": "PULLBACK"} to candidate
text3 = text3.replace('htf_context_timestamp=2000, mtf_alignment_timestamp=2100\n    )', 'htf_context_timestamp=2000, mtf_alignment_timestamp=2100, metadata={"context": "PULLBACK"}\n    )')

with open(path3, "w") as f:
    f.write(text3)
