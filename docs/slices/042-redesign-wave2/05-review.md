# 042 Wave 2 — senior architect review (step 5)

slice: 042-redesign-wave2 (Home and Inbox), carrying slice 044's scale fixtures
branch: `slice/042-redesign-wave2`, on top of `slice/034-redesign-wave1`
reviewer: hrms-technofunctional-reviewer
date: 2026-09-25
inputs read: `00-impact-analysis.md`, `01c`, `02` revision 2, `03-implementation-notes.md`,
`03b-implementation-notes-044-followups.md`, `07-devops-inputs.md`,
`../044-scale-fixtures/04-test-report.md`, Wave 1's `05-review.md`, and the full diff of
all 40 changed files against `slice/034-redesign-wave1`.

---

## 1. Verdict

**SHIP WITH FIXES.** The design is sound and most of it is better than the review it is
replacing: the count and the list really do come out of one filter, the scope helpers
really do fail closed, the deleted week-presence endpoint really is gone, and the query
budgets were re-measured instead of defended. **But there is one P1 that reaches every
customer's live Home page today, and it is a one-character fix.**

`SHIP WITH FIXES` means "ready to present for deploy approval once F1 is fixed and F2–F4
have your word". It is not itself permission to deploy.

**What I ran, and what I could not.**

| Ran | Result |
|---|---|
| `node scripts/run_dom_tests.js` | 4 run, 3 not run, **0 failed** (82 frame + 27 panels) |
| `python scripts/check_app_integrity.py` | 638 checks, OK |
| `python scripts/check_design_system.py` | OK |
| `python scripts/check_preview_flag.py` | OK |
| A div-balance walk of `parts/home.html`, this branch vs Wave 1 | **Wave 1: 0. This branch: −1.** See F1 |

**I could not run any `bench run-tests`** — there is no bench in this worktree. Every
Python test result below is the engineer's reported run, read from the notes, not re-run
by me. I did read the new test files line by line, which is the part that matters more.

**No P0.** I looked for a cross-tenant leak, a permission bypass and personal data in a
log or a payload, and did not find one.

---

## 2. Findings, worst first

### P1 — blocks the release

#### F1. One extra `</div>` breaks the layout of the Home page every customer uses today

**Proven, two ways.** `alvoraa_portal/alvoraa_portal/templates/includes/ess/parts/home.html:51`.
The commit that removed the week grid (`287ee08`) deleted the card's opening `<div>` and
its two inner `<div>`s but left the card's **closing** `</div>` behind.

I counted the tags with the comments stripped:

```
wave1 depth: 0      (balanced)
this branch: -1     (one closing div too many)
```

Failure scenario: any employee on any tenant opens today's portal Home →
`home-left-col` (opened at line 36) is closed at line 51 instead of line 76 → "My Goals"
and "Team Goals" fall out of the left column, and the whole right-hand column
(`home-actions-col`, approvals and holidays) falls out of `home-body-grid`. The browser's
parser will not error; it will just lay the page out wrong. Nothing in CI catches this —
the DOM tests drive the **preview** page, not `hrms-employee.html`.

This is the live page, in go-live week, on the first screen anybody sees.

**Smallest fix:** delete line 51. Then add a div-balance assertion for the tracked
`parts/*.html` files to `scripts/` — this class of mistake is invisible to every check
the repo has.

Owner: `hrms-fullstack-engineer`. **Wave 3 carries the same broken file** — fix it once,
on this branch, and let it flow.

---

### P2 — needs your decision or a written acceptance before release

#### F2. AC-19's Withdraw button does not exist, and the traceability table says "met"

**Proven.** `03-implementation-notes.md:84` records AC-19 / AC-20 as **met**, with
"plain-word state, withdraw only where allowed".

- The server does its half: `inbox_api._part_my_requests` puts `can_withdraw` on every
  row, and `next-inbox.js:72` even defines `SAY.withdraw = __("Withdraw")`.
- **Nothing draws it.** `ACTIONS` in `next-inbox.js:36-48` has entries for
  `leave_approvals` and `attendance_fixes` only, so `rowHtml` renders no buttons for
  `my_requests`. A grep for `withdraw` across every `next-*.js`, every `next/*.html` and
  every test finds exactly that one unused string.

