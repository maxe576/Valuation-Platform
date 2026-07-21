"""Assemble normalized facts into usable statement series (§11).

Thin selectors over a flat ``list[FinancialFact]``: annual series per metric,
latest values, and the enterprise→equity bridge inputs the DCF needs. These let
the DCF run on real SEC data (the Phase 3 vertical slice).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from models.common import FiscalPeriod
from models.financial_fact import FinancialFact


def annual_series(facts: list[FinancialFact], metric: str) -> dict[int, float]:
    """Map fiscal_year -> value for a metric's annual (FY) facts."""
    out: dict[int, float] = {}
    for f in facts:
        if f.metric == metric and f.fiscal_period is FiscalPeriod.FY:
            out[f.fiscal_year] = f.value
    return dict(sorted(out.items()))


def latest_annual(facts: list[FinancialFact], metric: str) -> Optional[float]:
    series = annual_series(facts, metric)
    if not series:
        return None
    return series[max(series)]


@dataclass
class DCFBridge:
    base_year: Optional[int]
    base_year_revenue: Optional[float]
    cash: float
    investments: float
    total_debt: float
    minority_interest: float
    shares_outstanding: float


def build_bridge(facts: list[FinancialFact]) -> DCFBridge:
    """Extract the latest bridge inputs from normalized facts.

    Debt = short-term + long-term where available. Missing items default to 0 so
    the DCF still runs; the UI surfaces which inputs were found vs. assumed.
    """
    rev_series = annual_series(facts, "revenue")
    base_year = max(rev_series) if rev_series else None
    base_rev = rev_series[base_year] if base_year is not None else None

    cash = latest_annual(facts, "cash") or 0.0
    investments = latest_annual(facts, "marketable_securities") or 0.0
    st_debt = latest_annual(facts, "short_term_debt") or 0.0
    lt_debt = latest_annual(facts, "long_term_debt") or 0.0
    shares = (
        latest_annual(facts, "shares_diluted")
        or latest_annual(facts, "shares_basic")
        or 0.0
    )
    return DCFBridge(
        base_year=base_year,
        base_year_revenue=base_rev,
        cash=cash,
        investments=investments,
        total_debt=st_debt + lt_debt,
        minority_interest=0.0,
        shares_outstanding=shares,
    )
