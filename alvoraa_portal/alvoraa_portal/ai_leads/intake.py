"""New emails on opted-in mailboxes into CRM Leads.

Each email is handed over as soon as Frappe pulls it (on_new_email); the five-minute
sweep is the safety net and the retry. Both go through the same steps:

For each email, in order, and stopping at the first that applies:

1. claim it - one call-log row per email, unique, written BEFORE anything else, so a
   retried or overlapping job never makes two leads (OPS-4);
2. already linked to a document -> skipped;
3. a cheap rule says skip (auto-reply, newsletter, internal, HR mail) -> skipped;
4. the sender already has a lead -> the email is attached to that lead, no model call;
5. today's cap is reached -> a lead marked Needs Review, not read by the model;
6. otherwise one model call; its answer is checked field by field; then
   - sure it is an enquiry and nothing was doubted -> lead, status New
   - sure it is NOT an enquiry -> no lead, the email stays in the mailbox
   - anything in between -> lead, status Needs Review.

A model failure is retried on the next sweeps; after three tries or 24 hours the email
becomes a Needs Review lead with only the header filled (SEC-26), so nothing is lost.

Runs on every tenant every five minutes and returns before touching the database
unless this site has switched the feature on.
"""
import time
from contextlib import contextmanager

import frappe
from frappe.utils import add_to_date, cint, escape_html, flt, get_datetime, now_datetime, today

import alvoraa_portal.ai_leads.extract as extract
import alvoraa_portal.ai_leads.guards as guards
import alvoraa_portal.ai_leads.research as research
import alvoraa_portal.ai_leads.rules as rules
import alvoraa_portal.ai_leads.text as text_mod

LOG = "Alvoraa AI Call Log"
SERVER_FLAG = "alvoraa_server_write"
NEEDS_REVIEW = "Needs Review"
BATCH = 25            # emails per sweep, all mailboxes together (OPS-2)
MAX_ATTEMPTS = 3
STALE_HOURS = 24
DEFAULT_CAP = 200     # D-5
CEILING = 500         # Alvoraa's own limit, whatever the tenant sets
TIME_LIMIT = 240      # seconds; the cron job's own timeout is 300 and it shares the worker
STUCK_MINUTES = 15    # a "Queued" row older than this was interrupted (a restart, a timeout)
CAP = "cap reached"   # sentinel: stop this sweep, nothing more today


def enabled(conf=None):
    conf = conf if conf is not None else frappe.conf
    return cint(conf.get("ai_lead_intake_enabled")) == 1


def daily_cap(conf=None):
    conf = conf if conf is not None else frappe.conf
    return min(cint(conf.get("ai_lead_intake_daily_cap") or DEFAULT_CAP), CEILING)


def _ready():
    """Is intake on for this site? Cheapest check first."""
    if not enabled():
        return False
    if "crm" not in frappe.get_installed_apps():
        return False
    if not frappe.get_meta("Email Account").has_field(guards.INTAKE_FIELD):
        return False
    from alvoraa_portal.subscription import has_feature
    return bool(has_feature("crm_ai_intake"))


def on_new_email(doc, method=None):
    """Communication after_insert: hand a newly pulled email to the intake at once,
    so a lead appears seconds after Frappe fetches the mail, not at the next sweep.

    Only queues a job; the model is never called inside the mail pull. The sweep
    stays as the safety net: if this job is lost, the email is still unclaimed and
    the next sweep takes it. The claim row stops the two ever making two leads.
    """
    if doc.sent_or_received != "Received" or doc.communication_medium != "Email":
        return
    if doc.communication_type != "Communication" or not doc.email_account:
        return
    if not enabled():                      # a site-config read, no query
        return
    if not frappe.get_meta("Email Account").has_field(guards.INTAKE_FIELD):
        return
    if not frappe.db.get_value("Email Account", doc.email_account, guards.INTAKE_FIELD):
        return
    frappe.enqueue(
        "alvoraa_portal.ai_leads.intake.process_new",
        queue="short",
        communication=doc.name,
        enqueue_after_commit=True,
        job_id=f"ai-lead-intake::{doc.name}",
        deduplicate=True,
    )


