"""Tests for CSV/JSON export."""

from __future__ import annotations

import csv
import io
import json

import pytest

from pm_trader.export import (
    export_positions_csv,
    export_positions_json,
    export_trades_csv,
    export_trades_json,
)
from pm_trader.models import Trade


def _trade(**overrides) -> Trade:
    defaults = dict(
        id=1,
        market_condition_id="0xabc",
        market_slug="test-market",
        market_question="Test?",
        outcome="yes",
        side="buy",
        order_type="fok",
        avg_price=0.65,
        amount_usd=65.0,
        shares=100.0,
        fee_rate_bps=200,
        fee=0.46,
        slippage=0.0,
        levels_filled=1,
        is_partial=False,
        created_at="2026-01-15 12:00:00",
    )
    defaults.update(overrides)
    return Trade(**defaults)


SAMPLE_POSITION = {
    "market_slug": "test-market",
    "market_question": "Test?",
    "outcome": "yes",
    "shares": 100.0,
    "avg_entry_price": 0.65,
    "total_cost": 65.0,
    "live_price": 0.70,
    "current_value": 70.0,
    "unrealized_pnl": 5.0,
    "percent_pnl": 7.69,
}


class TestExportTradesCsv:
    def test_empty(self):
        result = export_trades_csv([])
        reader = csv.reader(io.StringIO(result))
        rows = list(reader)
        assert len(rows) == 1  # header only
        assert "id" in rows[0]

    def test_single_trade(self):
        result = export_trades_csv([_trade()])
        reader = csv.reader(io.StringIO(result))
        rows = list(reader)
        assert len(rows) == 2
        assert rows[1][0] == "1"  # id
        assert rows[1][2] == "test-market"  # market_slug

    def test_multiple_trades(self):
        trades = [_trade(id=1), _trade(id=2, side="sell")]
        result = export_trades_csv(trades)
        reader = csv.reader(io.StringIO(result))
        rows = list(reader)
        assert len(rows) == 3


class TestExportTradesJson:
    def test_empty(self):
        result = export_trades_json([])
        data = json.loads(result)
        assert data == []

    def test_single_trade(self):
        result = export_trades_json([_trade()])
        data = json.loads(result)
        assert len(data) == 1
        assert data[0]["id"] == 1
        assert data[0]["market_slug"] == "test-market"
        assert data[0]["avg_price"] == 0.65
        assert data[0]["fee_rate_bps"] == 200

    def test_roundtrip_fields(self):
        t = _trade()
        result = export_trades_json([t])
        data = json.loads(result)
        assert data[0]["shares"] == t.shares
        assert data[0]["amount_usd"] == t.amount_usd


class TestExportPositionsCsv:
    def test_empty(self):
        result = export_positions_csv([])
        reader = csv.reader(io.StringIO(result))
        rows = list(reader)
        assert len(rows) == 1  # header only

    def test_single_position(self):
        result = export_positions_csv([SAMPLE_POSITION])
        reader = csv.reader(io.StringIO(result))
        rows = list(reader)
        assert len(rows) == 2
        assert rows[1][0] == "test-market"


class TestExportPositionsJson:
    def test_empty(self):
        result = export_positions_json([])
        assert json.loads(result) == []

    def test_single_position(self):
        result = export_positions_json([SAMPLE_POSITION])
        data = json.loads(result)
        assert len(data) == 1
        assert data[0]["market_slug"] == "test-market"
        assert data[0]["unrealized_pnl"] == 5.0
