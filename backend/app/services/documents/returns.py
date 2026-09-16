from __future__ import annotations

from io import BytesIO
from xml.sax.saxutils import escape

from fastapi import HTTPException
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
from sqlalchemy import select

from app.models import (
    Company,
    Customer,
    Product,
    SalesInvoice,
    User,
)
from app.models.credit_note import (
    CustomerRefund,
    RefundStatus,
)
from app.models.inventory import ProductSerialNumber
from app.models.returns import (
    ReturnResolution,
    ReturnStatus,
    SalesReturn,
    SalesReturnItem,
)
from app.services.documents.base import (
    BANDARA_BORDER,
    BANDARA_LIGHT_BLUE,
    BANDARA_MUTED,
    BANDARA_TEXT,
    STYLES,
    bandara_document_header,
    bandara_footer_story,
    bandara_page_footer,
    money,
)


def _text(value: object) -> str:
    if value is None:
        return "-"
    rendered = str(value).strip()
    return escape(rendered) if rendered else "-"


def _date(value: object) -> str:
    if value is None:
        return "-"
    formatter = getattr(value, "strftime", None)
    if callable(formatter):
        return formatter("%Y-%m-%d")
    return _text(value)


def _label(value: object) -> str:
    if value is None:
        return "-"
    return str(value).replace("_", " ").strip().title() or "-"


def _paragraph(value: object, *, bold: bool = False) -> Paragraph:
    rendered = _text(value)
    if bold:
        rendered = f"<b>{rendered}</b>"
    return Paragraph(rendered, STYLES["normal"])


def _info_table(rows: list[list[object]]) -> Table:
    data: list[list[Paragraph]] = []

    for row in rows:
        data.append(
            [
                _paragraph(row[0], bold=True),
                _paragraph(row[1]),
                _paragraph(row[2], bold=True),
                _paragraph(row[3]),
            ]
        )

    table = Table(
        data,
        colWidths=[
            28 * mm,
            62 * mm,
            28 * mm,
            62 * mm,
        ],
        hAlign="LEFT",
    )

    table.setStyle(
        TableStyle(
            [
                (
                    "GRID",
                    (0, 0),
                    (-1, -1),
                    0.45,
                    BANDARA_BORDER,
                ),
                (
                    "BACKGROUND",
                    (0, 0),
                    (0, -1),
                    colors.HexColor("#F8FAFC"),
                ),
                (
                    "BACKGROUND",
                    (2, 0),
                    (2, -1),
                    colors.HexColor("#F8FAFC"),
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
                    8,
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
                    5,
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
            ]
        )
    )

    return table


def _section(title: str) -> Table:
    table = Table(
        [[_paragraph(title.upper(), bold=True)]],
        colWidths=[180 * mm],
    )

    table.setStyle(
        TableStyle(
            [
                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, -1),
                    BANDARA_LIGHT_BLUE,
                ),
                (
                    "LINEBELOW",
                    (0, 0),
                    (-1, -1),
                    0.8,
                    colors.HexColor("#173F73"),
                ),
                (
                    "LEFTPADDING",
                    (0, 0),
                    (-1, -1),
                    5,
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
            ]
        )
    )

    return table


