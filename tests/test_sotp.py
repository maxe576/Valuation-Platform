"""Tests for the sum-of-the-parts engine (§29)."""
from __future__ import annotations

import pytest

from valuation.sotp import SegmentMethod, SegmentValuation, run_sotp


def _segments():
    return [
        SegmentValuation("A", SegmentMethod.MULTIPLE, fundamental=100, multiple=10),  # 1000
        SegmentValuation("B", SegmentMethod.MULTIPLE, fundamental=50, multiple=8),    # 400
    ]


def test_sotp_basic_bridge():
    res = run_sotp(
        _segments(),
        corporate_costs_annual=20,
        corporate_cost_multiple=5,     # capitalized 100
        cash=100,
        total_debt=300,
        shares_outstanding=10,
    )
    assert res.total_segment_ev == pytest.approx(1400)
    assert res.capitalized_corporate_costs == pytest.approx(100)
    assert res.enterprise_value == pytest.approx(1300)      # 1400 − 100
    assert res.equity_value == pytest.approx(1100)          # 1300 + 100 − 300
    assert res.per_share_value == pytest.approx(110)


def test_sotp_holdco_discount_applied_to_equity():
    res = run_sotp(
        _segments(),
        cash=0,
        total_debt=0,
        holdco_discount=0.10,
        shares_outstanding=10,
    )
    # EV 1400 → equity 1400 → ×0.9 = 1260 → 126 per share.
    assert res.equity_value_pre_discount == pytest.approx(1400)
    assert res.equity_value == pytest.approx(1260)
    assert res.per_share_value == pytest.approx(126)


def test_sotp_dcf_segment_uses_override():
    segs = [
        SegmentValuation("A", SegmentMethod.MULTIPLE, fundamental=100, multiple=10),
        SegmentValuation("B", SegmentMethod.DCF, enterprise_value_override=500),
    ]
    res = run_sotp(segs, shares_outstanding=10)
    assert res.total_segment_ev == pytest.approx(1500)


def test_sotp_dcf_segment_missing_override_raises():
    segs = [SegmentValuation("B", SegmentMethod.DCF)]
    with pytest.raises(ValueError):
        run_sotp(segs, shares_outstanding=10)
