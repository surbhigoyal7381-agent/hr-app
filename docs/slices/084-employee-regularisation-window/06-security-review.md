---
slice: 084-employee-regularisation-window
artifact: 06-security-review
author: hrms-security-privacy-engineer
date: 2026-11-19
status: review complete
verdict: no Blocker. One requirement not met by decision (SEC-12), gated before the first non-blank value.
inputs: [01c-security-privacy-requirements.md (mine), 02-functional-spec.md, 03-implementation-notes.md, 04-test-report.md, worktree /Users/mac/hr-app/.claude/worktrees/084-employee-window @ c162374b]
---

# 084 Security and privacy review

## 0. Read this first

**No Blocker. The slice may go to dev on my account.** One requirement, **SEC-12, is not
met**, by a decision that was forced by a fact nobody knew when I wrote `01c`. It is
gated, not waived: see §4.

**Two corrections of my own earlier claims, in the order the rule asks for.**

1. **My `01c` SEC-12 said the smallest sufficient fix was one
   `frappe.logger("security").warning(...)` line, "the same mechanism `log_refusal`
   already uses". That recommendation was wrong.** The analogue itself writes nothing:
   `frappe.logger("security")` resolves to level **ERROR** on our images, so every
   `.warning` is discarded. Surbhi confirmed it on the live dev site —
   `security.log` is **0 bytes**. I reasoned from a call site to a log line without
   seeing the line, which is the exact failure my own brief forbids. ALV-391.
2. **My `01c` §2 said "the window writes no record of a refusal … that is the detection
   gap".** That understated it. The gap is not this slice's; it is the whole security
   log (§5, Finding 1).

**Where I am reviewing my own work — flagged, as asked.** I wrote `01c`. Three items
below are me checking my own specification, not somebody else's design:

| Item | What is mine | Who else looked |
|---|---|---|
| **SEC-3, the `validate` hook** | The mechanism was my recommendation and my fail-closed default | **Given to `hrms-technofunctional-reviewer` in parallel.** My verdict below is a second opinion on my own design and should not be the only one |
| **SEC-12** | The requirement and the fix that did not work | Engineer disproved it; Surbhi confirmed on dev |
| **PRIV-2 (no refusal log)** | My trade-off, still mine | Nobody. It is a design choice with a stated cost (§6) |

Everything else in the table is me checking code I did not specify the shape of.

**What I checked, and how.** Worktree
`/Users/mac/hr-app/.claude/worktrees/084-employee-window`, branch
`slice/084-employee-window`, six commits `b1d57b0a`..`c162374b` on `origin/dev`
`fd658eff` (`git log`, `git diff`, this session). I read the full Python and template
diff, the JS diff, the new test class (30 tests), the new scope test, `_subject`,
`_employee_for` and all eight of its non-test call sites, `access.is_own_record`,
`access.log_refusal`, `_working_days_away`, and `set_org_setting`. I ran greps, named
below where they carry a claim. **I ran no test and touched no site** — the test
evidence is the engineer's and the test engineer's, and I say so wherever I lean on it.

**Three facts I was told to take as settled** (Surbhi / test engineer, not re-derived by
me): the dead `.warning` sink; the guard binding four routes including
`frappe.client.insert`, proved by breaking it; and blank costing 0 statements.

---

## 1. Every SEC requirement: met / partial / not met

"Code" = I read the line this session. "Test" = a test exists in the diff; the run is
the test report's, not mine.

