"""Valuation History — save and review permanent valuation runs (§25, §26)."""
from __future__ import annotations

import pandas as pd
import streamlit as st

from components.metric_cards import fmt_money, fmt_pct
from services.app_context import active_ticker, get_repo, get_valuation
from services.valuation_service import to_valuation_run


def render() -> None:
    st.header("Valuation History")
    ticker = active_ticker()
    repo = get_repo()
    fv = get_valuation()

    if fv is not None:
        if st.button("💾 Save current valuation", type="primary"):
            active = st.session_state.get("assumptions", {}).get(ticker)
            from config.lifecycle_weights import Lifecycle
            lifecycle = Lifecycle.MATURE_PROFITABLE
            company = repo.get_company(ticker)
            if company is not None:
                lifecycle = company.lifecycle
            run = to_valuation_run(fv, lifecycle)
            repo.save_valuation_run(run)
            st.success(f"Saved valuation for {ticker} (append-only, never overwritten).")

    runs = repo.list_valuation_runs(ticker)
    if not runs:
        st.info("No saved valuations yet. Save one above to start the audit trail.")
        return

    st.subheader(f"Saved runs — {ticker}")
    rows = []
    for r in runs:
        rows.append({
            "Date": r.valuation_date,
            "Price at time": fmt_money(r.current_price),
            "Bear": fmt_money(r.bear_value),
            "Base": fmt_money(r.base_value),
            "Bull": fmt_money(r.bull_value),
            "Blended": fmt_money(r.blended_value),
            "Upside": fmt_pct(r.upside) if r.upside is not None else "—",
            "Confidence": r.run_payload.get("confidence_score", "—"),
            "By": r.created_by,
        })
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    st.caption(
        "Runs are permanent records. 3/6/12-month outcome tracking and "
        "forecast-accuracy analytics attach here in Phase 9."
    )
