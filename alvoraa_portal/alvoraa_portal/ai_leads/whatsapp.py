"""Slice 057 (B): a WhatsApp message forwarded by a listed salesperson becomes a CRM Lead.

The email intake (intake.py) is reused for everything that decides: the same kill
switch, feature, daily cap, redaction, model call, field checks and thresholds.
What is different here:

- Only numbers on this tenant's forwarder list count (site config
  `ai_lead_whatsapp_forwarders`, {"919800000001": "vinda@example.com"}). Every other
  message is left exactly as frappe_whatsapp stored it. Empty list = off.
- frappe_whatsapp does not check that a webhook call really came from Meta. So this
  does, with the X-Hub-Signature-256 header and the app secret on the WhatsApp
  Account, while Meta's request is still open. No valid signature, nothing happens.
- A forward carries no original sender. The model sees only the forwarded text -
  never the forwarder's number or WhatsApp name - and the lead never gets the
  forwarder's number, or CRM would attach every later forward to it.
- A WhatsApp message cannot be fetched again like a mailbox, so there is no retry:
  if the AI is unavailable or the cap is reached, the lead is made at once as
  Needs Review, with the message on its WhatsApp tab.
"""
import hashlib
import hmac
import re

import frappe
from frappe.utils import cint, escape_html, flt, get_fullname, today

import alvoraa_portal.ai_leads.extract as extract
import alvoraa_portal.ai_leads.intake as intake
import alvoraa_portal.ai_leads.text as text_mod

FORWARDERS = "ai_lead_whatsapp_forwarders"
SECRET_FIELD = "alvoraa_app_secret"      # Password custom field on WhatsApp Account (setup.py)
SUBJECT = "Forwarded WhatsApp message"
MIN_CHARS = 20                           # a "hi" or "ok" never reaches the model
_EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}")


def forwarders(conf=None):
	conf = conf if conf is not None else frappe.conf
	return {text_mod.digits(k): v for k, v in (conf.get(FORWARDERS) or {}).items()}


def on_whatsapp_message(doc, method=None):
	"""WhatsApp Message after_insert. Cheapest checks first; only queues a job."""
	if doc.type != "Incoming" or doc.content_type != "text":
		return
	if not intake.enabled():
		return
	if text_mod.digits(doc.get("from")) not in forwarders():
		return
	if not signature_ok(doc.whatsapp_account):
		frappe.log_error(title="AI lead intake: forwarded WhatsApp message without a valid Meta signature",
						 message=f"WhatsApp Message {doc.name} was ignored. Check the app secret on the WhatsApp Account.",
						 reference_doctype="WhatsApp Message", reference_name=doc.name)
		return
	frappe.enqueue("alvoraa_portal.ai_leads.whatsapp.process", queue="short", message=doc.name,
				   enqueue_after_commit=True, job_id=f"ai-lead-whatsapp::{doc.name}", deduplicate=True)


def signature_ok(account):
	"""Meta signs the raw request body with the app secret (HMAC-SHA256). Fails closed."""
	request = getattr(frappe.local, "request", None)
	if request is None or not account:
		return False
	if not frappe.get_meta("WhatsApp Account").has_field(SECRET_FIELD):
		return False
	secret = frappe.get_doc("WhatsApp Account", account).get_password(SECRET_FIELD, raise_exception=False)
	if not secret:
		return False
	sent = request.headers.get("X-Hub-Signature-256") or ""
	expected = "sha256=" + hmac.new(secret.encode(), request.get_data(), hashlib.sha256).hexdigest()
	return hmac.compare_digest(sent, expected)


def _ready():
	if not intake.enabled() or "crm" not in frappe.get_installed_apps():
		return False
	from alvoraa_portal.subscription import has_feature
	return bool(has_feature("crm_ai_intake"))


