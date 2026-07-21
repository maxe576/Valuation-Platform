"""Financial Statements — annual / quarterly / TTM views (§26)."""
from __future__ import annotations

import pandas as pd
import streamlit as st

from config.metric_mappings import METRICS, Statement
from models.common import FiscalPeriod
from services.app_context import load_active


def render() -> None:
    st.header("Financial Statements")
    active = load_active()
    if active is None:
        return
    facts = active.facts

    tab_income, tab_balance, tab_cash = st.tabs(
        ["Income statement", "Balance sheet", "Cash flow"]
    )
    period = st.session_state.get("stmt_period", FiscalPeriod.FY)

    with tab_income:
        _statement_table(facts, Statement.INCOME, period)
    with tab_balance:
        _statement_table(facts, Statement.BALANCE, period)
    with tab_cash:
        _statement_table(facts, Statement.CASH_FLOW, period)

    st.caption(
        "Values as reported to SEC EDGAR (or demo fixture). Each row maps a "
        "standardized metric to the filer's XBRL tag; hover a cell's source in "
        "the Research Home data-quality summary."
    )


def _statement_table(facts: list, statement: Statement, period: FiscalPeriod) -> None:
    metrics = [m for m in METRICS if m.statement is statement]
    keys = {m.key: m.label for m in metrics}

    # Collect annual (FY) values by metric x year.
    fy_facts = [f for f in facts if f.fiscal_period is FiscalPeriod.FY
                and f.metric in keys]
    years = sorted({f.fiscal_year for f in fy_facts})
    if not years:
        st.info("No data for this statement.")
        return

    rows = []
    for m in metrics:
        by_year = {f.fiscal_year: f.value for f in fy_facts if f.metric == m.key}
        if not by_year:
            continue
        row = {"Metric": m.label}
        for y in years:
            row[str(y)] = _fmt(by_year.get(y))
        rows.append(row)
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)


def _fmt(v):
    if v is None:
        return "—"
    a = abs(v)
    if a >= 1e9:
        return f"{v/1e9:,.2f}B"
    if a >= 1e6:
        return f"{v/1e6:,.1f}M"
    return f"{v:,.0f}"
