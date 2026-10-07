import pandas as pd
from typing import Dict, Tuple

class DrawdownController:
    """
    The Automated Strategy Retirement Engine.
    
    If a strategy enters a drawdown that exceeds historical norms or an absolute
    risk threshold, it is automatically halted ("Retired").
    """
    
    def __init__(self, max_allowed_drawdown: float = 0.15):
        """
        :param max_allowed_drawdown: Absolute maximum peak-to-trough drawdown (e.g. 0.15 = 15%).
        """
        self.max_allowed_drawdown = max_allowed_drawdown
        
    def calculate_current_drawdown(self, equity_curve: pd.Series) -> float:
        """
        Calculates the current drawdown from the all-time high of the equity curve.
        """
        if len(equity_curve) == 0:
            return 0.0
            
        peak = equity_curve.cummax()
        drawdown = (equity_curve - peak) / peak
        
        # We only care about the most recent state for the kill switch
        current_dd = drawdown.iloc[-1]
        
        # Return as positive percentage (e.g., 0.10 means 10% drawdown)
        return abs(current_dd)

    def evaluate_strategies(self, equity_curves: Dict[str, pd.Series]) -> Tuple[list, list]:
        """
        Evaluates a portfolio of strategies and returns a list of strategies to keep
        and a list of strategies to halt.
        
        :returns: (active_strategies, halted_strategies)
        """
        active = []
        halted = []
        
        for strategy_id, eq_curve in equity_curves.items():
            current_dd = self.calculate_current_drawdown(eq_curve)
            
            if current_dd >= self.max_allowed_drawdown:
                # Halt immediately
                halted.append((strategy_id, current_dd))
            else:
                active.append(strategy_id)
                
        return active, halted