def process(message, conf=None):
	"""Background job: one forwarded message, at most one model call, at most one lead."""
	conf = conf if conf is not None else frappe.conf
	if not _ready():
		return None
	msg = frappe.db.get_value("WhatsApp Message", message, ["name", "from", "message", "type", "message_id"],
							  as_dict=True)
	if not msg or msg.type != "Incoming":
		return None
	forwarder = forwarders(conf).get(text_mod.digits(msg["from"]))
	if not forwarder:
		return None
	# Keyed on Meta's own message id, not our row: Meta delivers "at least once", and
	# frappe_whatsapp stores each delivery as a new row.
	log_name = claim(msg.message_id or msg.name)
	if not log_name:
		return None                      # Meta sent it twice, or another job has it
	try:
		return _process(msg, forwarder, frappe.get_doc(intake.LOG, log_name), conf)
	except Exception as e:  # noqa: BLE001 - ends as Failed, never stuck at Queued
		frappe.db.rollback()
		intake.finish(frappe.get_doc(intake.LOG, log_name), "Failed", reason=f"error: {type(e).__name__}",
					  attempts=1)
		return None


def claim(meta_id):
	log = frappe.new_doc(intake.LOG)
	log.whatsapp_message = meta_id
	log.outcome = "Queued"
	log.flags[intake.SERVER_FLAG] = True
	try:
		log.insert(ignore_permissions=True)
	except (frappe.DuplicateEntryError, frappe.UniqueValidationError):
		frappe.db.rollback()
		return None
	frappe.db.commit()
	return log.name


def _process(msg, forwarder, log, conf):
	body = (msg.message or "").strip()
	if len(body) < MIN_CHARS:
		return intake.finish(log, "Skipped", reason="too short to be an enquiry")

	email = _first_email(body)
	existing = intake._existing_lead(email)
	if existing:
		return _attach(existing, msg, forwarder, log)

	if frappe.db.count(intake.LOG, {"called": 1, "creation": [">=", today()]}) >= intake.daily_cap(conf):
		lead = make_lead(msg, forwarder, None, [], "cap", email, log)
		return intake.finish(log, "Needs review", reason="daily cap reached; not read by the AI", lead=lead)

	# No sender name, no number: only the forwarded words leave the tenant.
	prompt = text_mod.for_model(SUBJECT, "", "", body)
	try:
		data, model, tokens_in, tokens_out = extract.call_model(prompt, conf)
		fields, flags = extract.clean(data, prompt)
	except extract.ExtractionError as e:
		lead = make_lead(msg, forwarder, None, [], "unavailable", email, log)
		return intake.finish(log, "Needs review", reason=f"AI unavailable: {e.kind}", lead=lead, attempts=1)

	verdict = extract.decide(fields, flags,
							 flt(conf.get("ai_lead_intake_auto_accept") or 0.85),
							 flt(conf.get("ai_lead_intake_not_lead") or 0.85))
	log.update(dict(called=1, model=model, prompt_version=extract.PROMPT_VERSION,
					confidence=round(fields["confidence"] * 100, 1),
					input_tokens=tokens_in, output_tokens=tokens_out, attempts=1))
	if verdict == "not_lead":
		return intake.finish(log, "Not a lead", reason="the AI judged it not an enquiry")

	if _same_number(fields.get("phone"), msg["from"]):
		fields["phone"] = ""             # the forwarder's own number never goes on the lead
	existing = _lead_by_phone(fields.get("phone"))
	if existing:
		return _attach(existing, msg, forwarder, log)

	lead = make_lead(msg, forwarder, fields, flags, verdict, email, log)
	return intake.finish(log, "Lead created" if verdict == "lead" else "Needs review",
						 reason="; ".join(flags)[:140] if flags else None, lead=lead)


def _first_email(text):
	m = _EMAIL.search(text or "")
	return m.group(0).lower() if m else None


def _same_number(a, b):
	a, b = text_mod.digits(a), text_mod.digits(b)
	return bool(a and b) and a[-10:] == b[-10:]


