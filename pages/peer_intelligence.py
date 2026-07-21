"""Peer Intelligence — comps, premium/discount, justified multiple (§15–17, §26)."""
from __future__ import annotations

import pandas as pd
import streamlit as st

from components.metric_cards import fmt_money, fmt_pct, fmt_x
from components.peer_table import comp_stats_table
from services.app_context import get_valuation


def render() -> None:
    st.header("Peer Intelligence")
    fv = get_valuation()
    if fv is None:
        st.info("Build a forecast and add peers to compare.")
        return

    if not fv.comps:
        st.info("No peer multiples configured for this company.")
    for metric, result in fv.comps.items():
        st.subheader(metric.replace("_", "/").upper())
        cols = st.columns(4)
        cols[0].metric("Median", fmt_x(result.stats.median))
        cols[1].metric("25th–75th", f"{result.stats.p25:.1f}–{result.stats.p75:.1f}x")
        cols[2].metric("Implied $/sh (median)", fmt_money(result.per_share_at_median))
        cols[3].metric("Peers", str(result.stats.n))
        comp_stats_table(result)

    _justified(fv)
    _premium_discount(fv)


def _justified(fv) -> None:
    j = fv.justified
    if j is None:
        return
    st.divider()
    st.subheader("Justified multiple (regression)")
    if j.is_weak:
        for w in j.warnings:
            st.warning(w)
    cols = st.columns(3)
    cols[0].metric("Predicted multiple", fmt_x(j.predicted_target_multiple))
    cols[1].metric("R²", f"{j.r_squared:.2f}")
    cols[2].metric("Observations", str(j.n_observations))
    coef_rows = [{"Driver": "intercept", "Coefficient": round(j.intercept, 3)}]
    coef_rows += [{"Driver": k, "Coefficient": round(v, 3)} for k, v in j.coefficients.items()]
    st.dataframe(pd.DataFrame(coef_rows), use_container_width=True, hide_index=True)


def _premium_discount(fv) -> None:
    comp = fv.comps.get("ev_ebitda")
    if comp is None or comp.premium_discount_to_median is None:
        return
    st.divider()
    st.subheader("Premium / discount")
    st.metric(
        "Target vs peer median (EV/EBITDA)",
        fmt_pct(comp.premium_discount_to_median),
        help="Positive = target trades above the peer median multiple.",
    )
    st.caption(
        "A full premium/discount bridge (growth, margin, balance sheet, "
        "concentration, SBC) is populated as those drivers are entered (§16)."
    )
