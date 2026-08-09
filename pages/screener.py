"""Screener — rank the market against the fund's strategy."""
from __future__ import annotations

import pandas as pd
import streamlit as st

from components.metric_cards import fmt_money, metric_row
from config.settings import SETTINGS
from screener.scoring import score_universe
from services.app_context import get_strategy, screener_universe


def render() -> None:
    st.header("Screener")
    strategy = get_strategy()
    source = "live SEC data" if not SETTINGS.is_demo else "demo seed list"
    st.caption(f"Scored against **{strategy.name}** · {len(strategy.criteria)} criteria "
               f"· universe from **{source}**. Edit criteria in the Strategy page.")
    if not SETTINGS.is_demo and not SETTINGS.fmp_enabled:
        st.info("Fundamental metrics are live from SEC. Valuation multiples "
                "(P/E, P/S, PEG, market cap) show **n/a** until a free FMP API key "
                "is added — set `FMP_API_KEY` in the app secrets to unlock them.")

    universe = screener_universe()
    scored = score_universe(universe, strategy)
    by_ticker = {s.ticker: s for s in scored}
    meta = {row["ticker"]: row for row in universe}

    passing = [s for s in scored if s.verdict == "pass"]
    avg = round(sum(s.fit_score for s in scored) / len(scored), 0) if scored else 0
    metric_row([
        ("Universe", str(len(scored))),
        ("Passing (≥75)", str(len(passing))),
        ("Average fit", f"{avg:.0f}"),
        ("Top score", f"{scored[0].fit_score:.0f} · {scored[0].ticker}" if scored else "—"),
    ])

    # Filters
    c1, c2 = st.columns([1, 2])
    min_fit = c1.slider("Minimum fit score", 0, 100, 0, 5)
    verdicts = c2.multiselect("Show", ["pass", "near", "fail"],
                              default=["pass", "near", "fail"])

    rows = []
    for s in scored:
        if s.fit_score < min_fit or s.verdict not in verdicts:
            continue
        m = meta.get(s.ticker, {})
        rows.append({
            "Ticker": s.ticker,
            "Company": m.get("name", ""),
            "Mkt cap": fmt_money(m["market_cap"] * 1e9) if m.get("market_cap") else "—",
            "Rev gr.": _pct(m.get("revenue_growth")),
            "EBIT %": _pct(m.get("ebit_margin")),
            "EPS gr.": _pct(m.get("eps_growth")),
            "FCF gr.": _pct(m.get("fcf_growth")),
            "EV/EBITDA": _x(m.get("ev_ebitda")),
            "PEG": _num(m.get("peg")),
            "P/S": _x(m.get("ps")),
            "Fit": s.fit_score,
            "Verdict": s.verdict.upper(),
        })
    st.dataframe(
        pd.DataFrame(rows), use_container_width=True, hide_index=True,
        column_config={"Fit": st.column_config.ProgressColumn(
            "Fit", min_value=0, max_value=100, format="%d")},
    )
    st.caption("Fit = share of criterion weight passed. PASS ≥ 75 · NEAR 55–74 · FAIL < 55.")

    st.divider()
    st.subheader("Why a stock fits — or doesn't")
    pick = st.selectbox("Inspect a company", [s.ticker for s in scored])
    if pick:
        _explain(by_ticker[pick])


def _explain(result) -> None:
    cols = st.columns(2)
    cols[0].metric("Fit score", f"{result.fit_score:.0f}/100")
    cols[1].metric("Verdict", result.verdict.upper())

    grid = st.columns(2)
    for i, r in enumerate(result.results):
        mark = "✅" if r.passed else "❌"
        val = r.value_text.replace("$", "\\$")
        thr = r.criterion.threshold_text().replace("$", "\\$")
        grid[i % 2].markdown(
            f"{mark} **{r.criterion.label}** — {val} (needs {thr})"
        )
    if result.failures():
        st.warning(result.reason())
    else:
        st.success(result.reason())


def _pct(v):
    return "—" if v is None else f"{v:+g}%"


def _x(v):
    return "—" if v is None else f"{v:g}×"


def _num(v):
    return "—" if v is None else f"{v:g}"
