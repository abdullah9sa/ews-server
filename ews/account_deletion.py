"""
EWS Account Deletion API
=========================
Handles account deletion requests from the web form and in-app requests.
Stores requests for admin review and processing.
"""

import frappe
from frappe import _


@frappe.whitelist(allow_guest=True, methods=["POST"])
def request_account_deletion(full_name: str, email: str, phone: str, reason: str = ""):
    """
    Submit an account deletion request.

    This endpoint is publicly accessible (allow_guest) so that users can
    submit deletion requests from the website without being logged in.

    Args:
        full_name: The user's full name
        email: The registered email address
        phone: The registered phone number
        reason: Optional reason for deletion

    Returns:
        dict: Success message
    """
    # Skip CSRF for this guest endpoint (static HTML page, no Jinja template)
    frappe.flags.ignore_csrf = True
    # Basic validation
    if not full_name or not full_name.strip():
        frappe.throw(_("Full name is required."), frappe.ValidationError)

    if not email or not email.strip():
        frappe.throw(_("Email is required."), frappe.ValidationError)

    if not phone or not phone.strip():
        frappe.throw(_("Phone number is required."), frappe.ValidationError)

    email = email.strip().lower()
    phone = phone.strip()
    full_name = full_name.strip()
    reason = (reason or "").strip()

    # Check if a pending deletion request already exists
    existing = frappe.db.exists(
        "Account Deletion Request",
        {"email": email, "status": "Pending"}
    )
    if existing:
        return {
            "message": "A deletion request for this email is already being processed. You will receive an email confirmation once completed."
        }

    # Create the deletion request
    doc = frappe.get_doc({
        "doctype": "Account Deletion Request",
        "full_name": full_name,
        "email": email,
        "phone": phone,
        "reason": reason,
        "status": "Pending",
    })
    doc.insert(ignore_permissions=True)
    frappe.db.commit()

    return {
        "message": "Your deletion request has been submitted successfully. We will verify your identity and process the request within 7 business days."
    }
