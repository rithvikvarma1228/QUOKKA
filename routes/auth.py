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


def _json_error(message, status=400, error_code=None, extra=None):
    payload = {"success": False, "message": message}
    if error_code:
        payload["error"] = error_code
    if extra and isinstance(extra, dict):
        payload.update(extra)
    return jsonify(payload), status


def _json_ok(data=None, message=None, status=200):
    payload = {"success": True}
    if message:
        payload["message"] = message
    if data and isinstance(data, dict):
        payload.update(data)
    return jsonify(payload), status


def _is_valid_email(email):
    if not email or not isinstance(email, str):
        return False
    pattern = r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$"
    return re.match(pattern, email.strip()) is not None


def _password_ok(password):
    if not password or not isinstance(password, str):
        return False
    if len(password) < 8:
        return False
    return any(ch.isdigit() for ch in password)


def _parse_iso(dt_str):
    try:
        return datetime.fromisoformat(dt_str)
    except Exception:
        return None


# ----------------------------------------
# ASYNC EMAIL SENDER
# Runs email in background thread so the
# SMTP connection never blocks the request
# worker — fixes the SIGKILL/timeout issue
# ----------------------------------------
def send_email_async(app, fn, *args):
    def run():
        with app.app_context():
            try:
                fn(*args)
                print(f"[EMAIL] Sent via {fn.__name__}", flush=True)
            except Exception as e:
                print(f"[EMAIL ERROR] {fn.__name__}: {str(e)}", flush=True)
                print(traceback.format_exc(), flush=True)
    t = threading.Thread(target=run, daemon=True)
    t.start()


@auth_bp.route("/api/auth/register", methods=["POST"])
def register():
    try:
        print("\n[REGISTER] Request received", flush=True)
        data = request.get_json() or {}
        name = (data.get("name") or "").strip()
        email = (data.get("email") or "").strip().lower()
        password = data.get("password") or ""

        if len(name) < 2:
            return _json_error("Name is required (min 2 characters).")
        if not _is_valid_email(email):
            return _json_error("Please enter a valid email address.")
        if not _password_ok(password):
            return _json_error("Password must be at least 8 characters and include 1 number.")

        existing = storage.get_user_by_email(email)

        if existing and int(existing.get("is_verified") or 0) == 1:
            return _json_error("Email already in use")

        otp = str(secrets.randbelow(900000) + 100000)
        expiry = (datetime.now() + timedelta(minutes=10)).isoformat()

        if existing and int(existing.get("is_verified") or 0) == 0:
            storage.set_user_otp(email, otp, expiry)
            send_email_async(
                current_app._get_current_object(),
                send_otp_email,
                email, existing.get("name") or name, otp
            )
            print(f"[REGISTER] Resend OTP queued for {email}", flush=True)
            return _json_ok(
                message="Account exists but unverified. New OTP sent.",
                data={"resend": True},
            )

        password_hash = generate_password_hash(password)
        storage.create_user(name, email, password_hash)
        storage.set_user_otp(email, otp, expiry)

        send_email_async(
            current_app._get_current_object(),
            send_otp_email,
            email, name, otp
        )
        print(f"[REGISTER] OTP email queued for {email}", flush=True)
        return _json_ok(message="OTP sent to your email")

    except Exception as e:
        print("REGISTER ERROR:", traceback.format_exc(), flush=True)
        return jsonify({"success": False, "message": str(e)}), 500


