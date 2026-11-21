"""ALV-422: a joiner can actually sign out.

**The bug this file exists for.** Pressing "Sign out" on the joining form sent
the joiner to `/logout`, and they came straight back to their own form still
signed in.

`/logout` is Frappe's own page. It renders, loads `frappe-web.bundle.js` and
calls `frappe.logout()`, which is:

    frappe.logout = function () {
        frappe.call({ method: "logout", callback: ... });
    };

and `frappe.call` with a bare method name posts to **`/` with `cmd=logout`** -
`frappe.request.url = "/"` (`request.js:8`), used at `:260`. It does NOT post
to `/api/method/logout`.

`auth.lock_to_the_joining_page` allows a joiner a short list of paths, and on
`/` it allows only the `cmd` values in `_JOINER_MAY_CALL`. That set was
**empty**, so `cmd=logout` fell through to `_refuse("/")` and became
`_GoToTheJoiningPage`: a 302 back to the joining form, session untouched.

**Why nothing caught it.** `test_joiner_079.test_the_bare_root_with_a_cmd_is_refused`
exists for precisely this hazard - its own docstring says *"a website page's
`frappe.call` posts to '/' with the method in a `cmd` field, so a test that asks
only with a path proves nothing"*. It tries `frappe.client.get_list` and three
friends. It never tries `logout`, the one `cmd` a joiner is supposed to be able
to send. The knowledge was there; the case was not.

`_JOINER_MAY_CALL`'s own comment argued the set could stay empty because *"the
joining page uses `fetch` to /api/method/<dotted>, never a website-page
`frappe.call`"*. True of the joining page. **False of `/logout`**, which the
gate deliberately lets a joiner reach and which is not our page at all.

The sister gate in the same file, `_FIRST_USE_MAY_CALL`, has listed `"logout"`
from the start, and `_FIRST_USE_MAY_REACH` has listed `/website_script.js` -
measured, per its comment, by watching what that page loads. The joiner lists
were written without that measurement.

**So the test that matters here is the one that posts what the browser posts.**
`TestTheRealSignOut` drives `frappe.app.application` with a cookie jar: sign in,
post `/` with `cmd=logout`, ask whether the session survived. Everything else in
this file is cheaper and proves less.
"""

import os

import frappe

from alvoraa_portal import auth
from alvoraa_portal.tests import fixtures_079 as fx
from alvoraa_portal.tests.fixtures_045 import Wave4Base, own_user

DOCTYPE = "Alvoraa Joiner Submission"

AN_EMAIL = "s422.joiner@example.com"


def _the_joining_page():
	"""The page's source, read off disk.

	Not `frappe.get_app_path(..., "www", "joining.html")`: that scrubs each part
	it is given. Same trap as `test_joiner_sign_in_alv394._the_login_page`.
	"""
	path = os.path.join(frappe.get_app_path("alvoraa_portal"), "www",
	                    "joining.html")
	with open(path, encoding="utf-8") as f:
		return f.read()


class _Base(Wave4Base):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.hr = own_user("s422hr", ("Employee", "HR Manager"))

	def setUp(self):
		super().setUp()
		frappe.set_user("Administrator")
		fx.clear_the_rows()
		fx.switch_the_form_on()
		self._request_was = getattr(frappe.local, "request", None)

	def tearDown(self):
		frappe.local.request = self._request_was
		frappe.set_user("Administrator")
		fx.clear_the_rows()
		fx.switch_the_form_off()
		super().tearDown()

	def _invited(self, login_id=AN_EMAIL, full_name="S422 Ravi Menon"):
		"""HR writes the row and presses the button. Returns (doc, password)."""
		from alvoraa_portal import joiner_invite

		frappe.set_user(self.hr)
		row = fx.a_row(full_name=full_name, login_id=login_id)
		reply = joiner_invite.make_sign_in(submission=row.name)
		frappe.set_user("Administrator")
		return frappe.get_doc(DOCTYPE, row.name), reply["password"]


