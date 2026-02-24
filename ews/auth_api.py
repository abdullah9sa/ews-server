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


# ─────────────────────────────────────────────────
# Registration
# ─────────────────────────────────────────────────

@frappe.whitelist(allow_guest=True)
def register_reporter(
    full_name: str,
    email: str,
    province: str,
    password: str,
    phone_number: str,
    address: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Register a new reporter user.

    Creates a User document (disabled by default), assigns the province role,
    and stores phone number and address. After registration, the user must
    verify their phone via WhatsApp OTP to activate their account.

    Args:
        full_name (str): Full name of the user
        email (str): Email address (login ID)
        province (str): Province name
        password (str): User's password
        phone_number (str): Phone number with country code (e.g., +9647XXXXXXXXX)
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
        if not phone_number or not phone_number.strip():
            frappe.throw(_("Phone number is required"))

        email = email.strip().lower()
        phone_number = phone_number.strip()

        # Validate phone number format (basic check)
        if not phone_number.startswith("+"):
            frappe.throw(_("Phone number must include country code (e.g., +9647XXXXXXXXX)"))

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
        user.phone = phone_number
        user.location = address.strip() if address else ""
        user.enabled = 0  # Disabled until OTP verification
        user.new_password = password

        # Construct role name based on province (e.g., "Nineveh Reporter")
        role_name = f"{province} Reporter"

        # Verify role exists
        if not frappe.db.exists("Role", role_name):
            frappe.log_error(
                f"Role '{role_name}' does not exist. Creating user without province role.",
                "Registration Warning"
            )
        else:
            user.append("roles", {"role": role_name})

        user.save(ignore_permissions=True)
        frappe.db.commit()

        return {
            "status": "success",
            "message": _("Registration successful. Please verify your phone number with the OTP sent to your WhatsApp."),
            "user": email,
            "phone_number": phone_number,
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


def _get_twilio_settings() -> Dict[str, Any]:
    """
    Read Twilio credentials from EWS Settings.

    Returns:
        dict with keys: account_sid, auth_token, whatsapp_number, otp_expiry_minutes
    """
    try:
        settings = frappe.get_single("EWS Settings")
        account_sid = settings.get("twilio_account_sid")
        # Auth token is stored as Data field, not Password
        auth_token = settings.get("twilio_auth_token")
        whatsapp_number = settings.get("twilio_whatsapp_number")
        otp_expiry = settings.get("otp_expiry_minutes") or 5

        if not account_sid or not auth_token or not whatsapp_number:
            frappe.throw(_("Twilio settings are not configured. Please contact the administrator."))

        # Normalize whatsapp number — strip "whatsapp:" prefix if user added it
        whatsapp_number = whatsapp_number.replace("whatsapp:", "").strip()

        return {
            "account_sid": account_sid,
            "auth_token": auth_token,
            "whatsapp_number": whatsapp_number,
            "otp_expiry_minutes": int(otp_expiry),
        }
    except frappe.DoesNotExistError:
        frappe.throw(_("EWS Settings not found. Please configure Twilio settings."))
    except frappe.ValidationError:
        raise
    except Exception as e:
        frappe.log_error(f"Error reading Twilio settings: {str(e)}", "Twilio Config Error")
        frappe.throw(_("Error reading Twilio configuration: {0}").format(str(e)))


def _send_whatsapp_otp(phone_number: str, otp: str) -> bool:
    """
    Send OTP via Twilio WhatsApp API.

    Args:
        phone_number: Recipient phone number with country code
        otp: The OTP string to send

    Returns:
        True if message was sent successfully
    """
    try:
        from twilio.rest import Client
    except ImportError:
        frappe.throw(_(
            "Twilio SDK is not installed. "
            "Run: pip install twilio"
        ))

    settings = _get_twilio_settings()

    try:
        client = Client(settings["account_sid"], settings["auth_token"])

        from_number = f"whatsapp:{settings['whatsapp_number']}"
        to_number = f"whatsapp:{phone_number}"

        frappe.logger().info(
            f"Twilio WhatsApp: Sending OTP from={from_number} to={to_number}"
        )

        message = client.messages.create(
            body=f"Your EWS verification code is: {otp}\n\nThis code expires in {settings['otp_expiry_minutes']} minutes.",
            from_=from_number,
            to=to_number,
        )

        # Log detailed message info for debugging
        frappe.log_error(
            f"WhatsApp OTP Message Details:\n"
            f"  SID: {message.sid}\n"
            f"  Status: {message.status}\n"
            f"  From: {from_number}\n"
            f"  To: {to_number}\n"
            f"  Error Code: {message.error_code}\n"
            f"  Error Message: {message.error_message}",
            "Twilio WhatsApp Debug"
        )

        return True

    except Exception as e:
        frappe.log_error(
            f"Failed to send WhatsApp OTP to {phone_number}: {str(e)}\n"
            f"From: whatsapp:{settings['whatsapp_number']}\n"
            f"To: whatsapp:{phone_number}",
            "Twilio WhatsApp Error"
        )
        frappe.throw(_("Failed to send OTP. Please try again later."))
        return False


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
        if not frappe.db.exists("User", email):
            frappe.throw(_("No account found with this email address."))

        # Get user's phone number
        phone_number = frappe.db.get_value("User", email, "phone")
        if not phone_number:
            frappe.throw(_("No phone number found for this account. Please contact support."))

        # Rate limiting: prevent sending OTP too frequently
        rate_key = f"ews_otp_rate:{email}"
        last_sent = frappe.cache.get_value(rate_key)
        if last_sent:
            frappe.throw(_("Please wait before requesting another OTP."))

        # Generate OTP
        settings = _get_twilio_settings()
        otp = _generate_otp()

        # Store OTP
        _store_otp(email, otp, settings["otp_expiry_minutes"])

        # Send via WhatsApp
        _send_whatsapp_otp(phone_number, otp)

        # Set rate limit (60 seconds between sends)
        frappe.cache.set_value(rate_key, True, expires_in_sec=60)

        # Mask phone for response
        masked_phone = phone_number[:4] + "****" + phone_number[-3:]

        return {
            "status": "success",
            "message": _("OTP sent to your WhatsApp ({0})").format(masked_phone),
            "expires_in_minutes": settings["otp_expiry_minutes"],
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
        otp = otp.strip()

        # Check user exists
        if not frappe.db.exists("User", email):
            frappe.throw(_("No account found with this email address."))

        # Verify OTP
        result = _verify_stored_otp(email, otp)

        if not result["valid"]:
            frappe.throw(result["message"])

        # OTP verified — activate the account
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


