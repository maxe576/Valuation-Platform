"""Shared application context for the Streamlit UI (§26, §33).

Centralizes repository access, the active company, its facts, the working
assumption set, and the computed full valuation, so pages stay thin renderers.
State lives in ``st.session_state`` and survives page switches.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import streamlit as st

from config.lifecycle_weights import Lifecycle
from config.settings import SETTINGS
from models.company import Company
from models.forecast import AssumptionSet
from processing.forecast_seed import seed_assumptions_from_facts
from services.data_gateway import CompanyLoadError, load_company
from services.demo_data import DEMO_TICKER, build_demo_repository, demo_current_price
from services.repository import InMemoryRepository, Repository
from services.valuation_service import (
    FullValuation,
    ValuationInputs,
    build_demo_valuation_inputs,
    run_full_valuation,
)


@dataclass
class ActiveCompany:
    company: Company
    facts: list
    assumption_set: Optional[AssumptionSet]
    price: Optional[float]


@st.cache_resource
def get_repo() -> Repository:
    return build_demo_repository() if SETTINGS.is_demo else InMemoryRepository()


def active_ticker() -> str:
    return st.session_state.get("ticker", DEMO_TICKER if SETTINGS.is_demo else "AAPL")


def set_ticker(ticker: str) -> None:
    ticker = ticker.upper().strip()
    if ticker != st.session_state.get("ticker"):
        st.session_state["ticker"] = ticker
        # Invalidate any cached valuation for the previous ticker.
        st.session_state.pop("valuation", None)
        st.session_state.pop("assumptions", None)


def load_active() -> Optional[ActiveCompany]:
    """Load the active company + facts, seeding a working assumption set."""
    ticker = active_ticker()
    repo = get_repo()
    try:
        company, facts = load_company(ticker, repo)
    except CompanyLoadError as exc:
        st.error(str(exc))
        return None

    assumptions = _working_assumptions(ticker, repo, facts)
    price = _price_for(ticker, facts)
    return ActiveCompany(company=company, facts=facts,
                         assumption_set=assumptions, price=price)


def _working_assumptions(ticker: str, repo: Repository, facts: list) -> Optional[AssumptionSet]:
    # Session edits win; then any saved set; else seed from facts.
    store = st.session_state.setdefault("assumptions", {})
    if ticker in store:
        return store[ticker]
    saved = repo.list_assumption_sets(ticker)
    if saved:
        store[ticker] = saved[-1]
        return saved[-1]
    seeded = seed_assumptions_from_facts(facts, ticker)
    if seeded is not None:
        store[ticker] = seeded
    return seeded


def save_working_assumptions(ticker: str, aset: AssumptionSet) -> None:
    st.session_state.setdefault("assumptions", {})[ticker] = aset
    st.session_state.pop("valuation", None)  # force recompute


def _price_for(ticker: str, facts: list) -> Optional[float]:
    if SETTINGS.is_demo and ticker == DEMO_TICKER:
        return demo_current_price()
    return st.session_state.get("price_override", {}).get(ticker)


def get_valuation() -> Optional[FullValuation]:
    """Compute (and cache) the full valuation for the active company."""
    ticker = active_ticker()
    cache = st.session_state.setdefault("valuation", {})
    if ticker in cache:
        return cache[ticker]

    active = load_active()
    if active is None or active.assumption_set is None:
        return None

    inputs = _build_inputs(active)
    if inputs is None:
        return None
    fv = run_full_valuation(inputs)
    cache[ticker] = fv
    return fv


def _build_inputs(active: ActiveCompany) -> Optional[ValuationInputs]:
    ticker = active.company.ticker
    if SETTINGS.is_demo and ticker == DEMO_TICKER:
        inputs = build_demo_valuation_inputs()
        # Honor any session edits to the assumption set.
        if active.assumption_set is not None:
            inputs.assumption_set = active.assumption_set
        return inputs

    if active.assumption_set is None or active.price is None:
        return None
    # Live ticker: value on DCF + any peers/segments the analyst has added.
    from processing.statements import latest_annual

    da = latest_annual(active.facts, "depreciation_amortization") or 0.0
    ebit = latest_annual(active.facts, "operating_income") or 0.0
    target = {
        "revenue": latest_annual(active.facts, "revenue"),
        "ebitda": ebit + da,
        "ebit": ebit,
        "net_income": latest_annual(active.facts, "net_income"),
        "revenue_growth": active.assumption_set.scenarios[
            list(active.assumption_set.scenarios)[0]
        ].revenue_growth[0] if active.assumption_set.scenarios else 0.0,
        "ebit_margin": (ebit / latest_annual(active.facts, "revenue"))
        if latest_annual(active.facts, "revenue") else 0.0,
    }
    peers = st.session_state.get("peers", {}).get(ticker, [])
    segments = st.session_state.get("segments", {}).get(ticker, [])
    return ValuationInputs(
        ticker=ticker,
        lifecycle=active.company.lifecycle or Lifecycle.MATURE_PROFITABLE,
        current_price=active.price,
        assumption_set=active.assumption_set,
        target=target,
        peers=peers,
        segments=segments,
        residual_income=None,
    )
