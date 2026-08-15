from __future__ import annotations

from io import BytesIO
from pathlib import Path
from typing import Any

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.graphics.barcode import code128 as _code128
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


# ============================================================
# BANDARA COOL WORLD
# UNIFIED BRANDED DOCUMENT SYSTEM - PHASE 1
# ============================================================

from pathlib import Path as _BrandPath

from reportlab.lib import colors as _brand_colors
from reportlab.lib.enums import TA_CENTER as _TA_CENTER
from reportlab.lib.enums import TA_RIGHT as _TA_RIGHT
from reportlab.lib.styles import ParagraphStyle as _ParagraphStyle
from reportlab.lib.units import mm as _mm
from reportlab.platypus import KeepTogether as _KeepTogether
from reportlab.platypus import Paragraph as _Paragraph
from reportlab.platypus import Spacer as _Spacer
from reportlab.platypus import Table as _Table
from reportlab.platypus import TableStyle as _TableStyle


BANDARA_BRAND_MARKER = (
    "UNIFIED_BRANDED_PDF_PHASE1_V1"
)

BANDARA_COMPANY_NAME = (
    "BANDARA COOL WORLD"
)

BANDARA_ADDRESS = (
    "A/3, Public Shopping Complex, Kekirawa"
)

BANDARA_PHONE_LINE = (
    "077 530 2676 | 074 013 9090"
)

BANDARA_EMAIL = (
    "bandaracoolworld@gmail.com"
)

BANDARA_BRANDS = (
    "SAMSUNG",
    "Haier",
    "KANVOX",
    "TCL",
    "aiwa",
    "LMG",
)


# REAL_BANDARA_LOGO_PHASE2_V1
BANDARA_OFFICIAL_LOGO_PATH = (
    _BrandPath(__file__).resolve().parents[2]
    / "static"
    / "branding"
    / "bandara-cool-world-logo.png"
)

BANDARA_BLUE = _brand_colors.HexColor(
    "#173F73"
)

# Header-only bright Bandara Cool World blue.
# Do not use this for the footer.
BANDARA_HEADER_BLUE = _brand_colors.HexColor(
    "#00AFF3"
)

BANDARA_RED = _brand_colors.HexColor(
    "#D62828"
)

BANDARA_LIGHT_BLUE = _brand_colors.HexColor(
    "#EEF4FA"
)

BANDARA_BORDER = _brand_colors.HexColor(
    "#CBD5E1"
)

BANDARA_TEXT = _brand_colors.HexColor(
    "#1F2937"
)

BANDARA_MUTED = _brand_colors.HexColor(
    "#64748B"
)



# REAL_BANDARA_VISUAL_ASSETS_PHASE3_V2
BANDARA_FOOTER_BRANDS_PATH = (
    _BrandPath(__file__).resolve().parents[2]
    / "static"
    / "branding"
    / "footer-brand-logos.png"
)


def bandara_image_flowable(
    image_path: str | _BrandPath,
    *,
    max_width: float,
    max_height: float,
):
    """
    Create a ReportLab Image while preserving its native
    aspect ratio.

    This intentionally does not depend on the legacy
    logo_flowable() function signature.
    """

    image = Image(
        str(image_path)
    )

    native_width = float(
        image.drawWidth
    )
    native_height = float(
        image.drawHeight
    )

    if (
        native_width <= 0
        or native_height <= 0
    ):
        raise ValueError(
            "Invalid brand image dimensions"
        )

    scale = min(
        float(max_width)
        / native_width,
        float(max_height)
        / native_height,
    )

    image.drawWidth = (
        native_width * scale
    )

    image.drawHeight = (
        native_height * scale
    )

    return image


def bandara_brand_logo_path(
    configured_logo_path: str | None = None,
) -> str | None:
    """
    Resolve a usable Bandara Cool World header logo.

    Priority:
      1. valid configured company logo image
      2. official backend brand asset
      3. None so emergency BCW fallback remains possible
    """

    candidates: list[_BrandPath] = []

    if configured_logo_path:
        candidate = _BrandPath(
            str(configured_logo_path)
        ).expanduser()

        candidates.extend([
            candidate,
            _BrandPath.cwd() / candidate,
            _BrandPath.cwd().parent / candidate,
        ])

    candidates.append(
        BANDARA_OFFICIAL_LOGO_PATH
    )

    seen: set[str] = set()

    for value in candidates:
        try:
            resolved = value.resolve()
            key = str(resolved)

            if key in seen:
                continue

            seen.add(key)

            if (
                resolved.is_file()
                and resolved.suffix.lower()
                in {
                    ".png",
                    ".jpg",
                    ".jpeg",
                    ".webp",
                }
            ):
                return key

        except (
            OSError,
            RuntimeError,
        ):
            continue

    return None





