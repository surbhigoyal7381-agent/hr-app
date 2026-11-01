import frappe
from frappe import _
from werkzeug.exceptions import HTTPException

from alvoraa_portal.subscription import has_feature

# Roles that are allowed to reach the Frappe desk (/app) when the account is not
# tied to an Employee record — i.e. pure platform operators, not staff.
_DESK_ROLES = frozenset({
    "System Manager", "Administrator",
})


def home_page_for(user):
    """Where this user belongs when they ask for nothing in particular.

    One rule, used by three doors: the bare address (the
    `get_website_user_home_page` hook, slice 024), the moment of login
    (`on_login`), and the branded login page (`get_portal_redirect`). They used
    to answer only the last two, so typing https://<tenant>/ dropped an
    employee into the desk. Keeping the rule in one function is what stops the
    doors drifting apart again.

    Anyone with an Employee record lands in the portal, HR and managers
    included: the portal now covers goal setting, KPI assignment, appraisal
    generation and manager scoring, so staff have no reason to see the desk.
    A tenant's HR admin usually also holds System Manager, so seniority alone
    must not route someone to /app — only the absence of an Employee record does.

    Returns a path, or None meaning "Frappe, carry on as you would". None is the
    right answer for a platform operator (Frappe sends a System User to the
    desk) and for Guest (Frappe sends them to the login page). Never returning
    a page here is how /app and the sign-in screen keep working.
    """
    if not user or user == "Guest":
        return None
    if user == "Administrator":
        return None

    try:
        if frappe.db.exists("Employee", {"user_id": user}):
            if _still_on_an_issued_password(user):
                return "/update-password"
            return _portal_home_for(user)

        if _DESK_ROLES.intersection(set(frappe.get_roles(user))):
            return None  # Platform operator — the desk is their workplace

        return _portal_home_for(user)
    except Exception:
        # This runs on the front door of every tenant. A lookup that fails must
        # cost us the redirect, not the site. No user detail in the log line.
        frappe.log_error(title="Landing page lookup failed")
        return None


def _still_on_an_issued_password(user):
    """True while this person has never chosen their own password.

    HR hands out a password — the same one to everybody in a batch — and we want
    those people to land on /update-password until they have replaced it.

    We do NOT compare the password or its hash, and the common password must
    never appear in this code. It could not work anyway: Frappe hashes with
    pbkdf2_sha256 (`frappe/utils/password.py`), which salts every hash
    separately, so a hundred people sharing one password have a hundred
    different hashes and there is nothing to match against.

    What we read instead is `last_password_reset_date`. Frappe stamps it in ONE
    place only - the whitelisted `update_password`, which is what the
    /update-password page calls (`core/doctype/user/user.py`). A password set by
    HR on the User document goes down `set_new_password` -> the low-level
    `_update_password`, which never touches the field. So:

        empty  = nobody but HR has ever set this password  -> send them to change it
        a date = they have chosen their own                -> carry on

    It clears itself: the moment they finish on /update-password the date is
    written and this returns False for ever after. Nothing to reset, no flag to
    tidy up, and no list of who is still pending to keep in step.

    One way the signal dies, and it is stock Frappe, not us: the first time an
    admin ticks "Force user to reset password" in System Settings,
    `update_last_reset_password_date()`
    (`core/doctype/system_settings/system_settings.py`) stamps today onto EVERY
    user whose date is empty. On that tenant everybody then looks like they have
    chosen their own password and this redirect quietly stops. There is no error
    to see. If that happens, the fix is the backfill run the other way, not a
    flag field of our own - a parallel structure here would have to be kept in
    step with Frappe for ever.

    This is a landing page, not a lock. Someone who types another address still
    gets there. If the portal must be unusable until the password changes, that
    is the server-side gate in slice 072, not this.
    """
    return not frappe.db.get_value("User", user, "last_password_reset_date")


