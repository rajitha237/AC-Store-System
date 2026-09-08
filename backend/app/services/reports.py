from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo
from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.cash_book import ManualCashBookEntry
from app.models.inventory import StockMovement, StockMovementType
from app.models.purchasing import SupplierInvoice, SupplierPayment
from app.models.sales import (
    CustomerPayment,
    InvoiceStatus,
    SalesInvoice,
)
from app.schemas.reports import (
    CashFlowSummary,
    FinancialReportDetailResponse,
    FinancialReportLine,
    FinancialReportPeriod,
    FinancialReportsSummaryResponse,
    ProfitAndLossSummary,
    PurchasingSummary,
    ReceivablesSummary,
)


ZERO = Decimal("0.00")
CENT = Decimal("0.01")


def money(
    value: Decimal | int | float | str | None,
) -> Decimal:
    if value is None:
        value = ZERO

    return Decimal(str(value)).quantize(
        CENT,
        rounding=ROUND_HALF_UP,
    )


def _day_start(
    value: date,
    timezone_name: str,
) -> datetime:
    local_zone = ZoneInfo(timezone_name)

    local_start = datetime.combine(
        value,
        time.min,
        tzinfo=local_zone,
    )

    return local_start.astimezone(
        timezone.utc
    )


def _next_day_start(
    value: date,
    timezone_name: str,
) -> datetime:
    return _day_start(
        value + timedelta(days=1),
        timezone_name,
    )


async def _scalar_money(
    session: AsyncSession,
    statement,
) -> Decimal:
    result = await session.execute(statement)
    return money(result.scalar_one_or_none())


