"""Segment Studio — segment values, SOTP waterfall, reconciliation (§12, §18, §26)."""
from __future__ import annotations

import streamlit as st

from components.metric_cards import fmt_money
from components.segment_waterfall import sotp_table
from components.valuation_chart import segment_waterfall_chart
from processing.reconciliation import reconcile_segment_revenue
from processing.statements import latest_annual
from services.app_context import get_valuation, load_active


def render() -> None:
    st.header("Segment Studio")
    active = load_active()
    fv = get_valuation()
    if fv is None or fv.sotp is None:
        st.info(
            "No segment data configured. Segment revenue, peers, and multiples "
            "feed the sum-of-the-parts valuation (§18)."
        )
        return

    sotp = fv.sotp
    st.subheader("Sum-of-the-parts")
    cols = st.columns(3)
    cols[0].metric("Total segment EV", fmt_money(sotp.total_segment_ev))
    cols[1].metric("Enterprise value", fmt_money(sotp.enterprise_value))
    cols[2].metric("SOTP per share", fmt_money(sotp.per_share_value))

    segment_waterfall_chart(sotp.segments)
    sotp_table(sotp)

    _reconciliation(active, sotp)


def _reconciliation(active, sotp) -> None:
    if active is None:
        return
    consolidated = latest_annual(active.facts, "revenue")
    # Segment revenues aren't stored on the SOTP result (it holds EVs), so
    # reconciliation runs when segment revenue facts are available.
    st.divider()
    st.subheader("Segment reconciliation (§12)")
    st.caption(
        f"Consolidated revenue: {fmt_money(consolidated)}. When segment revenue "
        "facts are loaded, their sum is checked against this total and any gap "
        "beyond tolerance is flagged with likely causes (eliminations, corporate, "
        "FX, definition changes)."
    )
    # Demonstrate the check with the configured demo segments if present.
    seg_revs = st.session_state.get("segment_revenues")
    if seg_revs and consolidated:
        r = reconcile_segment_revenue(seg_revs, consolidated)
        if r.flagged:
            st.warning(f"Gap {r.gap_pct:+.1%}. Possible causes: "
                       + ", ".join(r.possible_causes))
        else:
            st.success("Segments reconcile within tolerance.")