def pull_intake_mailboxes():
    """Every minute: fetch new mail for intake mailboxes only, so an enquiry is read
    about a minute after it is sent. Frappe's own fetch of every mailbox stays at
    ten minutes. Returns at once, with no query, on a site where intake is off.

    Queued exactly as Frappe queues its own fetch - same queue, same job name - so the
    two never read one mailbox at the same time.
    """
    if not enabled():
        return
    if not frappe.get_meta("Email Account").has_field(guards.INTAKE_FIELD):
        return
    from frappe.email.doctype.email_account.email_account import pull_from_email_account
    from frappe.utils.background_jobs import get_jobs

    names = frappe.get_all(
        "Email Account",
        filters={guards.INTAKE_FIELD: 1, "enable_incoming": 1, "awaiting_password": 0},
        pluck="name",
    )
    if not names:
        return
    queued = get_jobs(site=frappe.local.site, key="job_name").get(frappe.local.site) or []
    for name in names:
        job_name = f"pull_from_email_account|{name}"
        if job_name not in queued:
            frappe.enqueue(pull_from_email_account, "short", job_name=job_name, email_account=name)


def process_new(communication):
    """Background job queued by on_new_email: the same checks as the sweep, for one email."""
    if not _ready():
        return None
    row = frappe.db.get_value(
        "Communication", communication,
        ["name", "email_account", "communication_date"], as_dict=True)
    if not row or not row.email_account:
        return None
    acc = frappe.db.get_value(
        "Email Account",
        {"name": row.email_account, guards.INTAKE_FIELD: 1, "enable_incoming": 1},
        ["name", "email_id", guards.SINCE_FIELD], as_dict=True)
    if not acc or not guards.account_still_ok(acc.name):          # V-7
        return None
    since = acc.get(guards.SINCE_FIELD)
    if since and row.communication_date and get_datetime(row.communication_date) < get_datetime(since):
        return None
    if frappe.db.exists(LOG, {"communication": communication}):
        return None
    return safely(communication, acc)


def sweep():
    """Scheduler entry point (hooks.py, every five minutes). The safety net behind
    on_new_email, and the retry of failed emails."""
    if not _ready():
        return

    deadline = time.monotonic() + TIME_LIMIT
    budget = BATCH - retry_failed(BATCH, deadline)
    accounts = frappe.get_all(
        "Email Account",
        filters={guards.INTAKE_FIELD: 1, "enable_incoming": 1},
        fields=["name", "email_id", guards.SINCE_FIELD],
    )
    for acc in accounts:
        if budget <= 0 or time.monotonic() > deadline:
            break
        if not guards.account_still_ok(acc.name):      # V-7
            continue
        done = process_account(acc, budget, deadline)
        if done == CAP:
            break
        budget -= done


def unclaimed(account_name, since, limit):
    """The oldest emails on this mailbox that no sweep has claimed yet.

    The exclusion is in the query itself. Filtering afterwards meant a mailbox
    whose oldest emails were all handled was never read again (review P1-2).
    Dated by the email, not by when Frappe pulled it, so a first pull of old
    mail does not count as new (review P2).
    """
    comm = frappe.qb.DocType("Communication")
    log = frappe.qb.DocType(LOG)
    rows = (
        frappe.qb.from_(comm)
        .left_join(log).on(log.communication == comm.name)
        .select(comm.name)
        .where(comm.email_account == account_name)
        .where(comm.sent_or_received == "Received")
        .where(comm.communication_medium == "Email")
        .where(comm.communication_type == "Communication")
        .where(comm.communication_date >= since)
        .where(log.name.isnull())
        .orderby(comm.communication_date)
        .limit(limit)
    ).run(pluck=True)
    return rows


