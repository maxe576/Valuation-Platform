"""Standalone-quarter derivation and period growth (§11).

Many filers report income-statement and cash-flow items on a cumulative
year-to-date basis (3, 6, 9, 12 months). Standalone quarters are derived by
differencing consecutive cumulative periods:

    Q1 = 3-month
    Q2 = 6-month  − 3-month
    Q3 = 9-month  − 6-month
    Q4 = 12-month − 9-month

Derived quarters are marked ``calculated``. This differencing is valid for FLOW
metrics only — never for point-in-time balance-sheet values (§11).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from models.common import DataStatus


@dataclass
class StandaloneQuarter:
    period: str            # "Q1".."Q4"
    value: float
    status: DataStatus     # REPORTED for Q1, CALCULATED for derived quarters


def derive_standalone_quarters(
    cumulative: dict[int, float]
) -> list[StandaloneQuarter]:
    """Given cumulative flow values keyed by month-count (3/6/9/12), return the
    standalone quarters that can be computed. Missing inputs are skipped.
    """
    out: list[StandaloneQuarter] = []

    if 3 in cumulative:
        out.append(StandaloneQuarter("Q1", cumulative[3], DataStatus.REPORTED))
    if 6 in cumulative and 3 in cumulative:
        out.append(
            StandaloneQuarter("Q2", cumulative[6] - cumulative[3], DataStatus.CALCULATED)
        )
    if 9 in cumulative and 6 in cumulative:
        out.append(
            StandaloneQuarter("Q3", cumulative[9] - cumulative[6], DataStatus.CALCULATED)
        )
    if 12 in cumulative and 9 in cumulative:
        out.append(
            StandaloneQuarter("Q4", cumulative[12] - cumulative[9], DataStatus.CALCULATED)
        )
    return out


def sequential_growth(current: float, previous: float) -> Optional[float]:
    """Quarter-over-quarter growth. None if the prior base is zero."""
    if previous == 0:
        return None
    return current / previous - 1.0


def yoy_growth(current: float, year_ago: float) -> Optional[float]:
    """Year-over-year growth. None if the year-ago base is zero."""
    if year_ago == 0:
        return None
    return current / year_ago - 1.0