@frappe.whitelist(allow_guest=True, methods=["POST"])
def update_password(new_password, logout_all_sessions=0, key=None, old_password=None):
    """Frappe's change-password endpoint, with our landing page on the end.

    Registered in hooks.py as `override_whitelisted_methods`, so every RPC call
    to `frappe.core.doctype.user.user.update_password` comes here instead - the
    /update-password page, the forgot-password link, and the desk's own
    change-password box.

    Why we have to: Frappe's function ends `return get_default_path() or
    "/desk"` for a System User, and the page does
    `window.location.href = r.message`. Every staff account is a System User
    (`tenant_setup.py`), and `get_default_path()` can only name a route an
    installed app registered on the apps screen - measured on this bench as
    "/desk". So the last step of first use dropped a frontline worker on the
    Frappe desk, which is the fault slice 024 exists to stop. That branch
    ignores `redirect_url` and the `redirect_after_login` cache entirely, so
    neither of those reaches it.

    There IS a stock route we have not taken, and this comment used to deny it
    wrongly. `get_default_path()` (`frappe/apps.py`) returns the `route` of the
    app named by `User.default_app` or `System Settings.default_app`, and that
    route is whatever an app declares in its `add_to_apps_screen` hook - Frappe
    HR already declares "/desk/people". So alvoraa_portal could declare
    "/hrms-employee" and set `default_app` at tenant setup, and stock Frappe
    would return the right path with no override at all.

    Two things have to be measured before that swap is worth making, and
    neither has been: `get_apps()` hides an app whose setup wizard is
    incomplete from anyone who is not a System Manager, which would send
    `get_default_path()` back to None and us back to "/desk"; and `default_app`
    changes where every System User flow lands, not only this one. Until
    somebody runs that test on a staff account, this wrapper is what we have.

    The decorator must mirror Frappe's own (`allow_guest=True`,
    `methods=["POST"]`): `frappe.is_whitelisted` checks the method it actually
    resolved, so a wrapper that is not guest-allowed would break the
    forgot-password link for everyone.

    This runs on every password change on every tenant, so it does as little as
    possible. Frappe's function runs first, unchanged, and keeps its own
    answer whenever we have no opinion - which is what a platform operator
    needs. `home_page_for` already swallows its own errors and returns None, so
    a failure here costs the redirect, not the password change.
    """
    from frappe.core.doctype.user.user import update_password as frappe_update_password

    answer = frappe_update_password(
        new_password=new_password,
        logout_all_sessions=logout_all_sessions,
        key=key,
        old_password=old_password,
    )
    if frappe.local.response.get("http_status_code") == 410:
        # A dead or reused reset link. `answer` is the message for the user.
        return answer
    # The password is now set and Frappe has signed them in, so session.user is
    # the right person to ask and the date is already stamped - which is why
    # this returns the portal and not /update-password again.
    return home_page_for(frappe.session.user) or answer


# ── The lock behind the redirect (ALV-242) ─────────────────────────────────
#
# `home_page_for` only decides where somebody LANDS. Surbhi found what that
# leaves open: sign in with the password HR issued, land on /update-password,
# press the browser's back button, and the whole app is there - payslips and
# all - with the shared password never changed. Since HR hands the same password
# to a whole batch, that means anyone in the batch can sign in AS A COLLEAGUE
# and read their pay.
#
# This is slice 072's US-5 ("a first-use session reaches nothing"), gate G-8.
# That spec already recorded why nothing in Frappe can be reused: its own
# `force_user_to_reset_password` is counted in DAYS and applies to the whole
# site, so it cannot say "this one account, now".
#
# `before_request` is the one place that covers every door at once - the portal,
# /me, /checkin and the Frappe desk - because it runs on every request, after
# the session is set up (`frappe/app.py`).

_PASSWORD_SCREEN = "/update-password"


class _GoChooseAPassword(HTTPException):
    """A 302 that Frappe hands straight back to the browser.

    `frappe.Redirect` CANNOT be used from `before_request`, and this cost us a
    live incident on 28 Oct. `app.py` turns an escaping exception into a page
    through `handle_exception`, which has branches for 401, 403, 404, 429 and
    500 and **none for a redirect** - so a redirect fell through to the generic
    "Uncaught Exception" error page, wearing its own 301 status. Frappe's own
    redirect is only understood deeper in, while a website page is rendering.

    Two lines above that, `app.py` does something else entirely for a werkzeug
    HTTPException: `e.get_response(request.environ)`, returned untouched. That
    is the supported way out, so this is one.

    302, and deliberately not werkzeug's own `RequestRedirect`, which is a
    **308 - permanent**. A browser caches a permanent redirect, so the moment
    somebody finished choosing their password the phone would carry on bouncing
    every page back to this screen, with nothing on the server able to clear
    it. `no-store` says the same thing again to anything in between.
    """

    code = 302

    def get_response(self, environ=None, scope=None):
        from werkzeug.utils import redirect

        response = redirect(_PASSWORD_SCREEN, code=302)
        response.headers["Cache-Control"] = "no-store"
        return response


