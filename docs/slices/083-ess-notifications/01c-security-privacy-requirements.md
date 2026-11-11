---
slice: 083-ess-notifications
artifact: 01c-security-privacy-requirements
author: hrms-security-privacy-engineer
date: 2026-11-06
status: draft — for Surbhi, alongside the DevOps requirements, before the spec
inputs: [01-product-brief.md, 01b-ux-design.md, 01a-ux-opportunities.md, 07-devops-inputs.md (§1 and §2), prototype-v1.html, .claude/context/data-doors.md, .claude/context/security-compliance-baseline.md, .claude/context/compliance-feature-map.md, .claude/context/no-over-engineering.md, notices.py, inbox_api.py, grooming.py, www/hrms_employee.py, field_app_pwa.py, portal.js, frame.html, tests/test_notices_076.py, tests/test_portal_security_010.py, Frappe 16.33.1 source inside hrlocal-bench]
ticket: ALV-322 (Epic)
---

# 083 · Security and privacy requirements

## Answer first

**No P0. No blocker at this gate. This slice is safe to specify.**

I re-ran the thing the whole slice rests on, rather than trusting it. **Verified by
running it, as a plain staff login on `ppj.localhost` today:** every Frappe door into
`Notification Log` returns **one row — the caller's own** — out of 2,016 rows belonging
to 300-odd people. List, report view, report count, **CSV export**, single-document
read, link search and **share** are all closed. The one door that is wide open is
`frappe.db.count`, which applies no permission condition at all and returned **2,016**.

That single fact is the whole security story of this slice, because the slice's one new
server-side read is a count, and its one new server-side write is a filtered `UPDATE`.
**Neither is protected by Frappe. Both are protected only by a `for_user` term the
engineer has to type.** Requirements SEC-1 and SEC-2 exist to make that term impossible
to lose quietly, and the tests behind them must fail if it goes.

**Three things I want on the record:**

1. **The riskiest line in this slice is the bulk mark-as-read, not the bell.** Get the
   count wrong and a badge lies — a bug. Get the write's filter wrong and you silently
   mark **other people's** notifications read across the tenant. Nothing logs that, and
   nobody would report it. The blast radius of one dropped word is the whole tenant, and
   the detection is zero. That asymmetry decides how the tests are written.

2. **The bulk mark-as-read is not new code.** `grooming.my_notices_seen`
   (`grooming.py:1035`) is already exactly the right shape — one `frappe.db.set_value`
   with `for_user`, `read = 0` and `document_type in (...)` — and DevOps notes it is no
   longer called from the portal. The slice should **extend that one function to cover
   `Announcement`**, not write a third thing. That drops this part from rung 4 to
   roughly rung 1. See the subtract pass.

3. **The shared-handset criteria are necessary but not yet sufficient**, and the gap is
   not ours to fix with code. See §6.

I also checked the opposite failure — did this slice quietly add surface? **No.** No new
address, no new cache, no new copy of personal data, no new export, no new public route,
no new field, no new DocType. **Verified** by reading the design, the prototype (zero
`localStorage`, zero `sessionStorage`, zero endpoint names) and DevOps §2.3–§2.5.

**I did not specify or write any part of this slice.** I am reviewing other agents'
inferences, which is the right separation. The one thing I am *proposing* — extending
`my_notices_seen` — I should not also sign off at review; flag it for the reviewer.

---

## 1 · Threat model in four lines

**1 · Who would want this data, and what is the cheapest way to get it?**
Not an outsider. A **curious colleague** on the next bench, who wants to know whether
Rakesh got a grooming red or took leave. The cheapest route is not the bell: it is
`/api/resource/Notification Log` or the report view with the filter removed, from a
browser tab, with their own valid session. Second cheapest, and genuinely cheap: **pick
up the handset the previous shift left signed in**, or press Back after they signed out.

**2 · What is the blast radius of one mistake?**
Reads: **one person** — Frappe pins `for_user` on both doors, verified below. Writes:
the new bulk mark-as-read is the only new write, and a missing `for_user` term makes it
**tenant-wide** (at DTC, 441 logins; at PPJ, 2,016 rows). A missing `document_type` term
makes it **one person's whole Desk notification history** — PPJ's heaviest user carries
**406 unread `Employee` rows** that this page never shows. Cross-tenant: **not reachable**
— `for_user` is a site-scoped User id and sites are separate databases.

**3 · What does this make possible that was impossible before?**
Exactly one thing, and both the PM and the designer named it correctly: **a durable,
addressable page holding 30 days of one person's HR messages, reachable in two taps from
any screen, on a handset 441 people share.** Today the same data needs Home plus a sheet.
No new collection. No new automation. No model, no prompt, no outbound flow.

**4 · How would we find out?**
For a read leak: **we would not.** Nothing in the product logs list reads of
`Notification Log`, and there is no audit ledger (`compliance-feature-map.md` A2, status
`?`). For a count that is too wide: CI, because the badge would stop equalling its own
lists. For a **write** that is too wide: **nothing at all** — the symptom is other
people's notifications quietly turning read. **That is the detection gap of this slice,
and it is why SEC-2's test must be written to fail, not to pass.**

---

## 2 · Verified: what Frappe actually enforces

**The load-bearing claim, checked three ways. Verified in code and verified by running
it, 6 Nov 2026, Frappe 16.33.1 inside the running `hrlocal-bench`.**

Read in Frappe's own source
(`apps/frappe/frappe/desk/doctype/notification_log/notification_log.py`):

- `get_permission_query_conditions(for_user)` — **line 104** — returns
  `` (`tabNotification Log`.for_user = '<escaped session user>') `` for everyone except
  Administrator.
- `has_permission(doc, ptype, user)` — **line 114** — returns
  `user == "Administrator" or doc.for_user == user`.
- Both registered in `apps/frappe/frappe/hooks.py` — **line 117**
  (`permission_query_conditions`) and **line 151** (`has_permission`).

DevOps §2.4 reported this correctly. I confirm it, and I add the part they did not run:
**the door list, as the plain staff login `aarti.dhillon212@ppjewellers.demo` (roles
`Employee`, `Employee Self Service`, `All`, `Guest`, `Desk User`), against 2,016 rows
belonging to 300-odd colleagues.**

