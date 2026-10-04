"""Slice 057 (A): a CRM lead or deal reaching a status creates that step's tasks.

Real site, real CRM: CRM Lead, CRM Deal, CRM Task, Email Template, Communication.
Skipped on a site without Frappe CRM. Everything here carries the tag S057.
"""
from unittest.mock import patch

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, today

import alvoraa_portal.crm_steps as crm_steps

TAG = "s057"
RULE = crm_steps.RULE
FIELD = crm_steps.LEAD_TYPE_FIELD
NITIN = f"nitin.{TAG}@example.com"
SALES = f"sales.{TAG}@example.com"
TEMPLATE = "S057 Partner welcome"


def ensure_lead_type_field():
	"""What Customize Form makes from the set-up guide, on both doctypes."""
	field = {"fieldname": FIELD, "label": "Lead Type", "fieldtype": "Select",
			 "options": "\nClient Project\nPartner Onboarding", "insert_after": "status"}
	create_custom_fields({"CRM Lead": [field], "CRM Deal": [field]}, ignore_validate=True, update=True)


def ensure_user(email, roles):
	if not frappe.db.exists("User", email):
		u = frappe.new_doc("User")
		u.email = email
		u.first_name = email.split(".")[0].title()
		u.send_welcome_email = 0
		for r in roles:
			u.append("roles", {"role": r})
		u.insert(ignore_permissions=True)
	return email


def ensure_outgoing_account():
	"""A default outgoing mailbox, as every tenant has. db_insert: no SMTP test.
	Returns its name if this test made it, so the test removes only its own."""
	if frappe.db.exists("Email Account", {"default_outgoing": 1, "enable_outgoing": 1}):
		return None
	acc = frappe.get_doc({"doctype": "Email Account", "email_account_name": "S057 Outgoing",
						  "email_id": f"crm.{TAG}@example.com", "enable_outgoing": 1, "default_outgoing": 1,
						  "smtp_server": "localhost", "no_smtp_authentication": 1})
	acc.db_insert()
	frappe.clear_cache()
	return acc.name


