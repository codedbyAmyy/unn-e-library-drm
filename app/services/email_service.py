
"""SMTP delivery for UNN E-Library notifications."""

import smtplib
import ssl

from email.message import EmailMessage

from app.config import settings


def send_notification_email(
    recipient: str,
    subject: str,
    body: str,
) -> None:
    """Send an email securely using Gmail SMTP."""

    if not all((
        settings.SMTP_HOST,
        settings.SMTP_FROM_EMAIL,
    )):
        raise RuntimeError("SMTP delivery is not configured.")

    message = EmailMessage()
    message["From"] = settings.SMTP_FROM_EMAIL
    message["To"] = recipient
    message["Subject"] = subject
    message.set_content(body)

    tls_context = ssl.create_default_context()

    if settings.SMTP_PORT == 465:
        smtp_connection = smtplib.SMTP_SSL(
            settings.SMTP_HOST,
            settings.SMTP_PORT,
            timeout=20,
            context=tls_context,
        )

    else:
        if not settings.SMTP_USE_TLS:
            raise RuntimeError(
                "SMTP encryption must be enabled."
            )

        smtp_connection = smtplib.SMTP(
            settings.SMTP_HOST,
            settings.SMTP_PORT,
            timeout=20,
        )

    with smtp_connection as smtp:
        smtp.ehlo()

        if settings.SMTP_PORT != 465:
            smtp.starttls(context=tls_context)
            smtp.ehlo()

        if settings.SMTP_USERNAME:
            if not settings.SMTP_PASSWORD:
                raise RuntimeError(
                    "SMTP password is not configured."
                )

            smtp.login(
                settings.SMTP_USERNAME,
                settings.SMTP_PASSWORD,
            )

        smtp.send_message(message)
