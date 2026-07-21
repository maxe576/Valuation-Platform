"""Segment-value table for Segment Studio / SOTP (§18, §26).

Kept separate from valuation_chart so the Segment Studio page can compose the
table and the chart independently.
"""
from __future__ import annotations

import pandas as pd
import streamlit as st

from valuation.sotp import SOTPResult


def sotp_table(result: SOTPResult) -> None:
    rows = [
        {"Segment": name, "Enterprise value ($B)": round(ev / 1e9, 2)}
        for name, ev in result.segments
    ]
    rows.append({"Segment": "— Corporate costs",
                 "Enterprise value ($B)": round(-result.capitalized_corporate_costs / 1e9, 2)})
    rows.append({"Segment": "Total EV",
                 "Enterprise value ($B)": round(result.enterprise_value / 1e9, 2)})
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
