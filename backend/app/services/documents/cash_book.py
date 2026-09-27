from __future__ import annotations

from datetime import date
from io import BytesIO
from typing import Iterable

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from app.schemas.cash_book import (
    CashBookSummaryResponse,
    CashBookTransactionResponse,
)


def _text(value: object | None) -> str:
    if value is None:
        return "-"

    return str(value)


def _amount(value: object) -> str:
    try:
        return f"{float(value):,.2f}"
    except (TypeError, ValueError):
        return str(value)


def build_cash_book_pdf(
    *,
    company_name: str,
    date_from: date,
    date_to: date,
    summary: CashBookSummaryResponse,
    transactions: Iterable[
        CashBookTransactionResponse
    ],
    approval_text: str | None = None,
) -> bytes:
    buffer = BytesIO()

    document = SimpleDocTemplate(
        buffer,
        pagesize=landscape(A4),
        leftMargin=10 * mm,
        rightMargin=10 * mm,
        topMargin=10 * mm,
        bottomMargin=10 * mm,
        title="Cash Book",
        author=company_name,
    )

    title_style = ParagraphStyle(
        "CashBookTitle",
        fontName="Helvetica-Bold",
        fontSize=16,
        leading=20,
        alignment=TA_CENTER,
        spaceAfter=4 * mm,
    )

    normal_style = ParagraphStyle(
        "CashBookNormal",
        fontName="Helvetica",
        fontSize=8,
        leading=10,
    )

    right_style = ParagraphStyle(
        "CashBookRight",
        fontName="Helvetica",
        fontSize=8,
        leading=10,
        alignment=TA_RIGHT,
    )

    story = [
        Paragraph(
            f"{company_name} - Cash Book",
            title_style,
        ),
        Paragraph(
            (
                f"Period: {date_from.isoformat()} "
                f"to {date_to.isoformat()}"
            ),
            normal_style,
        ),
    ]

    if approval_text:
        story.append(
            Paragraph(
                approval_text,
                normal_style,
            )
        )

    story.extend(
        [
            Spacer(1, 4 * mm),
            Table(
                [
                    [
                        "Opening Balance",
                        "Money In",
                        "Money Out",
                        "Closing Balance",
                        "Transactions",
                    ],
                    [
                        _amount(
                            summary.opening_balance
                        ),
                        _amount(summary.cash_in),
                        _amount(summary.cash_out),
                        _amount(
                            summary.closing_balance
                        ),
                        str(
                            summary.transaction_count
                        ),
                    ],
                ],
                colWidths=[
                    48 * mm,
                    48 * mm,
                    48 * mm,
                    48 * mm,
                    38 * mm,
                ],
            ),
            Spacer(1, 5 * mm),
        ]
    )

    rows = [
        [
            "Date",
            "Reference",
            "Source",
            "Description",
            "Method",
            "Status",
            "Money In",
            "Money Out",
            "Balance",
        ]
    ]

    for transaction in transactions:
        money_in = (
            _amount(transaction.amount)
            if transaction.direction
            == "cash_in"
            else "-"
        )

        money_out = (
            _amount(transaction.amount)
            if transaction.direction
            == "cash_out"
            else "-"
        )

        status_text = (
            transaction.status or "-"
        )

        if transaction.cheque_status:
            status_text = (
                f"{status_text} / "
                f"{transaction.cheque_status}"
            )

        rows.append(
            [
                Paragraph(
                    _text(
                        transaction.transaction_date
                    ),
                    normal_style,
                ),
                Paragraph(
                    _text(
                        transaction.source_reference
                        or transaction.reference_number
                    ),
                    normal_style,
                ),
                Paragraph(
                    _text(
                        transaction.source_type
                    ).replace(
                        "_",
                        " ",
                    ),
                    normal_style,
                ),
                Paragraph(
                    _text(
                        transaction.description
                    ),
                    normal_style,
                ),
                Paragraph(
                    _text(
                        transaction.payment_method
                    ).replace(
                        "_",
                        " ",
                    ),
                    normal_style,
                ),
                Paragraph(
                    status_text,
                    normal_style,
                ),
                Paragraph(
                    money_in,
                    right_style,
                ),
                Paragraph(
                    money_out,
                    right_style,
                ),
                Paragraph(
                    (
                        _amount(
                            transaction.running_balance
                        )
                        if (
                            transaction.running_balance
                            is not None
                        )
                        else "-"
                    ),
                    right_style,
                ),
            ]
        )

    transaction_table = Table(
        rows,
        repeatRows=1,
        colWidths=[
            28 * mm,
            29 * mm,
            28 * mm,
            52 * mm,
            27 * mm,
            31 * mm,
            26 * mm,
            26 * mm,
            29 * mm,
        ],
    )

    common_style = [
        (
            "BACKGROUND",
            (0, 0),
            (-1, 0),
            colors.HexColor("#E8EDF3"),
        ),
        (
            "FONTNAME",
            (0, 0),
            (-1, 0),
            "Helvetica-Bold",
        ),
        (
            "FONTSIZE",
            (0, 0),
            (-1, -1),
            7,
        ),
        (
            "VALIGN",
            (0, 0),
            (-1, -1),
            "TOP",
        ),
        (
            "GRID",
            (0, 0),
            (-1, -1),
            0.25,
            colors.HexColor("#B8C0CA"),
        ),
        (
            "LEFTPADDING",
            (0, 0),
            (-1, -1),
            3,
        ),
        (
            "RIGHTPADDING",
            (0, 0),
            (-1, -1),
            3,
        ),
        (
            "TOPPADDING",
            (0, 0),
            (-1, -1),
            3,
        ),
        (
            "BOTTOMPADDING",
            (0, 0),
            (-1, -1),
            3,
        ),
    ]

    transaction_table.setStyle(
        TableStyle(common_style)
    )

    story.append(transaction_table)

    story.extend(
        [
            Spacer(1, 5 * mm),
            Paragraph(
                (
                    "Payment method totals: "
                    f"Cash In {_amount(summary.cash_method_in)} | "
                    f"Cash Out {_amount(summary.cash_method_out)} | "
                    f"Bank In {_amount(summary.bank_transfer_in)} | "
                    f"Bank Out {_amount(summary.bank_transfer_out)} | "
                    f"Card In {_amount(summary.card_in)} | "
                    f"Card Out {_amount(summary.card_out)} | "
                    f"Cheque In {_amount(summary.cheque_in)} | "
                    f"Cheque Out {_amount(summary.cheque_out)} | "
                    f"Pending Cheque Out "
                    f"{_amount(summary.cheque_pending_out)}"
                ),
                normal_style,
            ),
        ]
    )

    document.build(story)

    return buffer.getvalue()