| # | Verdict | Mechanism in the diff | Proof |
|---|---|---|---|
| **SEC-1** Both portal paths bound by one derivation | **Met** | `employee_filing_from()` (`attendance_correction.py` ~1472) is the single derivation; the guard, `month()` and `get_requests_history` all call it | Code. Test `test_every_route_refuses_an_old_day_and_names_the_date_and_hr` runs routes a, b, c; `test_the_screens_and_the_refusal_name_the_same_day` pins the one date |
| **SEC-2** Rule server-side, no day count in a string | **Partial** | The browser only *compares* against server dates (`arWindowCheck`: `f.value >= w.from`). No `min` on the date inputs, deliberately, so the joining day is not greyed | My own grep over every added line in `portal.js`, the templates and `attendance_correction.py` for `[0-9]+ *(day|hour)` returned **nothing**. The only number in a string is `{0}` filled with the number HR themselves just typed. **Partial because** (a) that grep is not a committed test, and (b) the refusal words now exist **twice** — Python `refuse_own_day_outside_window` and JS `ownOldText` — so they can drift apart. See Finding 4 |
| **SEC-3** The third path is bound by structure | **Met** | `hooks.py:187` — `"validate": "alvoraa_portal.attendance_correction.refuse_own_day_outside_window"` on `Attendance Request` | Code. `test_the_hook_is_registered_on_validate` pins it on `validate` **and asserts it is not on `before_insert`**. Break-tested: moving it to `before_insert` failed 3 of 5 tests (the edit-path ones). Routes a, b, c in the committed suite; `frappe.client.insert`, `frappe.client.set_value` and `insert_many` by the test engineer's extra cases. **This is my own design — second opinion wanted** |
| **SEC-4** Joining date from the server, same employee row | **Met** | The hook reads `frappe.db.get_value("Employee", doc.employee, "date_of_joining")` and the boundary from `employee_filing_from(doc.employee)` — **the same row the document names**, read fresh on every save, no cache | Code. `test_whatever_the_caller_sends_the_joining_date_comes_from_the_employee`. See §3 for the three edges |
| **SEC-5** Blank joining date = no exception | **Met** | `own_day_state`: `if joined and from_date == getdate(joined)` — a falsy joining date never reaches a comparison | Code. `test_a_blank_joining_date_gives_no_exception_and_does_not_crash` also asserts no `joined_on` on the month payload |
| **SEC-6** Joining day allowed only alone | **Met** | `own_day_state` returns `joining` only when `to_date == from_date`, else `range`, which is refused whole with its own sentence | Code. `test_the_joining_day_is_allowed_on_its_own_and_only_that`, run on all three routes, with the fixture's joining date 10 days back against a 3-day window — the observability condition from `01c` §10 is actually met |
| **SEC-7** Binds nobody it was not meant to | **Met** | `if not is_own_record(doc.employee): return` — a manager's and HR's filing for other people never reaches the comparison. Two separate keys, two separate readers, neither reads the other | Code. `test_hr_is_bound_on_their_own_day_and_free_for_everybody_elses`, `test_the_two_windows_never_read_each_other`, both break-tested. **One consequence I did not foresee: see Finding 3** |
| **SEC-8** Who may change it, proven for the new key | **Met** | `_require_hr()` and `_refuse_store_hr()` run before any key logic in `set_org_setting`, so the new key is bound by construction | Code. New test in `test_org_setting_scope_030.py`: a store's HR person is refused with `PermissionError`, rule `030-D4`, **stored value unmoved**, and reading stays open. `test_a_plain_employee_cannot_save_or_read_the_setting` covers an ordinary login |
| **SEC-9** Blank reachable, bad values refused | **Met** | `hr_api.py:3412` — `if key in (MANAGER_FILING_WINDOW_KEY, EMPLOYEE_FILING_WINDOW_KEY) and value == ""`. This is the trap Surbhi singled out, and it is closed | Code. `test_hr_can_set_a_number_and_can_clear_it_again` saves 0 / 3 / 30, refuses `31`, `-1`, `"3 "`, `abc`, `999`, `1.5` with the stored value unmoved, then clears to `""` and raises an old day again on all three routes. `test_the_readers_keep_blank_and_zero_apart` keeps blank and 0 apart |
| **SEC-10** Leaver refused earlier | **Met** | Unchanged `status = "Active"` filters in `_employee_for` / `_get_employee` | Code. `test_a_leaver_is_refused_before_the_window_is_asked` asserts `PermissionError` and **zero rows created** |
| **SEC-11** No new `ignore_permissions`, no new endpoint | **Met** | — | **My own greps over the diff this session:** no added `@frappe.whitelist`, no added `allow_guest`, and the only two added `ignore_permissions=True` lines are in `tests/test_attendance_correction.py` (saving a holiday-list fixture). The AST ceiling test in `test_portal_security_010.py` passed. `submit_attendance_request`'s existing `ignore_permissions=True` was neither removed nor copied |
| **SEC-12** The setting change is attributable | **NOT MET, by decision** | Nothing was built. AC-45 to AC-47 are deliberately absent | See §4. The mechanism I specified does not work, and the engineer correctly refused to ship a test that would pass while production wrote nothing |
| **SEC-13** Fallback direction chosen on purpose | **Met** | `_working_days_away` unchanged: one counter, calendar-day fallback, `basis` says which | Code. `test_no_holiday_list_counts_calendar_days_and_says_so` |

