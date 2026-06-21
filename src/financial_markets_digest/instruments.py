"""Definitions of the market instruments tracked by the digest.

Each :class:`Instrument` maps a human-readable name to a yfinance ticker and an optional
Stooq fallback symbol. Instruments are grouped into sections so the report can render them
in a sensible order. The S&P 500 is flagged with ``compute_ema`` so EMA-20/EMA-200 are
calculated from its history.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class Section(StrEnum):
    """Report section an instrument belongs to."""

    INDEX = "Major Indices"
    FX = "FX & Rates"
    COMMODITY = "Commodities"
    CRYPTO = "Crypto"
    VOLATILITY = "Volatility"


@dataclass(frozen=True)
class Instrument:
    """A single market instrument and where to fetch it from."""

    name: str
    yf_ticker: str
    section: Section
    stooq_symbol: str | None = None
    # Free-text qualifier shown next to the value, e.g. "5y proxy" for yields.
    note: str | None = None
    # Compute and report EMA-20 / EMA-200 (only the S&P 500 today).
    compute_ema: bool = False
    # Decimal places used when formatting this instrument's prices.
    decimals: int = 2


# Order here is the order instruments appear within their section.
INSTRUMENTS: list[Instrument] = [
    # --- Major indices ---
    Instrument("S&P 500", "^GSPC", Section.INDEX, stooq_symbol="^SPX", compute_ema=True),
    Instrument("Nasdaq Composite", "^IXIC", Section.INDEX, stooq_symbol="^NDQ"),
    Instrument("STOXX Europe 600", "^STOXX", Section.INDEX),
    Instrument("Hang Seng", "^HSI", Section.INDEX, stooq_symbol="^HSI"),
    Instrument("Nikkei 225", "^N225", Section.INDEX, stooq_symbol="^NKX"),
    Instrument("KOSPI", "^KS11", Section.INDEX),
    # --- FX & rates ---
    Instrument("EUR/USD", "EURUSD=X", Section.FX, stooq_symbol="EURUSD", decimals=4),
    Instrument("US yield 5y", "^FVX", Section.FX, note="2y proxy"),
    Instrument("US yield 10y", "^TNX", Section.FX),
    Instrument("US yield 30y", "^TYX", Section.FX, note="20y proxy"),
    # --- Commodities ---
    Instrument("Brent crude", "BZ=F", Section.COMMODITY),
    Instrument("Gold", "GC=F", Section.COMMODITY, stooq_symbol="XAUUSD"),
    # --- Crypto ---
    Instrument("Bitcoin", "BTC-USD", Section.CRYPTO, stooq_symbol="BTCUSD"),
    # --- Volatility ---
    Instrument("VIX", "^VIX", Section.VOLATILITY, stooq_symbol="^VIX"),
]
