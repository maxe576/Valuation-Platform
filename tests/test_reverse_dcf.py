"""Tests for the reverse-DCF solver (§29).

Round-trip: run a forward DCF at a known assumption to get a price, then confirm
the reverse solver recovers that assumption from the price.
"""
from __future__ import annotations

import pytest

from models.common import Scenario
from models.forecast import ScenarioAssumptions
from valuation.dcf import TerminalMethod, run_dcf
from valuation.reverse_dcf import (
    implied_exit_multiple,
    implied_revenue_growth,
)

BRIDGE = dict(cash=100.0, investments=0.0, total_debt=200.0,
              minority_interest=0.0, shares_outstanding=10.0)


def _template(growth: float) -> ScenarioAssumptions:
    n = 3
    return ScenarioAssumptions(
        scenario=Scenario.BASE,
        revenue_growth=[growth] * n,
        ebit_margin=[0.25] * n,
        tax_rate=[0.21] * n,
        da_pct_sales=[0.05] * n,
        capex_pct_sales=[0.05] * n,
        nwc_pct_sales=[0.0] * n,
    )


def test_reverse_recovers_growth():
    true_growth = 0.12
    fwd = run_dcf(
        base_year_revenue=1000,
        scenario_assumptions=_template(true_growth),
        wacc=0.09, terminal_growth=0.025, exit_multiple=12,
        terminal_method=TerminalMethod.PERPETUAL_GROWTH, **BRIDGE,
    )
    price = fwd.per_share_value

    res = implied_revenue_growth(
        base_year_revenue=1000,
        template=_template(0.0),          # starting guess irrelevant
        wacc=0.09, terminal_growth=0.025, exit_multiple=12,
        bridge=BRIDGE, market_price=price,
    )
    assert res.implied_value == pytest.approx(true_growth, abs=1e-4)


def test_reverse_recovers_exit_multiple():
    true_mult = 14.0
    fwd = run_dcf(
        base_year_revenue=1000,
        scenario_assumptions=_template(0.10),
        wacc=0.09, terminal_growth=0.025, exit_multiple=true_mult,
        terminal_method=TerminalMethod.EXIT_MULTIPLE, **BRIDGE,
    )
    price = fwd.per_share_value

    res = implied_exit_multiple(
        base_year_revenue=1000,
        template=_template(0.10),
        wacc=0.09, terminal_growth=0.025,
        bridge=BRIDGE, market_price=price,
    )
    assert res.implied_value == pytest.approx(true_mult, abs=1e-4)


def test_reverse_returns_none_when_unreachable():
    # An absurdly high price no assumption in-range can reach → None + note.
    res = implied_revenue_growth(
        base_year_revenue=1000,
        template=_template(0.0),
        wacc=0.09, terminal_growth=0.025, exit_multiple=12,
        bridge=BRIDGE, market_price=1e12,
    )
    assert res.implied_value is None
    assert res.note
