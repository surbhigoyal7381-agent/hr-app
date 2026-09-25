"""Rate limits keyed on a hash, never on the secret (slice 013).

Frappe's `rate_limit(key=...)` reads `form_dict[key]` and writes the value into
the Redis key **in clear** - the step-1 probe saw `rl:<cmd>:<value>:<seconds>`.
So a limit keyed on the device secret or the joining code would write every
secret into Redis and into any error about it. The decorator below hashes the
argument into a form field of its own first, runs Frappe's limiter on that, and
removes the field afterwards. The field names contain "key", so Frappe's own
Error Log redaction masks their values as well.

`ip_based` is off: one phone behind a changing mobile IP is still one phone,
and 400 phones behind one depot's Wi-Fi are 400 phones, not one caller (AC-140).

Moved here from `field_app_join` in step 4 so the punch and the start screen in
`field_checkin.py` can use it too without an import cycle.
"""

import functools
import hashlib

import frappe
from frappe import _
from frappe.rate_limiter import rate_limit

from alvoraa_portal.field_app_errors import refuse

# The form fields the limiter reads. Their NAMES contain "key", so Frappe's own
# Error Log redaction masks their values (utils/logger.py sanitized_dict); the
# values are hashes, never the code or the secret.
CODE_KEY = "code_hash_key"
PHONE_KEY = "phone_hash_key"
HR_KEY = "hr_user_key"
# A signed-in employee asking about their own records (step 6, US-28).
SELF_KEY = "self_user_key"
# Signing in with email and password (ALV-128): the email, hashed, so an
# address is never written into a Redis key; and the two-factor step's
# one-time id, hashed the same way.
SIGNIN_KEY = "signin_email_key"
OTP_KEY = "signin_otp_key"

WINDOW_SECONDS = 60 * 60


def _hash(token: str) -> str:
	"""Store only the hash, the way an API secret should be kept.

	If a table or a Redis dump ever leaks, the secrets in it cannot be replayed.
	"""
	return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _limited(field, source, limit):
	"""Rate limit an endpoint on one of its arguments, hashed.

	`source` is the argument's name ("token", "code") or "user" for the signed-in
	desk user. An empty or malformed argument is hashed as the empty string, so
	every such caller shares one bucket and the endpoint itself still gives the
	answer it always gave (a missing secret is `NOT_SET_UP`, AC-3).
	"""
	def decorator(fn):
		limited = rate_limit(key=field, limit=limit, seconds=WINDOW_SECONDS,
		                     methods=["POST"], ip_based=False)(fn)

		@functools.wraps(fn)
		def wrapper(*args, **kwargs):
			value = frappe.session.user if source == "user" else kwargs.get(source)
			if source == "email" and isinstance(value, str):
				# One bucket per address however it is typed.
				value = value.strip().lower()
			hashed = _hash(value if isinstance(value, str) else "")
			frappe.form_dict[field] = hashed
			try:
				return limited(*args, **kwargs)
			except frappe.RateLimitExceededError:
				# Frappe's decorator says how many, not how long. The app needs
				# the wait (section 7.1), which is what is left of the window.
				frappe.clear_messages()
				refuse("TOO_MANY_TRIES",
				       _("Too many tries. Please wait a while and try again."),
				       retry_after_s=_seconds_left(hashed, WINDOW_SECONDS))
			finally:
				frappe.form_dict.pop(field, None)

		# So a test can read every endpoint's limit off the function itself and
		# pin the whole table (step 6, US-25): what it is keyed on, and how many.
		wrapper.__alvoraa_limit__ = (field, source, limit, WINDOW_SECONDS)
		return wrapper

	return decorator


def _limited_by_address(limit):
	"""Rate limit an endpoint per caller address (ALV-128, password sign-in only).

	Every other app endpoint is keyed on a phone or a code, never on the
	address, because 400 phones behind one depot Wi-Fi are 400 callers
	(AC-140). Signing in is different: the email is the thing an attacker
	varies, so a per-email limit alone would let one machine try a password
	against every address in turn. The address is the one thing it cannot vary
	cheaply. Set high enough that a depot signing everybody in on day one is
	not refused; Frappe's own lockout still counts every wrong password.
	"""
	def decorator(fn):
		limited = rate_limit(limit=limit, seconds=WINDOW_SECONDS, methods=["POST"],
		                     ip_based=True)(fn)

		@functools.wraps(fn)
		def wrapper(*args, **kwargs):
			try:
				return limited(*args, **kwargs)
			except frappe.RateLimitExceededError:
				frappe.clear_messages()
				refuse("TOO_MANY_TRIES",
				       _("Too many tries. Please wait a while and try again."),
				       retry_after_s=_seconds_left(getattr(frappe.local, "request_ip", "") or "",
				                                   WINDOW_SECONDS))

		wrapper.__alvoraa_address_limit__ = (limit, WINDOW_SECONDS)
		return wrapper

	return decorator


def _seconds_left(hashed, window):
	"""How long until Frappe's window for this key opens again. The key is the
	one `rate_limit` builds (rl:<cmd>:<identity>:<seconds>); step 1 saw it."""
	try:
		ttl = frappe.cache.ttl(frappe.cache.make_key(f"rl:{frappe.form_dict.cmd}:{hashed}:{window}"))
		return int(ttl) if ttl and int(ttl) > 0 else window
	except Exception:
		return window