## 2. Every PRIV requirement

| # | Verdict | Proof |
|---|---|---|
| **PRIV-1** No new personal data | **Met** | The diff is 9 files: 3 Python, 1 JS, 2 templates, 3 tests. **No `.json` DocType file, no Custom Field, no patch, no fixture.** See §7 for the full "nothing new is collected, stored, exported or logged" walk |
| **PRIV-2** No refusal log, no counter | **Met** | The hook ends in a bare `frappe.throw` and calls nothing else. `test_a_refusal_is_dates_and_fixed_words_and_is_not_logged` patches `access.log_refusal` and `frappe.log_error` and asserts **neither is called** on any of the three routes |
| **PRIV-3** `joined_on` only on the person's own payload | **Met** | **Two independent guards, both read in code.** (a) `month()` adds `own_window` and `joined_on` only inside `if is_self and filing_from:`. (b) When the subject is somebody else, `_subject` (line 406) builds them from a field list of `name, employee_name, company, default_shift, holiday_list` — **`date_of_joining` is not in it**, so there is nothing to leak even if the first guard were removed. Test covers an HR reader and a real direct manager whose own window is set. **A skip-level reader was not run as a test** (Finding 5) — structurally they take the same `_subject` branch |
| **PRIV-4** Sentences carry dates and nothing else | **Met** | I read the built strings — see §5. Test asserts the employee id, the employee name, the holiday-list name and the company are all absent from all three routes' messages |
| **PRIV-5** Every refusal names the way out | **Met** | `"HR can still fix it: tell HR which day it was and why."` on the window branch; `"Days after it that are older than {1} are HR's to fix: tell HR which days and why."` on the range branch. Asserted in `test_every_route_refuses_...`. **One exception that makes the sentence untrue for one reader: Finding 3** |
| **PRIV-6** Nothing personal in a log or an error | **Met** | No log call added anywhere in the diff (my grep). The one pre-existing `frappe.log_error` in `_working_days_away` still carries `employee=<id>` and nothing else, and the test asserts it is not called on a refusal |
| **PRIV-7** Nothing to retain | **Met** | The only stored thing is a site default holding a number 0-30 or blank. Not personal data, no purge, no legal hold. Stated, as agreed; no test needed |

---

## 3. The joining-day exception as a trust boundary, in the code as written

Asked directly, answered directly.

**Is the joining date taken from the employee's own record on every path? Yes — and
from the *same* row the document names.** The enforcement point is the hook:

- boundary: `employee_filing_from(doc.employee)` → that row's holiday list;
- exception day: `frappe.db.get_value("Employee", doc.employee, "date_of_joining")`.

Both read on every save, neither cached, neither taken from the payload. The
`Attendance Request` DocType has no joining-date field, so there is nothing on the
document to spoof; a caller who passes `date_of_joining` to `raise_correction` gets a
`TypeError` (tested). **An employee cannot move their own joining date** — it is
permlevel 2 (`employee_field_rights.py:55`) and `refuse_own_locked_change` refuses a
change to a high-permlevel field on one's own record, HR included.

**Blank.** `own_day_state` guards with `if joined and …`, so a null never reaches
`getdate`. The window then applies to every day with no exception, no `joined_on` is
sent, and no sentence about a joining day is shown. Tested. This is the opposite of
Frappe's own behaviour (`hr/utils.py:224` *skips* its floor check when the field is
empty), which is the right direction for a control that narrows a right: missing
configuration must not read as "every day is the joining day".

