"""Assemble the structured data package handed to the AI layer (§24).

The AI never computes financial values — it interprets this package of already
verified facts, calculated ratios, valuation results, and source/confidence
labels. Only supplied information may be used downstream; the package IS the
allowed universe of facts.
"""
from __future__ import annotations

from typing import Any

from models.common import Confidence
from processing.statements import annual_series, latest_annual
from services.valuation_service import FullValuation


def build_analysis_package(company, facts: list, fv: FullValuation) -> dict[str, Any]:
    rev = annual_series(facts, "revenue")
    yrs = sorted(rev)
    growth = None
    if len(yrs) >= 2 and rev[yrs[-2]]:
        growth = rev[yrs[-1]] / rev[yrs[-2]] - 1.0

    high = sum(1 for f in facts if f.confidence is Confidence.HIGH)
    sources = sorted({f.provenance.source for f in facts if f.provenance.source})

    return {
        "company": {
            "name": company.name,
            "ticker": company.ticker,
            "sector": company.sector,
            "lifecycle": company.lifecycle.value,
        },
        "market": {
            "current_price": fv.current_price,
            "blended_fair_value": round(fv.blended_value, 2),
            "bear": round(fv.bear, 2),
            "base": round(fv.base, 2),
            "bull": round(fv.bull, 2),
            "upside": round(fv.upside, 4) if fv.upside is not None else None,
            "confidence_score": fv.confidence_score,
            "method_dispersion": round(fv.blend.dispersion, 4),
        },
        "financials": {
            "latest_revenue": latest_annual(facts, "revenue"),
            "revenue_growth_yoy": round(growth, 4) if growth is not None else None,
            "operating_income": latest_annual(facts, "operating_income"),
            "net_income": latest_annual(facts, "net_income"),
            "revenue_history": {str(y): rev[y] for y in yrs},
        },
        "methods": [
            {
                "method": c.method.value,
                "per_share": round(c.per_share_value, 2),
                "normalized_weight": round(c.normalized_weight, 3),
            }
            for c in fv.blend.contributions
        ],
        "comparables": {
            metric: {
                "median_multiple": round(res.stats.median, 2),
                "implied_per_share": round(res.per_share_at_median, 2),
                "premium_discount_to_median": (
                    round(res.premium_discount_to_median, 4)
                    if res.premium_discount_to_median is not None else None
                ),
            }
            for metric, res in fv.comps.items()
        },
        "reverse_dcf": [
            {"solves_for": r.solved_for, "market_implied": r.implied_value}
            for r in fv.reverse_dcf
        ],
        "warnings": fv.blend.warnings,
        "data_quality": {
            "facts_total": len(facts),
            "facts_high_confidence": high,
            "sources": sources,
        },
    }
