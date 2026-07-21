"""Tests for the justified-multiple regression (§29)."""
from __future__ import annotations

import pytest

from valuation.justified_multiple import run_justified_multiple


def test_perfect_linear_fit_predicts_target():
    # multiple = 5 + 10 × growth, exactly.
    growths = [0.05, 0.10, 0.15, 0.20, 0.25, 0.30]
    peers = [{"growth": g, "multiple": 5 + 10 * g} for g in growths]

    res = run_justified_multiple(
        peers=peers,
        target_features={"growth": 0.20},
        features=["growth"],
    )
    assert res.r_squared == pytest.approx(1.0, abs=1e-6)
    assert res.intercept == pytest.approx(5.0, abs=1e-6)
    assert res.coefficients["growth"] == pytest.approx(10.0, abs=1e-6)
    assert res.predicted_target_multiple == pytest.approx(7.0, abs=1e-6)
    assert not res.is_weak


def test_too_few_observations_flags_weak():
    peers = [{"growth": 0.1, "multiple": 6}, {"growth": 0.2, "multiple": 7}]
    res = run_justified_multiple(
        peers=peers,
        target_features={"growth": 0.15},
        features=["growth"],
    )
    assert res.is_weak
    assert any("observations" in w for w in res.warnings)


def test_cap_and_override():
    growths = [0.05, 0.10, 0.15, 0.20, 0.25, 0.30]
    peers = [{"growth": g, "multiple": 5 + 10 * g} for g in growths]

    capped = run_justified_multiple(
        peers, {"growth": 0.20}, ["growth"], cap=6.5,
    )
    assert capped.applied_multiple == pytest.approx(6.5)

    overridden = run_justified_multiple(
        peers, {"growth": 0.20}, ["growth"],
        override_multiple=9.0, override_reason="analyst view",
    )
    assert overridden.applied_multiple == pytest.approx(9.0)
    assert overridden.override_reason == "analyst view"
