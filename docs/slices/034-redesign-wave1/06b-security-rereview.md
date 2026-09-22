---
slice: 034-redesign-wave1
artifact: 06b-security-rereview
author: hrms-security-privacy-engineer
date: 2026-09-22
status: re-review of requirements revision 2 — no code exists yet
reviews: 01c-security-privacy-requirements.md (revision 2), 02-functional-spec.md (revision 2), 00-impact-analysis.md (revision note) — commit 6ad7936
note: 06-security-review-of-requirements.md stands; this file records what closed
inputs: [06-security-review-of-requirements.md, 01c rev 2, 02 rev 2, 00 revision note, 02b-ba-review.md, ../009-ess-portal-redesign/00f-decisions-2026-09-22.md, the code in this worktree (read only), .claude/context/security-compliance-baseline.md, .claude/context/compliance-feature-map.md]
---

# Re-review of the Wave 1 requirements (revision 2)

## Verdict: closed with notes

**All eight must-changes (M1–M8) and all ten should-changes (S1–S10) are genuinely
closed.** They are not merely mentioned: each one has requirement text that says what
must be true, and an acceptance check in `02` that says how it is proved. The
traceability table in `02` §17 covers every SEC and PRIV item.

**Three things must still change before a line of code is written.** None of them
re-opens M1–M8. All three come out of reading the code that revision 2 now commits to
changing. They are N1, N2 and N4 below. N2 in particular would otherwise be found half
way through the build and settled on the spot, which is how a fail-closed control becomes
a warn-and-continue one.

---

## 1 · The eight must-changes

| # | What I required | Closed? | The evidence I checked |
|---|---|---|---|
| **M1** | `get_frame` returns a fixed key list and role booleans only | **Yes** | `01c` SEC-12 names the allowed keys exactly — `employee`, `employee_name`, `designation`, `department`, `image`, `company` — and names all six excluded fields (`date_of_birth`, `gender`, `cell_number`, `date_of_joining`, `reports_to`, `branch`). Roles go out as four booleans, not the role list. The cache-never-decides-data rule is stated. `02` AC-46 tests the key set per persona and names the same six exclusions plus "the full role list". The data inventory has a row for the excluded fields, and US-17 exists as a user story. **This is the strongest of the eight.** |
| **M2** | The preview gate is not a data control; every endpoint ships with its tests; registry test; `no_cache`; 404 after the swap | **Yes, with one traceability slip (N6)** | SEC-1 carries 403, the Guest redirect, `context.no_cache = 1` and not-in-sitemap, and the route is loaded over HTTP rather than the function called. SEC-2 states the "live on production from the first release" rule in plain words and requires the three tests in the same commit. AC-69 is the registry test and it fails on an unregistered function — that is the structural mechanism, and it is the right shape. AC-40 (the route as six personas), AC-65 (`no_cache`, sitemap) and AC-66 (404 and no tracked file names it) are all present. |
| **M3** | The leaver fix inside the two helpers this slice touches | **Yes** | SEC-14 names `_search_scope` and `_pending_approvals_scope`, requires an **Active-only** Employee lookup inside them, keeps `_me()` unchanged globally, and says plainly that the wider `goals_api` fix is `ALV-87`. Abuse case A9 is written. AC-68 tests a Left manager with an enabled login and unmoved reports. The engineer's handoff note flags that this changes today's live bell and org-chart search on release, not at the swap — that is exactly right, and it is the M2 principle applied without being told. |
| **M4** | The corrections queue store-scoped, same scope as its count | **Yes as written, but the scope chosen is wrong for part of its audience — see N2** | SEC-5's attendance row requires `attendance_correction.to_review` to gain the `permitted_employees()` filter, minus the caller. AC-52 tests store HR against three corrections. The impact analysis adds `attendance_correction.py` to the claimed files. Nothing is hand-waved. The problem is the scope itself, not whether it was applied. |
| **M5** | Every count part names its scope helper; count equals the list it links to | **Yes, with a cap problem — see N3** | SEC-5 is now a six-row table and every part names its helper by path. AC-51 requires count-equals-list per part **and** per persona, requires fixtures made through the endpoint a real user uses, and covers the three pending states. The PP Jewellers real-data check before the swap survives into `01c` and must go in the implementation notes. |
| **M6** | Resolve the language write | **Yes — resolved the way I recommended** | SEC-9: `set_my_language` is **not built in Wave 1**. No frame code writes a `User` record. "Offered language" is defined as enabled **and** translated, which is English only. AC-49 tests that no frame module writes `User`. AC-18 tests the offered list on a site with 17 enabled languages. The rules for a later wave (POST, no user argument, save through the document, one declared `ignore_permissions`, never `frappe.db.set_value`) are written down where the next wave will find them. |
| **M7** | SEC-6's test must be one that exists | **Yes** | SEC-6 now requires a test that reads `frame_api.py` and `inbox_api.py` and counts `ignore_permissions`, which is buildable today. The repo-wide counter is named as R4, owned by me, and explicitly **not claimed by this slice**. AC-71 traces it. That is the honest version. (The number quoted beside it is wrong — N7.) |
| **M8** | Nothing leaks between tenants | **Yes** | SEC-15 bans module-level caches and mutable globals, names `frappe.cache()` (per site) and `frappe.local` (per request, keyed by user), and AC-70 is a static check. The blast-radius line is in the threat model as point 5 and names the cross-tenant case as the worst. |

