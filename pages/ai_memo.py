"""AI Research Memo — generate, review, approve (§24, §26)."""
from __future__ import annotations

import streamlit as st

from processing.ai_package import build_analysis_package
from services.ai_client import AIClient, ValidationError
from services.app_context import active_ticker, get_repo, get_valuation, load_active

_SECTIONS = [
    ("executive_summary", "Executive summary"),
    ("what_changed", "What changed"),
    ("revenue_analysis", "Revenue analysis"),
    ("growth_quality", "Growth quality"),
    ("margin_analysis", "Margin analysis"),
    ("cash_flow_quality", "Cash-flow quality"),
    ("guidance_interpretation", "Guidance interpretation"),
    ("competitive_implications", "Competitive implications"),
    ("peer_comparison", "Peer comparison"),
    ("multiple_premium_explanation", "Multiple premium/discount"),
    ("valuation_implications", "Valuation implications"),
]
_LIST_SECTIONS = [
    ("risks", "Risks"),
    ("catalysts", "Catalysts"),
    ("assumption_challenges", "Assumption challenges"),
    ("questions_for_analyst", "Questions for the analyst"),
]


def render() -> None:
    st.header("AI Research Memo")
    st.caption(
        "The AI interprets verified data only — it never computes valuations or "
        "invents numbers. Review and approve before relying on it (§24)."
    )
    active = load_active()
    fv = get_valuation()
    if active is None or fv is None:
        st.info("Build a forecast/valuation first, then generate a memo.")
        return

    ticker = active_ticker()
    if st.button("🧠 Generate AI memo", type="primary"):
        package = build_analysis_package(active.company, active.facts, fv)
        try:
            client = AIClient()
            analysis = client.generate_analysis(ticker, package)
            st.session_state.setdefault("ai_memo", {})[ticker] = analysis
        except ValidationError as exc:
            st.error(f"AI output failed validation and was rejected: {exc}")
        except Exception as exc:  # noqa: BLE001
            st.error(f"AI provider error: {exc}")

    analysis = st.session_state.get("ai_memo", {}).get(ticker)
    if analysis is None:
        return

    st.caption(
        f"Provider: **{analysis.provider}** · model: {analysis.model} · "
        f"prompt: {analysis.prompt_version} · sources: "
        f"{', '.join(analysis.input_sources) or '—'} · "
        f"{'✅ approved' if analysis.analyst_approved else '⏳ pending approval'}"
    )

    out = analysis.output
    for key, label in _SECTIONS:
        st.subheader(label)
        st.write(out.get(key, "—"))
    for key, label in _LIST_SECTIONS:
        st.subheader(label)
        for item in out.get(key, []):
            st.write("• " + item)

    col1, col2 = st.columns(2)
    if col1.button("✅ Approve memo"):
        analysis.analyst_approved = True
        get_repo().save_ai_analysis(analysis)
        st.success("Memo approved and saved to the audit trail.")
    if col2.button("❌ Reject memo"):
        st.session_state.get("ai_memo", {}).pop(ticker, None)
        st.warning("Memo rejected and discarded.")
