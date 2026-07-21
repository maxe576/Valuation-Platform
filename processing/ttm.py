"""Trailing-twelve-month aggregation and margin/ratio helpers (§11).

TTM for FLOW metrics is the sum of the last four standalone quarters. Balance
sheet (point-in-time) items are NOT summed — TTM for those is simply the latest
value. Margins and ratios are thin, null-safe helpers used across the app.
"""
from __future__ import annotations

from typing import Optional


def trailing_twelve_months(standalone_quarters: list[float]) -> Optional[float]:
    """Sum the last four standalone quarterly flow values. None if <4 available."""
    if len(standalone_quarters) < 4:
        return None
    return sum(standalone_quarters[-4:])


def safe_ratio(numerator: float, denominator: float) -> Optional[float]:
    """Divide, returning None on a zero/undefined denominator."""
    if not denominator:
        return None
    return numerator / denominator


def free_cash_flow(operating_cash_flow: float, capex: float) -> float:
    """OCF − CapEx. CapEx is passed as a positive outflow magnitude."""
    return operating_cash_flow - abs(capex)


# --- margins (all null-safe; revenue == 0 → None) --------------------------

def gross_margin(gross_profit: float, revenue: float) -> Optional[float]:
    return safe_ratio(gross_profit, revenue)


def operating_margin(operating_income: float, revenue: float) -> Optional[float]:
    return safe_ratio(operating_income, revenue)


def ebitda_margin(ebit: float, da: float, revenue: float) -> Optional[float]:
    return safe_ratio(ebit + da, revenue)


def net_margin(net_income: float, revenue: float) -> Optional[float]:
    return safe_ratio(net_income, revenue)


def fcf_margin(fcf: float, revenue: float) -> Optional[float]:
    return safe_ratio(fcf, revenue)


def net_debt(total_debt: float, cash: float, investments: float = 0.0) -> float:
    """Total debt − cash − investments (negative == net cash)."""
    return total_debt - cash - investments
