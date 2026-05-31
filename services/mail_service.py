import os
import requests


BREVO_API_URL = "https://api.brevo.com/v3/smtp/email"
SENDER_NAME = "QUOKKA AI"


def _get_sender_email():
    return os.environ.get("MAIL_USERNAME", "brcvarma11227@gmail.com")


def _get_api_key():
    return os.environ.get("BREVO_API_KEY", "")


def _base_wrapper(body_content):
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>QUOKKA</title>
</head>
<body style="margin:0;padding:0;background-color:#0d0d0d;font-family:Inter,Arial,sans-serif;">
  <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background-color:#0d0d0d;">
    <tr>
      <td align="center" style="padding:40px 16px;">
        <table role="presentation" width="100%" cellspacing="0" cellpadding="0"
               style="max-width:600px;background-color:#141414;border:1px solid #27272a;border-radius:18px;">
          <tr>
            <td style="padding:32px 28px;">
              <div style="font-size:28px;font-weight:700;color:#d9f95d;letter-spacing:2px;margin-bottom:8px;">QUOKKA</div>
              {body_content}
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""


def _send_via_api(to_email, to_name, subject, html_body):
    """
    Send email via Brevo HTTP API (port 443).
    This works on Render free tier where SMTP port 587 is blocked.
    """
    api_key = _get_api_key()
    sender_email = _get_sender_email()

    if not api_key:
        raise RuntimeError("BREVO_API_KEY environment variable is not set")

    payload = {
        "sender": {"name": SENDER_NAME, "email": sender_email},
        "to": [{"email": to_email, "name": to_name}],
        "subject": subject,
        "htmlContent": html_body
    }

    print(f"[MAIL] Sending '{subject}' to {to_email} via Brevo API", flush=True)

    response = requests.post(
        BREVO_API_URL,
        headers={
            "api-key": api_key,
            "Content-Type": "application/json",
            "Accept": "application/json"
        },
        json=payload,
        timeout=15
    )

    print(f"[MAIL] Brevo API response: {response.status_code} — {response.text}", flush=True)

    if response.status_code not in (200, 201):
        raise RuntimeError(f"Brevo API error {response.status_code}: {response.text}")

    return response


def send_otp_email(email, name, otp):
    body = f"""
        <p style="color:#ffffff;font-size:16px;margin:0 0 16px;">Hi {name},</p>
        <p style="color:#a1a1aa;font-size:15px;line-height:1.6;margin:0 0 24px;">
            Use this code to verify your QUOKKA account:
        </p>
        <div style="background:#1f1f1f;border:1px solid #27272a;border-radius:12px;
                    padding:24px;text-align:center;margin:0 0 24px;">
            <span style="color:#d9f95d;font-size:36px;font-weight:700;letter-spacing:10px;">{otp}</span>
        </div>
        <p style="color:#a1a1aa;font-size:14px;margin:0 0 8px;">This code expires in 10 minutes.</p>
        <p style="color:#71717a;font-size:13px;margin:0;">If you didn't request this, ignore this email.</p>
    """
    html = _base_wrapper(body)
    _send_via_api(email, name, "Verify your QUOKKA account", html)


def send_reset_email(email, name, reset_link):
    body = f"""
        <p style="color:#ffffff;font-size:16px;margin:0 0 16px;">Hi {name},</p>
        <p style="color:#a1a1aa;font-size:15px;line-height:1.6;margin:0 0 24px;">
            Click the button below to reset your QUOKKA password:
        </p>
        <p style="text-align:center;margin:0 0 24px;">
            <a href="{reset_link}"
               style="display:inline-block;background:#d9f95d;color:#000000;
                      padding:14px 32px;border-radius:50px;text-decoration:none;
                      font-weight:600;font-size:15px;">
                Reset Password
            </a>
        </p>
        <p style="color:#a1a1aa;font-size:14px;margin:0 0 8px;">This link expires in 15 minutes.</p>
        <p style="color:#71717a;font-size:13px;margin:0;">If you didn't request this, ignore this email.</p>
    """
    html = _base_wrapper(body)
    _send_via_api(email, name, "Reset your QUOKKA password", html)


def send_welcome_email(email, name):
    body = f"""
        <p style="color:#ffffff;font-size:16px;margin:0 0 16px;">Welcome, {name}! 🎉</p>
        <p style="color:#a1a1aa;font-size:15px;line-height:1.6;margin:0 0 16px;">
            Your email has been verified. You're all set to use QUOKKA AI Assistant.
        </p>
        <p style="color:#a1a1aa;font-size:15px;line-height:1.6;margin:0;">
            Start chatting with LLaMA 3.1 and explore everything QUOKKA has to offer.
        </p>
    """
    html = _base_wrapper(body)
    _send_via_api(email, name, "Welcome to QUOKKA", html)