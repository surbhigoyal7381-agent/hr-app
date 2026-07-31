import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate, today, cstr


class Employee(Document):
	def autoname(self):
		from frappe.model.naming import set_name_by_naming_series

		set_name_by_naming_series(self)
		self.employee = self.name

	def validate(self):
		self.validate_date()
		self.set_employee_name()
		self.validate_status()
		self.set_preferred_email()

	def validate_date(self):
		if self.date_of_birth and getdate(self.date_of_birth) >= getdate(today()):
			frappe.throw(_("Date of Birth cannot be on or after today."))
		if self.date_of_joining and self.date_of_birth:
			if getdate(self.date_of_joining) < getdate(self.date_of_birth):
				frappe.throw(_("Date of Joining cannot be before Date of Birth"))

	def set_employee_name(self):
		parts = [p for p in [self.first_name, self.middle_name, self.last_name] if p]
		self.employee_name = " ".join(parts)

	def validate_status(self):
		if self.status == "Left" and not self.relieving_date:
			frappe.throw(
				_("Please enter relieving date for employee {0}").format(self.employee_name)
			)

	def set_preferred_email(self):
		if self.prefered_contact_email == "Company Email":
			self.prefered_email = self.company_email
		elif self.prefered_contact_email == "Personal Email":
			self.prefered_email = self.personal_email
		elif self.prefered_contact_email == "User ID":
			self.prefered_email = self.user_id


# ── Module-level utility functions imported by the rest of hrms ──────────────


def get_holiday_list_for_employee(employee, raise_exception=True):
	"""Return the holiday list for an employee, falling back to company default."""
	if not employee:
		return None
	holiday_list = frappe.db.get_value("Employee", employee, "holiday_list")
	if not holiday_list:
		# Company-level default (HR Settings)
		holiday_list = frappe.db.get_value("HR Settings", None, "default_holiday_list")
	if not holiday_list and raise_exception:
		frappe.throw(_("Please set a default Holiday List for Employee {0}").format(employee))
	return holiday_list


def is_holiday(holiday_list, date=None, daily_wages_applicable_for_holiday=False, raise_exception=True):
	"""Return True if date is a non-weekly-off holiday in the given holiday list."""
	if not date:
		date = today()
	if not holiday_list:
		return False
	filters = {"parent": holiday_list, "holiday_date": date, "weekly_off": 0}
	if daily_wages_applicable_for_holiday:
		filters["weekly_off"] = ["in", [0, 1]]
	return bool(frappe.db.get_value("Holiday", filters, "name"))


def get_all_employee_emails(company):
	"""Return list of all active employee email addresses for a company."""
	employee_list = frappe.get_all(
		"Employee",
		filters={"company": company, "status": "Active"},
		fields=["name"],
	)
	return get_employee_emails(employee_list)


def get_employee_emails(employee_list):
	"""Return email addresses for a list of employee records."""
	emails = []
	for emp in employee_list:
		emp_name = emp.name if hasattr(emp, "name") else emp
		email = get_employee_email(emp_name)
		if email:
			emails.append(email)
	return emails


def get_employee_email(employee, default=None):
	"""Return the preferred email for an employee."""
	if not employee:
		return default
	emp = frappe.db.get_value(
		"Employee",
		employee,
		["prefered_contact_email", "company_email", "personal_email", "user_id"],
		as_dict=True,
	)
	if not emp:
		return default
	if emp.prefered_contact_email == "Company Email":
		return emp.company_email or default
	if emp.prefered_contact_email == "Personal Email":
		return emp.personal_email or default
	if emp.prefered_contact_email == "User ID":
		return emp.user_id or default
	return emp.company_email or emp.personal_email or emp.user_id or default


def validate_employee_role(doc, method=None):
	"""Sync Employee record when User is saved — called from doc_events User.validate."""
	emp = frappe.db.get_value("Employee", {"user_id": doc.name}, "name")
	if emp:
		frappe.db.set_value("Employee", emp, "user_id", doc.name, update_modified=False)


def has_upload_permission(doc, ptype=None, user=None):
	if not user:
		user = frappe.session.user
	if frappe.has_permission("Employee", ptype, doc, user=user):
		return True
	return frappe.db.exists("Employee", {"user_id": user, "name": doc.name})
