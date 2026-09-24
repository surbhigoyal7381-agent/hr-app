"""Slice 043, slice one - the whole pipeline on a real site with Frappe CRM.

The model is stubbed: every test patches `extract.call_model`, so nothing leaves the
machine and nothing is paid for. Everything else is real - the Email Account, the
Communications, CRM Lead, FCRM Note, the call log and the permission rules.

Skipped on a site without the CRM app (the shared local bench has none).
"""
import frappe
from frappe.tests.utils import FrappeTestCase
from unittest.mock import patch

import alvoraa_portal.ai_leads.extract as extract
import alvoraa_portal.ai_leads.guards as guards
import alvoraa_portal.ai_leads.intake as intake
import alvoraa_portal.ai_leads.setup as setup

ACCOUNT = "AI Test Sales 043"
MAILBOX = "sales@aitest043.example.com"
TAG = "aitest043"

GOOD = {"is_lead": True, "confidence": 0.93, "first_name": "Ravi", "last_name": "Salunkhe",
        "organization": "Konkan Shipbuilders Ltd", "job_title": "Purchase Head",
        "phone": "022-2756-4410", "website": "", "city": "", "country": "", "industry": "",
        "requirement": "Hull anodes for two tugs; sample and price per kg.",
        "reasons": ["Asks for a sample and a price."], "language": "en"}
BODY = "Please quote hull anodes, 25 kg, for two tugs.\nRavi Salunkhe\nTel 022-2756-4410"


