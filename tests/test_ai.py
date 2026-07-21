"""Tests for the AI layer: package, provider, validation, approval (§29)."""
from __future__ import annotations

import json

import pytest

from models.company import Company
from config.lifecycle_weights import Lifecycle
from processing.ai_package import build_analysis_package
from services.ai_client import (
    REQUIRED_KEYS,
    AIClient,
    DemoProvider,
    ValidationError,
    validate_output,
)
from services.valuation_service import build_demo_valuation_inputs, run_full_valuation


def _company_and_package():
    inputs = build_demo_valuation_inputs()
    fv = run_full_valuation(inputs)
    company = Company(ticker="NFLX", name="Netflix, Inc.",
                      lifecycle=Lifecycle.HIGH_GROWTH_PROFITABLE, sector="Comm")
    # Facts aren't needed richly here; package tolerates an empty history.
    from services.demo_data import build_demo_repository
    facts = build_demo_repository().get_facts("NFLX")
    return company, facts, fv


def test_package_contains_only_supplied_numbers():
    company, facts, fv = _company_and_package()
    pkg = build_analysis_package(company, facts, fv)
    assert pkg["company"]["ticker"] == "NFLX"
    assert pkg["market"]["blended_fair_value"] == round(fv.blended_value, 2)
    assert pkg["methods"]  # method contributions present
    assert "sources" in pkg["data_quality"]


def test_demo_provider_output_validates():
    company, facts, fv = _company_and_package()
    pkg = build_analysis_package(company, facts, fv)
    raw = DemoProvider().generate("sys", pkg)
    out = validate_output(raw)
    assert all(k in out for k in REQUIRED_KEYS)
    assert isinstance(out["risks"], list)


def test_validate_rejects_missing_keys_and_bad_json():
    with pytest.raises(ValidationError):
        validate_output(json.dumps({"executive_summary": "x"}))
    with pytest.raises(ValidationError):
        validate_output("{not json")


def test_ai_client_with_demo_provider_returns_pending_analysis():
    company, facts, fv = _company_and_package()
    pkg = build_analysis_package(company, facts, fv)
    client = AIClient(provider=DemoProvider())
    analysis = client.generate_analysis("NFLX", pkg)
    assert analysis.provider == "demo"
    assert analysis.analyst_approved is False
    assert all(k in analysis.output for k in REQUIRED_KEYS)