**Two Employee rows for one login.** The guard is self-consistent whichever row is
involved: the boundary, the exception and the document are all that one row. What can
differ is the **screen**: `month()` and `get_requests_history` pick a row with
`get_value("Employee", {"user_id": …, "status": "Active"})`, which returns one of the
two in an order nothing defines. So a person with two active records could be shown
row A's boundary and have a Desk-created request judged on row B's. **This is a display
mismatch, not a bypass** — the refusal names the live date, and nobody can borrow row
B's older joining date to open a day on row A, because the exception is only ever
compared against the row the request is for. I still **could not check** whether ERPNext
enforces one Employee per `user_id`; that was open in `01c` (Q8) and is still open. It
is a worry, not a finding.

**Rehire.** A rehire is normally a new Employee row with a new joining date, so the
exception follows the new row — correct. If a Desk request names the **old, Left** row,
note that `is_own_record` has **no status filter**, so the hook still binds it, using
the old row's joining date, and Frappe's own `validate_dates` caps at
`relieving_date`. Every direction there is fail-closed. **[INFERENCE]** — I read the
code paths, I did not run a rehire, and no test covers one.

---

## 4. SEC-12: not met, by decision — and what it means

**The decision is right and the engineer's reasoning is right.** Building my line as
specified would have shipped a control that passes its test (the test patches the
logger) and writes nothing in production. That is a false green, and a false green about
an audit record is worse than an admitted gap.

**What it means for this slice.** There is **no attributable record of who set the
number, when, or what it was before** — for the new key or for the five existing ones.
If a refused employee raises a grievance, the only answer to "who decided I could not
correct my own attendance, and when" is somebody's memory. That is what my `01c` §5
named under DPDP grievance redressal. **It is not a release blocker because the setting
ships blank on every tenant**, so on release day no employee anywhere loses anything and
there is nothing to be asked about.

**It becomes a blocker at the same moment counsel does: before the first tenant sets a
non-blank value.** One gate, two items (C1 and SEC-12), one owner.

**What it means for SEC-17, which is the larger finding.** `access.log_refusal`
(`hrms/hrms/alvoraa_hr_core/access.py:34`) writes at `.warning` to the same dead sink.
I counted the call sites this session:

```
alvoraa_portal/grooming.py:996                  .info
alvoraa_portal/attendance_analytics.py:91       .warning
alvoraa_portal/performance_api.py:3574, 5575    .info
hrms/alvoraa_org_structure/settings.py:601      .warning
hrms/alvoraa_org_structure/plans.py:349         .warning
hrms/alvoraa_hr_core/access.py:34               .warning   ← every refuse() in the product
```

**Seven call sites, and at level ERROR not one of them writes — the `.info` ones even
less than the `.warning` ones.** `access.log_refusal` is the hub behind every
`access.refuse()` in both apps. I also grepped `deploy/` and `.github/` for `log_level`
and `DEV_SERVER`: **no hit** (I did not read `deploy/server.env` and will not).

So the honest sentence is: **"every refusal is logged for misuse detection" is true in
code and false in fact.** Dev is proven (0 bytes, Surbhi). Production **could not be
checked** — the read was refused as unauthorised, and that refusal is correct.

**For any incident the company might have to reconstruct**, this is what is actually
left: Frappe's `Version` rows for document changes, `Activity Log` for logins,
`Error Log` for `frappe.log_error`, and the web server's access log. **None of them
records a refusal, and none records an org-setting change.** If DTC or Grace asked us
tomorrow "who tried to reach what and was turned away", the answer today is *we cannot
tell you*. That is a programme finding (ALV-391), ranked below, and it is not this
slice's to fix.

⚠ **COMPLIANCE.** Two things need a named human:
- **Which fix** — the engineer's (a) write at `.error`, (b) give the `security` logger
  its own level in one place, or (c) accept no record. **(b) is the only one that also
  revives SEC-17**, and it is one place. **Decider: Surbhi.** Retention of that log is
  then a new question and must be answered before it starts writing — a security log of
  refusals is personal data.
- **The grievance position** — whether an employer can defend a time limit on a
  correction route with no record of who set it. **I am not a lawyer. Decider:
  counsel, through Surbhi**, best asked together with C1 and only once the baseline is
  re-verified (§8).

---

## 5. Findings

Ranked, each as *this actor, in this state, calling this path, sees this*. Nothing here
blocks the slice.

### Finding 1 — Major, **P1 for the programme, not for 084**: the security log has, very likely, never written a line

