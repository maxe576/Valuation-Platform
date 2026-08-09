"""Strategy — define the fund's screening criteria once; used everywhere."""
from __future__ import annotations

import copy

import streamlit as st

from models.strategy import Operator, Strategy
from services.app_context import get_strategy, set_strategy


def render() -> None:
    st.header("Strategy")
    strategy = get_strategy()
    st.caption(f"**{strategy.name}** — the screener, portfolio scoring, and idea "
               "engine all read from here. Change a threshold or weight and every "
               "score updates.")

    edited = copy.deepcopy(strategy)
    with st.form("strategy_form"):
        name = st.text_input("Strategy name", value=strategy.name)
        st.markdown("**Criteria**")
        hdr = st.columns([2.2, 1.4, 1.3, 1.3, 1])
        for col, t in zip(hdr, ["Criterion", "Test", "Threshold", "and", "Weight"]):
            col.markdown(f"<small style='color:#8a99ab'>{t}</small>", unsafe_allow_html=True)

        for c in edited.criteria:
            cols = st.columns([2.2, 1.4, 1.3, 1.3, 1])
            cols[0].markdown(f"**{c.label}**")
            cols[1].markdown(_op_text(c.operator))
            if c.operator is Operator.RANGE:
                c.low = cols[2].number_input(
                    f"low_{c.key}", value=float(c.low), label_visibility="collapsed")
                c.high = cols[3].number_input(
                    f"high_{c.key}", value=float(c.high), label_visibility="collapsed")
            else:
                c.value = cols[2].number_input(
                    f"val_{c.key}", value=float(c.value), label_visibility="collapsed")
                cols[3].markdown(f"<small>{c.unit or '—'}</small>", unsafe_allow_html=True)
            c.weight = cols[4].number_input(
                f"w_{c.key}", value=float(c.weight), min_value=0.0,
                label_visibility="collapsed")

        total = sum(c.weight for c in edited.criteria)
        st.caption(f"Total weight: {total:g} (weights are relative; they don't need "
                   "to sum to 100).")
        if st.form_submit_button("💾 Save strategy", type="primary"):
            edited.name = name
            set_strategy(edited)
            st.success("Strategy saved. Screener and portfolio scores now use it.")


def _op_text(op: Operator) -> str:
    return {Operator.GTE: "at least ≥", Operator.LTE: "at most ≤",
            Operator.RANGE: "between"}[op]
