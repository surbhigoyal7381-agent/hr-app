---
slice: 078-positions-faces
artifact: 00-impact-analysis
author: hrms-fullstack-engineer
date: 2026-10-31
status: for Surbhi's strategy gate. No code written. No commits. Nothing run that changes anything.
worktree: .claude/worktrees/078-positions-faces on slice/078-positions-faces, from origin/dev d3afcaa5
inputs:
  - 02-functional-spec.md (42 stories, 151 ACs) — read §0–§5 in full, §6–§25 through its own section map
  - 01c-security-privacy-requirements.md (16 SEC, 9 PRIV) — every item read
  - 07-devops-inputs.md §1 and §3 (38 OPS) — every row read
  - 01-product-brief.md, 01b-ux-design.md
  - .claude/context/{no-over-engineering,parallel-work,change-process,frappe-conventions,nfr-budget,security-compliance-baseline}.md
  - Frappe v16.33.1 and ERPNext source read inside the running container hrlocal-bench (image dev-3830ed3)
  - code read in this worktree, 31 Oct 2026, cited file:line throughout
---

# 078 · Impact analysis and strategy

---

## 0a · Facts measured on dev since I was briefed — used as given, not re-derived

Read-only on the live dev server today, by the coordinator. **Production (DTC) could not be
read in this session, so every DTC statement below and throughout this document is
`[STATED BY SURBHI]`, not measured.**

| Fact | Figure | What it changes here |
|---|---|---|
| Free disk on the server | **111 GB free, 43% used** | **OPS-31's first condition is satisfied.** It clears the deploy gate (fails below 25 GB) and the hourly alarm (warns below 40 GB) with room for the 3.2 GB-per-tenant document estimate several times over. Two of OPS-31's three conditions remain: one proved restore with `--with-files` on dev, and a recorded `BACKUP_BUCKET` decision |
| `dev.alvoraa.co` headcount | **363 active employees, 0 with a photo** | Confirms the premise on a second site. PPJ was 403/0, DTC is 0 `[STATED BY SURBHI]`. **No backfill anywhere** — OPS-16 holds |
| `Alvoraa Position` read on dev | **HR Manager and System Manager**, shipped `DocPerm` rows, **no `Custom DocPerm` override** | Narrower than PPJ, where `07` §1.2 measured `Custom DocPerm` rows cutting the effective set to **System Manager alone**. Same two roles as DTC. §0.7 is what follows |
| `Alvoraa Position` read at DTC | **HR Manager and System Manager, nothing wider** — the shipped default, no tenant override `[STATED BY SURBHI]` | **This settles the one question that could have changed the shape of the build.** §0.7 |
| `allow_guests_to_upload_files` / `allowed_doctypes_for_guest_uploads` | **0 and `''`** | Confirmed on dev too. **The empty-allow-list trap is real and live**: `handler.py:135` is `if guest_allowed_docs:`, so switching the flag on while the list is empty opens a guest upload against **any** doctype. AC-103 and AC-104 are the right two criteria |
| `max_file_size` | **0** → Frappe's **25 MB** fallback (`frappe/core/api/file.py:85-90`), nginx body limit 50 MB | OPS-24 stands: set it to **5**, site-wide, and say site-wide out loud |
| `send_work_anniversary_reminders` | **1 — live.** `send_birthday_reminders` = 0 | **This changes PRIV-1's wording, and it is the most actionable thing in this table.** §0.2 found that `employee_reminders.py:168, 180` puts the photo's URL into an email body sent to colleagues. On dev that path is **switched on today**. So the notice must say **emails**, not only charts. §4.2 PRIV-1 updated |
| `Employee Document` / `Employee Document Type` rows on dev | **none at all** | The 6,469 figure was the PPJ demo copy. **There is nothing on dev to test the document path against**, so **US-41's fixture set is load-bearing, not optional** — a document test run on dev today would report "0 findings" and prove nothing, which is lesson 1 from slice 028 exactly. §8 step 5 cannot start without it |
| DTC | **has the photo field; whether any photo has been added is unknown** `[STATED BY SURBHI]` | No change to the build. It does mean the "0 photos at DTC" line in `07` OPS-16 is now "0 known", which is still enough: the backfill is empty either way, and OPS-13's fallback means a photo without a thumbnail simply shows the full photo |

### Photo sizing — Surbhi's "keep an industry standard size"

**I agree with all three numbers and I am not asking to change any of them.** The reasons,
so the agreement is on record rather than assumed:

| Number | Verdict | Why this is the standard one |
|---|---|---|
| **Stored: 512 px longest edge, JPEG quality 82** (~30–60 KB) | **Agree** | 512 px is the common profile-photo standard (Slack, most HR products) and it is the largest size this product ever displays — the enlargement is ~240 px, so 512 px covers it on a 2× phone screen with nothing to spare and nothing wasted. Quality 82 is the usual floor before a face shows artefacts |
| **Derived: 48 px** | **Agree, and the arithmetic matters** | The chart circle is **24 px** (`panels.css:2141`) and a card is **34 px** (`panels.css:1855`). 48 px is exactly **2×** the chart circle, which is what a phone's 2× display needs to look sharp. Smaller would blur on every phone; larger would be bytes the screen cannot use. `07` §3.2's measured saving — **~720 KB → ~48 KB** on a 16-face first paint — is what buys it its place |
| **Upload cap: 5 MB** | **Agree** | A phone photo is 3–8 MB, so 5 MB accepts the ordinary case and refuses the outlier, and it is a tenth of the 25 MB that is allowed today. It also bounds the document endpoint's worst case from minutes to seconds in one of eight worker slots |

One thing I will **not** do, because it is the trap this sizing exists to avoid: the cap is
checked as the **length of the base64 string, before anything is decoded**. A 200 MB payload
must not be expanded in a worker's memory before we say we did not want it. That is
`field_app_photos.py:86` and it is the first line of the endpoint.

---

## 0 · The answer first — read these seven things before anything else

**I am not asking to build this exactly as specified. Five of the seven findings below
change the shape of the build, and three of them make it smaller. One of them (§0.7) is the
only piece of good news: the decision that looked riskiest turns out to cost nothing today.**

### 0.1 Frappe v16 already ships the pre-onboarding token. Most of that part should be deleted.

I read `frappe/website/doctype/web_form/web_form.py` and
`frappe/website/doctype/web_form_request/web_form_request.py` **in the running image**
(v16.33.1, tag `v16.33.1`, HEAD `988e54f3`, dated 8 Sep 2026). Frappe now has:

- a **`key_required`** checkbox on `Web Form`, and
- a **`Web Form Request`** DocType that mints a 32-byte `secrets.token_urlsafe()` key,
  with `expires_on`, `first_used_on` (single use), a `references` child table, and
  `doc_values` that the server forces onto the submitted document so the browser cannot
  override them.

The key is checked as **the first statement of `get_context`** (`web_form.py:205-211` →
`:497-521` → `web_form_request.py:124-150`), before any template work, and **again on
submit** at `web_form.py:753-758` — before the login check, before any document is
touched, under a row lock (`for_update=True`). Read, list, delete and link-options are
each gated separately. `Web Form Request` ships `Website Manager`-only, so Guest cannot
enumerate keys. The header on that file says `Copyright (c) 2026` — this is new, which is
why nobody on the team knew about it.

**What that deletes from the plan:** 078-SEC-9's hand-built token (`token_hash`,
`retired_token_hash`, `expires_at`, `lifetime_hours`, the `Waiting/Used/Cancelled/Ran out`
state machine copied from `Alvoraa App Invite`), 078-SEC-13's own-endpoint existence
oracle, and most of 078-SEC-14's "our own guest-allowed POST endpoints" fallback. The
framework does all of it, and maintains it.

**But it breaks one named rule, and only Surbhi can settle it.** Frappe passes the key as
**`?web_form_request_key=<token>` — a query string**. 078-SEC-9 says, in bold: *"It must
never appear in a query string."* The reason is good: a query string reaches access logs,
`Referer` headers and synced browser history. `www/enrol.html` uses a URL fragment
precisely to avoid that.

**I checked our nginx, and the query string is logged.** `deploy/nginx.conf` sets no
`log_format`, so nginx uses its default `combined` format, which includes `$request` — the
whole request line, query string and all. `access_log off` appears in only three places
(`/healthz` at lines 124 and `/assets/` at 211 and 414). **`location /`, where a web form
route lands, logs every request.** So a plain `key_required` Web Form would write the live
token into the access log on every page open. That is exactly the fault
`field_app_limits.py` was written to avoid in Redis, and 078-SEC-9 is right to forbid it.

So there are **three** options, and I recommend the third:

| | What we build | What it costs |
|---|---|---|
| (a) Frappe's Web Form with `key_required`, as shipped | Almost nothing: one doctype, one Web Form record, a small HR screen to mint a `Web Form Request` | **The live token lands in the nginx access log on every open** (verified above), plus browser history and any proxy. Breaks 078-SEC-9 |
| (b) Our own guest POST endpoints, token in the fragment, token schema ours | 078-SEC-9 as written: four token fields, a `Waiting/Used/Cancelled/Ran out` state machine, the retired-hash rule, our own validate/submit/upload endpoints and the tests for all of it | The largest single piece of new code in the slice, re-implementing what the framework now does, maintained through every Frappe upgrade |
| **(c) Frappe's `Web Form Request` as the token store and validator, our own hardened page** — **my recommendation** | Our own page on the `www/enrol.html` pattern: token in the **URL fragment**, `history.replaceState`, no external asset. It POSTs the token in the **request body** to `web_form.accept(web_form, data, web_form_request_key=...)` — which takes it as a parameter, so it never touches a URL. Validation is Frappe's `get_web_form_request()`; our own token-checked upload endpoint | **We skip the Web Form's own rendering**, which is the only part that forces the query string. So Frappe still owns the key generation, expiry, single-use burn, the `has_reference` check and the forced `doc_values` — and we own one page. **This is a variant of Decision 11, not Decision 11 as written, so it is Surbhi's to confirm** |

Option (c) keeps the whole subtraction in §10 item 1 — we delete the token schema, the state
machine and the retired-hash rule either way — and it keeps SEC-9's fragment rule and
SEC-15's hardened page. It costs one page we were building anyway.

**One hole exists either way, and it is the real one.** `/api/method/upload_file`
(`frappe/handler.py:128-218`) **never looks at `web_form_request_key`**. A guest upload is
gated only by `allow_guests_to_upload_files` plus the `allowed_doctypes_for_guest_uploads`
list, a MIME allow-list and a size cap. It is token-blind. So **whichever option is
chosen, the uploads must go through our own token-checked endpoint**, which is what
078-OPS-25 preferred on risk all along. I agree with OPS-25 on this one point and will
build the upload endpoint ourselves.

And I confirmed the trap Surbhi verified: `handler.py:135` is `if guest_allowed_docs:` —
**an empty list skips the allow-list entirely**, so "on with an empty list" lets a guest
attach a file to any doctype. AC-103 is right to insist both values go in one change.

### 0.2 The photo is not on ten surfaces. I count twenty endpoints.

