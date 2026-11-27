---
slice: 088-register-notice-and-forms
artifact: 05-review (senior architect review, change-process step 5)
author: hrms-technofunctional-reviewer
date: 2026-11-24
scope reviewed: `origin/main..HEAD` = `f68f2333..b4cf01a5`, 18 commits
where I looked: worktree `/Users/mac/hr-app/.claude/worktrees/release-088-alv436`, branch `release/088-alv436`, HEAD `b4cf01a5`; frappe source read inside container `alv436rel-bench`; no site, no tenant, no production system touched
status: advice. The decision to release is Surbhi's.
---

# 088 + ALV-436 + ALV-435 + the leave-card date fix · senior architect review

## 1 · Verdict

**BLOCK for production.** Two defects in this diff would be met by real users in the
first week, and one of them is not in slice 088's own feature at all: the new print
stylesheet hides every other printable screen in the portal, and a notice of six or
more changed days cannot be recorded at all, so the employee's pay stays held with no
way through the screen.

Both are small, local fixes. Neither is a design problem. With them fixed, and with the
release conditions in §8 written down, this is a **SHIP WITH FIXES** slice: the data
model, the refusals and the test habits in it are the strongest I have reviewed in this
repo.

**What the missing artifacts cost this review** (ranked at P2, finding 6):

- There is **no `00-impact-analysis.md`**. Step 1 of the change process produced no
  artifact for this slice, so I could not do the job this review exists to do — compare
  the dimensions the proposal claimed against the code that was written. I did the seven
  dimensions myself instead (§5). Nobody's claim is being checked; mine is the first.
- There is **no `03-implementation-notes.md`**. Several real decisions are recorded only
  as comments inside the code (the switch split, why `notices_are_on` fails closed, why
  the scope is resolved to ids). The comments are good, but a reader six months from now
  has to find them.
- There is **no `04-test-report.md`**. Every test figure I was handed is somebody else's
  claim. I verified what I could myself (§7); the 134-test 087 figure I did not.
- There is **no `06-security-review.md`** running beside me, so nothing in this slice has
  had a second pair of eyes on SEC-1..11 and PRIV-1..6 other than mine.

## 2 · Findings, worst first

### P1-1 · BLOCKER · A notice with two or more pages cannot be recorded. Pay stays held

**Proven, by running it.** `register_notice.list_people` builds each row at
`alvoraa_portal/alvoraa_portal/register_notice.py:348-369`. The keys are: `employee`,
`employee_name`, `employee_number`, `branch`, `changed_days`, `open_days`, `state`,
`uncovered`, `i_filed`, `printed_at`, `printed_by`, `recorded_by`, `recorded_on`,
`said`, `notice`, `can_tick`, `can_record`. **There is no page count.**

The record dialog reads one:

- `portal.js` (new block) `rnDrawRecord`: `var pages = r.pages || 1;`
- `portal.js` `rnSend`: `var pages = rnReg.row.pages || 1;` then
  `if (rnReg.photos.length !== pages) { ...refuse... }`

So `pages` is always 1.

*Inputs / state → what happens → why it is wrong.* Ramesh has 6 approved changes
someone else filed in November. `open_notices` writes one notice with `page_count = 2`
and returns two A4 sheets (`PER_PAGE = 5`). He signs both pages. HR opens "Signed on the
register":

- the dialog says *"One photo of each signed page (1 pages)"* and omits the "(2 pages)"
  sentence the prototype draws;
- HR adds the two photos → the **client** refuses: *"Add 1 photos, one for each page. You
  added 2."* and sends nothing;
- HR adds one photo → the **server** refuses: *"Add 2 photos, one for each page. You
  added 1."* (`register_notice.py:763-767`).

There is no third option. The change stays unconfirmed, `_unconfirmed_filters` keeps
holding the salary slip (`punch_fix.py:864-875`), and the one route 088 exists to
provide is closed for exactly the employees with the most changed days — which at DTC is
the people whose days HR fixes most often.

**The test could never have shown it.** `alvoraa_portal/tests/portal_register_notice_088_test.js:323`
patches the fixture by hand before the multi-page case:

```js
window.rnState.rows.filter(r => r.notice === NOTICE)[0].pages = 2;
```

`listRows()` (lines 33-51) has no `pages` key, correctly mirroring the server. The patch
invents one. I copied the suite, deleted that one line, and ran it against the real page:

```
FAIL  the photo count guard let the call through or worded it wrongly: ... One photo of each signed page (1 pages) ...
FAIL  record sent [] undefined
### 088 change notice DOM test: 27 passed, 2 failed
```

**Smallest fix.** Add the number to the row the server already has in hand —
`_latest_notices` already selects `page_count` (`register_notice.py:236-239`) — e.g.
`"pages": cint(notice.get("page_count")) or 1` in the row dict at line 348, and delete
line 323 of the browser test so the fixture is the server's shape again.

### P1-2 · BLOCKER · The new print stylesheet blanks every other printable screen in the portal

**Proven by reading; the blank page itself is inferred from the cascade, not rendered.**
`alvoraa_portal/alvoraa_portal/public/css/ess/panels.css`, new block at the end of the
file:

```css
@media print{
  body>*{display:none !important}
  body>.rn-pv{display:block !important; ...}
```

