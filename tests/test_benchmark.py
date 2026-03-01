"""Tests for benchmarking harness."""

from __future__ import annotations

from pathlib import Path

import pytest

from pm_trader.benchmark import compare_accounts, run_strategy
from pm_trader.engine import Engine


# ---------------------------------------------------------------------------
# Dummy strategies for testing
# ---------------------------------------------------------------------------


def noop_strategy(engine: Engine) -> None:
    """Does nothing — baseline strategy."""
    pass


def buy_once_strategy(engine: Engine) -> None:
    """Buys $100 of the first market's YES outcome."""
    markets = engine.api.list_markets(limit=1)
    if markets:
        engine.buy(markets[0].slug, "yes", 100.0)


# ---------------------------------------------------------------------------
# run_strategy tests
# ---------------------------------------------------------------------------


class TestRunStrategy:
    def test_invalid_strategy_path(self):
        with pytest.raises(ValueError, match="module.function"):
            run_strategy("just_a_name")

    def test_missing_module(self):
        with pytest.raises(ModuleNotFoundError):
            run_strategy("nonexistent_module.func")

    def test_missing_function(self):
        with pytest.raises(AttributeError):
            run_strategy("tests.test_benchmark.nonexistent_function")

    def test_noop_strategy(self):
        result = run_strategy(
            "tests.test_benchmark.noop_strategy",
            balance=5_000.0,
        )
        assert result["strategy"] == "tests.test_benchmark.noop_strategy"
        assert result["starting_balance"] == 5_000.0
        assert result["cash"] == 5_000.0
        assert result["total_trades"] == 0
        assert result["pnl"] == 0.0
        assert result["roi_pct"] == 0.0


# ---------------------------------------------------------------------------
# compare_accounts tests
# ---------------------------------------------------------------------------


class TestCompareAccounts:
    def test_compare_two_accounts(self, tmp_path: Path):
        # Create two accounts with different balances
        dir_a = tmp_path / "agent-a"
        dir_b = tmp_path / "agent-b"

        eng_a = Engine(dir_a)
        eng_a.init_account(10_000.0)
        eng_a.close()

        eng_b = Engine(dir_b)
        eng_b.init_account(5_000.0)
        eng_b.close()

        results = compare_accounts({
            "agent-a": dir_a,
            "agent-b": dir_b,
        })
        assert len(results) == 2
        assert results[0]["account"] == "agent-a"
        assert results[0]["starting_balance"] == 10_000.0
        assert results[1]["account"] == "agent-b"
        assert results[1]["starting_balance"] == 5_000.0

    def test_compare_empty(self):
        results = compare_accounts({})
        assert results == []
