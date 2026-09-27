# 034 Wave 1 — senior architect review (step 5)

slice: 034-redesign-wave1
branch: `slice/034-redesign-wave1`, 33 commits ahead of `origin/dev` (`8718f27`)
reviewer: hrms-technofunctional-reviewer
date: 2026-09-24
inputs read: `00-impact-analysis.md`, `00g-decision-register.md`, `01c` rev 4, `02` rev 5,
`02c-ba-rereview.md`, `03-implementation-notes.md` (six stretches), `06b-security-rereview.md`,
`07-devops-inputs.md`, and the full diff of all 88 changed files.

---

## 1. Verdict

**SHIP WITH FIXES.** The code does what the spec asked, the permission and privacy
controls are real mechanisms rather than sentences, and the tests mostly fail when the
guard is broken — but **four things need your word before this reaches a live tenant**, and
none of them is a code defect: a delivery gate that only a human remembers, a missed query
budget, one visibility widening that was raised and never answered, and a set of
measurements nobody has taken.

`SHIP WITH FIXES` means "ready to present for deploy approval once the four P2s below are
answered". It is not itself permission to deploy.

**What I could and could not run.** I ran the Node checks and the browser tests myself —
73 assertions pass, `check_app_integrity` 634 checks OK, `check_design_system` OK,
`check_preview_flag` OK, `check_undefined_js` and `check_portal_handlers` OK. **I could not
run any `bench run-tests`**: there is no bench in this worktree. Every Python test result
below is the engineer's reported run, read from the notes, not re-run by me. I did read
every new test file line by line, which is the part that matters more.

**No P0 and no P1.** I looked for a cross-tenant leak, a permission bypass and personal
data in a log or a payload, and did not find one. Details under §5.

---

## 2. Findings, worst first

### P2 — needs your decision or a written acceptance before release

#### F1. The whole portal now depends on three files under `/assets/`, and the only thing checking they arrived is a person remembering to check

*Proven.* `www/hrms-employee.html` now loads `frame.css`, `panels.css` and `portal.js`
from `/assets/alvoraa_portal/...`. nginx serves that path with `expires 30d` and
`Cache-Control: public, immutable` (`deploy/nginx.conf:207-213`), with `try_files $uri
=404`.

Failure scenario: a deploy where `scripts/refresh_bench_files.sh` does not run, or runs
against the wrong volume → `/assets/alvoraa_portal/js/ess/portal.js` answers 404 → the
portal page still renders its shell and **does nothing at all**. Nothing reaches the
backend, so nothing appears in any log. The first person to notice is a client's employee
on a dead portal in go-live week.

The spec writes this up properly as release gate 9 (`02-functional-spec.md:857`) and
`07-devops-inputs.md` OPS-35 and OPS-36 say exactly what to check. **But both rows are
still "Recommend" with an empty decision column, and both are manual `curl`s by a human
after the fact.** The deploy workflow does run `refresh_bench_files.sh` (`deploy.yml:497`)
and `bench --site all clear-cache` (`deploy.yml:563`), which is good and which I verified
— but nothing fails the deploy when the three files are not there.

**Smallest fix:** three `curl -fsI` lines in `deploy.yml` after the health check, failing
the job on a non-200 or a zero length. Five minutes' work, and it turns the highest-cost
failure in this slice from "someone must remember" into "the deploy goes red". If you
would rather keep it manual, that is a decision to accept in writing, not a default.

Owner: `hrms-devops-engineer`. Risk if it waits: one bad deploy in go-live week looks like
a broken product, not a broken delivery, and the first hour is spent in the wrong place.

#### F2. `get_nav_counts` is 19–20 queries against a budget of 15 (AC-24)

*Proven by the engineer's measurement, read and believed; not re-measured by me.*
`03-implementation-notes.md` §6 of the browser stretch: 19 queries / 35 ms for company-wide
HR, 20 / 41 ms for store HR, 11 / 14 ms for a plain employee.

The engineer flags this as dangerous debt and asks you to choose. **My recommendation:
accept 19–20 and move the budget, and do the `goals_api` change as its own small change
after go-live.** My reasons, in order:

