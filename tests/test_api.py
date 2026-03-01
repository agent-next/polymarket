"""Tests for the Polymarket HTTP client."""

from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest

from pm_sim.api import (
    CLOB_BASE,
    GAMMA_BASE,
    PolymarketClient,
    _parse_market,
    _parse_order_book,
)
from pm_sim.db import Database
from pm_sim.models import ApiError, MarketNotFoundError


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def db(tmp_data_dir: Path) -> Database:
    database = Database(tmp_data_dir)
    database.init_schema()
    return database


@pytest.fixture
def client(db: Database) -> PolymarketClient:
    c = PolymarketClient(db)
    yield c
    c.close()


# ---------------------------------------------------------------------------
# Gamma API response fixtures
# ---------------------------------------------------------------------------

SAMPLE_GAMMA_MARKET = {
    "condition_id": "0xabc123",
    "slug": "will-bitcoin-hit-100k",
    "question": "Will Bitcoin hit $100k by end of 2026?",
    "description": "Resolves YES if BTC >= 100k.",
    "outcomes": '["Yes", "No"]',
    "outcomePrices": '["0.65", "0.35"]',
    "tokens": json.dumps([
        {"token_id": "tok_yes", "outcome": "Yes"},
        {"token_id": "tok_no", "outcome": "No"},
    ]),
    "active": True,
    "closed": False,
    "volume": "5000000",
    "liquidity": "250000",
    "end_date_iso": "2026-12-31T23:59:59Z",
    "fee_rate_bps": 0,
    "minimum_tick_size": "0.01",
}

SAMPLE_BOOK_RESPONSE = {
    "bids": [
        {"price": "0.64", "size": "150"},
        {"price": "0.63", "size": "200"},
    ],
    "asks": [
        {"price": "0.66", "size": "80"},
        {"price": "0.67", "size": "120"},
    ],
}


# ---------------------------------------------------------------------------
# _parse_market tests
# ---------------------------------------------------------------------------

class TestParseMarket:
    def test_basic_parsing(self):
        market = _parse_market(SAMPLE_GAMMA_MARKET)
        assert market.condition_id == "0xabc123"
        assert market.slug == "will-bitcoin-hit-100k"
        assert market.outcomes == ["Yes", "No"]
        assert market.outcome_prices == [0.65, 0.35]
        assert market.active is True
        assert market.closed is False
        assert market.volume == 5_000_000.0
        assert market.liquidity == 250_000.0
        assert market.fee_rate_bps == 0
        assert market.tick_size == 0.01

    def test_tokens_parsed_from_json_string(self):
        market = _parse_market(SAMPLE_GAMMA_MARKET)
        assert len(market.tokens) == 2
        assert market.tokens[0]["token_id"] == "tok_yes"
        assert market.tokens[0]["outcome"] == "Yes"
        assert market.tokens[1]["token_id"] == "tok_no"

    def test_tokens_parsed_from_list(self):
        data = {**SAMPLE_GAMMA_MARKET, "tokens": [
            {"token_id": "t1", "outcome": "Yes"},
            {"token_id": "t2", "outcome": "No"},
        ]}
        market = _parse_market(data)
        assert market.tokens[0]["token_id"] == "t1"

    def test_outcome_prices_from_list(self):
        data = {**SAMPLE_GAMMA_MARKET, "outcomePrices": [0.7, 0.3]}
        market = _parse_market(data)
        assert market.outcome_prices == [0.7, 0.3]

    def test_missing_fields_use_defaults(self):
        data = {"condition_id": "0x1"}
        market = _parse_market(data)
        assert market.slug == ""
        assert market.volume == 0.0
        assert market.outcome_prices == [0.0, 0.0]
        assert market.tick_size == 0.01

    def test_null_volume_liquidity(self):
        data = {**SAMPLE_GAMMA_MARKET, "volume": None, "liquidity": None}
        market = _parse_market(data)
        assert market.volume == 0.0
        assert market.liquidity == 0.0


# ---------------------------------------------------------------------------
# _parse_order_book tests
# ---------------------------------------------------------------------------

