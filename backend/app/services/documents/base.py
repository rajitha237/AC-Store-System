from __future__ import annotations

from io import BytesIO
from pathlib import Path
from typing import Any

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Image, Paragraph, Spacer


PAGE_WIDTH, PAGE_HEIGHT = A4

BLACK = colors.black
LIGHT_GREY = colors.HexColor("#EAEAEA")


def money(value: Any) -> str:
    if value is None:
        value = 0

    return f"{float(value):,.2f}"


def quantity(value: Any) -> str:
    if value is None:
        return "0"

    number = float(value)

    if number.is_integer():
        return str(int(number))

    return f"{number:,.3f}"


def safe_text(
    value: Any,
    default: str = "",
) -> str:
    if value is None:
        return default

    return str(value)


def build_styles() -> dict[str, ParagraphStyle]:
    styles = getSampleStyleSheet()

    return {
        "normal": ParagraphStyle(
            "DocumentNormal",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=9,
            leading=11,
            textColor=BLACK,
        ),
        "small": ParagraphStyle(
            "DocumentSmall",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=7.5,
            leading=9,
            textColor=BLACK,
        ),
        "tiny": ParagraphStyle(
            "DocumentTiny",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=6.5,
            leading=8,
            textColor=BLACK,
        ),
        "bold": ParagraphStyle(
            "DocumentBold",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=9,
            leading=11,
            textColor=BLACK,
        ),
        "heading": ParagraphStyle(
            "DocumentHeading",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=18,
            leading=21,
            alignment=TA_CENTER,
            textColor=BLACK,
        ),
        "company": ParagraphStyle(
            "CompanyHeading",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=17,
            leading=20,
            alignment=TA_CENTER,
            textColor=BLACK,
        ),
        "company_detail": ParagraphStyle(
            "CompanyDetail",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=11,
            leading=13,
            alignment=TA_CENTER,
            textColor=BLACK,
        ),
        "right": ParagraphStyle(
            "DocumentRight",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=9,
            leading=11,
            alignment=TA_RIGHT,
        ),
        "center": ParagraphStyle(
            "DocumentCenter",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=9,
            leading=11,
            alignment=TA_CENTER,
        ),
        "quotation_title": ParagraphStyle(
            "QuotationTitle",
            parent=styles["Normal"],
            fontName="Times-Bold",
            fontSize=16,
            leading=19,
            alignment=TA_LEFT,
        ),
    }


STYLES = build_styles()


def paragraph(
    value: Any,
    style: str = "normal",
) -> Paragraph:
    return Paragraph(
        safe_text(value),
        STYLES[style],
    )


def logo_flowable(
    logo_path: str | None,
    *,
    width: float = 30 * mm,
    height: float = 24 * mm,
):
    if not logo_path:
        return Spacer(width, height)

    path = Path(logo_path)

    if not path.exists() or not path.is_file():
        return Spacer(width, height)

    image = Image(
        str(path),
        width=width,
        height=height,
    )

    image.hAlign = "LEFT"

    return image


def new_buffer() -> BytesIO:
    return BytesIO()
