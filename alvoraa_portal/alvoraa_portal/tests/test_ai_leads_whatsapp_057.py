"""Slice 057 (B): a forwarded WhatsApp message becomes a CRM Lead.

Real site with Frappe CRM and frappe_whatsapp. The model is stubbed (as in 043):
nothing leaves the machine. The webhook tests go through frappe_whatsapp's own
`post()` with a real werkzeug request, so the signature check sees exactly what
Meta's call would give it.
"""
import hashlib
import hmac
import json
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils.password import set_encrypted_password
from werkzeug.test import EnvironBuilder
from werkzeug.wrappers import Request

import alvoraa_portal.ai_leads.extract as extract
import alvoraa_portal.ai_leads.intake as intake
import alvoraa_portal.ai_leads.setup as setup
import alvoraa_portal.ai_leads.whatsapp as wa
from alvoraa_portal import subscription as _sub

TAG = "s057wa"
ACCOUNT = "S057 WA Intake"
PHONE_ID = "s057waphone"
SECRET = "s057-app-secret"
FORWARDER_NO = "919800005701"
STRANGER_NO = "919800005799"
VINDA = f"vinda.{TAG}@example.com"
PROFILE = "Forwarder Profile Name"
FEATURES = sorted(set(_sub.enabled_features({})) | {"crm", "crm_ai_intake"})
CONF = {"ai_lead_intake_enabled": 1, "ai_lead_intake_api_key": "stub", "features": FEATURES,
		wa.FORWARDERS: {"+91 98000 05701": VINDA}}
TEXT = ("Hotel Sea Breeze in Kankanady, Mangaluru. Bathroom leaks on two floors, wants a quote "
		"for waterproofing. Contact Prakash Shetty, manager.")
GOOD = {"is_lead": True, "confidence": 0.93, "first_name": "Prakash", "last_name": "Shetty",
		"organization": "Hotel Sea Breeze", "job_title": "Manager", "phone": "", "website": "",
		"city": "Mangaluru", "country": "", "industry": "",
		"requirement": "Waterproofing quote for bathroom leaks on two floors.",
		"reasons": ["Asks for a quote."], "language": "en"}


