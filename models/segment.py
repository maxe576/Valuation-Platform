"""Segment models: definitions (with alias/history) and per-period segment facts.

Companies rename and reorganize segments, so a segment definition carries an
effective window and a standardized name. Renamed segments are NOT auto-merged —
that requires analyst approval (§12).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from .common import Confidence, DataStatus, Provenance, SegmentType


@dataclass
class SegmentDefinition:
    name: str                        # as reported
    segment_type: SegmentType
    standardized_name: Optional[str] = None  # analyst-approved canonical name
    effective_start: Optional[str] = None
    effective_end: Optional[str] = None
    analyst_approved: bool = False
    id: Optional[int] = None


@dataclass
class SegmentFact:
    """A single segment metric for one period (revenue, operating income, ...)."""

    segment_name: str
    metric: str                      # e.g. "revenue", "operating_income"
    value: float
    fiscal_year: int
    fiscal_period: str = "FY"
    segment_type: SegmentType = SegmentType.BUSINESS
    unit: str = "USD"
    status: DataStatus = DataStatus.REPORTED
    confidence: Confidence = Confidence.MEDIUM  # dimensional facts default medium
    provenance: Provenance = field(default_factory=Provenance)