class TestParseOrderBook:
    def test_basic_parsing(self):
        book = _parse_order_book(SAMPLE_BOOK_RESPONSE)
        assert len(book.bids) == 2
        assert len(book.asks) == 2
        assert book.bids[0].price == 0.64
        assert book.bids[0].size == 150.0
        assert book.asks[0].price == 0.66
        assert book.asks[0].size == 80.0

    def test_empty_book(self):
        book = _parse_order_book({})
        assert book.bids == []
        assert book.asks == []

    def test_one_sided_book(self):
        book = _parse_order_book({"bids": [{"price": "0.5", "size": "100"}]})
        assert len(book.bids) == 1
        assert book.asks == []


# ---------------------------------------------------------------------------
# PolymarketClient.get_market tests (with httpx mock)
# ---------------------------------------------------------------------------

class TestGetMarket:
    def test_get_market_by_slug(self, client: PolymarketClient, httpx_mock):
        httpx_mock.add_response(
            url=httpx.URL(GAMMA_BASE + "/markets", params={"slug": "will-bitcoin-hit-100k"}),
            json=[SAMPLE_GAMMA_MARKET],
        )
        market = client.get_market("will-bitcoin-hit-100k")
        assert market.condition_id == "0xabc123"
        assert market.slug == "will-bitcoin-hit-100k"

    def test_get_market_by_condition_id(self, client: PolymarketClient, httpx_mock):
        # First request (slug lookup) returns empty
        httpx_mock.add_response(
            url=httpx.URL(GAMMA_BASE + "/markets", params={"slug": "0xabc123"}),
            json=[],
        )
        # Second request (condition_id lookup) returns the market
        httpx_mock.add_response(
            url=httpx.URL(GAMMA_BASE + "/markets", params={"condition_id": "0xabc123"}),
            json=[SAMPLE_GAMMA_MARKET],
        )
        market = client.get_market("0xabc123")
        assert market.condition_id == "0xabc123"

    def test_market_not_found(self, client: PolymarketClient, httpx_mock):
        httpx_mock.add_response(
            url=httpx.URL(GAMMA_BASE + "/markets", params={"slug": "nonexistent"}),
            json=[],
        )
        httpx_mock.add_response(
            url=httpx.URL(GAMMA_BASE + "/markets", params={"condition_id": "nonexistent"}),
            json=[],
        )
        with pytest.raises(MarketNotFoundError):
            client.get_market("nonexistent")

    def test_market_cached_on_second_call(self, client: PolymarketClient, httpx_mock):
        httpx_mock.add_response(
            url=httpx.URL(GAMMA_BASE + "/markets", params={"slug": "btc"}),
            json=[SAMPLE_GAMMA_MARKET],
        )
        m1 = client.get_market("btc")
        m2 = client.get_market("btc")  # Should use cache, no second HTTP call
        assert m1.condition_id == m2.condition_id
        assert len(httpx_mock.get_requests()) == 1

    def test_api_http_error(self, client: PolymarketClient, httpx_mock):
        httpx_mock.add_response(
            url=httpx.URL(GAMMA_BASE + "/markets", params={"slug": "err"}),
            status_code=500,
            text="Internal Server Error",
        )
        with pytest.raises(ApiError) as exc_info:
            client.get_market("err")
        assert exc_info.value.status_code == 500


# ---------------------------------------------------------------------------
# PolymarketClient.list_markets tests
# ---------------------------------------------------------------------------

class TestListMarkets:
    def test_list_markets(self, client: PolymarketClient, httpx_mock):
        httpx_mock.add_response(json=[SAMPLE_GAMMA_MARKET])
        markets = client.list_markets(limit=5)
        assert len(markets) == 1
        assert markets[0].slug == "will-bitcoin-hit-100k"

    def test_list_markets_empty(self, client: PolymarketClient, httpx_mock):
        httpx_mock.add_response(json=[])
        markets = client.list_markets()
        assert markets == []


# ---------------------------------------------------------------------------
# PolymarketClient.search_markets tests
# ---------------------------------------------------------------------------

class TestSearchMarkets:
    def test_search(self, client: PolymarketClient, httpx_mock):
        httpx_mock.add_response(json=[SAMPLE_GAMMA_MARKET])
        results = client.search_markets("bitcoin")
        assert len(results) == 1
        assert "bitcoin" in results[0].slug


