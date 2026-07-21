"""AI analysis layer (§24).

The AI interprets a structured package of verified facts and returns structured
JSON — it never performs the official calculations and never invents data. A
provider interface keeps Ollama (local, free, default), Gemini, and future
providers interchangeable. In demo mode (or when no provider is reachable) a
deterministic offline provider grounds a memo strictly in the supplied numbers,
so the workflow is exercisable with zero setup.

Every output is validated against the required §24 schema before it is returned,
and each analysis records provider/model/prompt-version/sources for the audit
trail and the analyst approve/reject step.
"""
from __future__ import annotations

import datetime as _dt
import json
from abc import ABC, abstractmethod
from typing import Any, Optional

from config.logging import get_logger
from config.settings import SETTINGS, AIProvider
from models.ai_analysis import AIAnalysis

log = get_logger("ai_client")

PROMPT_VERSION = "memo-v1"

# Required fields in the structured AI output (§24).
REQUIRED_KEYS = [
    "executive_summary",
    "what_changed",
    "revenue_analysis",
    "growth_quality",
    "margin_analysis",
    "cash_flow_quality",
    "guidance_interpretation",
    "competitive_implications",
    "peer_comparison",
    "multiple_premium_explanation",
    "valuation_implications",
    "risks",
    "catalysts",
    "assumption_challenges",
    "questions_for_analyst",
]

_SYSTEM_PROMPT = (
    "You are an equity research assistant. Use ONLY the supplied JSON data. "
    "Never invent numbers, consensus estimates, or facts not present. Separate "
    "fact from interpretation, flag contradictions, explain why methods disagree, "
    "and challenge unrealistic assumptions. Respond with a single JSON object "
    f"containing exactly these keys: {', '.join(REQUIRED_KEYS)}. "
    "'risks', 'catalysts', 'assumption_challenges', and 'questions_for_analyst' "
    "must be arrays of strings; the rest are strings."
)


class ValidationError(ValueError):
    pass


def validate_output(raw: Any) -> dict[str, Any]:
    """Parse/validate AI output against the required schema (§24)."""
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ValidationError(f"AI output was not valid JSON: {exc}") from exc
    if not isinstance(raw, dict):
        raise ValidationError("AI output must be a JSON object.")
    missing = [k for k in REQUIRED_KEYS if k not in raw]
    if missing:
        raise ValidationError(f"AI output missing required keys: {missing}")
    for list_key in ("risks", "catalysts", "assumption_challenges", "questions_for_analyst"):
        if not isinstance(raw[list_key], list):
            raise ValidationError(f"'{list_key}' must be a list.")
    return raw


# --- providers -------------------------------------------------------------

class AIProviderBase(ABC):
    name: str = "base"
    model: str = ""

    @abstractmethod
    def available(self) -> bool: ...

    @abstractmethod
    def generate(self, system: str, user_payload: dict) -> str: ...


class OllamaProvider(AIProviderBase):
    name = "ollama"

    def __init__(self) -> None:
        self.base_url = SETTINGS.ollama_base_url
        self.model = SETTINGS.ollama_model

    def available(self) -> bool:
        try:
            import requests

            requests.get(f"{self.base_url}/api/tags", timeout=2.0)
            return True
        except Exception:
            return False

    def generate(self, system: str, user_payload: dict) -> str:
        import requests

        resp = requests.post(
            f"{self.base_url}/api/generate",
            json={
                "model": self.model,
                "system": system,
                "prompt": json.dumps(user_payload),
                "format": "json",
                "stream": False,
            },
            timeout=SETTINGS.request_timeout_seconds,
        )
        resp.raise_for_status()
        return resp.json().get("response", "")


class GeminiProvider(AIProviderBase):
    name = "gemini"

    def __init__(self) -> None:
        self.model = "gemini-1.5-flash"
        self.api_key = SETTINGS.gemini_api_key

    def available(self) -> bool:
        return bool(self.api_key)

    def generate(self, system: str, user_payload: dict) -> str:
        import requests

        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{self.model}:generateContent?key={self.api_key}"
        )
        body = {
            "contents": [{"parts": [{"text": system + "\n\nDATA:\n"
                                     + json.dumps(user_payload)}]}],
            "generationConfig": {"responseMimeType": "application/json"},
        }
        resp = requests.post(url, json=body, timeout=SETTINGS.request_timeout_seconds)
        resp.raise_for_status()
        data = resp.json()
        return data["candidates"][0]["content"]["parts"][0]["text"]


