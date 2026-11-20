import frappe
from frappe import _
from frappe.utils import cint, cstr
from werkzeug.exceptions import HTTPException

from alvoraa_portal.subscription import has_feature

# Roles that are allowed to reach the Frappe desk (/app) when the account is not
# tied to an Employee record — i.e. pure platform operators, not staff.
_DESK_ROLES = frozenset({
    "System Manager", "Administrator",
})

# Slice 079. Named here as well as in `joiner_invite` so that neither module has
# to import the other on the front door of every tenant: `auth` is imported by
# `hooks.py` on every request, and `joiner_invite` pulls in the submission
# controller and the settings layer behind it.
JOINER_ROLE = "Alvoraa Joiner"
JOINING_PAGE = "/joining"
# Where HR's "Signs in with" value lives. Named here for the same reason as
# the role above: `auth` is on the front door of every request and must not
# drag the submission controller in behind it.
JOINER_SUBMISSION = "Alvoraa Joiner Submission"
# The three statuses that mean this invite is over. Named here rather than
# imported from the submission controller for the reason above - and kept in
# step with `TERMINAL` in
# `alvoraa_portal/doctype/alvoraa_joiner_submission/alvoraa_joiner_submission.py`,
# which is the definition. The five statuses are Invited, Submitted, Made an
# employee, Expired and Cancelled.
JOINER_TERMINAL = frozenset({"Made an employee", "Expired", "Cancelled"})


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

        roles = set(frappe.get_roles(user))

        # Slice 079, 079-SEC-3, and this branch IS the slice's P1.
        #
        # A new joiner is a signed-in account with NO Employee record and no
        # desk role, which is exactly the user the fall-through below sends to
        # /hrms-employee - the staff portal. Without this line a joiner's
        # sign-in opens the employee portal, which would make the login WIDER
        # than the bearer link it replaced, because a link at least reached one
        # page.
        #
        # It sits here, in the one function three doors already share, rather
        # than in each door - which is why that function exists. And it costs
        # nothing: the roles set below was already being read for the same
        # request.
        if JOINER_ROLE in roles:
            return JOINING_PAGE

        if _DESK_ROLES.intersection(roles):
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


# ── One page and nothing else (slice 079, 079-SEC-3) ───────────────────────
#
# **The load-bearing control of slice 079.** Counsel preferred a restricted
# login to an expiring link because a login identifies the person. That is only
# true if the restriction is real: an account inside the site is a bigger thing
# than a URL, and this is the only reason the login is safer than the link.
#
# It is deliberately the SAME SHAPE as `lock_until_password_chosen` above - a
# path allow-list, a `cmd` allow-list honoured only on "/", and an order that
# keeps the cheap checks first - because that shape is built, reviewed and paid
# for twice over in live incidents. Copying it was the cheapest rung available:
# Frappe has no "this role may reach one page" switch (`Role.home_page` decides
# a landing, not a boundary), and a per-route permission DocType would buy a
# permission surface and a migration for a list of ten strings.
#
# **It differs from its ancestor in exactly one way, and the difference is the
# point: this one fails CLOSED.** `lock_until_password_chosen` fails open on
# purpose, because locking 441 staff out at shift change is worse than the hole
# it closes. Here the trade is the other way round: a false denial costs ONE
# person a telephone call to HR, and a false allow puts an unidentified account
# inside a tenant's portal.

_JOINER_MAY_REACH = (
    "/joining",
    "/logout",
    "/login",
    "/alvoraa-login",
    "/assets/",
    "/favicon.ico",
    # Sign-in and sign-out themselves. Frappe completes the login inside
    # `init_request`, which is also where this hook runs - so by the time we are
    # called the session is ALREADY the joiner. Leave `/api/method/login` out
    # and the login reply carries "Logged In" and a 403 in the same body: the
    # person types the right password and is told it failed. Only a real HTTP
    # request shows this; every unit test passes without it.
    "/api/method/login",
    "/api/method/logout",
    # **The second half of signing in, and leaving it out is a real fault.** The
    # sign-in page asks this where the browser should go next, and for a joiner
    # it answers "/joining" - it is `home_page_for` behind a whitelist and it
    # names nothing about anybody else. Refuse it and the page falls back to
    # /hrms-employee, which this gate then turns into the one-page refusal: so
    # the first thing a joiner would see, after typing the right password, is
    # the screen that tells them they cannot be here.
    "/api/method/alvoraa_portal.auth.get_portal_redirect",
    # The joining page's own calls, by their dotted names, because the page
    # posts to /api/method/<dotted> with `fetch` rather than through Frappe's
    # website `frappe.call`.
    "/api/method/alvoraa_portal.joiner_public.",
)

