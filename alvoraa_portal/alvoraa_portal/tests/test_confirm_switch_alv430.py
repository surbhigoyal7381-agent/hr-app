"""ALV-430: each organisation chooses whether employees confirm changes made for them.

Surbhi, 22 Nov 2026: *"Make it an organisation setting to enable it, so it's the
organisation's choice to follow compliance of ensuring the employee confirms
other people's changes on their profile, or keep it a simple workflow."*

**What the switch decides.** Slice 087 made an unrequested change wait for the
employee's Confirm and held their salary slip until it came. That is right
where the law asks for it - counsel cleared DTC and Grace on exactly that
condition - and it is pure friction at an organisation with no such obligation.
So it becomes a per-company choice, **off by default**: a new tenant gets the
simple workflow, and DTC and Grace are switched on by hand.

**One place decides it, and that is the design.**
`punch_fix._own_the_confirm_fields` is the only function that sets
`alvoraa_needs_confirm`. Gate it there and every reader downstream - the slip
gate, the before-payroll list, the employee's day sheet, slice 088's notice
list - goes quiet by construction. The alternative was a company check at each
of those call sites: the same rule written seven times, and wrong the first
time somebody adds an eighth reader.

**What the switch does NOT do.** It never clears a confirm that has already
been asked for. Switching off stops NEW changes needing one; a change already
waiting keeps its flag - exactly as held days keep theirs ("Days already held
stay held if this is switched off", `held_day` SWITCH). Same sentence, same
reason: a flag already set is a fact about a change somebody has already been
shown, not a setting.

**Scope.** The switch covers everything the system already marks as needing a
confirm: HR-filed changes and cut changes. A manager's plain addition never
needed one. Surbhi's 22 Nov decision, and it matches counsel, who treats a
manager's cut as an unrequested employer edit.
"""

import frappe
from frappe.utils import cint

from alvoraa_portal import punch_fix
from alvoraa_portal.tests.fixtures_045 import Wave4Base, own_company, own_employee, own_user

COMPANY = "Company"


class _StandIn(frappe._dict):
	"""Just enough of a Document for the rule under test.

	`frappe._dict` answers any missing attribute with None, so `doc.set(...)`
	came back as None and the edit path died with "NoneType object is not
	callable" - a fault in the test, not in the rule. Caught on the first real
	run; worth keeping the note, because a stand-in that silently answers None
	to everything is a comfortable way to test nothing at all.
	"""

	def set(self, field, value):
		self[field] = value

	def has_value_changed(self, field):
		return self.get(field) != self._was.get(field)

	def freeze(self):
		"""Remember the stored values, the way Frappe's own before-save copy
		does, so `has_value_changed` means something."""
		self._was = dict(self)
		return self


class _Base(Wave4Base):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.hr = own_user("s430hr", ("Employee", "HR Manager"))
		cls.staff_user = own_user("s430staff", ("Employee",))
		cls.staff = own_employee("S430 Ravi", user=cls.staff_user)

	def setUp(self):
		super().setUp()
		frappe.set_user("Administrator")
		if not punch_fix.columns_ready():
			# Not a failing switch - a site that has not migrated. Said out
			# loud rather than passing quietly on nothing.
			self.skipTest("the 087 confirm columns are not on this site yet")
		self.company = own_company()
		self._switch_was = frappe.db.get_value(COMPANY, self.company,
		                                       punch_fix.CONFIRM_SWITCH)

	def tearDown(self):
		frappe.set_user("Administrator")
		frappe.db.set_value(COMPANY, self.company, punch_fix.CONFIRM_SWITCH,
		                    self._switch_was, update_modified=False)
		frappe.clear_cache()
		super().tearDown()

	def _switch(self, on):
		frappe.db.set_value(COMPANY, self.company, punch_fix.CONFIRM_SWITCH,
		                    1 if on else 0, update_modified=False)
		frappe.db.commit()
		frappe.clear_cache()

	def _hr_files_a_change(self):
		"""Run the rule exactly as a creation by HR, and report the flag.

		The rule is called with `before=None`, which is what Frappe passes on
		an insert. A stand-in document is used on purpose: the question here is
		what the rule DECIDES, and a real Attendance Request drags in shifts,
		punches, approvals and a monthly limit, each with its own suite. What a
		real request does end to end is 087's `test_security_alv411_412` and
		its own suite, which this change must leave green.
		"""
		doc = self._a_change()
		frappe.set_user(self.hr)
		try:
			punch_fix._own_the_confirm_fields(doc, None)
		finally:
			frappe.set_user("Administrator")
		return cint(doc.get("alvoraa_needs_confirm"))

	def _a_change(self):
		"""An HR-filed addition, as the rule sees it on an insert."""
		return _StandIn({
			"employee": self.staff,
			"alvoraa_missing_time": "2026-11-20 18:00:00",
			"alvoraa_missing_log": "OUT",
			"alvoraa_set_aside": None,
		}).freeze()