- The thing the budget was protecting is already true and is proven: **the call is flat in
  headcount.** Every part is an aggregate; none walks a list of people. Store HR and
  company-wide HR differ by one query on the same site. That is the property that decides
  whether this survives a thousand people, and it holds.
- 35–41 ms against a 500 ms p95 side of the same budget is not a performance problem.
- Option 1 (passing a ready-made scope into `goals_api.get_pending_approvals_count`) means
  editing a module this slice otherwise does not touch, in the week before go-live, to save
  four queries that cost nobody anything. That trades a real risk for a number.
- Option 2 (memoising `permitted_companies`) the engineer already refused for the right
  reason — a memo that outlives a request hands a background job a stale scope. Agreed; do
  not do it here.

So: **change AC-24 to 20 for an HR caller, keep 15 for everyone else, and raise a ticket
for the `goals_api` change.** What I would not accept is leaving a written budget that the
code misses with no decision recorded — a missed budget nobody answers becomes a number
nobody believes.

Owner: you, on the engineer's escalation.

#### F3. Open question 6 was shipped without being answered

*Proven.* `02-functional-spec.md:1063` says open question 6 "blocks **one line in the
SEC-13 commit**". The SEC-13 commit (`507fb74`) is on the branch. The question was never
answered.

What it means in practice: `frame_api`'s `is_hr` includes System Manager, and
`access.permitted_employee_filters` returns `ALL_EMPLOYEES` for a System Manager
(`hrms/hrms/alvoraa_hr_core/access.py:249`). So on release, **a tenant System Manager who
has an Employee record sees their whole tenant on the Team screen** (capped at 50 with the
true total), where today they see their own direct reports.

Why it is P2 and not higher: no new data. That person's desk already lists every employee,
and nothing crosses a tenant boundary. It is a wider *screen*, and this slice's own rule is
that nothing widens by accident. The engineer's and the analyst's recommendation is to
leave it, because it is what Kamal the owner wants and because we should not have two
versions of `permitted_employees()`. **I agree with that recommendation.** It needs one
line from you saying so, in the register, before release — not because the risk is large
but because `01c`'s PRIV-7 table calls it "the one wider row" and a wider row with no
decision beside it is the shape of a finding somebody will re-raise in six months.

#### F4. The new frame drops the stale-CSRF retry that the live page has, and the live page has it because this exact fault was hit before

*Proven by reading both.* `www/hrms_employee.py` carries a comment explaining that without
a minted CSRF token, "every open portal tab fails with *Invalid Request* the moment a desk
page opens in any tab". The live page's `gpFetch` handles the follow-on case:
`portal.js:5010-5022` detects `CSRFTokenError` or a 400 "invalid request", fetches a fresh
token and retries once.

The new frame does not. `next-frame.js:202` uses `frappe.call`, and its failure path
(`next-frame.js:916-930`) treats only `AuthenticationError`, 401 and 403 as "signed out";
everything else becomes the page-error state.

Scenario: an employee has the portal open on their phone and someone opens a desk page in
another tab, or the session token rotates → `get_frame` comes back with a CSRF error →
**the whole frame shows "The portal could not load. Try again."** Today's page recovers
silently.

It does not block *this* release — the new frame only exists on the preview page, which is
engineers only. **It must be fixed before the swap**, and it is worth fixing now while the
reason is fresh. Smallest fix: reuse `gpFetch`'s retry, or add the same `CSRFTokenError`
branch to `api()`.

Related, same area, smaller: `isSignedOut` counts **403** as signed out. Today `get_frame`
only returns 403 for Guest so it is harmless, but if any future 403 reaches a signed-in
caller the page bounces to `/login`, which redirects back, which bounces again. Narrow it
to `AuthenticationError` and 401.

---

### P3 — ship, but write it down with an owner

#### F5. The Team screen's cap only caps half of what it claims to cap

*Proven.* `hr_api.py` caps the HR list at 50 (`TEAM_LIST_CAP`), and the note says "at 1,000
employees it now draws 50 cards and **passes 50 ids to the queries below**". It does not.
`hr_api.py:435-450` then reads **every Active employee reporting to those 50**, with no
limit, and `team_ids = team + l2` is what goes into the attendance query, the raw-SQL
`IN (...)` for who is on leave today, and the month-leaves query.

