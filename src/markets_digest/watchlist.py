"""Evaluation of watchlist securities against their ``[min, max]`` price bands.

Produces structured, prose-free results: the digest reports the numbers and Claude writes the
analysis. A breach reports which bound was crossed, how far beyond it the price is, and the
recent direction.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

import pandas as pd

from .config import WatchItem
from .indicators import pct_change


class BandStatus(StrEnum):
    BELOW = "BELOW band"
    IN = "in band"
    ABOVE = "ABOVE band"


@dataclass(frozen=True)
class WatchResult:
    item: WatchItem
    last_date: pd.Timestamp
    close: float
    status: BandStatus
    # Percent beyond the breached bound (positive); None when in band.
    pct_beyond: float | None
    # Percent change over roughly the last 5 sessions; None if not computable.
    trend_5d: float | None

    @property
    def out_of_band(self) -> bool:
        return self.status is not BandStatus.IN


def _trend(close: pd.Series, sessions: int = 5) -> float | None:
    if len(close) <= sessions:
        return None
    return pct_change(float(close.iloc[-1]), float(close.iloc[-1 - sessions]))


def evaluate(
    items: list[WatchItem], frames: dict[str, pd.DataFrame]
) -> tuple[list[WatchResult], list[str]]:
    """Evaluate each item whose frame was fetched. Returns ``(results, missing_notes)``."""
    results: list[WatchResult] = []
    notes: list[str] = []
    for item in items:
        df = frames.get(item.ticker)
        if df is None:
            notes.append(f"{item.name} ({item.ticker}): no data")
            continue

        close_series = df["Close"]
        close = float(close_series.iloc[-1])

        if close < item.min:
            status = BandStatus.BELOW
            pct_beyond = pct_change(close, item.min)  # negative: below the floor
        elif close > item.max:
            status = BandStatus.ABOVE
            pct_beyond = pct_change(close, item.max)  # positive: above the ceiling
        else:
            status = BandStatus.IN
            pct_beyond = None

        results.append(
            WatchResult(
                item=item,
                last_date=df.index[-1],
                close=close,
                status=status,
                pct_beyond=pct_beyond,
                trend_5d=_trend(close_series),
            )
        )
    return results, notes
