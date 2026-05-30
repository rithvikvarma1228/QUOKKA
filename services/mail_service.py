from flask import current_app
from flask_mail import Message


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
        <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="max-width:600px;background-color:#141414;border:1px solid #27272a;border-radius:18px;">
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


def _send_html(subject, recipients, html_body):
    mail = current_app.extensions.get("mail")
    if mail is None:
        raise RuntimeError("Flask-Mail is not initialized on this app")
    msg = Message(subject=subject, recipients=[recipients], html=html_body)
    mail.send(msg)


def send_otp_email(email, name, otp):
    body = f"""
              <p style="color:#ffffff;font-size:16px;margin:0 0 16px;">Hi {name},</p>
              <p style="color:#a1a1aa;font-size:15px;line-height:1.6;margin:0 0 24px;">
                Use this code to verify your QUOKKA account:
              </p>
              <div style="background:#1f1f1f;border:1px solid #27272a;border-radius:12px;padding:24px;text-align:center;margin:0 0 24px;">
                <span style="color:#d9f95d;font-size:32px;font-weight:700;letter-spacing:8px;">{otp}</span>
              </div>
              <p style="color:#a1a1aa;font-size:14px;margin:0 0 8px;">This code expires in 10 minutes.</p>
              <p style="color:#71717a;font-size:13px;margin:0;">If you didn't request this, ignore this email.</p>
    """
    html = _base_wrapper(body)
    _send_html("Verify your QUOKKA account", email, html)


def send_reset_email(email, name, reset_link):
    body = f"""
              <p style="color:#ffffff;font-size:16px;margin:0 0 16px;">Hi {name},</p>
              <p style="color:#a1a1aa;font-size:15px;line-height:1.6;margin:0 0 24px;">
                Click the button below to reset your password:
              </p>
              <p style="text-align:center;margin:0 0 24px;">
                <a href="{reset_link}" style="display:inline-block;background:#d9f95d;color:#000000;padding:14px 32px;border-radius:50px;text-decoration:none;font-weight:600;font-size:15px;">Reset Password</a>
              </p>
              <p style="color:#a1a1aa;font-size:14px;margin:0 0 8px;">This link expires in 15 minutes.</p>
              <p style="color:#71717a;font-size:13px;margin:0;">If you didn't request this, ignore this email.</p>
    """
    html = _base_wrapper(body)
    _send_html("Reset your QUOKKA password", email, html)


def send_welcome_email(email, name):
    body = f"""
              <p style="color:#ffffff;font-size:16px;margin:0 0 16px;">Welcome, {name}!</p>
              <p style="color:#a1a1aa;font-size:15px;line-height:1.6;margin:0;">
                Your email is verified. You're all set to use QUOKKA AI Assistant.
              </p>
    """
    html = _base_wrapper(body)
    _send_html("Welcome to QUOKKA", email, html)
