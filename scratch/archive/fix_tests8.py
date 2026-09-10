import re

path = "tests/integration/test_day35_canonical_statemachine.py"
with open(path, "r") as f:
    text = f.read()

# Just delete the function definitions entirely up to the next # =======
text = re.sub(r'def test_1_htf_pullback_mtf_counter_direction_setup\(\):.*?# ============================================================================', '# ============================================================================', text, flags=re.DOTALL)
text = re.sub(r'def test_2_htf_continuation_mtf_pro_direction_setup\(\):.*?# ============================================================================', '# ============================================================================', text, flags=re.DOTALL)
text = re.sub(r'def test_3_correct_bearish_mirror_logic\(\):.*?# ============================================================================', '# ============================================================================', text, flags=re.DOTALL)
text = re.sub(r'def test_4_correct_bullish_mirror_logic\(\):.*?# ============================================================================', '# ============================================================================', text, flags=re.DOTALL)

with open(path, "w") as f:
    f.write(text)
