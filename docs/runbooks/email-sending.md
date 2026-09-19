# Outgoing email

How mail leaves the platform, and the three things that go wrong the first time.

Set up 18 September 2026.

---

## The shape of it

| Direction | Who does it | Notes |
|---|---|---|
| Sending | **Brevo**, `smtp-relay.brevo.com:587`, STARTTLS | Signs as `alvoraa.co` |
| Receiving | **Cloudflare Email Routing** | Forwards to a real inbox. Cannot send |

Sender address is `support@alvoraa.co`. Replies reach a real inbox through the
Cloudflare forward, which is why it is used in preference to `no-reply@`.

DNS on the domain: one SPF record covering both Cloudflare and Brevo, Brevo's two
DKIM selectors (`brevo1`, `brevo2`), Cloudflare's DKIM, and DMARC at `p=quarantine`
reporting to an address we read.

---

## Three traps

### 1. A saved Email Account beats the server settings

`bench set-config -g mail_server` and friends are **ignored** on any site that has an
enabled `Email Account` record. On `alvoraa.co` that record is `Alvoraa HR Admin`.

Symptom: mail sends perfectly, from the wrong address, and the relay's log is empty.
Read the message headers — `Return-Path` names the server that really carried it.

A site with no Email Account does fall back to the server settings.

### 2. Brevo's IP allow-list reports as a credentials error

```
smtplib.SMTPAuthenticationError: (525, b'5.7.1 Unauthorized IP address')
```

The key is fine. The server is not on Brevo's authorised IP list. Add it under
**SMTP & API → Authorised IPs**. The server's address is in `deploy/server.env`.

Leave the allow-list switched on. A stolen key is then useless anywhere else.

### 3. Frappe re-issues EHLO after AUTH, and Brevo drops the login

```
smtplib.SMTPSenderRefused: (502, b'5.7.0 Please authenticate first', ...)
```

The same credentials work from plain Python. The difference is in
`frappe/email/smtp.py`: after logging in, Frappe sends `EHLO` again to refresh the
server's capabilities. Brevo treats that as a fresh conversation and forgets the
authentication.

Frappe ships a switch for it:

```
bench set-config -g smtp_no_ehlo_after_auth 1
```

---

## Before switching email on

`mute_emails` was `1` across the whole bench until this date. Anything the product
tried to send while muted is **still queued**, and unmuting sends all of it at once.

There were 507 stale messages on the demo site and 2 on the live site. They were
deleted rather than sent — weeks-old notices confuse real people, and a burst of
hundreds is the fastest way to get a new relay account flagged as a spammer.

**Check the queue before unmuting, not after:**

```sql
SELECT status, COUNT(*) FROM `tabEmail Queue` GROUP BY status;
```

---

## Proving it works

1. Send one message and check the `Email Queue` row reaches `status = Sent` with a
   null `error`.
2. Open the received mail's original and look for three PASS lines. **DKIM must show
   `alvoraa.co`, not the relay's own domain** — that is alignment, and DNS alone
   cannot confirm it.
3. Check the relay's own log. It separates "Frappe never sent it" from "it was sent
   and not delivered", which the other two checks cannot.

A first message from a new sender often lands in spam. That is reputation, not
configuration, and it settles as real mail flows.

---

## Deliberately off

`track_email_status` and `send_unsubscribe_message` are both off on the outgoing
account.

The first embeds a pixel that reports when an employee opens a message — tracking a
customer's staff without telling them. The second offers an unsubscribe link on what
are transactional HR notices; an employee who used it would silently stop receiving
leave approvals and payslip notifications.

---

## Not built yet

Tenant logins are still created silently, with a generated password that is shown only
on the provisioning screen. They should receive an invitation link and set their own
password instead. See `alvoraa_portal/tenant_setup.py`, where `send_welcome_email` is
set to `0`.