| Door (`data-doors.md` list) | What I called | Result | Verdict |
|---|---|---|---|
| 1 · list | `frappe.get_list("Notification Log")`, no filter, no page limit | **1 row**; distinct `for_user` = `{self}` | **closed** |
| 1 · list, hostile filter | `filters={"for_user": ["!=", me]}` | `[]` | **closed** |
| 2 · `reportview.get` | real `form_dict`, 20 rows, `name`/`for_user`/`subject` | 1 row, own | **closed** |
| 2 · `reportview.get_count` | no limit | `1` | **closed** |
| 2 · `get_count` + `reference_doctype` | `reference_doctype = "Employee"` | `1` | **closed** |
| 3 · `client.get_list` / `get_value` / `get_count` | hostile filters | `[]`, `{}`, `1` | **closed** |
| 3 · `client.get` another person's row | row `tlacrsd1ae` | `PermissionError` | **closed** |
| 4 · link search | `search_link`, `search_widget`, blank query | no results | **closed** |
| 5 · **report view, CSV export** | `reportview.export_query`, naming `subject` **and** `email_content` | CSV: 1 header line + **1 data line, own row only** | **closed** |
| 6 · **share** | `has_permission("Notification Log", "share", doc=<colleague's row>)` | `False` | **closed** |
| 9 · write rights | doctype has **one** permission row: role `All` with `read, report, export, print, email, share` — **no write, no create, no delete** (read from the doctype JSON; `Custom DocPerm` for this doctype is **empty**) | — | **no write door** |
| — · `frappe.db.count`, no filter | `frappe.db.count("Notification Log")` | **2,016** | **OPEN — by design** |
| — · `frappe.db.count`, colleague's filter | `{"for_user": "<colleague>"}` | **1** | **OPEN — by design** |
| — · `frappe.get_all` | server-only helper, ignores permissions by design | **2,016** | not an HTTP door |

**`frappe.db.count` and `frappe.db.set_value` are not doors a user can call directly —
they are tools our code calls.** `database.py:1285` builds a plain `COUNT(*)` through the
query builder with no permission condition. That is why SEC-1 exists. The same is true of
the write: `frappe.db.set_value` issues a direct `UPDATE` and checks nothing. That is why
SEC-2 exists.

### The `export` and `share` question, answered properly

This is the abuse case the caller was most worried about, so I traced the mechanism, not
just the result.

- **`export`** is not a separate door. `reportview.export_query`
  (`frappe/desk/reportview.py:427`) goes through the same `get_form_params()` →
  `DatabaseQuery`, so the `for_user` condition applies. `DISALLOWED_PARAMS`
  (`reportview.py:24`) strips `ignore_permissions` and **`user`** from the request, so a
  client cannot ask for someone else's condition. **Verified by running it:** the CSV
  came back with the caller's own single row, including `email_content`. Net effect:
  **an employee can export their own notice bodies to CSV.** That is the data subject
  exporting their own data, which DPDP treats as a right, not a risk. Note for the
  record: `export_in_background=1` emails that CSV to the person's own registered
  address, so notice text can leave the product by email — own data, own address,
  pre-existing, and I am not asking for a control.

