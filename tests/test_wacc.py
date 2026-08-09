"""Tests for the auto-WACC builder."""
from __future__ import annotations

import pytest

from valuation.wacc import compute_wacc


def test_capm_cost_of_equity_and_wacc():
    # Rf 4%, beta 1.2, ERP 5% → Ke = 4 + 1.2*5 = 10%.
    # Kd pre-tax 5%, tax 25% → after-tax 3.75%.
    # Weights: equity 900, debt 100 → We 0.9, Wd 0.1.
    # WACC = 0.9*10% + 0.1*3.75% = 9.375%.
    r = compute_wacc(risk_free=0.04, beta=1.2, erp=0.05,
                     pretax_cost_of_debt=0.05, tax_rate=0.25,
                     equity_value=900, debt_value=100)
    assert r.cost_of_equity == pytest.approx(0.10)
    assert r.after_tax_cost_of_debt == pytest.approx(0.0375)
    assert r.equity_weight == pytest.approx(0.9)
    assert r.wacc == pytest.approx(0.09375)


def test_all_equity_company():
    r = compute_wacc(risk_free=0.04, beta=1.0, erp=0.05, equity_value=100, debt_value=0)
    assert r.equity_weight == 1.0
    assert r.wacc == pytest.approx(r.cost_of_equity)


def test_default_cost_of_debt_from_risk_free():
    r = compute_wacc(risk_free=0.04, tax_rate=0.21, equity_value=100, debt_value=0)
    # pretax Kd defaults to rf + 1.5% spread = 5.5%.
    assert r.pretax_cost_of_debt == pytest.approx(0.055)


def test_breakdown_has_wacc_row():
    r = compute_wacc(equity_value=100, debt_value=20)
    labels = [k for k, _ in r.breakdown()]
    assert "WACC" in labels and "Cost of equity" in labels