# PDF_HEADER_POLISH_PHASE5_1_V1
def bandara_document_header(
    *,
    document_title: str,
    document_number: str | None = None,
    configured_logo_path: str | None = None,
) -> list:
    """
    Final shared A4 Bandara Cool World header.

    PDF_HEADER_BARCODE_PHASE5_V1

    Layout goals:
    - real logo at left
    - company identity centered on the physical page
    - document title centered in the right zone
    - document number and Code128 barcode below title
    - proportional logo rendering
    """

    logo_path = bandara_brand_logo_path(
        configured_logo_path
    )

    logo = None

    if logo_path:
        try:
            logo = bandara_image_flowable(
                logo_path,
                max_width=24 * _mm,
                max_height=30 * _mm,
            )
        except Exception:
            logo = None

    if logo is None:
        logo = _Table(
            [[
                _Paragraph(
                    "<b>BCW</b>",
                    _ParagraphStyle(
                        "BandaraLogoEmergencyFallback",
                        fontName="Helvetica-Bold",
                        fontSize=15,
                        leading=17,
                        alignment=_TA_CENTER,
                        textColor=BANDARA_BLUE,
                    ),
                )
            ]],
            colWidths=[
                24 * _mm,
            ],
            rowHeights=[
                24 * _mm,
            ],
        )

        logo.setStyle(
            _TableStyle([
                (
                    "BOX",
                    (0, 0),
                    (-1, -1),
                    1.2,
                    BANDARA_BLUE,
                ),
                (
                    "VALIGN",
                    (0, 0),
                    (-1, -1),
                    "MIDDLE",
                ),
            ])
        )

    company = _Paragraph(
        (
            "<font size='18'>"
            "<b>"
            "<font color='#000000'>BANDARA</font>"
            " "
            "<font color='#00AFF3'>COOL</font>"
            " "
            "<font color='#000000'>WORLD</font>"
            "</b>"
            "</font>"
            "<br/>"
            "<font color='#475569' size='8.5'>"
            f"{BANDARA_ADDRESS}"
            "</font>"
            "<br/>"
            "<font color='#475569' size='8.5'>"
            f"{BANDARA_PHONE_LINE}"
            "</font>"
        ),
        _ParagraphStyle(
            "BandaraCompanyHeaderPhase5",
            fontName="Helvetica",
            fontSize=9,
            leading=12,
            alignment=_TA_CENTER,
            textColor=BANDARA_TEXT,
        ),
    )

    # PDF_HEADER_POLISH_PHASE5_2_V1
    #
    # The right header zone is intentionally kept at
    # 42 mm so the 42 / 96 / 42 physical-page centering
    # contract remains unchanged.
    #
    # PAYMENT RECEIPT is slightly longer than the other
    # document titles. Give only that title a compact
    # display size so it remains on one line without
    # moving the company identity or barcode geometry.
    #
    normalized_document_title = (
        str(document_title)
        .strip()
        .upper()
    )

    document_title_size = (
        10.5
        if normalized_document_title
        == "PAYMENT RECEIPT"
        else 13
    )

    title = _Paragraph(
        (
            "<font color='#D62828' "
            f"size='{document_title_size}'>"
            f"<b>{normalized_document_title}</b>"
            "</font>"
        ),
        _ParagraphStyle(
            "BandaraDocumentTitlePhase5",
            fontName="Helvetica-Bold",
            fontSize=document_title_size,
            leading=11.2,
            alignment=_TA_CENTER,
            textColor=BANDARA_TEXT,
            splitLongWords=False,
        ),
    )

    number_text = (
        str(document_number).strip()
        if document_number
        else ""
    )

    number_flowable = _Paragraph(
        (
            "<font color='#475569' size='8'>"
            f"<b>{number_text}</b>"
            "</font>"
        )
        if number_text
        else "",
        _ParagraphStyle(
            "BandaraDocumentNumberPhase5",
            fontName="Helvetica",
            fontSize=8,
            leading=10,
            alignment=_TA_CENTER,
            textColor=BANDARA_TEXT,
        ),
    )

    right_story = [
        title,
    ]

    if number_text:
        right_story.extend([
            _Spacer(
                1,
                0.7 * _mm,
            ),
            number_flowable,
            _Spacer(
                1,
                0.7 * _mm,
            ),
        ])

        try:
            barcode = _code128.Code128(
                number_text,
                barHeight=7.0 * _mm,
                barWidth=0.27 * _mm,
                humanReadable=False,
                quiet=True,
            )

            barcode_table = _Table(
                [[barcode]],
                colWidths=[
                    50 * _mm,
                ],
            )

            barcode_table.setStyle(
                _TableStyle([
                    (
                        "ALIGN",
                        (0, 0),
                        (-1, -1),
                        "CENTER",
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
                        0,
                    ),
                    (
                        "RIGHTPADDING",
                        (0, 0),
                        (-1, -1),
                        0,
                    ),
                    (
                        "TOPPADDING",
                        (0, 0),
                        (-1, -1),
                        0,
                    ),
                    (
                        "BOTTOMPADDING",
                        (0, 0),
                        (-1, -1),
                        0,
                    ),
                ])
            )

            right_story.append(
                barcode_table
            )

        except Exception:
            # Document generation must never fail only
            # because barcode rendering failed.
            pass

    #
    # A4 content width used by the branded document
    # templates is 180 mm.
    #
    # Symmetrical 42 / 96 / 42 columns make the
    # company column center exactly 90 mm from either
    # edge of the header table. Therefore the company
    # identity is physically centered.
    #
    left_width = 42 * _mm
    center_width = 96 * _mm
    right_width = 42 * _mm

    right_block = _Table(
        [[right_story]],
        colWidths=[
            right_width,
        ],
    )

    right_block.setStyle(
        _TableStyle([
            (
                "ALIGN",
                (0, 0),
                (-1, -1),
                "CENTER",
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
                0,
            ),
            (
                "RIGHTPADDING",
                (0, 0),
                (-1, -1),
                0,
            ),
            (
                "TOPPADDING",
                (0, 0),
                (-1, -1),
                0,
            ),
            (
                "BOTTOMPADDING",
                (0, 0),
                (-1, -1),
                0,
            ),
        ])
    )

    table = _Table(
        [[
            logo,
            company,
            right_block,
        ]],
        colWidths=[
            left_width,
            center_width,
            right_width,
        ],
    )

    table.setStyle(
        _TableStyle([
            (
                "VALIGN",
                (0, 0),
                (-1, -1),
                "MIDDLE",
            ),
            (
                "ALIGN",
                (0, 0),
                (0, 0),
                "LEFT",
            ),
            (
                "ALIGN",
                (1, 0),
                (1, 0),
                "CENTER",
            ),
            (
                "ALIGN",
                (2, 0),
                (2, 0),
                "CENTER",
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
                3,
            ),
        ])
    )

    divider = _Table(
        [[""]],
        colWidths=[
            180 * _mm,
        ],
        rowHeights=[
            1.6 * _mm,
        ],
    )

    divider.setStyle(
        _TableStyle([
            (
                "BACKGROUND",
                (0, 0),
                (-1, -1),
                BANDARA_HEADER_BLUE,
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
            (
                "TOPPADDING",
                (0, 0),
                (-1, -1),
                0,
            ),
            (
                "BOTTOMPADDING",
                (0, 0),
                (-1, -1),
                0,
            ),
        ])
    )

    return [
        table,
        _Spacer(
            1,
            1.5 * _mm,
        ),
        divider,
        _Spacer(
            1,
            4 * _mm,
        ),
    ]



def bandara_section_title(
    title: str,
):
    return _Table(
        [[
            _Paragraph(
                (
                    "<font color='#173F73'>"
                    f"<b>{title.upper()}</b>"
                    "</font>"
                ),
                _ParagraphStyle(
                    "BandaraSectionTitle",
                    fontName="Helvetica-Bold",
                    fontSize=9,
                    leading=11,
                    textColor=BANDARA_BLUE,
                ),
            )
        ]],
        colWidths=[
            180 * _mm,
        ],
        style=[
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
                BANDARA_BLUE,
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
        ],
    )


def bandara_info_table(
    rows: list[
        tuple[
            str,
            object,
            str,
            object,
        ]
    ],
):
    data = []

    label_style = _ParagraphStyle(
        "BandaraInfoLabel",
        fontName="Helvetica-Bold",
        fontSize=7.5,
        leading=10,
        textColor=BANDARA_MUTED,
    )

    value_style = _ParagraphStyle(
        "BandaraInfoValue",
        fontName="Helvetica",
        fontSize=8.5,
        leading=10,
        textColor=BANDARA_TEXT,
    )

    for (
        left_label,
        left_value,
        right_label,
        right_value,
    ) in rows:
        data.append([
            _Paragraph(
                str(left_label),
                label_style,
            ),
            _Paragraph(
                str(
                    left_value
                    if left_value
                    not in (
                        None,
                        "",
                    )
                    else "-"
                ),
                value_style,
            ),
            _Paragraph(
                str(right_label),
                label_style,
            ),
            _Paragraph(
                str(
                    right_value
                    if right_value
                    not in (
                        None,
                        "",
                    )
                    else "-"
                ),
                value_style,
            ),
        ])

    table = _Table(
        data,
        colWidths=[
            27 * _mm,
            63 * _mm,
            27 * _mm,
            63 * _mm,
        ],
    )

    table.setStyle(
        _TableStyle([
            (
                "BOX",
                (0, 0),
                (-1, -1),
                0.6,
                BANDARA_BORDER,
            ),
            (
                "INNERGRID",
                (0, 0),
                (-1, -1),
                0.35,
                BANDARA_BORDER,
            ),
            (
                "BACKGROUND",
                (0, 0),
                (0, -1),
                _brand_colors.HexColor(
                    "#F8FAFC"
                ),
            ),
            (
                "BACKGROUND",
                (2, 0),
                (2, -1),
                _brand_colors.HexColor(
                    "#F8FAFC"
                ),
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
        ])
    )

    return table


def bandara_footer_story() -> list:
    """
    Final shared footer using the supplied real horizontal
    brand-logo strip and Bandara Cool World contact bar.
    """

    brands = None

    try:
        footer_path = (
            BANDARA_FOOTER_BRANDS_PATH.resolve()
        )

        if footer_path.is_file():
            brands = bandara_image_flowable(
                footer_path,
                max_width=174 * _mm,
                max_height=13.5 * _mm,
            )

    except Exception:
        brands = None

    if brands is None:
        brands = _Table(
            [[
                _Paragraph(
                    (
                        "<font color='#173F73'>"
                        f"<b>{brand}</b>"
                        "</font>"
                    ),
                    _ParagraphStyle(
                        f"BandaraBrandFallback{index}",
                        fontName="Helvetica-Bold",
                        fontSize=8,
                        leading=10,
                        alignment=_TA_CENTER,
                    ),
                )
                for index, brand
                in enumerate(
                    BANDARA_BRANDS
                )
            ]],
            colWidths=[
                30 * _mm,
            ] * 6,
        )

    holder = _Table(
        [[brands]],
        colWidths=[
            180 * _mm,
        ],
    )

    holder.setStyle(
        _TableStyle([
            (
                "ALIGN",
                (0, 0),
                (-1, -1),
                "CENTER",
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
                0,
            ),
            (
                "RIGHTPADDING",
                (0, 0),
                (-1, -1),
                0,
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
                "LINEABOVE",
                (0, 0),
                (-1, -1),
                0.45,
                BANDARA_BORDER,
            ),
            (
                "LINEBELOW",
                (0, 0),
                (-1, -1),
                0.45,
                BANDARA_BORDER,
            ),
        ])
    )

    contact = _Table(
        [[
            _Paragraph(
                (
                    "<font color='white'>"
                    f"<b>{BANDARA_ADDRESS}</b>"
                    " &nbsp;&nbsp; | &nbsp;&nbsp; "
                    f"{BANDARA_PHONE_LINE}"
                    " &nbsp;&nbsp; | &nbsp;&nbsp; "
                    f"{BANDARA_EMAIL}"
                    "</font>"
                ),
                _ParagraphStyle(
                    "BandaraBottomContactFinal",
                    fontName="Helvetica",
                    fontSize=7.2,
                    leading=9,
                    alignment=_TA_CENTER,
                ),
            )
        ]],
        colWidths=[
            180 * _mm,
        ],
    )

    contact.setStyle(
        _TableStyle([
            (
                "BACKGROUND",
                (0, 0),
                (-1, -1),
                BANDARA_BLUE,
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
        ])
    )

    return [
        _Spacer(
            1,
            5 * _mm,
        ),
        _KeepTogether([
            holder,
            _Spacer(
                1,
                1.5 * _mm,
            ),
            contact,
        ]),
    ]




def bandara_page_footer(
    canvas,
    doc,
) -> None:
    """
    Small repeatable page-number footer for multi-page PDFs.
    """

    canvas.saveState()

    width, _height = A4

    canvas.setStrokeColor(
        BANDARA_BORDER
    )
    canvas.setLineWidth(
        0.4
    )

    canvas.line(
        15 * _mm,
        11 * _mm,
        width - 15 * _mm,
        11 * _mm,
    )

    canvas.setFillColor(
        BANDARA_MUTED
    )
    canvas.setFont(
        "Helvetica",
        6.5,
    )

    canvas.drawString(
        15 * _mm,
        7.2 * _mm,
        (
            "Bandara Cool World"
            " - System Generated Document"
        ),
    )

    canvas.drawRightString(
        width - 15 * _mm,
        7.2 * _mm,
        f"Page {doc.page}",
    )

    canvas.restoreState()
