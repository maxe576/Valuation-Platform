"""Data-quality checks: reconciliation and confidence rules (§10, §12).

A shared :func:`reconcile` powers both statement sanity checks (e.g. revenue −
cost of revenue ≈ gross profit) now and segment-sum-vs-consolidated checks in
Phase 5. Confidence downgrades follow the §10 rules.
"""
from __future__ import annotations

from dataclasses import dataclass

from config.settings import SETTINGS
from models.common import Confidence, DataStatus
from models.financial_fact import FinancialFact


@dataclass
class Reconciliation:
    total: float
    sum_of_parts: float
    tolerance: float

    @property
    def gap(self) -> float:
        return self.sum_of_parts - self.total

    @property
    def gap_pct(self) -> float:
        if self.total == 0:
            return 0.0
        return self.gap / self.total

    @property
    def within_tolerance(self) -> bool:
        return abs(self.gap_pct) <= self.tolerance


def reconcile(
    total: float, parts: list[float], tolerance: float | None = None
) -> Reconciliation:
    """Compare a reported total against the sum of its parts (§12)."""
    tol = SETTINGS.segment_reconciliation_tolerance if tolerance is None else tolerance
    return Reconciliation(total=total, sum_of_parts=sum(parts), tolerance=tol)


def effective_confidence(fact: FinancialFact) -> Confidence:
    """Apply §10 downgrade rules on top of the fact's stated confidence.

    Unapproved AI extractions and manual overrides without a reason are never
    treated as high confidence.
    """
    if fact.status is DataStatus.AI_EXTRACTED_PENDING:
        return Confidence.LOW
    if fact.status is DataStatus.MANUAL_OVERRIDE and not fact.override_reason:
        return Confidence.MEDIUM if fact.confidence is Confidence.HIGH else fact.confidence
    if fact.value is None:  # type: ignore[unreachable]
        return Confidence.LOW
    return fact.confidence
