"""Slice 034: the three structural checks the security review asked for.

These do not test behaviour. They test that behaviour tests EXIST, and that two
whole-file rules hold, so the next person to add an endpoint cannot quietly skip
either.

**AC-69 (SEC-2) - the registry.** The preview page is not a data control. Every
whitelisted function in `frame_api.py` and `inbox_api.py` is live on production
from the release that carries it, whatever page calls it. So each one ships with
a Guest-refused test, a wrong-persona test and a scope test IN THE SAME COMMIT.
The registry below names them; the test reads the module source and fails if a
whitelisted function has no entry, and fails again if an entry names a test that
does not exist. `test_portal_call_paths` does not prove this - it checks that a
path exists and is whitelisted, not that the function checks its caller.

**AC-70 (SEC-15) - no module-level state.** One worker serves several sites. A
module-level dict, list or set that is written to at run time is one site's data
in another site's request. Every constant in these modules is a tuple.

**AC-71 (SEC-6) - no `ignore_permissions`.** Not in these files, at all. The
repository-wide counter is a separate piece of work (residual risk R4); this
holds the two new files until it exists.

`inbox_api.py` was named here before it was written, on purpose: the day it
appeared, these three checks already applied to it, and its registry row was
part of the commit that created it. `staff_api.py` was added the same way, by
one line in MODULES - which is the whole point of listing the files rather than
the functions.
"""

import ast
import io
import os
import tokenize

import frappe
from frappe.tests.utils import FrappeTestCase

import alvoraa_portal

MODULES = ("frame_api.py", "inbox_api.py", "staff_api.py", "home_api.py",
           "pay_api.py", "time_api.py")

