# pm-sim

Paper trading simulator for [Polymarket](https://polymarket.com), built for AI agents.

Executes trades against **live Polymarket order books** without risking real money. Walks the book level-by-level, calculates exact fees and slippage, and tracks P&L in a local SQLite database.

## Install

```bash
pip install -e .

# dev dependencies (tests)
pip install -e ".[dev]"
```

Requires Python 3.10+.

## Quick start

```bash
# Initialize with $10k paper balance
pm-sim init --balance 10000

# Browse markets
pm-sim markets list --sort liquidity
pm-sim markets search "bitcoin"

# Trade
pm-sim buy will-bitcoin-hit-100k yes 100      # buy $100 of YES
pm-sim sell will-bitcoin-hit-100k yes 50       # sell 50 shares

# Check portfolio and P&L
pm-sim portfolio
pm-sim stats
```

## CLI commands

| Command | Description |
|---------|-------------|
| `init [--balance N]` | Create paper trading account |
| `balance` | Show cash, positions value, total P&L |
| `reset --confirm` | Wipe all data |
| `markets list [--limit N] [--sort volume\|liquidity]` | Browse active markets |
| `markets search QUERY` | Full-text market search |
| `markets get SLUG` | Market details |
| `price SLUG` | YES/NO midpoints and spread |
| `book SLUG [--depth N]` | Order book snapshot |
| `watch SLUG [SLUG...] [--outcome yes\|no]` | Monitor live prices |
| `buy SLUG OUTCOME AMOUNT [--type fok\|fak]` | Buy shares (walks ask side) |
| `sell SLUG OUTCOME SHARES [--type fok\|fak]` | Sell shares (walks bid side) |
| `portfolio` | Open positions with live prices |
| `history [--limit N]` | Trade history |
| `orders place SLUG OUTCOME SIDE AMOUNT PRICE` | Limit order (GTC/GTD) |
| `orders list` | Pending limit orders |
| `orders cancel ID` | Cancel a limit order |
| `orders check` | Fill limit orders if price crosses |
| `stats` | Sharpe ratio, win rate, max drawdown, ROI |
| `export trades [--format csv\|json]` | Export trade history |
| `export positions [--format csv\|json]` | Export positions |
| `benchmark run MODULE.FUNC` | Run a trading strategy |
| `benchmark compare ACCT1 ACCT2` | Compare account performance |
| `accounts list` | List named accounts |
| `accounts create NAME` | Create account for A/B testing |
| `mcp` | Start MCP server (stdio transport) |

Global flags: `--data-dir PATH`, `--account NAME` (or env vars `PM_SIM_DATA_DIR`, `PM_SIM_ACCOUNT`).

## MCP server

pm-sim exposes 23 tools via the [Model Context Protocol](https://modelcontextprotocol.io) for direct AI agent integration:

```bash
pm-sim-mcp  # starts on stdio
```

Add to your Claude Code config:

```json
{
  "mcpServers": {
    "pm-sim": {
      "command": "pm-sim-mcp"
    }
  }
}
```

Tools: `init_account`, `get_balance`, `buy`, `sell`, `portfolio`, `history`, `place_limit_order`, `list_orders`, `cancel_order`, `check_orders`, `stats`, `resolve`, `resolve_all`, `search_markets`, `list_markets`, `get_market`, `get_order_book`, `watch_prices`, `reset_account`, `backtest`.

## How it works

1. **Live order books** — Fetches real-time asks/bids from the Polymarket CLOB API
2. **Level-by-level execution** — Walks the book like a real order, consuming liquidity at each price level
3. **Exact fee model** — Polymarket's formula: `(bps/10000) * min(price, 1-price) * shares`
4. **Slippage tracking** — Records deviation from midpoint in basis points
5. **Order types** — FOK (fill-or-kill), FAK (fill-and-kill / partial), limit GTC/GTD

All state lives in `~/.pm-sim/<account>/paper.db` (SQLite, WAL mode).

## Multi-account support

Run parallel strategies with isolated accounts:

```bash
pm-sim --account aggressive init --balance 5000
pm-sim --account conservative init --balance 5000

pm-sim --account aggressive buy some-market yes 500
pm-sim --account conservative buy some-market yes 100

pm-sim benchmark compare aggressive conservative
```

## Backtesting

Replay historical price data through a strategy:

```python
# my_strat.py
def momentum(engine, snapshot, prices):
    """Buy when price rises above 0.6."""
    if snapshot.midpoint > 0.6:
        engine.buy(snapshot.market_slug, snapshot.outcome, 50.0)
```

```bash
pm-sim benchmark run my_strat.momentum
```

Data format (CSV):
```
timestamp,market_slug,outcome,midpoint
2026-01-01T00:00:00Z,will-x-happen,yes,0.65
2026-01-01T01:00:00Z,will-x-happen,yes,0.68
```

## Analytics

```bash
pm-sim stats
```

Returns: Sharpe ratio, win rate, max drawdown, ROI%, total P&L, trade counts, fee totals, average trade size.

## Project structure

```
pm_sim/
  cli.py          # Click CLI (30+ commands)
  mcp_server.py   # FastMCP server (23 tools)
  engine.py       # Core orchestration
  api.py          # Polymarket HTTP client (Gamma + CLOB APIs)
  orderbook.py    # Order book simulation engine
  orders.py       # Limit order state machine
  analytics.py    # Performance metrics
  backtest.py     # Historical replay engine
  benchmark.py    # Strategy runner & comparison
  db.py           # SQLite persistence layer
  models.py       # Dataclasses and error types
  export.py       # CSV/JSON export
```

## Tests

```bash
pytest                           # 451 tests, 100% coverage
pytest tests/test_e2e_live.py    # live API integration tests
```

## License

MIT
