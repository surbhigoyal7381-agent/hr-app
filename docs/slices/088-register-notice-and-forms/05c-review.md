---
slice: 088-register-notice-and-forms (the follow-on "088c": every manual punch change, with a reason)
artifact: 05c-review (change-process step 5, senior architect review)
author: hrms-technofunctional-reviewer
date: 2026-11-25
risk tier: 1 (personal data, pay evidence, a mandatory rule on the punch feed)
reviewed: worktree /Users/mac/hr-app/.claude/worktrees/088-notice-scope, branch docs/088-notice-scope-analysis, head 3d4591d4, against origin/main 7ebc5898 (5 commits, 12 files)
also read: origin/dev (01d counsel requirements), release/088-alv436 (05-review, 06-security-review — they exist on no other branch)
frappe source read read-only out of the running container alv436rel-bench (Frappe 16.33.x): docker exec … grep/sed only, nothing written, nothing started or stopped
ran: no tests, no bench, no site. Static only. See §8.
---

# 088c · senior architect review

Labels used throughout: **proven** = I read the line or ran the command this session · **inferred** = reasoned from what I read · **assumption** = my guess, marked · **not checked** = I did not look.

---

## 1 · Verdict

**BLOCK** — one defect puts the wrong date on the paper an employee signs, for every
night-shift punch change, and that is the one thing this feature exists to get right.

Three sentences of context, so the block is read correctly:

- **Nothing is at risk today.** The feature is gated by `alvoraa_print_change_notices`,
  which the coordinator verified is off on every company on all six production sites,
  with zero notice records. Taken as given, not re-checked by me (**not checked**).
- **The work is good.** The strategy is honest, the guard rail was written first, the
  exemptions are right, and three claimed test counts matched the source exactly when I
  counted them myself. This is not a block on quality.
- **The blocker and the two majors below are small fixes** — one line, one line, one
  test. I expect a fast second round.

| Level | Count |
|---|---|
| P0 stop the line | 0 |
| P1 blocks the release | 1 |
| P2 high (needs a fix or a written acceptance) | 5 |
| P3 medium (ship, tracked) | 5 |
| P4 low | 4 |

---

## 2 · Findings, worst first

### P1-1 · BLOCKER · The notice dates a night-shift punch change on the wrong day, and at a month boundary on the wrong month

**Proven, by reading four files.**

`punch_change.write_log` (`alvoraa_portal/alvoraa_portal/punch_change.py:113`) stores:

```python
"day": getdate(doc.time),
```

That is the punch's **calendar** date. Everywhere else in this product the working day
a punch belongs to is the date its **shift started**:

- `alvoraa_portal/alvoraa_portal/payroll_rules_apply.py:365` `shift_day(punch)` returns
  `str(getdate(punch.get("shift_start") or punch.get("time")))`, and its own docstring
  says *"Every reader that groups punches by day uses this, so the engine, the reports
  and the screens put a punch on one day."* (ALV-402.)
- `alvoraa_portal/alvoraa_portal/held_day.py:292` imports it with the comment
  *"the one working-day rule (ALV-402)"*.

**The failure scenario.** DTC runs night shifts (ALV-402 exists because of them).

1. A shift starts 20:30 on 23 Nov and ends about 05:00 on 24 Nov.
2. The employee misses the OUT punch. HR types a punch at `2026-11-24 00:30`, picks
   "Employee forgot to punch", saves.
3. `write_log` writes `day = 2026-11-24`.
4. `_punch_changes` (`register_notice.py:258`) selects by `day`, and `sheet_rows`
   (`register_notice.py:552`) prints `_day_words(change.from_date)`.
5. **The paper the employee signs says 24 November.** The engine, every report and the
   employee's own attendance screen say that punch belongs to 23 November.
6. In a grievance about 23 November, the register for 23 November shows nothing.

**And at a month end it is worse.** A shift starting 20:30 on 30 November with a typed
punch at 00:30 on 1 December is logged on `day = 1 Dec`, so it appears on **December's**
notice, while the hours it changed were paid in **November**. November's notice — the
one the employee signs for the month whose pay moved — never mentions it.

**Why this is a blocker and not an accepted simplification.** `03c-implementation-notes.md`
declares it: *"Acceptable simplification: an after-midnight punch is logged on its own
calendar day, not its shift day; only matters on the last night of a month."* The second
half of that sentence is wrong. It matters on **every** night-shift punch change, because
the day printed on the page is wrong every time, not only at a month boundary. A declared
trade-off resting on a wrong premise is still a finding. For a feature whose entire
purpose is evidence that survives a dispute, a date the rest of the system disagrees with
is a defect on the face of the document.

**Smallest fix.** One import and one line in `write_log`:

```python
from alvoraa_portal.payroll_rules_apply import shift_day   # the one working-day rule
...
"day": getdate(shift_day(doc)),
```

`shift_day` already falls back to `time` when `shift_start` is empty, so nothing changes
for a day-shift punch. **`shift_start` is set by the time this runs** (proven:
`hrms/hrms/hr/doctype/employee_checkin/employee_checkin.py:58` `fetch_shift()` inside the
controller's own `validate`, and app `validate` hooks run after the controller method —
the repo already depends on this ordering, `hooks.py:293-295`: *"On validate, after
Frappe HR has set the punch's shift"*). `write_log` is `on_update`, later still.

**Test that would catch it:** one case with a punch whose `shift_start` is the previous
day, asserting the log's `day` and the printed `day` are the shift's day, and that it
lands on the earlier month's notice.

---

### P2-2 · MAJOR · Re-tagging a punch's shift changes which day it counts on, and is neither refused nor logged

**Proven.** `punch_change.MATERIAL` (`punch_change.py:45`) is
`("time", "log_type", "employee", "skip_auto_attendance")`. The module docstring says
*"Shift, attendance link, photo and position are not changes to a punch."*

But `shift_start` **is** what decides the punch's working day (P1-1 above, same
evidence). So a person who re-tags a punch's shift moves it from one day to another,
which can change hours, flip Present to Absent, and change pay — with no reason asked
for and no row on any notice.

This is not hypothetical. `alvoraa_portal/alvoraa_portal/alv291_attendance_fix.py:966-970`
is the DTC October repair, and its `retag` step does exactly this:

```python
doc = frappe.get_doc("Employee Checkin", r.name)
doc.fetch_shift()
doc.flags.ignore_validate = True
doc.save()
```

Memory `dtc-reds-fix-is-alv291` records that DTC's wrong reds came from wrong shift tags.
So the shift tag is the field a real repair actually edits.

**Two separate reasons it escapes**, and the analysis names neither:

1. `shift` / `shift_start` are not in `MATERIAL`, so even a plain save would not be logged.
2. `doc.flags.ignore_validate = True` — see P2-3.

`00b-notice-scope-analysis.md` P13 says this script escapes because it uses
`frappe.db.set_value`. That is true of the skip-flag step (`:937`, `:1194`, `:1205`); it
is **not** true of the retag step, which goes through `doc.save()` and could have been
covered. Where the brief and the source disagree, the source wins.

**Smallest fix.** Add `shift_start` to `MATERIAL` and one sentence in `_sentence`
("Punch moved to the day before" / "moved to {day}"). Then P2-3's fix makes it bite.
If Surbhi decides a shift re-tag is out of scope, that needs saying out loud in the
release note, because counsel's words are "every direct edit".

---

### P2-3 · MAJOR · One line of server code switches the whole reason rule off: `doc.flags.ignore_validate = True`

**Proven, in the framework source.**
`frappe/model/document.py:1407` (read out of `alv436rel-bench`):

```python
if self.flags.ignore_validate:
    return
```

That return is inside `run_before_save_methods`, **before** `self.run_method("validate")`.
`require_reason` is registered as a `validate` hook (`hooks.py:300`). So any server-side
caller that sets `ignore_validate` skips the reason rule completely. `on_update` still
runs, finds no stash, and returns — so the punch is written with no reason and no record.

