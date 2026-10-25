from datetime import datetime, timezone
from io import BytesIO

from pypdf import PdfReader, PdfWriter
from reportlab.pdfgen import canvas

from app.services.watermark_style import paint_personal_watermark


def watermark_pdf(
    pdf_bytes: bytes,
    user_id: int,
    full_name: str,
    matric_number: str | None = None,
    staff_id: str | None = None,
) -> bytes:
    """Apply a subtle personalized watermark to every PDF page."""
    accessed_at = datetime.now(timezone.utc)

    name = full_name.strip() or f"USER {user_id}"
    identifier = (
        matric_number
        or staff_id
        or f"USER ID: {user_id}"
    )

    # These are displayed prominently across the page.
    name_text = name.upper()
    identifier_text = identifier.upper()

    # Secondary identification details.
    footer_text = (
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
            pageCompression=1,
        )

        paint_personal_watermark(
            overlay,
            width,
            height,
            name_text,
            identifier_text,
        )

        # Smaller secondary information near the bottom.
        overlay.saveState()
        overlay.setFillAlpha(0.55)
        overlay.setFillColorRGB(0.25, 0.25, 0.25)
        overlay.setFont("Helvetica", 7)

        overlay.drawCentredString(
            width / 2,
            20,
            footer_text,
        )

        overlay.restoreState()
        overlay.save()

        overlay_buffer.seek(0)
        watermark_page = PdfReader(
            overlay_buffer
        ).pages[0]

        page.merge_page(
            watermark_page,
            over=True,
        )

        # Explicitly include the modified page.
        writer.add_page(page)

    output = BytesIO()
    writer.write(output)

    return output.getvalue()
