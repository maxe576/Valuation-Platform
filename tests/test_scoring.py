"""Tests for the strategy scoring engine (§ screener)."""
from __future__ import annotations

import pytest

from models.strategy import Criterion, Operator, Strategy, DEFAULT_STRATEGY
from screener.scoring import score_company, score_universe
from screener.universe import seed_universe


def test_criterion_operators():
    gte = Criterion("g", "Growth", Operator.GTE, 10, value=15, unit="%")
    assert gte.passes(20) and not gte.passes(10) and not gte.passes(None)
    lte = Criterion("m", "Mult", Operator.LTE, 10, value=25, unit="x")
    assert lte.passes(20) and not lte.passes(30)
    rng = Criterion("peg", "PEG", Operator.RANGE, 10, low=0.5, high=2.0)
    assert rng.passes(1.0) and not rng.passes(2.5) and not rng.passes(0.2)


def test_perfect_stock_scores_100_and_no_reasons():
    metrics = {"ticker": "GREAT", "revenue_growth": 30, "ebit_margin": 40,
               "eps_growth": 40, "fcf_growth": 30, "ev_ebitda": 18, "ps": 8,
               "peg": 1.2, "market_cap": 500}
    r = score_company("GREAT", metrics, DEFAULT_STRATEGY)
    assert r.fit_score == 100.0
    assert r.verdict == "pass"
    assert r.failures() == []
    assert "Clears every criterion" in r.reason()


def test_failing_stock_explains_why():
    # Intel-like: negative growth, thin margins → should fail with reasons.
    metrics = {"ticker": "INTC", "revenue_growth": -1, "ebit_margin": 4,
               "eps_growth": -30, "fcf_growth": -20, "ev_ebitda": 12, "ps": 2.5,
               "peg": None, "market_cap": 90}
    r = score_company("INTC", metrics, DEFAULT_STRATEGY)
    assert r.verdict == "fail"
    assert r.fit_score < 55
    reason = r.reason()
    assert "Revenue growth" in reason
    assert "EBIT margin" in reason
    # Value multiples it does pass shouldn't appear as failures.
    passed_keys = {rr.criterion.key for rr in r.passes()}
    assert "ev_ebitda" in passed_keys and "ps" in passed_keys


def test_partial_score_weights():
    # Passes only revenue growth (weight 18) out of total weight.
    strat = Strategy("t", [
        Criterion("revenue_growth", "Rev", Operator.GTE, 60, value=15, unit="%"),
        Criterion("ebit_margin", "EBIT", Operator.GTE, 40, value=20, unit="%"),
    ])
    r = score_company("X", {"revenue_growth": 20, "ebit_margin": 5}, strat)
    assert r.fit_score == pytest.approx(60.0)  # 60 of 100 weight


def test_score_universe_sorted_and_covers_seed():
    scored = score_universe(seed_universe(), DEFAULT_STRATEGY)
    assert len(scored) == len(seed_universe())
    # Sorted best-first.
    assert all(scored[i].fit_score >= scored[i + 1].fit_score
               for i in range(len(scored) - 1))
    # INTC should land at/near the bottom.
    assert scored[-1].ticker in {"INTC", "F", "COST", "AAPL"}