Scenario: company-wide HR on a 1,000-person tenant; the first 50 people alphabetically
happen to include ten managers with fifteen reports each → `team_ids` is 200, not 50, and
the `IN` list in the raw SQL at `hr_api.py:465-475` carries 200 placeholders.

This is not a regression — before this change the same block ran over every unassigned
person in the tenant and *their* reports, which was worse — and every column is indexed. So
it ships. But the NFR claim in the notes is wrong and should be corrected, and §13's Team
budget (≤ 8 queries, ≤ 700 ms p95 at 1,000) remains unmeasured. Cap `l2` too, or say
plainly that it is uncapped.

Second, smaller thing on the same screen: for an HR caller the "indirect reports" list is
now the reports of an alphabetical slice of the company, which is not a meaningful group.
Nobody asked for it and nothing reads it usefully. Worth deleting for the HR branch.

#### F6. The CI step that proves the preview-flag guard works does not do anything

*Proven — I ran it.* `.github/workflows/ci.yml` runs
`python scripts/check_preview_flag.py --self-test` and then the same script again.
`check_preview_flag.py`'s `main()` never reads `sys.argv`, so **`--self-test` is silently
ignored and the same check simply runs twice.**

```
$ python scripts/check_preview_flag.py --self-test
preview flag: 11 deployment files checked
OK - no production file sets portal_preview
exit=0
```

The guard itself is real and it works — I ran it and read the walk. What is missing is its
positive control, and the notes explain exactly why one was wanted: the first version of
this script *passed a deliberately broken production file*. A check with no proof that it
can fail is the same shape as the hollow tests this slice has been bitten by twice.

Smallest fix: make `--self-test` write a throwaway `portal_preview` into a temporary
production-looking filename, assert the check returns 1, and clean up. Ten lines.

#### F7. "No `ignore_permissions` in these files" is a string match, and two calls get past it

*Proven.* `test_frame_endpoint_registry_034.py:188` asserts the literal text
`ignore_permissions` does not appear in `frame_api.py`, `inbox_api.py`, `staff_api.py`.
But `staff_api.py:171` uses `frappe.get_all` and `:187` uses `frappe.db.count`, and both of
those ignore Frappe's own permission layer by definition. `search_people` does the same.
`inbox_api` deliberately uses `frappe.get_list` and says why — so the two new files are
inconsistent with each other.

No leak follows from it: the scope filter in `staff_api` is explicit, is the shared one, and
fails closed. What is lost is any *extra* narrowing a tenant has configured — a User
Permission on Employee by department, for instance, would be honoured by the staff list if
it used `get_list` and is ignored as written.

Two options, both fine: switch `staff_api` to `get_list` (it is already inside a scope, so
the result can only narrow), or keep `get_all` and say so in the docstring instead of
claiming the stronger thing. Either way, AC-71's check should also look for `get_all`,
`db.count` and `db.sql`, or it will keep passing for files that bypass permissions.

#### F8. Two new caches that the impact analysis said did not exist

*Proven.* `00-impact-analysis.md:423` says Data integrity is Neutral because "counts are
live, not cached, so nothing can go stale". The code that was written adds two caches the
analysis did not foresee:

- `ess_parts.py:56-62` — the portal's markup, cached per site for 24 hours, keyed by the
  build version.
- `inbox_api.py:77-92` — "does this doctype exist", cached per site for 24 hours, **not**
  keyed by the build version.

Neither caches a count, so the sentence about counts still holds. Both are correct as long
as the deploy clears the cache — and it does: I verified `bench --site all clear-cache` at
`deploy.yml:563`. **The trap is the path that skips it.** `docker cp`-ing a part file onto
a running container — which is a deploy command this project uses — changes nothing a user
sees for up to 24 hours, and the markup that is served is the previous build's. Write that
into the release note.

The doctype cache has a second, smaller edge: if the goals app is installed on a live
tenant and the cache is not cleared, the Inbox counts KPI approvals as zero for up to a day.
`bench migrate` clears the cache, so the normal path is safe. One-line fix if you want it
airtight: put the build version in that key too, like `ess_part` does.

