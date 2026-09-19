---
slice: 012-leadership-view
artifact: 05-review
scope: push 1 only (US-1 to US-10)
author: hrms-technofunctional-reviewer
date: 2026-09-16
reviewed: local dev 5aad1ae plus worktree commit c78efcd (DEF-8), branch slice/012-leadership-view
status: recommendation — the decision to push is yours
inputs: [00-impact-analysis.md, 01-product-brief.md, 01b-ux-design.md + prototype-v2/index.html, 01c-security-privacy-requirements.md, 02-functional-spec.md (incl. §14 and User decisions 2026-09-15), 03-implementation-notes.md, 04-test-report.md (both runs), 07-devops-inputs.md §1-§4, change-process.md, nfr-budget.md, security-compliance-baseline.md, definition-of-ready-done.md]
---

# 012 push 1 · Senior architect review

## 1 · Verdict

# SHIP WITH FIXES

The code does what the spec asked, the three live leaks (G1, G2, G3) are really closed, and
the speed problem found in testing is really fixed. **I found no blocker.** I found one
Major that is a small code change, and a short list of things a human must still check by
eye before this goes anywhere near `main`.

**`SHIP WITH FIXES` means: ready to present to you for a dev push once the Major below is
done. It is not permission to deploy, and it is not permission for `main`.**

**The one number to remember:** at 1,000 people every warm call is now inside the 500 ms
budget (worst 283 ms, measured by the test engineer). Before the fixes it was 895 ms.

**What I actually ran** (read-only, no bench change, no migrate, no push):

| Command | Result |
|---|---|
| `ruff check` on `org_figures.py`, `data_review.py`, `attendance_analytics.py` and both new doctype controllers | **All checks passed** |
| `python -m py_compile` on the four changed Python files | **compile OK** |
| `docker exec hrlocal-bench` — read Frappe's `base_document.py` | Confirmed `flags` is in `RESERVED_KEYWORDS`, so a REST payload cannot set `via_rule_check` (see §5) |
| `git log` / `git diff` on the worktree | Worktree is clean; exactly one commit (`c78efcd`, DEF-8) sits on top of `5aad1ae`, as you said |

**I did not run the test suite.** It needs the bench and would write to `test_site`. I read
the tests instead and report on their quality in §7. The test report's numbers are the test
engineer's, not mine.

---

## 2 · Against the impact analysis — did the code match the claim?

This is the first thing I check, and it is the one that usually catches people out. Here it
holds up well.

| Dimension | `00` claimed | What the code does | Agree? |
|---|---|---|---|
| Performance | Improves | Fixed query count per endpoint; nine indexes; `detail=False` on the two screens that show none of the detail; one indexed read per company for "data up to". Measured 283 ms p95 at 1,000 | **Yes** |
| Security | Improves, no new `ignore_permissions` | Zero `ignore_permissions` in all five new/changed files, pinned at 0 in `test_portal_security_010.CEILINGS`. `hr_api.py`'s ceiling was **lowered** 77 → 75 | **Yes** |
| Reliability | Improves, one new moving part | Commit per company, rollback per company, stamp only on a clean run, error-type-only logging, page re-check failure does not break the page | **Yes** |
| Scalability | Improves | Query count grows with companies (1–2 on a tenant), not people or branches. Proved by a real test at 10/100 people and 2/8 branches | **Yes, with one caveat** — see m5 |
| Maintainability | Neutral | +2 modules, +2 doctypes, +1 job, ~19.5 KB of page code. `org_figures.py` is genuinely readable | **Yes** |
| Data integrity | Improves | Record name *is* the finding key, so the job cannot double-write; `for_update` row lock on confirm; a Confirmed record is immutable on every path | **Yes** |
| Compliance / privacy | Improves | Store HR and single-company HR stop seeing other people's names, gender and joining dates. New records hold counts only | **Yes** |

Two things the analysis promised and the code did **not** build, both correctly dropped:
`group_by` on `org_figures` (no caller in push 1) and the `ldr:` cache invalidation (no cache
in push 1). Both are the right call — no abstraction before its first use.

Three things changed after the analysis and are all improvements: the ninth index
(`Attendance`, company + date), the `detail` flag, and `=` instead of `in (one value)`.
Each is explained in `03` with the measurement that justified it. That is exactly how this
should read.

---

## 3 · Findings, worst first

### Blockers

**None.**

I looked hard for the ones that matter in this product: a personal-data leak into a log, a
notification or a response; a whitelisted endpoint with no document-level check; a
half-written document; an `ignore_permissions` nobody justified; a guardrail that is only a
sentence. I did not find any. §5 sets out what I checked.

---

### Major

**M1 · `data_review_items` writes to the database on every call and has no rate limit.**