# AC-69. One row per whitelisted function. `guest`, `persona` and `scope` each
# name a test method that must exist in the test file named by `tests`.
#
# "scope" for get_frame means: what this caller is shown is decided by what they
# are, not by what the browser asked for. It takes no arguments at all, so its
# scope case is the persona table itself.
ENDPOINT_REGISTRY = {
	"frame_api.get_frame": {
		"tests": "alvoraa_portal.tests.test_frame_api_034",
		"guest": "TestWhoMayCallIt.test_guest_is_refused",
		"persona": "TestThePersonaRules.test_rule_six_needs_no_active_employee_record",
		"scope": "TestWhatEachPersonaMayOpen.test_time_pay_and_growth_need_an_employee_record",
	},
	# The frame's second and last start-up call (US-6). Its "scope" case is the
	# corrections queue, because that is the one part of the count whose scope
	# differs by caller - a store's HR person counts their store, and a reviewer
	# who is not HR keeps their whole queue (W1D-05, W1D-14).
	"inbox_api.get_nav_counts": {
		"tests": "alvoraa_portal.tests.test_inbox_counts_034",
		"guest": "TestTheShapeOfThePayload.test_guest_is_refused",
		"persona": "TestAPlainEmployeeCountsNothingThatIsNotTheirs.test_a_plain_employee_approves_nothing",
		"scope": "TestTheCorrectionsCountEqualsItsScreen.test_store_hr_counts_their_store_and_nobody_elses",
	},
	# Wave 2's Inbox screen (042 AC-41). Same three cases as the count it sits
	# beside, because the rows are where a scope mistake becomes something a
	# person can read rather than a number they can only wonder about.
	"inbox_api.get_inbox": {
		"tests": "alvoraa_portal.tests.test_inbox_parts_042",
		"guest": "TestWhoMayCallTheInbox.test_guest_is_refused",
		"persona": "TestWhoMayCallTheInbox.test_a_plain_employee_gets_an_inbox_with_no_approvals_in_it",
		"scope": "TestStoreHrSeesTheirStore.test_priya_counts_her_store_and_nobody_elses",
	},
	# Wave 2's Home (042 AC-41). Its "scope" case is the team card, because that
	# is the one part of Home that describes anybody but the caller.
	"home_api.get_home": {
		"tests": "alvoraa_portal.tests.test_home_api_042",
		"guest": "TestThePayloadIsTheControl.test_guest_is_refused",
		"persona": "TestACallerWithNoEmployeeRecord.test_asha_gets_a_working_page_and_no_scoped_query_runs",
		"scope": "TestTheTeamCardIsCountsOnly.test_a_person_with_no_manager_gets_no_peer_card",
	},
	# The staff list (W1D-21, SEC-16). Its "persona" case is the one that
	# matters most for this endpoint: the feature switch is checked on the
	# SERVER, so an HR user on a tenant that was never given the feature is
	# refused when they call it by hand (abuse case A14).
	"staff_api.get_staff_list": {
		"tests": "alvoraa_portal.tests.test_staff_list_034",
		"guest": "TestWhoMayCallTheStaffList.test_guest_is_refused",
		"persona": "TestWhoMayCallTheStaffList.test_a_plain_employee_is_refused",
		"scope": "TestWhatTheStaffListShows.test_store_hr_gets_their_store_and_nobody_else",
	},
	# Wave 3's Why? sheet (043 AC-42). Its "scope" case is the only scope this
	# endpoint has: own record, and nothing else, for everybody including HR.
	# There is no wider view of it anywhere in the product, on purpose - a
	# manager may never learn what a report lost in pay.
	# Wave 3's Time screen (043 AC-42). Its "scope" case is the one place this
	# endpoint answers about somebody other than the caller: a manager opening
	# a report's month through `attendance_correction._subject`. The test that
	# carries it proves the answer stops at the month - no leave, no rule, no
	# pay - because that is where a scope mistake here would become a person's
	# leave balance on their manager's screen.
	"time_api.get_time": {
		"tests": "alvoraa_portal.tests.test_time_api_043",
		"guest": "TestWhoMayCallIt.test_guest_is_refused",
		"persona": "TestWhoMayCallIt.test_a_caller_with_no_employee_record_is_refused",
		"scope": "TestSomebodyElsesMonthCarriesNothingElse.test_no_leave_no_rule_and_no_pay_reach_a_manager",
	},
	# Wave 3's Pay screen (043 AC-42). Own record only, for everybody,
	# including HR - there is no wider view of a payslip anywhere in the
	# product, so its "scope" case is the payroll gate and the single refusal
	# sentence that cannot tell a caller what exists.
	"pay_api.get_pay": {
		"tests": "alvoraa_portal.tests.test_pay_screen_043",
		"guest": "TestWhoMayCallThePayScreen.test_guest_is_refused",
		"persona": "TestWhoMayCallThePayScreen.test_a_caller_with_no_employee_record_gets_no_slips",
		"scope": "TestWhoMayCallThePayScreen.test_a_tenant_without_payroll_is_refused",
	},
	"pay_api.get_deduction_explanation": {
		"tests": "alvoraa_portal.tests.test_why_sheet_043",
		"guest": "TestWhoMayCallIt.test_guest_is_refused",
		"persona": "TestWhoMayCallIt.test_a_caller_with_no_employee_record_is_refused",
		"scope": "TestWhoMayCallIt.test_somebody_elses_deduction_is_refused",
	},
}


def _module_files():
	"""The files these rules cover, skipping any not written yet."""
	root = os.path.dirname(os.path.abspath(alvoraa_portal.__file__))
	found = []
	for name in MODULES:
		path = os.path.join(root, name)
		if os.path.isfile(path):
			found.append((name, path))
	return found


def _source(path):
	return io.open(path, encoding="utf-8").read()


def _dotted_name(node):
	"""`frappe.db.count` for the node behind that call, or "" for anything that
	is not a plain dotted name. An AST walk rather than a text search, because
	`_code_only` puts spaces around every dot and a dotted name would never
	match."""
	parts = []
	while isinstance(node, ast.Attribute):
		parts.append(node.attr)
		node = node.value
	if not isinstance(node, ast.Name):
		return ""
	parts.append(node.id)
	return ".".join(reversed(parts))