## 2 · The ten should-changes

| # | Closed? | Where |
|---|---|---|
| **S1** — escaping in the browser, not only Jinja | **Yes** | SEC-10 bans `innerHTML` with API data in `templates/includes/ess/frame/`, requires `textContent` or one shared helper, and a scan script. AC-58 is the DOM test with the `<img src=x onerror=alert(1)>` designation in three places. Abuse case A8 added. |
| **S2** — PRIV-2 pins Active only | **Yes** | PRIV-2 says Active only and names Left, Inactive and Suspended. AC-56 tests the payload keys, not the screen, with one of each status in the fixture. |
| **S3** — escape wildcards, and say what is true | **Yes** | PRIV-3 escapes `%` and `_`, states the two-letter minimum, the frame's 12 and the server's 50. The untrue "nobody pages through a staff list" sentence is gone. AC-57 and AC-28 test it. |
| **S4** — say what the bell shows | **Yes** | PRIV-4: numbers only; the frame never calls `get_pending_approvals` on boot, with the reason (names, notes, evidence; about 15,000 queries). AC-55 tests that no boot path calls it. |
| **S5** — PRIV-5 automated, and no search term in a URL | **Yes** | PRIV-5 requires the automated log-capture test and pins POST bodies with the reason (the web server logs URLs). AC-59 covers a normal call and a refused one. |
| **S6** — reuse the definition, do not copy it | **Yes, and it needs one guard — see N1** | SEC-4 requires a new `access.permitted_employee_filters(user)` that both `permitted_employees()` and `_search_scope` use. |
| **S7** — SEC-3 states the union | **Yes** | SEC-3 states `permitted_employees()` Active, minus the caller, **plus** the caller's own Active direct reports, with the reason (a store HR person keeps a report in another store). AC-50 tests exactly that person. |
| **S8** — the two missing threat-model lines | **Yes** | Threat-model points 5 and 6. Point 6 says in bold that **a successful over-read leaves no signal**, names R3, and says the tests are the only defence. It did not get softened. |
| **S9** — abuse cases A9 and A10 | **Yes** | Both written. A10 is honest that the user's confirmation on real data is still outstanding rather than assuming it. |
| **S10** — obligations carry dates | **Yes** | The obligations table carries "verified 24 Aug 2026" per row and the May 2027 DPDP phase with its ⚠. Checked against the baseline today: 24 Aug 2026 is 29 days old, **not stale** (the 90-day line falls on 22 Nov 2026). The baseline itself is still Version 0.1 DRAFT and still needs counsel — unchanged, and not this slice's problem. |

**Nothing was declined, and nothing was quietly narrowed.** I looked specifically for a
fail-closed rule turned into a warning: there is none. The two places revision 2 could
have softened — SEC-14 (Active-only, which changes live behaviour on release) and SEC-2
(endpoints safe from day one) — both got **stronger** wording than I asked for.

---

## 3 · What must change before code is written

### N1 — `permitted_employee_filters()` must fail closed by returning a refusal, not an empty filter set. **Must fix.**

