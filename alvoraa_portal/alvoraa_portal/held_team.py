"""Slice 086: a manager sends the missing times for their direct reports' held days to HR.

Two calls, and nothing else. `held_days` reads the Held days of the caller's direct reports that nobody
has asked HR about yet. `send_held` files up to 50 of them in one POST, one request per day, each through
`attendance_correction.raise_for_report` - the door that already owns the reason rule, the filing window,
the tenant switch and the stamp - so nothing about a request is decided here. HR decides each request as
before (087). No DocType, field, setting or job is added.

What this file adds is only what was missing: the scope check on every row (SEC-1), two refusals for a
time that cannot be right (not yet happened; In/Out that disagrees with the time), and the lock that makes
a double send file one request (SEC-5).
"""

import frappe
from frappe import _
from frappe.utils import add_days, cint, get_datetime, getdate, now_datetime, nowdate

import alvoraa_portal.attendance_correction as ac
import alvoraa_portal.held_day as held_day
import alvoraa_portal.punch_fix as punch_fix
import hrms.alvoraa_hr_core.access as access
from alvoraa_portal.field_app_limits import SELF_KEY, _limited
from alvoraa_portal.payroll_rules_apply import shift_day  # the one working-day rule (ALV-402)

REQUEST = "Attendance Request"
ATTENDANCE = "Attendance"
CHECKIN = "Employee Checkin"
MAX_ROWS = 50
PERIOD_DAYS = 92          # the existing look-back of the team page
REASON_MAX = 500
KEYS = ("employee", "date", "time", "in_or_out", "reason")   # the only five things a row may say

NOT_YOURS = _("Not sent. This person is not one of your direct reports.")


def _team():
	"""(manager's Employee, their direct reports) or (None, []) when this caller has no team to act for.
	One reading of the reporting line, used for the list and for every row of a send (SEC-1)."""
	me = ac._employee_for(frappe.session.user)
	if not me or not ac.manager_on_behalf_on():
		return None, []
	return me, ac._reports_to(me.name, deep=False)


def _open_filters(employee, date):
	"""A request that is still waiting for HR on this day: a draft that is not Declined or Withdrawn
	(087 lets a declined or withdrawn draft be replaced, so it does not hide the day)."""
	return {"employee": employee, "from_date": getdate(date), "docstatus": 0,
	        "alvoraa_review_status": ("not in", list(ac.DONE_STATES))}


@frappe.whitelist()
def held_days(day=None, start=0):
	"""The Held days of the caller's direct reports that have no open request, one day at a time.

	Read-only; nothing here is cached. Queries: attendance, open requests, shifts, punches - four, however
	many rows, and the Held filter runs on the Attendance query before any punch is read (OPS-53)."""
	me, direct = _team()
	if not me:
		return {"nobody": True, "rows": [], "days": [], "total": 0, "hold_on": False}
	if not direct:
		return {"nobody": True, "rows": [], "days": [], "total": 0, "hold_on": held_day._switch_on(me.company)}

	today = getdate(nowdate())
	held = frappe.get_all(
		ATTENDANCE,
		filters={"employee": ("in", direct), "status": held_day.HELD, "docstatus": 1,
		         "attendance_date": ("between", [add_days(today, -PERIOD_DAYS), today])},
		fields=["employee", "employee_name", "attendance_date", "shift"],
		order_by="attendance_date desc, employee_name asc", limit_page_length=2000)
	waiting = {(r.employee, str(r.from_date)) for r in frappe.get_all(
		REQUEST, filters={"employee": ("in", direct), "docstatus": 0,
		                  "alvoraa_review_status": ("not in", list(ac.DONE_STATES))},
		fields=["employee", "from_date"], limit_page_length=5000)}
	held = [r for r in held if (r.employee, str(r.attendance_date)) not in waiting]

	counts = {}
	for r in held:
		counts[str(r.attendance_date)] = counts.get(str(r.attendance_date), 0) + 1
	days = [{"date": d, "count": n} for d, n in counts.items()]   # latest first, as read
	chosen = "all" if day == "all" else (str(getdate(day)) if day else (days[0]["date"] if days else None))
	scope = held if chosen == "all" else [r for r in held if str(r.attendance_date) == chosen]
	begin = max(0, cint(start))
	page = scope[begin:begin + MAX_ROWS]

	return {"nobody": False, "hold_on": held_day._switch_on(me.company), "day": chosen, "days": days,
	        "total": len(scope), "start": begin, "page_length": MAX_ROWS, "rows": _shaped(page)}


