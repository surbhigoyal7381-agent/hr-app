"""The field app's housekeeping and its numbers (slice 013, step 6).

Three jobs live here, because they share one thing: none of them is about a
person, and every line they write is a count.

**The daily clean-up (US-21).** Codes that have run out are marked "Ran out"
and their hash is retired, through the code record's own rules, so a code that
nobody used can never be used later. Codes that never set up a phone are
deleted twelve months after they ended (the user's decision Q-1: "keep codes
that made a phone; delete the rest after 12 months"). A self-check counts any
code or phone that has stopped but still holds a live secret - there should be
none - and raises a technical alert if it finds one. Phones and acknowledgement
rows are NOT deleted here: their retention waits for counsel (spec section 16.6,
C-3), and the phone record's own controller refuses every delete.

**The daily counts (US-22).** One row per day of how the app was used - codes
made and used, punches saved and refused, app starts, refusals by code and by
app version - with no name, employee ID, phone model, code or secret anywhere
in it. The request outcomes are counted in Redis as they happen (one INCR per
request, keyed on the day, the endpoint, the outcome and the app version) and
folded into the row by the clean-up job the next morning. The code lifecycle
numbers come from the code table itself.

**The threshold alert (US-19, N5).** Refused code checks - not recognised, run
out, used, cancelled - are also counted per clock hour. When the count passes
the threshold, every HR Manager of the tenant is told once, through the same
desk-bell mechanism as the other alerts (`field_app_alerts`), with the number
and nothing else: no code, no address, no name.

Two rules hold for everything in this file:

  * **Counting never changes an answer.** A Redis that is down, a key that
    cannot be read - the request is answered exactly as before and the count is
    simply missing. Counts are for watching a pilot, not for pay.
  * **The job never leaves an exception.** A failed scheduled job is written to
    the Scheduled Job Log WITH the local variables of every frame, and a `doc`
    local here holds an employee's name. So a failure is caught, logged as a
    place in the code with no values, and reported as a technical alert by its
    title - which the control plane's health pull already collects.

Technical alerts (spec section 10, T1-T4) are Error Log rows with a fixed
title. That is deliberate and not a shortcut: the control plane's daily health
pull (`health.py`) collects Error Log TITLES and counts from every tenant and
never the message, so a title is exactly the channel that reaches Alvoraa
without moving any tenant data.
"""

import json

import frappe
from frappe.query_builder.functions import Count
from frappe.utils import add_days, add_months, cint, now, now_datetime, today

from alvoraa_portal import field_app_alerts as alerts
from alvoraa_portal.alvoraa_portal.doctype.alvoraa_app_invite.alvoraa_app_invite import (
	INVITE,
	SERVER_FLAG,
	WAITING,
)
from alvoraa_portal.alvoraa_portal.doctype.alvoraa_field_app_daily_count.alvoraa_field_app_daily_count import (
	DAILY_COUNT,
)

# Not imported from field_checkin: that module imports this one, for the counting.
DEVICE = "Alvoraa Field Device"

# A phone in one of these states holds a live secret on purpose (section 5.1).
LIVE_PHONE_STATES = ("Active", "Pending", "Consent not given")

# The refusals that mean "the code the phone sent does not work".
BAD_CODE_OUTCOMES = ("QR_NOT_RECOGNISED", "QR_EXPIRED", "QR_USED", "QR_CANCELLED")
CODE_ENDPOINTS = ("check_code", "refuse_code", "join_with_code")

# N5: the starting threshold (AC-120, "50 an hour"), to be measured at the pilot.
BAD_CODE_ALERT_THRESHOLD = 50

# ── the Redis counters ───────────────────────────────────────────────────────
#
# Key: alvoraa_fa:<day>:<endpoint>:<outcome>:<app version>, prefixed by Frappe
# with the site's database name, so tenants never share a counter. Each key
# lives three days - long enough for the job that folds it into the day's row
# to run late, or twice, and still find it.

COUNTER_PREFIX = "alvoraa_fa"
COUNTER_TTL_SECONDS = 3 * 24 * 60 * 60
HOUR_TTL_SECONDS = 2 * 60 * 60