`permitted_employees()` (`hrms/hrms/alvoraa_hr_core/access.py:237-267`) fails closed by
returning an **empty set** for anyone who is not HR, System Manager or Administrator. A
filter-shaped version cannot do that. The natural implementation builds
`{"company": ["in", companies], "branch": ["in", branches]}` and, for a non-HR caller,
returns `{}` — and in Frappe an empty filter dict means **everybody**. A fail-closed
helper becomes a fail-open one, inside `access.py`, the file every app reads.

*Scenario:* a plain employee's search request reaches the HR branch of `_search_scope`
through any later refactor, `permitted_employee_filters()` returns `{}`, and the search
returns every Active person in the tenant.

**Add to SEC-4:** the helper returns an explicit "no access" result for a caller with no
HR entitlement — a sentinel the caller must handle, or filters that match nothing
(`{"name": ["in", []]}`) — never an empty or partial dict. **Test:** called as a plain
employee, as a manager and as a Vendor User, the helper produces a query that returns
zero rows; and a test asserts the return value is never an empty dict.

### N2 — the corrections queue is not an HR-only queue, and `permitted_employees()` empties it for everyone else. **Must fix.**

`_may_review()` (`alvoraa_portal/alvoraa_portal/attendance_correction.py:240-248`) does
**not** check an HR role. It returns `frappe.has_permission("Attendance Request",
"submit")` — deliberately, and its docstring explains why. `02` §5 says the same: the
audience is "whoever may submit one". But `permitted_employees()` returns the **empty
set** for a caller who is not HR, System Manager or Administrator.

*Scenario:* a tenant grants submit on Attendance Request to a Shift Supervisor role.
Today that person reviews corrections. The moment decision 5's filter ships, their queue
is empty and nothing tells them why. The new Inbox count agrees with the empty list, so
the count-matches-list test passes while a working flow is dead.

This fails closed, so it is not a leak. It is a functional break of exactly the kind that
gets repaired under time pressure by loosening the filter — which is how the leak comes
back.

**Decide before code, and write the answer into SEC-5 and AC-52:**

- **(a) Recommended.** The `permitted_employees()` filter applies **only when the caller
  is HR** (the same role test `permitted_employees` uses internally). A non-HR reviewer's
  queue stays scoped by Frappe's own permissions as today — unchanged by this slice, and
  recorded as a known gap rather than silently altered.
- **(b)** Narrow `_may_review()` to HR as well, so audience and scope match. A bigger
  change, outside what `00` claims, and it removes a capability some tenant may rely on.

**Either way AC-52 needs a fourth case:** a non-HR user who holds submit permission on
Attendance Request, with the expected result stated.

### N3 — count-matches-list needs a rule for a capped list. **Must fix, one sentence.**

`to_review(limit=50)` (`attendance_correction.py:722-739`) reads at most 50 rows by
creation date **and then** drops the ones that are not in the `waiting` state, in Python.
So the list is capped, and it is filtered after the cap. A count built as a query is not.

