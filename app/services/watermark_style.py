"""Soft, visible-on-scans watermark painter for the protected PDF overlay.

Designed for existing reportlab.Canvas watermark generation. This draws into
an overlay that is merged ABOVE a PDF page: do not merge beneath opaque scans.
"""
from reportlab.pdfbase.pdfmetrics import stringWidth


def paint_personal_watermark(canvas, width, height, full_name, matric_number):
    """Paint a gentle 2-line diagonal personalized stamp on the current page.

    Requires a reportlab Canvas with transparency support; width/height in points.
    The caller is responsible for saving the overlay and merging it into each page.
    """
    name = " ".join(str(full_name or "").split()) or "AUTHORIZED READER"
    matric = " ".join(str(matric_number or "").split()) or "UNN E-LIBRARY"

    canvas.saveState()
    # Muted soft sage-green. Alpha is intentionally low for scanned PDF pages.
    canvas.setFillColorRGB(0.08, 0.36, 0.26)
    canvas.setFillAlpha(0.30)
    canvas.translate(width / 2, height / 2)
    canvas.rotate(35)

    longest = max(stringWidth(name, "Helvetica-Bold", 1),
                  stringWidth(matric, "Helvetica", 1))
    max_text_width = max(140, (width ** 2 + height ** 2) ** 0.5 * 0.73)
    font_size = min(62.0, max(22.0, max_text_width / max(longest, 1)))
    canvas.setFont("Helvetica-Bold", font_size)
    canvas.drawCentredString(0, font_size * 0.13, name)
    canvas.setFont("Helvetica", font_size * 0.64)
    canvas.drawCentredString(0, -font_size * 0.80, matric)
    canvas.restoreState()
