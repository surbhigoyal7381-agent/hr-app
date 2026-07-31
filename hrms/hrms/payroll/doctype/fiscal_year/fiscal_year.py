import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate


class FiscalYear(Document):
    def validate(self):
        if getdate(self.year_start_date) > getdate(self.year_end_date):
            frappe.throw(_("Fiscal Year Start Date must be before End Date"))


def get_fiscal_year(date=None, fiscal_year=None, company=None, as_dict=False, raise_exception=True):
    """Return (year, start, end) for the given date. Replacement for erpnext.accounts.utils.get_fiscal_year."""
    if not date:
        date = frappe.utils.today()
    date = getdate(date)
    filters = {
        "year_start_date": ["<=", date],
        "year_end_date": [">=", date],
    }
    fy = frappe.db.get_value("Fiscal Year", filters, ["year", "year_start_date", "year_end_date"], as_dict=True, order_by="year_start_date desc")
    if fy:
        if as_dict:
            return fy
        return fy.year, fy.year_start_date, fy.year_end_date
    if raise_exception:
        frappe.throw(_("No Fiscal Year found for date {0}").format(date))
    return None
