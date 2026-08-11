from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from io import BytesIO
from decimal import Decimal

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
class JobCardPDFData:
    company_name: str
    company_address: str
    company_phone: str
    logo_path: str | None

    job_number: str
    customer_name: str
    customer_address: str
    mobile: str

    create_datetime: datetime
    user_name: str

    handover_date: date | None
    job_type: str
    receiving_officer: str | None

    brand: str | None
    model: str | None
    color: str | None
    common: str | None

    problems: str
    imei_number: str | None
    serial_number: str | None
    battery_condition: str | None
    special_note: str | None
    estimate_cost: Decimal | None

    terms_and_conditions: str | None


def build_job_card_pdf(
    data: JobCardPDFData,
) -> bytes:
    buffer = BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=9 * mm,
        rightMargin=9 * mm,
        topMargin=9 * mm,
        bottomMargin=10 * mm,
        title=f"JOB-{data.job_number}",
    )

    story = []

    header = Table(
        [
            [
                logo_flowable(
                    data.logo_path,
                    width=25 * mm,
                    height=21 * mm,
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
            37 * mm,
            145 * mm,
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
    story.append(Spacer(1, 5 * mm))

    rule = Table(
        [[""]],
        colWidths=[183 * mm],
    )

    rule.setStyle(
        TableStyle(
            [
                (
                    "LINEBELOW",
                    (0, 0),
                    (-1, -1),
                    1.5,
                    colors.black,
                ),
            ]
        )
    )

    story.append(rule)

    story.append(
        Paragraph(
            "<b>JOB CARD</b>",
            STYLES["normal"],
        )
    )

    left = [
        ["Customer", ":", data.customer_name],
        ["Address", ":", data.customer_address],
        ["Mobile", ":", data.mobile],
        [
            "Create Date",
            ":",
            data.create_datetime.strftime(
                "%Y-%m-%d"
            ),
        ],
        [
            "Create Time",
            ":",
            data.create_datetime.strftime(
                "%H:%M:%S"
            ),
        ],
    ]

    right = [
        ["Job No", ":", data.job_number],
        ["User", ":", data.user_name],
        [
            "Handover Date",
            ":",
            (
                data.handover_date.strftime(
                    "%Y-%m-%d"
                )
                if data.handover_date
                else ""
            ),
        ],
        ["Job Type", ":", data.job_type],
        [
            "Job Receiving Officer",
            ":",
            data.receiving_officer or "N/A",
        ],
    ]

    left_table = Table(
        left,
        colWidths=[
            22 * mm,
            4 * mm,
            69 * mm,
        ],
    )

    right_table = Table(
        right,
        colWidths=[
            31 * mm,
            4 * mm,
            51 * mm,
        ],
    )

    for table in [
        left_table,
        right_table,
    ]:
        table.setStyle(
            TableStyle(
                [
                    (
                        "FONTSIZE",
                        (0, 0),
                        (-1, -1),
                        7.5,
                    ),
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
                        1,
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

    info = Table(
        [[left_table, right_table]],
        colWidths=[
            98 * mm,
            86 * mm,
        ],
    )

    info.setStyle(
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

    story.append(info)
    story.append(Spacer(1, 3 * mm))

    details = [
        ["Brand:", data.brand or "None"],
        ["Model:", data.model or ""],
        ["Color:", data.color or ""],
        ["Common", data.common or ""],
        ["Problems:", data.problems],
        ["IMI Number:", data.imei_number or ""],
        ["Serial Number:", data.serial_number or ""],
        [
            "Battery Condition:",
            data.battery_condition or "",
        ],
        ["Special Note:", data.special_note or ""],
        [
            "Estimate Cost:",
            (
                f"Rs. {money(data.estimate_cost)}"
                if data.estimate_cost is not None
                else ""
            ),
        ],
    ]

    detail_table = Table(
        details,
        colWidths=[
            34 * mm,
            148 * mm,
        ],
        rowHeights=[
            7 * mm,
            7 * mm,
            7 * mm,
            7 * mm,
            8 * mm,
            7 * mm,
            7 * mm,
            7 * mm,
            7 * mm,
            7 * mm,
        ],
    )

    detail_table.setStyle(
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
                    (0, -1),
                    "Helvetica-Bold",
                ),
                (
                    "FONTSIZE",
                    (0, 0),
                    (-1, -1),
                    7.5,
                ),
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
                    3,
                ),
            ]
        )
    )

    story.append(detail_table)
    story.append(Spacer(1, 4 * mm))

    story.append(
        Paragraph(
            "<b>Terms and Conditions</b>",
            STYLES["small"],
        )
    )

    if data.terms_and_conditions:
        story.append(
            Paragraph(
                data.terms_and_conditions,
                STYLES["tiny"],
            )
        )

    story.append(Spacer(1, 12 * mm))

    signatures = Table(
        [
            [
                "____________________________",
                "",
                "____________________________",
            ],
            [
                "Signature Client",
                "",
                "Signature Cashier",
            ],
        ],
        colWidths=[
            68 * mm,
            46 * mm,
            68 * mm,
        ],
    )

    signatures.setStyle(
        TableStyle(
            [
                (
                    "ALIGN",
                    (0, 0),
                    (0, -1),
                    "LEFT",
                ),
                (
                    "ALIGN",
                    (2, 0),
                    (2, -1),
                    "LEFT",
                ),
                (
                    "FONTSIZE",
                    (0, 0),
                    (-1, -1),
                    7,
                ),
            ]
        )
    )

    story.append(signatures)

    doc.build(story)

    result = buffer.getvalue()
    buffer.close()

    return result