- **`share`** is a real but narrow finding, and it needs stating precisely because the
  mechanism is counter-intuitive. In `frappe/permissions.py`, `has_permission` computes
  `perm` from `get_doc_permissions` (which runs our `has_permission` hook and gets
  `False`), and then — **`if not perm and not ignore_share_permissions: perm =
  false_if_not_shared()`** — a `DocShare` row **overrides** the hook for the
  single-document door. So:

  > *A plain employee can share **their own** `Notification Log` row with a colleague,
  > and that colleague can then open **that one row** through `frappe.client.get`.*

  They cannot share anyone else's row — `has_permission(..., "share", doc=<colleague's
  row>)` returned **`False`**. And the shared row does **not** appear in the colleague's
  **list** door: `db_query.build_match_conditions` only adds the `name in (shared)` OR
  when `_fetch_shared_documents` is set, which happens only if a User Permission matches
  one of the doctype's link fields. `Notification Log`'s link fields are `type`,
  `document_type`, `source_doctype`, `for_user`, `from_user` and the pseudo-field `name`
  — **none is `Employee`**, which is the only thing PPJ's staff logins carry a User
  Permission on (`{allow: Employee, apply_to_all_doctypes: 1}`, read today).
  **Verified by running it:** `frappe.share.get_shared("Notification Log", <user>)`
  returned `[]`, and the list door returned 1 row.

  **My verdict: do nothing about it in this slice, and I am saying why rather than
  leaving it silent.** The harm is a person voluntarily disclosing their own message.
  The fix would be a `Custom DocPerm` removing `share` from role `All` on a Frappe core
  doctype — rung 2, cheap to type, but it changes a tenant-wide permission row on a
  doctype the Desk also uses, for a self-disclosure risk. That trade is not worth making
  on the way past. **Recorded as residual risk R3, P4.**

---

## 3 · Data inventory

**This slice adds no field, no DocType and no new kind of data.** Everything below is
already returned by `notices_feed` and `get_inbox` today. The classes are the ones the
product already uses; retention is the honest current answer, not an aspiration.

| Field / object | Source | Sensitivity | Purpose | Retention (today) | Who may see it |
|---|---|---|---|---|---|
| `Notification Log.subject` for a **grooming mark** | `notices_feed` | **Performance** — a grooming red is a performance record under counsel's 18 Sep 2026 policy | Tell the person, their manager on the day, and HR, that a mark was recorded | **For ever.** Nothing trims `Notification Log` (DevOps OPS-17; Frappe's `clear_notifications` deletes redis keys, not rows). Pre-existing gap, see PRIV-5 | The row's `for_user` only, **and only while `grooming._readable` still allows it** — a manager's mark notice dies the next day (`grooming.py:1072`) |
| `Notification Log.subject` for a **grooming review** | `notices_feed` | **Performance.** Carries a **colleague's name and a red count** — `notify_flag` writes *"Grooming review pending for {who}: 3 grooming reds in {month}"* (`grooming.py:1083`) | HR and the line manager must know a review is due | For ever, as above | `for_user` only, gated by `_readable`: own record, own direct report, or inside `hr_scope` |
| `Notification Log.subject` + `sender_label` for an **announcement** | `notices_feed` | **Internal** — an HR/management message to this person | Tell people the rules and the news | Unread: **for ever.** Read: still stored for ever; only *displayed* for 30 days (`SEE_ALL_DAYS`) | `for_user` only. The row is the person's own copy |
| `Notification Log.read` | `notices_feed`, and the new count | **Behavioural** — whether a named person opened a named message | Let the person clear their own backlog | For ever | **The recipient only.** Never the sender. This is the whole of §7 |
| Approval row — `employee_name`, `leave_type`, `from_date`, `to_date`, `total_days`, `context`, `waiting_since` | `get_inbox`, `ROW_KEYS` `leave_approvals` | **Colleague personal data** | The named approver is deciding this document | Lives on the `Leave Application`; unchanged | The named approver for that row; HR inside `permitted_companies` |
| Approval row — `half_day`, `lwp_in_play`, `lwp_limit`, `special_day`, `chain_top` | same, slice 063, **only** where a pay rule set is on | **Pay-adjacent** — "N of 5 unpaid days used" is a financial-pressure signal about a colleague; `chain_top` is an org fact | Decide leave correctly under DTC's rules | unchanged | same as above |
| Approval row — `expense_type`, `expense_date`, `amount`, `note`, `has_bill` | `ROW_KEYS` `expense_approvals` | **Colleague financial** | Decide the claim | unchanged | the named approver. **`has_bill` is a boolean** — never a filename, never a URL (slice 081) |
| Approval row — `reason` on an attendance fix | `ROW_KEYS` `attendance_fixes` | **Internal, low** | Decide the correction | unchanged | the reviewer |
| Own request row — `state`, `says`, `note` | `ROW_KEYS` `my_requests` | **Own personal data** | "Where has my request got to?" | unchanged | the requester only |
| **The rendered page on a shared handset** | the browser | **Aggregate** — 30 days of one named person's HR messages in one scroll | — | **Must be none** | the signed-in person, while signed in, and nobody after |

### What is deliberately NOT here, and I checked each one

- **No absence explanation.** The design claims *"no absence reason, anywhere, ever"*,
  and `ROW_KEYS` does carry a field literally called `reason` on attendance fixes — so I
  checked instead of accepting either statement. **Verified in code:** that `reason` is
  the **category the employee picked** from a fixed option list (`Attendance Request.reason`
  is a `Select`, widened to a `Text` by a property setter in
  `attendance_correction.py:157`), e.g. "the machine did not read my card". The free-text
  field is `explanation`, and **it is not in `ROW_KEYS`** (`inbox_api.py:152` lists
  `reason`, not `explanation`). The design's claim stands. PRIV-2 pins it.
- **No health, passport, bank, pay figure, salary, Aadhaar or photo** on any row.
  **Verified** against all seven `ROW_KEYS` lists.
- **No `document_name` leaves the server** in a notice row — `notices_feed` returns
  `name`, `kind`, `from`, `text`, `link`, `when`, `read` and nothing else
  (`notices.py:93–101`), and `link` is returned only when it matches the literal prefix
  `/hrms-employee?grooming=`.

---

## 4 · Access intent — who must NOT see what

The analyst builds the permission matrix from this table. It is the brief's §9
expectations turned into the rule and **the Frappe door that enforces it**, which is the
part the brief deliberately left to me.

| Rule | The Frappe door that enforces it | Verified? |
|---|---|---|
| A person reads **their own** notice rows and nobody else's, on every surface and every API | `get_permission_query_conditions` on `Notification Log` (`notification_log.py:104`) + `has_permission` (`:114`), hooked at `frappe/hooks.py:117` and `:151` | **Yes — by running the full door list.** §2 |
| A **line manager** gets no colleague's notice rows by being a manager | the same `for_user` pin. Being a manager is not a term in the condition | **Yes** |
| An **HR Manager** gets no colleague's notice rows *through this page* | the same `for_user` pin. HR's wider scope lives in `grooming`/`hr_api`, not here | **Yes** |
| A notice is hidden once its reader may no longer read the document it is about | `grooming._readable` (`grooming.py:1046`), applied in `notices.py:74` | **Yes — in code**, and `test_notices_076` already proves one case |
| A **leaver** with a live login gets nothing | `grooming._active_employee` filters `status = "Active"` (`grooming.py:195`); `hr_scope` returns `set()` when the linked Employee is not Active (`grooming.py:271`); `inbox_api._my_employee` filters `status = "Active"` (`inbox_api.py:267`) | **Yes — in code.** All three lookups filter on status. Lesson 3 checked and clean |
| An approver sees only rows where they are the named approver; HR only inside their companies | `get_inbox`'s per-part scope — `permitted_companies`, `permitted_employees`, the named-approver filter — and `no_rows()` returning `{"name": ["in", []]}` so "entitled to nobody" never means "everybody" (`inbox_api.py:195`) | **In code.** Owned by slices 034/042/076 and their tests; this slice changes none of it |
| A **client cannot name a doctype, a field, a user or a filter** | `get_inbox` takes **no arguments** (`inbox_api.py:1157`); `notices_feed` takes only `see_all` and `cint()`s it. The two new calls must keep this shape | **Yes — in code.** SEC-3 pins it for the new calls |
| **Guest** sees nothing | `www/hrms_employee.py` redirects Guest to `/alvoraa-login?redirect-to=/hrms-employee` before any context is built; `notices_feed` and `_refuse_guest()` throw as well | **Yes — by running it.** `curl` on the bench returned `301 → /alvoraa-login` |
| The **next holder of the handset** sees nothing | the session cookie, `Cache-Control: no-store`, no client storage, and the browser's bfcache eviction on the `sid` change. See §6 | **Partly.** §6 names the one piece I could not prove |
| An **announcement sender** never learns who read it | no endpoint returns per-recipient `read` state to anyone but the recipient | **PRIV-4.** See §7 |
| **No outside party** (auditor, agency, vendor) gets anything | there is no share, no print route and no export on this page; the only export is the person's own, through the Desk | **Yes** |

---

## 5 · Obligations engaged

| Obligation | Source | Date I last verified the source | What it means here |
|---|---|---|---|
| **Reasonable security safeguards** — access control | DPDP Act 2023, via `security-compliance-baseline.md` §2 | **24 Aug 2026** (baseline entry). I did **not** re-verify the Act in this run; this slice engages no new or changed duty | The record limit must sit in Frappe's permission layer, not our page. SEC-1 … SEC-5 |
| **Purpose limitation** | DPDP, same entry, 24 Aug 2026 | Read state exists to let a person clear their own backlog. Re-using it to tell a sender who read their notice is a **new purpose** — §7 |
| **Data minimisation** | DPDP, same entry | No new field, no new store, no new copy. PRIV-1 |
| **Breach intimation** — affected people and the Board, detailed report in 72 h | DPDP, same entry; and counsel 1 Nov 2026 (ALV-249): *a breach counts even with no logged reads* | If the door list ever fails on a real tenant, the clock starts on confirmation, not on proof of misuse |
| **CERT-In: report in 6 hours of awareness** | CERT-In Directions 28 Apr 2022, baseline §3, **24 Aug 2026** | Nothing new to log in this slice. The 6-hour clock is the binding one if SEC-2's write ever goes wide |
| **Performance records: employment + 6 months, then permanent erasure; indefinite soft-deletion prohibited** | **Counsel, 18 Sep 2026** — binding, in `legal-retention-rules-2026-09` | A grooming-mark notice **is** a performance record, and `Notification Log` rows are kept **for ever**. Pre-existing, not created here. PRIV-5 routes it |
| **Passport and health data are not for managers** | **Counsel, 1 Nov 2026** (ALV-249) | None reaches any row. PRIV-2 keeps it that way |
| **EU AI Act** | baseline §4, 24 Aug 2026 | **No surface at all.** No model, no prompt, no automated decision, no profiling in this slice |
| **GDPR** | baseline §1 | No EU data subjects in scope for DTC/PPJ. Nothing stricter applies than the above |

**Housekeeping on the file I own:** the DPDP and CERT-In entries are dated **24 Aug
2026** — **74 days old, so not yet stale, but they go stale on 22 November 2026.** I did
not re-verify them today because this slice rests on no new regulatory reading. **Someone
must re-verify them before 22 Nov**, and it should not be discovered inside a slice.

**New-Frappe-app checklist:** not applicable. This slice installs no app. No new public
page, no guest access, no self sign-up, no new role.

---

## 6 · Shared handsets — my decision on the two criteria

**The question put to me: are PM-AC-A and PM-AC-B plus a header assertion enough?**

**My answer: they are the right criteria, they are necessary, and they are sufficient
*on the condition* that one ten-minute manual check is treated as a release gate rather
than a nice-to-have. I am not asking for any new code.**

What I verified myself today:

- `context.no_cache = 1` in `www/hrms_employee.py` → `can_cache()` is False
  (`frappe/website/utils.py:548`) → Frappe's page-cache headers are never set →
  `process_response` applies its default (`frappe/app.py:289`,
  `NO_CACHE_HEADERS` at `:283`). **Verified by running it:** a real response from the
  bench carried `Cache-Control: no-store,no-cache,must-revalidate,max-age=0`. DevOps
  traced this from code and said they had not seen a response; now one has been seen.
  (That response was the Guest redirect. The header comes from a `setdefault` applied to
  **every** response, so the signed-in page takes the same path — **inference**, not
  observed.)
- The `sid` cookie is **`HttpOnly`** — seen in the same response headers. That matters,
  because HttpOnly-cookie change is exactly Chrome's eviction trigger for a bfcached
  `no-store` page.
- Client storage: the portal keeps **one** key, `sb-pinned` (`portal.js:24101`, `24109`),
  removed by **both** sign-out links (`frame.html:148`, `174`). Nothing else. The
  prototype contains **zero** `localStorage` and `sessionStorage` references — counted.
- **A thing nobody flagged, and I am glad I looked:** `/hrms-employee` registers a
  **service worker** (`www/hrms-employee.html:90`, scope `/hrms-employee`). A caching
  service worker would hold this page on the handset for ever, and no response header
  would stop it. **Verified in code:** today it caches nothing — its `fetch` listener is
  `function (e) { return; }` with no `respondWith`
  (`field_app_pwa.py:405–409`), and it is served with its own `no-store`. The file even
  carries a comment warning the next person. **This is a standing hazard beside a new
  durable page, so SEC-6 pins it with a test.**

**What I could not check, and nobody can from a desk:** whether Chrome on Android
back/forward-caches this `no-store` page, and whether it evicts the entry when `sid`
changes at logout. DevOps was right to refuse to guess. I expect eviction — the trigger
is an HttpOnly cookie change and `sid` is HttpOnly — but **expectation is not evidence**,
and if the expectation is wrong the symptom is precisely the front-page story the brief
wrote out: the previous holder's 30 days of HR messages, one Back press away.

**So the shape I am requiring (SEC-7) is:**

1. PM-AC-A — nothing in `localStorage`, `sessionStorage`, IndexedDB or the Cache API.
2. PM-AC-B — Back after `/logout` renders nothing, **tested on a real Android handset
   once, before release**, and recorded with the Chrome version.
3. The header assertion in the same automated test, so a future edit that drops
   `context.no_cache` is caught by CI and not by a factory floor.
4. The service-worker no-op assertion.

**And the fallback, named now so nobody has to invent it under pressure:** if the Android
check shows rows on Back, the fix is **one line** — clear the rendered rows on `pagehide`
— not a header and definitely not an nginx change. I am deliberately **not** asking for
that line now. Writing a control before knowing it is needed is the thing
`no-over-engineering.md` forbids, and this one is cheap to add later and impossible to
test before the check.

**One more, small and cheap:** the hash route stays in browser history after sign-out,
and on a Chrome profile signed into a Google account it may sync. **So the route must
carry no identifier** — `#notifications`, never `#notifications/NL-0001` or an employee
id. PRIV-3.