This is **not conditional on anything**. `panels.css` is the portal's shared stylesheet,
it loads on every ESS page, and the rule applies to every print of the portal whether or
not the 088 preview is open — and whether or not the tenant ever turns
`alvoraa_print_change_notices` on. The switch does not gate CSS.

Two shipped features print from the page itself:

1. **The wall chart** (slices 069/072). `posWallHolder()` appends its print root
   **directly to `<body>`**: `portal.js:3702-3708`, `h.id = "pos-wall-print";
   document.body.appendChild(h)`. The wall chart's own print rules
   (`panels.css:2405-2411`) set `position` and `visibility` on `#pos-wall-print` and
   **never set `display`** — I grepped: the only `display` declarations near it are
   `body.pos-wall-printing > :not(#pos-wall-print){display:none}`. So 088's later
   `display:none !important` on `body>*` wins and the chart prints blank pages.
2. **The Positions chart A4 print** (`panels.css:2337-2346`) keeps `#panel-positions`
   and hides the frame. `#panel-positions` lives inside the page shell
   (`templates/includes/ess/parts/positions.html:2`), so whichever element is its
   top-level body child is now `display:none !important` and the whole print is blank.

*Why that is wrong:* an HR Manager at any tenant presses Print on the org chart in their
first week and gets empty paper, with no error and nothing on screen to explain it. It is
a regression caused by a feature they may not even have switched on.

**Smallest fix.** Scope the rule the way this very file already does it two blocks
earlier — `body:has(#panel-positions.active)` at line 2338. Either
`body:has(.rn-pv)>*{display:none !important}` / `body:has(.rn-pv)>.rn-pv{display:block}`,
or add a `rn-printing` class to `<body>` in `rnPreview` and remove it in
`rnClosePreview`, and prefix the four print rules with it.

### P2-3 · MAJOR · "Signed on the register" is offered on a notice already answered "Not right"

**Proven.** `register_notice.py:368`: `"can_record": state["code"] in ("printed", "not_right")`.
`_state` returns `not_right` when the latest notice's outcome is `Not right`
(line 280-281). `record` then refuses every such call:
`if doc.outcome in ("Signed", "Not right"): frappe.throw(_("This notice has already been answered."))`
(line 741-742).

*Inputs / state → what happens → why it is wrong.* The worker says the page is wrong. HR
records it. The row keeps showing a primary-looking "Signed on the register" button.
Later the worker signs the reprint — or HR simply tries — and the button always fails
with "This notice has already been answered." Spec §5.3 lists the buttons for that state
as **"Print again"** only. A button whose only outcome is a refusal teaches HR to
distrust the screen.

**Smallest fix.** `"can_record": state["code"] == "printed"`. (And if the intent was that
an objection can later be converted to a signature, that is a product decision and needs
Surbhi, not a silent server refusal.)

### P2-4 · MAJOR · The new row filter hides every joiner export and purge row from HR Managers

**Proven.** `hooks.py:644` adds
`"Alvoraa Photo Access Log": "alvoraa_portal.register_notice.photo_log_query_conditions"`,
which emits (via `_scope_sql`, `register_notice.py:865`):

```
`tabAlvoraa Photo Access Log`.employee in (select name from `tabEmployee` where ...)
```

But `joiner_invite._write_joiner_row` (`joiner_invite.py:858-865`) inserts rows with
**no `employee` field at all** — a joiner has no Employee record yet. Fields written:
`reference_name`, `source`, `viewed_by`, `viewed_at`, `viewed_on_date`. A `NULL` never
satisfies an `IN (...)`.

*So:* after this release an HR Manager listing `Alvoraa Photo Access Log` sees no
"Joiner export (masked)", "Joiner export (not masked)" or "Joiner purge" row — the exact
rows counsel's "log every export" condition rests on (her 19 Nov decision to keep them
for ever). System Manager is unaffected (`_scope_sql` returns `""` for them).

Per the project memory, no production site has ever issued a joiner invite, so there are
probably no such rows today — **I did not check production and must not**; that is
inferred from the memory note, not measured. The defect is prospective, which is why it
is P2 and not P1: the day a joiner export happens, its audit row is invisible to the role
meant to read it.

**Smallest fix, and a decision to name.** A row with no employee cannot be scoped by
employee. Either keep those rows System-Manager-only on purpose and write that down, or
scope joiner rows through the submission's company. Needs one line from Surbhi, as it is
an audit-visibility rule. Owner: `hrms-security-privacy-engineer` to recommend.

### P2-5 · MAJOR · The new Python suite carries a date bomb, the same class this branch just fixed

**Proven by reading; not executed under a shifted clock.**

1. `tests/test_register_notice_088.py:748`:
   `self.assertTrue(sheet["ref"].endswith("/2026-11/1-1"), sheet["ref"])` — a hardcoded
   month. `ref` is built from `first.strftime("%Y-%m")` where `first` is the first of the
   month of `self.day`, and `self.day = add_days(nowdate(), -5)`
   (`test_held_day_085.py:71`). From **6 December 2026** that string is `2026-12` and this
   test fails for ever.
2. `an_approved_hr_change` (test file, lines 160-176) takes a new day per call by walking
   backwards: `add_days(self.day, -len(self._days))`. `qualifying_changes` filters
   `from_date between [month, last_day_of(month)]` (`register_notice.py:204-206`). So
   whenever `nowdate() - 5` lands in the first days of a month — the **6th to the 10th of
   every month** — the multi-change tests (the 5-and-1 page split, the content-hash test,
   "the caller cannot choose", the pay-line test) lose changes across the month boundary
   and assert the wrong counts.

