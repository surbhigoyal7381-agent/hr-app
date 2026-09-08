"""How an organisation handles temporary cover - all of it a setting.

Every rule here is a POLICY rather than a fact, so none of it is hard-coded. A
company covering a shop two streets away and one covering a plant three hours
away should not be forced into the same answer.

The tests come in pairs on purpose: the default behaviour, and the organisation
switching it round. A setting nobody can change is a constant with extra steps.
"""

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, nowdate

from hrms.alvoraa_org_structure import settings
from hrms.alvoraa_org_structure.tests.test_org_structure import OrgCase


class CoverCase(OrgCase):
	def setUp(self):
		super().setUp()
		self.s = settings
		self._saved = {k: frappe.db.get_default(k) for k in settings.DEFAULTS}

	def tearDown(self):
		for k, v in self._saved.items():
			frappe.db.set_default(k, v if v is not None else "")
		super().tearDown()

	def _set(self, key, value):
		frappe.db.set_default(key, value)

	def _covering(self, **kw):
		"""Ravi keeps Ambala and takes on Chandigarh."""
		own = self.pos("Store In-charge Ambala")
		other = self.pos("Store In-charge Chandigarh")
		ravi = self.person("Ravi")
		self.assign(ravi, own.name, weight=100)
		kw.setdefault("assignment_type", "Acting")
		return ravi, other, self.assign(ravi, other.name, **kw)


class TestTimeBoxItAlways(CoverCase):
	def test_cover_with_no_end_date_is_refused(self):
		"""Cover that never ends is a second job nobody agreed to."""
		with self.assertRaises(frappe.ValidationError):
			self._covering(weight=25)

	def test_with_an_end_date_it_is_fine(self):
		self._covering(weight=25, to_date=add_days(nowdate(), 60))

	def test_an_organisation_may_switch_that_off(self):
		self._set("alvoraa_cover_require_end_date", 0)
		self._covering(weight=25)          # no raise


class TestCapTheLoad(CoverCase):
	def test_over_the_cap_needs_a_written_reason(self):
		with self.assertRaises(frappe.ValidationError):
			self._covering(weight=50, to_date=add_days(nowdate(), 60))

	def test_with_a_reason_it_goes_through(self):
		"""Allowed rather than refused, so nobody works round it by recording
		the cover as permanent - which hides it completely."""
		self._covering(weight=50, to_date=add_days(nowdate(), 60),
		               load_exception_reason="Regional manager signed off, 8 weeks")

	def test_an_organisation_may_refuse_outright_instead(self):
		self._set("alvoraa_cover_allow_over_cap", 0)
		with self.assertRaises(frappe.ValidationError):
			self._covering(weight=50, to_date=add_days(nowdate(), 60),
			               load_exception_reason="signed off")

	def test_under_the_cap_needs_nothing(self):
		self._covering(weight=25, to_date=add_days(nowdate(), 60))   # 125%

	def test_the_cap_itself_is_a_setting(self):
		self._set("alvoraa_cover_max_load", 110)
		with self.assertRaises(frappe.ValidationError):
			self._covering(weight=25, to_date=add_days(nowdate(), 60))


class TestKeepTheVacancyOpen(CoverCase):
	def test_a_covered_seat_still_reads_open_to_recruitment(self):
		"""Once somebody is standing in, urgency drops and the requisition
		stalls. That is how a three-month gap becomes a year."""
		_, seat, _ = self._covering(weight=30, to_date=add_days(nowdate(), 60))
		seat.reload()
		self.assertAlmostEqual(seat.vacancy(), 0.7, places=2)
		self.assertAlmostEqual(seat.vacancy(for_recruitment=True), 1.0, places=2)

	def test_an_organisation_may_let_cover_close_it(self):
		self._set("alvoraa_cover_vacancy_stays_open", 0)
		_, seat, _ = self._covering(weight=30, to_date=add_days(nowdate(), 60))
		seat.reload()
		self.assertAlmostEqual(seat.vacancy(for_recruitment=True), 0.7, places=2)

	def test_a_permanent_hire_does_close_it(self):
		seat = self.pos("Store In-charge Noida", seats=1)
		self.assign(self.person("Anil"), seat.name, weight=100)
		seat.reload()
		self.assertEqual(seat.vacancy(for_recruitment=True), 0.0)


