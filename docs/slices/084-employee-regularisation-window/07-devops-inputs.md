# 084 DevOps inputs

## §1 Brief - 2026-11-19

**Read:** checkout `/Users/mac/hr-app`, branch `dev`, SHA a57764c4, file
`alvoraa_portal/alvoraa_portal/attendance_correction.py` (lines ~1278-1335, 1383-1450, 2060-2110, 1105).
Frappe's own source is not on this Mac, so how `frappe.db.get_default` caches is **not checked**.
Nothing was run, nothing was changed except this file.

**Bottom line: no red flag that should stop the brief. Nothing new to run.** No new app, queue, worker,
volume or container. Same rung as the manager window: configuration plus a few lines in the existing guard.

### What it adds to run

- **Fact (read):** one window check = 1 default read + `holiday_list_for` (2-3 statements, per its own docstring,
  cached per call by `call_cache.once`) + 1 `Holiday` query + a loop of at most `days*2+30` steps in Python, no queries.
  **Estimate:** 4-5 small indexed statements, one employee, once per submit. Flat for 20 or 2,000 staff, so it meets the
  "same count at any headcount" rule in `nfr-budget.md`. Nothing is measured yet.
- **Correction to your framing:** the employee path is `raise_correction`, a **write**, once per request, not a list.
  The cost the code comment warns about is the manager review queue, where it runs once per person in a loop.
  Employee submit has no loop. A path "every employee uses" is still only a few submits a day each.
- **The one place it could bite:** if the screen also shows the boundary (below) and someone computes it per row
  of an employee's own history. Compute it once per request and reuse it.
- **Not skipped when unset?** Recommend the same shortcut: when the setting is blank, return before the holiday walk.
  Then tenants with no limit pay one default read.

### Run cost
**Estimate: nil in money.** No storage, no job, no extra image size. Needs a number before anyone worries:
OPS-1 asks for a query count in a test, not a cache.

### Red flags

| ID | Recommendation | Why | Level | Decision |
|---|---|---|---|---|
| OPS-1 | Return the boundary when the screen loads, from the same single function that the guard uses (as `manager_filing_from` does) | Cost is the 4-5 statements above, once per page load. Cheaper than a refused Submit. Also stops screen and guard disagreeing | Recommend, P3 | |
| OPS-2 | Assert in a test that query count is the same for a short and a long holiday list, and that blank setting adds no holiday read | The NFR gate is the property, not the number | Recommend, P3 | |
| OPS-3 | **Before enabling on Grace: read the Server Script, name its limit, and decide which rule stays.** Two rules in force, one invisible, is the real risk. Either set the new value equal to the script's, then delete the script in the same release; or leave the new setting blank until the script is gone | The stricter of the two wins silently. An HR admin who raises the setting would see no effect and not know why. Counting differs too: a script is likely calendar days, ours is working days on the holiday list, so the two can disagree by a day around weekends | Recommend, P2 | |
| OPS-4 | The refusal text should name the boundary date and the basis, as the manager one does | Lets the employee and HR see which rule fired | Consider, P3 | |
| OPS-5 | Unset must mean no limit, and `0` must mean today only, read the same way as `manager_filing_window_days` (no `or DEFAULT`) | A new tenant must not suddenly lose a right employees have today | Recommend, P2 | |

**Other tenants:** I did not check which other tenants carry a similar Server Script. **Unknown.** Smallest question:
is Grace the only one? Default if you want to move on: assume yes, and have the engineer grep Server Scripts on dev only.

### Frappe defaults as config storage
- **Fact:** the key is global, one value per tenant site (each tenant is its own site and database). That fits "per tenant".
- **Multi-company:** a default has no company dimension. A tenant with two companies needing different windows
  cannot have it. **Inference:** acceptable, since the manager window has the same limit; say it in the brief.
- **Caching:** whether `get_default` hits the database on every call is **not checked** (Frappe source not here).
  Even if it does, it is one indexed row, so no cache is advised. Do not add one on suspicion.
- A setting changed by HR takes effect on the next request; there is nothing to clear and no restart or `clear-cache`.
  That keeps this out of the deploy-approval commands in CLAUDE.md §2 for the setting itself.
- Writing it goes through the existing `set_org_setting`, which already has the HR guard. No new endpoint, no new permission.

### Subtract pass
Removed: a suggested cache for the window value, and a proposed separate "boundary" endpoint (reuse the page-load call).
Nothing else.

---

## §2 Design - 2026-11-19

**Read:** checkout `/Users/mac/hr-app`, branch `dev`, SHA a57764c4. Files: `01-product-brief.md` (Gate 1),
`01b-ux-design.md` (Gate 2), `attendance_correction.py` (`_employee_for` 277, `_me` 288, day-sheet loader ~560-680,
`raise_correction` 1105), `hr_api.py` (`_get_employee` 301, `submit_attendance_request` 2886), `deploy/nginx.conf`,
`public/js/ess/portal.js` (size only). **Nothing was run on a bench, dev or production. Nothing changed but this file.**
I did not open the prototype in a browser. Gate 2 already says phone width was not measured; I add no measurement of it.

**Bottom line: no measurable change to page weight or load time, and no red flag. Nothing here blocks the design.**

### 1. Page weight and 3G load
- **Measured (today, this Mac, the file in the checkout):** `portal.js` is 1,274,393 bytes raw and **346,296 bytes**
  after `gzip -5`. nginx has `gzip on`, level 5 (`deploy/nginx.conf` 89-93), so that gzipped figure is the
  right comparison. Not measured: what a phone really downloads from dev.
- **Estimate:** the change adds a few strings, one boundary value in an existing JSON answer and a sentence under the
  `#att-req` title. Based on the manager's equivalent being a handful of lines: well under 1 KB raw, a few hundred bytes
  gzipped. That is about 0.1% of 346 KB. **Answer: no measurable change.** I will not invent a load time.
- **Larger cost that is not ours:** a 346 KB script is the real 3G cost, and it is already there. The change neither
  helps nor hurts it. **FYI, P4:** the 2.5 s budget is not shown to be met by this file; that is old debt, not slice 084.
- The new sentence appears with the data that is already coming (see 3), so it adds **no extra round trip**, no new
  request and no new file.

### 2. The joining-day read: free
- **Fact (read):** `hr_api._get_employee` (the path `submit_attendance_request` already calls) **already reads
  `date_of_joining`** in its field list. Cost: zero.
- **Fact (read):** `attendance_correction._employee_for` (behind `_me()`, which `raise_correction` and the day-sheet loader
  both use) reads `name, employee_name, company, default_shift, holiday_list`. **It does not read `date_of_joining`.**
- **Recommend:** add `date_of_joining` to that field list. It is the same single-row `get_value`, so it is one more column
  on a statement that already runs. **Do not add a second query, and do not fetch it only when needed.**
  Inference: that adds no statement. Not measured; OPS-7 asks for the test that proves it.
- Side effect to know: `_employee_for` has other callers. An extra column is harmless to them. **Not checked:** how many.
  The engineer's impact analysis should grep it.

### 3. Boundary at load plus check at submit: acceptable, and the load-time read is already folded
- **Fact (read):** the day-sheet loader, around line 665, **already** calls `manager_filing_from(me.name)` and puts the
  answer into the same dict it returns (`out`). The design's employee boundary belongs **right beside it, in that same
  return.** It is not a new call and not a new endpoint. **Name of the call to ride on: the day-sheet loader in
  `attendance_correction.py` (the function containing line 665, which returns `filing_from`).** I did not read its name
  from the `def` line; the engineer should confirm it.
- For `#att-req`: **I did not find which call that screen makes on load.** **Unknown.** Smallest question for the
  engineer: does `#att-req` already call something on open that can carry the date? If yes, ride on it. If the screen makes
  no call today, one small whitelisted read is the answer, **not** a second computation path. It must call the same single
  function the guard calls, which Surbhi has already settled.
- **Cost per interaction:** load = the one function once (4-5 small indexed statements, **estimate** from §1);
  submit = the same function once more. So 2 reads per filing, against 1 today for the manager. **Acceptable.** An employee
  files a handful of requests a month, not a list. The brief's rule stands: compute it once per request, never per day row
  of the sheet.
- **One trap to name:** the day sheet shows up to 31 days. The boundary is **one date for the whole month**, not one per
  day. If the screen's code compares each day to that one date in the browser, cost is nil. If someone calls the server once per day, it
  becomes 31 times and breaks the "same count for 20 or 2,000" rule. **Recommend: one date in, compared in the browser.**
