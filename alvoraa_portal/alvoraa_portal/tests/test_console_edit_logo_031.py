"""Slice 031 - a tenant's logo can be changed after the tenant is created.

Slice 029 made `update_tenant` able to take a logo and copy it to the tenant
site. Nothing called it: the admin console's Edit Tenant dialog had no logo
field at all. This slice adds that field, adds `remove_logo` so a logo can be
taken away, and pins what each action writes:

- an edit that does not mention the logo writes nothing (029's no-op, kept)
- a new logo is copied to the tenant FIRST, then the path is stored
- removal stores an EMPTY value, never a path to a file that is not there
- a file that is not a picture we can draw is refused, on the server as well
  as in the browser
- the endpoint is control-plane only, so an HR Manager on a tenant cannot
  change any tenant's logo

These tests need NO database and NO site, the same shape as
`test_tenant_logo_029.py`: a temporary sites folder, `_bench_run` replaced, and
plain `unittest.TestCase`.

    env/bin/python -m unittest alvoraa_portal.tests.test_console_edit_logo_031
"""

import os
import re
import tempfile
import unittest
from unittest.mock import patch

import frappe

from alvoraa_portal import tenant_api as api

CONTROL = "control.test"
TENANT = "acme.test"
LOGO = "AcmeNew.png"

ADMIN_PAGE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                          "www", "alvoraa-admin.html")


def _throw_without_a_site(case):
	"""Let `frappe.throw` raise, without dragging in a site.

	The real `frappe.throw` translates its message, and translation opens a log
	file under a site that does not exist here - so outside a request it dies
	with FileNotFoundError instead of the error the code asked for, and
	`assertRaises(Exception)` would then pass for the wrong reason. This
	stand-in does the one thing the tests care about: raise the exception class
	the caller named, with the caller's message.
	"""

	def _throw(msg, exc=frappe.ValidationError, *args, **kwargs):
		raise exc(msg)

	patcher = patch.object(frappe, "throw", _throw)
	patcher.start()
	case.addCleanup(patcher.stop)


class _Result:
	"""What `_bench_run` returns: only `returncode`, `stdout` and `stderr` are read."""

	def __init__(self, returncode=0, stdout="", stderr=""):
		self.returncode = returncode
		self.stdout = stdout
		self.stderr = stderr


def _logo_config_calls(bench_run):
	"""The `set-config tenant_logo_url ...` commands a mocked `_bench_run` saw."""
	return [c.args[0] for c in bench_run.call_args_list
	        if "set-config tenant_logo_url" in c.args[0]]


class _EditFixture(unittest.TestCase):
	"""A temporary sites/ folder with a control site that holds the upload."""

	def setUp(self):
		self._tmp = tempfile.TemporaryDirectory()
		self.sites = self._tmp.name
		self.src_dir = os.path.join(self.sites, CONTROL, "public", "files")
		self.dst_dir = os.path.join(self.sites, TENANT, "public", "files")
		os.makedirs(self.src_dir)
		os.makedirs(os.path.join(self.sites, TENANT))
		self._sites_patch = patch.object(api, "SITES_DIR", self.sites)
		self._sites_patch.start()
		self._had_site = hasattr(frappe.local, "site")
		self._old_site = getattr(frappe.local, "site", None)
		frappe.local.site = CONTROL
		_throw_without_a_site(self)

	def tearDown(self):
		self._sites_patch.stop()
		if self._had_site:
			frappe.local.site = self._old_site
		elif hasattr(frappe.local, "site"):
			del frappe.local.site
		self._tmp.cleanup()

	def put_upload(self, name=LOGO, content=b"png-bytes"):
		with open(os.path.join(self.src_dir, name), "wb") as f:
			f.write(content)

	def tenant_copy(self, name=LOGO):
		return os.path.join(self.dst_dir, name)

	def edit(self, **kwargs):
		"""Save the Edit Tenant dialog. Returns (result, logo set-config calls)."""
		with patch.object(api, "_bench_run", return_value=_Result()) as bench_run, \
				patch.object(api, "_require_admin"):
			out = api.update_tenant(TENANT, tenant_name="Acme", **kwargs)
		return out, _logo_config_calls(bench_run)