The branch's own last commit fixes exactly this fault in `portal_leave_063_test.js`
("went red on a date, not on a defect"). The same bomb went in two commits earlier in
Python. **Smallest fix:** derive the expected month from the fixture
(`get_first_day(self.day).strftime("%Y-%m")`), and pin the fixture's days inside one
month (e.g. anchor on `get_first_day(nowdate())` plus an offset, or walk forward within
the month rather than backwards out of it).

### P2-6 · MAJOR · No impact analysis, no implementation notes, no test report

Named in §1. It is a process finding, not a code one, but it is the reason three of the
findings above had to be discovered rather than read. The missing `00` is the one I would
not waive: on a slice that adds three DocTypes, a Custom Field and a global print
stylesheet to three live tenants, the seven-dimension analysis is what catches a
cross-feature regression like P1-2 before it is written.

### P2-7 · MAJOR · The slice's own documents say release to a customer is blocked

`02-functional-spec.md:654`: *"Release (not build) is blocked on C1, C2, C3 and the
Hindi review."* `01c` §19.6 and the brief's counsel list say the same: C1 (is a
photographed thumb print biometric data, and who may open it), C2 (retention period and
who deletes), C3 (one photo per page enough; HR's record of the worker's words enough).
Surbhi's 21 Nov decision 5 says these were **asked** of counsel, not answered. There is
no artifact in this slice recording an answer, and no `06-security-review.md`.

**This does not have to block the code.** The switch ships off and
`notices_are_on` answers NO when the column is missing, so a tenant that never turns it
on collects nothing new: no photo, no notice record, no screen. That is the honest
mitigation and it is already built.

**Recommendation:** ship the code dark; do **not** turn
`alvoraa_print_change_notices` on at DTC or Grace until C1, C2, C3 and the Hindi reader
are recorded in writing. Owner: Surbhi, with
`hrms-security-privacy-engineer` to write the record.

### P3-8 · The scope is read into Python and shipped back as `IN (...)`, against the NFR budget

`qualifying_changes` (`register_notice.py:193-196`) reads every permitted employee name
into Python, then filters the Attendance Request query with `employee in (<ids>)`.
`.claude/context/nfr-budget.md` line 65 forbids exactly this, by name, with the slice-044
precedent (981 values) — *"the scope stays in the database — a join or a subquery, never
a list of ids read into Python and shipped back as `IN (...)`"*.

The module already has the right tool: `_scope_sql` (line 839-866) builds the subquery
form for the row filter. The code comment explains the real constraint (Attendance
Request has `company` but no `branch` column) — which the subquery form solves and the
id list does not.

Worst case today: `my_changes` passes `dict(access.ALL_EMPLOYEES)` (line 927), so **every
employee's month view pulls the whole `tabEmployee` name list** to then keep exactly one
id. At 600 employees that is tolerable; at 10,000 on the last day of the month with
everyone opening the portal it is 10,000 rows per request for no benefit.

*Not checked:* I did not time it. Treat as a reasoned finding, not a measurement.

### P3-9 · No phone-side shrink before upload

`rnPickPhotos` reads each file with `FileReader.readAsDataURL` and posts it whole. The
spec's own NFR table (§12) and OPS-9 describe a phone that shrinks to about 1,600 px /
JPEG 75 before upload, about 350 KB, 3-5 s on 3G. What ships uploads the camera's
original — typically 2-8 MB per the 081 comments — so a shop on a weak connection waits
roughly ten times longer, and anything over 12 MB is refused *after* the whole upload
has gone up (`expense_evidence.RAW_B64_MAX_CHARS`). The spec already flagged "no AC can
prove the phone side" as a gap; this confirms the gap is a real one in the build, not
just in the test plan. Server-side caps are correct and unaffected.

### P3-10 · The paper's own words go through the translator

Every string on the A4 sheet in `rnSheetHtml` is wrapped in `rnT`, which calls
`window.__` when Frappe's translator is on the page. Decision 3 and AC-24 say the paper
is **English only, whatever the screen language**. The server side was careful about
this — `WHAT` deliberately avoids `_()` with a comment saying why — and then the client
undoes it for the headings, the boxed rule, the read line, the box labels and the footer.

Today nothing happens: `alvoraa_portal/translations/hi.csv` has **1 line**, so no sheet
string has a Hindi translation. It is a latent fault that fires the day Hindi lands,
which is the one change this slice's design is waiting on. **Smallest fix:** leave the
paper strings as plain literals, as `register_notice.WHAT` does.

### P3-11 · Rollback does not leave the field "empty", and that changes pay

AC-63 and OPS-28 say rollback leaves the DocType and field "in the database, unused and
empty". True only if nobody recorded a signature in the window. If they did, the old code
has no `signed_column_ready()` branch in `_unconfirmed_filters`, so those changes become
unconfirmed again and the salary slips they had released are held again. Not a code
defect — a line the release plan must carry. Owner: `hrms-devops-engineer`.

### P3-12 · A System Manager can hand-type a notice's answer while it is still "Printed"