def _shaped(page):
	"""What the screen draws for each row, and nothing more (PRIV-3): the name, the day, the shift and the
	counted punches as a time and where it came from. No GPS, photo, login, email or reason."""
	if not page:
		return []
	emps = sorted({r.employee for r in page})
	dates = sorted(str(r.attendance_date) for r in page)
	punches = {}
	for p in frappe.get_all(
			CHECKIN,
			filters={"employee": ("in", emps), "skip_auto_attendance": 0, "offshift": 0,
			         "time": ("between", [f"{dates[0]} 00:00:00", f"{add_days(dates[-1], 1)} 23:59:59"])},
			fields=["employee", "time", "log_type", "device_id", "shift_start", punch_fix.ADDED],
			order_by="time asc", limit_page_length=20000):
		punches.setdefault((p.employee, shift_day(p)), []).append(p)

	shift_names = sorted({r.shift for r in page if r.shift})
	shifts = {s.name: s for s in frappe.get_all(
		"Shift Type", filters={"name": ("in", shift_names)}, fields=["name", "start_time", "end_time"])} \
		if shift_names else {}

	out = []
	for r in page:
		day = str(r.attendance_date)
		logs = punches.get((r.employee, day), [])
		sh = shifts.get(r.shift)
		out.append({
			"employee": r.employee, "employee_name": r.employee_name, "date": day,
			"shift": {"start": held_day._as_time(sh.start_time).strftime("%H:%M"),
			          "end": held_day._as_time(sh.end_time).strftime("%H:%M")} if sh else None,
			"punches": [{"time": get_datetime(p.time).strftime("%H:%M"),
			             "m": punch_fix._mins(p.time, day), "source": punch_fix._source(p)} for p in logs],
			# The page's one guess, for the question only: a lone OUT means the arrival is missing. The
			# server never reads it - it works the kind out from the time (`send_held`).
			"single_is_out": len(logs) == 1 and logs[0].log_type == "OUT",
		})
	return out


def _refusal_of(error):
	"""The words an error already carries, with no markup."""
	frappe.clear_messages()
	return frappe.utils.strip_html_tags(str(error)).strip()


@frappe.whitelist(methods=["POST"])
@_limited(SELF_KEY, "user", limit=30, window=3600)
def send_held(rows=None):
	"""File up to 50 held-day times for the caller's direct reports, one request per day.

	Each row says five things: `employee`, `date`, `time`, `in_or_out`, `reason`. Anything else on a row
	is not read. Each row runs in its own savepoint, so a refused row leaves no document and the others
	still go. The answer has one entry per row, with a sentence when it was not sent."""
	rows = frappe.parse_json(rows) if isinstance(rows, str) else rows
	if not isinstance(rows, list) or not rows:
		frappe.throw(_("There is nothing to send. Type a time and a reason for at least one day."))
	if len(rows) > MAX_ROWS:
		frappe.throw(_("{0} at most in one send.").format(MAX_ROWS))
	me, direct = _team()
	if not me:
		frappe.throw(_("You cannot send held days for anybody. Your organisation may not let managers, "
		               "or you may not be an active employee. Ask HR to fix these days."), frappe.PermissionError)
	team = set(direct)

	clean = []
	for r in rows:
		r = r if isinstance(r, dict) else {}
		clean.append({k: (r.get(k) if isinstance(r.get(k), str) else "") for k in KEYS})
	# Sorted by person and day, so two sends that overlap take their locks in the same order.
	order = sorted(range(len(clean)), key=lambda i: (clean[i]["employee"], clean[i]["date"]))
	answers, seen, stopped = {}, set(), False
	faults = []
	for i in order:
		row = clean[i]
		answer = {"employee": row["employee"], "date": row["date"], "ok": False}
		answers[i] = answer
		if stopped:
			answer["sentence"] = _("Not sent. The office was busy with something else. Reload the page, then send again.")
			continue
		key = (row["employee"], row["date"])
		if key in seen:
			answer["sentence"] = _("Not sent. Already waiting with HR.")
			continue
		seen.add(key)
		if row["employee"] not in team:
			# One fixed sentence and no name, whoever the row names (SEC-1).
			access.log_refusal("SEC-1", "held_team.send_held", "Employee", row["employee"][:140])
			answer["sentence"] = NOT_YOURS
			continue
		frappe.db.savepoint("held_row")
		try:
			answer["request"] = _file_one(row, len(clean))
			answer["ok"] = True
		except (frappe.ValidationError, frappe.PermissionError) as e:
			frappe.db.rollback(save_point="held_row")
			answer["sentence"] = _("Not sent.") + " " + _refusal_of(e)
		except (frappe.QueryTimeoutError, frappe.QueryDeadlockError) as e:
			# A lock wait: stop here, keep what already went, say so for the rest (OPS-56).
			frappe.db.rollback(save_point="held_row")
			frappe.clear_messages()
			answer["sentence"] = _("Not sent. The office was busy with something else. Reload the page, then send again.")
			faults.append(type(e).__name__)
			stopped = True
		except Exception as e:
			frappe.db.rollback(save_point="held_row")
			frappe.clear_messages()
			answer["sentence"] = _("Could not send this one. Nothing was filed for it. Try again.")
			faults.append(type(e).__name__)

	results = [answers[i] for i in range(len(clean))]
	sent = sum(1 for a in results if a["ok"])
	if faults:
		# One entry for the whole call: counts, the manager's id and the kind of fault. Never a reason,
		# a time or a name (PRIV-2, OPS-60).
		frappe.log_error(
			title="Held days send: a fault",
			message="manager %s, %d rows, %d sent, %d not sent, first fault %s" % (
				me.name, len(results), sent, len(results) - sent, faults[0]))
	return {"results": results, "sent": sent, "not_sent": len(results) - sent}


