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
        return [r for r in self.results if not r.passed]

    def passes(self) -> list[CriterionResult]:
        return [r for r in self.results if r.passed]

    def reason(self) -> str:
        """Plain-English explanation of the score."""
        fails = self.failures()
        if not fails:
            return "Clears every criterion in the strategy."
        parts = [
            f"{r.criterion.label} ({r.value_text} vs {r.criterion.threshold_text()})"
            for r in fails
        ]
        n = len(fails)
        return f"Falls short on {n} {'test' if n == 1 else 'tests'}: " + "; ".join(parts) + "."


def score_company(ticker: str, metrics: dict, strategy: Strategy) -> ScoreResult:
    """Score one company's metrics dict against the strategy."""
    results: list[CriterionResult] = []
    got = 0.0
    total = 0.0
    for c in strategy.criteria:
        v = metrics.get(c.key)
        passed = c.passes(v)
        total += c.weight
        if passed:
            got += c.weight
        results.append(CriterionResult(criterion=c, value=v, passed=passed))
    fit = (got / total * 100.0) if total else 0.0
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
