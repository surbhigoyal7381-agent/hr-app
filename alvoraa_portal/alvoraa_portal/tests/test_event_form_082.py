"""Slice 082: the public event form - the page, the guest save and the doors around it.

Real site, real Frappe CRM (CRM Lead, Web Form with CRM's `crm_published`).
Skipped on a site without CRM; CI installs CRM since this slice (OPS-36), so in CI
these run. Everything here carries the tag s082.

Pin tests (a bad merge that drops the feature fails these):
  test_082_pins_the_limit_route_hooks_and_codes
  test_082_ac5_one_send_saves_one_stamped_lead
  test_082_sec6_no_guest_row_on_user_employee_or_crm_lead
  test_082_priv5_an_erased_event_lead_leaves_no_copy
"""

import json
import re
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

import alvoraa_portal.event_form as ef
from alvoraa_portal import field_app_errors as errors
from alvoraa_portal import field_app_limits as limits
from alvoraa_portal import request_guard

TAG = "s082"
ROUTE = f"{TAG}-pune-dealer-meet"
CMD = "alvoraa_portal.event_form.save"
MANAGER = f"manager.{TAG}@example.com"
SALES = f"sales.{TAG}@example.com"
SALES2 = f"sales2.{TAG}@example.com"
PLAIN = f"plain.{TAG}@example.com"
NOTICE = "Collected by Sharma Events for this event. Kept 6 months. privacy@example.com"

ROWS = [
	{"fieldname": "first_name", "label": "Your name / आपका नाम", "fieldtype": "Data", "reqd": 1},
	{"fieldname": "mobile_no", "label": "Mobile number / मोबाइल नंबर", "fieldtype": "Data", "options": "Phone", "reqd": 1},
	{"fieldname": "email", "label": "Email (optional) / ईमेल (वैकल्पिक)", "fieldtype": "Data", "options": "Email"},
	{"fieldname": ef.RATING, "label": "How was the event?", "fieldtype": "Select"},
	{"fieldname": ef.COMMENT, "label": "Anything you want to tell us?", "fieldtype": "Small Text"},
	{"fieldname": ef.CONSENT_EVENT, "label": "I agree", "fieldtype": "Check", "reqd": 1, "description": NOTICE,
	 "default": "1"},
	{"fieldname": ef.CONSENT_NEWS, "label": "Send me news", "fieldtype": "Check", "default": "1"},
]

GOOD = {"first_name": "Rakesh Kulkarni", "mobile_no": "9822041012", "email": "",
        ef.RATING: "2 · Poor · खराब", ef.COMMENT: "Could not hear the speaker",
        ef.CONSENT_EVENT: 1, ef.CONSENT_NEWS: 0}


class _Req:
	method = "POST"
	host = "test_site"
	scheme = "http"
	url = "http://test_site/api/method/" + CMD
	headers: dict = {}  # noqa: RUF012


def ensure_user(email, roles):
	if not frappe.db.exists("User", email):
		frappe.get_doc({"doctype": "User", "email": email, "first_name": email.split("@")[0],
		                "send_welcome_email": 0}).insert(ignore_permissions=True)
	user = frappe.get_doc("User", email)
	user.set("roles", [])
	user.add_roles(*roles) if roles else user.save(ignore_permissions=True)


def make_form(route=ROUTE, rows=None, **values):
	"""A CRM form the way crm.api.form.save_form makes one."""
	if frappe.db.exists("Web Form", {"route": route}):
		frappe.delete_doc("Web Form", frappe.db.get_value("Web Form", {"route": route}), force=True,
		                  ignore_permissions=True)
	doc = frappe.get_doc({
		"doctype": "Web Form", "route": route,
		"title": values.pop("title", "Pune Dealer Meet, 14 Nov" if route == ROUTE else route),
		"doc_type": ef.LEAD, "module": ef.FORM_MODULE, "is_standard": 0, "login_required": 0,
		"allow_multiple": 1, "button_label": "Send my details / जानकारी भेजें",
		"introduction_text": "Takes about one minute.", "published": 1, "crm_published": 1,
		"web_form_fields": [dict(r) for r in (rows if rows is not None else ROWS)], **values,
	})
	doc.insert(ignore_permissions=True)
	return doc


