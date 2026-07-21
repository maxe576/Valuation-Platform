"""AIAnalysis — a stored, approvable AI research artifact (§24, §25).

AI never produces official financial numbers; it interprets a structured package
of already-verified facts. Every analysis records provider, model, prompt
version, the input sources it was given, and an approval flag.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class AIAnalysis:
    company_ticker: str
    analysis_type: str                   # e.g. "quarterly_memo", "valuation_memo"
    provider: str                        # "ollama" | "gemini"
    model: str
    prompt_version: str
    input_sources: list[str] = field(default_factory=list)
    output: dict[str, Any] = field(default_factory=dict)  # validated structured JSON
    analyst_approved: bool = False
    valuation_run_id: Optional[int] = None
    created_at: Optional[str] = None
    id: Optional[int] = None