**Actor:** anybody at Alvoraa, after an incident, opening `security.log` to find out who
was refused what. **State:** any site we run. **Path:** `access.refuse()` →
`log_refusal` → `frappe.logger("security").warning`. **Sees:** nothing. Dev's
`security.log` is 0 bytes (Surbhi, live dev site). Seven call sites, enumerated in §4.
Production not checked; the read was refused as unauthorised.

Note the second-order effect, because it is the subtle one: **our tests for these
controls patch `log_refusal` and assert it was called.** They prove the *call*, not the
*line*. Three such tests exist in this slice's neighbourhood alone, including the new
store-HR one. They are good tests of the refusal and no evidence at all about the log.

**Not a blocker for 084:** this slice adds no log, removes none, and ships blank.
**Owner: Surbhi, via ALV-391.** Fix (b) in §4 is one place.

### Finding 2 — Major, **P2**: no attributable record of a rights-limiting setting change

SEC-12, above. **Actor:** an employee refused an old day who asks HR why. **State:** a
tenant with a non-blank number. **Path:** a grievance. **Sees:** no record of who set the
number or when. **Gate: before the first tenant sets a non-blank value**, together with
the C1 counsel question. **Owner: Surbhi.**

### Finding 3 — Minor, **P3**: an HR Manager's own old day has no way out, and the refusal sentence tells them one exists

**Actor:** an HR Manager who is also an employee. **State:** the window is set; they need
their own day from two months ago corrected. **Path:** the portal day sheet, the
Attendance Request page, the Desk, or `/api/resource/Attendance Request` — **all four**.
**Sees:** `"HR can still fix it: tell HR which day it was and why."`

The guard binds by `is_own_record`, not by path. That is the right mechanism and it is
what I recommended. But Gate 3's C3 note reasons that *"an HR Manager who is blocked on
the portal fixes the day through the HR route, which is deliberately unbounded — one
extra click, not a block."* **As built, that is not true**: the HR route is the same
DocType and is bound too, for their own record. `test_hr_is_bound_on_their_own_day_...`
confirms it on routes a and c.

The way out exists but is a different person: another HR user, or a System Manager, can
create the request for them (not their own record → unbound). On a tenant with one HR
person, the only way out is to clear the setting, file, and set it back. For that
reader the PRIV-5 sentence is false.

I am **not** proposing a role exemption — that is the two-rules-that-must-agree problem
C3 correctly rejected, and the separation of duties here is a feature. I am saying the
rationale recorded at Gate 3 does not match the code, and **Surbhi should accept the
real behaviour knowingly.** Cheapest honest fix if she wants one: nothing in the guard,
one line in the release note.

### Finding 4 — Minor, **P3**: the refusal words now live in two places

`refuse_own_day_outside_window` (Python) and `ownOldText` (`portal.js`) build the same
three sentences independently. The *rule* is in one place — SEC-2 holds, the browser
computes no dates — but the *words* can drift, and `02a-strings-that-become-false.md`
exists in this slice precisely because twelve sentences had drifted from the code
before. The JS copy is what a person reads **before** they type; the Python copy is what
they read **after**. No test compares them. Low cost to live with, zero cost to note.

### Finding 5 — Minor, **P3**: PRIV-3 is proven for HR and a direct manager, not run for a skip-level reader

`01c` named the skip-level manager as the one new disclosure risk, because they can read
a month but cannot see a `date_of_joining` through the other endpoints. The committed
test covers an HR reader and a direct manager. A skip-level reader takes the identical
`_subject` branch — and that branch's field list has no `date_of_joining` — so I am
confident; but *confident by reading* is not what I asked for in `01c`. One more case in
the existing test, using the deep-reporting fixture the file already has.

### Finding 6 — Minor, **P4**: two wording points

- `basis` reads `"working days on this person's own holiday list"`, shown to the person
  themselves. It discloses nothing; it just reads oddly in the second person. Shared
  string with the manager path, so changing it is not free.
- `arWindowNote()` decides the "today only" wording by comparing the server's date with
  the **browser's** `localToday()`. A phone clock a day out shows the other sentence.
  The server still refuses correctly. Already the test report's P4 #5.

### Worries — not findings

