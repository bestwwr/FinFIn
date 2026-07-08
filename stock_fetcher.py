import yfinance as yf
from datetime import datetime
from typing import List, Dict

INDICES = [
    {"symbol": "^GSPC",  "name": "S&P 500"},
    {"symbol": "^IXIC",  "name": "NASDAQ"},
    {"symbol": "^DJI",   "name": "Dow Jones"},
]

KEY_STOCKS = [
    "AAPL", "MSFT", "NVDA", "AMZN",
    "META", "GOOGL", "TSLA", "PLTR",
]


def _fetch_quote(symbol: str) -> Dict | None:
    try:
        fi = yf.Ticker(symbol).fast_info
        price = fi.last_price
        prev = fi.previous_close
        if price is None or prev is None or prev == 0:
            return None
        change_pct = (price - prev) / prev * 100
        return {"symbol": symbol, "price": price, "change_pct": change_pct}
    except Exception as e:
        print(f"[stock_fetcher] Error fetching {symbol}: {e}")
        return None


def _arrow(pct: float) -> str:
    return "▲" if pct >= 0 else "▼"


def _format_price(symbol: str, price: float) -> str:
    if symbol.startswith("^"):
        return f"{price:,.2f}"
    return f"${price:,.2f}"


def build_stock_snapshot() -> str:
    lines = ["📊 *US Market Snapshot*", ""]

    lines.append("🏛 Indices")
    for idx in INDICES:
        q = _fetch_quote(idx["symbol"])
        if q:
            arrow = _arrow(q["change_pct"])
            price_str = _format_price(idx["symbol"], q["price"])
            lines.append(f"  {idx['name']:<14} {price_str:>12}  {arrow} {q['change_pct']:+.2f}%")
        else:
            lines.append(f"  {idx['name']:<14}  N/A")

    lines.append("")
    lines.append("💎 Key Stocks")
    for sym in KEY_STOCKS:
        q = _fetch_quote(sym)
        if q:
            arrow = _arrow(q["change_pct"])
            price_str = _format_price(sym, q["price"])
            lines.append(f"  {sym:<6} {price_str:>10}  {arrow} {q['change_pct']:+.2f}%")
        else:
            lines.append(f"  {sym:<6}  N/A")

    lines.append("")
    lines.append(f"⏱ อัปเดต: {datetime.now().strftime('%d %b %Y %H:%M')} (Bangkok)")
    lines.append("─" * 36)
    return "\n".join(lines)
