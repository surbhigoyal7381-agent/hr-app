"""Slice 090 · PRIV-13, AC-62: the group rule holds over generated tenants.

For many random tenants (branches, departments, types, blanks; joining and leaving
dates over two years), every figure that can be got by SUBTRACTION from what the page
sends must come from a group that passes: the siblings hidden along a dimension, taken
together, are 0 people or at least the minimum, in every one of the nine stretches,
and every group that is shown passes in every stretch.

It must fail when part C's "together they pass" check is removed. `Mutant` is that
removal, and the last test asserts the property catches it (break-test, built in).
"""

import random

from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, getdate

from alvoraa_portal import people_trends as pt

END = getdate("2026-11-22")
DIMS = ("branch", "department", "employment_type")


def tenant(rng):
	people = []
	for company in rng.sample(["Ka", "Kb", "Kc"], rng.randint(1, 3)):
		branches = [None] + [f"B{i}" for i in range(rng.randint(1, 6))]
		for branch in branches:
			for dept in (None, "Sales", "Stores", "Sec")[: rng.randint(1, 4)]:
				for etype in (None, "Contract"):
					for _ in range(rng.choice([0, 0, 1, 2, 3, 4, 5, 6, 9, 14])):
						joined = add_days(END, -rng.randint(0, 700))
						left = rng.random() < 0.3
						relieved = add_days(joined, rng.randint(1, 400)) if left else None
						if relieved and relieved > END:
							left, relieved = False, None
						people.append(pt.Person(company, branch, dept, etype, "Left" if left else "Active", joined, relieved, 1))
	return people


class Mutant(pt.Rule):
	"""Part C with the "together they pass" check taken out: only the siblings that fail alone are hidden."""

	def hidden(self, dim, company=None):
		saved = pt.Rule.passes
		try:
			# a hidden group that fails on its own stays hidden; the "add the next smallest" loop never runs
			values = sorted({getattr(u, dim) if dim != "company" else u.company for u in self.units
			                 if dim == "company" or u.company == company}, key=str)
			make = (lambda v: pt._matcher(company=v)) if dim == "company" else (lambda v: pt._matcher(company, dim, v))
			return {v: r for v in values if (r := self.self_reason(make(v)))}
		finally:
			pt.Rule.passes = saved


def violations(rule_cls, seeds, minimum):
	bad = []
	for seed in seeds:
		rng = random.Random(seed)
		people = pt._counted_list(tenant(rng)) if hasattr(pt, "_counted_list") else [p for p in tenant(rng) if pt._counted(p)]
		units = pt._people_units(people, END)
		sizes = pt._sizes(people, END, ())
		rule = rule_cls(units, len(pt.STRETCHES), minimum, sizes)
		companies = sorted({p.company for p in people})
		scopes = [("company", None)] + [(d, c) for c in companies for d in DIMS]
		for dim, company in scopes:
			hidden = rule.hidden(dim, company)
			if dim == "company":
				values = {u.company for u in units}
				make = lambda v: pt._matcher(company=v)  # noqa: E731
			else:
				values = {getattr(u, dim) for u in units if u.company == company}
				make = lambda v: pt._matcher(company, dim, v)  # noqa: E731
			for v in values - set(hidden):
				if not rule.passes(make(v)):
					bad.append((seed, "shown group fails", dim, v))
			# The parent is what a leader could subtract from. If the parent itself is not
			# shown (it fails), there is nothing to subtract from, so only a passing parent counts.
			parent = (lambda u: True) if dim == "company" else pt._matcher(company)
			if hidden and rule.passes(parent):
				union = lambda u: any(make(v)(u) for v in hidden)  # noqa: E731
				if not rule.passes(union):
					bad.append((seed, "hidden siblings do not pass together", dim, sorted(map(str, hidden))))
	return bad


class TestTheRuleOverGeneratedTenants(FrappeTestCase):
	SEEDS = range(300)

	def test_the_real_rule_holds_at_every_minimum(self):
		for minimum in (3, 5, 10):
			self.assertEqual(violations(pt.Rule, self.SEEDS, minimum)[:3], [], f"minimum {minimum}")

	def test_the_property_catches_part_c_removed(self):  # the break test
		self.assertTrue(violations(Mutant, self.SEEDS, 5), "the property did not notice part C was gone")
