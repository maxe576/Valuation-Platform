"""Free current-share-price lookup (no API key).

SEC EDGAR provides filings but not market prices, so live valuations need a price
source. Stooq offers a keyless CSV quote endpoint we use here; failures degrade to
None so the analyst can enter the price manually. Cached briefly to avoid
re-fetching on every page rerun.
"""
from __future__ import annotations

from typing import Optional

from config.logging import get_logger
from config.settings import SETTINGS
from services.cache import JsonCache

log = get_logger("price")
_TTL = 900  # 15 minutes


def fetch_price(ticker: str, cache: Optional[JsonCache] = None) -> Optional[float]:
    """Return the latest close for a US ticker, or None if unavailable."""
    ticker = ticker.upper().strip()
    cache = cache or JsonCache()
    url = f"https://stooq.com/q/l/?s={ticker}.us&f=sd2t2ohlcv&h&e=csv"

    cached = cache.get(url, ttl_seconds=_TTL)
    if cached is not None:
        return cached

    try:
        import requests

        resp = requests.get(url, timeout=SETTINGS.request_timeout_seconds)
        resp.raise_for_status()
        lines = resp.text.strip().splitlines()
        if len(lines) < 2:
            return None
        header = lines[0].split(",")
        row = lines[1].split(",")
        rec = dict(zip(header, row))
        close = rec.get("Close")
        if close in (None, "", "N/D"):
            return None
        price = float(close)
        cache.set(url, price)
        return price
    except Exception as exc:  # noqa: BLE001 — degrade gracefully to manual entry
        log.warning("Price fetch failed for %s: %s", ticker, exc)
        return None
