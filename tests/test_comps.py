"""Tests for the comparable-company engine (§29)."""
from __future__ import annotations

import pytest

from valuation.comps import MultipleType, apply_multiple, percentile, run_comp


def test_percentile_interpolation():
    vals = [8, 10, 12, 14, 16]
    assert percentile(vals, 0.0) == 8
    assert percentile(vals, 1.0) == 16
    assert percentile(vals, 0.5) == 12
    assert percentile(vals, 0.25) == 10


def test_apply_ev_multiple_bridges_net_debt():
    # EV = 12 × 100 = 1200; equity = 1200 − 200 = 1000; per share = 100.
    ps = apply_multiple(MultipleType.EV, 12, 100, net_debt=200, shares_outstanding=10)
    assert ps == pytest.approx(100)


def test_apply_equity_multiple_direct():
    # P/E: equity = 20 × 50 = 1000; per share = 100.
    ps = apply_multiple(MultipleType.EQUITY, 20, 50, net_debt=0, shares_outstanding=10)
    assert ps == pytest.approx(100)


def test_run_comp_ev_ebitda_median_and_percentiles():
    res = run_comp(
        metric="ev_ebitda",
        peer_multiples=[8, 10, 12, 14, 16],
        target_fundamental=100,
        net_debt=200,
        shares_outstanding=10,
        target_own_multiple=15,
    )
    assert res.stats.median == pytest.approx(12)
    assert res.per_share_at_median == pytest.approx(100)     # (12·100−200)/10
    assert res.per_share_at_p25 == pytest.approx(80)         # (10·100−200)/10
    assert res.per_share_at_p75 == pytest.approx(120)        # (14·100−200)/10
    # Target trades at 15x vs 12x median → +25% premium.
    assert res.premium_discount_to_median == pytest.approx(0.25)


def test_run_comp_applied_multiple_override():
    res = run_comp(
        metric="ev_revenue",
        peer_multiples=[4, 5, 6],
        target_fundamental=100,
        net_debt=0,
        shares_outstanding=10,
        applied_multiple=7.0,
    )
    assert res.applied_multiple == pytest.approx(7.0)
    assert res.stats.median == pytest.approx(5.0)


def test_run_comp_empty_peers_raises():
    with pytest.raises(ValueError):
        run_comp("pe", [], 50, 0, 10)
