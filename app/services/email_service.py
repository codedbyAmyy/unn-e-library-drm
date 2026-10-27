"""SMTP delivery for UNN E-Library notifications."""
import smtplib
import ssl
import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from email.message import EmailMessage

from app.services.cas_email_template import render_cas_email
from app.config import settings


def send_via_resend(
    recipient: str,
    subject: str,
    body: str,
) -> None:
    """Send one CAS notification using Resend's HTTPS API."""

    api_key = settings.RESEND_API_KEY
    sender = settings.RESEND_FROM_EMAIL

    if not isinstance(api_key, str) or not api_key.strip():
        raise RuntimeError("RESEND_API_KEY is not configured.")

    if not isinstance(sender, str) or not sender.strip():
        raise RuntimeError("RESEND_FROM_EMAIL is not configured.")

    frontend_url = settings.FRONTEND_PUBLIC_URL
    if not isinstance(frontend_url, str):
        frontend_url = ""

    payload = {
        "from": sender,
        "to": [recipient],
        "subject": subject,
        "text": body,
        "html": render_cas_email(body, frontend_url),
    }

    request = Request(
        url="https://api.resend.com/emails",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "User-Agent": "UNN-ELibrary/1.0",
        },
        method="POST",
    )

    try:
        with urlopen(request, timeout=20) as response:
            result = json.loads(response.read().decode("utf-8"))

            if response.status != 200 or not result.get("id"):
                raise RuntimeError(
                    "Resend did not confirm email acceptance."
                )

    except HTTPError as exc:
        # Do not print response bodies or authorization headers:
        # they may contain private configuration details.
        raise RuntimeError(
            f"Resend rejected the request (HTTP {exc.code})."
        ) from None

    except URLError as exc:
        raise RuntimeError(
            "Could not connect to Resend over HTTPS."
        ) from None


def send_notification_email(recipient: str, subject: str, body: str) -> None:
    """Use Resend HTTPS when configured; otherwise preserve original SMTP."""
    transport = getattr(settings, "EMAIL_TRANSPORT", "smtp")
    if isinstance(transport, str) and transport.strip().lower() == "resend":
        send_via_resend(recipient, subject, body)
        return

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
    
    
    frontend_url = getattr(settings, "FRONTEND_PUBLIC_URL", "")
    if not isinstance(frontend_url, str):
        frontend_url = ""
    message.add_alternative(render_cas_email(body, frontend_url), subtype="html")


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