# What a phone that sent no usable version header is counted as.
NO_VERSION = "web"


def record_outcome(endpoint, outcome, app_version=None):
	"""One request has ended: count it. Called by the request wrappers.

	`outcome` is "ok" or the refusal code. Never raises, and never writes to
	the database on its own - except the one case where a threshold is
	crossed and HR has to be told, which commits the alert it queued.
	"""
	try:
		_bump(f"{today()}:{endpoint}:{outcome}:{_version_label(app_version)}")
		if endpoint in CODE_ENDPOINTS and outcome in BAD_CODE_OUTCOMES:
			_bad_code_seen()
	except Exception as exc:
		# A count that cannot be kept is a missing number, not a broken punch.
		# The class name only: the exception's text could quote a key.
		frappe.logger("alvoraa_portal.field_app").warning(
			f"field app: could not count an outcome ({type(exc).__name__})")


def _version_label(app_version):
	"""The version as a key part: a well-formed version, or one word.

	The header is the phone's to write, so it is not trusted into a key or a
	JSON field unless it parses as three numbers (section 6)."""
	from alvoraa_portal.field_app_errors import parse_version

	if not app_version:
		return NO_VERSION
	return app_version if parse_version(app_version) else "bad"


def _bump(suffix, ttl=COUNTER_TTL_SECONDS):
	key = frappe.cache.make_key(f"{COUNTER_PREFIX}:{suffix}")
	n = frappe.cache.incr(key)
	if n == 1:
		frappe.cache.expire(key, ttl)
	return cint(n)


def _bad_code_seen():
	"""N5: the threshold, per clock hour, fired once at the crossing."""
	hour = now_datetime().strftime("%Y-%m-%d-%H")
	n = _bump(f"bad_codes:{hour}", ttl=HOUR_TTL_SECONDS)
	if n == BAD_CODE_ALERT_THRESHOLD + 1:
		alerts.too_many_bad_codes(n)
		# This runs inside a refusal, after the wrapper's rollback; the alert
		# it queued must not wait for a commit that is never coming.
		frappe.db.commit()


def counters_for(day):
	"""The day's request counters: {endpoint: {outcome: {version: n}}}."""
	prefix = f"{COUNTER_PREFIX}:{day}:"
	out = {}
	for raw in frappe.cache.get_keys(prefix):
		key = raw.decode() if isinstance(raw, bytes) else str(raw)
		tail = key.split(prefix, 1)[1] if prefix in key else ""
		parts = tail.split(":")
		if len(parts) != 3:
			continue
		endpoint, outcome, version = parts
		value = frappe.cache.get(raw)
		value = value.decode() if isinstance(value, bytes) else value
		out.setdefault(endpoint, {}).setdefault(outcome, {})[version] = cint(value)
	return out


def _sum(counters, endpoints=None, outcomes=None, not_outcomes=()):
	total = 0
	for endpoint, by_outcome in counters.items():
		if endpoints is not None and endpoint not in endpoints:
			continue
		for outcome, by_version in by_outcome.items():
			if outcomes is not None and outcome not in outcomes:
				continue
			if outcome in not_outcomes:
				continue
			total += sum(by_version.values())
	return total


# ── the daily job ────────────────────────────────────────────────────────────

# Rows saved per commit (AC-130). And a ceiling on batches, so a row that a
# save somehow leaves unchanged can never keep the job in a loop.
BATCH = 500
MAX_BATCHES = 200

# Q-1: codes that never set up a phone go twelve months after they ended.
DELETE_AFTER_MONTHS = 12

# AC-134: the daily counts are kept for thirteen months.
KEEP_COUNTS_MONTHS = 13

LOGGER = "alvoraa_portal.field_app"
JOB_FAILED_TITLE = "Field app clean-up failed"