---

### P4 — backlog

- `renderTeamData` sets the "team size" tile to `team.length` (`portal.js:3527`), so a
  company-wide HR person on a 412-person scope sees a tile reading **50** with the subtitle
  "Showing the first 50 of 412" underneath it. The tile matches the list, which is the rule,
  but "team size 50" is not true. Show the total in the tile and the cap in the subtitle.
- `frame_api.get_frame` filters its top level through `FRAME_KEYS`, which is a genuinely
  good mechanism — but `features` is a pass-through of the whole of
  `get_available_features()`. The guarantee is one level deep, not "nothing can reach the
  browser by accident". I checked: that function returns booleans only, so there is nothing
  there today. Worth one honest sentence in the docstring.
- `inbox_api.PARTS` sends `my_requests` to `#time` rather than to the screen each item came
  from. Named in the code as an acceptable simplification for Wave 1. Agreed; it belongs to
  Wave 2's Inbox list.

---

## 3. The four things the engineer could not prove — my judgement on each

| # | What | Ship it? | Why |
|---|---|---|---|
| 1 | `get_nav_counts` 19–20 queries vs a budget of 15 | **Yes, with a decision** | F2. Accept the number, move the budget, ticket the `goals_api` change. Do not edit `goals_api` in go-live week to save four queries that cost 6 ms |
| 2 | No phone-width, 200 % zoom or Hindi rendering measured | **Yes for this release. No for the swap** | Nothing a customer sees changes shape in this release — the CSS moved file, byte for byte, and AC-36/AC-64 pin that. The moment the swap puts this frame in front of a shift supervisor on a phone, an unmeasured 390 px layout is a P1. Measure before the swap, not before this push |
| 3 | No p95 at 1,000 employees; the test site has ~120 people | **Yes** | This is the right call and the engineer made the right argument: the call is flat in headcount *by construction*, and that property is shown rather than asserted (store HR 20 queries, company-wide HR 19, same site). A p95 measured on 120 people would be a number pretending to be evidence. Build the 1,000-person fixture as its own piece of work — three acceptance checks in this spec name that number and none of them can be answered without it |
| 4 | AC-62, the signed-out redirect, not proven against a real expired session | **Yes for this release. No for the swap** | It only exists on the preview page today. And F4 says the same code path needs work anyway — prove them together, in a browser, with a real expired session, before the swap |

---

## 4. The three specific mechanisms you asked me to check

**`inbox_api.py` and slice 042.** *Safe to extend.* The file is counts only. `PARTS` is a
tuple of `(key, route)` pairs with the section-5 order in it, `APPROVAL_PARTS` names the
arithmetic rather than hiding it in one line, and each part is its own small function with
its scope rule written down. Wave 2 adds list functions beside these and reuses the same
part keys; nothing here has to be moved or rewritten. The one thing 042 must not do is
create the file — the docstring says so in its first paragraph and the work board says so
in capitals. That is as much as code can do about a scheduling clash.

**The 12 markup parts and `ess_part()`.** *Safe.* I traced it. `ess_parts.py:47-52`
matches the name against `^[a-z0-9-]+$` before anything else, so a path, a separator, an
extension, a URL-encoded `..`, an upper-case letter, a trailing space and an empty string
are all refused; then `_read` requires `os.path.isfile` on a name joined to one fixed
folder. No user input reaches it — the page calls it with twelve literals
(`www/hrms-employee.html`). A missing part **throws**, which takes the whole page down
rather than silently rendering a page with a hole in it; that is the right direction, and
`test_portal_split_034.test_the_helper_refuses_when_an_include_file_is_missing` and
`test_ess_parts_034` pin all of it. A part containing a Jinja tag is refused rather than
rendered as text. The one thing to remember operationally is F8: the parts are cached for a
day, so a hand-copied file does nothing until the cache is cleared.

**Stale or missing assets.** See F1, which is my highest-ranked finding. The version stamp
works: `get_build_version()` is the modified time of `sites/assets/assets.json`, and
`refresh_bench_files.sh:58` copies that file **last**, so a page served mid-copy cannot
name files that do not exist yet. The gap is not the mechanism, it is that nothing fails
when the mechanism does not run.

