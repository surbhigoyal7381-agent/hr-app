"""Every refusal the field app can be told, in one table.

**Why a table and not a sentence.** The app picks which screen to show from the
`code` in the body, never from the English words. A phone in a shed in Noida may
be running a build from three months ago, and a sentence we reworded on a Monday
must not turn into a blank screen on that phone. So the contract is:

  * one code per reason, one HTTP status per code, both frozen once an app
    version that uses them is out;
  * codes are only ever **added**, never renamed and never removed, for as long
    as a version that speaks them is supported;
  * the English sentence still goes where it always went - Frappe's
    `_server_messages` - so today's web check-in page, which matches on the
    words, keeps working unchanged, and so an operator reading a log still sees
    a sentence rather than a token.

The body therefore carries `code` and `values` at the top level, beside the
`exc_type` Frappe already puts there. Adding keys is safe for every existing
caller; that is the whole reason it is done this way.

`values` is a small, named set per code. It never carries a field name, a
person's name, an employee ID, a secret, a code, a photo or a coordinate - the
app only needs enough to fill a sentence it already has.
"""

import frappe
from frappe import _

# ── the table ────────────────────────────────────────────────────────────────
#
# code -> (HTTP status, the value names this code's body may carry)
#
# Kept in spec order (02-functional-spec.md §7.1) so the two can be read side by
# side. A test walks this table and fails if a code loses its status or grows a
# value the app was never told about.

CODES = {
	# the join code (built in step 3; the codes are frozen here now so that an
	# app built against step 1 already knows every screen it will ever need)
	"QR_NOT_RECOGNISED":  (404, ()),
	"QR_EXPIRED":         (410, ("expired_at",)),
	"QR_USED":            (410, ("used_at",)),
	"QR_CANCELLED":       (410, ()),

	# the organisation's own switches
	"APP_OFF_FOR_FIELD":  (403, ()),
	"NOT_FIELD_ROLE":     (403, ("designation",)),
	"FEATURE_OFF":        (403, ()),

	# the notice
	"NOTICE_CHANGED":     (409, ("version", "rows", "retention_days", "what_changed")),
	"CONSENT_REQUIRED":   (403, ("version",)),

	# the app build
	"APP_TOO_OLD":        (426, ("min_version",)),

	# the phone
	"NOT_SET_UP":         (401, ()),
	"DEVICE_PENDING":     (401, ()),
	"DEVICE_BLOCKED":     (403, ()),          # never a reason. PRIV-13
	"DEVICE_REPLACED":    (403, ("replaced_at",)),
	"DEVICE_REMOVED":     (403, ("removed_at",)),
	"EMPLOYEE_NOT_ACTIVE": (403, ()),

	# the punch
	"LOCATION_MISSING":   (422, ()),
	"GPS_NOT_EXACT":      (422, ("accuracy_m", "limit_m")),
	"OUTSIDE_WORKPLACE":  (422, ("distance_m", "site", "radius_m")),
	"ALREADY_RECORDED":   (409, ("time",)),

	# anything else
	"INVALID_REQUEST":    (400, ()),          # never a field name. SEC-19
	"TOO_MANY_TRIES":     (429, ("retry_after_s",)),
	"SERVER_ERROR":       (500, ()),
}


class FieldAppRefusal(frappe.ValidationError):
	"""A refusal that knows its own code and HTTP status.

	`http_status_code` is set on the INSTANCE, not the class, because one class
	has to answer 400, 401, 403, 409, 410, 422 and 426. Slice 014's wrapper
	already reads `getattr(exc, "http_status_code", None)`, so nothing else had
	to change to make this work.
	"""

	def __init__(self, message, code, http_status_code, values):
		super().__init__(message)
		self.alvoraa_code = code
		self.alvoraa_values = values
		self.http_status_code = http_status_code


def refuse(code, message, **values):
	"""Refuse this request with a named code and a sentence a person can read.

	Raises. The sentence goes into Frappe's message log exactly as
	`frappe.throw` would put it there, so the web page and the logs are
	unaffected; the code travels on the exception and the wrapper puts it in the
	body.
	"""
	status, allowed = CODES.get(code, (None, ()))
	if status is None:
		# An unknown code is our bug, not the caller's. Refuse the request the
		# honest way rather than inventing a screen the app cannot show.
		frappe.log_error(f"field app: unknown refusal code {code!r}",
		                 "Field check-in error table")
		status, allowed, code = CODES["SERVER_ERROR"][0], (), "SERVER_ERROR"

	# Only the names this code declared. A stray value is dropped rather than
	# sent, because the app has no screen for it and because "values" is a
	# public body - anything that leaks does so here.
	body = {k: v for k, v in values.items() if k in allowed}

	raise FieldAppRefusal(message, code, status, body)


# Frappe names an error class in `exc_type`, and that name is part of what every
# existing caller already sees. One refusal class now answers eight statuses, so
# the name is reported the way Frappe would have reported it for that status
# rather than as our own class - nothing outside has to learn a new word.
_EXC_TYPE_FOR_STATUS = {
	401: "AuthenticationError",
	403: "PermissionError",
	404: "DoesNotExistError",
	429: "TooManyRequestsError",
	500: "ServerError",
}