class TestWhatsAppIntake(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		apps = frappe.get_installed_apps()
		if "crm" not in apps or "frappe_whatsapp" not in apps:
			raise __import__("unittest").SkipTest("Frappe CRM and Frappe WhatsApp are needed")
		if not frappe.db.exists("User", VINDA):
			u = frappe.new_doc("User")
			u.update({"email": VINDA, "first_name": "Vinda", "send_welcome_email": 0})
			u.append("roles", {"role": "Sales User"})
			u.insert(ignore_permissions=True)
		# Adds the secret field, status, source and service user. Site config is not
		# written: the tests pass their own, and the test site stays switched off.
		with patch.dict(frappe.conf, {"features": FEATURES}), patch.object(setup, "update_site_config"):
			setup.switch_on_whatsapp({FORWARDER_NO: VINDA})
		if not frappe.db.exists("WhatsApp Account", ACCOUNT):
			frappe.get_doc({"doctype": "WhatsApp Account", "account_name": ACCOUNT, "token": "stub",
							"url": "https://graph.facebook.com", "version": "v20.0", "phone_id": PHONE_ID,
							"business_id": "b", "app_id": "a", "webhook_verify_token": "v"}).insert(ignore_permissions=True)
		set_encrypted_password("WhatsApp Account", ACCOUNT, SECRET, wa.SECRET_FIELD)
		frappe.db.commit()

	@classmethod
	def tearDownClass(cls):
		msgs = frappe.get_all("WhatsApp Message", filters={"whatsapp_account": ACCOUNT}, pluck="name")
		meta_ids = frappe.get_all("WhatsApp Message", filters={"whatsapp_account": ACCOUNT}, pluck="message_id")
		leads = frappe.get_all("CRM Lead", filters={"lead_owner": VINDA}, pluck="name")
		leads += frappe.get_all("CRM Lead", filters={"email": ["like", f"%{TAG}%"]}, pluck="name")
		frappe.db.delete("FCRM Note", {"reference_docname": ["in", leads or ["-"]]})
		frappe.db.delete("CRM Lead", {"name": ["in", leads or ["-"]]})
		frappe.db.delete(intake.LOG, {"whatsapp_message": ["in", meta_ids or ["-"]]})
		frappe.db.delete("WhatsApp Message", {"name": ["in", msgs or ["-"]]})
		frappe.db.commit()
		super().tearDownClass()

	# ── helpers ──────────────────────────────────────────────────────────────
	def message(self, text=TEXT, sender=FORWARDER_NO, meta_id=None):
		"""An incoming text, stored as frappe_whatsapp stores it (intake off, so no hook work)."""
		return frappe.get_doc({"doctype": "WhatsApp Message", "type": "Incoming", "from": sender,
							   "message": text, "message_id": meta_id or f"wamid.{frappe.generate_hash(length=12)}",
							   "content_type": "text", "profile_name": PROFILE,
							   "whatsapp_account": ACCOUNT}).insert(ignore_permissions=True).name

	def run_job(self, name, reply=GOOD, error=None, conf=None):
		effect = extract.ExtractionError(error) if error else None
		# As Guest: the job is queued from Meta's webhook call, so it runs as Guest on the server.
		frappe.set_user("Guest")
		try:
			with patch.dict(frappe.conf, dict(CONF, **(conf or {}))), \
					patch.object(extract, "call_model", side_effect=effect,
								 return_value=(dict(reply), "claude-haiku-4-5", 700, 90)) as called:
				wa.process(name)
		finally:
			frappe.set_user("Administrator")
		log = frappe.db.get_value(intake.LOG, {"whatsapp_message": self.meta_id(name)},
								  ["name", "outcome", "reason", "lead", "called"], as_dict=True)
		return log, called

	@staticmethod
	def meta_id(name):
		return frappe.db.get_value("WhatsApp Message", name, "message_id")

	def webhook(self, sender=FORWARDER_NO, signature="good", conf=None, msg_type="text"):
		"""Meta's POST, through frappe_whatsapp's own handler."""
		message = {"from": sender, "id": f"wamid.{frappe.generate_hash(length=12)}", "type": msg_type,
				   "context": {"forwarded": True}, "text": {"body": TEXT}}
		if msg_type != "text":
			message[msg_type] = {"emoji": "x", "message_id": "m"}
		payload = {"object": "whatsapp_business_account", "entry": [{"changes": [{"field": "messages", "value": {
			"metadata": {"phone_number_id": PHONE_ID}, "contacts": [{"profile": {"name": PROFILE}}],
			"messages": [message]}}]}]}
		body = json.dumps(payload).encode()
		headers = {}
		if signature == "good":
			headers["X-Hub-Signature-256"] = "sha256=" + hmac.new(SECRET.encode(), body, hashlib.sha256).hexdigest()
		elif signature:
			headers["X-Hub-Signature-256"] = signature
		req = Request(EnvironBuilder(method="POST", data=body, headers=headers,
									 content_type="application/json").get_environ())
		from frappe_whatsapp.utils.webhook import post
		before = (getattr(frappe.local, "request", None), frappe.local.form_dict)
		frappe.set_user("Guest")             # Meta's call is not logged in (set_user clears form_dict)
		frappe.local.request, frappe.local.form_dict = req, frappe._dict(payload)
		try:
			with patch.dict(frappe.conf, dict(CONF, **(conf or {}))), patch("frappe.enqueue") as queued:
				post()
		finally:
			frappe.set_user("Administrator")
			frappe.local.request, frappe.local.form_dict = before
		return queued, message["id"]

	# ── the webhook gate ─────────────────────────────────────────────────────
	def test_a_signed_forward_from_a_listed_number_is_queued(self):
		queued, mid = self.webhook()
		name = frappe.db.get_value("WhatsApp Message", {"message_id": mid})
		self.assertEqual(queued.call_count, 1)
		self.assertEqual(queued.call_args.args[0], "alvoraa_portal.ai_leads.whatsapp.process")
		self.assertEqual(queued.call_args.kwargs["message"], name)
		self.assertTrue(queued.call_args.kwargs["enqueue_after_commit"])

	def test_no_or_a_wrong_signature_does_nothing(self):                       # fails closed
		for sig in (None, "sha256=" + "0" * 64, "sha256=bad"):
			queued, mid = self.webhook(signature=sig)
			self.assertFalse(queued.called, sig)
			self.assertTrue(frappe.db.exists("WhatsApp Message", {"message_id": mid}),
							"frappe_whatsapp still stores it, as before")

	def test_no_app_secret_means_nothing_is_trusted(self):
		try:
			frappe.db.delete("__Auth", {"doctype": "WhatsApp Account", "name": ACCOUNT, "fieldname": wa.SECRET_FIELD})
			queued, _ = self.webhook()
			self.assertFalse(queued.called)
		finally:
			set_encrypted_password("WhatsApp Account", ACCOUNT, SECRET, wa.SECRET_FIELD)

	def test_a_number_not_on_the_list_is_left_alone(self):
		queued, mid = self.webhook(sender=STRANGER_NO)
		self.assertFalse(queued.called)
		name = frappe.db.get_value("WhatsApp Message", {"message_id": mid})
		self.assertFalse(frappe.db.exists(intake.LOG, {"whatsapp_message": mid}))
		log, called = self.run_job(name)                     # even if a job were queued by hand
		self.assertIsNone(log)
		self.assertFalse(called.called)

	def test_off_switch_and_non_text_do_nothing(self):
		queued, _ = self.webhook(conf={"ai_lead_intake_enabled": 0})
		self.assertFalse(queued.called)
		queued, _ = self.webhook(conf={wa.FORWARDERS: {}})
		self.assertFalse(queued.called)
		queued, _ = self.webhook(msg_type="reaction")
		self.assertFalse(queued.called)

	def test_an_outgoing_message_is_ignored(self):
		doc = frappe._dict(type="Outgoing", content_type="text", whatsapp_account=ACCOUNT, name="x",
						   **{"from": FORWARDER_NO})
		doc.get = doc.__getitem__
		with patch.dict(frappe.conf, CONF), patch("frappe.enqueue") as queued:
			wa.on_whatsapp_message(doc)
		self.assertFalse(queued.called)

	# ── the job ──────────────────────────────────────────────────────────────
	def test_a_sure_enquiry_becomes_a_lead_owned_by_the_forwarder(self):
		name = self.message()
		log, called = self.run_job(name)
		self.assertEqual((log.outcome, log.called), ("Lead created", 1))
		lead = frappe.get_doc("CRM Lead", log.lead)
		self.assertEqual((lead.status, lead.lead_owner, lead.source), ("New", VINDA, "WhatsApp"))
		self.assertEqual((lead.first_name, lead.organization), ("Prakash", "Hotel Sea Breeze"))
		self.assertNotIn("5701", (lead.mobile_no or "") + (lead.phone or ""), "never the forwarder's number")
		ref = frappe.db.get_value("WhatsApp Message", name, ["reference_doctype", "reference_name"], as_dict=True)
		self.assertEqual((ref.reference_doctype, ref.reference_name), ("CRM Lead", lead.name))
		note = frappe.db.get_value("FCRM Note", {"reference_docname": lead.name}, "content")
		self.assertIn("Forwarded on WhatsApp by Vinda", note)
		self.assertIn("+91 98…", note)
		self.assertNotIn(FORWARDER_NO, note, "the number is masked")
		self.assertNotIn("the email", note)

	def test_the_model_never_sees_the_forwarder(self):                        # privacy pin
		name = self.message(TEXT + " PAN ABCDE1234F.")
		_, called = self.run_job(name)
		prompt = called.call_args.args[0]
		for secret in (FORWARDER_NO, "98000 05701", "9800005701", PROFILE, "Vinda", VINDA):
			self.assertNotIn(secret, prompt)
		self.assertNotIn("ABCDE1234F", prompt, "identity numbers are blanked, as for email")
		self.assertIn("Kankanady", prompt)

	def test_an_unsure_answer_becomes_a_needs_review_lead(self):
		log, _ = self.run_job(self.message(), reply=dict(GOOD, confidence=0.6))
		self.assertEqual(log.outcome, "Needs review")
		self.assertEqual(frappe.db.get_value("CRM Lead", log.lead, "status"), intake.NEEDS_REVIEW)

	def test_not_an_enquiry_makes_no_lead(self):
		log, _ = self.run_job(self.message("Happy Diwali to the whole Amata team and families!"),
							  reply=dict(GOOD, is_lead=False, confidence=0.95))
		self.assertEqual((log.outcome, log.lead), ("Not a lead", None))

	def test_ai_down_still_gives_a_needs_review_lead_at_once(self):
		log, _ = self.run_job(self.message(), error="service unreachable")
		self.assertEqual(log.outcome, "Needs review")
		lead = frappe.get_doc("CRM Lead", log.lead)
		self.assertEqual((lead.status, lead.lead_owner), (intake.NEEDS_REVIEW, VINDA))
		self.assertEqual(frappe.db.get_value("WhatsApp Message", {"reference_name": lead.name}, "message"), TEXT,
						 "the text is on the lead's WhatsApp tab")

	def test_the_same_message_twice_makes_one_lead(self):
		name = self.message()
		self.run_job(name)
		log, called = self.run_job(name)
		self.assertFalse(called.called)
		self.assertEqual(frappe.db.count(intake.LOG, {"whatsapp_message": self.meta_id(name)}), 1)

	def test_a_meta_resend_makes_one_lead(self):                               # review M1
		"""Meta delivers at least once; frappe_whatsapp stores each delivery as a new row."""
		mid = f"wamid.{frappe.generate_hash(length=12)}"
		first, again = self.message(meta_id=mid), self.message(meta_id=mid)
		self.assertNotEqual(first, again)
		self.run_job(first)
		_, called = self.run_job(again)
		self.assertFalse(called.called, "no second AI call")
		self.assertEqual(frappe.db.count(intake.LOG, {"whatsapp_message": mid}), 1)
		self.assertEqual(frappe.db.count("CRM Lead", {"lead_owner": VINDA, "first_name": "Prakash",
													  "creation": [">=", frappe.db.get_value(
														  "WhatsApp Message", first, "creation")]}), 1)

	def test_a_short_message_never_reaches_the_model(self):
		log, called = self.run_job(self.message("hi, call me"))
		self.assertEqual(log.outcome, "Skipped")
		self.assertFalse(called.called)

	def test_a_known_email_is_attached_to_its_lead(self):
		known = frappe.get_doc({"doctype": "CRM Lead", "first_name": "Known", "email": f"known@{TAG}.example.com"}
							   ).insert(ignore_permissions=True).name
		log, called = self.run_job(self.message(TEXT + f" Mail: Known@{TAG}.example.com"))
		self.assertEqual((log.outcome, log.lead), ("Lead updated", known))
		self.assertFalse(called.called, "no AI money spent on a known contact")

	def test_a_known_phone_is_attached_to_its_lead(self):
		known = frappe.get_doc({"doctype": "CRM Lead", "first_name": "Known", "mobile_no": "9845005777",
								"email": f"phone@{TAG}.example.com"}).insert(ignore_permissions=True).name
		log, _ = self.run_job(self.message(TEXT + " Call 98450 05777"), reply=dict(GOOD, phone="98450 05777"))
		self.assertEqual((log.outcome, log.lead), ("Lead updated", known))

	def test_the_forwarders_own_number_is_dropped(self):
		log, _ = self.run_job(self.message(TEXT + " My number 98000 05701"), reply=dict(GOOD, phone="98000 05701"))
		lead = frappe.get_doc("CRM Lead", log.lead)
		self.assertFalse(lead.mobile_no or lead.phone)

	def test_the_cap_is_shared_with_email_and_still_gives_a_lead(self):
		with patch.object(intake, "daily_cap", return_value=0):
			log, called = self.run_job(self.message())
		self.assertFalse(called.called)
		self.assertEqual(log.outcome, "Needs review")
		self.assertTrue(log.lead)

	def test_the_email_retry_never_picks_up_a_whatsapp_row(self):
		log, _ = self.run_job(self.message(), error="service unreachable")
		frappe.db.set_value(intake.LOG, log.name, "outcome", "Failed")
		# It would be skipped later for having no mailbox, but it would still fill one
		# of the sweep's 25 places on every run, for ever. So it must not be read at all.
		with patch.object(frappe.db, "get_value", wraps=frappe.db.get_value) as read:
			intake.retry_failed(50)
		looked_up = [c.args[1] for c in read.call_args_list if c.args and c.args[0] == "Email Account"]
		self.assertNotIn(None, looked_up)

	def test_switch_on_refuses_a_bad_forwarder_list(self):
		with patch.dict(frappe.conf, {"features": FEATURES}):
			with self.assertRaisesRegex(frappe.ValidationError, "country code"):
				setup.switch_on_whatsapp({"98000": VINDA})
			with self.assertRaisesRegex(frappe.ValidationError, "not an enabled user"):
				setup.switch_on_whatsapp({FORWARDER_NO: f"ghost.{TAG}@example.com"})