---

## 5. The eight lessons this slice paid for — did they hold?

| Lesson | Held? | Evidence |
|---|---|---|
| `get_frame` returns a fixed key list, no DOB / gender / phone / joining date / manager / branch | **Yes — proven** | `frame_api.py` returns `{key: frame[key] for key in FRAME_KEYS}`, and `_me` selects six named columns. `test_frame_api_034` serialises the payload for seven personas and fails if any of the six words appears at any depth. I read both |
| The shared scope filter never returns `{}` | **Yes — proven** | `access.py` `NO_EMPLOYEES = {"name": ["in", []]}` and `ALL_EMPLOYEES = {"name": ["!=", ""]}`. `test_permitted_employee_filters_034` asserts the value directly, not just the result — which is the assertion that caught it when the engineer broke it on purpose |
| The preview page does not exist on production; flag first, role second | **Yes — proven** | `hrms_employee_next.py` raises `DoesNotExistError` before the login check and before the role check. The test file drives both orders, and the engineer's HTTP table shows 404 for all four personas with the flag off. I ran `check_preview_flag.py` myself. One weakness: F6 |
| A refusal reads the same either way | **Yes — proven** | `staff_api._refuse` is one sentence for both causes, and `test_the_refusal_says_the_same_thing_whatever_the_reason` compares the two exception strings. The browser side asserts the same sentence for "not bought" and "not allowed" — I watched that assertion pass |
| Counts equal the list, and say so when capped | **Yes — proven** | One definition (`attendance_correction.review_queue_filters`) used by both the queue and the count; the count is uncapped and the row carries `cap` and `capped`. I traced `_state` against the new database filter and they agree on every state including a draft with no label. The screen says "Showing the first 50 of 60" and a browser test checks the words |
| Fixtures that patch the feature gate to "on" | **Caught, and guarded** | `test_staff_list_034` patches the *real* function back on top of whatever is there and then **asserts it is not a Mock**, with the reason written out. `test_frame_api_034` has its own guard test. This is the best thing in the test suite |
| Masked guards — a cap or a helper covering for a missing check | **Two found by the engineer, one more found by me** | The engineer found the Python truncation masking a missing SQL `limit`, and found that breaking the HR scope did **not** turn the count-equals-list test red because both sides share one definition. Both are now written down. I add F7: AC-71's `ignore_permissions` check is a string match that `frappe.get_all` walks straight past |
| Browser assertions that can never fail | **Fixed, and I re-checked** | Every check in `next_frame_test.js` now goes through `is(got, want, msg)`. The two `ok(...)`-with-a-string shapes are gone. I read the file and ran it: 73 pass, 0 fail |

---

## 6. Acceptance checks