def _signature_block(
    *,
    acknowledgement: str,
) -> list:
    acknowledgement_box = Table(
        [[Paragraph(
            escape(acknowledgement),
            STYLES["normal"],
        )]],
        colWidths=[180 * mm],
    )

    acknowledgement_box.setStyle(
        TableStyle(
            [
                (
                    "BOX",
                    (0, 0),
                    (-1, -1),
                    0.6,
                    BANDARA_BORDER,
                ),
                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, -1),
                    colors.HexColor("#F8FAFC"),
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
                    7,
                ),
                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, -1),
                    7,
                ),
            ]
        )
    )

    signature_table = Table(
        [
            [
                "Customer Name",
                "",
                "Authorized By",
                "",
            ],
            [
                "Signature",
                "",
                "Signature",
                "",
            ],
            [
                "Date",
                "",
                "Date",
                "",
            ],
        ],
        colWidths=[
            24 * mm,
            66 * mm,
            24 * mm,
            66 * mm,
        ],
    )

    signature_table.setStyle(
        TableStyle(
            [
                (
                    "FONTNAME",
                    (0, 0),
                    (0, -1),
                    "Helvetica-Bold",
                ),
                (
                    "FONTNAME",
                    (2, 0),
                    (2, -1),
                    "Helvetica-Bold",
                ),
                (
                    "LINEBELOW",
                    (1, 0),
                    (1, -1),
                    0.5,
                    BANDARA_MUTED,
                ),
                (
                    "LINEBELOW",
                    (3, 0),
                    (3, -1),
                    0.5,
                    BANDARA_MUTED,
                ),
                (
                    "VALIGN",
                    (0, 0),
                    (-1, -1),
                    "BOTTOM",
                ),
                (
                    "TOPPADDING",
                    (0, 0),
                    (-1, -1),
                    9,
                ),
                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, -1),
                    3,
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

    return [
        acknowledgement_box,
        Spacer(1, 8 * mm),
        signature_table,
    ]


async def _serial_text(
    session,
    serial_id: int | None,
) -> str:
    if serial_id is None:
        return "-"

    serial = await session.get(
        ProductSerialNumber,
        serial_id,
    )

    if serial is None:
        return "-"

    return (
        getattr(serial, "serial_number", None)
        or getattr(serial, "serial", None)
        or "-"
    )


async def _product_text(
    session,
    product_id: int | None,
) -> str:
    if product_id is None:
        return "-"

    product = await session.get(
        Product,
        product_id,
    )

    if product is None:
        return "-"

    code = (
        getattr(product, "product_code", None)
        or getattr(product, "code", None)
        or ""
    )

    name = (
        getattr(product, "name", None)
        or getattr(product, "product_name", None)
        or getattr(product, "description", None)
        or ""
    )

    if code and name:
        return f"{code} - {name}"

    return code or name or f"Product #{product_id}"


async def build_refund_acknowledgement_pdf(
    session,
    refund: CustomerRefund,
) -> bytes:
    if refund.status != RefundStatus.POSTED.value:
        raise HTTPException(
            status_code=409,
            detail=(
                "Refund acknowledgement is available "
                "only for posted refunds"
            ),
        )

    sales_return = await session.get(
        SalesReturn,
        refund.return_id,
    )

    if sales_return is None:
        raise HTTPException(
            status_code=404,
            detail="Return not found for refund",
        )

    invoice = await session.get(
        SalesInvoice,
        refund.invoice_id,
    )

    customer = await session.get(
        Customer,
        refund.customer_id,
    )

    company = await session.get(
        Company,
        refund.company_id,
    )

    posted_by = None

    posted_by_id = getattr(
        refund,
        "posted_by_id",
        None,
    )

    if posted_by_id is not None:
        posted_by = await session.get(
            User,
            posted_by_id,
        )

    items = (
        await session.scalars(
            select(SalesReturnItem)
            .where(
                SalesReturnItem.return_id
                == sales_return.id
            )
            .order_by(SalesReturnItem.id)
        )
    ).all()

    buffer = BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=15 * mm,
        rightMargin=15 * mm,
        topMargin=10 * mm,
        bottomMargin=14 * mm,
        title=(
            refund.refund_number
            or f"Refund-{refund.id}"
        ),
    )

    story: list = []

    story.extend(
        bandara_document_header(
            document_title="Refund Acknowledgement",
            document_number=(
                refund.refund_number
                or f"REFUND-{refund.id}"
            ),
            configured_logo_path=getattr(
                company,
                "logo_path",
                None,
            ),
        )
    )

    story.append(_section("Refund Details"))
    story.append(Spacer(1, 2 * mm))

    story.append(
        _info_table(
            [
                [
                    "Refund No",
                    refund.refund_number
                    or f"#{refund.id}",
                    "Return No",
                    sales_return.return_number
                    or f"#{sales_return.id}",
                ],
                [
                    "Invoice No",
                    (
                        invoice.invoice_number
                        if invoice is not None
                        else f"#{refund.invoice_id}"
                    ),
                    "Status",
                    _label(refund.status),
                ],
                [
                    "Customer",
                    (
                        customer.full_name
                        if customer is not None
                        else f"#{refund.customer_id}"
                    ),
                    "Refund Date",
                    _date(
                        getattr(
                            refund,
                            "posted_at",
                            None,
                        )
                        or getattr(
                            refund,
                            "created_at",
                            None,
                        )
                    ),
                ],
                [
                    "Refund Method",
                    _label(refund.refund_method),
                    "Reference",
                    refund.reference_number or "-",
                ],
                [
                    "Amount",
                    f"Rs {money(refund.amount)}",
                    "Processed By",
                    (
                        getattr(
                            posted_by,
                            "full_name",
                            None,
                        )
                        or "-"
                    ),
                ],
            ]
        )
    )

    story.append(Spacer(1, 5 * mm))
    story.append(_section("Returned Items"))
    story.append(Spacer(1, 2 * mm))

    rows: list[list[object]] = [
        [
            "No",
            "Product",
            "Original Serial",
            "Qty",
            "Condition",
            "Amount",
        ]
    ]

    for index, item in enumerate(
        items,
        start=1,
    ):
        rows.append(
            [
                str(index),
                _paragraph(
                    await _product_text(
                        session,
                        item.product_id,
                    )
                ),
                _paragraph(
                    await _serial_text(
                        session,
                        item.serial_number_id,
                    )
                ),
                str(item.quantity),
                _label(item.condition),
                f"Rs {money(item.line_total)}",
            ]
        )

    item_table = Table(
        rows,
        colWidths=[
            9 * mm,
            62 * mm,
            45 * mm,
            14 * mm,
            24 * mm,
            26 * mm,
        ],
        repeatRows=1,
    )

    item_table.setStyle(
        TableStyle(
            [
                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, 0),
                    BANDARA_LIGHT_BLUE,
                ),
                (
                    "GRID",
                    (0, 0),
                    (-1, -1),
                    0.45,
                    BANDARA_BORDER,
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
                    7.3,
                ),
                (
                    "VALIGN",
                    (0, 0),
                    (-1, -1),
                    "TOP",
                ),
                (
                    "ALIGN",
                    (0, 1),
                    (0, -1),
                    "CENTER",
                ),
                (
                    "ALIGN",
                    (3, 1),
                    (-1, -1),
                    "RIGHT",
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
            ]
        )
    )

    story.append(item_table)
    story.append(Spacer(1, 5 * mm))

    notes = getattr(refund, "notes", None)

    if notes:
        story.append(_section("Notes"))
        story.append(Spacer(1, 2 * mm))
        story.append(
            Table(
                [[_paragraph(notes)]],
                colWidths=[180 * mm],
                style=[
                    (
                        "BOX",
                        (0, 0),
                        (-1, -1),
                        0.45,
                        BANDARA_BORDER,
                    ),
                    (
                        "LEFTPADDING",
                        (0, 0),
                        (-1, -1),
                        6,
                    ),
                    (
                        "RIGHTPADDING",
                        (0, 0),
                        (-1, -1),
                        6,
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
                ],
            )
        )
        story.append(Spacer(1, 5 * mm))

    story.extend(
        _signature_block(
            acknowledgement=(
                "I acknowledge that I have received "
                "the refund amount shown above for "
                "the referenced return."
            )
        )
    )

    story.extend(bandara_footer_story())

    doc.build(
        story,
        onFirstPage=bandara_page_footer,
        onLaterPages=bandara_page_footer,
    )

    return buffer.getvalue()


async def build_replacement_issue_note_pdf(
    session,
    sales_return: SalesReturn,
) -> bytes:
    if (
        sales_return.resolution
        != ReturnResolution.REPLACEMENT.value
        or sales_return.status
        != ReturnStatus.COMPLETED.value
    ):
        raise HTTPException(
            status_code=409,
            detail=(
                "Replacement issue note is available "
                "only for completed replacement returns"
            ),
        )

    items = (
        await session.scalars(
            select(SalesReturnItem)
            .where(
                SalesReturnItem.return_id
                == sales_return.id
            )
            .order_by(SalesReturnItem.id)
        )
    ).all()

    replacement_items = [
        item
        for item in items
        if (
            item.replacement_product_id
            is not None
            and item.replacement_stock_movement_id
            is not None
        )
    ]

    if not replacement_items:
        raise HTTPException(
            status_code=409,
            detail=(
                "No issued replacement items exist "
                "for this return"
            ),
        )

    invoice = await session.get(
        SalesInvoice,
        sales_return.invoice_id,
    )

    customer = await session.get(
        Customer,
        sales_return.customer_id,
    )

    company = await session.get(
        Company,
        sales_return.company_id,
    )

    approved_by = None

    if sales_return.approved_by_id is not None:
        approved_by = await session.get(
            User,
            sales_return.approved_by_id,
        )

    buffer = BytesIO()

    document_number = (
        sales_return.return_number
        or f"RET-{sales_return.id}"
    )

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=15 * mm,
        rightMargin=15 * mm,
        topMargin=10 * mm,
        bottomMargin=14 * mm,
        title=f"{document_number}-Replacement",
    )

    story: list = []

    story.extend(
        bandara_document_header(
            document_title="Replacement Issue Note",
            document_number=document_number,
            configured_logo_path=getattr(
                company,
                "logo_path",
                None,
            ),
        )
    )

    story.append(_section("Replacement Details"))
    story.append(Spacer(1, 2 * mm))

    story.append(
        _info_table(
            [
                [
                    "Return No",
                    document_number,
                    "Invoice No",
                    (
                        invoice.invoice_number
                        if invoice is not None
                        else f"#{sales_return.invoice_id}"
                    ),
                ],
                [
                    "Customer",
                    (
                        customer.full_name
                        if customer is not None
                        else f"#{sales_return.customer_id}"
                    ),
                    "Issue Date",
                    _date(
                        sales_return.completed_at
                    ),
                ],
                [
                    "Resolution",
                    _label(
                        sales_return.resolution
                    ),
                    "Status",
                    _label(
                        sales_return.status
                    ),
                ],
                [
                    "Approved By",
                    (
                        getattr(
                            approved_by,
                            "full_name",
                            None,
                        )
                        or "-"
                    ),
                    "Reason",
                    sales_return.reason,
                ],
            ]
        )
    )

    story.append(Spacer(1, 5 * mm))
    story.append(
        _section(
            "Returned Item / Replacement Item Mapping"
        )
    )
    story.append(Spacer(1, 2 * mm))

    rows: list[list[object]] = [
        [
            "No",
            "Returned Product",
            "Original Serial",
            "Replacement Product",
            "Replacement Serial",
            "Qty",
        ]
    ]

    for index, item in enumerate(
        replacement_items,
        start=1,
    ):
        rows.append(
            [
                str(index),
                _paragraph(
                    await _product_text(
                        session,
                        item.product_id,
                    )
                ),
                _paragraph(
                    await _serial_text(
                        session,
                        item.serial_number_id,
                    )
                ),
                _paragraph(
                    await _product_text(
                        session,
                        item.replacement_product_id,
                    )
                ),
                _paragraph(
                    await _serial_text(
                        session,
                        item.replacement_serial_number_id,
                    )
                ),
                str(item.quantity),
            ]
        )

    mapping_table = Table(
        rows,
        colWidths=[
            8 * mm,
            43 * mm,
            37 * mm,
            43 * mm,
            37 * mm,
            12 * mm,
        ],
        repeatRows=1,
    )

    mapping_table.setStyle(
        TableStyle(
            [
                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, 0),
                    BANDARA_LIGHT_BLUE,
                ),
                (
                    "GRID",
                    (0, 0),
                    (-1, -1),
                    0.45,
                    BANDARA_BORDER,
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
                    6.8,
                ),
                (
                    "VALIGN",
                    (0, 0),
                    (-1, -1),
                    "TOP",
                ),
                (
                    "ALIGN",
                    (0, 1),
                    (0, -1),
                    "CENTER",
                ),
                (
                    "ALIGN",
                    (5, 1),
                    (5, -1),
                    "RIGHT",
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

    story.append(mapping_table)
    story.append(Spacer(1, 7 * mm))

    story.extend(
        _signature_block(
            acknowledgement=(
                "I acknowledge receipt of the "
                "replacement item(s) listed above "
                "in connection with this return."
            )
        )
    )

    story.extend(bandara_footer_story())

    doc.build(
        story,
        onFirstPage=bandara_page_footer,
        onLaterPages=bandara_page_footer,
    )

    return buffer.getvalue()