class TestEditingTheLogo(_EditFixture):

	def test_a_new_logo_is_copied_before_the_config_is_written(self):
		"""The order matters: config last, so the tenant never points at nothing."""
		self.put_upload()
		copied_when_config_written = {}

		def record(cmd, *a, **kw):
			if "set-config tenant_logo_url" in cmd:
				copied_when_config_written["file_there"] = os.path.isfile(self.tenant_copy())
			return _Result()

		with patch.object(api, "_bench_run", side_effect=record) as bench_run, \
				patch.object(api, "_require_admin"):
			out = api.update_tenant(TENANT, tenant_name="Acme", logo_url=f"/files/{LOGO}")

		calls = _logo_config_calls(bench_run)
		self.assertEqual(out["status"], "ok")
		self.assertEqual(len(calls), 1)
		self.assertIn(f'tenant_logo_url "/files/{LOGO}"', calls[0])
		self.assertTrue(copied_when_config_written.get("file_there"),
		                "the config was written before the file reached the tenant")
		self.assertNotIn("[WARN]", out["message"])

	def test_an_edit_that_does_not_mention_the_logo_leaves_it_alone(self):
		"""Renaming a tenant or ticking a module must not touch the logo."""
		out, calls = self.edit(primary_color="#123456")
		self.assertEqual(out["status"], "ok")
		self.assertEqual(calls, [])

	def test_an_explicitly_empty_logo_url_is_still_a_no_op(self):
		"""'' means 'not touched'. Removal has its own argument, on purpose."""
		out, calls = self.edit(logo_url="")
		self.assertEqual(calls, [])
		out, calls = self.edit(logo_url="", remove_logo=0)
		self.assertEqual(calls, [])

	def test_remove_writes_an_empty_value(self):
		out, calls = self.edit(remove_logo=1)
		self.assertEqual(out["status"], "ok")
		self.assertEqual(len(calls), 1)
		self.assertIn('set-config tenant_logo_url ""', calls[0])
		self.assertIn(f"--site {TENANT}", calls[0])
		# Never a path, and never the word "None" or "null".
		self.assertNotIn("/files/", calls[0])
		self.assertNotIn("None", calls[0])
		self.assertNotIn("null", calls[0])

	def test_remove_accepts_the_shapes_a_browser_sends(self):
		for value in (1, True, "1", "true", "TRUE", "on", "yes"):
			out, calls = self.edit(remove_logo=value)
			self.assertEqual(len(calls), 1, value)
			self.assertIn('tenant_logo_url ""', calls[0], value)

	def test_anything_unrecognised_does_not_remove_a_logo(self):
		"""A destructive action fails closed."""
		for value in (0, False, "", "0", "false", "off", "no", None, "maybe"):
			out, calls = self.edit(remove_logo=value)
			self.assertEqual(calls, [], value)

	def test_asking_to_replace_and_remove_at_once_is_refused(self):
		self.put_upload()
		with patch.object(api, "_bench_run", return_value=_Result()) as bench_run, \
				patch.object(api, "_require_admin"):
			with self.assertRaises(frappe.ValidationError):
				api.update_tenant(TENANT, tenant_name="Acme",
				                  logo_url=f"/files/{LOGO}", remove_logo=1)
			self.assertEqual(_logo_config_calls(bench_run), [])

	def test_removal_does_not_delete_the_file(self):
		"""We chose to leave old files alone - see the slice notes."""
		self.put_upload()
		self.edit(logo_url=f"/files/{LOGO}")
		self.assertTrue(os.path.isfile(self.tenant_copy()))
		self.edit(remove_logo=1)
		self.assertTrue(os.path.isfile(self.tenant_copy()))
		self.assertTrue(os.path.isfile(os.path.join(self.src_dir, LOGO)))


class TestWhatWeRefuse(_EditFixture):

	def test_a_file_type_we_do_not_serve_is_refused(self):
		for name in ("payroll.pdf", "notes.txt", "shell.sh", "page.html", "logo.png.exe"):
			self.put_upload(name=name, content=b"not-a-picture")
			out, calls = self.edit(logo_url=f"/files/{name}")
			self.assertEqual(calls, [], name)
			self.assertIn("not an image we can show", out["message"], name)
			self.assertFalse(os.path.exists(self.tenant_copy(name)), name)

	def test_every_type_the_console_offers_is_accepted(self):
		for name in ("a.png", "b.jpg", "c.jpeg", "d.svg", "e.webp", "f.gif", "G.PNG"):
			self.put_upload(name=name)
			out, calls = self.edit(logo_url=f"/files/{name}")
			self.assertEqual(len(calls), 1, name)

	def test_an_absolute_url_with_shell_characters_is_refused(self):
		"""`_bench_run` uses shell=True; this value must never carry a command."""
		bad = [
			'https://x.test/a.png"; touch /tmp/pwned; echo "',
			"https://x.test/$(whoami).png",
			"https://x.test/`id`.png",
			"https://x.test/a.png & rm -rf /",
			"https://x.test/a b.png",
			"https://x.test/a.png\nrm -rf /",
		]
		for value in bad:
			out, calls = self.edit(logo_url=value)
			self.assertEqual(calls, [], value)
			self.assertIn("[WARN]", out["message"], value)

	def test_a_plain_absolute_url_still_works(self):
		out, calls = self.edit(logo_url="https://cdn.example.com/acme-logo.png?v=2")
		self.assertEqual(len(calls), 1)
		self.assertIn("https://cdn.example.com/acme-logo.png?v=2", calls[0])


