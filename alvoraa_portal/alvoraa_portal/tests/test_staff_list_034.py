"""Slice 034, W1D-21 / SEC-16 / AC-76: the staff list and its own switch.

Two things are pinned here, and they are different kinds of thing.

**The switch** is one `opt_in` key in `subscription.FEATURES`, next to
`org_structure` and shaped like it. What must hold is that shipping it hands it
to nobody: it is in no plan bundle, and a site with no recorded feature list
does not get it. That is what leaves the commercial question - free or paid, and
on which plans - settleable later by a tick rather than by another release.

**The endpoint** is where the switch is actually enforced. Not drawing a menu
entry is not a permission, so the test that matters most is the one where an HR
user on a tenant that was never given the feature calls the function by hand and
is refused (abuse case A14). Beside it: a store's HR person's list is their
store and nobody else's (A15), a leaver does not appear, and the payload carries
PRIV-2's five keys and nothing more.

Every refusal test has a positive control next to it - the same caller, the same
call, with the one thing changed - so that none of them can pass because the
fixture was broken.

Fixtures are slice 030's two stores, built through the ORM the way a person
builds them. The leaver is made a leaver the way HR makes one: the document is
saved with a relieving date, which is what Frappe HR insists on.
"""

import json
from unittest import mock

import frappe
from frappe.tests.utils import FrappeTestCase

from alvoraa_portal import staff_api
from alvoraa_portal import subscription as sub
from alvoraa_portal.tests.leave_fixtures import ensure_user
from alvoraa_portal.tests.test_portal_security_010 import _employee
from alvoraa_portal.tests.test_store_hr_scoping_030 import STORE_A, _Stores

KEY = staff_api.FEATURE

# The real entitlement function, captured while this module is imported - which
# happens during test discovery, before any test's setUp has started a patch.
# Everything in §"the trap" below depends on having a handle on the real one.
REAL_HAS_FEATURE = sub.has_feature


class _StaffListBase(_Stores):
	"""The two stores, plus one leaver in store A and a login outside HR."""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		# A leaver in store A. Made Active first and then relieved through the
		# document, which is how HR does it - Frappe HR refuses a status of
		# "Left" with no relieving date, so a fixture that wrote the column
		# directly would be testing a record no real tenant can have.
		cls.leaver = _employee("S034LeftAtA", company=cls.company_a)
		frappe.db.set_value("Employee", cls.leaver, "branch", STORE_A, update_modified=False)
		doc = frappe.get_doc("Employee", cls.leaver)
		doc.status = "Left"
		doc.relieving_date = "2026-06-30"
		doc.flags.ignore_permissions = True
		doc.save(ignore_permissions=True)
		cls.vendor_user = ensure_user("s034.staffvendor@example.com", roles=("Grace Vendor Portal",))
		frappe.db.commit()

	@classmethod
	def tearDownClass(cls):
		"""Take the leaver away again.

		Slice 030's fixture people are permanent on purpose, and several tests
		elsewhere assert the EXACT set of people in store A. A sixth person left
		behind there makes those tests fail in a later run for a reason that has
		nothing to do with what they are about - which is what happened the
		first time this file was run.
		"""
		frappe.set_user("Administrator")
		if frappe.db.exists("Employee", cls.leaver):
			frappe.delete_doc("Employee", cls.leaver, force=True, ignore_permissions=True)
		frappe.db.commit()
		super().tearDownClass()

	def setUp(self):
		super().setUp()
		# ── The trap this file nearly fell into ───────────────────────────────
		#
		# `_ReviewBase.setUp`, five classes up the chain, patches
		# `subscription.has_feature` to return True for everything, so that the
		# review tests are about reviews rather than about plans. Inheriting its
		# fixtures inherits that patch - and every entitlement test below would
		# then have passed while proving nothing, because the switch it is about
		# was answering yes to everybody.
		#
		# Stopping that patcher is not enough, and a whole-app run proves it:
		# other test modules patch the same name, patchers stack, and stopping
		# the innermost one restores the NEXT mock rather than the real
		# function. So the real function is patched back in explicitly, on top
		# of whatever is there, and taken off again in tearDown - which leaves
		# every other patcher's own bookkeeping untouched.
		#
		# The assertion is the important half: if this ever stops working, the
		# entitlement tests must break loudly rather than go quiet.
		self._real_plan = mock.patch.object(sub, "has_feature", REAL_HAS_FEATURE)
		self._real_plan.start()
		self.assertFalse(
			isinstance(sub.has_feature, mock.Mock),
			"subscription.has_feature is still mocked - every entitlement test "
			"in this file would pass without testing anything",
		)
		self._saved_features = frappe.conf.get("features")
		self._feature_on()

	def tearDown(self):
		frappe.set_user("Administrator")
		if self._saved_features is None:
			frappe.conf.pop("features", None)
		else:
			frappe.conf["features"] = self._saved_features
		self._real_plan.stop()
		super().tearDown()

	def _feature_on(self):
		"""What the tick in the admin console does: name the key on this site."""
		frappe.conf["features"] = list(sub.DEFAULT_ON) + [KEY]

	def _feature_off(self):
		"""Every other feature, this one withheld - a tenant nobody has ticked."""
		frappe.conf["features"] = list(sub.DEFAULT_ON)

	def _names(self, payload):
		return {row["employee"] for row in payload["rows"]}


