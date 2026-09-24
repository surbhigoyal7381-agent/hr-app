"""AI lead intake (slice 043, slice one): enquiry emails into Frappe CRM leads.

No screens in slice one. The pieces:

    guards.py   which mailboxes may be read at all (Email Account and User rules)
    text.py     turning an email into the short, redacted text the model sees
    rules.py    cheap checks that skip auto-replies, newsletters and internal mail
    extract.py  the one model call, and the code that checks what came back
    intake.py   the five-minute sweep that ties it together and makes the lead
    setup.py    switching the feature on or off for one tenant

The design and its reasons are in docs/slices/043-ai-email-leads/.
"""