# ── the one that would have caught it ──────────────────────────────────────

class TestTheRealSignOut(_Base):
	"""Drives `frappe.app.application` with a cookie jar, as the browser does.

	**This is the only test in the file that can tell a working sign-out from a
	working function.** Everything else calls the gate by hand, and the gate was
	never the part that was broken - what was broken was which request the
	browser actually makes.
	"""

	def _client(self):
		from werkzeug.test import Client

		from frappe.app import application

		return Client(application)

	def _run(self, work):
		"""Run `work(client, host)` outside this test's own connection.

		A real request calls `frappe.init`/`frappe.destroy` of its own and tears
		down the handle this test holds, so the context is rebuilt afterwards or
		every later assertion runs on a dead connection. Copied from
		`test_joiner_sign_in_alv394.TestARealRequest`, for the same reason.
		"""
		site = frappe.local.site
		frappe.db.commit()
		try:
			return work(self._client(), site)
		finally:
			frappe.destroy()
			frappe.init(site=site)
			frappe.connect()
			frappe.set_user("Administrator")

	def test_a_joiner_who_presses_sign_out_is_signed_out(self):
		"""**The reported fault, as the joiner meets it.**

		Before the fix this is a 302 to /joining and the session is still live:
		the person presses Sign out, watches the address change, and lands back
		on their own form still signed in.

		The two assertions are deliberately different questions. The first is
		what the sign-out call answered. The second is the only one that
		matters to the person: is the session actually gone?
		"""
		_doc, password = self._invited()

		def work(client, host):
			signed_in = client.post("/api/method/login",
			                        json={"usr": AN_EMAIL, "pwd": password},
			                        headers={"Host": host})
			self.assertEqual(signed_in.status_code, 200,
			                 "the joiner could not sign in to begin with")
			# EXACTLY what `frappe.logout()` sends. Not /api/method/logout:
			# see the module docstring.
			said = client.post("/", data={"cmd": "logout"},
			                   headers={"Host": host})
			# Was the session really ended? Ask for the one page a signed-in
			# joiner may have. 200 means still in; a redirect means out.
			after = client.get("/joining", headers={"Host": host})
			return said.status_code, after.status_code

		said, after = self._run(work)
		self.assertNotEqual(
			said, 302,
			"the sign-out call was turned away and the joiner sent back to "
			"their form")
		self.assertIn(
			after.status_code if hasattr(after, "status_code") else after,
			(301, 302),
			"the joiner is still signed in after pressing Sign out")

	def test_the_sign_out_call_is_not_turned_into_a_redirect(self):
		"""The gate's half of it, stated on its own.

		Kept separate from the test above because they fail for different
		reasons and a single assertion would hide which. This one says the gate
		let the call through; that one says the session actually ended.
		"""
		_doc, password = self._invited()

		def work(client, host):
			client.post("/api/method/login",
			            json={"usr": AN_EMAIL, "pwd": password},
			            headers={"Host": host})
			said = client.post("/", data={"cmd": "logout"},
			                   headers={"Host": host})
			return said.status_code, said.headers.get("Location") or ""

		code, where = self._run(work)
		self.assertNotIn("/joining", where,
		                 "the gate redirected the sign-out back to the form")
		self.assertEqual(code, 200)

	def test_everybody_else_could_always_sign_out(self):
		"""The control. Without it a green run above could mean the whole
		site's sign-out is broken rather than the joiner's."""
		other = own_user("s422staff", ("Employee",))
		frappe.set_user("Administrator")
		pwd = "s422-Only-A-Test-99"
		user = frappe.get_doc("User", other)
		user.new_password = pwd
		user.save(ignore_permissions=True)
		frappe.db.commit()

		def work(client, host):
			client.post("/api/method/login", json={"usr": other, "pwd": pwd},
			            headers={"Host": host})
			return client.post("/", data={"cmd": "logout"},
			                   headers={"Host": host}).status_code

		self.assertEqual(self._run(work), 200)


