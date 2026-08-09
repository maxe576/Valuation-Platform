"""SEC XBRL 'frames' API client — one concept across ALL filers for a period.

The frames endpoint returns a single concept's value for every company that
reported it in a given period, e.g. all filers' Revenues for CY2023. A handful of
these calls assembles market-wide fundamentals for the screener — free, no key.

Docs: https://www.sec.gov/edgar/sec-api-documentation
"""
from __future__ import annotations

import time
from typing import Any, Callable, Optional

from config.logging import get_logger
from config.settings import SETTINGS
from services.cache import JsonCache

log = get_logger("sec_frames")

_FRAME_URL = "https://data.sec.gov/api/xbrl/frames/{taxonomy}/{tag}/{unit}/{period}.json"
_TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
_FRAME_TTL = 24 * 3600
_TICKERS_TTL = 24 * 3600


def _requests_fetch(url: str, headers: dict, timeout: float) -> Any:
    import requests

    resp = requests.get(url, headers=headers, timeout=timeout)
    if resp.status_code == 404:
        return None  # concept/period not available — a normal, expected case
    resp.raise_for_status()
    return resp.json()


class SECFramesClient:
    def __init__(
        self,
        user_agent: Optional[str] = None,
        cache: Optional[JsonCache] = None,
        fetch_json: Optional[Callable[[str, dict, float], Any]] = None,
        min_interval_seconds: float = 0.15,
    ) -> None:
        self.user_agent = user_agent or SETTINGS.sec_user_agent
        self.cache = cache or JsonCache()
        self._fetch = fetch_json or _requests_fetch
        self.min_interval = min_interval_seconds
        self._last = 0.0

    def _headers(self) -> dict:
        return {"User-Agent": self.user_agent, "Accept-Encoding": "gzip, deflate"}

    def _throttle(self) -> None:
        dt = time.monotonic() - self._last
        if dt < self.min_interval:
            time.sleep(self.min_interval - dt)
        self._last = time.monotonic()

    def _get(self, url: str, ttl: float) -> Any:
        cached = self.cache.get(url, ttl_seconds=ttl)
        if cached is not None:
            return cached
        self._throttle()
        try:
            data = self._fetch(url, self._headers(), SETTINGS.request_timeout_seconds)
        except Exception as exc:  # noqa: BLE001 — degrade gracefully
            log.warning("frames fetch failed (%s): %s", url, exc)
            return None
        if data is not None:
            self.cache.set(url, data)
        return data

    def frame(self, tag: str, unit: str, period: str,
              taxonomy: str = "us-gaap") -> dict[int, float]:
        """Return ``{cik: value}`` for a concept/period, or empty on miss."""
        url = _FRAME_URL.format(taxonomy=taxonomy, tag=tag, unit=unit, period=period)
        data = self._get(url, _FRAME_TTL)
        out: dict[int, float] = {}
        if not data or "data" not in data:
            return out
        for row in data["data"]:
            cik = row.get("cik")
            val = row.get("val")
            if cik is not None and val is not None:
                out[int(cik)] = float(val)
        return out

    def merged_frame(self, tags: list[str], unit: str, period: str) -> dict[int, float]:
        """Merge several candidate tags (first tag wins per CIK) — for concepts
        companies report under different tags (e.g. revenue)."""
        out: dict[int, float] = {}
        for tag in tags:
            for cik, val in self.frame(tag, unit, period).items():
                out.setdefault(cik, val)
        return out

    def cik_to_ticker(self) -> dict[int, dict]:
        """Return ``{cik: {ticker, name}}`` from SEC's company_tickers.json."""
        data = self._get(_TICKERS_URL, _TICKERS_TTL)
        out: dict[int, dict] = {}
        if not data:
            return out
        rows = data.values() if isinstance(data, dict) else data
        for row in rows:
            cik = row.get("cik_str")
            if cik is not None:
                # First ticker listed for a CIK wins (usually the primary).
                out.setdefault(int(cik), {"ticker": str(row.get("ticker", "")).upper(),
                                          "name": row.get("title", "")})
        return out
