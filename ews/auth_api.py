"""
EWS Auth API
============
Authentication endpoints for the EWS mobile app.

Endpoints:
    - register_reporter: Register a new reporter (with phone, address)
    - send_otp: Send WhatsApp OTP via Twilio
    - verify_otp: Verify OTP and auto-activate account
    - login: Login with email/password
    - get_public_provinces: List provinces (guest access)

Setup Guide (Twilio WhatsApp OTP):
------------------------------------
1. Create a Twilio account at https://www.twilio.com/
2. In the Twilio Console:
   a. Go to "Messaging" > "Try it out" > "Send a WhatsApp message"
   b. Follow the sandbox setup to get your sandbox number (e.g., +14155238886)
   c. For production, request a dedicated WhatsApp-enabled number
3. Get your credentials from the Twilio Console Dashboard:
   - Account SID
   - Auth Token
4. In Frappe, create a new DocType "EWS Settings" (if not already created)
   and add these fields:
   - twilio_account_sid (Data, mandatory)
   - twilio_auth_token (Password, mandatory)
   - twilio_whatsapp_number (Data, mandatory) — format: +14155238886
   - otp_expiry_minutes (Int, default: 5)
5. Install the Twilio Python SDK:
   pip install twilio
   Or add it to pyproject.toml dependencies.
6. For sandbox testing:
   - Users must first send "join <sandbox-keyword>" to the Twilio
     WhatsApp sandbox number from their phone.
   - The sandbox keyword is shown in your Twilio Console.
7. For production:
   - Submit your WhatsApp sender profile for approval in Twilio Console.
   - Register your message templates (OTP template) for approval.
   - Use your approved WhatsApp Business number instead of sandbox.
"""

import frappe
from frappe import _
from typing import Dict, List, Any, Optional
import random
import string
from datetime import datetime, timedelta
import requests


# ─────────────────────────────────────────────────
# Registration
# ─────────────────────────────────────────────────

