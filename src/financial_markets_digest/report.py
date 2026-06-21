"""Rendering of the digest from fetched quotes and watchlist results.

Output uses Markdown tables so it is easy to read and reliable for an LLM to parse. The module
returns a single string; printing and archiving happen in ``__main__``.
"""

from __future__ import annotations

import datetime as dt
import math

from .indicators import Quote
from .instruments import Section
from .watchlist import WatchResult


def _fmt(value: float | None, decimals: int = 2) -> str:
    """Format a number with thousands separators, or ``n/a`` for None/NaN."""
    if value is None or math.isnan(value):
        return "n/a"
    return f"{value:,.{decimals}f}"


def _fmt_pct(value: float | None, decimals: int = 2) -> str:
    if value is None or math.isnan(value):
        return "n/a"
    return f"{value:+.{decimals}f}%"


def _fmt_int(value: float | None) -> str:
    """Format an integer-ish value (e.g. volume); treat None/NaN/0 as ``n/a``."""
    if value is None or math.isnan(value) or value == 0:
        return "n/a"
    return f"{value:,.0f}"


def _md_table(headers: list[str], aligns: list[str], rows: list[list[str]]) -> list[str]:
    """Render a Markdown table. ``aligns`` entries are 'l' (left) or 'r' (right)."""
    sep = {"l": "---", "r": "---:"}
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(sep[a] for a in aligns) + " |",
    ]
    lines.extend("| " + " | ".join(row) + " |" for row in rows)
    return lines


def _quote_table(quotes: list[Quote]) -> list[str]:
    headers = ["Instrument", "Close", "Day%", "Open", "High", "Low", "Volume", "Date", "Src"]
    aligns = ["l", "r", "r", "r", "r", "r", "r", "l", "l"]
    rows: list[list[str]] = []
    for q in quotes:
        d = q.instrument.decimals
        name = q.instrument.name
        if q.instrument.note:
            name = f"{name} ({q.instrument.note})"
        rows.append(
            [
                name,
                _fmt(q.close, d),
                _fmt_pct(q.day_pct),
                _fmt(q.open, d),
                _fmt(q.high, d),
                _fmt(q.low, d),
                _fmt_int(q.volume),
                q.last_date.date().isoformat(),
                q.source,
            ]
        )
    return _md_table(headers, aligns, rows)


def _section_block(title: str, quotes: list[Quote]) -> list[str]:
    rows = [q for q in quotes if q.instrument.section.value == title]
    if not rows:
        return []
    return [f"## {title}", *_quote_table(rows), ""]


def _sp500_focus(quotes: list[Quote]) -> list[str]:
    sp = next((q for q in quotes if q.instrument.compute_ema), None)
    if sp is None:
        return []

    rows: list[list[str]] = [
        ["Last close", _fmt(sp.close), f"as of {sp.last_date.date().isoformat()}"],
    ]
    for span, value in (("EMA-20", sp.ema20), ("EMA-200", sp.ema200)):
        if value is None:
            rows.append([span, "n/a", "insufficient history"])
            continue
        side = "ABOVE" if sp.close >= value else "BELOW"
        dist = (sp.close - value) / value * 100.0
        rows.append([span, _fmt(value), f"close {side}, {dist:+.2f}%"])

    if sp.ema20 is not None and sp.ema200 is not None:
        regime = "EMA-20 > EMA-200 (bullish)" if sp.ema20 >= sp.ema200 else (
            "EMA-20 < EMA-200 (bearish)"
        )
        rows.append(["Trend regime", "-", regime])

    table = _md_table(["Metric", "Value", "Note"], ["l", "r", "l"], rows)
    return ["## S&P 500 focus", *table, ""]


def _watchlist_row(r: WatchResult) -> list[str]:
    band = f"{_fmt(r.item.min)} - {_fmt(r.item.max)}"
    return [
        r.item.name,
        r.item.ticker,
        _fmt(r.close),
        r.item.currency,
        band,
        r.status.value,
        _fmt_pct(r.pct_beyond),
        _fmt_pct(r.trend_5d),
        r.last_date.date().isoformat(),
    ]


def _watchlist_block(results: list[WatchResult]) -> list[str]:
    lines = ["## Watchlist"]
    if not results:
        lines.extend(["(no watchlist items evaluated)", ""])
        return lines

    flagged = [r for r in results if r.out_of_band]
    ok = [r for r in results if not r.out_of_band]
    headers = ["Security", "Ticker", "Last", "Cur", "Band", "Status", "% vs bound", "5d", "Date"]
    aligns = ["l", "l", "r", "l", "r", "l", "r", "r", "l"]

    if flagged:
        lines.append("FLAGGED - price outside its [min, max] band:")
        lines.extend(_md_table(headers, aligns, [_watchlist_row(r) for r in flagged]))
        lines.append("")
    else:
        lines.extend(["No securities outside their bands.", ""])

    if ok:
        lines.append("In band:")
        lines.extend(_md_table(headers, aligns, [_watchlist_row(r) for r in ok]))
        lines.append("")
    return lines


def render(
    quotes: list[Quote],
    watch_results: list[WatchResult],
    notes: list[str],
    now: dt.datetime | None = None,
) -> str:
    """Build the full digest text."""
    now = now or dt.datetime.now()
    out: list[str] = [
        "# Financial Markets Digest - Raw Data",
        "",
        f"Generated: {now.strftime('%Y-%m-%d %H:%M')} local",
        "",
        "Per-row dates reflect each market's latest session (different time zones).",
        "",
    ]

    out += _section_block(Section.INDEX.value, quotes)
    out += _sp500_focus(quotes)
    out += _section_block(Section.FX.value, quotes)
    out += _section_block(Section.COMMODITY.value, quotes)
    out += _section_block(Section.CRYPTO.value, quotes)
    out += _section_block(Section.VOLATILITY.value, quotes)
    out += _watchlist_block(watch_results)

    if notes:
        out.append("## Data notes")
        out.extend(f"  ! {n}" for n in notes)
        out.append("")

    return "\n".join(out).rstrip() + "\n"
