"""Forecast Builder — edit bear/base/bull driver assumptions (§13, §26)."""
from __future__ import annotations

import copy
from dataclasses import replace

import pandas as pd
import streamlit as st

from models.common import Scenario
from services.app_context import active_ticker, load_active, save_working_assumptions

_DRIVERS = [
    ("revenue_growth", "Revenue growth"),
    ("ebit_margin", "EBIT margin"),
    ("tax_rate", "Tax rate"),
    ("da_pct_sales", "D&A % sales"),
    ("capex_pct_sales", "CapEx % sales"),
    ("nwc_pct_sales", "ΔNWC % sales"),
]


def render() -> None:
    st.header("Forecast Builder")
    active = load_active()
    if active is None or active.assumption_set is None:
        st.info("No forecast available. Load a company with revenue history first.")
        return

    aset = copy.deepcopy(active.assumption_set)
    st.caption(
        f"Editing **{aset.name}** for {aset.company_ticker}. "
        "Percentages are decimals (0.15 = 15%). Only revenue growth and EBIT "
        "margin differ across cases by default — mirroring the legacy switch model."
    )

    col1, col2, col3 = st.columns(3)
    aset.wacc = col1.number_input("WACC", value=float(aset.wacc), step=0.005, format="%.3f")
    aset.terminal_growth = col2.number_input(
        "Terminal growth", value=float(aset.terminal_growth), step=0.005, format="%.3f")
    aset.exit_multiple = col3.number_input(
        "Exit EV/EBITDA", value=float(aset.exit_multiple), step=0.5, format="%.1f")

    st.subheader("Enterprise → equity bridge")
    b1, b2, b3 = st.columns(3)
    aset.cash = b1.number_input("Cash", value=float(aset.cash), step=1e8, format="%.0f")
    aset.total_debt = b2.number_input("Total debt", value=float(aset.total_debt), step=1e8, format="%.0f")
    aset.shares_outstanding = b3.number_input(
        "Shares outstanding", value=float(aset.shares_outstanding), step=1e6, format="%.0f")

    st.subheader("Scenario drivers")
    tabs = st.tabs([s.value.title() for s in (Scenario.BEAR, Scenario.BASE, Scenario.BULL)])
    for tab, scen in zip(tabs, (Scenario.BEAR, Scenario.BASE, Scenario.BULL)):
        with tab:
            sa = aset.scenarios.get(scen)
            if sa is None:
                st.info(f"No {scen.value} scenario.")
                continue
            edited = _edit_scenario(sa, scen)
            aset.scenarios[scen] = edited

    if st.button("💾 Save assumptions", type="primary"):
        save_working_assumptions(active_ticker(), aset)
        st.success("Assumptions saved. Valuation will recompute on the next page.")


def _edit_scenario(sa, scen):
    n = sa.years()
    cols = [f"Y{i+1}" for i in range(n)]
    data = {label: getattr(sa, key) for key, label in _DRIVERS}
    df = pd.DataFrame(data, index=cols).T
    edited = st.data_editor(df, use_container_width=True, key=f"editor_{scen.value}")

    kwargs = {}
    for key, label in _DRIVERS:
        kwargs[key] = [float(x) for x in edited.loc[label].tolist()]
    return replace(sa, **kwargs)
