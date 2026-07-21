"""Forecast assumptions.

Assumptions are versioned and never overwritten (§13). Each important driver can
carry a written reason. A :class:`ScenarioAssumptions` holds the per-year driver
paths for one scenario; an :class:`AssumptionSet` bundles bear/base/bull plus the
shared valuation parameters (WACC, terminal growth, exit multiple) and the
enterprise→equity bridge items.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from .common import Scenario


@dataclass
class Assumption:
    """A single numeric assumption with an optional analyst rationale."""

    value: float
    reason: Optional[str] = None
    author: Optional[str] = None


@dataclass
class ScenarioAssumptions:
    """Per-year forecast drivers for one scenario.

    Each list has one entry per explicit forecast year. Percentages are decimals
    (0.15 == 15%). ``nwc_pct_sales`` is change-in-net-working-capital as a share
    of revenue (negative == a working-capital source of cash).
    """

    scenario: Scenario
    revenue_growth: list[float] = field(default_factory=list)   # yoy growth
    ebit_margin: list[float] = field(default_factory=list)      # EBIT / revenue
    tax_rate: list[float] = field(default_factory=list)
    da_pct_sales: list[float] = field(default_factory=list)     # D&A / revenue
    capex_pct_sales: list[float] = field(default_factory=list)  # CapEx / revenue
    nwc_pct_sales: list[float] = field(default_factory=list)    # ΔNWC / revenue

    # Optional written rationales keyed by driver name -> Assumption.
    rationales: dict[str, Assumption] = field(default_factory=dict)

    def years(self) -> int:
        return len(self.revenue_growth)


@dataclass
class AssumptionSet:
    """A complete, versioned set of assumptions for a company valuation (§25)."""

    company_ticker: str
    name: str
    base_year_revenue: float
    scenarios: dict[Scenario, ScenarioAssumptions] = field(default_factory=dict)

    # Shared valuation parameters (may be per-scenario via overrides later).
    wacc: float = 0.10
    terminal_growth: float = 0.025
    exit_multiple: float = 12.0            # EV/EBITDA for exit-multiple terminal value

    # Enterprise -> equity bridge (§14).
    cash: float = 0.0
    investments: float = 0.0
    total_debt: float = 0.0
    minority_interest: float = 0.0
    shares_outstanding: float = 0.0

    model_version: str = "dcf-1.0"
    created_by: Optional[str] = None
    approved_by: Optional[str] = None
    approval_status: str = "draft"          # draft | approved | rejected
    id: Optional[int] = None
