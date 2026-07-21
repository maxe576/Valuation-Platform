"""Standardized metric names -> candidate XBRL (US-GAAP) tags.

Companies do not all use the same XBRL tag for the same economic concept, so
each standardized metric maps to an *ordered* list of candidate tags. The SEC
normalizer (Phase 3) tries them in priority order and records which tag actually
supplied each value, along with the reported label (see §5, §10).

Statement classification lets the UI group facts into IS / BS / CFS views.
"""
from __future__ import annotations

from enum import Enum


class Statement(str, Enum):
    INCOME = "income_statement"
    BALANCE = "balance_sheet"
    CASH_FLOW = "cash_flow"
    SHARES = "shares"


class MetricMap:
    """A standardized metric and its candidate XBRL tags."""

    __slots__ = ("key", "label", "statement", "tags")

    def __init__(self, key: str, label: str, statement: Statement, tags: list[str]):
        self.key = key
        self.label = label
        self.statement = statement
        self.tags = tags


# Ordered so the most standard / most common tag is tried first.
METRICS: list[MetricMap] = [
    # ---------------- Income statement ----------------
    MetricMap("revenue", "Revenue", Statement.INCOME, [
        "RevenueFromContractWithCustomerExcludingAssessedTax",
        "RevenueFromContractWithCustomerIncludingAssessedTax",
        "Revenues",
        "SalesRevenueNet",
        "SalesRevenueGoodsNet",
    ]),
    MetricMap("cost_of_revenue", "Cost of Revenue", Statement.INCOME, [
        "CostOfRevenue",
        "CostOfGoodsAndServicesSold",
        "CostOfGoodsSold",
    ]),
    MetricMap("gross_profit", "Gross Profit", Statement.INCOME, [
        "GrossProfit",
    ]),
    MetricMap("research_development", "Research & Development", Statement.INCOME, [
        "ResearchAndDevelopmentExpense",
    ]),
    MetricMap("sales_marketing", "Sales & Marketing", Statement.INCOME, [
        "SellingAndMarketingExpense",
        "MarketingExpense",
    ]),
    MetricMap("general_administrative", "General & Administrative", Statement.INCOME, [
        "GeneralAndAdministrativeExpense",
    ]),
    MetricMap("sga", "Selling, General & Administrative", Statement.INCOME, [
        "SellingGeneralAndAdministrativeExpense",
    ]),
    MetricMap("operating_expenses", "Operating Expenses", Statement.INCOME, [
        "OperatingExpenses",
        "CostsAndExpenses",
    ]),
    MetricMap("operating_income", "Operating Income", Statement.INCOME, [
        "OperatingIncomeLoss",
    ]),
    MetricMap("interest_expense", "Interest Expense", Statement.INCOME, [
        "InterestExpense",
        "InterestExpenseNonoperating",
        "InterestAndDebtExpense",
    ]),
    MetricMap("pretax_income", "Pretax Income", Statement.INCOME, [
        "IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest",
        "IncomeLossFromContinuingOperationsBeforeIncomeTaxesMinorityInterestAndIncomeLossFromEquityMethodInvestments",
    ]),
    MetricMap("income_tax", "Income Tax Expense", Statement.INCOME, [
        "IncomeTaxExpenseBenefit",
    ]),
    MetricMap("net_income", "Net Income", Statement.INCOME, [
        "NetIncomeLoss",
        "ProfitLoss",
        "NetIncomeLossAvailableToCommonStockholdersBasic",
    ]),
    MetricMap("eps_basic", "Basic EPS", Statement.INCOME, [
        "EarningsPerShareBasic",
    ]),
    MetricMap("eps_diluted", "Diluted EPS", Statement.INCOME, [
        "EarningsPerShareDiluted",
    ]),

    # ---------------- Balance sheet ----------------
    MetricMap("cash", "Cash & Equivalents", Statement.BALANCE, [
        "CashAndCashEquivalentsAtCarryingValue",
        "CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents",
    ]),
    MetricMap("marketable_securities", "Marketable Securities", Statement.BALANCE, [
        "MarketableSecuritiesCurrent",
        "ShortTermInvestments",
        "AvailableForSaleSecuritiesCurrent",
    ]),
    MetricMap("accounts_receivable", "Accounts Receivable", Statement.BALANCE, [
        "AccountsReceivableNetCurrent",
        "ReceivablesNetCurrent",
    ]),
    MetricMap("inventory", "Inventory", Statement.BALANCE, [
        "InventoryNet",
    ]),
    MetricMap("current_assets", "Total Current Assets", Statement.BALANCE, [
        "AssetsCurrent",
    ]),
    MetricMap("ppe", "Property, Plant & Equipment", Statement.BALANCE, [
        "PropertyPlantAndEquipmentNet",
    ]),
    MetricMap("goodwill", "Goodwill", Statement.BALANCE, [
        "Goodwill",
    ]),
    MetricMap("intangibles", "Intangible Assets", Statement.BALANCE, [
        "IntangibleAssetsNetExcludingGoodwill",
        "FiniteLivedIntangibleAssetsNet",
    ]),
    MetricMap("total_assets", "Total Assets", Statement.BALANCE, [
        "Assets",
    ]),
    MetricMap("accounts_payable", "Accounts Payable", Statement.BALANCE, [
        "AccountsPayableCurrent",
        "AccountsPayableAndAccruedLiabilitiesCurrent",
    ]),
    MetricMap("deferred_revenue", "Deferred Revenue", Statement.BALANCE, [
        "ContractWithCustomerLiabilityCurrent",
        "DeferredRevenueCurrent",
        "ContractWithCustomerLiability",
    ]),
    MetricMap("current_liabilities", "Total Current Liabilities", Statement.BALANCE, [
        "LiabilitiesCurrent",
    ]),
    MetricMap("short_term_debt", "Short-Term Debt", Statement.BALANCE, [
        "LongTermDebtCurrent",
        "DebtCurrent",
        "ShortTermBorrowings",
    ]),
    MetricMap("long_term_debt", "Long-Term Debt", Statement.BALANCE, [
        "LongTermDebtNoncurrent",
        "LongTermDebt",
    ]),
    MetricMap("total_liabilities", "Total Liabilities", Statement.BALANCE, [
        "Liabilities",
    ]),
    MetricMap("shareholders_equity", "Shareholders' Equity", Statement.BALANCE, [
        "StockholdersEquity",
        "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest",
    ]),

    # ---------------- Cash flow ----------------
    MetricMap("operating_cash_flow", "Operating Cash Flow", Statement.CASH_FLOW, [
        "NetCashProvidedByUsedInOperatingActivities",
        "NetCashProvidedByUsedInOperatingActivitiesContinuingOperations",
    ]),
    MetricMap("capex", "Capital Expenditures", Statement.CASH_FLOW, [
        "PaymentsToAcquirePropertyPlantAndEquipment",
        "PaymentsToAcquireProductiveAssets",
    ]),
    MetricMap("acquisitions", "Acquisitions", Statement.CASH_FLOW, [
        "PaymentsToAcquireBusinessesNetOfCashAcquired",
    ]),
    MetricMap("share_repurchases", "Share Repurchases", Statement.CASH_FLOW, [
        "PaymentsForRepurchaseOfCommonStock",
    ]),
    MetricMap("dividends", "Dividends Paid", Statement.CASH_FLOW, [
        "PaymentsOfDividendsCommonStock",
        "PaymentsOfDividends",
    ]),
    MetricMap("stock_based_comp", "Stock-Based Compensation", Statement.CASH_FLOW, [
        "ShareBasedCompensation",
    ]),
    MetricMap("depreciation_amortization", "Depreciation & Amortization", Statement.CASH_FLOW, [
        "DepreciationDepletionAndAmortization",
        "DepreciationAmortizationAndAccretionNet",
        "DepreciationAndAmortization",
    ]),

    # ---------------- Shares ----------------
    MetricMap("shares_basic", "Basic Shares Outstanding", Statement.SHARES, [
        "WeightedAverageNumberOfSharesOutstandingBasic",
    ]),
    MetricMap("shares_diluted", "Diluted Shares Outstanding", Statement.SHARES, [
        "WeightedAverageNumberOfDilutedSharesOutstanding",
    ]),
]

# Lookups by key and reverse (tag -> standardized key).
METRIC_BY_KEY: dict[str, MetricMap] = {m.key: m for m in METRICS}
TAG_TO_METRIC: dict[str, str] = {
    tag: m.key for m in METRICS for tag in m.tags
}
