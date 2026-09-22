"""Slice 013, step 6: who may reach what, pinned per endpoint (US-27).

One table, six callers, every whitelisted field-app endpoint and every
field-app doctype. The callers:

  * **Guest** - nobody signed in;
  * **Employee** - a colleague with the Employee role and no employee record
    of note;
  * **Manager** - the field worker's line manager (Employee role, `reports_to`);
  * **Store HR** - an HR User whose Company User Permission is for ANOTHER
    company than the field worker's;
  * **HR Manager** - with a Company User Permission for the field worker's
    company;
  * **System Manager**.

What the table holds:

  * **AC-149** - the store HR user lists nothing, opens nothing, and is refused
    on E7, E10, E11 and E12 for the field worker; the same user is served for
    an employee of their own company.
  * **AC-150** - the manager and the colleague list nothing and open nothing on
    phones, codes, acknowledgements or the daily counts, and are refused on
    every desk endpoint.
  * **AC-151** - a guest gets nothing from the doctypes' read paths.
  * **AC-152** - an HR Manager cannot create, write or delete a code, an
    acknowledgement or a count row by any path.
  * **AC-139** - a signed-in session adds nothing on a phone endpoint: with no
    secret, an HR Manager's session is told NOT_SET_UP exactly as a guest is.

**Fail-without-fix recipe:** remove the four `has_permission` /
`permission_query_conditions` lines for the three doctypes from `hooks.py`
and the store-HR rows fail (they list the other company's rows); remove the
`has_permission` check in `field_app_desk.hr_who_may_act` and the store-HR
desk rows fail.
"""

from typing import ClassVar

import frappe
import frappe.client
from frappe.permissions import has_permission
from frappe.utils import add_to_date, now

from alvoraa_goals.tests.utils import ensure_company
from alvoraa_portal import field_app_desk as desk
from alvoraa_portal import field_app_device as device_api
from alvoraa_portal import field_app_join as join
from alvoraa_portal import field_app_records as records
from alvoraa_portal import field_app_settings as fas
from alvoraa_portal import field_checkin as fc
from alvoraa_portal.alvoraa_portal.doctype.alvoraa_app_invite.alvoraa_app_invite import INVITE
from alvoraa_portal.alvoraa_portal.doctype.alvoraa_field_app_daily_count.alvoraa_field_app_daily_count import (
	DAILY_COUNT,
)
from alvoraa_portal.alvoraa_portal.doctype.alvoraa_notice_acknowledgement.alvoraa_notice_acknowledgement import (
	ACKNOWLEDGEMENT,
)
from alvoraa_portal.tests.test_field_app_step1_013 import _new_phone
from alvoraa_portal.tests.test_field_app_step2_013 import _company_permission, _employee, _user
from alvoraa_portal.tests.test_field_app_step3_013 import JoinCase, _clear_codes, _code_of
from alvoraa_portal.tests.test_field_app_step5_013 import DeskCase
from alvoraa_portal.tests.test_portal_security_010 import _second_company

DOCTYPES = (fc.DEVICE, INVITE, ACKNOWLEDGEMENT, DAILY_COUNT)

# What each caller gets from a permission-checked list of the field worker's
# rows: "rows" (sees them), "none" (an empty list), "denied" (PermissionError).
LIST = {
	"guest": "denied", "employee": "denied", "manager": "denied",
	"store_hr": "none", "hr_manager": "rows", "system_manager": "rows",
}

# What each caller gets from a desk endpoint about the field worker:
# "ok" or "denied".
DESK = {
	"guest": "denied", "employee": "denied", "manager": "denied",
	"store_hr": "denied", "hr_manager": "ok", "system_manager": "ok",
}