def process_account(acc, limit, deadline=None):
    since = acc.get(guards.SINCE_FIELD) or now_datetime()
    count = 0
    for name in unclaimed(acc.name, since, limit):
        if deadline and time.monotonic() > deadline:
            break
        if safely(name, acc) == CAP:
            return CAP
        count += 1
    return count


def safely(comm_name, acc, log_name=None):
    """One email, isolated. Whatever breaks, the email ends as Failed - never stuck
    at Queued with nobody told (review P1-1) - and the sweep moves on."""
    try:
        return process_one(comm_name, acc, log_name=log_name)
    except Exception as e:  # noqa: BLE001 - one bad email must not stop the rest
        frappe.db.rollback()
        name = log_name or frappe.db.get_value(LOG, {"communication": comm_name}, "name")
        if name:
            log = frappe.get_doc(LOG, name)
            finish(log, "Failed", reason=f"error: {type(e).__name__}", attempts=cint(log.attempts) + 1)
        return None


def retry_failed(limit, deadline=None):
    """Failed or interrupted emails: try again, or after three tries / 24 hours make the
    header-only lead (SEC-26). Returns how many it actually worked on."""
    fields = ["name", "communication", "email_account", "attempts", "creation"]
    # Emails only: a forwarded WhatsApp row (slice 057) has no mailbox to read again.
    email = ["communication", "is", "set"]
    rows = frappe.get_all(LOG, filters=[["outcome", "=", "Failed"], email], fields=fields,
                          order_by="creation asc", limit=limit)
    stuck_before = add_to_date(now_datetime(), minutes=-STUCK_MINUTES)
    rows += frappe.get_all(LOG, filters=[["outcome", "=", "Queued"], ["modified", "<", stuck_before], email],
                           fields=fields, order_by="creation asc", limit=limit)
    stale_before = add_to_date(now_datetime(), hours=-STALE_HOURS)
    worked = 0
    for row in rows[:limit]:
        if deadline and time.monotonic() > deadline:
            break
        acc = frappe.db.get_value("Email Account", row.email_account, ["name", "email_id"], as_dict=True)
        if not acc or not guards.account_still_ok(acc.name):
            continue
        worked += 1
        if cint(row.attempts) >= MAX_ATTEMPTS or get_datetime(row.creation) <= stale_before:
            try:
                log = frappe.get_doc(LOG, row.name)
                comm = _comm(row.communication)
                if comm:
                    lead = _existing_lead(comm.sender) or make_lead(comm, None, [], "unavailable", acc, log)
                    finish(log, "Needs review", reason="AI unavailable; made from the header only", lead=lead)
            except Exception:  # noqa: BLE001
                frappe.db.rollback()
        else:
            safely(row.communication, acc, log_name=row.name)
    return worked


def claim(comm_name, account_name):
    """The idempotency row. None if another run already has this email."""
    log = frappe.new_doc(LOG)
    log.communication = comm_name
    log.email_account = account_name
    log.outcome = "Queued"
    log.flags[SERVER_FLAG] = True
    try:
        log.insert(ignore_permissions=True)
    except (frappe.DuplicateEntryError, frappe.UniqueValidationError):
        frappe.db.rollback()
        return None
    frappe.db.commit()
    return log.name


def finish(log, outcome, reason=None, lead=None, **fields):
    log.outcome = outcome
    if reason is not None:
        log.reason = (reason or "")[:140]
    if lead:
        log.lead = lead
    for k, v in fields.items():
        log.set(k, v)
    log.flags[SERVER_FLAG] = True
    log.save(ignore_permissions=True)
    frappe.db.commit()
    return lead


def _comm(name):
    return frappe.db.get_value(
        "Communication", name,
        ["name", "subject", "sender", "sender_full_name", "text_content", "content",
         "reference_doctype", "reference_name"],
        as_dict=True)


def _existing_lead(sender):
    return frappe.db.get_value("CRM Lead", {"email": sender}, "name") if sender else None


