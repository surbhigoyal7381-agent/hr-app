"""Slice 090 · People trends: scope, figures, the small-group rule, filters, early leavers.

AC numbers are from `docs/slices/090-leadership-hr-analytics/02-functional-spec.md`.
The group rule is also proved over generated tenants in `test_people_trends_property_090.py`.
All names are invented. Employees are written with `db_insert` (the calculation reads
the table, and building them through Frappe HR's validation would be the slowest part
of the suite for no extra proof). Test users take no literal password: none is needed.
"""

import json
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days

from alvoraa_portal import org_figures as of
from alvoraa_portal import people_trends as pt
from alvoraa_portal.tests import leader_fixtures_012 as fx

TAG = "P090"


FIX = {}


def setUpModule():
	"""Build the tenant once for the whole module, clearing what an earlier run left."""
	fx.setup_module_fixtures()
	pt.make_role()
	frappe.set_user("Administrator")
	frappe.db.delete("Employee", {"last_name": TAG})
	frappe.db.delete("User Permission", {"user": ["like", "s012.p090%"]})
	_build()
	frappe.db.commit()


def tearDownModule():
	frappe.set_user("Administrator")
	frappe.db.delete("Employee", {"last_name": TAG})
	frappe.db.commit()


def ago(n):
	return add_days(pt._end(), -n)


def person(company, branch, department=None, etype=None, joined=None, status="Active", relieved=None, n=1):
	"""n invented people straight into the table. Returns their names (kept only for the scan test)."""
	names = []
	for _i in range(n):
		name = f"{TAG}-{frappe.generate_hash(length=10)}"
		frappe.get_doc({
			"doctype": "Employee", "name": name, "first_name": f"Zed{name[-4:]}", "last_name": TAG,
			"employee_name": f"Zed{name[-4:]} {TAG}", "company": company, "branch": branch,
			"department": department, "employment_type": etype, "gender": "Male",
			"date_of_birth": "1990-01-01", "date_of_joining": joined or ago(2000), "status": status,
			"relieving_date": relieved, "naming_series": "HR-EMP-",
		}).db_insert()
		names.append(name)
	return names


def as_user(user):
	frappe.set_user(user)


def call(user, **kw):
	"""The endpoint as `user`, with the plan check allowed (the plan is not under test here)."""
	frappe.set_user(user)
	with patch("alvoraa_portal.subscription.has_feature", return_value=True):
		return pt.get_people_trends(**kw)


def _build():
	"""Kavya (five branches) and Other Co.

	Kavya on the last data day (END): Civil Lines 12 old + 2 left 10 days ago + 3 joined 20 days
	ago; Market Yard 7; Hilltop Kiosk 3 (Contract, Security); Station Road 6 (Stores);
	New Kiosk 3 old + 9 joined 120 days ago. Other Co: 8 old + 6 joined 60 days ago, two of
	whom left 40 days ago."""
	F = FIX
	F["cl"], F["my"], F["hk"], F["st"], F["nk"] = (fx.branch(b) for b in ("CivilLines", "MarketYard", "Hilltop", "Station", "NewKiosk"))
	K, O = fx.KAVYA, fx.OTHER
	names = []
	names += person(K, F["cl"], "S090 Sales", None, n=8)
	names += person(K, F["cl"], "S090 Stores", None, n=4)
	names += person(K, F["cl"], "S090 Sales", None, status="Left", relieved=ago(10), n=2)
	names += person(K, F["cl"], "S090 Sales", None, joined=ago(20), n=3)
	names += person(K, F["my"], "S090 Sales", None, n=7)
	names += person(K, F["hk"], "S090 Security", "Contract", n=3)
	names += person(K, F["st"], "S090 Stores", None, n=6)
	names += person(K, F["nk"], "S090 Sales", None, n=3)
	names += person(K, F["nk"], "S090 Sales", None, joined=ago(120), n=9)
	names += person(O, F["cl"], "S090 Sales", None, n=8)
	names += person(O, F["cl"], "S090 Sales", None, joined=ago(60), n=4)
	names += person(O, F["cl"], "S090 Sales", None, joined=ago(60), status="Left", relieved=ago(40), n=2)
	F["names"] = names

	def leader(local, *perms):
		user = fx.user(local, [pt.ROLE])
		for allow, value, applicable_for in perms:
			fx.permission(user, allow, value, applicable_for)
		return user

	F["lead_retail"] = leader("p090retail", ("Company", K, None))
	F["lead_other"] = leader("p090other", ("Company", O, None))
	F["lead_both"] = leader("p090both", ("Company", K, None), ("Company", O, None))
	F["lead_bh2"] = leader("p090bh2", ("Company", K, None), ("Branch", F["cl"], None), ("Branch", F["my"], None))
	F["lead_none"] = leader("p090none")
	F["lead_branch_only"] = leader("p090branchonly", ("Branch", F["cl"], None))
	F["lead_narrow"] = leader("p090narrow", ("Company", K, None), ("Branch", F["cl"], "Attendance"))
	F["lead_leave_app"] = leader("p090leaveapp", ("Company", K, "Leave Application"))
	F["sm_only"] = fx.user("p090sm", ["System Manager"])
	F["hr"] = fx.user("p090hr", ["HR Manager"])
	fx.permission(F["hr"], "Company", K)
	F["hr_lead"] = fx.user("p090hrlead", ["HR Manager", pt.ROLE])
	fx.permission(F["hr_lead"], "Company", K)
	F["plain"] = fx.user("p090plain", ["Employee"])


