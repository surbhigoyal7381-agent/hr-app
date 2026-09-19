"""Slice 021 — a tenant must never end up denied with no way back.

The fault these tests pin, in one paragraph. `sync_permissions()` used to write
the denial rows FIRST and record what it had done LAST. The record is a Single,
`Alvoraa Access State`, and saving it can fail. When it did, the rows were
already written, nothing said they existed, `sync_site` swallowed the error, and
`apply_to_users()` COMMITTED. The rows were then committed and unrecorded, and
`release_permissions()` can never remove them, because by design it releases only
what we recorded. The customer's modules were dark with no supported way back.

Every test here is bounded to a handful of doctypes on purpose. Restricting the
450 a Starter tenant blocks takes minutes and would leave a shared bench in a
state no other suite expects.

Every test restores what it changed, registered with addCleanup BEFORE the write
so it runs even when the test body raises - the lesson slice 020 paid for.
"""

import frappe
from frappe.tests.utils import FrappeTestCase

from alvoraa_portal import module_access as ma
from alvoraa_portal import subscription as sub

# Payroll doctypes, because every plan below Enterprise blocks them and they are
# not touched by any other suite's fixtures.
WATCH = ["Salary Slip", "Salary Structure", "Payroll Entry"]


class _StateRestored(FrappeTestCase):
    """Put the access state and the watched doctypes back, whatever happens."""

    def setUp(self):
        self.feats = sub.plan_features("starter")
        self._recorded = ma._recorded_restrictions()
        self._snapshot = ma._load("permission_snapshot")
        self._rows = {dt: ma._snapshot_existing(dt) for dt in WATCH}
        # A tenant's honest baseline is NOT zero. hrms/setup.py and the Employee
        # Self Service User Type write rows at install - on a freshly built site
        # these three doctypes carry nine of them between them. The invariant is
        # "the count comes back to where it started", never "the count is zero".
        self._baseline = self.rows_on()
        self.addCleanup(self._restore)

    def _restore(self):
        # Give back anything these tests recorded, through the supported route,
        # before putting the rows back by hand. Bounded to the watched doctypes:
        # a bare release_permissions() would hand back a restriction this site
        # legitimately holds for somebody else, and never put it back.
        ma.release_permissions(WATCH)
        for dt, rows in self._rows.items():
            frappe.db.delete("Custom DocPerm", {"parent": dt})
            if rows:
                ma._restore_snapshot(dt, rows)
        ma._save(restricted=self._recorded, snapshot=self._snapshot)
        frappe.db.commit()
        frappe.clear_cache()

    def rows_on(self, doctypes=WATCH):
        return frappe.db.count("Custom DocPerm", {"parent": ["in", list(doctypes)]})


class TestTheRecordComesBeforeTheRows(_StateRestored):
    def test_a_failing_save_leaves_nothing_denied(self):
        """The whole bug, and the proof that it is gone.

        With _save broken, the old order wrote three denial rows that nothing
        recorded. The new order cannot: the record is attempted first, so the
        failure happens before a single row is touched.
        """
        broken = _break_save()
        self.addCleanup(broken.restore)

        with self.assertRaises(RuntimeError):
            ma.sync_permissions(self.feats, only=WATCH)

        # And now the step that made it permanent. sync_site used to swallow the
        # error and carry on to apply_to_users(), which COMMITS - so anything
        # already written became a fact. A rollback here would hide the very
        # thing this test exists to catch.
        frappe.db.commit()
        broken.restore()

        self.assertEqual(self.rows_on(), self._baseline,
                         "a failed record must leave the permission rows exactly "
                         "where it found them, even when something commits "
                         "straight afterwards")
        self.assertEqual(ma._recorded_restrictions() & set(WATCH), set())

    def test_the_record_is_written_before_the_first_row(self):
        """Order, watched as it happens rather than inferred afterwards."""
        seen = []
        real_save = ma._save
        real_keep = ma._keep_exempt_row

        def spy_save(restricted=None, snapshot=None):
            seen.append(("record", sorted((restricted or set()) & set(WATCH))))
            return real_save(restricted=restricted, snapshot=snapshot)

        def spy_keep(doctype, exempt):
            seen.append(("row", doctype))
            return real_keep(doctype, exempt)

        ma._save, ma._keep_exempt_row = spy_save, spy_keep
        self.addCleanup(lambda: setattr_many(ma, _save=real_save, _keep_exempt_row=real_keep))
        try:
            ma.sync_permissions(self.feats, only=WATCH)
        finally:
            ma._save, ma._keep_exempt_row = real_save, real_keep

        kinds = [s[0] for s in seen]
        self.assertIn("record", kinds)
        self.assertIn("row", kinds)
        self.assertLess(kinds.index("record"), kinds.index("row"),
                        f"the record must be written first; saw {seen}")
        # And it must already name every doctype the run is about to take.
        self.assertEqual(seen[kinds.index("record")][1], sorted(WATCH))

    def test_release_can_still_undo_a_successful_run(self):
        """Record-first must not break the reversal it exists to protect."""
        ma.sync_permissions(self.feats, only=WATCH)
        self.assertEqual(self.rows_on(), len(WATCH))
        self.assertTrue(set(WATCH) <= ma._recorded_restrictions())

        out = ma.release_permissions(WATCH)
        self.assertEqual(sorted(out["released"]), sorted(WATCH))
        self.assertEqual(self.rows_on(), self._baseline,
                         "the snapshot must put the tenant's own rows back")
        self.assertEqual(ma._recorded_restrictions() & set(WATCH), set())


