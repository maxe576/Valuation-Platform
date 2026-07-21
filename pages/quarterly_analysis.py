"""Quarterly Analysis — earnings trend and cash-flow quality (§23, §26)."""
from __future__ import annotations

import pandas as pd
import streamlit as st

from components.metric_cards import fmt_money, fmt_pct, metric_row
from models.common import FiscalPeriod
from processing.quarterly_periods import sequential_growth, yoy_growth
from processing.statements import annual_series, latest_annual
from processing.ttm import operating_margin
from services.app_context import load_active


def render() -> None:
    st.header("Quarterly Analysis")
    active = load_active()
    if active is None:
        return
    facts = active.facts

    quarterly = [f for f in facts if f.fiscal_period in
                 {FiscalPeriod.Q1, FiscalPeriod.Q2, FiscalPeriod.Q3, FiscalPeriod.Q4}
                 and f.metric == "revenue"]

    if quarterly:
        _quarterly_view(quarterly)
    else:
        st.info(
            "No standalone quarterly facts available for this company yet "
            "(the demo fixture ships annual data). Showing the annual trend."
        )
        _annual_trend(facts)

    _scorecard(facts)


def _quarterly_view(quarterly: list) -> None:
    q = sorted(quarterly, key=lambda f: (f.fiscal_year, f.fiscal_period.value))
    rows = []
    for i, f in enumerate(q):
        seq = sequential_growth(f.value, q[i - 1].value) if i > 0 else None
        yo = None
        if i >= 4:
            yo = yoy_growth(f.value, q[i - 4].value)
        rows.append({
            "Period": f"{f.fiscal_year} {f.fiscal_period.value}",
            "Revenue": fmt_money(f.value),
            "QoQ": fmt_pct(seq) if seq is not None else "—",
            "YoY": fmt_pct(yo) if yo is not None else "—",
        })
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)


def _annual_trend(facts: list) -> None:
    rev = annual_series(facts, "revenue")
    if not rev:
        return
    df = pd.DataFrame(
        [{"Year": str(y), "Revenue ($B)": v / 1e9} for y, v in rev.items()]
    ).set_index("Year")
    st.bar_chart(df, use_container_width=True)


def _scorecard(facts: list) -> None:
    st.subheader("Latest-year scorecard")
    rev = latest_annual(facts, "revenue")
    oi = latest_annual(facts, "operating_income")
    ni = latest_annual(facts, "net_income")
    metric_row([
        ("Revenue", fmt_money(rev)),
        ("Operating income", fmt_money(oi)),
        ("Operating margin",
         fmt_pct(operating_margin(oi, rev)) if (oi is not None and rev) else "—"),
        ("Net income", fmt_money(ni)),
    ])
    st.caption(
        "Beat/miss vs. internal forecast appears here once a forecast is saved. "
        "Consensus is only shown with a licensed/approved source (§23)."
    )