---

## 7 · Out of scope: may an announcement sender see who read it?

**I am the named decider. My answer is no — not per named recipient, not now, and not as
a small addition to a later slice.** Three reasons, in order of weight:

1. **Purpose limitation, and it is the cleanest example of it in the product.**
   `Notification Log.read` was written so a person could clear their own backlog. Turning
   it into "who has not read my notice" is a **different purpose** with a different
   subject and a different power relationship. Under DPDP that needs a stated purpose and
   a line in the **employer's** notice, not a feature flag. *(I am not a lawyer.)*
2. **It surveils the least powerful person in the picture.** A frontline worker on a
   shared handset who has not opened an announcement produces a per-person list that a
   supervisor can act on. The designer and the PM both reached this conclusion
   independently; I agree with them.
3. **The data is already there, so the control must be a deliberate refusal.** There is
   nothing to build to prevent it and nothing to stop someone adding it in an afternoon.
   That is exactly the case where a written decision is the control.

**What I would allow, if Surbhi wants the sender's real question answered.** The
sender's question is *"did it land?"*, not *"who ignored me?"* An **aggregate** answers
it: *"Sent to 441 · read by 318."* Conditions, all four: a stated purpose; a line in the
employer's privacy notice; a **minimum-audience floor** so the figure can never identify
one person (an announcement sent to 3 people must show no figure at all); and **no
drill-down, ever** — no "show me the 123". **Its own slice. I am not designing it here.**

