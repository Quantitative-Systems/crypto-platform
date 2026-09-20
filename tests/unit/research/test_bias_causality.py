import pandas as pd
import numpy as np
import pytest

from research.bias_families import CanonicalSupertrendStochasticBias, TrendMAAlignmentBias, StructHHHLBias, MomRSIRegimeBias
from research.grammar_components import AbstractBias

def generate_mock_data(size=200):
    np.random.seed(42)
    close = pd.Series(100 + np.random.randn(size).cumsum())
    high = close + np.random.rand(size) * 2
    low = close - np.random.rand(size) * 2
    open_ = close.shift(1).fillna(100)
    
    df = pd.DataFrame({
        "open": open_,
        "high": high,
        "low": low,
        "close": close,
        "volume": np.random.randint(100, 1000, size)
    })
    return df

@pytest.mark.parametrize("bias_component", [
    CanonicalSupertrendStochasticBias(),
    TrendMAAlignmentBias(),
    StructHHHLBias(),
    MomRSIRegimeBias(),
])
def test_bias_causality(bias_component: AbstractBias):
    """
    Ensure that changing future data does not affect past evaluations.
    """
    df_original = generate_mock_data(200)
    df_modified = df_original.copy()
    
    # Modify data after index 100
    df_modified.loc[101:, "close"] = df_modified.loc[101:, "close"] * 1.5
    df_modified.loc[101:, "high"] = df_modified.loc[101:, "high"] * 1.5
    
    # Evaluate both
    bull1, bear1 = bias_component.evaluate(df_original, scale=1)
    bull2, bear2 = bias_component.evaluate(df_modified, scale=1)
    
    # The output up to index 100 must be identical
    pd.testing.assert_series_equal(bull1.loc[:100], bull2.loc[:100], check_names=False)
    pd.testing.assert_series_equal(bear1.loc[:100], bear2.loc[:100], check_names=False)

