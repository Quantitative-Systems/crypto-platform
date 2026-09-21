import pandas as pd
import numpy as np
from typing import Dict

class VolatilityTargeter:
    """
    Capital Allocation Engine based on Volatility Parity.
    
    Instead of assigning $10,000 to every strategy, we assign capital based
    on the underlying volatility of the asset and strategy, such that every
    strategy contributes an equal amount of risk to the portfolio.
    """
    
    def __init__(self, target_annualized_vol: float = 0.10, total_capital: float = 100000.0):
        """
        :param target_annualized_vol: 0.10 means we aim for a 10% annualized portfolio volatility.
        :param total_capital: Total AUM in base currency (e.g., USD).
        """
        self.target_annualized_vol = target_annualized_vol
        self.total_capital = total_capital
        self.TRADING_DAYS = 365.25 # Crypto is 24/7
        
    def calculate_position_size(self, daily_returns: pd.Series) -> float:
        """
        Calculates the optimal capital allocation for a strategy given its historical daily returns.
        
        Formula:
        Target Daily Volatility = Target Annual Volatility / sqrt(365)
        Strategy Daily Volatility = standard deviation of daily returns
        Leverage Scalar = Target Daily Vol / Strategy Daily Vol
        Allocated Capital = Total Capital * Leverage Scalar / N_strategies (simplified)
        """
        if len(daily_returns) < 30:
            # Need at least 30 days of data for stable vol estimate
            return 0.0
            
        strategy_daily_vol = daily_returns.std()
        
        if strategy_daily_vol == 0 or np.isnan(strategy_daily_vol):
            return 0.0
            
        target_daily_vol = self.target_annualized_vol / np.sqrt(self.TRADING_DAYS)
        
        # How much we need to scale this strategy to hit the target vol
        vol_scalar = target_daily_vol / strategy_daily_vol
        
        # Raw allocation (before dividing by number of strategies)
        raw_allocation = self.total_capital * vol_scalar
        
        # Max cap at 50% of total capital per strategy to prevent infinite leverage on low-vol assets
        return min(raw_allocation, self.total_capital * 0.5)

    def allocate_portfolio(self, strategy_returns: Dict[str, pd.Series]) -> Dict[str, float]:
        """
        Given a dictionary of strategy names -> daily returns, returns the $ allocation for each.
        """
        allocations = {}
        for strategy_id, returns in strategy_returns.items():
            allocations[strategy_id] = self.calculate_position_size(returns)
            
        # Normalize so sum doesn't exceed total capital (if we have many strategies)
        total_requested = sum(allocations.values())
        if total_requested > self.total_capital:
            scale_down = self.total_capital / total_requested
            for k in allocations:
                allocations[k] *= scale_down
                
        return allocations