def _code_only(path):
	"""The file with every comment and every string literal removed.

	The `ignore_permissions` check below has to look at CODE. Reading the raw
	text would fail on the sentence in frame_api's own docstring that promises
	the flag is not used - which is the opposite of what the check is for. A
	plain text search is still the right shape for the check itself, because it
	catches getattr tricks and kwargs dicts that an AST walk would miss; it just
	has to be told what is prose.
	"""
	kept = []
	with io.open(path, "rb") as handle:
		for tok in tokenize.tokenize(handle.readline):
			if tok.type in (tokenize.COMMENT, tokenize.STRING):
				continue
			kept.append(tok.string)
	return " ".join(kept)


def _whitelisted_functions(tree):
	"""Top-level functions carrying @frappe.whitelist(...)."""
	names = []
	for node in tree.body:
		if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
			continue
		for dec in node.decorator_list:
			call = dec.func if isinstance(dec, ast.Call) else dec
			if isinstance(call, ast.Attribute) and call.attr == "whitelist":
				names.append(node.name)
				break
	return names


class TestEveryNewEndpointHasItsThreeCases(FrappeTestCase):
	def test_at_least_one_module_is_present(self):
		"""If neither file exists, the checks below pass by doing nothing. Say so."""
		self.assertTrue(_module_files(), "frame_api.py is missing - the rest of this file is vacuous")

	def test_every_whitelisted_function_is_in_the_registry(self):
		for name, path in _module_files():
			module = name[:-3]
			for fn in _whitelisted_functions(ast.parse(_source(path))):
				key = f"{module}.{fn}"
				self.assertIn(
					key, ENDPOINT_REGISTRY,
					f"{key} is whitelisted and has no registry entry. Add it, with its "
					f"Guest-refused, wrong-persona and scope tests, in the same commit (SEC-2).",
				)

	def test_the_registry_names_no_function_that_has_gone(self):
		live = set()
		for name, path in _module_files():
			module = name[:-3]
			live.update(f"{module}.{fn}" for fn in _whitelisted_functions(ast.parse(_source(path))))
		for key in ENDPOINT_REGISTRY:
			if key.split(".")[0] + ".py" in [n for n, _ in _module_files()]:
				self.assertIn(key, live, f"{key} is in the registry but is no longer whitelisted")

	def test_every_named_case_is_a_test_that_exists(self):
		"""A registry of names nobody runs would be worse than no registry."""
		for key, row in ENDPOINT_REGISTRY.items():
			module = frappe.get_module(row["tests"])
			for kind in ("guest", "persona", "scope"):
				cls_name, method = row[kind].split(".")
				cls = getattr(module, cls_name, None)
				self.assertIsNotNone(cls, f"{key}: {row[kind]} names a class that does not exist")
				self.assertTrue(
					callable(getattr(cls, method, None)),
					f"{key}: {row[kind]} names a test method that does not exist",
				)


