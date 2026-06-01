"""
Auth routes — complete rebuild.
Flow: Register → OTP email → Verify → Logged in
      Login | Forgot password → Reset link → Reset password
"""
import os
import re
import secrets
import threading
import traceback
from datetime import datetime, timedelta

from flask import Blueprint, jsonify, request, session, current_app
from werkzeug.security import check_password_hash, generate_password_hash

import memory.chat_storage as storage
from routes.auth_middleware import login_required
from services.mail_service import send_otp_email, send_reset_email, send_welcome_email

auth_bp = Blueprint("auth", __name__)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _ok(data=None, message=None, status=200):
    payload = {"success": True}
    if message:
        payload["message"] = message
    if data and isinstance(data, dict):
        payload.update(data)
    return jsonify(payload), status


def _err(message, status=400, code=None):
    payload = {"success": False, "message": message}
    if code:
        payload["error"] = code
    return jsonify(payload), status


def _valid_email(email):
    if not email or not isinstance(email, str):
        return False
    return re.match(r"^[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}$", email.strip()) is not None


def _valid_password(pw):
    """Min 8 chars, at least 1 digit."""
    return bool(pw) and len(pw) >= 8 and any(c.isdigit() for c in pw)


def _parse_dt(s):
    try:
        return datetime.fromisoformat(s)
    except Exception:
        return None


def _new_otp():
    return str(secrets.randbelow(900000) + 100000)   # 6-digit


def _send_async(fn, *args):
    """Run email send in background thread — never blocks the HTTP response."""
    def _run():
        try:
            fn(*args)
        except Exception:
            print(f"[EMAIL ERROR] {fn.__name__}:\n{traceback.format_exc()}", flush=True)
    threading.Thread(target=_run, daemon=True).start()


# ── Register ──────────────────────────────────────────────────────────────────

@auth_bp.route("/api/auth/register", methods=["POST"])
def register():
    try:
        data     = request.get_json() or {}
        name     = (data.get("name") or "").strip()
        email    = (data.get("email") or "").strip().lower()
        password = data.get("password") or ""

        if len(name) < 2:
            return _err("Name must be at least 2 characters.")
        if not _valid_email(email):
            return _err("Please enter a valid email address.")
        if not _valid_password(password):
            return _err("Password must be at least 8 characters and contain a number.")

        existing = storage.get_user_by_email(email)

        # Already verified → reject
        if existing and int(existing.get("is_verified") or 0) == 1:
            return _err("An account with this email already exists.")

        otp    = _new_otp()
        expiry = (datetime.now() + timedelta(minutes=10)).isoformat()

        if existing:
            # Unverified account exists → refresh OTP and resend
            storage.set_user_otp(email, otp, expiry)
            _send_async(send_otp_email, email, existing.get("name") or name, otp)
            print(f"[REGISTER] Resent OTP to existing unverified {email}", flush=True)
            return _ok(message="OTP resent — check your inbox.")

        # New account
        pw_hash = generate_password_hash(password)
        storage.create_user(name, email, pw_hash)
        storage.set_user_otp(email, otp, expiry)
        _send_async(send_otp_email, email, name, otp)
        print(f"[REGISTER] Created account + OTP sent to {email}", flush=True)
        return _ok(message="OTP sent to your email.")

    except Exception:
        print("[REGISTER ERROR]", traceback.format_exc(), flush=True)
        return _err("Something went wrong. Please try again.", 500)


# ── Verify OTP ────────────────────────────────────────────────────────────────