**⚠ COMPLIANCE — the one question that is genuinely new to counsel**, in one sentence, if
and only if Surbhi wants the per-person version:

> *May an employer show an announcement sender which named employees have and have not
> opened an internal notice, and if so on what lawful basis and with what notice?*

**Router: Surbhi.** It blocks nothing in this slice.

---

## 8 · Abuse cases

Each one is written as *this actor, in this state, calling this path, sees this data* —
because that is the only form in which I will accept a finding later.

| # | Actor and state | Path | What happens today | Requirement |
|---|---|---|---|---|
| A1 | **The curious colleague.** A DTC machine operator, valid session, `Employee` + `Employee Self Service` | `/api/resource/Notification Log?limit_page_length=0`, and the same through report view, report count, CSV export and link search | **Nothing.** One row — their own — out of 2,016. **Verified by running all six as this exact role** | SEC-5 keeps it true |
| A2 | The same colleague, **after** the slice ships | the new unread-count endpoint, with the `for_user` term lost in a refactor | Would return **2,016**. `frappe.db.count` applies no permission condition — **verified by running it** | **SEC-1** |
| A3 | The same colleague | the new bulk mark-as-read, with the `for_user` term lost | Would mark **every unread notification in the tenant** read. Nothing logs it; nobody reports it | **SEC-2** |
| A4 | The same colleague | the new bulk mark-as-read, with the `document_type` term lost (or using Frappe's own `mark_all_as_read`, `notification_log.py:271`, which filters on `for_user` **only** — **verified in source**) | Would clear **406 unread `Employee` rows** this page never showed, for PPJ's heaviest user | **SEC-2** |
| A5 | The same colleague | the new calls with crafted arguments — `document_type=["Employee"]`, `for_user="<colleague>"`, `filters={...}`, `ignore_permissions=1` | Must be impossible: the calls take no such argument, and `request_guard.py` strips permission-skipping flags | **SEC-3** |
| A6 | **The over-scoped manager.** A line manager who stopped managing Rakesh yesterday | opens the notifications page | The grooming review row disappears (`_readable`: `managers.get(d.employee) == me` is now false), and the mark notice expired the day after the mark. **The screen says nothing about why** — by design, because "you no longer approve for Rakesh" leaks an org change | PRIV-2; design §6.4 already specifies silence |
| A7 | **The departing employee.** Marked `Left`, login not disabled — ERPNext does not disable it | opens the page, or calls either endpoint | Notices gated by `_readable` return nothing (`_active_employee` filters `status = "Active"`); `get_inbox` parts collapse (`_my_employee` filters the same). **A `Left` HR Manager gets `set()` from `hr_scope`.** All three checked today | **PRIV-2** adds the regression test |
| A8 | **The guest / unauthenticated scanner** | `GET /hrms-employee`, and the two endpoints directly | `301 → /alvoraa-login?redirect-to=/hrms-employee` — **verified by running curl on the bench.** Both endpoints throw `PermissionError` for Guest | SEC-6 |
| A9 | **The next holder of the shared handset.** Previous shift signed out; same Chrome profile | presses Back to `/hrms-employee#notifications` | `no-store` sent (**verified on a real response**), nothing in client storage, service worker caches nothing, `sid` is HttpOnly so bfcache should evict. **The last link is unproven** | **SEC-7**, and the Android check as a release gate |
| A10 | **The announcement sender**, an HR user | any surface | No endpoint returns per-recipient read state. The refusal is the control | **PRIV-4** |
| A11 | **The HR person with the biggest inbox** | the Desk CSV export of their own notices | Gets their own rows, including `email_content`. Own data, own export | none — recorded, R2 |
| A12 | **A platform operator with no Employee record** | the page | `notices_feed` works (they can hold notices); `get_inbox` returns `has_employee: false` and empty parts. No colleague data. Slice 012's "All Companies" trap does not apply — there is no tree or roll-up view here | none |

---

## 9 · Requirements

Every one says how it will be tested, and **every test is written to fail if the control
is removed.** A check that cannot fail proves nothing.

### Security

**SEC-1 · The true unread count is protected only by its own `for_user` filter, so that
filter is a tested contract.**
The new uncapped unread count must filter on **both** `for_user = frappe.session.user`
**and** `document_type in NOTICE_DOCTYPES`. It must never take a user, doctype or filter
from the client, and must never use `frappe.get_all` (which ignores permissions by
design) for the counted set.
*How it is tested.* Seed two users, each with unread notices of the three kinds, plus
rows of a fourth `document_type`. As user A, assert the returned count equals **A's own
notice rows only**; assert it is **strictly less** than the site-wide count of unread
rows. Then, in the same test file, a source assertion: the count call's filter dict
contains the key `for_user`. **Delete the `for_user` term and both assertions must fail.**

**SEC-2 · The bulk mark-as-read is bounded to the caller and to the three document types
this feed owns. [P0 if it ever goes wrong]**
The write is **one** set-based `frappe.db.set_value("Notification Log", {"for_user":
<session user>, "read": 0, "document_type": ["in", NOTICE_DOCTYPES]}, "read", 1,
update_modified=False)`. It is **not** Frappe's `mark_all_as_read`
(`notification_log.py:271`, which filters on `for_user` only — verified in source). It is
**not** a loop over `mark_as_read`. It accepts **no arguments at all**.
*How it is tested.* Seed: caller has unread rows of all three notice kinds **and** two
unread `document_type = "Employee"` rows; a colleague has unread notice rows. Call it.
Assert: the caller's three notice rows are read; **the caller's two `Employee` rows are
still unread**; **every one of the colleague's rows is still unread**. **Drop the
`document_type` term and assertion 2 fails; drop the `for_user` term and assertion 3
fails.** Both must be separate assertions so the failure names the cause.
*Note:* `frappe.db.set_value` accepts an `["in", [...]]` filter — **verified by running
it** against a filter that matched nothing, then rolled back. No raw SQL is needed, and
none is permitted.

**SEC-3 · No new client-supplied filter, doctype, field or user.**
The count and the mark-as-read take no doctype, field, user, filter or limit from the
request. The three notice document types are a server-side constant
(`notices.NOTICE_DOCTYPES`). The slice adds **at most one** new whitelisted method; the
mark-as-read is a `POST`.
*How it is tested.* Call each new endpoint with crafted keyword arguments —
`document_type=["Employee"]`, `for_user="<colleague>"`, `filters={}`,
`ignore_permissions=1` — and assert each is either refused or has **no effect on any row
outside the caller's three notice types**. Plus: assert the count of `@frappe.whitelist`
in `alvoraa_portal` grew by no more than 1.

**SEC-4 · No bypass is added.**
`ignore_permissions` stays at **0** in `notices.py` and in any new file. No raw SQL. No
`frappe.get_all` added to a user-callable path for anything other than the pre-existing
`sender_label` lookup, which is already bounded to the caller's own announcement rows.
*How it is tested.* The existing CI ceiling —
`test_portal_security_010.test_sec16_ignore_permissions_does_not_grow`, which already
carries `("alvoraa_portal", "notices.py"): 0` at line 748. Any new file is added to
`CEILINGS` at **0** in the same commit.

**SEC-5 · The Frappe door list on `Notification Log` becomes a test, not a memory.**
A test, run as a **plain staff login** on a **freshly created** site, proves that a
colleague's notice rows are unreachable through: the list API; `reportview.get`;
`reportview.get_count` (including with `reference_doctype`); `reportview.export_query`
(CSV); `client.get` of a named row; and `has_permission(..., "share", doc=<colleague's
row>)`. Six assertions.
*Why this is in scope even though it tests Frappe's code, not ours:* the whole slice
rests on it absolutely, Frappe upgrades, and the doctype grants role `All` `read`,
`report`, `export` and `share`. It is a canary for an upgrade, and it is six assertions
in one test — proportionate, and the cheapest possible honest answer to question 2 of
`data-doors.md`.
*What must exist for it to be observable:* **at least two users with notice rows of the
three kinds.** On a fresh site that means fixtures. **If the fixtures are missing the
test passes on an empty table and proves nothing** — this is slice 028's lesson, and it
bit this slice already: **PPJ holds 2,016 `Notification Log` rows and exactly 0 of the
three notice kinds.** So the test must also assert that the colleague's seeded row
**exists** before asserting it is invisible.

**SEC-6 · The page stays behind the session, at no new address.**
A hash route inside `/hrms-employee`. No new web page, no new nginx rule, no new guest
route. Guest is redirected before any context is built. The response carries
`Cache-Control: no-store,...`. The portal service worker stays a **no-op** — no
`caches.`, no `respondWith`, no `event.waitUntil(cache…)`.
*How it is tested.* An unauthenticated request to the page asserts the redirect to
`/alvoraa-login?redirect-to=/hrms-employee`; the authenticated request asserts the
`Cache-Control` header; a source assertion on `field_app_pwa._PORTAL_SERVICE_WORKER`
asserts it contains none of `caches`, `respondWith`, `Cache`. Plus `git diff --stat`
shows `deploy/nginx.conf` unchanged.

**SEC-7 · The handset leaves nothing for the next person.**
(a) Nothing about notices or approvals is written to `localStorage`, `sessionStorage`,
IndexedDB or the Cache API — `sb-pinned` remains the only client-stored key.
(b) After `/logout`, pressing **Back** renders nothing.
*How it is tested.* (a) An automated assertion over the built portal JS: the only
`localStorage`/`sessionStorage` keys are `sb-pinned` and the existing theme key, and the
set of storage call sites has not grown. (b) The header assertion from SEC-6, **plus a
manual check on a real Android handset before release**, recorded with the Chrome
version and the date. **This manual check is a release gate.** If it shows rows, stop and
add the one-line `pagehide` clear — see §6.

### Privacy

**PRIV-1 · The field set is frozen, and the page proves it rather than asserting it.**
`ROW_KEYS` is unchanged. `notices_feed`'s returned keys are unchanged **except** the two
new ones (`capped`, and `unread` becoming a true count). No new field, no new Custom
Field, no new DocType, no new table.
*How it is tested.* Extend the existing
`test_the_person_sees_their_own_unread_notice_with_a_fixed_set_of_keys`
(`test_notices_076.py:56`) to assert the **exact** key set including the new ones; the
existing `ROW_KEYS` / `row_keys()` tests already fail if a part grows a key. Plus: the
slice's diff contains no `.json` DocType file and no `Custom Field` fixture.

**PRIV-2 · No absence explanation, health, passport, bank, pay figure or salary reaches
a row — and a leaver reaches nothing.**
*How it is tested.* (a) An assertion that `explanation` is **not** in the
`attendance_fixes` row keys and not in any row returned (the free-text field; `reason` is
a fixed-option category — verified in code today). (b) An assertion that no `ROW_KEYS`
list contains a salary, bank, passport or health fieldname, by name list. (c) A leaver
test: set the login's Employee to `Left`, call both feeds, assert empty — and the same
for a `Left` login that still holds `HR Manager` (`hr_scope` must return `set()`). The
`_readable` case is already covered by
`test_a_notice_is_hidden_when_its_reader_may_no_longer_read_the_mark`.

**PRIV-3 · The route and the page carry no identifier anywhere a browser keeps it.**
The hash route is a fixed word — `#notifications` — with no employee id, document name
or email in the URL, the hash, the document title or any `history.pushState` state.
*Why:* browser history survives sign-out on a shared handset and may sync to a personal
Google account.
*How it is tested.* A source assertion that the route string is a constant with no
interpolation, plus an assertion that the page sets no `document.title` containing a
name.

**PRIV-4 · Read state stays with the recipient.**
No endpoint, payload or log returns per-recipient `read` state, or any other person's
`for_user`, to anyone other than that person. The new count returns **a number**; the new
mark-as-read returns **`{"ok": 1}`** and no row list.
*How it is tested.* Assert the return shape of both new calls contains no `for_user`, no
email, no employee name and no row identifiers belonging to anyone else. Plus a grep
assertion that the slice's diff adds no read-receipt field, report or endpoint.

**PRIV-5 · The retention answer is written down, and the gap is routed rather than
hidden.**
This slice creates **no** new store and **no** new copy, so it needs no new retention
period. It must also record, in the spec, the honest current state: **`Notification Log`
rows are never deleted** (DevOps OPS-17; Frappe's `clear_notifications` removes redis
keys, not rows — verified), and a grooming-mark notice **is** a performance record under
counsel's binding 18 Sep 2026 policy (*employment + 6 months, then permanent erasure;
indefinite soft-deletion prohibited*). The retention and purge engine is
`compliance-feature-map.md` **A6, status `?` — not built.**
*How it is tested.* Not by a test — by a line in the spec and a ticket. **This is
pre-existing debt that this slice must not be blamed for and must not quietly inherit.**
*Owner to route:* `hrms-product-manager` for the slice, with counsel's periods already
in hand. **Temporary debt. ⚠ DECISION SEC-R1 — Surbhi to accept it in writing for this
slice, with a date.**

