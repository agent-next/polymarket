---
name: polymarket-paper-trader
description: "Paper trading on Polymarket — trade prediction markets with real order books, zero risk. Built for AI agents. MCP server, backtesting, strategy PK, shareable stats cards."
version: 0.1.2
metadata:
  clawdbot:
    requires:
      bins:
        - pm-trader-mcp
        - python3
    install:
      - kind: uv
        package: polymarket-paper-trader
        bins: [pm-trader, pm-trader-mcp]
    emoji: "🎯"
    homepage: "https://github.com/agent-next/polymarket-paper-trader"
    tags:
      - finance
      - trading
      - polymarket
      - prediction-markets
      - paper-trading
      - backtesting
      - mcp
---

# polymarket-paper-trader

Paper trading simulator for [Polymarket](https://polymarket.com) prediction markets. Executes trades against **live order books** — real prices, real slippage, real fees — without risking real money.

Part of [agent-next](https://github.com/agent-next) — open research lab for self-evolving autonomous agents.

## What you can do

You have a full paper trading account on Polymarket. You can:

- **Search and browse** active prediction markets (politics, crypto, sports, AI, etc.)
- **Buy and sell** outcome shares at live market prices
- **Place limit orders** (GTC/GTD) that trigger when prices reach your target
- **Track your portfolio** with live P&L, unrealized gains, and position values
- **Analyze performance** — Sharpe ratio, win rate, max drawdown, ROI
- **Resolve markets** when outcomes are determined — winners get $1/share

## Getting started

First, initialize your paper trading account:

```
init_account with balance 10000
```

Then explore markets:

```
search_markets "bitcoin"
list_markets with sort_by "liquidity"
```

## Trading

Buy $100 of YES shares on a market:

```
buy slug="will-bitcoin-hit-100k" outcome="yes" amount_usd=100
```

Sell shares when you want to take profit or cut losses:

```
sell slug="will-bitcoin-hit-100k" outcome="yes" shares=50
```

## Limit orders

Place a limit buy that triggers when the price drops:

```
place_limit_order slug="will-bitcoin-hit-100k" outcome="yes" side="buy" amount=200 limit_price=0.40
```

Check and execute pending orders:

```
check_orders
```

## Monitor and analyze

```
portfolio          — see all open positions with live prices
get_balance        — cash + positions value + total P&L
stats              — Sharpe ratio, win rate, drawdown, ROI
history            — recent trade log
watch_prices       — monitor live prices for specific markets
```

## Share your results

Generate a stats card to share on X/Twitter:

```
stats_card format="tweet"
```

Or for Telegram/Discord:

```
stats_card format="markdown"
```

The tweet format includes hashtags and install link — ready to post.

## How it works

- Trades execute against **real Polymarket order books** fetched live via API
- The order book is walked level-by-level, calculating exact average price and slippage
- Fees follow the exact Polymarket formula: `(bps/10000) * min(price, 1-price) * shares`
- All data stored locally in SQLite — your trading history is yours
- Multi-account support — run separate strategies in parallel

## Tools reference

| Tool | Purpose |
|------|---------|
| `init_account` | Create paper account with starting balance |
| `get_balance` | Cash, positions value, total P&L |
| `reset_account` | Wipe all data and start fresh |
| `search_markets` | Full-text search for markets |
| `list_markets` | Browse markets sorted by volume/liquidity |
| `get_market` | Detailed market info |
| `get_order_book` | Live order book snapshot |
| `watch_prices` | Monitor midpoint prices |
| `buy` | Buy outcome shares (FOK or FAK) |
| `sell` | Sell outcome shares |
| `portfolio` | Open positions with live valuations |
| `history` | Recent trade log |
| `place_limit_order` | GTC/GTD limit order |
| `list_orders` | Pending limit orders |
| `cancel_order` | Cancel a pending order |
| `check_orders` | Execute pending orders against live prices |
| `stats` | Performance analytics |
| `stats_card` | Shareable stats card (tweet, markdown, plain) |
| `resolve` | Resolve a closed market |
| `resolve_all` | Resolve all closed markets |
| `backtest` | Backtest a strategy against historical snapshots |

## Security & Privacy

- **No real money involved** — this is paper trading only
- **No authentication required** — uses public Polymarket API endpoints only
- **Data stays local** — all trades stored in local SQLite database at `~/.pm-trader/`
- **Network access** — reads from `gamma-api.polymarket.com` (market data) and `clob.polymarket.com` (order books, prices)

## External Endpoints

| Endpoint | Data Sent | Purpose |
|----------|-----------|---------|
| `gamma-api.polymarket.com` | Market slug/query | Fetch market metadata |
| `clob.polymarket.com` | Token ID | Fetch order books, midpoints, fee rates |

No user credentials, API keys, or personal data are transmitted.

## Source

[github.com/agent-next/polymarket-paper-trader](https://github.com/agent-next/polymarket-paper-trader) — MIT License, 528 tests, 100% coverage.