def daily():
	"""scheduler_events daily. Safe to run twice: a second run finds nothing to
	expire or delete and writes the same numbers again. The log line holds
	counts only (AC-127)."""
	result = {"codes_expired": 0, "live_hashes": 0, "codes_deleted": 0,
	          "counts_written": 0, "counts_deleted": 0, "failed": False}
	try:
		result["codes_expired"] = expire_codes()
		result["live_hashes"] = live_hashes_on_stopped_records()
		result["codes_deleted"] = delete_old_codes()
		result["counts_written"] = write_daily_counts(result)
		result["counts_deleted"] = purge_old_counts()
		frappe.db.commit()
	except Exception as exc:
		result["failed"] = True
		frappe.db.rollback()
		# Where, never with what. A re-raise would put every frame's local
		# variables - an invite's employee name among them - into the Scheduled
		# Job Log; the title here is the alert, and the health pull carries it.
		frappe.log_error(title=JOB_FAILED_TITLE, message=_code_places(exc))
	frappe.logger(LOGGER).info("field app clean-up: " + json.dumps(result))
	return result


def expire_codes():
	"""Waiting codes past their lifetime become "Ran out", hash retired (AC-126).

	Through the document, so the code record's own rules run - the retired
	hash is what lets E1 still say "this code has run out" rather than "not
	recognised". No employee lock is taken: this transaction only ever wants
	the code row, so it cannot form a cycle with a join, which locks the
	employee first and re-reads the code after its own lock.
	"""
	total = 0
	for _batch in range(MAX_BATCHES):
		names = frappe.get_all(
			INVITE, filters={"status": WAITING, "expires_at": ["<", now()]},
			pluck="name", order_by="expires_at asc", limit=BATCH)
		if not names:
			break
		for name in names:
			doc = frappe.get_doc(INVITE, name)
			if doc.status != WAITING:
				continue
			doc.status = "Ran out"
			doc.flags[SERVER_FLAG] = True
			doc.save(ignore_permissions=True)
			total += 1
		frappe.db.commit()
		if len(names) < BATCH:
			break
	return total


def live_hashes_on_stopped_records():
	"""The self-check (AC-128): a code that is not Waiting, or a phone that is
	not Active, Pending or not-yet-agreed, still holding a live hash. The
	count should be 0. Anything else is a technical alert, by title; the
	message names the rows (their names are random hashes, not people)."""
	Invite = frappe.qb.DocType(INVITE)
	codes = (
		frappe.qb.from_(Invite).select(Invite.name)
		.where(Invite.status != WAITING)
		.where(Invite.token_hash.isnotnull() & (Invite.token_hash != ""))
		.limit(BATCH)
	).run(pluck=True)
	Device = frappe.qb.DocType(DEVICE)
	phones = (
		frappe.qb.from_(Device).select(Device.name)
		.where(Device.status.notin(list(LIVE_PHONE_STATES)))
		.where(Device.token_hash.isnotnull() & (Device.token_hash != ""))
		.limit(BATCH)
	).run(pluck=True)
	n = len(codes) + len(phones)
	if n:
		frappe.log_error(
			title=f"Field app clean-up: {n} live secret(s) on stopped records",
			message="codes: " + ", ".join(codes) + "\nphones: " + ", ".join(phones))
	return n


def delete_old_codes():
	"""Q-1 (AC-129): codes that never set up a phone - cancelled, or run out -
	are deleted twelve months after they ended. A Used code is never touched:
	it is kept with the phone it let in. Permanently, so no copy of the row
	lands in Deleted Document; the code record's own `on_trash` allows only
	the server to do this."""
	cutoff = add_months(today(), -DELETE_AFTER_MONTHS)
	total = 0
	for _batch in range(MAX_BATCHES):
		ended = frappe.get_all(
			INVITE, filters={"status": "Cancelled", "cancelled_at": ["<", cutoff]},
			pluck="name", limit=BATCH)
		ran_out = frappe.get_all(
			INVITE, filters={"status": "Ran out", "expires_at": ["<", cutoff]},
			pluck="name", limit=BATCH)
		names = ended + ran_out
		if not names:
			break
		for name in names:
			doc = frappe.get_doc(INVITE, name)
			if doc.status not in ("Cancelled", "Ran out"):
				continue
			doc.flags[SERVER_FLAG] = True
			doc.delete(ignore_permissions=True, delete_permanently=True)
			total += 1
		frappe.db.commit()
		if len(names) < BATCH:
			break
	return total