Stated separately, as my own rules require, because I cannot write the actor-state-path
sentence for them.

1. **ALV-387's probe is unexplained.** A peer filing for someone else's old day was
   refused with `PermissionError` on a fresh site. **Nobody has named the line that
   refused.** See §6.
2. **Two active Employee rows for one login** — `01c` Q8 is still open.
3. **Rehire** — reasoned, not run.
4. **The hooks cache (OPS-21).** The engineer proved the list survives a process
   restart. A deploy with migrations off would leave the old list and **the guard would
   silently not run while everything looked green**. Mitigated, well, by
   `test_the_hook_is_registered_on_validate` — but only if somebody runs it after the
   deploy. That is a release-step dependency, not a control.

---

## 6. What would actually close ALV-387

Asked directly. **The probe does not close it, and not mainly because it is one probe.
It does not close it because nobody can say what refused.** A `PermissionError` of
unknown origin is the same evidential class as an empty grep: it proves something
happened, not that a control exists. Three things close it, in order, and all three are
needed:

1. **Name the refusing line.** Re-run the probe and read the traceback to the file and
   line — Frappe's `has_permission`, a User Permission, a permlevel, or one of our own
   hooks. Until that line is named, "an employee cannot file for a colleague" is a
   belief. If it turns out to be a fresh-site accident (no `Employee` User Permission
   rows exist on a fresh site at all, so nothing *restricts* — which makes the refusal
   more surprising, not less), the belief is wrong.
2. **A committed, break-tested regression test.** Employee A, employee B, no User
   Permission rows, A calls `frappe.client.insert` naming B; assert refused and assert
   no row. Then remove the guard found in step 1, watch *that* test fail, restore.
   A test that has never failed for the right reason is not evidence.
3. **Read the two tables that actually decide, per tenant, on dev copies — never by
   probing production.** `Custom DocPerm` for `Attendance Request` (the shipped JSON is
   not what a migrated tenant runs — memory `bench-stale-app-sync`), and the
   `User Permission` rows. The DTC trap is specific and it points the dangerous way:
   DTC's Employee User Permissions are **narrow, per-DocType on purpose** (memory
   `dtc-user-permission-pattern`), so a permission that does not list
   `Attendance Request` **does not restrict it**. DTC, Grace and PPJ each need their own
   answer; one answer is not three.

Plus, separately: `submit_attendance_request`'s `ignore_permissions=True` either goes or
gets a written justification. This slice correctly left it alone.

**Until all three are done, the honest sentence in any questionnaire is: "an employee
filing an attendance correction in a colleague's name is refused on a default install;
we have not verified it on a configured tenant."**

---

## 7. PRIV: nothing new is collected, stored, exported or logged — checked against the code

| Question | Answer | How I checked it |
|---|---|---|
| New field or DocType? | **No** | `git diff --stat fd658eff..c162374b`: 9 files, none a `.json` DocType, no Custom Field call, no patch, no fixture |
| New stored data? | **One site default**, `alvoraa_employee_filing_window_days`, holding `""` or `0`-`30`. Not personal data, not per person, not per company | `frappe.db.set_default` in `set_org_setting`, unchanged mechanism |
| New personal data leaving the server? | **No new data; one existing field to one new place.** `Employee.date_of_joining` now reaches the browser as `joined_on` — **only the person's own, only when it is older than their boundary** | `month()`: inside `if is_self and filing_from:`. `get_requests_history`: `emp = _get_employee()`, which keys on `frappe.session.user` |
| Did adding `date_of_joining` to `_employee_for` widen anything else? | **No** | I enumerated **all eight** non-test call sites of `_employee_for`. Every one passes `frappe.session.user` (the one that takes a `user` argument, line 1256, uses only `me.name`). **No caller returns the dict to a client.** `month()` builds its payload key by key |
| New export? | **No** | No report, no CSV, no print format, no new whitelisted method in the diff |
| New log line? | **No** | My grep of added lines for `logger(`, `log_refusal`, `log_error`, `print(`: the only hits are in tests, patching them to assert they are **not** called |
| New cache holding personal data? | **No** | `get_portal_context` (cached per user in Redis) is untouched, and `test_the_boundary_is_not_in_the_portal_context` pins that |
| New public route or guest access? | **No** | No added `@frappe.whitelist`, no added `allow_guest` |
| Anything reaching a model prompt? | **No** | No model is involved anywhere in this slice |
| Retention | **Nothing to retain.** No refusal record exists, by design (PRIV-2) | — |

