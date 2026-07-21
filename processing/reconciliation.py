"""Segment reconciliation (§12).

Compares the sum of reported segment revenue against consolidated company
revenue and flags gaps beyond a tolerance, with the usual candidate causes so an
analyst knows where to look.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from processing.quality_checks import Reconciliation, reconcile

_POSSIBLE_CAUSES = [
    "Corporate / unallocated revenue",
    "Intersegment eliminations",
    "Segment-definition changes",
    "Missing segment facts",
    "Foreign-exchange differences",
    "Rounding",
]


@dataclass
class SegmentReconciliation:
    reconciliation: Reconciliation
    possible_causes: list[str] = field(default_factory=list)

    @property
    def flagged(self) -> bool:
        return not self.reconciliation.within_tolerance

    @property
    def gap(self) -> float:
        return self.reconciliation.gap

    @property
    def gap_pct(self) -> float:
        return self.reconciliation.gap_pct


def reconcile_segment_revenue(
    segment_revenues: list[float],
    consolidated_revenue: float,
    tolerance: Optional[float] = None,
) -> SegmentReconciliation:
    rec = reconcile(consolidated_revenue, segment_revenues, tolerance)
    causes = list(_POSSIBLE_CAUSES) if not rec.within_tolerance else []
    return SegmentReconciliation(reconciliation=rec, possible_causes=causes)
