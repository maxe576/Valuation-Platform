"""Repository interface + an in-memory backend.

The rest of the app depends only on the :class:`Repository` protocol, so the
storage engine can move from in-memory (demo/tests) to SQLite to Supabase
(Phase 8) without touching callers. Historical valuation runs are append-only.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

from models.ai_analysis import AIAnalysis
from models.company import Company
from models.financial_fact import FinancialFact
from models.filing import Filing
from models.forecast import AssumptionSet
from models.valuation import ValuationRun


class Repository(ABC):
    """Persistence boundary. Keyed by uppercase ticker where practical."""

    # --- companies ---
    @abstractmethod
    def save_company(self, company: Company) -> Company: ...

    @abstractmethod
    def get_company(self, ticker: str) -> Optional[Company]: ...

    @abstractmethod
    def list_companies(self) -> list[Company]: ...

    # --- filings ---
    @abstractmethod
    def save_filings(self, ticker: str, filings: list[Filing]) -> None: ...

    @abstractmethod
    def get_filings(self, ticker: str) -> list[Filing]: ...

    # --- financial facts ---
    @abstractmethod
    def save_facts(self, ticker: str, facts: list[FinancialFact]) -> None: ...

    @abstractmethod
    def get_facts(self, ticker: str) -> list[FinancialFact]: ...

    # --- assumptions ---
    @abstractmethod
    def save_assumption_set(self, aset: AssumptionSet) -> AssumptionSet: ...

    @abstractmethod
    def list_assumption_sets(self, ticker: str) -> list[AssumptionSet]: ...

    # --- valuation runs (append-only) ---
    @abstractmethod
    def save_valuation_run(self, run: ValuationRun) -> ValuationRun: ...

    @abstractmethod
    def list_valuation_runs(self, ticker: str) -> list[ValuationRun]: ...

    # --- ai analyses ---
    @abstractmethod
    def save_ai_analysis(self, analysis: AIAnalysis) -> AIAnalysis: ...

    @abstractmethod
    def list_ai_analyses(self, ticker: str) -> list[AIAnalysis]: ...


class InMemoryRepository(Repository):
    """Dict-backed repository for demo mode and tests. Not persistent."""

    def __init__(self) -> None:
        self._companies: dict[str, Company] = {}
        self._filings: dict[str, list[Filing]] = {}
        self._facts: dict[str, list[FinancialFact]] = {}
        self._assumptions: dict[str, list[AssumptionSet]] = {}
        self._runs: dict[str, list[ValuationRun]] = {}
        self._ai: dict[str, list[AIAnalysis]] = {}
        self._seq = 0

    def _next_id(self) -> int:
        self._seq += 1
        return self._seq

    @staticmethod
    def _k(ticker: str) -> str:
        return ticker.upper().strip()

    # --- companies ---
    def save_company(self, company: Company) -> Company:
        if company.id is None:
            company.id = self._next_id()
        self._companies[self._k(company.ticker)] = company
        return company

    def get_company(self, ticker: str) -> Optional[Company]:
        return self._companies.get(self._k(ticker))

    def list_companies(self) -> list[Company]:
        return list(self._companies.values())

    # --- filings ---
    def save_filings(self, ticker: str, filings: list[Filing]) -> None:
        self._filings[self._k(ticker)] = list(filings)

    def get_filings(self, ticker: str) -> list[Filing]:
        return list(self._filings.get(self._k(ticker), []))

    # --- facts ---
    def save_facts(self, ticker: str, facts: list[FinancialFact]) -> None:
        self._facts[self._k(ticker)] = list(facts)

    def get_facts(self, ticker: str) -> list[FinancialFact]:
        return list(self._facts.get(self._k(ticker), []))

    # --- assumptions ---
    def save_assumption_set(self, aset: AssumptionSet) -> AssumptionSet:
        if aset.id is None:
            aset.id = self._next_id()
        self._assumptions.setdefault(self._k(aset.company_ticker), []).append(aset)
        return aset

    def list_assumption_sets(self, ticker: str) -> list[AssumptionSet]:
        return list(self._assumptions.get(self._k(ticker), []))

    # --- valuation runs (append-only) ---
    def save_valuation_run(self, run: ValuationRun) -> ValuationRun:
        if run.id is None:
            run.id = self._next_id()
        # Append only — never replace an existing run (§25, §33).
        self._runs.setdefault(self._k(run.company_ticker), []).append(run)
        return run

    def list_valuation_runs(self, ticker: str) -> list[ValuationRun]:
        return list(self._runs.get(self._k(ticker), []))

    # --- ai analyses ---
    def save_ai_analysis(self, analysis: AIAnalysis) -> AIAnalysis:
        if analysis.id is None:
            analysis.id = self._next_id()
        self._ai.setdefault(self._k(analysis.company_ticker), []).append(analysis)
        return analysis

    def list_ai_analyses(self, ticker: str) -> list[AIAnalysis]:
        return list(self._ai.get(self._k(ticker), []))
