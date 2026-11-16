"""Slice 082: /event-form/<route> - the attendee's phone page for one CRM form.

Public. Draws a published, clean CRM Lead form at phone sizes (16 px inputs,
48 px targets, no Discard), with the phone's own fonts and nothing from another
host (OPS-13, PRIV-6). The organiser box and the QR card are put in the page
only for a signed-in Sales Manager or System Manager (SEC-7) - never hidden with
CSS. Every closed, draft, unsafe or unknown link gives guests the same card
(SEC-4). Never cached (OPS-22).
"""

import json

import frappe
import frappe.sessions
from frappe import _

from alvoraa_portal import event_form as ef

no_cache = 1


def get_context(context):
	context.no_cache = 1
	context.no_header = 1
	context.no_sidebar = 1
	context.no_breadcrumbs = 1
	try:
		frappe.local.response_headers["Cache-Control"] = "no-store"
		frappe.local.response_headers["X-Robots-Tag"] = "noindex, nofollow"
	except Exception:  # a header is a nicety; the page still answers
		pass

	route = frappe.form_dict.get("route") or ""
	state = ef.form_state(route)
	form, problem = state["form"], state["problem"]
	organiser = frappe.session.user != "Guest" and bool(ef.ORGANISER_ROLES & set(frappe.get_roles()))

	context.route = route
	context.csrf_token = frappe.sessions.get_csrf_token() if frappe.session.user != "Guest" else ""
	context.closed = form is None or (problem is not None and not organiser)
	context.show_form = not context.closed and problem in (None, "draft")
	context.box = None
	if context.closed:
		return context

	context.title = form.title or ""
	context.intro = form.introduction_text or ""
	context.button = form.button_label or _("Send")
	# The organiser's own success message, or ours naming the event (the brief's WOW).
	context.thanks = form.success_message or _("Thank you. Your details are saved for {0}.").format(form.title or "")
	context.thanks_hi = "" if form.success_message else f"धन्यवाद। आपकी जानकारी {form.title or ''} के लिए सहेज ली गई है।"
	context.fields = [_field(row, df) for row, df in state["fields"]]

	if organiser:
		address = frappe.utils.get_url("/event-form/" + route)
		context.box = {
			"problem": problem,
			"label": state["label"],
			"address": address,
			"extras": state["extras"],
			"qr": _qr(address) if problem is None else None,
			"organiser_name": frappe.defaults.get_global_default("company") or "",
		}
	return context


def _field(row, df) -> dict:
	"""What the template needs to draw one row. Never a default value (PRIV-3a)."""
	kind = df.fieldtype
	field = {
		"name": df.fieldname,
		"label": row.label or df.label or df.fieldname,
		"english": ef.english(row.label or df.label or df.fieldname),
		"required": bool(row.reqd or df.reqd or df.fieldname == ef.CONSENT_EVENT),
		"description": row.description or "",
		"kind": "text",
		"options": [],
		"maxlength": ef.TEXT_MAX if kind in ef.TEXT else ef.DATA_MAX,
	}
	if kind in ef.TEXT:
		field["kind"] = "textarea"
	elif kind == "Check":
		field["kind"] = "check"
	elif kind == "Select":
		options = [o for o in (df.options or "").split("\n") if o]
		field["options"] = [{"value": o, "main": o.rsplit(" · ", 1)[0] if " · " in o else o,
		                     "hint": ("· " + o.rsplit(" · ", 1)[1]) if " · " in o else ""} for o in options]
		field["kind"] = "radio" if len(options) <= 6 else "select"
	elif kind == "Int":
		field["kind"] = "int"
	elif kind == "Float":
		field["kind"] = "float"
	elif kind == "Date":
		field["kind"] = "date"
	elif kind == "Phone" or df.options == "Phone":
		field["kind"] = "tel"
	elif df.options == "Email":
		field["kind"] = "email"
	return field


def _qr(address: str) -> str:
	"""The QR matrix as rows of 0/1, drawn into the card by the browser (where a
	Devanagari font exists). PyQRCode ships with Frappe for two-factor sign-in."""
	import pyqrcode

	code = pyqrcode.create(address, error="M")
	return json.dumps(["".join(str(cell) for cell in line) for line in code.code])
