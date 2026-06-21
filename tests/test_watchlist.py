import pandas as pd
import pytest

from financial_markets_digest.config import WatchItem
from financial_markets_digest.watchlist import BandStatus, evaluate


def _frame(closes: list[float]) -> pd.DataFrame:
    idx = pd.date_range("2026-01-01", periods=len(closes), freq="D")
    return pd.DataFrame(
        {"Open": closes, "High": closes, "Low": closes, "Close": closes}, index=idx
    )


def _item(min_: float, max_: float) -> WatchItem:
    return WatchItem(name="Test", ticker="TST", currency="USD", min=min_, max=max_)


def test_in_band() -> None:
    items = [_item(70, 80)]
    frames = {"TST": _frame([75.0] * 10)}
    results, notes = evaluate(items, frames)
    assert notes == []
    assert results[0].status is BandStatus.IN
    assert results[0].out_of_band is False
    assert results[0].pct_beyond is None


def test_above_band_reports_percent_beyond_ceiling() -> None:
    items = [_item(70, 80)]
    frames = {"TST": _frame([88.0] * 10)}
    (result,), _ = evaluate(items, frames)
    assert result.status is BandStatus.ABOVE
    assert result.out_of_band is True
    assert result.pct_beyond == pytest.approx((88 - 80) / 80 * 100)


def test_below_band_reports_negative_percent() -> None:
    items = [_item(70, 80)]
    frames = {"TST": _frame([63.0] * 10)}
    (result,), _ = evaluate(items, frames)
    assert result.status is BandStatus.BELOW
    assert result.pct_beyond == pytest.approx((63 - 70) / 70 * 100)
    assert result.pct_beyond is not None and result.pct_beyond < 0


def test_trend_5d_computed_when_enough_history() -> None:
    items = [_item(70, 80)]
    closes = [70, 71, 72, 73, 74, 77]  # 6 points -> 5-session change exists
    frames = {"TST": _frame([float(c) for c in closes])}
    (result,), _ = evaluate(items, frames)
    assert result.trend_5d == pytest.approx((77 - 70) / 70 * 100)


def test_missing_frame_produces_note_not_result() -> None:
    items = [_item(70, 80)]
    results, notes = evaluate(items, {})
    assert results == []
    assert len(notes) == 1
    assert "no data" in notes[0]