def exc_type_for(exc, status):
	if isinstance(exc, FieldAppRefusal):
		return _EXC_TYPE_FOR_STATUS.get(status, "ValidationError")
	return type(exc).__name__


def code_and_values(exc, status):
	"""The code to put in the body for an exception the wrapper caught.

	Anything raised through `refuse` says what it is. Anything else - a stray
	`frappe.throw`, Frappe's own rate limiter, a crash - gets the safest code
	that matches its status, so a body never goes out without one.
	"""
	code = getattr(exc, "alvoraa_code", None)
	if code:
		return code, getattr(exc, "alvoraa_values", None) or {}

	if status >= 500:
		return "SERVER_ERROR", {}
	if status == 429:
		# Frappe's own limiter answers before our code runs. Its remaining
		# window is the only thing the app can act on.
		limiter = getattr(frappe.local, "rate_limiter", None)
		wait = getattr(limiter, "reset", None) if limiter else None
		return "TOO_MANY_TRIES", ({"retry_after_s": int(wait)} if wait else {})
	if status in (401, 403, 404, 409, 410, 422, 426):
		# A refusal with a status but no code is a gap in our own table. It is
		# answered, and it is logged as a place in the code with no values, so
		# the gap is found before an app version relies on it.
		frappe.log_error(
			f"field app: refusal with status {status} carried no code "
			f"({type(exc).__name__})", "Field check-in error table")
	return "INVALID_REQUEST", {}


# ── the app's build number ───────────────────────────────────────────────────
#
# The phone sends `X-Alvoraa-App-Version: MAJOR.MINOR.PATCH`. No header at all
# means the web check-in page, which has no version and is always allowed.
#
# Raising MIN_APP_VERSION locks out every phone below it, so it is raised only
# for a security reason and only after the replacement has been available for
# 90 days (OPS-48). The pilot is before the first store release, so the rule is
# written down here and enforced by CI later, in step 6.

MIN_APP_VERSION = "1.0.0"

# Builds that must never be served again whatever their number - a build that
# shipped with a mistake we cannot fix from the server.
DENIED_APP_VERSIONS = frozenset()

VERSION_HEADER = "X-Alvoraa-App-Version"

# Longer than "999.999.999" and its spare room. Anything longer is not a version
# and is refused before it is parsed, so a long string cannot be used to make the
# server work.
MAX_VERSION_CHARS = 24


def parse_version(raw):
	"""Three numbers, or None. "1.10.0" is newer than "1.9.0", which is the
	whole reason this is not a string comparison."""
	if not isinstance(raw, str):
		return None
	raw = raw.strip()
	if not raw or len(raw) > MAX_VERSION_CHARS:
		return None
	parts = raw.split(".")
	if len(parts) != 3:
		return None
	try:
		numbers = tuple(int(p) for p in parts)
	except (TypeError, ValueError):
		return None
	if any(n < 0 for n in numbers):
		return None
	return numbers


def check_app_version():
	"""Refuse a build too old to be trusted. Called by every device endpoint.

	No header means the web check-in page. It has no version, it is served from
	our own site, and it is always allowed - that is what keeps AC-35 true.
	"""
	try:
		raw = frappe.get_request_header(VERSION_HEADER)
	except Exception:
		# No request at all: a test, a console, a background job.
		return

	if raw is None:
		return

	sent = parse_version(raw)
	if sent is None or raw.strip() in DENIED_APP_VERSIONS or sent < parse_version(MIN_APP_VERSION):
		refuse("APP_TOO_OLD",
		       _("Please update the app to carry on."),
		       min_version=MIN_APP_VERSION)


# ── the plan gate, with a code the app can read ──────────────────────────────

def requires_field_app_plan(fn):
	"""Refuse the endpoint when the tenant's plan does not include field check-in.

	A wrapper of our own rather than a change to `subscription.requires_feature`:
	28 vendor endpoints plus the goals, analytics and payroll endpoints share
	that decorator and slice 016 has only just settled them. This one asks the
	same question of the same function, throws the same sentence with the same
	403, and adds the `FEATURE_OFF` code the app needs to pick its screen.

	It sets `__alvoraa_feature__` for the same reason the shared one does: the
	entitlement tests walk every endpoint looking for that attribute, and a gate
	nobody can see is a gate nobody can check.
	"""
	import functools

	from alvoraa_portal.subscription import FEATURES, has_feature

	@functools.wraps(fn)
	def wrapper(*args, **kwargs):
		if not has_feature("field_checkin"):
			label = FEATURES.get("field_checkin", {}).get("label", "field_checkin")
			refuse("FEATURE_OFF", _("{0} is not included in your plan.").format(label))
		return fn(*args, **kwargs)

	wrapper.__alvoraa_feature__ = "field_checkin"
	return wrapper
