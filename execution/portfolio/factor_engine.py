"""Portfolio Factor Engine: Multi-Factor Exposure & Concentration Governor.

Decomposes trading positions into underlying financial risk factors:
1. CRYPTO_BETA: Systematic exposure to the crypto market (BTC beta, ETH beta, Alt beta)
2. USD_FACTOR: Exposure to the US Dollar (via quote leg USD/USDT/USDC)
3. GOLD_FACTOR: Exposure to physical Gold (via quote leg XAU)
4. FIAT_FX_FACTOR: Exposure to non-USD fiat currencies (EUR, GBP, JPY)
5. CONCENTRATION: Strict 1.0% single-asset ceiling; 3.0% gross portfolio heat limit

Risk Hierarchy (Strict Non-Negotiable Ceilings):
    CORE TRADE RISK <= 1.00% (Strict individual trade ceiling)
            ↓
    PORTFOLIO ALLOCATION MAY REDUCE IT (Haircuts, Volatility Pacing)
            ↓
    SINGLE BASE ASSET CEILING <= 1.00% (Max cumulative risk per base asset)
            ↓
    PORTFOLIO HEAT <= 3.00% (Max aggregate portfolio risk across all assets)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple

from instrument.asset_class import AssetClass
from instrument.instrument_contract import CryptoBaseInstrument, build_instrument


class RiskFactor(str, Enum):
    """Systematic risk factors driving instrument PnL."""
    CRYPTO_BETA = "CRYPTO_BETA"          # Aggregate crypto asset class exposure
    BTC_IDIOSYNCRATIC = "BTC_IDIO"       # Direct Bitcoin idiosyncratic factor
    ETH_IDIOSYNCRATIC = "ETH_IDIO"       # Direct Ethereum idiosyncratic factor
    USD_FACTOR = "USD_FACTOR"            # Long or Short US Dollar
    GOLD_FACTOR = "GOLD_FACTOR"          # Long or Short Gold (XAU)
    EUR_FACTOR = "EUR_FACTOR"            # Euro exposure
    LIQUIDITY_BETA = "LIQUIDITY_BETA"    # High-beta risk asset liquidity factor


# Empirical factor betas relative to Bitcoin
ASSET_CRYPTO_BETAS: Dict[str, float] = {
    "BTC": 1.00,
    "ETH": 1.25,
    "SOL": 1.65,
    "AVAX": 1.70,
    "LINK": 1.30,
    "DOGE": 1.80,
    "BNB": 0.90,
}


@dataclass(frozen=True)
class FactorDecomposition:
    """Factor loadings for a single position."""
    symbol: str
    direction: int                # +1 Long, -1 Short
    allocated_risk_pct: float     # 0.01 = 1.0% risk
    crypto_beta_exposure: float   # Net crypto market exposure
    usd_factor_exposure: float    # Positive = Long USD, Negative = Short USD
    gold_factor_exposure: float   # Positive = Long Gold, Negative = Short Gold
    fiat_fx_exposure: float       # Non-USD currency exposure


@dataclass
class PortfolioFactorState:
    """Aggregated portfolio-level factor exposures and capacity."""
    total_portfolio_heat_pct: float = 0.0      # Aggregate risk % (Max 3.0%)
    net_crypto_beta_pct: float = 0.0           # Net crypto market direction
    gross_crypto_beta_pct: float = 0.0
    net_usd_exposure_pct: float = 0.0          # Net USD currency direction
    net_gold_exposure_pct: float = 0.0         # Net gold exposure direction
    active_positions_count: int = 0
    asset_concentrations: Dict[str, float] = field(default_factory=dict)
    factor_loadings: List[FactorDecomposition] = field(default_factory=list)


class PortfolioFactorEngine:
    """Decomposes positions into risk factors and enforces institutional limits."""

    def __init__(
        self,
        max_total_portfolio_heat_pct: float = 0.03,  # 3.0% maximum aggregate risk
        max_single_trade_risk_pct: float = 0.01,     # 1.0% max per trade
        max_net_crypto_beta_pct: float = 0.035,      # 3.5% max net crypto directional beta
        max_net_usd_exposure_pct: float = 0.03,      # 3.0% max USD directional exposure
        max_net_gold_exposure_pct: float = 0.02,     # 2.0% max Gold factor exposure
        max_single_asset_risk_pct: float = 0.01,     # 1.0% strict ceiling on single base asset risk
    ):
        self.max_total_portfolio_heat_pct = max_total_portfolio_heat_pct
        self.max_single_trade_risk_pct = max_single_trade_risk_pct
        self.max_net_crypto_beta_pct = max_net_crypto_beta_pct
        self.max_net_usd_exposure_pct = max_net_usd_exposure_pct
        self.max_net_gold_exposure_pct = max_net_gold_exposure_pct
        self.max_single_asset_risk_pct = max_single_asset_risk_pct

    def decompose_position(
        self,
        instrument: CryptoBaseInstrument,
        direction: int,
        risk_pct: float,
    ) -> FactorDecomposition:
        """Decompose a position into its systematic factor exposures."""
        # 1. Crypto Beta
        base_beta = ASSET_CRYPTO_BETAS.get(instrument.base_asset, 1.30)
        crypto_beta_exp = direction * risk_pct * base_beta

        # 2. Currency / Commodity quote factor
        # Long Base/Quote -> Short Quote. Short Base/Quote -> Long Quote.
        usd_exp = 0.0
        gold_exp = 0.0
        fiat_exp = 0.0

        quote = instrument.quote_asset
        if quote in ("USD", "USDT", "USDC"):
            usd_exp = -direction * risk_pct
        elif quote == "XAU":
            gold_exp = -direction * risk_pct
        elif instrument.quote_class == AssetClass.FIAT:
            fiat_exp = -direction * risk_pct

        return FactorDecomposition(
            symbol=instrument.symbol,
            direction=direction,
            allocated_risk_pct=risk_pct,
            crypto_beta_exposure=crypto_beta_exp,
            usd_factor_exposure=usd_exp,
            gold_factor_exposure=gold_exp,
            fiat_fx_exposure=fiat_exp,
        )

    def calculate_portfolio_state(
        self,
        active_positions: List[Tuple[CryptoBaseInstrument, int, float]],
    ) -> PortfolioFactorState:
        """Aggregate all active positions into a portfolio factor state."""
        state = PortfolioFactorState()
        for inst, direction, risk_pct in active_positions:
            decomp = self.decompose_position(inst, direction, risk_pct)
            state.factor_loadings.append(decomp)
            state.total_portfolio_heat_pct += risk_pct
            state.net_crypto_beta_pct += decomp.crypto_beta_exposure
            state.gross_crypto_beta_pct += abs(decomp.crypto_beta_exposure)
            state.net_usd_exposure_pct += decomp.usd_factor_exposure
            state.net_gold_exposure_pct += decomp.gold_factor_exposure
            state.active_positions_count += 1

            base = inst.base_asset
            state.asset_concentrations[base] = state.asset_concentrations.get(base, 0.0) + risk_pct

        return state

    def evaluate_capital_approval(
        self,
        instrument: CryptoBaseInstrument,
        direction: int,
        requested_risk_pct: float,
        active_positions: List[Tuple[CryptoBaseInstrument, int, float]],
    ) -> Tuple[bool, float, Optional[str]]:
        """Evaluate if proposed position satisfies factor exposure limits."""
        # Check single trade limit
        capped_risk = min(requested_risk_pct, self.max_single_trade_risk_pct)
        if capped_risk <= 0.0:
            return False, 0.0, "REQUESTED_RISK_ZERO"

        # Check existing portfolio state
        current_state = self.calculate_portfolio_state(active_positions)

        # 1. Check Total Portfolio Heat
        if current_state.total_portfolio_heat_pct + capped_risk > self.max_total_portfolio_heat_pct:
            remaining_headroom = max(0.0, self.max_total_portfolio_heat_pct - current_state.total_portfolio_heat_pct)
            if remaining_headroom < 0.0025:  # Less than 0.25% headroom
                return False, 0.0, f"PORTFOLIO_HEAT_LIMIT ({current_state.total_portfolio_heat_pct*100:.1f}% + {capped_risk*100:.1f}% > {self.max_total_portfolio_heat_pct*100:.1f}%)"
            capped_risk = remaining_headroom

        # 2. Check Single Asset Concentration
        base_asset = instrument.base_asset
        current_asset_risk = current_state.asset_concentrations.get(base_asset, 0.0)
        if current_asset_risk + capped_risk > self.max_single_asset_risk_pct:
            asset_headroom = max(0.0, self.max_single_asset_risk_pct - current_asset_risk)
            if asset_headroom < 0.0025:
                return False, 0.0, f"ASSET_CONCENTRATION_LIMIT ({base_asset} {current_asset_risk*100:.1f}% + {capped_risk*100:.1f}% > {self.max_single_asset_risk_pct*100:.1f}%)"
            capped_risk = min(capped_risk, asset_headroom)

        # 3. Simulate new factor exposures
        new_decomp = self.decompose_position(instrument, direction, capped_risk)
        simulated_net_crypto = current_state.net_crypto_beta_pct + new_decomp.crypto_beta_exposure
        simulated_net_usd = current_state.net_usd_exposure_pct + new_decomp.usd_factor_exposure
        simulated_net_gold = current_state.net_gold_exposure_pct + new_decomp.gold_factor_exposure

        if abs(simulated_net_crypto) > self.max_net_crypto_beta_pct:
            return False, 0.0, f"CRYPTO_BETA_FACTOR_LIMIT ({abs(simulated_net_crypto)*100:.1f}% > {self.max_net_crypto_beta_pct*100:.1f}%)"

        if abs(simulated_net_usd) > self.max_net_usd_exposure_pct:
            return False, 0.0, f"USD_FACTOR_LIMIT ({abs(simulated_net_usd)*100:.1f}% > {self.max_net_usd_exposure_pct*100:.1f}%)"

        if abs(simulated_net_gold) > self.max_net_gold_exposure_pct:
            return False, 0.0, f"GOLD_FACTOR_LIMIT ({abs(simulated_net_gold)*100:.1f}% > {self.max_net_gold_exposure_pct*100:.1f}%)"

        return True, round(capped_risk, 4), "APPROVED"
