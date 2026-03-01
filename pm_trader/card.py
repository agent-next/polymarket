"""Shareable stats cards for social platforms.

Generates formatted trading performance cards optimized for:
- X/Twitter (280 chars, hashtags, engagement bait)
- Chat apps (Telegram, Discord, WhatsApp — markdown)
- Plain text (fallback)
"""

from __future__ import annotations


def _roi_icon(roi: float) -> str:
    """Pick emoji based on ROI performance."""
    if roi > 20:
        return "🔥"
    if roi > 10:
        return "🚀"
    if roi > 0:
        return "📈"
    if roi == 0:
        return "➖"
    if roi > -10:
        return "📉"
    return "💀"


def _extract(stats: dict) -> dict:
    """Extract and format common fields from stats dict."""
    roi = stats.get("roi_pct", 0.0)
    pnl = stats.get("pnl", 0.0)
    return {
        "roi": roi,
        "pnl": pnl,
        "total": stats.get("total_value", 0.0),
        "sharpe": stats.get("sharpe_ratio", 0.0),
        "win": stats.get("win_rate", 0.0),
        "trades": stats.get("total_trades", 0),
        "dd": stats.get("max_drawdown", 0.0),
        "fees": stats.get("total_fees", 0.0),
        "starting": stats.get("starting_balance", 0.0),
        "icon": _roi_icon(roi),
        "pnl_sign": "+" if pnl >= 0 else "",
        "roi_sign": "+" if roi >= 0 else "",
    }


def generate_tweet(stats: dict, account: str = "default") -> str:
    """Generate a tweet-optimized card (< 280 chars).

    Designed for X/Twitter sharing. Compact, eye-catching, with hashtags.
    """
    s = _extract(stats)

    lines = [
        f"{s['icon']} My AI agent's Polymarket results:",
        "",
        f"ROI: {s['roi_sign']}{s['roi']:.1f}%",
        f"P&L: {s['pnl_sign']}${s['pnl']:,.0f}",
        f"Sharpe: {s['sharpe']:.2f} | Win: {s['win'] * 100:.0f}% | {s['trades']} trades",
        "",
        "Paper trading with real order books, zero risk",
        "",
        "#Polymarket #AITrading #PredictionMarkets",
        "npx clawhub install polymarket-paper-trader",
    ]

    return "\n".join(lines)


def generate_card(stats: dict, account: str = "default") -> str:
    """Generate a chat-optimized card with markdown.

    For Telegram, Discord, Slack — supports bold/italic.
    """
    s = _extract(stats)

    lines = [
        f"{s['icon']} *Polymarket Paper Trading*",
        "",
        f"ROI: *{s['roi_sign']}{s['roi']:.1f}%* | Sharpe: *{s['sharpe']:.2f}*",
        f"Win Rate: *{s['win'] * 100:.0f}%* | Trades: *{s['trades']}*",
        f"Max DD: *{s['dd'] * 100:.1f}%* | Fees: *${s['fees']:.2f}*",
        "",
        f"P&L: *{s['pnl_sign']}${s['pnl']:,.2f}*",
        f"Portfolio: *${s['total']:,.2f}* (started ${s['starting']:,.0f})",
        "",
        "`npx clawhub install polymarket-paper-trader`",
    ]

    return "\n".join(lines)


def generate_card_plain(stats: dict, account: str = "default") -> str:
    """Generate a plain-text card (no markdown)."""
    s = _extract(stats)

    lines = [
        f"{s['icon']} Polymarket Paper Trading",
        "",
        f"  ROI:       {s['roi_sign']}{s['roi']:.1f}%",
        f"  Sharpe:    {s['sharpe']:.2f}",
        f"  Win Rate:  {s['win'] * 100:.0f}%",
        f"  Trades:    {s['trades']}",
        f"  Max DD:    {s['dd'] * 100:.1f}%",
        f"  Fees:      ${s['fees']:.2f}",
        "",
        f"  P&L:       {s['pnl_sign']}${s['pnl']:,.2f}",
        f"  Portfolio: ${s['total']:,.2f}",
        "",
        "npx clawhub install polymarket-paper-trader",
    ]

    return "\n".join(lines)
