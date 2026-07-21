"""Integration tests for the SEC client + normalization — fully mocked (§29).

No network access: a fake ``fetch_json`` routes by URL to canned JSON, and a
null cache keeps everything in-memory.
"""
from __future__ import annotations

import pytest

from models.common import Confidence, FiscalPeriod
from processing.normalize_financials import normalize_company_facts
from services.sec_client import SECClient, SECError

CIK = "0001065280"

TICKERS_JSON = {
    "0": {"cik_str": 1065280, "ticker": "NFLX", "title": "NETFLIX INC"},
    "1": {"cik_str": 320193, "ticker": "AAPL", "title": "APPLE INC"},
}

FACTS_JSON = {
    "cik": 1065280,
    "entityName": "NETFLIX INC",
    "facts": {
        "us-gaap": {
            # Primary revenue tag → HIGH confidence.
            "RevenueFromContractWithCustomerExcludingAssessedTax": {
                "label": "Revenue",
                "units": {"USD": [
                    {"start": "2023-01-01", "end": "2023-12-31", "val": 33723297000,
                     "fy": 2023, "fp": "FY", "form": "10-K", "accn": "acc-fy23",
                     "filed": "2024-01-25"},
                    {"start": "2023-01-01", "end": "2023-03-31", "val": 8161503000,
                     "fy": 2023, "fp": "Q1", "form": "10-Q", "accn": "acc-q1",
                     "filed": "2023-04-20"},
                    # 6-month YTD (181 days) → must be SKIPPED by normalizer.
                    {"start": "2023-01-01", "end": "2023-06-30", "val": 16000000000,
                     "fy": 2023, "fp": "Q2", "form": "10-Q", "accn": "acc-q2",
                     "filed": "2023-07-20"},
                ]},
            },
            # Balance-sheet instant (no start).
            "Assets": {
                "label": "Total assets",
                "units": {"USD": [
                    {"end": "2023-12-31", "val": 48731992000, "fy": 2023, "fp": "FY",
                     "accn": "acc-fy23", "filed": "2024-01-25"},
                ]},
            },
            # Alternate operating-income tag is the primary here → HIGH.
            "OperatingIncomeLoss": {
                "label": "Operating income",
                "units": {"USD": [
                    {"start": "2023-01-01", "end": "2023-12-31", "val": 6954930000,
                     "fy": 2023, "fp": "FY", "accn": "acc-fy23", "filed": "2024-01-25"},
                ]},
            },
            "WeightedAverageNumberOfDilutedSharesOutstanding": {
                "label": "Diluted shares",
                "units": {"shares": [
                    {"start": "2023-01-01", "end": "2023-12-31", "val": 444000000,
                     "fy": 2023, "fp": "FY", "accn": "acc-fy23", "filed": "2024-01-25"},
                ]},
            },
        }
    },
}

SUBMISSIONS_JSON = {
    "name": "NETFLIX INC",
    "sicDescription": "Services-Video Tape Rental",
    "fiscalYearEnd": "1231",
    "filings": {"recent": {
        "accessionNumber": ["0001065280-24-000017", "0001065280-23-000090"],
        "form": ["10-K", "10-Q"],
        "filingDate": ["2024-01-25", "2023-10-19"],
        "reportDate": ["2023-12-31", "2023-09-30"],
        "primaryDocument": ["nflx-20231231.htm", "nflx-20230930.htm"],
    }},
}


class _NullCache:
    def get(self, key, ttl_seconds=None):
        return None

    def set(self, key, data):
        pass


def _fake_fetch(url, headers, timeout):
    assert "User-Agent" in headers and headers["User-Agent"]
    if "company_tickers" in url:
        return TICKERS_JSON
    if "companyfacts" in url:
        return FACTS_JSON
    if "submissions" in url:
        return SUBMISSIONS_JSON
    raise AssertionError(f"unexpected url {url}")


def _client() -> SECClient:
    return SECClient(
        user_agent="test-agent (test@example.com)",
        cache=_NullCache(),
        fetch_json=_fake_fetch,
        min_interval_seconds=0.0,
        max_retries=1,
    )


def test_get_cik_resolves_ticker():
    assert _client().get_cik("nflx") == CIK
    assert _client().get_cik("AAPL") == "0000320193"


def test_get_cik_unknown_ticker_raises():
    with pytest.raises(SECError):
        _client().get_cik("ZZZZ")


def test_get_recent_filings_parses_forms():
    filings = _client().get_recent_filings(CIK)
    assert len(filings) == 2
    k = filings[0]
    assert k.form_type.value == "10-K"
    assert k.accession_number == "0001065280-24-000017"
    assert k.source_url.endswith("nflx-20231231.htm")


def test_normalization_annual_quarterly_and_skips_ytd():
    facts = normalize_company_facts(FACTS_JSON)
    by = {(f.metric, f.fiscal_period): f for f in facts}

    # Annual revenue present, HIGH confidence (primary tag), correct value/label.
    rev_fy = by[("revenue", FiscalPeriod.FY)]
    assert rev_fy.value == pytest.approx(33723297000)
    assert rev_fy.confidence is Confidence.HIGH
    assert rev_fy.provenance.xbrl_tag == "RevenueFromContractWithCustomerExcludingAssessedTax"
    assert rev_fy.provenance.filing_accession == "acc-fy23"

    # Standalone Q1 (89 days) kept.
    assert ("revenue", FiscalPeriod.Q1) in by
    # 6-month YTD entry (fp=Q2) must NOT appear as a Q2 fact.
    assert ("revenue", FiscalPeriod.Q2) not in by

    # Balance-sheet instant classified as FY.
    assert by[("total_assets", FiscalPeriod.FY)].value == pytest.approx(48731992000)

    # Shares use the 'shares' unit.
    shares = by[("shares_diluted", FiscalPeriod.FY)]
    assert shares.unit == "shares"
    assert shares.value == pytest.approx(444000000)


def test_bridge_from_normalized_facts():
    from processing.statements import build_bridge

    facts = normalize_company_facts(FACTS_JSON)
    bridge = build_bridge(facts)
    assert bridge.base_year == 2023
    assert bridge.base_year_revenue == pytest.approx(33723297000)
    assert bridge.shares_outstanding == pytest.approx(444000000)