@auth_bp.route("/api/auth/verify-otp", methods=["POST"])
def verify_otp():
    try:
        data = request.get_json() or {}
        email = (data.get("email") or "").strip().lower()
        otp = (data.get("otp") or "").strip()

        user = storage.get_user_by_email(email)
        if not user:
            return _json_error("User not found", 404)
        if int(user.get("is_verified") or 0) == 1:
            return _json_error("Account already verified.")

        attempts = int(user.get("otp_attempts") or 0)
        if attempts >= 5:
            conn = storage.get_connection()
            c = conn.cursor()
            c.execute("DELETE FROM users WHERE email = ? AND is_verified = 0", (email,))
            conn.commit()
            conn.close()
            return _json_error("Too many attempts. Please register again.", 400)

        # Check expiry BEFORE incrementing attempts
        expiry_str = user.get("otp_expiry")
        exp_dt = _parse_iso(expiry_str) if expiry_str else None
        if not exp_dt or exp_dt < datetime.now():
            return _json_error("OTP expired. Please register again.", 400)

        # Check OTP BEFORE incrementing attempts so a correct final attempt succeeds
        if (user.get("otp") or "") != otp:
            storage.increment_otp_attempts(email)
            return _json_error("Invalid OTP", 400)

        storage.verify_user_email(email)

        session["user_id"] = user["id"]
        session["user_email"] = user["email"]
        session["user_name"] = user["name"]

        send_email_async(
            current_app._get_current_object(),
            send_welcome_email,
            user["email"], user["name"]
        )
        return _json_ok(message="Account verified")

    except Exception as e:
        print("VERIFY OTP ERROR:", traceback.format_exc(), flush=True)
        return jsonify({"success": False, "message": str(e)}), 500


@auth_bp.route("/api/auth/resend-otp", methods=["POST"])
def resend_otp():
    try:
        data = request.get_json() or {}
        email = (data.get("email") or "").strip().lower()

        user = storage.get_user_by_email(email)
        if not user:
            return _json_error("User not found", 404)
        if int(user.get("is_verified") or 0) == 1:
            return _json_error("Account already verified.")

        otp = str(secrets.randbelow(900000) + 100000)
        expiry = (datetime.now() + timedelta(minutes=10)).isoformat()
        storage.set_user_otp(email, otp, expiry)

        send_email_async(
            current_app._get_current_object(),
            send_otp_email,
            email, user.get("name") or "there", otp
        )
        print(f"[RESEND] OTP queued for {email}", flush=True)
        return _json_ok()

    except Exception as e:
        print("RESEND OTP ERROR:", traceback.format_exc(), flush=True)
        return jsonify({"success": False, "message": str(e)}), 500


@auth_bp.route("/api/auth/login", methods=["POST"])
def login():
    try:
        data = request.get_json() or {}
        email = (data.get("email") or "").strip().lower()
        password = data.get("password") or ""

        user = storage.get_user_by_email(email)
        if not user:
            return _json_error("Invalid email or password", 401)

        if int(user.get("is_verified") or 0) != 1:
            return _json_error(
                "Please verify your email first",
                401,
                error_code="not_verified",
            )

        if not check_password_hash(user.get("password_hash") or "", password):
            return _json_error("Invalid email or password", 401)

        session["user_id"] = user["id"]
        session["user_email"] = user["email"]
        session["user_name"] = user["name"]

        return _json_ok(
            data={"user": {"id": user["id"], "name": user["name"], "email": user["email"]}},
        )

    except Exception as e:
        print("LOGIN ERROR:", traceback.format_exc(), flush=True)
        return jsonify({"success": False, "message": str(e)}), 500


@auth_bp.route("/api/auth/logout", methods=["POST"])
def logout():
    session.clear()
    return _json_ok()


@auth_bp.route("/api/auth/forgot-password", methods=["POST"])
def forgot_password():
    try:
        print("\n[FORGOT PASSWORD] Request received", flush=True)
        data = request.get_json() or {}
        email = (data.get("email") or "").strip().lower()
        print(f"[FORGOT PASSWORD] Email: {email}", flush=True)

        user = storage.get_user_by_email(email) if _is_valid_email(email) else None
        print(f"[FORGOT PASSWORD] User found: {user is not None}", flush=True)

        if user and int(user.get("is_verified") or 0) == 1:
            token = secrets.token_urlsafe(32)
            expiry = (datetime.now() + timedelta(minutes=15)).isoformat()
            storage.set_reset_token(email, token, expiry)
            base_url = os.environ.get("BASE_URL", "http://localhost:8000").rstrip("/")
            reset_link = f"{base_url}/reset-password?token={token}"
            print(f"[FORGOT PASSWORD] Reset link generated, queuing email", flush=True)

            send_email_async(
                current_app._get_current_object(),
                send_reset_email,
                user["email"], user["name"], reset_link
            )
        else:
            print(f"[FORGOT PASSWORD] User not found or not verified", flush=True)

        return _json_ok(message="If that email exists, a reset link has been sent")

    except Exception as e:
        print("FORGOT PASSWORD ERROR:", traceback.format_exc(), flush=True)
        return jsonify({"success": False, "message": str(e)}), 500


