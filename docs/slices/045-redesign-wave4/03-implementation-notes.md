---
slice: 045-redesign-wave4
artifact: 03-implementation-notes
author: hrms-fullstack-engineer
date: 2026-09-24
status: partial — the server side of the defect fixes, the decision capacity, the Team
  two-section matrix, the Growth data model and the directory are built and tested
  locally. The screens are NOT built. Local only: not pushed, not merged into `dev`,
  no server, no production, no `docker cp`.
bench: own container `hrlocal-045`, own site `test045`, bind-mounted apps from this
  worktree. `hrlocal-bench` not used. Measurement sites `test044` / `test044s` mounted
  read-only in intent and not rebuilt.
---

# Wave 4 — what was built, and what it really proves

## 1. Bad news first

**Three things you should know before the good parts.**

1. **The screens are not built.** This is server side, the data model and the tests.
   Growth, Team and People still draw from the old panels. Surbhi's answer 3 said the
   wizard's look waits for a short design pass; the rest of the screens are simply not
   done yet in this session.
2. **`get_manager_dashboard` still sends an `IN (...)` of the drawn ids** for
   "on leave today". The raw SQL is gone and both privacy fields are gone, but the id
   list is not, and AC-14 asks for a subquery. That is a **declared trade-off** with a
   reason (section 5), not an oversight — and the function is replaced by `team_api`
   anyway.
3. ~~**`test044` and `test044s` measurements have not been taken yet.** The flatness gate
   is not proved.~~ **Closed 2026-09-24 by the test engineer — see section 11. Flatness
   holds: `get_team` costs the same at 20 people and at 981, for every persona.** The
   rest of this document below was run on `test045`, my own site.

## 2. What was built, file by file

| File | Mechanism | Why |
|---|---|---|
| `hr_api.py` — `me_block()` | **extend** | The six-key caller block, reusing `frame_api.ME_FIELDS` rather than re-typing the names. One list, so the two cannot drift |
| `hr_api.py` — `direct_reports_query()` | **extend** | "Your own Active direct reports" **as a subquery**, failing closed on no employee id |
| `hr_api.py` — `_pending_leave_for_approver()` | **build** | Two reads. The difference between them is the whole of AC-76 |
| `hr_api.py` — `get_manager_dashboard` | **extend** | `"manager": emp` → `"me"`; `leave_type` dropped; month overlap fixed; `l2_reports` / `l2_size` deleted |
| `hr_api.py` — `get_team_scorecard` | **extend** | Scope as a subquery, the privacy filter moved into the `WHERE`, the unbounded `ORDER BY` replaced by a correlated `MAX(creation)` |
| `team_api.py` | **build** | New. Two sections, the eleven-row matrix, the derivation |
| `growth_api.py` | **build** | New. The byte ceiling, whole-point ratings, all company values |
| `performance_api.py` — `save_review_page` | **extend** | The byte budget, checked before the write |
| `attendance_correction.py` | **extend** | `alvoraa_decided_as`, the guarded stamp, the two-working-day window, `request_fields()` |
| `staff_api.py` | **extend** | One field: `company_email as work_email` |
| `tests/fixtures_045.py` + six `test_*_045.py` | **build** | Wave 4's own company, branches, people and **roles** |

## 3. Surbhi's five answers — what each became

| # | Answer | What shipped |
|---|---|---|
| 1 | Self-review rates **goals**, whole points | `growth_api.check_whole_point` — integer, 1–5, validated **on the server**. A half-point is refused with "Ratings are whole points — please pick 3, not 3.5" |
| 2 | **All** company values | `growth_api.company_values_for` reads every **active** `Company Value` for the employee's company, plus tenant-wide ones. **The fixture uses seven, not five**, so an implementation that assumed five fails. A static check bans `[:5]` and `range(5)` in the module |
| 3 | Design pass on the wizard only | Server side, data model and tests built. **What the design pass could still change:** the step order, the rating control's look, and how a long value list is laid out on a phone. **What it cannot change without a new decision:** the byte budget, the whole-point rule, and that every value is rated |
| 4 | Directory for employees, work contact in | **`company_email` only.** See section 4 — this is the one I had to stop on |
| 5 | HR sees from day one, acts from day three | `hr_may_act_from()` counts two working days on the **requester's own** holiday list. `decided_as()` derives the capacity server side. This closes **D-12** |