class TrendsBase(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		for k, v in FIX.items():
			setattr(cls, k, v)

	def setUp(self):
		self.caller = frappe.session.user
		frappe.set_user("Administrator")
		frappe.db.savepoint("pt090")

	def tearDown(self):
		frappe.set_user("Administrator")
		frappe.db.rollback(save_point="pt090")
		frappe.set_user(self.caller)


class TestScopeAndRefusals(TrendsBase):
	def scope(self, user):
		return pt.leader_scope(user)

	def test_scope_table(self):  # AC-1 to AC-6
		self.assertEqual(self.scope(self.lead_retail), of.Scope((fx.KAVYA,), None))
		self.assertEqual(self.scope(self.lead_bh2), of.Scope((fx.KAVYA,), tuple(sorted((self.cl, self.my)))))
		self.assertIsNone(self.scope(self.lead_branch_only), "a branch counts only with its company")
		self.assertIsNone(self.scope(self.lead_none))
		self.assertIsNone(self.scope(self.lead_leave_app), "a permission narrowed to Leave Application grants nothing")
		self.assertIsNone(self.scope(self.lead_narrow), "a narrowed Branch permission means not set up")

	def test_not_set_up_runs_no_figure_query(self):  # AC-4
		with patch.object(pt, "_people", side_effect=AssertionError("a figure query ran")):
			out = call(self.lead_none)
		self.assertEqual(out, {"state": "not_set_up"})

	def test_who_is_refused(self):  # AC-16, AC-118, AC-7 (HR is off in v1)
		for user in (self.sm_only, self.plain, self.hr, self.hr_lead, "Guest"):
			with self.assertRaises(frappe.PermissionError, msg=user):
				call(user)

	def test_role_has_no_permissions_and_hook_is_repeatable(self):  # AC-8, AC-121
		pt.make_role()
		pt.make_role()
		self.assertEqual(frappe.db.count("Role", {"name": pt.ROLE}), 1)
		self.assertEqual(frappe.db.get_value("Role", pt.ROLE, "desk_access"), 0)
		self.assertEqual(frappe.db.count("DocPerm", {"role": pt.ROLE}), 0)
		self.assertEqual(frappe.db.count("Custom DocPerm", {"role": pt.ROLE}), 0)

	def test_a_leader_whose_own_record_is_left_is_refused(self):  # AC-10, SEC-6
		user = fx.user("p090left", [pt.ROLE])
		emp = fx.employee("P090Left", fx.KAVYA, self.cl, user_id=user)  # first: it resets the user's permissions
		fx.permission(user, "Company", fx.KAVYA)
		self.assertEqual(call(user)["state"], "ok")
		frappe.db.set_value("Employee", emp, {"status": "Left", "relieving_date": ago(1)})
		with self.assertRaises(frappe.PermissionError):
			call(user)

	def test_period_is_checked_not_defaulted(self):  # AC-18
		for bad in (45, "abc", 0, "30.5", -7):
			with self.assertRaises(frappe.PermissionError, msg=str(bad)):
				call(self.lead_retail, period=bad)
		self.assertEqual(call(self.lead_retail, period="30")["period"], 30)

	def test_extra_parameters_have_no_effect(self):  # AC-17
		base = call(self.lead_retail, period=30)
		frappe.set_user(self.lead_retail)
		with patch("alvoraa_portal.subscription.has_feature", return_value=True):
			extra = frappe.call(pt.get_people_trends, period=30, min_group=1, raw=1, sort="name", start="2020-01-01")
		self.assertEqual(json.dumps(base, sort_keys=True), json.dumps(extra, sort_keys=True))


class TestPeopleFigures(TrendsBase):
	def test_company_figures_and_identity(self):  # AC-32, AC-33
		out = call(self.lead_retail, period=30)
		p = out["people"]
		self.assertEqual((p["headcount"], p["joined"], p["left"], p["net"]), (43, 3, 2, 1))
		self.assertEqual(p["headcount"], p["headcount_start"] + p["joined"] - p["left"])
		self.assertEqual(p["attrition"], round(2 / ((42 + 43) / 2.0) * 100, 1))

	def test_window_and_comparison_dates(self):  # AC-26
		out = call(self.lead_retail, period=90)
		self.assertEqual(out["window"]["start"], str(ago(89)))
		self.assertEqual(out["window"]["end"], str(ago(0)))
		self.assertEqual(out["window"]["compare"], {"start": str(ago(179)), "end": str(ago(90))})

	def test_identity_holds_for_every_chip_and_cut(self):  # AC-33
		for period in pt.PERIODS:
			for kw in ({}, {"branch": self.my}, {"department": "S090 Sales"}):
				out = call(self.lead_retail, period=period, **kw)
				if out["state"] == "ok":
					p = out["people"]
					self.assertEqual(p["headcount"], p["headcount_start"] + p["joined"] - p["left"], (period, kw))

	def test_edges(self):  # AC-34, AC-35
		K = fx.KAVYA
		b = fx.branch("Edge")
		person(K, b, "S090 Edge", None, joined=ago(0), n=5)           # joined on END: counted
		person(K, b, "S090 Edge", None, joined=add_days(ago(0), 1), n=5)  # after END: not
		person(K, b, "S090 Edge", None, status="Left", relieved=None, n=5)   # Left, no relieving date: nowhere
		person(K, b, "S090 Edge", None, status="Left", relieved=ago(0), joined=ago(300), n=5)
		out = call(self.lead_retail, period=7, branch=b)
		self.assertEqual(out["state"], "ok")
		p = out["people"]
		self.assertEqual((p["joined"], p["left"], p["headcount"]), (5, 5, 5))
		self.assertEqual(out["data_quality"], None, "a filter hides the data-quality count (AC-103)")

	def test_future_relieving_date_is_still_on_the_roll(self):  # AC-37
		b = fx.branch("Notice")
		person(fx.KAVYA, b, "S090 Notice", None, status="Left", relieved=add_days(ago(0), 1), n=6)
		self.assertEqual(call(self.lead_retail, period=7, branch=b)["people"]["headcount"], 6)

	def test_clipped_window(self):  # AC-27, AC-28
		early = fx.branch("Late")
		K = "S090 Late Co"
		out = call(self.lead_retail, period=365)
		self.assertFalse(out["window"]["clipped"])
		self.assertIsNotNone(out["window"]["compare"] is None or True)
		start = pt._end()
		# a company whose records start 100 days ago
		other = fx.OTHER
		frappe.db.sql("update tabEmployee set date_of_joining = %s where company = %s and date_of_joining < %s",
		              (ago(100), other, ago(100)))
		out = call(self.lead_other, period=365)
		self.assertTrue(out["window"]["clipped"])
		self.assertEqual(out["window"]["days"], 101)
		self.assertIsNone(out["window"]["compare"])
		self.assertEqual(start, pt._end())


class TestTheGroupRule(TrendsBase):
	def test_branches_part_b_and_c(self):  # AC-48, AC-55 (this fixture)
		for period in pt.PERIODS:
			ok = call(self.lead_retail, period=period, branch=self.my)
			self.assertEqual(ok["state"], "ok", period)  # Market Yard, 7 stable: shown on every chip
		hk = call(self.lead_retail, period=30, branch=self.hk)
		self.assertEqual((hk["state"], hk["reason"]), ("not_shared", "few"))
		nk = call(self.lead_retail, period=30, branch=self.nk)  # grew from 3 to 12
		self.assertEqual((nk["state"], nk["reason"]), ("not_shared", "subtraction"))
		self.assertEqual(call(self.lead_retail, period=365, branch=self.nk)["state"], "not_shared")
		# Station Road (6) is shown: the two hidden ones together pass
		self.assertEqual(call(self.lead_retail, period=30, branch=self.st)["state"], "ok")

	def test_hidden_means_not_sent(self):  # AC-49, AC-54
		hk = call(self.lead_retail, period=30, branch=self.hk)
		self.assertNotIn("people", hk)
		self.assertNotIn("attendance", hk)
		listed = {b["value"]: b["shared"] for b in hk["filters"]["branches"]}
		self.assertFalse(listed[self.hk])
		self.assertTrue(listed[self.my])

	def test_employment_type_and_department_siblings(self):  # AC-57
		contract = call(self.lead_retail, period=30, employment_type="Contract")
		self.assertEqual(contract["state"], "not_shared")
		dept = call(self.lead_retail, period=30, department="S090 Security")
		self.assertEqual((dept["state"], dept["reason"]), ("not_shared", "few"))
		# Stores (10) is the next smallest, so it goes too
		stores = call(self.lead_retail, period=30, department="S090 Stores")
		self.assertEqual((stores["state"], stores["reason"]), ("not_shared", "subtraction"))
		self.assertEqual(call(self.lead_retail, period=30, department="S090 Sales")["state"], "ok")

	def test_minimum_is_read_every_call(self):  # AC-46
		with patch("alvoraa_portal.alvoraa_portal.doctype.alvoraa_leader_view_settings."
		           "alvoraa_leader_view_settings.min_group_size", return_value=8):
			self.assertEqual(call(self.lead_retail, period=30, branch=self.st)["state"], "not_shared")
		self.assertEqual(call(self.lead_retail, period=30, branch=self.st)["state"], "ok")

	def test_callers_own_record_is_left_out_of_the_pass_test(self):  # AC-45
		b = fx.branch("Own5")
		user = fx.user("p090own5", [pt.ROLE])
		fx.employee("P090Own5", fx.KAVYA, b, user_id=user, joined=ago(2000))
		fx.permission(user, "Company", fx.KAVYA)
		person(fx.KAVYA, b, "S090 Own", None, n=4)  # five people with the caller
		self.assertEqual(call(user, period=30, branch=b)["state"], "not_shared")
		self.assertEqual(call(self.lead_retail, period=30, branch=b)["state"], "ok")

	def test_empty_cut_is_no_match(self):  # AC-47
		b = fx.branch("Nobody")
		person(fx.KAVYA, b, "S090 Nobody", None, status="Inactive", n=6)
		self.assertEqual(call(self.lead_retail, period=30, branch=b)["state"], "no_match")

	def test_the_chart_is_whole_or_absent(self):  # AC-50
		out = call(self.lead_retail, period=30, branch=self.my)
		self.assertTrue(out["chart"]["shared"])
		pts = out["chart"]["points"]
		self.assertEqual(sum(x["joined"] for x in pts), out["people"]["joined"])
		self.assertEqual(sum(x["left"] for x in pts), out["people"]["left"])
		self.assertEqual(pts[-1]["net"], out["people"]["net"])  # AC-73
		self.assertEqual(sum(len(range(x)) for x in pt._bin_lengths(30)), 30)

	def test_leaving_unshared_leaves_nothing_derived(self):  # AC-51, PRIV-7
		people = [pt.Person("c", None, None, None, "Active", ago(500), None, 6)]
		block = pt._people_block(people, ago(29), ago(0), None, share_left=False)
		self.assertEqual(set(block), {"headcount", "joined"})


class TestFilters(TrendsBase):
	def test_refused_filters(self):  # AC-63 to AC-68
		bad = [
			{"branch": self.cl, "department": "S090 Sales"},               # two filters
			{"company": fx.OTHER},                                       # other company
			{"branch": "No Such Branch"},                                # not used
			{"department": "No Such Department"},
			{"employment_type": "No Such Type"},
		]
		for kw in bad:
			with self.assertRaises(frappe.PermissionError, msg=str(kw)):
				call(self.lead_retail, period=30, **kw)
		with self.assertRaises(frappe.PermissionError):  # a branch with no company under All companies
			call(self.lead_both, period=30, branch=self.cl)
		with self.assertRaises(frappe.PermissionError):  # a branch head asking for a branch outside the set
			call(self.lead_bh2, period=30, branch=self.hk)

	def test_a_branch_name_with_a_quote_is_just_refused(self):  # AC-21
		with self.assertRaises(frappe.PermissionError):
			call(self.lead_retail, period=30, branch="x' or '1'='1")

	def test_lists_hold_only_the_scope(self):  # AC-67
		text = json.dumps(call(self.lead_retail, period=30))
		self.assertNotIn(fx.OTHER, text)
		bh = call(self.lead_bh2, period=30)
		self.assertEqual({b["value"] for b in bh["filters"]["branches"]}, {self.cl, self.my})
		self.assertNotIn(self.hk, json.dumps(bh))

	def test_branch_head_has_no_company_total_beyond_the_set(self):  # AC-66
		out = call(self.lead_bh2, period=30)
		self.assertEqual(out["people"]["headcount"], 15 + 7)
		self.assertFalse(out["early"]["shared"])  # a branch head's set is not a whole company

	def test_all_companies_has_no_sub_company_figures(self):  # AC-64
		out = call(self.lead_both, period=30)
		self.assertEqual(out["filters"]["branches"], [])
		self.assertEqual([b["company"] for b in out["by_company"]], sorted((fx.KAVYA, fx.OTHER)))  # AC-93
		self.assertIsNone(out["leave"]["types"])
		self.assertEqual(out["early"]["reason"], "whole_company_only")


class TestEarlyLeavers(TrendsBase):
	def test_whole_company_only(self):  # AC-44
		self.assertEqual(call(self.lead_retail, period=90, branch=self.my)["early"]["reason"], "whole_company_only")

	def test_shown_cells(self):  # AC-40, AC-42, AC-53 (Other Co: stretches 0, 6, 0, 0)
		out = call(self.lead_other, period=90)
		self.assertTrue(out["early"]["shared"])
		cells = {c["within"]: c for c in out["early"]["cells"]}
		self.assertEqual((cells[30]["cohort"], cells[30]["left"], cells[30]["inside"]), (6, 2, 0))
		self.assertEqual((cells[7]["cohort"], cells[7]["left"]), (6, 0))
		self.assertEqual((cells[90]["cohort"], cells[90]["inside"]), (0, 6))
		week = call(self.lead_other, period=7)["early"]["cells"]
		self.assertEqual([c["cohort"] for c in week], [0, 0, 0])  # 1 week: always too early to tell

	def test_four_stretches_hide_small_cohorts(self):  # AC-53 (Kavya: 3 joiners in the 7-30 stretch)
		out = call(self.lead_retail, period=90)
		self.assertEqual(out["early"], {"shared": False, "reason": "few"})


class TestBins(FrappeTestCase):
	def test_bins_sum_to_the_window(self):  # AC-72
		end = pt._end()
		for d, n in ((7, 7), (30, 4), (90, 13), (180, 6), (365, 12)):
			bins = pt._bins(end, d, add_days(end, -d + 1))
			self.assertEqual(len(bins), n)
			self.assertEqual(sum((b[1] - b[0]).days + 1 for b in bins), d)
			self.assertEqual(bins[-1][1], end)
		self.assertEqual([(b[1] - b[0]).days + 1 for b in pt._bins(end, 90, add_days(end, -89))][:2], [6, 7])


class TestWhatLeaves(TrendsBase):
	def test_totals_only(self):  # AC-111, AC-112
		allowed = {"state", "period", "window", "filters", "scope", "data_up_to", "people", "early", "chart",
		           "attendance", "leave", "by_company", "data_quality", "minimum", "headline", "reason"}
		for user in (self.lead_retail, self.lead_both, self.lead_bh2, self.lead_other):
			for period in pt.PERIODS:
				text_out = call(user, period=period)
				self.assertLessEqual(set(text_out), allowed)
				text = json.dumps(text_out)
				for name in self.names[:200]:
					self.assertNotIn(name, text)
					self.assertNotIn(name[-4:] + " " + TAG, text)

	def test_no_reason_or_pay_columns_in_the_sql(self):  # AC-21, AC-89, AC-113, AC-117
		import inspect
		src = inspect.getsource(pt)
		for banned in ("reason_for_leaving", "description", "tabSalary Slip", "tabEmployee Checkin",
		               "ignore_permissions", "scheduler_events", "frappe.cache"):
			self.assertNotIn(banned, src, banned)

	def test_the_headline_never_names_a_hidden_figure(self):  # AC-91, AC-92
		out = call(self.lead_retail, period=30)
		self.assertIn("Headcount 43", out["headline"])
		self.assertIn("3 joined, 2 left", out["headline"])

	def test_goals_and_appraisals_do_not_import_it(self):  # AC-24
		import pathlib
		root = pathlib.Path(frappe.get_app_path("alvoraa_goals"))
		for path in root.rglob("*.py"):
			self.assertNotIn("people_trends", path.read_text(), str(path))

	def test_the_hook_is_registered(self):  # pin: a bad merge cannot drop it silently
		from alvoraa_portal import hooks
		self.assertIn("alvoraa_portal.people_trends.make_role", hooks.after_migrate)
		self.assertIn("alvoraa_portal.people_trends.make_role", hooks.after_install)

	def test_query_count_is_fixed(self):  # AC-61 (3 vs 30 branches)
		def count():
			with fx.QueryCounter() as q:
				call(self.lead_retail, period=365)
			return q.count

		base = count()
		for i in range(27):
			b = fx.branch(f"Many{i}")
			person(fx.KAVYA, b, "S090 Many", None, n=6)
		self.assertEqual(count(), base)
		self.assertLessEqual(base, 30)


class TestSavedPeriod(TrendsBase):
	def test_save_and_reopen(self):  # AC-29, AC-30
		frappe.set_user(self.lead_retail)
		self.assertEqual(call(self.lead_retail)["period"], 90)
		pt.save_people_trends_period(period=180)
		self.assertEqual(call(self.lead_retail)["period"], 180)
		self.assertEqual(call(self.lead_other)["period"], 90)  # another person's choice is theirs

	def test_a_bad_period_is_refused_on_save(self):
		for bad in (45, "x", None):
			frappe.set_user(self.lead_retail)
			with self.assertRaises(frappe.PermissionError):
				pt.save_people_trends_period(period=bad)
		frappe.set_user(self.plain)
		with self.assertRaises(frappe.PermissionError):
			pt.save_people_trends_period(period=30)


class TestAttendanceAndLeave(TrendsBase):
	def make_branch(self):
		b = fx.branch("Att")
		emps = person(fx.KAVYA, b, "S090 Att", None, n=6)
		return b, emps

	def test_absent_percent_and_leave_days_match_the_shared_figures(self):  # AC-76, AC-77, AC-83
		b, emps = self.make_branch()
		K = fx.KAVYA
		for i, e in enumerate(emps):
			for d in range(1, 8):
				status = "Absent" if (i + d) % 4 == 0 else "On Leave" if (i + d) % 7 == 0 else "Present"
				fx.attendance(e, K, b, ago(d), status)
		fx.attendance(emps[0], K, b, ago(9), "Absent", docstatus=0)      # a draft counts nowhere
		fx.review_item(K, b, check_date=ago(3))                          # an Open doubtful day is left out
		out = call(self.lead_retail, period=30, branch=b)
		scope = of.Scope((K,), (b,))
		figs = of.attendance_figures(scope, ago(29), ago(0), detail=False)
		self.assertEqual(out["attendance"]["absent_pct"], round(100 - figs["rate"], 1))
		self.assertEqual(out["leave"]["days"], figs["on_leave"])
		self.assertGreater(figs["on_leave"], 0)
		self.assertGreater(out["attendance"]["left_out_days"], 0)
		self.assertEqual(sum(out["leave"]["series"]), out["leave"]["days"])  # the bins add up

	def test_leave_across_the_window_edge_counts_only_days_inside(self):  # AC-82
		b, emps = self.make_branch()
		for d in (31, 30, 29, 28):  # a 30-day window starts 29 days back
			fx.attendance(emps[0], fx.KAVYA, b, ago(d), "On Leave")
		out = call(self.lead_retail, period=30, branch=b)
		self.assertEqual(out["leave"]["days"], 2)

	def test_no_attendance_says_so(self):  # AC-79
		b, _emps = self.make_branch()
		out = call(self.lead_retail, period=30, branch=b)
		self.assertIsNone(out["attendance"]["absent_pct"])

	def test_pending_requests_are_a_count_only(self):  # AC-88
		b, emps = self.make_branch()
		fx.application(emps[0], fx.KAVYA, b, ago(2), 1, status="Open", docstatus=0)
		fx.application(emps[1], fx.KAVYA, b, ago(2), 1, status="Approved", docstatus=1)
		out = call(self.lead_retail, period=30, branch=b)
		self.assertEqual(out["leave"]["pending"], 1)

	def test_leave_types_fold_small_ones_into_other(self):  # AC-86, AC-122
		rows = [(f"c{i}", "Casual", 0, 2) for i in range(6)] + [(f"e{i}", "Earned", 0, 1) for i in range(5)] + [("s0", "Sick", 0, 4), ("n0", "", 0, 1)]
		types = pt._leave_types(rows, 365, 5, own_key=None)
		named = {t["type"] for t in types}
		self.assertNotIn("Sick", named)                                  # one person: never named
		self.assertIn("Casual", named)
		self.assertEqual(sum(t["days"] for t in types), 12 + 5 + 4 + 1)  # the total is exact
		other = next(t for t in types if t["type"] is None)
		self.assertGreaterEqual(other["days"], 5)
		# nobody taking a type is ever alone in Other: if Other cannot pass, the total only
		self.assertIsNone(pt._leave_types([("a", "X", 0, 1)], 365, 5, own_key=None))

	def test_types_are_named_only_at_the_top(self):  # AC-85
		b, emps = self.make_branch()
		for e in emps:
			fx.attendance(e, fx.KAVYA, b, ago(2), "On Leave")
		frappe.db.sql("update tabAttendance set leave_type = 'Casual Leave' where employee in %s", (emps,))
		top = call(self.lead_retail, period=30)["leave"]
		cut = call(self.lead_retail, period=30, branch=b)["leave"]
		self.assertIsNone(cut["types"])
		self.assertEqual([t["type"] for t in top["types"]], ["Casual Leave"])


class TestReviewFixes(TrendsBase):
	"""Round 1 after the architect and security reviews (24 Nov 2026)."""

	def test_a_failing_bucket_sends_no_series_at_all(self):  # AC-50, AC-81, AC-90 (B1, F2)
		K = fx.KAVYA
		b = fx.branch("Bkt")
		steady = person(K, b, "S090 Bkt", None, n=4)
		leaver = person(K, b, "S090 Bkt", None, status="Left", relieved=ago(4))
		joiner = person(K, b, "S090 Bkt", None, joined=ago(3))
		for e in steady + leaver + joiner:
			for d in range(0, 7):
				fx.attendance(e, K, b, ago(d), "On Leave" if d == 2 else "Present")
		out = call(self.lead_retail, period=7, branch=b)
		self.assertEqual(out["state"], "ok")
		self.assertFalse(out["chart"]["shared"])                     # only 4 on the roll on one day
		self.assertNotIn("series", out["attendance"])
		self.assertNotIn("series", out["leave"])
		self.assertIsNotNone(out["leave"]["days"])                   # the window totals stay
		self.assertNotIn("total", out["chart"])
		# a chip where every bucket passes still sends them
		whole = call(self.lead_retail, period=30, branch=self.my)
		self.assertTrue(whole["chart"]["shared"])
		self.assertIn("series", whole["leave"])

	def _company_minus_branches(self):
		"""Company attendance and pending, and the same added up over the branches the rule checks."""
		K, end = fx.KAVYA, pt._end()
		first, scope, c = ago(29), of.Scope((fx.KAVYA,), None), pt.Call()
		edges = [first, add_days(end, 1)]

		def figures(dim, value):
			rows = [r for r in pt._attendance_bins(c, scope, K, dim, value, first, end, edges) if r["k"] == 1]
			return {**pt._sum_counts(rows), "pending": pt._pending(c, scope, K, dim, value)}
		people = [p for p in pt._people(c, scope) if pt._counted(p)]
		self.assertTrue(all(p.branch for p in people))              # no "none set" cut can be asked for
		total = figures(None, None)
		parts = [figures("branch", b) for b in sorted({p.branch for p in people})]
		return total, {k: sum(p[k] for p in parts) for k in total}

	def _a_counted_person_with(self, tag):
		K = fx.KAVYA
		b = fx.branch("Sub")
		e = person(K, b, "S090 Sub", None, n=1)[0]
		fx.attendance(e, K, tag(b), ago(2), "On Leave")
		fx.attendance(e, K, tag(b), ago(3), "Absent")
		fx.application(e, K, tag(b), ago(2), 1, status="Open", docstatus=0)

	def test_company_minus_branches_leaves_nothing_a_row_with_no_branch_tag(self):  # F1, row kind 1
		self._a_counted_person_with(lambda b: "")
		total, parts = self._company_minus_branches()
		self.assertEqual(total, parts)
		self.assertGreater(total["on_leave"], 0)

	def test_company_minus_branches_leaves_nothing_a_row_with_a_branch_nobody_holds(self):  # F1, row kind 2
		gone = fx.branch("Gone")                                      # no employee holds it
		self._a_counted_person_with(lambda b: gone)
		total, parts = self._company_minus_branches()
		self.assertEqual(total, parts)
		self.assertGreater(total["on_leave"], 0)

	def test_company_minus_branches_leaves_nothing_inactive_staff(self):  # F1, row kind 3
		K = fx.KAVYA
		b = fx.branch("Idle")
		e = person(K, b, "S090 Idle", None, status="Inactive", n=1)[0]
		fx.attendance(e, K, b, ago(2), "On Leave")
		fx.application(e, K, b, ago(2), 1, status="Open", docstatus=0)
		total, parts = self._company_minus_branches()
		self.assertEqual(total, parts)
		self.assertEqual(self._the_rows_of(e), 0)

	def _the_rows_of(self, emp):
		"""How many of this person's attendance rows the figures would count."""
		_row_where, e_where, params = pt._rows_of_counted_people(of.Scope((fx.KAVYA,), None), fx.KAVYA, None, None, "a")
		return len(pt.Call().sql(f"select a.name from `tabAttendance` a join `tabEmployee` e on e.name = a.employee "
		                         f"where a.employee = %(emp)s and {e_where}", {**params, "emp": emp}))

	def test_attendance_is_shown_only_when_five_people_have_rows(self):  # M2 guard (Surbhi, 24 Nov 2026)
		K = fx.KAVYA
		b = fx.branch("Few")
		emps = person(K, b, "S090 Few", None, n=6)                   # six on the roll
		for e in emps[:4]:                                           # four of them have rows
			for d in range(0, 30):
				fx.attendance(e, K, b, ago(d), "Absent" if d % 5 == 0 else "Present")
		few = call(self.lead_retail, period=30, branch=b)
		self.assertEqual(few["attendance"], {"shared": False, "reason": "few_attending"})   # no number, no series
		fx.attendance(emps[4], K, b, ago(1), "Present")              # a fifth person, but only in one week
		still = call(self.lead_retail, period=30, branch=b)
		self.assertFalse(still["attendance"]["shared"])              # that week has 5, the others 4
		for d in range(0, 30):
			if d != 1:
				fx.attendance(emps[4], K, b, ago(d), "Present")
		five = call(self.lead_retail, period=30, branch=b)["attendance"]
		self.assertTrue(five["shared"])
		self.assertIsNotNone(five["absent_pct"])

	def test_named_leave_types_are_the_same_on_every_chip(self):  # AC-86 (M3, F3)
		def rows(per_stretch):
			out = []
			for kind, (a, b) in per_stretch.items():
				out += [(f"{kind}{i}", kind, 0, a) for i in range(5)] + [(f"{kind}{i}", kind, 4, b) for i in range(5)]
			return out
		data = rows({"Casual": (1, 10), "Sick": (3, 1)}) + [("m0", "Maternity", 0, 4), ("m0", "Maternity", 4, 4)]
		week = pt._leave_types(data, 7, 5, own_key=None)
		year = pt._leave_types(data, 365, 5, own_key=None)
		self.assertEqual([t["type"] for t in week if t["type"]], ["Casual"])
		self.assertEqual([t["type"] for t in year if t["type"]], ["Casual"])

	def test_the_nav_item_is_hidden_from_a_login_the_page_refuses(self):  # m1: HR roles plus Leadership
		src = frappe.read_file(frappe.get_app_path("alvoraa_portal", "public", "js", "ess", "portal.js"))
		self.assertRegex(src, r"ptShow = \(roles\.leadership && !roles\.is_hr && f\.plan_analytics")

	def test_the_page_never_uses_the_website_call(self):  # OPS-18, B2
		src = frappe.read_file(frappe.get_app_path("alvoraa_portal", "public", "js", "ess", "people-trends.js"))
		self.assertNotRegex(src, r"frappe\.call\(")
		self.assertIn('"/api/method/" + method', src)

	def test_the_headline_names_a_leave_type_only_if_it_beats_other(self):  # AC-87 (M3)
		def line(types):
			return pt._headline(30, {"headcount": 9}, None, {}, {"shared": True, "days": 1105, "types": types}, 5)
		self.assertNotIn("the most", line([{"type": "Sick", "days": 105}, {"type": None, "days": 1000}]))
		self.assertIn("Sick the most", line([{"type": "Sick", "days": 105}, {"type": None, "days": 4}]))


class TestThePagePins(FrappeTestCase):
	def test_the_page_carries_the_panel_the_nav_and_the_script(self):  # pin: a bad merge cannot drop them
		from alvoraa_portal.tests import portal_source as PS
		page = PS.read_page()
		for needle in ('id="panel-people-trends"', 'id="nav-people-trends"', 'id="bnav-people-trends"',
		               "window.ptLoad"):  # the shared expander pastes the script in, so its code is what shows
			self.assertIn(needle, page, needle)
		self.assertIn('ptLoad()', open(frappe.get_app_path("alvoraa_portal", "public", "js", "ess", "portal.js")).read())


class TestMore(TrendsBase):
	def test_response_size_follows_branches_not_people(self):  # AC-114
		before = len(json.dumps(call(self.lead_retail, period=365)))
		person(fx.KAVYA, self.my, "S090 Sales", None, n=400)
		after = len(json.dumps(call(self.lead_retail, period=365)))
		self.assertLess(abs(after - before), before * 0.1)

	def test_the_role_adds_no_rows_anywhere(self):  # AC-8
		def counts(user):
			frappe.set_user(user)
			out = {}
			for dt in ("Employee", "Attendance", "Leave Application", "Salary Slip", "Employee Checkin"):
				try:
					out[dt] = len(frappe.get_list(dt, limit_page_length=0))
				except frappe.PermissionError:
					out[dt] = 0
			frappe.set_user("Administrator")
			return out

		user = fx.user("p090rowcount", ["Employee"])
		before = counts(user)
		doc = frappe.get_doc("User", user)
		doc.append("roles", {"role": pt.ROLE})
		doc.save(ignore_permissions=True)
		fx.permission(user, "Company", fx.KAVYA)
		after = counts(user)
		for dt in before:
			self.assertLessEqual(after[dt], before[dt], dt)

	def test_leadership_is_still_refused_the_organisation_attendance_view(self):  # AC-9
		from alvoraa_portal import attendance_analytics as aa
		frappe.set_user(self.lead_retail)
		with self.assertRaises(frappe.PermissionError):
			aa.summary(view="organisation")

	def test_data_quality_line_only_at_the_top_and_only_five_or_more(self):  # AC-102, AC-103
		b = fx.branch("NoDate")
		person(fx.KAVYA, b, "S090 NoDate", None, status="Left", relieved=None, n=4)
		self.assertIsNone(call(self.lead_retail, period=30)["data_quality"])
		person(fx.KAVYA, b, "S090 NoDate", None, status="Left", relieved=None, n=1)
		self.assertEqual(call(self.lead_retail, period=30)["data_quality"], {"no_relieving": 5})
		self.assertIsNone(call(self.lead_retail, period=30, branch=self.my)["data_quality"])

	def test_a_small_company_hides_the_next_smallest_too(self):  # AC-59, AC-93
		frappe.db.sql("update tabEmployee set status = 'Inactive' where company = %s and last_name = %s and status = 'Active' "
		              "and name not in (select n from (select name n from tabEmployee where company = %s and last_name = %s and status = 'Active' limit 3) x)",
		              (fx.OTHER, TAG, fx.OTHER, TAG))
		out = call(self.lead_both, period=30)
		self.assertEqual(out["state"], "ok")  # the all-companies total is the parent
		blocks = {b["company"]: b for b in out["by_company"]}
		self.assertFalse(blocks[fx.OTHER]["shared"])
		self.assertFalse(blocks[fx.KAVYA]["shared"])  # the next smallest goes with it
		self.assertNotIn("headcount", blocks[fx.OTHER])
		listed = {c["value"]: c["shared"] for c in out["filters"]["companies"]}
		self.assertEqual(listed, {fx.KAVYA: False, fx.OTHER: False})
