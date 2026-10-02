"""Slice 057 (C): the founders' daily CRM summary.

Real site with Frappe CRM and frappe_whatsapp. Nothing reaches Meta: the WhatsApp
send (`WhatsAppMessage.notify`) is patched, and email goes to the queue only.
"""
import json
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, now_datetime, today

import alvoraa_portal.crm_summary as summary
from alvoraa_portal.tests.test_crm_step_tasks_057 import FIELD, ensure_lead_type_field, ensure_outgoing_account

TAG = "s057sum"
TEMPLATE = "s057_founder_summary"
FOUNDER_NO = "919800000057"
FOUNDER_MAIL = f"founder.{TAG}@example.com"
CUSTOMER_MAIL = f"customer.{TAG}@example.com"
CUSTOMER_PHONE = "9812300057"
CONF = {"whatsapp": [FOUNDER_NO], "email": [FOUNDER_MAIL], "template": f"{TEMPLATE}-en"}  # its autoname


def _wa_installed():
	return "frappe_whatsapp" in frappe.get_installed_apps()


class TestFounderSummary(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		if "crm" not in frappe.get_installed_apps():
			raise __import__("unittest").SkipTest("Frappe CRM is not installed on this site")
		ensure_lead_type_field()
		cls.outgoing = ensure_outgoing_account()
		if _wa_installed():
			if not frappe.db.exists("WhatsApp Account", "S057 Account"):
				frappe.get_doc({"doctype": "WhatsApp Account", "account_name": "S057 Account",
								"token": "stub", "url": "https://graph.facebook.com", "version": "v20.0",
								"phone_id": "s057phone", "business_id": "b", "app_id": "a",
								"webhook_verify_token": "s057verify", "is_default_outgoing": 1,
								"is_default_incoming": 1}).insert(ignore_permissions=True)
			if not frappe.db.exists("WhatsApp Templates", CONF["template"]):
				t = frappe.get_doc({"doctype": "WhatsApp Templates", "template_name": TEMPLATE,
									"actual_name": TEMPLATE, "language_code": "en", "category": "UTILITY",
									"template": "Amata CRM, {{1}}. New leads: {{2}}. By step: {{3}}. "
												"Overdue tasks: {{4}}. Deals won: {{5}}. Open: {{6}}",
									"sample_values": "1,2,3,4,5,6", "whatsapp_account": "S057 Account"})
				t.name = CONF["template"]
				t.db_insert()   # insert() would submit it to Meta
		cls.leads = []
		for kind, status in (("Client Project", "New"), ("Client Project", "Contacted"),
							 ("Partner Onboarding", "New")):
			cls.leads.append(frappe.get_doc({
				"doctype": "CRM Lead", "first_name": f"{TAG} Ravi", "last_name": "Customer",
				"email": CUSTOMER_MAIL if not cls.leads else None,
				"mobile_no": CUSTOMER_PHONE if not cls.leads else None,
				"status": status, FIELD: kind}).insert(ignore_permissions=True).name)
		cls.deal = frappe.get_doc({"doctype": "CRM Deal", "status": "Won", FIELD: "Client Project",
								   "deal_value": 250000}).insert(ignore_permissions=True).name
		cls.task = frappe.get_doc({"doctype": "CRM Task", "title": f"{TAG} overdue", "status": "Todo",
								   "due_date": add_days(now_datetime(), -2)}).insert(ignore_permissions=True).name
		frappe.db.commit()

	@classmethod
	def tearDownClass(cls):
		frappe.db.delete("CRM Task", {"title": ["like", f"{TAG}%"]})
		frappe.db.delete("CRM Lead", {"name": ["in", cls.leads]})
		frappe.db.delete("CRM Deal", {"name": cls.deal})
		if _wa_installed():
			frappe.db.delete("WhatsApp Message", {"to": FOUNDER_NO})
		if cls.outgoing:
			frappe.db.delete("Email Account", {"name": cls.outgoing})
		frappe.db.commit()
		super().tearDownClass()

	def run_with(self, conf, notify_error=None):
		sent = []

		def fake_notify(doc, data):
			if notify_error:
				raise notify_error
			sent.append(data)

		frappe.db.delete("Email Queue Recipient", {"recipient": FOUNDER_MAIL})
		with patch.dict(frappe.local.conf, {"crm_founder_summary": conf}), \
				patch("frappe_whatsapp.frappe_whatsapp.doctype.whatsapp_message.whatsapp_message.WhatsAppMessage.notify",
					  fake_notify):
			summary.send_daily()
		mails = frappe.get_all("Email Queue Recipient", filters={"recipient": FOUNDER_MAIL},
							   fields=["parent"], order_by="creation desc")
		return sent, mails

	def test_off_by_default_and_no_query(self):
		with patch.dict(frappe.local.conf, {"crm_founder_summary": None}), \
				patch.object(summary, "build") as build:
			summary.send_daily()
		self.assertFalse(build.called)

	def test_the_counts_by_type_and_step_overdue_and_won(self):
		v = summary.build()
		self.assertEqual(set(v), {"1", "2", "3", "4", "5", "6"})
		self.assertIn("Client Project 2", v["2"])
		self.assertIn("Partner Onboarding 1", v["2"])
		self.assertIn("Client Project:", v["3"])
		self.assertIn("Contacted 1", v["3"])
		self.assertGreaterEqual(int(v["4"]), 1)
		self.assertRegex(v["5"], r"2,?50,?000")
		self.assertTrue(v["6"].startswith("http"), "a full link, not a path")

	def test_no_customer_detail_and_no_line_break_in_any_variable(self):   # privacy pin
		v = summary.build()
		for key, value in v.items():
			self.assertNotIn("Ravi", value, key)
			self.assertNotIn("Customer", value, key)
			self.assertNotIn(CUSTOMER_MAIL, value, key)
			self.assertNotIn(CUSTOMER_PHONE, value, key)
			self.assertNotIn("\n", value, key)
			self.assertNotIn("    ", value, key)
			self.assertLessEqual(len(value), summary.MAX_VAR, key)

	def test_whatsapp_template_and_email_both_go(self):
		if not _wa_installed():
			self.skipTest("frappe_whatsapp is not installed")
		sent, mails = self.run_with(CONF)
		self.assertEqual(len(sent), 1)
		self.assertEqual(sent[0]["type"], "template")
		self.assertEqual(sent[0]["to"], FOUNDER_NO)
		params = [p["text"] for p in sent[0]["template"]["components"][0]["parameters"]]
		self.assertEqual(len(params), 6)
		self.assertTrue(mails, "the email copy is always sent")

	def test_a_whatsapp_failure_still_sends_the_email(self):
		if not _wa_installed():
			self.skipTest("frappe_whatsapp is not installed")
		sent, mails = self.run_with(CONF, notify_error=Exception("meta down"))
		self.assertEqual(sent, [])
		self.assertTrue(mails)
		self.assertTrue(frappe.db.exists("Error Log", {"method": ["like", "%founders' summary%"]}))

	def test_email_only_needs_no_template(self):
		sent, mails = self.run_with({"email": [FOUNDER_MAIL]})
		self.assertEqual(sent, [])
		self.assertTrue(mails)

	def test_it_runs_daily_at_nine(self):
		hooks = frappe.get_hooks("scheduler_events")
		self.assertIn("alvoraa_portal.crm_summary.send_daily", hooks["cron"]["0 9 * * *"])
