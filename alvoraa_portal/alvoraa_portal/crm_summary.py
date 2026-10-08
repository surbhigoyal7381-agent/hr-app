"""Slice 057 (C): the founders' daily pipeline summary, on WhatsApp and by email.

Settings are per tenant, in site config, and empty by default (= off, no query):

    crm_founder_summary = {"whatsapp": ["<number with country code>"], "email": ["<founder email>"],
                           "template": "<WhatsApp Templates name>"}

WhatsApp goes out as an approved Meta template: outside the 24 hours after a
founder last wrote to the number, Meta delivers nothing else, and a plain text
fails later and silently. So the email copy always goes too.

Counts only. No customer's name, number or email, and no user's name, is ever in
the summary - it goes to Meta and to inboxes outside the CRM.

Runs daily at 09:00 (hooks.py). To send one now: Scheduled Job Type
"crm_summary.send_daily" -> Execute.
"""
import json

import frappe
from frappe import _
from frappe.query_builder.functions import Count, Sum
from frappe.utils import add_days, format_date, fmt_money, get_url, now_datetime, today

from alvoraa_portal.crm_steps import LEAD_TYPE_FIELD

CLOSED = ("Won", "Lost")
MAX_VAR = 300   # characters per template variable; Meta caps the whole body at 1,024


def send_daily():
	conf = frappe.conf.get("crm_founder_summary") or {}
	if not (conf.get("whatsapp") or conf.get("email")):
		return
	if "crm" not in frappe.get_installed_apps():
		return
	values = build()
	if conf.get("whatsapp") and conf.get("template"):
		for number in conf["whatsapp"]:
			_send_whatsapp(number, conf["template"], values)
	if conf.get("email"):
		frappe.sendmail(recipients=conf["email"], subject=_("CRM summary, {0}").format(values["1"]),
						message=email_html(values))


def _send_whatsapp(number, template, values):
	try:
		frappe.get_doc({
			"doctype": "WhatsApp Message",
			"type": "Outgoing",
			"to": number,
			"content_type": "text",
			"message_type": "Template",
			"use_template": 1,
			"template": template,
			"body_param": json.dumps(values),
		}).insert(ignore_permissions=True)
	except Exception:  # noqa: BLE001 - one number failing must not stop the others or the email
		frappe.log_error(title="CRM founders' summary: WhatsApp send failed",
						 message=frappe.get_traceback(with_context=False))


def _grouped(doctype, status_doctype, status_field):
	"""{(lead type, status): count} for open records. One query."""
	closed = frappe.get_all(status_doctype, filters={"type": ["in", CLOSED]}, pluck=status_field)
	t = frappe.qb.DocType(doctype)
	has_type = frappe.get_meta(doctype).has_field(LEAD_TYPE_FIELD)
	kind = t[LEAD_TYPE_FIELD] if has_type else t.status
	q = frappe.qb.from_(t).select(kind, t.status, Count("*")).groupby(kind, t.status)
	if closed:
		q = q.where(t.status.notin(closed))
	if doctype == "CRM Lead":
		q = q.where(t.converted == 0)    # a converted lead is counted as its deal
	return {((k if has_type else "") or _("No type"), s): n for k, s, n in q.run()}


def build():
	"""The six template variables, each one line. Eight small queries, whatever the volume."""
	since = add_days(now_datetime(), -1)
	lead = frappe.qb.DocType("CRM Lead")
	has_type = frappe.get_meta("CRM Lead").has_field(LEAD_TYPE_FIELD)
	kind = lead[LEAD_TYPE_FIELD] if has_type else lead.status
	new = (frappe.qb.from_(lead).select(kind, Count("*")).where(lead.creation >= since).groupby(kind)).run()
	new_by_type = {((k if has_type else "") or _("No type")): n for k, n in new}

	steps = _grouped("CRM Lead", "CRM Lead Status", "lead_status")
	steps.update(_grouped("CRM Deal", "CRM Deal Status", "deal_status"))

	task = frappe.qb.DocType("CRM Task")
	overdue = (frappe.qb.from_(task).select(Count("*"))
			   .where(task.status.notin(["Done", "Canceled"]))
			   .where(task.due_date < now_datetime())).run()[0][0]

	won_statuses = frappe.get_all("CRM Deal Status", filters={"type": "Won"}, pluck="deal_status") or ["Won"]
	deal = frappe.qb.DocType("CRM Deal")
	won_count, won_value = (frappe.qb.from_(deal).select(Count("*"), Sum(deal.deal_value))
							.where(deal.status.isin(won_statuses))
							.where(deal.closed_date >= add_days(today(), -1))).run()[0]

	return {
		"1": format_date(today()),
		"2": _line(new_by_type),
		"3": _steps_line(steps),
		"4": str(overdue or 0),
		"5": _("{0} worth {1}").format(won_count or 0, fmt_money(won_value or 0,
														currency=frappe.db.get_default("currency") or "INR")),
		"6": get_url("/crm/leads"),
	}


def _line(by_type):
	total = sum(by_type.values())
	if not total:
		return "0"
	parts = ", ".join(f"{k} {n}" for k, n in sorted(by_type.items()))
	return _clip(f"{total} ({parts})")


def _steps_line(steps):
	if not steps:
		return _("none open")
	types = {}
	for (k, s), n in sorted(steps.items()):
		types.setdefault(k, []).append(f"{s} {n}")
	return _clip("; ".join(f"{k}: {', '.join(v)}" for k, v in types.items()))


def _clip(text):
	# A template variable may not hold a line break, a tab or four spaces in a row.
	text = " ".join(str(text).split())
	return text if len(text) <= MAX_VAR else text[: MAX_VAR - 1] + "…"


def email_html(v):
	rows = [
		(_("New leads, last 24 hours"), v["2"]),
		(_("Open, by step"), v["3"]),
		(_("Overdue tasks"), v["4"]),
		(_("Deals won since yesterday"), v["5"]),
	]
	body = "".join(f"<p><b>{frappe.utils.escape_html(k)}:</b> {frappe.utils.escape_html(x)}</p>" for k, x in rows)
	return f"{body}<p><a href=\"{v['6']}\">{_('Open the CRM')}</a></p>"