# ── the switch itself ────────────────────────────────────────────────────────


class TestShippingTheKeyGrantsItToNobody(FrappeTestCase):
	"""No fixtures. This is about the registry, not about any tenant."""

	def test_the_key_exists_and_is_opt_in(self):
		self.assertIn(KEY, sub.FEATURES)
		self.assertTrue(sub.FEATURES[KEY].get("opt_in"))
		self.assertIn(KEY, sub.OPT_IN)
		self.assertNotIn(KEY, sub.DEFAULT_ON)
		self.assertNotIn(KEY, sub.REQUIRED)

	def test_it_is_in_no_plan_bundle(self):
		"""The commercial decision is deferred, so no plan may grant it yet.

		If somebody later sells it, this test is the place they have to come and
		change, which is the point - it makes the grant deliberate.
		"""
		for plan in sub.PLANS:
			self.assertNotIn(KEY, sub.plan_features(plan), msg=plan)
		self.assertNotIn(KEY, sub.plan_features("a plan that does not exist"))

	def test_a_site_with_nothing_recorded_does_not_get_it(self):
		"""The fallback grants the whole product LESS the opt-in keys."""
		self.assertNotIn(KEY, sub.enabled_features({}))
		self.assertFalse(sub.has_feature(KEY, {}))
		self.assertFalse(sub.has_feature(KEY, {"subscription_plan": "enterprise"}))

	def test_a_tenant_that_was_ticked_does_get_it(self):
		"""The positive control: the three checks above are about the default,
		not about the feature being unreachable."""
		self.assertTrue(sub.has_feature(KEY, {"features": [KEY]}))

	def test_the_org_chart_is_untouched_and_the_two_are_independent(self):
		"""W1D-21's whole point. One flag used to gate both screens."""
		self.assertIn("org_structure", sub.FEATURES)
		self.assertTrue(sub.FEATURES["org_structure"].get("opt_in"))
		self.assertNotEqual(KEY, "org_structure")
		self.assertTrue(sub.has_feature(KEY, {"features": [KEY]}))
		self.assertFalse(sub.has_feature("org_structure", {"features": [KEY]}))
		self.assertTrue(sub.has_feature("org_structure", {"features": ["org_structure"]}))
		self.assertFalse(sub.has_feature(KEY, {"features": ["org_structure"]}))

	def test_it_needs_no_desk_module_and_breaks_no_module_gate(self):
		"""There is no workspace behind this key. The module allow-list must
		still be derivable, and granting the key must not open a desk module."""
		self.assertFalse(sub.FEATURES[KEY].get("module_defs"))
		self.assertEqual(
			sub.allowed_module_defs(list(sub.DEFAULT_ON) + [KEY]),
			sub.allowed_module_defs(list(sub.DEFAULT_ON)),
		)


