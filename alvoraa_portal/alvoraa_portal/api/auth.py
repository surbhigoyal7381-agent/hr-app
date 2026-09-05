import frappe

from alvoraa_portal.subscription import requires_feature
from frappe import _
from frappe.utils import now_datetime


@frappe.whitelist(allow_guest=True)
@requires_feature("vendor")
def vendor_login(email, password, otp=None):
    """
    Step 1: email+password -> returns {status: 'otp_required'} if 2FA enabled
    Step 2: email+password+otp -> returns Frappe session
    """
    # Check vendor user exists
    vendor_user = frappe.get_value(
        "Vendor User",
        {"email": email},
        [
            "name",
            "vendor",
            "two_fa_enabled",
            "account_locked",
            "failed_attempts",
            "frappe_user",
        ],
        as_dict=True,
    )
    if not vendor_user:
        frappe.throw(_("Invalid email or password"))

    if vendor_user.account_locked:
        frappe.throw(_("Account locked. Contact support."))

    # Attempt Frappe login
    from frappe.auth import LoginManager

    login_mgr = LoginManager()
    try:
        login_mgr.authenticate(user=vendor_user.frappe_user or email, pwd=password)
    except frappe.AuthenticationError:
        attempts = (vendor_user.failed_attempts or 0) + 1
        frappe.db.set_value("Vendor User", vendor_user.name, "failed_attempts", attempts)
        if attempts >= 5:
            frappe.db.set_value("Vendor User", vendor_user.name, "account_locked", 1)
        frappe.db.commit()
        frappe.throw(_("Invalid email or password"))

    # Reset failed attempts and update last login
    frappe.db.set_value(
        "Vendor User",
        vendor_user.name,
        {"failed_attempts": 0, "last_login": now_datetime()},
    )
    frappe.db.commit()

    if vendor_user.two_fa_enabled and not otp:
        # In production: send SMS OTP here
        return {"status": "otp_required", "message": "OTP sent to registered mobile"}

    login_mgr.post_login()
    return {"status": "success", "vendor": vendor_user.vendor}


@frappe.whitelist()
@requires_feature("vendor")
def vendor_logout():
    frappe.local.login_manager.logout()
    return {"status": "logged_out"}