class TestNoModuleLevelStateAndNoIgnorePermissions(FrappeTestCase):
	def test_no_global_statement(self):
		"""AC-70. `global` in a web worker is one request writing another's data."""
		for name, path in _module_files():
			for node in ast.walk(ast.parse(_source(path))):
				self.assertNotIsInstance(node, ast.Global, f"{name} uses `global`")

	def test_no_module_level_dict_list_or_set(self):
		"""AC-70. A tuple cannot be appended to; a list, dict or set can be, and
		a worker serves several sites. Constants in these modules are tuples."""
		for name, path in _module_files():
			for node in ast.parse(_source(path)).body:
				if not isinstance(node, (ast.Assign, ast.AnnAssign)):
					continue
				value = node.value
				if isinstance(value, (ast.Dict, ast.List, ast.Set, ast.ListComp,
				                      ast.DictComp, ast.SetComp)):
					targets = node.targets if isinstance(node, ast.Assign) else [node.target]
					label = ", ".join(getattr(t, "id", "?") for t in targets)
					self.fail(f"{name}: module-level mutable `{label}` (line {node.lineno}). "
					          f"Use a tuple, or build it inside the function.")

	def test_no_ignore_permissions_anywhere_in_these_files(self):
		"""AC-71 / SEC-6, first half. Not "few". None."""
		for name, path in _module_files():
			self.assertNotIn("ignore_permissions", _code_only(path),
			                 f"{name} uses ignore_permissions")

	def test_every_other_way_past_the_permission_layer_is_declared(self):
		"""AC-71 / SEC-6, second half (F7).

		The check above is a string search for one flag, and the claim on it used
		to be the much larger "these files do not bypass permissions". They do.
		`frappe.get_all`, `frappe.db.count` and `frappe.db.sql` all skip Frappe's
		own permission layer by definition, and a search for `ignore_permissions`
		walks straight past every one of them.

		Nothing leaks today: every call below sits inside the shared scope filter,
		which is explicit and fails closed. What IS lost is any extra narrowing a
		tenant has configured - a User Permission on Employee by department would
		be honoured by `frappe.get_list` and is ignored by these. That is a real
		difference and it should be a decision, not an accident.

		So the ban stays absolute for the flag, and every other route past the
		permission layer is COUNTED here. Add one and this test goes red until
		somebody writes it down. What the check proves is "no UNDECLARED bypass",
		which is what it has always actually been able to prove.
		"""
		declared = {
			# frame_api: one count of a person's own reports, to decide whether
			# they see a Team entry. No rows, no fields, one boolean.
			"frame_api.py": ("frappe.db.count",),
			# inbox_api, after slice 042 reshaped it into parts. THREE now, down
			# from six: the five counts became `frappe.get_list` through
			# `_count_rows`, because a count and its list must be the same
			# query and the list was already a get_list. What is left:
			#
			#   `_leave_contexts`   - the "2 other people are away on those
			#     days" aggregate. Under get_list a plain employee who happens
			#     to be a named approver would read 0, because they may not see
			#     a colleague's leave row, and a wrong number is worse than no
			#     number. Only the COUNT leaves the function; no name, no leave
			#     type, no row.
			#   `_part_goal_updates` - one Employee name lookup for ids that are
			#     already inside `goals_api._pending_approvals_scope`. The scope
			#     decided who; this only turns ids into names.
			#   `_part_policies`    - the caller's OWN Policy Acknowledgement
			#     rows, filtered to their own employee id. The readable policies
			#     beside it are a get_list, which is where the permission
			#     question actually is.
			# ...plus the four `frappe.qb.from_` queries in the goal-updates
			# part. They were always here; this test could not see them until
			# 044 R4 added `frappe.qb.get_query` to the watched list and the
			# blind spot became obvious. Two count them and two list them, and
			# all four take the SAME scope subquery out of the part's one filter
			# expression - which is the control, not the call.
			"inbox_api.py": ("frappe.get_all",) * 3 + ("frappe.qb.from_",) * 4,
			# home_api (slice 042, re-counted for 044 R1/D6). EIGHT reads, one
			# count and one aggregate, and all but two are the CALLER'S OWN
			# record:
			#
			#   own: Shift Assignment, Employee Checkin, Holiday, Attendance,
			#     Leave Application, Attendance Request, Individual Goal - every
			#     one filtered to `employee = the caller's own Active record`,
			#     which `_me` resolved. get_list would add nothing: a tenant
			#     cannot narrow a person out of their own attendance.
			#   `_reports` - Employee ids by `reports_to`, used only to decide
			#     which group the team card is about. No name and no field
			#     leaves it.
			#   `_presence_counts` - the team card, now two aggregates instead
			#     of a name list plus a row-per-person lookup (044 D6). The
			#     group is a condition on Employee built from
			#     `permitted_employee_filters()`, the shared scope helper: one
			#     statement counts the group, one counts today's Attendance by
			#     status, and "still to come" is the subtraction. The status is
			#     collapsed into in / away / due, so no name, no row and no
			#     leave type can reach a caller even by accident. Two
			#     `frappe.qb.get_query` (the group count and the scope subquery)
			#     and one `frappe.qb.from_`. **All three are new to this list.**
			#     They bypass the permission layer exactly as `frappe.get_all`
			#     does, and until 044 this test did not watch them, so a scope
			#     written in the query builder was an undeclared route. It is
			#     declared now.
			#   the team goal summary - one integer over a scope
			#     `permitted_employees()` already decided. **It was a
			#     `frappe.db.count` until 045 and is now a ninth
			#     `frappe.get_all`.** The two do not agree on a negation:
			#     `get_all` writes `IFNULL(`status`,'') <> 'Cancelled'` and
			#     `db.count` writes a bare `<>`, and `NULL <> 'Cancelled'` is
			#     NULL in SQL - so the count dropped every goal with a NULL
			#     status while the Goals screen listed it. Counting through the
			#     list path is the fix, and it is the same route past the
			#     permission layer as before, over the same scope.
			#
			# `_peers` is gone: the peer group is one of the three conditions
			# `_scope_filters` returns, so it is no longer a separate read.
			#
			# The HR scope itself is never read here: it comes from
			# `permitted_employees()` and `permitted_employee_filters()`, which
			# are the shared definitions.
			"home_api.py": (("frappe.get_all",) * 9
			                + ("frappe.qb.get_query",) * 2 + ("frappe.qb.from_",)),
			# staff_api: the staff list itself and its total. Both take the same
			# filters dict, built by the shared scope helper.
			"staff_api.py": ("frappe.db.count", "frappe.get_all"),
			# time_api (slice 043). FIVE reads, and every one of them is
			# filtered to a SINGLE employee id that `attendance_correction.
			# _subject` already decided the caller may open:
			#
			#   `_shift_card`       - today's Shift Assignment, `employee = me`.
			#   `_days_off`         - the weekly-off rows of the holiday list
			#     ERPNext says this person is on. A Holiday row holds a date and
			#     a description and says nothing about anybody.
			#   `_past_leave`       - the caller's own Leave Applications, and
			#     their own Leave Ledger Entry rows. Both `employee = me`.
			#   `_record_this_year` - the caller's own Attendance Deduction
			#     rows, `employee = me`, bounded by the financial year and
			#     capped, with the cap declared in the payload.
			#
			# `get_list` would add nothing to any of them: a tenant cannot
			# narrow a person out of their own attendance, and these are only
			# ever reached on the `is_self` branch. The month calendar itself
			# is `attendance_correction`'s, which uses `frappe.get_list`
			# throughout and is not this file.
			"time_api.py": ("frappe.get_all",) * 5,
		}
		# `frappe.qb.get_query` and `frappe.qb.from_` join the list in 044.
		# A query written in the query builder skips Frappe's permission layer
		# just as `frappe.get_all` does, and this test used to walk past every
		# one of them - so "no undeclared bypass" was not true for the four in
		# the Inbox's goal-updates part. It is true now.
		watched = ("frappe.get_all", "frappe.db.get_all", "frappe.db.count",
		           "frappe.db.sql", "frappe.db.sql_list", "frappe.db.multisql",
		           "frappe.qb.get_query", "frappe.qb.from_")

		for name, path in _module_files():
			found = []
			for node in ast.walk(ast.parse(_source(path))):
				if not isinstance(node, ast.Call):
					continue
				dotted = _dotted_name(node.func)
				if dotted in watched:
					found.append(dotted)
			self.assertEqual(
				sorted(found), sorted(declared.get(name, ())),
				f"{name}: the calls that get past Frappe's permission layer are not the "
				f"ones declared in this test. Found {sorted(found)}. If you added one, "
				f"say here why the scope filter around it is enough - or use "
				f"frappe.get_list, which honours a tenant's own User Permissions.")
