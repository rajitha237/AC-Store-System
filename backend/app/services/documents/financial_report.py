from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from io import BytesIO
from zoneinfo import ZoneInfo

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


@dataclass(frozen=True)
class FinancialReportPDFData:
    company_name: str
    currency_code: str
    timezone_name: str
    date_from: date
    date_to: date

    gross_sales: Decimal
    sales_credits: Decimal
    net_revenue: Decimal
    cost_of_goods_sold: Decimal
    gross_profit: Decimal
    operating_expenses: Decimal
    net_profit: Decimal

    customer_collections: Decimal
    manual_cash_in: Decimal
    total_cash_in: Decimal
    supplier_payments: Decimal
    manual_cash_out: Decimal
    total_cash_out: Decimal
    net_cash_flow: Decimal

    supplier_invoices: Decimal
    customer_receivables: Decimal
    supplier_payables: Decimal


def _money(
    currency: str,
    value: Decimal,
) -> str:
    return (
        f"{currency} "
        f"{Decimal(value):,.2f}"
    )


def _page_number(
    canvas,
    doc,
) -> None:
    canvas.saveState()

    canvas.setFont(
        "Helvetica",
        8,
    )

    canvas.setFillColor(
        colors.HexColor("#667085")
    )

    canvas.drawRightString(
        A4[0] - 18 * mm,
        10 * mm,
        f"Page {doc.page}",
    )

    canvas.restoreState()


