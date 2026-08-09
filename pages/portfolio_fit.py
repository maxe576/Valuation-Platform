"""Portfolio fit — score the club's holdings against the strategy."""
from __future__ import annotations

import io

import pandas as pd
import streamlit as st

from screener.scoring import score_company
from screener.universe import get_screener_universe
from services.app_context import get_strategy

_EXAMPLE = [
    ("META", 14), ("MSFT", 13), ("NVDA", 12), ("GOOGL", 11), ("NOW", 9),
    ("PANW", 8), ("CRM", 7), ("V", 6), ("INTC", 20),
]


def render() -> None:
    st.header("Portfolio fit")
    strategy = get_strategy()
    st.caption(f"Each holding scored against **{strategy.name}**. Upload a CSV with "
               "`ticker` and `weight` columns, or use the example.")

    holdings = _load_holdings()
    if not holdings:
        return

    meta = {row["ticker"]: row for row in get_screener_universe()}
    st.session_state["portfolio_tickers"] = [t for t, _ in holdings]

    rows, weighted_fit, total_w, passing_w = [], 0.0, 0.0, 0.0
    for ticker, weight in holdings:
        m = meta.get(ticker)
        if m is None:
            rows.append({"Ticker": ticker, "Weight": f"{weight:g}%", "Fit": None,
                         "Verdict": "NO DATA",
                         "Flag": "Not in the screener universe yet"})
            continue
        s = score_company(ticker, m, strategy)
        total_w += weight
        weighted_fit += weight * s.fit_score
        if s.verdict == "pass":
            passing_w += weight
        fails = s.failures()
        flag = ("On thesis" if s.verdict == "pass"
                else ", ".join(f.criterion.label.lower() for f in fails[:2]))
        rows.append({"Ticker": ticker, "Weight": f"{weight:g}%",
                     "Fit": s.fit_score, "Verdict": s.verdict.upper(), "Flag": flag})

    port_fit = round(weighted_fit / total_w, 0) if total_w else 0
    cols = st.columns(3)
    cols[0].metric("Portfolio fit (weighted)", f"{port_fit:.0f}/100")
    cols[1].metric("Weight on-thesis", f"{(passing_w/total_w*100 if total_w else 0):.0f}%")
    offs = [r for r in rows if r["Verdict"] == "FAIL"]
    cols[2].metric("Off-thesis holdings", str(len(offs)))

    st.dataframe(
        pd.DataFrame(rows), use_container_width=True, hide_index=True,
        column_config={"Fit": st.column_config.ProgressColumn(
            "Fit", min_value=0, max_value=100, format="%d")},
    )
    if offs:
        st.warning("Off-thesis positions worth a look: "
                   + ", ".join(f"**{r['Ticker']}** ({r['Flag']})" for r in offs))


def _load_holdings() -> list[tuple[str, float]]:
    up = st.file_uploader("Portfolio CSV", type=["csv"], label_visibility="collapsed")
    if up is not None:
        try:
            df = pd.read_csv(io.BytesIO(up.getvalue()))
            df.columns = [c.strip().lower() for c in df.columns]
            tcol = "ticker" if "ticker" in df.columns else df.columns[0]
            wcol = "weight" if "weight" in df.columns else None
            out = []
            for _, r in df.iterrows():
                t = str(r[tcol]).upper().strip()
                w = float(r[wcol]) if wcol else 100.0 / len(df)
                out.append((t, w))
            return out
        except Exception as exc:  # noqa: BLE001
            st.error(f"Couldn't read that CSV: {exc}. Expected columns: ticker, weight.")
            return []
    st.info("No file uploaded — showing an example portfolio. "
            "Upload your own CSV (ticker, weight) to score the club's book.")
    return list(_EXAMPLE)