The coordinator asked me to confirm security's count of ten. **I cannot. I get 20 distinct
client-reachable whitelisted endpoints that return `Employee.image`, and 24 surfaces if
you include four routes that are not endpoints.** Full list in §2.3. The ten in `01c` §0(1)
look like *screens*, not code paths. What a screen-level count hides:

- `hr_api.get_checkin_status` (`hr_api.py:1783`) and `hr_api.get_expense_claims`
  (`hr_api.py:2207`) return `_get_employee()`'s **whole dict**, so neither file ever
  contains the word `image` near the return — the field list is 1,400 lines away at
  `hr_api.py:306`. A grep for `"image"` misses both.
- `goals_api.get_portal_context` (`goals_api.py:257`) and `goals_api.get_team_goals`
  (`goals_api.py:1083`) emit the key as **`avatar`**, not `image`. A grep for `image` in
  the payload misses both.
- The org chart is **three** endpoints — `my_view`, `subtree`, `get_children` — not one.
- There are **two different functions called `get_children`**:
  `hrms.alvoraa_org_structure.api.get_children` and
  `hrms.hr.page.organizational_chart.organizational_chart.get_children`. A grep on the
  bare name collapses them.
- **`hrms.api.get_all_employees`** (`hrms/hrms/api/__init__.py:62`) is the widest thing in
  the repo: `frappe.get_list` with **`limit=999999`, no filters and no company scoping at
  all**. It lives in the vendored `hrms` app, so an audit scoped to `alvoraa_portal/`
  never sees it.
- **`Appraisal.employee_image`** (`appraisal.json:177`, `fetch_from: "employee.image"`)
  **copies the photograph onto every Appraisal record**. Employee permissions stop
  mattering: anyone who can read an Appraisal has the face.
- `/api/resource/Employee?fields=["image"]` returns it to any role with Employee read,
  because **`image` is permlevel 0** and `employee_field_rights.py` never raises it.

**What follows.** Nothing in the code changes — this slice still adds no reader and widens
no scope, and `01c` is right that **the exposure is created by the upload, not by us**. But
**078-PRIV-1's sentence is the product's promise to the employee, and it is now wrong in a
second way**: it must also cover appraisals, and a reviewer checking the sentence against
"the ten in §0(1)" will sign off something incomplete. I recommend PRIV-1's wording be
settled against the 20-item list in §2.3, and that AC-8 cite that list. This is a sentence,
not a feature — but it is the sentence the whole privacy position rests on.

### 0.3 The field picker: I agree with the coordinator's reading of Surbhi's words

Surbhi said *"whatever field is selected from the organisation settings page will be
visible"*. The coordinator read that as "the setting decides, not a list we hardcode", with
the picker still offering only the server allow-list. **I agree, and here is the reason
that is not just caution.**