@auth_bp.route("/api/auth/verify-otp", methods=["POST"])
def verify_otp():
    try:
        data  = request.get_json() or {}
        email = (data.get("email") or "").strip().lower()
        otp   = (data.get("otp") or "").strip()

        user = storage.get_user_by_email(email)
        if not user:
            return _err("User not found.", 404)
        if int(user.get("is_verified") or 0) == 1:
            return _err("Account is already verified.")

        attempts = int(user.get("otp_attempts") or 0)
        if attempts >= 5:
            # Wipe the unverified account so they can re-register
            storage.delete_unverified_user(email)
            return _err("Too many incorrect attempts. Please register again.", 400)

        # Check expiry first (no penalty for expired OTP)
        exp = _parse_dt(user.get("otp_expiry") or "")
        if not exp or exp < datetime.now():
            return _err("OTP has expired. Click 'Resend OTP' to get a new code.", 400)

        # Wrong OTP → increment counter
        if (user.get("otp") or "") != otp:
            storage.increment_otp_attempts(email)
            remaining = 4 - attempts   # attempts hasn't been incremented yet in memory
            return _err(f"Incorrect code. {remaining} attempt(s) remaining.", 400)

        # ✅ Correct OTP
        storage.verify_user_email(email)
        session["user_id"]    = user["id"]
        session["user_email"] = user["email"]
        session["user_name"]  = user["name"]

        _send_async(send_welcome_email, user["email"], user["name"])
        print(f"[VERIFY] {email} verified OK", flush=True)
        return _ok(message="Email verified — welcome!")

    except Exception:
        print("[VERIFY OTP ERROR]", traceback.format_exc(), flush=True)
        return _err("Something went wrong. Please try again.", 500)


# ── Resend OTP ────────────────────────────────────────────────────────────────

@auth_bp.route("/api/auth/resend-otp", methods=["POST"])
def resend_otp():
    try:
        data  = request.get_json() or {}
        email = (data.get("email") or "").strip().lower()

        user = storage.get_user_by_email(email)
        if not user:
            return _err("User not found.", 404)
        if int(user.get("is_verified") or 0) == 1:
            return _err("Account is already verified.")

        otp    = _new_otp()
        expiry = (datetime.now() + timedelta(minutes=10)).isoformat()
        storage.set_user_otp(email, otp, expiry)
        _send_async(send_otp_email, email, user.get("name") or "there", otp)
        print(f"[RESEND] OTP resent to {email}", flush=True)
        return _ok(message="New OTP sent.")

    except Exception:
        print("[RESEND OTP ERROR]", traceback.format_exc(), flush=True)
        return _err("Something went wrong. Please try again.", 500)


# ── Login ─────────────────────────────────────────────────────────────────────

@auth_bp.route("/api/auth/login", methods=["POST"])
def login():
    try:
        data     = request.get_json() or {}
        email    = (data.get("email") or "").strip().lower()
        password = data.get("password") or ""

        user = storage.get_user_by_email(email)

        # Generic error — don't reveal whether email exists
        if not user or not check_password_hash(user.get("password_hash") or "", password):
            if user and int(user.get("is_verified") or 0) == 0:
                return _err("Please verify your email before logging in.", 401, code="not_verified")
            return _err("Invalid email or password.", 401)

        if int(user.get("is_verified") or 0) != 1:
            return _err("Please verify your email before logging in.", 401, code="not_verified")

        session["user_id"]    = user["id"]
        session["user_email"] = user["email"]
        session["user_name"]  = user["name"]

        print(f"[LOGIN] {email} logged in", flush=True)
        return _ok(data={"user": {"id": user["id"], "name": user["name"], "email": user["email"]}})

    except Exception:
        print("[LOGIN ERROR]", traceback.format_exc(), flush=True)
        return _err("Something went wrong. Please try again.", 500)


# ── Logout ────────────────────────────────────────────────────────────────────

@auth_bp.route("/api/auth/logout", methods=["POST"])
def logout():
    session.clear()
    return _ok()


# ── Forgot password ───────────────────────────────────────────────────────────

@auth_bp.route("/api/auth/forgot-password", methods=["POST"])
def forgot_password():
    try:
        data  = request.get_json() or {}
        email = (data.get("email") or "").strip().lower()

        # Always return success — prevents email enumeration
        if _valid_email(email):
            user = storage.get_user_by_email(email)
            if user and int(user.get("is_verified") or 0) == 1:
                token  = secrets.token_urlsafe(32)
                expiry = (datetime.now() + timedelta(minutes=15)).isoformat()
                storage.set_reset_token(email, token, expiry)
                base     = os.environ.get("BASE_URL", "http://localhost:8000").rstrip("/")
                link     = f"{base}/reset-password?token={token}"
                _send_async(send_reset_email, user["email"], user["name"], link)
                print(f"[FORGOT] Reset link sent to {email}", flush=True)

        return _ok(message="If that email is registered, a reset link has been sent.")

    except Exception:
        print("[FORGOT ERROR]", traceback.format_exc(), flush=True)
        return _err("Something went wrong. Please try again.", 500)


