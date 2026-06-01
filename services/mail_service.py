"""
Mail service — ONLY Brevo HTTP API (port 443).
Works on Render free tier. No SMTP, no Flask-Mail.

Required env vars:
  BREVO_API_KEY  — from Brevo dashboard → API Keys
  MAIL_FROM      — your verified sender email in Brevo
"""
import os
import requests

BREVO_API_URL = "https://api.brevo.com/v3/smtp/email"
SENDER_NAME   = "QUOKKA AI"


def _send(to_email: str, to_name: str, subject: str, html_body: str) -> None:
    api_key   = os.environ.get("BREVO_API_KEY", "").strip()
    from_mail = os.environ.get("MAIL_FROM", "").strip()

    if not api_key:
        raise RuntimeError("[MAIL] BREVO_API_KEY is not set")
    if not from_mail:
        raise RuntimeError("[MAIL] MAIL_FROM is not set — add your verified Brevo sender email")

    payload = {
        "sender": {"name": SENDER_NAME, "email": from_mail},
        "to": [{"email": to_email, "name": to_name or to_email}],
        "subject": subject,
        "htmlContent": html_body,
    }

    print(f"[MAIL] → {to_email}  subject='{subject}'", flush=True)

    resp = requests.post(
        BREVO_API_URL,
        headers={
            "api-key": api_key,
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        json=payload,
        timeout=20,
    )

    print(f"[MAIL] Brevo {resp.status_code}: {resp.text[:200]}", flush=True)

    if resp.status_code not in (200, 201):
        raise RuntimeError(f"Brevo API error {resp.status_code}: {resp.text}")


# ── HTML wrapper ──────────────────────────────────────────────────────────────

def _wrap(body: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>QUOKKA</title></head>
<body style="margin:0;padding:0;background:#0d0d0d;font-family:Inter,Arial,sans-serif;">
<table width="100%" cellspacing="0" cellpadding="0" style="background:#0d0d0d;">
  <tr><td align="center" style="padding:40px 16px;">
    <table width="100%" cellspacing="0" cellpadding="0"
           style="max-width:580px;background:#141414;border:1px solid #27272a;border-radius:16px;">
      <tr><td style="padding:32px 28px;">
        <div style="font-size:26px;font-weight:800;color:#d9f95d;letter-spacing:2px;margin-bottom:24px;">QUOKKA</div>
        {body}
        <hr style="border:none;border-top:1px solid #27272a;margin:28px 0 16px;">
        <p style="color:#52525b;font-size:12px;margin:0;">
          You received this email because you have a QUOKKA account.
        </p>
      </td></tr>
    </table>
  </td></tr>
</table>
</body></html>"""


# ── Public functions ──────────────────────────────────────────────────────────

def send_otp_email(email: str, name: str, otp: str) -> None:
    body = f"""
    <p style="color:#fff;font-size:16px;margin:0 0 12px;">Hi <strong>{name}</strong>,</p>
    <p style="color:#a1a1aa;font-size:15px;margin:0 0 24px;">
        Here is your one-time verification code for QUOKKA:
    </p>
    <div style="background:#1a1a1a;border:1px solid #27272a;border-radius:12px;
                padding:28px;text-align:center;margin:0 0 24px;">
        <span style="color:#d9f95d;font-size:40px;font-weight:800;letter-spacing:12px;
                     font-family:monospace;">{otp}</span>
    </div>
    <p style="color:#a1a1aa;font-size:14px;margin:0 0 8px;">
        ⏱ This code expires in <strong>10 minutes</strong>.
    </p>
    <p style="color:#71717a;font-size:13px;margin:0;">
        If you didn't create a QUOKKA account, you can safely ignore this email.
    </p>"""
    _send(email, name, "Your QUOKKA verification code", _wrap(body))


def send_reset_email(email: str, name: str, reset_link: str) -> None:
    body = f"""
    <p style="color:#fff;font-size:16px;margin:0 0 12px;">Hi <strong>{name}</strong>,</p>
    <p style="color:#a1a1aa;font-size:15px;margin:0 0 28px;">
        We received a request to reset your QUOKKA password. Click the button below:
    </p>
    <div style="text-align:center;margin:0 0 28px;">
        <a href="{reset_link}"
           style="display:inline-block;background:#d9f95d;color:#000;padding:14px 36px;
                  border-radius:50px;font-weight:700;font-size:15px;text-decoration:none;">
            Reset Password
        </a>
    </div>
    <p style="color:#a1a1aa;font-size:14px;margin:0 0 8px;">
        ⏱ This link expires in <strong>15 minutes</strong>.
    </p>
    <p style="color:#71717a;font-size:13px;margin:0;">
        If you didn't request a password reset, ignore this email — your account is safe.
    </p>"""
    _send(email, name, "Reset your QUOKKA password", _wrap(body))


def send_welcome_email(email: str, name: str) -> None:
    body = f"""
    <p style="color:#fff;font-size:18px;font-weight:700;margin:0 0 12px;">
        Welcome to QUOKKA, {name}! 🎉
    </p>
    <p style="color:#a1a1aa;font-size:15px;margin:0 0 12px;">
        Your email has been verified and your account is ready to use.
    </p>
    <p style="color:#a1a1aa;font-size:15px;margin:0;">
        Start a conversation with QUOKKA AI and experience the power of LLaMA 3.1 right in your browser.
    </p>"""
    _send(email, name, "Welcome to QUOKKA 🚀", _wrap(body))