async def build_financial_reports_summary(
    session: AsyncSession,
    *,
    company_id: int,
    date_from: date,
    date_to: date,
    timezone_name: str = "Asia/Colombo",
) -> FinancialReportsSummaryResponse:
    start_at = _day_start(
        date_from,
        timezone_name,
    )
    end_before = _next_day_start(
        date_to,
        timezone_name,
    )

    # --------------------------------------------------------
    # REVENUE
    #
    # Revenue is invoice activity, not cash received.
    # Draft/cancelled invoices are excluded.
    # Posted credits already recorded on the invoice reduce
    # revenue through credited_amount.
    # --------------------------------------------------------

    gross_sales = await _scalar_money(
        session,
        select(
            func.coalesce(
                func.sum(
                    SalesInvoice.grand_total
                ),
                ZERO,
            )
        ).where(
            SalesInvoice.company_id
            == company_id,
            SalesInvoice.invoice_date
            >= start_at,
            SalesInvoice.invoice_date
            < end_before,
            SalesInvoice.invoice_status.notin_(
                [
                    InvoiceStatus.DRAFT.value,
                    InvoiceStatus.CANCELLED.value,
                ]
            ),
        ),
    )

    sales_credits = await _scalar_money(
        session,
        select(
            func.coalesce(
                func.sum(
                    SalesInvoice.credited_amount
                ),
                ZERO,
            )
        ).where(
            SalesInvoice.company_id
            == company_id,
            SalesInvoice.invoice_date
            >= start_at,
            SalesInvoice.invoice_date
            < end_before,
            SalesInvoice.invoice_status.notin_(
                [
                    InvoiceStatus.DRAFT.value,
                    InvoiceStatus.CANCELLED.value,
                ]
            ),
        ),
    )

    net_revenue = money(
        gross_sales - sales_credits
    )

    # --------------------------------------------------------
    # COGS
    #
    # Sales/service stock issues store their cost snapshot in
    # StockMovement.unit_cost.
    #
    # Returns reduce COGS.
    # --------------------------------------------------------

    sale_issue_cogs = await _scalar_money(
        session,
        select(
            func.coalesce(
                func.sum(
                    func.abs(
                        StockMovement.quantity
                    )
                    * StockMovement.unit_cost
                ),
                ZERO,
            )
        ).where(
            StockMovement.company_id
            == company_id,
            StockMovement.movement_date
            >= start_at,
            StockMovement.movement_date
            < end_before,
            StockMovement.movement_type.in_(
                [
                    StockMovementType.SALE_ISSUE.value,
                    StockMovementType.SERVICE_USAGE.value,
                    StockMovementType.REPLACEMENT_ISSUE.value,
                    "service_issue",
                ]
            ),
        ),
    )

    sale_return_cogs = await _scalar_money(
        session,
        select(
            func.coalesce(
                func.sum(
                    func.abs(
                        StockMovement.quantity
                    )
                    * StockMovement.unit_cost
                ),
                ZERO,
            )
        ).where(
            StockMovement.company_id
            == company_id,
            StockMovement.movement_date
            >= start_at,
            StockMovement.movement_date
            < end_before,
            StockMovement.movement_type
            == StockMovementType.SALE_RETURN.value,
        ),
    )

    sale_return_reversal_cogs = await _scalar_money(
        session,
        select(
            func.coalesce(
                func.sum(
                    func.abs(
                        StockMovement.quantity
                    )
                    * StockMovement.unit_cost
                ),
                ZERO,
            )
        ).where(
            StockMovement.company_id
            == company_id,
            StockMovement.movement_date
            >= start_at,
            StockMovement.movement_date
            < end_before,
            StockMovement.movement_type
            == (
                StockMovementType
                .SALE_RETURN_REVERSAL
                .value
            ),
        ),
    )

    cost_of_goods_sold = money(
        sale_issue_cogs
        - sale_return_cogs
        + sale_return_reversal_cogs
    )

    if cost_of_goods_sold < ZERO:
        cost_of_goods_sold = ZERO

    gross_profit = money(
        net_revenue - cost_of_goods_sold
    )

    # --------------------------------------------------------
    # OPERATING EXPENSES
    #
    # Current system has manual Cash Book cash-out records as
    # its manual business-expense source. Supplier payments are
    # NOT treated as P&L expenses here because stock purchasing
    # and cash settlement are different accounting events.
    # --------------------------------------------------------

    operating_expenses = await _scalar_money(
        session,
        select(
            func.coalesce(
                func.sum(
                    ManualCashBookEntry.amount
                ),
                ZERO,
            )
        ).where(
            ManualCashBookEntry.company_id
            == company_id,
            ManualCashBookEntry.entry_date
            >= start_at,
            ManualCashBookEntry.entry_date
            < end_before,
            ManualCashBookEntry.entry_type
            == "cash_out",
            ManualCashBookEntry.reversed_at
            .is_(None),
        ),
    )

    net_profit = money(
        gross_profit - operating_expenses
    )

    # --------------------------------------------------------
    # CASH FLOW
    # --------------------------------------------------------

    customer_collections = await _scalar_money(
        session,
        select(
            func.coalesce(
                func.sum(
                    CustomerPayment.amount
                ),
                ZERO,
            )
        ).where(
            CustomerPayment.company_id
            == company_id,
            CustomerPayment.payment_date
            >= start_at,
            CustomerPayment.payment_date
            < end_before,
            CustomerPayment.is_reversed
            .is_(False),
        ),
    )

    manual_cash_in = await _scalar_money(
        session,
        select(
            func.coalesce(
                func.sum(
                    ManualCashBookEntry.amount
                ),
                ZERO,
            )
        ).where(
            ManualCashBookEntry.company_id
            == company_id,
            ManualCashBookEntry.entry_date
            >= start_at,
            ManualCashBookEntry.entry_date
            < end_before,
            ManualCashBookEntry.entry_type
            == "cash_in",
            ManualCashBookEntry.reversed_at
            .is_(None),
        ),
    )

    supplier_payments = await _scalar_money(
        session,
        select(
            func.coalesce(
                func.sum(
                    SupplierPayment.amount
                ),
                ZERO,
            )
        ).where(
            SupplierPayment.company_id
            == company_id,
            SupplierPayment.payment_date
            >= start_at,
            SupplierPayment.payment_date
            < end_before,
            SupplierPayment.is_reversed
            .is_(False),
        ),
    )

    total_cash_in = money(
        customer_collections
        + manual_cash_in
    )

    total_cash_out = money(
        supplier_payments
        + operating_expenses
    )

    net_cash_flow = money(
        total_cash_in
        - total_cash_out
    )

    # --------------------------------------------------------
    # PURCHASE ACTIVITY
    #
    # Posted supplier invoices represent purchase liability /
    # acquisition activity. Reversed invoices are excluded.
    # --------------------------------------------------------

    supplier_invoices = await _scalar_money(
        session,
        select(
            func.coalesce(
                func.sum(
                    SupplierInvoice.grand_total
                ),
                ZERO,
            )
        ).where(
            SupplierInvoice.company_id
            == company_id,
            SupplierInvoice.invoice_date
            >= start_at,
            SupplierInvoice.invoice_date
            < end_before,
            SupplierInvoice.posted_at
            .is_not(None),
            SupplierInvoice.is_reversed
            .is_(False),
        ),
    )

    # --------------------------------------------------------
    # CURRENT OUTSTANDING POSITION
    #
    # These are current balances for documents dated on/before
    # the selected report end date. This intentionally does not
    # pretend to reconstruct a historical balance after later
    # payments.
    # --------------------------------------------------------

    customer_receivables = await _scalar_money(
        session,
        select(
            func.coalesce(
                func.sum(
                    SalesInvoice.balance_amount
                ),
                ZERO,
            )
        ).where(
            SalesInvoice.company_id
            == company_id,
            SalesInvoice.invoice_date
            < end_before,
            SalesInvoice.invoice_status.notin_(
                [
                    InvoiceStatus.DRAFT.value,
                    InvoiceStatus.CANCELLED.value,
                ]
            ),
            SalesInvoice.balance_amount
            > ZERO,
        ),
    )

    supplier_payables = await _scalar_money(
        session,
        select(
            func.coalesce(
                func.sum(
                    SupplierInvoice.balance_amount
                ),
                ZERO,
            )
        ).where(
            SupplierInvoice.company_id
            == company_id,
            SupplierInvoice.invoice_date
            < end_before,
            SupplierInvoice.posted_at
            .is_not(None),
            SupplierInvoice.is_reversed
            .is_(False),
            SupplierInvoice.balance_amount
            > ZERO,
        ),
    )

    period = FinancialReportPeriod(
        date_from=date_from,
        date_to=date_to,
    )

    return FinancialReportsSummaryResponse(
        period=period,
        profit_and_loss=ProfitAndLossSummary(
            gross_sales=gross_sales,
            sales_credits=sales_credits,
            net_revenue=net_revenue,
            cost_of_goods_sold=(
                cost_of_goods_sold
            ),
            gross_profit=gross_profit,
            operating_expenses=(
                operating_expenses
            ),
            net_profit=net_profit,
        ),
        cash_flow=CashFlowSummary(
            customer_collections=(
                customer_collections
            ),
            manual_cash_in=manual_cash_in,
            total_cash_in=total_cash_in,
            supplier_payments=(
                supplier_payments
            ),
            manual_cash_out=(
                operating_expenses
            ),
            total_cash_out=total_cash_out,
            net_cash_flow=net_cash_flow,
        ),
        purchasing=PurchasingSummary(
            supplier_invoices=(
                supplier_invoices
            ),
            supplier_payments=(
                supplier_payments
            ),
        ),
        receivables=ReceivablesSummary(
            customer_receivables=(
                customer_receivables
            ),
            supplier_payables=(
                supplier_payables
            ),
        ),
    )


