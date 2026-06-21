"""Entry point: fetch market data, print the digest, and archive a copy.

Run with ``python -m markets_digest`` (or ``uv run python -m markets_digest``).
"""

from __future__ import annotations

from .config import load_watchlist
from .fetch import fetch_quotes, fetch_watch_frames
from .instruments import INSTRUMENTS
from .raws import save_raw
from .report import render
from .watchlist import evaluate


def main() -> None:
    quotes, fetch_notes = fetch_quotes(INSTRUMENTS)

    watch_items = load_watchlist()
    frames, watch_fetch_notes = fetch_watch_frames(watch_items)
    watch_results, watch_eval_notes = evaluate(watch_items, frames)

    notes = fetch_notes + watch_fetch_notes + watch_eval_notes

    text = render(quotes, watch_results, notes)
    print(text)
    path = save_raw(text)
    print(f"[saved] {path}")


if __name__ == "__main__":
    main()
