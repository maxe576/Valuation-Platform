"""Tests for the residual-income engine (§29)."""
from __future__ import annotations

import pytest

from valuation.residual_income import run_residual_income


def test_residual_income_hand_calc():
    res = run_residual_income(
        beginning_book_value=1000,
        net_income_forecast=[150, 160],
        cost_of_equity=0.10,
        terminal_growth=0.03,
        shares_outstanding=10,
        dividend_payout_ratio=0.0,
    )
    y1, y2 = res.years
    # Year 1: charge 100, RI 50, BV→1150.
    assert y1.equity_charge == pytest.approx(100)
    assert y1.residual_income == pytest.approx(50)
    assert y1.ending_book_value == pytest.approx(1150)
    # Year 2: charge 115, RI 45.
    assert y2.equity_charge == pytest.approx(115)
    assert y2.residual_income == pytest.approx(45)

    # PV forecast RI = 50/1.1 + 45/1.21.
    assert res.pv_forecast_ri == pytest.approx(50 / 1.1 + 45 / 1.21, rel=1e-9)
    # Terminal RI = 45·1.03/0.07, discounted at 1/1.21.
    tv = 45 * 1.03 / 0.07
    assert res.terminal_ri == pytest.approx(tv)
    assert res.pv_terminal_ri == pytest.approx(tv / 1.21, rel=1e-9)

    equity = 1000 + (50 / 1.1 + 45 / 1.21) + tv / 1.21
    assert res.equity_value == pytest.approx(equity, rel=1e-9)
    assert res.per_share_value == pytest.approx(equity / 10, rel=1e-9)


def test_warns_on_negative_book_value():
    res = run_residual_income(
        beginning_book_value=-100,
        net_income_forecast=[10],
        cost_of_equity=0.10,
        terminal_growth=0.03,
        shares_outstanding=10,
    )
    assert any("book value" in w.lower() for w in res.warnings)


def test_warns_when_coe_le_growth():
    res = run_residual_income(
        beginning_book_value=1000,
        net_income_forecast=[100],
        cost_of_equity=0.03,
        terminal_growth=0.05,
        shares_outstanding=10,
    )
    assert res.terminal_ri == 0.0
    assert any("terminal growth" in w for w in res.warnings)
