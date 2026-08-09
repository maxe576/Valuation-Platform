"""FRED macro data (§7) — risk-free rate for the WACC builder.

Fetches the latest observation of a FRED series (e.g. 10-year Treasury, DGS10).
A free FRED key enables live values; without one, callers fall back to a sensible
recent default so WACC still computes.
"""
from __future__ import annotations

from typing import Optional

from config.logging import get_logger
from config.settings import SETTINGS
from services.cache import JsonCache

log = get_logger("fred_client")

_URL = "https://api.stlouisfed.org/fred/series/observations"
_TTL = 12 * 3600

# Reasonable fallbacks when FRED isn't configured (recent levels).
DEFAULT_RISK_FREE = 0.043       # 10-year Treasury ~4.3%
TEN_YEAR_TREASURY = "DGS10"


class FREDClient:
    def __init__(self, api_key: Optional[str] = None,
                 cache: Optional[JsonCache] = None, fetch_json=None) -> None:
        self.api_key = api_key if api_key is not None else SETTINGS.fred_api_key
        self.cache = cache or JsonCache()
        self._fetch = fetch_json

    @property
    def enabled(self) -> bool:
        return bool(self.api_key)

    def latest_value(self, series_id: str) -> Optional[float]:
        if not self.enabled:
            return None
        url = (f"{_URL}?series_id={series_id}&api_key={self.api_key}"
               f"&file_type=json&sort_order=desc&limit=1")
        cached = self.cache.get(url, ttl_seconds=_TTL)
        data = cached
        if data is None:
            try:
                import requests

                if self._fetch:
                    data = self._fetch(url)
                else:
                    resp = requests.get(url, timeout=SETTINGS.request_timeout_seconds)
                    resp.raise_for_status()
                    data = resp.json()
                self.cache.set(url, data)
            except Exception as exc:  # noqa: BLE001
                log.warning("FRED fetch failed (%s): %s", series_id, exc)
                return None
        try:
            obs = data["observations"][0]["value"]
            return float(obs) / 100.0   # FRED reports percent
        except (KeyError, IndexError, ValueError, TypeError):
            return None

    def risk_free_rate(self) -> float:
        """10-year Treasury yield as a decimal; falls back to a recent default."""
        v = self.latest_value(TEN_YEAR_TREASURY)
        return v if v is not None else DEFAULT_RISK_FREE
