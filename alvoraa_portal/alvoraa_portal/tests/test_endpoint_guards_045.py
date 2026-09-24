"""045 - every new whitelisted endpoint, called as Guest and as the wrong person.

A non-negotiable for this wave: **every new whitelisted endpoint ships Guest,
wrong-persona and scope tests in the same commit.** This file is that, and it
is written so that a new endpoint added later without its guards fails here
rather than passing quietly - the endpoint list is discovered from the modules,
not typed out.

Two more rules checked here because they are easiest to break in a new module:

* **Refusals read identically** whether the cause is "your tenant did not buy
  it" or "you are not allowed". A different sentence for a different cause
  tells the caller which guess was closer.
* **No scope helper returns an empty filter dict.** An empty filter is not a
  narrow scope, it is every row in the table.
"""

import inspect

import frappe

from alvoraa_portal import growth_api, team_api
from alvoraa_portal.tests.fixtures_045 import Wave4Base

WAVE4_MODULES = (team_api, growth_api)


def whitelisted_in(module):
	"""Every whitelisted function this module actually exposes.

	Discovered rather than listed, so an endpoint added next month without
	guards fails this file instead of slipping past it.
	"""
	out = []
	for name, fn in vars(module).items():
		if not callable(fn) or getattr(fn, "__module__", None) != module.__name__:
			continue
		# **`frappe.whitelisted` is the register, and membership is by the
		# FUNCTION OBJECT.** The first version of this looked for a
		# `whitelisted` attribute on the function, which does not exist - so it
		# discovered nothing and every Guest check below looped over an empty
		# list and passed. `test_the_discovery_itself_finds_the_endpoints_we_know_about`
		# is what caught it, which is the whole reason that test is here: a
		# green suite over an empty loop is the failure you cannot see from
		# outside.
		if fn in frappe.whitelisted:
			out.append((name, fn))
	return out


class TestGuestReachesNothing(Wave4Base):
	def test_every_wave_four_endpoint_refuses_a_guest(self):
		"""Not one of them is `allow_guest`, and calling as Guest refuses.

		Both halves matter: the decorator is the declaration and the call is
		the fact. A decorator can be right while the function reads
		`frappe.session.user` and finds "Guest" acceptable.
		"""
		found = 0
		for module in WAVE4_MODULES:
			for name, fn in whitelisted_in(module):
				found += 1
				with self.subTest(endpoint=f"{module.__name__}.{name}"):
					self.assertFalse(
						getattr(fn, "allow_guest", False),
						f"{name} is whitelisted with allow_guest")
					frappe.set_user("Guest")
					try:
						result = fn()
					except Exception as exc:
						self.assertIsInstance(
							exc, (frappe.PermissionError, frappe.ValidationError,
							      frappe.AuthenticationError),
							f"{name} failed as Guest for the wrong reason: {exc!r}")
					else:
						# A quiet empty answer is acceptable only if it is
						# genuinely empty - never a populated payload.
						self.assertTrue(
							result in (None, {}, []) or result.get("no_employee"),
							f"{name} answered a Guest with data: {result!r}")
					finally:
						frappe.set_user("Administrator")
		self.assertTrue(found, "no whitelisted endpoints were discovered at all, "
		                       "so this test proves nothing")

	def test_the_discovery_itself_finds_the_endpoints_we_know_about(self):
		"""Check the check. If discovery returns nothing, the test above is
		green over an empty loop."""
		names = {n for m in WAVE4_MODULES for n, _f in whitelisted_in(m)}
		self.assertIn("get_team", names)
		self.assertIn("get_company_values", names)


class TestTheWrongPersonaIsRefused(Wave4Base):
	def test_a_person_with_no_reports_and_no_hr_role_gets_no_team(self):
		"""Rahul. Team is not in his menu, and typing the route must not
		hand him a populated screen."""
		self.as_user(self.rahul_user)
		d = team_api.get_team()
		self.assertEqual(0, d["direct"]["total"])
		self.assertFalse(d["is_hr_scope"])
		self.assertIsNone(d["covered"])
		self.assertFalse(d["has_direct"])
		self.assertFalse(d["has_covered"])

	def test_a_manager_who_is_not_hr_is_refused_every_hr_only_action(self):
		self.as_user(self.sandeep_user)
		for act in (team_api.ACT_INVITE_OR_BLOCK_PHONE,
		            team_api.ACT_CANCEL_DEDUCTION, team_api.ACT_ACT_AS_HR):
			with self.subTest(action=act):
				ok, _r = team_api.may(act, self.rahul)
				self.assertFalse(ok)

	def test_a_caller_with_no_employee_record_gets_no_employee_not_a_screen(self):
		user = "s045.noemployee@example.com"
		if not frappe.db.exists("User", user):
			doc = frappe.get_doc({"doctype": "User", "email": user,
			                      "first_name": "S045 NoEmployee",
			                      "send_welcome_email": 0})
			doc.append("roles", {"role": "Employee"})
			doc.insert(ignore_permissions=True)
			frappe.db.commit()
		self.as_user(user)
		self.assertTrue(team_api.get_team().get("no_employee"))


class TestNoScopeHelperReturnsEverything(Wave4Base):
	def test_no_wave_four_helper_can_return_an_empty_filter(self):
		"""An empty filter is not a narrow scope, it is the whole table.

		Checked by calling the helpers with the shapes that have produced a
		fail-open before: no employee id, and no employee id with HR true.
		"""
		for user, emp in ((self.kamal_user, None), ("Administrator", None),
		                  (self.priya_user, None)):
			with self.subTest(user=user, emp=emp):
				conds = team_api.covered_conditions(user, emp)
				self.assertTrue(conds, "an empty condition list was returned")
				self.assertIn(["name", "in", []], conds,
				              "a caller with no employee id was not failed closed")

	def test_the_direct_subquery_fails_closed_with_no_employee_id(self):
		from alvoraa_portal.hr_api import direct_reports_query

		q = direct_reports_query(None)
		self.assertEqual([], [row[0] for row in q.run()],
		                 "the direct-reports subquery matched somebody for a "
		                 "caller with no employee id")


class TestRefusalsReadIdentically(Wave4Base):
	def test_one_sentence_whatever_the_cause(self):
		"""A plain employee must not be able to tell "not bought" from
		"not allowed" - the first is a fact about the company, the second a
		fact about a colleague's role."""
		self.as_user(self.rahul_user)
		_ok_a, out_of_scope = team_api.may(team_api.ACT_OPEN_RECORD,
		                                   self.covered_only[0])
		_ok_b, no_such = team_api.may(team_api.ACT_OPEN_RECORD, "NO-SUCH-EMPLOYEE")
		self.assertEqual(out_of_scope, no_such)
		self.assertEqual(team_api.REFUSAL, out_of_scope)

	def test_no_refusal_carries_anybodys_name_or_number(self):
		self.as_user(self.rahul_user)
		_ok, reason = team_api.may(team_api.ACT_APPROVE_LEAVE, self.covered_only[0])
		for leak in ("S045", "MOBILE", self.covered_only[0]):
			self.assertNotIn(leak, reason)
