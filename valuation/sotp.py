"""Sum-of-the-parts valuation (§18).

Each segment is valued on its own basis — a peer multiple, a supplied mini-DCF
enterprise value, or an asset value — because unrelated business units should not
share one peer set. Segment EVs sum, corporate costs are capitalized and
subtracted, then the enterprise→equity bridge and an optional holding-company
discount produce a per-share value with a full waterfall.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class SegmentMethod(str, Enum):
    MULTIPLE = "multiple"
    DCF = "dcf"
    ASSET = "asset"


@dataclass
class SegmentValuation:
    name: str
    method: SegmentMethod = SegmentMethod.MULTIPLE
    fundamental: float = 0.0            # e.g. segment EBITDA (for MULTIPLE)
    multiple: float = 0.0               # e.g. EV/EBITDA (for MULTIPLE)
    enterprise_value_override: Optional[float] = None  # for DCF / ASSET
    metric_label: str = "EBITDA"

    def enterprise_value(self) -> float:
        if self.method is SegmentMethod.MULTIPLE:
            return self.fundamental * self.multiple
        if self.enterprise_value_override is None:
            raise ValueError(
                f"Segment '{self.name}' uses {self.method.value} but no "
                "enterprise_value_override was provided."
            )
        return self.enterprise_value_override


@dataclass
class SOTPResult:
    segments: list[tuple[str, float]]        # (name, EV) for the waterfall
    total_segment_ev: float
    capitalized_corporate_costs: float
    other_adjustments: float
    enterprise_value: float
    equity_value_pre_discount: float
    holdco_discount: float
    equity_value: float
    per_share_value: float
    warnings: list[str] = field(default_factory=list)


def run_sotp(
    segments: list[SegmentValuation],
    corporate_costs_annual: float = 0.0,
    corporate_cost_multiple: float = 0.0,
    other_enterprise_adjustments: float = 0.0,
    cash: float = 0.0,
    investments: float = 0.0,
    total_debt: float = 0.0,
    minority_interest: float = 0.0,
    pension_deficit: float = 0.0,
    holdco_discount: float = 0.0,
    shares_outstanding: float = 0.0,
) -> SOTPResult:
    if not segments:
        raise ValueError("SOTP requires at least one segment.")

    seg_evs = [(s.name, s.enterprise_value()) for s in segments]
    total_seg_ev = sum(ev for _, ev in seg_evs)

    # Unallocated corporate overhead is a negative-value stub capitalized at a
    # multiple, then subtracted from the segment sum.
    cap_corp = corporate_costs_annual * corporate_cost_multiple

    enterprise_value = total_seg_ev - cap_corp + other_enterprise_adjustments
    equity_pre = (
        enterprise_value + cash + investments
        - total_debt - minority_interest - pension_deficit
    )
    equity_value = equity_pre * (1.0 - holdco_discount)
    per_share = equity_value / shares_outstanding if shares_outstanding > 0 else 0.0

    warnings: list[str] = []
    if shares_outstanding <= 0:
        warnings.append("Share count is zero or negative; per-share value is invalid.")
    if not 0.0 <= holdco_discount < 1.0:
        warnings.append(
            f"Holding-company discount {holdco_discount:.0%} is outside 0–100%."
        )

    return SOTPResult(
        segments=seg_evs,
        total_segment_ev=total_seg_ev,
        capitalized_corporate_costs=cap_corp,
        other_adjustments=other_enterprise_adjustments,
        enterprise_value=enterprise_value,
        equity_value_pre_discount=equity_pre,
        holdco_discount=holdco_discount,
        equity_value=equity_value,
        per_share_value=per_share,
        warnings=warnings,
    )
