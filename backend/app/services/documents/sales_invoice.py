from __future__ import annotations

from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from app.models import (
    Branch,
    Company,
    Customer,
    Product,
    ProductSerialNumber,
    SalesInvoice,
)
from app.services.documents.base import (
    STYLES,
    logo_flowable,
    money,
    quantity,
)


DEFAULT_TERMS = (
    "For Inverter - 1 year Body warranty, 10 years Compressor Warranty. "
    "For Non Inverter - 1 year Body warranty, 05 years Compressor Warranty. "
    "Installation and after sale service Information Free Installation, "
    "Free 3m copper, Free Brackets."
)


async def build_sales_invoice_pdf(
    session,
    invoice: SalesInvoice,
) -> bytes:
    company = await session.get(
        Company,
        invoice.company_id,
    )

    branch = await session.get(
        Branch,
        invoice.branch_id,
    )

    customer = await session.get(
        Customer,
        invoice.customer_id,
    )

    buffer = BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=7 * mm,
        rightMargin=7 * mm,
        topMargin=10 * mm,
        bottomMargin=10 * mm,
        title=invoice.invoice_number,
    )

    story = []

    logo_path = (
        company.logo_path
        if company is not None
        else None
    )

    company_name = (
        company.name.upper()
        if company is not None
        else "BANDARA COOL WORLD"
    )

    company_address = (
        company.address
        if company is not None
        and company.address
        else "A/3 ,Public Shopping Complex ,Kekirawa"
    )

    phone = (
        company.phone
        if company is not None
        and company.phone
        else "077 530 2676 | 074 013 9090"
    )

    heading = Table(
        [
            [
                logo_flowable(
                    logo_path,
                    width=27 * mm,
                    height=23 * mm,
                ),
                Paragraph(
                    (
                        f"<b>{company_name}</b><br/>"
                        f"{company_address}<br/>"
                        f"{phone}"
                    ),
                    STYLES["company_detail"],
                ),
                "",
            ]
        ],
        colWidths=[
            34 * mm,
            127 * mm,
            30 * mm,
        ],
    )

    heading.setStyle(
        TableStyle(
            [
                (
                    "VALIGN",
                    (0, 0),
                    (-1, -1),
                    "TOP",
                ),
            ]
        )
    )

    story.append(heading)
    story.append(Spacer(1, 5 * mm))

    title = Table(
        [["INVOICE"]],
        colWidths=[29 * mm],
    )

    title.setStyle(
        TableStyle(
            [
                (
                    "BOX",
                    (0, 0),
                    (-1, -1),
                    0.8,
                    colors.black,
                ),
                (
                    "FONTNAME",
                    (0, 0),
                    (-1, -1),
                    "Times-Bold",
                ),
                (
                    "FONTSIZE",
                    (0, 0),
                    (-1, -1),
                    13,
                ),
                (
                    "LEFTPADDING",
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
        )
    )

    story.append(title)
    story.append(Spacer(1, 5 * mm))

    display_invoice_number = (
        invoice.invoice_number
        .replace("INV-", "")
        .lstrip("0")
        or "0"
    )

    meta = [
        [
            Paragraph(
                (
                    "<b>Invoice Number:</b> "
                    f"{display_invoice_number}"
                ),
                STYLES["normal"],
            )
        ],
        [
            Paragraph(
                (
                    "<b>Date:</b> "
                    f"{invoice.invoice_date:%Y-%m-%d}"
                ),
                STYLES["normal"],
            )
        ],
        [
            Paragraph(
                (
                    "<b>Time:</b> "
                    f"{invoice.invoice_date:%H:%M:%S}"
                ),
                STYLES["normal"],
            )
        ],
        [
            Paragraph(
                (
                    "<b>Customer:</b> "
                    f"{customer.full_name if customer else '-'}"
                ),
                STYLES["normal"],
            )
        ],
    ]

    meta_table = Table(
        meta,
        colWidths=[190 * mm],
    )

    meta_table.setStyle(
        TableStyle(
            [
                (
                    "LEFTPADDING",
                    (0, 0),
                    (-1, -1),
                    0,
                ),
                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, -1),
                    1,
                ),
            ]
        )
    )

    story.append(meta_table)
    story.append(Spacer(1, 6 * mm))

    rows = [
        [
            Paragraph(
                "<b>Item</b>",
                STYLES["normal"],
            ),
            Paragraph(
                "<b>Qty</b>",
                STYLES["center"],
            ),
            Paragraph(
                "<b>Item<br/>Price</b>",
                STYLES["center"],
            ),
            Paragraph(
                "<b>Discount</b>",
                STYLES["center"],
            ),
            Paragraph(
                "<b>Amount(Rs.)</b>",
                STYLES["center"],
            ),
        ]
    ]

    gross_total = 0

    for item in invoice.items:
        product = await session.get(
            Product,
            item.product_id,
        )

        description = (
            item.description
            or (
                product.name
                if product is not None
                else "Product"
            )
        )

        if item.serial_number_id is not None:
            serial = await session.get(
                ProductSerialNumber,
                item.serial_number_id,
            )

            if serial is not None:
                serial_text = serial.serial_number

                if serial.secondary_serial_number:
                    serial_text += (
                        ", "
                        + serial.secondary_serial_number
                    )

                description += (
                    " - "
                    + serial_text
                )

        if (
            product is not None
            and product.warranty_months > 0
        ):
            if product.warranty_months % 12 == 0:
                years = product.warranty_months // 12

                description += (
                    f"<br/>({years} year"
                    f"{'s' if years != 1 else ''})"
                )

        gross = (
            item.quantity
            * item.unit_price
        )

        gross_total += gross

        rows.append(
            [
                Paragraph(
                    description,
                    STYLES["small"],
                ),
                quantity(item.quantity),
                money(item.unit_price),
                money(item.discount_amount),
                money(item.line_total),
            ]
        )

    item_table = Table(
        rows,
        colWidths=[
            116 * mm,
            15 * mm,
            22 * mm,
            20 * mm,
            24 * mm,
        ],
        repeatRows=1,
    )

    item_table.setStyle(
        TableStyle(
            [
                (
                    "LINEABOVE",
                    (0, 0),
                    (-1, 0),
                    0.7,
                    colors.black,
                ),
                (
                    "LINEBELOW",
                    (0, 0),
                    (-1, 0),
                    0.7,
                    colors.black,
                ),
                (
                    "LINEBELOW",
                    (0, 1),
                    (-1, -1),
                    0.35,
                    colors.grey,
                    None,
                    (1, 2),
                ),
                (
                    "ALIGN",
                    (1, 1),
                    (-1, -1),
                    "RIGHT",
                ),
                (
                    "VALIGN",
                    (0, 0),
                    (-1, -1),
                    "TOP",
                ),
                (
                    "FONTSIZE",
                    (0, 0),
                    (-1, -1),
                    7.5,
                ),
                (
                    "LEFTPADDING",
                    (0, 0),
                    (-1, -1),
                    1,
                ),
                (
                    "RIGHTPADDING",
                    (0, 0),
                    (-1, -1),
                    1,
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

    story.append(item_table)
    story.append(Spacer(1, 4 * mm))

    paid_method = "Cash"

    active_payments = [
        p
        for p in invoice.payments
        if not p.is_reversed
    ]

    if active_payments:
        paid_method = (
            active_payments[-1]
            .payment_method
            .replace("_", " ")
            .title()
        )

    totals = [
        [
            "",
            "Gross Amount",
            money(gross_total),
        ],
        [
            "",
            "Total Discount",
            f"({money(invoice.discount_amount)})",
        ],
        [
            "",
            Paragraph(
                "<b>Net Amount</b>",
                STYLES["normal"],
            ),
            Paragraph(
                f"<b>{money(invoice.grand_total)}</b>",
                STYLES["right"],
            ),
        ],
        [
            "",
            f"Paid Amount ({paid_method})",
            money(invoice.paid_amount),
        ],
        [
            "",
            "Given Credit (Credit)",
            money(invoice.balance_amount),
        ],
    ]

    totals_table = Table(
        totals,
        colWidths=[
            92 * mm,
            57 * mm,
            48 * mm,
        ],
    )

    totals_table.setStyle(
        TableStyle(
            [
                (
                    "ALIGN",
                    (1, 0),
                    (-1, -1),
                    "RIGHT",
                ),
                (
                    "FONTSIZE",
                    (0, 0),
                    (-1, -1),
                    8.5,
                ),
                (
                    "TOPPADDING",
                    (0, 0),
                    (-1, -1),
                    1,
                ),
                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, -1),
                    1,
                ),
            ]
        )
    )

    story.append(totals_table)

    bottom_line = Table(
        [[""]],
        colWidths=[197 * mm],
    )

    bottom_line.setStyle(
        TableStyle(
            [
                (
                    "LINEBELOW",
                    (0, 0),
                    (-1, -1),
                    0.8,
                    colors.black,
                ),
            ]
        )
    )

    story.append(bottom_line)
    story.append(Spacer(1, 12 * mm))

    story.append(
        Paragraph(
            "<b>Terms &amp; Conditions:</b>",
            STYLES["small"],
        )
    )

    story.append(Spacer(1, 5 * mm))

    story.append(
        Paragraph(
            DEFAULT_TERMS,
            STYLES["tiny"],
        )
    )

    story.append(Spacer(1, 12 * mm))

    bank_name = company_name.title()

    bank_table = Table(
        [
            [
                Paragraph(
                    "<b>Bank Account Name</b>",
                    STYLES["normal"],
                ),
                bank_name,
            ],
            [
                Paragraph(
                    "<b>Account Number (BOC)</b>",
                    STYLES["normal"],
                ),
                "88023503",
            ],
            [
                Paragraph(
                    "<b>Account Number (HNB)</b>",
                    STYLES["normal"],
                ),
                "231010003950",
            ],
        ],
        colWidths=[
            69 * mm,
            75 * mm,
        ],
    )

    bank_table.setStyle(
        TableStyle(
            [
                (
                    "FONTSIZE",
                    (0, 0),
                    (-1, -1),
                    9,
                ),
                (
                    "TOPPADDING",
                    (0, 0),
                    (-1, -1),
                    5,
                ),
                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, -1),
                    5,
                ),
            ]
        )
    )

    story.append(bank_table)

    doc.build(story)

    result = buffer.getvalue()
    buffer.close()

    return result
