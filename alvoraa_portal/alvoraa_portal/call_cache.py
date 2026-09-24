"""A memo that lives for exactly one call and dies with it.

Slice 044/042 R1. Measured on a 981-person tenant, one `get_home` asked the
database the **same question with the same parameters** four or five times: the
caller's holiday-list assignment twice, their company twice, their direct
reports two or three times, and for an HR caller the whole permitted-employee
list twice. Nothing about the answer can change inside one call, because
nothing inside the call writes.

**Why this is not a cache.** A cache keeps an answer for later. This keeps an
answer for the next line of the same function and then throws it away, in a
`finally`, whether the call returned or raised. There is no key that outlives
the call, nothing in redis, nothing on the session, and nothing a second
request can read.

That distinction is the whole point, and it is a permission rule, not a taste.
`permitted_companies()` and `permitted_employees()` decide who a person may
see. If either were remembered across requests, an HR person removed from a
company at 10:00 would keep seeing it until the memo expired. Asking once per
call is free; asking once per hour is a permission bug. Within one call there
is no window at all - the answer cannot change between two lines that do not
write.

**Outside a call, this does nothing.** `once()` with no cache open simply runs
the function. That is what makes it safe to put inside a shared helper like
`hr_api._own_upcoming_holidays`: every other caller of that helper behaves
exactly as it did before, and a test that calls it twice still sees two
queries.
"""

import frappe

_SLOT = "alvoraa_call_cache"


def open_cache():
	"""Start a memo for this call. Always paired with `close_cache` in a `finally`."""
	setattr(frappe.local, _SLOT, {})


def close_cache():
	"""Throw the memo away. Safe to call when none was opened."""
	if hasattr(frappe.local, _SLOT):
		try:
			delattr(frappe.local, _SLOT)
		except AttributeError:
			setattr(frappe.local, _SLOT, None)


def is_open():
	return isinstance(getattr(frappe.local, _SLOT, None), dict)


def once(key, fn):
	"""Run `fn` the first time this key is asked for in this call, then reuse it.

	With no cache open, `fn` runs every time - no memo, no behaviour change.
	"""
	cache = getattr(frappe.local, _SLOT, None)
	if not isinstance(cache, dict):
		return fn()
	if key not in cache:
		cache[key] = fn()
	return cache[key]


def holiday_list_for(employee, as_on):
	"""ERPNext's `get_holiday_list_for_employee`, asked once per call.

	Frappe HR answers this from Holiday List Assignment, which costs two or
	three statements (the employee's assignment, their company, the company's
	assignment). Home asks it twice - once for the attendance-gap rule and once
	for the holidays card - and both want the same answer for the same day.
	"""
	from erpnext.setup.doctype.employee.employee import get_holiday_list_for_employee

	return once(
		("holiday_list", employee, str(as_on)),
		lambda: get_holiday_list_for_employee(employee, raise_exception=False, as_on=as_on),
	)