def process_one(comm_name, acc, log_name=None, conf=None):
    conf = conf if conf is not None else frappe.conf
    if log_name is None:
        log_name = claim(comm_name, acc.name)
        if not log_name:
            return None
    log = frappe.get_doc(LOG, log_name)
    comm = _comm(comm_name)
    if not comm:
        return finish(log, "Skipped", reason="email no longer exists")
    if comm.reference_doctype and comm.reference_name:
        return finish(log, "Skipped", reason="already linked to a document")

    body = text_mod.plain_text(comm.text_content, comm.content)
    reason = rules.skip_reason(comm.subject, comm.sender, body, acc.email_id,
                               ignore=conf.get("ai_lead_intake_ignore") or [])
    if reason:
        return finish(log, "Skipped", reason=reason)

    existing = _existing_lead(comm.sender)
    if existing:
        link_email(comm.name, existing)
        add_note(existing, "Another email from this sender",
                 f"<p>Subject: {escape_html(comm.subject or '')}</p><p>Attached to this lead by AI lead intake; "
                 "not read by the AI because the sender already has a lead.</p>")
        return finish(log, "Lead updated", lead=existing)

    if frappe.db.count(LOG, {"called": 1, "creation": [">=", today()]}) >= daily_cap(conf):
        # AC-30: over the cap, emails wait for tomorrow. Release the claim so the
        # next day's sweep picks this one up, and stop the sweep. A flood of spam
        # becomes a queue, not a pile of junk leads (review P2).
        frappe.db.delete(LOG, {"name": log.name})
        frappe.db.commit()
        return CAP

    prompt = text_mod.for_model(comm.subject, comm.sender_full_name, comm.sender, body)
    try:
        data, model, tokens_in, tokens_out = extract.call_model(prompt, conf)
        fields, flags = extract.clean(data, prompt)
    except extract.ExtractionError as e:
        return finish(log, "Failed", reason=e.kind, attempts=cint(log.attempts) + 1)

    verdict = extract.decide(fields, flags,
                             flt(conf.get("ai_lead_intake_auto_accept") or 0.85),
                             flt(conf.get("ai_lead_intake_not_lead") or 0.85))
    common = dict(called=1, model=model, prompt_version=extract.PROMPT_VERSION,
                  confidence=round(fields["confidence"] * 100, 1),
                  input_tokens=tokens_in, output_tokens=tokens_out,
                  attempts=cint(log.attempts) + 1)
    if verdict == "not_lead":
        # A fixed reason, not the model's words: the log stays content-free (SEC-17).
        return finish(log, "Not a lead", reason="the AI judged it not an enquiry", **common)
    log.update(common)
    lead = make_lead(comm, fields, flags, verdict, acc, log)
    finish(log, "Lead created" if verdict == "lead" else "Needs review",
           reason="; ".join(flags)[:140] if flags else None, lead=lead, **common)
    if research.enabled(conf) and research.wanted(fields, verdict):
        research.enqueue(log.name)          # its own job: the lead never waits for it
    return lead


# ── The lead ─────────────────────────────────────────────────────────────────

def _match(doctype, value):
    if not value:
        return None
    return frappe.db.get_value(doctype, {"name": ["like", value.strip()]}, "name")


def _is_mobile(phone):
    d = text_mod.digits(phone)
    return (len(d) == 10 and d[0] in "6789") or (len(d) == 12 and d.startswith("91") and d[2] in "6789")


def service_user_email():
    """The one account every AI-made lead and note is created by (01c: never Administrator)."""
    site = frappe.local.site or ""
    domain = site if "." in site else f"{site}.example.com"
    return f"ai-leads@{domain}"


@contextmanager
def _as_service_user():
    user = frappe.conf.get("ai_lead_intake_user") or service_user_email()
    before = frappe.session.user
    if user and frappe.db.exists("User", user):
        frappe.set_user(user)
    try:
        yield
    finally:
        frappe.set_user(before)