*Scenario:* company-wide HR on a busy tenant has 60 waiting corrections. The bell says
60, the screen shows at most 50, and some of those 50 are dropped by the state filter, so
the screen may show 41. AC-51 as written ("the count equals the number of rows on the
screen") is then false in production while passing on a small fixture.

**Add to SEC-5 and AC-51:** where a list is capped, the count is capped and shown the same
way (for example `50+`), or the count uses the same post-filter the list uses. **Test at
the boundary:** a fixture with one more item than the cap.

### N4 — the decisions that close five of the eight items are not written down anywhere. **Must fix before code.**

`01c` and `02` close M4, M6, M3, S7 and R1 by citing "decision 4", "decision 5",
"decision 6", "decision 7" and "decision 8" of a 22 September review-decision set. `02`
§17 calls it "22 Sep review decisions 1–12". **That list does not exist in any file.** The
one decisions file in the tree, `../009-ess-portal-redesign/00f-decisions-2026-09-22.md`,
holds a **different** set: its decision 3 is "the preview page is open to System Manager
only" and its decision 4 is "the swap does not reach production in go-live week".

So two different decision sets are both cited as "decision 3" and "decision 4" in the same
documents, and the one relied on for the security changes cannot be read. This also
weakens R5: its acceptance rests on "decision 3", and there is no way to check which
decision 3 is meant or what it actually said.

**Fix:** write the twelve decisions of 22 September into a dated file in this slice, with
the decision text as agreed, and cite it by filename. Five minutes of work. Without it
nobody can reconstruct, a year from now, why `to_review` was scoped or why
`set_my_language` was dropped — and a grievance is the only time anyone reads this.

---

## 4 · Smaller notes (not blocking)

| # | Note |
|---|---|
| **N5** | **PRIV-7's table does not exist.** PRIV-7 requires "a table listing each thing the frame shows, per persona, and where that person can see it today"; `02` §17 traces PRIV-7 to "the table in `01c` PRIV-7". That is circular — `01c` requires the table, it does not contain it. PRIV-7 is therefore still not testable, for the same reason it was not testable in revision 1. Write the table before the review, not before the build. |
| **N6** | **`02` §17's SEC-2 row is wrong.** It reads "AC-69, plus the Guest and wrong-persona cases inside AC-8, AC-21, AC-26". None of those three ACs mentions Guest; AC-8 is about role, feature and switch-target values. The real mechanism is AC-69's registry, which does require a Guest-refused case per function. Correct the row, or add a plain AC: every whitelisted function in `frame_api.py` and `inbox_api.py` refuses Guest. |
| **N7** | **The "267 uses" figure in SEC-6 is not reproducible.** In this worktree today: 927 occurrences of `ignore_permissions` in `.py` files, 473 once paths containing `test` are excluded. My own 267 in the first review used a narrower basis, and I should not have quoted a bare number either. The requirement does not depend on the figure — delete it, and let the B4 script establish the baseline when it is built. |
| **N8** | The SEC numbering skips **SEC-13**. Harmless, but a reader will look for it. Say "there is no SEC-13" or renumber. |
| **N9** | `permitted_branches()` (`access.py:217-234`) still reads `applicable_for in (None, "", "Employee")`, which is the R6 fail-open. Unchanged, correctly recorded, not this slice's job. |

---

## 5 · Residual risks: recommended owners and dates

These are recommendations for the user to accept or change. **None of them is accepted by
me.** An accepted risk with a name and a date is governance; an unnamed one is an accident
waiting for an owner.

| # | Risk | Recommended owner | Recommended date | Why that date |
|---|---|---|---|---|
| **R3** | A successful over-read leaves no signal. Nobody reads the security log and nothing alerts on it. `access.log_refusal` records only refusals | **Security & privacy engineer** (me), with the **DevOps engineer** for delivery | **Step 1 by 2026-10-15; the detection slice by 2026-11-30** | Step 1 is small and worth doing first: log a structured event whenever an HR-scoped read runs company-wide (no Branch permission), and whenever the returned set is larger than a threshold, then a weekly digest to one named person. That much is a day's work and gives the first signal we have ever had. The full slice — alerting, retention, a place to look — waits until after DTC's go-live in the first week of October, because nothing should compete with that. This is feature map **I3/I4** territory and has no owner today |
| **R4** | No repo-wide `ignore_permissions` counter in CI | **Security & privacy engineer** (me) — it is feature map **B4**, P0, and it is mine | **Baseline script by 2026-10-31; the blocking gate on the next commit after that** | The gate must exist before Wave 2 adds more endpoints, or the count only ever rises. The baseline is whatever the script measures on the day — not the numbers quoted in either review (N7). Two steps: a script that counts and writes the baseline, then a CI job that fails on an increase. Until it exists, SEC-6's file-scoped test is the only thing holding, and it holds two files |
| **R6** | A store HR person whose Branch permission applies to only some record types is treated as company-wide (`access.py:233`) — it fails open | **Two owners, because it is two jobs.** The **live-tenant check**: Surbhi, or whoever administers tenant users. The **code fix**: the fullstack engineer, in the ALV-86 slice | **Live-tenant check by 2026-09-30; code fix by 2026-11-15, with ALV-86** | The check comes first and is cheap: list the Branch User Permissions on `dtc`, `aahr` and PP Jewellers and look at `applicable_for`. If none is narrowed to a single doctype, the risk is theoretical today and the code fix can ride with ALV-86. If any is, it is live now and a store HR person is reading the whole company — that changes the priority immediately, and it is worth knowing before DTC goes live. The fix itself is to fail closed: a Branch permission narrowed to any doctype still narrows the person |

### R5 — a tenant System Manager seeing unfinished screens with real data

**Plainly: yes, this is acceptable — but not in the shape currently specified, and the
reason it is acceptable is narrower than the documents imply.**

Why it is acceptable: the preview page shows that person's **own** permitted data. A
tenant System Manager already sees everything in the desk. The preview widens no
visibility; it only shows half-built screens. The privacy exposure is close to zero. The
real cost is reputational and operational — a customer's admin finds a broken screen and
loses confidence, or raises a ticket about a bug we already know about.

Two things make it more than zero, and neither is in the documents:

1. **A support engineer is not the same actor as a tenant System Manager.** A10 puts them
   in one row. If our support people hold System Manager on a customer tenant, then
   "System Manager only" also means our own staff, viewing a customer's live data on a
   page with no audit entry and no reason recorded. That is break-glass access without the
   break-glass (feature map B series, not built). It is worth one sentence saying whether
   our staff hold System Manager on customer tenants.
2. **Any endpoint the preview page calls is open to every logged-in user anyway.** SEC-2
   already says this, correctly. R5 must not be read as covering the endpoints — it covers
   the **page** only.

**The safest version, in order of preference:**

1. **Best — the preview page never exists on production.** Gate it on the site as well as
   the role: it renders only when `frappe.conf` carries an explicit `portal_preview: 1`,
   set on the dev stack and the local bench and never on production. Then decision 3's
   role check is a second lock, not the only one. This is a handful of lines in
   `get_context`, it is testable (AC-40 gains a "flag off → 404" case), and it removes the
   risk instead of accepting it. **This is what I recommend.**
2. If the page must be reachable on production, keep everything in SEC-1 and add a visible
   banner saying the page is unfinished and not for use, plus a log line recording who
   opened it and when. That gives the one thing R5 has none of today: a record that it
   happened.
3. The current shape — a role check only — accepted by name and date, with the
   confirmation on real data that open question 3 is waiting for.

Option 1 costs less than the conversation about options 2 and 3.

---

## 6 · What I could not check

- **Production.** By rule. So R6's live-tenant question — which Branch permissions exist
  on `dtc` and `aahr`, and what `applicable_for` holds — is still open, and it is the one
  question that would change R6's priority.
- **Whether our support staff hold System Manager on customer tenants** (R5, point 1). A
  question for the user, not something I can read out of the code.
- **The 22 September decision list** (N4) — it is not in the repository.
- **Nothing was run.** No bench, no server, no tests, no push. This is a reading of the
  code in the worktree and of the three revised documents.

I am not a lawyer. Nothing in this slice engages counsel's retention rules or the rules on
automated decisions — the frame stores nothing and decides nothing — and that reading is
unchanged from the first review.

---

## 7 · Verdict

**Closed with notes.** M1–M8 and S1–S10 are all genuinely closed. Revision 2 is honest
work: it declined nothing, it strengthened two items beyond what was asked, and where it
could not close something — the repo-wide counter, the user's confirmation on R5 — it said
so instead of hiding it.

### Must change before code is written

| # | Change | Whose |
|---|---|---|
| **N1** | `permitted_employee_filters()` returns an explicit refusal for a non-HR caller, never an empty filter dict. Add it to SEC-4, with the test | Engineer in `01c`; analyst adds the AC |
| **N2** | Decide the corrections-queue audience — recommendation (a): the `permitted_employees()` filter applies only to HR callers. Write it into SEC-5 and add the non-HR reviewer case to AC-52 | **User decides**, then engineer and analyst |
| **N4** | Write the 22 September decision list into a dated file in this slice and cite it by filename | Engineer |

### Should change before code, cheap

| # | Change |
|---|---|
| **N3** | One sentence in SEC-5 and AC-51 on how a capped list and its count agree, with a boundary test |
| **N6** | Correct `02` §17's SEC-2 row, or add a plain "every new endpoint refuses Guest" AC |
| **N7** | Remove the "267 uses" figure from SEC-6 |

### Before the swap, not before the build

| # | Change |
|---|---|
| **N5** | Write PRIV-7's actual table |
| **R5** | Take option 1 — gate the preview page on a site flag, so it never exists on production |

### For the user to settle

| # | |
|---|---|
| R3, R4, R6 | Accept the owners and dates in §5, or change them |
| R5 | Confirm decision 3 covers real data, or take option 1 and make the question moot |
| N2 | Choose (a) or (b) |
| R5, point 1 | Do our support staff hold System Manager on customer tenants? |

**No Blocker. The slice is not blocked from going to build once N1, N2 and N4 are written
into `01c` and `02`.**
