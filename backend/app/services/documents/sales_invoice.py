from __future__ import annotations

from io import BytesIO
from xml.sax.saxutils import escape

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
    quantity,    bandara_document_header,    bandara_footer_story,    bandara_page_footer,
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


    # UNIFIED_BRANDED_PDF_INVOICE_V1
    try:
        _brand_logo = getattr(
            company,
            "logo_path",
            None,
        )
    except Exception:
        _brand_logo = None

    _document_number = str(
        getattr(
            invoice,
            "invoice_number",
            "",
        )
        or ""
    )

    story.extend(
        bandara_document_header(
            document_title="Sales Invoice",
            document_number=_document_number,
            configured_logo_path=_brand_logo,
        )
    )


    company_name = (
        company.name.upper()
        if company is not None
        else "BANDARA COOL WORLD"
    )


    # PDF_LAYOUT_CLEANUP_PHASE4_V2
    # company_name is intentionally preserved because it
    # is reused by the bank-account section.
    # Duplicate company heading and boxed INVOICE title
    # are intentionally removed.


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

        if product is not None:
            product_name = (
                product.name
                or "Product"
            )

            product_code = (
                product.product_code
                or ""
            ).strip()

            description = (
                f"{product_name} ({product_code})"
                if product_code
                else product_name
            )
        else:
            description = (
                item.description
                or "Product"
            )

        if item.description:
            item_note = (
                item.description.strip()
            )

            if item_note.upper().startswith(
                "FREE ITEM -"
            ):
                free_reason = (
                    item_note[
                        len("FREE ITEM -"):
                    ].strip()
                )

                description = (
                    "<b>FREE ITEM</b> - "
                    + description
                )

                if free_reason:
                    description += (
                        "<br/>Reason: "
                        + escape(
                            free_reason
                        )
                    )
            else:
                description += (
                    "<br/>"
                    + escape(
                        item_note
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

    if invoice.trade_ins:
        story.append(
            Paragraph(
                "<b>Trade-In / Exchange</b>",
                STYLES["normal"],
            )
        )

        trade_rows = [
            [
                Paragraph(
                    "<b>Old Unit</b>",
                    STYLES["small"],
                ),
                Paragraph(
                    "<b>Serial</b>",
                    STYLES["small"],
                ),
                Paragraph(
                    "<b>Condition</b>",
                    STYLES["small"],
                ),
                Paragraph(
                    "<b>Allowance</b>",
                    STYLES["small"],
                ),
            ]
        ]

        for trade_in in invoice.trade_ins:
            unit_text = " ".join(
                value
                for value in (
                    trade_in.brand,
                    trade_in.model,
                )
                if value
            ) or "Old A/C unit"

            if trade_in.description:
                unit_text += (
                    "<br/>"
                    + escape(
                        trade_in.description
                    )
                )

            trade_rows.append(
                [
                    Paragraph(
                        escape(unit_text)
                        if "<br/>" not in unit_text
                        else unit_text,
                        STYLES["small"],
                    ),
                    Paragraph(
                        escape(
                            trade_in.serial_number
                            or "-"
                        ),
                        STYLES["small"],
                    ),
                    Paragraph(
                        escape(
                            trade_in.condition
                            or "-"
                        ),
                        STYLES["small"],
                    ),
                    money(
                        trade_in.allowance_amount
                    ),
                ]
            )

        trade_table = Table(
            trade_rows,
            colWidths=[
                92 * mm,
                40 * mm,
                35 * mm,
                30 * mm,
            ],
            repeatRows=1,
        )

        trade_table.setStyle(
            TableStyle(
                [
                    (
                        "LINEABOVE",
                        (0, 0),
                        (-1, 0),
                        0.6,
                        colors.black,
                    ),
                    (
                        "LINEBELOW",
                        (0, 0),
                        (-1, 0),
                        0.6,
                        colors.black,
                    ),
                    (
                        "ALIGN",
                        (-1, 1),
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
                ]
            )
        )

        story.append(
            trade_table
        )

        story.append(
            Spacer(
                1,
                4 * mm,
            )
        )

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
            "Trade-In Allowance",
            f"({money(invoice.trade_in_amount)})",
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
            Paragraph(
                "<b>Customer Payable</b>",
                STYLES["normal"],
            ),
            Paragraph(
                (
                    "<b>"
                    f"{money(invoice.balance_amount + invoice.paid_amount)}"
                    "</b>"
                ),
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

    story.extend(bandara_footer_story())
    doc.build(
        story,
        onFirstPage=bandara_page_footer,
        onLaterPages=bandara_page_footer,
    )

    result = buffer.getvalue()
    buffer.close()

    return result
