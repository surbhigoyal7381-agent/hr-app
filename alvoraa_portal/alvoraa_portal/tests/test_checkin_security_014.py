"""Slice 014: field check-in keeps photos, positions and names out of the logs.

Frappe logs a failed request with its fields (Error Log `metadata`, and
`frappe.log`) and, for anything that reaches its request handler, with the local
variables of every frame. It hides only field names containing password,
secret, token, key or pwd. So a punch's photo text and coordinates, and an
employee's name, went straight into the logs:

  * whenever a photo was rejected - a normal request, no crash needed;
  * on any server error in a field check-in endpoint;
  * on dev, where developer mode logs every refusal too.

Every test here names the fix it guards. If a merge drops the wrapper, these
fail instead of the logs quietly filling up again.

Markers are made-up strings that cannot occur by accident, so "the marker is
nowhere in the Error Log" is a real test rather than a lucky one.
"""

import json
import secrets
from unittest import mock

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import now

from alvoraa_portal import field_checkin as fc
from alvoraa_portal import subscription as sub

PHOTO_MARKER = "ZQXPHOTO014MARKER"
LAT_MARKER = "12.3456789"
LON_MARKER = "76.5432101"
NAME_MARKER = "Zqxnamefourteen"
EMP_EMAIL = "zqx.checkin014@example.com"


def _company():
	return frappe.db.get_value("Company", {}, "name")


class CheckinLogCase(FrappeTestCase):
	"""An Active employee with an Active phone, ready to punch."""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		frappe.set_user("Administrator")
		cls.employee = cls._employee()
		cls.token = secrets.token_urlsafe(32)
		cls.device = frappe.get_doc({
			"doctype": fc.DEVICE,
			"employee": cls.employee,
			"employee_name": NAME_MARKER,
			"status": "Active",
			"token_hash": fc._hash(cls.token),
		}).insert(ignore_permissions=True).name
		# The endpoints commit part-way, which would commit our fixtures anyway.
		# Committing here makes that explicit, and tearDownClass removes them.
		frappe.db.commit()

	@classmethod
	def tearDownClass(cls):
		frappe.set_user("Administrator")
		for name in frappe.get_all("Employee Checkin", {"employee": cls.employee}, pluck="name"):
			for f in frappe.get_all("File", {"attached_to_doctype": "Employee Checkin",
			                                 "attached_to_name": name}, pluck="name"):
				frappe.delete_doc("File", f, force=True, ignore_permissions=True)
			frappe.delete_doc("Employee Checkin", name, force=True, ignore_permissions=True)
		for name in frappe.get_all(fc.DEVICE, {"employee": cls.employee}, pluck="name"):
			frappe.delete_doc(fc.DEVICE, name, force=True, ignore_permissions=True)
		frappe.db.commit()
		super().tearDownClass()

	@classmethod
	def _employee(cls):
		existing = frappe.db.get_value("Employee", {"user_id": EMP_EMAIL, "status": "Active"})
		if existing:
			return existing
		if not frappe.db.exists("User", EMP_EMAIL):
			frappe.get_doc({"doctype": "User", "email": EMP_EMAIL, "first_name": NAME_MARKER,
			                "send_welcome_email": 0}).insert(ignore_permissions=True)
		return frappe.get_doc({
			"doctype": "Employee", "first_name": NAME_MARKER, "company": _company(),
			"date_of_birth": "1990-01-01", "date_of_joining": "2015-01-01",
			"gender": frappe.db.get_value("Gender", {}, "name") or "Male",
			"status": "Active", "user_id": EMP_EMAIL,
		}).insert(ignore_permissions=True).name

	def setUp(self):
		frappe.set_user("Guest")
		self._features = frappe.conf.get("features")
		frappe.conf["features"] = list(sub.FEATURES)
		self._dev_mode = frappe.conf.get("developer_mode")
		frappe.local.response = frappe._dict()
		frappe.clear_messages()
		self.started = now()

	def tearDown(self):
		if self._features is None:
			frappe.conf.pop("features", None)
		else:
			frappe.conf["features"] = self._features
		frappe.conf["developer_mode"] = self._dev_mode
		frappe.local.form_dict = frappe._dict()
		frappe.local.response = frappe._dict()
		frappe.clear_messages()
		frappe.set_user("Administrator")

	# ── helpers ────────────────────────────────────────────────────────────

	def punch_args(self, **overrides):
		args = {
			"token": self.token, "log_type": "IN",
			"latitude": LAT_MARKER, "longitude": LON_MARKER, "accuracy": "8",
			"photo": "data:image/jpeg;base64," + PHOTO_MARKER,
		}
		args.update(overrides)
		return args

	def call(self, endpoint, args):
		"""Call an endpoint the way Frappe's handler does: the request fields sit
		in form_dict and are also passed as keyword arguments."""
		frappe.local.form_dict = frappe._dict(args, cmd=f"alvoraa_portal.field_checkin.{endpoint.__name__}")
		return endpoint(**args)

	def new_error_logs(self):
		"""Error Log rows written since the test started, from field check-in.

		Filtered so a background job on the test site cannot make a test fail."""
		rows = frappe.get_all(
			"Error Log", filters={"creation": [">=", self.started]},
			fields=["name", "method", "error", "metadata"])
		return [r for r in rows
		        if "field_checkin" in (r.metadata or "") + (r.error or "")
		        or (r.method or "").startswith("Field check-in")]

	def assert_no_personal_data(self, text, where):
		for marker in (PHOTO_MARKER, LAT_MARKER, LON_MARKER, NAME_MARKER, self.token, self.employee):
			self.assertNotIn(marker, text or "", f"{marker!r} leaked into {where}")

	def assert_logs_clean(self):
		for row in frappe.get_all("Error Log", filters={"creation": [">=", self.started]},
		                          fields=["name", "method", "error", "metadata"]):
			for field in ("method", "error", "metadata"):
				self.assert_no_personal_data(row.get(field), f"Error Log {row.name}.{field}")
		# And whatever Frappe would log next in this request, from its own
		# metadata builder, is clean too.
		from frappe.utils.error import get_error_metadata
		self.assert_no_personal_data(get_error_metadata(), "Frappe's error metadata")
		from frappe.utils.logger import sanitized_dict
		self.assert_no_personal_data(str(sanitized_dict(frappe.local.form_dict)), "frappe.log form dict")