---

## 10 · What an approver may see on a row — the answer to question 6

**This slice widens nothing. Verified against all seven `ROW_KEYS` lists in
`inbox_api.py:112–167` and against `get_inbox`, which takes no arguments.** Same caller,
same scope, same endpoint, same fields — a second place to draw them.

**But the design's own list is shorter than `ROW_KEYS`, and that gap must not survive
into the spec.** Design §6.2 says *"Row contents are `ROW_KEYS`, unchanged. Name · kind ·
dates · days · amount · 'waiting N days'."* The actual lists also carry `context`,
`note`, `reason`, `has_bill`, `can_decide`, `can_withdraw`, `says`, `state`, `title`,
`subject`, `value`, `logged_on`, `document`, `half_day`, `lwp_in_play`, `lwp_limit`,
`special_day` and `chain_top`. **The analyst must write the full per-part field list into
the spec's parity table**, so PRIV-1's test asserts the real set and not the design's
prose summary.

**Is there any field that should not be on a notifications page even though it is already
on the Home card? My answer: no — one field is worth a sentence, and it stays.**

`lwp_in_play` / `lwp_limit` — the colleague's "N of 5 unpaid days used" figure — is the
closest thing here to pay data about another person. It appears only where a pay rule set
is enabled, only to the named approver, and it is **the thing being decided**: approving
a sixth unpaid day when the limit is five is the decision. Removing it would make the
approver decide blind, and a control people route around is not a control. **It stays, and
it stays out of the context line, which carries no colleague name and no leave type
(slice 042 AC-28).**