# ── who may call it ──────────────────────────────────────────────────────────


class TestWhoMayCallTheStaffList(_StaffListBase):
	def test_guest_is_refused(self):
		frappe.set_user("Guest")
		with self.assertRaises(frappe.PermissionError):
			staff_api.get_staff_list()

	def test_it_is_post_only_and_not_open_to_guests(self):
		"""PRIV-5. A search term is a colleague's name, and a web server logs
		every URL it serves - so it must travel in a body, not in the address."""
		# `whitelisted` and `guest_methods` are sets of the functions themselves,
		# and the allowed methods are a dict keyed by the same function
		# (frappe/__init__.py:423-426, read on the bench).
		self.assertIn(staff_api.get_staff_list, frappe.whitelisted)
		self.assertNotIn(staff_api.get_staff_list, frappe.guest_methods)
		self.assertEqual(
			frappe.allowed_http_methods_for_whitelisted_func[staff_api.get_staff_list],
			["POST"],
		)

	def test_a_junk_argument_is_answered_not_crashed(self):
		"""A JSON body can send a list or a number where a string is expected.
		That must not become a 500 with an internal message in it."""
		self._as(self.hr_user)
		for junk in ([], ["a"], 7, {"x": 1}):
			self.assertIn("rows", staff_api.get_staff_list(q=junk), msg=repr(junk))

	def test_a_plain_employee_is_refused(self):
		"""Not an empty list - a refusal. An employee is entitled to nobody
		here, and an empty list would read as "this company has no staff"."""
		self._as(self.subject_user)
		with self.assertRaises(frappe.PermissionError):
			staff_api.get_staff_list()

	def test_a_plain_manager_and_a_vendor_login_are_refused(self):
		for user in (self.manager_user, self.vendor_user):
			self._as(user)
			self.assertFalse(
				{"HR Manager", "HR User", "System Manager"} & set(frappe.get_roles(user)),
				msg=f"{user} was handed an HR role by a fixture; this test would pass for the wrong reason",
			)
			with self.assertRaises(frappe.PermissionError, msg=user):
				staff_api.get_staff_list()

	def test_hr_is_refused_on_a_tenant_that_was_never_given_the_feature(self):
		"""Abuse case A14, and the reason SEC-16 exists.

		This caller is HR, is entitled to people, and would get a list a second
		later if the tenant had been ticked. The only thing stopping them is the
		check in the endpoint - which is exactly what must not be left to the
		browser.
		"""
		self._feature_off()
		for user in (self.store_hr_user, self.hr_user, self.sysman_user):
			self._as(user)
			with self.assertRaises(frappe.PermissionError, msg=user):
				staff_api.get_staff_list()

	def test_the_same_hr_callers_are_allowed_once_the_tenant_is_ticked(self):
		"""The positive control for the test above."""
		self._feature_on()
		for user in (self.store_hr_user, self.hr_user, self.sysman_user):
			self._as(user)
			self.assertIn("rows", staff_api.get_staff_list(), msg=user)

	def test_the_refusal_carries_no_personal_content(self):
		"""PRIV-5. A refusal must be findable later without anybody's NAME,
		department, store or search term being in the log.

		The caller's login id is allowed and is the point of the line - it is
		how misuse is traced. What must never be there is a third party.
		"""
		self._feature_off()
		self._as(self.store_hr_user)
		with mock.patch("frappe.logger") as logger:
			with self.assertRaises(frappe.PermissionError):
				staff_api.get_staff_list(q="Priya")
		calls = logger.return_value.warning.call_args_list
		self.assertTrue(calls, "the refusal was not logged at all")
		line = calls[0].args[0]
		entry = json.loads(line)
		self.assertEqual(set(entry), {"event", "at", "user", "endpoint", "doctype", "name", "rule"})
		self.assertEqual(entry["endpoint"], "staff_api.get_staff_list")
		self.assertEqual(entry["rule"], "staff_list")
		self.assertEqual(entry["user"], self.store_hr_user)
		self.assertIsNone(entry["name"])
		body = line.lower()
		self.assertNotIn("priya", body, "the search term is in the security log line")
		self.assertNotIn(STORE_A.lower(), body, "the caller's store is in the security log line")
		for employee in (self.store_hr, self.a1, self.a2, self.b1, self.n1):
			name = (frappe.db.get_value("Employee", employee, "employee_name") or "").lower()
			self.assertNotIn(name, body, f"{employee} is named in the security log line")

	def test_the_refusal_says_the_same_thing_whatever_the_reason(self):
		"""A plain employee must not be able to tell "your company did not buy
		this" from "you are not HR". Both are facts they are not entitled to."""
		self._feature_off()
		self._as(self.store_hr_user)
		with self.assertRaises(frappe.PermissionError) as no_feature:
			staff_api.get_staff_list()
		self._feature_on()
		self._as(self.subject_user)
		with self.assertRaises(frappe.PermissionError) as not_hr:
			staff_api.get_staff_list()
		self.assertEqual(str(no_feature.exception), str(not_hr.exception))


