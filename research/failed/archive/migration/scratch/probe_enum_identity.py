import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from market_intelligence.primitives import TrendDirection as PrimTrendDirection
from market_intelligence.structure_builder_engine import TrendDirection as StructTrendDirection
from market_intelligence.trend_engine import TrendDirection as TrendEngineTrendDirection

print(f"PrimTrendDirection: {PrimTrendDirection}")
print(f"StructTrendDirection: {StructTrendDirection}")
print(f"Are classes identical? {PrimTrendDirection is StructTrendDirection}")
print(f"Are enum members equal? {PrimTrendDirection.BULLISH == StructTrendDirection.BULLISH}")
print(f"PrimTrendDirection.BULLISH.value == StructTrendDirection.BULLISH.value? {PrimTrendDirection.BULLISH.value == StructTrendDirection.BULLISH.value}")