class TheWrapperIsInPlace(CheckinLogCase):
	def test_014_endpoints_are_wrapped(self):
		"""All three guest endpoints carry the wrapper, above the plan gate and
		the rate limit, and name the fields they remove."""
		expected = {
			"register_device": ("employee_id", "device_label", "platform"),
			"field_checkin": ("photo", "latitude", "longitude", "accuracy", "captured_at"),
			"field_status": (),
		}
		for name, fields in expected.items():
			# functools.wraps copies attributes outwards, so the INNERMOST function
			# holding an attribute is the decorator that set it.
			chain, fn = [], getattr(fc, name)
			while fn is not None:
				chain.append(fn)
				fn = getattr(fn, "__wrapped__", None)
			private = [i for i, f in enumerate(chain) if hasattr(f, "__alvoraa_private_request__")]
			gate = [i for i, f in enumerate(chain) if hasattr(f, "__alvoraa_feature__")]
			self.assertTrue(private, f"{name} is not wrapped by _private_request")
			self.assertEqual(chain[private[-1]].__alvoraa_private_request__, fields, name)
			self.assertTrue(gate, f"{name} lost its plan gate")
			self.assertLess(private[-1], gate[-1],
			                f"{name}: _private_request must sit above requires_feature")


class NothingPersonalReachesTheLogs(CheckinLogCase):
	def test_014_rejected_photo_leaves_no_photo_or_gps_in_error_log(self):
		"""The path that needed no crash: a photo that will not decode is logged
		by _attach_photo. The punch still lands; the log row holds no photo text
		and no coordinates."""
		out = self.call(fc.field_checkin, self.punch_args())
		self.assertEqual((out or {}).get("status"), "ok")
		rows = [r for r in self.new_error_logs() if (r.method or "").startswith("Field check-in photo")]
		self.assertTrue(rows, "the rejected photo should still be logged, by check-in name")
		self.assert_logs_clean()

	def test_014_server_error_in_punch_leaks_nothing(self):
		"""An unexpected failure answers a plain 500 and writes one Error Log row
		that says where, never with what - not even the exception's own text."""
		with mock.patch.object(fc, "_refuse_duplicate",
		                       side_effect=RuntimeError("boom " + NAME_MARKER)):
			out = self.call(fc.field_checkin, self.punch_args())

		self.assertIsNone(out)
		self.assertEqual(frappe.local.response.get("http_status_code"), 500)
		rows = [r for r in self.new_error_logs() if (r.method or "").startswith(fc._SERVER_ERROR_TITLE)]
		self.assertEqual(len(rows), 1)
		self.assertIn("RuntimeError", rows[0].error)
		self.assertIn("field_checkin.py", rows[0].error)
		self.assert_logs_clean()
		self.assertIn("Something went wrong on our side", json.dumps(frappe.local.message_log))

	def test_014_refusal_in_developer_mode_leaks_nothing(self):
		"""Dev runs developer mode, where Frappe logs every refusal with local
		variables. No refusal may leave the endpoint as an exception."""
		frappe.conf["developer_mode"] = 1
		out = self.call(fc.field_checkin, self.punch_args(log_type="SIDEWAYS"))
		self.assertIsNone(out)
		self.assertEqual(frappe.local.response.get("http_status_code"), 417)
		self.assertEqual(self.new_error_logs(), [])
		self.assert_logs_clean()

	def test_014_personal_fields_leave_form_dict(self):
		self.call(fc.field_checkin, self.punch_args(log_type="SIDEWAYS"))
		for field in ("photo", "latitude", "longitude", "accuracy", "captured_at"):
			self.assertNotIn(field, frappe.local.form_dict)

	def test_014_field_status_error_leaks_no_name(self):
		with mock.patch.object(fc, "_shift_location_for",
		                       side_effect=RuntimeError("boom " + NAME_MARKER)):
			out = self.call(fc.field_status, {"token": self.token})
		self.assertIsNone(out)
		self.assertEqual(frappe.local.response.get("http_status_code"), 500)
		self.assert_logs_clean()