@auth_bp.route("/api/auth/reset-password", methods=["POST"])
def reset_password():
    try:
        data = request.get_json() or {}
        token = (data.get("token") or "").strip()
        password = data.get("password") or ""

        if not token:
            return _json_error("Invalid or expired reset link", 400)

        user = storage.get_user_by_reset_token(token)
        if not user:
            return _json_error("Invalid or expired reset link", 400)

        exp_str = user.get("reset_token_expiry")
        exp_dt = _parse_iso(exp_str) if exp_str else None
        if not exp_dt or exp_dt < datetime.now():
            return _json_error("Invalid or expired reset link", 400)

        if not _password_ok(password):
            return _json_error("Password must be at least 8 characters and include 1 number.")

        new_hash = generate_password_hash(password)
        storage.update_password(user["email"], new_hash)
        storage.clear_reset_token(user["email"])
        return _json_ok(message="Password reset successful")

    except Exception as e:
        print("RESET PASSWORD ERROR:", traceback.format_exc(), flush=True)
        return jsonify({"success": False, "message": str(e)}), 500


@auth_bp.route("/api/auth/me", methods=["GET"])
def me():
    if "user_id" not in session:
        return jsonify({"error": "Unauthorized"}), 401

    user = storage.get_user_by_id(session["user_id"])
    if not user:
        session.clear()
        return jsonify({"error": "Unauthorized"}), 401

    return jsonify({
        "success": True,
        "user": {"id": user["id"], "name": user["name"], "email": user["email"]},
    })


@auth_bp.route("/api/auth/profile", methods=["GET"])
@login_required
def get_profile():
    user = storage.get_user_by_id(session["user_id"])
    if not user:
        session.clear()
        return jsonify({"error": "Unauthorized"}), 401

    chat_count = storage.get_user_chat_count(session["user_id"])
    return jsonify({
        "success": True,
        "name": user["name"],
        "email": user["email"],
        "created_at": user.get("created_at"),
        "chat_count": chat_count,
        "is_verified": bool(int(user.get("is_verified") or 0)),
    })


@auth_bp.route("/api/auth/profile", methods=["PUT"])
@login_required
def update_profile():
    data = request.get_json() or {}
    name = (data.get("name") or "").strip()

    if len(name) < 2:
        return _json_error("Name must be at least 2 characters.")

    storage.update_user_name(session["user_id"], name)
    session["user_name"] = name
    return _json_ok(message="Profile updated")


@auth_bp.route("/api/auth/change-password", methods=["PUT"])
@login_required
def change_password():
    data = request.get_json() or {}
    current_password = data.get("current_password") or ""
    new_password = data.get("new_password") or ""

    user = storage.get_user_by_id(session["user_id"])
    if not user:
        session.clear()
        return jsonify({"error": "Unauthorized"}), 401

    if not check_password_hash(user.get("password_hash") or "", current_password):
        return _json_error("Current password is incorrect")

    if not _password_ok(new_password):
        return _json_error("Password must be at least 8 characters and include 1 number.")

    storage.update_password(user["email"], generate_password_hash(new_password))
    return _json_ok(message="Password updated")


@auth_bp.route("/api/auth/account", methods=["DELETE"])
@login_required
def delete_account():
    user_id = session["user_id"]
    storage.delete_user_account(user_id)
    session.clear()
    return _json_ok()