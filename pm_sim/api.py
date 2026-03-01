"""Polymarket HTTP client for Gamma and CLOB APIs.

Fetches market data, order books, prices, fees, and tick sizes from
the public Polymarket APIs.  Market metadata is cached in SQLite;
prices and order books are NEVER cached (always live).
"""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone

import httpx

from pm_sim.db import Database
from pm_sim.models import (
    ApiError,
    Market,
    MarketNotFoundError,
    OrderBook,
    OrderBookLevel,
)

GAMMA_BASE = "https://gamma-api.polymarket.com"
CLOB_BASE = "https://clob.polymarket.com"

CACHE_TTL_SECONDS = 300  # 5 minutes for market metadata

_TIMEOUT = httpx.Timeout(10.0)


class PolymarketClient:
    """HTTP client for Polymarket public APIs."""

    def __init__(self, db: Database) -> None:
        self.db = db
        self._http = httpx.Client(timeout=_TIMEOUT)

    def close(self) -> None:
        self._http.close()

    # ------------------------------------------------------------------
    # Cache helpers
    # ------------------------------------------------------------------

    def _get_cached(self, key: str) -> dict | list | None:
        """Return cached value if it exists and is within TTL."""
        row = self.db.conn.execute(
            "SELECT data, fetched_at FROM market_cache WHERE cache_key = ?",
            (key,),
        ).fetchone()
        if row is None:
            return None
        fetched_at = datetime.fromisoformat(row["fetched_at"])
        if not fetched_at.tzinfo:
            fetched_at = fetched_at.replace(tzinfo=timezone.utc)
        now = datetime.now(timezone.utc)
        age = (now - fetched_at).total_seconds()
        if age > CACHE_TTL_SECONDS:
            return None
        return json.loads(row["data"])

    def _set_cached(self, key: str, data: dict | list) -> None:
        self.db.set_cache(key, data)

    # ------------------------------------------------------------------
    # Gamma API — market discovery
    # ------------------------------------------------------------------

    def _gamma_get(self, path: str, params: dict | None = None) -> list | dict:
        """Make a GET request to the Gamma API."""
        url = f"{GAMMA_BASE}{path}"
        try:
            resp = self._http.get(url, params=params)
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPStatusError as e:
            raise ApiError(
                f"Gamma API error: {e.response.status_code} {e.response.text[:200]}",
                status_code=e.response.status_code,
            ) from e
        except httpx.RequestError as e:
            raise ApiError(f"Gamma API request failed: {e}") from e

    def _clob_get(self, path: str, params: dict | None = None) -> dict | list:
        """Make a GET request to the CLOB API."""
        url = f"{CLOB_BASE}{path}"
        try:
            resp = self._http.get(url, params=params)
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPStatusError as e:
            raise ApiError(
                f"CLOB API error: {e.response.status_code} {e.response.text[:200]}",
                status_code=e.response.status_code,
            ) from e
        except httpx.RequestError as e:
            raise ApiError(f"CLOB API request failed: {e}") from e

    # ------------------------------------------------------------------
    # Market resolution (slug or condition_id → Market)
    # ------------------------------------------------------------------

    def get_market(self, slug_or_id: str) -> Market:
        """Resolve a slug or condition_id to a full Market object.

        Market metadata is cached for 5 minutes.
        """
        cache_key = f"market:{slug_or_id}"
        cached = self._get_cached(cache_key)
        if cached is not None:
            return _parse_market(cached)

        # Try by slug first
        data = self._gamma_get("/markets", params={"slug": slug_or_id})
        if isinstance(data, list) and len(data) > 0:
            market_data = data[0]
        elif isinstance(data, dict) and data.get("condition_id"):
            market_data = data
        else:
            # Try by condition_id
            data = self._gamma_get(
                "/markets", params={"condition_id": slug_or_id}
            )
            if isinstance(data, list) and len(data) > 0:
                market_data = data[0]
            elif isinstance(data, dict) and data.get("condition_id"):
                market_data = data
            else:
                raise MarketNotFoundError(slug_or_id)

        self._set_cached(cache_key, market_data)
        return _parse_market(market_data)

    def list_markets(
        self, *, limit: int = 20, sort_by: str = "volume"
    ) -> list[Market]:
        """List active markets sorted by volume or liquidity."""
        params: dict = {
            "limit": limit,
            "active": "true",
            "closed": "false",
        }
        if sort_by == "volume":
            params["order"] = "volume"
            params["ascending"] = "false"
        elif sort_by == "liquidity":
            params["order"] = "liquidity"
            params["ascending"] = "false"

        data = self._gamma_get("/markets", params=params)
        if not isinstance(data, list):
            return []
        return [_parse_market(m) for m in data if m.get("condition_id")]

    def search_markets(self, query: str, *, limit: int = 10) -> list[Market]:
        """Search markets by text query."""
        data = self._gamma_get(
            "/markets", params={"_q": query, "limit": limit}
        )
        if not isinstance(data, list):
            return []
        return [_parse_market(m) for m in data if m.get("condition_id")]

    # ------------------------------------------------------------------
    # CLOB API — prices, order book, fees, tick size
    # ------------------------------------------------------------------

    def get_order_book(self, token_id: str) -> OrderBook:
        """Fetch the live order book for a token.  NEVER cached."""
        data = self._clob_get("/book", params={"token_id": token_id})
        return _parse_order_book(data)

    def get_midpoint(self, token_id: str) -> float:
        """Fetch the live midpoint price for a token.  NEVER cached."""
        data = self._clob_get("/midpoint", params={"token_id": token_id})
        return float(data.get("mid", 0.0))

    def get_fee_rate(self, token_id: str) -> int:
        """Fetch the fee rate in bps for a token.  Cached 5 min."""
        cache_key = f"fee_rate:{token_id}"
        cached = self._get_cached(cache_key)
        if cached is not None:
            return int(cached.get("fee_rate_bps", 0))

        data = self._clob_get("/fee-rate", params={"token_id": token_id})
        fee_bps = int(data.get("fee_rate_bps", 0))
        self._set_cached(cache_key, {"fee_rate_bps": fee_bps})
        return fee_bps

    def get_tick_size(self, token_id: str) -> float:
        """Fetch the tick size for a token.  Cached 5 min."""
        cache_key = f"tick_size:{token_id}"
        cached = self._get_cached(cache_key)
        if cached is not None:
            return float(cached.get("minimum_tick_size", 0.01))

        data = self._clob_get("/tick-size", params={"token_id": token_id})
        tick = float(data.get("minimum_tick_size", 0.01))
        self._set_cached(cache_key, {"minimum_tick_size": tick})
        return tick

    # ------------------------------------------------------------------
    # Convenience: get everything needed for a trade
    # ------------------------------------------------------------------

    def get_trade_context(
        self, slug_or_id: str, outcome: str
    ) -> tuple[Market, OrderBook, int]:
        """Return (Market, OrderBook, fee_rate_bps) for a trade.

        - Market metadata is cached.
        - Order book is always live.
        - Fee rate is cached.
        """
        market = self.get_market(slug_or_id)
        token_id = (
            market.yes_token_id if outcome == "yes" else market.no_token_id
        )
        book = self.get_order_book(token_id)
        fee_rate = self.get_fee_rate(token_id)
        return market, book, fee_rate


