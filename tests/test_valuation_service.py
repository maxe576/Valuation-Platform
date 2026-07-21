"""Integration test: the full valuation orchestration on demo inputs (§29)."""
from __future__ import annotations

import math

from config.lifecycle_weights import Method
from models.common import Scenario
from services.valuation_service import (
    build_demo_valuation_inputs,
    run_full_valuation,
    to_valuation_run,
)


def test_full_valuation_runs_all_methods():
    inputs = build_demo_valuation_inputs()
    fv = run_full_valuation(inputs)

    # DCF scenarios ordered.
    assert fv.bull > fv.base > fv.bear
    # Comps produced for both metrics.
    assert "ev_ebitda" in fv.comps and "ev_revenue" in fv.comps
    # Justified, SOTP, RI all produced.
    assert fv.justified is not None
    assert fv.sotp is not None
    assert fv.residual_income is not None
    # Reverse DCF: three diagnostics, none blended.
    assert len(fv.reverse_dcf) == 3

    # Blend is finite and excludes reverse DCF.
    assert math.isfinite(fv.blended_value) and fv.blended_value > 0
    blended_methods = {c.method for c in fv.blend.contributions}
    assert Method.REVERSE_DCF not in blended_methods
    # high_growth_profitable template blends DCF/comps/justified/RI.
    assert Method.DCF in blended_methods

    assert 0.0 <= fv.confidence_score <= 100.0
    assert fv.upside is not None


def test_to_valuation_run_is_persistable():
    inputs = build_demo_valuation_inputs()
    fv = run_full_valuation(inputs)
    run = to_valuation_run(fv, inputs.lifecycle)
    assert run.company_ticker == "NFLX"
    assert run.blended_value == fv.blended_value
    assert run.method_results
    assert run.run_payload["confidence_score"] == fv.confidence_score