# **Empty, and that is not an oversight.** The joining page uses `fetch` to
# /api/method/<dotted>, never a website-page `frappe.call`, so there is no
# legitimate `cmd` for a joiner at all. The set exists so that the check on "/"
# exists: honouring a `cmd` the allow-list does not name would hand over the
# key, and a POST to "/" with `cmd=frappe.client.get_list` is a door a path
# check cannot see. This product has paid for the missing-`cmd` half twice.
_JOINER_MAY_CALL = frozenset()

# "Has this account got the joiner role?" Remembered per user, in one hash.
# Keeping it off the database is the whole of NFR-3: this gate must add no
# database read for a member of staff.
#
# **This comment used to say the entry never needed invalidating, because the
# answer never needed to change. That was wrong, and it locked a real person out
# of a real tenant.** ALV-319, amata.dev, 5 November 2026. The recorded reasoning
# was that a joiner account never gains or loses the role, and that nothing in
# this product ever gives a member of staff the role. Both premises failed on the
# same morning: the role was added to a Role Profile (ALV-318), a user inherited
# it a minute later, and when it was taken away again the cached "yes" went on
# confining them to the joining form. Nothing on screen pointed at a cache; only
# a hand-typed `frappe.cache().delete_key("alvoraa_is_a_joiner")` released them.
#
# So the entry is now dropped whenever a user's roles change - see
# `forget_whether_they_are_a_joiner` below.
_JOINER_CACHE = "alvoraa_is_a_joiner"

# One sentence, used by both halves of the refusal. It names nothing: not the
# page they asked for, not a menu, not a count.
_ONE_PAGE = "This sign-in only opens your joining form."


def _is_a_joiner(user):
    cache = frappe.cache()
    seen = cache.hget(_JOINER_CACHE, user)
    if seen is not None:
        return bool(cint(seen))
    answer = JOINER_ROLE in set(frappe.get_roles(user))
    cache.hset(_JOINER_CACHE, user, 1 if answer else 0)
    return answer


def forget_whether_they_are_a_joiner(user, method=None) -> None:
    """Frappe `User.on_update` hook. Drop this account's cached answer.

    ALV-319, and the only thing it has to get right is that **taking a role away
    takes effect**. An administrator who removes a role, sees it gone from the
    user record and finds the person still locked out has nothing on screen that
    would lead them to a cache.

    It fires on an insert as well as on a save (`document.py`,
    `run_post_save_methods` runs `on_update` whenever the action is "save"), so a
    new account can never inherit a stale entry left behind under a login id that
    was used before.

    Takes a `User` document or a plain name, so a caller holding only the name
    can use it too.

    **The one window this does not close, named rather than hidden:** the hook
    runs before the transaction commits, so a request arriving from the same
    person in between can read the old roles and cache "yes" again after this
    `hdel`. It is one request wide, and the next save of that account clears it.
    `frappe.db.after_commit` would shut it, at the price of a fix that does not
    run inside a test transaction and so cannot be proved by a test - the wrong
    trade for one key in one hash.
    """
    name = getattr(user, "name", user)
    if not name:
        return
    try:
        frappe.cache().hdel(_JOINER_CACHE, name)
    except Exception:
        # A Redis blip costs us the invalidation, never the person's save. No
        # user detail in the log line.
        _quietly("Joiner gate could not forget a cached answer")


class _GoToTheJoiningPage(HTTPException):
    """A 302 to the one page this sign-in opens.

    A werkzeug `HTTPException`, and deliberately not `frappe.Redirect`, for the
    reason recorded on `_GoChooseAPassword` above: `app.py` has no branch for a
    redirect in `handle_exception`, so a `frappe.Redirect` escaping a
    `before_request` hook renders the generic "Uncaught Exception" page. A
    werkzeug exception is handed back untouched, which is the supported way out.

    302 rather than werkzeug's own 308, which a browser caches - a permanent
    redirect here would go on bouncing the person's pages after they start work
    and become an employee, with nothing on the server able to clear it.

    `?one-page=1` is what makes the joining page draw the refusal the design
    asks for - *"This sign-in only opens your joining form"*, one button that
    works, code `JOIN-ONEPAGE` - instead of silently showing the form. The
    refusal names no page, no menu and no count.
    """

    code = 302

    def get_response(self, environ=None, scope=None):
        from werkzeug.utils import redirect

        response = redirect(f"{JOINING_PAGE}?one-page=1", code=302)
        response.headers["Cache-Control"] = "no-store"
        return response


