"""Unit Tests for Crypto Engine Promotion Gate and Isolated Architecture."""
from __future__ import annotations

import json
from pathlib import Path
import pytest

from crypto_engine.pipeline.promotion_gate import (
    ProductionPromotionGate,
    PromotionStatus,
    PromotionVerdict,
)


def test_promotion_gate_passed_candidate(tmp_path, monkeypatch):
    test_passed_dir = tmp_path / "passed"
    test_failed_dir = tmp_path / "failed"
    test_reg_file = tmp_path / "champions.json"

    monkeypatch.setattr("crypto_engine.pipeline.promotion_gate.PASSED_DIR", test_passed_dir)
    monkeypatch.setattr("crypto_engine.pipeline.promotion_gate.FAILED_DIR", test_failed_dir)
    monkeypatch.setattr("crypto_engine.pipeline.promotion_gate.REGISTRY_FILE", test_reg_file)

    test_passed_dir.mkdir(parents=True, exist_ok=True)
    test_failed_dir.mkdir(parents=True, exist_ok=True)

    metrics = {
        "total_trades": 100,
        "profit_factor": 1.65,
        "total_r": 45.0,
        "win_rate": 0.35,
        "max_drawdown_r": 12.0,
    }

    verdict = ProductionPromotionGate.evaluate_and_route(
        model_id="TEST_MODEL_PASSED",
        symbol="BTCUSDT",
        timeframe_set="SET_2",
        stream_metrics=metrics,
    )

    assert verdict.status == PromotionStatus.PASSED
    assert (test_passed_dir / "TEST_MODEL_PASSED.json").exists()
    assert not (test_failed_dir / "TEST_MODEL_PASSED.json").exists()

    champions = ProductionPromotionGate.list_live_champions()
    assert "TEST_MODEL_PASSED" in champions
    assert champions["TEST_MODEL_PASSED"]["profit_factor"] == 1.65


def test_promotion_gate_failed_candidate(tmp_path, monkeypatch):
    test_passed_dir = tmp_path / "passed"
    test_failed_dir = tmp_path / "failed"
    test_reg_file = tmp_path / "champions.json"

    monkeypatch.setattr("crypto_engine.pipeline.promotion_gate.PASSED_DIR", test_passed_dir)
    monkeypatch.setattr("crypto_engine.pipeline.promotion_gate.FAILED_DIR", test_failed_dir)
    monkeypatch.setattr("crypto_engine.pipeline.promotion_gate.REGISTRY_FILE", test_reg_file)

    test_passed_dir.mkdir(parents=True, exist_ok=True)
    test_failed_dir.mkdir(parents=True, exist_ok=True)

    # Low profit factor & negative R
    metrics = {
        "total_trades": 120,
        "profit_factor": 0.75,
        "total_r": -25.0,
        "win_rate": 0.20,
        "max_drawdown_r": 45.0,
    }

    verdict = ProductionPromotionGate.evaluate_and_route(
        model_id="TEST_MODEL_FAILED",
        symbol="ETHUSDT",
        timeframe_set="SET_4",
        stream_metrics=metrics,
    )

    assert verdict.status == PromotionStatus.FAILED
    assert not (test_passed_dir / "TEST_MODEL_FAILED.json").exists()
    assert (test_failed_dir / "TEST_MODEL_FAILED.json").exists()

    champions = ProductionPromotionGate.list_live_champions()
    assert "TEST_MODEL_FAILED" not in champions
