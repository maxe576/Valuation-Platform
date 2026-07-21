"""Valuation result models: per-method results and the saved valuation run.

Valuation runs are permanent historical records — never overwritten (§25, §33).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from config.lifecycle_weights import Method
from .common import Confidence


@dataclass
class MethodResult:
    """Output of one valuation method for one run (§25 method_results)."""

    method: Method
    per_share_value: float
    equity_value: Optional[float] = None
    raw_weight: float = 0.0
    confidence: Confidence = Confidence.MEDIUM
    normalized_weight: float = 0.0
    assumptions: dict[str, Any] = field(default_factory=dict)
    results: dict[str, Any] = field(default_factory=dict)
    # Reverse DCF and unavailable/invalid methods are excluded from the blend.
    included_in_blend: bool = True


@dataclass
class ValuationRun:
    """A saved, timestamped valuation (§25 valuation_runs)."""

    company_ticker: str
    valuation_date: str                  # ISO date
    current_price: float

    bear_value: Optional[float] = None
    base_value: Optional[float] = None
    bull_value: Optional[float] = None
    blended_value: Optional[float] = None

    confidence: Confidence = Confidence.MEDIUM
    company_lifecycle: Optional[str] = None
    assumption_set_id: Optional[int] = None
    model_version: str = "dcf-1.0"
    created_by: Optional[str] = None
    approval_status: str = "draft"       # draft | approved | rejected

    method_results: list[MethodResult] = field(default_factory=list)
    run_payload: dict[str, Any] = field(default_factory=dict)
    created_at: Optional[str] = None
    id: Optional[int] = None

    @property
    def upside(self) -> Optional[float]:
        if self.blended_value is None or not self.current_price:
            return None
        return self.blended_value / self.current_price - 1.0


@dataclass
class ValuationOutcome:
    """Realized outcome of a valuation run at a horizon (§25 valuation_outcomes)."""

    valuation_run_id: Optional[int]
    horizon: str                     # "3m" | "6m" | "12m"
    observed_date: str               # ISO date
    observed_price: float
    total_return: float              # price change vs. price at valuation time
    forecast_error: float            # (blended fair value − observed) / observed
    notes: Optional[str] = None
    id: Optional[int] = None
