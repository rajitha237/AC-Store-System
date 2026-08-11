from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
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

from app.services.documents.base import (
    STYLES,
    logo_flowable,
    money,
)


@dataclass
class QuotationItemPDFData:
    description: str
    quantity: Decimal
    rate: Decimal
    discounted_amount: Decimal


@dataclass
class QuotationPDFData:
    company_name: str
    company_address: str
    company_phone: str
    logo_path: str | None

    quotation_date: date

    items: list[QuotationItemPDFData]

    warranty_details: list[str]
    service_details: list[str]

    boc_account: str
    hnb_account: str

    validity_days: int = 5


def build_quotation_pdf(
    data: QuotationPDFData,
) -> bytes:
    buffer = BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=16 * mm,
        rightMargin=16 * mm,
        topMargin=13 * mm,
        bottomMargin=10 * mm,
        title="Quotation",
    )

    story = []

    header = Table(
        [
            [
                logo_flowable(
                    data.logo_path,
                    width=31 * mm,
                    height=26 * mm,
                ),
                Paragraph(
                    (
                        f"<b>{data.company_name.upper()}</b><br/>"
                        f"{data.company_address}<br/>"
                        f"{data.company_phone}"
                    ),
                    STYLES["company_detail"],
                ),
            ]
        ],
        colWidths=[
            39 * mm,
            132 * mm,
        ],
    )

    header.setStyle(
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

    story.append(header)
    story.append(Spacer(1, 8 * mm))

    title = Table(
        [["QUOTATION"]],
        colWidths=[38 * mm],
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
                    15,
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

    story.append(title)
    story.append(Spacer(1, 10 * mm))

    story.append(
        Paragraph(
            (
                "<b>Date&nbsp;&nbsp;&nbsp;&nbsp;: "
                f"{data.quotation_date:%Y.%m.%d}</b>"
            ),
            STYLES["normal"],
        )
    )

    story.append(Spacer(1, 5 * mm))

    rows = [
        [
            Paragraph(
                "<b>DESCRIPTIONS</b>",
                STYLES["normal"],
            ),
            Paragraph(
                "<b>QUTY</b>",
                STYLES["center"],
            ),
            Paragraph(
                "<b>RATE</b>",
                STYLES["center"],
            ),
            Paragraph(
                "<b>DISCOUNT<br/>AMOUNT (8%)</b>",
                STYLES["center"],
            ),
        ]
    ]

    for item in data.items:
        rows.append(
            [
                Paragraph(
                    item.description.upper(),
                    STYLES["normal"],
                ),
                f"{int(item.quantity):02d}",
                money(item.rate),
                Paragraph(
                    f"<b>{money(item.discounted_amount)}</b>",
                    STYLES["right"],
                ),
            ]
        )

    table = Table(
        rows,
        colWidths=[
            100 * mm,
            15 * mm,
            34 * mm,
            34 * mm,
        ],
        repeatRows=1,
    )

    table.setStyle(
        TableStyle(
            [
                (
                    "GRID",
                    (0, 0),
                    (-1, -1),
                    0.55,
                    colors.black,
                ),
                (
                    "FONTNAME",
                    (0, 0),
                    (-1, 0),
                    "Times-Bold",
                ),
                (
                    "FONTSIZE",
                    (0, 0),
                    (-1, 0),
                    11,
                ),
                (
                    "FONTSIZE",
                    (0, 1),
                    (-1, -1),
                    8.5,
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
                    "MIDDLE",
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

    story.append(table)
    story.append(Spacer(1, 10 * mm))

    story.append(
        Paragraph(
            "<b>WARRANTY DETAILS</b>",
            STYLES["bold"],
        )
    )

    for value in data.warranty_details:
        story.append(
            Paragraph(
                f"&bull;&nbsp;&nbsp;{value}",
                STYLES["small"],
            )
        )

    story.append(Spacer(1, 6 * mm))

    story.append(
        Paragraph(
            "<b>INSTALLATION &amp; AFTER SALE SERVICE</b>",
            STYLES["bold"],
        )
    )

    for value in data.service_details:
        story.append(
            Paragraph(
                f"&bull;&nbsp;&nbsp;{value}",
                STYLES["normal"],
            )
        )

    story.append(Spacer(1, 11 * mm))

    accounts = Table(
        [
            [
                Paragraph(
                    "<b>Account Number (BOC)</b>",
                    STYLES["normal"],
                ),
                Paragraph(
                    f"<b>{data.boc_account}</b>",
                    STYLES["normal"],
                ),
            ],
            [
                Paragraph(
                    "<b>Account Number (HNB)</b>",
                    STYLES["normal"],
                ),
                Paragraph(
                    f"<b>{data.hnb_account}</b>",
                    STYLES["normal"],
                ),
            ],
        ],
        colWidths=[
            59 * mm,
            45 * mm,
        ],
    )

    accounts.setStyle(
        TableStyle(
            [
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

    story.append(accounts)
    story.append(Spacer(1, 18 * mm))

    valid_style = STYLES["bold"].clone(
        "QuotationValid"
    )

    valid_style.textColor = colors.red

    story.append(
        Paragraph(
            (
                "<b><i>This Quotation Valid - "
                f"{data.validity_days} Days</i></b>"
            ),
            valid_style,
        )
    )

    doc.build(story)

    result = buffer.getvalue()
    buffer.close()

    return result