*File:* `alvoraa_portal/alvoraa_portal/data_review.py:551` (`data_review_items`), and the
limiter it does not use at `:501` (`_within_hourly_limit`).

*Failure scenario:* an HR user's session (or a left-open tab with a refresh, or a script
using their cookie) calls `data_review_items` in a loop. Each call runs `recheck(scope)`,
which for central HR is roughly five queries **per company in scope** plus `leave_figures`,
and then `apply_findings` — which **saves documents** and writes Version rows whenever a
count has moved. `data_review_confirm` is capped at 30 an hour per user; this one is capped
at nothing. At 1,000 people one call is 243 ms of server work; a thousand calls is four
minutes of one worker, and it is a *write* path, not a read path.

*Why it is wrong:* OPS-40 asked for a per-user limit on this screen's work. The helper
already exists, is already tested (`test_thirty_confirmations_an_hour_per_user`) and is
already designed to be reused ("Push 2 reuses it for leader reads"). The read half of the
screen was simply left off it.

*Smallest fix:* one line in `data_review_items`, after `_require_hr(...)`:

```python
_within_hourly_limit("data_review.data_review_items", READS_PER_HOUR)
```

with `READS_PER_HOUR` set generously (120 an hour is two page opens a minute and will never
trouble a real person). Add one test: the 121st call in an hour is refused.

---

### Minors

**m1 · A company that never records attendance gets no data review at all, for ever.**

*File:* `data_review.py:266` in `company_findings`.

```python
if not frappe.db.sql("select 1 from `tabAttendance` where company = %s and docstatus = 1 limit 1", company):
    return out
```

*Scenario:* a customer uses Alvoraa for leave and people records but takes attendance on a
different system — a real pattern for office-only companies. That company's D6 ("leave looks
unrecorded") and D18 ("leavers with no leaving date") checks never run, so a genuine leaver
gap is never surfaced. Deviation #5 in `03` justifies this as AC-30 ("a new tenant says no
figures yet"), which is right for a *new* tenant, but the guard is permanent, not a
first-run guard.

*Fix, if you want it:* gate only the D5 doubtful-day rule on "has attendance", and let D6 and
D18 run regardless. Or accept and record it — it is a small population. Either way it should
be a decision, not a side effect.

**m2 · The list and the badge silently stop counting above 1,000 open items.**

*File:* `data_review.py:40` (`MAX_ITEMS = 1000`), used at `:72`, `:85` and `:578`.

*Scenario:* the comment says a scope can hold at most "25 branches × 35 days". A tenant with
30 or more branches in one HR person's scope, hit by a multi-day device outage, produces more
than 1,000 open records. `open_count` is `len(rows)`, so HR Analytics says "1,000 figures
need review" when it is 1,200, and the cards for the rest never appear. There is no "and more"
line.

*Fix:* read the count with `frappe.db.count` (the permission-checked filters already exist in
`item_filters`) instead of `len(rows)`, and show "showing the first 1,000" when the list is
truncated.

**m3 · A morning run that fails for one company is invisible to HR for up to 26 hours.**

*File:* `data_review.py:229` — the stamp is written only when every company succeeded.

*Scenario:* company B throws at 06:30 today. `last_checks_run_on` stays at yesterday 06:32.
HR's page shows "stale" only once that stamp is more than 26 hours old — about 08:32
*tomorrow*. For a day and a half HR sees a list that is out of date with no sign. The Error
Log row is there and `health.collect_scheduled` carries the count up, so the operator knows;
the HR user does not.

*Fix:* small — write the stamp whenever the run finishes and carry a separate "last run had a
failure" flag, or judge staleness against the expected 06:30 rather than the last stamp.

**m4 · The per-user rate limit fails open.**

