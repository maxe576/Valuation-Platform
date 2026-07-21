"""Valuation History — save, export, and track outcomes (§25, §28, §9, §26)."""
from __future__ import annotations

import pandas as pd
import streamlit as st

from components.metric_cards import fmt_money, fmt_pct
from exports.csv_export import valuation_summary_csv
from exports.excel_export import build_excel
from exports.memo_export import build_markdown_memo
from services.app_context import active_ticker, get_repo, get_valuation
from services.outcomes import accuracy_summary, record_outcome
from services.valuation_service import to_valuation_run


def render() -> None:
    st.header("Valuation History")
    ticker = active_ticker()
    repo = get_repo()
    fv = get_valuation()
    company = repo.get_company(ticker)

    if fv is not None and company is not None:
        _save_and_export(ticker, repo, fv, company)

    runs = repo.list_valuation_runs(ticker)
    if not runs:
        st.info("No saved valuations yet. Save one above to start the audit trail.")
        return

    _runs_table(ticker, runs)
    _outcomes(ticker, runs)


def _save_and_export(ticker, repo, fv, company) -> None:
    aset = st.session_state.get("assumptions", {}).get(ticker)
    sources = sorted({f.provenance.source for f in repo.get_facts(ticker)
                      if f.provenance.source})

    c1, c2, c3, c4 = st.columns(4)
    if c1.button("💾 Save valuation", type="primary"):
        run = to_valuation_run(fv, company.lifecycle)
        repo.save_valuation_run(run)
        st.success(f"Saved {ticker} valuation (append-only).")

    if aset is not None:
        c2.download_button(
            "⬇️ Excel", data=build_excel(company, fv, aset, sources=sources),
            file_name=f"{ticker}_valuation.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    c3.download_button(
        "⬇️ CSV", data=valuation_summary_csv(company, fv, sources=sources),
        file_name=f"{ticker}_valuation.csv", mime="text/csv",
    )
    ai = st.session_state.get("ai_memo", {}).get(ticker)
    memo = build_markdown_memo(company, fv, ai.output if ai else None)
    c4.download_button(
        "⬇️ Memo (.md)", data=memo,
        file_name=f"{ticker}_memo.md", mime="text/markdown",
    )


def _runs_table(ticker, runs) -> None:
    st.subheader(f"Saved runs — {ticker}")
    rows = []
    for i, r in enumerate(runs):
        rows.append({
            "#": i + 1,
            "Date": r.valuation_date,
            "Price at time": fmt_money(r.current_price),
            "Bear": fmt_money(r.bear_value),
            "Base": fmt_money(r.base_value),
            "Bull": fmt_money(r.bull_value),
            "Blended": fmt_money(r.blended_value),
            "Upside": fmt_pct(r.upside) if r.upside is not None else "—",
            "Confidence": r.run_payload.get("confidence_score", "—"),
        })
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)


def _outcomes(ticker, runs) -> None:
    st.divider()
    st.subheader("Outcome tracking (§9)")
    st.caption("Record the observed price at a horizon to measure realized return "
               "and forecast error.")

    store = st.session_state.setdefault("outcomes", {}).setdefault(ticker, [])
    with st.form("outcome_form"):
        cols = st.columns(3)
        idx = cols[0].number_input("Run #", min_value=1, max_value=len(runs), value=len(runs))
        horizon = cols[1].selectbox("Horizon", ["3m", "6m", "12m"])
        price = cols[2].number_input("Observed price", min_value=0.0, value=0.0, step=1.0)
        if st.form_submit_button("Record outcome") and price > 0:
            outcome = record_outcome(runs[int(idx) - 1], horizon, price)
            store.append(outcome)
            st.success(f"Recorded {horizon} outcome: "
                       f"{outcome.total_return:+.1%} return, "
                       f"{outcome.forecast_error:+.1%} forecast error.")

    if store:
        rows = [{
            "Horizon": o.horizon, "Observed": fmt_money(o.observed_price),
            "Total return": fmt_pct(o.total_return),
            "Forecast error": fmt_pct(o.forecast_error),
        } for o in store]
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
        summ = accuracy_summary(runs, store)
        c1, c2, c3 = st.columns(3)
        c1.metric("Outcomes", str(summ.n))
        c2.metric("Mean abs. forecast error", fmt_pct(summ.mean_abs_forecast_error))
        c3.metric("Direction hit rate", fmt_pct(summ.direction_hit_rate))