**One thing I want on the record as a positive**, since my own brief tells me to check
the opposite failure too: the slice **did not** build the thing it could easily have
built. No refusal counter, no exposure metric, no "wasted submissions" baseline, no new
DocType, no cache, no new endpoint. The PM's measure lost its in-product baseline and
that was the right trade. Unneeded surface is a security finding; there is none here.

---

## 8. Can the refusal text disclose anything about another person? No — now read from the built strings, not the design

`01c` answered this from the design. Here are the strings as built
(`attendance_correction.py`, `refuse_own_day_outside_window`):

- *"This day is older than your organisation lets you raise yourself."*
- *"The oldest day you can raise yourself is {boundary}, counted in {basis}."*
- *"HR can still fix it: tell HR which day it was and why."*
- *"The one exception is your joining day, {joined}."*
- range branch: *"Your joining day, {joined}, can be asked about on its own: set To to
  the same day. Days after it that are older than {boundary} are HR's to fix: tell HR
  which days and why."*

Three variables, nothing else: two dates and `basis`, which is one of exactly two fixed
phrases. **And the subject is always the reader** — the hook returns early unless
`is_own_record(doc.employee)`, so the message is only ever built for a person about
their own record. There is no code path that renders this text about somebody else.
No name, no employee id, no company, no holiday-list name, no attendance status, no
reason for absence. The test asserts the first four by value, on all three routes.

**One residual, small and named.** The browser's refusal boxes
(`ar-refusal`, `ac-refusal`) echo **whatever the server refused with**, via
`refusalWords(e)` — not only this slice's sentence. So a Frappe HR message, such as the
overlapping-request error, lands in the box too. Those messages are about the caller's
own request. Both boxes use `textContent`, not `innerHTML`, so there is no injection
surface either. Acceptable.

---

## 9. The DPDP baseline goes stale on 22 November. Does it change anything here?

**Plainly: no, not for this release. Yes, before the first tenant sets a number.**

- The slice ships **blank on every tenant**. Nothing is narrowed on release day, so
  there is no processing for an expiring page to be wrong about.
- The obligation I leaned on — the Data Principal's right to correction, and grievance
  redressal — is in the DPDP Act itself, not in a phase date. What moves in that
  baseline section is the **timing** (the ⚠ already on it: phase dates and our
  Fiduciary-vs-Processor position, both unconfirmed). Nothing in this slice turns on
  timing.
- The safeguard that carries the compliance argument is in the code and tested: **HR's
  route stays open and every refusal names it** (PRIV-5, with Finding 3's one exception
  noted).

**What it does change.** Gate 3 decoupled the counsel question (C1) to "before the first
non-blank value" and noted that an opinion sought today would rest on an expiring
document. That is now three days from expiring. So: **re-verify
`.claude/context/security-compliance-baseline.md` §2 against a primary source before C1
is put to counsel**, and put SEC-12 in the same envelope. Putting a stale baseline in
front of counsel wastes the one thing a counsel question buys you — a week.

**Owner: me (`hrms-security-privacy-engineer`). Trigger: the first non-blank value, or
the next slice touching a data-principal right, whichever comes first.** I did **not**
re-verify it in this run, because this slice needed no new legal fact.

---

## 10. Residual risk — what needs a named human, and who

An accepted risk with a name and a date is governance. These are the ones that need a
name. The first four are not mine to accept.