## 4. The one thing I stopped on

**There is no work phone or extension field in the data model.** Read from the installed
ERPNext source, not assumed:

| Field | Label | Verdict |
|---|---|---|
| `company_email` | Company Email | **work — shipped** |
| `cell_number` | **Mobile** | personal — not shipped |
| `personal_email` | Personal Email | personal — not shipped |
| `emergency_phone_number` | Emergency Phone | **somebody else's number entirely** — not shipped |

Her instruction had a stop condition for exactly this: *"If the data model has only a
personal mobile field, say so and stop rather than shipping a personal number."*
**So no phone number ships.** The directory is work email, name, title, department and
photo. Adding a work-phone custom field is a small change plus a way to populate it, and
it needs her word.

**And the NDA point, written down as she asked.** An NDA binds **the employee who looks**.
It is not the same as the employer's own duty to the person whose data it is. A colleague
promising not to share a home address does not make collecting and showing it
proportionate. Keeping the directory to work contact is what makes the wider audience safe.

### 4a. The other half of decision 4 is NOT built, and it needs her word too

Her decision had two halves. **The field half is done; the audience half is not.**

**Today `get_staff_list` refuses any caller with no HR entitlement.**
`permitted_employee_filters()` returns `NO_EMPLOYEES` for a plain employee and the
endpoint refuses before it reads anything. So the directory is HR-only, and adding
`work_email` to it does not change who can open it.

**Why I did not just widen it.** Opening the audience needs a scope, and the scope is the
decision: **does a shop assistant see their own store, or their whole company?** Those
are two very different directories. Store HR is narrowed to their branches today
(`permitted_branches`), so "their own store" has a precedent; "their whole company" is
what "a staff directory" usually means. Guessing would **widen visibility as a side
effect**, which is the one thing this wave is not allowed to do.

**It is pinned rather than left silent.**
`test_a_plain_employee_still_cannot_open_the_directory_at_all` asserts today's refusal,
and its docstring says it is expected to be **replaced** by a test of the new scope once
Surbhi decides — not deleted.

**My recommendation, if she wants one:** own company, **not** own store. A directory
whose point is "find and contact a colleague" is not much use if it stops at your own
shop floor, and the fields on it are already limited to what is safe to show widely.
That is a recommendation, not a decision I have taken.

## 5. What the five defect fixes actually did

| Fix | Before | After | Honest note |
|---|---|---|---|
| **AC-6** the whole Employee row | `"manager": emp` — twelve fields including date of birth, gender, mobile, branch | `"me": me_block(emp)` — six, from `ME_FIELDS` | **Nothing read `d.manager`.** The only caller is `portal.js:3474`, checked by hand. A leak nobody used is a leak nobody noticed |
| **AC-76** leave type and reason | `leave_type` selected in two places, `description` carried in a third | Both gone from every card, chip and count; both on **one** row — the approval row for a direct report | Two reads, not one read and a blank-out. The fields must be absent from the `fields` list |
| **AC-21** the month filter | `from_date >= mo_start` | overlap: `from_date <= month_end AND to_date >= month_start` | Wrong since it was written. Missed leave that began last month and included next month's |
| **AC-14** the banned shape | two raw-SQL statements with one bound parameter per person | scorecard: subquery + filter in SQL + bounded. `on_leave_today`: raw SQL gone | **`on_leave_today` still uses an id list.** Declared, see below |
| **AC-16** the dead fields | `l2_reports`, `l2_size` in the payload | gone | Only reader anywhere was Wave 1's own test asserting they were empty |

**The declared trade-off on `on_leave_today`.** AC-14 asks for a subquery. This read must
match the list the screen **draws**, which is capped at 50 — a subquery over the caller's
whole scope would count people who are not on the page, and a number that does not equal
the list beside it is the fault AC-12 exists to stop. MariaDB's support for `LIMIT` inside
`IN (SELECT ...)` is not something to build a privacy-relevant read on. The list is
bounded at 50 by construction, so the ×5 slope cannot appear. **AC-14's subquery lands
with `team_api`**, where each section is its own scope with its own count.

## 6. The two things OPS-W4 flagged

### The migration