def lock_to_the_joining_page():
    """Frappe `before_request` hook. A joiner reaches their form and nothing else.

    Three blocks, and the split is the fail-closed design rather than style.

    The first two blocks establish facts and **fail open**, because a failure
    there means we never found out who is asking, and refusing every request on
    a database blip would take a tenant down. The third block runs only once we
    KNOW the session holds the joiner role and is asking for something that is
    not theirs - and from there a failure **refuses**, because at that point the
    only thing we could get wrong is our own refusal.
    """
    try:
        request = getattr(frappe.local, "request", None)
        if request is None:
            return

        path = request.path or "/"
        if path.startswith(_JOINER_MAY_REACH):
            return

        # Only ever on "/", and deliberately so - see _JOINER_MAY_CALL.
        if path == "/":
            form = getattr(frappe.local, "form_dict", None)
            asked = (form or {}).get("cmd")
            if asked and asked in _JOINER_MAY_CALL:
                return

        user = frappe.session.user
        if not user or user in ("Guest", "Administrator"):
            return
    except Exception:
        # The logging gets its own net: the likeliest reason we are here at all
        # is that the database is unreachable, and `frappe.log_error` writes to
        # the database. No user detail - this runs on every request.
        _quietly("Joiner gate could not read the request")
        return

    try:
        if not _is_a_joiner(user):
            return
    except Exception:
        # We never established what this account is. Everybody else keeps
        # working; a joiner whose roles we cannot read gets in, and that window
        # is narrower than a tenant locked out of its own portal.
        _quietly("Joiner gate could not read the roles")
        return

    try:
        _refuse(path)
    except (_GoToTheJoiningPage, frappe.PermissionError):
        raise
    except Exception:
        # **FAIL CLOSED.** We know this session is a joiner and we know it is
        # asking for something that is not theirs. The inverse of
        # `test_it_fails_open`, and it must never be copied from it.
        _quietly("Joiner gate failed, and refused")
        raise frappe.PermissionError(_(_ONE_PAGE))


def _refuse(path):
    """Turn away a joiner asking for something that is not theirs.

    Its own function for one reason: it is the only thing left that can
    genuinely be buggy once the gate knows who is asking, so it is the thing a
    fail-closed test forces an exception inside. A test that broke the role
    lookup instead would be testing the block that is *meant* to fail open.
    """
    if path.startswith("/api/"):
        # Not a redirect: an XHR cannot follow one usefully, and a caller at
        # this level is asking for data, not a page. The refusal names nothing -
        # no doctype, no page, no count.
        raise frappe.PermissionError(_(_ONE_PAGE))
    raise _GoToTheJoiningPage


