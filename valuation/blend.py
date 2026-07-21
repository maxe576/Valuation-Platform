"""Method-weighting / blend engine (§22).

Each method's template weight is scaled by data quality and model confidence,
then normalized across the *available* methods to 100%:

    adjusted weight = template weight × data quality × model confidence
    normalized weight = adjusted / Σ adjusted

The reverse DCF is a diagnostic and is never blended. Methods that are
unavailable or invalid (non-positive per-share) drop out and get zero weight.
The engine also reports valuation-method dispersion and flags when correlated
market-multiple methods dominate the blend.
"""
from __future__ import annotations

import statistics
from dataclasses import dataclass, field

from config.lifecycle_weights import Method
from models.common import Confidence

# Confidence -> multiplicative factor used for the model-confidence adjustment.
CONFIDENCE_FACTOR: dict[Confidence, float] = {
    Confidence.HIGH: 1.0,
    Confidence.MEDIUM: 0.7,
    Confidence.LOW: 0.4,
}

# Methods that lean on the same market-multiple signal (§22 caution).
_MARKET_MULTIPLE_METHODS = {Method.COMPARABLES, Method.JUSTIFIED_MULTIPLE}
_MARKET_MULTIPLE_CAP = 0.60


@dataclass
class BlendInput:
    method: Method
    per_share_value: float
    template_weight: float
    data_quality: float = 1.0                 # 0..1
    confidence: Confidence = Confidence.MEDIUM
    available: bool = True


@dataclass
class BlendContribution:
    method: Method
    per_share_value: float
    template_weight: float
    adjusted_weight: float
    normalized_weight: float
    weighted_value: float


@dataclass
class BlendResult:
    contributions: list[BlendContribution]
    blended_value: float
    dispersion: float                          # stdev / mean across included methods
    warnings: list[str] = field(default_factory=list)


def _is_included(b: BlendInput) -> bool:
    if b.method is Method.REVERSE_DCF:
        return False
    if not b.available:
        return False
    return b.per_share_value > 0


def blend(inputs: list[BlendInput]) -> BlendResult:
    included = [b for b in inputs if _is_included(b)]
    warnings: list[str] = []

    if not included:
        return BlendResult([], 0.0, 0.0, ["No valid methods available to blend."])

    adjusted = {
        b.method: b.template_weight * b.data_quality * CONFIDENCE_FACTOR[b.confidence]
        for b in included
    }
    total_adj = sum(adjusted.values())
    if total_adj <= 0:
        return BlendResult([], 0.0, 0.0,
                           ["All adjusted weights are zero; cannot blend."])

    contributions: list[BlendContribution] = []
    blended = 0.0
    for b in included:
        norm = adjusted[b.method] / total_adj
        weighted = norm * b.per_share_value
        blended += weighted
        contributions.append(
            BlendContribution(
                method=b.method,
                per_share_value=b.per_share_value,
                template_weight=b.template_weight,
                adjusted_weight=adjusted[b.method],
                normalized_weight=norm,
                weighted_value=weighted,
            )
        )

    values = [b.per_share_value for b in included]
    mean = statistics.mean(values)
    dispersion = (statistics.pstdev(values) / mean) if mean and len(values) > 1 else 0.0

    mm_weight = sum(
        c.normalized_weight for c in contributions
        if c.method in _MARKET_MULTIPLE_METHODS
    )
    if mm_weight > _MARKET_MULTIPLE_CAP:
        warnings.append(
            f"Market-multiple methods carry {mm_weight:.0%} of the blend "
            f"(> {_MARKET_MULTIPLE_CAP:.0%}); the result may double-count one signal."
        )

    return BlendResult(contributions, blended, dispersion, warnings)