`alvoraa_register_notice.py` closes `ANSWER_OWNED` only `if before.outcome in ANSWERED`.
The DocType gives System Manager `write`. So on a notice still in `Printed`, a System
Manager can set `outcome = Signed`, `recorded_by`, `recorded_on` and `dispute_reason`
by hand in the Desk, bypassing the filer rule and the photo requirement.

It does **not** lift the pay gate — that needs `alvoraa_signed_notice` on the request,
which only `record_register_signature` writes — and `track_changes` records who did it.
But AC-30 reads wider than the code does. Either tighten (`ANSWER_OWNED` writable only
under the flag) or write the exception down.

### P4 · Nits, in one list

- `list_people`'s docstring (`register_notice.py:296-304`) still describes the **old**
  confirm-switch behaviour and calls it "a departure from the approved spec". After the
  23 Nov split it is simply wrong, and it is the first thing a maintainer reads.
- `MINE_STATES` (`register_notice.py:893-898`) is referenced nowhere. The four sentences
  live in `portal.js`'s `said` map. Dead code, and two copies that can drift.
- `_state` compares only membership, not the stored `content_hash`; spec §5.3 defines
  "changed after printing" as *"not in the latest notice, **or** its content differs from
  the stored hash"*. Unreachable in practice — no field on Attendance Request is
  `allow_on_submit` (I grepped both the app and
  `hrms/hr/doctype/attendance_request/attendance_request.json`), so a submitted request's
  content cannot be edited through the ORM at all; the 088 test reaches it with
  `frappe.db.set_value`. Hence P4, not P2.
- No counterpart to `punch_fix.py:531` for the register: when confirmed content changes,
  an app Confirm is cleared but `alvoraa_signed_notice` is put back. Same unreachability.
- The "not right" row note drops the prototype's `"The changes stay open: {3}"` clause
  (prototype `nr_note`); it shows the worker's words instead.
- `_latest_notices` orders by `printed_at asc` only; `_latest_for` by
  `printed_at desc, creation desc`. Two prints inside the same microsecond would
  disagree. Microsecond timestamps make it theoretical.
- `employee` and `month` each carry `search_index: 1` **and** the composite
  `employee_month` index is added in `_index()`. Three indexes on a small, insert-only
  table.

## 3 · The four things I was asked to look at specifically

**Migration safety — passes, and it is the best-argued part of the slice.**

- Hook order is right: `register_notice.after_migrate` is listed **after**
  `punch_fix.after_migrate` in both `after_migrate` and `after_install`
  (`hooks.py:801-805`, `899-903`), which is what the `insert_after` on both new fields
  needs. `after_migrate` also returns early unless the notice DocType exists, so the Link
  is never created pointing at nothing.
- **Interrupted migrate fails closed, every way round.** Column present but DocType
  missing → `columns_ready()` False → list returns the empty shape, print throws a plain
  sentence. DocType present but Company switch missing → `notices_are_on` returns False.
  Switch present but request column missing → `columns_ready()` False. And
  `_unconfirmed_filters` only adds the new filter behind `signed_column_ready()`, so the
  salary-slip gate cannot die on an unknown column between a deploy and its migrate
  (`punch_fix.py:864-875`). That one guard is what keeps a half-finished migrate from
  taking payroll down.
- **A tenant that never turns the switch on:** three new empty tables, one new nullable
  column, one new Company checkbox at `0`, one extra Select option, one extra row filter
  on the photo access log (see P2-4), and the global print CSS (see P1-2). No scheduler
  entry, no job, no new dependency, no new container.
- `_index()` swallows its own failure on purpose — correct; a missing index is a slow
  list, not a broken migrate.

**The switch's blast radius — no reader was missed.** I grepped the whole worktree for
`CONFIRM_SWITCH`, `confirms_are_on`, `NOTICE_SWITCH` and `notices_are_on`. All three 088
surfaces read the new switch: `list_people:331`, `open_notices:566`, `my_changes:923`.
The four remaining `confirms_are_on` call sites (`punch_fix.py:500, 525, 928, 965`) are
087's own — whether a change asks for a confirm, the before-payroll list, the day sheet —
and must stay on the confirm switch. Nothing reads the wrong one.

`notices_are_on` answering **NO** on a missing column is correct and the docstring's
reasoning is right: before the migrate there is no notice table to print into, so
"not yet" is the honest answer, whereas 087's YES-on-missing protects behaviour that is
already live. Confirmed intentional, do not "align" them.

One question worth her word, not a defect: `my_changes` is now gated by the **print**
switch, so at a tenant with confirms ON and notices OFF, an employee **with** the app
loses the "N days were changed by someone else" view. That may be exactly what was meant
(US-7 was always part of the paper-round story) — if it is, say so; if not, gate it on
either switch.

**ALV-436's placement — right, and I verified the premise rather than trusting it.**
Placing `refuse_if_the_words_would_be_lost(doc.get("explanation"))` **before** the
`alvoraa_for_held_day` column guard in `validate` is correct: the check needs no column,
so it covers a site between deploy and migrate, and it covers every door into the
DocType — portal, Desk, REST, import — rather than one endpoint.

I read frappe's own code in container `alv436rel-bench`:
`frappe/utils/html_utils.py:146-191` (`sanitize_html` returns the input unchanged when
BeautifulSoup finds no tag) and `frappe/model/base_document.py:1307-1345`
(`_sanitize_content` skips values with no `<` or `>`, skips submitted documents, and
calls the same `sanitize_html`). Then I ran 24 strings through the real function:

```
REFUSED  'Machine down <no punch>'      -> 'Machine down '
REFUSED  '<machine down>'               -> ''
REFUSED  'mail me <ravi@dtc.com>'       -> 'mail me '
allowed  'temp <35 degrees>'   'a<b'   '9 > 8'   'Site A -> Site B'   '100%'
allowed  'Ravi & Sons'   'He said "ok"'   'line1\nline2'   'काम नहीं हुआ'   'ok 🙂'
allowed  '< 5 min'   'a < b and c > d'   '15'   '<b>late</b>'   '10<br>late'
```

So the refusal fires **only** where text would really be lost, and it cannot refuse a
save that previously stored what the person typed. Two notes:

- It now also refuses on plain hrms Attendance Requests (leave/WFH regularisation), not
  only punch fixes, and it refuses an angle-bracketed email address. Both are the right
  answer — that text was being eaten — but they are a behaviour change on a shared
  doctype, and an old-data import carrying `<...>` would now fail. Worth one line in the
  release note. P4.
- `validate` runs again at submit, where frappe would **not** sanitise. The check is
  still correct there because a draft carrying `<word>` can no longer be saved, so no
  submit can carry one.

**Cross-module impact.** `erpnext` and `hrms` source untouched (the only `hrms` file in
the diff is nothing — `hrms` is not in the changed-file list at all). `alvoraa_goals`
untouched. Inside `alvoraa_portal` the slice reaches four shared things: `punch_fix`
(new constant, new seam, new filter — all guarded), `expense_evidence` (two dictionary
entries, correctly reusing the decoder, caps and access log rather than copying them),
`subscription.TENANT_DOCTYPES` (right side of the control-plane line), and `panels.css`
(P1-2). Personas: **CXO** gains nothing and sees nothing (no role row). **HR Manager**
gains the card, scoped by company *and* branch in both the list and the row filter.
**Employee** gets their own month list, own record only, with no id to swap — and the
photo is attached to the notice, not to the request, which is the structural reason their
own login cannot fetch it. The persona question that usually finds the leak here finds
none.

## 4 · Acceptance criteria

Walked against the code. I verified the groups below; I did not re-run the Python suites,
so "test" means I read the test and judged what it would catch.

| AC | Verdict | Evidence |
|---|---|---|
| AC-1..AC-5 list contents, states, done/waiting | met | `list_people:306-371`; `qualifying_changes` five tests at :221-228; tests `TheHRList` |
| AC-6 empty and error words | met | `rnDraw` empty/err branches; DOM test "an empty month names the month" |
| AC-7 paging 25 + Show more | met | `PAGE = 25`, `rows[start:start+PAGE]`; `_rows_for_me` walks pages |
| AC-8 no reason/explanation in the list payload | met | row dict :348-369 holds none; test `test_the_response_carries_no_reason_no_time_and_no_request` |
| AC-9 card not rendered without an HR role | met | `rnState.phase = isDenied(e) ? "hide"`; DOM test asserts the card is empty |
| AC-10 forward arrow off at this month, 300 ms skeleton | partial | arrow disabled proven; **the 300 ms skeleton is not measured** anywhere |
| AC-11 record written, then content | met | `open_notices:571-593` inserts before building sheets; test asserts row then sheet |
| AC-12 insert fails → nothing returned | met | one transaction; `_write_the_notice` raises before any sheet is built |
| AC-13 101 people refused, nothing written | met | `MAX_PEOPLE` check before any write; test asserts the count before and after |
| AC-14 five ticked → five records | met | loop at :563-593 |
| AC-15 no reason/hours/text on the record | met | test greps the whole serialised doc for the words, the time and the sentence |
| AC-16 markup in a reason stays literal | met | every insertion point in `portal.js` goes through `gpEsc`; DOM test covers the sheet |
| AC-17 POST only, CSRF, rate limit | partial | `methods=["POST"]` and `__alvoraa_limit__` proven; **CSRF I did not test** — it rests on the existing `gpFetch` path |
| AC-18..AC-20 one sheet, weekday, four sentences, filer, reason in full | met | `sheet_rows`, `WHAT`, `KIND_SENTENCE`, `_day_words`; and `filed_role`/`filed_by` implement Surbhi's OQ-1 reversal — "HR" with no name, a manager named |
| AC-21, AC-22 nothing else on the paper | met | the sheet is built only from the qualifying change rows; set-aside punches come from `punch_fix.aside_names` |
| AC-23 pay line only where the page holds pay | met | `pay_line: any(r["blocks_pay"] ...)` per sheet; test covers both ways |
| AC-24 English paper under a Hindi screen | **partial** | server sentences protected; client labels translate. See P3-10 |
| AC-25 boxed rule, read line, 26 mm box, date box | met | `panels.css .rn-a4 .rn-box{height:26mm}`; strings present |
| AC-26 reference with the print number, differs on reprint | met | `ref` + `print_no`; test asserts a reprint differs |
| AC-27 signed marks every covered change | met | `_write_the_answer` → `record_register_signature` |
| **AC-28 one photo per page, 3 pages needs 3** | **not met on the screen** | server side correct; the dialog cannot send more than one. **P1-1** |
| AC-29 edited change stays open and is named back | met at record time | `_still_the_same`; the row state misses it (P4) |
| AC-30 hand-set field is put back | met | `SERVER_OWNED` now includes `SIGNED_NOTICE` (`punch_fix.py:513`); controller refuses print-owned edits |
| AC-31 caller cannot choose the covered days | met | `covered = list(doc.changes)`; test passes extra ids and asserts they are not marked |
| AC-32, AC-33 no record / newer notice refused | met | `_latest_for` check at :743 |
| AC-34, AC-35 photo checks, generated name | met | `_photo_bytes` → 081's `_decode`/`_shrink_to_cap`; `_stored_name` |
| AC-36 reused photo refused | met | `_refuse_a_reused_photo`; test uses a fixed colour to repeat the bytes |
| AC-37 preview and empty-photo words | met | dialog strings; the name-and-ref check line is present |
| AC-38 all or nothing, photos survive a failure, no cache | met | one transaction; `rnReg` keeps the photos; no storage API used |
| AC-39 stored size logged with no names | met | `_save_the_photo` logs notice, page, bytes, user |
| AC-40..AC-43 objection | met | `record` requires a reason, stores it, marks nothing; filer refused for both outcomes |
| AC-44..AC-46 photo private, parent is the notice, no export | met by structure | `is_private = 1`, attached to the notice; DocType grants no create/delete/export/report to anyone. **The `GET /private/files/...` 403 is not tested** — there is no HTTP test |
| AC-47 photo log scoped | met for employee rows | `photo_log_query_conditions`; see **P2-4** for rows with no employee |
| AC-48, AC-49 nothing deletes | met | `on_trash` refuses for every role; no delete call anywhere in 088; no scheduler entry |
| AC-50 employee + month stored, no `retain_until` | met | DocType json |
| AC-51..AC-53 employee's own view | met | `my_changes`; `shown` state for a manager addition |
| AC-54..AC-56 employee / manager / sync refusals | met | `_hr_or_refuse` on all four calls; no role row on the DocType; `notice_has_permission` on the **parent**, correctly, not a child table |
| AC-57..AC-59 company, branch, filer, self | met | `employee_in_scope`, `refuse_own_decision`, filer read from the database `owner` |
| AC-60, AC-61 migrate, integrity, no new package | met / not re-run | guards read (§3); `check_app_integrity.py` is a CI gate and CI is green on this SHA — **I did not run it myself** |
| AC-62 log lines with ids only | met | three `security_logger().info` lines, all counts and ids |
| AC-63 rollback | partial | see P3-11 |