# ── Reset password ────────────────────────────────────────────────────────────

@auth_bp.route("/api/auth/reset-password", methods=["POST"])
def reset_password():
    try:
        data     = request.get_json() or {}
        token    = (data.get("token") or "").strip()
        password = data.get("password") or ""

        if not token:
            return _err("Invalid or expired reset link.", 400)

        user = storage.get_user_by_reset_token(token)
        if not user:
            return _err("Invalid or expired reset link.", 400)

        exp = _parse_dt(user.get("reset_token_expiry") or "")
        if not exp or exp < datetime.now():
            return _err("This reset link has expired. Please request a new one.", 400)

        if not _valid_password(password):
            return _err("Password must be at least 8 characters and contain a number.")

        storage.update_password(user["email"], generate_password_hash(password))
        storage.clear_reset_token(user["email"])
        print(f"[RESET] Password reset for {user['email']}", flush=True)
        return _ok(message="Password reset successfully. You can now log in.")

    except Exception:
        print("[RESET ERROR]", traceback.format_exc(), flush=True)
        return _err("Something went wrong. Please try again.", 500)


# ── Me (session check) ────────────────────────────────────────────────────────

@auth_bp.route("/api/auth/me", methods=["GET"])
def me():
    if "user_id" not in session:
        return jsonify({"error": "Unauthorized"}), 401
    user = storage.get_user_by_id(session["user_id"])
    if not user:
        session.clear()
        return jsonify({"error": "Unauthorized"}), 401
    return jsonify({"success": True, "user": {
        "id": user["id"], "name": user["name"], "email": user["email"]
    }})


# ── Profile ───────────────────────────────────────────────────────────────────

@auth_bp.route("/api/auth/profile", methods=["GET"])
@login_required
def get_profile():
    user = storage.get_user_by_id(session["user_id"])
    if not user:
        session.clear()
        return jsonify({"error": "Unauthorized"}), 401
    return jsonify({
        "success":    True,
        "name":       user["name"],
        "email":      user["email"],
        "created_at": user.get("created_at"),
        "chat_count": storage.get_user_chat_count(session["user_id"]),
        "is_verified": bool(int(user.get("is_verified") or 0)),
    })


@auth_bp.route("/api/auth/profile", methods=["PUT"])
@login_required
def update_profile():
    data = request.get_json() or {}
    name = (data.get("name") or "").strip()
    if len(name) < 2:
        return _err("Name must be at least 2 characters.")
    storage.update_user_name(session["user_id"], name)
    session["user_name"] = name
    return _ok(message="Profile updated.")


# ── Change password ───────────────────────────────────────────────────────────

@auth_bp.route("/api/auth/change-password", methods=["PUT"])
@login_required
def change_password():
    data             = request.get_json() or {}
    current_password = data.get("current_password") or ""
    new_password     = data.get("new_password") or ""

    user = storage.get_user_by_id(session["user_id"])
    if not user:
        session.clear()
        return jsonify({"error": "Unauthorized"}), 401

    if not check_password_hash(user.get("password_hash") or "", current_password):
        return _err("Current password is incorrect.")
    if not _valid_password(new_password):
        return _err("New password must be at least 8 characters and contain a number.")

    storage.update_password(user["email"], generate_password_hash(new_password))
    return _ok(message="Password updated.")


# ── Delete account ────────────────────────────────────────────────────────────

@auth_bp.route("/api/auth/account", methods=["DELETE"])
@login_required
def delete_account():
    storage.delete_user_account(session["user_id"])
    session.clear()
    return _ok()