# ── what it shows ────────────────────────────────────────────────────────────


class TestWhatTheStaffListShows(_StaffListBase):
	def test_store_hr_gets_their_store_and_nobody_else(self):
		"""A15. Head office has no branch, so it is outside every store."""
		self._as(self.store_hr_user)
		rows = self._names(staff_api.get_staff_list(limit=50))
		self.assertEqual(rows, {self.store_hr, self.a1, self.a2})
		self.assertFalse(rows & self.outside)

	def test_company_wide_hr_gets_their_companies(self):
		"""Both stores AND head office - the three places store HR cannot see.

		Asked for by name rather than by reading the first page of the whole
		company: on a site with more than 50 Active people the cap is doing its
		job and the fixture people are not on page one. That is the endpoint
		behaving correctly, and a test that assumed otherwise was testing the
		size of the database.
		"""
		self._as(self.hr_user)
		rows = self._names(staff_api.get_staff_list(q="S030", limit=50))
		self.assertTrue({self.a1, self.a2, self.b1, self.n1} <= rows)

	def test_company_wide_hr_sees_more_people_than_store_hr(self):
		"""The scopes are different sizes, not just different lists."""
		self._as(self.store_hr_user)
		store_total = staff_api.get_staff_list()["total"]
		self._as(self.hr_user)
		self.assertGreater(staff_api.get_staff_list()["total"], store_total)

	def test_a_leaver_does_not_appear_for_anyone(self):
		"""PRIV-2. The shared scope helper returns every status on purpose; the
		staff list is the caller that has to add Active itself."""
		for user in (self.store_hr_user, self.hr_user, self.sysman_user):
			self._as(user)
			self.assertNotIn(self.leaver, self._names(staff_api.get_staff_list(limit=50)), msg=user)

	def test_the_payload_holds_exactly_the_keys_that_were_decided(self):
		"""PRIV-2, asserted on the payload rather than on the screen.

		**This pin changed once, on purpose, and here is the decision.**
		Wave 1 fixed the list at five keys and said adding one is a visibility
		change that needs its own decision. **Surbhi took that decision on
		24 September 2026:** the staff directory is for employees too and work
		contact is in, because the companies have NDAs.

		So **one** key was added - `work_email`, from `Employee.company_email`.
		**No phone number.** There is no work-phone or extension field in the
		data model at all: `cell_number` is labelled "Mobile" and is personal,
		and shipping it would have been the dangerous reading of "contact
		details are in". Her instruction had a stop condition for exactly that,
		and this is it, kept as a test.

		Still absent, and each would need its own decision: personal email,
		mobile, employee number, branch, manager, date of birth.
		"""
		self._as(self.store_hr_user)
		payload = staff_api.get_staff_list(limit=50)
		self.assertEqual(set(payload), {"rows", "total", "start", "limit"})
		self.assertTrue(payload["rows"])
		for row in payload["rows"]:
			self.assertEqual(set(row), set(staff_api.ROW_KEYS))
		self.assertEqual(
			set(staff_api.ROW_KEYS),
			{"employee", "name", "title", "department", "image", "work_email"}
		)
		for never in ("cell_number", "personal_email", "employee_number",
		              "branch", "reports_to", "date_of_birth"):
			self.assertNotIn(never, staff_api.ROW_KEYS)

	def test_the_true_total_is_returned_even_when_the_page_is_smaller(self):
		"""On a large tenant a silent cap is how somebody concludes a colleague
		has left. The screen can only say "the first 50 of 412" if it is told."""
		self._as(self.store_hr_user)
		payload = staff_api.get_staff_list(limit=1)
		self.assertEqual(len(payload["rows"]), 1)
		self.assertEqual(payload["total"], 3)
		self.assertEqual(payload["limit"], 1)

	def test_paging_walks_the_same_list(self):
		self._as(self.store_hr_user)
		first = staff_api.get_staff_list(limit=2, start=0)
		second = staff_api.get_staff_list(limit=2, start=2)
		self.assertEqual(second["start"], 2)
		self.assertFalse(self._names(first) & self._names(second))
		self.assertEqual(self._names(first) | self._names(second),
		                 {self.store_hr, self.a1, self.a2})

	def test_the_caps_are_the_servers_not_the_callers(self):
		self._as(self.hr_user)
		self.assertEqual(staff_api.get_staff_list()["limit"], staff_api.DEFAULT_LIMIT)
		self.assertEqual(staff_api.get_staff_list(limit=500)["limit"], staff_api.MAX_LIMIT)
		self.assertEqual(staff_api.get_staff_list(limit=0)["limit"], staff_api.DEFAULT_LIMIT)
		self.assertEqual(staff_api.get_staff_list(limit=-5)["limit"], 1)
		self.assertEqual(staff_api.get_staff_list(start=-5)["start"], 0)

	def test_a_search_finds_a_name_inside_the_scope_and_never_outside_it(self):
		"""A15 again, through the search box rather than the plain list."""
		self._as(self.store_hr_user)
		self.assertEqual(self._names(staff_api.get_staff_list(q="S030AtAOne")), {self.a1})
		self.assertEqual(staff_api.get_staff_list(q="S030NoBranch")["rows"], [])
		self.assertEqual(staff_api.get_staff_list(q="S030AtB")["rows"], [])
		self._as(self.hr_user)
		self.assertEqual(self._names(staff_api.get_staff_list(q="S030NoBranch")), {self.n1})

	def test_a_wildcard_in_the_term_means_itself(self):
		"""PRIV-3. Without escaping, a single `%` returns everybody in one call
		and `a_b` quietly matches `axb`."""
		self._as(self.hr_user)
		self.assertEqual(staff_api.get_staff_list(q="%%")["rows"], [])
		self.assertEqual(staff_api.get_staff_list(q="S030AtAOn_")["rows"], [])
		self.assertEqual(staff_api.get_staff_list(q="S030%AtAOne")["rows"], [])
		# and the same term without the wildcard still works, so the assertions
		# above are not passing because the fixture is missing.
		self.assertEqual(self._names(staff_api.get_staff_list(q="S030AtAOne")), {self.a1})

	def test_a_one_letter_term_is_not_a_search(self):
		self._as(self.hr_user)
		payload = staff_api.get_staff_list(q="S")
		self.assertEqual(payload["rows"], [])
		self.assertEqual(payload["total"], 0)

	def test_an_empty_term_is_the_plain_list(self):
		self._as(self.store_hr_user)
		for term in (None, "", "   "):
			self.assertEqual(self._names(staff_api.get_staff_list(q=term, limit=50)),
			                 {self.store_hr, self.a1, self.a2}, msg=repr(term))

	def test_the_key_reaches_the_page_the_way_every_other_plan_flag_does(self):
		"""SEC-16: no parallel mechanism. `get_available_features` loops the
		registry, so the flag is `plan_staff_list` with no new code."""
		from alvoraa_portal.hr_api import get_available_features

		self._as(self.hr_user)
		self._feature_on()
		self.assertIs(get_available_features().get(f"plan_{KEY}"), True)
		self._feature_off()
		self.assertIs(get_available_features().get(f"plan_{KEY}"), False)


