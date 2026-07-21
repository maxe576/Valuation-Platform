"""Metric card helpers and number formatting (§27)."""
from __future__ import annotations

from typing import Optional

import streamlit as st


def fmt_money(x: Optional[float]) -> str:
    if x is None:
        return "—"
    a = abs(x)
    if a >= 1e12:
        return f"${x/1e12:,.2f}T"
    if a >= 1e9:
        return f"${x/1e9:,.2f}B"
    if a >= 1e6:
        return f"${x/1e6:,.2f}M"
    return f"${x:,.2f}"


def fmt_pct(x: Optional[float], digits: int = 1) -> str:
    if x is None:
        return "—"
    return f"{x*100:.{digits}f}%"


def fmt_x(x: Optional[float]) -> str:
    if x is None:
        return "—"
    return f"{x:.1f}x"


def metric_row(items: list[tuple[str, str]], deltas: Optional[list[Optional[str]]] = None) -> None:
    """Render a row of st.metric cards. ``items`` = [(label, value), ...]."""
    cols = st.columns(len(items))
    for i, (col, (label, value)) in enumerate(zip(cols, items)):
        delta = deltas[i] if deltas and i < len(deltas) else None
        col.metric(label, value, delta)
