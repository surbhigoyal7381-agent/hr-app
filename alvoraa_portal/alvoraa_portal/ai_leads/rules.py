"""Emails that never reach the model.

Every check here is cheap and local, and runs before any paid call. A skipped email
stays in the mailbox as it always did; nothing is deleted. The reason is written to
the call log so a tenant can see why an email did not become a lead.

Pure function: pass in what it needs, get a reason back or None.
"""
import re

import alvoraa_portal.ai_leads.text as text_mod

# Senders that are machines, not people.
_MACHINE_LOCAL = re.compile(
    r"^(no-?reply|do-?not-?reply|donotreply|mailer-daemon|postmaster|bounces?|"
    r"notifications?|newsletters?|mailer|automailer)([._+-].*)?$",
    re.IGNORECASE,
)

# Subjects of auto-replies and bounces.
_AUTO_SUBJECT = re.compile(
    r"^(auto:|automatic reply|auto-?reply|out of (the )?office|undeliverable|"
    r"delivery status notification|mail delivery (failed|failure)|returned mail|read:)",
    re.IGNORECASE,
)

# Mail that belongs to HR or recruitment, never to a sales pipeline (SEC-8's
# per-email half). The mailbox rules already refuse HR mailboxes; this catches
# the odd HR email that lands in a sales one.
_HR_SUBJECT = re.compile(
    r"(pay ?slip|salary slip|salary certificate|leave application|attendance|"
    r"resignation|offer letter|appointment letter|job application|curriculum vitae|\bresume\b|\bcv\b)",
    re.IGNORECASE,
)


def skip_reason(subject, sender_email, body, mailbox_email, ignore=None):
    """Why this email is skipped, or None to send it on.

    `ignore` is the tenant's own list: whole addresses, or "@domain" entries.
    """
    sender = (sender_email or "").strip().lower()
    if "@" not in sender:
        return "no sender"
    local, domain = sender.rsplit("@", 1)

    if _MACHINE_LOCAL.match(local):
        return "automatic sender"
    if _AUTO_SUBJECT.match((subject or "").strip()):
        return "auto-reply or bounce"
    if domain and domain == text_mod.sender_domain(mailbox_email):
        return "internal sender"
    for entry in ignore or []:
        entry = (entry or "").strip().lower()
        if not entry:
            continue
        if entry.startswith("@") and domain == entry[1:]:
            return "on the ignore list"
        if entry == sender:
            return "on the ignore list"
    if _HR_SUBJECT.search(subject or ""):
        return "HR or recruitment mail"

    lower = (body or "").lower()
    if not lower.strip():
        return "empty email"
    if "unsubscribe" in lower and ("view in browser" in lower or "view this email" in lower
                                   or "manage your preferences" in lower):
        return "newsletter"
    return None
