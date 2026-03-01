"""Click CLI for pm-sim — Polymarket paper trading simulator."""

from __future__ import annotations

import dataclasses
import json
import sys
from pathlib import Path

import click

from pm_sim.engine import Engine
from pm_sim.models import SimError

DEFAULT_DATA_DIR = Path.home() / ".pm-sim"


# ---------------------------------------------------------------------------
# JSON helpers
# ---------------------------------------------------------------------------

def _ok(data) -> str:
    """Return a JSON success envelope."""
    return json.dumps({"ok": True, "data": _serialize(data)}, indent=2)


def _err(error: SimError) -> str:
    """Return a JSON error envelope."""
    return json.dumps(
        {"ok": False, "error": error.message, "code": error.code},
        indent=2,
    )


def _serialize(obj):
    """Recursively convert dataclasses and other objects to JSON-safe dicts."""
    if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
        return {k: _serialize(v) for k, v in dataclasses.asdict(obj).items()}
    if isinstance(obj, list):
        return [_serialize(item) for item in obj]
    if isinstance(obj, dict):
        return {k: _serialize(v) for k, v in obj.items()}
    return obj


# ---------------------------------------------------------------------------
# CLI group
# ---------------------------------------------------------------------------

@click.group()
@click.option(
    "--data-dir",
    type=click.Path(path_type=Path),
    default=DEFAULT_DATA_DIR,
    envvar="PM_SIM_DATA_DIR",
    help="Data directory for SQLite database.",
)
@click.pass_context
def main(ctx: click.Context, data_dir: Path) -> None:
    """pm-sim — 1:1 faithful Polymarket paper trading simulator."""
    ctx.ensure_object(dict)
    ctx.obj["data_dir"] = data_dir


def _get_engine(ctx: click.Context) -> Engine:
    return Engine(ctx.obj["data_dir"])


# ---------------------------------------------------------------------------
# Account commands
# ---------------------------------------------------------------------------

@main.command()
@click.option("--balance", type=float, default=10_000.0, help="Starting balance in USD.")
@click.pass_context
def init(ctx: click.Context, balance: float) -> None:
    """Initialize a paper trading account."""
    engine = _get_engine(ctx)
    try:
        account = engine.init_account(balance)
        click.echo(_ok(account))
    except SimError as e:
        click.echo(_err(e))
        sys.exit(1)
    finally:
        engine.close()


@main.command()
@click.pass_context
def balance(ctx: click.Context) -> None:
    """Show account balance and total portfolio value."""
    engine = _get_engine(ctx)
    try:
        data = engine.get_balance()
        click.echo(_ok(data))
    except SimError as e:
        click.echo(_err(e))
        sys.exit(1)
    finally:
        engine.close()


@main.command()
@click.option("--confirm", is_flag=True, help="Required to confirm reset.")
@click.pass_context
def reset(ctx: click.Context, confirm: bool) -> None:
    """Wipe all data and start fresh."""
    if not confirm:
        click.echo(
            json.dumps(
                {"ok": False, "error": "Pass --confirm to reset all data.", "code": "CONFIRM_REQUIRED"},
                indent=2,
            )
        )
        sys.exit(1)
    engine = _get_engine(ctx)
    try:
        engine.reset()
        click.echo(_ok({"reset": True}))
    except SimError as e:
        click.echo(_err(e))
        sys.exit(1)
    finally:
        engine.close()


# ---------------------------------------------------------------------------
# Market commands
# ---------------------------------------------------------------------------

@main.group()
def markets() -> None:
    """Market data commands."""
    pass


@markets.command("list")
@click.option("--limit", type=int, default=20)
@click.option("--sort", "sort_by", type=click.Choice(["volume", "liquidity"]), default="volume")
@click.pass_context
def markets_list(ctx: click.Context, limit: int, sort_by: str) -> None:
    """List active markets."""
    engine = _get_engine(ctx)
    try:
        result = engine.api.list_markets(limit=limit, sort_by=sort_by)
        click.echo(_ok(result))
    except SimError as e:
        click.echo(_err(e))
        sys.exit(1)
    finally:
        engine.close()


@markets.command("search")
@click.argument("query")
@click.option("--limit", type=int, default=10)
@click.pass_context
def markets_search(ctx: click.Context, query: str, limit: int) -> None:
    """Search markets by text query."""
    engine = _get_engine(ctx)
    try:
        result = engine.api.search_markets(query, limit=limit)
        click.echo(_ok(result))
    except SimError as e:
        click.echo(_err(e))
        sys.exit(1)
    finally:
        engine.close()


@markets.command("get")
@click.argument("slug_or_id")
@click.pass_context
def markets_get(ctx: click.Context, slug_or_id: str) -> None:
    """Get full market details."""
    engine = _get_engine(ctx)
    try:
        market = engine.api.get_market(slug_or_id)
        click.echo(_ok(market))
    except SimError as e:
        click.echo(_err(e))
        sys.exit(1)
    finally:
        engine.close()


# ---------------------------------------------------------------------------
# Price & book commands
# ---------------------------------------------------------------------------

