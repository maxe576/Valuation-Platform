"""Reverse DCF (§21).

Start from the current share price and solve for the single assumption that makes
the DCF output equal that price — implied revenue growth, terminal EBIT margin,
or exit multiple. This is a *diagnostic*: it shows what the market is pricing in
and never receives a weight in the blended fair value.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Callable, Optional

from scipy.optimize import brentq

from models.forecast import ScenarioAssumptions
from .dcf import TerminalMethod, run_dcf


@dataclass
class ReverseDCFResult:
    solved_for: str
    implied_value: Optional[float]     # None if no solution in the search range
    market_price: float
    analyst_value: Optional[float] = None   # analyst's own assumption, for contrast
    note: str = ""

    @property
    def gap_vs_analyst(self) -> Optional[float]:
        if self.implied_value is None or self.analyst_value is None:
            return None
        return self.implied_value - self.analyst_value


def _per_share_for(
    base_year_revenue: float,
    sa: ScenarioAssumptions,
    wacc: float,
    terminal_growth: float,
    exit_multiple: float,
    bridge: dict,
    method: TerminalMethod,
) -> float:
    return run_dcf(
        base_year_revenue=base_year_revenue,
        scenario_assumptions=sa,
        wacc=wacc,
        terminal_growth=terminal_growth,
        exit_multiple=exit_multiple,
        terminal_method=method,
        **bridge,
    ).per_share_value


def _solve(objective: Callable[[float], float], lo: float, hi: float) -> Optional[float]:
    """Bracketed root find; returns None if the target isn't reachable in range."""
    try:
        f_lo, f_hi = objective(lo), objective(hi)
    except (ValueError, ZeroDivisionError):
        return None
    if f_lo == 0:
        return lo
    if f_hi == 0:
        return hi
    if f_lo * f_hi > 0:
        return None  # no sign change — price not achievable within [lo, hi]
    try:
        return float(brentq(objective, lo, hi, maxiter=200, xtol=1e-8))
    except (ValueError, RuntimeError):
        return None


def implied_revenue_growth(
    base_year_revenue: float,
    template: ScenarioAssumptions,
    wacc: float,
    terminal_growth: float,
    exit_multiple: float,
    bridge: dict,
    market_price: float,
    method: TerminalMethod = TerminalMethod.PERPETUAL_GROWTH,
    lo: float = -0.20,
    hi: float = 0.60,
) -> ReverseDCFResult:
    """Solve for a uniform annual revenue growth that reproduces the price."""
    n = template.years()

    def obj(g: float) -> float:
        sa = replace(template, revenue_growth=[g] * n)
        return _per_share_for(base_year_revenue, sa, wacc, terminal_growth,
                              exit_multiple, bridge, method) - market_price

    sol = _solve(obj, lo, hi)
    note = "" if sol is not None else (
        f"No uniform growth in [{lo:.0%}, {hi:.0%}] reproduces the price; the "
        "market may imply assumptions outside this range or a different driver."
    )
    return ReverseDCFResult("implied_revenue_growth", sol, market_price, note=note)


def implied_terminal_margin(
    base_year_revenue: float,
    template: ScenarioAssumptions,
    wacc: float,
    terminal_growth: float,
    exit_multiple: float,
    bridge: dict,
    market_price: float,
    method: TerminalMethod = TerminalMethod.PERPETUAL_GROWTH,
    lo: float = 0.0,
    hi: float = 0.80,
) -> ReverseDCFResult:
    """Solve for a uniform EBIT margin across all years that reproduces the price."""
    n = template.years()

    def obj(m: float) -> float:
        sa = replace(template, ebit_margin=[m] * n)
        return _per_share_for(base_year_revenue, sa, wacc, terminal_growth,
                              exit_multiple, bridge, method) - market_price

    sol = _solve(obj, lo, hi)
    note = "" if sol is not None else (
        f"No uniform EBIT margin in [{lo:.0%}, {hi:.0%}] reproduces the price."
    )
    return ReverseDCFResult("implied_terminal_margin", sol, market_price, note=note)


def implied_exit_multiple(
    base_year_revenue: float,
    template: ScenarioAssumptions,
    wacc: float,
    terminal_growth: float,
    bridge: dict,
    market_price: float,
    lo: float = 1.0,
    hi: float = 60.0,
) -> ReverseDCFResult:
    """Solve for the EV/EBITDA exit multiple that reproduces the price."""

    def obj(x: float) -> float:
        return _per_share_for(base_year_revenue, template, wacc, terminal_growth,
                              x, bridge, TerminalMethod.EXIT_MULTIPLE) - market_price

    sol = _solve(obj, lo, hi)
    note = "" if sol is not None else (
        f"No exit multiple in [{lo:.0f}x, {hi:.0f}x] reproduces the price."
    )
    return ReverseDCFResult("implied_exit_multiple", sol, market_price, note=note)
