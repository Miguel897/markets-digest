"""Archiving of the rendered digest to the ``raws/`` folder."""

from __future__ import annotations

import datetime as dt
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
RAWS_DIR = _REPO_ROOT / "raws"


def save_raw(text: str, date: dt.date | None = None, raws_dir: Path | None = None) -> Path:
    """Write ``text`` to ``raws/YYYY-MM-DD_raw_financial_data.md`` and return the path.

    Overwrites an existing file for the same day so re-runs stay idempotent.
    """
    date = date or dt.date.today()
    raws_dir = raws_dir or RAWS_DIR
    raws_dir.mkdir(parents=True, exist_ok=True)
    path = raws_dir / f"{date.isoformat()}_raw_financial_data.md"
    path.write_text(text, encoding="utf-8")
    return path
