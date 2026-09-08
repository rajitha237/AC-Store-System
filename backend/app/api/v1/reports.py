from __future__ import annotations

import csv
from datetime import date
from io import StringIO
from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    Response,
    status,
)

from app.api.deps import (
    DatabaseSession,
    require_permission,
)
from app.models import User
from app.schemas.reports import (
    FinancialReportDetailResponse,
    FinancialReportsSummaryResponse,
)
from app.services.cash_book import (
    get_active_cash_book_company,
)
from app.services.reports import (
    build_financial_report_detail,
    build_financial_reports_summary,
)

from app.services.documents.financial_report import (
    FinancialReportPDFData,
    build_financial_report_pdf,
)

from app.services.documents.financial_report_excel import (
    build_financial_report_excel,
)


router = APIRouter(
    prefix="/reports",
    tags=["Financial Reports"],
)


CanViewReports = Annotated[
    User,
    Depends(
        require_permission(
            "reports.view"
        )
    ),
]


def _validate_period(
    date_from: date,
    date_to: date,
) -> None:
    if date_from > date_to:
        raise HTTPException(
            status_code=(
                status.HTTP_422_UNPROCESSABLE_ENTITY
            ),
            detail=(
                "date_from cannot be after date_to"
            ),
        )

    if (date_to - date_from).days > 3660:
        raise HTTPException(
            status_code=(
                status.HTTP_422_UNPROCESSABLE_ENTITY
            ),
            detail=(
                "Report period cannot exceed 10 years"
            ),
        )


async def _active_company(
    session: DatabaseSession,
):
    try:
        company = (
            await get_active_cash_book_company(
                session
            )
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=(
                status.HTTP_409_CONFLICT
            ),
            detail=str(exc),
        ) from exc

    return company


@router.get(
    "/financial-summary",
    response_model=(
        FinancialReportsSummaryResponse
    ),
)
async def financial_summary(
    session: DatabaseSession,
    _: CanViewReports,
    date_from: date = Query(...),
    date_to: date = Query(...),
) -> FinancialReportsSummaryResponse:
    _validate_period(
        date_from,
        date_to,
    )

    company = await _active_company(
        session
    )

    return await build_financial_reports_summary(
        session,
        company_id=company.id,
        date_from=date_from,
        date_to=date_to,
        timezone_name=company.timezone,
    )


@router.get(
    "/financial-detail",
    response_model=(
        FinancialReportDetailResponse
    ),
)
async def financial_detail(
    session: DatabaseSession,
    _: CanViewReports,
    date_from: date = Query(...),
    date_to: date = Query(...),
) -> FinancialReportDetailResponse:
    _validate_period(
        date_from,
        date_to,
    )

    company = await _active_company(
        session
    )

    return await build_financial_report_detail(
        session,
        company_id=company.id,
        date_from=date_from,
        date_to=date_to,
        timezone_name=company.timezone,
    )


@router.get(
    "/financial-summary.csv",
)
async def financial_summary_csv(
    session: DatabaseSession,
    _: CanViewReports,
    date_from: date = Query(...),
    date_to: date = Query(...),
) -> Response:
    _validate_period(
        date_from,
        date_to,
    )

    company = await _active_company(
        session
    )

    report = (
        await build_financial_report_detail(
            session,
            company_id=company.id,
            date_from=date_from,
            date_to=date_to,
            timezone_name=company.timezone,
        )
    )

    output = StringIO()
    writer = csv.writer(output)

    writer.writerow(
        [
            "Bandara Cool World",
            "Financial Report",
        ]
    )
    writer.writerow(
        [
            "Period",
            (
                f"{date_from.isoformat()} "
                f"to {date_to.isoformat()}"
            ),
        ]
    )
    writer.writerow([])
    writer.writerow(
        [
            "Section",
            "Account",
            "Amount (LKR)",
        ]
    )

    for line in report.lines:
        writer.writerow(
            [
                line.section,
                line.label,
                f"{line.amount:.2f}",
            ]
        )

    filename = (
        "financial-report-"
        f"{date_from.isoformat()}-"
        f"{date_to.isoformat()}.csv"
    )

    return Response(
        content=output.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": (
                f'attachment; filename="{filename}"'
            )
        },
    )

