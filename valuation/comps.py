"""Comparable-company valuation (§15).

Given peer multiples for a metric, compute the distribution (min / 25th / median
/ 75th / max), then apply a chosen multiple to the target's fundamental to imply
a per-share value. Handles both enterprise-value multiples (bridge through net
debt) and equity multiples. The analyst approves the peer set upstream — this
engine does not accept API peer suggestions on its own (§15).
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class MultipleType(str, Enum):
    EV = "ev"          # applies to an operating fundamental, bridges via net debt
    EQUITY = "equity"  # applies to an equity fundamental, straight to market cap


# Registry: multiple key -> (type, the target fundamental it multiplies).
MULTIPLE_REGISTRY: dict[str, tuple[MultipleType, str]] = {
    "ev_revenue": (MultipleType.EV, "revenue"),
    "ev_gross_profit": (MultipleType.EV, "gross_profit"),
    "ev_ebitda": (MultipleType.EV, "ebitda"),
    "ev_ebit": (MultipleType.EV, "ebit"),
    "ev_fcf": (MultipleType.EV, "fcf"),
    "pe": (MultipleType.EQUITY, "net_income"),
    "ps": (MultipleType.EQUITY, "revenue"),
    "pb": (MultipleType.EQUITY, "book_value"),
    "p_tangible_book": (MultipleType.EQUITY, "tangible_book_value"),
}


def percentile(values: list[float], q: float) -> float:
    """Linear-interpolation percentile (q in [0, 1]). Deterministic, no numpy."""
    if not values:
        raise ValueError("percentile of empty sequence")
    s = sorted(values)
    if len(s) == 1:
        return s[0]
    pos = q * (len(s) - 1)
    lo = int(pos)
    hi = min(lo + 1, len(s) - 1)
    frac = pos - lo
    return s[lo] + (s[hi] - s[lo]) * frac


@dataclass
class MultipleStats:
    metric: str
    values: list[float]

    @property
    def n(self) -> int:
        return len(self.values)

    @property
    def minimum(self) -> float:
        return min(self.values)

    @property
    def p25(self) -> float:
        return percentile(self.values, 0.25)

    @property
    def median(self) -> float:
        return percentile(self.values, 0.50)

    @property
    def p75(self) -> float:
        return percentile(self.values, 0.75)

    @property
    def maximum(self) -> float:
        return max(self.values)

    @property
    def mean(self) -> float:
        return sum(self.values) / len(self.values)


@dataclass
class CompResult:
    metric: str
    stats: MultipleStats
    per_share_at_median: float
    per_share_at_p25: float
    per_share_at_p75: float
    applied_multiple: float          # median, unless overridden
    target_own_multiple: Optional[float] = None
    premium_discount_to_median: Optional[float] = None  # target vs peer median


def apply_multiple(
    multiple_type: MultipleType,
    multiple_value: float,
    fundamental: float,
    net_debt: float,
    shares_outstanding: float,
) -> float:
    """Convert a multiple + fundamental into a per-share value."""
    if shares_outstanding <= 0:
        return 0.0
    if multiple_type is MultipleType.EV:
        implied_ev = multiple_value * fundamental
        equity = implied_ev - net_debt
    else:
        equity = multiple_value * fundamental
    return equity / shares_outstanding


def run_comp(
    metric: str,
    peer_multiples: list[float],
    target_fundamental: float,
    net_debt: float,
    shares_outstanding: float,
    target_own_multiple: Optional[float] = None,
    applied_multiple: Optional[float] = None,
) -> CompResult:
    """Run one metric's comparable analysis.

    ``applied_multiple`` defaults to the peer median; pass a value to use an
    analyst-selected (e.g. premium/discount-adjusted) multiple instead.
    """
    if metric not in MULTIPLE_REGISTRY:
        raise ValueError(f"Unknown multiple '{metric}'.")
    m_type, _fundamental_key = MULTIPLE_REGISTRY[metric]
    stats = MultipleStats(metric=metric, values=[v for v in peer_multiples if v is not None])
    if stats.n == 0:
        raise ValueError(f"No peer multiples supplied for '{metric}'.")

    chosen = applied_multiple if applied_multiple is not None else stats.median

    def ps(mult: float) -> float:
        return apply_multiple(m_type, mult, target_fundamental, net_debt, shares_outstanding)

    prem: Optional[float] = None
    if target_own_multiple is not None and stats.median:
        prem = target_own_multiple / stats.median - 1.0

    return CompResult(
        metric=metric,
        stats=stats,
        per_share_at_median=ps(stats.median),
        per_share_at_p25=ps(stats.p25),
        per_share_at_p75=ps(stats.p75),
        applied_multiple=chosen,
        target_own_multiple=target_own_multiple,
        premium_discount_to_median=prem,
    )
