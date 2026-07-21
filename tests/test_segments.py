"""Tests for segment parsing, aliases, reconciliation, and FMP fallback (§29)."""
from __future__ import annotations

import pytest

from models.common import SegmentType
from processing.metric_aliases import MetricAliasStore
from processing.reconciliation import reconcile_segment_revenue
from processing.segment_parser import SegmentRegistry, parse_segment_facts
from services.fmp_client import FMPClient


# --- metric aliases --------------------------------------------------------

def test_alias_auto_resolution_by_tag_and_label():
    store = MetricAliasStore()
    # Known XBRL tag resolves automatically.
    assert store.resolve("OperatingIncomeLoss") == "operating_income"
    # Standard label (normalized) resolves automatically.
    assert store.resolve("Gross Profit") == "gross_profit"
    # Unknown returns None until an approved alias exists.
    assert store.resolve("Adjusted Widget Revenue") is None


def test_alias_requires_approval():
    store = MetricAliasStore()
    store.add_alias("Total Net Revenues", "revenue", approved=False)
    assert store.resolve("Total Net Revenues") is None  # pending
    store.approve("Total Net Revenues", approved_by="analyst")
    assert store.resolve("Total Net Revenues") == "revenue"


def test_alias_rejects_unknown_standard():
    with pytest.raises(ValueError):
        MetricAliasStore().add_alias("X", "not_a_metric", approved=True)


# --- segment registry / history -------------------------------------------

def test_renamed_segment_not_merged_until_approved():
    reg = SegmentRegistry()
    # Unapproved alias must NOT merge.
    reg.add_alias("Cloud Services", "Cloud Platform", approved=False)
    assert reg.canonical_name("Cloud Services") == "Cloud Services"
    # Approved alias merges to canonical.
    reg.add_alias("Cloud Services", "Cloud Platform", approved=True)
    assert reg.canonical_name("Cloud Services") == "Cloud Platform"


def test_parse_segment_facts_uses_canonical_name():
    reg = SegmentRegistry()
    reg.add_alias("Cloud Services", "Cloud Platform", approved=True)
    rows = [
        {"name": "Cloud Services", "type": "business", "revenue": 500,
         "operating_income": 100},
        {"name": "Devices", "type": "product", "revenue": 300},
    ]
    facts = parse_segment_facts(rows, fiscal_year=2024, registry=reg)
    names = {f.segment_name for f in facts}
    assert "Cloud Platform" in names and "Cloud Services" not in names
    assert any(f.metric == "operating_income" for f in facts)
    devices = [f for f in facts if f.segment_name == "Devices"][0]
    assert devices.segment_type is SegmentType.PRODUCT


# --- reconciliation --------------------------------------------------------

def test_segment_reconciliation_within_tolerance():
    r = reconcile_segment_revenue([500, 300, 200], consolidated_revenue=1000,
                                  tolerance=0.02)
    assert not r.flagged
    assert r.possible_causes == []


def test_segment_reconciliation_flags_gap_with_causes():
    # Parts sum 900 vs consolidated 1000 → 10% gap.
    r = reconcile_segment_revenue([500, 250, 150], consolidated_revenue=1000,
                                  tolerance=0.02)
    assert r.flagged
    assert r.gap == pytest.approx(-100)
    assert "Intersegment eliminations" in r.possible_causes


# --- FMP graceful degradation ---------------------------------------------

def test_fmp_disabled_without_key():
    client = FMPClient(api_key="")
    assert not client.enabled
    assert client.get_quote_price("NFLX") is None
    assert client.get_peers("NFLX") == []
    assert client.get_geographic_segmentation("NFLX") == []


def test_fmp_uses_injected_fetch_when_keyed():
    def fake_fetch(url, timeout):
        if "quote-short" in url:
            return [{"symbol": "NFLX", "price": 912.34}]
        return []

    client = FMPClient(api_key="demo", fetch_json=fake_fetch, cache=_NullCache())
    assert client.enabled
    assert client.get_quote_price("NFLX") == pytest.approx(912.34)


class _NullCache:
    def get(self, key, ttl_seconds=None):
        return None

    def set(self, key, data):
        pass
