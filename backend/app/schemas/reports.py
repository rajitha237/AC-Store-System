from __future__ import annotations

from datetime import date
from decimal import Decimal

from pydantic import BaseModel


class FinancialReportPeriod(BaseModel):
    date_from: date
    date_to: date


class ProfitAndLossSummary(BaseModel):
    gross_sales: Decimal
    sales_credits: Decimal
    net_revenue: Decimal
    cost_of_goods_sold: Decimal
    gross_profit: Decimal
    operating_expenses: Decimal
    net_profit: Decimal


class CashFlowSummary(BaseModel):
    customer_collections: Decimal
    manual_cash_in: Decimal
    total_cash_in: Decimal
    supplier_payments: Decimal
    manual_cash_out: Decimal
    total_cash_out: Decimal
    net_cash_flow: Decimal


class PurchasingSummary(BaseModel):
    supplier_invoices: Decimal
    supplier_payments: Decimal


class ReceivablesSummary(BaseModel):
    customer_receivables: Decimal
    supplier_payables: Decimal


class FinancialReportsSummaryResponse(BaseModel):
    period: FinancialReportPeriod
    profit_and_loss: ProfitAndLossSummary
    cash_flow: CashFlowSummary
    purchasing: PurchasingSummary
    receivables: ReceivablesSummary


class FinancialReportLine(BaseModel):
    section: str
    label: str
    amount: Decimal


class FinancialReportDetailResponse(BaseModel):
    period: FinancialReportPeriod
    lines: list[FinancialReportLine]
