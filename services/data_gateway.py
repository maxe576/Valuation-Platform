"""Data gateway: the single entry point the app uses to load a company.

In demo mode it serves the bundled fixture (zero network). In live mode it
resolves the ticker via SEC EDGAR, normalizes Company Facts into FinancialFacts,
and derives sector/industry from the submissions metadata. Either way the caller
gets a :class:`Company` plus normalized facts, cached in the repository.
"""
from __future__ import annotations

from typing import Optional

from config.logging import get_logger
from config.lifecycle_weights import Lifecycle
from config.settings import SETTINGS
from models.company import Company
from models.financial_fact import FinancialFact
from processing.normalize_financials import normalize_company_facts
from services.repository import Repository
from services.sec_client import SECClient, SECError

log = get_logger("data_gateway")


class CompanyLoadError(RuntimeError):
    """User-facing failure loading a company (unknown ticker, SEC down, ...)."""


def load_company(
    ticker: str,
    repo: Repository,
    client: Optional[SECClient] = None,
) -> tuple[Company, list[FinancialFact]]:
    """Load a company + normalized facts, preferring the repository cache."""
    ticker = ticker.upper().strip()

    cached = repo.get_company(ticker)
    if cached is not None:
        return cached, repo.get_facts(ticker)

    if SETTINGS.is_demo:
        raise CompanyLoadError(
            f"'{ticker}' is not available in demo mode. "
            "Set APP_MODE=live with a SEC_USER_AGENT to fetch real filings."
        )

    client = client or SECClient()
    try:
        cik = client.get_cik(ticker)
        submissions = client.get_submissions(cik)
        facts_json = client.get_company_facts(cik)
    except SECError as exc:
        raise CompanyLoadError(str(exc)) from exc

    company = _company_from_submissions(ticker, cik, submissions)
    facts = normalize_company_facts(facts_json)

    repo.save_company(company)
    repo.save_facts(ticker, facts)
    repo.save_filings(ticker, client.get_recent_filings(cik))
    log.info("Loaded %s from SEC: %d facts", ticker, len(facts))
    return company, facts


def _company_from_submissions(ticker: str, cik: str, submissions: dict) -> Company:
    return Company(
        ticker=ticker,
        name=submissions.get("name", ticker),
        cik=cik,
        sector=submissions.get("sicDescription"),
        industry=submissions.get("sicDescription"),
        fiscal_year_end=_fye(submissions.get("fiscalYearEnd")),
        lifecycle=Lifecycle.MATURE_PROFITABLE,  # refined by analyst / heuristics later
    )


def _fye(raw: Optional[str]) -> Optional[str]:
    # SEC gives fiscalYearEnd as MMDD, e.g. "1231".
    if raw and len(raw) == 4:
        return f"{raw[:2]}-{raw[2:]}"
    return None