def make_lead(comm, fields, flags, verdict, acc, log):
    """A CRM Lead in Frappe CRM's own form. `fields` is None when the AI did not read it."""
    f = fields or {}
    name_parts = (comm.sender_full_name or "").split()
    local = (comm.sender or "").split("@")[0]
    lead = frappe.new_doc("CRM Lead")
    lead.first_name = f.get("first_name") or (name_parts[0] if name_parts else local) or "Unknown"
    lead.last_name = f.get("last_name") or (name_parts[-1] if len(name_parts) > 1 else "")
    lead.email = comm.sender            # always the header, never the model
    for field in ("organization", "job_title", "website"):
        if f.get(field):
            lead.set(field, f[field])
    if f.get("phone"):
        lead.set("mobile_no" if _is_mobile(f["phone"]) else "phone", f["phone"])
    if frappe.db.exists("CRM Lead Source", "Email"):
        lead.source = "Email"
    industry = _match("CRM Industry", f.get("industry"))
    if industry:
        lead.industry = industry
    territory = _match("CRM Territory", f.get("city")) or _match("CRM Territory", f.get("country"))
    if territory:
        lead.territory = territory
    review = verdict != "lead"
    lead.status = NEEDS_REVIEW if review and frappe.db.exists("CRM Lead Status", NEEDS_REVIEW) else "New"
    owner = frappe.conf.get("ai_lead_intake_owner")
    if owner and frappe.db.exists("User", owner):
        lead.lead_owner = owner
    meta = frappe.get_meta("CRM Lead")
    for field, value in (("alvoraa_ai_created", 1),
                         ("alvoraa_ai_needs_review", 1 if review else 0),
                         ("alvoraa_ai_confidence", round(f.get("confidence", 0) * 100, 1) if fields else 0),
                         ("alvoraa_ai_model", log.get("model") or ""),
                         ("alvoraa_ai_prompt_version", extract.PROMPT_VERSION if fields else ""),
                         ("alvoraa_ai_mailbox", acc.name),
                         ("alvoraa_ai_communication", comm.name)):
        if meta.has_field(field):
            lead.set(field, value)
    lead.flags.ignore_permissions = True
    with _as_service_user():
        lead.insert(ignore_permissions=True)
    link_email(comm.name, lead.name)
    add_note(lead.name, "What they asked for (AI summary)", _note_html(f, flags, verdict))
    return lead.name


def _note_html(f, flags, verdict):
    parts = []
    if verdict == "cap":
        parts.append("<p>Not read by the AI: today's limit of emails was reached. "
                     "Only the sender's name and address are filled.</p>")
    elif verdict == "unavailable":
        parts.append("<p>Not read by the AI: the AI service could not be reached. "
                     "Only the sender's name and address are filled.</p>")
    else:
        if f.get("requirement"):
            parts.append(f"<p>{escape_html(f['requirement'])}</p>")
        if f.get("reasons"):
            items = "".join(f"<li>{escape_html(r)}</li>" for r in f["reasons"])
            parts.append(f"<p><b>Why it looked like a lead</b></p><ul>{items}</ul>")
        if flags:
            items = "".join(f"<li>{escape_html(x)}</li>" for x in flags)
            parts.append(f"<p><b>Checked by code</b></p><ul>{items}</ul>")
        parts.append(f"<p><i>Filled from the email by AI (confidence {round(f.get('confidence', 0) * 100)}%). "
                     "Check it against the email before relying on it.</i></p>")
    if verdict != "lead":
        parts.append("<p><b>Needs review.</b> Open the email on this lead, correct anything wrong, "
                     "then set the status to New, or to Junk if it is not an enquiry.</p>")
    return "".join(parts)


def link_email(comm_name, lead_name):
    frappe.db.set_value("Communication", comm_name,
                        {"reference_doctype": "CRM Lead", "reference_name": lead_name},
                        update_modified=False)


def add_note(lead_name, title, html):
    note = frappe.new_doc("FCRM Note")
    note.title = title
    note.content = html
    note.reference_doctype = "CRM Lead"
    note.reference_docname = lead_name
    note.flags.ignore_permissions = True
    with _as_service_user():
        note.insert(ignore_permissions=True)
