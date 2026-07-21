"""FinancialFact — the atomic unit of financial data.

One reported (or calculated) number, fully annotated with period, unit, segment,
provenance, status, and confidence (§10). Everything downstream — statements,
forecasts, valuations — is assembled from these.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from .common import Confidence, DataStatus, FiscalPeriod, Provenance


@dataclass
class FinancialFact:
    metric: str                       # standardized key, e.g. "revenue"
    value: float
    fiscal_year: int
    fiscal_period: FiscalPeriod = FiscalPeriod.FY

    # What the filer actually called it (§5, §10).
    reported_label: Optional[str] = None

    unit: str = "USD"
    currency: str = "USD"

    period_start: Optional[str] = None  # ISO date
    period_end: Optional[str] = None    # ISO date

    # Segment / geography dimensions (blank = consolidated).
    segment: Optional[str] = None
    geography: Optional[str] = None

    status: DataStatus = DataStatus.REPORTED
    confidence: Confidence = Confidence.HIGH
    provenance: Provenance = field(default_factory=Provenance)

    # Analyst override trail (§10).
    analyst_override: bool = False
    override_reason: Optional[str] = None

    @property
    def is_usable_in_valuation(self) -> bool:
        """Low-confidence and unapproved AI values must not silently feed a
        valuation (§10)."""
        if self.status is DataStatus.AI_EXTRACTED_PENDING:
            return False
        if self.confidence is Confidence.LOW:
            return False
        return True

    def key(self) -> tuple:
        """Identity for de-duplication: metric + period + segment + geography."""
        return (
            self.metric,
            self.fiscal_year,
            self.fiscal_period.value,
            self.segment or "",
            self.geography or "",
        )
