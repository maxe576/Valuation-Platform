"""Settings & Administration — configuration and reference (§26)."""
from __future__ import annotations

import pandas as pd
import streamlit as st

from config.lifecycle_weights import LIFECYCLE_WEIGHTS
from config.settings import SETTINGS


def render() -> None:
    st.header("Settings & Administration")

    st.subheader("Run mode & data sources")
    st.write(f"**Mode:** {SETTINGS.mode.value}  ·  demo = fixture data, live = SEC EDGAR")
    st.write("**Source priority (§4):** SEC EDGAR → Investor Relations → FMP → "
             "FRED → Damodaran → analyst estimates → AI (pending approval)")

    st.subheader("API configuration")
    rows = [
        {"Service": "SEC EDGAR", "Status": "ready (no key required)",
         "Detail": "User-Agent set" if SETTINGS.sec_user_agent else "set SEC_USER_AGENT"},
        {"Service": "FMP", "Status": "enabled" if SETTINGS.fmp_enabled else "disabled",
         "Detail": "convenience source; redistribution may need a license"},
        {"Service": "FRED", "Status": "enabled" if SETTINGS.fred_api_key else "disabled",
         "Detail": "macro data"},
        {"Service": "Supabase", "Status": "enabled" if SETTINGS.supabase_enabled else "disabled",
         "Detail": "persistence (Phase 8)"},
        {"Service": f"AI ({SETTINGS.ai_provider.value})", "Status": "configured",
         "Detail": "Ollama local by default; never produces reported facts"},
    ]
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    st.caption("Keys are read from environment / .env — never entered or stored in the UI.")

    st.subheader("Confidence thresholds")
    st.write(f"Segment reconciliation tolerance: **{SETTINGS.segment_reconciliation_tolerance:.0%}**")

    st.subheader("Lifecycle valuation templates (§22)")
    rows = []
    for lifecycle, weights in LIFECYCLE_WEIGHTS.items():
        row = {"Lifecycle": lifecycle.value}
        for method, w in weights.items():
            row[method.value] = f"{w:.0%}"
        rows.append(row)
    st.dataframe(pd.DataFrame(rows).fillna("—"), use_container_width=True, hide_index=True)