@main.command()
@click.argument("slug_or_id")
@click.pass_context
def price(ctx: click.Context, slug_or_id: str) -> None:
    """Show YES/NO midpoint prices and spread."""
    engine = _get_engine(ctx)
    try:
        market = engine.api.get_market(slug_or_id)
        yes_mid = engine.api.get_midpoint(market.yes_token_id)
        no_mid = engine.api.get_midpoint(market.no_token_id)
        spread = abs(yes_mid - (1.0 - no_mid)) if yes_mid and no_mid else 0.0
        click.echo(_ok({
            "market": market.slug,
            "question": market.question,
            "yes_price": yes_mid,
            "no_price": no_mid,
            "spread": spread,
        }))
    except SimError as e:
        click.echo(_err(e))
        sys.exit(1)
    finally:
        engine.close()


@main.command()
@click.argument("slug_or_id")
@click.option("--depth", type=int, default=10, help="Number of levels to show.")
@click.pass_context
def book(ctx: click.Context, slug_or_id: str, depth: int) -> None:
    """Show the order book for a market's YES token."""
    engine = _get_engine(ctx)
    try:
        market = engine.api.get_market(slug_or_id)
        ob = engine.api.get_order_book(market.yes_token_id)
        bids = sorted(ob.bids, key=lambda l: l.price, reverse=True)[:depth]
        asks = sorted(ob.asks, key=lambda l: l.price)[:depth]
        click.echo(_ok({
            "market": market.slug,
            "token_id": market.yes_token_id,
            "bids": [{"price": l.price, "size": l.size} for l in bids],
            "asks": [{"price": l.price, "size": l.size} for l in asks],
        }))
    except SimError as e:
        click.echo(_err(e))
        sys.exit(1)
    finally:
        engine.close()


# ---------------------------------------------------------------------------
# Trading commands
# ---------------------------------------------------------------------------

@main.command()
@click.argument("slug_or_id")
@click.argument("outcome")
@click.argument("amount_usd", type=float)
@click.option("--type", "order_type", type=click.Choice(["fok", "fak"]), default="fok")
@click.pass_context
def buy(ctx: click.Context, slug_or_id: str, outcome: str, amount_usd: float, order_type: str) -> None:
    """Buy shares: spend USD, receive shares (walks ask side)."""
    engine = _get_engine(ctx)
    try:
        result = engine.buy(slug_or_id, outcome, amount_usd, order_type)
        click.echo(_ok(result))
    except SimError as e:
        click.echo(_err(e))
        sys.exit(1)
    finally:
        engine.close()


@main.command()
@click.argument("slug_or_id")
@click.argument("outcome")
@click.argument("shares", type=float)
@click.option("--type", "order_type", type=click.Choice(["fok", "fak"]), default="fok")
@click.pass_context
def sell(ctx: click.Context, slug_or_id: str, outcome: str, shares: float, order_type: str) -> None:
    """Sell shares: sell shares, receive USD (walks bid side)."""
    engine = _get_engine(ctx)
    try:
        result = engine.sell(slug_or_id, outcome, shares, order_type)
        click.echo(_ok(result))
    except SimError as e:
        click.echo(_err(e))
        sys.exit(1)
    finally:
        engine.close()


# ---------------------------------------------------------------------------
# Portfolio & history commands
# ---------------------------------------------------------------------------

@main.command()
@click.pass_context
def portfolio(ctx: click.Context) -> None:
    """Show open positions with live prices and unrealized P&L."""
    engine = _get_engine(ctx)
    try:
        data = engine.get_portfolio()
        click.echo(_ok(data))
    except SimError as e:
        click.echo(_err(e))
        sys.exit(1)
    finally:
        engine.close()


@main.command()
@click.option("--limit", type=int, default=50)
@click.pass_context
def history(ctx: click.Context, limit: int) -> None:
    """Show trade history."""
    engine = _get_engine(ctx)
    try:
        trades = engine.get_history(limit)
        click.echo(_ok(trades))
    except SimError as e:
        click.echo(_err(e))
        sys.exit(1)
    finally:
        engine.close()


# ---------------------------------------------------------------------------
# Resolution commands
# ---------------------------------------------------------------------------

@main.command()
@click.argument("slug_or_id", required=False)
@click.option("--all", "resolve_all", is_flag=True, help="Resolve all closed markets.")
@click.pass_context
def resolve(ctx: click.Context, slug_or_id: str | None, resolve_all: bool) -> None:
    """Resolve a market or all closed markets."""
    engine = _get_engine(ctx)
    try:
        if resolve_all:
            results = engine.resolve_all()
        elif slug_or_id:
            results = engine.resolve_market(slug_or_id)
        else:
            click.echo(
                json.dumps(
                    {"ok": False, "error": "Provide a market slug/id or --all", "code": "MISSING_ARGUMENT"},
                    indent=2,
                )
            )
            sys.exit(1)
            return
        click.echo(_ok(results))
    except SimError as e:
        click.echo(_err(e))
        sys.exit(1)
    finally:
        engine.close()