**Reachability.** Not from a browser or the REST API: `"flags"` is in
`RESERVED_KEYWORDS` (`frappe/model/base_document.py:1601`), so a client cannot set it —
which also **confirms** the module's claim that the stash on `doc.flags` is server-only.
It is reachable from server code, and exactly one place in this repository already does
it on an Employee Checkin: `alv291_attendance_fix.py:969` (proven: I grepped
`ignore_validate` across `alvoraa_portal`, `hrms`, `scripts`, `demo` — 20 hits, all the
others are `create_custom_fields(ignore_validate=…)` or Goal documents).

**This repository already knows the answer.** `field_app_access.guard_shift_type_change`
(`field_app_access.py:163-172`) is a guard on another doctype, and its docstring says:
*"`before_validate` because the document is still as it arrived and it runs even with
ignore_validate set."* The same reasoning applies here and was not applied.

**Smallest fix.** Move the hook from `validate` to `before_validate` in `hooks.py`.
I checked the two things that could break:

- `get_doc_before_save()` still works: `check_if_latest()` loads `_doc_before_save`
  (`document.py:1097`) and runs before `run_before_save_methods` (`document.py:588`
  and `:594`). **Proven.**
- `require_reason` reads only the reason field, the four material fields, the session
  user and `doc.employee`. It does not need the shift, the geofence result or the 087
  marks. The only consequence of running earlier is message precedence: a punch failing
  both the geofence and the reason rule would now report "Pick a reason" first. That is
  a cosmetic trade, worth saying in the hook comment. (**If P2-2's fix adds
  `shift_start` to `MATERIAL`, this changes** — `shift_start` is set by the controller's
  `validate`, so a `before_validate` handler would see it unset on an insert. The two
  fixes interact: either compare `shift_start` in `write_log` against the before-copy, or
  keep a `validate` hook for the shift field only and accept P2-3 for that one field.
  **Name the choice; do not let the two fixes silently cancel each other.**)

---

### P2-4 · MAJOR · A punch moved from one person to another is logged only against the person who gained it

**Proven.** `employee` is in `MATERIAL`, so moving a punch between people is a logged
change. But `write_log` files the row against `doc.employee` — the **new** employee
(`punch_change.py:111`) — and `_sentence` writes "Punch moved to another person"
(`punch_change.py:161`).

**The failure scenario.** HR types a punch onto Ravi by mistake, then edits the punch to
Joginder.

- Joginder's notice gains a row saying "Punch moved to another person". It does not say
  from whom, and from Joginder's side the punch is an addition, not a move.
- **Ravi's day lost a punch, and Ravi's notice says nothing at all.** Ravi is the person
  whose attendance was reduced and who is never told.

Two smaller edges of the same code path:

- `_is_a_persons_change` resolves the company switch and the own-user test from
  `doc.employee`, i.e. the **new** employee. Moving a punch from a switch-on company's
  employee to a switch-off company's employee logs nothing at all.
- Moving a punch onto HR's own employee record hits the own-user exemption and logs
  nothing. (In practice `checkin_has_permission` already refuses an HR login writing
  their own punch — see "verified and dismissed" below — so this needs an
  `ignore_permissions` path.)

