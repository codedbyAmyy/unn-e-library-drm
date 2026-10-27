
"""Branded HTML presentation for existing CAS email jobs."""

import re
from html import escape
from urllib.parse import urlparse


def render_password_reset_email(body: str) -> str:
    """Render a reset message without exposing other CAS/academic content."""
    match = re.search(r"https?://[^\s<>\"']+/reset-password\.html\?[^\s<>\"']+", body)
    if not match:
        raise ValueError("Password reset email is missing its reset URL")
    from urllib.parse import urlsplit
    url = match.group(0)
    parsed = urlsplit(url)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        raise ValueError("Invalid password reset URL")
    safe_url = escape(url, quote=True)
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Reset your UNN E-Library password</title></head>
<body style="margin:0;padding:0;background:#f4f1e9;font-family:Arial,Helvetica,sans-serif;color:#263b2f;">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#f4f1e9"><tr><td align="center" style="padding:32px 14px">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="max-width:580px;background:#ffffff;border-radius:12px;overflow:hidden">
<tr><td style="background:#174932;padding:28px 32px"><p style="margin:0;color:#e3d6aa;font-size:11px;letter-spacing:1.5px">UNIVERSITY OF NIGERIA, NSUKKA</p><h1 style="color:#ffffff;margin:10px 0 4px">E-Library</h1><p style="color:#dcebe0;margin:0;font-size:13px">Account Security</p></td></tr>
<tr><td style="padding:32px"><p style="color:#397350;font-size:12px;letter-spacing:1px;font-weight:bold">PASSWORD RESET REQUEST</p><h2 style="color:#174932;font-size:25px;margin:12px 0 18px">Reset your password</h2>
<p style="font-size:15px;line-height:1.7">A password reset was requested for your UNN E-Library account. Click below to choose a new password.</p>
<p style="margin:28px 0"><a href="{safe_url}" style="display:inline-block;background:#00734f;color:#ffffff;text-decoration:none;padding:15px 24px;border-radius:8px;font-weight:bold">Reset Password</a></p>
<p style="font-size:14px;line-height:1.7">This link expires in <strong>20 minutes</strong> and becomes invalid after your password is changed.</p>
<p style="font-size:14px;line-height:1.7">If you did not request this, you can safely ignore this email. Your existing password remains unchanged.</p>
<p style="font-size:12px;color:#64756b;line-height:1.6">If the button does not work, open the link in the plain-text version of this email.</p></td></tr>
<tr><td style="background:#f8f9f5;padding:20px 32px;border-top:1px solid #e4e9df;color:#68766d;font-size:12px">UNN E-Library · Account Security</td></tr></table></td></tr></table></body></html>"""


def render_cas_email(body: str, library_url: str = "") -> str:
    if body.startswith("A password reset was requested for your UNN E-Library account."):
        return render_password_reset_email(body)

    def extract(pattern: str, default: str) -> str:
        match = re.search(pattern, body, re.MULTILINE)
        return escape(match.group(1).strip()) if match else default

    recipient = extract(r"^Hello (.+?),\s*$", "Library member")
    title = extract(r"^Title:\s*(.+)$", "New academic resource")
    resource_id = extract(r"^Resource ID:\s*(.+)$", "")

    parsed = urlparse(library_url)
    safe_url = (
        escape(library_url.rstrip("/") + "/index.html#library", quote=True)
        if parsed.scheme in ("http", "https") and parsed.netloc
        else ""
    )

    button = (
        f'<a href="{safe_url}" '
        'style="display:inline-block;background:#174932;'
        'color:#ffffff;text-decoration:none;padding:14px 24px;'
        'border-radius:7px;font-weight:bold;">'
        'Explore the E-Library</a>'
        if safe_url
        else '<p style="color:#47564d;">Sign in to your E-Library '
             'account to explore this resource.</p>'
    )

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>UNN E-Library Resource Alert</title>
</head>
<body style="margin:0;padding:0;background:#f4f1e9;
font-family:Arial,Helvetica,sans-serif;color:#263b2f;">
<table role="presentation" cellpadding="0" cellspacing="0"
width="100%" style="background:#f4f1e9;">
<tr><td align="center" style="padding:32px 14px;">
<table role="presentation" cellpadding="0" cellspacing="0"
width="100%" style="max-width:580px;background:#ffffff;
border-radius:12px;overflow:hidden;">
<tr><td style="background:#174932;padding:28px 32px;">
<p style="margin:0;color:#e3d6aa;font-size:11px;
letter-spacing:1.5px;">UNIVERSITY OF NIGERIA, NSUKKA</p>
<h1 style="margin:10px 0 4px;color:#ffffff;font-size:28px;">
E-Library</h1>
<p style="margin:0;color:#dcebe0;font-size:13px;">
Current Awareness Service</p>
</td></tr>
<tr><td style="padding:32px;">
<p style="font-size:12px;letter-spacing:1px;
color:#397350;font-weight:bold;">NEW RESOURCE ALERT</p>
<h2 style="font-size:25px;line-height:1.3;
color:#174932;margin:12px 0 20px;">
Something new for your studies.</h2>
<p style="font-size:15px;line-height:1.7;">
Hello {recipient},</p>
<p style="font-size:15px;line-height:1.7;">
A new academic resource relevant to your studies
has been published in the UNN E-Library.</p>
<table role="presentation" width="100%" cellpadding="0"
cellspacing="0" style="margin:22px 0;background:#f2f5ef;
border-left:4px solid #397350;">
<tr><td style="padding:20px;">
<p style="margin:0 0 8px;font-size:11px;color:#617568;">
ACADEMIC RESOURCE</p>
<p style="margin:0;font-size:19px;font-weight:bold;
line-height:1.4;color:#174932;">{title}</p>
<p style="margin:9px 0 0;font-size:12px;color:#657267;">
Resource ID: {resource_id}</p>
</td></tr>
</table>
<p style="margin:26px 0;">{button}</p>
<p style="font-size:13px;line-height:1.7;color:#59685f;">
Continue exploring academic resources through your
secure university library account.</p>
</td></tr>
<tr><td style="background:#f8f9f5;padding:20px 32px;
border-top:1px solid #e4e9df;">
<p style="margin:0;font-size:12px;line-height:1.7;
color:#68766d;">UNN E-Library · Current Awareness Service</p>
<p style="margin:8px 0 0;font-size:12px;line-height:1.7;
color:#68766d;">Manage email and in-app notification preferences
from your E-Library account.</p>
</td></tr>
</table>
</td></tr>
</table>
</body>
</html>"""