**Prototype parity.** The spec's §18 table is present and complete, which is what the
parity rule asks for, and Surbhi's 21 Nov answers close P-9, P-11, P-14, P-15 and OQ-1.
The build matches her answers, including the reversal most likely to be "fixed" back
later: the paper prints **"HR"** with no name for an HR filing and names a manager
(`sheet_rows:494-501`), and the browser test pins it. The footer's "Printed by {name}" is
the prototype's own `s_foot` string, so that is parity, not a leak of the OQ-1 decision.
Two small drifts: the "not right" row note drops the prototype's "The changes stay open"
clause (P4), and the dialog's multi-page sentence never appears because of P1-1.

## 5 · Non-functional: the seven dimensions

No `00-impact-analysis.md` exists, so the "claimed" column is empty. That is the finding,
not an omission in this table.

| Dimension | Claim | My finding |
|---|---|---|
| Performance | none on record | **Mixed.** The list is one query per concern and caps at 25 rows; `notices_are_on` is cached per company, not per person. Against that: the permitted-employee ids are read into Python and shipped back as `IN (...)` (P3-8), and `my_changes` does it with the whole table. No N+1 inside the row loop. `_aside_sentences` does one `get_value` per set-aside punch per change — bounded by 5 changes a page, acceptable |
| Security | none on record | **Improved.** Three readers and three writers all behind `_hr_or_refuse` + `employee_in_scope`; the covered days come from the record, never the caller; the process flag cannot be sent by a client; `_scope_sql` whitelists the two column names instead of escaping them as values and returns `1=0` on anything unexpected. No raw SQL built from input. No new `ignore_permissions` that is not argued |
| Reliability | none on record | **Improved.** One transaction per record; photos before marks before the notice; `notices_are_on` and `columns_ready` both fail closed; `_index` and `_month_of` swallow only what they should. Concurrency: a second HR user recording at the same instant is stopped by frappe's own modified-timestamp check rather than by a plain sentence (P4) |
| Scalability | none on record | **Neutral to slightly worse** — P3-8. 100-person print and 600-person list are capped; nothing unbounded is rendered |
| Maintainability | none on record | **Improved overall.** The comments explain *why*, including the faults found while building. Against it: a stale docstring (P4), a dead constant (P4), and four sentences duplicated between Python and JS |
| Data integrity | none on record | **Improved.** `content_hash` per change; print-owned fields immutable; delete refused for every role; `SERVER_OWNED` put-back extended to the new field; the snapshot is read, never recomputed |
| Compliance / privacy | none on record | **Improved, with one regression.** Photo is private and attached to the HR-only parent; every opening logged; no reason text on the record; no export, email or notification. The regression is P2-4 |