# ---------------------------------------------------------------------------
# CLOB API tests
# ---------------------------------------------------------------------------

class TestClobEndpoints:
    def test_get_order_book(self, client: PolymarketClient, httpx_mock):
        httpx_mock.add_response(
            url=httpx.URL(CLOB_BASE + "/book", params={"token_id": "tok_yes"}),
            json=SAMPLE_BOOK_RESPONSE,
        )
        book = client.get_order_book("tok_yes")
        assert len(book.bids) == 2
        assert len(book.asks) == 2

    def test_get_midpoint(self, client: PolymarketClient, httpx_mock):
        httpx_mock.add_response(
            url=httpx.URL(CLOB_BASE + "/midpoint", params={"token_id": "tok_yes"}),
            json={"mid": "0.65"},
        )
        mid = client.get_midpoint("tok_yes")
        assert mid == 0.65

    def test_get_fee_rate(self, client: PolymarketClient, httpx_mock):
        httpx_mock.add_response(
            url=httpx.URL(CLOB_BASE + "/fee-rate", params={"token_id": "tok_yes"}),
            json={"fee_rate_bps": 200},
        )
        fee = client.get_fee_rate("tok_yes")
        assert fee == 200

    def test_fee_rate_cached(self, client: PolymarketClient, httpx_mock):
        httpx_mock.add_response(
            url=httpx.URL(CLOB_BASE + "/fee-rate", params={"token_id": "tok_yes"}),
            json={"fee_rate_bps": 175},
        )
        f1 = client.get_fee_rate("tok_yes")
        f2 = client.get_fee_rate("tok_yes")
        assert f1 == f2 == 175
        assert len(httpx_mock.get_requests()) == 1

    def test_get_tick_size(self, client: PolymarketClient, httpx_mock):
        httpx_mock.add_response(
            url=httpx.URL(CLOB_BASE + "/tick-size", params={"token_id": "tok_yes"}),
            json={"minimum_tick_size": 0.001},
        )
        tick = client.get_tick_size("tok_yes")
        assert tick == 0.001

    def test_clob_api_error(self, client: PolymarketClient, httpx_mock):
        httpx_mock.add_response(
            url=httpx.URL(CLOB_BASE + "/book", params={"token_id": "bad"}),
            status_code=404,
            text="Not Found",
        )
        with pytest.raises(ApiError) as exc_info:
            client.get_order_book("bad")
        assert exc_info.value.status_code == 404


# ---------------------------------------------------------------------------
# get_trade_context tests
# ---------------------------------------------------------------------------

class TestGetTradeContext:
    def test_returns_market_book_fee(self, client: PolymarketClient, httpx_mock):
        httpx_mock.add_response(
            url=httpx.URL(GAMMA_BASE + "/markets", params={"slug": "btc"}),
            json=[SAMPLE_GAMMA_MARKET],
        )
        httpx_mock.add_response(
            url=httpx.URL(CLOB_BASE + "/book", params={"token_id": "tok_yes"}),
            json=SAMPLE_BOOK_RESPONSE,
        )
        httpx_mock.add_response(
            url=httpx.URL(CLOB_BASE + "/fee-rate", params={"token_id": "tok_yes"}),
            json={"fee_rate_bps": 0},
        )
        market, book, fee = client.get_trade_context("btc", "yes")
        assert market.condition_id == "0xabc123"
        assert len(book.bids) == 2
        assert fee == 0

    def test_no_outcome(self, client: PolymarketClient, httpx_mock):
        httpx_mock.add_response(
            url=httpx.URL(GAMMA_BASE + "/markets", params={"slug": "btc"}),
            json=[SAMPLE_GAMMA_MARKET],
        )
        httpx_mock.add_response(
            url=httpx.URL(CLOB_BASE + "/book", params={"token_id": "tok_no"}),
            json=SAMPLE_BOOK_RESPONSE,
        )
        httpx_mock.add_response(
            url=httpx.URL(CLOB_BASE + "/fee-rate", params={"token_id": "tok_no"}),
            json={"fee_rate_bps": 175},
        )
        market, book, fee = client.get_trade_context("btc", "no")
        assert fee == 175
