# markets-digest

Console digest of daily financial-market data, designed to be run by a weekday Claude routine.
The script prints a clean, structured, LLM-readable snapshot of global markets to stdout and
archives a copy to `raws/YYYY-MM-DD_raw_financial_data.md`. Claude then combines that output with
internet news to write the final markets digest.

The repo **does not write the prose report** — it only produces the data.

## Data sources (keyless)

- **Primary:** [yfinance](https://github.com/ranaroussi/yfinance) (Yahoo Finance). Fetched with a
  short retry/backoff since its main failure mode is transient rate-limiting (HTTP 429).
- **Fallback (best-effort):** [Stooq](https://stooq.com) CSV endpoint, attempted per-ticker when
  yfinance fails. Stooq now guards downloads behind a JavaScript proof-of-work *and* an IP-level
  gate, so it frequently returns "Access denied" to automated clients — treat it as a bonus, not a
  guarantee.

No API keys are required. A single failing ticker never aborts the run; failures are listed in a
"Data notes" section. If a reliable second source becomes necessary, FRED (free API key) is the
natural addition — it also provides true 2y/20y Treasury yields.

### Coverage

Indices (S&P 500, Nasdaq, STOXX 600, Hang Seng, Nikkei, KOSPI), EUR/USD, US Treasury yields
(5y/10y/30y Yahoo proxies — Yahoo has no true 2y/20y), Brent, gold, Bitcoin and the VIX. The
S&P 500 additionally gets locally computed **EMA-20** and **EMA-200**.

### Watchlist

Securities to follow closely are defined in [`config/watchlist.json`](config/watchlist.json) with a
`[min, max]` price band. When the latest close leaves the band, the digest emits a structured flag
(price, bound breached, % beyond bound, recent direction). In-band items get a one-line OK.

## Usage

```bash
uv sync
uv run python -m markets_digest
```

This prints the digest and writes `raws/YYYY-MM-DD_raw_financial_data.md`.

## Development

```bash
uv run pytest
uv run ruff check .
uv run mypy src
```
