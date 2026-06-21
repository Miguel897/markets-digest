import pandas as pd
import pytest

from markets_digest.indicators import ema, pct_change, summarize
from markets_digest.instruments import Instrument, Section


def _frame(closes: list[float]) -> pd.DataFrame:
    idx = pd.date_range("2026-01-01", periods=len(closes), freq="D")
    return pd.DataFrame(
        {"Open": closes, "High": closes, "Low": closes, "Close": closes}, index=idx
    )


def test_ema_matches_recursive_definition() -> None:
    s = pd.Series([1.0, 2.0, 3.0, 4.0, 5.0])
    span = 3
    alpha = 2 / (span + 1)
    expected = [1.0]
    for x in s.iloc[1:]:
        expected.append(alpha * x + (1 - alpha) * expected[-1])
    assert ema(s, span).tolist() == pytest.approx(expected)


def test_ema_of_constant_series_is_constant() -> None:
    s = pd.Series([7.0] * 50)
    assert ema(s, 20).iloc[-1] == pytest.approx(7.0)


def test_pct_change_basic() -> None:
    assert pct_change(110, 100) == pytest.approx(10.0)
    assert pct_change(90, 100) == pytest.approx(-10.0)
    assert pct_change(5, 0) is None


def test_summarize_fills_emas_only_with_enough_history() -> None:
    instr = Instrument("S&P 500", "^GSPC", Section.INDEX, compute_ema=True)

    short = summarize(instr, _frame(list(range(1, 11))), "test")  # 10 rows
    assert short.ema20 is None
    assert short.ema200 is None
    assert short.prev_close == 9.0
    assert short.day_pct == pytest.approx((10 - 9) / 9 * 100)

    long = summarize(instr, _frame([100.0] * 250), "test")  # 250 rows
    assert long.ema20 == pytest.approx(100.0)
    assert long.ema200 == pytest.approx(100.0)


def test_summarize_without_ema_flag() -> None:
    instr = Instrument("VIX", "^VIX", Section.VOLATILITY)
    q = summarize(instr, _frame([100.0] * 250), "test")
    assert q.ema20 is None
    assert q.ema200 is None