class TestOnlyTheControlPlaneMayDoThis(unittest.TestCase):
	"""The permission boundary, proved rather than assumed.

	`_require_admin` is NOT mocked here. It is the real guard.
	"""

	def setUp(self):
		self._old_conf = getattr(frappe.local, "conf", None)
		self._had_conf = hasattr(frappe.local, "conf")
		self._old_session = getattr(frappe.local, "session", None)
		self._had_session = hasattr(frappe.local, "session")
		_throw_without_a_site(self)

	def tearDown(self):
		if self._had_conf:
			frappe.local.conf = self._old_conf
		elif hasattr(frappe.local, "conf"):
			del frappe.local.conf
		if self._had_session:
			frappe.local.session = self._old_session
		elif hasattr(frappe.local, "session"):
			del frappe.local.session

	def _refused(self, conf, user, roles):
		frappe.local.conf = frappe._dict(conf)
		frappe.local.session = frappe._dict({"user": user})
		with patch.object(api, "_bench_run", return_value=_Result()) as bench_run, \
				patch.object(frappe, "get_roles", return_value=roles):
			with self.assertRaises(frappe.PermissionError):
				api.update_tenant("victim.test", remove_logo=1)
			bench_run.assert_not_called()

	def test_a_tenant_site_has_no_tenant_management_at_all(self):
		"""No alvoraa_control_plane flag - the endpoint does not exist here."""
		self._refused({}, "admin@tenant.test", ["System Manager", "HR Manager"])

	def test_an_hr_manager_cannot_change_a_logo(self):
		"""Even on the control plane, and even without System Manager."""
		self._refused({"alvoraa_control_plane": 1}, "hr@acme.test",
		              ["HR Manager", "Employee"])

	def test_guest_cannot_change_a_logo(self):
		self._refused({"alvoraa_control_plane": 1}, "Guest", [])


class TestTheConsoleActuallyCallsIt(unittest.TestCase):
	"""029 built the server half and nothing used it. Pin that this one is wired.

	A static read of the page, so it needs no browser. It catches the failure
	that matters: the control being there but sending nothing.
	"""

	@classmethod
	def setUpClass(cls):
		with open(ADMIN_PAGE, encoding="utf-8") as f:
			cls.page = f.read()

	def test_the_edit_dialog_has_a_logo_control(self):
		for needle in ('id="edit-logo"', 'ke-logo-state', 'keRemoveLogo', 'keChooseLogo'):
			self.assertIn(needle, self.page, needle)

	def test_the_edit_modal_sends_the_logo_to_update_tenant(self):
		self.assertIn("args.logo_url = await uploadLogoFile(keLogoFile)", self.page)
		self.assertIn("args.remove_logo = 1", self.page)
		self.assertIn("api('alvoraa_portal.tenant_api.update_tenant', args)", self.page)

	def test_it_reuses_the_one_upload_path(self):
		"""One door to upload_file, not two."""
		self.assertEqual(len(re.findall(r"/api/method/upload_file", self.page)), 1)

	def test_the_limits_are_on_screen_in_plain_words(self):
		self.assertIn("logos must be under 2 MB", self.page)
		self.assertIn("That is not an image we can use", self.page)
		self.assertIn("PNG, JPG, SVG, WEBP or GIF, under 2 MB", self.page)

	def test_it_says_when_there_is_no_logo_rather_than_showing_nothing(self):
		self.assertIn("No logo set", self.page)

	def test_the_control_has_a_real_label(self):
		self.assertIn('<label class="ka-label" for="edit-logo">Company Logo</label>', self.page)
