"""CSV exports (§28). Simple, dependency-light strings for download."""
from __future__ import annotations

import csv
import datetime as _dt
import io
from typing import Optional


def valuation_summary_csv(
    company, fv, model_version: str = "dcf-1.0",
    analyst: str = "analyst", sources: Optional[list[str]] = None,
) -> str:
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["field", "value"])
    w.writerow(["company", f"{company.name} ({company.ticker})"])
    w.writerow(["valuation_date", _dt.date.today().isoformat()])
    w.writerow(["analyst", analyst])
    w.writerow(["model_version", model_version])
    w.writerow(["sources", "; ".join(sources or [])])
    w.writerow(["current_price", fv.current_price])
    w.writerow(["bear", round(fv.bear, 2)])
    w.writerow(["base", round(fv.base, 2)])
    w.writerow(["bull", round(fv.bull, 2)])
    w.writerow(["blended", round(fv.blended_value, 2)])
    w.writerow(["upside", round(fv.upside, 4) if fv.upside is not None else ""])
    w.writerow(["confidence_score", fv.confidence_score])
    w.writerow([])
    w.writerow(["method", "per_share", "normalized_weight", "contribution"])
    for c in fv.blend.contributions:
        w.writerow([c.method.value, round(c.per_share_value, 2),
                    round(c.normalized_weight, 3), round(c.weighted_value, 2)])
    w.writerow(["DISCLAIMER", "Research/educational use only — not investment advice."])
    return buf.getvalue()


def method_results_csv(fv) -> str:
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["method", "per_share", "template_weight", "normalized_weight",
                "contribution"])
    for c in fv.blend.contributions:
        w.writerow([c.method.value, round(c.per_share_value, 2),
                    round(c.template_weight, 3), round(c.normalized_weight, 3),
                    round(c.weighted_value, 2)])
    return buf.getvalue()
