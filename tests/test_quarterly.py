"""Tests for quarterly-period logic, TTM, margins, and reconciliation (§29)."""
from __future__ import annotations

import pytest

from models.common import DataStatus
from processing.quality_checks import reconcile
from processing.quarterly_periods import (
    derive_standalone_quarters,
    sequential_growth,
    yoy_growth,
)
from processing.ttm import (
    ebitda_margin,
    fcf_margin,
    free_cash_flow,
    gross_margin,
    net_debt,
    operating_margin,
    safe_ratio,
    trailing_twelve_months,
)


def test_standalone_quarters_from_cumulative():
    # Cumulative: 3m=100, 6m=210, 9m=330, 12m=460.
    q = {sq.period: sq for sq in derive_standalone_quarters({3: 100, 6: 210, 9: 330, 12: 460})}
    assert q["Q1"].value == pytest.approx(100)   # reported
    assert q["Q2"].value == pytest.approx(110)   # 210 − 100
    assert q["Q3"].value == pytest.approx(120)   # 330 − 210
    assert q["Q4"].value == pytest.approx(130)   # 460 − 330
    assert q["Q1"].status is DataStatus.REPORTED
    assert q["Q4"].status is DataStatus.CALCULATED


def test_standalone_quarters_partial_inputs():
    # Only H1 available: Q1 reported, Q2 derived, no Q3/Q4.
    q = {sq.period for sq in derive_standalone_quarters({3: 50, 6: 120})}
    assert q == {"Q1", "Q2"}


def test_sequential_and_yoy_growth():
    assert sequential_growth(110, 100) == pytest.approx(0.10)
    assert yoy_growth(120, 100) == pytest.approx(0.20)
    assert sequential_growth(10, 0) is None
    assert yoy_growth(10, 0) is None


def test_ttm_sums_last_four_quarters():
    assert trailing_twelve_months([100, 110, 120, 130]) == pytest.approx(460)
    # More than four → last four only.
    assert trailing_twelve_months([90, 100, 110, 120, 130]) == pytest.approx(460)
    # Fewer than four → undefined.
    assert trailing_twelve_months([100, 110, 120]) is None


def test_margins_and_fcf():
    assert gross_margin(400, 1000) == pytest.approx(0.40)
    assert operating_margin(200, 1000) == pytest.approx(0.20)
    assert ebitda_margin(200, 50, 1000) == pytest.approx(0.25)
    assert fcf_margin(150, 1000) == pytest.approx(0.15)
    assert free_cash_flow(300, 120) == pytest.approx(180)     # capex magnitude
    assert free_cash_flow(300, -120) == pytest.approx(180)    # sign-agnostic
    assert safe_ratio(1, 0) is None


def test_net_debt_sign():
    assert net_debt(1000, 300, 100) == pytest.approx(600)     # net debt
    assert net_debt(100, 300, 50) == pytest.approx(-250)      # net cash


def test_reconcile_within_and_outside_tolerance():
    # Revenue 1000 − cost 600 should reconcile to gross profit 400.
    r = reconcile(total=400, parts=[1000, -600], tolerance=0.02)
    assert r.within_tolerance
    assert r.gap == pytest.approx(0)

    bad = reconcile(total=400, parts=[1000, -500], tolerance=0.02)
    assert not bad.within_tolerance
    assert bad.gap == pytest.approx(100)