The honest residual: the notifications page is a **more durable and more browsable**
surface for the same fields than a Home card is — one scroll, a bookmarkable address, 30
days. That is a change in *exposure shape*, not in *entitlement*, and §6 is where it is
answered.

---

## 11 · Open questions

Sorted. **Only the first blocks anything.**

| # | Question | My reading | Why it changes the control | Fail-closed default I apply meanwhile | Owner |
|---|---|---|---|---|---|
| **must know** · ⚠ **DECISION SEC-R1** | Do you accept, in writing and with a date, that `Notification Log` rows — including grooming-mark notices, which counsel classes as performance records — are kept **for ever**, as pre-existing debt this slice does not fix? | This is the only obligation gap the slice touches. It is not caused here and fixing it is a slice of its own (the purge engine, A6, is not built) | It is the difference between "accepted risk with a name and a date" and "an unnamed one waiting for an owner". It does not change a line of code in this slice | I treat it as **accepted-pending**, record it as residual risk R1, and the spec must carry the sentence | **Surbhi** |
| should know | Do DTC's staff logins carry any **User Permission on a `User` record** (as opposed to the `Employee`-only rows PPJ carries)? | I expect not. PPJ's staff logins carry one row, `{allow: Employee, apply_to_all_doctypes: 1}` — read today | If any tenant granted a User Permission on `User`, `_fetch_shared_documents` turns on for `Notification Log` and shared rows would start appearing in the **list** door, not only the single-document door. It would not leak anything nobody shared, but it changes my §2 answer | I require SEC-5's door list to be run **on DTC as a read-only check before release**, which answers it directly | `hrms-devops-engineer`, read-only count |
| should know | **How many `Notification Log` rows of the three notice kinds does the heaviest DTC user carry?** | Unknown. PPJ holds **0** of the three kinds and 2,016 of other kinds, with four users over 400 | Not a security question, but it decides whether SEC-5's test and the Android check have any data to work with. **Zero rows means every "0 findings" in this slice means nothing** — slice 028's lesson, already live on this slice | I require SEC-5's test to assert the colleague's seeded row **exists** before asserting it is invisible | **Surbhi** to authorise a read-only count |
| nice to know | Who is the **named compliance owner**? `product-context.md` §5 still says `TODO — founder to name a person` | I cannot name a human for the §7 decision or for a DPDP notice if SEC-7 ever fails | It decides who signs, not what is built | I have written "Surbhi, with counsel" throughout | Founder |

**Nothing here needs counsel.** Counsel has already ruled on retention (18 Sep 2026),
on manager access to passport and health data and on breach handling (1 Nov 2026). The
only genuinely new question is the announcement read-receipt one in §7, and it is out of
scope and blocks nothing.

---

## 12 · Subtract pass

I read this twice more, asking only what I could delete. **Removed:**

- **A ninth requirement on PII in logs.** The new code is a `COUNT` and an `UPDATE`;
  neither handles a subject or a name, and the existing scanner already covers the files.
  A requirement that forces a test for something that cannot happen is padding. **Covered
  as inherited, not numbered.**
- **A requirement to add an `ignore_permissions` ceiling for `inbox_api.py`** (it has 1
  and no ceiling, so a second could land unnoticed). Real, but **not this slice's** —
  this slice does not touch that file. **Routed as R4, P4**, not a requirement.
- **A requirement to remove `share` and `export` from role `All` on `Notification Log`.**
  Rung 2 and tempting. Rejected: the only harm is a person disclosing their own message,
  and the change edits a tenant-wide permission row on a Frappe core doctype the Desk
  also uses. **Recorded as R3, P4** with the reasoning, so nobody has to re-derive it.
- **A `pagehide` row-clearing requirement.** It is the right fix *if* the Android check
  fails. Writing it now is building a control before knowing it is needed. **Named as the
  fallback in §6 instead.**
- **A fourth privacy requirement on purpose tags for the three notice kinds.** There is
  no purpose-tag mechanism in the product (feature map, not built), so the requirement
  would have forced one into a front-end slice. **Dropped.**
- **A per-door requirement** (ten requirements, one per row of `data-doors.md`). Collapsed
  into **SEC-5**, six assertions in one test. A long list buries the two that matter.
- **An "evidence for questionnaires" section.** The §2 table *is* the evidence; I will
  fold it into `docs/security/questionnaire-answers.md` at the review step, not now.

**What I merged:** the count and the write were four requirements; they are now SEC-1,
SEC-2 and SEC-3, because the third hazard (a client-supplied filter) is one rule covering
both.

**What I kept, and why:** SEC-5, even though it tests Frappe's code rather than ours —
the slice rests on it absolutely, Frappe upgrades, and ALV-249 was exactly this shape.
And PRIV-5, even though it fixes nothing — an unnamed accepted risk is the thing I exist
to prevent.

**Result: 7 SEC + 5 PRIV = 12 requirements, one new whitelisted method at most, no new
DocType, no new field, no new permission layer, no new CI gate, no feature flag.**

