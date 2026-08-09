"""Financial Modeling Prep adapter (§6) — an OPTIONAL convenience source.

FMP is never the sole source of statements, and the app must keep working when
FMP is unavailable or an endpoint isn't in the current plan. Every method returns
``None``/``[]`` gracefully when no key is configured or a request fails, so
callers can fall back to SEC / analyst data.

Note: FMP redistribution/display rights may require additional licensing before
FMP data is shown in any shared deployment (§6).
"""
from __future__ import annotations

from typing import Any, Callable, Optional

from config.logging import get_logger
from config.settings import SETTINGS
from services.cache import JsonCache

log = get_logger("fmp_client")

_BASE = "https://financialmodelingprep.com/api/v3"
_STABLE = "https://financialmodelingprep.com/stable"
_TTL = 6 * 3600


def _requests_fetch_json(url: str, timeout: float) -> Any:
    import requests

    resp = requests.get(url, timeout=timeout)
    resp.raise_for_status()
    return resp.json()


class FMPClient:
    def __init__(
        self,
        api_key: Optional[str] = None,
        cache: Optional[JsonCache] = None,
        fetch_json: Optional[Callable[[str, float], Any]] = None,
    ) -> None:
        self.api_key = api_key if api_key is not None else SETTINGS.fmp_api_key
        self.cache = cache or JsonCache()
        self._fetch_json = fetch_json or _requests_fetch_json

    @property
    def enabled(self) -> bool:
        return bool(self.api_key)

    def _get(self, url: str) -> Optional[Any]:
        if not self.enabled:
            return None
        cached = self.cache.get(url, ttl_seconds=_TTL)
        if cached is not None:
            return cached
        try:
            data = self._fetch_json(url, SETTINGS.request_timeout_seconds)
            self.cache.set(url, data)
            return data
        except Exception as exc:  # noqa: BLE001 — degrade gracefully
            log.warning("FMP request failed (%s): %s", url, exc)
            return None

    # --- convenience endpoints --------------------------------------------

    def get_quote_price(self, ticker: str) -> Optional[float]:
        data = self._get(f"{_BASE}/quote-short/{ticker.upper()}?apikey={self.api_key}")
        if isinstance(data, list) and data and "price" in data[0]:
            return float(data[0]["price"])
        return None

    def get_batch_quotes(self, tickers: list[str]) -> dict[str, dict]:
        """Batch quotes (price, marketCap, pe, eps, shares) keyed by symbol.

        FMP accepts many comma-separated symbols per request, so the whole
        screener universe is covered in a few calls. Empty without a key.
        """
        if not self.enabled or not tickers:
            return {}
        out: dict[str, dict] = {}
        for i in range(0, len(tickers), 400):
            syms = ",".join(tickers[i:i + 400])
            data = self._get(f"{_BASE}/quote/{syms}?apikey={self.api_key}")
            if isinstance(data, list):
                for q in data:
                    sym = q.get("symbol")
                    if sym:
                        out[str(sym).upper()] = q
        return out

    def get_profile(self, ticker: str) -> Optional[dict]:
        data = self._get(f"{_BASE}/profile/{ticker.upper()}?apikey={self.api_key}")
        if isinstance(data, list) and data:
            return data[0]
        return None

    def get_peers(self, ticker: str) -> list[str]:
        data = self._get(
            f"{_STABLE}/stock-peers?symbol={ticker.upper()}&apikey={self.api_key}"
        )
        if isinstance(data, list):
            return [d.get("symbol") for d in data if d.get("symbol")]
        if isinstance(data, dict) and "peersList" in data:
            return list(data["peersList"])
        return []

    def get_product_segmentation(self, ticker: str) -> list[dict]:
        return self._segmentation(ticker, "revenue-product-segmentation")

    def get_geographic_segmentation(self, ticker: str) -> list[dict]:
        return self._segmentation(ticker, "revenue-geographic-segmentation")

    def _segmentation(self, ticker: str, endpoint: str) -> list[dict]:
        data = self._get(
            f"{_STABLE}/{endpoint}?symbol={ticker.upper()}&apikey={self.api_key}"
        )
        return data if isinstance(data, list) else []
