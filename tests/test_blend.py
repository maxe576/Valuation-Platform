"""Tests for the blend / method-weighting engine (§29)."""
from __future__ import annotations

import pytest

from config.lifecycle_weights import Method
from models.common import Confidence
from valuation.blend import BlendInput, blend


def test_blend_excludes_reverse_dcf_and_normalizes():
    inputs = [
        BlendInput(Method.DCF, 100, template_weight=0.45, confidence=Confidence.HIGH),
        BlendInput(Method.COMPARABLES, 120, template_weight=0.30,
                   confidence=Confidence.MEDIUM),
        BlendInput(Method.REVERSE_DCF, 90, template_weight=0.0),  # must be ignored
    ]
    res = blend(inputs)
    methods = {c.method for c in res.contributions}
    assert Method.REVERSE_DCF not in methods

    # adjusted: dcf 0.45×1.0=0.45; comps 0.30×0.7=0.21; total 0.66.
    total = 0.45 + 0.21
    exp = (0.45 / total) * 100 + (0.21 / total) * 120
    assert res.blended_value == pytest.approx(exp)
    assert sum(c.normalized_weight for c in res.contributions) == pytest.approx(1.0)


def test_blend_drops_unavailable_and_nonpositive():
    inputs = [
        BlendInput(Method.DCF, 100, template_weight=0.5, confidence=Confidence.HIGH),
        BlendInput(Method.SOTP, -5, template_weight=0.5, confidence=Confidence.HIGH),
        BlendInput(Method.RESIDUAL_INCOME, 80, template_weight=0.5,
                   confidence=Confidence.HIGH, available=False),
    ]
    res = blend(inputs)
    assert [c.method for c in res.contributions] == [Method.DCF]
    assert res.blended_value == pytest.approx(100)


def test_market_multiple_dominance_warning():
    inputs = [
        BlendInput(Method.COMPARABLES, 100, template_weight=0.5,
                   confidence=Confidence.HIGH),
        BlendInput(Method.JUSTIFIED_MULTIPLE, 110, template_weight=0.5,
                   confidence=Confidence.HIGH),
        BlendInput(Method.DCF, 90, template_weight=0.1, confidence=Confidence.HIGH),
    ]
    res = blend(inputs)
    assert any("Market-multiple" in w for w in res.warnings)


def test_blend_dispersion_and_empty():
    assert blend([]).warnings  # no valid methods
    inputs = [
        BlendInput(Method.DCF, 100, template_weight=0.5, confidence=Confidence.HIGH),
        BlendInput(Method.COMPARABLES, 200, template_weight=0.5,
                   confidence=Confidence.HIGH),
    ]
    res = blend(inputs)
    assert res.dispersion > 0