| # | Risk | Level | Who must accept it | By when | State |
|---|---|---|---|---|---|
| 1 | **No record of who set a rights-limiting number** (SEC-12), and the wider fact that the security log writes nothing (SEC-17, ALV-391) | P2 for 084; **P1 for the programme** | **Surbhi**, choosing fix (a)/(b)/(c). ⚠ COMPLIANCE: **counsel** if she wants the grievance position confirmed | **Before the first tenant sets a non-blank value** | Open, 19 Nov 2026 |
| 2 | **C1: is a time limit on a correction route acceptable**, with no rights console in the product (feature map A8)? | ⚠ COMPLIANCE | **Counsel, through Surbhi** | Before the first non-blank value; **after** the baseline is re-verified | Open, decoupled at Gate 3 |
| 3 | **An HR Manager cannot raise their own old day on any route**, and the refusal tells them HR can (Finding 3) | P3 | **Surbhi** — the Gate 3 C3 rationale does not match the code | Before the first non-blank value | Open, 19 Nov 2026 |
| 4 | **Per-tenant `Custom DocPerm` and `User Permission` on `Attendance Request` not checked** (ALV-387, §6) | P3 | **Surbhi** to assign; `hrms-fullstack-engineer` on dev copies | Before the first non-blank value at DTC, where the permission pattern is narrow by design | Open, 19 Nov 2026 |
| 5 | **The baseline's DPDP section goes stale 22 Nov 2026** and I relied on it again | P3 | **Me** (`hrms-security-privacy-engineer`) | Before C1 goes to counsel | Open, 19 Nov 2026 |
| 6 | **A deploy with migrations off would leave the guard not running**, green all the way (OPS-21) | P3 | `hrms-devops-engineer` / Surbhi | Every release; run the hook pin test after the deploy | Open, 19 Nov 2026 |
| 7 | **No record of who was refused** — deliberate (PRIV-2). We can evidence "the control fired" only by test | P3 | **This document.** Intentional trade-off; I still own it | — | Accepted, 19 Nov 2026 |
| 8 | **Calendar-day fallback narrows the window** for an employee with no holiday list (SEC-13) | P4 | **This document** | — | Accepted, 19 Nov 2026 |
| 9 | **Hindi strings not translated**; a refusal in English to a Hindi reader is a refusal they may not act on | P3 | **Surbhi** | Before a Hindi-reading tenant sets a number | Open, carried from `03` §6 |

**Debt labels.** (1) is **dangerous debt — escalate now** for the programme, and
**temporary debt** for this slice, removed by fix (b). (3) and (4) are **temporary
debt**. (7) and (8) are **intentional trade-offs**, mine, dated. (9) is **dangerous debt
at DTC specifically** and harmless until the number is set.

**What must exist before "0 findings" means anything here** — the `01c` §10 conditions,
re-checked against the fixtures: the setting non-blank (`self.window(3)` in every case),
the joining date older than the boundary (`self.joined(self.back(10))`), no overlapping
request (`frappe.db.delete(REQUEST, …)` between cases, with a comment saying why), and
every test made to fail once by breaking the code (the engineer's §7 table, including
**two tests that passed at first and were rewritten** — which is the part that tells me
the break-tests were real).

---

## 11. Subtract pass

**Removed from this review before sending:** a fourth and fifth Minor about comment
wording and about the `own_day_state` return values; a proposed new CI check comparing
the Python and JS refusal strings (Finding 4 names the drift; a new gate for two
sentences is exactly the over-engineering my brief forbids — the existing `02a` file is
the mechanism); a re-statement of the data inventory from `01c`, which has not changed;
and a DPIA recommendation, for the same reason I removed it from `01c` — no new
processing, no new data, blast radius one person's own day.

**Not removed:** Finding 1. It is not this slice's fault and it is the most important
sentence in this document.

---

## 12. Verdict

**No Blocker.** Twelve of thirteen SEC requirements met, one partial (SEC-2, on test
automation and word duplication, not on the control), **one not met by a decision I
agree with** (SEC-12). All seven PRIV requirements met. No cross-tenant surface, no new
collection, no new export, no new log, no widened visibility, no new public route, and
no new `ignore_permissions`.

**The slice closes a real hole** — an employee's own old day was unbound on three ways
in, and is now bound on four by one `validate` hook, break-tested in both directions.

**The one sentence I would put in front of Surbhi:** the product's security log has
probably never written a line, so "every refusal is logged" is false today; that is
ALV-391, not 084, and 084 should not wait for it — but **the first tenant to set a
non-blank number should**, together with the counsel question and a re-verified DPDP
baseline. One gate, three items, one date.

**SEC-3 is my own design. A second opinion from `hrms-technofunctional-reviewer` is
wanted before this is treated as independently reviewed.**