**Smallest fix.** Either write a second row against `before.employee` ("Punch at 10:00
moved to another person" on the losing side), or drop `employee` from `MATERIAL` and
refuse the edit while the switch is on, pointing HR at delete-and-retype — which is
itself refused, so: refuse the reassignment and say "add the punch to the right person
and set this one aside with a reason". The second is smaller and loses nothing.

---

### P2-5 · MAJOR · The only scope test compares two SQL strings. Neither new permission wiring is exercised

**Proven, by reading the test.** `test_punch_change_088c.py:282`:

```python
self.assertEqual(
    register_notice.punch_change_query_conditions(self.hr),
    register_notice.notice_query_conditions(self.hr).replace(
        "`tabAlvoraa Register Notice`", "`tabAlvoraa Punch Change`"))
```

Both sides are `_scope_sql` with a different table argument. The test can only fail if
the implementation stops calling `_scope_sql` — which is what break B13 showed. It
proves the SQL *shape*. It does not prove that the row filter is **wired**, and it does
not prove that a cross-company HR user actually sees nothing.

Two wirings in this diff are proven only by my reading `hooks.py`, and by no test:

| Wiring | Line | Tested? |
|---|---|---|
| `permission_query_conditions["Alvoraa Punch Change"]` | `hooks.py:669` | no |
| `has_permission["Alvoraa Punch Change"] = notice_has_permission` | `hooks.py:696` | no |

The second one reuses a function written for a different DocType. It happens to be
correct — `notice_has_permission` reads `doc.get("employee")` (`register_notice.py:950`)
and the new DocType has an `employee` Link (`alvoraa_punch_change.json:31`) — but a
reused function whose correctness depends on a field name matching is exactly the thing
a test should pin. The rows at stake are employee names, HR logins and reason codes.

This is the hollow-test class the slice-016 lesson is about: a green assertion that buys
confidence it has not earned.

**Smallest fix.** Two cases, both cheap, using the fixtures `test_register_notice_088`
already has for the SEC-1 branch and company tests:
1. As HR of company B, `frappe.get_list("Alvoraa Punch Change")` returns no row for
   company A's employee.
2. As the same user, `frappe.get_doc(LOG, <row>).has_permission("read")` is False.

---

### P2-6 · MAJOR · 088c makes the un-landed two-page blocker the common case, not an edge

**Proven for the numbers in the code; inferred for the volume.**

- `PER_PAGE = 5` (`register_notice.py:428`). Six qualifying changes for one person in one
  month means two pages.
- The earlier review's P1-1 (`release/088-alv436`, `05-review.md:43`) is that a notice of
  two or more pages cannot be recorded and the person's pay stays held. That fix is 4
  commits on `release/088-alv436` and is **not on main**. Taken as given.
- `01d-counsel-requirements-2026-11-24.md` §1 puts October at 3,322 changes over roughly
  600 staff — about 5.5 each (the PM labels it inferred, and October was a deliberate
  catch-up, so a normal month is unknown).

Before 088c, the two-page case needed six *request-based* fixes for one person in one
month, which has never happened on either tenant. After 088c, every direct punch change
counts toward the same five-per-page limit. If a normal month is anywhere near
October's rate, **two-page notices become ordinary**, and the dormant blocker becomes
the first thing HR meets.

This does not change the code in this diff. It changes the release condition from
"nobody should tick the switch yet" to "the switch cannot be ticked until those 4
commits are on main", and it means the two-page path needs a test that includes direct
punch changes, not only requests.

**Owner:** Surbhi, for the release order. **Recommendation:** land the 4 page-count
commits before or with 088c, and add one test that prints six direct changes for one
person and records the answer.

---

### P3-7 · `_moved` compares raw, uncast values, so an API or import edit can print a false sentence or fail the punch save

**Proven for the mechanism; the reachability is inferred.**

`punch_change.py:76`:

```python
return any(str(doc.get(f) or "") != str(before.get(f) or "") for f in MATERIAL)
```

`doc.get()` returns the value **as it arrived**. Frappe does not cast it before the
validate hooks: `BaseDocument.cast` is called only from `get_value`
(`base_document.py:1534`), and `_fix_numeric_types` runs only when loading a single
doctype (`document.py:268`). `before` is loaded from the database, so its values are
native Python types. **Proven in the framework source.**

Two consequences, both only on an edit by a person with the switch on, where the caller
sends strings (REST, or a Data Import — both declared untested in `03c`):

1. **A false sentence on the evidence.** `skip_auto_attendance` arriving as the string
   `"0"` against a stored `0`: `str("0" or "")` is `"0"`, `str(0 or "")` is `""`, so
   `_moved` says changed. `_sentence` then evaluates `bool("0")`, which is **True** in
   Python, and writes *"Punch at 10:00 not counted"* — a statement on a printed legal
   notice that nothing in the data supports.
2. **A punch save that fails with a confusing error.** A `time` of
   `"2026-11-25 09:15"` against a stored `09:15:00` makes `_moved` True while
   `_sentence` compares with `get_datetime` and finds nothing, returning `""`. `what` is
   `reqd: 1` on the log (`alvoraa_punch_change.json:81`), so the log insert raises a
   mandatory-field error and the whole punch save fails — after the caller was already
   told to supply a reason.

The Desk is safe: its form sends `0`/`1` for a Check and `YYYY-MM-DD HH:mm:ss` for a
Datetime (**inferred**, not driven).

**Smallest fix.** Use the cast accessor on both sides — `doc.get_value(f)` and
`before.get_value(f)` — which is `cint` for the Check, `get_datetime` for the Datetime
and `cstr` for the Link and Select. One line, and it removes both consequences.

---

### P3-8 · The test-pollution fix is the right direction but blunt, and the order that failed was never re-run green

**Proven for the mechanism.** `expense_evidence.log_view` ends with `frappe.db.commit()`
(`expense_evidence.py:763`), reached from `register_notice.open_photo`
(`register_notice.py:726`), which `test_register_notice_088` calls in five places
(`:1090, :1109, :1141, :1192`). So the suite does commit mid-test, the switch set to 1
in `setUp` becomes permanent, and the restore must be permanent too. The fix
(`test_register_notice_088.py:87`, `frappe.db.commit()` inside
`_put_the_notice_switch_back`) is correct and is the only way to make a restore survive
a prior commit in Frappe.

**Two things to say about it.**

1. **It is blunt.** `frappe.db.commit()` in an `addCleanup` commits *everything*
   outstanding at that moment — the test's punches, notices and log rows — not only the
   switch. Because `log_view` already commits, the suite was already leaking rows, so
   the incremental cost is small. Worth a line in the suite so nobody "tidies" it later.
2. **The order that failed is not proven fixed.** `03c` says every suite was run "one at
   a time". The red was found by running 087 after 088; the notes do not record that
   pair being re-run green together after the fix. **This is my one must-know item** —
   see §9.

**Other committing paths in these suites — I looked, and here is the enumeration, not a
scope word.** I grepped `db.commit()` across `alvoraa_portal` (excluding tests, demo,
seeders, patches) and checked each against the call graph these two suites use:

| Path | Reached by 088 / 088c? |
|---|---|
| `expense_evidence.py:763` (`log_view`) | **yes**, via `open_photo` — this is the one |
| `punch_dedupe.py:255, :275` | no — `flag_existing` / `unflag_existing` are hand-run bench commands, **not** the `before_insert` hook |
| `field_checkin.py:489, :614, :726` | no — the phone endpoints; 088c simulates a Guest insert instead of calling them |
| `hr_api` web check-in | no — same, simulated |
| `register_notice.py`, `punch_fix.py`, `punch_change.py` | **none at all** (proven by grep) |

So: one committing path, correctly identified and correctly fixed.

---

### P3-9 · The machine exemption is a login a person can use, so "every manual addition" is not literally true

**Proven, and the test fixture proves it better than the code does.**
`files_as_machine` (`field_app_access.py:71-77`) is "holds the `Biometric Sync` role, has
no Employee record, is not Administrator". The new fixture
(`test_register_notice_088.py:60`) builds exactly that user **with `HR User` alongside**:

```python
self._machine_login = self.h._login("mach088", ("Biometric Sync", "HR User"))
```

That is realistic — the comment in `files_as_machine` records that removing HR roles from
the sync accounts is what broke every DTC punch on 2 Nov (ALV-302). So a person who
signs in as the sync account can add and edit punches with no reason and no log row.

The exemption itself is **right** and must stay: a refused machine punch is lost for
good. The finding is that the claim needs its boundary stated. Memory
`sync-accounts-no-hr-roles-alv386` says DTC's sync account now holds only
`Biometric Sync`, which narrows it in practice at DTC (**not checked** by me on any
site).

**Recommendation:** no code change. One line in the release note and in the runbook: the
sync account's password is a bypass of the reason rule, so it is a named-login control
(ALV-386), not a product control.

---

### P3-10 · A log row can exist that no employee will ever be shown, and nothing says so

**Proven by reading.** The log is written whenever the switch is on. It reaches a notice
only through `list_people` / `open_notices`, both of which drop a person whose
**current** company has the switch off (`register_notice.py:382-384` and `:629-632`).

So: HR makes ten direct changes in November, the organisation unticks the switch on
1 December, and ten log rows sit there about ten employees who were never told. Surbhi's
decision 5 covers the opposite case ("nothing is logged while the switch is off"); it
does not cover this one.

Same shape, smaller: a person who leaves. `my_changes` goes through
`attendance_correction._me()`, which is Active only (`register_notice.py:999`), so a
leaver's unsigned changes disappear from their own view.

**Recommendation:** accept, written down with an owner. The honest cheap mitigation is
one sentence on the Company switch's description: "Unticking this stops the notice; it
does not remove changes already recorded."

### P3-11 · The notice shows October's changes as nothing at all, and the PM's recommended honest line was dropped

**Proven.** Nothing before switch-on is in the log, by design (Surbhi's decision 4, and
I am not proposing a backfill). `01d-counsel-requirements-2026-11-24.md` §2 recommended
option **A + B together**: start at switch-on, *and* show "No reason recorded: before
24 Nov 2026" on old rows, because *"it costs almost nothing and stops a blank looking
like a loss"*. A is built. B is not built and is not recorded as rejected anywhere I
read.

This is the lesson-3 trap: an empty list that cannot be told apart from "configured to
show nothing". It is display-only, not a backfill.

**Recommendation:** Surbhi's call, one sentence on the screen or nothing. Record the
decision either way.

### P3-12 · No requirements or test artifact exists for 088c, so two axes are partly unreviewable

**Proven, by listing the slice folder on four branches.**

| Artifact | Where it is |
|---|---|
| `00b` strategy, `03c` notes | this branch |
| `01`, `01a`, `01b`, `01c`, `02`, `07`, prototype | main, dev, this branch — all 088-base, none mention 088c |
| `01d` counsel requirements | **`origin/dev` only** — not on this branch |
| `04` test report | **does not exist** for 088 or 088c on any of the four branches |
| `05-review`, `06-security-review` | **`release/088-alv436` only** |

Consequences I have to state rather than paper over:

- There are **no numbered ACs for 088c**. I walked counsel's sentence and Surbhi's five
  decisions instead (§4). An AC table in the usual sense would be invented by me.
- There is **no 01c-style security and privacy requirement set for 088c** — no new SEC,
  PRIV or OPS item to trace. The engineer's own §6 is the only requirements-side
  analysis of a Tier 1 change, and the engineer wrote both halves.
- There is **no independent test report**. All test figures come from the engineer.
- The earlier reviews' open findings live on a branch that is not in anybody's path.

**Recommendation:** at minimum, pull `01d` onto this branch so the requirement travels
with the code, and copy `05`/`06` where they can be read. A security verification pass
on 088c specifically is worth asking for, given Tier 1 and the new permission surface
(P2-5).

---

### P4 · Nits, in one list

- **`company` on the log is written and never read.** `_punch_changes` is the only
  reader and selects `name, employee, day, changed_by, changed_on, reason_code, what,
  kind` (`register_notice.py:258-262`) — no `company`. The scope filter goes through
  Employee, not company (`_scope_sql`). One test asserts it
  (`test_punch_change_088c.py:135`), which is a test of a field nothing uses. Delete it,
  or say in one line why the company-at-the-time matters as evidence. See §6.
- **`kind` is selected and never used.** It is put on the row (`register_notice.py:277`)
  and read by nothing — `sheet_rows` and `my_changes` both use `what`. Keep it only if
  the Added/Changed distinction is wanted as evidence in its own right; say which.
- **Two indexes on the same leading column.** `employee` has `search_index: 1`
  (`alvoraa_punch_change.json:38`) and `after_migrate` adds a composite
  `(employee, day)` (`punch_change.py:186`). The composite serves the only query and
  makes the single-column one redundant. `no-over-engineering.md` also asks for a
  measured number before an index; none was given. Keep one.
- **`FLAG = "in_punch_change"` is written out twice** — `punch_change.py:47` and
  `alvoraa_punch_change.py:19`. The controller should import the module's constant. If
  they ever drift, the append-only guard refuses the system's own writes, which fails
  closed and loudly, so this is a nit, not a risk.
- Also noted and deliberately **not** raised as findings: `except Exception: pass`
  around `add_index`; the `security_logger().info` line sitting outside the `try`
  (memory `alv391-security-log-never-written` says that file is never written anyway);
  the notice child JSON losing its trailing newline; `my_changes` returning a log row's
  name under the key `"request"` (the screen uses `d.date`, proven at
  `portal.js:7789`, so nothing breaks).

---

## 3 · Things I checked, expected to be defects, and dismissed

Recording these so the next reviewer does not spend the time again.

| What I suspected | Why it is not a defect |
|---|---|
| `kind` would always be "Changed", because `flags.in_insert` is cleared before the writes | **Not a defect.** `document.py:506` re-sets `self.flags.in_insert = True` immediately before `run_post_save_methods()` at `:512`. On_update during an insert sees it True. |
| The HR list would show every printed punch change as "changed after print", because `_content_hash` has no `reason_code` or `what` when `with_content=False` | **Not a defect.** `_state` compares membership by name only (`register_notice.py:325`, `c.name not in covered`). The hash is used solely by `_write_the_notice` and `_still_the_same`, and `_still_the_same` is skipped for punch rows (`register_notice.py:853-854`). |
| Refusing human deletes would break the 087 undo | **Not a defect.** `punch_fix._reverse` (`:1071-1086`) sets `in_punch_fix_apply` and its docstring says *"deleting nothing"* — it only saves. Proven. |
| A client could send `flags: {ignore_validate: 1}` and switch the rule off from a browser | **Not possible.** `"flags"` is in `RESERVED_KEYWORDS` (`base_document.py:1601`), so `update()`/`set()` drop it. This also proves the module's own claim that the reason stash on `doc.flags` is server-only. |
| HR editing or adding their own punch is a self-dealing hole left open by the own-user exemption | **Mostly already closed, by a different layer.** `field_app_access.checkin_has_permission` (wired at `hooks.py:682`) refuses `create` on one's own employee record (`:362`) and `write`/`delete` on it (`:356`). So the exemption bites only for a genuine employee on their own punch, and for server paths using `ignore_permissions`. |
| A reason captured with no log row written | **Only on a rollback, which is correct.** Employee Checkin has no `is_submittable` (proven from its JSON), so `_action` is always `"save"` and `on_update` always follows `validate`. If a later validation throws, the punch and the row both roll back — `test_a_refused_punch_leaves_no_punch_and_no_record` covers it. |
| `punch_dedupe` commits inside the punch-insert hook, so test state leaks on every punch | **No.** Its two commits are in `flag_existing`/`unflag_existing`, hand-run bench commands, not in `skip_repeat_scan`. |
| The reason list on the punch and on the log would drift | **They cannot, after a migrate.** `create_custom_fields` defaults to `update=True` (`custom_field.py:322`), so the Select options are rewritten from the DocType each time. Proven in the framework source, and `test_the_reason_options_on_the_punch_are_the_options_on_the_record` pins it. |
| HR's edit of a punch linked to Attendance would be a common un-logged path | **hrms refuses it first.** `validate_time_change` (`employee_checkin.py:78-85`) throws when `attendance` is set and `time` changed, inside the controller's validate, i.e. before our hook. It narrows where the time-edit path applies; it does not create a gap. |

---

## 4 · Counsel's requirement and Surbhi's five decisions, walked one by one

There are no numbered ACs for 088c (P3-12). These are the requirements that exist.

### Counsel, 24 Nov 2026 (as relayed in `01d` §1)

> the monthly notice must pull **every manual punch addition** and **every direct edit**, and each must carry a **reason code**

| Obligation | Mechanism in this diff | Test that proves it | Verdict |
|---|---|---|---|
| Every manual punch **addition** carries a reason | `require_reason` on `validate`; refuses with "Pick a reason" | `test_switch_is_on_and_a_person_is_refused_without_a_reason`, `test_a_person_adds_a_punch_with_a_reason_and_one_record_is_written`, `…sync_api…`, `test_administrator_is_a_person_and_needs_a_reason` | **partial** — escapes via `ignore_validate` (P2-3) and the sync login (P3-9) |
| Every **direct edit** carries a reason | same hook; `MATERIAL` = time, log_type, employee, skip_auto_attendance | `test_an_edit_needs_a_fresh_reason_every_time`, `test_not_counting_a_punch_is_a_change_and_says_so`, `test_changing_what_does_not_decide_the_day_needs_no_reason` | **partial** — the shift tag changes the day and is excluded (P2-2) |
| The **notice lists** them | `_punch_changes` + `sheet_rows` + `_write_the_notice` | `test_a_typed_punch_reaches_the_list_the_sheet_and_the_notice_record` | **partial** — wrong day for night shifts (P1-1) |
| A **reason code**, not free text | Select on the log, 7 options, mirrored onto the punch | `test_the_reason_options_on_the_punch_are_the_options_on_the_record` | **discharged**, list pending sign-off (declared) |
| The record is **evidence** (not editable, not deletable) | controller `validate` and `on_trash` refuse unless the module flag is set; no create/write/delete in `permissions` | `test_the_record_cannot_be_made_edited_or_deleted_by_hand`, for `self.hr` **and** `Administrator` | **discharged** for every document-layer and API door; `frappe.db.set_value`/raw SQL remain (declared, accepted) |
| The **employee** can read it | `my_changes` returns `why` and the sentence | `test_the_employees_own_view_shows_it_with_its_reason`; screen renders at `portal.js:7787`, and the printed "Why" column at `portal.js:7083` | **discharged** |
| Administrator counted, shown as "HR" | Administrator skip removed at `_request_changes`; `sheet_rows` returns `filed_role "HR"`, `filed_by None` | `test_administrator_is_a_person_and_needs_a_reason`, `test_the_employees_own_change_is_not_on_the_list_but_an_administrator_one_is` | **discharged** |

**On the "every" in counsel's sentence.** The honest count: of the 15 paths in `00b` §2,
this diff covers P1–P7 (7 paths), exempts P8, P9, P11, P12 on purpose, leaves P10 out by
decision, and cannot cover P13, P14, P15. On top of that I found three more escapes the
analysis did not list: `ignore_validate` (P2-3), the shift tag (P2-2), and the sync
login (P3-9). **Say "every path through Frappe's document layer except the shift tag",
not "every".** That sentence is defensible; the shorter one is not.

### Surbhi's five decisions

| # | Decision | Verdict | Evidence |
|---|---|---|---|
| 1 | Punches only; Attendance rows out of scope | **met** | no hook, field or query on Attendance in the diff (proven by reading all 12 files) |
| 2 | The reason lives in one append-only log DocType, not a field on the punch | **met** | the Custom Field is blanked at the top of `require_reason` on every path; `test_a_person_adds_a_punch…` asserts the punch's field is None afterwards |
| 3 | A person's delete is refused while the switch is on | **met** | `refuse_delete`; `test_a_person_cannot_delete_a_punch_while_notices_are_on`, with a switch-off control |
| 4 | Reason codes start at switch-on; October untouched; no backfill | **met** | the log is the boundary; `test_something_done_before_the_switch_is_never_listed`. See P3-11 for the display question only |
| 5a | Administrator counts and prints as "HR" | **met** | above |
| 5b | Direct changes hold no pay | **met** | `blocks_pay: False`; `test_…` asserts `sheet["pay_line"]` is False; `_write_the_answer` skips `record_register_signature` for punch rows |
| 5c | A late edit is listed on its own day's month | **met for day shifts, not met for night shifts** | `test_a_late_edit_of_an_earlier_month_is_listed_on_that_month_only` passes — but it uses a daytime punch, so it could never have shown **P1-1** |
| 5d | Nothing is logged while the switch is off | **met** | `test_switch_off_nothing_is_demanded_or_logged` |
| 5e | Undo out of this release | **met** | nothing in the diff touches `_reverse` |

---

## 5 · Non-functional, re-checked against the code

### The seven dimensions: the strategy's claim beside my finding

| Dimension | `00b` §6 claim | My finding |
|---|---|---|
| Performance | neutral off; 2 queries on, for a machine punch | **Agreed, and I verified the mechanism rather than the number.** Switch off: `frappe.flags` reads, the session user, then `notices_are_on` = a cached column list (`get_db_table_columns` caches under `table_columns::…`, `database.py:1348`) plus `get_cached_value` on Company → **0 SQL on a warm cache**. Switch on, machine punch: `files_as_machine` = 2 uncached `frappe.db.exists` (`field_app_access.py:74-77`) → **2 SQL**. The shape of both claims is right. Not measured by me. |
| | "two handlers already pay `files_as_machine` on every punch" | **Overstated.** In the punch-insert path I count **one** other production caller: `held_day.py:420` (`after_insert`). The third, `field_app_access.py:369`, is in `checkin_has_permission` and does not run for the phone or portal inserts, which use `ignore_permissions`. So 088c doubles that cost rather than adding a third share of it. Still only 2 extra queries per punch, with the switch on. **P4**, but correct the record: the justification for not caching is weaker than written. |
| Security | improves | **Agreed, with P2-3 and P2-5.** The guard is server-side and structural, not a prompt or a hidden button. The log grants read to three HR roles and create/write/delete to nobody (`alvoraa_punch_change.json:110-123`), with controller guards that also catch Administrator, who bypasses Frappe's permission layer. The one `ignore_permissions=True` (`punch_change.py:119`) is the module's own insert, gated by a flag a client cannot set — argued and safe. No raw SQL and no client-supplied doctype, field or path anywhere in the diff (proven by reading). |
| Reliability | "degrades slightly, guarded"; a fault must never fail a machine punch | **Agreed for machines and phones, with one correction to the wording.** A machine or Guest punch returns before any write and cannot be failed by this code (proven: `_is_a_persons_change` returns False, no stash, `write_log` returns at `:104`). But for a **person's** punch the handler can and does fail the save — by design for a missing reason, and by accident in P3-7's mandatory-field case. "The handler never raises" is true only for the exempt paths; say so. |
| Scalability | neutral | **Agreed.** DTC's 8 machines at ~5-minute intervals for ~620 staff: every one of those punches is a machine insert, so the added cost is 2 queries each and no log row. The notice query is indexed `(employee, day)` and bounded by the month and the 25-row page (`PAGE = 25`). The real scale problem is **human**, not technical — see the volume note below. |
| Maintainability | degrades slightly | **Agreed.** One new DocType, one module, three hook lines, one Custom Field, and `qualifying_changes` split into two honest halves. The split is an improvement on what was there. Two unread fields and a duplicated constant to clean (§6). |
| Data integrity | improves | **Agreed on the transaction** (the log row and the punch are in one transaction; a rollback loses both — proven and tested). **Disagree on one word:** "the reason is stored with the change" is only true for the four material fields, and the `day` it is stored against is the wrong one for night shifts (P1-1). |
| Compliance / privacy | improves, one new item | **Agreed.** The log holds a sentence with two times, an employee, a user and a code — no free text, no reason prose about a person. Nothing personal reaches a log line (`write_log`'s logger line carries the punch name and the user id only). The employee's own view shows the reason but **not** the HR login (`sheet_rows` returns `filed_by: None` for punch rows — proven, and it is the right call under OQ-1). Retention: a `day` column and no purge job, by Surbhi's decision, with a ticket still to be raised. **partial, by decision.** |

### Budget lines

| Budget | Measured or reasoned | Verdict |
|---|---|---|
| No added queries on the hot path when a feature is off | reasoned, from the framework source | **pass** — 0 SQL, switch off, warm cache |
| Over 2 s of work goes to a background job | reasoned | **pass** — no new synchronous work; the log insert is one row |
| Scope stays in the database (the earlier review's P3-8) | reasoned, from `_scope_sql` | **fail, inherited and now widened.** `punch_change_query_conditions` reuses `_scope_sql`, which reads permitted employee ids into Python and ships them back as `IN (...)`. Not new; one more doctype now does it |
| An index needs a measured number first | — | **fail, minor** — two indexes, no measurement (§2 P4) |
| Notice query count | not measured | **not checked** — and `_punch_changes` carries an admitted N+1: one `frappe.db.get_value(NOTICE, c.parent, "outcome")` per covering child row (`register_notice.py:268-270`). Bounded by changes per person per month, so small now; it grows with exactly the volume this slice adds. Accepted as temporary debt, with the trigger named: fix it with one grouped query if a normal month shows more than a handful per person |

### The volume consequence nobody owns yet · P2

A direct change becomes "done" only when a notice covering it is answered **Signed**
(`_punch_changes` sets `is_open = r.name not in signed`). Unlike an 087 request, it can
never be closed by the employee confirming in the app, and it holds no pay, so there is
no pressure on anyone. If DTC's rate is anywhere near October's ~5.5 changes per person,
HR's list goes from a handful of people to most of the floor, every month, and rows that
nobody collects a signature for stay open for ever.

`01d` §1 flagged this ("the notice changes from 'a few people a month' to most of the
floor") and `00b` answers "measure the first normal month", which is honest. But there
is no mechanism to close a row other than paper, so the backlog only grows.

**This needs Surbhi's written acceptance before the switch is ticked**, not a code
change in this slice.

---

## 6 · What to delete

The subtract pass, applied to the diff:

1. **`company` on the log DocType** — written by `write_log`, read by nothing (proven:
   `_punch_changes` is the only query and does not select it). Delete it, or write one
   line saying the company-at-the-time is wanted as evidence. If it stays, the test that
   asserts it (`test_punch_change_088c.py:135`) is asserting a field nothing uses.
2. **One of the two indexes on `employee`** — `search_index: 1` on the field, plus a
   composite `(employee, day)` from `after_migrate`. The composite serves the only query.
3. **`kind`, unless the Added/Changed distinction is wanted for its own sake** — it is
   selected and never used; `what` already says "added".
4. **The duplicated `FLAG` literal** in the DocType controller — import the module's.

Everything else in the diff earns its place. In particular I tried hard to kill the new
DocType and could not:

- The cheaper rung (a persistent Select on the punch plus `Version`) fails on three
  things the strategy proved, and I re-checked two of them in the framework source: a
  plain insert leaves **no** `Version` row (`save_version` returns with no earlier copy),
  and `Administrator` holds delete on `Version`. A record the break-glass account can
  delete is not evidence.
- No new app, no new Frappe module (`modules.txt` untouched — proven, it is not in the
  diff), no new settings page, no feature flag (the existing Company switch is reused),
  no abstraction, no dependency, no cache, no background job, no backfill, no shim.
- The rung is declared for every item in `03c`, and the cheaper rungs are named with
  what breaks. That is the standard.

**Nothing was removed from this review on my own subtract pass** beyond the findings I
checked and dismissed in §3 — six candidate findings deleted there, which is where the
subtraction went.

---

## 7 · What was done well

Named as decisions, not people.

- **The guard rail was written first, and it is a real one.** `TheGuardRail` proves,
  with the switch on, that a machine, a Guest phone punch, the web check-in, the
  employee's own edit and an approved 087 fix are neither refused nor logged — each with
  a control so "allowed" cannot quietly mean "the rule is not running". On a table where
  a refused write loses a punch for good, that is the right order to build in.
- **The break table in `03c` is the best part of the slice.** Sixteen breaks, each with
  what the break produced, and the distinction between "Error" and "Wrong value" made
  explicit. That is how a reader can judge a test without re-running it.
- **Two of its own tests were found passing for the wrong reason and fixed to name the
  refusal.** A duplicate-timestamp error and a mandatory-field error were both masquerading
  as the rule working. Finding that in your own work is the hardest check there is.
- **The reason is taken at entry and blanked immediately**, so a stale reason can never
  be reused by the next edit — and the chosen reason travels on `doc.flags`, which a
  client provably cannot set. Both halves of that design are right.
- **The punch name is stored as `Data`, not a `Link`**, so the record outlives the punch.
  Small decision, exactly the right one for evidence.
- **The sync-API path was found and closed.** `add_log_based_on_employee_field` is the
  endpoint a person could use to reach the same insert a machine uses; it is open to the
  machine and refused for a person with no reason, and tested both ways.
- **`qualifying_changes` was split into `_request_changes` and `_punch_changes`** instead
  of being widened in place. A 965-line file got easier to read, not harder.

---

## 8 · The six `test_held_day_085` failures — confirmed from the source, and better than "inferred"

**Proven, by enumeration, which is stronger than what `03c` claims.** The notes say one
failure was opened and the other five were inferred from their names. I can confirm all
six from the test source without running anything.

`test_held_day_085.py:29-37` defines:

```python
def backfill_script_path():
    repo = os.environ.get("GITHUB_WORKSPACE") or os.path.abspath(
        os.path.join(os.path.dirname(__file__), *[".."] * 4))
    path = os.path.join(repo, "scripts", "alv392_held_backfill_grace.py")
    assert os.path.exists(path), "the backfill script is not at " + path
```

Four levels up from `apps/alvoraa_portal/alvoraa_portal/tests/` is the bench root, so
outside CI the test requires `<bench>/scripts/alv392_held_backfill_grace.py`. **Exactly
six** tests reach it, directly or through `_backfill_module` / `_load`:

1. `test_backfill_end_to_end_dry_run_then_apply_then_undo` (`:696`)
2. `test_a_day_in_a_submitted_slip_is_not_held_by_the_backfill` (`:754`)
3. `test_the_test_hook_still_refuses_every_other_site` (`:760`)
4. `test_hold_then_rerun_finds_nothing_then_undo_restores` (`:769`)
5. `test_it_refuses_any_other_site_and_a_repo_undo_file` (`:809`)
6. `test_undo_puts_back_only_rows_that_are_still_held` (`:821`)

The script **does** exist in the repository (`scripts/alv392_held_backfill_grace.py`,
7,391 bytes), so this is purely the bench not exposing `scripts/` — `GITHUB_WORKSPACE`
makes CI pass. The file count also reconciles: 45 `def test_` in that module, 39 + 6.

**Does it hide a real defect?** No, and here is the reason rather than an assurance: the
failure is an `assert os.path.exists` on a fixture path, raised before any product code
runs. 088c changed nothing on that path. And the 085 suite never ticks the notice switch
(only `test_register_notice_088` does, by grep), so the reason rule is inert in it.
**Environmental, for all six, with the mechanism named.**

---

## 9 · Confidence, and what I could not check

### What I ran
- `git log`, `git diff`, `git ls-tree`, `git show` in the worktree above.
- `python3 -m py_compile` on all five changed Python files — **clean**.
- `json.load` on both changed DocType JSONs — **both valid**.
- `grep -c 'def test_'`: **23** in `test_punch_change_088c`, **80** in
  `test_register_notice_088`, **134** in `test_punch_fix_087`, **45** in
  `test_held_day_085`. All four match `03c` exactly, including 39 + 6.
- `docker exec alv436rel-bench` with `grep`/`sed` only, to read Frappe 16.33.x source:
  `document.py`, `base_document.py`, `database.py`, `custom_field.py`. **Read-only. I
  started, stopped and changed nothing**, and I touched no other session's container.

### What I did not run
- **No test suite.** Every pass/fail count in `03c` is the engineer's and is
  **unverified by me** — I verified the test *counts* statically, not that they pass.
  Building a stack for this review would have cost more than it bought, given the figures
  are internally consistent and the break table is specific.
- No bench, no site, no Desk form, no Data Import, no REST call. So P3-7's reachability
  through those doors is **inferred**, not proven.
- No production site read. The switch being off everywhere and zero notice records are
  taken from the brief as given (**not checked** by me).
- The printed page on paper. **not checked**, as in the earlier review.
- `held_team.py` in full — I read enough to confirm it only reads punches
  (`held_team.py:107`, a `get_all`, no insert or save).

### Must know — this one holds the verdict open even after the blocker is fixed

**Was `test_register_notice_088` followed by `test_punch_fix_087` re-run, in one process,
after the commit fix?**

- My reading: the fix is correct and is the only way to make the restore survive
  `log_view`'s commit.
- What is uncertain: `03c` says every suite ran "one at a time". The failure was found by
  running the pair; the notes do not record the pair passing afterwards.
- Why it changes the verdict: if it still leaks, CI goes red for any punch suite ordered
  after the 088 suite — the exact failure the fix exists for, and one that would look
  like a product bug.
- The one question: run those two modules in a single `bench run-tests` invocation, in
  that order, and paste the last line plus
  `frappe.db.get_value("Company", <company>, "alvoraa_print_change_notices")` afterwards.
- Meanwhile I rank it **P3, provisional** — the mechanism is right, only the proof of
  the pair is missing.

### Should know
- Does Surbhi want a shift re-tag covered (P2-2), or is it out of scope with that said
  in the release note? My reading of counsel's "every direct edit" says covered. If it is
  out of scope, P2-2 drops to a disclosure.
- Is the volume consequence (§5) accepted in writing, by whom, and with what first
  measurement?
- Should the PM's option B line about pre-switch-on changes be shown (P3-11)?

### Nice to know
- Was a security verification (06) commissioned for 088c? If not, P2-5's untested
  permission wiring and the new personal-data store argue for one.

---

## 10 · What has to happen before this ships, in order

1. **P1-1** — the log's `day` uses the working-day rule. One line, plus a night-shift test.
2. **P2-3** — move the hook to `before_validate`, and decide the interaction with P2-2
   explicitly (see the note in P2-3).
3. **P2-2** — cover the shift tag, or record that it is out of scope and say so in the
   release note.
4. **P2-4** — decide the moved-punch case: a second row, or refuse the reassignment.
5. **P2-5** — two real scope tests against the new DocType.
6. **P2-6** — the 4 page-count commits land before the switch is ticked anywhere, and one
   two-page test that uses direct punch changes.
7. **P3-7** — use the casting accessor in `_moved`. One line.
8. Write down, with an owner: the volume consequence (§5), the sync-login bypass (P3-9),
   the switch-off orphan rows (P3-10), and the expiry ticket `03c` already names.

**`SHIP` was not available here, and it would not have been permission to deploy in any
case. The decision to ship is Surbhi's, not mine.**

---

# 088c · senior architect review, round 2

```
reviewed: same worktree, branch docs/088-notice-scope-analysis, head 350a7a12 (was 3d4591d4)
new commits: bccf8f77, 6ac59220, 350a7a12 — diff read in full (12 files, +1607/-75)
base: still origin/main 7ebc5898, not rebased. origin/dev has moved to 2558540b; I did not
      read it and I did not need to — the coordinator says it touches none of these files
      (not checked by me)
ran: py_compile on all 5 changed Python files — clean. JSON valid. Test-method counts
     recounted. Frappe 16.33.x source re-read read-only out of the running alv436rel-bench
     with grep/sed only. NO test suite, no bench, no site. See "what I could not run".
```

## Verdict: SHIP WITH FIXES

Split in two, because the two halves have different answers:

- **Clear to land on dev.** The blocker is properly fixed, and fixed in the one place that
  writes the date rather than patched where the tests look. Nine of my eleven findings are
  closed, several with better tests than I asked for.
- **Not clear for any tenant to tick the switch.** That still waits on the 4 page-count
  commits reaching main, which is Surbhi's call and not in this branch.

Four one-line fixes are worth taking in one more pass (R-1 to R-4 below). None of them
blocks the dev landing, because the switch is off everywhere.

## P1-1 is closed, and closed correctly

**Proven.** `punch_change.py:161` now writes `"day": getdate(shift_day(doc))`.

I checked the three things that could have made this a patch rather than a fix:

1. **Is `shift_day` resolvable there?** Yes. `write_log` is `on_update`, which runs after
   the controller's `validate` → `fetch_shift()` (`hrms/…/employee_checkin.py:58`), so
   `shift_start` is set in memory by then. `shift_day` falls back to `time` when it is not
   (`payroll_rules_apply.py:373`), which is the documented ALV-402 behaviour, so a punch
   with no shift is unchanged. The lazy import is safe: `payroll_rules_apply`'s only
   top-level app import is `alvoraa_portal.payroll_rules`, so there is **no cycle** back
   to `punch_change` or `register_notice`.
2. **Every path that writes or reads that date, not only where the tests look.** One
   writer (`write_log`). Three readers, all of the log's `day`: the month filter and
   `from_date` in `_punch_changes` (`register_notice.py:258, :274`), the printed heading
   `_day_words(change.from_date)` in `sheet_rows` (`:552`), and `my_changes`'s
   `"date": str(c.from_date)`, which the screen hands to `rnSeeDay(d.date)`
   (`portal.js:7789`). All three now agree with the engine. **It is also now consistent
   with the request rows**, whose `from_date` is the Attendance Request's working day — so
   the two halves of one notice are dated by the same rule. That was not true before.
3. **Could the test have passed without the fix?** No, and the test says so itself. It
   asserts the fixture first — *"fixture is wrong: the night shift was not matched, so this
   proves nothing"* — then the log's day, then the printed heading. The declared breaks are
   value-level (`'2026-11-21' != '2026-11-20'`, and `0 != 1 : missing from the month that
   was paid`). This is the lesson-2 discipline applied properly: it checks that the data
   could show the behaviour before asserting the behaviour.

## Which of my original findings are closed

| # | Finding | Now |
|---|---|---|
| P1-1 | wrong day on the paper for night shifts | **closed** — above |
| P2-2 | shift re-tag not watched | **closed but one field short** — `shift` and `shift_start` are material; `shift_end` is not. See **R-1** |
| P2-3 | `ignore_validate` switches the rule off | **closed** — `before_validate`, and a test drives `again.flags.ignore_validate = True` with a control proving the same save works with a reason |
| P2-4 | the person who loses a punch is never told | **closed, by refusing the move** — and this is the better answer of the two I offered: a second log row would have told Ravi about a change on Priya's punch, which is a worse thing to put on paper |
| P2-5 | the hollow scope test | **closed** — see below |
| P2-6 | 088c makes two pages ordinary | **half closed, and precisely located.** The server half is now proven: six direct changes print two sheets, `page_count` 2, one photo refused, two accepted. The screen half is untouched — the HR list row still carries no `pages`, so the dialog still cannot ask for two photos. **This stays a release condition, not a code fix here** |
| P3-7 | `_moved` compares uncast values | **open, and its surface grew.** See **R-2** |
| P3-8 | the test-pollution fix and the unproven pair order | **closed** — see below |
| P3-9 | the sync login a person can use | **closed as a disclosure.** The fixture now holds only `Biometric Sync` by default, and one guard-rail test keeps the realistic sync-plus-HR shape on purpose, with a docstring naming it as the shape a person could use. The wording is fixed to "every path through Frappe's document layer except where a script skips it". That is the smaller true sentence |
| P3-10, P3-11 | orphan rows after the switch is unticked; no "nothing recorded before switch-on" line | **open, declared.** Ranked below |
| P3-12 | no `01d`, `04`, `01c` or `07` for 088c | **partly closed** — a `06c` security review now exists and is a real one. `01d` is still only on `origin/dev`; there is still no independent test report |
| P4 nits | `company`, `kind`, the duplicate index, the duplicated `FLAG` | **all four deleted.** Verified nothing read them: `grep` for `kind`/`company` across `register_notice.py`, `punch_change.py`, the DocType and the suite returns nothing, and `_punch_changes`'s field list no longer selects them |

### P2-5, verified rather than taken

The three persona tests genuinely exercise **both** hooks, and I can say which from the
declared breaks: `['PCH-000055'] != []` can only come from the row filter at
`hooks.py:669` being absent, and `True is not false` from `has_permission` at
`hooks.py:696`. `frappe.get_list(..., user=…)` and `frappe.has_permission(..., doc=…,
user=…)` are the two doors the app actually uses. That is the right shape.

One precision point, **P4**: the outsider is `_login("hrfar088c", ("HR Manager",))` with no
Employee record and no Company user permission. `permitted_companies` (`access.py:238-256`)
returns the user-permission companies, else their own Employee's company, else nothing — so
this login resolves to `NO_EMPLOYEES` and `_scope_sql` returns `1=0`. The test therefore
proves **"an HR Manager with no entitlement sees nothing"** (fail-closed), not literally
"HR of company B cannot see company A". The company and branch cases are covered for the
shared `_scope_sql` by the 088 suite's own SEC-1 tests, so the coverage is adequate; only
the comment oversells the persona.

### P3-8, the pair run: the right evidence, and I can check its arithmetic

`Ran 214 tests in 1459.673s` / `OK`. **214 is exactly 80 + 134**, the two suites' test-method
counts, which I recounted myself from the source this session (`grep -c 'def test_'`: 80 in
`test_register_notice_088`, 134 in `test_punch_fix_087`). So the figure is internally
consistent with both suites having run in one process, which is the question I asked. The
switch reading 0 on every company afterwards answers the other half.

**On the throwaway `load_tests` module being deleted: that was the right call.** Keeping a
test harness nobody asked for is exactly what `no-over-engineering.md` §2 forbids, and the
fix it proved lives in the suite's own cleanup. The honest cost is that **CI does not pin
the ordering**, so if someone later deletes the `frappe.db.commit()` from
`_put_the_notice_switch_back`, nothing fails until a punch suite happens to run after the
088 suite. The comment above that line already says why it is there, in plain words. I rank
that residual **P4** and would not build a guard for it.

## What the fixes newly broke, judged

**Two production paths are newly refused, and I enumerated them rather than asserting it.**
Every place in `alvoraa_portal`, `hrms` and `scripts` that saves an Employee Checkin
*document* (grep for `.save()` within three lines of a checkin, plus every `fetch_shift`
caller):

| Path | Effect |
|---|---|
| `punch_fix.py:1080, :1084` (087 undo) and `:1298` (087 approval) | **unaffected** — both inside `in_punch_fix_apply` |
| `alv291_attendance_fix.py:967-970` (retag) | **refused** as Administrator until a reason is given. This is the intended catch |
| `hrms/…/employee_checkin.py:216-222` `bulk_fetch_shift`, called from the Desk list action (`employee_checkin_list.js:12`) | **refused** for a person while the switch is on. Note it sets `ignore_validate` itself at `:222` — Frappe HR's own bulk action relies on the flag, which is precisely why `before_validate` was the right move |
| `employee_checkin.js:31-35` single-form "Fetch Shift" button | **works** — the button only fills the fields in memory; the person's own Save then asks for a reason, which they can give on the form |
| Auto attendance and the scheduler | **unaffected, and this was the big risk.** A scheduled job runs as `Administrator`, which this rule treats as a person. But Frappe HR never saves a punch document: `skip_attendance_in_checkins` and `update_attendance_in_checkins` (`employee_checkin.py:485-500`) use query-builder `UPDATE`s, and `shift_type.py` writes with `frappe.db.set_value` (`:448`, `:483`). So auto attendance cannot be stopped by this rule. Proven by reading all three |
| hrms' own test suites that call `fetch_shift` / `bulk_fetch_shift` | **unaffected while the switch is restored** — which is what P3-8's commit fix guarantees. The two facts are linked: if the switch ever leaks again, Frappe HR's own tests go red too, not just ours |

**Is refusing `bulk_fetch_shift` acceptable?** In substance yes — a bulk re-tag of many
people's punches with no reason is exactly what counsel's rule forbids, and nobody should be
able to move fifty people's days silently. But **the message is wrong for that door**: a
person who ticked thirty rows and pressed "Fetch Shift" is told *"If you are importing
punches or calling the API, fill in 'Reason For This Change' on every row"*, which does not
describe what they did and gives them nothing to do next. The bulk action has no way to ask
for a reason, so it is a **dead button** while the switch is on, not a prompt. That needs one
clause in the message and one line in the release note. **R-3.**

**Three message-order changes, not one.** `03c` names only the geofence. `before_validate`
now also runs before Frappe HR's `validate_active_employee` and `validate_duplicate_log`
(`employee_checkin.py:55-56`), so a duplicate punch or a punch for an inactive employee,
filed by a person with no reason, now says "Pick a reason" first. All three still refuse, so
nothing is unsafe — but note it, because the engineer's own earlier weak test passed on the
duplicate-timestamp error, and this reordering makes that class of confusion *less* likely,
not more. **P4.**

## The remaining items, answered one by one

**Item 6 · the import free-text hole, and whether the flag test is enough.** **Adequate, and
I verified why.** `base_document.py:1101-1103`: `_validate_selects` returns immediately when
`frappe.flags.in_import` is set. Setting that flag in a test does not *approximate* an
import for this check — it takes **the same branch**. And the test proves its own premise
first, by showing Frappe accepts `log_type="SIDEWAYS"` under the flag ("fixture is wrong:
Frappe did not skip the Select check, so this proves nothing"). Two checks now guard it, at
entry and at write time, and the second is tested on its own by handing `write_log` a bad
stash.

What a real import run would add is **not** this hole: it would cover the row-number prefix
in the message (`_("Row #{0}")`), whether the Custom Field is mappable from a spreadsheet
column at all, and what the refusal looks like to the person uploading. Those are import
mechanics and usability, and they are worth **one manual upload** before the switch is
ticked — not another test. **P3, operational.**

**Item 7 · the deletions and the migrate exemptions.** Nothing read `kind` or `company`
(grep, clean). Removing the exemptions cannot wedge a migration today: no patch creates or
deletes a log row (`patches.txt` is untouched), DocType sync does not instantiate documents,
and an uninstall drops tables rather than deleting docs. `test_the_record_cannot_be_deleted_even_during_a_migration`
pins the new behaviour. **The forward-looking cost is real and the security review names it
as F5:** the expiry job counsel's 5-year maximum requires will have to delete rows the
controller refuses to delete, so it will need either `frappe.db.delete` or the module's own
flag — and whichever is chosen becomes the supported way to remove audit rows. That belongs
in the dated retention ticket, in one sentence, so the next person does not invent an
exemption flag casually. **P3, for the ticket, not for this release.**

**Item 8 · refusal logging cannot swallow or replace the refusal. Proven.**
`access.log_refusal` (`hrms/…/access.py:71-93`) wraps the whole write in `try/except: pass`,
and `_refuse` (`punch_change.py:99-103`) calls it and *then* throws unconditionally. So a
broken logger loses the line, never the refusal. And the test behind it is stronger than I
expected: `security_lines_from_a_fresh_process` resets the "security" logger to Frappe's own
default ERROR **before** running the attempt, so a path that never calls `security_logger()`
produces nothing and the test fails. That is the ALV-391 trap closed properly — it proves
the line is really written at a level that writes, not that a function was called.

The exception classes are now split, deliberately and sensibly: punch-level refusals are
`ValidationError` (an ordinary message a person can act on), and tampering with the record
itself stays `PermissionError` via `access.refuse`.

**Item 9 · the weaker break on `write_log`'s second line of defence.** The test now drives
`write_log` directly with a bad stash and asserts `"not one of the reasons"` — that is
`_valid_reason`'s own message from `punch_change.py:148`, raised before the log insert, so it
is **this slice's refusal and not Frappe's**. Reading the code, `_valid_reason` runs before
the `frappe.get_doc(...).insert()`, so the log's own Select check can no longer be what
fires. The break the engineer reported ("Reason cannot be … It should be one of …") was from
the *earlier* shape, where Frappe's Select check was the thing that fired. **Adequate as it
now stands**, and the assertion is on the slice's message, which is the right thing to pin.

**Item 10 · ranking the three unfixed findings now that the rest is closed.**

- **P3-7 (uncast comparison) — now the most worth doing of the three, and its surface grew.**
  `MATERIAL` went from four fields to five, and `shift_start` is a Datetime arriving from the
  API or an import as a string. The two consequences I traced still hold: a `"0"` for
  `skip_auto_attendance` prints *"Punch at 10:00 not counted"* when nothing changed, and a
  cosmetically-different datetime makes `_sentence` return `""`, which fails the punch save
  on the log's `reqd` `what` with a mandatory-field error. The fix is still one line —
  `doc.get_value(f)` and `before.get_value(f)`, which cast per field type. **R-2.** Rank
  **P3**, and do it now because it is cheaper than explaining a false sentence on a signed
  page later.
- **P3-10 (orphan rows after the switch is unticked) — leave, but write the sentence.** The
  cheapest honest mitigation is one clause on the Company switch's description, which is
  configuration, not code. **P3, tracked.**
- **P3-11 (no "nothing recorded before switch-on" line) — leave, Surbhi's call.** It is the
  PM's own option B from `01d` §2 and is display-only, not a backfill. The empty-list trap is
  real but October's changes are not in any notice at all, so there is no screen today where
  a reader could be misled into thinking a month had none. **P4 until a tenant asks.**

## New findings this round — four one-liners (R-1 to R-4)

**R-1 · P3 · `shift_end` is material and is not watched.** The security review's F2 names
three fields — `shift`, `shift_start`, `shift_end`. Two were taken; the third was not, and
`03c` items 4–5 do not say so. `shift_end` on a punch **is** read by the engine:
`held_day.py:300` selects it, `:329-337` carries it per log, and it is handed to
`shift.get_attendance(logs, absent, half)` at `:342`, which decides working hours and
Present / Half Day / Absent. So an API or Data Import write that changes `shift_end` alone
changes what a day counts, with no reason and no row. The escape is narrow — `fetch_shift`
always sets all three together, so no UI or script path changes it on its own — which is why
this is P3 and not P2. **Fix: add `"shift_end"` to `MATERIAL` (`punch_change.py:58`)**, and
either extend the shift sentence or accept that it reuses "Punch shift changed".

**R-2 · P3 · the uncast comparison (my P3-7), unchanged and one field wider.** Above.

**R-3 · P3 · the refusal message does not fit the Desk bulk action.** Above. One clause,
plus a line in the release note so HR is not surprised the first time they use "Fetch Shift".

**R-4 · P3 · a night-shift *addition* prints an ambiguous line.** The day heading is now
right, but `_sentence(doc, None)` returns `"Punch at %s added" % _hm(doc.time)`
(`punch_change.py:197`) — the clock time with no date. So the paper reads
*"20 November · Punch at 00:30 added"* for a punch made at 00:30 on the 21st. That is how
the rest of the product presents a night shift, so it is consistent — but on a page somebody
signs as evidence, the time alone invites the wrong reading. The file already has the helper
for it: `_when(doc.time, <the day>)` prints the date when the two differ. One line.

**One new thing I checked and dismissed:** an edit that moves a punch *across* a shift-day
boundary (HR changes the time from 10:00 to 23:30) writes its log row against the **new**
working day, so the old day's notice says nothing — the same shape as the person-move case.
I am not raising it, for two reasons, both read in source: `hrms.validate_time_change`
(`employee_checkin.py:78-85`) refuses a time edit on any punch with an attendance row, so no
already-decided day can lose a figure this way; and the sentence itself carries the old time
("Punch moved from 10:00 to 23:30"), so a reader of the new day's row can see where it came
from. That is materially different from the person-move case, where the losing side saw
nothing at all.

## The shortest honest statement of what must be true before this lands

**To land on dev:** nothing further. The blocker is fixed, nine findings are closed, and the
switch is off on every company on all six production sites, so no tenant behaviour changes
when this lands. I would take R-1 to R-4 in the same pass because together they are four
lines and one sentence of release note, but they do not block the landing.

**Before any tenant ticks `alvoraa_print_change_notices`**, all of these, and they are not
mine to grant:

1. The 4 page-count commits on `release/088-alv436` are on main. Until then a two-page
   notice cannot be signed on the screen, and 088c makes two pages ordinary.
2. The reason list is signed off by the employer and counsel. It is a draft.
3. Surbhi accepts, in writing, the paper volume: HR's list goes from a handful of people to
   most of the floor, monthly, and a direct change closes only when somebody collects a
   signature.
4. HR is told that "Fetch Shift" on the punch list stops working, and that the sync account's
   password bypasses the reason rule (ALV-386 is the control, not the product).
5. The retention ticket is raised, with F5's tension written into it: whatever enforces the
   5-year maximum must get past an `on_trash` that refuses everybody.
6. One real Data Import of a punch sheet with the reason column is driven by hand, once.

## What I could not run, this round

- **No test suite, no bench, no site.** Every pass/fail figure — the 214-test pair run, the
  36 new tests, the sixteen declared breaks — is the engineer's and is **unverified by me**.
  What I did verify myself: `py_compile` on all five changed Python files, the DocType JSON
  parses, and the test-method counts (36 / 80 / 134 / 50), with 80 + 134 = 214 reconciling
  the pair run exactly.
- **I did not read `origin/dev` 2558540b.** That it does not touch these files is the
  coordinator's statement, **not checked** by me. The branch is not rebased, so slice 091's
  changes are not in anything I read.
- The printed page on paper, a real Data Import, and the Desk forms: **not checked**, as
  before.
- The live switch values and the zero notice records: taken as given, **not checked**.
