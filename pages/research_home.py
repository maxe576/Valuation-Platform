"""Research Home — the at-a-glance company dashboard (§26)."""
from __future__ import annotations

import streamlit as st

from components.metric_cards import fmt_money, fmt_pct, metric_row
from components.valuation_chart import valuation_range_chart
from models.common import Scenario
from processing.statements import annual_series, latest_annual
from processing.ttm import net_debt as _net_debt
from services.app_context import get_valuation, load_active


def render() -> None:
    st.header("Research Home")
    active = load_active()
    if active is None:
        return

    c = active.company
    st.subheader(f"{c.name} ({c.ticker})")
    st.caption(f"{c.sector or '—'} · CIK {c.cik or '—'} · lifecycle: {c.lifecycle.value}")

    price = active.price
    aset = active.assumption_set
    shares = aset.shares_outstanding if aset else 0.0
    mktcap = price * shares if (price and shares) else None
    nd = _net_debt(aset.total_debt, aset.cash, aset.investments) if aset else 0.0
    ev = (mktcap + nd) if mktcap is not None else None

    metric_row([
        ("Share price", fmt_money(price) if price else "—"),
        ("Market cap", fmt_money(mktcap)),
        ("Enterprise value", fmt_money(ev)),
        ("Net cash / (debt)", fmt_money(-nd)),
    ])

    _fundamentals_row(active.facts)

    fv = get_valuation()
    if fv is None:
        if aset is not None and not price:
            st.info("Enter the current share price in the sidebar (or let it "
                    "auto-fetch) to generate a valuation.")
        else:
            st.info("Add a forecast in the **Forecast Builder** to generate a valuation.")
        return

    st.divider()
    st.subheader("Valuation range")
    valuation_range_chart(fv.bear, fv.base, fv.bull, fv.blended_value, fv.current_price)

    rating, color = _rating(fv.upside)
    metric_row([
        ("Blended fair value", fmt_money(fv.blended_value)),
        ("Upside / (downside)", fmt_pct(fv.upside) if fv.upside is not None else "—"),
        ("Margin of safety", fmt_pct(fv.margin_of_safety) if fv.margin_of_safety is not None else "—"),
        ("Confidence score", f"{fv.confidence_score:.0f}/100"),
    ])
    st.markdown(f"**Rating:** :{color}[{rating}]  ·  "
                f"method dispersion {fv.blend.dispersion:.0%}")

    if fv.blend.warnings:
        with st.expander("⚠️ Blend warnings"):
            for w in fv.blend.warnings:
                st.write("• " + w)

    _data_quality(active.facts)


def _fundamentals_row(facts: list) -> None:
    rev = annual_series(facts, "revenue")
    growth = None
    if len(rev) >= 2:
        yrs = sorted(rev)
        if rev[yrs[-2]]:
            growth = rev[yrs[-1]] / rev[yrs[-2]] - 1.0
    oi = latest_annual(facts, "operating_income")
    r = latest_annual(facts, "revenue")
    op_margin = (oi / r) if (oi is not None and r) else None
    metric_row([
        ("Latest revenue", fmt_money(r)),
        ("Revenue growth (yoy)", fmt_pct(growth) if growth is not None else "—"),
        ("Operating margin", fmt_pct(op_margin) if op_margin is not None else "—"),
        ("Fiscal years loaded", str(len(rev))),
    ])


def _rating(upside):
    if upside is None:
        return "Not rated", "gray"
    if upside >= 0.20:
        return "Buy", "green"
    if upside <= -0.20:
        return "Sell", "red"
    return "Hold", "orange"


def _data_quality(facts: list) -> None:
    from models.common import Confidence

    total = len(facts)
    high = sum(1 for f in facts if f.confidence is Confidence.HIGH)
    st.caption(
        f"Data quality: {high}/{total} facts high-confidence · "
        f"sources: {', '.join(sorted({f.provenance.source for f in facts if f.provenance.source}))}"
    )