Second half of the same AC: AC-19 asks for states "Waiting for Sakshi Verma", "Approved",
"Declined — <the reason he was given>". The part only ever returns `state: "waiting"`,
because its filters exclude anything decided. §6.2 defines part 6 as *open* requests, so
the two halves of the spec disagree — but the table records "met" for both.

Failure scenario: Rahul raises an attendance correction by mistake, opens the Inbox,
sees his row, and has no way to take it back. US-6's whole point was "so that I stop
asking HR".

**Smallest fix:** either build the button (`attendance_correction.withdraw` already
exists and `can_withdraw` is already on the row — about fifteen lines in `next-inbox.js`
plus one DOM assertion), or change the notes to say AC-19 is **partial** and say which
half shipped. What is not acceptable is a "met" with no mechanism.

Related and in the same rows: `rowHtml` at `next-inbox.js:116` falls back to
`row.kind` for the title, and a `my_requests` row carries no `employee_name` and no
`title`. So an employee's own requests are headed **`attendance_fix`** and
**`shift_request`** — raw internal keys, on screen, untranslated.

Owner: `hrms-fullstack-engineer` for the fix; `hrms-business-analyst` if AC-19's wording
should be narrowed to match §6.2 instead.

#### F3. The team goal summary is computed, is wrong, breaks the rule this slice wrote, and nothing draws it

**Proven.** `home_api.py:616-626`:

```python
names = _hr_scope() if is_hr else _reports(me["employee"])
...
total = frappe.db.count("Individual Goal", {"employee": ["in", names[:LIST_CAP]], ...})
team = {"people": len(names), "goals": total} if len(names) >= MIN_GROUP else ...
```

Three separate problems in five lines:

1. **The number is wrong.** `people` counts everybody; `goals` counts the goals of the
   first **fifty** of them. For company-wide HR on the 981-person fixture the payload
   says "981 people, N goals" where N came from 50 people. That is the exact "a heading
   said 4 over a list of nine" shape this programme has paid for four times.
2. **It breaks the rule this very slice added to `nfr-budget.md`.** `_hr_scope()` reads
   every permitted employee id into Python — 981 of them — and ships fifty back as an
   `IN (...)`. The line this branch added to the budget says: *"A cap is the wrong
   answer — it makes the number wrong instead of slow."* This is that cap.
3. **Nothing reads it.** `next-home.js:233-245` (`goals()`) draws `g.mine` only. `g.team`
   is never referenced anywhere in the panel.

So an HR Home load pays for a full scope read plus a count, to produce a wrong number
that no screen shows.

**Smallest fix: delete the `team` branch of `_goals` and `_hr_scope` with it.** That
removes the last list-of-ids from Home and takes `get_home`'s worst-case query count down
as a side effect. If a team goal summary is wanted later it is a new, specified thing.

Owner: `hrms-fullstack-engineer`. This is the most valuable deletion in the slice.

#### F4. The presence card's privacy rule is real, but the risk it leaves is recorded as "not yet accepted"

You asked me to judge two things about this card. Taking them in order:

**Are the rules real?** *Yes — proven.* `home_api._suppress` is asserted directly in
`test_home_api_042.py:371-416`, including a five-row table of cases and an assertion that
where anything is hidden at most one number survives. `_presence_counts` collapses
Attendance status into three buckets before it returns, so a leave type cannot escape
even by accident, and the payload key list `TEAM_TODAY_KEYS` does not carry the group
size. `test_no_name_no_photo_no_reason_reaches_the_payload` checks the fixture's name tag
and the words "Leave", "Absent", "Sick", "reason", "image" are absent from the serialised
card. These are mechanisms, not sentences.

**Does it hide so much the card is useless?** Not useless, but thinner than the design
imagined. Run the rule on a realistic team:

