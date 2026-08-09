"""Scoring engine: score a company's metrics against a strategy (§ screener).

Produces a 0–100 fit score (share of criterion weight passed), a verdict
(pass / near / fail), and a plain-English explanation of the misses — the "why it
doesn't fit" the analyst asked for. Pure functions; no I/O.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from models.strategy import Criterion, Strategy

PASS_THRESHOLD = 75.0
NEAR_THRESHOLD = 55.0


@dataclass
class CriterionResult:
    criterion: Criterion
    value: Optional[float]
    passed: bool

    @property
    def no_data(self) -> bool:
        return self.value is None

    @property
    def value_text(self) -> str:
        return self.criterion.format_value(self.value)


@dataclass
class ScoreResult:
    ticker: str
    fit_score: float                 # 0–100
    results: list[CriterionResult]

    @property
    def verdict(self) -> str:
        if self.fit_score >= PASS_THRESHOLD:
            return "pass"
        if self.fit_score >= NEAR_THRESHOLD:
            return "near"
        return "fail"

    def failures(self) -> list[CriterionResult]:
        # A failure means the metric exists and did not clear the threshold.
        return [r for r in self.results if not r.passed and not r.no_data]

    def passes(self) -> list[CriterionResult]:
        return [r for r in self.results if r.passed]

    def missing(self) -> list[CriterionResult]:
        return [r for r in self.results if r.no_data]

    def reason(self) -> str:
        """Plain-English explanation of the score."""
        fails = self.failures()
        note = ""
        miss = self.missing()
        if miss:
            note = (f" ({len(miss)} criteria not scored — data pending: "
                    + ", ".join(m.criterion.label.lower() for m in miss) + ")")
        if not fails:
            return "Clears every criterion with available data." + note
        parts = [
            f"{r.criterion.label} ({r.value_text} vs {r.criterion.threshold_text()})"
            for r in fails
        ]
        n = len(fails)
        return (f"Falls short on {n} {'test' if n == 1 else 'tests'}: "
                + "; ".join(parts) + "." + note)


def score_company(ticker: str, metrics: dict, strategy: Strategy) -> ScoreResult:
    """Score one company against the strategy.

    Criteria whose metric is missing are excluded from the fit calculation (not
    counted as failures), so a company is scored only on the data available. The
    fit score is the share of *available* criterion weight that passed.
    """
    results: list[CriterionResult] = []
    got = 0.0
    available = 0.0
    for c in strategy.criteria:
        v = metrics.get(c.key)
        if v is None:
            results.append(CriterionResult(criterion=c, value=None, passed=False))
            continue
        available += c.weight
        passed = c.passes(v)
        if passed:
            got += c.weight
        results.append(CriterionResult(criterion=c, value=v, passed=passed))
    fit = (got / available * 100.0) if available else 0.0
    return ScoreResult(ticker=ticker, fit_score=round(fit, 1), results=results)


def score_universe(
    universe: list[dict], strategy: Strategy
) -> list[ScoreResult]:
    """Score every company in a universe and return results sorted best-first.

    Each universe row is a dict with at least ``ticker`` plus the metric keys.
    """
    scored = [
        score_company(row.get("ticker", "?"), row, strategy) for row in universe
    ]
    scored.sort(key=lambda s: s.fit_score, reverse=True)
    return scored
