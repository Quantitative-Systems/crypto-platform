"""Unit tests for STRATA Multi-Account & Broker Account Manager."""
import os
import pytest
from accounts.account_manager import (
    AccountConfig,
    AccountEnvironment,
    AccountManager,
    BrokerVenue,
)


def test_account_manager_default_accounts():
    mgr = AccountManager()
    accounts = mgr.list_accounts()
    assert len(accounts) >= 3

    acc_ids = [a["account_id"] for a in accounts]
    assert "ACC_PAPER_PRIMARY" in acc_ids
    assert "ACC_BINANCE_DEMO" in acc_ids
    assert "ACC_BINANCE_MICRO_LIVE" in acc_ids

    active = mgr.get_active_account()
    assert active.account_id == "ACC_PAPER_PRIMARY"
    assert active.environment == AccountEnvironment.PAPER


def test_account_switching_and_credential_isolation():
    mgr = AccountManager()
    mgr.set_active_account("ACC_BINANCE_DEMO")
    assert mgr.get_active_account().account_id == "ACC_BINANCE_DEMO"

    cfg = mgr.get_account_config("ACC_BINANCE_DEMO")
    creds = cfg.resolve_credentials()
    # No env var set, should safely be None without raising
    assert creds["api_key"] is None
    assert creds["api_secret"] is None
