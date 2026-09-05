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

from app.models.company import Company
from app.schemas.purchasing import (
    PurchaseOrderDetailResponse,
)
from app.services.documents.base import (
    STYLES,
    bandara_document_header,
    bandara_footer_story,
    bandara_page_footer,
    money,
    quantity,
)


async def build_purchase_order_pdf(
    session,
    purchase_order: PurchaseOrderDetailResponse,
) -> bytes:
    company = await session.get(
        Company,
        purchase_order.company_id,
    )

    buffer = BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=7 * mm,
        rightMargin=7 * mm,
        topMargin=10 * mm,
        bottomMargin=10 * mm,
        title=purchase_order.purchase_order_number,
    )

    story = []

    logo_path = (
        getattr(
            company,
            "logo_path",
            None,
        )
        if company is not None
        else None
    )

    po_number = str(
        purchase_order.purchase_order_number
        or ""
    )

    story.extend(
        bandara_document_header(
            document_title="Purchase Order",
            document_number=po_number,
            configured_logo_path=logo_path,
        )
    )

    order_date = (
        purchase_order.order_date.strftime(
            "%Y-%m-%d"
        )
        if hasattr(
            purchase_order.order_date,
            "strftime",
        )
        else str(
            purchase_order.order_date
            or "-"
        )
    )

    if purchase_order.expected_date is None:
        expected_date = "-"
    elif hasattr(
        purchase_order.expected_date,
        "strftime",
    ):
        expected_date = (
            purchase_order.expected_date
            .strftime(
                "%Y-%m-%d"
            )
        )
    else:
        expected_date = str(
            purchase_order.expected_date
        )

    status_value = (
        purchase_order.status.value
        if hasattr(
            purchase_order.status,
            "value",
        )
        else purchase_order.status
    )

    status_text = str(
        status_value
        or "-"
    ).replace(
        "_",
        " ",
    ).title()

    info = [
        [
            Paragraph(
                (
                    "<b>PO Number:</b> "
                    f"{escape(po_number)}"
                ),
                STYLES["normal"],
            ),
            Paragraph(
                (
                    "<b>Status:</b> "
                    f"{escape(status_text)}"
                ),
                STYLES["normal"],
            ),
        ],
        [
            Paragraph(
                (
                    "<b>Supplier:</b> "
                    f"{escape(str(purchase_order.supplier_name or '-'))}"
                ),
                STYLES["normal"],
            ),
            Paragraph(
                (
                    "<b>Warehouse:</b> "
                    f"{escape(str(purchase_order.warehouse_name or '-'))}"
                ),
                STYLES["normal"],
            ),
        ],
        [
            Paragraph(
                (
                    "<b>Order Date:</b> "
                    f"{escape(order_date)}"
                ),
                STYLES["normal"],
            ),
            Paragraph(
                (
                    "<b>Expected Date:</b> "
                    f"{escape(expected_date)}"
                ),
                STYLES["normal"],
            ),
        ],
    ]

    info_table = Table(
        info,
        colWidths=[
            98 * mm,
            98 * mm,
        ],
    )

    info_table.setStyle(
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
                    4,
                ),
                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, -1),
                    4,
                ),
            ]
        )
    )

    story.append(info_table)

    story.append(
        Spacer(
            1,
            5 * mm,
        )
    )

    rows = [
        [
            Paragraph(
                "<b>#</b>",
                STYLES["center"],
            ),
            Paragraph(
                "<b>Product</b>",
                STYLES["normal"],
            ),
            Paragraph(
                "<b>Qty</b>",
                STYLES["center"],
            ),
            Paragraph(
                "<b>Unit Cost</b>",
                STYLES["center"],
            ),
            Paragraph(
                "<b>Discount</b>",
                STYLES["center"],
            ),
            Paragraph(
                "<b>Tax</b>",
                STYLES["center"],
            ),
            Paragraph(
                "<b>Amount</b>",
                STYLES["center"],
            ),
        ]
    ]

    for index, item in enumerate(
        purchase_order.items,
        start=1,
    ):
        product_name = (
            item.product_name
            or f"Product {item.product_id}"
        )

        product_code = (
            item.product_code
            or ""
        ).strip()

        description = (
            f"{product_name} ({product_code})"
            if product_code
            else product_name
        )

        rows.append(
            [
                Paragraph(
                    str(index),
                    STYLES["center"],
                ),
                Paragraph(
                    escape(description),
                    STYLES["normal"],
                ),
                Paragraph(
                    quantity(
                        item.quantity
                    ),
                    STYLES["center"],
                ),
                Paragraph(
                    money(
                        item.unit_cost
                    ),
                    STYLES["right"],
                ),
                Paragraph(
                    money(
                        item.discount_amount
                    ),
                    STYLES["right"],
                ),
                Paragraph(
                    money(
                        item.tax_amount
                    ),
                    STYLES["right"],
                ),
                Paragraph(
                    money(
                        item.line_total
                    ),
                    STYLES["right"],
                ),
            ]
        )

    items_table = Table(
        rows,
        colWidths=[
            8 * mm,
            63 * mm,
            15 * mm,
            26 * mm,
            25 * mm,
            20 * mm,
            39 * mm,
        ],
        repeatRows=1,
    )

    items_table.setStyle(
        TableStyle(
            [
                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, 0),
                    colors.HexColor(
                        "#F2F6FA"
                    ),
                ),
                (
                    "TEXTCOLOR",
                    (0, 0),
                    (-1, 0),
                    colors.HexColor(
                        "#173F73"
                    ),
                ),
                (
                    "GRID",
                    (0, 0),
                    (-1, -1),
                    0.35,
                    colors.HexColor(
                        "#CBD5E1"
                    ),
                ),
                (
                    "VALIGN",
                    (0, 0),
                    (-1, -1),
                    "TOP",
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
                (
                    "LEFTPADDING",
                    (0, 0),
                    (-1, -1),
                    4,
                ),
                (
                    "RIGHTPADDING",
                    (0, 0),
                    (-1, -1),
                    4,
                ),
            ]
        )
    )

    story.append(
        items_table
    )

    story.append(
        Spacer(
            1,
            5 * mm,
        )
    )

    totals = [
        [
            Paragraph(
                "<b>Subtotal</b>",
                STYLES["right"],
            ),
            Paragraph(
                money(
                    purchase_order.subtotal
                ),
                STYLES["right"],
            ),
        ],
        [
            Paragraph(
                "<b>Discount</b>",
                STYLES["right"],
            ),
            Paragraph(
                money(
                    purchase_order.discount_amount
                ),
                STYLES["right"],
            ),
        ],
        [
            Paragraph(
                "<b>Tax</b>",
                STYLES["right"],
            ),
            Paragraph(
                money(
                    purchase_order.tax_amount
                ),
                STYLES["right"],
            ),
        ],
        [
            Paragraph(
                "<b>Grand Total (LKR)</b>",
                STYLES["right"],
            ),
            Paragraph(
                (
                    "<b>"
                    + money(
                        purchase_order.grand_total
                    )
                    + "</b>"
                ),
                STYLES["right"],
            ),
        ],
    ]

    totals_table = Table(
        totals,
        colWidths=[
            40 * mm,
            40 * mm,
        ],
        hAlign="RIGHT",
    )

    totals_table.setStyle(
        TableStyle(
            [
                (
                    "LINEABOVE",
                    (0, -1),
                    (-1, -1),
                    0.8,
                    colors.HexColor(
                        "#173F73"
                    ),
                ),
                (
                    "TOPPADDING",
                    (0, 0),
                    (-1, -1),
                    4,
                ),
                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, -1),
                    4,
                ),
                (
                    "LEFTPADDING",
                    (0, 0),
                    (-1, -1),
                    4,
                ),
                (
                    "RIGHTPADDING",
                    (0, 0),
                    (-1, -1),
                    4,
                ),
            ]
        )
    )

    story.append(
        totals_table
    )

    if (
        purchase_order.notes
        and str(
            purchase_order.notes
        ).strip()
    ):
        story.append(
            Spacer(
                1,
                5 * mm,
            )
        )

        story.append(
            Paragraph(
                "<b>Notes</b>",
                STYLES["normal"],
            )
        )

        story.append(
            Spacer(
                1,
                1.5 * mm,
            )
        )

        story.append(
            Paragraph(
                escape(
                    str(
                        purchase_order.notes
                    )
                ).replace(
                    "\n",
                    "<br/>",
                ),
                STYLES["normal"],
            )
        )

    story.append(
        Spacer(
            1,
            10 * mm,
        )
    )

    signature_table = Table(
        [
            [
                Paragraph(
                    "________________________",
                    STYLES["center"],
                ),
                Paragraph(
                    "________________________",
                    STYLES["center"],
                ),
                Paragraph(
                    "________________________",
                    STYLES["center"],
                ),
            ],
            [
                Paragraph(
                    "<b>Prepared By</b>",
                    STYLES["center"],
                ),
                Paragraph(
                    "<b>Authorized By</b>",
                    STYLES["center"],
                ),
                Paragraph(
                    "<b>Supplier Acceptance</b>",
                    STYLES["center"],
                ),
            ],
        ],
        colWidths=[
            65 * mm,
            65 * mm,
            65 * mm,
        ],
    )

    signature_table.setStyle(
        TableStyle(
            [
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

    story.append(
        signature_table
    )

    story.append(
        Spacer(
            1,
            6 * mm,
        )
    )

    story.extend(
        bandara_footer_story()
    )

    doc.build(
        story,
        onFirstPage=bandara_page_footer,
        onLaterPages=bandara_page_footer,
    )

    return buffer.getvalue()
