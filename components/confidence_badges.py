"""Confidence and data-status badges (§27)."""
from __future__ import annotations

from models.common import Confidence, DataStatus

_CONF_COLOR = {
    Confidence.HIGH: ("#1a7f37", "HIGH"),
    Confidence.MEDIUM: ("#9a6700", "MED"),
    Confidence.LOW: ("#b42318", "LOW"),
}

_STATUS_LABEL = {
    DataStatus.REPORTED: ("#1a7f37", "reported"),
    DataStatus.CALCULATED: ("#0969da", "calculated"),
    DataStatus.ANALYST_ESTIMATE: ("#9a6700", "analyst est."),
    DataStatus.AI_EXTRACTED_PENDING: ("#8250df", "AI pending"),
    DataStatus.MANUAL_OVERRIDE: ("#bc4c00", "override"),
}


def _pill(text: str, color: str) -> str:
    return (
        f"<span style='background:{color};color:#fff;padding:1px 7px;"
        f"border-radius:10px;font-size:0.72rem;font-weight:600'>{text}</span>"
    )


def confidence_badge(confidence: Confidence) -> str:
    color, label = _CONF_COLOR[confidence]
    return _pill(label, color)


def status_badge(status: DataStatus) -> str:
    color, label = _STATUS_LABEL[status]
    return _pill(label, color)