class TestTheStateSaveTakesALock(_StateRestored):
    """Why a plain re-read was not enough.

    MariaDB runs at REPEATABLE READ. Once this transaction has read anything it
    holds a snapshot, and Frappe's two reads of the record then disagree by
    construction:

        reload()          -> plain SELECT      -> the snapshot (stale)
        check_if_latest() -> SELECT FOR UPDATE -> the latest committed row

    So a plain reload made TimestampMismatchError certain, not unlucky, whenever
    a second connection wrote the record while we worked. Proved on test_site
    with two processes: the plain reload returned a 35-second-old timestamp and
    the save raised every time.

    The fix is to read with the lock, so we read the row the guard will compare
    against and hold it until commit.
    """

    def test_the_reread_is_a_locking_read(self):
        """Counted, not merely observed.

        Frappe's own check_if_latest() already does ONE locking read of the
        record on every save, so "a locking read happened" proves nothing. What
        the fix adds is a SECOND one - our own re-read before the save. One
        locking read means the old, stale, plain reload; two means the fix.
        """
        real = frappe.db.get_singles_dict
        calls = []

        def spy(doctype, *args, for_update=False, **kwargs):
            calls.append((doctype, for_update))
            return real(doctype, *args, for_update=for_update, **kwargs)

        frappe.db.get_singles_dict = spy
        try:
            ma._save(restricted=self._recorded)
        finally:
            frappe.db.get_singles_dict = real

        locking = [c for c in calls
                   if c[0] == ma.STATE_DOCTYPE and c[1]]
        self.assertGreaterEqual(
            len(locking), 2,
            "our own re-read of the state record must take the lock too, or it "
            f"reads a stale snapshot; locking reads seen: {len(locking)} of {calls}")

    def test_two_saves_in_a_row_still_both_land(self):
        """The lock must not break the ordinary path."""
        ma._save(restricted={"Leave Type"})
        ma._save(restricted={"Leave Type", "Holiday List"})
        frappe.db.commit()
        self.assertEqual(ma._recorded_restrictions(), {"Leave Type", "Holiday List"})


class TestTheFailureIsVisible(_StateRestored):
    """Silence is what let half-done denials reach a commit.

    sync_site's other steps - the two Module Profiles, the workspaces, the
    sidebars, the navbar - each COMMIT, and this suite has no business changing
    any of them on a shared bench. So they are stubbed out and only the one
    question under test is left standing: when the permission sync fails, does
    the caller find out?

    apply_to_users is stubbed too, and watched: it is the call that used to
    commit the stranded rows, and it must never run after a failure.
    """

    def setUp(self):
        # The base registers its restore FIRST, so it runs last and puts the
        # site back whatever these stubs do.
        super().setUp()
        self.applied = []
        self._real = {n: getattr(ma, n) for n in
                      ("sync_module_profile", "sync_workspaces", "sync_module_sidebars",
                       "sync_navbar_item", "apply_to_users", "get_hidden_workspaces",
                       "sync_permissions")}
        self.addCleanup(self._put_back)
        ma.sync_module_profile = lambda *a, **k: None
        ma.sync_workspaces = lambda *a, **k: {"hidden": [], "shown": []}
        ma.sync_module_sidebars = lambda *a, **k: {"silenced": [], "restored": []}
        ma.sync_navbar_item = lambda *a, **k: None
        ma.get_hidden_workspaces = lambda *a, **k: {"hidden": [], "visible": []}
        ma.apply_to_users = lambda *a, **k: (self.applied.append(1),
                                             {"applied": 0, "admins_exempt": 0})[1]

        def boom(*a, **k):
            raise RuntimeError("forced: the permission sync failed")

        ma.sync_permissions = boom

    def _put_back(self):
        for name, fn in self._real.items():
            setattr(ma, name, fn)

    def test_sync_site_no_longer_swallows_a_permission_failure(self):
        with self.assertRaises(RuntimeError):
            ma.sync_site(sub.plan_features("starter"))

    def test_nothing_commits_behind_the_failure(self):
        """apply_to_users() is the commit that made a half-done denial permanent."""
        with self.assertRaises(RuntimeError):
            ma.sync_site(sub.plan_features("starter"))
        self.assertEqual(self.applied, [],
                         "apply_to_users must not run after a failed permission sync")

    def test_the_failure_is_logged_with_a_title_support_can_find(self):
        logged = []
        real_log = frappe.log_error
        frappe.log_error = lambda **kw: logged.append(kw.get("title", "")) or None
        try:
            with self.assertRaises(RuntimeError):
                ma.sync_site(sub.plan_features("starter"))
        finally:
            frappe.log_error = real_log

        self.assertTrue(
            any("permission sync failed" in t for t in logged),
            f"support needs a findable title; logged {logged}")


