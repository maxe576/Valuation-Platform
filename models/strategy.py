"""Investment-strategy definition: criteria the screener scores against.

A Strategy is a named set of Criteria. Each Criterion tests one metric with a
comparison (≥, ≤, or a range) and carries a weight. The scoring engine
(screener/scoring.py) turns a company's metrics into a 0–100 fit score plus a
plain-English explanation of any misses. Defined once here, used by the screener,
portfolio scoring, and idea engine.

Metric unit conventions (what the universe builder must produce):
  * growth / margin metrics are PERCENT numbers  (15.0 == 15%)
  * multiples (ev_ebitda, ps) are plain ratios    (24.0 == 24x)
  * peg is a plain ratio
  * market_cap is in USD BILLIONS                  (10.0 == $10B)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class Operator(str, Enum):
    GTE = "gte"      # value must be >= threshold
    LTE = "lte"      # value must be <= threshold
    RANGE = "range"  # low <= value <= high


@dataclass
class Criterion:
    key: str                       # metric key, e.g. "revenue_growth"
    label: str
    operator: Operator
    weight: float                  # relative importance; weights need not sum to 100
    value: Optional[float] = None  # threshold for GTE / LTE
    low: Optional[float] = None    # range lower bound
    high: Optional[float] = None   # range upper bound
    unit: str = ""

    def passes(self, v: Optional[float]) -> bool:
        if v is None:
            return False
        if self.operator is Operator.GTE:
            return self.value is not None and v >= self.value
        if self.operator is Operator.LTE:
            return self.value is not None and v <= self.value
        if self.operator is Operator.RANGE:
            return (self.low is not None and self.high is not None
                    and self.low <= v <= self.high)
        return False

    def threshold_text(self) -> str:
        u = self.unit
        if self.operator is Operator.GTE:
            return f"≥ {self.value:g}{u}"
        if self.operator is Operator.LTE:
            return f"≤ {self.value:g}{u}"
        return f"{self.low:g}–{self.high:g}{u}"

    def format_value(self, v: Optional[float]) -> str:
        if v is None:
            return "n/a"
        if self.unit == "$B":
            return f"${v:,.0f}B" if v < 1000 else f"${v/1000:,.1f}T"
        return f"{v:g}{self.unit}"


@dataclass
class Strategy:
    name: str
    criteria: list[Criterion] = field(default_factory=list)

    def total_weight(self) -> float:
        return sum(c.weight for c in self.criteria) or 1.0


# The fund's starting strategy — every threshold is editable in the Strategy page.
DEFAULT_STRATEGY = Strategy(
    name="Quality Compounders",
    criteria=[
        Criterion("revenue_growth", "Revenue growth", Operator.GTE, 18, value=15, unit="%"),
        Criterion("ebit_margin", "EBIT margin", Operator.GTE, 15, value=20, unit="%"),
        Criterion("eps_growth", "Earnings growth", Operator.GTE, 15, value=15, unit="%"),
        Criterion("fcf_growth", "FCF growth", Operator.GTE, 12, value=15, unit="%"),
        Criterion("ev_ebitda", "EV/EBITDA", Operator.LTE, 12, value=25, unit="x"),
        Criterion("ps", "P/S", Operator.LTE, 10, value=15, unit="x"),
        Criterion("peg", "PEG", Operator.RANGE, 12, low=0.5, high=2.0),
        Criterion("market_cap", "Market cap", Operator.GTE, 6, value=10, unit="$B"),
    ],
)