---

## 13 · Residual risk

| # | Risk | Severity | Owner | Status |
|---|---|---|---|---|
| **R1** | `Notification Log` rows are **never deleted**, including grooming-mark notices that counsel classes as performance records (*employment + 6 months, then permanent erasure* — 18 Sep 2026). The purge engine (feature map **A6**) is not built | **Temporary debt** — the obligation is real, the clock is not this slice's | **Surbhi to accept**, ⚠ DECISION SEC-R1; route to `hrms-product-manager` | **ACCEPTED IN WRITING by Surbhi on 6 November 2026.** Accepted as pre-existing debt that this slice does not create and does not fix. The purge engine (feature map **A6**) remains unbuilt and needs its own slice; until it exists, `Notification Log` rows — grooming-mark notices among them — are kept indefinitely, against counsel's 18 Sep 2026 rule of *employment + 6 months, then permanent erasure*. This acceptance covers slice 083 only; it is not a standing waiver and it does not carry to any later slice that adds a new store of performance data |
| **R2** | An employee can CSV-export their own notice bodies (including `email_content`) from the Desk, and have it emailed to themselves | **Acceptable simplification** — own data, own address; DPDP treats self-access as a right | — | Accepted, 6 Nov 2026, by me |
| **R3** | Role `All` holds `share` on `Notification Log`, and a `DocShare` **overrides** our `has_permission` hook for the single-document door (`frappe/permissions.py`, `false_if_not_shared`). So a person can disclose **their own** notice row to a colleague. No one can share anyone else's — **verified** | **Intentional trade-off**, P4 | me | Accepted, 6 Nov 2026, by me, **reversible** — one `Custom DocPerm` if it ever matters |
| **R4** | `inbox_api.py` holds 1 `ignore_permissions` and has **no CI ceiling**, so a second could land unnoticed | **Security debt**, P4. Not this slice's file | `hrms-security-privacy-engineer` (me) | Open, routed |
| **R5** | **Chrome Android's back/forward-cache behaviour for a `no-store` page is unproven.** If it restores the page instead of evicting on the `sid` change, the next holder of a shared handset sees the previous holder's 30 days of HR messages | **Dangerous if unverified** — and the whole reason the Android check is a release gate, not a nice-to-have | `hrms-test-automation-engineer` to run it; **Surbhi** if it fails | **Open. Must close before release.** Fallback named in §6 |
| **R6** | **No tenant has been counted.** PPJ holds **0** rows of the three notice kinds, so every control in this slice is currently **unobservable on real data**. "0 findings" from any test run on PPJ today means nothing | **Dangerous debt — escalate now**, because it makes every other assurance in this document hollow | **Surbhi** to authorise a read-only count on DTC | Open |
| **R7** | The baseline entries for DPDP and CERT-In are dated **24 Aug 2026** and **go stale on 22 November 2026** | **Security debt** on the file I own | me | Open, dated |

---

## 14 · What I could not verify, and what I would need

Said plainly, because each one is a finding in its own right.

1. **DTC's roles, User Permissions and `Notification Log` counts.** I read **PPJ's**, on
   the local bench. DTC is a dev/production tenant and this run is local and read-only.
   *What I would need:* Surbhi's authorisation for a read-only count on DTC — roles per
   staff login, User Permission rows, and `Notification Log` rows by `for_user` and
   `document_type`. **Ten minutes, counts only.**
2. **The `Cache-Control` header on the *signed-in* page.** I observed it on the real Guest
   redirect from the bench. The signed-in page takes the same `setdefault` path
   (`frappe/app.py:289`), so it is an **inference**, not an observation. A login POST
   would have written a session row to a bench shared with other sessions, so I did not
   do it. *What I would need:* a browser session, or the test engineer's assertion in CI
   — which SEC-6 now requires.
3. **Chrome Android bfcache on Back after logout.** A real handset. R5.
4. **Whether a `DocShare` on a `Notification Log` row actually renders in a colleague's
   single-document door.** I proved the mechanism by reading
   `frappe/permissions.py` and proved the list door stays closed; I did **not** create a
   `DocShare` row, because that is a write to a shared bench. **Inference from source**,
   not run.
5. **Any timing.** I measured nothing. Every performance statement in this slice is
   DevOps', and theirs are estimates.
6. **Nothing was seen in a browser.** No screen in this slice has been looked at by me.

**What I changed on the shared bench: nothing.** Every query was a read; the one write I
tried used a filter that matched no rows, and I rolled the transaction back. No
`bench migrate`, no `clear-cache`, no site config change, no record edit, nothing against
dev or production.

---

## 15 · Handoff

**To `hrms-business-analyst`:** every `SEC-n` and `PRIV-n` above must trace to an
acceptance criterion. Three things need you specifically:

1. **The parity table must carry the full per-part `ROW_KEYS` field list**, not the
   design's six-word summary — see §10. PRIV-1's test asserts the real set.
2. **PRIV-5 is a sentence in the spec, not a test**: `Notification Log` rows are kept for
   ever, that is pre-existing, and ⚠ DECISION SEC-R1 is Surbhi's to date.
3. **§4 is your permission matrix**, with the Frappe door named per rule and the
   verification status attached.

**To `hrms-fullstack-engineer`:** the bulk mark-as-read already exists in the right shape
— `grooming.my_notices_seen` (`grooming.py:1035`) does `for_user` + `read = 0` +
`document_type in (MARK, REVIEW)` in one `set_value`. **Extend it to cover `Announcement`
rather than writing a third thing**, and move it to `notices.py` if that is where it
belongs now. `frappe.db.set_value` accepts the `["in", [...]]` filter — I checked. And
**neither** the count **nor** the write is protected by Frappe; the filter terms are the
whole control.

**To `hrms-test-automation-engineer`:** SEC-1, SEC-2 and SEC-5 are the three that matter.
Write each to **fail with the control removed**, and prove it fails before you commit it.
SEC-5 needs **seeded rows for two users**, and must assert the colleague's row **exists**
before asserting it is invisible — otherwise it passes on an empty table, which is
exactly where PPJ is today. The Android check in SEC-7 is yours and it is a release gate.

**To `hrms-technofunctional-reviewer`:** I am proposing the `my_notices_seen` extension,
so **I should not be the only one who signs it off at review.** Please take that one part.

---

**I am not a lawyer.** Everything in §5 and §7 that turns on a point of law is either
counsel's already-given ruling, cited with its date, or a question marked for them.
