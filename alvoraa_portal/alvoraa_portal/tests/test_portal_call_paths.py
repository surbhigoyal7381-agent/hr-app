"""Every method the portal calls must actually exist, and be whitelisted.

The portal talks to the server by building a dotted path as a STRING:

    var PF = "alvoraa_portal.performance_api.";
    function pf(method, args) { return gpFetch(PF + method, args || {}); }

Nothing checks that string. Python never imports it, the linter never sees it,
and CI has nothing to compare it against. A wrong module in that path produces a
function that exists, is spelled correctly, is whitelisted - and is still never
reachable. It fails the first time a human opens the page, and not before.

That is not hypothetical. `get_org_setting` was written into hr_api.py and called
through pf() - which points at performance_api - in the SAME commit, on
2026-08-18. The Org Setup page did not work from the day it shipped. Nobody
noticed for eleven days, and in the meantime the broken line was copied to add
two more settings, because it looked exactly like working code.

So this test does the one thing nobody was doing: it reads the paths out of the
page and resolves each one against the real module.
"""

import ast
import os
import re

import frappe
from frappe.tests.utils import FrappeTestCase

APP = frappe.get_app_path("alvoraa_portal") if hasattr(frappe, "get_app_path") else None

# pf("name")  ->  the PF prefix is prepended at runtime
PF_CALL = re.compile(r'\bpf\(\s*["\']([A-Za-z_][A-Za-z0-9_]*)["\']')
# gpFetch("full.dotted.path") and window.gpFetch("...")
FULL_CALL = re.compile(r'\bgpFetch\(\s*["\']([A-Za-z_][A-Za-z0-9_.]*)["\']')
# var PF = "alvoraa_portal.performance_api.";
PF_CONST = re.compile(r'\bPF\s*=\s*["\']([A-Za-z_][A-Za-z0-9_.]*\.)["\']')


def _app_root():
    """The alvoraa_portal package directory, however the bench lays it out."""
    import alvoraa_portal

    return os.path.dirname(os.path.abspath(alvoraa_portal.__file__))


def _portal_html():
    path = os.path.join(_app_root(), "www", "hrms-employee.html")
    with open(path, encoding="utf-8", errors="replace") as fh:
        return fh.read()


def _whitelisted(module_path):
    """Names in `module_path` carrying @frappe.whitelist(), read from SOURCE.

    Parsed rather than imported: a module that fails to import would make every
    path in it look broken and bury the real finding in noise.
    """
    rel = module_path.replace("alvoraa_portal.", "", 1).replace(".", os.sep) + ".py"
    path = os.path.join(_app_root(), rel)
    if not os.path.exists(path):
        return None                     # the MODULE is missing, not the function
    with open(path, encoding="utf-8-sig") as fh:
        tree = ast.parse(fh.read())
    out = set()
    for node in tree.body:
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if any("whitelist" in ast.unparse(d) for d in node.decorator_list):
            out.add(node.name)
    return out


def _called_paths():
    """Every server method the portal page asks for, as a full dotted path."""
    html = _portal_html()
    prefixes = PF_CONST.findall(html)
    assert prefixes, "no PF prefix found - has the page changed how it calls out?"
    prefix = prefixes[0]

    paths = {prefix + name for name in PF_CALL.findall(html)}
    paths |= {p for p in FULL_CALL.findall(html) if p.startswith("alvoraa_portal.")}
    return sorted(paths)


class TestEveryPortalCallResolves(FrappeTestCase):
    def test_the_page_calls_something(self):
        """A regex that quietly matches nothing would make every other test here
        pass while checking absolutely nothing."""
        self.assertGreater(len(_called_paths()), 50)

    def test_every_called_method_exists_and_is_whitelisted(self):
        broken = []
        for path in _called_paths():
            module_path, _, fn = path.rpartition(".")
            names = _whitelisted(module_path)
            if names is None:
                broken.append(f"{path}  (no such module)")
            elif fn not in names:
                broken.append(f"{path}  (not whitelisted in {module_path})")
        self.assertEqual(broken, [], "portal calls that cannot resolve:\n  " + "\n  ".join(broken))

    def test_the_three_that_were_broken_stay_fixed(self):
        """Named explicitly so a regression reads as itself, not as a count."""
        html = _portal_html()
        for gone in ('pf("get_org_setting"', 'pf("set_org_setting"', 'pf("delete_goal"'):
            self.assertNotIn(gone, html,
                f'{gone}...) routes to performance_api, which does not define it')
        for present in ("alvoraa_portal.hr_api.get_org_setting",
                        "alvoraa_portal.hr_api.set_org_setting",
                        "alvoraa_portal.goals_api.delete_goal"):
            self.assertIn(present, html)