- **Blank setting:** return before any holiday read (OPS-5 of §1 stays). Most tenants pay one default read.

### 4. Caching: I agree, nothing new
- No cache for the setting, the boundary or the joining date. Each is one indexed row or a bounded loop.
  `call_cache.once` already holds the holiday list for one request; **that is request-scoped, not a new store.**
- **One caution:** `get_portal_context` in `hr_api.py` caches under `portal_ctx_<user>`. **Do not put the boundary in
  that context.** It would go stale when HR changes the setting and need invalidation. Read it live, as the manager one does.
  Not checked: what else is in that cache.
- HR changes the number: takes effect on the next request. Nothing to clear.

### 5. Must anything be public? The boundary needs no guard of its own
- **Fact (read):** both loaders sit behind a session. `_me()` throws `PermissionError` with no employee; `hr_api`'s
  `_get_employee` returns nothing for a user with no record, and `submit_attendance_request` throws. Neither is
  `allow_guest`. (`get_portal_context` is `allow_guest=True`, which is **a second reason not to put the boundary in it**: a
  tenant's policy date would then be one call away from a logged-out visitor. It returns early for Guest, but do not rely on that.)
- The value is a **date**, the same for every employee of the tenant, and each person's own holiday list changes it by
  at most a day or two. It reveals a company rule to the people it already binds. **No new guard.**
- **What must stay private:** the joining date. The refusal and the screen may **say** "your joining day is allowed". They
  must **not return `date_of_joining` in the boundary answer for another person.** The employee's own is theirs to see;
  a manager's screen for a report should never carry it. Recommend: the loader returns a yes/no per own day, or the date only when `is_self`.
- **A real exposure to name (P2, pre-existing, not caused by 084):** `submit_attendance_request` writes with
  `ignore_permissions=True` and checks no dates. The window bounds the **start**. **Nothing in the design bounds the
  end date.** An employee could still send `to_date` far in the future. The brief rightly lets WFH be raised ahead, so this is
  not a defect of the slice, but **a start inside the window with an end in 2099 passes the window.** A human approves it, so
  the data is not written automatically. Recommend: the engineer decides whether a sane upper limit belongs in this
  slice or in Surbhi's separate ticket from Gate 1. I did not check whether Frappe HR's own `Attendance Request` already
  refuses a long range.

### §2 rows (Decision column left blank for Surbhi)

| ID | Recommendation | Why | Cost of ignoring it | Level | Decision |
|---|---|---|---|---|---|
| OPS-6 | Add `date_of_joining` to the field list in `_employee_for`; do not add a query | Same row, same statement. `_get_employee` in `hr_api` already has it | A second statement per filing, for nothing | Recommend, P3 | |
| OPS-7 | Test: the count of statements on a filing is the same with the joining-day check on and off, and for a short and a long holiday list | The NFR property (same count at any headcount) | A hidden extra query nobody sees | Recommend, P3 | |
| OPS-8 | Ride on the day-sheet loader that already returns `filing_from`; one boundary for the month, compared in the browser | No new call, no per-day server read | 31 calls per sheet if done per day | Recommend, P2 | |
| OPS-9 | Do not put the boundary in `get_portal_context` (cached, and `allow_guest`) | Stale after HR changes it; policy date near a public route | Wrong date on screen; a public leak of a tenant rule | Recommend, P2 | |
| OPS-10 | Never return another person's `date_of_joining` from the boundary answer | Personal data on a manager's screen | PII exposure, `security-compliance-baseline.md` | Recommend, P2 | |
| OPS-11 | Decide whether `to_date` gets an upper limit, here or in the Gate 1 ticket. Name the owner | Start is bounded; end is not | A far-future range passes the window | Consider, P3 | |

**Subtract pass (§2):** removed a suggested separate "boundary endpoint" for `#att-req` (kept only as a fallback if the
screen has no call at all), and a measured-load-time table I could not fill honestly. Nothing else.

---

## §3 Requirements - 2026-11-19

**Read:** same checkout, branch `dev`, SHA a57764c4, plus `deploy/nginx.conf` (rate-limit zones, `access_log` lines), the two
"Server Script" mentions in this slice. **Not read: Grace's Server Script itself** (the brief says it caps regularisations at 3 per
employee per month; I have only that description). Nothing was run. Production not touched.

**Bottom line, bad news first:**
1. **The five false strings are not an afterthought: if one ships late, the product tells employees a limit does not exist
   while enforcing it.** They go in the same commit as the code.
2. **Grace's remaining cap is the only count limit on that tenant, and it is invisible.** It will keep working. That is
   fine for the release, but nobody should believe the new setting replaced it.
3. **Other tenants are unchecked. Say "not checked" in the release note, never "no other tenant has one".**

### Rate limit: no new limit of our own
- **Fact (read):** `location /api/` has `limit_req zone=kinexus_api burst=30` on 120 requests a minute per client address
  (`deploy/nginx.conf` 69-70, 292-293). Employee calls to `/api/method/...` already pass through it. **Not checked:** whether
  the ESS screens call `/api/method/` or post to `/` with `cmd` (the website-page trap in memory). The portal uses
  `frappe.call`, which I believe uses `/api/method/`. **Inference, not proven.** The engineer should send one filing on dev and read
  the request line.
- **Recommend: no new rate limit for `submit_attendance_request`.** A person files a handful a month; 120/min per address
  is far above that. There is no measured abuse. A per-user limit needs a new key and a new refusal message for a case
  nobody has seen. **The real protection is the date check itself**, which shrinks what the unchecked insert can do.
  Grace's per-month cap leaves the same hole open on other tenants for count, and that is **an accepted trade-off the
  brief already made**, not new debt.
- **Caveat to write down:** nginx limits per **client address**. A whole office behind one address shares the 120.
  Today's behaviour; not changed here.

### Monitoring: can "fewer wasted submissions" be measured?
- **Fact (read):** a refusal is a thrown validation error. It writes **no row** anywhere we own: the Attendance Request is
  not inserted, and I have not seen a refusal log. The PM declined to build one.
- **Not available without building something:** a count of refusals. Frappe does not store ordinary validation errors in
  its Error Log (inference from how `frappe.throw` is normally handled; **not checked here**, Frappe source is not on this Mac).
  The nginx access log is `off` for some locations (lines 125, 213, 434); **I could not check whether `/api/` is logged or
  how long it is kept, and I may not read the live nginx.** **Unknown.**
- **Recommend: drop "fewer wasted submissions" as a measure.** A measure with no baseline, no source and no one
  building a source is a number nobody will ever read. Say so in the spec. Do not write a trigger that needs it.
- **Replace it with a baseline that costs nothing to build and answers the real question, "who would this have refused?":**
  a read-only count of existing Attendance Requests whose first day is older than the working-day boundary at the time
  they were created, per tenant. It reads rows that already exist. **For the user to approve and run, per tenant:**
  production is out of bounds for me. On dev I would run it only if asked.
  - Use it **before** anyone types a number, so HR sees "N of last 90 days' requests would have been refused at 3 days".
  - Cost: one query, no code in the product. **It is a script for a person, not a feature.**
- **After release, what can be seen without building:** the Attendance Request rows that **do** exist. A rising count of
  "HR filed on the employee's behalf for an old day" would show the window pushing work to HR. Source: HR's own route
  (the Attendance Request doctype), **not checked** whether those rows can be told apart from employee-filed ones.
  Name that as a question for the engineer; do not promise the measure.

### Release order (the shortest safe path)
**Each step needs Surbhi's word.** Branch rules from `CLAUDE.md` §1 stand. I write commands for her to decide; I run none.

1. **Local:** engineer builds in its own worktree and stack. Tests press **Submit on both paths** and assert the payload,
   plus the query-count property (OPS-7), plus a joining-day case in both directions (alone: allowed; From = joining day,
   To = later: refused whole).