class RefusalsStillReadTheSame(CheckinLogCase):
	def test_014_refusal_response_shape_unchanged(self):
		"""www/field-checkin.html matches on the sentence in _server_messages and
		on a non-2xx status. Both must survive the wrapper."""
		self.call(fc.field_checkin, self.punch_args(log_type="SIDEWAYS"))
		self.assertEqual(frappe.local.response.get("http_status_code"), 417)
		self.assertEqual(frappe.local.response.get("exc_type"), "ValidationError")
		self.assertIn("Invalid check-in type", json.dumps(frappe.local.message_log))

	def test_014_bad_token_is_still_a_401(self):
		self.call(fc.field_status, {"token": "short"})
		self.assertEqual(frappe.local.response.get("http_status_code"), 401)
		self.assertIn("not set up", json.dumps(frappe.local.message_log))

	def test_014_plan_gate_is_still_a_403(self):
		frappe.conf["features"] = []
		self.call(fc.field_status, {"token": self.token})
		self.assertEqual(frappe.local.response.get("http_status_code"), 403)


class OldCopiesAreRedacted(FrappeTestCase):
	"""The one-time patch blanks personal values in Error Log rows written before
	the fix, keeps the rows, and leaves every other Error Log alone."""

	def _row(self, method, error, metadata):
		doc = frappe.get_doc({"doctype": "Error Log", "method": method,
		                      "error": error, "metadata": metadata})
		doc.insert(ignore_permissions=True)
		return doc.name

	def test_014_redaction_patch(self):
		from alvoraa_portal.patches.v1_0 import redact_field_checkin_error_logs as patch

		metadata = json.dumps({
			"type": "http_request", "method": "POST",
			"path": "/api/method/alvoraa_portal.field_checkin.field_checkin",
			"form_dict": {"cmd": "alvoraa_portal.field_checkin.field_checkin",
			              "token": "********", "log_type": "IN",
			              "photo": "data:image/jpeg;base64," + PHOTO_MARKER,
			              "latitude": LAT_MARKER, "longitude": LON_MARKER},
			"user": "Guest",
		})
		error = "\n".join([
			"Traceback with variables (most recent call last):",
			'  File "apps/alvoraa_portal/alvoraa_portal/field_checkin.py", line 293, in field_checkin',
			"    _attach_photo(doc, photo)",
			f"      photo = 'data:image/jpeg;base64,{PHOTO_MARKER}'",
			f"      emp = {{'name': 'HR-EMP-1', 'employee_name': '{NAME_MARKER}'}}",
			"      src = 'first line",
			f"      {NAME_MARKER} second line'",
			"builtins.RuntimeError: boom",
		])
		leaky = self._row("Field check-in photo could not be decoded for EMP-CKIN-1", error, metadata)
		other_error = '  File "apps/frappe/x.py", line 1, in y\n      value = 42'
		other = self._row("Some other failure", other_error, json.dumps({"form_dict": {"photo": "keep"}}))

		patch.execute()

		row = frappe.db.get_value("Error Log", leaky, ["method", "error", "metadata"], as_dict=True)
		self.assertIsNotNone(row, "the row is kept")
		for marker in (PHOTO_MARKER, LAT_MARKER, LON_MARKER, NAME_MARKER):
			self.assertNotIn(marker, row.error)
			self.assertNotIn(marker, row.metadata)
		self.assertIn("field_checkin.py\", line 293", row.error, "where it failed is kept")
		self.assertIn("builtins.RuntimeError: boom", row.error)
		self.assertEqual(json.loads(row.metadata)["form_dict"]["log_type"], "IN")

		untouched = frappe.db.get_value("Error Log", other, ["error", "metadata"], as_dict=True)
		self.assertEqual(untouched.error, other_error)
		self.assertIn("keep", untouched.metadata)

		# Safe to run twice.
		before = frappe.db.get_value("Error Log", leaky, ["error", "metadata"], as_dict=True)
		patch.execute()
		after = frappe.db.get_value("Error Log", leaky, ["error", "metadata"], as_dict=True)
		self.assertEqual(before, after)

	def test_014_patch_is_registered(self):
		import os

		import alvoraa_portal
		path = os.path.join(os.path.dirname(alvoraa_portal.__file__), "patches.txt")
		with open(path, encoding="utf-8") as f:
			self.assertIn("alvoraa_portal.patches.v1_0.redact_field_checkin_error_logs",
			              f.read().split())
