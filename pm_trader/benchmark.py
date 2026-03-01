"""Benchmarking harness for pm-trader trading strategies.

A strategy is any Python callable with signature:
    def strategy(engine: Engine) -> None

The runner creates a fresh account, executes the strategy,
and computes analytics on the resulting trades.
"""

from __future__ import annotations

import importlib
from pathlib import Path
from tempfile import mkdtemp

from pm_trader.analytics import compute_stats
from pm_trader.engine import Engine


def run_strategy(
    strategy_path: str,
    *,
    balance: float = 10_000.0,
    data_dir: Path | None = None,
) -> dict:
    """Run a strategy and return its scorecard.

    Args:
        strategy_path: Dotted import path like "my_module.my_strategy".
        balance: Starting account balance.
        data_dir: Optional data directory. Uses a temp dir if not provided.

    Returns:
        Dict with strategy name, analytics metrics, and trade count.
    """
    # Import the strategy callable
    module_path, _, func_name = strategy_path.rpartition(".")
    if not module_path:
        raise ValueError(
            f"Strategy path must be 'module.function', got: {strategy_path!r}"
        )
    module = importlib.import_module(module_path)
    strategy_fn = getattr(module, func_name)

    # Create a fresh engine
    if data_dir is None:
        data_dir = Path(mkdtemp(prefix="pm-trader-bench-"))
    engine = Engine(data_dir)
    engine.init_account(balance)

    try:
        # Execute the strategy
        strategy_fn(engine)

        # Compute analytics
        account = engine.get_account()
        trades = engine.get_history(limit=10_000)
        portfolio = engine.get_portfolio()
        positions_value = sum(p["current_value"] for p in portfolio)
        stats = compute_stats(trades, account, positions_value)

        return {
            "strategy": strategy_path,
            "data_dir": str(data_dir),
            **stats,
        }
    finally:
        engine.close()


def compare_accounts(
    data_dirs: dict[str, Path],
) -> list[dict]:
    """Compare analytics across multiple named accounts.

    Args:
        data_dirs: Mapping of account name → data directory path.

    Returns:
        List of scorecards, one per account.
    """
    results = []
    for name, data_dir in data_dirs.items():
        engine = Engine(data_dir)
        try:
            account = engine.get_account()
            trades = engine.get_history(limit=10_000)
            portfolio = engine.get_portfolio()
            positions_value = sum(p["current_value"] for p in portfolio)
            stats = compute_stats(trades, account, positions_value)
            results.append({"account": name, **stats})
        finally:
            engine.close()
    return results