# ── the switch itself ──────────────────────────────────────────────────────

class TestTheSwitchExists(_Base):
	def test_the_company_carries_the_switch(self):
		"""AC-430-1. Organisation config belongs on the organisation record,
		not in code - CLAUDE.md section 4, and the same place held days put
		theirs."""
		self.assertTrue(frappe.db.has_column(COMPANY, punch_fix.CONFIRM_SWITCH))

	def test_it_is_off_unless_somebody_turns_it_on(self):
		"""AC-430-2. **The default is the whole decision.** A tenant that never
		heard of this gets the simple workflow; compliance is opted into, by a
		person, per company."""
		field = frappe.get_meta(COMPANY).get_field(punch_fix.CONFIRM_SWITCH)
		self.assertIsNotNone(field, "the switch is not on the Company form")
		self.assertEqual(cint(field.default or 0), 0)

	def test_the_description_says_what_switching_it_off_means(self):
		"""Surbhi, 22 Nov: the screen must say plainly what off means. The
		person choosing is an HR Manager, not a lawyer, and the consequence
		they care about is the salary slip."""
		field = frappe.get_meta(COMPANY).get_field(punch_fix.CONFIRM_SWITCH)
		words = (field.description or "").lower()
		self.assertTrue(words, "the switch has no description at all")
		for ought in ("confirm", "salary slip"):
			with self.subTest(word=ought):
				self.assertIn(ought, words)

	def test_one_function_answers_it(self):
		"""Read in one place, so the rule cannot drift between readers."""
		self._switch(False)
		self.assertFalse(punch_fix.confirms_are_on(self.company))
		self._switch(True)
		self.assertTrue(punch_fix.confirms_are_on(self.company))

	def test_an_unknown_company_does_not_blow_up(self):
		"""A request whose employee has no company must not take the save
		down. Off is the safe answer: it is the default everywhere."""
		self.assertFalse(punch_fix.confirms_are_on(None))
		self.assertFalse(punch_fix.confirms_are_on("No Such Company Ltd"))


# ── what it changes ────────────────────────────────────────────────────────

class TestWhatTheSwitchChanges(_Base):
	def test_off_means_an_hr_change_needs_no_confirm(self):
		"""AC-430-3. **The simple workflow.** HR approves, the change counts,
		the slip is not held and nobody is asked to press anything.

		This is the assertion that fails before the switch exists: today every
		HR-filed change is flagged, whatever the company wants."""
		self._switch(False)
		self.assertEqual(self._hr_files_a_change(), 0)

	def test_on_means_an_hr_change_still_waits(self):
		"""AC-430-4. The switch must not quietly weaken the compliant path.
		Everything 087 held, it still holds - this is the control, and without
		it a green run above could just mean the confirm is broken for
		everybody."""
		self._switch(True)
		self.assertEqual(self._hr_files_a_change(), 1)

	def test_switching_off_does_not_clear_a_confirm_already_asked_for(self):
		"""AC-430-5. **The rule a careless version would get wrong.**

		A change already waiting was shown to the employee as waiting. If
		switching the company off cleared it, an organisation could release
		every held slip by flicking a switch, and the record would say the
		employee agreed to things they never saw. So the flag survives, as a
		held day survives, and the only way out stays the real one: Confirm,
		the register, or Withdraw.
		"""
		self._switch(True)
		doc = self._a_change()
		frappe.set_user(self.hr)
		try:
			punch_fix._own_the_confirm_fields(doc, None)
		finally:
			frappe.set_user("Administrator")
		self.assertEqual(cint(doc.get("alvoraa_needs_confirm")), 1)

		# The company changes its mind. The saved change is edited afterwards.
		self._switch(False)
		before = _StandIn(dict(doc)).freeze()
		doc = _StandIn(dict(doc)).freeze()
		frappe.set_user(self.hr)
		try:
			punch_fix._own_the_confirm_fields(doc, before)
		finally:
			frappe.set_user("Administrator")
		self.assertEqual(
			cint(doc.get("alvoraa_needs_confirm")), 1,
			"switching the company off cleared a confirm that was already "
			"asked for")

	def test_the_employees_own_request_never_needed_one_either_way(self):
		"""The switch is about changes made FOR somebody. Their own request
		was never affected, on or off."""
		for on in (True, False):
			with self.subTest(switch=on):
				self._switch(on)
				doc = self._a_change()
				frappe.set_user(self.staff_user)
				try:
					punch_fix._own_the_confirm_fields(doc, None)
				finally:
					frappe.set_user("Administrator")
				self.assertEqual(cint(doc.get("alvoraa_needs_confirm")), 0)