*File:* `data_review.py:501-516`. If Redis is unreachable, `except Exception: return` — the
limit simply does not apply. The comment says this is deliberate ("Cache trouble never blocks
HR"), and for a *confirm* action with a row lock and an audit trail I think that is the right
trade. But OPS-40 is written as a control, and a control that quietly disables itself should
be recorded as fail-open, not read as enforced. One line in `03` and in the security review
closes it.

**m5 · Query count grows with the number of companies, and System Manager gets every company.**

*Files:* `org_figures.py:248` (`data_up_to`, one query per company), `org_figures.py:291`
(`leave_figures`, one leave-year lookup per company), `data_review.py:215` (the job loops
companies). `access.permitted_companies` returns **every** company for a System Manager.

*Scenario:* the test engineer already saw this — on `test_site` with 20+ companies a System
Manager's `data_up_to` fires 20+ small queries per call. On a real tenant this is 1–2 and
harmless. But nothing in the code caps it, and `hr_scope` gives a System Manager the whole
list. It is a watch item, not a defect today. R5 in the test report already says so; I agree
with their reading.

**m6 · HR Analytics and Attendance Insights still use two different scope rules.**

`get_hr_analytics` scopes by `permitted_companies` (which can be several companies).
`attendance_analytics.person` and `_population` scope by `me.company` — the caller's own
Employee record's company. So an HR Manager with Company permissions for A and B, whose own
Employee sits in A, sees both companies' figures in HR Analytics but cannot open a person in
company B in Attendance Insights. That is decision D-6, recorded and accepted, and it fails
*closed*, so it is not a leak. It will confuse someone, and it is the kind of difference that
gets "fixed" wrongly in six months. Worth one line in the code beside `_in_organisation`
saying it is deliberate.

**m7 · An HR administrator with no Employee record can see the organisation list but cannot
open anyone in it.** `attendance_analytics.person` throws "Your user is not linked to an
employee record" for any caller with no Employee, while `_population` explicitly allows the
organisation view without one ("An HR administrator is often not on the payroll"). So they
get a list of names and every click fails. **This is pre-existing, not caused by 012** — I
checked the diff of commit `bdc50c0`. Noting it so it is not discovered later and blamed on
this slice.

**m8 · The audit record for a "figure is right" confirmation has no "before".**

*File:* `data_review.py:704`. For a D6 (leave) confirmation, `figure_without` is set to `None`
and `figure_with` to the current percentage. For a D18-2 (leavers) confirmation both are
`None`. The doctype was built to hold before and after, and §14.4 of the spec names the
confirming HR user as the accountable human. Nothing *changes* on these two, so "before" is
arguably meaningless — but in a grievance, "HR confirmed that leave used really is 0.06% on
16 Sep" is a far better record than "HR confirmed something". Put the current figure in
`figure_without` as well, or record the counts.

**m9 · Four screen strings in the build are draft copy the UX designer has not confirmed.**

`03` known gap 7 lists them: the "not linked" message (BA-Q5), the empty state and the
success toast (BA-Q12), the D18-2 confirm dialog, and the "no branch" leavers line. The
design gate you gave was on prototype-v2; these sentences were not in it. They read well and I
would not hold the slice for them, but they are a difference from what you approved, so they
are a finding, not a detail.

**m10 · Small differences from prototype-v2.** I read both. The build matches the prototype
closely. The differences I found:

| Prototype v2 | Built | My view |
|---|---|---|
| Footer also says "Store HR sees only items for their own branch." | Omitted | Put it back — one sentence, and it explains the whole scoping rule to the person reading |
| Leave confirm sheet shows the numbers: "0.2% (3 requests, 15 days of 6,912)" | Shows the percentage only | Put the numbers back. That is the information HR needs to decide |
| "attendance for September will drop" | "attendance for this month will drop" | Fine — the built version is safer when the month is ambiguous |
| "fewer than 2% checked in" | "no more than 2% checked in" | Fine |
| — | Focus is not returned to a control after a successful confirm | Small accessibility gap; the card is redrawn, so focus falls to the page |

---

### Nits (one list, take or leave)

- `hr_api.py` `int(present)` truncates the half-day halves, so "Days Present" can read one
  lower than the arithmetic. Round instead.
- `people_figures` counts joiners to the **end of the month**, so someone starting on the 28th
  is a "new joiner" on the 1st, while `active` counts only people who have joined by today.
  Pre-existing behaviour, carried over unchanged.
- `drAnalyticsNotes` un-hides every `:scope > .card` in the analytics panel when the user *is*
  linked. Harmless today; it would fight any future card hidden for another reason.
- `min_group_size()` writes an Error Log row every time it reads a broken stored value. Once a
  day, so tiny — but on a broken tenant it is a daily row for ever.
- `drT()` falls through to English because the page has no `window.__`. Every `__()` in the new
  block is decorative until push 2 wires it up. `03` says so; it is honest, just worth knowing.

---

## 4 · Acceptance criteria — met, partial, not met

I walked the push-1 ACs against the code myself and cross-checked the test engineer's table.
Where I say "met" I found the mechanism in the code **and** a test that would fail without it.

| AC | Verdict | Evidence |
|---|---|---|
| AC-1 all indexes created | **Met** | `data_review.SINGLE_COLUMN_INDEXES` + `TWO_COLUMN_INDEXES` = 9; `test_leader_indexes_012.test_install_creates_every_index`. Verified on `test_site`, **not on a fresh `install-app` site** |
| AC-2 second migrate changes nothing | **Met** | `add_indexes` checks for the Property Setter before writing; `test_running_again_adds_and_changes_nothing` |
| AC-3 speed and no full scans | **Met at 1,000, partial above** | R4: every warm p95 inside 500 ms, `EXPLAIN` shows no full scan of Attendance or Employee Checkin. **2,000 people not run** |
| AC-4 fixed query count | **Met** | Four separate query-count tests at 10/100 people and 2/8 branches. `data_review_confirm` has no such test (bounded at 40 items) |
| AC-5 index migrate time | **Not met** | Never measured. See §9 |
| AC-6 to AC-10 the calculation | **Met** | `org_figures.rate()` implements the stated formula exactly; six tests in `test_org_figures_012` |
| AC-11 appraisal scores do not move | **Met** | `attendance_score.py` untouched (confirmed by diff); `TestAppraisalScoresDoNotMove`; plus an import check that nothing which rates people imports `org_figures` |
| AC-12 to AC-16 doubtful days | **Met** | `_doubtful_days` thresholds match; minimum-group rule enforced in SQL (`having expected >= %(minimum)s`); the anti-join leaves out that branch and that day only |
| AC-17 warning line | **Met (copy traced, not seen)** | `drAnalyticsNotes` builds both lines; page pin test |
| AC-18 re-run changes nothing | **Met** | `apply_findings` writes only differences; DEF-2 (days older than 35) fixed and independently re-probed |
| AC-19 to AC-25 confirmations | **Met** | `for_update` lock, all-or-nothing loop, immutable-after-confirm controller, one Version row per item. Weak spot: the before/after figure on non-attendance confirmations (m8); no real two-connection race test |
| AC-26 to AC-30 "Needs review" rules | **Met** | D6 / D18-1 / D18-2 each with their own test; the leave-year key proves the yearly re-ask |
| AC-31 badge on page load | **Met** | `_with_review_count` sits **outside** the one-hour context cache and wraps **both** return paths (`hr_api.py` lines 104 and 152). I checked that myself — this was DEF-3 and it is properly fixed |
| AC-32 store HR sees only own items | **Met against the approved strategy; the AC text is wrong** | The code hides company-wide items from store HR entirely (fail closed). The AC says they see them without a confirm button. DEF-4. **The BA should correct AC-32; do not change the code** |
| AC-33 to AC-36 page behaviour | **Met** | Stale line, empty state, no names or employee ids in the response (asserted by test) |
| AC-37 to AC-39, AC-161 morning job | **Met** | Cron queues onto `long` with `deduplicate`; commit per company; failure logged with type only |
| AC-40 release plan | **Not this artifact** | `07` §5 |
| AC-41 to AC-45 HR Analytics scoped (G1) | **Met** | Every count goes through `employee_condition` / `org_figures`; the two name lists use `frappe.get_list`; zero `ignore_permissions`, pinned |
| AC-46 to AC-50 `person()` / `filter_options()` (G3) | **Met** | `_in_organisation` + `_linked_branches`; 12-month cap; refusals logged as SEC-17 |
| AC-51 to AC-54 allow-list (G2) and org-roles guard | **Met** | `ALLOWED_ORG_SETTINGS` checks key **and** value; `NEVER_ORG_ROLES` strips Leadership, Employee, Employee Self Service, All, Guest, Desk User. A test reads the page source and fails if a new key is ever written from it — that is the right kind of test |

**User decisions D-1 to D-15, Q1 to Q12, BA-Q1 / Q5 / Q11:** all the push-1 ones are
implemented as decided. Two are worth naming:

- **Q11 (Hindi at launch)** is push 2; nothing in push 1 breaks it.
- **BA-Q14 (who tells each tenant's HR the numbers are changing) is still open.** That is the
  single biggest real-world risk in this slice and it is not a code problem. See §9.

**The eleven deviations in `03` §4:** I read every one. Ten are right and well argued.
Deviation 6 (AC-32) is right *as code* but leaves the spec saying the opposite — that must be
closed in the spec, not left as a difference between two documents.

---

## 5 · Guardrails — verified, not assumed

| Guard | Is it structural? | How I checked |
|---|---|---|
| Nobody edits a review record by hand | **Yes** | The controller refuses unless `flags.via_rule_check` or `flags.via_confirm` is set. I read Frappe's `base_document.py` in the container: `RESERVED_KEYWORDS` contains `"flags"`, and `update()` skips reserved keys — so a REST or `set_value` payload **cannot** inject the flag. A real structural guard, not a sentence |
| One finding, one record | **Yes** | `autoname` sets the name to a hash of (rule, company, branch, date). A second insert hits the primary key. A unique index would not have worked, because MariaDB lets NULLs repeat — the comment says exactly that, and it is correct |
| Confirmed is immutable | **Yes** | `_check_rule_update` refuses if `before.status == "Confirmed"`; `_check_confirmation` refuses unless `before.status == "Open"` and forces `confirmed_by == frappe.session.user`. Tested on desk save, `frappe.client.set_value` and `frappe.client.save` |
| Every whitelisted endpoint checks the caller | **Yes** | `data_review_items` / `data_review_confirm`: `@frappe.whitelist(methods=["POST"])` (so no GET, and Guest is refused by the framework), `@requires_feature("analytics")`, then `_require_hr`, then `hr_scope`, then per-document checks. `get_hr_analytics`: plan + role + scope. `get_org_setting` / `set_org_setting`: `_require_hr` + key allow-list + value allow-list |
| Authorisation is on the **document**, not the button | **Yes** | `data_review_confirm` checks, per item: company in scope, branch in scope, `frappe.has_permission(doc, "write")`, item type matches the action, status is Open. Any failure refuses the **whole** request. The refusal message is identical for "missing", "someone else's" and "wrong kind", so it does not reveal what exists outside the caller's scope. A deliberate, correct choice |
| No new `ignore_permissions` | **Yes** | Zero in all five new/changed files, pinned at **0** in `CEILINGS`, and `hr_api.py`'s ceiling was lowered from 77 to 75. The job can insert without it because it runs as Administrator in a background worker |
| No string-built SQL | **Yes** | Every scope value is a bound parameter. The only things interpolated into SQL are module constants (`alias`, `branch_field`, `ABSENT_PCT`). A branch name containing a quote has its own test |
| No personal data in logs | **Yes** | `log_if_slow`: endpoint, scope kind, branch count, duration — and it filters `extra` to numbers only. `_log_failure`: company, stage, `type(error).__name__`, explicitly **not** `get_traceback()`. `log_refusal`: user, endpoint, doctype, document name. The only identifier that reaches a log is an employee id in a `person()` refusal, which SEC-14 permits |
| Tenant isolation | **Yes** | Both new doctypes are in `subscription.TENANT_DOCTYPES`, which was DEF-1 and is fixed; `test_every_billing_doctype_is_named_as_control_plane_only` passes |
| Branch never trusted alone | **Yes** | `org_figures.condition()` always adds the company condition with the branch, because an ERPNext Branch has no company and two companies can share one. There is a test for a same-named branch in another company |
| AI guardrails | **Not applicable** | This slice has no AI |

**Cross-checked each fix against a test that would really fail if the protection were
removed** (I read the tests, I did not count them):

| Fix | Pin test | Would it fail? |
|---|---|---|
| G1 (HR Analytics scope) | `test_hr_analytics_scope_012` — store HR, other-company HR, not-linked | **Yes** — they assert on the *figures*, not only the names, after the persona test was strengthened in `05342a9` |
| G2 (setting allow-list) | `test_every_other_key_is_refused_unchanged_and_logged` | **Yes** — it also asserts the stored default is **unchanged** and that neither key nor value appears in the log line |
| G3 (`person`, `filter_options`) | `test_attendance_scope_012` | **Yes** — nine tests including "another company is refused even for central HR" |
| Q6 (org-roles guard) | `TestOrgRolesGuard` | **Yes** — including `test_frappe_automatic_roles_never_count` |
| DEF-1 | `test_invoicing` classification test | **Yes** |
| DEF-2 | `test_fixing_a_day_older_than_the_window_still_clears_it` | **Yes** — and the expected-failure marker is gone, so it is a real passing test now |
| DEF-3 | `test_the_badge_is_set_from_the_page_load_call` + the engineer's probe | Partly — the test pins the page **string**. The server half (`_with_review_count` outside the cache) is proven only by the test engineer's probe, not by a committed test. **Add one:** confirm, then call `get_portal_context` and assert the count dropped |
| DEF-5 | `test_the_page_never_re_opens_a_cleared_record` | **Yes** |
| DEF-6 | `test_store_hr_cannot_open_someone_with_no_branch` | **Yes** |
| DEF-7 | Not a pin test — a measurement, plus `test_leader_indexes_012` pinning the ninth index | Acceptable. The index list is pinned, which is the part that can silently regress |
| DEF-8 | `test_store_hr_sees_their_own_store_and_nobody_without_a_branch` + `test_store_hr_cannot_ask_for_another_branch` (in `c78efcd`) | **Yes.** And I checked slice 011's pinned tests myself: `_linked_branches()` returns `None` for a user with no Branch permission, so central HR and System Manager are untouched and those tests still hold |

**One gap:** there is no test proving that a client **cannot** set `flags.via_rule_check`
through a REST payload. The protection is real (I verified it in Frappe's source), but it
lives in the framework, not in this repo — so a Frappe upgrade could remove it without a
single test going red. One test that posts `{"flags": {"via_rule_check": true}}` through
`frappe.client.save` and expects a refusal would close that for good. Cheap, and it is the
kind of test that earns its keep in three years.

---

## 6 · Non-functional budget

| Budget | Measured / reasoned | Pass? |
|---|---|---|
| Whitelisted call ≤ 500 ms p95 (`nfr-budget.md` §2) | `get_hr_analytics` 283 ms, `data_review_items` 243 ms warm at 1,000 people, company scope (tester). Engineer measured 359 / 409 ms — same ballpark, both inside | **Pass** |
| `get_hr_analytics` ≤ 1 s at 2,000 (`07` §3 H) | **Not measured.** 2,000 was never run | **Unknown** |
| Cold call | 564–672 ms after a full cache flush | **Over budget, acceptable** — a full flush is harsher than any real first call, and most of it is Frappe reloading its own metadata |
| Morning job ≤ 20 s at 400 / ≤ 60 s at 2,000 | 962 ms at 400; 675 ms at 1,000 after the index | **Pass** |
| No full scan of Attendance or Employee Checkin (AC-3) | `EXPLAIN` clean at both scopes after the ninth index | **Pass** |
| Query count does not grow with people or branches (AC-4) | Four query-count tests | **Pass** |
| `ignore_permissions` count must not rise | 0 in every new file, `hr_api.py` down 77 → 75 | **Pass** |

**Watch item the test engineer raised and I agree with:** Leave Allocation and Leave
Application are read without a `(company, from_date)` index. At 1,000 people they are 1,000
and 2,000 rows and the optimiser reads them whole, which is fine. They grow with headcount.
That is the next thing to bite, and it belongs in the push-2 or the OPS backlog, not here.

**On the `detail` flag and its two `detail=False` callers.** I think this is the right
design, and I want to say why, because a boolean flag on a shared function is usually a smell.
Here it is not: the flag removes two joins and a `count(distinct)` that neither calling screen
displays, it is measured (158 ms → 23 ms), the default is the **safe, complete** one, and the
full branch stays alive under test because `test_late_arrivals_and_short_days` calls it with
the default and asserts on late = 1 and short = 1. My only concern — that the `detail=True`
branch would rot with no production caller until push 2 — is answered by that test. Leave it
as it is.

---

## 7 · Test quality

I read the tests rather than counting them. They are good — better than most of what comes
through this gate.

**What is right:**

- They assert on **behaviour**, not on call counts. The store-HR tests check the figures, not
  just the names, after the persona test was tightened.
- The negative permission cases are all there: other store, other company, same-named branch
  in another company, not-HR, Guest, no-Employee, Leadership, plain Employee.
- No hard-coded dates I could find, no `sleep`, no assertion on a real employee id.
- `test_the_page_still_calls_only_the_allowed_key` reads the page source with a regular
  expression and fails if a new setting key is ever written from the page. That is a test that
  keeps a *rule* alive, not a line of code.
- `test_the_resync_really_drops_an_unmarked_index` proves the problem the Property Setter
  solves actually exists. Most teams would have asserted the fix and never proved the bug.
- The ceiling test, with a comment explaining every number, is the best kind of budget test.

**Gaps, in order of how much they matter:**

1. No test for M1 (no limit on `data_review_items`) — it does not exist yet.
2. No server test that `_with_review_count` sits outside the context cache (DEF-3's real fix).
3. No test that a REST payload cannot inject `flags` (see §5).
4. No real two-connection race on `data_review_confirm`. The `for_update` is right and a
   second confirm is refused; a true concurrent test would need two connections and I accept
   the engineer's and tester's reasoning for not building one.
5. `test_leave_year` has three pre-existing errors on `test_site`, so **AC-9's calendar-year
   fallback did not run cleanly**. That is a pre-existing bench problem, not this slice's, but
   it means one AC is unproven. Worth fixing before `main`, since the leave-year rule is the
   thing that changes HR's leave figure.
6. AC-1 was proved on `test_site`, not on a site built from scratch with `bench install-app`.
   `after_install` is a different code path from `after_migrate`.

**Fixtures:** `leader_fixtures_012.py` uses made-up names (`S012 …`) and no real employee
data. `03` notes a few stray `S012` Branch rows left on `test_site`. Harmless, uniquely named,
but worth clearing so the next person does not wonder.

---

## 8 · Compliance verification

The spec **does** carry a compliance-impact sub-analysis (§14), so this slice is reviewable on
this axis. Taking it row by row, for push 1 only:

| Obligation (spec §14) | Mechanism in the diff | Test that proves it | Verdict |
|---|---|---|---|
| Purpose limitation — totals only, no leave type, never reused for ratings (PRIV-1, PRIV-13) | `org_figures.PURPOSE` constant; no name, employee id or leave type in any `org_figures` or `data_review` return; `attendance_score.py` untouched | `test_central_hr_sees_every_kind_with_counts_and_no_people`; `TestAppraisalScoresDoNotMove`; `test_nothing_that_rates_people_imports_the_leader_figures` | **Discharged** |
| Minimisation — no new personal data collected | Both new doctypes hold counts, dates, company, branch and HR user ids. No employee field exists on either | `test_no_employee_field_and_no_name` reads the doctype definition | **Discharged** |
| Refusal logging ≥ 1 year (DPDP Rules 6(1)(c)/(e), SEC-14) | `access.refuse` → `log_refusal`, one JSON line, rule id + document name only | Log-line assertions in the G2 and confirm tests | **Discharged for the writing.** The one-year *keeping* is a log-retention setting, not in this diff — that is `07`'s |
| Deny by default / server-side scope (ASVS L2, SEC-1, SEC-2) | `hr_scope` returns an empty scope and every path returns `not_linked` rather than everything | `test_hr_with_no_company_and_no_employee_gets_no_figures` | **Discharged** |
| `ignore_permissions` budget must not rise (B4/I3) | Zero in all new files | `CEILINGS` pinned at 0; `hr_api.py` lowered | **Discharged** |
| Audit entry records **before and after** (AC-19) | `figure_without` / `figure_with` + `confirmed_by` + `confirmed_on`, `track_changes` on, one Version row per save | `test_hr_confirms_the_absence_was_real` | **Partial.** Correct for doubtful days. For leave and leavers confirmations `figure_without` is `None` — see m8 |
| Named accountable human for every confirmation | `confirmed_by` is forced to equal `frappe.session.user` in the controller; a confirmation naming anyone else is refused | `test_a_confirmation_must_carry_the_confirming_user` | **Discharged** — and enforced structurally, which is the right way |
| Derivation can be replayed from stored inputs | Every finding stores `expected_count`, `absent_count`, `checked_in_count` (or `affected_count`, `people_count`, `days_allocated`), plus the rule and the date; the thresholds are module constants | Count assertions throughout `test_morning_checks_012` | **Discharged** |
| Retention 13 months + 1 year for review items (PRIV-14, Q10) | Declared in the doctype description and in `03`. **No purge, no legal-hold concept** | `Version` is not in the log clean-up list | **Partial, and the spec says so** — there is no retention engine (feature map A6). Not this slice's job to build one, but do not let it be recorded as done |
| Nothing personal reaches a log, an error message or a notification | §5 above; `_log_failure` deliberately avoids `get_traceback()` | `test_a_failure_is_logged_without_figures_and_the_stamp_stays_old` | **Discharged** |
| No automated decision about a person (§14.4) | Doubtful days change which rows count in a total; a named HR user confirms; no employee record is written | AC-11 pin; the import check | **Discharged** |
| CQ1–CQ5, F1 (name the compliance owner), residual risks R1–R8 | Nothing in the diff | — | **Open — yours and counsel's, unchanged by this push** |

Two visibility changes that were **not** in the spec's delta, both narrowing, both fine — but I
name them so the record is complete: `filter_options` no longer lists managers the caller
cannot read, and (in `c78efcd`) the Attendance Insights organisation list no longer shows
no-branch staff to location HR.

One field I want to draw your eye to, because it is a widening decision that was made
deliberately and is easy to forget: `get_hr_analytics` still returns **`gender`** in
`recent_employees` (the 10 newest joiners). It was there before, it is now scoped to the
caller's companies and branches, and `00` records the choice to keep it. It is still gender
data on a dashboard that nothing on that dashboard needs. My recommendation: drop it in push
2 unless a screen uses it. Not a blocker, and not a change to make quietly now.

---

## 9 · What a human must still check by eye

Nothing here can be closed by reading code, and two of them should be closed before `main`.

| # | What | Before `dev`? | Before `main`? |
|---|---|---|---|
| 1 | **The browser run.** Nobody has seen this page. 360 px, 200% zoom, keyboard through the confirm dialog, and the four desk links actually opening the right filtered list. `ppj.localhost` has no 012 tables, so this needs your word to migrate a site | Helpful | **Yes** |
| 2 | **Index build time (AC-5).** Nine indexes are created inside `after_migrate`, one of them on an Attendance table with 200,000+ rows on a real tenant. Nobody has timed it. This is a deploy that holds a table lock for an unknown period | No | **Yes — do not skip this one** |
| 3 | **2,000 employees.** The budget says ≤ 1 s there. 1,000 came in at 283 ms after the fix, so it will very likely pass, but "very likely" is not a measurement | No | **Yes** |
| 4 | **Telling each tenant's HR the numbers are changing (BA-Q14, OPS-68).** On the demo tenant September attendance moves from 65.8% to 97.0% and three "needs review" items appear on day one. There is no switch, and no rollback except a revert. **If HR is not told first, this lands as "the system broke"** | No | **Yes, and it is the biggest one** |
| 5 | A fresh `bench install-app` site, to prove `after_install` (AC-1) | No | Yes |
| 6 | The three pre-existing `test_leave_year` errors, so AC-9's calendar-year fallback actually runs | No | Yes |

---

## 10 · What I would delete or simplify

Short list, which is itself a good sign.

1. **Nothing built that the spec did not ask for.** I looked specifically: no new settings
   page nobody asked for, no feature flag, no compatibility shim, no generic framework built
   for one use. `group_by` and the cache invalidation were both *correctly left unbuilt*
   because push 1 has no caller for them. That restraint is unusual and I want it on the record.
2. **`org_figures.FORMULA_VERSION = 1`** is dead in push 1 — nothing reads it. Its only stated
   purpose is push 2's cache key. By the slice's own rule (no abstraction before its use) it
   should arrive with the cache, not before it. **One line to delete.** I would not hold the
   slice for it.
3. **`rate_with` and `open_doubtful_counts`** could arguably fold into one, but they are used
   at three call sites between them and each reads clearly on its own. Leave them.
4. **`_finding`'s `**counts` signature** hides which count fields each rule sets. A small named
   tuple per rule would read better, but it is three rules and the file is short. Leave it.

Nothing else. There is no over-engineering in this diff, and no under-engineering either — the
error handling, the permission checks, the indexes and the tests are all there.

---

## 11 · What was done well

Specific decisions, not people.

1. **The record's name *is* the finding.** A hash of (rule, company, branch, date) as the
   primary key, with the reasoning written down: a unique index would not have worked because
   MariaDB lets NULLs repeat. The job can run twice, or twice at once, and cannot double-write.
   That is a structural guarantee where most people would have written a check-then-insert and
   a race.
2. **Disagreeing with DevOps in writing, with evidence.** OPS-52 said `add_index` alone. The
   engineer read Frappe's schema sync, found that it drops unmarked single-column indexes,
   proposed the Property Setter, said plainly "I disagree with DevOps here; you decide" — and
   then wrote `test_the_resync_really_drops_an_unmarked_index` to prove the problem is real.
   Proving the bug, not just asserting the fix, is the part I want other slices to copy.
3. **The test engineer re-probing the fixes instead of trusting the tests.** DEF-6 was reported
   fixed; the re-probe found DEF-8 — the same leak through a different door. That is what an
   independent test step is for, and it worked.
4. **Measuring before deciding.** `detail=False`, the `=` versus `in (one value)` change, and
   the ninth index were each justified by a number (158 → 23 ms, 292 → 29 ms, `EXPLAIN` showing
   a 212,585-row scan) rather than by instinct.
5. **The refusal message that is identical whether the record is missing, someone else's, or
   the wrong kind.** Small, deliberate, and it is what stops the endpoint becoming an oracle
   for what exists in other branches.
6. **The comments explain *why*, including what went wrong before.** `_with_review_count`,
   `condition()`, `data_up_to()` and `branch_scope` all carry the reason and the measurement.
   A new engineer will understand this in six months without the author. Rarer than it should be.

---

## 12 · Confidence, and where I could not check

**High confidence** on: the server code, the permission model, the SQL, the doctype
controllers, the guardrails in §5, the absence of new `ignore_permissions`, the absence of
personal data in logs, and that the DEF-8 fix does not break slice 011's pinned tests (I read
those tests).

**Medium confidence** on: the ACs marked "copy traced". I read the built strings against
prototype-v2 line by line, but nobody has seen this page in a browser, so I cannot tell you it
*looks* right, only that it *says* right.

**I am relying on others, not on my own observation, for:** every performance number (the
engineer's and the tester's, measured on a laptop bench shared with three other Frappe
stacks); every test-run result; and the claim that the whole suite's 14 failures are all
pre-existing. The test report is unusually honest about its own limits, which is why I am
comfortable relying on it — but it is reliance, not verification.

**I could not check, and would need the bench and your word for:** the test suite itself, the
index build time, behaviour at 2,000 employees, and anything in a browser.

**Process note:** the change process was followed. The impact analysis exists, it was written
before any file was opened, the strategy was approved on 2026-09-15, tests ran, and this
review is step 5. Nothing was pushed and nothing was deployed. **Step 7 is yours.**
