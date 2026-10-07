"""Unit tests for the Instrument Intelligence Layer."""

from instrument.asset_class import AssetClass, classify_asset
from instrument.instrument_contract import CryptoBaseInstrument, build_instrument
from instrument.instrument_health import HealthStatus, InstrumentHealth
from instrument.instrument_registry import AdmissionDecision, InstrumentAdmissionGate, InstrumentRegistry
from instrument.liquidity_profile import LiquidityProfile, TradingSessionType
from instrument.quote_currency import QuoteSettlementType, get_quote_info
from instrument.symbol_normalizer import SymbolNormalizer
from instrument.trading_constraints import TradingConstraints
from instrument.venue_symbol_mapper import VenueSymbolMapper


class TestInstrumentIntelligenceLayer:
    """Test suite verifying crypto-first instrument contracts and invariants."""

    def test_asset_class_classification(self):
        assert classify_asset("BTC") == AssetClass.CRYPTO
        assert classify_asset("ETH") == AssetClass.CRYPTO
        assert classify_asset("SOL") == AssetClass.CRYPTO
        assert classify_asset("USD") == AssetClass.FIAT
        assert classify_asset("EUR") == AssetClass.FIAT
        assert classify_asset("GBP") == AssetClass.FIAT
        assert classify_asset("JPY") == AssetClass.FIAT
        assert classify_asset("USDT") == AssetClass.STABLECOIN
        assert classify_asset("USDC") == AssetClass.STABLECOIN
        assert classify_asset("XAU") == AssetClass.COMMODITY
        assert classify_asset("XAG") == AssetClass.COMMODITY

    def test_crypto_first_instrument_eligibility(self):
        # Eligible pairs: Base is CRYPTO
        eligible_pairs = ["BTC/USD", "BTC/USDT", "BTC/EUR", "BTC/GBP", "BTC/JPY", "BTC/XAU", "ETH/USD", "SOL/USD"]
        for p in eligible_pairs:
            inst = build_instrument(p)
            assert inst.engine_eligible is True
            assert inst.base_class == AssetClass.CRYPTO
            assert inst.reason is None
            d = inst.to_dict()
            assert d["engine_eligible"] is True
            assert "reason" not in d

    def test_non_crypto_base_strictly_rejected(self):
        # Ineligible pairs: Base is NOT CRYPTO
        ineligible_pairs = ["EUR/USD", "GBP/USD", "XAU/USD", "USD/JPY", "EUR/JPY"]
        for p in ineligible_pairs:
            inst = build_instrument(p)
            assert inst.engine_eligible is False
            assert inst.reason == "BASE_NOT_CRYPTO"
            d = inst.to_dict()
            assert d["engine_eligible"] is False
            assert d["reason"] == "BASE_NOT_CRYPTO"

    def test_btc_xau_gold_quote_properties(self):
        inst = build_instrument("BTC/XAU")
        assert inst.engine_eligible is True
        assert inst.base_asset == "BTC"
        assert inst.base_class == AssetClass.CRYPTO
        assert inst.quote_asset == "XAU"
        assert inst.quote_class == AssetClass.COMMODITY
        assert inst.quote_info.settlement_type == QuoteSettlementType.COMMODITY_XAU
        assert inst.quote_info.requires_fx_conversion is True

    def test_symbol_normalizer(self):
        assert SymbolNormalizer.normalize("BTCUSDT") == ("BTC/USDT", "BTC", "USDT")
        assert SymbolNormalizer.normalize("BTC-USD") == ("BTC/USD", "BTC", "USD")
        assert SymbolNormalizer.normalize("ETH_EUR") == ("ETH/EUR", "ETH", "EUR")
        assert SymbolNormalizer.normalize("BTCXAU") == ("BTC/XAU", "BTC", "XAU")
        assert SymbolNormalizer.normalize("XBTUSD") == ("BTC/USD", "BTC", "USD")
        assert SymbolNormalizer.normalize("SOLUSDC") == ("SOL/USDC", "SOL", "USDC")

    def test_venue_symbol_mapper(self):
        assert VenueSymbolMapper.to_venue_symbol("BTC/USDT", "binance") == "BTCUSDT"
        assert VenueSymbolMapper.to_venue_symbol("BTC/USD", "coinbase") == "BTC-USD"
        assert VenueSymbolMapper.to_venue_symbol("BTC/USD", "kraken") == "XXBTZUSD"
        assert VenueSymbolMapper.to_venue_symbol("ETH/USD", "kraken") == "XETHZUSD"
        assert VenueSymbolMapper.to_canonical("BTC-USD", "coinbase") == "BTC/USD"
        assert VenueSymbolMapper.to_canonical("BTCUSDT", "binance") == "BTC/USDT"

    def test_instrument_admission_gate(self):
        # Case 1: All criteria met -> ADMITTED
        btc_usd = build_instrument("BTC/USD")
        report = InstrumentAdmissionGate.evaluate(btc_usd)
        assert report.decision == AdmissionDecision.ADMITTED
        assert report.checklist.all_passed() is True

        # Case 2: Base not crypto (EUR/USD) -> REJECTED
        eur_usd = build_instrument("EUR/USD")
        report_eur = InstrumentAdmissionGate.evaluate(eur_usd)
        assert report_eur.decision == AdmissionDecision.REJECTED
        assert not report_eur.checklist.crypto_base
        assert any("Base must be CRYPTO" in r for r in report_eur.rejection_reasons)

        # Case 3: Missing historical data -> REJECTED
        report_nodata = InstrumentAdmissionGate.evaluate(btc_usd, has_historical_data=False)
        assert report_nodata.decision == AdmissionDecision.REJECTED
        assert not report_nodata.checklist.historical_data_available

    def test_instrument_registry(self):
        registry = InstrumentRegistry()
        rep1 = registry.register("BTC/USD")
        rep2 = registry.register("EUR/USD")
        rep3 = registry.register("SOL/USDT")

        assert registry.is_admitted("BTC/USD") is True
        assert registry.is_admitted("EUR/USD") is False
        assert registry.is_admitted("SOL/USDT") is True

        admitted = registry.get_admitted_instruments()
        symbols = [inst.symbol for inst in admitted]
        assert "BTC/USD" in symbols
        assert "SOL/USDT" in symbols
        assert "EUR/USD" not in symbols

    def test_instrument_health_evaluation(self):
        health = InstrumentHealth(symbol="BTC/USD")
        assert health.evaluate() == HealthStatus.HEALTHY
        assert health.is_operational() is True

        # Corrupted orderbook
        health.orderbook_valid = False
        assert health.evaluate() == HealthStatus.CORRUPTED
        assert health.is_operational() is False

        # Reset and test stale feed
        health.orderbook_valid = True
        health.last_tick_time = 0.0  # ancient
        assert health.evaluate(current_time=1000.0) == HealthStatus.DISCONNECTED
        assert health.is_operational() is False

    def test_trading_constraints_rounding(self):
        tc = TradingConstraints(
            min_order_qty=0.01,
            max_order_qty=10.0,
            step_size=0.01,
            tick_size=0.5,
            price_precision=1,
            qty_precision=2,
            min_notional_usd=50.0,
        )
        assert tc.round_price(65432.12) == 65432.0
        assert tc.round_price(65432.35) == 65432.5
        assert tc.round_qty(0.1284) == 0.12

        valid, msg = tc.validate_order(price=60000.0, qty=0.1)
        assert valid is True

        valid_too_small, msg = tc.validate_order(price=60000.0, qty=0.0001)
        assert valid_too_small is False