class DemoProvider(AIProviderBase):
    """Offline, deterministic provider. Grounds every statement in the package's
    own numbers — no external calls, no fabrication. Used in demo mode or as a
    fallback when no real provider is reachable."""

    name = "demo"
    model = "offline-template"

    def available(self) -> bool:
        return True

    def generate(self, system: str, user_payload: dict) -> str:
        p = user_payload
        m, f = p["market"], p["financials"]
        up = m.get("upside")
        up_txt = f"{up*100:.1f}%" if up is not None else "n/a"
        g = f.get("revenue_growth_yoy")
        g_txt = f"{g*100:.1f}%" if g is not None else "n/a"
        method_txt = ", ".join(
            f"{x['method']} ${x['per_share']}" for x in p["methods"]
        )
        out = {
            "executive_summary": (
                f"{p['company']['name']} ({p['company']['ticker']}) trades at "
                f"${m['current_price']} vs a blended fair value of "
                f"${m['blended_fair_value']} ({up_txt} upside). Confidence "
                f"{m['confidence_score']}/100 with method dispersion "
                f"{m['method_dispersion']*100:.0f}%."
            ),
            "what_changed": (
                f"Latest revenue {f.get('latest_revenue')} with {g_txt} year-over-year "
                "growth per the loaded filings."
            ),
            "revenue_analysis": f"Reported revenue history: {f.get('revenue_history')}.",
            "growth_quality": (
                f"Year-over-year growth of {g_txt} is drawn from reported figures; "
                "assess durability against segment and peer trends."
            ),
            "margin_analysis": (
                f"Operating income {f.get('operating_income')} on revenue "
                f"{f.get('latest_revenue')}."
            ),
            "cash_flow_quality": (
                "Cash-flow quality should be judged from the DCF's unlevered FCF "
                "path in the Valuation Lab; no fabricated figures are added here."
            ),
            "guidance_interpretation": "No management guidance supplied in this package.",
            "competitive_implications": (
                f"Sector: {p['company'].get('sector')}. Peer multiples: "
                f"{p.get('comparables')}."
            ),
            "peer_comparison": f"Comparable-method medians: {p.get('comparables')}.",
            "multiple_premium_explanation": (
                "Premium/discount vs peers is quantified in Peer Intelligence; "
                "no multiple adjustments are invented here."
            ),
            "valuation_implications": (
                f"Method values — {method_txt}. Blended ${m['blended_fair_value']} "
                f"gives {up_txt} vs price."
            ),
            "risks": (["Model warnings: " + "; ".join(p["warnings"])]
                      if p.get("warnings") else
                      ["No model warnings flagged; standard sector and execution risks apply."]),
            "catalysts": ["Upcoming earnings and guidance updates (none supplied in package)."],
            "assumption_challenges": [
                f"Market-implied vs analyst: {p.get('reverse_dcf')}."
            ],
            "questions_for_analyst": [
                "Are the peer set and segment splits approved?",
                "Do the forecast growth and margin paths reflect the latest guidance?",
            ],
        }
        return json.dumps(out)


def _select_provider() -> AIProviderBase:
    if SETTINGS.is_demo:
        return DemoProvider()
    provider = (GeminiProvider() if SETTINGS.ai_provider is AIProvider.GEMINI
                else OllamaProvider())
    if provider.available():
        return provider
    log.warning("AI provider '%s' unavailable; falling back to offline demo provider.",
                provider.name)
    return DemoProvider()


class AIClient:
    def __init__(self, provider: Optional[AIProviderBase] = None) -> None:
        self.provider = provider or _select_provider()

    def generate_analysis(
        self,
        ticker: str,
        package: dict,
        analysis_type: str = "quarterly_memo",
    ) -> AIAnalysis:
        raw = self.provider.generate(_SYSTEM_PROMPT, package)
        output = validate_output(raw)
        return AIAnalysis(
            company_ticker=ticker,
            analysis_type=analysis_type,
            provider=self.provider.name,
            model=self.provider.model,
            prompt_version=PROMPT_VERSION,
            input_sources=package.get("data_quality", {}).get("sources", []),
            output=output,
            analyst_approved=False,
            created_at=_dt.datetime.now().isoformat(timespec="seconds"),
        )
