
from unittest.mock import MagicMock, patch

import pytest

from app.services.email_service import send_notification_email


@patch("app.services.email_service.smtplib.SMTP_SSL")
@patch("app.services.email_service.settings")
def test_gmail_uses_secure_ssl(
    mock_settings,
    mock_smtp_ssl,
):
    mock_settings.SMTP_HOST = "smtp.gmail.com"
    mock_settings.SMTP_PORT = 465
    mock_settings.SMTP_USERNAME = "sender@example.com"
    mock_settings.SMTP_PASSWORD = "fake-test-password"
    mock_settings.SMTP_FROM_EMAIL = "sender@example.com"
    mock_settings.SMTP_USE_TLS = False

    smtp = MagicMock()
    mock_smtp_ssl.return_value.__enter__.return_value = smtp

    send_notification_email(
        recipient="student@example.com",
        subject="New Academic Resource",
        body="A new resource is available.",
    )

    
    mock_smtp_ssl.assert_called_once()

    assert mock_smtp_ssl.call_args.args[0] == "smtp.gmail.com"
    assert mock_smtp_ssl.call_args.args[1] == 465


    smtp.login.assert_called_once_with(
        "sender@example.com",
        "fake-test-password",
    )
    smtp.send_message.assert_called_once()

    message = smtp.send_message.call_args.args[0]
    assert message["To"] == "student@example.com"
    assert message["Subject"] == "New Academic Resource"


@patch("app.services.email_service.smtplib.SMTP_SSL")
@patch("app.services.email_service.settings")
def test_gmail_authentication_failure_is_reported(
    mock_settings,
    mock_smtp_ssl,
):
    mock_settings.SMTP_HOST = "smtp.gmail.com"
    mock_settings.SMTP_PORT = 465
    mock_settings.SMTP_USERNAME = "sender@example.com"
    mock_settings.SMTP_PASSWORD = "fake-test-password"
    mock_settings.SMTP_FROM_EMAIL = "sender@example.com"

    smtp = MagicMock()
    smtp.login.side_effect = RuntimeError(
        "Simulated authentication failure"
    )
    mock_smtp_ssl.return_value.__enter__.return_value = smtp

    with pytest.raises(
        RuntimeError,
        match="Simulated authentication failure",
    ):
        send_notification_email(
            recipient="student@example.com",
            subject="Test",
            body="Test message",
        )

    smtp.send_message.assert_not_called()
