"""Segment parsing, aliasing, and history (§12).

SEC Company Facts does not expose segment (dimensional) breakdowns cleanly, so
structured segment data comes from filings tables, FMP, or analyst entry and is
parsed here into :class:`SegmentFact` objects. A segment registry tracks aliases
and effective windows because companies rename/reorganize segments — renamed
segments are NEVER auto-merged; merging requires analyst approval.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional

from models.common import Confidence, DataStatus, Provenance, SegmentType
from models.segment import SegmentDefinition, SegmentFact


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", s.lower())


@dataclass
class SegmentRegistry:
    """Alias + history store mapping reported segment names to canonical names."""

    definitions: list[SegmentDefinition] = field(default_factory=list)
    _alias_to_canonical: dict[str, str] = field(default_factory=dict)

    def register(
        self,
        name: str,
        segment_type: SegmentType,
        standardized_name: Optional[str] = None,
        analyst_approved: bool = False,
        effective_start: Optional[str] = None,
        effective_end: Optional[str] = None,
    ) -> SegmentDefinition:
        d = SegmentDefinition(
            name=name,
            segment_type=segment_type,
            standardized_name=standardized_name or name,
            analyst_approved=analyst_approved,
            effective_start=effective_start,
            effective_end=effective_end,
        )
        self.definitions.append(d)
        return d

    def add_alias(self, reported_name: str, canonical_name: str, approved: bool) -> None:
        """Link a reported (possibly renamed) segment to a canonical name.

        Only *approved* aliases are honored — an unapproved rename does not merge
        history automatically (§12).
        """
        if approved:
            self._alias_to_canonical[_norm(reported_name)] = canonical_name

    def canonical_name(self, reported_name: str) -> str:
        """Resolve a reported name to its approved canonical name, else itself."""
        return self._alias_to_canonical.get(_norm(reported_name), reported_name)


def parse_segment_facts(
    raw_segments: list[dict],
    fiscal_year: int,
    fiscal_period: str = "FY",
    source: str = "analyst",
    registry: Optional[SegmentRegistry] = None,
) -> list[SegmentFact]:
    """Convert structured segment rows into SegmentFacts.

    Each row: ``{name, type, revenue, [operating_income], [ebitda_margin], ...}``.
    Names are resolved through the registry (approved aliases only).
    """
    prov = Provenance(source=source)
    facts: list[SegmentFact] = []
    for row in raw_segments:
        name = row["name"]
        canonical = registry.canonical_name(name) if registry else name
        seg_type = SegmentType(row.get("type", "business"))
        if "revenue" in row and row["revenue"] is not None:
            facts.append(
                SegmentFact(
                    segment_name=canonical,
                    metric="revenue",
                    value=float(row["revenue"]),
                    fiscal_year=fiscal_year,
                    fiscal_period=fiscal_period,
                    segment_type=seg_type,
                    status=DataStatus.REPORTED,
                    confidence=Confidence.MEDIUM,
                    provenance=prov,
                )
            )
        if row.get("operating_income") is not None:
            facts.append(
                SegmentFact(
                    segment_name=canonical,
                    metric="operating_income",
                    value=float(row["operating_income"]),
                    fiscal_year=fiscal_year,
                    fiscal_period=fiscal_period,
                    segment_type=seg_type,
                    status=DataStatus.REPORTED,
                    confidence=Confidence.MEDIUM,
                    provenance=prov,
                )
            )
    return facts