| Group | Counts | Published |
|---|---|---|
| 19 people (Sandeep's own persona) | in 15, away 2, due 2 | **"15 in" only** |
| 20 people | in 12, away 5, due 3 | **"12 in" only** |
| 6 people | in 5, away 1, due 0 | **"5 in" only** |
| 10 people, nobody away | in 10 | all three |

So on a normal day most managers see one number. That is a card, not a dashboard, and I
think it is the right trade — but it is **not** the card AC-29 (b) describes, and the
engineer says so plainly in the code.

**What actually needs your word.** The spec records this at `02-functional-spec.md:1024`
as **D-7**, with the security engineer's residual risk **R6**, and the row ends
*"Proposed for acceptance at the strategy gate, **not yet accepted**"*. It also notes the
limit of the control honestly: complementary suppression assumes the reader does not know
the group size — and a **manager knows their own team size**, so for the `team` basis the
subtraction is still available to them. For the `peers` basis it is mostly not.

Ranked P2 because it is an unaccepted residual risk on personal data, not because the
code is wrong. One line from you in the decision register closes it. If you would rather
not carry R6 at all, the alternative is to drop the card for the `team` basis and keep it
for `peers` — that is the basis the privacy rule was written for.

Owner: you, with `hrms-security-privacy-engineer`.

---

### P3 — ship, but write it down with an owner

#### F5. Every failed decision reads as "This one has already been decided."

**Proven.** `next-inbox.js:163-171`. The `.catch()` on the decide call removes the row,
shows `SAY.decided` and refreshes the counts — for **any** rejection, not only a
conflict.

Failure scenario: Sandeep is on a factory-floor phone, taps Approve, the request times
out or the server throws → the row vanishes from his screen and he is told somebody else
decided it. He believes the leave is handled. It is not, and the list does not redraw
(`draw(ctx)` is only called on the success path), so the stale screen is what he keeps
looking at.

AC-18 is about the conflict case only. Smallest fix: branch on the error — a conflict is
the sentence, anything else is the error state with Try again — and call `draw(ctx)` on
both paths.

#### F6. Four of the six Inbox parts draw rows nobody can act on, and no link either

**Proven.** `next-inbox.js` gives Approve/Decline to `leave_approvals` and
`attendance_fixes`. `goal_updates`, `shift_requests`, `policies` and `my_requests` get
rows with no buttons — and `build()` never uses `part.route`, which the server sends, so
there is no link out either.

So the screen can say "1 shift change to approve" and "2 policies to read and accept"
with no way to approve or read anything. The spec's own error-and-empty table
(`02-functional-spec.md:461`) promises "a row he may not act on is never drawn, so there
is no refusal state to reach" — this is the other half of that idea going missing.

Smallest fix: make each part's card title a link to `part.route`. Four lines.

#### F7. The celebrations card is computed on the server and drawn nowhere

**Proven.** `home_api._celebrations` runs on every Home load and `HOME_KEYS` carries
`celebrations`. `next-home.js:253-260` (`build`) composes hero + needs + leave + holidays
+ team + goals. No celebrations. So the "own work anniversary" that AC-61's fail-closed
default was supposed to ship does not appear on screen.

Either draw it or delete the server side. Cheap either way; it is only listed because the
notes imply it is built.

#### F8. Nobody is told the "this week" grid has gone

You asked me to judge the deletion. **The deletion is right and I would not reverse it.**
The old endpoint was whitelisted, returned `employee_name`, `designation` and `image` with
a per-day away state, and fell back to the caller's **whole department capped at 40** when
they had no reports — so any signed-in person could ask, by hand, for forty colleagues'
week of absences. Replacing that with three suppressed numbers is a straight improvement,
and `test_week_presence_retired_042.py` is a good test: it walks the app's source, asserts
the name appears nowhere, and **first asserts that more than 50 files were scanned**, so a
broken walk fails rather than passes.

**Is the replacement enough?** For the privacy purpose, yes. For the customer's purpose,
no — a manager who used the grid to see who is off on Thursday now gets one number and
cannot get that view anywhere. That is a deliberate loss and you have already been told
it is one.

**Is the release note adequate?** *There is no release note.* I searched `02`, `01c`,
`03` and `07` for any customer-facing notice: the only sentence anywhere is
`03-implementation-notes.md:29` ("Anybody who used the 'this week' grid on today's Home
will notice it…"). `07-devops-inputs.md` has fourteen OPS rows and none of them is
"tell the customer". The card will simply be absent one morning.

Smallest fix: one line in the release note, and — because the old page has no in-product
announcement mechanism (the spec dropped Announcements for v1) — an email or a message to
the two live tenants before the deploy. Owner: `hrms-product-manager` with
`hrms-devops-engineer`.

#### F9. The `get_home` budget move from 20 to 28 was the right call

You asked me to judge this. **Yes, and I would not change it.**

The old number was 20. It was never measured; the code measured 30–31 *for every persona
at both fixture sizes*, which means it was wrong the day it was written. Slice 044 then
did the cheap work first — R1's one-call memo and D6's aggregate team card — and got it to
28 before anybody moved the line. That is the right order: fix, then re-baseline, not
re-baseline instead of fixing.

More importantly the branch changed **what the budget is**. `nfr-budget.md` now says the
gate is that the count is the same at twenty people as at a thousand, and the number is a
note that makes drift visible. That is the property that actually protects a tenant, and
`test_scale_flatness_044.py` asserts it — with a positive control
(`test_a_call_that_walks_the_team_one_by_one_is_caught` writes the 16.4-second bell in
three lines and proves the guard catches it) and a second guard that fails when the
fixture team did not really grow. Lesson 10 held here.

One limit worth writing down: the automated flatness gate grows a team from **4 to 30**
people. The 981-person numbers come from `measure_044.py`, run by hand. A cost that only
appears above 50 — a cap, a page length — would pass CI. Note it; do not act on it now.

---

### P4 — backlog

- The endpoint registry's "no undeclared permission bypass" check watches `frappe.get_all`,
  `db.get_all`, `db.count`, `db.sql`, `db.sql_list`, `db.multisql` and (new in 044)
  `qb.get_query`, `qb.from_`. It does **not** watch `frappe.db.get_value`, which
  `home_api` uses five times and `inbox_api` once. All six are the caller's own record or
  doctype metadata, so nothing leaks — but the guard is narrower than its docstring
  claims. Add `frappe.db.get_value` to `watched` and declare the six.
- `get_nav_counts` and `get_inbox` each call `_my_employee()` a second time for
  `has_employee`, after `parts()` already resolved it. One wasted query on each call.
- `_part_goal_updates` guards on `_has_doctype("KPI")` but then queries `Individual Goal`
  and `Goal Progress Update` unguarded. Safe today (they install together); brittle.
- `home_api._card` logs `frappe.get_traceback()` and its docstring promises the line
  carries "nothing about a person". A raised `ValidationError` message can name one. The
  card name is safe; the exception text is not guaranteed. Narrow the claim or the log.

---

## 3. AC verification

Walked against the code, not against the notes. Only rows where I disagree with the
notes, or where the evidence is thin, are listed — the rest I read and agree with.

| AC | Notes say | I find | Evidence |
|---|---|---|---|
| AC-5 (fixed key list) | met | **met** | `home_api.py:762` returns `{key: home[key] for key in HOME_KEYS}`; `test_the_key_set_is_exactly_home_keys_for_every_persona` |
| AC-8 / AC-9 (count = list) | met | **met** | `Part.count()` and `Part.rows()` are both handed `self.filters` and nothing else; `_count_rows` and every `rows_fn` use `frappe.get_list` on the same dict. There is no seam for a second filter |
| AC-11 (capped list says so) | met | **met, proven in a browser** | `next_panels_test.js` "a capped list says how many it is showing of how many" and "no part ever shows a 50+" — both passed when I ran them |
| AC-13 (never decrement) | met | **met** | `next-inbox.js` calls `ctx.reloadCounts()`; no arithmetic on a stored count anywhere in the file |
| **AC-17 / US-5** | met | **partial** | Two of six parts have actions. F6 |
| **AC-19** | met | **not met** | No Withdraw control exists. F2 |
| AC-29 (a)(b)(c) | met | **met as built, with D-7 open** | `test_home_api_042.py:371-416`. F4 |
| AC-59 (endpoint retired) | met | **met** | `test_week_presence_retired_042.py`, with a positive control on the walk |
| AC-60 (escaping) | met | **met** | 27 jsdom assertions passed here, including three hostile-string placements, and a deliberate control at `next_panels_test.js:316` proving the hero assertion can fail |
| **AC-61 / D-8 (own anniversary)** | met | **partial** | Server builds it; no screen draws it. F7 |

---

## 4. The seven dimensions — claim vs. what was written

| Dimension | Impact analysis claimed | I find | Note |
|---|---|---|---|
| Performance | improves | **improves** | 16.4 s bell path never called; measured flat at 981 |
| Security | improves | **improves** | A named-per-day-absence endpoint deleted; every new endpoint has guest/persona/scope rows in the registry |
| Reliability | neutral to improves | **improves, with F5** | `_card` isolation is real; the Inbox's decide path mislabels failures |
| Scalability | "degrades if built naively, neutral if built as specified" | **built as specified, except F3** | One list-of-981-ids survives, in the one place nothing reads |
| Maintainability | improves | **improves** | `Part` with a compulsory scope string is a genuinely good mechanism |
| Data integrity | improves (claimed "nothing cached") | **improves** | Wave 1's F8 was acted on: the doctype cache is now keyed by build version (`inbox_api.py:178`). The one-call memo in `call_cache.py` is torn down in a `finally` and is correctly argued not to be a cache |
| Compliance / privacy | improves, one disclosure refused | **improves, D-7 open** | F4 |

---

## 5. Compliance verification

| Obligation (spec §17) | Mechanism in the diff | Test that proves it | Verdict |
|---|---|---|---|
| DPDP minimisation | `HOME_KEYS`, `ME_FIELDS`, `ROW_KEYS` per part, enforced in `Part.rows()` | `test_the_key_set_is_exactly_home_keys_for_every_persona`, `test_no_personal_field_wave_one_removed_comes_back` | **discharged** |
| DPDP access rights (every queue scoped server-side) | `parts()`; `no_rows()` instead of `{}`; `PartDefinitionError` at construction | scope rows in `ENDPOINT_REGISTRY`; `permitted_employee_filters` returns `ALL_EMPLOYEES`/`NO_EMPLOYEES`, never `{}` | **discharged** |
| OWASP ASVS L2 — list and action share one scope | one filter expression per part | AC-17 (a) drives rows through actions | **partial** — only two parts have actions at all (F6) |
| Purpose limitation on absence data | `_presence_counts` collapses status to three buckets before returning; old endpoint deleted | `test_no_name_no_photo_no_reason_reaches_the_payload`, `test_week_presence_retired_042` | **discharged** |
| Small-group suppression | `MIN_GROUP` + complementary suppression | five-case table test on `_suppress` | **discharged as built**; the residual risk it leaves is **not accepted** (F4) |
| No new personal-data field, no new retention question | no new DocType, no new custom field, nothing written | `03` §14 | **discharged** |

No AI in this slice.

---

## 6. What to delete

1. **`home_api._goals`'s `team` branch and `_hr_scope()` with it** (F3). Wrong number,
   only reader of a 981-id scope list, drawn nowhere.
2. **`next-inbox.js`'s unused `SAY.mine`, `SAY.waitingOnMe`, `SAY.withdraw`** — or, better,
   build the thing they were written for (F2).
3. **`home_api._celebrations`**, unless the card is drawn (F7).

---

## 7. What was done well

- **`Part` refuses to be built without a scope string and refuses an empty filter dict.**
  That turns two of this programme's recurring defects into import-time failures. It is
  the best single idea in the slice.
- **Re-measuring a budget instead of defending it, and then changing what the budget
  *is*.** The `nfr-budget.md` edit — flatness is the gate, the number is a note — is worth
  more than the code it came from.
- **Deleting the endpoint and not just the card**, with a source walk that proves the
  walk happened.
- **Wave 1's review findings were actually acted on**: the qb calls are now in the watched
  list (F7 of Wave 1), and the doctype cache is keyed by build version (F8 of Wave 1).
- **The DOM test carries its own control** at `next_panels_test.js:316` — "with a shift
  the hero IS drawn, so the assertion above can fail". That is the habit lesson 1 asks for.

---

## 8. Confidence

- **Proven:** F1 (counted the tags, both branches), F2, F3, F5, F6, F7 (read the code and
  the call sites), the DOM and static-check results (I ran them), and every "met" in §3
  that I read line by line.
- **Read, not re-run:** every `bench run-tests` figure, and every measurement at 20 and
  981 people. There is no bench in this worktree. If you want those independently
  confirmed I need a container with `test044` and `test044s` on it.
- **Not checked:** the 390 px layout, dark mode, the Hindi fixture, and the nginx
  rate-limit arithmetic in §13. `07-devops-inputs.md` asks for all four and none was run
  here.
- **Assumption, marked:** `[ASSUMPTION]` that `frappe.qb.get_query`'s `or_filters` compose
  as `filters AND (or_filters)`. I read the signature in the container
  (`ignore_permissions` defaults to **True**, `or_filters` is supported) but did not read
  the builder end to end. It matters only for `goals_api._pending_approvals_scope_query`,
  which has a test asserting the subquery and the list agree on the 981-person fixture.
