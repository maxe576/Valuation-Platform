"""Valuation Lab — a per-method workbench: DCF drivers, comps, weighting (§14–22)."""
from __future__ import annotations

import copy
from dataclasses import replace

import pandas as pd
import streamlit as st

from components.metric_cards import fmt_money, fmt_pct, fmt_x
from components.valuation_chart import valuation_range_chart
from models.common import Scenario
from processing.statements import latest_annual
from valuation import sensitivity as sens
from valuation.dcf import TerminalMethod, run_dcf
from valuation.wacc import build_wacc_for_company
from services.app_context import (
    active_ticker,
    get_valuation,
    load_active,
    save_working_assumptions,
)

_DRIVERS = [
    ("revenue_growth", "Revenue growth %"),
    ("ebit_margin", "EBIT margin %"),
    ("tax_rate", "Tax rate %"),
    ("da_pct_sales", "D&A % of sales"),
    ("capex_pct_sales", "CapEx % of sales"),
    ("nwc_pct_sales", "ΔNWC % of sales"),
]


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

    # Persistent header: the blended fair value up top, always visible.
    valuation_range_chart(fv.bear, fv.base, fv.bull, fv.blended_value, fv.current_price)
    cols = st.columns(4)
    cols[0].metric("Blended fair value", fmt_money(fv.blended_value))
    cols[1].metric("Upside", fmt_pct(fv.upside) if fv.upside is not None else "—")
    cols[2].metric("Method spread", fmt_pct(fv.blend.dispersion))
    cols[3].metric("Confidence", f"{fv.confidence_score:.0f}/100")

    tab_blend, tab_dcf, tab_comps, tab_diag = st.tabs(
        ["Blend & weights", "DCF workbench", "Comparables", "Diagnostics"])
    with tab_blend:
        _method_table(fv)
        _weight_editor(fv)
    with tab_dcf:
        _auto_wacc(active)
        _dcf_workbench(active)
        _sensitivity(active)
    with tab_comps:
        _comps_view(fv)
    with tab_diag:
        _dcf_detail(fv)
        _reverse(fv)


def _dcf_workbench(active) -> None:
    """Edit the base-case DCF drivers by year and see the full FCF build live."""
    if active is None or active.assumption_set is None:
        st.info("Load a company with a forecast to edit the DCF.")
        return
    aset = active.assumption_set
    base = aset.scenarios.get(Scenario.BASE)
    if base is None:
        return

    st.subheader("Edit DCF drivers by year")
    st.caption("Percentages below. Revenue → EBIT (margin) → less tax = NOPAT; "
               "plus D&A, less CapEx and ΔNWC = unlevered free cash flow.")
    n = base.years()
    cols = [f"Y{i+1}" for i in range(n)]
    data = {label: [round(getattr(base, key)[i] * 100, 1) for i in range(n)]
            for key, label in _DRIVERS}
    df = pd.DataFrame(data, index=cols).T
    edited = st.data_editor(df, use_container_width=True, key="dcf_wb")

    def col(label):
        return [float(x) / 100.0 for x in edited.loc[label].tolist()]

    sa = replace(base, **{key: col(label) for key, label in _DRIVERS})
    res = run_dcf(
        base_year_revenue=aset.base_year_revenue, scenario_assumptions=sa,
        wacc=aset.wacc, terminal_growth=aset.terminal_growth,
        exit_multiple=aset.exit_multiple, cash=aset.cash, investments=aset.investments,
        total_debt=aset.total_debt, minority_interest=aset.minority_interest,
        shares_outstanding=aset.shares_outstanding,
        terminal_method=TerminalMethod.PERPETUAL_GROWTH, current_price=active.price,
    )

    build = [{
        "Year": y.year_index, "Revenue": fmt_money(y.revenue), "EBIT": fmt_money(y.ebit),
        "NOPAT": fmt_money(y.ebiat), "D&A": fmt_money(y.da), "CapEx": fmt_money(y.capex),
        "ΔNWC": fmt_money(y.nwc_change), "Unlevered FCF": fmt_money(y.unlevered_fcf),
        "PV of FCF": fmt_money(y.pv_unlevered_fcf),
    } for y in res.years]
    st.dataframe(pd.DataFrame(build), use_container_width=True, hide_index=True)

    b = st.columns(4)
    b[0].metric("Enterprise value", fmt_money(res.enterprise_value))
    b[1].metric("Equity value", fmt_money(res.equity_value))
    b[2].metric("Value / share", fmt_money(res.per_share_value))
    b[3].metric("Upside", fmt_pct(res.upside) if res.upside is not None else "—")
    st.caption(f"WACC {aset.wacc:.1%} · terminal growth {aset.terminal_growth:.1%} · "
               f"terminal = {res.tv_pct_of_ev:.0%} of EV. Edit WACC/terminal in the "
               "Forecast Builder; set WACC via Auto-WACC above.")
    for w in res.warnings:
        st.warning(w)
    if st.button("💾 Save these drivers to the base case"):
        new = copy.deepcopy(aset)
        new.scenarios[Scenario.BASE] = sa
        save_working_assumptions(active_ticker(), new)
        st.success("Base-case drivers saved. The blended valuation will update.")


def _comps_view(fv) -> None:
    if not fv.comps:
        st.info("No peer multiples configured for this company. "
                "Peer comparison lives on the Peer Intelligence page.")
        return
    for metric, res in fv.comps.items():
        st.markdown(f"**{metric.replace('_', '/').upper()}**")
        c = st.columns(4)
        c[0].metric("Median", fmt_x(res.stats.median))
        c[1].metric("25th–75th", f"{res.stats.p25:.1f}–{res.stats.p75:.1f}x")
        c[2].metric("Implied $/sh", fmt_money(res.per_share_at_median))
        c[3].metric("Peers", str(res.stats.n))
    st.caption("Full peer table and premium/discount on the Peer Intelligence page.")


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