| NFR budget item | Measured or reasoned | Pass? |
|---|---|---|
| Whitelisted API p95 ≤ 500 ms | not measured by me; queries counted by reading | unproven |
| Skeleton within 300 ms | `rnDraw` paints a skeleton before the call — timing not measured | unproven |
| Scope stays in the database (budget line 65) | reasoned, from the code | **fail** — P3-8 |
| List page size | 25, server-enforced | pass |
| Photo stored ≤ 1 MB, ≤ 1,600 px | 081's caps, called not copied | pass |
| Upload ≈ 350 KB on 3G | reasoned | **fail** — P3-9 |
| No new queue, job, container, dependency | read `hooks.py`, no scheduler entry added | pass |
| Nothing cached | no cache headers set; nothing memoised across requests | pass |
| WCAG: 44 px targets, labelled tick boxes, focus-trapping dialog, word+icon status | CSS `min-height:44px`, `aria-label` per tick box, `role="dialog" aria-modal`, Escape closes | pass on inspection; **no screen-reader or 200% zoom check was done** — the spec already calls that a release step |

## 6 · Compliance verification

Spec §19 carries a real compliance sub-analysis, so this axis is reviewable.

| Obligation | Mechanism in the diff | Test that proves it | Verdict |
|---|---|---|---|
| Content leaves only through one logged call (SEC-2) | `open_notices` inserts the record before building any sheet; list payload carries no content | `test_printing_writes_one_notice_then_returns_the_sheet`, `test_the_response_carries_no_reason...` | discharged |
| One scope rule on every reader and writer (SEC-1) | `_hr_or_refuse` + `employee_in_scope` + `permission_query_conditions` + `has_permission` on the parent | branch and other-company tests, incl. `photo_log_query_conditions(outsider) == "1=0"` | discharged |
| Signature covers exactly what was printed (SEC-3) | `content_hash` per change; covered list from the record | `test_a_change_edited_since_the_print...`, `test_the_caller_cannot_choose...` | discharged |
| No one records a change they have an interest in (SEC-4) | filer read from the database `owner`; `refuse_own_decision` | `test_the_filer_is_refused_on_the_endpoint_and_another_hr_person_succeeds` | discharged |
| Fields written by the call only (SEC-5) | `SERVER_OWNED` put-back incl. `SIGNED_NOTICE`; controller refuses insert, delete and print-owned edits | `test_a_client_cannot_sign_its_own_change`, `test_what_was_printed_cannot_be_edited_afterwards` | **partial** — P3-12 |
| Photo checks reuse 081 (SEC-6) | `_photo_bytes` calls `_decode` and `_shrink_to_cap`; PDF refused | `test_a_pdf_and_rubbish_are_refused`, `test_the_stored_photo_is_private_named_by_us_and_carries_no_exif` | discharged |
| A reused photo is refused (SEC-7) | md5 against `File.content_hash` scoped to the notice doctype | `test_a_photo_cannot_be_used_twice` | discharged |
| Photo private by structure (SEC-8) | `is_private=1`, parent is the HR-only notice, no role row for employee or manager | `test_an_employee_and_a_manager_cannot_open_the_photo...` | **partial** — no HTTP 403 test for `/private/files/...`; the structure is right |
| Free text as text (SEC-9) | `gpEsc` at every insertion point | DOM test | discharged |
| Access log scoped (SEC-10) | new `permission_query_conditions` entry | SQL-shape assertions | **partial** — P2-4 hides unrelated audit rows |
| POST only + CSRF (SEC-11) | `methods=["POST"]` on all five calls | limit/annotation asserted; CSRF not tested | partial |
| Nothing new collected but the photo (PRIV-1) | notice stores ids, a hash and an outcome | `test_no_reason_no_hours_and_no_change_text_are_stored_on_the_notice` | discharged |
| What goes on paper (PRIV-2) | sheet built only from this person's qualifying changes | sheet tests | discharged |
| Nothing deletes; HR cannot delete (PRIV-4) | `on_trash` refuses for every role incl. Administrator; no erase job | `test_a_notice_is_never_deleted_by_anyone`, `test_no_role_can_export_or_delete...` | discharged |
| Employee app shows the same facts, own only (PRIV-5) | `my_changes` takes no employee id; no photo/file/url key | `test_the_response_carries_no_photo_no_file_and_no_address`, `test_the_employee_cannot_ask_for_anybody_else` | discharged |
| Audit answerable from the database a year later (§17) | `printed_by/at`, `changes`, `recorded_by/on`, `pages`, `track_changes=1`, photo access log | permission and record tests | discharged |
| C1 photo = biometric? C2 retention? C3 one photo per page? | **no mechanism; the questions are open** | none | **not discharged** — P2-7. Mitigated only by the switch shipping off |

No AI in this slice; `01c` and the spec both say so and I found none.

## 7 · What I ran, and what I did not

Ran, in this worktree, today:

- `node scripts/run_dom_tests.js` → **"DOM tests: 27 run, 0 not run, 0 failed"**, including
  the new `portal_register_notice_088_test.js`. My own evidence.
- The same suite with line 323's hand-patch removed (copy run from inside
  `alvoraa_portal/tests/`, then deleted; `git status` clean afterwards) → **2 failures**,
  quoted in P1-1.
- frappe's real `sanitize_html` over 24 strings, in container `alv436rel-bench` → the
  table in §3.
- `grep -c "	def test" tests/test_register_notice_088.py` → **80**. The figure I was
  handed is right.