class TestStepTasks(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		if "crm" not in frappe.get_installed_apps():
			raise __import__("unittest").SkipTest("Frappe CRM is not installed on this site")
		ensure_lead_type_field()
		cls.deals = []
		ensure_user(NITIN, ["Sales User"])
		ensure_user(SALES, ["Sales User"])
		if not frappe.db.exists("Email Template", TEMPLATE):
			frappe.get_doc({"doctype": "Email Template", "name": TEMPLATE,
							"subject": "Welcome, {{ first_name }}",
							"response": "<p>Dear {{ first_name }}, our partner pack is attached.</p>"}).insert()
		cls.outgoing = ensure_outgoing_account()
		crm_steps.ensure_task_label_field()   # what after_migrate does on a real site
		cls.org = f"S057 Builders {frappe.generate_hash(length=4)}"
		frappe.get_doc({"doctype": "CRM Organization", "organization_name": cls.org}).insert()
		cls.rules = [
			cls.rule("CRM Lead", "Partner Onboarding", "Qualified", "Send partner pack", 2, TEMPLATE),
			cls.rule("CRM Lead", "Client Project", "Qualified", "Schedule site visit", 3),
			cls.rule("CRM Deal", "Client Project", "Proposal/Quotation", "Send the proposal", 1),
		]
		frappe.db.commit()

	@classmethod
	def tearDownClass(cls):
		leads = frappe.get_all("CRM Lead", filters={"first_name": ["like", f"{TAG}%"]}, pluck="name")
		deals = cls.deals
		for dt, names in (("CRM Lead", leads), ("CRM Deal", deals)):
			frappe.db.delete("CRM Task", {"reference_doctype": dt, "reference_docname": ["in", names or ["-"]]})
			frappe.db.delete("Communication", {"reference_doctype": dt, "reference_name": ["in", names or ["-"]]})
			frappe.db.delete(dt, {"name": ["in", names or ["-"]]})
		frappe.db.delete(RULE, {"task_title": ["in", [r.task_title for r in cls.rules]]})
		frappe.db.delete("CRM Task", {"title": "S057 hand-made"})
		frappe.db.delete("CRM Organization", {"name": cls.org})
		if cls.outgoing:
			frappe.db.after_commit.reset()   # the step emails' send-on-commit needs the account
			frappe.db.delete("Email Account", {"name": cls.outgoing})
		frappe.db.commit()
		super().tearDownClass()

	@staticmethod
	def rule(applies_to, lead_type, status, title, days, template=None):
		doc = frappe.get_doc({"doctype": RULE, "applies_to": applies_to, "lead_type": lead_type,
							  "status": status, "task_title": title, "assign_to": NITIN,
							  "due_in_days": days, "email_template": template})
		return doc.insert()

	def lead(self, lead_type, email=None, status="New"):
		return frappe.get_doc({"doctype": "CRM Lead", "first_name": f"{TAG} {frappe.generate_hash(length=5)}",
							   "email": email, "status": status, FIELD: lead_type}).insert(ignore_permissions=True)

	def tasks(self, doc):
		return frappe.get_all("CRM Task", filters={"reference_doctype": doc.doctype, "reference_docname": doc.name},
							  fields=["title", "assigned_to", "due_date", "status"])

	def move(self, doc, status):
		doc.reload()
		doc.status = status
		doc.save(ignore_permissions=True)
		return doc

	# ── the tests ────────────────────────────────────────────────────────────
	def test_a_matching_step_makes_one_task_for_the_right_person(self):
		lead = self.move(self.lead("Client Project"), "Qualified")
		tasks = self.tasks(lead)
		self.assertEqual(len(tasks), 1)
		self.assertEqual((tasks[0].title, tasks[0].assigned_to, tasks[0].status),
						 ("Schedule site visit", NITIN, "Todo"))
		self.assertEqual(str(tasks[0].due_date), f"{add_days(today(), 3)} 18:00:00")
		self.assertTrue(frappe.db.exists("ToDo", {"reference_type": "CRM Task", "allocated_to": NITIN,
												  "status": "Open"}), "CRM assigns the task itself")

	def test_the_other_lead_types_steps_do_not_fire(self):
		lead = self.move(self.lead("Partner Onboarding"), "Qualified")
		self.assertEqual([t.title for t in self.tasks(lead)], ["Send partner pack"])

	def test_a_lead_without_a_type_gets_nothing(self):
		lead = self.move(self.lead(None), "Qualified")
		self.assertEqual(self.tasks(lead), [])

	def test_a_save_without_a_status_change_makes_nothing(self):
		lead = self.move(self.lead("Client Project"), "Qualified")
		lead.reload()
		lead.job_title = "Owner"
		lead.save(ignore_permissions=True)
		self.assertEqual(len(self.tasks(lead)), 1)

	def test_moving_back_and_forth_makes_no_second_open_task(self):
		lead = self.move(self.lead("Client Project"), "Qualified")
		self.move(lead, "Contacted")
		self.move(lead, "Qualified")
		self.assertEqual(len(self.tasks(lead)), 1)
		# Once the first is done, reaching the step again is a new piece of work.
		frappe.db.set_value("CRM Task", {"reference_docname": lead.name}, "status", "Done")
		self.move(lead, "Contacted")
		self.move(lead, "Qualified")
		self.assertEqual(len(self.tasks(lead)), 2)

	def test_the_deal_path(self):
		deal = frappe.get_doc({"doctype": "CRM Deal", "status": "Qualification", FIELD: "Client Project"})
		deal.insert(ignore_permissions=True)
		self.deals.append(deal.name)
		self.assertEqual(self.tasks(deal), [])
		self.move(deal, "Proposal/Quotation")
		self.assertEqual([t.title for t in self.tasks(deal)], ["Send the proposal"])

	def test_a_template_email_goes_to_the_lead_and_shows_on_its_timeline(self):
		lead = self.move(self.lead("Partner Onboarding", email=f"partner.{TAG}@example.com"), "Qualified")
		comm = frappe.get_all("Communication", filters={"reference_doctype": "CRM Lead", "reference_name": lead.name},
							  fields=["recipients", "subject", "content", "sent_or_received"])
		self.assertEqual(len(comm), 1)
		self.assertIn(f"partner.{TAG}@example.com", comm[0].recipients)
		self.assertEqual(comm[0].sent_or_received, "Sent")
		self.assertIn(lead.first_name, comm[0].subject)

	def test_a_sales_user_moving_the_lead_gets_the_task_and_the_email(self):
		"""The real case: a salesperson, not Administrator, changes the status in /crm."""
		frappe.set_user(SALES)
		try:
			lead = frappe.get_doc({"doctype": "CRM Lead", "first_name": f"{TAG} {frappe.generate_hash(length=5)}",
								   "email": f"own.{TAG}@example.com", "lead_owner": SALES,
								   FIELD: "Partner Onboarding"}).insert()
			lead.status = "Qualified"
			lead.save()
		finally:
			frappe.set_user("Administrator")
		self.assertEqual([t.title for t in self.tasks(lead)], ["Send partner pack"])
		self.assertTrue(frappe.db.exists("Communication", {"reference_doctype": "CRM Lead",
														   "reference_name": lead.name}))

	def test_no_outgoing_mailbox_still_leaves_the_task(self):                  # review M2
		"""The email is optional; the task is not. A failed send must not take the task with it."""
		with patch("alvoraa_portal.crm_steps.make_email",
				   side_effect=frappe.OutgoingEmailError("no outgoing account")):
			lead = self.move(self.lead("Partner Onboarding", email=f"nomail.{TAG}@example.com"), "Qualified")
		self.assertEqual([t.title for t in self.tasks(lead)], ["Send partner pack"])
		self.assertEqual(frappe.db.get_value("CRM Lead", lead.name, "status"), "Qualified")
		self.assertTrue(frappe.db.exists("Error Log", {"reference_name": lead.name}))

	def test_the_step_assignee_can_open_the_lead(self):
		"""Surbhi's option (b): a Sales User given a step task can open that lead and sees it listed."""
		lead = self.move(self.lead("Client Project"), "Qualified")      # step assigns NITIN
		frappe.set_user(NITIN)
		try:
			self.assertTrue(frappe.has_permission("CRM Lead", "read", lead.name))
			self.assertIn(lead.name, frappe.get_list("CRM Lead", pluck="name"))
		finally:
			frappe.set_user("Administrator")
		other = self.lead("Client Project")                              # no step: no access
		frappe.set_user(NITIN)
		try:
			self.assertFalse(frappe.has_permission("CRM Lead", "read", other.name))
		finally:
			frappe.set_user("Administrator")

	def test_a_data_import_starts_no_steps(self):                            # M3, approved 2 Oct
		frappe.flags.in_import = True
		try:
			lead = self.lead("Client Project", status="Qualified")
		finally:
			frappe.flags.in_import = False
		self.assertEqual(self.tasks(lead), [])
		self.move(lead, "Contacted")
		self.move(lead, "Qualified")                                     # a real change afterwards
		self.assertEqual(len(self.tasks(lead)), 1)

	def test_a_lead_without_email_still_gets_its_task(self):
		lead = self.move(self.lead("Partner Onboarding"), "Qualified")
		self.assertEqual(len(self.tasks(lead)), 1)
		self.assertFalse(frappe.db.exists("Communication", {"reference_name": lead.name,
															"reference_doctype": "CRM Lead"}))

	def test_a_broken_step_never_blocks_the_status_change(self):
		bad = self.rule("CRM Lead", "Client Project", "Nurture", "S057 broken step", 0)
		frappe.db.set_value(RULE, bad.name, "assign_to", "nobody.s057@example.com")  # bypasses validate
		try:
			lead = self.move(self.lead("Client Project"), "Nurture")
			self.assertEqual(frappe.db.get_value("CRM Lead", lead.name, "status"), "Nurture")
			self.assertEqual(self.tasks(lead), [])
			err = frappe.db.get_value("Error Log", {"method": ["like", f"%{bad.name}%"]}, "error")
			self.assertTrue(err)
			self.assertNotIn(lead.first_name, err, "no personal data in the log")
		finally:
			frappe.db.delete(RULE, {"name": bad.name})

	def test_a_wrong_step_is_refused_when_saved(self):
		with self.assertRaisesRegex(frappe.ValidationError, "no CRM Lead Status"):
			self.rule("CRM Lead", "Client Project", "Site Visted", "x", 0)
		with self.assertRaisesRegex(frappe.ValidationError, "not one of the Lead Type options"):
			self.rule("CRM Lead", "Retail", "Qualified", "x", 0)
		with self.assertRaisesRegex(frappe.ValidationError, "no CRM Deal Status"):
			self.rule("CRM Deal", "Client Project", "Qualified", "x", 0)   # a lead status, not a deal one
		frappe.db.set_value("User", NITIN, "enabled", 0)
		try:
			with self.assertRaisesRegex(frappe.ValidationError, "disabled"):
				self.rule("CRM Lead", "Client Project", "Qualified", "x", 0)
		finally:
			frappe.db.set_value("User", NITIN, "enabled", 1)
		with self.assertRaisesRegex(frappe.ValidationError, "negative"):
			self.rule("CRM Lead", "Client Project", "Qualified", "x", -1)

	def test_a_sales_user_can_read_steps_but_not_write_them(self):
		frappe.set_user(SALES)
		try:
			self.assertTrue(frappe.has_permission(RULE, "read"))
			self.assertFalse(frappe.has_permission(RULE, "create"))
			with self.assertRaises(frappe.PermissionError):
				self.rule("CRM Lead", "Client Project", "Contacted", "x", 0)
		finally:
			frappe.set_user("Administrator")

	# ── 4 Oct: a new step task shows on the open lead page at once ──────────

	def refetch_calls(self, mock):
		return [c for c in mock.call_args_list if c.args and c.args[0] == "refetch_resource"]

	def test_a_new_task_asks_the_open_page_to_reload_after_commit(self):
		lead = self.lead("Client Project")
		with patch("frappe.publish_realtime") as pub:
			self.move(lead, "Qualified")
		calls = self.refetch_calls(pub)
		self.assertEqual(len(calls), 1)
		self.assertEqual(calls[0].args[1], {"cache_key": ["activity", lead.name]})
		self.assertEqual(calls[0].kwargs, {"doctype": "CRM Lead", "docname": lead.name, "after_commit": True})

	def test_no_task_no_reload(self):
		lead = self.move(self.lead("Client Project"), "Qualified")
		with patch("frappe.publish_realtime") as pub:
			self.move(lead, "Contacted")                         # no step for Contacted
			self.move(lead, "Qualified")                         # the open task is still there
		self.assertEqual(self.refetch_calls(pub), [])

	# ── 4 Oct: every CRM Task carries '<person> – <company>' for its lead or deal

	def task(self, ref_dt=None, ref_name=None, title="S057 hand-made"):
		return frappe.get_doc({"doctype": "CRM Task", "title": title, "status": "Todo",
							   "reference_doctype": ref_dt, "reference_docname": ref_name}).insert()

	def label(self, task):
		return frappe.db.get_value("CRM Task", task.name, crm_steps.TASK_LABEL)

	def test_the_field_is_on_crm_task_and_shows_in_the_columns_list(self):
		field = frappe.get_meta("CRM Task").get_field(crm_steps.TASK_LABEL)
		self.assertEqual((field.label, field.fieldtype, field.read_only, field.in_list_view, field.hidden),
						 ("Lead / Deal", "Data", 1, 1, 0))
		self.assertTrue(crm_steps.ensure_task_label_field(), "safe to run twice")

	def test_a_step_task_gets_person_and_company(self):
		lead = self.lead("Client Project")
		frappe.db.set_value("CRM Lead", lead.name, "organization", "S057 Hill View")
		self.move(lead, "Qualified")
		self.assertEqual(frappe.db.get_value("CRM Task", {"reference_docname": lead.name}, crm_steps.TASK_LABEL),
						 f"{lead.lead_name} – S057 Hill View")

	def test_a_hand_made_task_gets_it_too(self):
		lead = self.lead(None)
		self.assertEqual(self.label(self.task("CRM Lead", lead.name)), lead.lead_name)   # no company: no dash

	def test_the_deal_puts_the_company_first(self):
		deal = frappe.get_doc({"doctype": "CRM Deal", "status": "Qualification", "organization": self.org,
							   "lead_name": "S057 Ravi"}).insert(ignore_permissions=True)
		self.deals.append(deal.name)
		self.assertEqual(self.label(self.task("CRM Deal", deal.name)), f"{self.org} – S057 Ravi")
		bare = frappe.get_doc({"doctype": "CRM Deal", "status": "Qualification"}).insert(ignore_permissions=True)
		self.deals.append(bare.name)
		self.assertEqual(self.label(self.task("CRM Deal", bare.name)), bare.name)          # nothing else to show

	def test_empty_parts_and_repeats_are_dropped(self):
		row = frappe._dict
		self.assertEqual(crm_steps.task_label("CRM Lead", row(name="L", lead_name="", first_name="Asha",
															  last_name=None, organization="")), "Asha")
		self.assertEqual(crm_steps.task_label("CRM Lead", row(name="L", lead_name="Acme", first_name=None,
															  last_name=None, organization="Acme")), "Acme")
		self.assertEqual(crm_steps.task_label("CRM Lead", None), "")
		self.assertEqual(len(crm_steps.task_label("CRM Lead", row(name="L", lead_name="x" * 200,
																   organization=None))), 140)

	def test_other_or_no_reference_leaves_it_empty(self):
		self.assertFalse(self.label(self.task()))
		self.assertEqual(crm_steps.task_label("Contact", frappe._dict(name="x", lead_name="y")), "")

	def test_a_changed_reference_refreshes_it_and_other_saves_read_nothing(self):
		a, b = self.lead(None), self.lead(None)
		task = self.task("CRM Lead", a.name)
		task.reference_docname = b.name
		task.save()
		self.assertEqual(self.label(task), b.lead_name)
		task.reload()
		task.status = "Done"
		with patch("frappe.db.get_value", wraps=frappe.db.get_value) as gv:
			task.save()
		# Frappe's own link check reads ('name',); ours would read NAME_FIELDS.
		self.assertFalse([c for c in gv.call_args_list if crm_steps.NAME_FIELDS in c.args])

	def test_the_backfill_fills_old_rows_and_runs_twice_safely(self):
		import alvoraa_portal.patches.v1_0.crm_task_lead_deal_label as patch_mod
		lead = self.lead(None)
		task = self.task("CRM Lead", lead.name)
		frappe.db.set_value("CRM Task", task.name, crm_steps.TASK_LABEL, "", update_modified=False)
		patch_mod.execute()
		self.assertEqual(self.label(task), lead.lead_name)
		modified = frappe.db.get_value("CRM Task", task.name, "modified")
		with patch("frappe.db.set_value") as sv:
			crm_steps.backfill_task_labels(batch=1)               # second run, one row a page
		self.assertFalse([c for c in sv.call_args_list if c.args[1] == task.name], "nothing rewritten")
		self.assertEqual(frappe.db.get_value("CRM Task", task.name, "modified"), modified)