def let_the_joiner_type_what_hr_gave_them(login_manager=None):
    """Frappe `before_login` hook. ALV-394.

    A joiner is told to sign in with the number or email HR reached them on.
    That value is on no account anywhere: slice 079 gives the joiner an opaque,
    non-routable login id on purpose (079-SEC-1), and `make_sign_in` copies what
    HR typed onto `User.mobile_no` **only when it is a telephone number**. So an
    email invite had nothing for Frappe to match, `find_by_credentials` returned
    no row, and the page - which turns every refusal it does not recognise into
    the wrong-password wording - told the joiner to check a password that was
    never read. Invited by email, nobody could ever get in.

    This swaps what they typed for the login id that exists, before Frappe looks
    anything up. The opaque id stays opaque; nothing new is returned to the
    browser.

    **`before_login`, and NOT `before_request`.** The first shape of this fix
    was a `before_request` hook and it never ran: `frappe/app.py:242` builds
    `HTTPRequest()`, which constructs a `LoginManager`, which signs the person
    in and raises - all **before** the `before_request` loop two lines below at
    :244. Sixteen tests passed against a hook that was never reached, because
    they called it by hand with a fake request instead of driving a real one.
    `run_trigger("before_login")` is the first line of `LoginManager.login()`
    (`frappe/auth.py:147`), eight lines ahead of `authenticate()`, which reads
    `frappe.form_dict.usr` (`:261`) once `get_cached_user_pass()` comes back
    empty - and it does, unless two-factor is mid-flight.

    Two things fall out of being here rather than there. Nothing runs on an
    ordinary request at any tenant any more. And `cmd=login` on "/" - the other
    way into `login()` (`frappe/auth.py:130`) - is covered, which a path check
    would have missed.

    **It is not an oracle (US-4).** There is no new endpoint and no new wording.
    A stranger guessing an address gets the same refusal as before, because the
    only thing that changes is which row Frappe fails to authenticate against.

    **It makes `allow_login_using_mobile_number` unnecessary for joiners.** That
    setting is tenant-wide: turning it on let every employee at that tenant sign
    in with their mobile number too, a side effect accepted by name in 079
    decision 6b. Mobile invites now work without it.

    **Fails open.** Every failure leaves what was typed alone, so the worst case
    is the refusal that happens today - never a tenant locked out of its login.

    `login_manager` is passed by `run_trigger` and is not used; the parameter is
    there because `on_login` below takes it the same way.
    """
    try:
        form = getattr(frappe.local, "form_dict", None)
        if not form:
            return
        typed = cstr(form.get("usr") or "").strip()
        if not typed:
            return

        # A real account: leave it alone. This is also what keeps every member
        # of staff out of the lookup below - they cost nothing extra, because a
        # successful sign-in never reaches the next line.
        if frappe.db.exists("User", typed):
            return

        hidden = _the_sign_in_hr_made_for(typed)
        if hidden:
            form["usr"] = hidden
    except Exception:
        # No user detail: what was typed may be somebody's real address.
        _quietly("Joiner sign-in could not be resolved")


