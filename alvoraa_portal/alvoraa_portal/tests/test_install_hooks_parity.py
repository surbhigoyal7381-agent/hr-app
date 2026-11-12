"""ALV-312 / ALV-292: a job that must run on a NEW tenant, and only migrates.

**Why this file exists.** A tenant is built with `bench install-app`, which
never runs `bench migrate`. So a job listed only under `after_migrate` runs on
every site that already exists and on no site made after it was written. The
failure is silent: nothing errors, the tenant simply starts life without a
column, a role or a default, and nobody finds out until somebody uses the
feature months later.

It has happened twice, a day apart, and no test caught either one:

* **ALV-292** - `joiner_invite.make_role` was migrate-only, so a new tenant had
  no Alvoraa Joiner role and every joiner invite refused.
* **ALV-312** - `expense_evidence.after_migrate` was migrate-only, so a new
  tenant had no legal-hold field at all, and took the bill-rule cut-off date
  from whatever release came next instead of from its own install date. All
  five live tenants read 2026-11-05, the release date. Harmless there by luck -
  a later cut-off exempts claims rather than blocking them - but luck is not a
  control.

**The rule, stated the safe way round.** Every `after_migrate` entry is also an
`after_install` entry, unless it is listed in `MIGRATE_ONLY` below with its
reason. Being in both lists is the default and costs nothing, because every one
of these jobs is safe to run twice. A new exception is then a deliberate act
with a sentence attached, rather than an omission nobody sees.

The exceptions are checked too, not merely accepted: an entry excused because
something else covers a new tenant must name that cover, and this file fails if
the cover has gone. An excuse that quietly stopped being true is the same bug
wearing a comment.

**Not here, on purpose:** whether each hook string names a function that exists.
`scripts/check_app_integrity.py` already walks every string in hooks.py and
fails CI on a name that does not resolve. This file is only about which LIST a
job is in, and in what order.
"""

from frappe.tests.utils import FrappeTestCase

from alvoraa_portal import hooks

# Jobs that are deliberately NOT in `after_install`.
#
# value = (what covers a new tenant instead, or None, the reason)
#
# A "cover" is another hook path, which must itself be present in
# `after_install` or `after_app_install`. Pass None only when a new tenant
# genuinely needs nothing, and say why.
MIGRATE_ONLY = {
	"alvoraa_portal.data_review.after_migrate": (
		"alvoraa_portal.data_review.after_install",
		"A new site has no attendance to check, so install runs the indexes "
		"only. Its own function, deliberately - see data_review.after_install.",
	),
	"alvoraa_portal.lms_defaults.after_migrate": (
		None,
		"LMS is not on the site yet when alvoraa_portal installs, so this "
		"would be a no-op at that moment. provision_tenant.sh calls "
		"lms_defaults.apply_safe_defaults straight after `install-app lms`, "
		"and tenant_api does the same for a tenant that ticks the feature "
		"later.",
	),
	"alvoraa_portal.helpdesk_defaults.after_migrate": (
		None,
		"Same as lms_defaults above: Helpdesk is not on the site yet, and "
		"provision_tenant.sh applies the defaults right after installing it.",
	),
	"alvoraa_portal.crm_steps.ensure_task_label_field": (
		"alvoraa_portal.crm_steps.on_app_install",
		"A no-op without CRM, which is not installed yet at this point. The "
		"after_app_install hook puts the column on as CRM arrives, whenever "
		"that turns out to be.",
	),
}

# Documented ordering inside each list. (earlier, later, why)
#
# hooks.py states these as comments today, and nothing enforces them.
# Reordering a list is a one-line edit that breaks them in silence.
MUST_RUN_BEFORE = [
	(
		"alvoraa_portal.branch_scope.after_migrate",
		"alvoraa_portal.data_review.after_migrate",
		"two of the indexes are on branch_scope's column",
	),
	(
		"alvoraa_portal.branch_scope.after_migrate",
		"alvoraa_portal.expense_evidence.after_migrate",
		"both touch Expense Claim and Attendance Request, and branch_scope is "
		"what creates alvoraa_branch on them",
	),
	(
		"alvoraa_portal.alternative_number.after_migrate",
		"alvoraa_portal.employee_field_rights.apply",
		"the field has to exist before field rights are applied to it",
	),
]


class TestEveryMigrateJobReachesANewTenant(FrappeTestCase):
	def test_after_migrate_entries_are_in_after_install(self):
		"""The rule itself. Add a job to `after_migrate` alone and this fails,
		with the sentence its author needs to read."""
		missing = [e for e in hooks.after_migrate
		           if e not in hooks.after_install and e not in MIGRATE_ONLY]
		self.assertEqual(
			missing, [],
			"These jobs run on every migrate and on no new tenant, because "
			"`bench install-app` never migrates: %s. Add each one to "
			"`after_install` in hooks.py - they are all safe to run twice - "
			"or, if a new tenant really needs nothing, add it to MIGRATE_ONLY "
			"in this file with the reason. ALV-312 and ALV-292 were both this "
			"bug." % ", ".join(missing))

	def test_every_excuse_is_still_true(self):
		"""An exception that names a cover must still have one. ALV-312's own
		excuse was a comment, and the comment outlived what it described."""
		covers = set(hooks.after_install) | set(getattr(hooks, "after_app_install", []))
		for path, (cover, reason) in MIGRATE_ONLY.items():
			self.assertTrue(reason and reason.strip(),
			                "%s is excused with no reason given" % path)
			if cover is None:
				continue
			self.assertIn(
				cover, covers,
				"%s is excused from after_install because %s covers a new "
				"tenant instead - and %s is no longer in after_install or "
				"after_app_install, so nothing covers it now."
				% (path, cover, cover))

	def test_no_excuse_outlives_its_job(self):
		"""A stale key here would excuse a job that no longer exists, and hide
		a later one that happens to be given the same name."""
		live = set(hooks.after_migrate)
		stale = sorted(k for k in MIGRATE_ONLY if k not in live)
		self.assertEqual(
			stale, [],
			"MIGRATE_ONLY excuses jobs that are not in after_migrate any "
			"more: %s. Remove them." % ", ".join(stale))


class TestTheDocumentedOrderIsKept(FrappeTestCase):
	def test_jobs_that_depend_on_another_run_after_it(self):
		"""hooks.py says "must stay AFTER" in three places. Nothing enforced
		it, and reordering a list is a one-line edit."""
		for list_name in ("after_migrate", "after_install"):
			entries = getattr(hooks, list_name, [])
			for earlier, later, why in MUST_RUN_BEFORE:
				if earlier not in entries or later not in entries:
					continue
				self.assertLess(
					entries.index(earlier), entries.index(later),
					"%s must run before %s in `%s` - %s - and it does not."
					% (earlier, later, list_name, why))