async def build_financial_report_detail(
    session: AsyncSession,
    *,
    company_id: int,
    date_from: date,
    date_to: date,
    timezone_name: str = "Asia/Colombo",
) -> FinancialReportDetailResponse:
    summary = (
        await build_financial_reports_summary(
            session,
            company_id=company_id,
            date_from=date_from,
            date_to=date_to,
            timezone_name=timezone_name,
        )
    )

    pnl = summary.profit_and_loss
    cash = summary.cash_flow
    purchasing = summary.purchasing
    receivables = summary.receivables

    lines = [
        FinancialReportLine(
            section="Profit & Loss",
            label="Gross sales",
            amount=pnl.gross_sales,
        ),
        FinancialReportLine(
            section="Profit & Loss",
            label="Sales credits / reductions",
            amount=pnl.sales_credits,
        ),
        FinancialReportLine(
            section="Profit & Loss",
            label="Net revenue",
            amount=pnl.net_revenue,
        ),
        FinancialReportLine(
            section="Profit & Loss",
            label="Cost of goods sold",
            amount=pnl.cost_of_goods_sold,
        ),
        FinancialReportLine(
            section="Profit & Loss",
            label="Gross profit",
            amount=pnl.gross_profit,
        ),
        FinancialReportLine(
            section="Profit & Loss",
            label="Operating expenses",
            amount=pnl.operating_expenses,
        ),
        FinancialReportLine(
            section="Profit & Loss",
            label="Net profit",
            amount=pnl.net_profit,
        ),
        FinancialReportLine(
            section="Cash Flow",
            label="Customer collections",
            amount=cash.customer_collections,
        ),
        FinancialReportLine(
            section="Cash Flow",
            label="Manual cash in",
            amount=cash.manual_cash_in,
        ),
        FinancialReportLine(
            section="Cash Flow",
            label="Total cash in",
            amount=cash.total_cash_in,
        ),
        FinancialReportLine(
            section="Cash Flow",
            label="Supplier payments",
            amount=cash.supplier_payments,
        ),
        FinancialReportLine(
            section="Cash Flow",
            label="Manual cash out",
            amount=cash.manual_cash_out,
        ),
        FinancialReportLine(
            section="Cash Flow",
            label="Total cash out",
            amount=cash.total_cash_out,
        ),
        FinancialReportLine(
            section="Cash Flow",
            label="Net cash flow",
            amount=cash.net_cash_flow,
        ),
        FinancialReportLine(
            section="Purchasing",
            label="Supplier invoices",
            amount=purchasing.supplier_invoices,
        ),
        FinancialReportLine(
            section="Purchasing",
            label="Supplier payments",
            amount=purchasing.supplier_payments,
        ),
        FinancialReportLine(
            section="Outstanding",
            label="Customer receivables",
            amount=(
                receivables.customer_receivables
            ),
        ),
        FinancialReportLine(
            section="Outstanding",
            label="Supplier payables",
            amount=(
                receivables.supplier_payables
            ),
        ),
    ]

    return FinancialReportDetailResponse(
        period=summary.period,
        lines=lines,
    )