def build_financial_report_pdf(
    data: FinancialReportPDFData,
) -> bytes:
    buffer = BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=16 * mm,
        leftMargin=16 * mm,
        topMargin=16 * mm,
        bottomMargin=18 * mm,
        title="Financial Report",
        author=data.company_name,
    )

    title_style = ParagraphStyle(
        "FinancialReportTitle",
        fontName="Helvetica-Bold",
        fontSize=18,
        leading=22,
        textColor=colors.HexColor(
            "#101828"
        ),
        alignment=TA_CENTER,
        spaceAfter=4 * mm,
    )

    company_style = ParagraphStyle(
        "FinancialReportCompany",
        fontName="Helvetica-Bold",
        fontSize=11,
        leading=14,
        textColor=colors.HexColor(
            "#344054"
        ),
        alignment=TA_CENTER,
    )

    meta_style = ParagraphStyle(
        "FinancialReportMeta",
        fontName="Helvetica",
        fontSize=9,
        leading=12,
        textColor=colors.HexColor(
            "#667085"
        ),
        alignment=TA_CENTER,
    )

    section_style = ParagraphStyle(
        "FinancialReportSection",
        fontName="Helvetica-Bold",
        fontSize=12,
        leading=15,
        textColor=colors.HexColor(
            "#101828"
        ),
        spaceBefore=5 * mm,
        spaceAfter=2 * mm,
    )

    note_style = ParagraphStyle(
        "FinancialReportNote",
        fontName="Helvetica",
        fontSize=8.5,
        leading=12,
        textColor=colors.HexColor(
            "#667085"
        ),
    )

    right_style = ParagraphStyle(
        "FinancialAmount",
        fontName="Helvetica",
        fontSize=9,
        leading=12,
        alignment=TA_RIGHT,
    )

    right_bold_style = ParagraphStyle(
        "FinancialAmountBold",
        fontName="Helvetica-Bold",
        fontSize=9,
        leading=12,
        alignment=TA_RIGHT,
    )

    story = []

    story.append(
        Paragraph(
            data.company_name,
            company_style,
        )
    )

    story.append(
        Spacer(
            1,
            2 * mm,
        )
    )

    story.append(
        Paragraph(
            "FINANCIAL REPORT",
            title_style,
        )
    )

    story.append(
        Paragraph(
            (
                f"Period: "
                f"{data.date_from.isoformat()} "
                f"to "
                f"{data.date_to.isoformat()}"
            ),
            meta_style,
        )
    )

    generated_at = datetime.now(
        ZoneInfo(
            data.timezone_name
        )
    )

    story.append(
        Paragraph(
            (
                "Generated: "
                + generated_at.strftime(
                    "%Y-%m-%d %H:%M"
                )
                + " "
                + data.timezone_name
            ),
            meta_style,
        )
    )

    story.append(
        Spacer(
            1,
            6 * mm,
        )
    )

    def section_table(
        title: str,
        rows: list[
            tuple[str, Decimal, bool]
        ],
    ) -> None:
        story.append(
            Paragraph(
                title,
                section_style,
            )
        )

        table_rows = [
            [
                Paragraph(
                    "<b>Account</b>",
                    note_style,
                ),
                Paragraph(
                    "<b>Amount</b>",
                    right_bold_style,
                ),
            ]
        ]

        for label, amount, strong in rows:
            label_style = (
                right_bold_style
                if strong
                else note_style
            )

            amount_style = (
                right_bold_style
                if strong
                else right_style
            )

            table_rows.append(
                [
                    Paragraph(
                        (
                            f"<b>{label}</b>"
                            if strong
                            else label
                        ),
                        label_style,
                    ),
                    Paragraph(
                        _money(
                            data.currency_code,
                            amount,
                        ),
                        amount_style,
                    ),
                ]
            )

        table = Table(
            table_rows,
            colWidths=[
                105 * mm,
                55 * mm,
            ],
            repeatRows=1,
        )

        table.setStyle(
            TableStyle(
                [
                    (
                        "BACKGROUND",
                        (0, 0),
                        (-1, 0),
                        colors.HexColor(
                            "#F2F4F7"
                        ),
                    ),
                    (
                        "TEXTCOLOR",
                        (0, 0),
                        (-1, 0),
                        colors.HexColor(
                            "#344054"
                        ),
                    ),
                    (
                        "GRID",
                        (0, 0),
                        (-1, -1),
                        0.35,
                        colors.HexColor(
                            "#D0D5DD"
                        ),
                    ),
                    (
                        "VALIGN",
                        (0, 0),
                        (-1, -1),
                        "MIDDLE",
                    ),
                    (
                        "LEFTPADDING",
                        (0, 0),
                        (-1, -1),
                        7,
                    ),
                    (
                        "RIGHTPADDING",
                        (0, 0),
                        (-1, -1),
                        7,
                    ),
                    (
                        "TOPPADDING",
                        (0, 0),
                        (-1, -1),
                        6,
                    ),
                    (
                        "BOTTOMPADDING",
                        (0, 0),
                        (-1, -1),
                        6,
                    ),
                ]
            )
        )

        story.append(table)

    section_table(
        "Profit & Loss",
        [
            (
                "Gross sales",
                data.gross_sales,
                False,
            ),
            (
                "Sales credits / reductions",
                data.sales_credits,
                False,
            ),
            (
                "Net revenue",
                data.net_revenue,
                True,
            ),
            (
                "Cost of goods sold",
                data.cost_of_goods_sold,
                False,
            ),
            (
                "Gross profit",
                data.gross_profit,
                True,
            ),
            (
                "Recorded operating expenses",
                data.operating_expenses,
                False,
            ),
            (
                "Net profit",
                data.net_profit,
                True,
            ),
        ],
    )

    section_table(
        "Cash Flow",
        [
            (
                "Customer collections",
                data.customer_collections,
                False,
            ),
            (
                "Manual cash in",
                data.manual_cash_in,
                False,
            ),
            (
                "Total cash in",
                data.total_cash_in,
                True,
            ),
            (
                "Supplier payments",
                data.supplier_payments,
                False,
            ),
            (
                "Manual cash out",
                data.manual_cash_out,
                False,
            ),
            (
                "Total cash out",
                data.total_cash_out,
                True,
            ),
            (
                "Net cash flow",
                data.net_cash_flow,
                True,
            ),
        ],
    )

    section_table(
        "Purchasing & Outstanding",
        [
            (
                "Supplier invoices",
                data.supplier_invoices,
                False,
            ),
            (
                "Customer receivables",
                data.customer_receivables,
                True,
            ),
            (
                "Supplier payables",
                data.supplier_payables,
                True,
            ),
        ],
    )

    story.append(
        Spacer(
            1,
            6 * mm,
        )
    )

    story.append(
        Paragraph(
            (
                "<b>Accounting note:</b> "
                "Revenue and profit are based "
                "on recorded invoice and inventory "
                "cost activity. Cash collections "
                "are shown separately and may include "
                "payments relating to earlier periods. "
                "Operating expenses include active "
                "manual cash-out entries recorded in "
                "the Cash Book."
            ),
            note_style,
        )
    )

    doc.build(
        story,
        onFirstPage=_page_number,
        onLaterPages=_page_number,
    )

    return buffer.getvalue()