class TestTheReportIsReadOnly(_StateRestored):
    """Support must be able to ask the question without holding the knife.

    `find_unrecorded_restrictions` is the check an operator runs against a live
    tenant - including production - when a plan change may have stranded rows.
    It has to be safe there, which means it writes nothing at all.
    """

    def _strand(self):
        exempt = ma._exempt_roles()
        for dt in WATCH:
            frappe.db.delete("Custom DocPerm", {"parent": dt})
            ma._keep_exempt_row(dt, exempt)
        ma._save(restricted=self._recorded - set(WATCH),
                 snapshot={k: v for k, v in self._snapshot.items() if k not in WATCH})
        frappe.db.commit()

    def test_it_finds_a_stranded_doctype(self):
        self._strand()
        found = ma.find_unrecorded_restrictions(self.feats, doctypes=WATCH)
        self.assertEqual(sorted(s["doctype"] for s in found["stranded"]), sorted(WATCH))
        for s in found["stranded"]:
            self.assertIsNotNone(s["first_seen"], "support needs a date to judge by")

    def test_it_does_not_call_an_install_time_row_stranded(self):
        """The rows hrms/setup.py and the ESS User Type write are not ours.

        Every one of them names a role we do not exempt - HR Manager, HR User,
        Employee, Employee Self Service - and one such role anywhere in a
        doctype's rows is enough to leave it alone. Proved here with the two
        shapes those two sources actually produce.
        """
        self._strand()
        for dt, role in ((WATCH[0], "HR Manager"), (WATCH[1], "Employee Self Service")):
            doc = frappe.get_doc({"doctype": "Custom DocPerm", "parent": dt,
                                  "parenttype": "DocType", "parentfield": "permissions",
                                  "role": role, "permlevel": 0, "read": 1})
            doc.name = frappe.generate_hash(length=10)
            doc.db_insert()
        frappe.db.commit()

        found = ma.find_unrecorded_restrictions(self.feats, doctypes=WATCH)
        self.assertEqual([s["doctype"] for s in found["stranded"]], [WATCH[2]])
        self.assertEqual(sorted(s["doctype"] for s in found["legitimate"]),
                         sorted(WATCH[:2]))

    def test_it_writes_nothing(self):
        """No INSERT, no UPDATE, no DELETE, no commit. On any tenant."""
        self._strand()
        rows_before = frappe.db.count("Custom DocPerm")
        state_before = frappe.db.get_value(ma.STATE_DOCTYPE, ma.STATE_DOCTYPE, "modified")

        writes, commits = [], []
        real_sql, real_commit = frappe.db.sql, frappe.db.commit

        def spy_sql(query, *a, **kw):
            head = str(query).strip().split(None, 1)[0].upper() if str(query).strip() else ""
            if head in ("INSERT", "UPDATE", "DELETE", "REPLACE", "TRUNCATE", "ALTER", "DROP"):
                writes.append(str(query)[:120])
            return real_sql(query, *a, **kw)

        frappe.db.sql = spy_sql
        frappe.db.commit = lambda *a, **kw: commits.append(1)
        try:
            ma.find_unrecorded_restrictions(self.feats)
        finally:
            frappe.db.sql, frappe.db.commit = real_sql, real_commit

        self.assertEqual(writes, [], f"the report must not write; it ran {writes}")
        self.assertEqual(commits, [], "the report must not commit")
        self.assertEqual(frappe.db.count("Custom DocPerm"), rows_before)
        self.assertEqual(
            frappe.db.get_value(ma.STATE_DOCTYPE, ma.STATE_DOCTYPE, "modified"),
            state_before, "the state record must not move")

    def test_it_scans_the_whole_site_by_default(self):
        """A strand left by a plan the tenant has moved off sits OUTSIDE the
        current plan's blocked list, and is exactly what support is looking for."""
        self._strand()
        found = ma.find_unrecorded_restrictions(sub.plan_features("enterprise"))
        names = {s["doctype"] for s in found["stranded"]}
        self.assertTrue(set(WATCH) <= names,
                        "the default scan must not be limited to the current plan")
        # ...and every entry says whether it is in the current plan, so the
        # operator can see at a glance which plan left it behind.
        for s in found["stranded"]:
            self.assertIn(s["in_current_plan"], (True, False))


