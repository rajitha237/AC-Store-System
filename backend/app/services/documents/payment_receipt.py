from __future__ import annotations

from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.platypus import (
    KeepTogether,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from app.models import (
    Company,
    Customer,
    CustomerPayment,
    SalesInvoice,
    User,
)
from app.services.documents.base import (
    STYLES,
    money,
    paragraph,
)


async def build_payment_receipt_pdf(
    session,
    payment: CustomerPayment,
) -> bytes:
    company = await session.get(
        Company,
        payment.company_id,
    )

    customer = await session.get(
        Customer,
        payment.customer_id,
    )

    invoice = None

    if payment.invoice_id is not None:
        invoice = await session.get(
            SalesInvoice,
            payment.invoice_id,
        )

    user = await session.get(
        User,
        payment.created_by_id,
    )

    buffer = BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=16 * mm,
        rightMargin=16 * mm,
        topMargin=10 * mm,
        bottomMargin=13 * mm,
        title=payment.receipt_number,
    )

    story = []

    company_name = (
        company.name
        if company is not None
        else "BANDARA COOL WORLD"
    )

    story.append(
        Paragraph(
            company_name.upper(),
            STYLES["heading"],
        )
    )

    line = Table(
        [[""]],
        colWidths=[178 * mm],
        rowHeights=[1.5 * mm],
    )

    line.setStyle(
        TableStyle(
            [
                (
                    "LINEBELOW",
                    (0, 0),
                    (-1, -1),
                    1,
                    colors.black,
                    None,
                    (2, 2),
                ),
            ]
        )
    )

    story.append(line)
    story.append(Spacer(1, 5 * mm))

    story.append(
        Paragraph(
            "CUSTOMER RECEIPT",
            STYLES["normal"],
        )
    )

    receipt_number = (
        payment.receipt_number
        .replace("REC-", "")
        .lstrip("0")
        or "0"
    )

    invoice_date = (
        invoice.invoice_date.strftime(
            "%Y-%m-%d"
        )
        if invoice is not None
        else payment.payment_date.strftime(
            "%Y-%m-%d"
        )
    )

    customer_name = (
        customer.full_name
        if customer is not None
        else "-"
    )

    customer_city = ""

    if customer is not None:
        customer_city = (
            customer.city
            or customer.address_line_1
            or ""
        )

    left_box = Table(
        [
            [
                "Receipt No",
                ":",
                receipt_number,
            ],
            [
                "Invoice Date",
                ":",
                invoice_date,
            ],
        ],
        colWidths=[
            24 * mm,
            5 * mm,
            30 * mm,
        ],
        rowHeights=[
            7 * mm,
            7 * mm,
        ],
    )

    left_box.setStyle(
        TableStyle(
            [
                (
                    "BOX",
                    (0, 0),
                    (-1, -1),
                    0.7,
                    colors.black,
                ),
                (
                    "VALIGN",
                    (0, 0),
                    (-1, -1),
                    "MIDDLE",
                ),
                (
                    "FONTNAME",
                    (0, 0),
                    (-1, -1),
                    "Helvetica",
                ),
                (
                    "FONTSIZE",
                    (0, 0),
                    (-1, -1),
                    8.5,
                ),
                (
                    "LEFTPADDING",
                    (0, 0),
                    (-1, -1),
                    5,
                ),
                (
                    "RIGHTPADDING",
                    (0, 0),
                    (-1, -1),
                    3,
                ),
            ]
        )
    )

    right_box = Table(
        [
            [
                "Customer",
                ":",
                customer_name,
            ],
            [
                "",
                ":",
                customer_city.upper(),
            ],
        ],
        colWidths=[
            28 * mm,
            5 * mm,
            79 * mm,
        ],
        rowHeights=[
            7 * mm,
            7 * mm,
        ],
    )

    right_box.setStyle(
        TableStyle(
            [
                (
                    "BOX",
                    (0, 0),
                    (-1, -1),
                    0.7,
                    colors.black,
                ),
                (
                    "VALIGN",
                    (0, 0),
                    (-1, -1),
                    "MIDDLE",
                ),
                (
                    "FONTNAME",
                    (0, 0),
                    (-1, -1),
                    "Helvetica",
                ),
                (
                    "FONTSIZE",
                    (0, 0),
                    (-1, -1),
                    8.5,
                ),
                (
                    "LEFTPADDING",
                    (0, 0),
                    (-1, -1),
                    5,
                ),
            ]
        )
    )

    header_boxes = Table(
        [[left_box, right_box]],
        colWidths=[
            62 * mm,
            114 * mm,
        ],
        hAlign="LEFT",
    )

    header_boxes.setStyle(
        TableStyle(
            [
                (
                    "VALIGN",
                    (0, 0),
                    (-1, -1),
                    "TOP",
                ),
                (
                    "LEFTPADDING",
                    (0, 0),
                    (-1, -1),
                    0,
                ),
                (
                    "RIGHTPADDING",
                    (0, 0),
                    (-1, -1),
                    3,
                ),
            ]
        )
    )

    story.append(header_boxes)
    story.append(Spacer(1, 5 * mm))

    invoice_number = ""

    if invoice is not None:
        invoice_number = (
            invoice.invoice_number
            .replace("INV-", "")
            .lstrip("0")
        )

    invoice_amount = (
        invoice.grand_total
        if invoice is not None
        else payment.amount
    )

    current_paid = (
        invoice.paid_amount
        if invoice is not None
        else payment.amount
    )

    current_balance = (
        invoice.balance_amount
        if invoice is not None
        else 0
    )

    invoice_rows = [
        [
            "No",
            "Inv No",
            "Inv Amount",
            "Paid Amount",
            "Balance",
            "Total",
        ],
        [
            "1",
            invoice_number,
            money(invoice_amount),
            money(payment.amount),
            money(current_balance),
            money(payment.amount),
        ],
    ]

    invoice_table = Table(
        invoice_rows,
        colWidths=[
            11 * mm,
            23 * mm,
            40 * mm,
            45 * mm,
            29 * mm,
            30 * mm,
        ],
    )

    invoice_table.setStyle(
        TableStyle(
            [
                (
                    "GRID",
                    (0, 0),
                    (-1, -1),
                    0.6,
                    colors.black,
                ),
                (
                    "FONTNAME",
                    (0, 0),
                    (-1, 0),
                    "Helvetica-Bold",
                ),
                (
                    "FONTNAME",
                    (0, 1),
                    (-1, -1),
                    "Helvetica",
                ),
                (
                    "FONTSIZE",
                    (0, 0),
                    (-1, -1),
                    7.5,
                ),
                (
                    "ALIGN",
                    (0, 0),
                    (-1, -1),
                    "CENTER",
                ),
                (
                    "ALIGN",
                    (2, 1),
                    (-1, -1),
                    "RIGHT",
                ),
                (
                    "TOPPADDING",
                    (0, 0),
                    (-1, -1),
                    2,
                ),
                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, -1),
                    2,
                ),
            ]
        )
    )

    story.append(invoice_table)
    story.append(Spacer(1, 5 * mm))

    cash = 0
    cheque = 0
    card = 0
    bank = 0
    over_balance = 0

    method = payment.payment_method

    if method == "cash":
        cash = payment.amount
    elif method == "cheque":
        cheque = payment.amount
    elif method == "card":
        card = payment.amount
    elif method in {
        "bank_transfer",
        "online",
    }:
        bank = payment.amount

    payment_details = Table(
        [
            [
                Paragraph(
                    "<b><u>Payment Details</u></b>",
                    STYLES["normal"],
                ),
                "",
                "",
            ],
            [
                "Cash Amount",
                ":",
                f"Rs {money(cash)}",
            ],
            [
                "Chq Amount",
                ":",
                f"Rs {money(cheque)}",
            ],
            [
                "Over Balance",
                ":",
                f"Rs {money(over_balance)}",
            ],
            [
                "Card Amount",
                ":",
                f"Rs {money(card)}",
            ],
            [
                "Bank Amount",
                ":",
                f"Rs {money(bank)}",
            ],
        ],
        colWidths=[
            25 * mm,
            5 * mm,
            31 * mm,
        ],
    )

    payment_details.setStyle(
        TableStyle(
            [
                (
                    "BOX",
                    (0, 0),
                    (-1, -1),
                    0.6,
                    colors.black,
                ),
                (
                    "SPAN",
                    (0, 0),
                    (-1, 0),
                ),
                (
                    "ALIGN",
                    (0, 0),
                    (-1, 0),
                    "CENTER",
                ),
                (
                    "FONTSIZE",
                    (0, 0),
                    (-1, -1),
                    8,
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
                (
                    "LEFTPADDING",
                    (0, 0),
                    (-1, -1),
                    5,
                ),
            ]
        )
    )

    totals = Table(
        [
            [
                "Total Amount",
                ":",
                "Rs",
                money(payment.amount),
            ],
            [
                "Bill Discount",
                ":",
                "Rs",
                "0.00",
            ],
            [
                "Balance",
                ":",
                "Rs",
                "0.00",
            ],
            [
                "",
                "",
                "",
                "",
            ],
            [
                Paragraph(
                    "<b>Net Amount</b>",
                    STYLES["normal"],
                ),
                ":",
                "Rs",
                money(payment.amount),
            ],
        ],
        colWidths=[
            33 * mm,
            8 * mm,
            9 * mm,
            27 * mm,
        ],
    )

    totals.setStyle(
        TableStyle(
            [
                (
                    "FONTSIZE",
                    (0, 0),
                    (-1, -1),
                    8.5,
                ),
                (
                    "ALIGN",
                    (0, 0),
                    (0, -1),
                    "RIGHT",
                ),
                (
                    "ALIGN",
                    (3, 0),
                    (3, -1),
                    "RIGHT",
                ),
                (
                    "LINEABOVE",
                    (0, 4),
                    (-1, 4),
                    1,
                    colors.black,
                ),
                (
                    "LINEBELOW",
                    (0, 4),
                    (-1, 4),
                    1,
                    colors.black,
                ),
                (
                    "TOPPADDING",
                    (0, 0),
                    (-1, -1),
                    2,
                ),
                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, -1),
                    2,
                ),
            ]
        )
    )

    middle = Table(
        [[payment_details, totals]],
        colWidths=[
            74 * mm,
            101 * mm,
        ],
    )

    middle.setStyle(
        TableStyle(
            [
                (
                    "VALIGN",
                    (0, 0),
                    (-1, -1),
                    "TOP",
                ),
                (
                    "LEFTPADDING",
                    (0, 0),
                    (-1, -1),
                    0,
                ),
                (
                    "RIGHTPADDING",
                    (0, 0),
                    (-1, -1),
                    0,
                ),
            ]
        )
    )

    story.append(middle)

    story.append(
        Spacer(
            1,
            4 * mm,
        )
    )

    story.append(
        Paragraph(
            (
                "Total Credit Balance : "
                f"Rs. {money(current_balance)}"
            ),
            STYLES["normal"],
        )
    )

    story.append(
        Spacer(
            1,
            14 * mm,
        )
    )

    prepared_name = (
        user.full_name
        if user is not None
        else ""
    )

    prepared = Table(
        [
            [
                "",
                "____________________________",
            ],
            [
                "",
                "Prepared By",
            ],
            [
                "",
                prepared_name,
            ],
        ],
        colWidths=[
            120 * mm,
            55 * mm,
        ],
    )

    prepared.setStyle(
        TableStyle(
            [
                (
                    "ALIGN",
                    (1, 0),
                    (1, -1),
                    "CENTER",
                ),
                (
                    "FONTSIZE",
                    (0, 0),
                    (-1, -1),
                    8,
                ),
            ]
        )
    )

    story.append(prepared)

    doc.build(story)

    result = buffer.getvalue()
    buffer.close()

    return result