# ---------------------------------------------------------------------------
# Parsing helpers
# ---------------------------------------------------------------------------


def _parse_market(data: dict) -> Market:
    """Parse a Gamma API market response into a Market dataclass."""
    # Parse tokens — Gamma returns a JSON string or list
    tokens_raw = data.get("tokens", [])
    if isinstance(tokens_raw, str):
        tokens_raw = json.loads(tokens_raw)

    tokens = []
    for t in tokens_raw:
        tokens.append({
            "token_id": t.get("token_id", ""),
            "outcome": t.get("outcome", ""),
        })

    # Parse outcome prices — can be string or list
    outcome_prices_raw = data.get("outcomePrices", data.get("outcome_prices", []))
    if isinstance(outcome_prices_raw, str):
        outcome_prices_raw = json.loads(outcome_prices_raw)
    outcome_prices = [float(p) for p in outcome_prices_raw] if outcome_prices_raw else [0.0, 0.0]

    # Parse outcomes
    outcomes_raw = data.get("outcomes", [])
    if isinstance(outcomes_raw, str):
        outcomes_raw = json.loads(outcomes_raw)

    return Market(
        condition_id=data.get("condition_id", ""),
        slug=data.get("slug", ""),
        question=data.get("question", ""),
        description=data.get("description", ""),
        outcomes=outcomes_raw if outcomes_raw else ["Yes", "No"],
        outcome_prices=outcome_prices,
        tokens=tokens,
        active=bool(data.get("active", False)),
        closed=bool(data.get("closed", False)),
        volume=float(data.get("volume", 0) or 0),
        liquidity=float(data.get("liquidity", 0) or 0),
        end_date=data.get("end_date_iso", data.get("end_date", "")),
        fee_rate_bps=int(data.get("fee_rate_bps", 0) or 0),
        tick_size=float(data.get("minimum_tick_size", 0.01) or 0.01),
    )


def _parse_order_book(data: dict) -> OrderBook:
    """Parse a CLOB /book response into an OrderBook dataclass."""
    bids = []
    for entry in data.get("bids", []):
        bids.append(OrderBookLevel(
            price=float(entry.get("price", 0)),
            size=float(entry.get("size", 0)),
        ))

    asks = []
    for entry in data.get("asks", []):
        asks.append(OrderBookLevel(
            price=float(entry.get("price", 0)),
            size=float(entry.get("size", 0)),
        ))

    return OrderBook(bids=bids, asks=asks)
