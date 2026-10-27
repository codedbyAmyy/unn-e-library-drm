from unittest.mock import patch
from app.services.email_service import send_notification_email


def test_resend_transport_does_not_connect_to_smtp():
    with patch('app.services.email_service.settings') as cfg, \
         patch('app.services.email_service.send_via_resend') as resend, \
         patch('app.services.email_service.smtplib.SMTP') as smtp, \
         patch('app.services.email_service.smtplib.SMTP_SSL') as smtp_ssl:
        cfg.EMAIL_TRANSPORT = 'resend'
        send_notification_email('student@example.com', 'Test', 'Hello')
        resend.assert_called_once_with('student@example.com', 'Test', 'Hello')
        smtp.assert_not_called()
        smtp_ssl.assert_not_called()