# What a person who has not chosen a password may still reach. Everything here
# is either the way OUT (the password screen, sign-out) or something that screen
# needs in order to work. Measured, not guessed: /update-password loads
# /assets/.../frappe-web.bundle.js and /website_script.js, and calls exactly two
# methods, `update_password` and `test_password_strength`.
_FIRST_USE_MAY_REACH = (
    "/update-password",
    "/logout",
    "/login",
    "/alvoraa-login",
    "/assets/",
    "/files/",
    "/website_script.js",
    "/favicon.ico",
    "/api/method/frappe.core.doctype.user.user.update_password",
    "/api/method/frappe.core.doctype.user.user.test_password_strength",
    "/api/method/alvoraa_portal.auth.update_password",
    "/api/method/frappe.core.doctype.user.user.reset_password",
    "/api/method/logout",
    # Sign-in itself. Frappe completes the login inside `init_request`, which
    # is also where this hook runs - so by the time we are called the session
    # is ALREADY the new user and looks like first use. Leave this out and the
    # login reply carries "Logged In" and a 403 in the same body: the person
    # types the right password and is told it failed. Only a real request over
    # HTTP showed this; every unit test passed without it.
    "/api/method/login",
)

# The same permissions again, by `cmd` name - because a website page does not
# call /api/method/<dotted> at all. `frappe.call` on a website page is
# `frappe/website/js/website.js`, not `request.js`: it posts to "/" with the
# method in a `cmd` field. /update-password IS a website page, so that is how
# its Confirm button and its strength meter actually reach the server.
#
# Leaving this out is what put a live tenant on a dead password screen on
# 29 Oct. The path was "/", nothing in the list above matched, and the POST was
# answered with our own 302. jQuery followed the redirect, got the HTML of the
# password screen where it was expecting JSON, and gave up without a sound: no
# error, no redirect, password unchanged. The screen simply sat there, and
# because the password never changed the way out stayed shut for ever.
#
# Every unit test passed, because every unit test asked with a path and the
# page never sends one.
#
# `frappe.local.form_dict` is built by `make_form_dict(request)` in
# `app.py:init_request`, two lines before the before_request hooks run, so it
# is always there by the time we read it.
_FIRST_USE_MAY_CALL = frozenset({
    "frappe.core.doctype.user.user.update_password",
    "frappe.core.doctype.user.user.test_password_strength",
    "frappe.core.doctype.user.user.reset_password",
    "alvoraa_portal.auth.update_password",
    "login",
    "logout",
})

# Once somebody has chosen their own password they can never go back to not
# having chosen one, so a "yes" is true for ever and is safe to remember. This
# is what keeps the lock off the database on the ordinary request: everybody
# who is past first use is answered out of redis.
_CHOSEN_CACHE = "alvoraa_password_chosen"


def _has_chosen_own_password(user):
    cache = frappe.cache()
    if cache.hget(_CHOSEN_CACHE, user):
        return True
    if frappe.db.get_value("User", user, "last_password_reset_date"):
        cache.hset(_CHOSEN_CACHE, user, 1)
        return True
    return False


def route_the_bare_root():
    """Frappe `before_request` hook: decide what "/" means on a tenant.

    We already answer this through `get_website_user_home_page`, but Frappe
    asks that hook fourth. `get_home_page()` tries, in order: a home_page on
    any role the person holds, Portal Settings' default_portal_home, our hook,
    Website Settings' home_page - and then, last of all, a default workspace
    REPLACES whatever any of that decided. So on a tenant where a role or a
    workspace happens to be set, typing the bare address lands somewhere
    nobody chose: the desk for a member of staff, and Frappe's own unbranded
    Login page for a visitor, because our redirect only covers /login.

    `frappe.local.flags.home_page` is read before all five, so this is the one
    place the answer holds whatever a tenant has been configured with.

    It changes nothing but the bare "/" - every other path returns at once -
    and it fails open: if anything here raises, Frappe decides exactly as it
    does today.
    """
    try:
        request = getattr(frappe.local, "request", None)
        if request is None or (request.path or "/") != "/":
            return

        user = frappe.session.user
        if not user or user == "Guest":
            # Our own sign-in page, with the tenant's name and colours on it.
            frappe.local.flags.home_page = "alvoraa-login"
            return

        # Staff land where login sends them, which already answers the
        # password-not-yet-chosen case. A platform operator gets None, and
        # Frappe keeps sending them to the desk.
        where = home_page_for(user)
        if where:
            # Frappe returns this flag unstripped, so strip it here.
            frappe.local.flags.home_page = where.strip("/")
    except Exception:
        frappe.clear_last_message()


