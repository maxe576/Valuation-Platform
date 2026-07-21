"""Seed a starter forecast from historical facts (§13).

Turns normalized financial history into a first-draft bear/base/bull
:class:`AssumptionSet` the analyst then edits in the Forecast Builder. Every
driver is derived from reported history (growth fades toward a mature terminal
rate; margins/tax/D&A/capex from the latest year), so live SEC tickers become
valuable without hand-entering every number. These are ESTIMATES to review, not
reported facts.
"""
from __future__ import annotations

from statistics import mean
from typing import Optional

from models.common import Scenario
from models.forecast import AssumptionSet, ScenarioAssumptions
from processing.statements import annual_series, build_bridge
from processing.ttm import safe_ratio


def _clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def _fade_path(start: float, terminal: float, years: int) -> list[float]:
    """Linearly fade from start to terminal over ``years``."""
    if years == 1:
        return [terminal]
    step = (terminal - start) / (years - 1)
    return [start + step * i for i in range(years)]


def seed_assumptions_from_facts(
    facts: list,
    ticker: str,
    years: int = 5,
    wacc: float = 0.09,
    terminal_growth: float = 0.03,
    exit_multiple: float = 12.0,
    name: str = "Seeded from filings",
) -> Optional[AssumptionSet]:
    """Build a starter AssumptionSet, or None if revenue history is missing."""
    rev = annual_series(facts, "revenue")
    if len(rev) < 2:
        return None

    yrs = sorted(rev)
    base_rev = rev[yrs[-1]]

    # Historical growth: average of the last up-to-3 yoy readings.
    growths = [rev[b] / rev[a] - 1.0 for a, b in zip(yrs, yrs[1:]) if rev[a]]
    start_growth = _clamp(mean(growths[-3:]) if growths else 0.05, 0.0, 0.40)

    # Latest-year margins / ratios (fall back to sensible defaults).
    oi = annual_series(facts, "operating_income")
    last = yrs[-1]
    ebit_margin = _clamp(safe_ratio(oi.get(last, 0.0), base_rev) or 0.15, 0.02, 0.60)

    tax = annual_series(facts, "income_tax")
    tax_rate = _clamp(safe_ratio(tax.get(last, 0.0), oi.get(last, 0.0)) or 0.21, 0.0, 0.35)

    da = annual_series(facts, "depreciation_amortization")
    da_pct = _clamp(safe_ratio(da.get(last, 0.0), base_rev) or 0.05, 0.0, 0.60)

    capex = annual_series(facts, "capex")
    capex_pct = _clamp(abs(safe_ratio(capex.get(last, 0.0), base_rev) or 0.05), 0.0, 0.60)

    def scenario(scen: Scenario, g_shift: float, m_shift: float) -> ScenarioAssumptions:
        growth = [_clamp(g + g_shift, -0.20, 0.60)
                  for g in _fade_path(start_growth, terminal_growth + 0.01, years)]
        margin = [_clamp(ebit_margin + m_shift, 0.0, 0.70)] * years
        return ScenarioAssumptions(
            scenario=scen,
            revenue_growth=growth,
            ebit_margin=margin,
            tax_rate=[tax_rate] * years,
            da_pct_sales=[da_pct] * years,
            capex_pct_sales=[capex_pct] * years,
            nwc_pct_sales=[-0.005] * years,
        )

    bridge = build_bridge(facts)
    return AssumptionSet(
        company_ticker=ticker,
        name=name,
        base_year_revenue=base_rev,
        scenarios={
            Scenario.BEAR: scenario(Scenario.BEAR, -0.03, -0.03),
            Scenario.BASE: scenario(Scenario.BASE, 0.0, 0.0),
            Scenario.BULL: scenario(Scenario.BULL, +0.03, +0.03),
        },
        wacc=wacc,
        terminal_growth=terminal_growth,
        exit_multiple=exit_multiple,
        cash=bridge.cash,
        investments=bridge.investments,
        total_debt=bridge.total_debt,
        minority_interest=bridge.minority_interest,
        shares_outstanding=bridge.shares_outstanding,
        created_by="seed",
        approval_status="draft",
    )
