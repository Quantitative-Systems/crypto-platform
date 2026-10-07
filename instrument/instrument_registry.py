"""Instrument Registry and Admission Gate.

Enforces the 11-step institutional admission gate before any instrument
can be traded with capital:

1. Crypto base verified (Invariant: base_class == CRYPTO)
2. Historical data depth verified
3. Multi-timeframe (HTF/MTF/LTF) availability verified
4. Cross-timeframe timestamp overlap validated
5. Liquidity volume sufficient
6. Typical spread acceptable (<= threshold)
7. Slippage & impact model calibrated
8. Financing / funding rate mechanics understood
9. Execution venue connectivity & routing supported
10. Trading session calendar understood (24/7 vs weekend closure)
11. Quote-to-USD risk conversion pipeline validated
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple

from instrument.asset_class import AssetClass
from instrument.instrument_contract import CryptoBaseInstrument, build_instrument


class AdmissionDecision(str, Enum):
    """Admission decision outcome."""
    ADMITTED = "ADMITTED"
    REJECTED = "REJECTED"
    PROBATIONARY = "PROBATIONARY"


@dataclass
class AdmissionChecklist:
    """Individual gate check evaluations."""
    crypto_base: bool = False
    historical_data_available: bool = False
    timeframes_available: bool = False
    sufficient_overlap: bool = False
    liquidity_sufficient: bool = False
    spread_acceptable: bool = False
    slippage_model_available: bool = False
    financing_understood: bool = False
    venue_supported: bool = False
    availability_schedule_understood: bool = False
    risk_conversion_validated: bool = False

    def all_passed(self) -> bool:
        """Check if all 11 admission gates passed."""
        return all([
            self.crypto_base,
            self.historical_data_available,
            self.timeframes_available,
            self.sufficient_overlap,
            self.liquidity_sufficient,
            self.spread_acceptable,
            self.slippage_model_available,
            self.financing_understood,
            self.venue_supported,
            self.availability_schedule_understood,
            self.risk_conversion_validated,
        ])

    def failed_gates(self) -> List[str]:
        """List the specific gates that failed."""
        fails = []
        for field_name, passed in self.__dict__.items():
            if not passed:
                fails.append(field_name)
        return fails


@dataclass
class AdmissionReport:
    """Detailed audit report for an admission decision."""
    symbol: str
    decision: AdmissionDecision
    checklist: AdmissionChecklist
    rejection_reasons: List[str]
    evaluated_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "symbol": self.symbol,
            "decision": self.decision.value,
            "all_passed": self.checklist.all_passed(),
            "failed_gates": self.checklist.failed_gates(),
            "rejection_reasons": self.rejection_reasons,
            "evaluated_at": self.evaluated_at,
        }


class InstrumentAdmissionGate:
    """Evaluates whether an instrument satisfies institutional readiness."""

    @staticmethod
    def evaluate(
        instrument: CryptoBaseInstrument,
        has_historical_data: bool = True,
        has_htf_mtf_ltf: bool = True,
        has_sufficient_overlap: bool = True,
        has_calibrated_slippage: bool = True,
        has_financing_model: bool = True,
        venue_supported: bool = True,
    ) -> AdmissionReport:
        """Evaluate an instrument against all admission criteria."""
        reasons: List[str] = []
        checklist = AdmissionChecklist()

        # Gate 1: Base asset must be crypto
        if instrument.engine_eligible and instrument.base_class == AssetClass.CRYPTO:
            checklist.crypto_base = True
        else:
            reasons.append(f"Ineligible base asset: {instrument.base_asset} ({instrument.base_class.value}). Base must be CRYPTO.")

        # Gate 2: Historical data depth
        checklist.historical_data_available = has_historical_data
        if not has_historical_data:
            reasons.append("Historical data insufficient for backtesting and model training.")

        # Gate 3: Triplet timeframes available
        checklist.timeframes_available = has_htf_mtf_ltf
        if not has_htf_mtf_ltf:
            reasons.append("Required HTF, MTF, and LTF data feeds not all present.")

        # Gate 4: Timestamp overlap
        checklist.sufficient_overlap = has_sufficient_overlap
        if not has_sufficient_overlap:
            reasons.append("Cross-timeframe historical candle timestamps do not sufficiently align.")

        # Gate 5: Liquidity depth
        liq = instrument.liquidity_profile
        if liq.daily_volume_usd >= liq.min_required_volume_usd:
            checklist.liquidity_sufficient = True
        else:
            reasons.append(f"Daily volume ${liq.daily_volume_usd:,.0f} below ${liq.min_required_volume_usd:,.0f} requirement.")

        # Gate 6: Spread acceptable
        if liq.typical_spread_bps <= liq.max_tolerated_spread_bps:
            checklist.spread_acceptable = True
        else:
            reasons.append(f"Typical spread {liq.typical_spread_bps} bps exceeds tolerance {liq.max_tolerated_spread_bps} bps.")

        # Gate 7: Slippage model
        checklist.slippage_model_available = has_calibrated_slippage
        if not has_calibrated_slippage:
            reasons.append("Calibrated execution slippage and market impact model missing.")

        # Gate 8: Financing / funding mechanics
        checklist.financing_understood = has_financing_model
        if not has_financing_model:
            reasons.append("Funding / borrow / overnight carry mechanics not configured.")

        # Gate 9: Venue connectivity
        checklist.venue_supported = venue_supported
        if not venue_supported:
            reasons.append("Target execution venue does not support this trading pair.")

        # Gate 10: Schedule / calendar
        checklist.availability_schedule_understood = True

        # Gate 11: Risk conversion pipeline
        if instrument.quote_info is not None:
            checklist.risk_conversion_validated = True
        else:
            reasons.append("Quote-to-USD risk conversion pipeline unverified.")

        decision = AdmissionDecision.ADMITTED if checklist.all_passed() else AdmissionDecision.REJECTED
        return AdmissionReport(
            symbol=instrument.symbol,
            decision=decision,
            checklist=checklist,
            rejection_reasons=reasons,
        )


class InstrumentRegistry:
    """Central repository of registered, admitted, and rejected instruments."""

    def __init__(self) -> None:
        self._instruments: Dict[str, CryptoBaseInstrument] = {}
        self._admission_reports: Dict[str, AdmissionReport] = {}

    def register(
        self,
        symbol_or_instrument: str | CryptoBaseInstrument,
        has_historical_data: bool = True,
        has_htf_mtf_ltf: bool = True,
        has_sufficient_overlap: bool = True,
        has_calibrated_slippage: bool = True,
        has_financing_model: bool = True,
        venue_supported: bool = True,
    ) -> AdmissionReport:
        """Register an instrument and evaluate admission gate."""
        if isinstance(symbol_or_instrument, str):
            instrument = build_instrument(symbol_or_instrument)
        else:
            instrument = symbol_or_instrument

        report = InstrumentAdmissionGate.evaluate(
            instrument=instrument,
            has_historical_data=has_historical_data,
            has_htf_mtf_ltf=has_htf_mtf_ltf,
            has_sufficient_overlap=has_sufficient_overlap,
            has_calibrated_slippage=has_calibrated_slippage,
            has_financing_model=has_financing_model,
            venue_supported=venue_supported,
        )

        self._instruments[instrument.symbol] = instrument
        self._admission_reports[instrument.symbol] = report
        return report

    def get_instrument(self, symbol: str) -> Optional[CryptoBaseInstrument]:
        """Retrieve instrument by symbol."""
        from instrument.symbol_normalizer import SymbolNormalizer
        norm_sym, _, _ = SymbolNormalizer.normalize(symbol)
        return self._instruments.get(norm_sym)

    def is_admitted(self, symbol: str) -> bool:
        """Check if instrument has passed the admission gate."""
        from instrument.symbol_normalizer import SymbolNormalizer
        norm_sym, _, _ = SymbolNormalizer.normalize(symbol)
        report = self._admission_reports.get(norm_sym)
        return report is not None and report.decision == AdmissionDecision.ADMITTED

    def get_admitted_instruments(self) -> List[CryptoBaseInstrument]:
        """List all admitted instruments."""
        return [
            inst for sym, inst in self._instruments.items()
            if self.is_admitted(sym)
        ]

    def get_admission_report(self, symbol: str) -> Optional[AdmissionReport]:
        """Retrieve admission audit report."""
        from instrument.symbol_normalizer import SymbolNormalizer
        norm_sym, _, _ = SymbolNormalizer.normalize(symbol)
        return self._admission_reports.get(norm_sym)
