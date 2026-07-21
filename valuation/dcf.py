"""Multi-stage unlevered DCF (§14) — ported from the legacy Excel model.

Legacy mapping (NFLX Valuation.xlsx, DCF sheet):
    Unlevered FCF  = EBIAT + D&A - CapEx - ΔNWC          (rows 58/60/63/66/69)
    PV of UFCF     = UFCF / (1 + dr)^year                (row 70; dr = WACC)
    Exit-multiple TV = Year-5 EBITDA × EV/EBITDA         (rows 75/78)
    EV → equity    = EV - Debt + Cash → ÷ shares         (rows 81-86)

Changes vs. legacy (see ROADMAP.md), all pure numeric now:
  * terminal multiple is a real number, replacing the `=C75*LEFT(EM,2)` string hack
  * both terminal methods are computed (perpetual growth AND exit multiple);
    neither is auto-averaged — the caller selects one for equity value (§14)
  * a warning engine flags unreasonable inputs

This module is pure: no I/O, no Streamlit. Everything here is unit-tested.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from models.common import Scenario
from models.forecast import AssumptionSet, ScenarioAssumptions


class TerminalMethod(str, Enum):
    PERPETUAL_GROWTH = "perpetual_growth"
    EXIT_MULTIPLE = "exit_multiple"


@dataclass
class DCFYear:
    """One explicit forecast year of the projection."""

    year_index: int          # 1-based
    revenue: float
    revenue_growth: float
    ebit: float
    ebit_margin: float
    taxes: float
    tax_rate: float
    ebiat: float             # EBIT × (1 − tax) = NOPAT
    da: float
    capex: float
    nwc_change: float
    unlevered_fcf: float
    discount_factor: float
    pv_unlevered_fcf: float


@dataclass
class TerminalValue:
    method: TerminalMethod
    terminal_value: float
    pv_terminal_value: float
    implied_ebitda_multiple: Optional[float] = None
    implied_terminal_roic: Optional[float] = None


@dataclass
class DCFResult:
    scenario: Optional[Scenario]
    years: list[DCFYear]
    pv_forecast_fcf: float
    terminal_selected: TerminalValue
    terminal_perpetual: TerminalValue
    terminal_exit: TerminalValue
    enterprise_value: float
    equity_value: float
    per_share_value: float
    wacc: float
    terminal_growth: float
    exit_multiple: float
    current_price: Optional[float] = None
    warnings: list[str] = field(default_factory=list)

    @property
    def tv_pct_of_ev(self) -> float:
        if self.enterprise_value == 0:
            return 0.0
        return self.terminal_selected.pv_terminal_value / self.enterprise_value

    @property
    def upside(self) -> Optional[float]:
        if self.current_price is None or not self.current_price:
            return None
        return self.per_share_value / self.current_price - 1.0


# --- core primitives (independently testable) ------------------------------

def discount_factor(wacc: float, year_index: int) -> float:
    """1 / (1 + wacc)^t. Mirrors the legacy `(1+dr)^year` denominator."""
    return 1.0 / ((1.0 + wacc) ** year_index)


def unlevered_fcf(ebiat: float, da: float, capex: float, nwc_change: float) -> float:
    """EBIAT + D&A − CapEx − ΔNWC (legacy DCF row 69)."""
    return ebiat + da - capex - nwc_change


def terminal_value_perpetual(
    last_fcf: float, wacc: float, growth: float
) -> float:
    """Gordon growth: FCF_{n}·(1+g) / (WACC − g). Requires WACC > g."""
    if wacc <= growth:
        # Caller surfaces this as a warning; return NaN-safe 0 to avoid blow-up.
        return 0.0
    return last_fcf * (1.0 + growth) / (wacc - growth)


def terminal_value_exit_multiple(
    terminal_ebitda: float, exit_multiple: float
) -> float:
    """Year-N EBITDA × EV/EBITDA multiple (legacy rows 75/78)."""
    return terminal_ebitda * exit_multiple


# --- projection ------------------------------------------------------------

def project_years(
    base_year_revenue: float, s: ScenarioAssumptions, wacc: float
) -> list[DCFYear]:
    """Build the explicit forecast from base-year revenue and driver paths."""
    n = s.years()
    if n == 0:
        return []

    years: list[DCFYear] = []
    prev_rev = base_year_revenue
    for t in range(1, n + 1):
        i = t - 1
        growth = s.revenue_growth[i]
        rev = prev_rev * (1.0 + growth)
        margin = s.ebit_margin[i]
        ebit = rev * margin
        tax_rate = s.tax_rate[i]
        # Tax only positive EBIT; losses do not create a cash tax benefit here.
        taxes = ebit * tax_rate if ebit > 0 else 0.0
        ebiat = ebit - taxes
        da = rev * s.da_pct_sales[i]
        capex = rev * s.capex_pct_sales[i]
        nwc = rev * s.nwc_pct_sales[i]
        ufcf = unlevered_fcf(ebiat, da, capex, nwc)
        df = discount_factor(wacc, t)
        years.append(
            DCFYear(
                year_index=t,
                revenue=rev,
                revenue_growth=growth,
                ebit=ebit,
                ebit_margin=margin,
                taxes=taxes,
                tax_rate=tax_rate,
                ebiat=ebiat,
                da=da,
                capex=capex,
                nwc_change=nwc,
                unlevered_fcf=ufcf,
                discount_factor=df,
                pv_unlevered_fcf=ufcf * df,
            )
        )
        prev_rev = rev
    return years


def _build_terminals(
    years: list[DCFYear], wacc: float, terminal_growth: float, exit_multiple: float
) -> tuple[TerminalValue, TerminalValue]:
    last = years[-1]
    n = last.year_index
    df_n = last.discount_factor

    # Perpetual growth.
    tv_perp = terminal_value_perpetual(last.unlevered_fcf, wacc, terminal_growth)
    terminal_ebitda = last.ebit + last.da
    perp = TerminalValue(
        method=TerminalMethod.PERPETUAL_GROWTH,
        terminal_value=tv_perp,
        pv_terminal_value=tv_perp * df_n,
        implied_ebitda_multiple=(tv_perp / terminal_ebitda) if terminal_ebitda else None,
        implied_terminal_roic=_implied_terminal_roic(last, terminal_growth),
    )

    # Exit multiple.
    tv_exit = terminal_value_exit_multiple(terminal_ebitda, exit_multiple)
    exit_tv = TerminalValue(
        method=TerminalMethod.EXIT_MULTIPLE,
        terminal_value=tv_exit,
        pv_terminal_value=tv_exit * df_n,
        implied_ebitda_multiple=exit_multiple,
        implied_terminal_roic=None,
    )
    return perp, exit_tv


def _implied_terminal_roic(last: DCFYear, growth: float) -> Optional[float]:
    """From the perpetuity identity g = reinvestment_rate × ROIC.

    reinvestment = CapEx + ΔNWC − D&A; reinvestment_rate = reinvestment / NOPAT.
    ROIC = g / reinvestment_rate. Diagnostic only — returns None if undefined.
    """
    nopat = last.ebiat
    if nopat <= 0:
        return None
    reinvestment = last.capex + last.nwc_change - last.da
    if reinvestment == 0:
        return None
    reinvestment_rate = reinvestment / nopat
    if reinvestment_rate == 0:
        return None
    return growth / reinvestment_rate


def _collect_warnings(
    years: list[DCFYear],
    wacc: float,
    terminal_growth: float,
    selected: TerminalValue,
    enterprise_value: float,
    shares: float,
) -> list[str]:
    w: list[str] = []
    if wacc <= 0:
        w.append(f"WACC is non-positive ({wacc:.1%}); discounting is invalid.")
    if wacc <= terminal_growth:
        w.append(
            f"WACC ({wacc:.1%}) ≤ terminal growth ({terminal_growth:.1%}); "
            "perpetual-growth terminal value is not meaningful."
        )
    if terminal_growth < 0 or terminal_growth > 0.04:
        w.append(
            f"Terminal growth of {terminal_growth:.1%} is outside a typical "
            "long-run range (0%–4%, near nominal GDP)."
        )
    if enterprise_value > 0:
        tv_pct = selected.pv_terminal_value / enterprise_value
        if tv_pct > 0.75:
            w.append(
                f"Terminal value is {tv_pct:.0%} of enterprise value; the result "
                "leans heavily on terminal assumptions."
            )
    if years:
        late_growth = years[-1].revenue_growth
        if late_growth > 0.15:
            w.append(
                f"Final-year revenue growth ({late_growth:.1%}) stays elevated; "
                "consider fading growth toward a mature rate."
            )
        term_margin = years[-1].ebit_margin
        if term_margin > 0.50:
            w.append(
                f"Terminal EBIT margin ({term_margin:.0%}) exceeds most peer "
                "leaders; justify the premium or trim it."
            )
    if shares <= 0:
        w.append("Share count is zero or negative; per-share value is invalid.")
    return w


# --- entry point -----------------------------------------------------------

def run_dcf(
    base_year_revenue: float,
    scenario_assumptions: ScenarioAssumptions,
    wacc: float,
    terminal_growth: float,
    exit_multiple: float,
    cash: float = 0.0,
    investments: float = 0.0,
    total_debt: float = 0.0,
    minority_interest: float = 0.0,
    shares_outstanding: float = 0.0,
    terminal_method: TerminalMethod = TerminalMethod.PERPETUAL_GROWTH,
    current_price: Optional[float] = None,
) -> DCFResult:
    """Run a single-scenario DCF and return the full result with both TVs."""
    years = project_years(base_year_revenue, scenario_assumptions, wacc)
    if not years:
        raise ValueError("DCF requires at least one forecast year.")

    pv_fcf = sum(y.pv_unlevered_fcf for y in years)
    perp, exit_tv = _build_terminals(years, wacc, terminal_growth, exit_multiple)
    selected = perp if terminal_method is TerminalMethod.PERPETUAL_GROWTH else exit_tv

    enterprise_value = pv_fcf + selected.pv_terminal_value
    # EV → equity bridge (legacy rows 81-84): + cash + investments − debt − minority.
    equity_value = (
        enterprise_value + cash + investments - total_debt - minority_interest
    )
    per_share = equity_value / shares_outstanding if shares_outstanding > 0 else 0.0

    warnings = _collect_warnings(
        years, wacc, terminal_growth, selected, enterprise_value, shares_outstanding
    )

    return DCFResult(
        scenario=scenario_assumptions.scenario,
        years=years,
        pv_forecast_fcf=pv_fcf,
        terminal_selected=selected,
        terminal_perpetual=perp,
        terminal_exit=exit_tv,
        enterprise_value=enterprise_value,
        equity_value=equity_value,
        per_share_value=per_share,
        wacc=wacc,
        terminal_growth=terminal_growth,
        exit_multiple=exit_multiple,
        current_price=current_price,
        warnings=warnings,
    )


def run_scenarios(
    aset: AssumptionSet,
    terminal_method: TerminalMethod = TerminalMethod.PERPETUAL_GROWTH,
    current_price: Optional[float] = None,
) -> dict[Scenario, DCFResult]:
    """Run bear/base/bull from an :class:`AssumptionSet` (§13, §14)."""
    out: dict[Scenario, DCFResult] = {}
    for scenario, sa in aset.scenarios.items():
        out[scenario] = run_dcf(
            base_year_revenue=aset.base_year_revenue,
            scenario_assumptions=sa,
            wacc=aset.wacc,
            terminal_growth=aset.terminal_growth,
            exit_multiple=aset.exit_multiple,
            cash=aset.cash,
            investments=aset.investments,
            total_debt=aset.total_debt,
            minority_interest=aset.minority_interest,
            shares_outstanding=aset.shares_outstanding,
            terminal_method=terminal_method,
            current_price=current_price,
        )
    return out