`employee_field_rights.py` deliberately locked **write** on 35 Employee fields and left
**read open** (`01a` F12, and I confirmed it: `image`, `cell_number`, `personal_email`,
`company_email` and the emergency-contact fields are all at permlevel 0 on purpose, and the
module's own docstring calls level 0 "the employee's own details"). So a permission level
cannot refuse a read. If the picker offered every Employee field, ticking `bank_ac_no` or
`date_of_birth` would **work** — the only thing standing between a hurried tick and 403
people's dates of birth on a structure page is the allow-list constant. That is abuse case
A2 in `01c` §5, and permlevel does not save us because HR Manager holds read at level 1.

A picker that offers a field it will then refuse is also the failure 078-SEC-7 names: *"a
setting that silently does nothing is how a tenant comes to believe a field is editable."*

So: the setting decides, from a closed list of ten. One sentence from Surbhi changes it.

### 0.4 The nine "already at permlevel 2" profile fields are not at permlevel 2 on the bench

The spec says the nine Positions profile fields are "all already at **permlevel 2**
(`employee_field_rights.py` LEVEL_2, verified today)". The code says so. **The running site
does not.** On `ppj.localhost` there are **13 fields at permlevel 1** (bank, statutory,
`ctc`, `salary_mode`, `pan_number`, `payroll_cost_center` and the rest) applied by Property
Setters, and **no Property Setter has value 2 at all** — the LEVEL_2 locks have not been
applied on that site.

This does not change the design, because the allow-list is the control and not the
permlevel. It changes **testing**: a test that proves "a level-2 field is refused" will
pass on the bench for the wrong reason, or fail for a reason that is not this slice's. I
will note it, test against the constant rather than the permlevel, and not "fix" a site
this slice was not asked about.

### 0.5 A `has_permission` hook on `File` will not help. Do not add one. (AC-70 / Q5 answered)

Full trace in §5.1. The short version: **no.** The private-file download path calls a
plain module-level function in `file.py`, never `frappe.permissions.has_permission`, so the
hook-reading code at `frappe/permissions.py:491` is never entered for the `File` doc.
078-SEC-4's conditional — *"if it does, add the hook and this becomes a real boundary"* —
**does not fire.** The ticked-type list stays defence in depth, R1 stands as written and
accepted, and nothing in the product's wording may imply otherwise.

### 0.6 `portal.js` had 83 commits in 14 days. That is the biggest delivery risk in this slice.

Not `hrms-employee.html` (1 commit in 14 days) — **`portal.js`**, and `panels.css` at 46.
This slice touches both heavily, for six weeks of screens. §9 is the plan.

### 0.7 Declining 078-SEC-3 costs nothing at DTC today, and here is the reason it is true

Surbhi declined SEC-3's HR-roles-only gate: the documents section follows whoever can read
the Positions page (Decision 4). **At DTC that audience is HR Manager and System Manager and
nothing wider** — the shipped `DocPerm` default, with no tenant override `[STATED BY SURBHI]`.
Dev measures the same two roles; PPJ is narrower still, at System Manager alone.

**The reason that makes the decision safe, not just the conclusion:** both of those roles
already hold plain read on `Employee`, and `01c` §10 found the three existing
`Employee Document` readers are all self-scoped or HR-scoped. So **every reader who can see
the documents section can already open every one of those files from Desk today.** The
section adds a faster door, not a disclosure. That is exactly `01c` §0(2)'s own argument —
and with the audience confirmed, it holds without SEC-3 doing any work.

**So I am not re-arguing SEC-3.** Decision 4 is built as decided, and declining the gate
changes nothing in practice today.

**What keeps it true is the tripwire, so here is where it lives and who runs it.** `01c`'s R1
is *"if any tenant grants Positions read to a non-HR role, revisit before that tenant goes
live."* **It does not fire for DTC.** It stays in place for every future tenant, and it needs
a home, because a risk with no owner is the accident `01c` §12 warns about. Two places, and
I will build the first:

1. **On the page, at the moment of the tick — the one I build.** AC-86's amber line on the
   settings card names **the actual roles** holding Read on `Alvoraa Position`, not a count.
   One query for enabled users holding that permission. So a System Manager ticking a
   sensitive document type sees *"HR Manager, System Manager"* — or sees a third role appear
   the day somebody widens it. **This is the only automatic detection R7 leaves us**, since
   one-click tag removal was refused, and it is why I will not trade the wording away.
2. **At tenant go-live, by a human.** The check is "read the roles on `Alvoraa Position` for
   this tenant before switching the documents section on." That belongs on the tenant
   go-live checklist, owned by whoever provisions a tenant — **not in CI**, because CI
   cannot see a tenant's `Custom DocPerm` rows, and once any custom row exists Frappe ignores
   the shipped rows entirely (`frappe/permissions.py:528-529`). I am **not** adding a gate
   for this (078-SEC-16, OPS and `01c` all deleted theirs); I am naming the owner, because
   that is the part that was missing.

**R1 itself is unchanged and still accepted:** a private-file URL fetched directly still asks
only the parent Employee's read permission, and §5.1 proves no hook closes it. What §0.7
settles is that **the audience for whom R1 would matter does not exist at DTC today.**

---

## 1 · Where I am on the cost ladder, and why every cheaper rung was rejected

`.claude/context/no-over-engineering.md` §1. The spec's own table is sound; I am restating
it with my own verdict, and I disagree in two places.

| # | Piece | Rung | Why the rung below fails |
|---|---|---|---|
| 1 | Faces on the Positions cards and table | **1 · already there** | `ocAvatar` (`portal.js:276-279`, read today) already returns `<img class="av" src=p.image>` when a photo exists. Nothing to build but one field on an existing read |
| 2 | `image` on the Positions read | **3 · customisation**, one field | `register.py:302-306` already joins `employee.reports_to` and `employee.status` through link fields. `employee.image as image` is one more string in the same `fields` list — **no extra statement, no extra query**. Confirmed by reading the call |
| 3 | The 48 px copy | **4 · new code**, one handler | The measured exception, and it is `07` §3.2's number, not mine: 16 faces at the stored 512 px size is **~720 KB / ~14 s on Slow 3G**; at 48 px it is **~48 KB / ~1 s**, against a 2.5 s budget. Two orders of magnitude. Frappe's `make_thumbnail` writes to `public/` (`file.py:561`) and is the wrong tool |
| 4 | The photo upload endpoint | **4 · new code** | There is no non-Desk upload path for `Employee.image`, and a frontline worker has no Desk. I copy `field_app_photos.py:84-114` line for line — I read it today: length of the **string** first, then decode, then magic bytes, then a private `File` insert, then `db_set`, with the whole thing wrapped so a bad photo never takes the parent record down |
| 5 | The mini-profile read endpoint | **4 · new code** | No endpoint returns a chosen subset. A permission level cannot do it (§0.3). Reuses `register.may_view()` and `access.employee_in_scope` — **I write no new scope helper**, because `scripts/check_scope_traps.py` already fails CI on exactly that mistake |
| 6 | The document streaming endpoint | **4 · new code** | `Employee Document` is `istable: 1`; a rule at the row never reaches the file (§5.1). Copies the payslip-PDF pattern at `hr_api.py:2184` |
| 7 | The four settings keys | **2 · configuration** | `ACCESS_GRANTING` is a `frozenset` of four keys at `settings.py:89-94` — read today. Four more names join it and inherit System-Manager-only, the logged refusal and the `Version` row. Rung 3 (a Check on `Employee Document Type`) is refused on the permission row: that doctype ships `write: 1` to HR Manager, who **is** the DTC Positions audience. Rung 5 buys a permission surface, a migration and a list view and does nothing a key with a `Version` row does not |
| 8 | The settings card and three pickers | **4 · new code**, one card | Organisation Settings already has ten `pf-card`s in one settled pattern. Nothing renders a tag-and-picker today |
| 9 | The seat page | **4 · new code** | §6 — and it retires a modal three CI scripts name |
| 10 | The mini profile drawer | **3 · customisation** | `.emp-drawer` exists and is already shared by the payslip, the scorecard and goals (`drawers.html:111-114`). It needs four ARIA attributes and two handlers, copied from `#payslip-drawer` two lines above it at `drawers.html:99`, which already has `role="dialog" aria-modal="true" aria-labelledby` |
| 11 | Pre-onboarding | **3 · customisation** under §0.1(c) | Frappe's `Web Form Request` owns the token; we own one hardened page on the `enrol.html` pattern and one token-checked upload endpoint. **A rung cheaper than the spec's rung 5**, because Frappe now owns the token machinery. Option (a) is rung 2 and breaks SEC-9; option (b) is rung 4–5 |
| 12 | The one new DocType | **5 · new DocType**, and I accept it | A Web Form needs a doctype; `Employee` is refused (a guest-writable Employee lets strangers consume the naming series and trips the absence-backfill trap, which is already logged); nothing shipped means "has told us about themselves, not yet an employee" |
| 13 | The document-open record | **3 · customisation** | `Alvoraa Photo Access Log` exists, already reads to System Manager and HR Manager only, and `field_app_access.log_photo_view` already applies the three narrowing rules. Two columns and one optional link |

**Where I disagree with the spec's ladder:** item 11 is rung 2, not rung 5, if Surbhi takes
§0.1(a). And item 2 is rung 3, not "extend" — worth saying because it means **no migration
and no new query**.

---

## 2 · Functional impact — all four dimensions

### 2.1 Cross-module reach, with every caller grepped

| App | Touched how | Verdict |
|---|---|---|
| **`alvoraa_portal`** | `public/js/ess/portal.js` (`ocAvatar`, `ocNodeCard`, `posFew`, `posPaintTree`, `posPaintList`, the drawer, the seat editor, a new My-Profile panel, a new settings card), `public/css/ess/panels.css`, `templates/includes/ess/parts/{positions,org-settings,drawers,home}.html`, `hooks.py` (one `Employee.on_update` entry), new `my_profile.py` / photo endpoint / document endpoint / pre-onboarding endpoints, `Alvoraa Photo Access Log` + 2 fields, `field_app_limits` reused unchanged | **Heavy** |
| **`hrms`** | `alvoraa_org_structure/register.py` (one field on one read), `settings.py` (four names into `DEFAULTS`, `LABELS`, `ACCESS_GRANTING`), `api.py` (OPS-6 batching, OPS-20 cap), `alvoraa_employee_documents` **read only** | **Moderate** |
| **`erpnext`** | **Read only.** `Employee` lives in **erpnext**, not hrms — `erpnext/setup/doctype/employee/employee.json`, 109 standard fields, confirmed in the image. Read and written through the ORM. **No upstream edit** | **None** |
| **`frappe`** | **Read only**, plus two System Settings values set by configuration: `max_file_size = 5` (OPS-24) and the guest-upload pair (OPS-25). Plus, if §0.1(a): one `Web Form` and one `Web Form Request` record — data, not code | **None** |
| **`alvoraa_goals`** | **Not touched.** `goals_api.py:248` and `:1045` already select `Employee.image` and emit it as `avatar`. Faces appear there the day photos exist, with no change by us. Two of the 20 surfaces | **None** |
| **`alvox_compensation`** | **Not installed** (memory, 25 Sep 2026). Not touched | **None** |
| New app / new module / new workspace | **None.** Nothing here needs one | — |

**Callers grepped, for every function whose behaviour or signature I will change:**

| Function I touch | Callers found | How I keep them safe |
|---|---|---|
| `ocAvatar(p)` (`portal.js:276`) | **3**: `portal.js:321` (`ocNodeCard`), `portal.js:4410` (the people list) | I change its **body only** — initials in the circle, the photo layered over at `opacity:0` until it loads. Signature unchanged, so both callers get the loading, failed and printed states for free. This is the one change in the slice that pays for itself three times |
| `register.position_table` → the assignment read (`register.py:299-324`) | the Positions page and `plans.table_view` | One more field in an existing `fields` list. No signature change, no new statement |
| `settings.get_cover_settings` / `set_cover_setting` | `01a` F16: **whitelisted and no screen calls `get_cover_settings` today** — confirmed | Four keys join the existing tables. I add no function and change no signature, as `parallel-work.md` §6 requires for shared settings files |
| `access.employee_in_scope` (`access.py:289-301`) | existing HR readers | **Called, never changed.** It fails closed and its docstring records the trap |
| `field_app_access.log_photo_view` | `Employee Checkin.onload` (`hooks.py:171`) | I do **not** change it. I add a sibling that writes the same table with `source = "Employee document"`. Changing it would alter check-in logging, which is not this slice |
| `Employee.on_update` chain | 4 handlers today (`hooks.py:180-189`): `invalidate_portal_context_cache`, `block_devices_for_leaver`, `block_phones_for_unlinked_login`, `manager_scope.on_employee_update` | **One line added at the end with a comment**, per `parallel-work.md` §6. Guarded by `doc.has_value_changed("image")` so the other four are untouched on a normal save |

### 2.2 Persona impact

| Surface | CXO (all companies) | HR Manager (their companies) | Employee (own record) |
|---|---|---|---|
| **My profile** | Own record, like anybody | Own record, like anybody. An HR login with no Employee row gets **S1-E**, not the 500 that happens today (`01b` E2, reproduced) | **The whole point.** Their photo, six details, a link to `/update-password` |
| **Faces on the chart** | Recognises a face across six stores | Same | **Appears on it, cannot open it.** Gets faces on the Organisation page instead — which is where the 3G budget actually binds (OPS-20) |
| **Mini profile** | Opens it | Opens it | **Never opens it** |
| **Documents section** | Follows Positions read (Decision 4) | At DTC this is them | **Never.** Sees their own in My profile, as today |
| **Settings card** | Only if they hold System Manager | **Absent**, never greyed | Absent |
| **Pre-onboarding** | — | Issues the invite, reviews, creates the Employee **by hand** | — (not an employee yet) |

**The asymmetry, said plainly:** the employee whose face and documents appear on the
Positions page cannot open that page. That is deliberate, and it is exactly why PRIV-1 (the
notice) and PRIV-5 (the access record) are not optional — they are the only two ways a
person who cannot see the surface can ever find out what happened on it. I will build both,
and I will not trade either away for scope.

### 2.3 The twenty surfaces that already return `Employee.image`

Verified in this worktree today. Scope column is the code's own, not an assumption.

| # | Endpoint | File:line | Scope as the code stands |
|---|---|---|---|
| 1 | `frame_api.get_frame` | `frame_api.py:117` | own Active record |
| 2 | `home_api.get_home` | `home_api.py:132` | own record |
| 3 | `team_api.get_team` | `team_api.py:48, 229, 242` | direct reports + HR scope; **`ignore_permissions=True`**; cap 50 |
| 4 | `time_api.get_time` | `time_api.py:437` | own record only — image withheld for others (`:473-479`) |
| 5 | `staff_api.get_staff_list` | `staff_api.py:64, 284` | **the widest authorised one**: HR company+branch scope, else own-company; `DIRECTORY_SCOPE_FOR_EMPLOYEES = "own_company"` (`:127`); Active; feature-gated; cap 50 |
| 6 | `hr_api.get_portal_context` | `hr_api.py:306, 349` | own record; `allow_guest=True` with a Guest short-circuit; **Redis-cached 1 h** |
| 7 | `hr_api.get_manager_dashboard` | `hr_api.py:539, 542` | reports + HR scope; **`ignore_permissions=True`** |
| 8 | `hr_api.get_employee_scorecard` | `hr_api.py:1169` | effective manager, or HR via `_hr_target_employee()` |
| 9 | `hr_api.get_employee_detail_for_manager` | `hr_api.py:1502` | direct manager, or HR scope |
| 10 | `hr_api.get_payslips` | `hr_api.py:1960` | own record; payroll feature gate |
| 11 | **`hr_api.get_checkin_status`** | `hr_api.py:1783` | own record — **returns the whole employee dict; the word `image` never appears here** |
| 12 | **`hr_api.get_expense_claims`** | `hr_api.py:2207` | own record — same whole-dict shape |
| 13 | **`goals_api.get_portal_context`** | `goals_api.py:248, 257` | own record — **emitted as `avatar`** |
| 14 | **`goals_api.get_team_goals`** | `goals_api.py:1045, 1083` | direct reports only — **emitted as `avatar`** |
| 15 | `org_structure.api.get_children` | `api.py:177, 216` | reach rule; company only if the caller passes it. **No caller anywhere in the repo** |
| 16 | `org_structure.api.my_view` | `api.py:555` | own, or reach rule |
| 17 | `org_structure.api.subtree` | `api.py:550` via `_card` | reach rule. Reach is **unlimited for anyone with a direct report** by default (`settings.py:58`, applied `api.py:838`) |
| 18 | `org_structure.api.search_people` | `api.py:718` | `_search_scope()`; Active; capped |
| 19 | **`hrms.api.get_all_employees`** | `hrms/hrms/api/__init__.py:74` | **none beyond Frappe's Employee read. `limit=999999`, no filters, no company scoping** |
| 20 | **Desk `organizational_chart.get_children`** | `organizational_chart.py:27` | **none beyond Employee read.** Caller-supplied `company`, no reach rule |

**Four more that are not endpoints:** `Appraisal.employee_image` (`appraisal.json:177` —
the photo is **copied onto a submittable record**, so Employee permissions stop applying);
the Employee CTC Break-up report (`employee_ctc_break_up.py:270-277`); the birthday and
anniversary reminder emails (`employee_reminders.py:168, 180` — the photo's **URL goes into
an email body** sent to colleagues, and **`send_work_anniversary_reminders` is 1 on dev
today**, §0a, which closes `01c`'s open question S2 with the answer "yes, it is on"); and
`/api/resource/Employee?fields=["image"]`, open to any role with Employee read because
`image` is permlevel 0.

**I widen none of these and I add no reader.** I say this so that PRIV-1's sentence is
written against the real list and so nobody reads "ten" again.

### 2.4 HRMS domain impact

| Domain | Impact |
|---|---|
| **Org structure** | The whole Positions page; the Organisation page gains faces as a consequence. The only domain this slice is about |
| **Attendance** | **Indirect and the one that matters.** The document endpoint, the table's 125 near-simultaneous face requests and the 9 a.m. biometric punch burst draw from **the same 8 gunicorn slots** (4 workers × 2 threads, `docker-compose.app.yml:261-262`). This is why OPS-19 exists and why I will not skip it |
| **Payroll** | **Not touched.** `rule_set_fields()` (`employee_field_rights.py:125`) is read **as a deny list** only. Nothing in the slice writes a payroll field |
| **Appraisals** | Faces appear, because `Appraisal.employee_image` already fetches them. No code change — and it is a privacy-notice item, not a build item |
| **Goals / learning** | Faces appear. No code change |
| **Leaves** | Not touched |
| **Onboarding** | The joiner's form sits **one step before** `Employee Onboarding`, which is untouched. SEC-12: a submission never becomes an Employee by itself, and **no joining date comes from the form** — the absence-backfill trap is already logged and is the reason |

---

## 3 · Verdict on each of the seven non-functional dimensions

| Dimension | Verdict | Why, in one line each |
|---|---|---|
| **Performance** | **Degrades, bounded on purpose** | First paint goes from 16 requests to 32 (16 data + 16 faces at 48 px, **~48 KB / ~1 s Slow 3G**, `07` §3.2). The table is the real cost — **215 faces over 120 rows, ~125 arriving at once on 3G** — and OPS-19 bounds it to the first 25 rows. The mini profile is one extra call per open. `register.position_table` stays **two queries for 403 people**. Without OPS-19 and OPS-21 this would be "degrades, badly"; with them it is a measured, defended cost |
| **Scalability** | **Neutral to improves** | The query count stays flat in headcount (OPS-6 batches `api.py:177`'s existing one-read-per-person into one `get_all`, which is a straight improvement on today). Nothing new grows with months or transactions except documents, and OPS-24's 5 MB cap plus OPS-26's per-token byte cap bound that. **No queue, no worker, no cache, no bucket, no CDN** — and I am not proposing one |
| **Security** | **Degrades, knowingly, in one place** | Six new permission surfaces: the photo upload (own Active record only), the My-Profile save (permlevel-0 closed list), the mini profile (`may_view` + `employee_in_scope`), the document endpoint (five ordered checks), the settings setters (`ACCESS_GRANTING`), and the first **public write path in the product's history**. The honest degradation is **R1**: a private-file URL still asks only the parent Employee's read permission, and §5.1 proves no hook closes it. Everything else is net-neutral or better |
| **Reliability** | **Improves** | The thumbnail handler catches everything and never fails an Employee save (OPS-13), with a renderer fallback **thumbnail → full photo → initials**. The upload has a 15 s timeout whose message admits the write may have succeeded. And it **fixes a live defect**: My profile for an HR login with no Employee row throws today (`01b` E2) |
| **Maintainability** | **Degrades slightly** | ~9 new server functions, 2 new DocType-level changes, one new DocType, and a lot of new `portal.js`. Two things hold it: `ocAvatar` is changed **once** for five states, and the mini profile is **one component** used by Positions and the seat page — the spec has an AC that fails if the field list exists twice, and I will honour it |
| **Data integrity** | **Neutral** | No schema change to `Employee`. `hr_api.get_portal_context` is Redis-cached for an hour and carries `image`, and `invalidate_portal_context_cache` is **already first** in the `Employee.on_update` chain, so a photo change already busts it — I verified the ordering. OPS-15: replacing or clearing a photo deletes the old thumbnail row **and its bytes** in the same operation, or we grow one orphan per re-upload for ever |
| **Compliance / privacy** | **Degrades, and this is the dimension to argue about** | The slice creates the trigger for 24 surfaces to start showing faces, and invites strangers to upload identity documents. Four things make it defensible: PRIV-1's notice **before** the control, PRIV-2's removal (the employee's route out), PRIV-5's access record, and PRIV-7's off-by-default switch that cannot be turned on without a deliberately set retention period. **Two counsel questions are open** and R4 is labelled dangerous debt |

---

## 4 · How each SEC, PRIV and OPS item will be met — by name

### 4.1 The 16 SEC items

| Item | How it will be met |
|---|---|
| **078-SEC-1** closed Positions allow-list | `POSITIONS_PROFILE_FIELDS` as a module constant, **ten** names (the spec drops "Work phone" — see §8, D1). The setter intersects the posted list with it and refuses an off-list name; the **reader** intersects again, so a value written straight into `DefaultValue` by any other route produces nothing. Three tests, and the third — `frappe.db.set_default` then read the profile — is the one that survives a future UI |
| **078-SEC-2** scoped, absent not blank | `register.may_view()` then `access.employee_in_scope(employee_id)` (`access.py:289-301`). **I write no new scope helper and no `dict(permitted_employee_filters(user), name=chosen_id)`** — `scripts/check_scope_traps.py` already fails CI on that. A field the reader may not see is **omitted from the dict**, never set to `""` or `"hidden"`. A caller with no companies is refused |
| **078-SEC-3** documents gated on HR roles | **Declined by Surbhi; the section follows Positions read (Decision 4), and §0.7 shows that costs nothing at DTC today** — the audience is HR Manager and System Manager, both of whom can already open every one of those files from Desk. I build Decision 4 as decided and I do not re-argue the gate. I do build the mitigation the spec asked for in exchange (**AC-86**): the amber line names **the actual roles** holding Read on `Alvoraa Position`, not a count, so a widening is visible at the moment of the tick. **R1's tripwire does not fire for DTC and stays in place for future tenants, with its owner named in §0.7** |
| **078-SEC-4** ticked-type check, no false claim | Own whitelisted endpoint, checks **in order**: page permission → `employee_in_scope` → row's `parent` is that employee → row's `document_type` is ticked → plan is on. The browser never receives a `/private/files/` URL. **§5.1 answers the half-day question: no `File` hook fires, so this stays defence in depth.** No product copy will say or imply the un-ticked types are protected, and I will write the direct-GET test that records the real behaviour rather than asserting a refusal that does not happen |
| **078-SEC-5** four lists are access-granting | Four names join the `ACCESS_GRANTING` frozenset at `settings.py:89-94` and inherit `_set_access_setting`'s behaviour at `settings.py:170-208`: System Manager only, anyone else refused and logged, a `Version` row in the same transaction. **No `show_in_positions` Check on `Employee Document Type`** — that doctype ships `write: 1` to HR Manager. A test asserts the field does not exist. **This is where I disagree with OPS-5 in writing, and I side with SEC-5**: the reason is a permission row, not taste |
| **078-SEC-6** photo upload | Copy `field_app_photos.py:84-114` exactly, in this order: `len()` of the **string** before any decode; `base64.b64decode(validate=True)` in a try; magic bytes; re-encode to JPEG longest-edge 512 quality 82 with Pillow (**12.3.0, already in the image, measured**) — which does the resize and the metadata strip in one call; `File` insert with `is_private=1`; `db_set`. **Writes only to the caller's own Active Employee.** Not `make_thumbnail` |
| **078-SEC-7** My-Profile write list | `MY_PROFILE_WRITE_FIELDS`, **six** permlevel-0 names. The server intersects the tick with the constant **and** `has_permlevel_access_to(..., "write")`, so a level-1/2 field cannot be written even if someone edits the key. `refuse_own_locked_change` (`employee_field_rights.py:140`) already refuses the rest. Blood group and marital status stay off. **No new permission machinery** |
| **078-SEC-8** Active filter | Every new "who am I" lookup resolves the Employee with `status = "Active"`, the shape `_get_employee` already uses at `hr_api.py:300-308` and `field_app_access._viewer` at `:32`. A login with no Active Employee gets **S1-E**, never a 500 and never somebody else's record |
| **078-SEC-9** the token | **This is the item §0.1 changes, and option (c) meets SEC-9 in full.** Frappe's `Web Form Request` supplies a 32-byte `secrets.token_urlsafe` key, `expires_on`, `first_used_on` single-use, a `has_reference` check that stops a key being walked onto another candidate's document, and a `Website Manager`-only table Guest cannot enumerate. Our own page carries the token in the **URL fragment** and posts it in the **request body**, so it reaches no access log, no `Referer` and no synced history — which is SEC-9's actual requirement. The rate-limit key is the **hash**, via `field_app_limits`. **Only server code mints a key.** Under option (a) the fragment rule is broken and I would record it as a residual risk; under (b) I build the schema and the state machine by hand |
| **078-SEC-10** rate limits | `field_app_limits._limited` / `_limited_by_address` (`field_app_limits.py:43-48`), unchanged. It already hashes the argument, because Frappe writes the limiter's key value into Redis in clear, and it already exposes `__alvoraa_limit__` so a table test can read every endpoint's limit off the function. **No new limiter, no CAPTCHA, no new dependency** |
| **078-SEC-11** pre-onboarding uploads | **Our own token-checked upload endpoint**, because `upload_file` is token-blind (§0.1). JPEG/PNG/PDF only, **magic bytes**, per-file and per-submission byte ceilings server-side. Images re-encoded per SEC-6. **PDFs not re-encoded**, so: private, `Content-Disposition: attachment`, never inline. Files attach to the **new DocType, never `Employee`**. We do not scan for malware and will not claim we do (R3) |
| **078-SEC-12** never auto-creates an Employee | The review screen has a button a signed-in HR user presses. **No joining date from the form or from the submission's dates.** A test asserts no `Employee` row appears and the naming series does not move |
| **078-SEC-13** no existence oracle | `get_web_form_request()` raises the same `PermissionError` for a missing and for an unknown key, and `LinkExpired` for used and for expired. Our page renders **one** J-E1 answer for missing, unknown, expired and cancelled, and the narrower "already used" answer only for a key that was genuinely burnt — which is SEC-13's own allowance, *"a deliberate, narrower disclosure to a person who already held a live token"*. Byte-identical-response tests for the first four |
| **078-SEC-14** Guest reads nothing | New DocType ships **no Guest permission row**; HR roles read-only, System Manager full. **No Web Form onto `Employee`.** SEC-14 defaults against a `login_required: 0` Web Form *"unless the engineer can show the token check cannot be bypassed on that path"* — **§5.2 is that showing**, and under option (c) the question does not even arise, because no Web Form renders: our page is the only public surface. I verified the obvious bypass too — `frappe/client.py` grants `allow_guest` to nothing but `get_time_zone`, and `frappe/api/v1.py:44-47` inserts without `ignore_permissions`, so Guest needs explicit create permission it will not have. Checklist rows: public pages **one**; Guest access **token-bound only**; self sign-up **none**; new roles **none** |
| **078-SEC-15** hardened public page | Copy `www/enrol.py:12-28` and `www/enrol.html:1-20`. `no_cache`, `X-Robots-Tag: noindex, nofollow` as header **and** meta, `Cache-Control: no-store`, `referrer: no-referrer`, **no external host for any asset**. I extend the nearest existing `scripts/check_*` text check rather than adding a gate |
| **078-SEC-16** no new `ignore_permissions`, no new gate | The only two are the `File` insert (the pattern at `field_app_photos.py:107`) and the `Version` insert (which has no create permission for anyone, `settings.py:205`). New files start at **zero** in the ceiling `test_portal_security_010` already holds. **Nothing added to `ci.yml`** |

### 4.2 The 9 PRIV items

| Item | How it will be met |
|---|---|
| **078-PRIV-1** truthful notice | One translated sentence through `drT()`, rendered **before** the upload control in the DOM, with a Hindi entry. **Written against §2.3's twenty surfaces, not ten.** It must name three things the design's draft does not: the **staff directory** (the widest, company-wide), **appraisals** (because `Appraisal.employee_image` copies the photo onto a submittable record, so Employee permissions stop applying), and **emails** — because `send_work_anniversary_reminders` is **1 on dev today** (§0a), and `employee_reminders.py:168, 180` puts the photo's URL into a mail body sent to colleagues. `01c` S2 could not check whether that reminder was on anywhere; **it is, and the notice would have been false without this.** No notice-versioning object, no consent ledger — the lawful basis for an employee photo is the employment relationship, not consent |
| **078-PRIV-2** the employee may remove | The same write, cleared, plus deleting the stored `File` and the 48 px row **and their bytes**. Every surface falls back to initials with no broken image. **Not** the per-person visibility toggle that was refused |
| **078-PRIV-3** purpose limitation | A static test assertion in the slice's own module: `Employee.image`, the thumbnail field and the submission's upload fields appear in no module under an AI or model path; nothing reads `alvoraa_checkin_photo` into `Employee.image` or the reverse. No matching, no scoring, no emotion analysis, no chart-as-image download. Three greps in a test, not a gate |
| **078-PRIV-4** minimisation | The mini profile is **its own call**, made when a profile opens. **No personal field joins `position_table`** beyond the photo URL — a test asserts the response keys are unchanged. The chart and table request the 48 px copy; the full picture only on an actual enlargement. And the query-count assertion (same for 20 as for 400) is reused as a privacy gate, because a per-person read is how a payload quietly grows |
| **078-PRIV-5** the access record | Two fields on `Alvoraa Photo Access Log` (`document_type` Link read-only, `source` Select read-only) and `checkin` made optional. Permissions unchanged. The three narrowing rules copied from `field_app_access.py:160-172`: only when there is something to look at; **never a person looking at their own**; **one row per viewer per document per day**. It holds **no file, no file URL, no document number and no value from the document** |
| **078-PRIV-6** retention is a setting | `alvoraa_joiner_retention_days` as a `DefaultValue` key read by a daily job. Deletes files and row for submissions past the period that never became an Employee; **legal hold wins**, as `field_app_photos.py:136-138` already does; logs a **count**. **`0` or unset means the feature is off, not keep-for-ever** — I will not copy `field_app_photos.py:133-135`'s semantics, because counsel's 18 Sep policy prohibits indefinite retention in so many words |
| **078-PRIV-7** ships off, needs a deliberate period | One entry in `ORG_SWITCH_NEEDS` / `_switch_missing` (`hr_api.py:3278-3306`). The precondition is *a `Version` row exists for the retention key and the current value is a positive number* — which a left-alone default cannot satisfy, because a default writes no `Version` row. **Shipped default unset, not 90.** The refusal says: "Set how long a joiner's details are kept before you turn this on." Four tests, including the one that sets the key with `frappe.db.set_default` and proves the switch **still** refuses |
| **078-PRIV-8** the joiner's notice | Design J1: notice **before the first question**, not under a tick at the end. Renders the **configured** period, never a literal 90. Names who sees it, says no account or password is involved, and gives a real contact **from tenant settings — the screen refuses to render with a blank contact**. Hindi at parity through `drT()` |
| **078-PRIV-9** fewest fields | `JOINER_FIELDS` as a closed server constant, **with SEC-1's deny list applied to it**: no bank account, no salary, no CTC, no statutory identifier as a typed field. An identity number arrives as a ticked document type — a file under HR's verification flow, not a searchable column on a guest-writable table |

### 4.3 The 38 OPS items

I adopt **36 of 38**. I disagree with **OPS-5** (settled above, SEC-5 wins) and I partly
disagree with **OPS-25** (the upload must be ours regardless of which form we use, §0.1).

| Items | How they will be met |
|---|---|
| **OPS-1** faces in the mini profile, initials on cards | **Superseded by Surbhi's decision** — faces at 24 px on the cards. OPS-1's concern is answered instead by **OPS-2 + OPS-21**: the 48 px copy and the two constants bring 16 faces to ~48 KB. I record the disagreement as resolved by measurement, not by overruling DevOps |
| **OPS-2, OPS-12, OPS-13, OPS-14, OPS-15, OPS-16** the thumbnail | One handler at the **end** of `Employee.on_update` (`hooks.py:189`), guarded by `doc.has_value_changed("image")`, one Pillow call, in the request. **No queue, no job, no service.** It catches everything, writes Error Log and leaves no thumbnail; the renderer falls back thumbnail → photo → initials. JPEG/PNG/WEBP accepted, all stored as JPEG 512/82. **No `pillow-heif`** — Pillow 12.3.0 cannot read HEIC (measured), so a HEIC file can be neither resized nor stripped, which is exactly why Surbhi's "HEIC refused" is the right call. Replacing or clearing deletes the old thumbnail and its bytes. **No backfill, no patch** — 0 photos at PPJ, 0 at DTC |
| **OPS-3, OPS-17, OPS-27** nginx | **No change to `deploy/nginx.conf` in this slice.** One nginx container serves dev *and* production from that file, and a dev push restarts the live proxy. The form needs none either: `location /api/` already carries 120 r/m per IP, burst 30. The form page stays out of the compressed-HTML list (the BREACH rule). If this is ever revisited it is `X-Accel-Redirect`, behind `scripts/check_nginx_parses.sh`, **in its own slice** |
| **OPS-4, OPS-22, OPS-23** the document endpoint | `frappe.local.response.filecontent / .filename / .type = "download"`, the payslip pattern at `hr_api.py:2184`. **One file per call, no "all documents" call**, named by its `Employee Document` row and never by a file URL. `@rate_limit(limit=60, seconds=3600)` per user. **I say the cost out loud: the whole file sits in one of 8 worker slots for the length of the download** — which is why OPS-24 is not optional |
| **OPS-6** batch the photo read | One `get_all` keyed by employee for the chart and the table, replacing `api.py:177`'s per-person `frappe.db.get_value` and `_card`'s per-person read. A test asserts the query count is **the same for 20 employees as for 400** |
| **OPS-7, OPS-8** phone uploads, metadata | Employees upload from phones, so OPS-7 is P1: the cap and the resize are **server-side**, before any decode. The re-encode strips metadata for **every** accepted type, which Frappe's own strip does not (`file.py:813-819` runs for `image/jpeg` only) |
| **OPS-9 / OPS-36** assets | **No `assets.json` step in the release plan.** `refresh_bench_files.sh:55-68` copies bundles first and `assets.json` last, and `?v=` comes from `get_build_version()` reading that timestamp. The pipeline does it. The trap bites only a manual `docker cp` or a hotfix |
| **OPS-10, OPS-11** no new moving parts, `portal.js` weight | No container, queue, worker, cache, CDN or bucket. The 1.12 MB `portal.js` already misses the 3G budget — **standing debt, not this slice's to fix**, and I will not quietly start fixing it |
| **OPS-18** repaint re-requests every face | Accepted at this size. Private files go out with **`Cache-Control: no-cache`** (werkzeug, Frappe passes no `max_age`), so every `posPaint()` revalidates: 304s, ~30-50 ms of Python each, at 16-29 faces. Zoom does **not** repaint; expand, filter and arrange do. **This is the second reason the table needs bounding** |
| **OPS-19** bound the table | **IntersectionObserver with a 200 px margin**, not `loading="lazy"`. 215 faces over 120 rows; the 3G lazy threshold is 2,500 px and reaches ~60-70 rows, and `http2 on` lets them all leave at once. ~15 lines, and it is the option that keeps the wall-chart print path honest, where a browser-threshold lazy image prints as a blank circle |
| **OPS-20** the Organisation page | **Surbhi has decided: apply the 3-name cap here too.** `ocNodeCard` (`portal.js:309`) lists every person today — one expansion is 94 boxes and 185 people. This is the employee-facing page, so this is where the ≤ 2.5 s / 3G budget actually binds |
| **OPS-21** the two constants | `POS_OPEN_DEPTH` stays 1, `POS_NAMES_SHOWN` stays 3, asserted in `scripts/run_dom_tests.js` — **a suite that already runs in CI. Nothing added to `ci.yml`.** §7 has the detail, including a trap in the existing harness |
| **OPS-24** `max_file_size = 5` | Site-wide, and I will say so out loud on the release note: it applies to every upload on the site, not only documents. Today it is 0 → Frappe's 25 MB default, while nginx allows 50 MB |
| **OPS-25** guest-upload switch | **Both values in one change, never one then the other** (AC-103, AC-104). And I take OPS-25's preferred half: **the uploads go through our own token-checked endpoint**, because `upload_file` never looks at the token (§0.1). Whether the switch needs to go on at all depends on §0.1's decision |
| **OPS-26, OPS-30** per-token limits and disk | `field_app_limits`, keyed on the hash: 20 link opens/hour, 3 submits/24 h, 12 uploads/hour, ≤ 6 files and ≤ 20 MB per token, 7-day single-use link. Plus OPS-24's 5 MB and the hourly disk alarm that already runs (`check_workers.sh`, fail below 20 GB). **The per-token byte cap is the one that matters**: without it, 120 r/m per IP allows about 3 GB a minute at today's limit |
| **OPS-28, OPS-33** the invariant | Count submissions, links issued and refusals per day. The alert is **submissions > links issued**, or one token uploading more than 6 files. Files-tree size read at each release, not continuously. **No new tool** |
| **OPS-29** nothing stored before the token is checked | No partial row and no file before validation. **No document bytes in `localStorage`** — "your answers are kept on this phone" means the typed answers only. A joiner may be on a borrowed phone |
| **OPS-31, OPS-32** the restore proof | **One of the three preconditions is now met: free disk on the server is 111 GB, 43% used** (§0a) — clear of the deploy gate's 25 GB and the hourly alarm's 40 GB, with room for the 3.2 GB-per-tenant document estimate many times over. **Two remain**: one restore proved on dev from a backup with `--with-files`, written down; and a recorded yes/no on `BACKUP_BUCKET`, which is **not set** (measured) and which I am **not** proposing to set, because doing it quietly would move identity documents offshore without a privacy decision. All three sit in **Release, not in the acceptance criteria** — they gate the documents part shipping, not the build |
| **OPS-34** no thumbnail monitoring | Error Log plus "the faces are missing", which HR reports within a day. **Nothing built** |
| **OPS-35** migrations | Nothing special; `migrate=true` already on every branch deploy, maintenance mode wraps it. The settings keys need no migration at all |
| **OPS-37** build order | **Agreed. The photo upload ships and switches on first.** §8 |
| **OPS-38** pre-release check on dev | Open Positions on dev, count `<img class="av">` on first paint, confirm against OPS-21. **Nobody has ever rendered this chart** — the local bench cannot, because `Replacement Plan` is not migrated on `ppj.localhost`. 16 is arithmetic on measured data, not a render |

---

## 5 · The three half-day questions, answered

### 5.1 AC-70 / Q5 — does Frappe consult a `has_permission` hook on `File` when a private file is downloaded?

**No. Written down once so nobody re-litigates it.**

Read inside `hrlocal-bench`, Frappe **v16.33.1**, HEAD `988e54f3`, 8 Sep 2026. The chain is
short and I read all of it:

1. `frappe/app.py:163-165` — the **only** route: `/private/files/` →
   `frappe.utils.response.download_private_file(request.path)`. (Public `/files/` is plain
   static content with **no permission check at all**.)
2. `frappe/utils/response.py:294-306` — refuses Guest, then `find_file_by_url(path, ...)`,
   then `make_access_log`, then sends the file.
3. `frappe/core/doctype/file/utils.py:452-465` — `find_file_by_url` uses
   **`frappe.get_all`, which does not check permissions**, so `File`'s
   `get_permission_query_conditions` plays no part. The whole gate is `file.is_downloadable()`.
4. `frappe/core/doctype/file/file.py:896-897` — `is_downloadable()` returns
   `has_permission(self, "read")`. That bare name is the **module-level function in the same
   file at line 989**, not `frappe.has_permission`, and nothing in that file's imports
   shadows it.
5. `frappe/core/doctype/file/file.py:989-1027` — the real decision, in this order:
   Administrator → **not private** → **`doc.owner == user`** → **an explicit DocShare row**
   → **else delegate to the attached parent's `read`** → otherwise refuse.
6. `frappe/permissions.py:483-499` — `has_controller_permissions` is the **only** place in
   Frappe that reads the `has_permission` hook (`frappe.get_hooks("has_permission")`, keyed
   on `doc.doctype` plus a `"*"` wildcard). Its only caller is `get_doc_permissions`
   (`permissions.py:239`), reached only from `frappe.permissions.has_permission` when a
   `doc` is passed.

**Step 4 never enters step 6.** So a hook registered as `has_permission = {"File": ...}`
does not fire on this path. Note Frappe registers that very function as the File hook
itself (`frappe/hooks.py:147`), so it *is* the hook on Desk and REST paths — it is simply
also called as a plain Python call on download.

**Three consequences, and the third is the one that matters:**

- **A hook on the *parent* doctype does fire.** Step 5 calls
  `ref_doc.has_permission("read")` → `document.py:402-414` →
  `frappe.permissions.has_permission` → `has_controller_permissions`. So
  `has_permission = {"Employee": ...}` **would** close the URL.
- **Do not do that.** A `has_permission` hook on `Employee` runs on every Employee
  permission check in the whole product — 20 endpoints, the Desk, the REST API, payroll,
  attendance, appraisals. ALV-256 was exactly this shape two days ago and killed an Inbox
  part; and our seven existing hooks (`hooks.py:421-428`) are all on narrow,
  feature-specific doctypes for that reason. Hooking the HR master to protect one list of
  ticked document types is a rung-6 answer to a rung-4 problem. **I recommend against it,
  and I will not build it without Surbhi saying so explicitly.**
- **Two short-circuits make even that unreliable.** `owner` and DocShare are checked
  **before** the parent, so a hook on `Employee` would not stop the file's own owner or
  anyone with a share row. And `find_file_by_url` **loops over every `File` row with the
  same `file_url` and returns the first that passes** — so if the same file is attached to
  several documents, access to any one of them is enough.

**Verdict:** 078-SEC-4's conditional does not fire. **R1 stands exactly as `01c` §12 wrote
it and Surbhi accepted it.** The ticked-type check is defence in depth. No product copy may
say otherwise, and the test for AC-70 should **record** what a direct GET actually does
rather than assert a refusal that will not happen.

One useful side note for PRIV-2 and the guest uploads: because `owner` is checked third, an
employee can always fetch their own photo, and a guest-inserted file whose owner is
`"Guest"` is protected by `user != "Guest"` in that same line.

### 5.2 Q6 — can the token check be proved to run before a `login_required: 0` Web Form renders?

**Yes — and better than the question assumed.** §0.1 is the full answer. The short form:

- Frappe v16 ships **`Web Form.key_required`** and a **`Web Form Request`** DocType.
- The check is the **first statement of `get_context`** (`web_form.py:205-211`), i.e. before
  any template work, and a bad or missing key raises `frappe.PermissionError`, which
  `serve.py:31-32` turns into `NotPermittedPage`. **Nothing of the form renders.**
- The check runs **again on submit** at `web_form.py:753-758`, **before** the login check and
  before any document is touched, with `for_update=True` taking a row lock — which closes
  the double-submit race on a single-use key.
- Read, list, delete and link-options each re-validate separately
  (`web_form.py:1035-1040, 983-988, 883-888, 1154-1160`).
- `Web Form Request.doc_values` is forced onto the document server-side
  (`web_form.py:801-804`), so the candidate's browser cannot override their own identity.
- `accept` writes with `doc.insert(ignore_permissions=True)` (`web_form.py:829`), so the
  target doctype needs **no Guest create permission** — keep it that way.
- I checked the obvious bypass: **`frappe/client.py` grants `allow_guest` to nothing but
  `get_time_zone`.** Every write function there is plain `@frappe.whitelist`. And
  `frappe/api/v1.py:44-47`'s `create_doc` inserts without `ignore_permissions`, so Guest
  needs explicit create permission. **Writing is confined to the form's own `accept`.**

**So the analyst's fallback is not needed, and that is a large subtraction.** Two things
still leak, and I have measured both:

- **The query string.** Frappe's own form rendering requires `?web_form_request_key=`, and
  **our nginx logs it** — no `log_format`, so the default `combined` format carrying
  `$request`, and `access_log off` only on `/healthz` and `/assets/`. This is why I recommend
  option (c): keep Frappe's validator, render our own page, token in the fragment, posted in
  the body to `accept(..., web_form_request_key=...)`, which takes it as a parameter.
- **`upload_file` is token-blind** and no option changes that. Our own upload endpoint,
  settled.

Two smaller things worth writing down so nobody is surprised: `allow_multiple = 1` makes a
key **deliberately reusable** (`web_form.py:757`), so it stays 0; and `accept`'s rate limit
is `key="web_form"`, a **shared bucket at 10 per 60 s**, so a flood of bad keys could lock
out a real candidate — which is a second reason the per-token limits of OPS-26 are ours.

### 5.3 Q4 — the ERPNext fieldnames

Read from `erpnext/setup/doctype/employee/employee.json` inside the container. **The
Employee doctype lives in `erpnext`, not `hrms`** — worth recording, because the spec's
`[UNVERIFIED]` marker assumed otherwise.

| Fieldname | Label | Type | permlevel (JSON) | permlevel (live, ppj) | Verdict |
|---|---|---|---|---|---|
| `person_to_be_contacted` | Emergency Contact Name | Data | 0 | 0 | **Confirmed** |
| `relation` | Relation | Data | 0 | 0 | **Confirmed** |
| `emergency_phone_number` | Emergency Phone | Data | 0 | 0 | **Confirmed** — this is the real name of the third emergency field |
| `image` | Image | Attach Image | 0 | 0 | Confirmed. **`hidden: 1`** (it is the doctype's `image_field`), which does not restrict reads |
| `cell_number`, `personal_email`, `current_address`, `company_email` | | Data | 0 | 0 | Confirmed, permlevel 0 |

All three emergency fields sit in the `emergency_contact_details` section. **The spec's
`[UNVERIFIED]` marker on §5.1 can be cleared.**

**Two things I found while there, which the spec should know:**

1. **There is no work-phone field on `Employee`, confirmed independently.** D1's drop is
   correct — and `cell_number` is labelled "Mobile" and is personal, so it is not a
   substitute.
2. **`pan_number` is a Custom Field, not standard** — created by
   `hrms/regional/india/setup.py:43`. It only exists on India-regional tenants. The deny
   list must not assume it is always present, and a test that asserts "`pan_number` is
   refused" needs the field to exist on the test site or it proves nothing.

---

## 6 · The three CI scripts that name the old seat modal

The spec is right that three scripts name `#pos-editor`. I found **five references across
those three files**, and they are not equivalent — which matters, because two of them would
pass after the change while silently proving nothing.

| Reference | What it actually does | What the change must do |
|---|---|---|
| `scripts/check_portal_trays.js:79` | A **comment** inside a `.gp-backdrop` entry in the selector table. The real rule is on the class, not the id | Update the comment to drop `#pos-editor`. **If the seat page is not a `.gp-backdrop` dialog at all, the entry must stop claiming it.** A stale comment here is how the next person believes the dialog still exists |
| `scripts/check_positions_tree.js:710` | Builds a fake `pos-editor` element so `posAskDelete`/`posDelete` can be exercised. **This is a delete-flow test, not a seat-editor test** | The delete flow must keep working **from the seat page**. So this test does not get deleted — it gets **re-pointed at the page**, and `t.opened` becomes "did the page navigate away", not "did a dialog close" |
| `scripts/check_positions_tree.js:733, 736` | Asserts *"a deleted seat closes both dialogs"* | Becomes *"a deleted seat leaves the seat page and returns to the chart"*. **Same intention, different mechanism** — this is the one that would quietly pass if the assertion were just removed |
| `scripts/browser_check_positions.js:180` | A real browser check: clicks "Change this seat", asserts the dialog is open and visible, **asserts the tray closes behind it**, asserts a filled seat lists its people, then exercises the person picker | Becomes a **navigation** check: the page opens at its own address, the tray is gone, a filled seat lists its people, the person picker still works. **The tray-closes assertion is the valuable one** and must survive, because that is the regression a modal-to-page change actually causes |

**How the change keeps them honest, rather than just green.** Three rules I will hold
myself to:

1. **Every assertion is re-pointed, never deleted.** If an assertion cannot be expressed
   against the page, that is a sign the page lost a behaviour, and I stop and say so rather
   than dropping the line.
2. **The seat page ships with its own pin test in the same commit**
   (`parallel-work.md` §7) — named for the slice, asserting the page exists at its address,
   that the delete flow returns to the chart, and that the tray closes behind it. A bad merge
   that drops the page fails CI instead of a user finding out.
3. **The id `pos-editor` disappears from the repository in one commit**, with the three
   scripts changed in that same commit. A half-removed id that still exists in a check is
   worse than either state.

**One trap I found in the harness that the spec does not mention.**
`scripts/check_positions_tree.js:1244-1246` does this:

```js
W.POS_NAMES_SHOWN = opts.names || 1000;
W.posPaint();
W.POS_NAMES_SHOWN = 3;
```

The existing harness **overrides `POS_NAMES_SHOWN` to 1000** for most of its painting, then
puts it back. So OPS-21's face-count assertion must run in a context that does **not** do
that, or it will assert against 1000 names per box and pass for the wrong reason. I will add
the assertion as its own case with the real constant, and say so in the test's name.

---

## 7 · The two load-bearing constants — confirmed, and what else depends on them

Both confirmed by reading the file today.

| Constant | Declared | Read by | Confirmed |
|---|---|---|---|
| `POS_OPEN_DEPTH` | `portal.js:476`, value **1** | **exactly one place**: `portal.js:962`, in the `shut` calculation | **Yes** |
| `POS_NAMES_SHOWN` | `portal.js:802`, value **3** | `portal.js:816` (`posFew`) and `portal.js:827`; **plus `scripts/check_positions_tree.js:1244, 1246`, which overrides it** | **Yes** |

**Confirmed: they, not lazy loading, are why first paint is 16 faces.** I agree with `07`
§3's reasoning and I did not re-derive its numbers. Chrome's lazy threshold on 3G is
2,500 px and a 16-box chart fits inside it, so lazy loading defers nothing at first paint. It
still earns its place on the table — it costs nothing — but it is not the reason the design is
affordable.

**What else depends on them, beyond the face count:**

1. **The horizontal width of the chart.** The comment above `portal.js:955` records why
   `POS_OPEN_DEPTH` is 1 at all: at a tenant's real size one open level would be **120 boxes
   in one row several thousand pixels wide, with the card scrolling sideways and a tall empty
   gap above it. "Seen in a screenshot; no check could measure it."** So the constant is
   already load-bearing for **layout**, and OPS-21's assertion is now its second job. A later
   change that raises it breaks two things, and only one of them has a test.
2. **`POS.shown[r.id]`** is set from the same `shut` calculation (`portal.js:963`), which is
   what makes one press on a closed box open it. Anything that changes the constant changes
   the open/close behaviour, not just the paint cost.
3. **The wall-chart print path (slice 069).** It renders the whole tree and prints
   immediately. The 3-name cap applies there too, so the cap is what keeps the printed chart
   finite — and it is why OPS-19's bounding must be an IntersectionObserver rather than the
   browser's own threshold, which prints blank circles.
4. **The existing jsdom harness**, as §6 explains — it sets `POS_NAMES_SHOWN` to 1000 itself.
5. **`posAnyFilter()`** (`portal.js:722`) opens everything when any filter is on, which takes
   the chart to ≤ 215 faces regardless of `POS_OPEN_DEPTH`. **So the constant protects first
   paint and nothing else** — the filtered view needs the same bounding as the table, and I
   will apply OPS-19's observer to both rather than to the table alone. That is a correction
   to the plan, not an addition: it is the same fifteen lines used in a second place.

**Both pinned in the jsdom suite that already runs in CI. Nothing added to `ci.yml`.**

---

## 8 · Build order

**I agree with the analyst and the coordinator: the photo upload ships and switches on
first.** Until photographs exist, every face in this design is a pair of initials, and
`07` OPS-37 and `01b` §15 say the same. A release that changes nothing anyone can see is
also the release where nobody notices what broke.

But I would not build it in one straight line, because two gates sit in the middle of this
slice and one decision sits at the front of it. My order, each step a complete outcome:

| # | Step | Why here | Gate before it ships |
|---|---|---|---|
| **1** | **My profile + the photo upload + the 48 px copy + removal + the privacy sentence** | This is the whole WOW, it creates the data everything else displays, and it is the only part with **no dependency on any open question**. It also fixes the live S1-E defect | **PRIV-1's wording** gates switching it on at a tenant (⚠ COMPLIANCE 1). Build it, ship it, and switch it on at a tenant once Surbhi has the sentence she wants |
| **2** | **Faces on the Positions cards and table, the 3-name cap on the Organisation page, the print rule, OPS-19's observer, OPS-21's assertion, OPS-6's batching** | Now there are faces to show. This is mostly `ocAvatar`'s body plus one field on one read — the cheapest visible step in the slice | OPS-38: count the `<img class="av">` on dev's first paint and confirm 16, **because nobody has ever rendered this chart** |
| **3** | **The mini profile drawer, the profile endpoint, the ten-field allow-list, the settings card's field picker** | The drawer is the component everything downstream reuses, so it must exist before the seat page and before documents. The ARIA fix rides along | — |
| **4** | **The seat page**, retiring `#pos-editor`, with the three CI scripts and its own pin test in the same commit | It consumes the drawer from step 3. Done later it would be built twice | — |
| **5** | **Documents: the streaming endpoint, the document-type picker, the amber line naming the real roles, the access record** | Needs the drawer (3) and the card (4). It is also the step carrying R1 | Two gates. **(i) US-41's fixture set must exist first** — **dev has no `Employee Document` and no `Employee Document Type` rows at all** (§0a), so a document test on dev today reports "0 findings" and proves nothing. This is lesson 1 from slice 028 and it makes US-41 load-bearing, not optional: four document rows with real files, on an employee inside and outside the reader's scope, as fixtures and **never a real person's scan**. **(ii) OPS-31's remaining two** — one proved restore with `--with-files` on dev, and a recorded `BACKUP_BUCKET` decision. Disk is already satisfied at 111 GB. These gate the **ship**, not the build |
| **6** | **Pre-onboarding: the DocType, the form, the token, the uploads, the review screen, the erase job, the switch precondition** | Last, because it is the only part gated on a decision that has not been made (§0.1) and on a question counsel has not answered. It also ships **off**, so shipping it last costs nothing | **PRIV-7**: off at every tenant, cannot be switched on without a deliberately set retention period. **⚠ COMPLIANCE 2 still open — R4 is dangerous debt, and switching this on at a real tenant before counsel answers is a P1 finding, not a P2** |

**Why this order and not the spec's "one slice, any order":** steps 1 and 2 deliver the
whole visible outcome and depend on nothing open. Steps 5 and 6 are the two carrying the
named risks. If anything has to be cut on the day, it should be cut from the end, and this
order makes that possible without rework. I am not proposing to split the slice — Surbhi
decided one slice and I am building one slice. This is the sequence inside it.

---

## 9 · The parallel-work check

### 9.1 What came in while this slice was being specified

`git fetch origin` brought **270 commits** that are in `origin/dev` and not in my worktree's
base `d3afcaa5`, across **306 files, +84,509 / −1,674**. **I read the incoming diff**, as
`CLAUDE.md` §1 requires. What landed that touches my ground:

| Incoming | What it did | Effect on me |
|---|---|---|
| `e9dcf690` **ALV-256** | "the expense guard asked about a child table, so nobody had the part" | **The most relevant commit in the batch.** It is the same child-table permission fault this slice's document endpoint has to avoid. `frappe.has_permission` on a child table silently returns `False` for everyone. I will not call it on `Employee Document` |
| `cc2620b9`, `d3afcaa5`, `a77bd781`, `6ae6e203`, `ed0274b3`, `dced62f6` (076 A/B/C) | Home notices, expense approvers, birthday branch scoping | `home.html`, `hooks.py`, `hr_api.py`, `portal.js`. **Already in my base** — I must not re-derive against an older shape |
| `bfabde63` ALV-251, `552916cb` ALV-250, `377f336e` ALV-237, `cf65c663` ALV-248, `5aa654d2` ALV-232 | attendance bar, Inbox permissions, manifest, Set Password, issued-password redirect | `auth.py` and the password path — **ALV-232 and ALV-248 matter to US-4**, the My-Profile link to `/update-password`. I will read `auth.py:99` as it now stands, not as the spec read it |
| `hrms/alvoraa_org_structure/api.py` +130, `register.py` +421, `settings.py` +19, `plans.py` +695, new `Replacement Plan` doctype, `hiring.py` +297 | slices 071, 072, 194 and the replacement plans | **All four files I am editing in `hrms`.** My base already has them, but they are moving weekly |
| `scripts/check_positions_tree.js` +1374, `browser_check_positions.js` +427, `check_portal_trays.js` +342, `check_positions_connectors.js` +303, `check_wall_chart*.js` +1036 | the Positions and wall-chart checks | **All three scripts I must change, plus two more, were heavily rewritten in the last fortnight.** §6's plan has to be executed against the current text, not the line numbers in the spec |

Nothing in the incoming diff was unexplained, and nothing looked like the 8 September
obfuscated-JavaScript incident. No font files, no `postcss.config.js`, no unrelated binaries.

### 9.2 Files I will change, and who else is in them

| File | Commits in the last 14 days on `origin/dev` | Hot? | Who else |
|---|---|---|---|
| `alvoraa_portal/.../public/js/ess/portal.js` | **83** | **Yes — and it is not in `parallel-work.md` §6's hot-file table. It should be** | Everybody. 070, 071, 072, 073, 076 all landed in it this fortnight |
| `alvoraa_portal/.../public/css/ess/panels.css` | **46** | **Yes, same** | Same |
| `alvoraa_portal/.../hooks.py` | 19 | Yes (§6 names it) | 076 added `home_people.keep_hide_birthday` to `Employee.validate` |
| `hrms/.../alvoraa_org_structure/register.py` | 13 | Yes in practice | 071, 072, 194 |
| `.../parts/positions.html` | 10 | Yes in practice | 064, 069, 071 |
| `.../parts/org-settings.html` | 5 | Moderate | — |
| `hrms/.../alvoraa_org_structure/api.py` | 3 | Moderate | 072 |
| `hrms/.../alvoraa_org_structure/settings.py` | 2 | **DocType-adjacent and access-granting** | — |
| `.../parts/drawers.html` | 1 | No | — |
| `Alvoraa Photo Access Log` JSON | — | **DocType JSON — one slice at a time** | **Nobody, as far as I can see. I will claim it on the board** |
| `scripts/check_positions_tree.js`, `browser_check_positions.js`, `check_portal_trays.js` | heavily rewritten this fortnight | Yes | 064, 069, 071, 076 |

**The shared checkout `C:/Surbhi-Git/hr-app` holds 259 uncommitted changed files.** None of
them are mine. They include `hooks.py` and `auth.py` with **staged and unstaged changes
both** (`MM`), plus the whole `alvoraa_portal` tree, `hrms/alvoraa_org_structure`, and
`.claude/` context files. **Every one of them belongs to someone else and I will not touch,
stage, revert or tidy any of it.** I will not run `git add -A`, `git stash`, `git reset
--hard`, `git checkout .`, `git restore .` or `git clean` there, ever.

**One file in my own worktree is not mine.** `git status` here shows
` M .claude/context/ux-learnings.md` — written during this slice's `/slice-start` run, by the
UX designer, which is what that file is for. **I have not touched it and I will not commit
it with my code.** `.claude/` is not part of a feature slice.

**The work board is stale and I am flagging it rather than editing it.**
`.claude/work-in-progress.md` still shows 070-readable-on-phone and 069-wall-chart as "LOCAL
ONLY, NOT pushed" — **both are in `origin/dev` now** (0 unmerged commits each, checked). It
also shows rows back to late September whose work has shipped. I will add my own row after
the strategy is approved, as `parallel-work.md` §2 says, and I will not clean up anyone
else's rows.

**`git worktree list` shows 120 worktrees.** That is a finding in itself. Two of them hold
unmerged commits in files I will change:

| Worktree / branch | Unmerged | What it holds |
|---|---|---|
| `.claude/worktrees/064-old-chart` · `slice/064-old-chart` | 2 commits | **Rewrites 2,391 lines of `portal.js`, 956 of `check_positions_tree.js`, 131 of `panels.css`, 127 of `positions.html`, and deletes `check_positions_connectors.js`** — "Positions goes back to the chart that is live" |
| `.claude/worktrees/064-old-v2` · `slice/064-old-v2` | 2 commits | The same experiment, improved |
| `.claude/worktrees/077-field-roles` · `slice/077-field-roles` | 1 commit | "dropped at the design gate. Keeping what it found" — matches memory. No overlap with my files |

**I believe 064-old-chart and 064-old-v2 are abandoned**: `origin/dev` has moved 270 commits
past them, the chart on `dev` is the live one, and the portal redesign was discarded on 26
Oct. But they are not mine to judge and **the answer changes my plan completely** — if either
is still live, a 2,391-line `portal.js` rewrite and a 956-line rewrite of the exact script I
must edit are on their way, and nothing I build against the current chart survives. **⚠ This
is a question for Surbhi in §12.**

### 9.3 The plan where there is overlap

**Sequence** for the two `064-old-*` branches: if they are live, they go into `dev` first and
I rebase on them before writing a line. If they are dead, say so and I will ask for them to be
cleaned up rather than leaving them to look like pending work.

**Split** for everything else, by the rules `parallel-work.md` §6 already sets:

- **`portal.js`:** every new screen is **its own block with its own name prefix** — `mp…` for
  My profile, `mpf…` for the mini profile, `sp…` for the seat page, `ocs…` for the settings
  card. One line each in `switchPanel()`. **I do not move, re-indent or rename existing code.**
  The two shared changes — `ocAvatar`'s body and the `POS_*` assertions — go in **commits of
  their own that say so**, so a conflict there is obvious rather than buried in a 2,000-line
  feature commit.
- **`panels.css`:** new rules appended with the same prefixes. No reformatting.
- **`hooks.py`:** **one line at the end of `Employee.on_update` with a comment**, and one
  entry in `has_permission` if ever needed (it will not be — §5.1). Never rewrite the block.
  On conflict, keep every entry from both sides.
- **`settings.py`:** four names appended to `DEFAULTS`, `LABELS` and `ACCESS_GRANTING`. **I
  add no function and change no signature**, which is the rule for shared settings files.
- **`register.py`:** one field appended to one existing `fields` list. The smallest possible
  diff in a file with 13 commits in a fortnight.
- **`patches.txt`:** append only, never reorder, and I expect to need **no patch at all**
  (OPS-16, OPS-35).
- **DocType JSON:** I claim `Alvoraa Photo Access Log` on the board and the new
  joiner-submission DocType is mine alone.
- **The CI scripts:** §6's three rules, in one commit.

**Ask** rather than decide: the `064-old-*` question (§12 Q1), and anything where a conflict
turns out to want different behaviour rather than different lines.

### 9.4 The test that pins each existing feature I touch

`parallel-work.md` §7: every feature ships with a test that names it, so a bad merge fails CI
instead of a user.

| Existing behaviour I touch | The pin |
|---|---|
| `ocAvatar` renders initials when there is no photo | New case: no photo → initials; photo → `<img class="av">` layered over the initials; broken `src` → initials still visible. **Three states in one test, because one function now owns all three** |
| First paint is 16 faces | OPS-21's assertion, in `run_dom_tests.js`, in a case that does **not** inherit the harness's `POS_NAMES_SHOWN = 1000` override (§6) |
| `POS_OPEN_DEPTH = 1` and `POS_NAMES_SHOWN = 3` | Asserted literally, with the layout reason from `portal.js:955` in the test's name, so the next person knows raising it breaks two things |
| The seat tray closes behind the seat editor | Re-pointed to the page in `browser_check_positions.js` (§6) |
| A deleted seat returns to the chart | Re-pointed in `check_positions_tree.js` |
| `Employee.on_update`'s four existing handlers | A test that saves an Employee **without** changing `image` and asserts all four still ran and no thumbnail work happened |
| `invalidate_portal_context_cache` busts the 1-hour cache on a photo change | Asserted, because `get_portal_context` carries `image` |
| `position_table` is two queries for 403 people | The query-count assertion (20 vs 400), which is also PRIV-4's privacy gate |
| The Organisation page's own expansion | The 3-name cap asserted on `ocNodeCard`, which has no cap today |
| `/update-password` still returns the user to the portal | Pinned, because ALV-232 and ALV-248 both changed that path this week |

### 9.5 Bench discipline

The board shows **no current bench claim**. I will claim it before any run, check **both**
`docker exec hrlocal-bench pgrep -af run-tests` **and** `docker ps` (neither check alone sees
the other side), and **run anything longer than one module in a throwaway container with its
own site**, because the Redis hook cache is shared by every container and a run from
`hrlocal-bench` silently strips another branch's hooks out of it.

**One thing will cost whoever builds this an hour and it is already documented:**
`register.position_table` raises on `ppj.localhost` because `Replacement Plan` is not migrated
there, and `bench execute` reports it as `NameError: name 'hrms' is not defined`. I will
migrate my own throwaway site rather than migrating the shared one.

---

## 10 · Subtract pass

`no-over-engineering.md` §4. Read back asking only: **what can I delete and still meet the
requirement?** This is on top of the spec's own seven drops (D1–D7) and `01c`'s and `07`'s
subtract passes, all of which I accept.

**Removed — nine things:**

1. **The hand-built pre-onboarding token: the whole of it.** Frappe v16 ships
   `Web Form Request`. That deletes a four-field token schema, a
   `Waiting/Used/Cancelled/Ran out` state machine, the retired-hash rule, the key generator,
   the expiry check, the single-use burn and the tests for all of it. **The single largest
   subtraction available in this slice**, and it is only available because somebody read the
   installed source instead of the training data. Survives under both option (a) and option
   (c); only option (b) puts it back.
2. **Our own validate and submit endpoints**, same reason — Frappe's `get_web_form_request()`
   and `accept` do both. The **uploads stay ours**, because `upload_file` is token-blind —
   that is the one piece of the four the framework does not cover.
3. **Any `has_permission` hook.** I proved the `File` one cannot fire and argued the
   `Employee` one must not be built (§5.1). Two files not written, and a rung-6 answer
   avoided.
4. **A second IntersectionObserver.** The filtered chart view (`posAnyFilter`, ≤ 215 faces)
   needs the same bounding as the table. Same fifteen lines, used twice — not a second
   mechanism, and not a shared abstraction either.
5. **A `has_value_changed` wrapper, a thumbnail service, and a thumbnail settings key.** One
   guarded handler at the end of a chain that already has four. No class, no registry, no
   switch.
6. **A new function in `settings.py`.** Four names appended to three existing tables. The
   access-granting behaviour comes for free, and adding a function to a shared file is exactly
   what §6 of the parallel-work rules says not to do.
7. **A migration, a patch and a backfill.** Zero photos exist, and OPS-13's fallback means
   one never has to. `patches.txt` stays untouched.
8. **A fourth settings picker.** Carrying D2 — the Web Form owns the joiner's field list, and
   two pickers for one form will disagree in front of the joiner. The section stays as facts
   plus a link to the form's own builder. **This is Surbhi's decision 6-vs-11 tension and she
   has already settled it as three pickers plus a facts panel.**
9. **The 11th profile field.** Carrying D1: there is no work-phone field on `Employee`, which
   I confirmed independently in the ERPNext source. Ten fields.

**Not removed, and why, since the user should be able to judge:**

- **PRIV-5's document-open record.** Nobody asked for it. It stays because it is the only way
  an employee who cannot open the Positions page can ever ask "who looked at my Aadhaar" and
  get an answer that is not "we do not know". It is two columns on a table that already exists.
- **PRIV-2's removal.** It is one cleared write plus two file deletes, and without it PRIV-1's
  notice is a sentence the employee cannot act on.
- **The amber line on the settings card naming the real roles.** With SEC-3 declined, it is
  the only thing that makes a widening visible at the moment of the tick (R7).
- **OPS-38's render on dev.** 16 is arithmetic. Nobody has seen this chart.

---

## 11 · Proposed strategy, in one page

**Build all six steps of §8 in that order, in this worktree, on the local bench only, with
these commitments:**

1. **Rung by rung as §1 sets out.** One new DocType, no new app, no new module, no new
   workspace, no queue, no worker, no cache, no bucket, no feature flag, no abstraction. The
   one measured exception is the 48 px copy, and `07` §3.2's numbers are why.
2. **`ocAvatar` is changed once, in its body, and gives five states to three callers.** The
   mini profile is **one component**, used by Positions and the seat page, with the field list
   in one place — the spec has an AC that fails otherwise and I will keep it.
3. **Permissions are enforced server-side on every one of the six new surfaces**, reusing
   `register.may_view()`, `access.employee_in_scope` and `ACCESS_GRANTING`. **No new scope
   helper.** Two `ignore_permissions` only: the `File` insert and the `Version` insert.
4. **Nothing personal reaches a log.** Document name and employee id only — no name, no
   document number, no file URL, no joiner's details, no token. The access record holds no
   document content.
5. **Every number in `07` is taken as measured and not re-derived.** Where I measure
   something different I say so with my own figure: §0.2 (twenty surfaces, not ten), §0.4 (the
   permlevel-2 locks are not applied on the bench), §7 (the harness overrides
   `POS_NAMES_SHOWN`), and §5.1–5.3 (the three source reads).
6. **Nothing added to `ci.yml`.** One assertion in `run_dom_tests.js`, which already runs.
7. **No nginx change. No production access. No deploy command.** Pushing to `dev`, and later
   to `main`, is Surbhi's word and not implied by a green test run.

**What this strategy deliberately does not do:** it does not close R1, because §5.1 proves
nothing available closes it at a proportionate cost; it does not turn the pre-onboarding form
on anywhere; and it does not fix the 1.12 MB `portal.js`, the stale work board or the 120
worktrees, however much all three are tempting.

---

## 12 · ⚠ Decisions and questions for Surbhi — before I write a line

| # | Question | My recommendation |
|---|---|---|
| **Q1** | **Are `slice/064-old-chart` and `slice/064-old-v2` dead?** They hold unmerged commits that rewrite 2,391 lines of `portal.js` and 956 of `check_positions_tree.js` — the exact file and the exact script this slice must edit. If either is live, nothing I build against the current chart survives | **Dead, and the worktrees cleaned up.** `origin/dev` has moved 270 commits past them and the redesign was discarded on 26 Oct. But I will not assume it |
| **Q2** | **The pre-onboarding token — which of the three options in §0.1?** Frappe v16 ships the token machinery, which deletes the largest single piece of new code in this slice. But its own form renders from a **query string**, and **I verified that our nginx logs query strings** (no `log_format`, so the default `combined` format, which carries `$request`; `access_log off` only on `/healthz` and `/assets/`). So the shipped Web Form would write live tokens into the access log | **Option (c)**: Frappe's `Web Form Request` as the token store and validator, our own hardened page with the token in the URL fragment, posting it in the request body. It keeps the whole subtraction and keeps SEC-9's rule. **It is a variant of your Decision 11 rather than Decision 11 as written, so it needs your yes** |
| **Q3** | **Does PRIV-1's sentence get written against twenty surfaces, not ten?** §0.2. It must also name **appraisals** (`Appraisal.employee_image` copies the photo onto a submittable record) and **emails** — `send_work_anniversary_reminders` is **on, on dev, today** (§0a), and that path mails the photo's URL to colleagues | **Yes.** The sentence is the whole privacy position, and a notice that understates the audience is worse than none. The anniversary finding is the one that would have made it false |
| **Q4** | **Confirming the field picker offers only the ten-field allow-list**, not every Employee field. The coordinator read your words that way and §0.3 is why I agree | **Confirm the allow-list.** One sentence from you changes it |
| **Q5** | **With 078-SEC-3 declined, confirm the amber line names the real roles** holding Read on `Alvoraa Position` (AC-86), rather than a count. It costs one query, and with one-click tag removal refused it is the only automatic detection R7 leaves us. **And confirm who owns the tenant-go-live check** in §0.7 item 2, since it cannot live in CI | **Yes to the wording.** For the owner, my recommendation is whoever provisions a tenant, on the tenant go-live checklist. **Not a CI gate** — CI cannot see a tenant's `Custom DocPerm` rows |
| **Q6** | **Is the site-wide `max_file_size = 5 MB` accepted?** OPS-24. It applies to **every** upload on the site, not only documents | **Yes.** It is a tenth of today's effective limit and it bounds the document endpoint's memory cost from minutes to seconds |
| **Q7** | **⚠ COMPLIANCE 2 is still open** (the retention period for a joiner who never joins). R4 is labelled **dangerous debt**. PRIV-7 means the build is safe, but switching the form on at a real tenant before counsel answers is a P1 finding | **Build it, ship it off, do not switch it on anywhere real.** And chase counsel, because R4 is the only item in this slice I would escalate on its own |

**I have written no code, made no commit, run no bench command that changes anything, and
touched nothing in the shared checkout.** Everything above is read in this worktree or in
the running container on 31 October 2026, cited at file and line, or explicitly attributed
to `07`'s and `01c`'s measurements.

**Waiting for the strategy gate.**
