"""Shared enums and small value objects used across all domain models.

Central to the platform's discipline (see §10): every material data point carries
a *status*, a *confidence*, and enough provenance to trace it back to a filing.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class DataStatus(str, Enum):
    """Where a value came from / how much to trust its provenance (§10)."""

    REPORTED = "reported"                    # straight from a filing
    CALCULATED = "calculated"                # derived by us (e.g. standalone quarter)
    ANALYST_ESTIMATE = "analyst_estimate"    # entered by the analyst
    AI_EXTRACTED_PENDING = "ai_extracted_pending"  # AI-read, needs approval
    MANUAL_OVERRIDE = "manual_override"      # analyst overrode a reported/calc value


class Confidence(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class Scenario(str, Enum):
    BEAR = "bear"
    BASE = "base"
    BULL = "bull"


class FilingType(str, Enum):
    TEN_K = "10-K"
    TEN_Q = "10-Q"
    EIGHT_K = "8-K"
    OTHER = "other"


class SegmentType(str, Enum):
    PRODUCT = "product"
    BUSINESS = "business"
    GEOGRAPHIC = "geographic"


class FiscalPeriod(str, Enum):
    """Reporting period a fact belongs to."""

    FY = "FY"      # full year
    Q1 = "Q1"
    Q2 = "Q2"
    Q3 = "Q3"
    Q4 = "Q4"
    TTM = "TTM"    # trailing twelve months (always calculated)


@dataclass(frozen=True)
class Provenance:
    """Traceability metadata attached to a value (§10)."""

    source: str = ""                 # e.g. "SEC EDGAR", "FMP", "analyst"
    source_url: Optional[str] = None
    xbrl_tag: Optional[str] = None
    xbrl_dimensions: Optional[dict[str, str]] = None
    filing_accession: Optional[str] = None
    collected_at: Optional[str] = None  # ISO date string; set at ingest time
