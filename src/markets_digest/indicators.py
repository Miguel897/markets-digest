"""Indicator math and per-instrument quote summarisation.

Pure functions over pandas objects plus a :class:`Quote` dataclass that condenses a daily
OHLC frame into the handful of values the report needs.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from .instruments import Instrument


def ema(close: pd.Series, span: int) -> pd.Series:
    """Exponential moving average over a close-price series."""
    return close.ewm(span=span, adjust=False).mean()


def pct_change(current: float, previous: float) -> float | None:
    """Percentage change from ``previous`` to ``current`` (None if not computable)."""
    if previous == 0:
        return None
    return (current - previous) / previous * 100.0


@dataclass(frozen=True)
class Quote:
    """Condensed daily snapshot for one instrument."""

    instrument: Instrument
    last_date: pd.Timestamp
    open: float
    high: float
    low: float
    close: float
    prev_close: float | None
    source: str
    volume: float | None = None
    ema20: float | None = None
    ema200: float | None = None

    @property
    def day_pct(self) -> float | None:
        """Daily % change vs the previous close."""
        if self.prev_close is None:
            return None
        return pct_change(self.close, self.prev_close)


def summarize(instrument: Instrument, df: pd.DataFrame, source: str) -> Quote:
    """Build a :class:`Quote` from a daily OHLC frame.

    ``df`` must be indexed by date with ``Open/High/Low/Close`` columns and at least one row.
    EMA-20/EMA-200 are filled only when the instrument requests them and enough rows exist.
    """
    last = df.iloc[-1]
    prev_close = float(df["Close"].iloc[-2]) if len(df) >= 2 else None
    volume = float(last["Volume"]) if "Volume" in df.columns else None

    ema20 = ema200 = None
    if instrument.compute_ema:
        close = df["Close"]
        if len(close) >= 20:
            ema20 = float(ema(close, 20).iloc[-1])
        if len(close) >= 200:
            ema200 = float(ema(close, 200).iloc[-1])

    return Quote(
        instrument=instrument,
        last_date=df.index[-1],
        open=float(last["Open"]),
        high=float(last["High"]),
        low=float(last["Low"]),
        close=float(last["Close"]),
        prev_close=prev_close,
        source=source,
        volume=volume,
        ema20=ema20,
        ema200=ema200,
    )
