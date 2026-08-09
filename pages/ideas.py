"""Ideas — surface new names that fit the strategy but aren't owned."""
from __future__ import annotations

import streamlit as st

from components.metric_cards import fmt_pct
from screener.scoring import score_universe
from services.app_context import get_strategy, screener_universe, set_ticker


def render() -> None:
    st.header("Ideas")
    strategy = get_strategy()
    owned = set(st.session_state.get("portfolio_tickers", []))
    st.caption(f"Stocks that clear **{strategy.name}** and aren't in your portfolio. "
               "A research starting point, not a buy list.")

    universe = screener_universe()
    meta = {row["ticker"]: row for row in universe}
    scored = score_universe(universe, strategy)

    ideas = [s for s in scored if s.verdict == "pass" and s.ticker not in owned]
    if not ideas:
        st.info("No passing names outside your portfolio right now. "
                "Loosen the strategy or upload holdings on the Portfolio page.")
        return

    if owned:
        st.caption(f"Excluding {len(owned)} names you already hold.")

    for chunk_start in range(0, len(ideas), 3):
        cols = st.columns(3)
        for col, s in zip(cols, ideas[chunk_start:chunk_start + 3]):
            m = meta.get(s.ticker, {})
            with col.container(border=True):
                top = st.columns([2, 1])
                top[0].markdown(f"### {s.ticker}")
                top[1].markdown(f"**:green[{s.fit_score:.0f}]**")
                st.caption(m.get("name", ""))
                growth = m.get("revenue_growth")
                margin = m.get("ebit_margin")
                st.write(f"Revenue {fmt_pct((growth or 0)/100)} · EBIT margin "
                         f"{fmt_pct((margin or 0)/100)} · clears all "
                         f"{len(strategy.criteria)} criteria.")
                if st.button("Research →", key=f"idea_{s.ticker}"):
                    set_ticker(s.ticker)
                    st.success(f"{s.ticker} set as the active company — open "
                               "Company Model or Valuation to dig in.")