def _the_sign_in_hr_made_for(typed):
    """The opaque login id behind what HR wrote in "Signs in with", or None.

    `login_id` is **not unique** on the submission - only `user` is - so one
    address can appear on more than one row once an invite has been cancelled
    and another made. The order here is deliberate rather than left to the
    database:

    1. exactly one **live** row - its account enabled AND its status not one of
       the three in `JOINER_TERMINAL` - so a re-invited joiner reaches the one
       that works;
    2. more than one live row - nothing, and a security-log line. Choosing
       between two working accounts would sign the joiner into somebody
       else's record;
    3. no live row - the newest **closed** account, so an ended sign-in
       resolves to something rather than to nothing and the joiner is told
       their sign-in is over rather than that they typed it wrong;
    4. terminal rows whose accounts are all still OPEN - nothing, and a
       security-log line. Handing one back would sign a cancelled joiner in.

    Steps 2 and 4 both go through `_refuse_and_log`.

    **Why it takes both the account and the status.** Status alone was the first
    shape and it was wrong: `joiner_housekeeping.expire_the_dead_sign_ins`
    calls `doc.save`, which bumps `modified`, so the nightly job can make a
    DEAD row the newest one. A joiner re-invited after an expiry would then be
    sent to the expired account and told their password was wrong - the very
    failure this fix exists to remove.

    `User.enabled` alone was the second shape, and that was wrong too, caught
    by `test_the_live_invite_wins_over_a_cancelled_one`. **Cancelling an invite
    does not necessarily disable its account** - only `end_the_sign_in` does
    that, and the status can be set without it - so an ordinary
    cancel-then-reinvite left two enabled accounts on one address and step 2
    refused a sign-in that was never ambiguous.

    So: the account says whether the sign-in still works, the status says
    whether anyone still means it to, and a row has to pass both.

    `ignore_permissions` because the caller is Guest and has no read on the
    submission. It returns a login id and nothing else: no name, no status, and
    nothing reaches the browser.
    """
    rows = frappe.get_all(
        JOINER_SUBMISSION,
        filters={"login_id": typed},
        fields=["user", "status"],
        order_by="modified desc",
        ignore_permissions=True,
    )

    with_an_account = []
    for row in rows:
        enabled = frappe.db.get_value("User", row.get("user"), "enabled") \
            if row.get("user") else None
        if enabled is None:
            continue
        with_an_account.append((row, cint(enabled)))

    if not with_an_account:
        return None

    # **Live means both things, and it took a regression to learn that.**
    # Keying on `User.enabled` alone refused a case that is not ambiguous: an
    # invite can be cancelled by a path that does not disable its account - the
    # status is set directly, and only `end_the_sign_in` disables the User - so
    # a plain cancel-then-reinvite left two ENABLED accounts and this branch
    # turned a working sign-in into a refusal. Status alone is no good either,
    # for the `modified` reason in the docstring above. It has to be both.
    live = [row for row, enabled in with_an_account
            if enabled and cstr(row.get("status")) not in JOINER_TERMINAL]

    # **Two working accounts on one address: refuse, do not choose.** Neither
    # this fix nor ALV-396's guard can clean up data that predates them, and a
    # tenant invited on the same address twice before either landed has two
    # enabled accounts for one `login_id`. Picking the newest would sign the
    # joiner into SOMEBODY ELSE'S record - the worst outcome available here, and
    # the hardest to notice, because both parties see a screen that works.
    #
    # Returning None leaves what was typed alone, so Frappe refuses exactly as
    # it does today. The joiner is no worse off than before this fix existed,
    # and HR gets a line in the security log instead of nobody getting anything.
    #
    # Once ALV-396 is in, this branch should be unreachable for NEW invites: the
    # guard refuses a second invite while the first is live and has a sign-in.
    # If it fires on fresh data, that guard has a hole.
    if len(live) > 1:
        _refuse_and_log(
            "joiner_sign_in_matched_more_than_one_live_account", live)
        return None

    if live:
        return live[0]["user"]

    # No live row, so fall back to the ended sign-in. That is on purpose: Frappe
    # answers "User disabled or missing" for a closed account, which the page
    # turns into "this sign-in has finished its job" (079 decision 4a), instead
    # of sending the joiner back to try a password that was never the problem.
    #
    # **Only ever an account that is genuinely CLOSED**, which is why this reads
    # `enabled` again rather than reusing the row's status.
    closed = [row for row, enabled in with_an_account if not enabled]
    if closed:
        return closed[0]["user"]

    # Left over: every row is terminal and yet its account is still OPEN.
    #
    # That is the silent close failure. `joiner_invite.end_the_sign_in` catches
    # every exception, writes an Error Log and returns False, and `on_update`
    # discards the answer
    # (`alvoraa_portal/doctype/alvoraa_joiner_submission/
    #   alvoraa_joiner_submission.py:99`) - so the save succeeds, HR's screen
    # reads Cancelled, and the login still works.
    #
    # **Resolving one of these would sign a cancelled joiner in.** Before
    # ALV-394 nothing mapped an emailed address to that account, so the fault
    # sat there unreachable; this hook is exactly what would turn it into a
    # working door. Refusing leaves it shut and puts a line where HR can find
    # it. The underlying fault is its own ticket, not this one's to fix.
    _refuse_and_log(
        "joiner_sign_in_closed_invite_still_has_an_open_account",
        [row for row, _enabled in with_an_account])
    return None


def _refuse_and_log(event, rows):
    """Record a refusal to resolve, and never get in its way.

    **No personal data in the line** (079-PRIV-7). What the joiner typed is
    somebody's real email address or mobile number, so it is not written here;
    the login ids are, because 079 makes those opaque and non-routable by
    design, and they are what HR needs in order to find the two rows.

    `security_logger` rather than `frappe.logger("security")`: the plain logger
    sits at ERROR in every one of our images, so a `.warning` line is thrown
    away silently. That was ALV-391, and it had made every security line this
    product ever wrote disappear. The helper turns this one logger down to INFO.

    Wrapped, and then `_quietly` as well, because a sign-in must never fail on
    its own audit trail - and because the Error Log row is the copy that
    survives the security log's 2 MB of rotation.
    """
    try:
        import json

        from hrms.alvoraa_hr_core.access import security_logger
        security_logger().warning(json.dumps({
            "event": event,
            "at": str(frappe.utils.now_datetime()),
            "count": len(rows),
            "accounts": sorted(cstr(row.get("user")) for row in rows),
        }))
    except Exception:
        pass
    _quietly("Joiner sign-in matched more than one live account")


def _quietly(title):
    try:
        frappe.log_error(title=title)
    except Exception:
        pass


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
