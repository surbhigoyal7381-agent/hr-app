"""The portal must carry a real CSRF token, and its token repair must find it.

A CSRF token is a value every save or load request must carry, so another
website cannot send requests on someone's behalf. Frappe checks it against the
one saved in the login session.

Two faults together made the portal fail with "Invalid Request" (2026-09-11):

1. Frappe only creates the session's token when a DESK page loads. The portal
   page was built while the session had none, so it carried "None". The server
   accepted that - there was nothing to compare - until the person opened any
   desk page in any tab. From then on every open portal tab was refused.

2. The page's repair, gpRefreshCsrf(), re-reads the token from a fresh copy of
   the page. Its pattern also matched example text in the page's own comments,
   which comes first, so it installed the literal text "<value>" as the token
   and broke every later request until a manual reload.

Seen in the dev access log on 2026-09-10 (a run of 400s, each retry refused
too) and reproduced step by step on the local copy and on dev.
"""

import importlib.util
import inspect
import os
import re

import frappe
from frappe.tests.utils import FrappeTestCase


def _www(name):
    import alvoraa_portal

    return os.path.join(os.path.dirname(os.path.abspath(alvoraa_portal.__file__)), "www", name)


def _portal_html():
    with open(_www("hrms-employee.html"), encoding="utf-8", errors="replace") as fh:
        return fh.read()


def _page_module():
    """Loaded from its file: www/ is a folder of pages, not an importable package."""
    spec = importlib.util.spec_from_file_location("_hrms_employee_page", _www("hrms_employee.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _repair_pattern():
    """The pattern gpRefreshCsrf() uses, read out of the page and compiled."""
    html = _portal_html()
    start = html.index("function gpRefreshCsrf(")
    body = html[start:html.index("function gpSend(", start)]
    m = re.search(r"html\.match\(/(.+?)/\)", body)
    assert m, "gpRefreshCsrf() no longer reads the token with html.match(/.../) - update this test"
    return re.compile(m.group(1))


def _injected_line(token):
    """The exact line Frappe writes into a built page, taken from Frappe's source,
    so a Frappe upgrade that changes the format fails here rather than in use."""
    from frappe.website.page_renderers.base_template_page import BaseTemplatePage

    src = inspect.getsource(BaseTemplatePage.add_csrf_token)
    m = re.search(r"f'(<script>[^']*)'", src)
    assert m, "Frappe no longer injects the token as f'<script>...' - check gpRefreshCsrf()"
    return m.group(1).replace("{csrf_token}", token)


class TestThePortalPageGivesTheSessionAToken(FrappeTestCase):
    def setUp(self):
        if not getattr(frappe.local.session, "data", None):
            frappe.local.session.data = frappe._dict()
        self._saved = frappe.local.session.data.get("csrf_token")
        self.page = _page_module()
        # branding reads tenant settings this test is not about
        self.page.get_branding = lambda: {}

    def tearDown(self):
        frappe.local.session.data.csrf_token = self._saved

    def test_building_the_page_creates_the_token(self):
        frappe.local.session.data.csrf_token = None
        self.page.get_context(frappe._dict())
        self.assertTrue(frappe.local.session.data.csrf_token,
                        "the page was built without a token, so it would carry None")

    def test_a_token_that_already_exists_is_kept(self):
        """A desk tab may have made one first. Replacing it would break that tab
        instead - the same fault the other way round."""
        frappe.local.session.data.csrf_token = "token-made-by-a-desk-tab"
        self.page.get_context(frappe._dict())
        self.assertEqual(frappe.local.session.data.csrf_token, "token-made-by-a-desk-tab")


class TestTheTokenRepairReadsTheRealLine(FrappeTestCase):
    def test_nothing_in_the_page_source_can_be_mistaken_for_the_token(self):
        """The built page is this source plus Frappe's injected line. If the
        pattern matches anything in the source, that match comes first and wins."""
        hit = _repair_pattern().search(_portal_html())
        self.assertIsNone(hit, f"the repair would read {hit.group(0)!r} as the token" if hit else "")

    def test_it_reads_the_line_frappe_injects(self):
        page = 'frappe.csrf_token = "<value>" ' + _injected_line("abc123def456")
        self.assertEqual(_repair_pattern().search(page).group(1), "abc123def456")
