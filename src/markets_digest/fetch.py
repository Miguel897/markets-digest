"""Data fetching with a yfinance primary source and a Stooq fallback.

Every fetch is wrapped so a single failing ticker never aborts the run; failures are returned
as human-readable notes for the report's "Data notes" section.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import io
import re
import time
import warnings

import pandas as pd
import requests
import yfinance as yf

from .config import WatchItem
from .indicators import Quote, summarize
from .instruments import Instrument

_OHLC_COLUMNS = ["Open", "High", "Low", "Close"]

# Stooq's keyless CSV endpoint: returns Date,Open,High,Low,Close,Volume for a daily series.
_STOOQ_BASE = "https://stooq.com"
_STOOQ_URL = f"{_STOOQ_BASE}/q/d/l/"
_STOOQ_HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
# Stooq guards the endpoint with a JS proof-of-work: the page embeds `c="...",d=N`,
# the client must find n where sha256(c+n) starts with N hex zeros, POST it to /__verify,
# then retry. We solve it once per process and reuse the verified session cookie.
_STOOQ_CHALLENGE_RE = re.compile(r'c="([^"]+)",d=(\d+)')
_stooq_session: requests.Session | None = None


def _solve_stooq_pow(c: str, difficulty: int) -> int:
    target = "0" * difficulty
    n = 0
    while True:
        if hashlib.sha256(f"{c}{n}".encode()).hexdigest().startswith(target):
            return n
        n += 1


def _get_stooq_session() -> requests.Session:
    """Return a session that has cleared Stooq's proof-of-work challenge (solved once)."""
    global _stooq_session
    if _stooq_session is not None:
        return _stooq_session

    session = requests.Session()
    session.headers.update(_STOOQ_HEADERS)
    probe = session.get(_STOOQ_URL, params={"s": "aapl.us", "i": "d"}, timeout=20)
    match = _STOOQ_CHALLENGE_RE.search(probe.text)
    if match:
        c, difficulty = match.group(1), int(match.group(2))
        n = _solve_stooq_pow(c, difficulty)
        session.post(
            f"{_STOOQ_BASE}/__verify",
            data={"c": c, "n": n},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=20,
        )
    _stooq_session = session
    return session


class FetchError(Exception):
    """Raised when an instrument cannot be fetched from any source."""


def _normalize(df: pd.DataFrame) -> pd.DataFrame:
    """Return an ascending-date frame with the four OHLC columns and no empty rows."""
    if df is None or df.empty:
        raise FetchError("empty frame")
    if isinstance(df.columns, pd.MultiIndex):
        # yfinance returns a column MultiIndex when given a list of tickers; flatten it.
        df = df.droplevel(axis=1, level=1)
    missing = [c for c in _OHLC_COLUMNS if c not in df.columns]
    if missing:
        raise FetchError(f"missing columns {missing}")
    # Keep Volume when the source provides it (indices/FX/yields often report 0 or none).
    cols = [*_OHLC_COLUMNS, "Volume"] if "Volume" in df.columns else list(_OHLC_COLUMNS)
    # Drop rows without a Close: everything downstream keys off it, and providers sometimes
    # emit a stub row for the current (unfinished) session with a null close.
    df = df[cols].dropna(subset=["Close"]).sort_index()
    if df.empty:
        raise FetchError("no rows after cleaning")
    return df


def _from_yfinance(ticker: str, period: str) -> pd.DataFrame:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        df = yf.Ticker(ticker).history(period=period, interval="1d", auto_adjust=False)
    return _normalize(df)


def _from_stooq(symbol: str, days: int) -> pd.DataFrame:
    end = dt.date.today()
    start = end - dt.timedelta(days=days)
    params = {
        "s": symbol,
        "i": "d",
        "d1": start.strftime("%Y%m%d"),
        "d2": end.strftime("%Y%m%d"),
    }
    resp = _get_stooq_session().get(_STOOQ_URL, params=params, timeout=20)
    resp.raise_for_status()
    text = resp.text.strip()
    # A CSV reply starts with the "Date,Open,..." header. Anything else (a "No data" line
    # or the HTML anti-bot page) means we have no usable data.
    if not text.lower().startswith("date,"):
        raise FetchError("stooq returned no usable data (empty or blocked)")
    df = pd.read_csv(io.StringIO(text), parse_dates=["Date"], index_col="Date")
    return _normalize(df)


def fetch_ohlc(
    yf_ticker: str,
    stooq_symbol: str | None = None,
    period: str = "1y",
    stooq_days: int = 400,
    retries: int = 3,
) -> tuple[pd.DataFrame, str]:
    """Fetch a daily OHLC frame, trying yfinance (with retries) then Stooq.

    yfinance is the primary source; its main failure mode is transient rate-limiting (HTTP 429),
    so we retry with a short backoff before falling back. Stooq is best-effort: it now guards its
    CSV download behind both a proof-of-work and an IP-level gate, so it often returns "Access
    denied" to automated clients. Raises :class:`FetchError` if every source fails.
    """
    primary_error: Exception | None = None
    for attempt in range(retries):
        try:
            return _from_yfinance(yf_ticker, period), "yfinance"
        except Exception as exc:  # noqa: BLE001 - any failure should retry then fall back
            primary_error = exc
            if attempt < retries - 1:
                time.sleep(1.5 * (attempt + 1))

    if stooq_symbol:
        try:
            return _from_stooq(stooq_symbol, stooq_days), "stooq"
        except Exception as exc:  # noqa: BLE001
            raise FetchError(
                f"yfinance failed ({primary_error}); stooq failed ({exc})"
            ) from exc

    raise FetchError(f"yfinance failed ({primary_error}); no stooq fallback")


def fetch_quotes(instruments: list[Instrument]) -> tuple[list[Quote], list[str]]:
    """Fetch and summarise every instrument. Returns ``(quotes, error_notes)``."""
    quotes: list[Quote] = []
    notes: list[str] = []
    for instr in instruments:
        label = f"{instr.name} ({instr.yf_ticker})"
        try:
            df, source = fetch_ohlc(instr.yf_ticker, instr.stooq_symbol)
            quotes.append(summarize(instr, df, source))
        except FetchError as exc:
            notes.append(f"{label}: {exc}")
    return quotes, notes


def fetch_watch_frames(items: list[WatchItem]) -> tuple[dict[str, pd.DataFrame], list[str]]:
    """Fetch recent closes for each watchlist item. Returns ``(frames_by_ticker, error_notes)``."""
    frames: dict[str, pd.DataFrame] = {}
    notes: list[str] = []
    for item in items:
        label = f"{item.name} ({item.ticker})"
        try:
            df, _ = fetch_ohlc(item.ticker, period="1mo", stooq_days=45)
            frames[item.ticker] = df
        except FetchError as exc:
            notes.append(f"{label}: {exc}")
    return frames, notes