# ── the dead end the first version of this switch created ──────────────────

class TestTheReaderIsGatedToo(_Base):
	"""ALV-430, after the 087 session's review on 22 Nov 2026.

	**Gating only the writer left a trap.** A change flagged while the company
	asked for confirmations keeps its flag when the company stops - on purpose,
	because the flag is a fact about a change the employee was already shown.
	But the three ways out are: the employee confirms in the app (the staff
	this matters to have no app), a signed register (slice 088, paused), or
	`withdraw_filed`, **which refuses an approved request**. So an approved,
	unconfirmed change at a switched-off company would have held that person's
	salary slip for ever with no exit - the very fault 088 exists to remove.

	So the reader is gated as well. Nothing is falsified: the flag stays 1 and
	`alvoraa_confirmed_on` stays empty, so the history still says plainly that
	nobody confirmed. Only the block lifts.
	"""

	def _a_flagged_request(self):
		"""A saved request that needs a confirm and has not had one.

		Inserted with validation bypassed on purpose: the 087 rules that build
		a real request (shift, punches, the monthly limit, approval) have their
		own suites, and what is under test here is only which rows the reader
		hands back.
		"""
		doc = frappe.get_doc({
			"doctype": "Attendance Request", "employee": self.staff,
			"from_date": "2026-11-20", "to_date": "2026-11-20",
			"reason": "On Duty", "explanation": "s430 reader gate",
		})
		doc.flags.ignore_validate = True
		doc.flags.ignore_mandatory = True
		doc.insert(ignore_permissions=True)
		frappe.db.set_value("Attendance Request", doc.name, {
			"alvoraa_needs_confirm": 1, "alvoraa_confirmed_on": None,
			"alvoraa_missing_time": "2026-11-20 18:00:00",
		}, update_modified=False)
		frappe.db.commit()
		self.addCleanup(self._drop, doc.name)
		return doc.name

	def _drop(self, name):
		frappe.set_user("Administrator")
		if frappe.db.exists("Attendance Request", name):
			frappe.delete_doc("Attendance Request", name, force=True,
			                  ignore_permissions=True)
			frappe.db.commit()

	def _names(self, **kw):
		return [r["name"] for r in punch_fix.unconfirmed_changes(
			[self.staff], "2026-11-01", "2026-11-30", **kw)]

	def test_with_the_switch_on_the_change_is_waiting(self):
		"""The control. Without it, a green test below could simply mean the
		reader is broken for everybody."""
		name = self._a_flagged_request()
		self._switch(True)
		self.assertIn(name, self._names())

	def test_with_the_switch_off_it_holds_nothing(self):
		"""AC-430-6. The dead end, closed."""
		name = self._a_flagged_request()
		self._switch(False)
		self.assertNotIn(name, self._names())

	def test_the_row_still_says_nobody_confirmed(self):
		"""AC-430-7. **The block lifts; the history does not change.**

		If switching off had cleared the flag or written a confirmation, the
		record would claim the employee agreed to something they never saw.
		It must still be possible to ask, later, "was this ever confirmed?"
		and get the truthful answer: no.
		"""
		name = self._a_flagged_request()
		self._switch(False)
		self.assertNotIn(name, self._names())
		row = frappe.db.get_value("Attendance Request", name,
		                          ["alvoraa_needs_confirm", "alvoraa_confirmed_on"],
		                          as_dict=True)
		self.assertEqual(cint(row.alvoraa_needs_confirm), 1)
		self.assertIsNone(row.alvoraa_confirmed_on)

	def test_the_switch_can_be_ignored_on_purpose(self):
		"""`respect_switch=False` is how the slip gate counts what it is
		letting through, so that it can be written down rather than passed
		over in silence."""
		name = self._a_flagged_request()
		self._switch(False)
		self.assertIn(name, self._names(respect_switch=False))