| | What happens |
|---|---|
| Deploy **with** migrations | The field appears; `decide()` stamps `Manager` or `HR` |
| Deploy **without** migrations | **The approval still works.** `_decided_as_is_storable()` guards the write and `request_fields()` guards the read. Only the capacity is lost, read afterwards as "not recorded" |
| Rollback | The Python goes back, the **column stays** — a revert does not drop a column and should not. Read-only and unused by the old code, so inert |
| Rollback after data exists | Stored capacities survive and become readable the moment the code returns |

**Why both a read guard and a write guard.** The write guard alone is not enough: a
`fields` list naming a missing column makes the **read** fail, so every screen listing
corrections would go blank rather than just losing a label. That is asserted by
`test_the_read_survives_a_site_without_the_column`, which patches `has_column` to False.

### The `page_data` ceiling — **it throws, it does not truncate**

Measured on `hrlocal-045` against the real column.

| Fact | Measured |
|---|---|
| Column | `text`, **`CHARACTER_OCTET_LENGTH` 65535** — bytes, not characters |
| `sql_mode` | `STRICT_TRANS_TABLES,…`, identical at `@@GLOBAL` and `@@SESSION` — MariaDB's own default, not Frappe's |
| 21,845 Devanagari characters (65,535 bytes) | **stored whole — the exact boundary** |
| 21,846 characters (65,538 bytes) | **raises `DataError (1406, "Data too long for column 'page_data' at row 1")`** |

**So there is no silent truncation to fear. There is an autosave that fails while
somebody keeps typing.** That is why the budget is checked before the write, in **bytes**,
with a sentence that says what to do and confirms nothing already saved was lost.

**A Devanagari answer gets one third the characters of an English one for the same
budget.** A test proves that directly: the same character count passes in English and is
refused in Devanagari. A character-count budget would have passed every English test in
the suite and failed the first employee who wrote in Hindi.

**Caveat:** this is my bench's MariaDB. Production runs the same `mariadb:10.8` image, so
it should behave the same — confirming the production server's `sql_mode` is the DevOps
engineer's check, not a claim I can make.

## 7. The Team screen — two sections and eleven rows

`team_api.get_team()` returns **one** payload with **two** sections, each carrying its own
`total`, `capped` and `cap`. **There is no combined total anywhere**, and a test asserts it
by arithmetic rather than by naming keys: no integer in the payload equals
`direct + covered`.

**The section is derived, never declared.** `relationship()` asks the database at the
moment the question is asked. A test passes `section` and `basis` in the form dict anyway
and asserts the answer does not move; another moves a person's `reports_to` and asserts
they change sections, which is what proves the derivation is real rather than a constant.

**`allowed()` is the only place the matrix is read.** The payload builder and the by-hand
permission check both call it, so a screen and a server cannot disagree about a row. The
matrix is **data, not branching**, so a test can walk all eleven rows one at a time —
eleven UI rows are eleven server checks, and a matrix is the shape where one row gets
missed.

**The both-person** appears once, under "Your team", with the manager actions **plus** the
HR-only ones. Being somebody's manager does not take an HR caller's HR entitlements away;
it decides which section the row is in.

**One N+1 avoided on purpose:** the obvious way to mark the both-people is a
`relationship()` call inside the row loop. It is one query for the whole section instead,
over the drawn names, which are capped at fifty by construction.

## 7a. What the tests found, by going red first

**Ten things, and three of them were defects in the code rather than in the
fixture.** Every one was found by an assertion failing, not by reading.