I walked the ACs the branch claims. I did not re-run the Python tests, so rows marked
*(engineer's run)* rest on the notes plus my reading of the test code.

| AC | State | Evidence |
|---|---|---|
| AC-1, AC-44 (Expenses always there; no payroll hides My pay) | **Met** | `next-frame.js` MENU `pay` group; two browser assertions, run by me |
| AC-6 (nothing greyed out) | **Met** | Browser test queries for `[disabled]` and `[aria-disabled]` across rail, top bar and bottom bar. Run by me |
| AC-7 (two start-up calls, no timers) | **Met** | Browser test counts the calls. Run by me |
| AC-8 (agrees with the three old calls) | **Met** *(engineer's run)* | `TestItAgreesWithTheThreeOldCalls`, seven personas, compares against the live functions |
| AC-10, AC-11, AC-47, AC-63 (persona rules and the bar) | **Met** *(engineer's run + browser)* | `RULE_BARS` plus `_persona_rule`; the five named bar cases are asserted literally |
| AC-12, AC-48 (390 px, 200 %, Hindi) | **Not met** | Written to the rules, not measured. §3 item 2 |
| AC-19 (theme before first paint) | **Met** | Inline script precedes the design system; a browser assertion checks the ordering in the source. Run by me |
| AC-20, AC-23, AC-51, AC-52, AC-61 (one honest number) | **Met** *(engineer's run + browser)* | `inbox_api` + `review_queue_filters`; cap boundary tested at 51 |
| AC-24 (≤ 15 queries) | **Not met** | 19–20 for HR. F2 |
| AC-26, AC-28, AC-29, AC-56, AC-57 (search scope, caps, wildcard escaping) | **Met** *(engineer's run)* | `_search_scope`'s five cases, `_escape_like`, `MAX_RESULTS`; `test_search_scope_034` |
| AC-31, AC-32, AC-33, AC-34, AC-35 (server-rendered shell, the five states, the sheet, toasts) | **Met** | Browser tests, run by me |
| AC-36, AC-37, AC-64 (the split changes nothing, and the checks follow it) | **Met** *(engineer's run)* | `test_portal_split_034` plus the two source expanders; I ran the Node side |
| AC-40, AC-65, AC-74 (the preview page's two locks) | **Met** | `test_preview_page_034`, plus the engineer's real HTTP table. I ran the repository half |
| AC-45 (absent opt-in key hides) | **Met** | `plan_staff_list === true` in the menu; browser assertion, run by me |
| AC-46, AC-70, AC-71 (fixed keys, no run-time module state, no `ignore_permissions`) | **Met, with F7 on the third** | Registry test reads the AST for `global` and module-level mutables |
| AC-58 (a nasty job title creates no element) | **Met** | `esc()`; browser assertion with `<img src=x onerror=…>`, run by me |
| AC-62 (signed-out redirect) | **Not proven** | §3 item 4 |
| AC-67 (the Save flag matches the endpoint) | **Met** *(engineer's run)* | Tested against the **real** endpoint for every persona, not against a rule written twice. This is the right way to test a mirrored guard |
| AC-69 (the endpoint registry) | **Met** *(engineer's run)* | Fails if a whitelisted function has no row, and fails if a row names a test that does not exist |
| AC-72 (Team screen follows HR scope) | **Met, with F5** | All six rows of the table, plus a static check that the orphan query is gone and a spy that the `limit` is on the query |
| AC-73 (never an empty filter dict) | **Met** | Direct assertion on the value |
| AC-76 (staff list and its switch) | **Met** *(engineer's run + browser)* | Server-side refusal with a positive control beside every negative |
| AC-9a/9b/9c, AC-16, AC-21, AC-50, AC-53, AC-54 | **Out of reach in Wave 1** | Need screens later waves own. Correctly declared |

---

## 7. Non-functional: the analysis's claim beside what the code does

| Dimension | Impact analysis said | What I found | Verdict |
|---|---|---|---|
| Performance | Improves; `get_nav_counts` ≤ 15 queries | 19–20 for HR, 11 for an employee; 35–41 ms. Page HTML down from 1,071,272 to 209,574 bytes; server render −22 % | **Budget missed, real-world better.** F2 |
| Security | Improves; `ignore_permissions` count does not rise | Improves, genuinely: store HR narrows on search and Team, leavers find nobody, the staff-list switch is enforced server-side with a logged refusal. `ignore_permissions` did not rise; `get_all` is used in the new staff list | **Improves.** F7 is a wording and consistency point, not an exposure |
| Reliability | Improves, with new-code risk | Five states, all reachable and all tested; a failed count leaves the page working. Minus the CSRF retry | **Improves, F4 outstanding for the swap** |
| Scalability | Neutral | Better than neutral: the Team screen had no ceiling and now has one; counts are aggregates and flat in headcount. But `l2` is still uncapped | **Improves. F5** |
| Maintainability | Improves (degrades 2–3 weeks) | The page is 32 lines and twelve parts; one definition of "waiting"; one scope helper in two shapes. `portal.js` is still 13,451 lines in one file | **Improves** |
| Data integrity | Neutral; "nothing is cached, nothing can go stale" | Two new 24-hour caches the analysis did not foresee | **Changed, and it was not named.** F8 |
| Compliance / privacy | Improves; "no visibility is widened" | Six rows narrower. **One row wider** — the System Manager Team screen — raised in a later revision and never answered | **Improves, with F3 open** |

NFR budget (`.claude/context/nfr-budget.md` §2/§3) — pass/fail as measured by the engineer:
p95 comfortably inside 500 ms on a 120-person site; query budget missed for one caller; the
1,000-person p95 and the 390 px measurement are **not checked**, not failed.

---

## 8. Compliance

`01c` revision 4 carries a real compliance sub-analysis (PRIV-1 to PRIV-7 and SEC-1 to
SEC-16), so this axis is reviewable. Walking the items that this branch actually touches:

| Obligation | Mechanism in the diff | Test that proves it | Verdict |
|---|---|---|---|
| SEC-1 — the preview page does not exist on production | `hrms_employee_next.py`, flag read before role; `scripts/check_preview_flag.py` in CI | `test_preview_page_034` (12 tests) + the script, which I ran | **Discharged**, F6 is about the script's own self-test only |
| SEC-2 — every endpoint is live from its release, whatever page calls it | The endpoint registry | `test_frame_endpoint_registry_034` | **Discharged** |
| SEC-3 / SEC-4 / SEC-5 — one scope rule, never fail-open | `permitted_employee_filters`, `NO_EMPLOYEES`, `review_queue_filters` | `test_permitted_employee_filters_034`, `test_search_scope_034`, `test_inbox_counts_034` | **Discharged** |
| SEC-6 — no `ignore_permissions` in the new files | String check in the registry test | Same | **Partial** — F7 |
| SEC-12 — a fixed payload, no extra personal fields | `FRAME_KEYS` filter on the way out | `test_frame_api_034`, at every depth | **Discharged** at the top level; one level deep for `features` |
| SEC-13 — the Team screen follows HR scope | The orphan block deleted, not filtered | `test_team_scope_034`, incl. a static check and a query spy | **Discharged**, with F3 open on one persona |
| SEC-14 — a leaver finds nobody | `_me_active()` in the search path | `test_a_leaver_with_a_live_login_finds_nobody`, and the frame's rule 6 test | **Discharged** |
| SEC-15 — no module-level state that changes at run time | Tuples everywhere; AST check | `test_no_module_level_dict_list_or_set` | **Discharged** |
| SEC-16 — the staff-list switch enforced on the server | `has_feature` + logged refusal in `staff_api` | A14 test, with a positive control | **Discharged** |
| PRIV-2 — five keys, Active only | `ROW_KEYS`, built key by key | `test_the_payload_holds_exactly_the_five_keys` | **Discharged** |
| PRIV-3 — `%` and `_` mean themselves | `_escape_like` in two places | Wildcard tests in both files, each with a positive control | **Discharged** |
| PRIV-4 — counts carry no personal data | Numbers only | `test_the_payload_carries_numbers_and_nothing_else` serialises and searches | **Discharged** |
| PRIV-5 — a name never travels in a URL | Both search endpoints are POST-only | `frappe.allowed_http_methods_for_whitelisted_func` asserted; refusal-log test proves no name, store or term is logged | **Discharged** |
| PRIV-7 — the visibility table | Written, 18 rows | Checked by the test engineer against the built screens | **Partial** — the one wider row is undecided. F3 |
| Retention / legal hold / audit before-and-after | Not touched by this slice | — | **Not applicable**; nothing here writes or deletes |

No AI in this slice, so the AI-specific axis does not apply.

---

## 9. What to delete

Little, which is a good sign. Three candidates:

1. **The `l2` block for the HR branch** of `get_manager_dashboard` (`hr_api.py:435-448`).
   For a manager it is meaningful. For an HR caller it is "the reports of an alphabetical
   slice", which nobody asked for and which is the uncapped half of F5. Skipping it when
   `is_hr_scope` is true removes code *and* removes the scale concern.
2. **`team_cap` in the payload** (`hr_api.py`). The screen never reads it — it uses
   `team.length` and `team_total`. One key nothing consumes.
3. Nothing else. I looked specifically for a new DocType where a field would do, a new app
   where a hook would do, a settings page nobody asked for and a generic framework built
   for one use. There is none. The staff-list switch reuses the existing `FEATURES`
   registry rather than inventing a second mechanism; the scope helper is one function in
   two shapes rather than two rules; `ess_part` is 76 lines and replaces a problem that
   twelve `{% include %}`s could not solve. That restraint is worth saying out loud.

---

## 10. What was done well

- **The entitlement-patch guard in `test_staff_list_034`.** It patches the real
  `has_feature` back on top of whatever mocks are stacked and then *asserts it is not a
  Mock*, with the failure message written for the person who will see it. This is the
  direct answer to the lesson from slice 016, and it is the single most valuable thing in
  this branch.
- **Breaking each guard on purpose and recording which test went red** — including the two
  cases where **nothing** went red, and why. "Removing the `limit` turned nothing red
  because the Python truncation covered for it" is worth more than a page of green ticks.
- **Testing a mirrored flag against the real endpoint.** `may_save_settings` could have
  been tested against a rule written twice. Instead it calls `hr_api.set_org_setting` for
  every persona and asserts it throws exactly when the flag is false. The two cannot drift.
- **`FRAME_KEYS` as a filter on the way out**, not as a docstring. A new field inside
  `get_frame` does not ship.
- **Deleting the orphan query rather than filtering it**, with the reason written where the
  next person will be standing when they are tempted to put it back.
- **Saying "I did not measure that"** four times, in the artifact, with the number that was
  not measured named. That is what made this review possible in a day.

---

## 11. Confidence, and what I could not check

**Proven by me:** every Node and Python repository check named in §1 (I ran them and pasted
the output); the full text of `frame_api.py`, `inbox_api.py`, `staff_api.py`,
`ess_parts.py`, `access.py`'s diff, `hr_api.get_manager_dashboard`,
`attendance_correction`'s diff, both www pages, `next-frame.js`, the eight new test files,
`scripts/lib/portal_source.js`, `run_dom_tests.js`, `check_preview_flag.py`, the CI diff,
the nginx assets block and the deploy workflow's cache and asset steps.

**Read but not re-run:** every `bench run-tests` result. There is no bench in this
worktree. To re-run them I would need the engineer's container `hrlocal-034` or an
equivalent site.

**Not checked, and I would need a browser on the bench:**

- Whether `frappe.call` is actually available on a Frappe *website* page, and whether the
  new frame boots at all in a real browser. The proof offered is a `curl` (which does not
  run JavaScript) and jsdom (where `frappe.call` is a stub the test wrote). This is not a
  finding — I have no reason to think it is broken — but it is the one assumption under the
  whole browser stretch, and it is untested. **Open it once on the preview page on dev
  before anyone celebrates.** Related to F4.
- The 390 px layout, 200 % zoom, Hindi strings, and p95 at 1,000 people. §3.

**Assumptions I am carrying, marked:**

- `[ASSUMPTION]` Frappe's `"not in"` filter wraps the column in `ifnull()`, so a NULL
  `alvoraa_review_status` counts as waiting. The spec carries the same assumption and says
  it could not be verified from the repository. The engineer's
  `test_a_correction_with_no_label_is_still_waiting` passed on a real bench, which is
  stronger evidence than either of us reading the source — I am treating it as proven by
  that test and not by the assumption.
- `[ASSUMPTION]` `cp -p` in `refresh_bench_files.sh` preserves the image's `assets.json`
  timestamp, so the build version moves with every image. If a build ever produced an
  identical mtime, the `?v=` would not move. I did not test this; OPS-36 is exactly the
  check that catches it, which is another argument for F1.

**Questions that would change my verdict, smallest first:**

1. *Must know.* Is F1 acceptable as a manual gate? I am reading release gate 9 as "a human
   runs three `curl`s after each deploy". If that is accepted in writing, my verdict stands
   at SHIP WITH FIXES. If nobody owns it, I would move it to BLOCK, because a dead portal
   in go-live week is the worst thing in this slice and it has no automatic detection.
2. *Must know.* F3 — leave the System Manager's Team screen as the whole tenant, or restrict
   it to HR Manager / HR User? I recommend leaving it. Either way it needs a line.
3. *Should know.* F2 — move the budget to 20, or take the `goals_api` change now? I
   recommend moving the budget.
