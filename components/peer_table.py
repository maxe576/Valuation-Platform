"""Peer comparison table (§15, §26)."""
from __future__ import annotations

import pandas as pd
import streamlit as st

from valuation.comps import CompResult


def peer_multiples_table(peers: list[dict]) -> None:
    if not peers:
        st.info("No peers configured.")
        return
    st.dataframe(pd.DataFrame(peers), use_container_width=True, hide_index=True)


def comp_stats_table(result: CompResult) -> None:
    s = result.stats
    df = pd.DataFrame([
        {"Statistic": "Minimum", "Multiple": round(s.minimum, 2)},
        {"Statistic": "25th pctile", "Multiple": round(s.p25, 2)},
        {"Statistic": "Median", "Multiple": round(s.median, 2)},
        {"Statistic": "75th pctile", "Multiple": round(s.p75, 2)},
        {"Statistic": "Maximum", "Multiple": round(s.maximum, 2)},
    ])
    st.dataframe(df, use_container_width=True, hide_index=True)
    if result.target_own_multiple is not None and result.premium_discount_to_median is not None:
        st.caption(
            f"Target trades at {result.target_own_multiple:.1f}x — "
            f"{result.premium_discount_to_median:+.0%} vs peer median."
        )
