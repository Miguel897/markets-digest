"""Loading of the user-defined watchlist from ``config/watchlist.json``."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

# config/ sits at the repo root, two levels up from this file
# (src/financial_markets_digest/config.py -> repo root).
_REPO_ROOT = Path(__file__).resolve().parents[2]
WATCHLIST_PATH = _REPO_ROOT / "config" / "watchlist.json"


@dataclass(frozen=True)
class WatchItem:
    """A security followed closely with a ``[min, max]`` price band."""

    name: str
    ticker: str
    currency: str
    min: float
    max: float


def load_watchlist(path: Path | None = None) -> list[WatchItem]:
    """Read and validate the watchlist JSON file.

    Returns an empty list if the file is missing, so the digest still runs.
    """
    path = path or WATCHLIST_PATH
    if not path.exists():
        return []

    raw = json.loads(path.read_text(encoding="utf-8"))
    items: list[WatchItem] = []
    for entry in raw:
        items.append(
            WatchItem(
                name=str(entry["name"]),
                ticker=str(entry["ticker"]),
                currency=str(entry.get("currency", "")),
                min=float(entry["min"]),
                max=float(entry["max"]),
            )
        )
    return items
