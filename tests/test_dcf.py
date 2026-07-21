"""Unit tests for the DCF engine (§29).

Uses hand-computed values on a deliberately simple projection so the arithmetic
is verifiable by inspection, then checks terminal methods, the equity bridge,
and the warning engine.
"""
from __future__ import annotations

import math

import pytest

from models.common import Scenario
from valuation.dcf import (
    TerminalMethod,
    discount_factor,
    run_dcf,
    run_scenarios,
    terminal_value_exit_multiple,
    terminal_value_perpetual,
    unlevered_fcf,
)
from models.forecast import ScenarioAssumptions


def _one_year_scenario() -> ScenarioAssumptions:
    # Revenue 1000 → 1100; EBIT 220; taxes 55; EBIAT 165; D&A 55; CapEx 55; ΔNWC 0.
    return ScenarioAssumptions(
        scenario=Scenario.BASE,
        revenue_growth=[0.10],
        ebit_margin=[0.20],
        tax_rate=[0.25],
        da_pct_sales=[0.05],
        capex_pct_sales=[0.05],
        nwc_pct_sales=[0.0],
    )


# --- primitives ------------------------------------------------------------

def test_discount_factor():
    assert discount_factor(0.10, 1) == pytest.approx(1 / 1.10)
    assert discount_factor(0.10, 2) == pytest.approx(1 / 1.21)


def test_unlevered_fcf_formula():
    # EBIAT + D&A − CapEx − ΔNWC
    assert unlevered_fcf(165, 55, 55, 0) == pytest.approx(165)
    assert unlevered_fcf(100, 20, 30, 10) == pytest.approx(80)


def test_terminal_perpetual_and_exit():
    assert terminal_value_perpetual(165, 0.10, 0.02) == pytest.approx(
        165 * 1.02 / 0.08
    )
    assert terminal_value_exit_multiple(275, 10) == pytest.approx(2750)


def test_perpetual_guard_when_wacc_le_growth():
    # WACC ≤ g must not blow up; returns 0 and is flagged elsewhere.
    assert terminal_value_perpetual(100, 0.03, 0.05) == 0.0


# --- full DCF: hand-computed ----------------------------------------------

def test_run_dcf_perpetual_matches_hand_calc():
    res = run_dcf(
        base_year_revenue=1000,
        scenario_assumptions=_one_year_scenario(),
        wacc=0.10,
        terminal_growth=0.02,
        exit_multiple=10,
        cash=100,
        total_debt=200,
        shares_outstanding=10,
        terminal_method=TerminalMethod.PERPETUAL_GROWTH,
        current_price=150.0,
    )
    y = res.years[0]
    assert y.revenue == pytest.approx(1100)
    assert y.ebit == pytest.approx(220)
    assert y.taxes == pytest.approx(55)
    assert y.ebiat == pytest.approx(165)
    assert y.unlevered_fcf == pytest.approx(165)

    # PV of forecast FCF = 165 / 1.10
    assert res.pv_forecast_fcf == pytest.approx(165 / 1.10)

    # Perpetual TV = 165·1.02/0.08 = 2103.75; discounted at 1/1.10.
    tv = 165 * 1.02 / 0.08
    assert res.terminal_perpetual.terminal_value == pytest.approx(tv)
    assert res.terminal_selected.pv_terminal_value == pytest.approx(tv / 1.10)

    ev = 165 / 1.10 + tv / 1.10
    assert res.enterprise_value == pytest.approx(ev)
    # Equity = EV + cash − debt (no investments/minority).
    assert res.equity_value == pytest.approx(ev + 100 - 200)
    assert res.per_share_value == pytest.approx((ev + 100 - 200) / 10)


def test_run_dcf_exit_multiple_uses_ebitda():
    res = run_dcf(
        base_year_revenue=1000,
        scenario_assumptions=_one_year_scenario(),
        wacc=0.10,
        terminal_growth=0.02,
        exit_multiple=10,
        cash=100,
        total_debt=200,
        shares_outstanding=10,
        terminal_method=TerminalMethod.EXIT_MULTIPLE,
    )
    # Terminal EBITDA = EBIT 220 + D&A 55 = 275; TV = 2750; PV = 2750/1.10.
    assert res.terminal_exit.terminal_value == pytest.approx(2750)
    assert res.terminal_selected.pv_terminal_value == pytest.approx(2750 / 1.10)
    ev = 165 / 1.10 + 2750 / 1.10
    assert res.enterprise_value == pytest.approx(ev)


def test_both_terminals_always_present_and_not_averaged():
    res = run_dcf(
        base_year_revenue=1000,
        scenario_assumptions=_one_year_scenario(),
        wacc=0.10,
        terminal_growth=0.02,
        exit_multiple=10,
        shares_outstanding=10,
    )
    # Both computed; selected equals exactly one of them (never a blend).
    assert res.terminal_perpetual.terminal_value > 0
    assert res.terminal_exit.terminal_value > 0
    assert res.terminal_selected.terminal_value in (
        res.terminal_perpetual.terminal_value,
        res.terminal_exit.terminal_value,
    )


def test_upside_calculation():
    res = run_dcf(
        base_year_revenue=1000,
        scenario_assumptions=_one_year_scenario(),
        wacc=0.10,
        terminal_growth=0.02,
        exit_multiple=10,
        shares_outstanding=10,
        current_price=100.0,
    )
    assert res.upside == pytest.approx(res.per_share_value / 100.0 - 1.0)


# --- warnings --------------------------------------------------------------

def test_warns_when_wacc_le_terminal_growth():
    res = run_dcf(
        base_year_revenue=1000,
        scenario_assumptions=_one_year_scenario(),
        wacc=0.03,
        terminal_growth=0.05,
        exit_multiple=10,
        shares_outstanding=10,
    )
    assert any("terminal growth" in w for w in res.warnings)
    assert res.terminal_perpetual.terminal_value == 0.0


def test_warns_on_zero_shares():
    res = run_dcf(
        base_year_revenue=1000,
        scenario_assumptions=_one_year_scenario(),
        wacc=0.10,
        terminal_growth=0.02,
        exit_multiple=10,
        shares_outstanding=0,
    )
    assert res.per_share_value == 0.0
    assert any("Share count" in w for w in res.warnings)


def test_no_forecast_years_raises():
    empty = ScenarioAssumptions(scenario=Scenario.BASE)
    with pytest.raises(ValueError):
        run_dcf(1000, empty, 0.10, 0.02, 10, shares_outstanding=10)


# --- scenarios on the demo assumption set ----------------------------------

def test_scenarios_order_bull_ge_base_ge_bear():
    from services.demo_data import build_default_assumptions, load_demo_fixture

    aset = build_default_assumptions(load_demo_fixture())
    results = run_scenarios(aset, current_price=900.0)
    bear = results[Scenario.BEAR].per_share_value
    base = results[Scenario.BASE].per_share_value
    bull = results[Scenario.BULL].per_share_value
    assert bull > base > bear
    assert all(math.isfinite(v) for v in (bear, base, bull))
