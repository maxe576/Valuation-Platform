"""Company — the top-level research subject."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from config.lifecycle_weights import Lifecycle


@dataclass
class Company:
    ticker: str
    name: str
    cik: Optional[str] = None            # 10-digit zero-padded SEC CIK
    sector: Optional[str] = None
    industry: Optional[str] = None
    fiscal_year_end: Optional[str] = None  # e.g. "12-31"
    currency: str = "USD"
    lifecycle: Lifecycle = Lifecycle.MATURE_PROFITABLE
    id: Optional[int] = None             # DB id once persisted

    def __post_init__(self) -> None:
        self.ticker = self.ticker.upper().strip()
        if self.cik is not None:
            # SEC CIKs are canonically 10 digits, zero-padded.
            self.cik = str(self.cik).lstrip("CIK").strip().zfill(10)
