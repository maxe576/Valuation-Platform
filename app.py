"""Valuation Platform — Streamlit entry point (§26).

Multipage research app. The sidebar selects the active company; pages render
from the engines under valuation/ and processing/ via services/app_context.py.
Business logic never lives here — this file only wires navigation and state.
"""
from __future__ import annotations

import bootstrap  # noqa: F401  — must precede config imports (loads st.secrets → env)
import streamlit as st

from config.settings import SETTINGS
from services.app_context import active_ticker, set_ticker
from pages import (
    ai_memo,
    financial_statements,
    forecast_builder,
    peer_intelligence,
    quarterly_analysis,
    research_home,
    segment_studio,
    settings as settings_page,
    valuation_history,
    valuation_lab,
)

st.set_page_config(
    page_title="Valuation Platform",
    layout="wide",
    page_icon="📊",
    initial_sidebar_state="expanded",
)


def _sidebar() -> None:
    with st.sidebar:
        st.title("📊 Valuation Platform")
        mode = "DEMO — fixture data" if SETTINGS.is_demo else "LIVE — SEC EDGAR"
        st.caption(f"Mode: **{mode}**")

        if SETTINGS.is_demo:
            st.info("Demo mode: the bundled company is **NFLX**. "
                    "Set `APP_MODE=live` for any ticker.")
        with st.form("ticker_form", clear_on_submit=False):
            entered = st.text_input("Ticker", value=active_ticker())
            if st.form_submit_button("Load", type="primary"):
                set_ticker(entered)
        st.divider()
        st.caption("All 10 phases complete · research & paper-valuation only.")


def _page(func, title, icon, path):
    return st.Page(func, title=title, icon=icon, url_path=path)


NAV = {
    "Research": [
        _page(research_home.render, "Research Home", "🏠", "home"),
        _page(quarterly_analysis.render, "Quarterly Analysis", "📈", "quarterly"),
        _page(financial_statements.render, "Financial Statements", "📄", "financials"),
    ],
    "Model": [
        _page(forecast_builder.render, "Forecast Builder", "🧮", "forecast"),
        _page(valuation_lab.render, "Valuation Lab", "⚗️", "valuation"),
        _page(peer_intelligence.render, "Peer Intelligence", "👥", "peers"),
        _page(segment_studio.render, "Segment Studio", "🧩", "segments"),
    ],
    "Output": [
        _page(ai_memo.render, "AI Research Memo", "🧠", "ai-memo"),
        _page(valuation_history.render, "Valuation History", "🗃️", "history"),
        _page(settings_page.render, "Settings", "⚙️", "settings"),
    ],
}


def main() -> None:
    _sidebar()
    nav = st.navigation(NAV)
    nav.run()


if __name__ == "__main__":
    main()