def lock_until_password_chosen():
    """Frappe `before_request` hook. Nothing but the password screen, until.

    The order of the checks is the performance design, not habit. The cheap,
    local tests come first and the database comes last, so an ordinary request
    from an ordinary member of staff costs one redis read and nothing else.

    **It fails open, on purpose.** If this function raises for any reason we
    have not thought of, the person gets in. A lock that breaks must not become
    441 people who cannot use the portal at shift change; the wrong answer here
    costs a window, the other wrong answer costs the day's work.
    """
    try:
        request = getattr(frappe.local, "request", None)
        if request is None:
            return

        path = request.path or "/"
        if path.startswith(_FIRST_USE_MAY_REACH):
            return

        # How the password screen itself calls - see _FIRST_USE_MAY_CALL.
        # Only ever on "/", and deliberately so: honouring `cmd` on any other
        # path would hand anyone the key. Add `&cmd=login` to a POST to
        # /api/method/<anything> and we would wave it through, while Frappe
        # went on routing by the URL and ran the method we meant to block.
        if path == "/":
            form = getattr(frappe.local, "form_dict", None)
            if (form or {}).get("cmd") in _FIRST_USE_MAY_CALL:
                return

        user = frappe.session.user
        if not user or user in ("Guest", "Administrator"):
            return

        if _has_chosen_own_password(user):
            return

        # Only staff. A platform operator's account is not handed out on a card,
        # and locking the back office out of its own site would be worse than
        # the hole this closes.
        if not frappe.db.exists("Employee", {"user_id": user}):
            return

        if path.startswith("/api/"):
            # Not a redirect: an XHR cannot follow one usefully, and a caller
            # at this level is asking for data, not a page.
            raise frappe.PermissionError(
                _("Choose your own password before using the app.")
            )

        raise _GoChooseAPassword

    except (_GoChooseAPassword, frappe.PermissionError):
        raise
    except Exception:
        # The logging gets its own net, and this is not belt and braces. The
        # most likely reason we are here at all is that the database is
        # unreachable - and `frappe.log_error` writes to the database, so it
        # would raise too and the failure would escape after all. The test
        # `test_it_fails_open` caught exactly that. No user detail in the line;
        # this runs on every request.
        try:
            frappe.log_error(title="First-use lock failed open")
        except Exception:
            pass
        return


def on_login(login_manager=None):
    """Frappe hook — fires after every successful login.

    Sets the landing page only when we have an opinion. When `home_page_for`
    returns None the key is left alone, so Frappe's own logic decides — which
    is what a platform operator needs.
    """
    user = frappe.session.user
    if not user or user == "Guest":
        return

    home = home_page_for(user)
    if home:
        frappe.local.response["home_page"] = home


def _portal_home_for(user):
    """Return the correct portal URL for a non-admin user.

    The vendor and driver portals are checked only when the tenant actually has
    the `vendor` feature. Slice 016 made both pages 404 off-plan, so without
    this check a Starter tenant that happens to hold a Vendor User row landed
    that person on a missing page. `/hrms-employee` is always safe: `portal` is
    a required feature, so every tenant has it whatever the plan says.
    """
    if has_feature("vendor"):
        if frappe.db.exists("Vendor User", {"email": user}):
            return "/vendor-portal"
        if frappe.db.exists("Delivery Partner", {"primary_email": user}):
            return "/driver-portal"
    # Default: HRMS self-service portal (covers all employees)
    return "/hrms-employee"


# ── Tenant branding API ────────────────────────────────────────────────────

@frappe.whitelist(allow_guest=True)
def get_tenant_config():
    """Return branding and feature config for the current site.

    Values come from site_config.json, set by provision_tenant.sh.
    All fields have safe defaults so the login page always renders.
    """
    conf = frappe.conf
    return {
        "tenant_name":       conf.get("tenant_name",       "Kinexus HRMS"),
        "logo_url":          conf.get("tenant_logo_url",   ""),
        "primary_color":     conf.get("primary_color",     "#1a7f5a"),
        "accent_color":      conf.get("accent_color",      "#f59e0b"),
        "support_email":     conf.get("support_email",     "support@kinexus.in"),
        "subscription_plan": conf.get("subscription_plan", "starter"),
        "modules_enabled":   conf.get("modules_enabled",   ["hrms", "vendor_portal", "goals"]),
    }


@frappe.whitelist()
def get_portal_redirect():
    """Return the correct portal URL for the currently logged-in user.

    Used by the login page JS after a successful login to decide where
    to send the user without a page round-trip.
    """
    user = frappe.session.user
    if not user or user == "Guest":
        return {"url": "/alvoraa-login"}

    # The same rule as the bare address and as on_login: staff go to the portal
    # regardless of seniority, and no opinion means the desk.
    home = home_page_for(user)
    if home:
        return {"url": home}
    return {"url": "/app", "role": "admin"}
