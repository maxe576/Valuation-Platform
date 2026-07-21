"""SEC EDGAR client (§5).

SEC EDGAR is the source of truth for U.S. filings. This client resolves tickers
to CIKs, pulls submissions and Company Facts (XBRL), and lists recent filings.
It is polite by construction: a descriptive User-Agent, request throttling well
under SEC limits, on-disk caching, retries with backoff, and logging.

Network access is funnelled through a single injectable ``fetch_json`` so tests
can run entirely offline (see tests/test_sec.py).
"""
from __future__ import annotations

import time
from typing import Any, Callable, Optional

from config.logging import get_logger
from config.settings import SETTINGS
from models.common import FilingType
from models.filing import Filing
from services.cache import JsonCache

log = get_logger("sec_client")

# SEC endpoints.
TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik}.json"
COMPANY_FACTS_URL = "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"

# Cache TTLs (seconds).
_TICKERS_TTL = 24 * 3600
_FACTS_TTL = 12 * 3600
_SUBMISSIONS_TTL = 6 * 3600


class SECError(RuntimeError):
    """Raised when SEC data cannot be retrieved or parsed."""


def _requests_fetch_json(url: str, headers: dict[str, str], timeout: float) -> Any:
    import requests  # local import so the module loads without requests installed

    resp = requests.get(url, headers=headers, timeout=timeout)
    resp.raise_for_status()
    return resp.json()


class SECClient:
    def __init__(
        self,
        user_agent: Optional[str] = None,
        cache: Optional[JsonCache] = None,
        fetch_json: Optional[Callable[[str, dict, float], Any]] = None,
        min_interval_seconds: float = 0.2,   # ≤ 5 req/s, well under SEC's limit
        max_retries: int = 3,
    ) -> None:
        self.user_agent = user_agent or SETTINGS.sec_user_agent
        self.cache = cache or JsonCache()
        self._fetch_json = fetch_json or _requests_fetch_json
        self.min_interval = min_interval_seconds
        self.max_retries = max_retries
        self._last_request = 0.0

    # --- low-level fetch with throttle + retry + cache ---------------------

    def _headers(self) -> dict[str, str]:
        return {"User-Agent": self.user_agent, "Accept-Encoding": "gzip, deflate"}

    def _throttle(self) -> None:
        elapsed = time.monotonic() - self._last_request
        if elapsed < self.min_interval:
            time.sleep(self.min_interval - elapsed)
        self._last_request = time.monotonic()

    def _get(self, url: str, ttl: Optional[float] = None) -> Any:
        cached = self.cache.get(url, ttl_seconds=ttl)
        if cached is not None:
            return cached

        last_err: Optional[Exception] = None
        for attempt in range(1, self.max_retries + 1):
            self._throttle()
            try:
                data = self._fetch_json(
                    url, self._headers(), SETTINGS.request_timeout_seconds
                )
                self.cache.set(url, data)
                return data
            except Exception as exc:  # noqa: BLE001 — retry any transport error
                last_err = exc
                backoff = 0.5 * (2 ** (attempt - 1))
                log.warning("SEC fetch failed (attempt %d/%d): %s",
                            attempt, self.max_retries, exc)
                time.sleep(backoff)
        raise SECError(f"Failed to fetch {url}: {last_err}")

    # --- public API --------------------------------------------------------

    @staticmethod
    def _pad_cik(cik: str | int) -> str:
        return str(cik).lstrip("CIK").strip().zfill(10)

    def get_cik(self, ticker: str) -> str:
        """Resolve a ticker to a 10-digit zero-padded CIK."""
        ticker = ticker.upper().strip()
        data = self._get(TICKERS_URL, ttl=_TICKERS_TTL)
        # Payload is {index: {"cik_str": int, "ticker": str, "title": str}}.
        for row in data.values():
            if str(row.get("ticker", "")).upper() == ticker:
                return self._pad_cik(row["cik_str"])
        raise SECError(f"Ticker '{ticker}' not found in SEC company list.")

    def get_submissions(self, cik: str) -> dict:
        cik = self._pad_cik(cik)
        return self._get(SUBMISSIONS_URL.format(cik=cik), ttl=_SUBMISSIONS_TTL)

    def get_company_facts(self, cik: str) -> dict:
        cik = self._pad_cik(cik)
        return self._get(COMPANY_FACTS_URL.format(cik=cik), ttl=_FACTS_TTL)

    def get_recent_filings(
        self, cik: str, forms: Optional[set[str]] = None, limit: int = 40
    ) -> list[Filing]:
        """Parse the submissions 'recent' block into :class:`Filing` objects."""
        forms = forms or {"10-K", "10-Q", "8-K"}
        cik = self._pad_cik(cik)
        subs = self.get_submissions(cik)
        recent = subs.get("filings", {}).get("recent", {})
        acc = recent.get("accessionNumber", [])
        form_list = recent.get("form", [])
        filing_dates = recent.get("filingDate", [])
        report_dates = recent.get("reportDate", [])
        primary_docs = recent.get("primaryDocument", [])

        out: list[Filing] = []
        for i, form in enumerate(form_list):
            if form not in forms:
                continue
            accession = acc[i]
            accession_nodash = accession.replace("-", "")
            primary = primary_docs[i] if i < len(primary_docs) else ""
            url = (
                f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/"
                f"{accession_nodash}/{primary}"
            )
            out.append(
                Filing(
                    accession_number=accession,
                    form_type=_form_type(form),
                    filing_date=filing_dates[i] if i < len(filing_dates) else "",
                    report_date=report_dates[i] if i < len(report_dates) else None,
                    primary_document=primary or None,
                    source_url=url,
                    processing_status="pending",
                    company_cik=cik,
                )
            )
            if len(out) >= limit:
                break
        return out


def _form_type(form: str) -> FilingType:
    mapping = {"10-K": FilingType.TEN_K, "10-Q": FilingType.TEN_Q,
               "8-K": FilingType.EIGHT_K}
    return mapping.get(form, FilingType.OTHER)