def _lead_by_phone(phone):
	d = text_mod.digits(phone)[-10:]
	if len(d) < 10:
		return None
	found = frappe.get_all("CRM Lead", or_filters=[["mobile_no", "like", f"%{d}"], ["phone", "like", f"%{d}"]],
						   pluck="name", limit=1)
	return found[0] if found else None


def _forwarded_by(forwarder, number):
	d = text_mod.digits(number)
	return f"{get_fullname(forwarder)} (+{d[:2]} {d[2:4]}…)"


def _link(msg, lead):
	frappe.db.set_value("WhatsApp Message", msg.name,
						{"reference_doctype": "CRM Lead", "reference_name": lead}, update_modified=False)


def _attach(lead, msg, forwarder, log):
	_link(msg, lead)
	intake.add_note(lead, "Another forwarded WhatsApp message",
					f"<p>Forwarded on WhatsApp by {escape_html(_forwarded_by(forwarder, msg['from']))}. "
					"Attached to this lead because the email address or phone number in it matches. "
					"See the WhatsApp tab.</p>")
	return intake.finish(log, "Lead updated", lead=lead)


def make_lead(msg, forwarder, fields, flags, verdict, email, log):
	"""A CRM Lead in CRM's own form, owned by the forwarder. `fields` is None when the AI did not read it."""
	f = fields or {}
	lead = frappe.new_doc("CRM Lead")
	lead.first_name = f.get("first_name") or "WhatsApp enquiry"
	lead.last_name = f.get("last_name") or ""
	if email:
		lead.email = email               # found in the text by a plain pattern, never by the model
	for field in ("organization", "job_title", "website"):
		if f.get(field):
			lead.set(field, f[field])
	if f.get("phone"):
		lead.set("mobile_no" if intake._is_mobile(f["phone"]) else "phone", f["phone"])
	if frappe.db.exists("CRM Lead Source", "WhatsApp"):
		lead.source = "WhatsApp"
	industry = intake._match("CRM Industry", f.get("industry"))
	if industry:
		lead.industry = industry
	territory = intake._match("CRM Territory", f.get("city")) or intake._match("CRM Territory", f.get("country"))
	if territory:
		lead.territory = territory
	review = verdict != "lead"
	lead.status = intake.NEEDS_REVIEW if review and frappe.db.exists("CRM Lead Status", intake.NEEDS_REVIEW) else "New"
	if frappe.db.get_value("User", forwarder, "enabled"):
		lead.lead_owner = forwarder
	meta = frappe.get_meta("CRM Lead")
	for field, value in (("alvoraa_ai_created", 1),
						 ("alvoraa_ai_needs_review", 1 if review else 0),
						 ("alvoraa_ai_confidence", round(f.get("confidence", 0) * 100, 1) if fields else 0),
						 ("alvoraa_ai_model", log.get("model") or ""),
						 ("alvoraa_ai_prompt_version", extract.PROMPT_VERSION if fields else "")):
		if meta.has_field(field):
			lead.set(field, value)
	with intake._as_service_user():
		lead.insert(ignore_permissions=True)
	_link(msg, lead.name)

	head = f"<p>Forwarded on WhatsApp by {escape_html(_forwarded_by(forwarder, msg['from']))}. " \
		   "The message is on this lead's WhatsApp tab.</p>"
	if fields is None:
		why = "today's limit of AI reads was reached" if verdict == "cap" else "the AI service could not be reached"
		body = (f"<p>Not read by the AI: {why}. Nothing is filled in.</p>"
				"<p><b>Needs review.</b> Read the message, fill in the lead, then set the status to New, "
				"or to Junk if it is not an enquiry.</p>")
	else:
		body = intake._note_html(f, flags, verdict).replace("the email", "the forwarded message")
	intake.add_note(lead.name, "Forwarded on WhatsApp (AI summary)", head + body)
	return lead.name
