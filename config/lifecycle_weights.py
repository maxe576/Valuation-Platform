"""Company-type valuation-method weighting templates (see §22).

These are *starting points*. The analyst may override every weight in the
Valuation Lab. The blend engine (Phase 4) further adjusts each weight by data
quality and model confidence, then normalizes to 100%.
"""
from __future__ import annotations

from enum import Enum


class Lifecycle(str, Enum):
    MATURE_PROFITABLE = "mature_profitable"
    HIGH_GROWTH_PROFITABLE = "high_growth_profitable"
    HIGH_GROWTH_UNPROFITABLE = "high_growth_unprofitable"
    FINANCIAL = "financial"
    CONGLOMERATE = "conglomerate"


class Method(str, Enum):
    DCF = "dcf"
    COMPARABLES = "comparables"
    JUSTIFIED_MULTIPLE = "justified_multiple"
    SOTP = "sotp"
    RESIDUAL_INCOME = "residual_income"
    REVERSE_DCF = "reverse_dcf"  # diagnostic only — never weighted (see §21)


# Raw template weights (must sum to 1.0 per lifecycle). Reverse DCF is
# intentionally excluded — it is a diagnostic, not a valuation input.
LIFECYCLE_WEIGHTS: dict[Lifecycle, dict[Method, float]] = {
    Lifecycle.MATURE_PROFITABLE: {
        Method.DCF: 0.45,
        Method.COMPARABLES: 0.30,
        Method.JUSTIFIED_MULTIPLE: 0.10,
        Method.RESIDUAL_INCOME: 0.15,
    },
    Lifecycle.HIGH_GROWTH_PROFITABLE: {
        Method.DCF: 0.30,
        Method.COMPARABLES: 0.35,
        Method.JUSTIFIED_MULTIPLE: 0.25,
        Method.RESIDUAL_INCOME: 0.10,
    },
    Lifecycle.HIGH_GROWTH_UNPROFITABLE: {
        Method.DCF: 0.20,  # scenario DCF
        Method.COMPARABLES: 0.40,  # EV/Revenue
        Method.JUSTIFIED_MULTIPLE: 0.40,  # forward multiple
        Method.RESIDUAL_INCOME: 0.0,
    },
    Lifecycle.FINANCIAL: {
        Method.RESIDUAL_INCOME: 0.40,
        Method.COMPARABLES: 0.35,  # P/B and P/E
        Method.DCF: 0.0,  # enterprise DCF not meaningful; FCFE handled elsewhere
        Method.JUSTIFIED_MULTIPLE: 0.25,
    },
    Lifecycle.CONGLOMERATE: {
        Method.SOTP: 0.40,
        Method.DCF: 0.30,
        Method.COMPARABLES: 0.30,
    },
}


def default_weights(lifecycle: Lifecycle) -> dict[Method, float]:
    """Return a copy of the template weights for a lifecycle."""
    return dict(LIFECYCLE_WEIGHTS[lifecycle])