2. **One commit holds code and all five strings.** Not two commits, not "words next time":
   - three comments in `attendance_correction.py` (~654-655, ~658-661, ~1378-1382),
   - the `acOutsideWindow` comment in `portal.js` (~6228-6232),
   - the day-sheet sentence "outside the window a manager can file within" (`portal.js` ~6204), which an employee must not read,
   - plus the manager hint in `org-settings.html` (the UX design's OS2), which becomes false the same day. **That is a
     sixth string, not on your list of five. Please check I have not double-counted: the hint is a screen text, not a comment.**
   **Gate (recommend, P2):** a grep step in the review that fails if any of `does not limit`, `not bounded`, `their own month`,
   `neither setting` still describes an employee's own day. The UX scan searched only `alvoraa_portal/alvoraa_portal`.
   **Search the repo and the docs too, including the DTC user manual.**
3. **Integrity and nginx:** `scripts/check_app_integrity.py` before commit. **No `deploy/nginx.conf` change** is planned, so the
   one-nginx-for-dev-and-prod trap does not arise. Recommend that the slice's diff is checked to contain none.
4. **Dev, on Surbhi's word:** push to `dev`, wait for CI to finish before any second push (memory: a new push cancels the
   running CI). The automatic Deploy runs `main`'s workflow copy; this slice changes no workflow, so that trap does not apply.
   **Prove it landed three ways, not by a green tick:** the pin file `.image.dev.env`, `docker ps` image tags the same on
   every app container, and the file itself (grep a changed string inside the container).
5. **Assets: the portal JS must really change.** The sites volume hides the image's assets. After the dev deploy compare
   `assets.json` in the volume with the image's, and load `portal.js` from the dev URL and grep for the new sentence.
   **A green deploy with the old JS would ship the false comment-driven wording to employees.** No `bench build` on a server
   (frappe-conventions). **Which ESS script the page loads (`public/js/ess/portal.js`) is a Python-served template path
   not yet proven by me.**
6. **Setting stays blank on every tenant at release.** That is the default; nothing is migrated, no patch, no fixture.
   **Fact (inference from the brief):** blank means no limit, so release changes **no behaviour** for any tenant until HR
   types a number. That makes release safe and the rollback small.
7. **Grace and others: see below. Then main**, in the night window IST, only on Surbhi's word after she has tested on dev.
8. **After main:** the same three-way proof against the production stack's pin file `.image.env`. Open the HR settings
   screen on the live site, **read the new row back**, change nothing, and confirm the manager hint no longer says an
   employee is unlimited.

**Migration:** none expected. No new DocType, no custom field, no patch. **Not checked:** whether the engineer's final design
adds any. If it does, this changes to a dry run on a copy per `REHEARSAL.md`. **Migrate-time risk is nil for this slice
as designed** (the queue-overload trap came from permission clean-ups, not settings).

### Rollback: what "undo this" means for a Frappe default HR may have set
- **The release itself:** redeploy the previous image tag with migrations off (production pulls an image only during a deploy).
  **Before the release, name the previous tag and prove it exists in the package we pull from (`alvoraa-app`).** I have not checked.
  **Measured earlier (22 Sep): a deploy and a rollback each waste about 7 minutes in the `bench version` wait.** Plan for it.
- **The value HR typed:** a Frappe default is a **row in the tenant's own database, not in the image.** Rolling the image
  back **does not remove it.** The old code ignores an unknown key, so the number becomes a dead value that does nothing.
  **Harm:** HR believes a limit is on, and it is not. The reverse of the Grace trap.
- **What to write in the rollback plan:**
  1. Before release, **read and record** the key's current value on each tenant that is touched. Expect blank/none.
     **Not checked** (no access, and the key does not exist yet).
  2. If HR has set a number and the code is rolled back, **tell HR in words**: "the limit you set is not enforced after
     the rollback". Do not leave it silent.
  3. Rolling **forward** again restores the old number with no work. Do not delete the row on rollback; it is the user's data.
  4. To switch the limit off **without** a rollback: HR clears the field in the same screen. Blank = no limit. **That is the
     fast undo, with no deploy.** Recommend this is the first thing said in an incident.
- **Read-back rule:** after any change to the value, read it again from outside and write the value that came back.