| # | Found by | What it was |
|---|---|---|
| 1 | `4 != 9` on a store HR caller's section | **`frappe.db.count` and `frappe.get_all` disagree about NULL.** `frappe.db.count` goes through Frappe's newer query engine and `get_all` through the legacy `db_query`; legacy wraps a `!=` in `ifnull(field, '')`, the newer one does not. So `reports_to != me` kept a NULL row in the **list** and dropped it from the **count**. Measured: the list drew **9** people and the count said **4**, because five of the nine have no manager recorded — the ordinary state of most people in a shop. **The screen would have read "You cover (4)" above nine cards.** Fixed by taking the total through `get_all` too, so the filter semantics are identical by construction |
| 2 | Reviewing `decided_as` before shipping it | **A near-regression against W1D-14.** The first version returned `"HR"` for anybody who was not the manager. A Shift Supervisor a tenant has given the submit permission to holds no HR entitlement — labelling them "HR" would have written a false claim into an audit field **and** put them behind the two-working-day wait, silently killing a flow that works today. They now get `None`, which reads as "not recorded". Pinned by a test |
| 3 | `OK (skipped=1)` | **A test that skipped the only assertion it existed for**, and reported it as a pass. The directory test skipped itself when the `staff_list` feature was off. It now turns the feature on. A skip that appears in the count is worse than no test |
| 4 | `'leave_type' unexpectedly found` | **My own static check was wrong, not the code.** It read the raw source and went red on the *comment* explaining why the field was removed — a test failing because the code was documented. It now strips comments and docstrings, and a second test proves the stripper strips |
| 5 | `InvalidPhoneNumberError` | Frappe validates the phone format, so the distinctive fixture mobile had to become a real-shaped number |
| 6 | `holds roles this fixture did not give it: {'Desk User'}` | My own roles guard fired on a role **Frappe adds itself** to every System User. Narrowed to the framework's three |
| 7 | `TimestampMismatchError` ×4, and `No Holiday List was found` ×12 | Two fixture facts about this Frappe HR version: creating an Employee with a `user_id` **saves that User** (`employee.update_user:212`), so a cached copy goes stale; and holidays resolve through a **submitted `Holiday List Assignment`**, not the old `Employee.holiday_list` field |
| 8 | `AssertionError: 0 is not true : no whitelisted endpoints were discovered at all, so this test proves nothing` | **My Guest-and-persona suite was looping over an empty list and passing.** `whitelisted_in()` looked for a `whitelisted` attribute on the function; Frappe's register is `frappe.whitelisted` and membership is by the **function object**. So every Guest check was green over nothing. **Caught by the test I wrote to check the check** — `test_the_discovery_itself_finds_the_endpoints_we_know_about` — which is the entire reason that test exists |
| 9 | `PermissionError: You do not review attendance corrections.` ×3 | `_may_review()` is `frappe.has_permission(REQUEST, "submit")`, and on a clean site the plain `Employee` role does not hold it — so the fixture's manager could not decide anything. Fixed with a role the **fixture owns** (`S045 Correction Reviewer`) rather than by giving `Employee` submit site-wide, which would have changed every other suite's permissions |
| 10 | `Assignment start date cannot be outside holiday list dates` | A `Holiday List Assignment` must start inside its list's own range. Now read from the list instead of hard-coded |

**Finding 1 is the one worth carrying forward, and I checked how far it reaches.**
The trap is: a `frappe.db.count` paired with a `frappe.get_all` over the same filters,
where one filter is a `!=` on a **nullable** field. Then the number and the list
disagree, and Surbhi's standing rule is broken by a framework difference nobody would
think to look for.

**I swept for it and it is not live anywhere else today.** Every other
`frappe.db.count` in `alvoraa_portal`, `alvoraa_goals` and our `hrms` modules filters
with `=`, `in` or `like`, and none of those three differ between the two query paths.
`staff_api.get_staff_list` is the closest call — it pairs a count with a list over one
filter dict — and it is safe for that reason. **So this is a trap, not a live defect
elsewhere.** It is written down here because the next person to add a `!=` beside a
count will not find it by reading.

## 8. Non-functional re-assessment — against the code actually written

| Dimension | Verdict | Against the code |
|---|---|---|
| Performance | **improves** | Two banned raw-SQL shapes gone; the scorecard's unbounded `ORDER BY` bounded; the privacy filter moved into the `WHERE` so unreleased ratings are never fetched. **Not yet measured on `test044`** — the flatness gate is unproven |
| Security | **improves** | A live leak closed; eleven rows enforced server side and callable by hand; the section derived; the capacity derived; Guest and wrong-persona tests on both new endpoints |
| Reliability | **improves** | The migration risk is handled at the read **and** the write. The holiday-list read fails soft and says which basis it used |
| Scalability | **improves, partly unproven** | Subqueries where it matters; both sections capped with their own totals. The 981-person measurement is not done |
| Maintainability | **improves** | One filter builder, one matrix, one capacity derivation, two dead fields gone. Two new modules is the cost |
| Data integrity | **neutral** | No backfill, no default. Empty means "not recorded" |
| Compliance / privacy | **improves** | Both leave fields dropped at the SQL; the directory is work contact only; no refusal carries a name or a number, asserted |

