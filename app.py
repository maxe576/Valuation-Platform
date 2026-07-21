"""Valuation Platform — Streamlit entry point.

This is a thin shell for now (full pages arrive in Phase 6). It proves the
vertical slice end to end: load a company (demo fixture or live SEC), show its
financials, and run the ported DCF across bear/base/bull. All heavy lifting lives
in the engines under valuation/ and processing/ — the UI only renders.
"""
from __future__ import annotations

import streamlit as st

from config.settings import SETTINGS, AppMode
from models.common import Scenario
from services.data_gateway import CompanyLoadError, load_company
from services.demo_data import DEMO_TICKER, build_demo_repository, demo_current_price
from valuation.dcf import TerminalMethod, run_scenarios

st.set_page_config(
    page_title="Valuation Platform",
    layout="wide",
    page_icon="📊",
    initial_sidebar_state="expanded",
)


@st.cache_resource
def _demo_repo():
    return build_demo_repository()


def _fmt_b(x: float) -> str:
    return f"${x/1e9:,.2f}B"


def main() -> None:
    st.title("📊 Valuation Platform")
    mode_label = "DEMO — fixture data" if SETTINGS.is_demo else "LIVE — SEC EDGAR"
    st.caption(
        f"Mode: **{mode_label}** · engines built through Phase 3 "
        "(DCF on real/normalized financials)."
    )

    with st.sidebar:
        st.header("Company")
        if SETTINGS.is_demo:
            st.info("Demo mode: the bundled fixture is **NFLX**. "
                    "Set `APP_MODE=live` in `.env` for any ticker.")
            ticker = st.text_input("Ticker", value=DEMO_TICKER)
        else:
            ticker = st.text_input("Ticker", value="AAPL")
        terminal_method = st.radio(
            "Terminal value method",
            [TerminalMethod.PERPETUAL_GROWTH, TerminalMethod.EXIT_MULTIPLE],
            format_func=lambda m: "Perpetual growth" if m is TerminalMethod.PERPETUAL_GROWTH
            else "Exit multiple",
        )
        run = st.button("Load & value", type="primary")

    if not run:
        st.write("Enter a ticker and click **Load & value**.")
        return

    repo = _demo_repo() if SETTINGS.is_demo else _live_repo()
    try:
        company, facts = load_company(ticker, repo)
    except CompanyLoadError as exc:
        st.error(str(exc))
        return

    price = demo_current_price() if SETTINGS.is_demo else None
    _render_company(company, facts)
    _render_valuation(ticker, repo, terminal_method, price)


@st.cache_resource
def _live_repo():
    from services.repository import InMemoryRepository

    return InMemoryRepository()


def _render_company(company, facts) -> None:
    st.subheader(f"{company.name} ({company.ticker})")
    cols = st.columns(4)
    cols[0].metric("Sector", company.sector or "—")
    cols[1].metric("CIK", company.cik or "—")
    cols[2].metric("Lifecycle", company.lifecycle.value)
    cols[3].metric("Facts loaded", str(len(facts)))

    from processing.statements import annual_series

    rev = annual_series(facts, "revenue")
    if rev:
        st.markdown("**Annual revenue**")
        st.dataframe(
            {"Fiscal year": list(rev.keys()),
             "Revenue": [_fmt_b(v) for v in rev.values()]},
            use_container_width=True, hide_index=True,
        )


def _render_valuation(ticker, repo, terminal_method, price) -> None:
    assumption_sets = repo.list_assumption_sets(ticker)
    if not assumption_sets:
        st.warning(
            "No forecast assumptions saved for this company yet. "
            "The Forecast Builder (Phase 6) will let you create them; "
            "the demo company ships with a default bear/base/bull set."
        )
        return

    aset = assumption_sets[-1]
    results = run_scenarios(aset, terminal_method=terminal_method, current_price=price)

    st.subheader("DCF valuation range")
    cols = st.columns(3)
    for col, scen in zip(cols, (Scenario.BEAR, Scenario.BASE, Scenario.BULL)):
        r = results.get(scen)
        if r:
            delta = f"{r.upside:+.1%} vs price" if r.upside is not None else None
            col.metric(scen.value.title(), f"${r.per_share_value:,.2f}", delta)

    base = results.get(Scenario.BASE)
    if base and base.warnings:
        with st.expander("⚠️ Model warnings"):
            for w in base.warnings:
                st.write("• " + w)

    if base:
        st.markdown("**Base-case projection**")
        st.dataframe(
            {
                "Year": [y.year_index for y in base.years],
                "Revenue": [_fmt_b(y.revenue) for y in base.years],
                "EBIT": [_fmt_b(y.ebit) for y in base.years],
                "Unlevered FCF": [_fmt_b(y.unlevered_fcf) for y in base.years],
                "PV of FCF": [_fmt_b(y.pv_unlevered_fcf) for y in base.years],
            },
            use_container_width=True, hide_index=True,
        )
        st.caption(
            f"EV {_fmt_b(base.enterprise_value)} · "
            f"Equity {_fmt_b(base.equity_value)} · "
            f"Terminal = {base.tv_pct_of_ev:.0%} of EV · "
            f"WACC {base.wacc:.1%}, g {base.terminal_growth:.1%}, "
            f"exit {base.exit_multiple:.0f}x"
        )


if __name__ == "__main__":
    main()