def leads():
	return frappe.get_all(ef.LEAD, filters={ef.EVENT_FORM: ["like", f"%{TAG}%"]}, pluck="name") + \
		frappe.get_all(ef.LEAD, filters={"first_name": ["like", f"{TAG}%"]}, pluck="name")


class EventFormCase(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		if "crm" not in frappe.get_installed_apps():
			raise __import__("unittest").SkipTest("Frappe CRM is not installed on this site")
		frappe.set_user("Administrator")
		ef.ensure_fields()  # what after_migrate does on a real site
		ensure_user(MANAGER, ["Sales Manager"])
		ensure_user(SALES, ["Sales User"])
		ensure_user(SALES2, ["Sales User"])
		ensure_user(PLAIN, [])
		cls.form = make_form()
		frappe.db.commit()

	@classmethod
	def tearDownClass(cls):
		frappe.set_user("Administrator")
		for name in set(leads()):
			frappe.delete_doc(ef.LEAD, name, force=True, ignore_permissions=True)
		for name in frappe.get_all("Web Form", filters={"route": ["like", f"{TAG}%"]}, pluck="name"):
			frappe.delete_doc("Web Form", name, force=True, ignore_permissions=True)
		frappe.db.commit()
		super().tearDownClass()

	def setUp(self):
		frappe.set_user("Guest")
		frappe.local.request = _Req()
		frappe.local.request_ip = "203.0.113.82"
		frappe.cache.delete_keys(f"rl:{CMD}")

	def tearDown(self):
		frappe.local.request = None
		frappe.set_user("Administrator")
		frappe.form_dict.pop("route", None)

	def send(self, values=None, route=ROUTE, raw=None):
		"""Call the save as the page does. Returns (body, status, code, values)."""
		frappe.local.response = frappe._dict()
		frappe.clear_messages()
		args = {"route": route, "values": raw if raw is not None else json.dumps(values or GOOD)}
		frappe.local.form_dict = frappe._dict(args, cmd=CMD)
		body = ef.save(**args)
		if body:
			frappe.db.commit()  # what the request would do; a later refusal's rollback must not undo it
		r = frappe.local.response
		return body, r.get("http_status_code", 200), r.get("code"), r.get("values")

	def page(self, route=ROUTE, user="Guest", **params):
		"""GET the page as a browser would. Route rules only match with a real
		request environ (frappe.website.router.evaluate_dynamic_routes)."""
		from werkzeug.test import EnvironBuilder
		from werkzeug.wrappers import Request

		from frappe.website.serve import get_response_content

		frappe.set_user(user)
		frappe.local.request = Request(EnvironBuilder(path="/event-form/" + route, method="GET",
		                                              query_string=params).get_environ())
		frappe.local.form_dict = frappe._dict(params)
		frappe.local.response_headers = __import__("werkzeug").datastructures.Headers()
		html = get_response_content("event-form/" + route)
		frappe.local.request = _Req()
		return html

	def count(self):
		return frappe.db.count(ef.LEAD, {ef.EVENT_FORM: self.form.name})


# ── pins ────────────────────────────────────────────────────────────────────


class Pins(EventFormCase):
	def test_082_pins_the_limit_route_hooks_and_codes(self):
		self.assertEqual(ef.save.__alvoraa_limit__, (limits.EVENT_KEY, "route", 300, 60))
		# slice 013's endpoints keep their one-hour window (AC-26)
		from alvoraa_portal import notices
		self.assertEqual(notices.mark_all_seen.__alvoraa_limit__[3], 3600)
		self.assertEqual(errors.CODES["FIELD_INVALID"], (422, ("label",)))
		self.assertEqual(errors.CODES["FORM_CLOSED"], (404, ()))
		self.assertIn("POST", frappe.allowed_http_methods_for_whitelisted_func[ef.save])
		self.assertNotIn("GET", frappe.allowed_http_methods_for_whitelisted_func[ef.save])
		self.assertIn(ef.save, frappe.guest_methods)
		hooks = frappe.get_hooks()
		self.assertIn({"from_route": "/event-form/<route>", "to_route": "event-form"}, hooks.website_route_rules)
		self.assertIn("alvoraa_portal.event_form.after_lead_delete", hooks.doc_events[ef.LEAD]["after_delete"])
		self.assertIn("alvoraa_portal.event_form.refuse_guest_perm", hooks.doc_events["Custom DocPerm"]["validate"])
		self.assertIn("alvoraa_portal.event_form.ensure_fields", hooks.after_migrate)
		self.assertIn("alvoraa_portal.event_form.ensure_fields", hooks.after_install)
		self.assertIn("alvoraa_portal.event_form.on_app_install", hooks.after_app_install)
		self.assertIn("alvoraa_portal.crm_steps.on_app_install", hooks.after_app_install)

	def test_082_ac11_the_crm_fields_our_page_reads_still_exist(self):
		meta = frappe.get_meta("Web Form")
		for field in ("crm_published", "route", "doc_type", "module", "login_required", "title",
		              "introduction_text", "button_label", "success_message", "web_form_fields"):
			self.assertTrue(meta.has_field(field), field)
		row = frappe.get_meta("Web Form Field")
		for field in ("fieldname", "fieldtype", "label", "reqd", "options", "description", "hidden"):
			self.assertTrue(row.has_field(field), field)
		lead = frappe.get_meta(ef.LEAD)
		for field in ("first_name", "mobile_no", "email", *[f["fieldname"] for f in ef.FIELDS]):
			self.assertTrue(lead.has_field(field), field)


# ── the save ────────────────────────────────────────────────────────────────


class TheSave(EventFormCase):
	def test_082_ac5_one_send_saves_one_stamped_lead(self):
		before = self.count()
		body, status, code, _v = self.send()
		self.assertEqual((body, status, code), ({"saved": 1}, 200, None))
		self.assertEqual(self.count(), before + 1)  # already in the database: synchronous (AC-11)
		frappe.set_user("Administrator")
		lead = frappe.get_all(ef.LEAD, filters={ef.EVENT_FORM: self.form.name}, order_by="creation desc",
		                      limit=1, fields=["*"])[0]
		self.assertEqual(lead.first_name, "Rakesh Kulkarni")
		self.assertEqual(lead.mobile_no, "9822041012")
		self.assertEqual(lead.get(ef.RATING), "2 · Poor · खराब")
		self.assertEqual((lead.get(ef.CONSENT_EVENT), lead.get(ef.CONSENT_NEWS)), (1, 0))
		self.assertFalse(lead.lead_owner)
		self.assertEqual(lead.status, "New")

	def test_082_ac53_every_save_answers_the_same_body_with_no_lead_name(self):
		first = self.send()[0]
		second = self.send(dict(GOOD, first_name="Asha Patil"))[0]
		self.assertEqual(json.dumps(first), json.dumps(second))
		self.assertNotIn("CRM-LEAD", json.dumps(first))

	def test_082_ac52_a_key_the_form_does_not_ask_for_refuses_the_whole_save(self):
		before = self.count()
		for key in ("lead_owner", "status", "owner", "name", "naming_series", "_assign", "docstatus",
		            ef.EVENT_FORM, "unknown_key"):
			_b, status, code, _v = self.send(dict(GOOD, **{key: "Administrator"}))
			self.assertEqual((status, code), (400, "INVALID_REQUEST"), key)
		_b, status, code, _v = self.send(raw="not json")
		self.assertEqual((status, code), (400, "INVALID_REQUEST"))
		self.assertEqual(self.count(), before)

	def test_082_ac57_consent_to_this_event_is_required_on_the_server(self):
		before = self.count()
		_b, status, code, values = self.send(dict(GOOD, **{ef.CONSENT_EVENT: 0}))
		self.assertEqual((status, code, values), (422, "FIELD_INVALID", {"label": "I agree"}))
		self.assertEqual(self.count(), before)

	def test_082_ac17_ac56_a_bad_answer_names_its_label_and_nothing_else(self):
		cases = {
			"email": ("rakesh@", "Email (optional)"),
			"first_name": ("x" * 141, "Your name"),
			ef.COMMENT: ("y" * 2001, "Anything you want to tell us?"),
			ef.RATING: ("6 · Amazing", "How was the event?"),
			"mobile_no": ("call me", "Mobile number"),
		}
		for field, (value, label) in cases.items():
			_b, status, code, values = self.send(dict(GOOD, **{field: value}))
			self.assertEqual((status, code, values), (422, "FIELD_INVALID", {"label": label}), field)
			self.assertNotIn(value[:20], json.dumps(frappe.local.response, default=str))

	def test_082_ac56_html_typed_by_a_guest_cannot_run(self):
		text = "<img src=x onerror=alert(1)><script>alert(1)</script>"
		self.send(dict(GOOD, **{ef.COMMENT: text}))
		frappe.set_user("Administrator")
		stored = frappe.get_all(ef.LEAD, filters={ef.EVENT_FORM: self.form.name}, order_by="creation desc",
		                        limit=1, pluck=ef.COMMENT)[0]
		# Frappe itself cleans HTML out of a text field on save; nothing can run (SEC-9)
		self.assertNotIn("onerror", stored)
		self.assertNotIn("<script", stored)

	def test_082_ac58_a_crash_logs_the_route_hash_and_error_type_only(self):
		before = frappe.db.count("Error Log")
		from crm.fcrm.doctype.crm_lead.crm_lead import CRMLead
		with patch.object(CRMLead, "before_insert", side_effect=RuntimeError("Rakesh 9822041012")):
			_b, status, code, _v = self.send()
		self.assertEqual((status, code), (500, "SERVER_ERROR"))
		frappe.set_user("Administrator")
		rows = frappe.get_all("Error Log", fields=["method", "error"], order_by="creation desc",
		                      limit=frappe.db.count("Error Log") - before)
		self.assertTrue(rows, "the crash was not logged at all")
		for row in rows:
			text = f"{row.method} {row.error}"
			for value in ("Rakesh", "9822041012", "Could not hear", ROUTE):
				self.assertNotIn(value, text)
		self.assertIn("RuntimeError", rows[0].error)

	def test_082_ac68_one_log_line_per_refusal_with_no_answers(self):
		lines = []
		with patch.object(ef, "log") as logger:
			logger.return_value.info.side_effect = lines.append
			self.send(dict(GOOD, unknown_key="x"))
			self.send(dict(GOOD, email="rakesh@"))
			self.send(route=f"{TAG}-never-existed")
		self.assertEqual([re.search(r"reason=(\w+)", ln).group(1) for ln in lines],
		                 ["invalid", "invalid", "closed"])
		for line in lines:
			self.assertRegex(line, r"^refused reason=\w+ route=[0-9a-f]{16}$")
			self.assertNotIn(ROUTE, line)

	def test_082_ac25_ac27_the_301st_save_in_a_minute_is_refused_and_the_key_holds_the_hash(self):
		hashed = limits._hash(ROUTE)
		key = frappe.cache.make_key(f"rl:{CMD}:{hashed}:60")
		frappe.cache.setex(key, 60, 300)
		before = self.count()
		_b, status, code, values = self.send()
		self.assertEqual((status, code), (429, "TOO_MANY_TRIES"))
		self.assertLessEqual(values["retry_after_s"], 60)
		self.assertEqual(self.count(), before)
		self.assertNotIn(ROUTE.encode(), key)
		frappe.cache.delete(key)
		self.assertEqual(self.send()[1], 200)

	def test_082_ac60_the_request_guard_drops_permission_skips(self):
		frappe.local.form_dict = frappe._dict(ignore_permissions=1, ignore_user_permissions=1, route=ROUTE)
		request_guard.drop_permission_skips()
		self.assertNotIn("ignore_permissions", frappe.form_dict)
		self.assertNotIn("ignore_user_permissions", frappe.form_dict)


# ── what makes a form open (SEC-4, PRIV-2, PRIV-3b, the two new rules) ─────


class WhatOpens(EventFormCase):
	def closed(self, route, rows=None, **values):
		frappe.set_user("Administrator")
		make_form(route, rows, **values)
		frappe.db.commit()
		frappe.set_user("Guest")
		state = ef.form_state(route)
		before = frappe.db.count(ef.LEAD)
		_b, status, code, _v = self.send(route=route)
		self.assertEqual((status, code), (404, "FORM_CLOSED"), route)
		self.assertEqual(frappe.db.count(ef.LEAD), before)
		return state["problem"], state["label"]

	def field_of(self, fieldtype):
		meta = frappe.get_meta(ef.LEAD)
		return next(f for f in meta.fields if f.fieldtype == fieldtype and not f.hidden and not f.read_only
		            and f.fieldname not in ef.NEVER)

	def test_082_ac19_unknown_and_unpublished_answer_the_same(self):
		self.assertEqual(ef.form_state(f"{TAG}-never")["problem"], "missing")
		self.assertEqual(self.closed(f"{TAG}-draft", crm_published=0, published=0)[0], "draft")
		unknown = self.page(f"{TAG}-never")
		draft = self.page(f"{TAG}-draft")
		self.assertEqual(unknown, draft)
		self.assertIn("This form is not taking answers.", unknown)
		self.assertNotIn("Pune Dealer Meet", unknown)

	def test_082_ac21_login_only_and_non_crm_forms_never_open(self):
		self.assertEqual(self.closed(f"{TAG}-login", login_required=1)[0], "missing")
		self.assertEqual(self.closed(f"{TAG}-notcrm", module="Website")[0], "missing")

	def test_082_ac22_a_field_type_we_cannot_show_closes_the_form(self):
		link = self.field_of("Link")
		problem, label = self.closed(f"{TAG}-link", [*ROWS, {"fieldname": link.fieldname, "label": "Pick",
		                                                     "fieldtype": "Link"}])
		self.assertEqual((problem, label), ("link", "Pick"))
		for fieldtype in ("Currency", "Datetime", "Text Editor"):
			try:
				f = self.field_of(fieldtype)
			except StopIteration:
				continue
			self.assertEqual(self.closed(f"{TAG}-t", [*ROWS, {"fieldname": f.fieldname, "label": "X",
			                                                  "fieldtype": fieldtype}])[0], "type")
		# a row whose row type lies: what counts is the CRM Lead field's own type
		self.assertEqual(self.closed(f"{TAG}-lie", [*ROWS, {"fieldname": link.fieldname, "label": "Pick",
		                                                    "fieldtype": "Data"}])[0], "link")

	def test_082_ac23_sensitive_words_missing_consent_or_notice_close_the_form(self):
		sensitive = [dict(r) for r in ROWS]
		sensitive[2]["label"] = "Aadhaar number"
		self.assertEqual(self.closed(f"{TAG}-aadhaar", sensitive), ("sensitive", "Aadhaar number"))
		no_news = [r for r in ROWS if r["fieldname"] != ef.CONSENT_NEWS]
		self.assertEqual(self.closed(f"{TAG}-nonews", no_news)[0], "consent")
		no_notice = [dict(r, description="") if r["fieldname"] == ef.CONSENT_EVENT else r for r in ROWS]
		self.assertEqual(self.closed(f"{TAG}-nonotice", no_notice)[0], "consent")
		# "pan" is a whole word only: "Company name" does not close a form
		company = [dict(r) for r in ROWS]
		company[2]["label"] = "Company name"
		frappe.set_user("Administrator")
		make_form(f"{TAG}-company", company)
		self.assertIsNone(ef.form_state(f"{TAG}-company")["problem"])

	def test_082_new_rule_every_required_crm_field_must_be_on_the_form(self):
		no_name = [r for r in ROWS if r["fieldname"] != "first_name"]
		problem, label = self.closed(f"{TAG}-noname", no_name)
		self.assertEqual(problem, "required")
		self.assertEqual(label, frappe.get_meta(ef.LEAD).get_field("first_name").label)

	def test_082_a_layout_row_is_drawn_as_nothing_and_accepted(self):
		frappe.set_user("Administrator")
		make_form(f"{TAG}-layout", [{"fieldname": "section_break_seed1", "label": "Personal Details",
		                             "fieldtype": "Section Break"}, *ROWS])
		frappe.db.commit()
		self.assertIsNone(ef.form_state(f"{TAG}-layout")["problem"])
		self.assertEqual(self.send(route=f"{TAG}-layout")[1], 200)


# ── the page ───────────────────────────────────────────────────────────────


class ThePage(EventFormCase):
	def test_082_ac1_ac9_the_guest_page_draws_the_form_and_nothing_from_another_host(self):
		html = self.page()
		self.assertIn("Pune Dealer Meet, 14 Nov", html)
		self.assertIn("Send my details", html)
		self.assertNotIn("Discard", html)
		self.assertNotIn("fonts.googleapis", html)
		self.assertNotIn("<img", html)
		self.assertEqual(re.findall(r"https?://", html), [], "the page names another host")
		self.assertIn('type="tel"', html)
		self.assertIn('type="email"', html)
		self.assertEqual(html.count('<input type="radio" name="custom_event_rating"'), 5)  # five rows

	def test_082_ac57_both_ticks_load_unticked_whatever_the_default_or_url(self):
		html = self.page(**{ef.CONSENT_NEWS: "1", ef.CONSENT_EVENT: "1"})
		self.assertIsNone(re.search(r"<input[^>]*checked", html))

	def test_082_ac35_sec7_the_organiser_box_is_only_in_a_managers_page(self):
		for user in ("Guest", SALES, PLAIN):
			html = self.page(user=user)
			self.assertNotIn('id="orgbar"', html, user)
			self.assertNotIn("Download QR card", html, user)
		html = self.page(user=MANAGER)
		self.assertIn("You are signed in as an organiser.", html)
		self.assertIn("Download QR card", html)
		self.assertIn("Extra questions: 0.", html)

	def test_082_ac33_sec8_the_qr_holds_this_sites_own_address(self):
		html = self.page(user=MANAGER, site="other.alvoraa.co", host="evil.example")
		address = re.search(r"This form's address: (\S+)<br>", html).group(1)
		self.assertTrue(address.endswith("/event-form/" + ROUTE), address)
		self.assertRegex(address, r"^https?://localhost(:\d+)?/")  # the host the request came to
		self.assertNotIn("other.alvoraa.co", html)
		self.assertNotIn("evil.example", html)

	def test_082_the_dom_fixtures_carry_todays_script(self):
		"""event_form_082_dom_test.js drives two rendered pages kept in fixtures/.
		If the page's script changes, render them again (scratch script in 03 §6)
		or that test keeps passing against yesterday's code."""
		import os

		def script(html):
			body = html.split("<script>")[-1].split("</script>")[0]
			return re.sub(r"var T = .*?;\n", "", body, flags=re.S)

		here = os.path.join(os.path.dirname(__file__), "fixtures")
		for name, user in (("event_form_082_guest.html", "Guest"), ("event_form_082_manager.html", MANAGER)):
			with open(os.path.join(here, name), encoding="utf-8") as f:
				kept = f.read()
			self.assertEqual(script(kept), script(self.page(user=user)), name)

	def test_082_ac34_ac36_the_box_says_what_is_wrong_and_offers_no_qr(self):
		frappe.set_user("Administrator")
		make_form(f"{TAG}-boxdraft", crm_published=0, published=0)
		link = next(f for f in frappe.get_meta(ef.LEAD).fields if f.fieldtype == "Link" and f.fieldname not in ef.NEVER)
		make_form(f"{TAG}-boxlink", [*ROWS, {"fieldname": link.fieldname, "label": "Lead source", "fieldtype": "Link"}])
		frappe.db.commit()
		draft = self.page(f"{TAG}-boxdraft", user=MANAGER)
		self.assertIn("This form is a draft.", draft)
		self.assertNotIn("Download QR card", draft)
		broken = self.page(f"{TAG}-boxlink", user=MANAGER)
		self.assertIn("“Lead source” (it picks from a list of your staff)", broken)
		self.assertNotIn("Download QR card", broken)
		self.assertNotIn("Lead source", self.page(f"{TAG}-boxlink"))


# ── the doors (SEC-6, SEC-10, PRIV-5) ─────────────────────────────────────


class TheDoors(EventFormCase):
	def test_082_sec6_no_guest_row_on_user_employee_or_crm_lead(self):
		frappe.set_user("Administrator")
		for doctype in ("User", "Employee", ef.LEAD):
			if not frappe.db.exists("DocType", doctype):
				continue
			with self.assertRaises(frappe.PermissionError, msg=doctype):
				frappe.get_doc({"doctype": "Custom DocPerm", "parent": doctype, "parenttype": "DocType",
				                "parentfield": "permissions", "role": "Guest", "read": 1}).insert()
		# CRM's own one-click grant is stopped by the same hook
		from crm.api.form import grant_guest_link_access
		frappe.set_user(MANAGER)
		with self.assertRaises(frappe.PermissionError):
			grant_guest_link_access("User")
		frappe.set_user("Administrator")
		frappe.db.rollback()
		self.assertFalse(frappe.db.exists("Custom DocPerm", {"parent": "User", "role": "Guest"}))
		# a Guest row elsewhere is still allowed
		row = frappe.get_doc({"doctype": "Custom DocPerm", "parent": "Web Page", "parenttype": "DocType",
		                      "parentfield": "permissions", "role": "Guest", "read": 1}).insert()
		frappe.delete_doc("Custom DocPerm", row.name)  # its `delete` is a permission column

	def test_082_ac61_a_sales_user_reads_only_their_own_event_leads(self):
		self.send()
		self.send(dict(GOOD, first_name="Asha Patil"))
		frappe.set_user("Administrator")
		mine, other = frappe.get_all(ef.LEAD, filters={ef.EVENT_FORM: self.form.name}, order_by="creation desc",
		                             limit=2, pluck="name")
		from frappe.desk.form.assign_to import add
		frappe.local.request = None
		add({"doctype": ef.LEAD, "name": mine, "assign_to": [SALES]})
		frappe.set_user(SALES)
		seen = set(frappe.get_list(ef.LEAD, filters={ef.EVENT_FORM: self.form.name}, pluck="name"))
		self.assertIn(mine, seen)
		self.assertNotIn(other, seen)
		self.assertFalse(frappe.has_permission(ef.LEAD, "read", other))
		from frappe.desk.reportview import get_count
		frappe.local.form_dict = frappe._dict(doctype=ef.LEAD, filters=json.dumps({ef.EVENT_FORM: self.form.name}))
		self.assertEqual(get_count(), len(seen))
		frappe.set_user(SALES2)
		self.assertEqual(frappe.get_list(ef.LEAD, filters={"name": ["in", [mine, other]]}), [])
		for user in (PLAIN, "Guest"):
			frappe.set_user(user)
			with self.assertRaises(frappe.PermissionError, msg=user):
				frappe.get_list(ef.LEAD, filters={"name": mine})
		frappe.set_user(MANAGER)
		self.assertEqual(len(frappe.get_list(ef.LEAD, filters={"name": ["in", [mine, other]]})), 2)

	def test_082_priv5_an_erased_event_lead_leaves_no_copy(self):
		self.send()
		frappe.set_user("Administrator")
		name = frappe.get_all(ef.LEAD, filters={ef.EVENT_FORM: self.form.name}, order_by="creation desc",
		                      limit=1, pluck="name")[0]
		lead = frappe.get_doc(ef.LEAD, name)
		lead.add_comment("Comment", "Called back, wants a demo")
		lead.set(ef.CONSENT_NEWS, 1)
		lead.save()
		frappe.db.commit()
		self.assertTrue(frappe.db.count("Comment", {"reference_doctype": ef.LEAD, "reference_name": name,
		                                            "comment_type": "Comment"}))
		frappe.delete_doc(ef.LEAD, name)
		frappe.db.commit()
		for doctype, filters in (("Deleted Document", {"deleted_doctype": ef.LEAD, "deleted_name": name}),
		                         ("Version", {"ref_doctype": ef.LEAD, "docname": name}),
		                         ("Comment", {"reference_doctype": ef.LEAD, "reference_name": name})):
			self.assertEqual(frappe.db.count(doctype, filters), 0, doctype)

	def test_082_ac48_a_lead_without_an_event_stamp_keeps_frappes_copy(self):
		frappe.set_user("Administrator")
		lead = frappe.get_doc({"doctype": ef.LEAD, "first_name": f"{TAG} plain lead"}).insert()
		frappe.delete_doc(ef.LEAD, lead.name)
		frappe.db.commit()
		self.assertEqual(frappe.db.count("Deleted Document", {"deleted_doctype": ef.LEAD,
		                                                      "deleted_name": lead.name}), 1)
		frappe.db.delete("Deleted Document", {"deleted_doctype": ef.LEAD, "deleted_name": lead.name})
		frappe.db.commit()

	def test_082_ac50_consent_to_this_event_cannot_be_changed_after_saving(self):
		self.send()
		frappe.set_user("Administrator")
		name = frappe.get_all(ef.LEAD, filters={ef.EVENT_FORM: self.form.name}, order_by="creation desc",
		                      limit=1, pluck="name")[0]
		lead = frappe.get_doc(ef.LEAD, name)
		lead.set(ef.CONSENT_EVENT, 0)
		with self.assertRaises(frappe.CannotChangeConstantError):
			lead.save()


# ── the saved views the setup guide makes (AC-43, AC-44, AC-49) ───────────
# The views are configuration in CRM, not shipped records; these tests run the
# same filters and sort a view runs, so the guide's recipe is proved on a site.


class TheViews(EventFormCase):
	def lead(self, form, rating=None, news=0, days_old=0):
		doc = frappe.get_doc({"doctype": ef.LEAD, "first_name": f"{TAG} view", ef.EVENT_FORM: form,
		                      ef.RATING: rating, ef.CONSENT_EVENT: 1, ef.CONSENT_NEWS: news}).insert()
		if days_old:
			frappe.db.set_value(ef.LEAD, doc.name, "creation", frappe.utils.add_days(frappe.utils.now(), -days_old),
			                    update_modified=False)
		return doc.name

	def setUp(self):
		super().setUp()
		frappe.set_user("Administrator")

	def test_082_ac43_lowest_first_puts_every_1_before_every_2_and_drops_blanks(self):
		form = make_form(f"{TAG}-views").name
		for i in range(20):
			self.lead(form, ef.RATINGS[i % 5])
		for _ in range(5):
			self.lead(form)
		rows = frappe.get_list(ef.LEAD, filters={ef.EVENT_FORM: form, ef.RATING: ["is", "set"]},
		                       order_by=f"{ef.RATING} asc, creation asc", pluck=ef.RATING, limit=0)
		self.assertEqual(len(rows), 20)
		self.assertEqual([r[0] for r in rows], sorted(r[0] for r in rows))
		self.assertTrue(rows[0].startswith("1 · ") and rows[-1].startswith("5 · "))
		# without "is set" the five unrated leads sort FIRST ascending (01b EF13, now a fact)
		every = frappe.get_list(ef.LEAD, filters={ef.EVENT_FORM: form}, order_by=f"{ef.RATING} asc, creation asc",
		                        pluck=ef.RATING, limit=0)
		self.assertEqual([bool(r) for r in every[:5]], [False] * 5)
		self.assertTrue(all(every[5:]))

	def test_082_ac44_entries_per_form_counts_each_event(self):
		forms = [make_form(f"{TAG}-count{i}").name for i in range(3)]
		for form, n in zip(forms, (3, 1, 2), strict=True):
			for _ in range(n):
				self.lead(form, ef.RATINGS[0])
		got = frappe.get_list(ef.LEAD, filters={ef.EVENT_FORM: ["in", forms]},
		                      fields=[ef.EVENT_FORM, {"COUNT": "name", "as": "n"}], group_by=ef.EVENT_FORM)
		self.assertEqual({r[ef.EVENT_FORM]: r.n for r in got}, dict(zip(forms, (3, 1, 2), strict=True)))

	def test_082_ac49_due_for_deletion_lists_only_old_leads_without_news(self):
		form = make_form(f"{TAG}-old").name
		old = self.lead(form, days_old=210)
		self.lead(form, days_old=150)
		self.lead(form, news=1, days_old=210)
		due = frappe.get_list(ef.LEAD, pluck="name", filters={
			ef.EVENT_FORM: form, ef.CONSENT_NEWS: 0,
			"creation": ["<", frappe.utils.add_months(frappe.utils.today(), -6)]})
		self.assertEqual(due, [old])
