"""CSV and JSON export for pm-trader trade history and positions."""

from __future__ import annotations

import csv
import io
import json

from pm_trader.models import Trade


def export_trades_csv(trades: list[Trade]) -> str:
    """Export trades to CSV string."""
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow([
        "id", "timestamp", "market_slug", "side", "outcome",
        "shares", "avg_price", "amount_usd", "fee", "order_type",
        "levels_filled", "is_partial",
    ])
    for t in trades:
        writer.writerow([
            t.id, t.created_at, t.market_slug, t.side, t.outcome,
            f"{t.shares:.6f}", f"{t.avg_price:.6f}", f"{t.amount_usd:.2f}",
            f"{t.fee:.4f}", t.order_type, t.levels_filled,
            "true" if t.is_partial else "false",
        ])
    return buf.getvalue()


def export_trades_json(trades: list[Trade]) -> str:
    """Export trades to JSON string."""
    data = []
    for t in trades:
        data.append({
            "id": t.id,
            "timestamp": t.created_at,
            "market_slug": t.market_slug,
            "market_condition_id": t.market_condition_id,
            "side": t.side,
            "outcome": t.outcome,
            "shares": t.shares,
            "avg_price": t.avg_price,
            "amount_usd": t.amount_usd,
            "fee": t.fee,
            "fee_rate_bps": t.fee_rate_bps,
            "order_type": t.order_type,
            "slippage": t.slippage,
            "levels_filled": t.levels_filled,
            "is_partial": t.is_partial,
        })
    return json.dumps(data, indent=2)


def export_positions_csv(positions: list[dict]) -> str:
    """Export portfolio positions to CSV string.

    Args:
        positions: List of dicts from Engine.get_portfolio().
    """
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow([
        "market_slug", "outcome", "shares", "avg_entry_price",
        "total_cost", "live_price", "current_value",
        "unrealized_pnl", "percent_pnl",
    ])
    for p in positions:
        writer.writerow([
            p["market_slug"], p["outcome"],
            f"{p['shares']:.6f}", f"{p['avg_entry_price']:.6f}",
            f"{p['total_cost']:.2f}", f"{p['live_price']:.6f}",
            f"{p['current_value']:.2f}", f"{p['unrealized_pnl']:.2f}",
            f"{p['percent_pnl']:.2f}",
        ])
    return buf.getvalue()


def export_positions_json(positions: list[dict]) -> str:
    """Export portfolio positions to JSON string."""
    return json.dumps(positions, indent=2)