Did **not** run: `bench run-tests` for either Python suite (so the **134** for
`test_punch_fix_087.py` is unverified by me), `scripts/check_app_integrity.py`, a migrate
rehearsal, any permission check against a real site, any production query. CI run
`45318596896` being green is evidence the gates pass on this SHA; it is not my evidence
of correctness, and it did not catch any of the five code findings above.

## 8 · If it ships

Before `main`:

1. Fix **P1-1** and **P1-2**. Both are a few lines.
2. Fix **P2-3** (one line) and **P2-5** (the test dates), and decide **P2-4**.
3. Write down the release conditions: the switch stays **off** everywhere (**P2-7**); the
   rollback caveat (**P3-11**); the Attendance Request reason behaviour change (§3).
4. Keep OPS-27's order and window: 087 first, then 088, in the 00:30-06:00 IST window,
   with her word each time; check the job queue is empty before the migrate (the 5 Nov
   trap).

## 9 · What to delete

- `MINE_STATES` (`register_notice.py:893-898`) — dead, and a second copy of four
  sentences that already live in `portal.js`.
- Line 323 of `portal_register_notice_088_test.js` — the invented `pages` key. It is not
  only useless, it is what hid P1-1.
- One of the three indexes on the notice table: `search_index` on `employee` and `month`
  plus the composite `employee_month` is one more than this table needs.
- `open_photo` is the one thing I looked hard at and would **keep**: it has no screen, one
  caller in tests and none in the product, which normally makes it dead weight — but
  Surbhi decided it (P-14), and the alternative is an HR person opening a signature with a
  file URL and no log. Keep it, and keep the decision recorded next to it.

Nothing else. The subtract pass on the slice itself was done honestly in the spec (§23)
and the build followed it: no PDF engine, no background job, no settings screen, no photo
viewer, no retention field, no feature flag beyond the one switch Surbhi asked for.

## 10 · What was done well

- **Splitting the paper round off ALV-430's confirm switch.** The two tenants the feature
  was built for run with confirmations off *because* their staff have no app. Reusing that
  switch would have shipped a feature that was invisible exactly where it was needed. The
  reasoning is written down in the module docstring, where the next person will find it.
- **`notices_are_on` deliberately failing the opposite way to `confirms_are_on`**, with
  the reason stated: before the migrate there is no table to print into. That is the kind
  of asymmetry a later reviewer would "tidy" and break.
- **A controller whose job is to say no.** No create, delete, export or report permission
  for anyone; delete refused in code even for Administrator; print-owned fields frozen;
  the write gate is a process flag a browser cannot send.
- **Attaching the photo to the notice and not to the request** — and saying in the
  docstring that the way to break it is to attach it to the request. That one choice is
  what makes SEC-8 structural rather than a rule.
- **Fixtures that assert they are valid.** `an_approved_hr_change` fails with "fixture is
  wrong: the change does not need a confirm" rather than passing quietly; `_rows_for_me`
  walks the pages rather than assuming page one; `_a_jpeg` randomises its bytes after the
  reuse check caught the fixture lying. These are the habits that stop hollow tests, and
  they are why most of the suite is worth its green.
- **ALV-436 fixed by calling the same function frappe is about to call**, rather than
  guessing at hook order, with a positive control in the test ("an ordinary reason is
  stored character for character") beside the refusal.
- **The leave-card fix is the right fix**: assert the gate's wording, not the bare string
  `"15"`. A narrower assertion that still means what R-88 meant.
- **ALV-435** closes a real hole — a cancelled CI run left commits unscanned until a
  release found them — and falls back safely to `before..after` when `merge-base` is
  unavailable.

## 11 · Confidence, and what I could not check

- **Proven by running:** P1-1, the `sanitize_html` behaviour, the DOM suite result, the
  80-test count.
- **Proven by reading the source this session:** P1-2's rule and `#pos-wall-print`'s
  parent, P2-3, P2-4, P2-5, every entry in §3's migration and switch analysis, the
  permission json, the put-back.
- **Inferred:** that P1-2 produces a literally blank page (CSS cascade, not rendered in a
  print preview); that P2-4 has no rows on production today (project memory, not
  measured).
- **Not checked:** the Python suites under me; `check_app_integrity.py`; a migrate
  rehearsal on a tenant copy; the CSRF path; the `/private/files/...` 403; any timing
  figure; any production data. To check the first three I would need a bench site on this
  branch; for the 403 I would need an HTTP test the repo does not have.
- **Unreviewable:** whether the impact analysis's dimension claims held, because the
  artifact does not exist; and C1/C2/C3, because counsel has not answered in writing.

**Must know before you decide** (each would change the verdict):

1. **P1-2 — is any tenant using the wall chart or Positions print?** My reading says they
   print blank after this release. If someone can confirm a tenant uses it, this is the
   first thing to fix; if nobody does, it is still a fix, but the window is wider.
2. **P2-7 — has counsel answered C1, C2 or C3 anywhere I have not seen?** If yes, point
   me at it and the release gate in §8 drops to a note. If no, my recommendation stands:
   ship dark, enable later. Ranked provisionally as a release condition, not a code
   blocker, because the switch is off.
3. **P2-4 — should a Photo Access Log row that names no employee be visible to an HR
   Manager?** If yes, the filter needs an exception; if no, this is a deliberate narrowing
   and needs one line in the record. Provisionally ranked P2 until someone decides.