## 8a. Commands run, and what they really said

Every run is on my own container `hrlocal-045`, my own site `test045`, with the
apps bind-mounted from this worktree. `hrlocal-bench` was not used and no
`docker cp` was run.

| Command | Result |
|---|---|
| `git rebase slice/043-redesign-wave3` | clean, 7 document commits replayed, no conflict |
| `docker run` + `bench new-site test045` (first attempt) | **failed**: `OSError: [Errno 12] Cannot allocate memory` part-way through installing hrms, leaving a half-built site whose next install failed on `Duplicate entry 'HR' for key 'PRIMARY'`. Dropped and rebuilt, installing **one app at a time** |
| `bench new-site test045` + four `install-app` | frappe 16.33.1, erpnext 16.34.2, hrms 17.0.0-dev, alvoraa_goals, alvoraa_portal |
| `python scripts/check_app_integrity.py` | **643 checks, OK** — run before every commit |
| `bench run-tests --module ...test_growth_045` | **17 ran, OK** (after 3 errors from an invalid fixture phone number and my own roles guard firing on `Desk User`) |
| `bench run-tests --module ...test_team_payload_045` | **6 ran, OK** |
| `bench run-tests --module ...test_leave_privacy_045` | **11 ran, OK** (after 1 failure and 8 errors: my own static check matching its own comment, and a fixture with no Leave Allocation) |
| `bench run-tests --module ...test_team_sections_045` | **20 ran, OK** (after 2 real defects — the count/list disagreement — plus a `NameError` I introduced with a careless `sed`, and two fixture facts about this Frappe version) |
| `bench run-tests --module ...test_staff_list_034` (Wave 1's, with the updated pin) | **9 + 22 ran, OK** |
| `bench run-tests --module ...test_team_scope_034` (Wave 1's) | **19 ran, 2 errors** — both read `d["manager"]["name"]`, the key AC-6 renamed. **The pin doing its job.** Updated to `d["me"]["employee"]` with the reason in the test; re-run pending |
| the `page_data` probe, on the real column | ceiling is **bytes**; 21,845 Devanagari characters fit, 21,846 raises `DataError 1406`; `sql_mode` strict at `@@GLOBAL` and `@@SESSION` |

**Three modules were still running when these notes were written** —
`test_decided_as_045`, `test_endpoint_guards_045`, `test_directory_contact_045`,
and the `test_team_scope_034` re-run. Their numbers are in the hand-off report,
not guessed here.

**One process mistake worth recording, because it wasted an hour.** I twice
concluded a test run was hung when it was only slow, and once killed a module
that was about to finish. The tell I should have used first is whether CPU time
is climbing **and** SQL is flowing — a run with rising CPU and live statements is
working, however long it has been. Killing it cost a full re-run.

## 9. What I could not prove

- ~~**The flatness gate.**~~ **Done — section 11.** Measured on `test044` (981) and
  `test044s` (20), both twice. Flatness holds. What is still **not** proved there:
  `get_growth`, because there is no such endpoint yet (§11.4), and `get_inbox`, whose
  count is data-dependent rather than flat (§11.5).
- **The screens.** Nothing in Growth, Team or People is drawn differently yet, so nothing
  here has been seen by a person in a browser.
- **`hrms`'s own tests.** Not run — `attendance_correction.py` lives in `alvoraa_portal`,
  so the portal suite covers it, but the wider hrms suite was not exercised.
- **Production's `sql_mode`.** Same image, so probably the same; not my claim to make.

## 10. Known gaps, each labelled

| Gap | Label |
|---|---|
| `on_leave_today` keeps an id list instead of a subquery | **intentional trade-off** — the count must equal the drawn list; `team_api` supersedes the function |
| The screens are not built | **temporary debt** — removed by the screen work, with the wizard waiting on the design pass |
| ~~No `test044` measurement~~ | **Paid off 2026-09-24** — section 11 |
| No `get_growth` measurement, because there is no `get_growth` | **temporary debt** — removed when the Growth screen is built; §14's Growth budget stays an unmeasured number until then |
| `get_inbox`'s query count is not flat between the two sites | **not this slice's debt** — `get_inbox` is untouched by Wave 4. Logged for Wave 5, P3 (§11.5) |
| The five defect fixes land in **three** commits, not five | **acceptable simplification, and the grouping is deliberate.** AC-6 (the `me` block) and AC-16 (the dead keys) edit the **same return dict**, so they ship together — splitting them would mean writing the deleted keys back in one commit to remove them in the next. AC-76 (the leave fields), AC-21 (the month) and the raw-SQL half of AC-14 are **three lines of the same read** in one function. AC-14's scorecard half is its own commit. Each of the three is independently revertable and each intermediate state runs and passes; they were staged hunk by hunk rather than by editing the file three times |
| No work phone in the directory | **not debt — a decision waiting for Surbhi.** Shipping `cell_number` would have been the dangerous option |

---

# 11. The flatness measurement — taken 2026-09-24 (test automation)

**Section 9 said this was not proved. It is now.** Measured by the test engineer, not
the engineer who wrote the code.

**Flatness holds.** Every query count on `get_team` is **identical at 20 people and at
981**, for all five personas. `get_staff_list` is identical too. Nothing in the two new
sections grew with headcount.

## 11.1 How it was measured, and what to trust in it

| | |
|---|---|
| Harness | `alvoraa_portal.tests.measure_044.run`, slice 044's, unchanged |
| Sites | `test044` (981 Employees) and `test044s` (20 Employees), **reused, not rebuilt** — `build_first=0`, `write=0`, so neither fixture site was written to |
| Container | `hrlocal-045` (mine). `hrlocal-bench` not used. No `docker cp` |
| Method | 3 warm-up calls, then **20 measured** calls, per call per persona. Nothing written between measurements (Wave 2's method fault) |
| Commands | `bench --site test044s execute alvoraa_portal.tests.measure_044.run --kwargs "{'shape':'small','build_first':0,'write':0}"` and the same with `--site test044` / `'shape':'large'` |
| Runs | **Both sites measured twice**, in two windows |

**What is safe to quote, and what is not.**

* **Query counts and payload bytes: trust them.** Every single number reproduced
  **exactly** across both runs, on both sites, for all five personas. They are
  deterministic.
* **Wall-clock times: treat as an upper bound, not a measurement.** The machine was busy
  throughout — load average **7.1–7.8 on 8 cores**, because another session was running a
  full `alvoraa_portal` suite in `hrlocal-wa042` the whole time. The same untouched call
  moved a lot between the two runs (`storehr` `get_team` p50 went 22.5 ms → 54.9 ms at
  981 with no code change). So **the times below are worse than the real ones**, which is
  the safe direction: they pass the budget anyway, with a lot of room.

## 11.2 `get_team` — the gate

Query counts and bytes are from both runs and were identical in both. Times are shown as
run 1 / run 2.

| Persona | q @20 | q @981 | **flat?** | bytes @20 | bytes @981 | p50 @20 | p95 @20 | p50 @981 | p95 @981 |
|---|---|---|---|---|---|---|---|---|---|
| plain employee | **3** | **3** | **yes** | 320 | 320 | 4.2 / 5.8 | 5.5 / 8.3 | 16.6 / 17.7 | 28.2 / 23.6 |
| manager | **3** | **3** | **yes** | 6,243 | 6,931 | 5.4 / 6.0 | 6.2 / 9.5 | 15.1 / 33.2 | 19.1 / 47.4 |
| store HR | **6** | **6** | **yes** | 6,185 | 16,369 | 14.4 / 18.0 | 22.4 / 25.5 | 22.5 / 54.9 | 27.2 / 88.6 |
| company HR | **6** | **6** | **yes** | 6,496 | 16,543 | 14.2 / 9.6 | 23.3 / 12.2 | 26.0 / 38.4 | 30.7 / 50.6 |
| System Manager | **3** | **3** | **yes** | 320 | 320 | 5.1 / 6.0 | 7.2 / 10.6 | 11.1 / 27.7 | 18.8 / 41.8 |

**Read it this way.** A caller with an HR entitlement pays **6** queries — the two
sections asked as two scopes, each a row read plus its own total — and a caller without
one pays **3**. Forty-nine times the headcount adds **nothing**. That is the thing §14
made the gate, and it is the thing a two-list rewrite was most likely to break.

**Against §14's budgets:**

| Budget | Measured | Verdict |
|---|---|---|
| `get_team` payload ≤ **40 KB** | **16,543 bytes** worst case (company HR at 981) | **passes, 41 % of budget.** §14's "revision 2" worry about 100 rows instead of 50 was right to ask and wrong to fear |
| p95 ≤ **500 ms** | **88.6 ms** worst case, **on a machine at 95 % load** | **passes with room** |
| Two sections must stay **two constant queries, not one per person** | 6 at twenty people, 6 at 981 | **passes** |

## 11.3 `get_staff_list` — the People call

| Persona | q @20 | q @981 | bytes @20 | bytes @981 |
|---|---|---|---|---|
| plain employee | **refused** | **refused** | — | — |
| manager | **refused** | **refused** | — | — |
| store HR | **2** | **2** | 1,769 | 1,763 |
| company HR | **2** | **2** | 1,765 | 1,728 |
| System Manager | **2** | **2** | 1,765 | 1,725 |

**§14's "`get_staff_list`, which exists and costs 2 queries flat" was written before
anybody measured it. It is now measured, and it was right.** Two queries, flat, and the
payload does not grow.

The two refusals are section 4a's open decision showing up in the numbers, not a fault:
the directory is HR-only today, and a plain employee gets
`PermissionError: This page is not part of your access.` **The audience half of decision
4 is still waiting on Surbhi**, and when it is answered these two rows must be
re-measured, because widening the audience is what would change the shape.

## 11.4 `get_growth` — **not measured, because it does not exist**

§14 budgets "Calls on Growth: 1 (`get_growth`)". **There is no `get_growth`.**
`growth_api.py` exposes exactly one whitelisted endpoint, `get_company_values()`, and the
Growth screen is not built (section 1, bad news 1). So the Growth budget in §14 is still
an unmeasured number and must stay labelled as one. **It is a gap, not a pass.**

## 11.5 Everything else the harness covers, and one thing that is not flat

Measured on the way past, both runs identical.

| Call | emp | mgr | store HR | company HR | sysmgr | flat 20 → 981? |
|---|---|---|---|---|---|---|
| `get_frame` | 3 | 3 | 5 | 5 | 5 | **yes** |
| `get_nav_counts` | 13 | 13 | 21 | 21 | 16 | **yes** |
| `get_home` | 26 | 27 | 27 | 27 | 28 | **yes** |
| `get_team_scorecard` | 2 | 10 | 2 | 2 | 2 | **yes** |
| `get_time` | 35 | 35 | 36 | 35 | 32 | **yes** |
| `get_pay` | 2 | 2 | 2 | 2 | 2 | **yes** |
| **`get_inbox`** | 13 → 13 | **20 → 17** | **26 → 24** | 26 → 26 | **23 → 20** | **NO** |

**`get_inbox` is the one call whose query count is not identical between the two sites.**
Three personas move. Two things say it is not an N+1 on headcount, and one says it still
needs a look:

* It moves **downward** with 49× the people. An N+1 goes up.
* Both runs gave the same numbers on the same site, so it is the data, not noise.
* But it means `get_inbox`'s cost depends on **what is in the inbox**, so this method
  cannot prove it flat. The two fixture sites hold different numbers of open items, and
  a site with more of the right kind of item could push it the other way.

**Not Wave 4's code** — `get_inbox` is untouched by this slice. Logged as a note for
Wave 5 rather than fixed here. **P3.**

## 11.6 One thing the numbers show that is worth a sentence

**A System Manager's Team screen is empty** — 320 bytes, the same as a plain employee's,
at both sizes. That is `team_api._caller()` deciding HR entitlement as
`{"HR Manager", "HR User"} & roles`, and **System Manager is not in that set**.

It fails **closed**, so it is not a leak and not a defect. It is worth knowing because
§14 and the persona list treat System Manager as one of the five, and on the Team screen
that persona sees nothing unless the tenant also gives them an HR role. If a CXO is
expected to see a company's team, that is a product decision, not a bug — flagged, not
changed.