class TestTheRepairTouchesOnlyWhatIsOurs(_StateRestored):
    def _strand(self):
        """Put the watched doctypes into the exact stranded state, by hand."""
        exempt = ma._exempt_roles()
        for dt in WATCH:
            frappe.db.delete("Custom DocPerm", {"parent": dt})
            ma._keep_exempt_row(dt, exempt)
        # and record NOTHING about them, which is the whole point. Only the
        # watched doctypes are taken out of the record - whatever else this site
        # legitimately has recorded is left exactly as it is.
        ma._save(restricted=self._recorded - set(WATCH),
                 snapshot={k: v for k, v in self._snapshot.items() if k not in WATCH})
        frappe.db.commit()

    def test_it_finds_rows_that_nothing_records(self):
        self._strand()
        found = ma.find_unrecorded_restrictions(self.feats, doctypes=WATCH)
        self.assertEqual(sorted(s["doctype"] for s in found["stranded"]), sorted(WATCH))
        self.assertEqual(found["suspect"], [])

    def test_it_releases_exactly_those(self):
        self._strand()
        out = ma.repair_unrecorded_restrictions(self.feats, doctypes=WATCH, apply=1)
        self.assertTrue(out["applied"])
        self.assertEqual(sorted(out["released"]), sorted(WATCH))
        self.assertEqual(self.rows_on(), 0)

    def test_a_dry_run_changes_nothing(self):
        self._strand()
        out = ma.repair_unrecorded_restrictions(self.feats, doctypes=WATCH)
        self.assertFalse(out["applied"])
        self.assertEqual(len(out["stranded"]), len(WATCH))
        self.assertEqual(self.rows_on(), len(WATCH))

    def test_it_leaves_a_tenants_own_rows_alone(self):
        """The line that stops this becoming the blanket delete that hurt us.

        ppj.localhost carries 625 legitimate rows across 351 doctypes. A row
        naming a role we do not exempt is somebody else's configuration, and the
        repair must report it and walk past.
        """
        self._strand()
        # A customer's own row on one of them - an HR Manager who is meant to
        # keep read access.
        doc = frappe.get_doc({"doctype": "Custom DocPerm", "parent": WATCH[0],
                              "parenttype": "DocType", "parentfield": "permissions",
                              "role": "HR Manager", "permlevel": 0, "read": 1})
        doc.name = frappe.generate_hash(length=10)
        doc.db_insert()
        frappe.db.commit()

        out = ma.repair_unrecorded_restrictions(self.feats, doctypes=WATCH, apply=1)
        self.assertNotIn(WATCH[0], out["released"])
        self.assertEqual([s["doctype"] for s in out["suspect"]], [WATCH[0]])
        self.assertEqual(sorted(out["released"]), sorted(WATCH[1:]))
        self.assertTrue(
            frappe.db.exists("Custom DocPerm", {"parent": WATCH[0], "role": "HR Manager"}),
            "the tenant's own row must still be there")

    def test_it_will_not_touch_a_doctype_we_did_record(self):
        """Recorded restrictions belong to release_permissions, not to this."""
        ma.sync_permissions(self.feats, only=WATCH)
        out = ma.repair_unrecorded_restrictions(self.feats, doctypes=WATCH, apply=1)
        self.assertEqual(out["released"], [])
        self.assertEqual(self.rows_on(), len(WATCH))


def setattr_many(obj, **kw):
    for k, v in kw.items():
        setattr(obj, k, v)


class _break_save:
    """Make the state record refuse to be written, the way the real fault did.

    A plain exception, not a forged TimestampMismatchError: what matters is that
    the record cannot be made, not which way it failed.
    """

    def __init__(self):
        self.real = ma._save
        ma._save = self._boom
        self.restored = False

    def _boom(self, restricted=None, snapshot=None):
        raise RuntimeError("forced: the state record could not be written")

    def restore(self):
        if not self.restored:
            ma._save = self.real
            self.restored = True
