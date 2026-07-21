"""Filing — an SEC submission (10-K/10-Q/8-K) and its metadata."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from .common import FilingType


@dataclass
class Filing:
    accession_number: str
    form_type: FilingType
    filing_date: str                 # ISO date
    report_date: Optional[str] = None  # period the filing reports on
    primary_document: Optional[str] = None
    source_url: Optional[str] = None
    processing_status: str = "pending"  # pending | parsed | error
    company_cik: Optional[str] = None
    id: Optional[int] = None