def write_daily_counts(job_numbers=None, day=None):
	"""Yesterday's row (or `day`'s) from the counters and the code table;
	today's row gets the job's own numbers. Both are upserts, so a second run
	rewrites the same values. Returns how many rows were written."""
	day = day or add_days(today(), -1)
	_upsert_count_row(day, _numbers_for(day))
	written = 1
	if job_numbers is not None:
		_upsert_count_row(today(), {
			"codes_expired_by_job": job_numbers.get("codes_expired", 0),
			"codes_deleted_by_job": job_numbers.get("codes_deleted", 0),
			"live_hashes_found": job_numbers.get("live_hashes", 0),
		}, add=("codes_expired_by_job", "codes_deleted_by_job"))
		written += 1
	return written


def _numbers_for(day):
	"""Every column of one day's row, from the code table and the counters."""
	start = f"{day} 00:00:00"
	end = f"{add_days(day, 1)} 00:00:00"
	numbers = {
		"codes_made": _count_between(INVITE, "creation", start, end),
		"codes_used": _count_between(INVITE, "used_at", start, end),
		"codes_cancelled": _count_between(INVITE, "cancelled_at", start, end),
		"codes_ran_out": _count_between(INVITE, "expires_at", start, end, status="Ran out"),
	}
	counters = counters_for(day)
	if not counters:
		# The keys have expired (the job ran days late): keep whatever the
		# row already holds rather than overwrite it with zeros.
		return numbers
	numbers.update({
		"code_checks_refused": _sum(counters, CODE_ENDPOINTS, BAD_CODE_OUTCOMES),
		"not_me": _sum(counters, ("refuse_code",), ("ok",)),
		"app_starts": _sum(counters, ("field_status",), ("ok",)),
		"punches_saved": _sum(counters, ("field_checkin",), ("ok",)),
		"punches_refused": _sum(counters, ("field_checkin",),
		                        not_outcomes=("ok", "TOO_MANY_TRIES", "SERVER_ERROR")),
		"phones_removed": _sum(counters, ("remove_my_phone",), ("ok",)),
		"app_too_old": _sum(counters, outcomes=("APP_TOO_OLD",)),
		"rate_limited": _sum(counters, outcomes=("TOO_MANY_TRIES",)),
		"server_errors": _sum(counters, outcomes=("SERVER_ERROR",)),
		"detail": json.dumps(counters, sort_keys=True),
	})
	return numbers


def _count_between(doctype, field, start, end, **equals):
	Table = frappe.qb.DocType(doctype)
	column = Table[field]
	query = (frappe.qb.from_(Table).select(Count("*"))
	         .where(column >= start).where(column < end))
	for name, value in equals.items():
		query = query.where(Table[name] == value)
	return cint(query.run()[0][0])


def _upsert_count_row(day, values, add=()):
	"""Write one day's row, as the server. Columns in `add` accumulate (a
	second run adds its zero); every other column is set."""
	name = frappe.db.get_value(DAILY_COUNT, {"on_date": day}, "name")
	doc = frappe.get_doc(DAILY_COUNT, name) if name else frappe.new_doc(DAILY_COUNT)
	doc.on_date = day
	doc.job_ran_at = now_datetime()
	for field, value in values.items():
		if field in add:
			doc.set(field, cint(doc.get(field)) + cint(value))
		else:
			doc.set(field, value)
	doc.flags[SERVER_FLAG] = True
	doc.save(ignore_permissions=True)
	return doc.name


def purge_old_counts():
	"""AC-134: rows older than thirteen months go. Numbers only, no links."""
	cutoff = add_months(today(), -KEEP_COUNTS_MONTHS)
	n = frappe.db.count(DAILY_COUNT, {"on_date": ["<", cutoff]})
	if n:
		frappe.db.delete(DAILY_COUNT, {"on_date": ["<", cutoff]})
	return cint(n)


def _code_places(exc):
	from alvoraa_portal.field_checkin import _code_places
	return _code_places(exc)

