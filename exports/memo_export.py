"""Research-memo export (§28).

Renders an approved AI memo + valuation summary to Markdown now; a formatted PDF
is a later enhancement (the directive prioritizes Excel/CSV first). Markdown keeps
the export dependency-free and easy to paste into docs.
"""
from __future__ import annotations

import datetime as _dt
from typing import Optional


def build_markdown_memo(company, fv, ai_output: Optional[dict] = None,
                        analyst: str = "analyst") -> str:
    lines = [
        f"# {company.name} ({company.ticker}) — Research Memo",
        f"_Date: {_dt.date.today().isoformat()} · Analyst: {analyst}_",
        "",
        "## Valuation summary",
        f"- Current price: **{fv.current_price}**",
        f"- Blended fair value: **{round(fv.blended_value, 2)}** "
        f"({fv.upside*100:.1f}% upside)" if fv.upside is not None
        else f"- Blended fair value: **{round(fv.blended_value, 2)}**",
        f"- Range: bear {round(fv.bear, 2)} · base {round(fv.base, 2)} "
        f"· bull {round(fv.bull, 2)}",
        f"- Confidence: {fv.confidence_score}/100 · dispersion "
        f"{fv.blend.dispersion*100:.0f}%",
        "",
        "## Method contributions",
    ]
    for c in fv.blend.contributions:
        lines.append(
            f"- {c.method.value}: {round(c.per_share_value, 2)} "
            f"(weight {c.normalized_weight*100:.0f}%)"
        )

    if ai_output:
        lines += ["", "## AI research memo"]
        for key, value in ai_output.items():
            title = key.replace("_", " ").title()
            lines.append(f"### {title}")
            if isinstance(value, list):
                lines += [f"- {v}" for v in value]
            else:
                lines.append(str(value))

    lines += [
        "",
        "---",
        "_Research/educational use only — not investment advice. Verify against "
        "primary filings._",
    ]
    return "\n".join(lines)
