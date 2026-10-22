
from datetime import datetime, timezone
from io import BytesIO

from pypdf import PdfReader, PdfWriter
from reportlab.pdfgen import canvas


def watermark_pdf(pdf_bytes: bytes, user_id: int) -> bytes:
    """Apply an identifiable watermark to every PDF page."""

    accessed_at = datetime.now(timezone.utc)

    watermark_text = (
        f"UNN E-Library | User ID: {user_id} | "
        f"{accessed_at:%Y-%m-%d %H:%M UTC}"
    )

    reader = PdfReader(BytesIO(pdf_bytes), strict=True)

    if reader.is_encrypted:
        raise ValueError("Encrypted PDFs are not supported.")

    if not reader.pages:
        raise ValueError("The PDF contains no pages.")

    writer = PdfWriter()

    for page in reader.pages:
        width = float(page.mediabox.width)
        height = float(page.mediabox.height)

        overlay_buffer = BytesIO()
        overlay = canvas.Canvas(
            overlay_buffer,
            pagesize=(width, height),
        )

        overlay.saveState()
        overlay.setFont("Helvetica", 9)
        overlay.setFillGray(0.35)
        overlay.drawCentredString(
            width / 2,
            25,
            watermark_text,
        )
        overlay.restoreState()
        overlay.save()

        overlay_buffer.seek(0)
        watermark_page = PdfReader(overlay_buffer).pages[0]

        page.merge_page(watermark_page, over=True)
        writer.add_page(page)

    output = BytesIO()
    writer.write(output)

    return output.getvalue()
