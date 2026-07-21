"""Valuation range and waterfall charts (§27)."""
from __future__ import annotations

from typing import Optional

import pandas as pd
import streamlit as st


def valuation_range_chart(
    bear: float, base: float, bull: float, blended: float,
    current_price: Optional[float] = None,
) -> None:
    """Horizontal bar of the bear/base/bull/blended per-share values."""
    rows = [
        {"Case": "Bear", "Value": bear},
        {"Case": "Base", "Value": base},
        {"Case": "Bull", "Value": bull},
        {"Case": "Blended", "Value": blended},
    ]
    if current_price is not None:
        rows.append({"Case": "Price", "Value": current_price})
    df = pd.DataFrame(rows).set_index("Case")
    st.bar_chart(df, horizontal=True, use_container_width=True)


def segment_waterfall_chart(segments: list[tuple[str, float]]) -> None:
    """Segment enterprise-value contributions (§18)."""
    if not segments:
        st.info("No segment values to display.")
        return
    df = pd.DataFrame(
        [{"Segment": name, "Enterprise value ($B)": ev / 1e9} for name, ev in segments]
    ).set_index("Segment")
    st.bar_chart(df, use_container_width=True)