### Grace's leftover Server Script and the other tenants
- **Fact (from the brief and Surbhi's note):** Grace's 48-hour limit was removed and its daily salary-slip script fixed on
  19 Nov 2026, both on the live site. A cap of 3 regularisations per employee per month remains. I have **not** read it.
- **What the release plan should do (recommend, P2):**
  1. **Leave the cap running through this release.** It is outside the slice and removing it is a change on a live
     customer tenant, which needs Surbhi's separate word. Retiring it is not a release step.
  2. **Write it into the release note as a known second rule:** "Grace enforces a 3-a-month cap that is not in Org settings.
     The new window and the cap are two rules; the stricter wins." HR must be told.
  3. **Before anyone sets a number on Grace:** read the script on Grace and compare its counting basis (the brief expects
     calendar days against our working days). The user decides who reads it, since it is a live tenant.
  4. **Do not treat the new setting as having replaced it.** The brief's "HR stops writing Server Scripts" is only half
     true for Grace; say so.
  5. **A cap with a calendar-day count may refuse a day that our date allows.** If an employee says "the screen said I
     could, and I was refused," look at the script first. Add that to the support notes.
- **Other tenants (aahr, dtc, tft, demo): not checked, and I do not recommend reading them.** Reading was refused as
  unauthorised access, and that stands. Options, with my recommendation first:
  1. **Ask each tenant's HR contact one question:** "Did anyone write a script or rule that limits how far back an
     employee can ask to fix attendance, or how many times per month?" Recommended. It is faster than reading code and needs
     no access we lack.
  2. Ship on blank default (already the plan) and **say in the note that other tenants were not checked.** Safe either way:
     because blank means no limit, a hidden script elsewhere only matters **when HR sets a number**, and then it is the
     stricter-wins problem OPS-3 already covers.
  3. Have the engineer grep Server Scripts **on dev only** (as the brief offers). That shows dev's scripts, **not** any live tenant's.
     Do not report it as "other tenants are clear".
- **Words to keep out of every note:** "no other tenant has a script" and "all tenants are clear". The honest sentence is
  "Grace has one; the others were not checked."

### §3 rows (Decision column left blank for Surbhi)

| ID | Recommendation | Why | Cost of ignoring it | Level | Decision |
|---|---|---|---|---|---|
| OPS-12 | No new rate limit on `submit_attendance_request`. The date check is the control. Confirm on dev which URL the call uses, to be sure nginx's 120/min applies | No measured abuse; nginx already limits `/api/`; the new check shrinks what the unchecked insert can do | A new key and message for a case nobody has seen | Recommend, P4 | |
| OPS-13 | Drop "fewer wasted submissions" as a measure. Optionally, a one-off read-only count per tenant of past requests older than the proposed boundary, run by a person, before HR picks a number | No refusal log, no baseline, none to be built. The one-off answers "who would this refuse?" with existing rows | A measure nobody can read, quoted later as proof | Recommend, P3 | |
| OPS-14 | One commit: code plus all five strings **plus the manager hint (sixth)**; a repo-wide grep for the false phrases at review | False wording on release day is the Grace failure again | Staff told a limit does not exist while it is enforced | Recommend, P2 | |
| OPS-15 | Prove the landing three ways and compare `assets.json` volume against image after each deploy; load the JS from the URL and grep the new sentence | A green deploy of old JS hides everything; the volume hides the image's assets | Old screens, new guard: refusal with no date on screen | Recommend, P1 | |
| OPS-16 | Setting blank on every tenant at release; read it back after any change and write the value read | No behaviour change at release; reversible by clearing the field | A limit appears on a tenant nobody told | Recommend, P2 | |
| OPS-17 | Rollback plan: record the key's value before release; HR clears the field for the fast undo; tell HR if code is rolled back with a number set; name the previous tag and prove it exists in `alvoraa-app` | The value outlives the image | A dead number HR believes in | Recommend, P2 | |
| OPS-18 | Leave Grace's 3-a-month cap running; say in the release note that two rules exist and the stricter wins; read it before setting a number on Grace | Removing it is a live-tenant change, outside the slice | Silent disagreement between screen and refusal | Recommend, P2 | |
| OPS-19 | Ask each other tenant's HR contact one question; say "not checked" in the note until answered | Reading their scripts was refused | A false "all clear" | Recommend, P2 | |

**Open questions (smallest first):**
1. **Must know:** does `#att-req` already call something on open that can carry the boundary? Engineer, on read. Default: add the date to the loader that exists.
2. **Should know:** what is the previous production image tag, and is it in `alvoraa-app`? Default: check at release readiness (§5).
3. **Should know:** the sixth string (manager hint). Please confirm whether you counted it among the five.

**Subtract pass (§3):** removed a proposed per-user rate limit, a refusal log, a dashboard for refusals, and a plan to read other
tenants' scripts. Added nothing new to run. **I kept the one-off baseline count because it is a person's script, not a feature.**
Nothing was left behind: no container, no file outside this one, no setting changed.

---

## §4 — the two open questions, answered from the source (19 Nov 2026)

Read on `dev` at `a57764c4` by the session running the slice, not by the DevOps agent.

**Q1 (must-know): what call does `#att-req` make when it opens?**

**It makes one.** `loadAttReqPanel()` at `public/js/ess/portal.js:12140` sets both date
boxes to today and calls `reloadAttReqHistory()`, which calls the whitelisted
`get_requests_history`. So **no new endpoint is needed**: the employee's boundary date
rides back in that existing call, exactly as the day sheet's rides in its own loader.
OPS-8's fallback (a separate boundary endpoint) is not required and should be dropped.

**Also found while looking, and it confirms ALV-387.** The browser-side check in
`submitAttendanceRequest()` (`portal.js:12156`) is only:

```js
if (!from || !to || from > to) { showErr("ar-date-err"); ok = false; }
```

No limit of any kind on how old a date may be, on either side. The screen and the
server both accept anything.

**Q3: did the "five strings" already include the manager hint in `org-settings.html`?**

**No — DevOps is right, there are six.** The UX design listed the manager hint
separately ("The false manager hint is replaced in full") and *then* gave five further
places. OPS-14's one-commit rule should cover all six.

**Q2 (previous production image tag) is still open** and is a §5 release question.

---

## §5 Strategy - 2026-11-19

(The slice-build skill calls this "§4 Strategy". This file already has a §4, so this is **§5**. §5 Release readiness
from the original list will be a later section.)

**Read:** checkout `/Users/mac/hr-app`, branch `dev`, SHA a57764c4. Files: `00-impact-analysis.md` (all), the Gate 4
block of `02-functional-spec.md` and AC-59/62 and its "no migrate" paragraph, the Gate 3 block of
`01c-security-privacy-requirements.md`, my §1-§4, and `.github/workflows/deploy.yml` (grep of the migrate,
clear-cache and assets lines). **Not read this session:** `DEPLOYMENT_RUNBOOK.md`, `REHEARSAL.md`, the compose files,
Frappe's own source (not on this Mac). **Nothing was run.** No bench, docker, git, gh or deploy command. Nothing
changed except this file.

**Bottom line, bad news first:**
1. **The previous production image tag is still unproven (Q10). Until it is, the release is not ready (P1).**
2. **A rollback has a trap the engineer's note only half sees.** Once the code is rolled back, the HR screen row is
   gone, so HR can no longer clear the number. HR must clear it **before** the rollback, not after (OPS-22).
3. **Probable second trap, inference only:** a rollback with migrations off does not run `clear-cache`, so a cached
   hook list may still name a function the old code does not have (OPS-21).
4. Everything else is small. No schema, no new moving part, ships blank.

### 1. Install order, image, Compose, migration, CI, pinning

**Confirmed, with one correction.** The engineer says: no DocType, field or patch; a stored setting, one `validate`
key in the existing `Attendance Request` block of `alvoraa_portal/hooks.py`, and a few lines. That matches what I
read in AC-60 and the spec's "no migrate" paragraph. **Not independently verified by me against the code:** I read
the engineer's account, not `hooks.py`.

| Question | Answer |
|---|---|
| Install order | None. No new app, no new dependency. One image rebuild of the existing app, same app list. |
| Image build | Code and static files only (`attendance_correction.py`, `hr_api.py`, `hooks.py`, `portal.js`, two templates). **Not checked by me:** that no `requirements` or `Dockerfile` line is touched. Make it a check: `git diff --stat origin/dev` must show **none** of `deploy/`, `Dockerfile`, `.github/workflows/`, requirements, `deploy/nginx.conf`. That also keeps the one-nginx trap out. |
| Compose, nginx | No change. |
| `bench migrate` | **Correction to "no migrate needed".** True for the schema: migrate has nothing to change. But **the Deploy workflow runs `bench --site all migrate` and then `clear-cache` itself** when migrations are on (`deploy.yml` 534-571, `migrate=true` on a push, line 159). So it will run, as a no-op here, and the `clear-cache` after it is what refreshes Frappe's cached hook list. **Recommend: deploy normally with migrations on. Do not choose "migrations off" for the release or for a fix-forward.** (Migration-queue trap from 5 Nov: unrelated, a permission clean-up caused it; nothing in 084 writes permissions.) |
| Hooks load | With the app, at process start. The deploy recreates containers, so every app container loads the new hooks. After the deploy, check **all** app containers show the same tag (lesson 2). |
| Assets | `portal.js` is served from `/assets/alvoraa_portal/js/ess/portal.js` (`deploy.yml` 764). **Fact (read):** the "Portal assets must be served" step checks that the file is served, **not what is in it.** The sites volume hides the image's assets. So OPS-15 stands as P1: compare `assets.json` in the volume with the image's, and grep the new sentence in the **served** file. No `bench build` on a server. |
| CI gates to add | **None new.** Use what exists: `scripts/check_app_integrity.py` before commit; the existing AST ceiling test for `ignore_permissions`; the pin test on `frappe.get_hooks("doc_events")` for the `validate` entry (already in the engineer's plan); AC-12's break test. Plus two checks at review, not CI jobs: the `git diff --stat` above, and the grep for false phrases (OPS-25). A new CI job for one slice would be a permanent cost. |
| Version pinning | Nothing to pin. **Use the exact commit SHA for the image tag and for any checkout** (memory, 12 Nov: checking `main` out by name gave the 27 Oct release). |
| Timing | Main only in the night window IST and only on Surbhi's word. The deploy pause refuses biometric posts for about a minute (memory, 26 Oct). Measured earlier: a deploy and a rollback each lose ~7 minutes to the `bench version` wait. |

### 2. Where I agree and disagree with the engineer

**I disagree with the engineer on nothing that changes release or operations.** Plain list, for Surbhi:

| Engineer's point | My view | Where it differs from the spec |
|---|---|---|
| Hook also fires when `employee` changes (1) | **Agree.** One tuple element. Without it an own-name can be put on an old-dated draft. | Spec AC-12 says dates only. |
| Compare with `getdate()`, not `has_value_changed` (2) | **Agree.** A false "changed" would refuse a harmless edit of the explanation. | Spec section 6. |
| Check the cheap change test first, then the setting read (hook order) | **Agree.** HR's submit, cancel and edits cost zero reads. Fits OPS-1 and the NFR "same count at any headcount". | Spec puts the setting read first. |
| `"validate"` is a new key with a string, not a list (11) | **Agree**, from the engineer's read of `hooks.py` 179-191. | Spec says "becomes a list". |
| Class in the existing test file (10) | **Agree.** No ops effect. Fallback if CI's split makes the file slow: a new file importing `CorrectionCase`. | Spec said a new file. |
| `own_window` only for "outside" and "joining" (9) | **Agree.** Smaller payload on a 3G phone. | AC-30/31 reworded. |
| `get_requests_history` rides on four panels (shift, request, encashment, advance) | **Agree, with a measurement condition.** Three of the four never use the date and still pay ~5 statements, but only when a number is set. **Estimate, not measured.** Recommend AC-68 counts statements per panel; add a flag only if the count misses the 500 ms API budget. | New finding, not in the spec. |
| Drop the date from the HR save line for n of 1 or more (3) | **Agree. Details in section 3.** | Departs from the prototype: **needs Surbhi's yes.** |
| Delete US-11 / AC-59 (5) | **Agree. Section 3.** | Spec and my OPS-13. |
| Eleven false-text items, not nine (section 9.6) | **Agree it is more. Section 3.** | 02a says nine. |
| No Hindi file (6) | **Not a release blocker; blocks the first tenant that sets a number. Section 4.** | Gate 4 lists it as release-blocking. |

The engineer's "I build Gate 4 as decided unless you say otherwise" is the right default for Surbhi to be told: both
views go to her on items 3, 4 and 5 of the engineer's own list.

### 3. The engineer's disagreements with the spec

**Drop the date from the HR save line (n of 1 or more). I agree with the engineer.**
- The line would count on `Company.default_holiday_list`, which may not be a list employees are on. **Inference** from
  the engineer's reading of `tests/fixtures_scale_044.py:281-283`; I did not read that file. A wrong date shown to the person who sets the rule is
  worse than no date.
- It needs an optional last argument on `_working_days_away`. That function has **four** callers (HR wait, two manager
  paths, the new one). Changing a shared function for one sentence on one screen is a release risk with no matching gain.
- It breaks my own OPS-1 rule: the screen and the guard must come from one function. A "reference" list is a second answer.
- Cost of the engineer's version: the sentence says "an employee can ask about the last N working days. Their joining day is always
  allowed. HR can still fix any day." No date, no wrong date.
- **It differs from the approved prototype, so it needs Surbhi's yes** (prototype parity rule, 21 Oct).

**Delete US-11 / AC-59. I recommended OPS-13, so: I no longer want it in this slice.**
- My reason then was "HR should pick a number knowing its effect". That need only arrives when a tenant asks for a number.
  Gate 3 C1 already ties counsel to that same moment. Nothing sets a number on release day.
- Building a reviewed script now means it is written against an unknown tenant, and AC-59's own count (boundary "at creation
  time") is the fiddly part. Better written when there is a real tenant and number.
- **Not lost:** put one line in the release note: "when a tenant asks for a number, run a read-only count first".
  I said OPS-13 was "a script for a person, not a feature". Agree it is not worth 2 points before demand.
- Cost of deleting: none on release. Cost of keeping: a script, a review, and a second path that counts days.

**Eleven items, not nine.**
- The engineer's search found two more: the test docstring "Neither setting may take away..." (`test_attendance_correction.py` 1700-1703)
  and the new hint "It does not limit HR." (which is itself false, the engineer's disagreement 4). I only knew of the five
  plus the manager hint (six).
- **What matters is the check, not the count.** A count of "all false text" is a scope claim. Recommend: update
  `02a-strings-that-become-false.md` to eleven and say "found by grep on this date", and keep AC-50 as a floor.
- Add `neither setting` and `take away what somebody asks` to the grep list; **include test docstrings**.
- Still **not checked by anyone:** the DTC user manual (a Claude Doc outside the repo). If it quotes a false sentence, employees read it.
  One person opens it and searches the same phrases. Does not block the release (nothing changes for DTC while blank); does
  block the first number at DTC.

### 4. Two operational items

**A. A stored setting outlives a code rollback (OPS-17, restated as steps)**

What the steps must actually say:
1. **Fact about order:** the HR row exists only in the new code. After a rollback it is gone. **So HR cannot clear the
   number after the rollback.** The only fast undo, "HR empties the box", works only **while the new code is live.**
2. **If a rollback is planned (not an emergency):** first read the key on each tenant (read-only, **needs Surbhi's word on a
   live tenant**). If any tenant has a number, HR clears the box first, the value is read back and written down as read, and
   only then the image is rolled back.
3. **If it is an emergency and a number is set:** roll back, then **tell that tenant's HR in words** that no limit is
   enforced any more. Do not delete the row; it is HR's data, and rolling forward restores the rule with no work.
4. **How to know which tenants have a number:** the new `security` log line (SEC-12) would tell us, **but only if
   `.warning` reaches `security.log` (Gate 4 Q6, not yet checked).** The engineer stops and asks if it does not. **Agree.**
   Until Q6 is answered, keep a hand list in the release note: tenant, number, date, who set it.
5. At release the key does not exist on any tenant (the row is only in the new code), so a "before" read is a formality. The real
   risk window starts the first time HR saves a number.

**Probable extra trap (OPS-21), marked inference.** `deploy.yml` runs `clear-cache` only inside the `MIGRATE=true` branch
(540-571). Frappe normally keeps the hook list in a cache in Redis, and a container restart does not empty Redis. **If so**,
rolling back with migrations off leaves a cached `validate` entry naming `refuse_own_day_outside_window`, which the old code
does not have. Every `Attendance Request` save, **including HR's**, could then fail. **I have not checked this**: Frappe's source is not on this
Mac. The engineer's step 2 (read the installed Frappe in the container) should answer it. If true, the rollback needs a `clear-cache`
(**requires Surbhi's approval**, CLAUDE.md §2) and "migrations off" must not be the rollback default for this slice. If untrue, say so in the
rollback note and delete this paragraph.

**B. No `hi.csv`: release blocker or follow-on?**
- **Recommend: not a release blocker. A blocker for the first tenant that sets a number whose staff read Hindi.**
- Why: the setting ships blank. Employees see nothing new while it is blank (the day-sheet sentence and the `#att-req` note appear
  only with a number, per the engineer's design). The only new text on release day is the HR row, read by HR.
- What breaks if Hindi never ships: a Hindi-reading employee sees an English refusal in English, with HR's route named. A
  refusal they cannot read is a dead end for pay (Section 7 of the impact analysis).
- **Not checked:** how `drT` finds translations, so I cannot confirm "nowhere to live" beyond what the engineer found (`find` for `hi.csv`: none).
- **This differs from Gate 4**, which wrote Q4 as blocking release. It is Surbhi's decision to move it. Default if she says nothing:
  keep it as written (release waits for a native reader). The cheaper path, which I recommend, is: release blank, finish Hindi before any number is set.

### 5. `next-time.js` also calls `raise_correction`

- **Does it need checking before release? No.** Blank means no limit; nothing there changes on release day.
- **Before the first number is set on any tenant: yes, two cheap checks.**
  1. Which tenants, if any, still open `/hrms-employee-next`. This joins Q7 ("is `#att-req` used on Grace and DTC")
     as one question to HR contacts, since I cannot read live access logs and may not probe production.
  2. On the engineer's own stack, press Submit in that frame with a number set and assert the refusal text shows (memory:
     test what it sends, not just what it draws). The engineer says the code shows the server's sentence; **I have not read `next-time.js`.**
- If a tenant does use it, it works (the hook binds it) but shows no boundary before typing. That is a missing hint, not a hole. Level: P3.

### 6. Previous production image tag (Q2 / Q10)

- **Still open and unproven. I did not check it** (production and the package are not mine to probe; I ran no `gh`).
- **Who:** the engineer cannot do it, and I may not. **Surbhi approves, a session she names runs it, read-only.**
- **What to do:**
  1. Name the previous production tag. Read it from the last successful **main** Deploy run in GitHub Actions (this does not touch
     production), and cross-check against production's pin file `.image.env` only if Surbhi approves a read of the server.
  2. Prove that tag exists in `alvoraa-app` (not the old `hr-app` package, which must never be the source). Read-only:
     list the package's versions with `gh api` and find the tag. **I did not read the package owner path (user or organisation); do
     not guess it.**
  3. Write the tag and the date proved into the release note.
- **When:** before Surbhi is asked to approve the push to main, not at rollback time, and **again on release night**
  before the deploy, because a package cleanup could remove a tag. A rollback path that does not exist is P0; an unproven one is P1.
- Rollback needs migrations ON if OPS-21 proves true. Say which in the note.

### 7. Release steps, for Surbhi to decide (I run none)

Each line **requires Surbhi's explicit approval.** Paths and container names are not typed here: take them from
`DEPLOYMENT_RUNBOOK.md`, which **I did not re-read this session**.

| # | Step | Needs approval | Proof to write down |
|---|---|---|---|
| 1 | Engineer builds and tests locally in its own worktree and stack | local, already allowed | CI-equivalent tests; AC-12 break test; query-count test |
| 2 | `git push origin <slice branch>:dev` after `git fetch origin dev` and rebase | **Surbhi: push to dev** | Wait for CI to finish before any second push |
| 3 | Dev deploy lands | automatic, from `main`'s workflow copy; no workflow changes here | Three ways: `.image.dev.env`, every dev app container shows the same tag, the new sentence found inside the served `portal.js` and `org-settings.html`; `assets.json` volume vs image |
| 4 | On dev: set a number on a test tenant, press Submit on both paths, clear it, **read the value back** | **Surbhi: dev data change** | The value read, written down |
| 5 | Prove previous production tag in `alvoraa-app` (section 6) | **Surbhi: read-only check** | Tag and date |
| 6 | Push or merge to main, night window IST, exact SHA | **Surbhi: push to main, after she has tested on dev** | Same three-way proof on `.image.env` and the `compose-*` containers; HR row present and blank |
| 7 | Release note: Grace has two rules (stricter wins); other tenants "not checked"; setting blank everywhere; hand list of tenants with a number | Surbhi reads it | |

**Rollback (decision for Surbhi, not a command I run):** section 4A order, then "redeploy the previous tag"; ~7 minutes lost to
the `bench version` wait (measured 22 Sep); migrations ON if OPS-21 proves true.

### §5 rows (Decision column left blank for Surbhi)

| ID | Recommendation | Why | Cost of ignoring it | Level | Decision |
|---|---|---|---|---|---|
| OPS-20 | Deploy with migrations ON. Check `git diff --stat` shows no `deploy/`, `Dockerfile`, workflows, requirements or nginx file | Migrate is a no-op here but its `clear-cache` refreshes hooks | A cached hook list after a quiet "migrations off" run | Recommend, P2 | |
| OPS-21 | Engineer reads in the container whether the hook list is cached in Redis; if yes, rollback includes `clear-cache` (**needs approval**) and migrations are not turned off | `deploy.yml` clears the cache only with migrate on. **Inference, not checked** | Every `Attendance Request` save, HR's too, could fail after a rollback | Recommend, P2 | |
| OPS-22 | Rollback order: HR clears the number first, read back, then roll back. If urgent, roll back and tell HR in words | The row disappears with the new code | HR believes a limit is on | Recommend, P2 | |
| OPS-23 | Agree to drop the date from the HR save line for n of 1 or more (Surbhi's yes needed: prototype difference) | Wrong date risk; avoids changing a function with four callers | A misleading date on the one screen HR trusts | Recommend, P3 | |
| OPS-24 | Agree to delete US-11/AC-59; write one line in the release note instead | Nothing sets a number at release | A script written for no tenant | Recommend, P3 | |
| OPS-25 | Update 02a to eleven "found by grep, dated"; grep list adds `neither setting`, `take away what somebody asks`; include tests; one person searches the DTC manual | Count is a scope claim; the manual is outside the repo | False text read by DTC staff | Recommend, P2 | |
| OPS-26 | Hindi: release blank without it; finish before the first number on a Hindi-reading tenant. Surbhi changes Gate 4 Q4 from "release" to "first number" | Nothing new is visible to staff while blank | Delay with no safety gain, or an English-only refusal later | Consider, P2 | |
| OPS-27 | `next-time.js`: before the first number, ask who opens it (join with Q7) and press Submit there on the engineer's stack | Hook binds it; hint is missing | An unseen refusal path | Consider, P3 | |
| OPS-28 | Name the previous production tag and prove it exists in `alvoraa-app`: before the push-to-main approval, and again on release night | Without it a rollback does not exist | No rollback | Recommend, **P1** | |
| OPS-29 | Count statements per `get_requests_history` panel with a number set; add a flag only if it misses the API budget | Three of four panels pay for the fourth | A small, unmeasured cost | Consider, P3 | |
| OPS-30 | Agree: engineer stops and asks if `.warning` does not reach `security.log`. Until then keep a hand list of tenants with a number | The log is how we would find those tenants | No way to know whom to warn | Recommend, P2 | |

**Open questions (smallest first):**
1. **Must know:** who, and when, proves the previous production tag in `alvoraa-app`? Default: Surbhi names a session; before her push-to-main word.
2. **Should know:** does Redis cache the hook list on our image? Default: the engineer reads it on their own stack; until then assume yes (OPS-21).
3. **Should know:** is the number moved from "release" to "first number set" for Hindi? Default: leave it as Gate 4 wrote it.

**Subtract pass (§5):** removed a proposed new CI job for the false-text grep (a review step is enough), a proposed pre-release read of
every tenant's key (the key cannot exist before the new code), and a "boundary" endpoint fallback (already dropped in §4). Removed nothing else.
Left behind: nothing. No container, no file but this one, no setting.

---

## §6 Release readiness - 2026-11-19

(The slice-build skill calls this "§5 Release readiness". This file already has a §5 Strategy, so this is **§6**.)

**Read:** worktree `/Users/mac/hr-app/.claude/worktrees/084-employee-window`, branch `slice/084-employee-window`, cut from
`origin/dev` at `fd658eff`, six commits `b1d57b0a`..`c162374b` (named by the engineer; **I ran no git, so I did not confirm the SHAs**).
Files read today: `03-implementation-notes.md`, `04-test-report.md`, my §1-§5, `.github/workflows/deploy.yml` (trigger, inputs, plan job,
backup, refresh-assets, migrate and clear-cache, prune, worker check, rollback text), `deploy/compose/docker-compose.app.yml` (redis block),
`scripts/refresh_bench_files.sh` (grep). **Not re-read:** `DEPLOYMENT_RUNBOOK.md`, `REHEARSAL.md`. **Nothing was run.** No git, bench, docker,
gh or deploy command. Nothing changed except this file. Every command below is **quoted, not run**, and **requires Surbhi's approval**.

### Bad news first

1. **The rollback instruction GitHub prints on a failed deploy is the wrong one for this slice.** `deploy.yml` (the "Rollback instructions"
   step) says "previous tag and `run_migrations: false`". For 084, rolling back with migrations off can leave a cached hook list that names a
   function the old code does not have, and then **every Attendance Request save fails, HR's too** (engineer proved the mechanism, section 4 of
   `03`). **Roll back with `run_migrations: true`.** (OPS-31.)
2. **A green dev deploy proves nothing about the test suite.** The Deploy workflow starts after **"Build Image"**, not after CI
   (`deploy.yml` `workflow_run: workflows: ["Build Image"]`). Dev gets the code whether CI is red, running or never finished. And the full suite
   was never run to the end locally (4,433 methods, stopped at ~70 min). **CI is the only proof of the other ~3,400 tests.** (OPS-32.)
3. **The slice's own log line is not built, and the logger that would carry it drops it.** So there is no log to monitor. Section 5. (OPS-33.)
4. **OPS-28 (previous production tag proved in `alvoraa-app`) is still unchecked by anyone. P1. The release is not ready until it is.**

### 1. OPS-21 closed: what the deploy does to Redis

| Claim | Label | Source |
|---|---|---|
| `deploy.yml` contains no Redis flush of any kind | **Fact** | grep for `flush` over `deploy.yml` and the app compose file: no hit |
| The only cache clear is `bench --site all clear-cache`, run straight after `bench --site all migrate`, **inside `if [ "$MIGRATE" = "true" ]`** | **Fact** | `deploy.yml` 534-571 |
| An automatic push deploy always has `migrate=true`; only a hand dispatch can turn it off (`run_migrations` input, default true) | **Fact** | `deploy.yml` 143, 159 |
| Redis is its own `redis:alpine` service with `--appendonly yes` and a `redis-data` volume, so the cache holds across an app image swap, and across a Redis restart too | **Fact** (compose read). That compose recreates only changed services: **inference** | `docker-compose.app.yml` 164-172 |
| One Redis serves cache (DB 0) and queue (DB 1) | **Fact** | comment at line 166 |

**Answer:** on a rollback with migrations **off**, nothing touches Redis, so the cached hook list stays. With migrations **on**, `clear-cache`
refreshes it.

**A smaller window remains even with migrations on (inference from the order of steps, 519-571):** the new containers start (`up -d`), the loop
waits for `bench version` (about 7 minutes, measured 22 Sep), and only then do maintenance mode, migrate and `clear-cache` run. In that gap,
**on a rollback**, old code runs against the cached new hook list. Attendance Request saves fail until `clear-cache`. **Forward direction in the
same gap:** new code, old cached list, so the guard silently does not run. That is harmless at release because the setting is blank.
Not measured on a real deploy. Recommend: roll back in the night window, when almost nobody files. Nothing to build.

### 2. Rollout, local to dev to main

Each step needs Surbhi's word. I name the proof to write down for each.

| # | Step | Needs approval | Proof to write down |
|---|---|---|---|
| L1 | Before asking for dev: in the worktree, fetch `origin/dev`; if it moved, rebase and **read every incoming diff aloud** (CLAUDE.md section 1). The engineer saw `fd658eff` still current | local, already allowed | the SHA fetched and what came in |
| L2 | `git diff --stat origin/dev` shows nothing under `deploy/`, `Dockerfile`, `.github/`, requirements, `deploy/nginx.conf`, and **no `patches.txt` or DocType `.json`** (that last part is new in this section) | local | empty list for those paths |
| L3 | `scripts/check_app_integrity.py` before the commit. Engineer: 952 OK | local | the line |
| L4 | **Decide the untracked file** `test_employee_window_084_independent.py` (18 tests, ~60 s): commit it or delete it. Recommend **commit**: it is the only test of the `frappe.client.insert` route and of fixtures without a Shift Assignment | **Surbhi** | her answer |
| D1 | Check no CI is running on `dev` now (`gh run list`, read-only), else wait: a second push cancels it. Then `git push origin slice/084-employee-window:dev`. **One push, not several** | **requires Surbhi's approval: push to dev** | the pushed SHA |
| D2 | Build Image, then the automatic Deploy, from **`main`'s copy of the workflow** (no workflow change in 084, so that trap does not bite). Tag will be `dev-<first 7 of the SHA>` | automatic | the run id and the tag |
| D3 | **Wait for CI on that exact SHA to finish green.** See section 6 for exactly what counts | **Surbhi reads it** | CI run id, conclusion, test count |
| D4 | Landing proof, section 4 | read-only on dev, **only when Surbhi asks** | each check's output |
| D5 | On a dev test tenant: set a number, press Submit on an old day on the Attendance Request page and on the day sheet, clear the box, **read the value back** and write down what came back | **requires Surbhi's approval: dev data change** | the value read |
| D6 | Prove the previous production tag (OPS-28, section 6 below). Do it **now**, during dev, since it blocks nothing | **requires Surbhi's approval: read-only check** | tag, date |
| M1 | Surbhi tests on dev. Then her explicit word for main | **requires Surbhi's approval: push to main**, night window 00:30-06:00 IST | |
| M2 | Fast-forward `main` to the **exact SHA** that passed D3 (memory 12 Nov: a branch name gave the wrong release). Build Image runs again on main and makes `prod-<7 chars>`, a **new build of the same code**, not the dev image | **requires Surbhi's approval** | the SHA and the tag |
| M3 | Landing proof on the production stack, section 4. Production reads (pin file, containers) need her word each time | **requires Surbhi's approval** | outputs |
| M4 | Release note (section 3 of §3 / OPS-18, 19, 24): Grace has a second rule, other tenants "not checked", setting blank everywhere, "when a tenant asks for a number, run a read-only count first" | Surbhi reads | |

**Dispatch, if a hand run is ever needed.** The inputs are `environment`, `image_tag`, `image_package` (default `alvoraa-app`) and
`run_migrations` (default true) (**fact, read in `deploy.yml` 22-49**). Dev: `gh workflow run Deploy --ref dev -f environment=dev -f image_tag=dev-<sha> -f image_package=alvoraa-app -f run_migrations=true`. **Requires Surbhi's approval.** Production uses `--ref main`.

**There is no approval prompt on the production environment** (memory: no required reviewers on the free plan; the file's header comment
still says one should exist). The gate is a person starting it. Do not write a plan that assumes a prompt.

### 3. Migration dry run on a copy: not needed, and why

- **Why none:** 084 adds no DocType, Custom Field, patch or fixture (engineer, `03` section 1, AC-64; test report read `git show --stat`). **Not
  checked by me:** I ran no git. L2 above checks it. `bench migrate` therefore has nothing to change; `REHEARSAL.md`'s copy-of-real-data rehearsal exists
  for patches that rewrite rows, and there are none.
- **What does run anyway:** the deploy runs `bench --site all migrate` and `clear-cache` on every tenant (`deploy.yml` 570-571), after a pre-deploy
  backup of all sites (`Backup all sites` step). The **dev deploy is the rehearsal of that exact run**, on dev's tenants.
- **Two checks that are not about 084 but decide whether migrate really finished** (memory 5 Nov: a queue of 1,780 deletes stopped a migrate halfway and
  later sites were silently left behind):
  1. In the run log, count the sites migrated against the sites that exist. **Write both numbers.** "All sites migrated" is a claim.
  2. Before the production deploy, read the background-job queue length on production (read-only, **needs her word**). Not checked today.
- **No restore of the backup on rollback.** 084 writes no data of its own. The workflow's text "a migration ran: restore the pre-deploy backup"
  does **not** apply here and would lose a day of real data. Say so in the note.

### 4. After deploying: what to check, and how to say it landed

Each check below is **read-only** and **requires Surbhi's approval** on a live stack. Take container names from `DEPLOYMENT_RUNBOOK.md`:
`devstack-*` is dev, `compose-*` is **production**. Never mix them. **Not run by me.**

| # | Check | Pass looks like | Why |
|---|---|---|---|
| P1 | **Pin file.** Read `.image.dev.env` (dev) or `.image.env` (production) in `/var/www/html/hr-app/deploy/compose` on the server | names exactly the tag that was built (`dev-<sha>` or `prod-<sha>`) | a green run of an old tag hides everything |
| P2 | **Containers.** `docker ps` is not enough (lesson 15). List the image of every app container of that stack, then `docker top` on a worker, and run the repo's worker check (the deploy runs `scripts/check_workers.sh` itself) | every app container shows the same tag; the worker check passes | one worker on an old image crashed on a new argument |
| P3 | **The file itself.** Grep a new sentence from the day-sheet or org-settings hint inside the container's `org-settings.html` and `attendance_correction.py` | found | proves code, not just tag |
| P4 | **Assets (OPS-15, P1).** Compare `sites/assets/assets.json` in the **volume** with the one in the **image** (`docker run --rm --entrypoint bash <image:tag> -c 'cat .../sites/assets/assets.json'`, path as in memory `sites-volume-assets-stale`). Then fetch `/assets/alvoraa_portal/js/ess/portal.js` from the **served URL** and grep one new string from it (a string from the new own-day note, not an old one) | manifests equal; the served file holds the new string; the `?v=` on the page differs from before | the deploy's "Portal assets must be served" step checks the file **is served, not what is in it** |
| P5 | **Hook pin, in a live process, not a test.** Do **not** run the test suite on a tenant site (memory: tests overwrite tenant data; use `test_site`). Read `frappe.get_hooks("doc_events")` for `Attendance Request` from inside the production-like container and look for the `validate` entry naming `refuse_own_day_outside_window`. **The engineer should prove the exact one-liner on their stack first**: I did not, and `bench execute` swallows errors (lesson 8). Run it in **every** app container, not one | the entry is there after a deploy; **after a rollback, it is not** | the forward trap: migrations off leaves the guard silently off |
| P6 | **Blank everywhere.** Open the HR settings screen on the tenant, read the new row, change nothing, say the value shown | blank | no behaviour change at release |
| P7 | **Dev only, behaviour.** D5 above | an old day refused with a date; today and the joining day accepted; clearing the box lets the old day through again | proves the guard and the fast undo |
| P8 | Count sites migrated against sites present (section 3) | the two numbers equal | scope claim |

### 5. Rollback

**Rule: stored value first, image second.** The row HR types is in each tenant's database. The image rollback removes the screen that edits it
(`03` section 4A), so HR cannot clear it afterwards.

**Prerequisite (OPS-28):** the previous production tag, proved to exist in `alvoraa-app`, written in the release note, checked **again on release
night** before the deploy. Registry tags can be pruned. The server keeps the **two most recent prod tags on disk** (`deploy.yml` ~604-622), so the
previous tag should still be local after the new one lands: **inference**; if it is, there is no pull. Otherwise it pulls, and that must work.

**A. Planned rollback, new code live, a number is set on some tenant**
1. Read the hand list of tenants with a number (section 5). Read each tenant's value back (**needs approval on a live tenant**).
2. HR clears the box on each tenant, on the HR settings screen. **Read the value back and write what came back (blank).**
3. **Only then** redeploy the previous tag: `gh workflow run Deploy --ref main -f environment=production -f image_tag=<previous prod tag> -f image_package=alvoraa-app -f run_migrations=true` (**requires Surbhi's approval**). **`run_migrations` stays true** (section 1 and OPS-31); the GitHub failure text that says `false` is wrong for 084.
4. Prove it landed (P1-P4), and prove the **inverse of P5**: the hook entry is **absent** from every app container and an Attendance Request can still be saved by HR (dev: yes; production: look, do not write).
5. Cost: about 7 minutes lost to the `bench version` wait (**measured 22 Sep**, 6:54 dev and 7:09 production; **not measured for this slice**), plus maintenance mode while migrate runs. Plan a night window.

**B. Emergency, number is set, no time to ask HR:** roll back with `run_migrations: true`, then **tell that tenant's HR in words**: "the limit you set is no longer enforced". Do **not** delete the row (it is HR's data; rolling forward restores the rule with no work). The old code ignores the unknown key.

**C. The fastest undo needs no deploy:** while the new code is live, **HR empties the box**. Blank means no limit and the hook costs 0 statements
(tested). **Say this first in any incident.** Read it back.

**D. If the guard itself is faulty (it blocks things it should not):** do C first. It stops the guard from refusing anything. Only then decide on a rollback.

**Do not** restore the pre-deploy backup on a rollback of this slice (section 3). **Do not** choose "migrations off" for a rollback or a fix-forward.

### 6. What Surbhi waits for before dev counts as proven

A dev push counts as proven only when **all five** are true, written down with the dev SHA beside them:
1. **CI finished green for that exact SHA.** Not "started". Not a CI tick from an earlier SHA. If a second push goes in, CI restarts, so **do not push twice** (memory 4 Nov).
2. **CI's test count is read**, not just the colour. The split run-parallel-tests job is what runs the 4,433 methods; confirm every shard reported.
3. **Any red is compared with the last dev tick before this slice** (`fd658eff`), not assumed to be ours. Memory 3 Nov: red may be site state. The five modules that errored in `setUpModule` for the test engineer
   (`test_leave_credit_rows_063`, `test_notices_076`, `test_late_minutes_017`, `test_grooming_066`, `test_daily_workings_alv358`) are the first suspects for **a fresh-site baseline problem, not 084**
   (**assumption**: only 063 was diagnosed). If CI is red on a **different** module, that is ours until shown otherwise.
4. Landing proof P1-P4 on dev, and P7.
5. Dev looked at by a person on a phone width and a keyboard: **not automated** (`04` section 11). No browser, phone or screen reader check has been run by anyone.

**For main**, repeat 1-3 on main's own SHA. There is a precedent for shipping on a deliberately red tick (2 Nov). **Do not repeat it for this slice
without her explicit word**, since the guard is on a permission-adjacent path and the test report is the only substitute for the full suite.

### 7. Monitoring, and why the security log is not part of it

**Fact (reported by the caller, checked on the live dev site; not checked by me, production refused as unauthorised):** `frappe.logger("security")`
sits at ERROR, `.warning` is dropped, and `security.log` on dev is **0 bytes**. ALV-391. The engineer also found `access.log_refusal` (SEC-17) writes at `.warning`.
**Consequences I can state:**
- **There is no log of a refusal, and no log of who changed the setting.** Nothing to alert on, nothing to read back.
- **The existing SEC-17 refusal log has possibly never been written on dev, and may not on production.** That is a bigger finding than 084; it belongs to ALV-391.
- **OPS-30's hand list is no longer a stopgap "until Q6 is answered". Q6 is answered. It is the only record.**

What is available, with no new moving part:

| Signal | What it tells you | Honest limit |
|---|---|---|
| **Hand list**: tenant, number, date set, who set it | which tenants to warn on a rollback (case A or B) | a person keeps it. Recommend Surbhi owns it: she already gates the first number through counsel (Gate 3 C1). Update it **in the same minute** the number is set |
| **Read-back on the setting** (the key named by `EMPLOYEE_FILING_WINDOW_KEY` in `attendance_correction.py`; I did not type the key's value) | the real value now | live tenants need her word; no history of changes |
| **Error Log doctype**, read by a person for 24 h after the first number is set on a tenant | an unexpected crash in the hook (an `AttributeError` or `TypeError` would be an unhandled error) | **inference**: Frappe normally records an unhandled exception there, and a deliberate refusal (`ValidationError`) is not recorded. Not checked, not alerted |
| **The deploy's own checks**: worker check, "Portal assets must be served", smoke test | deploy-level breakage | does not see the guard |
| **Support signal**: an employee says "refused, with no date on screen" | old JS with new guard (P4 failing) | late and by hand |
| **Query counts** (measured today by the test engineer, tiny data): `month()` 17 / 16.8 ms blank, 19 / 16.7 ms with a limit; `get_requests_history` 5 / 2.8 ms, 7 / 4.5 ms; a refused insert 10.5 ms | the 500 ms API budget is met by a wide margin **at three-row volume only** | not a scale claim. The flatness test shows no growth with 300 more holiday rows |

**Not recommended:** a new alert, a refusal counter or a dashboard. A number set on one tenant does not justify a new moving part. **If Surbhi wants
a real record, the cheapest fix is ALV-391 option (b):** give the `security` logger its own level in one place, which also repairs SEC-17. That is a
separate small change, **not before release (the setting ships blank), but before the first number is set on any tenant.** It is her choice.

**Capacity:** nil change. No new container, volume, queue, worker or image dependency. Disk gate before pull stays as is. Month-end load: the hook is
0 statements for HR's actions and about 4 per employee submit **only when a number is set**.

### 8. What Surbhi must decide

**Before any push to dev:**
1. **Push to dev** (one push, after CI is not running). Whether to commit the untracked independent test file (L4).
2. **The inline row versus the prototype's dialog** (parity gap, `03` section 6, test report section 10). Her yes is needed, per the prototype-parity rule.
3. **Hindi (OPS-26):** confirm "release blank without it; no number on a Hindi-reading tenant until a native reader has done `hi.csv`". Gate 4 currently says release waits.
4. **Who proves the previous production tag, and when** (OPS-28). My recommendation: she names a session now, read-only, during dev. It needs `read:packages` on the token **[ASSUMPTION]**; the owner in `deploy.yml` is `surbhigoyal7381-agent` (a user account), so the read is `gh api /user/packages/container/alvoraa-app/versions --paginate` run as that user. **Quoted from `deploy.yml` and lesson 19, not run.**

**Before any push to main (in addition):**
5. **CI green on main's own SHA, read by her** (section 6), and **no repeat of the deliberately-red precedent**.
6. **The previous production tag, named and proved, twice** (now, and again on release night).
7. **The night window**, and who is awake for the rollback if P4 or P5 fails.
8. **Release note wording** (OPS-18, 19, 24): Grace's second rule, other tenants "not checked", blank everywhere, "no number without a read-only count first and counsel's word".
9. **The ALV-391 choice** (a, b or c): **(b) before the first number is set**, not before release. And **who owns the hand list**.
10. **The first number is a separate decision**, never a release step: counsel (Gate 3 C1), Hindi (3), DTC manual search (OPS-25), `next-time.js` (OPS-27), Grace's 3-a-month script read (OPS-3, 18).

### §6 rows (Decision column left blank for Surbhi)

| ID | Recommendation | Why | Cost of ignoring it | Level | Decision |
|---|---|---|---|---|---|
| OPS-31 | Roll back and fix-forward with `run_migrations: true`; correct the "false" in the deploy's failure text for this release. Closes OPS-21: `deploy.yml` never flushes Redis; only `clear-cache` inside the migrate branch does | cached hook list survives a restart | every Attendance Request save fails after a rollback, HR's too | Recommend, P2 | |
| OPS-32 | Dev is proven only by CI green on the exact SHA, not by the deploy. One push; read the count and any red against `fd658eff` | Deploy follows Build Image, not CI; the full suite never finished locally | ~3,400 tests nobody ran | Recommend, **P1** | |
| OPS-33 | Treat the security log as unusable. Keep the hand list as the only record; Surbhi names its owner; fix ALV-391 (b) before the first number | `.warning` is dropped, `security.log` is 0 bytes on dev | nobody knows whom to warn; SEC-17's refusals may never have been written | Recommend, P2 | |
| OPS-34 | Run P1-P8 after each deploy; prove the hook entry in **every** app container, not a test on a tenant | green deploy of old tag; forward trap leaves the guard off | silent guard-off | Recommend, P2 | |
| OPS-35 | No migration rehearsal on a copy; the dev deploy is the rehearsal; count sites migrated vs present; do not restore the backup on rollback | no schema, patch or fixture | a pointless rehearsal; or a rollback that restores and loses a day | Recommend, P3 | |
| OPS-36 | Commit `test_employee_window_084_independent.py` (adds ~60 s to CI) | only test of the REST insert route | one route untested | Consider, P4 | |
| OPS-28 (restated) | The previous production tag, proved in `alvoraa-app`, **during the dev stage**, by a session Surbhi names, then again on release night | no tag, no rollback | no rollback | Recommend, **P1** | |

**Subtract pass (§6):** I removed a proposed pre-release dry run on a copy of production data (no schema or patch to rehearse), a proposed refusal counter and alert
(nothing to feed it), and a proposed separate check script for the hook (the engineer's one-liner is enough). I kept the asset and hook checks because each
is the only proof of a silent failure. Nothing left behind: no container, file or setting; only this file changed.

**Open and mine to close next time:** the exact P5 one-liner (needs the engineer's stack), the container names (runbook), whether the previous prod tag is
still in the registry (OPS-28). **Not checked at all:** production's `DEV_SERVER` setting, `/api/` access-log retention, and DTC manual wording.