class TestPipeline(FrappeTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        if "crm" not in frappe.get_installed_apps():
            raise __import__("unittest").SkipTest("Frappe CRM is not installed on this site")
        setup.ensure_fields()
        setup.ensure_status()
        setup.ensure_view()
        cls.service_user = setup.ensure_service_user()
        if not frappe.db.exists("Email Account", ACCOUNT):
            acc = frappe.get_doc({"doctype": "Email Account", "email_account_name": ACCOUNT,
                                  "email_id": MAILBOX, "enable_incoming": 1})
            acc.db_insert()
        frappe.db.set_value("Email Account", ACCOUNT, {guards.INTAKE_FIELD: 1,
                                                        guards.SINCE_FIELD: "2000-01-01 00:00:00"})
        frappe.db.commit()
        # As the sweep reads it from the database, "read since" included.
        cls.acc = frappe._dict(name=ACCOUNT, email_id=MAILBOX,
                               **{guards.SINCE_FIELD: "2000-01-01 00:00:00"})

    @classmethod
    def tearDownClass(cls):
        comms = frappe.get_all("Communication", filters={"email_account": ACCOUNT}, pluck="name")
        leads = frappe.get_all("CRM Lead", filters={"email": ["like", f"%{TAG}%"]}, pluck="name")
        for lead in leads:
            frappe.db.delete("FCRM Note", {"reference_docname": lead})
            frappe.db.delete("CRM Lead", {"name": lead})
        frappe.db.delete(intake.LOG, {"communication": ["in", comms or ["-"]]})
        frappe.db.delete("Communication", {"email_account": ACCOUNT})
        frappe.db.delete("Email Account", {"name": ACCOUNT})
        for u in frappe.get_all("User", filters={"name": ["like", f"%{TAG}%"]}, pluck="name"):
            frappe.delete_doc("User", u, force=True, ignore_permissions=True)
        frappe.db.commit()
        super().tearDownClass()

    # ── helpers ──────────────────────────────────────────────────────────────
    def email(self, sender, subject="RFQ: hull anodes", body=BODY, name="Ravi Salunkhe"):
        c = frappe.get_doc({"doctype": "Communication", "communication_medium": "Email",
                            "communication_type": "Communication", "sent_or_received": "Received",
                            "sender": sender, "sender_full_name": name, "subject": subject,
                            "content": body, "text_content": body, "email_account": ACCOUNT})
        c.insert(ignore_permissions=True)
        frappe.db.commit()
        return c.name

    def run_one(self, comm, reply=GOOD, conf=None, error=None):
        conf = dict({"ai_lead_intake_api_key": "stub"}, **(conf or {}))
        effect = extract.ExtractionError(error) if error else None
        with patch.object(extract, "call_model",
                          side_effect=effect,
                          return_value=(dict(reply), "claude-haiku-4-5", 900, 120)) as called:
            intake.process_one(comm, self.acc, conf=conf)
        log = frappe.get_all(intake.LOG, filters={"communication": comm},
                             fields=["name", "outcome", "reason", "lead", "called", "attempts",
                                     "input_tokens", "confidence"])
        return (log[0] if log else None), called

    # ── the tests ────────────────────────────────────────────────────────────
    def test_an_enquiry_becomes_a_lead_with_its_email(self):
        comm = self.email(f"ravi@{TAG}-a.example.com")
        log, called = self.run_one(comm)
        self.assertEqual(log.outcome, "Lead created")
        self.assertEqual((log.called, log.input_tokens), (1, 900))
        lead = frappe.get_doc("CRM Lead", log.lead)
        self.assertEqual(lead.status, "New")
        self.assertEqual(lead.email, f"ravi@{TAG}-a.example.com", "the header, never the model")
        self.assertEqual((lead.first_name, lead.organization), ("Ravi", "Konkan Shipbuilders Ltd"))
        self.assertIn("2756", (lead.mobile_no or "") + (lead.phone or ""))
        self.assertEqual(lead.alvoraa_ai_created, 1)
        self.assertEqual(lead.alvoraa_ai_mailbox, ACCOUNT)
        self.assertEqual(lead.owner, self.service_user)
        c = frappe.db.get_value("Communication", comm, ["reference_doctype", "reference_name"], as_dict=True)
        self.assertEqual((c.reference_doctype, c.reference_name), ("CRM Lead", lead.name))
        self.assertTrue(frappe.db.exists("FCRM Note", {"reference_docname": lead.name}))

    def test_the_same_email_twice_makes_one_lead(self):
        comm = self.email(f"twice@{TAG}-b.example.com")
        self.run_one(comm)
        _, called = self.run_one(comm)
        self.assertFalse(called.called, "the claimed email is not sent again")
        self.assertEqual(frappe.db.count("CRM Lead", {"email": f"twice@{TAG}-b.example.com"}), 1)

    def test_a_doubtful_answer_becomes_a_needs_review_lead(self):
        comm = self.email(f"maybe@{TAG}-c.example.com")
        log, _ = self.run_one(comm, reply=dict(GOOD, confidence=0.6))
        self.assertEqual(log.outcome, "Needs review")
        lead = frappe.get_doc("CRM Lead", log.lead)
        self.assertEqual(lead.status, intake.NEEDS_REVIEW)
        self.assertEqual(lead.alvoraa_ai_needs_review, 1)

    def test_an_invented_phone_is_dropped_and_sent_to_review(self):
        comm = self.email(f"phone@{TAG}-d.example.com")
        log, _ = self.run_one(comm, reply=dict(GOOD, phone="+91 99999 88888"))
        self.assertEqual(log.outcome, "Needs review")
        lead = frappe.get_doc("CRM Lead", log.lead)
        self.assertFalse(lead.mobile_no or lead.phone)

    def test_not_an_enquiry_makes_no_lead(self):
        comm = self.email(f"vendor@{TAG}-e.example.com", subject="Our new ingot price list")
        log, _ = self.run_one(comm, reply=dict(GOOD, is_lead=False, confidence=0.95,
                                              reasons=["A private remark the log must not keep."]))
        self.assertEqual(log.outcome, "Not a lead")
        self.assertFalse(log.lead)
        self.assertNotIn("private remark", log.reason or "", "the log stays content-free")

    def test_machine_mail_never_reaches_the_model(self):
        comm = self.email(f"noreply@{TAG}-f.example.com")
        log, called = self.run_one(comm)
        self.assertEqual((log.outcome, log.reason), ("Skipped", "automatic sender"))
        self.assertFalse(called.called)

    def test_a_known_sender_is_attached_not_duplicated(self):
        first = self.email(f"repeat@{TAG}-g.example.com")
        self.run_one(first)
        second = self.email(f"repeat@{TAG}-g.example.com", subject="Re: RFQ")
        log, called = self.run_one(second)
        self.assertEqual(log.outcome, "Lead updated")
        self.assertFalse(called.called)
        self.assertEqual(frappe.db.count("CRM Lead", {"email": f"repeat@{TAG}-g.example.com"}), 1)

    def test_failure_is_retried_then_becomes_a_header_only_lead(self):
        comm = self.email(f"down@{TAG}-h.example.com")
        log, _ = self.run_one(comm, error="service unreachable")
        self.assertEqual((log.outcome, log.attempts), ("Failed", 1))
        frappe.db.set_value(intake.LOG, log.name, "attempts", intake.MAX_ATTEMPTS)
        frappe.db.commit()
        with patch.object(guards, "_feature_on", return_value=True):   # retries re-check the mailbox
            intake.retry_failed(5)
        after = frappe.db.get_value(intake.LOG, log.name, ["outcome", "lead"], as_dict=True)
        self.assertEqual(after.outcome, "Needs review")                        # SEC-26
        self.assertEqual(frappe.db.get_value("CRM Lead", after.lead, "status"), intake.NEEDS_REVIEW)

    def test_over_the_cap_an_email_waits_for_tomorrow(self):                  # AC-30
        comm = self.email(f"cap@{TAG}-i.example.com")
        with patch.object(intake, "daily_cap", return_value=0):
            log, called = self.run_one(comm)
        self.assertIsNone(log, "the claim is released, so tomorrow's sweep takes it")
        self.assertFalse(called.called)
        self.assertEqual(frappe.db.count("CRM Lead", {"email": f"cap@{TAG}-i.example.com"}), 0)

    def _sweep(self, enabled):
        conf = {"ai_lead_intake_enabled": 1 if enabled else 0, "ai_lead_intake_api_key": "stub"}
        with patch.dict(frappe.conf, conf), \
                patch("alvoraa_portal.subscription.has_feature", return_value=True), \
                patch.object(guards, "_feature_on", return_value=True), \
                patch.object(extract, "call_model",
                             return_value=(dict(GOOD), "claude-haiku-4-5", 900, 120)) as called:
            intake.sweep()
        return called

    def test_the_sweep_does_the_work_when_on_and_none_when_off(self):
        comm = self.email(f"sweep@{TAG}-k.example.com")
        called = self._sweep(enabled=False)
        self.assertFalse(called.called)
        self.assertFalse(frappe.db.exists(intake.LOG, {"communication": comm}), "off means untouched")
        called = self._sweep(enabled=True)
        self.assertTrue(called.called)
        self.assertEqual(frappe.db.get_value(intake.LOG, {"communication": comm}, "outcome"), "Lead created")

    def test_a_mailbox_keeps_being_read_after_its_oldest_emails_are_done(self):  # review P1-2
        for i in range(6):
            done = self.email(f"noreply{i}@{TAG}-l.example.com")
            self.run_one(done)                              # skipped: machine sender
        fresh = self.email(f"fresh@{TAG}-l.example.com")
        with patch.object(extract, "call_model", return_value=(dict(GOOD), "claude-haiku-4-5", 1, 1)):
            intake.process_account(self.acc, 1)
        self.assertEqual(frappe.db.get_value(intake.LOG, {"communication": fresh}, "outcome"), "Lead created")

    def test_an_error_after_the_claim_ends_as_failed_not_stuck(self):           # review P1-1
        comm = self.email(f"boom@{TAG}-m.example.com")
        with patch.object(extract, "call_model", return_value=(dict(GOOD), "claude-haiku-4-5", 1, 1)), \
                patch.object(intake, "make_lead", side_effect=RuntimeError("db went away")):
            intake.safely(comm, self.acc)
        row = frappe.db.get_value(intake.LOG, {"communication": comm}, ["outcome", "reason"], as_dict=True)
        self.assertEqual(row.outcome, "Failed")
        self.assertEqual(row.reason, "error: RuntimeError", "the type only, never the message")

    def test_the_needs_review_list_is_public(self):
        view = frappe.db.get_value("CRM View Settings", {"label": "Needs review", "dt": "CRM Lead"},
                                   ["public", "user"], as_dict=True)
        self.assertEqual((view.public, view.user or ""), (1, ""))

    def test_a_default_mailbox_cannot_be_ticked(self):                         # V-1 on the real doc
        doc = frappe.get_doc("Email Account", ACCOUNT)
        doc.default_incoming = 1
        with patch.object(guards, "_feature_on", return_value=True):
            with self.assertRaises(frappe.ValidationError):
                guards.validate_email_account(doc)

    def test_an_hr_user_cannot_hold_the_mailbox(self):                         # V-6 mirror
        user = frappe.get_doc({"doctype": "User", "email": f"hrperson@{TAG}.example.com",
                               "first_name": "HR", "send_welcome_email": 0,
                               "roles": [{"role": "HR Manager"}],
                               "user_emails": [{"email_account": ACCOUNT}]})
        with self.assertRaises(frappe.ValidationError):
            guards.validate_user(user)

    def test_an_employee_cannot_list_the_mailbox(self):                        # AC-40 / OQ-8
        email = f"employee@{TAG}.example.com"
        if not frappe.db.exists("User", email):
            frappe.get_doc({"doctype": "User", "email": email, "first_name": "Emp",
                            "send_welcome_email": 0, "roles": [{"role": "Employee"}]}).insert(
                ignore_permissions=True)
        self.email(f"secret@{TAG}-j.example.com")
        frappe.set_user(email)
        try:
            rows = frappe.get_list("Communication", filters={"email_account": ACCOUNT}, pluck="name")
        finally:
            frappe.set_user("Administrator")
        self.assertEqual(rows, [])