class PermissionTable(DeskCase):
	"""The step-5 fixture (a field worker, HR maker with a company permission)
	plus the four other callers, and one row of each doctype for the worker."""

	callers: ClassVar[dict] = {}

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		frappe.set_user("Administrator")
		cls.other_company = _second_company()
		if cls.other_company == cls.company:
			cls.other_company = ensure_company()
		assert cls.other_company != cls.company
		cls.colleague = _user("perm.colleague", ["Employee"])
		cls.manager_user = _user("perm.manager", ["Employee"])
		cls.manager = _employee("PermManager", cls.company, user=cls.manager_user)
		cls._saved_reports_to = frappe.db.get_value("Employee", cls.employee, "reports_to")
		frappe.db.set_value("Employee", cls.employee, "reports_to", cls.manager, update_modified=False)
		cls.store_hr = _user("perm.storehr", ["HR User"])
		cls.store_perm = _company_permission(cls.store_hr, cls.other_company)
		cls.sysman = _user("perm.sysman", ["System Manager"])
		cls.other_employee = _employee("PermOther", cls.other_company, designation=cls.driver)
		cls.callers = {
			"guest": "Guest", "employee": cls.colleague, "manager": cls.manager_user,
			"store_hr": cls.store_hr, "hr_manager": cls.maker, "system_manager": cls.sysman,
		}
		frappe.db.commit()

	@classmethod
	def tearDownClass(cls):
		frappe.set_user("Administrator")
		frappe.db.set_value("Employee", cls.employee, "reports_to", cls._saved_reports_to,
		                    update_modified=False)
		frappe.delete_doc("User Permission", cls.store_perm, force=True, ignore_permissions=True)
		_clear_codes(cls.other_employee)
		for name in frappe.get_all(fc.DEVICE, {"employee": cls.other_employee}, pluck="name"):
			frappe.delete_doc(fc.DEVICE, name, force=True, ignore_permissions=True, ignore_on_trash=True)
		frappe.db.commit()
		super().tearDownClass()

	def setUp(self):
		super().setUp()
		# One row of each kind for the field worker: an app phone (joined the
		# real way), the used code behind it, its acknowledgement, and a count
		# row for today.
		self.token, out = self.app_phone()
		self.invite = out["invite"]
		self.phone = frappe.db.get_value(fc.DEVICE, {"token_hash": fc._hash(self.token)}, "name")
		self.ack = frappe.db.get_value(ACKNOWLEDGEMENT, {"device": self.phone}, "name")
		frappe.set_user("Administrator")
		from alvoraa_portal import field_app_housekeeping as hk
		self.count_row = hk._upsert_count_row(frappe.utils.today(), {"punches_saved": 1})
		frappe.db.commit()
		frappe.set_user("Guest")

	def tearDown(self):
		frappe.set_user("Administrator")
		frappe.db.delete(DAILY_COUNT, {"name": self.count_row})
		frappe.db.commit()
		super().tearDown()

	def rows_of(self, doctype):
		if doctype == DAILY_COUNT:
			return {"name": self.count_row}
		return {"employee": self.employee}

	# ── the doctypes: list, open, REST ───────────────────────────────────────

	def test_013_ac149_ac150_ac151_lists_by_caller(self):
		for caller, expected in LIST.items():
			for doctype in DOCTYPES:
				with self.subTest(caller=caller, doctype=doctype):
					frappe.set_user(self.callers[caller])
					try:
						if expected == "denied":
							with self.assertRaises(frappe.PermissionError):
								frappe.get_list(doctype, filters=self.rows_of(doctype), pluck="name")
							continue
						names = frappe.get_list(doctype, filters=self.rows_of(doctype), pluck="name")
						if expected == "none" and doctype != DAILY_COUNT:
							self.assertEqual(names, [], f"{caller} listed {doctype} rows of another company")
						else:
							self.assertTrue(names, f"{caller} saw no {doctype} rows")
					finally:
						frappe.db.rollback()
						frappe.set_user("Guest")

	def test_013_ac149_ac150_opening_one_row_by_name(self):
		rows = {fc.DEVICE: self.phone, INVITE: self.invite, ACKNOWLEDGEMENT: self.ack,
		        DAILY_COUNT: self.count_row}
		for caller, expected in LIST.items():
			for doctype, name in rows.items():
				with self.subTest(caller=caller, doctype=doctype):
					frappe.set_user(self.callers[caller])
					try:
						allowed = has_permission(doctype, "read", doc=name, print_logs=False)
						if expected == "rows" or (expected == "none" and doctype == DAILY_COUNT):
							self.assertTrue(allowed, f"{caller} cannot open {doctype} {name}")
						else:
							self.assertFalse(allowed, f"{caller} can open {doctype} {name}")
					finally:
						frappe.set_user("Guest")

	def test_013_ac149_the_store_hr_user_is_served_for_their_own_company(self):
		frappe.set_user("Administrator")
		own_phone, _t = _new_phone(self.other_employee, status="Active")
		frappe.db.commit()
		frappe.set_user(self.store_hr)
		try:
			self.assertEqual(frappe.get_list(fc.DEVICE, filters={"employee": self.other_employee},
			                                 pluck="name"), [own_phone.name])
			self.assertTrue(has_permission(fc.DEVICE, "read", doc=own_phone.name, print_logs=False))
		finally:
			frappe.set_user("Guest")

	def test_013_ac152_an_hr_manager_cannot_create_write_or_delete_a_code_reading_or_count(self):
		frappe.set_user(self.maker)
		try:
			for doctype, values in ((INVITE, {"employee": self.employee, "status": "Waiting",
			                                  "lifetime_hours": 1,
			                                  "expires_at": add_to_date(now(), hours=1),
			                                  "token_hash": "x" * 64}),
			                        (ACKNOWLEDGEMENT, {"employee": self.employee, "notice_version": "x",
			                                           "acknowledged_at": now(), "channel": "App"}),
			                        (DAILY_COUNT, {"on_date": "2020-01-01"})):
				with self.subTest(doctype=doctype, action="create"):
					with self.assertRaises(frappe.PermissionError):
						frappe.get_doc({"doctype": doctype, **values}).insert()
					frappe.db.rollback()
			for doctype, name in ((INVITE, self.invite), (ACKNOWLEDGEMENT, self.ack),
			                      (DAILY_COUNT, self.count_row)):
				with self.subTest(doctype=doctype, action="write"):
					self.assertFalse(has_permission(doctype, "write", doc=name, print_logs=False))
					with self.assertRaises(frappe.PermissionError):
						frappe.client.set_value(doctype, name, "modified_by", self.maker)
					frappe.db.rollback()
				with self.subTest(doctype=doctype, action="delete"):
					self.assertFalse(has_permission(doctype, "delete", doc=name, print_logs=False))
					with self.assertRaises(frappe.PermissionError):
						frappe.delete_doc(doctype, name)
					frappe.db.rollback()
					self.assertTrue(frappe.db.exists(doctype, name))
		finally:
			frappe.set_user("Guest")

	# ── the desk endpoints ───────────────────────────────────────────────────

	def test_013_ac149_ac150_desk_endpoints_by_caller(self):
		frappe.set_user("Administrator")
		waiting = _code_of(self.make())
		waiting_name = frappe.db.get_value(INVITE, {"token_hash": fc._hash(waiting)}, "name")
		frappe.db.commit()
		calls = {
			"E12 section": (desk.employee_app_section, {"employee": self.employee}),
			"E7 make": (join.make_code, {"employee": self.employee}),
			"E10 cancel": (join.cancel_code, {"invite": waiting_name}),
			"E11 block": (device_api.block_phone, {"device": self.phone, "reason": "Other"}),
		}
		# The refused callers first, all four endpoints each.
		for caller, expected in DESK.items():
			if expected != "denied":
				continue
			for label, (endpoint, args) in calls.items():
				with self.subTest(caller=caller, endpoint=label):
					with self.assertRaises(frappe.PermissionError):
						self.desk(endpoint, args, user=self.callers[caller])
					frappe.db.rollback()
		# nothing was cancelled or blocked by a refused caller
		self.assertEqual(frappe.db.get_value(INVITE, waiting_name, "status"), "Waiting")
		self.assertEqual(frappe.db.get_value(fc.DEVICE, self.phone, "status"), "Active")

		# The served callers: the section and a new code (which cancels the
		# waiting one - that is E7's rule, SEC-6). Cancelling and blocking are
		# proven for HR in the step-3 and step-5 modules.
		for caller, expected in DESK.items():
			if expected != "ok":
				continue
			for label in ("E12 section", "E7 make"):
				endpoint, args = calls[label]
				with self.subTest(caller=caller, endpoint=label):
					self.assertIsNotNone(self.desk(endpoint, args, user=self.callers[caller]),
					                     self.words())

	def test_013_ac149_the_store_hr_user_is_served_for_an_employee_of_their_own_company(self):
		out = self.section(employee=self.other_employee, user=self.store_hr)
		self.assertEqual(out["employee"]["name"], self.other_employee)

	def test_013_settings_info_is_for_hr_only(self):
		for caller, user in self.callers.items():
			with self.subTest(caller=caller):
				frappe.set_user(user)
				try:
					if caller in ("guest", "employee", "manager"):
						with self.assertRaises(frappe.PermissionError):
							fas.settings_info()
					else:
						self.assertIn("waiting_codes", fas.settings_info())
				finally:
					frappe.db.rollback()
					frappe.set_user("Guest")

	def test_013_us28_only_a_sign_in_with_an_employee_record_gets_its_own_records(self):
		for caller, user in self.callers.items():
			with self.subTest(caller=caller):
				frappe.set_user(user)
				try:
					frappe.local.form_dict = frappe._dict(
						cmd="alvoraa_portal.field_app_records.my_field_app_records")
					if caller == "manager":
						out = records.my_field_app_records()
						self.assertEqual(out["employee"], self.manager)
						self.assertEqual(out["phones"], [], "the manager saw a phone that is not theirs")
					else:
						with self.assertRaises(frappe.PermissionError):
							records.my_field_app_records()
				finally:
					frappe.db.rollback()
					frappe.set_user("Guest")

	# ── the phone endpoints: a session adds nothing ──────────────────────────

	def test_013_ac139_a_signed_in_session_with_no_secret_is_told_not_set_up(self):
		for caller in ("hr_manager", "system_manager", "employee"):
			for endpoint, args, code in ((fc.field_status, {"token": ""}, "NOT_SET_UP"),
			                             (fc.field_checkin, {"token": "", "log_type": "IN"}, "NOT_SET_UP"),
			                             (device_api.remove_my_phone, {"token": ""}, "NOT_SET_UP"),
			                             (join.acknowledge_notice, {"token": ""}, "NOT_SET_UP"),
			                             (join.check_code, {"code": "nothing"}, "QR_NOT_RECOGNISED")):
				with self.subTest(caller=caller, endpoint=endpoint.__name__):
					frappe.set_user(self.callers[caller])
					try:
						self.assertIsNone(self.call(endpoint, args))
						self.assertEqual(self.answer()[1], code)
					finally:
						frappe.set_user("Guest")
