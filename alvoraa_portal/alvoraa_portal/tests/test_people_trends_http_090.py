"""Slice 090 · the endpoint over real HTTP, and the log line read back from its file.

AC-11 to AC-15, AC-19, AC-20. Calling the function in process skips Frappe's own
request checks (method, CSRF, headers) and writes through a patchable logger, which is
how ALV-343 and ALV-391 went unseen. Here the request goes through Frappe's WSGI
application, the log is read from the file, and the password is generated.
"""

import json
import re
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils.password import update_password
from frappe.app import application
from werkzeug.test import Client

from alvoraa_portal import people_trends as pt
from alvoraa_portal.tests import test_people_trends_090 as base

METHOD = "/api/method/alvoraa_portal.people_trends.get_people_trends"


def setUpModule():
	base.setUpModule()


def tearDownModule():
	base.tearDownModule()


def parse(line):
	"""The logger puts a timestamp before the JSON."""
	return json.loads(line[line.index("{"):])


def log_lines():
	"""Every line the security logger has written, read from its file."""
	from hrms.alvoraa_hr_core.access import security_logger

	path = next(h.baseFilename for h in security_logger().handlers if hasattr(h, "baseFilename"))
	with open(path) as fh:
		return fh.read().splitlines()


class TestOverHttp(FrappeTestCase):
	def setUp(self):
		self.site = frappe.local.site
		self.host = {"Host": self.site}
		self.user = base.FIX["lead_retail"]
		self.password = frappe.generate_hash(length=16)
		update_password(self.user, self.password)
		frappe.db.commit()
		self.client = Client(application)

	def tearDown(self):
		# The WSGI application tears the request down; put the test's own state back.
		frappe.init(site=self.site)
		frappe.connect()
		frappe.set_user("Administrator")

	def login(self):
		r = self.client.post("/api/method/login", headers=self.host, data={"usr": self.user, "pwd": self.password})
		self.assertEqual(r.status_code, 200)

	def token(self):
		"""The page hands a signed-in person a CSRF token (www/hrms_employee.py)."""
		# Frappe saves the token in the session only when it is not under test
		# (`generate_csrf_token`), and without a saved token its check passes. So the
		# token is saved here the live way, or the check this test is about never runs.
		def live_token():
			frappe.local.session.data.csrf_token = frappe.generate_hash()
			frappe.local.session_obj.update(force=True)

		with patch("frappe.sessions.generate_csrf_token", live_token):
			html = self.client.get("/hrms-employee", headers=self.host).get_data(as_text=True)
		found = re.search(r'csrf_token\s*=\s*"([^"]+)"', html)
		self.assertTrue(found and found.group(1) not in ("None", "fetch"), "the page carries a real token")  # AC-13
		return found.group(1)

	def test_get_and_guest_are_refused(self):  # AC-11, AC-12
		self.assertNotEqual(self.client.post(METHOD, headers=self.host, data={"period": "30"}).status_code, 200)
		self.login()
		self.assertNotEqual(self.client.get(METHOD, headers=self.host).status_code, 200)

	def test_a_post_without_the_token_is_refused_and_with_it_is_served(self):  # AC-13, AC-14
		self.login()
		token = self.token()
		bad = self.client.post(METHOD, headers=self.host, data={"period": "30"})
		self.assertNotEqual(bad.status_code, 200)
		self.assertNotIn("headcount", bad.get_data(as_text=True))
		good = self.client.post(METHOD, headers={**self.host, "X-Frappe-CSRF-Token": token}, data={"period": "30"})
		self.assertEqual(good.status_code, 200)
		self.assertEqual(good.headers.get("Cache-Control"), "private, no-store")
		self.assertEqual(json.loads(good.get_data(as_text=True))["message"]["state"], "ok")

	def test_a_plan_without_analytics_is_refused(self):  # AC-15
		self.login()
		token = self.token()
		with patch("alvoraa_portal.subscription.has_feature", return_value=False):
			r = self.client.post(METHOD, headers={**self.host, "X-Frappe-CSRF-Token": token}, data={"period": "30"})
		self.assertNotEqual(r.status_code, 200)

	def test_the_log_line_is_in_the_file_and_holds_no_figure(self):  # AC-19
		self.login()
		token = self.token()
		before = len(log_lines())
		self.client.post(METHOD, headers={**self.host, "X-Frappe-CSRF-Token": token}, data={"period": "30"})
		new = [parse(x) for x in log_lines()[before:] if '"people_trends"' in x]
		self.assertEqual(len(new), 1)
		line = new[0]
		self.assertEqual((line["outcome"], line["role"], line["period"], line["user"]), ("shown", "leadership", 30, self.user))
		text = json.dumps(line)
		for secret in (base.fx.KAVYA, base.FIX["cl"]):
			self.assertNotIn(secret, text)
		# a headcount as a value (not as digits inside the time stamp or the millisecond count, which made this flaky)
		self.assertNotIn(43, line.values())
		self.assertNotIn("43", line.values())

	def test_a_refusal_writes_exactly_one_line(self):  # AC-16, AC-65
		self.login()
		token = self.token()
		before = len(log_lines())
		r = self.client.post(METHOD, headers={**self.host, "X-Frappe-CSRF-Token": token}, data={"period": "30", "company": base.fx.OTHER})
		self.assertNotEqual(r.status_code, 200)
		self.assertNotIn("headcount", r.get_data(as_text=True))
		new = [parse(x) for x in log_lines()[before:] if '"people_trends"' in x]
		self.assertEqual([(x["outcome"], x["rule"]) for x in new], [("refused", "PT-SCOPE")])
		self.assertNotIn(base.fx.OTHER, json.dumps(new))


class TestAFailureLeaksNothing(base.TrendsBase):
	def test_forced_exception_gives_the_generic_message(self):  # AC-20
		secret = "Secret Branch Name 123"
		with patch.object(pt, "_build", side_effect=RuntimeError(secret)):
			with self.assertRaises(frappe.ValidationError) as caught:
				base.call(self.lead_retail, period=30)
		self.assertIn("PT-LOAD", str(caught.exception))
		self.assertNotIn(secret, str(caught.exception))
		row = frappe.get_all("Error Log", filters={"method": ["like", "%People trends%"]}, fields=["error", "method"],
		                     order_by="creation desc", limit=1)
		self.assertTrue(row)
		self.assertNotIn(secret, json.dumps(row))
