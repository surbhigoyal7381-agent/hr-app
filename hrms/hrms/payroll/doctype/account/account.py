import frappe
from frappe.model.document import Document


class Account(Document):
    pass


def get_account_currency(account):
    if not account:
        return frappe.db.get_default("currency")
    return frappe.db.get_value("Account", account, "account_currency") or frappe.db.get_default("currency")