# ── the gate, asked directly ───────────────────────────────────────────────

class TestTheGateAllowsTheWayOut(_Base):
	"""Cheap checks on the lists themselves.

	They prove less than `TestTheRealSignOut` and are here for one reason: when
	that test goes red, these say in one line whether the list or something else
	is at fault.
	"""

	def _as_the_joiner(self, doc):
		frappe.set_user(frappe.db.get_value(DOCTYPE, doc.name, "user"))

	def _ask(self, path, cmd=None):
		"""Call the gate the way a request would, and report what it did."""
		frappe.local.request = frappe._dict(path=path)
		frappe.local.form_dict = frappe._dict({"cmd": cmd} if cmd else {})
		try:
			auth.lock_to_the_joining_page()
		except auth._GoToTheJoiningPage:
			return "redirected"
		except frappe.PermissionError:
			return "refused"
		return "allowed"

	def test_the_sign_out_command_is_allowed(self):
		"""AC-422-1. The whole fix, in one line."""
		doc, _pwd = self._invited()
		self._as_the_joiner(doc)
		self.assertEqual(self._ask("/", cmd="logout"), "allowed")
		frappe.set_user("Administrator")

	def test_the_page_the_logout_screen_loads_is_allowed(self):
		"""AC-422-2. `/logout` pulls in `/website_script.js`, which the gate
		was turning into a redirect to the joining page - so a joiner's sign-out
		screen was served a page where a script was expected.

		`_FIRST_USE_MAY_REACH` has allowed it from the start, and its comment
		says the list was built by watching what that screen actually loads.
		"""
		doc, _pwd = self._invited()
		self._as_the_joiner(doc)
		self.assertEqual(self._ask("/website_script.js"), "allowed")
		frappe.set_user("Administrator")

	def test_the_data_commands_are_still_refused(self):
		"""**The fix must widen the door by exactly one name.**

		`_JOINER_MAY_CALL` is an allow-list, and the reason it exists at all is
		that a POST to "/" with `cmd=frappe.client.get_list` is a door a path
		check cannot see. This repeats
		`test_joiner_079.test_the_bare_root_with_a_cmd_is_refused` on purpose:
		that test lives beside the gate, this one lives beside the change, and
		the change is the thing that could widen it too far.
		"""
		doc, _pwd = self._invited()
		self._as_the_joiner(doc)
		for cmd in ("frappe.client.get_list", "frappe.client.get_value",
		            "frappe.client.set_value", "frappe.client.delete",
		            "frappe.desk.reportview.get", "frappe.share.add",
		            "frappe.desk.form.utils.add_comment", "login"):
			with self.subTest(cmd=cmd):
				self.assertEqual(self._ask("/", cmd=cmd), "redirected")
		frappe.set_user("Administrator")

	def test_the_other_doors_are_still_shut(self):
		"""The paths 079 closed stay closed. A fix to the way OUT must not
		become a fix to the way in."""
		doc, _pwd = self._invited()
		self._as_the_joiner(doc)
		for path in ("/app", "/hrms-employee", "/files/anything.jpg",
		             "/private/files/anything.jpg"):
			with self.subTest(path=path):
				self.assertIn(self._ask(path), ("redirected", "refused"))
		for path in ("/api/method/frappe.client.get_list",
		             "/api/method/alvoraa_portal.my_profile.get_my_profile"):
			with self.subTest(path=path):
				self.assertEqual(self._ask(path), "refused")
		frappe.set_user("Administrator")


# ── the button itself ──────────────────────────────────────────────────────

class TestTheSignOutButtonExists(_Base):
	def test_the_joining_page_has_a_sign_out_control(self):
		"""If the button is ever removed, the gate entry above becomes dead
		code and this file starts proving nothing."""
		self.assertIn('id="signout"', _the_joining_page())
