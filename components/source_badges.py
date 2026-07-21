"""Source badges + provenance rendering (§10, §27)."""
from __future__ import annotations

from typing import Optional

from models.common import Provenance


def source_badge(source: str) -> str:
    color = {
        "SEC EDGAR": "#0969da",
        "FMP": "#8250df",
        "FRED": "#1a7f37",
        "DEMO fixture": "#57606a",
        "analyst": "#9a6700",
    }.get(source, "#57606a")
    return (
        f"<span style='background:{color};color:#fff;padding:1px 7px;"
        f"border-radius:10px;font-size:0.72rem;font-weight:600'>{source}</span>"
    )


def provenance_caption(prov: Optional[Provenance]) -> str:
    """A compact one-line provenance string for tooltips/captions."""
    if prov is None:
        return ""
    bits = []
    if prov.source:
        bits.append(prov.source)
    if prov.xbrl_tag:
        bits.append(f"tag: {prov.xbrl_tag}")
    if prov.filing_accession:
        bits.append(f"accn: {prov.filing_accession}")
    return " · ".join(bits)