@router.get(
    "/financial-summary.pdf",
)
async def financial_summary_pdf(
    session: DatabaseSession,
    _: CanViewReports,
    date_from: date = Query(...),
    date_to: date = Query(...),
) -> Response:
    _validate_period(
        date_from,
        date_to,
    )

    company = await _active_company(
        session
    )

    summary = (
        await build_financial_reports_summary(
            session,
            company_id=company.id,
            date_from=date_from,
            date_to=date_to,
            timezone_name=company.timezone,
        )
    )

    pnl = summary.profit_and_loss
    cash = summary.cash_flow
    purchasing = summary.purchasing
    outstanding = summary.receivables

    pdf_bytes = build_financial_report_pdf(
        FinancialReportPDFData(
            company_name=company.name,
            currency_code=company.currency_code,
            timezone_name=company.timezone,
            date_from=date_from,
            date_to=date_to,
            gross_sales=pnl.gross_sales,
            sales_credits=pnl.sales_credits,
            net_revenue=pnl.net_revenue,
            cost_of_goods_sold=(
                pnl.cost_of_goods_sold
            ),
            gross_profit=pnl.gross_profit,
            operating_expenses=(
                pnl.operating_expenses
            ),
            net_profit=pnl.net_profit,
            customer_collections=(
                cash.customer_collections
            ),
            manual_cash_in=(
                cash.manual_cash_in
            ),
            total_cash_in=(
                cash.total_cash_in
            ),
            supplier_payments=(
                cash.supplier_payments
            ),
            manual_cash_out=(
                cash.manual_cash_out
            ),
            total_cash_out=(
                cash.total_cash_out
            ),
            net_cash_flow=(
                cash.net_cash_flow
            ),
            supplier_invoices=(
                purchasing.supplier_invoices
            ),
            customer_receivables=(
                outstanding
                .customer_receivables
            ),
            supplier_payables=(
                outstanding
                .supplier_payables
            ),
        )
    )

    filename = (
        "financial-report-"
        f"{date_from.isoformat()}-"
        f"{date_to.isoformat()}.pdf"
    )

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": (
                f'attachment; filename="{filename}"'
            )
        },
    )

@router.get(
    "/financial-summary.xlsx",
)
async def financial_summary_excel(
    session: DatabaseSession,
    _: CanViewReports,
    date_from: date = Query(...),
    date_to: date = Query(...),
) -> Response:
    _validate_period(
        date_from,
        date_to,
    )

    company = await _active_company(
        session
    )

    summary = (
        await build_financial_reports_summary(
            session,
            company_id=company.id,
            date_from=date_from,
            date_to=date_to,
            timezone_name=company.timezone,
        )
    )

    pnl = summary.profit_and_loss
    cash = summary.cash_flow
    purchasing = summary.purchasing
    outstanding = summary.receivables

    excel_bytes = (
        build_financial_report_excel(
            FinancialReportPDFData(
                company_name=company.name,
                currency_code=(
                    company.currency_code
                ),
                timezone_name=(
                    company.timezone
                ),
                date_from=date_from,
                date_to=date_to,
                gross_sales=(
                    pnl.gross_sales
                ),
                sales_credits=(
                    pnl.sales_credits
                ),
                net_revenue=(
                    pnl.net_revenue
                ),
                cost_of_goods_sold=(
                    pnl.cost_of_goods_sold
                ),
                gross_profit=(
                    pnl.gross_profit
                ),
                operating_expenses=(
                    pnl.operating_expenses
                ),
                net_profit=(
                    pnl.net_profit
                ),
                customer_collections=(
                    cash.customer_collections
                ),
                manual_cash_in=(
                    cash.manual_cash_in
                ),
                total_cash_in=(
                    cash.total_cash_in
                ),
                supplier_payments=(
                    cash.supplier_payments
                ),
                manual_cash_out=(
                    cash.manual_cash_out
                ),
                total_cash_out=(
                    cash.total_cash_out
                ),
                net_cash_flow=(
                    cash.net_cash_flow
                ),
                supplier_invoices=(
                    purchasing
                    .supplier_invoices
                ),
                customer_receivables=(
                    outstanding
                    .customer_receivables
                ),
                supplier_payables=(
                    outstanding
                    .supplier_payables
                ),
            )
        )
    )

    filename = (
        "financial-report-"
        f"{date_from.isoformat()}-"
        f"{date_to.isoformat()}.xlsx"
    )

    return Response(
        content=excel_bytes,
        media_type=(
            "application/vnd."
            "openxmlformats-officedocument."
            "spreadsheetml.sheet"
        ),
        headers={
            "Content-Disposition": (
                f'attachment; '
                f'filename="{filename}"'
            )
        },
    )
