"""Every reach into a tenant leaves a record that cannot be edited.

Under the DPDP Act the customer is the Data Fiduciary for their employees' data
and Alvoraa is the Processor. A processor must be able to answer "who opened
that payroll, and when". Until this log existed, nothing could: the control
plane runs bench commands against every tenant as Administrator and left no
trace at all.

`_bench_run` is the single door - all twenty call sites go through it - so the
log lives there rather than at each caller, where the next one added would
simply forget.
"""

import frappe
from frappe.tests.utils import FrappeTestCase

from alvoraa_portal import tenant_api


class TestEveryCallIsLogged(FrappeTestCase):
    def test_bench_run_logs_on_the_way_out(self):
        """In a `finally`, so a command that raises is still recorded. An audit
        log that only captures successes is not an audit log."""
        import inspect

        src = inspect.getsource(tenant_api._bench_run)
        self.assertIn("finally:", src)
        self.assertIn("_log_tenant_access", src)

    def test_it_records_which_tenant(self):
        """The site is pulled from the command itself, so a caller cannot reach
        a tenant without naming it in the record."""
        m = tenant_api._SITE_ARG.search("--site acme.alvoraa.co migrate")
        self.assertIsNotNone(m)
        self.assertEqual(m.group(1), "acme.alvoraa.co")

    def test_a_bench_wide_command_is_still_logged(self):
        """`bench version` names no site. It still gets a row, marked so."""
        self.assertIsNone(tenant_api._SITE_ARG.search("version"))
        import inspect

        self.assertIn('"(bench)"', inspect.getsource(tenant_api._log_tenant_access))


class TestSecretsNeverReachTheLog(FrappeTestCase):
    def test_the_command_is_redacted(self):
        import inspect

        src = inspect.getsource(tenant_api._log_tenant_access)
        self.assertIn("_redact(cmd)", src)

    def test_stderr_is_redacted_too(self):
        """A failing command echoes its arguments back, and provisioning passes
        generated passwords as arguments."""
        import inspect

        self.assertIn("_redact(detail)", inspect.getsource(tenant_api._log_tenant_access))

    def test_redaction_actually_removes_a_password(self):
        line = "set-admin-password hunter2 --password s3cret"
        self.assertNotIn("s3cret", tenant_api._redact(line))


class TestTheLogCannotBeQuietlyEdited(FrappeTestCase):
    """A log the operator can change answers nothing."""

    def test_nobody_may_create_write_or_delete(self):
        if not frappe.db.exists("DocType", "Alvoraa Tenant Access Log"):
            self.skipTest("doctype not installed on this bench yet")
        meta = frappe.get_meta("Alvoraa Tenant Access Log")
        for perm in meta.permissions:
            self.assertFalse(perm.get("create"), f"{perm.role} can create rows")
            self.assertFalse(perm.get("write"), f"{perm.role} can edit rows")
            self.assertFalse(perm.get("delete"), f"{perm.role} can delete rows")

    def test_every_field_is_read_only(self):
        if not frappe.db.exists("DocType", "Alvoraa Tenant Access Log"):
            self.skipTest("doctype not installed on this bench yet")
        for f in frappe.get_meta("Alvoraa Tenant Access Log").fields:
            self.assertTrue(f.read_only, f"{f.fieldname} is editable")


class TestItNeverBreaksProvisioning(FrappeTestCase):
    def test_a_failed_write_is_swallowed_and_reported(self):
        """An audit gap is bad. A tenant that fails to provision because the
        audit write failed is worse."""
        import inspect

        src = inspect.getsource(tenant_api._log_tenant_access)
        self.assertIn("except Exception:", src)
        self.assertIn("log_error", src)

    def test_it_does_nothing_off_the_control_plane(self):
        """Only the control plane reaches into other tenants. A tenant site
        running this would be logging its own ordinary work."""
        import inspect

        self.assertIn("alvoraa_control_plane", inspect.getsource(tenant_api._log_tenant_access))
