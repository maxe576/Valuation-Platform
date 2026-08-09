"""Valuation Lab — all methods, weighting, sensitivity, reverse DCF (§14–22, §26)."""
from __future__ import annotations

import pandas as pd
import streamlit as st

from components.metric_cards import fmt_money, fmt_pct, fmt_x
from components.valuation_chart import valuation_range_chart
from models.common import Scenario
from processing.statements import latest_annual
from valuation import sensitivity as sens
from valuation.wacc import build_wacc_for_company
from services.app_context import (
    active_ticker,
    get_valuation,
    load_active,
    save_working_assumptions,
)


def render() -> None:
    st.header("Valuation Lab")
    active = load_active()
    fv = get_valuation()
    if fv is None:
        if active is not None and active.assumption_set is not None and not active.price:
            st.info("Enter the current share price in the sidebar (or let it "
                    "auto-fetch) so the valuation has something to compare against.")
        else:
            st.info("Load a company and build a forecast to run valuations.")
        return

    st.subheader("Blended fair value")
    valuation_range_chart(fv.bear, fv.base, fv.bull, fv.blended_value, fv.current_price)
    cols = st.columns(4)
    cols[0].metric("Blended", fmt_money(fv.blended_value))
    cols[1].metric("Upside", fmt_pct(fv.upside) if fv.upside is not None else "—")
    cols[2].metric("Dispersion", fmt_pct(fv.blend.dispersion))
    cols[3].metric("Confidence", f"{fv.confidence_score:.0f}/100")

    _method_table(fv)
    _weight_editor(fv)
    _auto_wacc(active)
    _dcf_detail(fv)
    _sensitivity(active)
    _reverse(fv)


def _auto_wacc(active) -> None:
    """Auto-calculate WACC (CAPM, like the Excel) and offer to apply it."""
    if active is None or active.assumption_set is None:
        return
    aset = active.assumption_set
    with st.expander("⚙️ Auto-WACC (calculated for you)"):
        shares = aset.shares_outstanding
        equity = (active.price * shares) if (active.price and shares) else 0.0

        # Tax rate from filings: income tax / operating income, else default.
        tax = latest_annual(active.facts, "income_tax")
        ebit = latest_annual(active.facts, "operating_income")
        tax_rate = None
        if tax and ebit and ebit > 0:
            tax_rate = max(0.0, min(0.35, tax / ebit))

        beta = st.number_input("Beta", value=1.0, step=0.05, format="%.2f",
                               help="Default 1.0. Enter the company's beta if you have it.")
        result = build_wacc_for_company(
            equity_value=equity or 1.0, debt_value=aset.total_debt,
            tax_rate=tax_rate, beta=beta,
        )
        rows = [{"Component": k, "Value": v} for k, v in result.breakdown()]
        st.dataframe(rows, use_container_width=True, hide_index=True)
        st.caption("Risk-free from FRED when configured (else a recent default); "
                   "tax rate from filings; equity/debt weights from market cap and debt.")
        if st.button(f"Apply WACC = {result.wacc*100:.2f}% to the model"):
            import copy
            new = copy.deepcopy(aset)
            new.wacc = round(result.wacc, 4)
            save_working_assumptions(active_ticker(), new)
            st.success(f"WACC set to {result.wacc*100:.2f}%. Reopen the page to see "
                       "the valuation update.")


def _method_table(fv) -> None:
    st.subheader("Method results")
    rows = []
    for c in fv.blend.contributions:
        rows.append({
            "Method": c.method.value.replace("_", " ").title(),
            "Per share": fmt_money(c.per_share_value),
            "Template wt": fmt_pct(c.template_weight, 0),
            "Normalized wt": fmt_pct(c.normalized_weight, 0),
            "Contribution": fmt_money(c.weighted_value),
        })
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    if fv.reverse_dcf:
        st.caption("Reverse DCF is shown below as a diagnostic — it is never weighted.")


def _weight_editor(fv) -> None:
    with st.expander("Adjust method weights (§22)"):
        st.caption("Override the template weights; the blend renormalizes live.")
        weights = {}
        for c in fv.blend.contributions:
            weights[c.method] = st.slider(
                c.method.value.replace("_", " ").title(),
                0.0, 1.0, float(c.template_weight), 0.05,
                key=f"w_{c.method.value}",
            )
        total = sum(weights.values())
        if total > 0:
            blended = sum(
                (weights[c.method] / total) * c.per_share_value
                for c in fv.blend.contributions
            )
            st.metric("Re-weighted blended value", fmt_money(blended))


def _dcf_detail(fv) -> None:
    with st.expander("DCF detail (base case)"):
        base = fv.dcf[Scenario.BASE]
        rows = [{
            "Year": y.year_index,
            "Revenue": fmt_money(y.revenue),
            "EBIT": fmt_money(y.ebit),
            "UFCF": fmt_money(y.unlevered_fcf),
            "PV UFCF": fmt_money(y.pv_unlevered_fcf),
        } for y in base.years]
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
        st.caption(
            f"Perpetual-growth TV {fmt_money(base.terminal_perpetual.terminal_value)} "
            f"(implied {fmt_x(base.terminal_perpetual.implied_ebitda_multiple)}) · "
            f"Exit-multiple TV {fmt_money(base.terminal_exit.terminal_value)} · "
            f"Terminal {fv.dcf[Scenario.BASE].tv_pct_of_ev:.0%} of EV"
        )
        if base.warnings:
            for w in base.warnings:
                st.warning(w)


def _sensitivity(active) -> None:
    aset = active.assumption_set
    base = aset.scenarios.get(Scenario.BASE)
    if base is None:
        return
    with st.expander("Sensitivity: WACC × terminal growth"):
        waccs = [round(aset.wacc + d, 3) for d in (-0.02, -0.01, 0.0, 0.01, 0.02)]
        growths = [round(aset.terminal_growth + d, 3) for d in (-0.01, -0.005, 0.0, 0.005, 0.01)]
        table = sens.wacc_vs_terminal_growth(aset, base, waccs, growths)
        df = pd.DataFrame(
            [[round(v, 2) for v in row] for row in table.cells],
            index=[f"{w:.1%}" for w in waccs],
            columns=[f"{g:.1%}" for g in growths],
        )
        st.dataframe(df, use_container_width=True)
        st.caption("Rows = WACC, columns = terminal growth; cells = implied $/share.")


def _reverse(fv) -> None:
    with st.expander("Reverse DCF — what the market is pricing in (§21)"):
        rows = []
        for r in fv.reverse_dcf:
            val = r.implied_value
            if val is None:
                shown = "unreachable in range"
            elif "multiple" in r.solved_for:
                shown = f"{val:.1f}x"
            else:
                shown = f"{val*100:.1f}%"
            rows.append({
                "Solves for": r.solved_for.replace("implied_", "").replace("_", " "),
                "Market-implied": shown,
            })
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