@frappe.whitelist(allow_guest=True)
def register_reporter(
    full_name: str,
    email: str,
    password: str,
    province: Optional[str] = None,
    phone_number: Optional[str] = None,
    address: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Register a new reporter user.

    Creates a User document (disabled by default if phone is provided), assigns the province role,
    and stores phone number and address. After registration, if phone is provided, the user must
    verify their phone via WhatsApp OTP to activate their account.

    Args:
        full_name (str): Full name of the user
        email (str): Email address (login ID)
        province (str, optional): Province name
        password (str): User's password
        phone_number (str, optional): Phone number with country code (e.g., +9647XXXXXXXXX)
        address (str, optional): Physical address of the reporter

    Returns:
        dict: Success message with user email, or error
    """
    try:
        # Validate required fields
        if not full_name or not full_name.strip():
            frappe.throw(_("Full name is required"))
        if not email or not email.strip():
            frappe.throw(_("Email is required"))
        if not province or not province.strip():
            frappe.throw(_("Province is required"))
        if not password:
            frappe.throw(_("Password is required"))

        email = email.strip().lower()

        if phone_number and phone_number.strip():
            phone_number = phone_number.strip()
            # Validate phone number format (basic check)
            if not phone_number.startswith("+"):
                frappe.throw(_("Phone number must include country code (e.g., +9647XXXXXXXXX)"))
        else:
            phone_number = None

        # Check if user already exists
        if frappe.db.exists("User", email):
            frappe.throw(_("User with email {0} already exists").format(email))

        # # Check if phone number is already registered
        # existing_phone = frappe.db.exists("User", {"phone": phone_number})
        # if existing_phone:
        #     frappe.throw(_("Phone number {0} is already registered").format(phone_number))

        # Validate province exists
        if not frappe.db.exists("Province", province):
            frappe.throw(_("Province {0} does not exist").format(province))

        # Disable strong password policy for registration
        frappe.flags.ignore_password_policy = True

        # Create User document
        user = frappe.new_doc("User")
        user.first_name = full_name.strip()
        user.email = email
        user.phone = phone_number or ""
        user.location = address.strip() if address else ""
        user.enabled = 0 if phone_number else 1  # Requires OTP to enable if phone number is provided, otherwise enabled immediately
        user.new_password = password

        # Assign the user to the single "Reporter" role
        role_name = "Reporter"

        # Verify role exists
        if not frappe.db.exists("Role", role_name):
            frappe.log_error(
                f"Role '{role_name}' does not exist. Creating user without Reporter role.",
                "Registration Warning"
            )
        else:
            user.append("roles", {"role": role_name})

        user.save(ignore_permissions=True)
        
        # Link user to their province using User Provinces single doctype
        user_provinces = frappe.get_doc("User Provinces")
        # Check if already linked to avoid duplicates
        existing_link = next((row for row in user_provinces.get("ews_user_province") if row.user == email and row.province == province), None)
        if not existing_link:
            user_provinces.append("ews_user_province", {
                "user": email,
                "province": province
            })
            user_provinces.save(ignore_permissions=True)

        frappe.db.commit()

        message = _("Registration successful. Please verify your phone number with the OTP sent to your WhatsApp.") if phone_number else _("Registration successful. You can now log in.")

        return {
            "status": "success",
            "message": message,
            "user": email,
            "phone_number": phone_number,
            "requires_otp": True if phone_number else False,
        }

    except frappe.ValidationError:
        raise
    except Exception as e:
        frappe.log_error(f"Error registering user: {str(e)}", "Registration Error")
        frappe.throw(_("Error registering user: {0}").format(str(e)))
    finally:
        frappe.flags.ignore_password_policy = False


# ─────────────────────────────────────────────────
# OTP — Twilio WhatsApp
# ─────────────────────────────────────────────────

def _generate_otp(length: int = 6) -> str:
    """Generate a random numeric OTP."""
    return "".join(random.choices(string.digits, k=length))


def _send_standingtech_otp(phone_number: str) -> Optional[str]:
    """
    Send OTP via StandingTech API.
    Returns the generated OTP if successful, else None.
    """
    url = "https://gateway.standingtech.com/api/v5/otp/send"
    headers = {
        "Authorization": "Bearer 695|af51ce7f78a94e970ca905678656e593b17f676bbb970b591c3ae7c560d60f70",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }

    # Clean phone number (remove positive sign if present)
    clean_phone = phone_number.replace("+", "").strip()

    payload = {
        "recipient": clean_phone,
        "sender_id": "TigrisSol",
        "channel": "whatsapp",
        "message": "auto",
        "fallback": "sms",
        "lang": "ar"
    }

    try:
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        res_data = response.json()

        if res_data.get("status") == "success":
            return str(res_data.get("data", {}).get("message"))
        else:
            frappe.log_error(f"OTP API Error: {res_data}", "StandingTech OTP Error")
            return None
    except Exception as e:
        frappe.log_error(f"Failed to send StandingTech OTP to {phone_number}: {str(e)}", "StandingTech OTP Error")
        return None


def _store_otp(email: str, otp: str, expiry_minutes: int = 5) -> None:
    """
    Store OTP in the database with expiry time.
    Uses Frappe's cache for fast lookup and automatic expiry.
    """
    cache_key = f"ews_otp:{email}"
    expiry_seconds = expiry_minutes * 60
    frappe.cache.set_value(
        cache_key,
        {
            "otp": otp,
            "created_at": datetime.now().isoformat(),
            "attempts": 0,
        },
        expires_in_sec=expiry_seconds,
    )


def _verify_stored_otp(email: str, otp: str) -> Dict[str, Any]:
    """
    Verify OTP from cache.

    Returns:
        dict with 'valid' (bool) and 'message' (str)
    """
    cache_key = f"ews_otp:{email}"
    stored = frappe.cache.get_value(cache_key)

    if not stored:
        return {"valid": False, "message": _("OTP has expired. Please request a new one.")}

    # Rate limit: max 5 attempts
    attempts = stored.get("attempts", 0)
    if attempts >= 5:
        frappe.cache.delete_value(cache_key)
        return {"valid": False, "message": _("Too many failed attempts. Please request a new OTP.")}

    if stored["otp"] != otp:
        # Increment attempt counter
        stored["attempts"] = attempts + 1
        frappe.cache.set_value(cache_key, stored, expires_in_sec=300)
        remaining = 5 - stored["attempts"]
        return {
            "valid": False,
            "message": _("Invalid OTP. {0} attempts remaining.").format(remaining),
        }

    # OTP is valid — remove it
    frappe.cache.delete_value(cache_key)
    return {"valid": True, "message": _("OTP verified successfully.")}


@frappe.whitelist(allow_guest=True)
def send_otp(email: str) -> Dict[str, Any]:
    """
    Send a WhatsApp OTP to the user's registered phone number.

    The user must be registered (User document must exist) but can be disabled.
    This is used after registration to verify the phone number.

    Args:
        email (str): The registered email address

    Returns:
        dict: Status message
    """
    try:
        if not email or not email.strip():
            frappe.throw(_("Email is required"))

        email = email.strip().lower()

        # Check user exists
        user = frappe.db.get_value("User", email, ["name", "phone"], as_dict=True)
        if not user:
            frappe.throw(_("No account found with this email address."))

        phone_number = user.phone
        if not phone_number:
            frappe.throw(_("No phone number registered for this account."))

        otp_val = _send_standingtech_otp(phone_number)
        if not otp_val:
            frappe.throw(_("Failed to send OTP to your Whatsapp. Please try again later."))

        # Store the OTP internally with 10 minute expiry
        _store_otp(email, otp_val, 10)

        return {
            "status": "success",
            "message": _("OTP sent successfully to your WhatsApp"),
            "expires_in_minutes": 10,
        }

    except frappe.ValidationError:
        raise
    except Exception as e:
        frappe.log_error(f"Error sending OTP: {str(e)}", "OTP Send Error")
        frappe.throw(_("Error sending OTP: {0}").format(str(e)))


@frappe.whitelist(allow_guest=True)
def verify_otp(email: str, otp: str) -> Dict[str, Any]:
    """
    Verify the WhatsApp OTP and auto-activate the user account.

    On successful verification:
    - User account is enabled (activated)
    - User can now log in

    Args:
        email (str): The registered email address
        otp (str): The OTP received on WhatsApp

    Returns:
        dict: Verification result with login credentials if successful
    """
    try:
        if not email or not email.strip():
            frappe.throw(_("Email is required"))
        if not otp or not otp.strip():
            frappe.throw(_("OTP is required"))

        email = email.strip().lower()

        # Check user exists
        if not frappe.db.exists("User", email):
            frappe.throw(_("No account found with this email address."))

        # Verify OTP using the cache
        verify_res = _verify_stored_otp(email, otp)
        if not verify_res["valid"]:
            frappe.throw(verify_res["message"])

        # OTP is valid, enable the user account
        frappe.db.set_value("User", email, "enabled", 1)
        frappe.db.commit()

        return {
            "status": "success",
            "message": _("Phone number verified! Your account is now active. You can log in."),
            "user": email,
            "activated": True,
        }

    except frappe.ValidationError:
        raise
    except Exception as e:
        frappe.log_error(f"Error verifying OTP: {str(e)}", "OTP Verify Error")
        frappe.throw(_("Error verifying OTP: {0}").format(str(e)))


# ─────────────────────────────────────────────────
# Login
# ─────────────────────────────────────────────────

@frappe.whitelist(allow_guest=True)
def login(email: str, password: str) -> Dict[str, Any]:
    """
    Login with email and password.

    Returns session info and API keys for subsequent authenticated requests.

    Args:
        email (str): User's email address
        password (str): User's password

    Returns:
        dict: Login result with user info, api_key, api_secret, and sid
    """
    try:
        if not email or not email.strip():
            frappe.throw(_("Email is required"))
        if not password:
            frappe.throw(_("Password is required"))

        email = email.strip().lower()

        # Check user exists
        if not frappe.db.exists("User", email):
            frappe.throw(_("Invalid email or password"))

        # Check if user is enabled
        user_enabled = frappe.db.get_value("User", email, "enabled")
        if not user_enabled:
            frappe.throw(_(
                "Your account is not activated. "
                "Please verify your phone number with the OTP sent to your WhatsApp."
            ))

        # Authenticate using Frappe's built-in method
        from frappe.auth import LoginManager

        login_manager = LoginManager()
        login_manager.authenticate(email, password)
        login_manager.post_login()

        # Get or generate API keys for the user
        api_key = frappe.db.get_value("User", email, "api_key")
        api_secret = None

        if not api_key:
            # Generate new API keys
            api_key = frappe.generate_hash(length=15)
            frappe.db.set_value("User", email, "api_key", api_key)

        api_secret = frappe.utils.password.get_decrypted_password(
            "User", email, "api_secret", raise_exception=False
        )

        if not api_secret:
            api_secret = frappe.generate_hash(length=15)
            user_doc = frappe.get_doc("User", email)
            user_doc.api_secret = api_secret
            user_doc.save(ignore_permissions=True)

        frappe.db.commit()

        # Get user info
        user_doc = frappe.get_doc("User", email)

        return {
            "status": "success",
            "message": _("Login successful"),
            "user": email,
            "full_name": user_doc.first_name or "",
            "api_key": api_key,
            "api_secret": api_secret,
            "sid": frappe.session.sid,
        }

    except frappe.AuthenticationError:
        frappe.clear_messages()
        frappe.throw(_("Invalid email or password"))
    except frappe.ValidationError:
        raise
    except Exception as e:
        frappe.log_error(f"Error during login: {str(e)}", "Login Error")
        frappe.throw(_("Login failed: {0}").format(str(e)))


# ─────────────────────────────────────────────────
# Public Helpers
# ─────────────────────────────────────────────────

@frappe.whitelist(allow_guest=True)
def get_public_provinces() -> List[Dict[str, Any]]:
    """
    Get all provinces. Publicly accessible for the registration form.

    Returns:
        list: List of Province documents with name field
    """
    try:
        provinces = frappe.db.get_list(
            "Province",
            fields=["*"],
            order_by="name asc",
        )
        return provinces
    except Exception as e:
        frappe.log_error(f"Error fetching provinces: {str(e)}")
        return []


# ─────────────────────────────────────────────────
# Forgot Password
# ─────────────────────────────────────────────────

def _store_reset_otp(email: str, otp: str, expiry_minutes: int = 10) -> None:
    """Store forgot password OTP in cache with expiry time."""
    cache_key = f"ews_pwd_reset_otp:{email}"
    expiry_seconds = expiry_minutes * 60
    frappe.cache.set_value(
        cache_key,
        {
            "otp": otp,
            "created_at": datetime.now().isoformat(),
            "attempts": 0,
        },
        expires_in_sec=expiry_seconds,
    )


def _verify_reset_otp(email: str, otp: str) -> Dict[str, Any]:
    """Verify forgot password OTP from cache."""
    cache_key = f"ews_pwd_reset_otp:{email}"
    stored = frappe.cache.get_value(cache_key)

    if not stored:
        return {"valid": False, "message": _("OTP has expired. Please request a new one.")}

    attempts = stored.get("attempts", 0)
    if attempts >= 5:
        frappe.cache.delete_value(cache_key)
        return {"valid": False, "message": _("Too many failed attempts. Please request a new OTP.")}

    if stored["otp"] != otp:
        stored["attempts"] = attempts + 1
        frappe.cache.set_value(cache_key, stored, expires_in_sec=300)
        remaining = 5 - stored["attempts"]
        return {
            "valid": False,
            "message": _("Invalid OTP. {0} attempts remaining.").format(remaining),
        }

    frappe.cache.delete_value(cache_key)
    return {"valid": True, "message": _("OTP verified successfully.")}


@frappe.whitelist(allow_guest=True)
def forgot_password_send_otp(email: str) -> Dict[str, Any]:
    """
    Send an OTP for password reset to the user's WhatsApp and/or Email.
    """
    try:
        print(f"DEBUG [forgot_password_send_otp]: Start request for email: {email}")
        if not email or not email.strip():
            frappe.throw(_("Email is required"))

        email = email.strip().lower()

        user = frappe.db.get_value("User", email, ["name", "phone", "first_name"], as_dict=True)
        print(f"DEBUG [forgot_password_send_otp]: Fetched user doc: {user}")
        if not user:
            frappe.throw(_("No account found with this email address."))

        phone_number = user.phone
        print(f"DEBUG [forgot_password_send_otp]: User phone number: {phone_number}")
        if not phone_number or not phone_number.strip():
            frappe.throw(_("No phone number registered for this account."))

        print(f"DEBUG [forgot_password_send_otp]: Sending OTP to {phone_number} via StandingTech...")
        otp_val = _send_standingtech_otp(phone_number)
        print(f"DEBUG [forgot_password_send_otp]: StandingTech response OTP: {otp_val}")
        if not otp_val:
            frappe.throw(_("Failed to send verification code to your WhatsApp/phone. Please try again later."))

        _store_reset_otp(email, otp_val, 10)
        print(f"DEBUG [forgot_password_send_otp]: OTP stored in cache successfully for {email}")

        masked_target = phone_number[:-4] + "****" if len(phone_number) > 4 else "WhatsApp"

        return {
            "status": "success",
            "message": _("Verification code sent successfully to your WhatsApp/phone"),
            "target": masked_target,
            "expires_in_minutes": 10,
        }

    except frappe.ValidationError:
        print("DEBUG [forgot_password_send_otp]: ValidationError raised")
        raise
    except Exception as e:
        print(f"DEBUG [forgot_password_send_otp]: Exception occurred: {str(e)}")
        frappe.log_error(f"Error sending forgot password OTP: {str(e)}", "Forgot Password OTP Error")
        frappe.throw(_("Error sending verification code: {0}").format(str(e)))


@frappe.whitelist(allow_guest=True)
def forgot_password_reset(email: str, otp: str, new_password: str) -> Dict[str, Any]:
    """
    Verify the reset OTP and update the user's password.
    """
    try:
        if not email or not email.strip():
            frappe.throw(_("Email is required"))
        if not otp or not otp.strip():
            frappe.throw(_("OTP is required"))
        if not new_password or len(new_password) < 6:
            frappe.throw(_("Password must be at least 6 characters"))

        email = email.strip().lower()

        if not frappe.db.exists("User", email):
            frappe.throw(_("No account found with this email address."))

        verify_res = _verify_reset_otp(email, otp)
        if not verify_res["valid"]:
            frappe.throw(verify_res["message"])

        user_doc = frappe.get_doc("User", email)
        user_doc.new_password = new_password
        if not user_doc.enabled:
            user_doc.enabled = 1
        user_doc.save(ignore_permissions=True)
        frappe.db.commit()

        return {
            "status": "success",
            "message": _("Password reset successfully! You can now log in."),
        }

    except frappe.ValidationError:
        raise
    except Exception as e:
        frappe.log_error(f"Error resetting password: {str(e)}", "Forgot Password Reset Error")
        frappe.throw(_("Error resetting password: {0}").format(str(e)))



