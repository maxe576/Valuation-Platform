"""Metric alias resolution (§10, §25 metric_aliases).

Maps a company's raw reported label (or non-standard XBRL tag) to a standardized
metric key, with an approval workflow. Exact and normalized (case/space/punct)
matches against the known tag registry are automatic; anything else needs
analyst approval before it feeds a valuation.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional

from config.metric_mappings import METRIC_BY_KEY, TAG_TO_METRIC


def _normalize(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", s.lower())


# Normalized standard label -> metric key, for auto-resolution.
_LABEL_INDEX = {_normalize(m.label): m.key for m in METRIC_BY_KEY.values()}


@dataclass
class MetricAlias:
    raw_metric_name: str
    standardized_metric_name: str
    alias_type: str = "manual"          # "auto" | "manual"
    approval_status: str = "pending"    # "pending" | "approved" | "rejected"
    approved_by: Optional[str] = None


@dataclass
class MetricAliasStore:
    aliases: dict[str, MetricAlias] = field(default_factory=dict)

    def resolve(self, raw: str) -> Optional[str]:
        """Return the standardized metric key for a raw label/tag, or None.

        Resolution order: exact XBRL tag → normalized standard label →
        an approved stored alias. Pending/rejected aliases do not resolve.
        """
        if raw in TAG_TO_METRIC:
            return TAG_TO_METRIC[raw]
        norm = _normalize(raw)
        if norm in _LABEL_INDEX:
            return _LABEL_INDEX[norm]
        alias = self.aliases.get(norm)
        if alias and alias.approval_status == "approved":
            return alias.standardized_metric_name
        return None

    def add_alias(
        self,
        raw: str,
        standardized: str,
        approved: bool = False,
        approved_by: Optional[str] = None,
    ) -> MetricAlias:
        if standardized not in METRIC_BY_KEY:
            raise ValueError(f"Unknown standardized metric '{standardized}'.")
        alias = MetricAlias(
            raw_metric_name=raw,
            standardized_metric_name=standardized,
            alias_type="manual",
            approval_status="approved" if approved else "pending",
            approved_by=approved_by if approved else None,
        )
        self.aliases[_normalize(raw)] = alias
        return alias

    def approve(self, raw: str, approved_by: str) -> None:
        alias = self.aliases.get(_normalize(raw))
        if alias is None:
            raise KeyError(f"No alias registered for '{raw}'.")
        alias.approval_status = "approved"
        alias.approved_by = approved_by