def _file_one(row, n):
	"""One row, inside its savepoint. Returns the request's name or throws the sentence."""
	employee, date = row["employee"], row["date"]
	try:
		day = getdate(date)
	except Exception:
		frappe.throw(_("That day was not understood. Reload the page and try again."))
	if day > getdate(nowdate()):
		frappe.throw(_("You cannot send a time for a day that has not happened yet."))
	if not row["time"]:
		frappe.throw(_("Enter the time first."))
	if len(row["reason"]) > REASON_MAX:
		frappe.throw(_("Keep the reason to {0} characters.").format(REASON_MAX))
	if row["in_or_out"] not in ("IN", "OUT"):
		frappe.throw(_("Say whether the missing punch was in or out."))

	# THE LOCK (SEC-5). Two sends at once for one day: the second waits here until the first has filed,
	# then must SEE the first one's request. A plain read can miss it on MariaDB's default isolation, so
	# the duplicate check is a locking read too. Both are read as the latest committed or own rows.
	att = punch_fix.day_row(employee, date, for_update=True)
	if not att or att.status != held_day.HELD:
		frappe.throw(_("This day is no longer held. A machine punch or HR may have fixed it. "
		               "Reload the page to see where it stands."))
	if frappe.db.get_value(REQUEST, _open_filters(employee, date), "name", for_update=True):
		frappe.throw(_("Already waiting with HR."))

	try:
		log_type, _label, when = punch_fix.derive(employee, date, row["time"])
	except Exception:
		frappe.throw(_("That time was not understood. Enter it like 18:30."))
	shown = when.strftime("%H:%M")
	if when > now_datetime():
		frappe.throw(_("It is only {0} now, so {1} has not happened yet. Enter the time the person really left.").format(
			now_datetime().strftime("%H:%M"), shown))
	if log_type != row["in_or_out"]:
		now_is, sent_is = (_("an arrival") if log_type == "IN" else _("a leaving"),
		                   _("an arrival") if row["in_or_out"] == "IN" else _("a leaving"))
		frappe.throw(_("{0} fits as {1}, not {2}, next to the punches already on this day. Press Change if the "
		               "missing punch is the other one.").format(shown, now_is, sent_is))

	reason = row["reason"].strip()
	# The "One of n" line goes AFTER a blank line, so it is never part of the reason that 088 prints.
	# A blank reason is passed on as it is: `raise_for_report` refuses it with its own sentence.
	explanation = (reason + "\n\n" + _("One of {0} days sent together.").format(n)) if reason and n > 1 else reason
	out = ac.raise_for_report(employee=employee, from_date=date, explanation=explanation,
	                          missing_time=row["time"], missing_log=log_type)
	return out["name"]