# ── the frame ────────────────────────────────────────────────────────────────


class TestTheStaffListSwitchOpensTheGroupForAnybody(FrappeTestCase):
	"""**This class asserted the opposite until slice 045, and the reason it
	gave has gone away.**

	What it said: *"The staff list must not open the Company group for a non-HR
	person. It is an HR screen. If the tenant having the feature were enough to
	open the group, an ordinary employee would be shown a Company menu whose
	only new entry refuses them - which is worse than not offering it."*

	Every word of that was true while `get_staff_list` refused a caller with no
	HR entitlement. Surbhi opened the directory to employees on 24 September
	2026, and the endpoint now gives them their own company
	(`staff_api.DIRECTORY_SCOPE_FOR_EMPLOYEES`). So the entry no longer refuses
	them, and the group has to open - otherwise the server allows a screen the
	frame never offers.

	**Two things are kept, and they are what stops this being a widening.**
	`test_the_group_carries_no_hr_screen_for_an_employee` below asserts that
	opening the group hands an employee none of the four HR-only entries, and
	`test_with_the_switch_off_an_employee_still_has_no_group` asserts the switch
	is still what decides it. The tenant switch is untouched.
	"""

	def _company_group(self, is_hr, features):
		from alvoraa_portal.frame_api import _allowed_pages

		return _allowed_pages(True, is_hr, False, features)["company"]

	def test_the_switch_opens_the_group_for_a_plain_employee(self):
		"""045. The assertion turns over, with its reason above."""
		self.assertTrue(
			self._company_group(False, {f"plan_{KEY}": True}),
			"the staff-list switch did not open the Company group for a plain "
			"employee, so the directory is unreachable for them")

	def test_with_the_switch_off_an_employee_still_has_no_group(self):
		"""So the widening really is the switch, and not the persona."""
		self.assertFalse(self._company_group(False, {}))
		self.assertFalse(self._company_group(False, {f"plan_{KEY}": False}))

	def test_the_group_carries_no_hr_screen_for_an_employee(self):
		"""Opening the group must not have handed an employee an HR screen.

		Read off the frame's own menu rather than from a list typed here, so an
		entry added later is covered by this check instead of slipping past it.
		"""
		import re

		path = frappe.get_app_path("alvoraa_portal", "public", "js", "ess",
		                           "next-frame.js")
		with open(path, encoding="utf-8") as handle:
			source = handle.read()
		block = source[source.index('key: "company"'):source.index('var DEEP')]
		hr_only = re.findall(r'route: "(company/[a-z]+)"[^}]*?f\.is_hr', block)
		self.assertTrue(hr_only, "no HR-only Company entries were found at all, "
		                         "so this check proves nothing")
		for route in hr_only:
			self.assertNotEqual(
				"company/staff", route,
				"the People entry is gated on is_hr again, which undoes 045")

	def test_hr_already_has_the_group_with_or_without_the_switch(self):
		self.assertTrue(self._company_group(True, {f"plan_{KEY}": True}))
		self.assertTrue(self._company_group(True, {}))

	def test_the_things_that_did_open_it_still_do(self):
		"""So the assertion above is about the staff list, not about a group
		that stopped working."""
		self.assertTrue(self._company_group(False, {"plan_policy_library": True}))
		self.assertTrue(self._company_group(False, {"plan_org_structure": True}))
