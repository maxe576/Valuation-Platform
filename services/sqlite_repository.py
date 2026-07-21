"""SQLite-backed Repository — durable local persistence (§8, §33).

Gives real save/reopen on Windows with no cloud or keys (the free-first default
when live but not Supabase-configured). Entities are stored as JSON via
services.serialization so a valuation reopens byte-for-byte. Valuation runs and
assumption sets are append-only; companies/facts/filings are current snapshots.
"""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Optional

from config.settings import SETTINGS
from models.ai_analysis import AIAnalysis
from models.company import Company
from models.filing import Filing
from models.financial_fact import FinancialFact
from models.forecast import AssumptionSet
from models.valuation import ValuationRun
from services.repository import Repository
from services import serialization as ser


class SQLiteRepository(Repository):
    def __init__(self, db_path: Optional[str] = None) -> None:
        path = Path(db_path or SETTINGS.local_db_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(path), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._create_tables()

    def _create_tables(self) -> None:
        cur = self.conn.cursor()
        cur.executescript(
            """
            CREATE TABLE IF NOT EXISTS companies (ticker TEXT PRIMARY KEY, data TEXT);
            CREATE TABLE IF NOT EXISTS facts    (ticker TEXT PRIMARY KEY, data TEXT);
            CREATE TABLE IF NOT EXISTS filings  (ticker TEXT PRIMARY KEY, data TEXT);
            CREATE TABLE IF NOT EXISTS assumption_sets (
                id INTEGER PRIMARY KEY AUTOINCREMENT, ticker TEXT, data TEXT);
            CREATE TABLE IF NOT EXISTS valuation_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT, ticker TEXT, data TEXT);
            CREATE TABLE IF NOT EXISTS ai_analyses (
                id INTEGER PRIMARY KEY AUTOINCREMENT, ticker TEXT, data TEXT);
            """
        )
        self.conn.commit()

    @staticmethod
    def _k(ticker: str) -> str:
        return ticker.upper().strip()

    def _dumps(self, obj) -> str:
        return json.dumps(ser.to_jsonable(obj))

    # --- companies ---
    def save_company(self, company: Company) -> Company:
        self.conn.execute(
            "INSERT INTO companies(ticker, data) VALUES(?,?) "
            "ON CONFLICT(ticker) DO UPDATE SET data=excluded.data",
            (self._k(company.ticker), self._dumps(company)),
        )
        self.conn.commit()
        return company

    def get_company(self, ticker: str) -> Optional[Company]:
        row = self.conn.execute(
            "SELECT data FROM companies WHERE ticker=?", (self._k(ticker),)
        ).fetchone()
        return ser.company_from_dict(json.loads(row["data"])) if row else None

    def list_companies(self) -> list[Company]:
        rows = self.conn.execute("SELECT data FROM companies").fetchall()
        return [ser.company_from_dict(json.loads(r["data"])) for r in rows]

    # --- filings ---
    def save_filings(self, ticker: str, filings: list[Filing]) -> None:
        self.conn.execute(
            "INSERT INTO filings(ticker, data) VALUES(?,?) "
            "ON CONFLICT(ticker) DO UPDATE SET data=excluded.data",
            (self._k(ticker), self._dumps(filings)),
        )
        self.conn.commit()

    def get_filings(self, ticker: str) -> list[Filing]:
        row = self.conn.execute(
            "SELECT data FROM filings WHERE ticker=?", (self._k(ticker),)
        ).fetchone()
        return [ser.filing_from_dict(d) for d in json.loads(row["data"])] if row else []

    # --- facts ---
    def save_facts(self, ticker: str, facts: list[FinancialFact]) -> None:
        self.conn.execute(
            "INSERT INTO facts(ticker, data) VALUES(?,?) "
            "ON CONFLICT(ticker) DO UPDATE SET data=excluded.data",
            (self._k(ticker), self._dumps(facts)),
        )
        self.conn.commit()

    def get_facts(self, ticker: str) -> list[FinancialFact]:
        row = self.conn.execute(
            "SELECT data FROM facts WHERE ticker=?", (self._k(ticker),)
        ).fetchone()
        return [ser.fact_from_dict(d) for d in json.loads(row["data"])] if row else []

    # --- assumptions (append-only, versioned) ---
    def save_assumption_set(self, aset: AssumptionSet) -> AssumptionSet:
        cur = self.conn.execute(
            "INSERT INTO assumption_sets(ticker, data) VALUES(?,?)",
            (self._k(aset.company_ticker), self._dumps(aset)),
        )
        aset.id = cur.lastrowid
        # Persist the assigned id inside the stored blob too.
        self.conn.execute("UPDATE assumption_sets SET data=? WHERE id=?",
                          (self._dumps(aset), aset.id))
        self.conn.commit()
        return aset

    def list_assumption_sets(self, ticker: str) -> list[AssumptionSet]:
        rows = self.conn.execute(
            "SELECT data FROM assumption_sets WHERE ticker=? ORDER BY id",
            (self._k(ticker),),
        ).fetchall()
        return [ser.assumption_set_from_dict(json.loads(r["data"])) for r in rows]

    # --- valuation runs (append-only, never overwritten) ---
    def save_valuation_run(self, run: ValuationRun) -> ValuationRun:
        cur = self.conn.execute(
            "INSERT INTO valuation_runs(ticker, data) VALUES(?,?)",
            (self._k(run.company_ticker), self._dumps(run)),
        )
        run.id = cur.lastrowid
        self.conn.execute("UPDATE valuation_runs SET data=? WHERE id=?",
                          (self._dumps(run), run.id))
        self.conn.commit()
        return run

    def list_valuation_runs(self, ticker: str) -> list[ValuationRun]:
        rows = self.conn.execute(
            "SELECT data FROM valuation_runs WHERE ticker=? ORDER BY id",
            (self._k(ticker),),
        ).fetchall()
        return [ser.valuation_run_from_dict(json.loads(r["data"])) for r in rows]

    # --- ai analyses ---
    def save_ai_analysis(self, analysis: AIAnalysis) -> AIAnalysis:
        cur = self.conn.execute(
            "INSERT INTO ai_analyses(ticker, data) VALUES(?,?)",
            (self._k(analysis.company_ticker), self._dumps(analysis)),
        )
        analysis.id = cur.lastrowid
        self.conn.execute("UPDATE ai_analyses SET data=? WHERE id=?",
                          (self._dumps(analysis), analysis.id))
        self.conn.commit()
        return analysis

    def list_ai_analyses(self, ticker: str) -> list[AIAnalysis]:
        rows = self.conn.execute(
            "SELECT data FROM ai_analyses WHERE ticker=? ORDER BY id",
            (self._k(ticker),),
        ).fetchall()
        return [ser.ai_analysis_from_dict(json.loads(r["data"])) for r in rows]
