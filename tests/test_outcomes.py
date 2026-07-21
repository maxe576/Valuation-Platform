"""Outcome-tracking and accuracy-analytics tests (§29)."""
from __future__ import annotations

import pytest

from models.common import Confidence
from models.valuation import ValuationRun
from services.outcomes import accuracy_summary, record_outcome


def _run(run_id, price, blended):
    return ValuationRun(
        company_ticker="X", valuation_date="2025-01-01", current_price=price,
        blended_value=blended, confidence=Confidence.MEDIUM, id=run_id,
    )


def test_record_outcome_math():
    run = _run(1, price=100.0, blended=120.0)
    o = record_outcome(run, "12m", observed_price=110.0, observed_date="2026-01-01")
    assert o.total_return == pytest.approx(0.10)          # 110/100 − 1
    assert o.forecast_error == pytest.approx((120 - 110) / 110)
    assert o.horizon == "12m"
    assert o.valuation_run_id == 1


def test_accuracy_summary_direction_hit_rate():
    # Run A predicted upside (120 vs 100), price rose → hit.
    a = _run(1, 100.0, 120.0)
    # Run B predicted downside (80 vs 100), price rose → miss.
    b = _run(2, 100.0, 80.0)
    outcomes = [
        record_outcome(a, "12m", 110.0),   # up
        record_outcome(b, "12m", 105.0),   # up (miss)
    ]
    summ = accuracy_summary([a, b], outcomes)
    assert summ.n == 2
    assert summ.direction_hit_rate == pytest.approx(0.5)
    assert summ.mean_abs_forecast_error > 0


def test_accuracy_summary_empty():
    summ = accuracy_summary([], [])
    assert summ.n == 0
    assert summ.mean_abs_forecast_error == 0.0
    assert summ.direction_hit_rate == 0.0