class TestCoverThatQuietlyBecamePermanent(CoverCase):
	"""The failure is not somebody at 130% on day one - that was a decision. It
	is nobody noticing on day two hundred."""

	def test_long_cover_is_listed_worst_first(self):
		self._set("alvoraa_cover_max_days", 30)
		self._covering(weight=25, from_date=add_days(nowdate(), -200),
		               to_date=add_days(nowdate(), 30))
		out = self.s.long_running_cover()
		self.assertEqual(out["count"], 1)
		self.assertGreaterEqual(out["cover"][0]["days"], 200)
		self.assertGreaterEqual(out["cover"][0]["over_by"], 170)

	def test_recent_cover_is_left_alone(self):
		self._set("alvoraa_cover_max_days", 90)
		self._covering(weight=25, from_date=add_days(nowdate(), -10),
		               to_date=add_days(nowdate(), 30))
		self.assertEqual(self.s.long_running_cover()["count"], 0)

	def test_finished_cover_is_not_still_nagged_about(self):
		self._set("alvoraa_cover_max_days", 30)
		self._covering(weight=25, from_date=add_days(nowdate(), -300),
		               to_date=add_days(nowdate(), -100))
		self.assertEqual(self.s.long_running_cover()["count"], 0)

	def test_the_threshold_is_a_setting(self):
		self._covering(weight=25, from_date=add_days(nowdate(), -100),
		               to_date=add_days(nowdate(), 30))
		self._set("alvoraa_cover_max_days", 365)
		self.assertEqual(self.s.long_running_cover()["count"], 0)
		self._set("alvoraa_cover_max_days", 30)
		self.assertEqual(self.s.long_running_cover()["count"], 1)


class TestTheSettingsThemselves(CoverCase):
	def test_a_setting_nobody_has_chosen_falls_back(self):
		frappe.db.set_default("alvoraa_cover_max_load", "")
		self.assertEqual(self.s.get("alvoraa_cover_max_load"),
		                 self.s.DEFAULTS["alvoraa_cover_max_load"])

	def test_an_unknown_key_is_refused(self):
		"""A typo in the front end must not create a setting nothing reads."""
		with self.assertRaises(frappe.ValidationError):
			self.s.set_cover_setting("alvoraa_cover_nonsense", 1)

	def test_every_setting_has_a_label_and_a_reason(self):
		"""The Org Setup page renders both. A setting with no explanation gets
		set wrong by somebody guessing what it means."""
		for key in self.s.DEFAULTS:
			self.assertIn(key, self.s.LABELS, key)
			label, why = self.s.LABELS[key]
			self.assertTrue(label and why, key)


class TestDelegatedAuthority(CoverCase):
	"""A title without authority is the half-measure that makes cover useless:
	the acting manager cannot approve the leave of the people they are covering,
	so everything still queues behind somebody who is not there."""

	def _store_with_staff(self):
		boss = self.pos("Store In-charge Chandigarh")
		staff = self.pos("Sales Executive Chandigarh", parent=boss.name)
		under = self.person("Suresh")
		self.assign(under, staff.name, weight=100)
		return boss, under

	def _ravi_with_login(self):
		emp = self.person("Ravi")
		email = "ravi.cover@example.com"
		if not frappe.db.exists("User", email):
			frappe.get_doc({"doctype": "User", "email": email, "first_name": "Ravi",
			                "send_welcome_email": 0}).insert(ignore_permissions=True)
		frappe.db.set_value("Employee", emp, "user_id", email)
		return emp, email

	def _cover(self, boss, ravi, **kw):
		own = self.pos("Store In-charge Ambala")
		self.assign(ravi, own.name, weight=100)
		return self.assign(ravi, boss.name, weight=30, assignment_type="Acting",
		                   to_date=add_days(nowdate(), 60), **kw)

	def test_approvals_move_to_whoever_is_standing_in(self):
		boss, under = self._store_with_staff()
		ravi, email = self._ravi_with_login()
		self._cover(boss, ravi, delegate_authority=1)
		self.assertEqual(frappe.db.get_value("Employee", under, "leave_approver"), email)

	def test_what_changed_is_recorded_so_it_can_be_undone(self):
		boss, under = self._store_with_staff()
		frappe.db.set_value("Employee", under, "leave_approver", "before@example.com")
		ravi, _ = self._ravi_with_login()
		row = self._cover(boss, ravi, delegate_authority=1)
		row.reload()
		self.assertEqual(row.delegated_approvals[0].previous_leave_approver,
		                 "before@example.com")

	def test_ending_it_puts_approvals_back_exactly(self):
		"""Blanking them instead would quietly break approvals for everybody who
		had a perfectly good approver before the cover started."""
		boss, under = self._store_with_staff()
		frappe.db.set_value("Employee", under, "leave_approver", "before@example.com")
		ravi, _ = self._ravi_with_login()
		row = self._cover(boss, ravi, delegate_authority=1)
		row.reload()
		row.restore_delegation()
		self.assertEqual(frappe.db.get_value("Employee", under, "leave_approver"),
		                 "before@example.com")

	def test_nothing_moves_unless_it_is_asked_for(self):
		boss, under = self._store_with_staff()
		frappe.db.set_value("Employee", under, "leave_approver", "before@example.com")
		ravi, _ = self._ravi_with_login()
		self._cover(boss, ravi)
		self.assertEqual(frappe.db.get_value("Employee", under, "leave_approver"),
		                 "before@example.com")

	def test_somebody_with_no_login_cannot_be_given_authority(self):
		boss, _ = self._store_with_staff()
		ravi = self.person("Ravi")          # deliberately no user account
		with self.assertRaises(frappe.ValidationError):
			self._cover(boss, ravi, delegate_authority=1)
