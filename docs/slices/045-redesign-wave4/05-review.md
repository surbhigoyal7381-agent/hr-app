---
slice: 045-redesign-wave4
artifact: 05-review
author: hrms-technofunctional-reviewer
date: 2026-09-25
reviewed: `slice/045-redesign-wave4` at `b5d892b`, diffed against `slice/043-redesign-wave3`
  at `5f2b314` — 53 files, +15,100 / −400
---

# Wave 4 — senior architect review (step 5)

## 1. Verdict

**BLOCK**, on one thing, and it is the smallest fix in the slice: **AC-35 was
promised, was not done, and is not written down anywhere as not done.**
`goals_api.get_upward_feedback` is still a live whitelisted endpoint that hands
back individual upward-feedback comments with no minimum group. Delete it (or
declare it with an owner and a date) and this becomes **SHIP WITH FIXES**.

Everything else in this wave is good work, and several parts of it are the best
evidence this programme has produced. Three defects were found by tests going
red first — a heading that counted four people over nine cards, a KPI chip short
of its own list, and a Send that stored nothing — and each fix ships with a test
that was proved able to fail.

`SHIP WITH FIXES`, once F1 is closed, would mean *ready to present for deploy
approval*. It is never itself permission to deploy.

### Where the branch actually sits

| | |
|---|---|
| Rebase state | **Clean. No rebase in progress** (`git status` empty, no `rebase-merge` directory) |
| Wave 4 on Wave 3 | `git merge-base --is-ancestor slice/043-redesign-wave3 HEAD` → **yes**, 0 Wave 3 commits missing, 56 Wave 4 commits on top |
| Against `origin/dev` | **11 commits behind.** Not reviewed here, and it must be rebased and the incoming diff read before any push |

**What came in on `dev` while this branch sat, named rather than absorbed
quietly:** `98f0b7f` user-creation throttle, `b06495d` WhatsApp feature,
`2ed6366`/`1f05f7b` AI lead intake, `60bf410`/`e8b0f49` CI fiscal-year fixtures,
and **`79b53d1`…`42f89c4` — slice 047 / ALV-117, the `Employee Performance
Feedback` row-scope**. That last one matters to this slice: it is the mechanism
this wave's own `01c` SEC-17 demanded before DTC's staff load. It is discharged
upstream, not here, and Wave 4 rebasing onto it is how that stays true.

### What I ran, and what I could not

| Ran, in this worktree | Result |
|---|---|
| `node scripts/run_dom_tests.js` | **8 run, 0 not run, 0 failed.** Wave 3's three never-run files now run |
| `python scripts/check_tag_balance.py` | 2 pages, 18 fragments, **OK** — and `home.html` is back to depth 0, so **Wave 3's F1 is fixed** |
| `python scripts/check_app_integrity.py` | 643 checks, OK |
| `python scripts/check_design_system.py` · `check_preview_flag.py` | OK, OK |

**I could not run a single Python test.** There is no bench in this worktree
(`which bench` → nothing). Every `bench run-tests` figure below is the
engineer's, read from the notes. I did read the test files. I also did not run
`scripts/browser_check_growth_team.js` or `browser_check_self_review.js` — they
need a served site, a real login and Chromium.

**On timings.** This machine's wall-clock is not trustworthy; identical runs
have varied by more than the effect being measured. So I am ignoring §18.3's
millisecond figures entirely and judging on **query counts and payload bytes**,
which are stable and were measured at two sizes. §18.3 should carry that caveat.

---

## 2. Findings, worst first

### P1 — blocks the release

#### F1. AC-35 is not met, and nothing says so

**Proven by reading.** `alvoraa_portal/alvoraa_portal/goals_api.py:1129-1159`:

```python
@frappe.whitelist()
def get_upward_feedback(cycle, employee=None):
    ...
    rows = frappe.get_all("Upward Feedback",
        filters={"about_employee": target, "appraisal_cycle": cycle},
        fields=["rating", "comments", "submitted_on"],
        ignore_permissions=True)
    ...
    return {"count": len(rows), "avg_rating": avg,
            "comments": [r["comments"] for r in rows if r.get("comments")]}
```

**The failure scenario.** A manager in a cycle where exactly one person has left
upward feedback about them calls this endpoint by hand. They get back
`{"count": 1, "avg_rating": 2.0, "comments": ["he shouts at the floor staff"]}`.
In a team of six, the author is recoverable by elimination; in a team of one
direct report, there is nothing to eliminate. `PRIV-12` sets `MIN_GROUP = 5`
precisely for this shape, and `home_api._suppress` already implements it. There
is no minimum here, no suppression, and `ignore_permissions=True` on the read.

**What was asked for**, in three places in this slice's own documents:

* `01c` **PRIV-6** — *"`goals_api.get_upward_feedback:1113`, which has no
  minimum and no caller, is **deleted**"*
* `01c` **SEC-11** — *"each deletion ships in its own commit and is proved
  gone from the whitelist"*
* `02` §appendix D B22, US-16, AC-35 — **"Deleted"**

**What happened.** AC-16, the other half of the same user story, is done and
recorded (`03` §5 table: *"`l2_reports`, `l2_size` — gone"`). AC-35 appears
**nowhere** in `03-implementation-notes.md` or `00-impact-analysis.md` — I
grepped both. It is not in the known-gaps lists in §15.12 or §18.4, which are
otherwise scrupulous. So this is not a declared trade-off; it is a requirement
that fell out.

**Smallest fix**, and it is genuinely small: delete the function in its own
commit, with the call-by-hand test AC-35 asks for (`getattr(goals_api,
"get_upward_feedback", None)` is gone, and a whitelist lookup raises). If it
must stay, route it through `home_api._suppress` with `MIN_GROUP` and record
that as the answer to AC-35 instead.

**Honest caveat on the ranking, and it is a must-know question.** This endpoint
is **pre-existing** — Wave 4 did not create it and did not widen it. Whether it
is a live exposure or only a paperwork miss depends on whether any
`Upward Feedback` rows exist on `dtc.alvoraa.co` and `aahr.alvoraa.co`, and
**I could not check that**: no bench, no site access. If the doctype is empty on
both tenants, this drops to **P2** and can ship with a written owner and a date.
If it is not empty, P1 is right. One read-only count answers it — the same shape
of census the security engineer had run for SEC-17.

**Ranked P1 provisionally**, because an undeclared missing privacy control is
the failure mode this programme has paid for more than once, and because the
appraisal cycles that create these rows are scheduled for the same October
window as the staff load.

---

### P2 — needs a fix or a written acceptance before release

#### F2. A Send goes through after a save that did not happen

**Proven by reading.** `public/js/ess/next-growth.js:609-628` (`doSend`) and
`:635-668` (`save`).

`save()` returns a **resolved** promise on two paths that are not successes:

```js
if (roomLeft() < 0) { showRoom(ctx); return Promise.resolve(); }   // :644
...
.catch(function (reason) {
   lastSent = "";
   ctx.toast(refusalSentence(reason) || words(ctx).cardFailed, "bad");  // :660
});
```

and `doSend` chains straight on:

```js
save(ctx).then(function () {
  return ctx.api(SUBMIT, { appraisal: review.appraisal, overall_comment: "" });
})
```

**The failure scenario.** Rahul is on the last step. He goes back, changes a
goal from 3 to 5, returns, and presses Send. The autosave POST fails — a stale
CSRF token from a desk tab, or a dropped connection on a shop-floor phone. A red
toast flashes for four seconds; then `SUBMIT` runs anyway, the server reads the
`page_data` it already had, stores **3**, and the screen paints *"Sent. Your
manager has your review now."* His manager reads 3 in the calibration meeting.

**Why that is wrong.** This is exactly the silent Send AC-96 exists to catch, in
the one place AC-96's test does not look. The server-side check
(`refuse_if_unfinished`) catches a **missing** rating; nothing catches a **stale**
one. AC-96's test (`test_the_stored_answers_read_back_equal_to_what_was_posted`)
posts and then sends, so the browser's save/send ordering is never exercised.
The over-budget path at `:644` is the same shape: the person is told there is no
room, and the Send proceeds regardless.

**Smallest fix.** Make `save()` reject on both paths; `doSend`'s existing
`.catch` already re-enables the button and shows the server's sentence, so the
person stays on the wizard. One DOM test: make the save call fail, press Send,
assert `SUBMIT` was never called and the screen does not say "Sent".

#### F3. A required step whose answers nobody ever reads

**Proven by reading, in two files.** `growth_api.py:732`:

```python
REQUIRED_STEPS = (STEP_GOALS, STEP_VALUES)
```

so `refuse_if_unfinished` will not let a review be sent until **every active
company value** carries a rating. And `03` §15.11b's own known-gaps list:

> the manager's screen still does not draw the wizard's value ratings … the
> company-value ratings and the "still open from last time" note **travel in the
> payload and are not drawn**

pinned by `test_the_manager_receives_what_was_sent`, which asserts
`assertNotIn("wizard", json.dumps(payload.get("page_config")))`.

**The failure scenario.** Rahul is blocked from sending until he rates six
company values on a phone. Nobody — not his manager, not HR, not a later screen
— ever sees those six numbers. He is being made to do work with no reader.

**This is not a code defect; it is a decision that has drifted.** The debt itself
is named honestly (see §3 below — AC-99 is one of the better-written ACs in this
programme, and the notes say plainly that it is not fixed). What nobody appears
to have joined up is that the *required* half and the *invisible* half are the
same step.

**Two ways out, and this one is Surbhi's, not mine.** Either draw the wizard's
value block on the manager's review screen before this ships, or take
`STEP_VALUES` out of `REQUIRED_STEPS` — which the code is built for: it is one
line, and the refusal sentences, the screen's blank-step list and the tests all
read that tuple. **My recommendation: make it optional until it is drawn.**

---

### P3 — ship, with an owner

#### F4. The eleven server checks have no production caller

**Proven by grep.** `team_api.may()` is imported by two test modules and nothing
else. `next-team.js` never calls it; no other Python module imports it. On the
screen an action is a navigation — `ctx.go(GOES_TO[act])` at `next-team.js:243`
— to the inbox or the growth panel, both of which enforce their own rules.

So **nothing is unguarded today**, and the derivation half of SEC-18 is properly
done: there is no `section` or `basis` argument anywhere (asserted by signature
*and* by `test_passing_a_section_anyway_changes_nothing`), and
`test_moving_reports_to_moves_the_person_between_sections` proves the derivation
is live rather than a constant. That is a good, complete piece of work.

What is not true is the module docstring's claim at `team_api.py:51-52`:

> Each one is enforced here **AND by the endpoint behind it**

Six of the eleven have no endpoint behind them at all — the person sheet is not
built. And SEC-18(a) asks for the eleven rows *"called by hand"*; what the tests
call by hand is the matrix helper, not the endpoints. So the matrix is today a
very well-tested **display** rule.

**What to do:** correct that sentence, and write into the person-sheet ticket
that `may()` becomes the gate on each new endpoint and that the test calls the
endpoint, not the helper. **This is a P1 for the slice that builds the person
sheet.**

#### F5. "You cover" can draw fewer rows than it has slots — or none

**Proven by reading.** `team_api.py:208-222`:

```python
fetched = frappe.get_all("Employee", filters=conds, ...,
                         order_by=order_by, limit=TEAM_LIST_CAP * 2, ...)
kept = [r for r in fetched if r.get("reports_to") != exclude]
rows = [{k: r.get(k) for k in ROW_FIELDS} for r in kept[:TEAM_LIST_CAP]]
```

with `TEAM_LIST_CAP = 50`, and the comment *"at most `cap` of the fetched rows
can be direct reports"*. **That is not true.** The direct-report *section* is
capped at 50; the number of people who actually report to the caller is not.

**The failure scenario.** Kamal is store HR for a 300-person store and also line
manager of 120 of them. `fetched` is the first 100 names alphabetically in his
HR scope. If more than 50 of those 100 report to him, "You cover" draws fewer
than 50 cards; if all 100 do, it draws **zero** — while `total` (a correct
subtraction of two equality counts) says 180 and `has_covered` is true. The
heading then reads *"You cover — showing the first 0 of 180"* over an empty
list. The totals are right; the list is wrong.

The `!=`-on-a-nullable-field reasoning that led here is **correct and well
documented** — that defect (nine cards under a count of four) was real and the
fix is right. Only the bound is wrong.

**Smallest fix:** page the read until 50 are kept, or read `limit=None` with a
`limit_page_length` and slice — anything that does not assume the excluded set
is smaller than the page.

#### F6. The whole-Employee-row guard still scans three files

`tests/test_payslips_payload_043.py:167-169` lists `hr_api.py`, `pay_api.py`,
`time_api.py`. Wave 4 added `team_api.py` and `growth_api.py` — two new modules
whose whole job is building payloads about people — and neither is scanned.

Today neither offends: I read both. `team_api` builds rows key-by-key from
`ROW_FIELDS` and the caller block from `me_block`, and `growth_api` has no
Employee row in a payload at all. **Lesson 5 held and no fifth was added** — one
was paid off (`get_manager_dashboard` is out of `KNOWN_PRE_EXISTING`, correctly).

But this was raised as a P4 in Wave 3's review and stayed, and it now costs more.
Two lines in `_wave_three_sources`.

#### F7. The wizard had no design pass, and here is what that costs

You asked me to judge this. **The decision to ship without one is defensible —
the wizard works, the server owns every rule, and nothing on it is a lie.** Four
specific things a design pass would have caught, on a once-a-year form filled in
on a phone:

1. **Focus is thrown away on every rating tap.** `next-growth.js:557` calls
   `paint(ctx)` after each rating, which replaces the screen's markup and
   re-wires it. With five goals and six values that is eleven focus resets for a
   keyboard or screen-reader user, and eleven jumps to the top of the card on a
   phone. No test covers focus after a rating. **This is the one I would fix.**
2. **Three identical buttons, one of them irreversible.** Back, Next and Send
   are all `nf-btn` — acknowledged in the code comment at `:355-360`, because
   the stylesheet has no primary variant. A mis-tap sends a review.
3. **"Step N of 5" does not move while you answer.** Declared, and the reasoning
   (do not keep a second copy of the server's rule in a browser) is right. But a
   counter that does not move reads as broken. The honest fix is named in the
   notes — return `steps_answered` from the save — and it is small.
4. **The values step is never driven in a real browser.**
   `browser_check_self_review.js:196-203` writes the value ratings straight into
   `NextGrowth._state().answers` and then clicks Send, so the rating control on
   that step is jsdom-only. Lesson 8.

None of these blocks a release. Together they are the argument for the design
pass happening before the wizard meets four hundred people, not after.

---

### P4 — backlog

* `01c` **SEC-15** — `hr_api.get_employee_detail_for_manager:1428` is still a
  second whitelisted person-sheet door with the over-wide field list. SEC-15's
  own condition ("in the same slice" as the person sheet) correctly did not
  trigger, because the person sheet was not built. Carry it into the
  person-sheet ticket rather than leaving it in a `01c`.
* `team_api.relationship:291` filters `conds` for a `reports_to != …` condition
  that `covered_conditions` never produces. Harmless, but it reads as though the
  exclusion exists in SQL, which is the opposite of what `_section`'s docstring
  spent forty lines explaining.
* `get_manager_dashboard`'s `IN (...)` of drawn ids survives (`03` §1 bad-news 2).
  Declared, with a reason, and the function is superseded by `team_api`. Agreed.

---

## 3. AC verification

Only rows where I disagree with the notes, or where the evidence deserves a
word. The rest I read and agree with.

| AC | Notes say | I find | Evidence |
|---|---|---|---|
| **AC-35** (delete the minimum-less upward-feedback endpoint) | *silent* | **not met, and not declared** | F1. `goals_api.py:1129` is still whitelisted |
| AC-16 (dead `l2_*` keys) | met | **met** | Gone from the payload; `test_team_scope_034:388` asserts absence |
| AC-6 (fixed key list, `me` block) | met | **met, and well** | `me_block` reuses `frame_api.ME_FIELDS` rather than re-typing them; the fixture populates all six forbidden fields and the assertion searches the serialised payload recursively |
| AC-14 (scope as a subquery) | partial, declared | **partial, correctly declared** | `direct_reports_query` is a real subquery; `on_leave_today` still sends an `IN (...)` of drawn ids. Bounded by the page, not by the company |
| AC-76 (a colleague's leave reason) | met | **met, and this is the best privacy work in the wave** | `_pending_leave_for_approver` does **two reads** so `leave_type` and `description` are absent from the `fields` list on a non-report row, not blanked afterwards. A field removed after the query is a field that was read |
| AC-82 / SEC-19 (`alvoraa_decided_as`) | met | **met** | Derived server-side; `request_fields()` asks the schema so a deploy that skipped migrations degrades to a working read instead of a blank screen. That is a good anticipation |
| AC-84 / SEC-4 (never an empty filter) | met | **met** | `covered_conditions` always carries `status = Active`; `_own_scope_filters` returns `NO_EMPLOYEES`, never `{}`; both directions tested |
| AC-87 to AC-98 (Send) | met | **met** | See §5 |
| **AC-96** | met | **met, and proved the right way** | `test_the_stored_answers_read_back_equal_to_what_was_posted` compares the **whole** posted object against `get_self_review`'s `answers`, then compares every stored `self_rating` against the on-screen number, and `test_the_assertion_can_fail` proves the row was unrated first. The proof is in the tests, not only in the notes |
| AC-99 (the manager receives it) | partial, declared | **partial, and honestly written** | The AC text itself says the value ratings are not drawn, and the oracle is *"the payload keys, plus a named entry in §12 — not a promise that the screen shows them"*. That is how a declared limitation should be written. See F3 for the consequence nobody joined up |
| AC-54 (no `ignore_permissions` in the new modules) | partial, declared | **partial, correctly** | One pre-existing flag in `company_values_for:193`, scope-checked first. §18.5 states it plainly and refuses to guess which fix the AC wanted. Right call |
| SEC-18 (eleven server checks, section derived) | met | **derivation met; enforcement is display-only** | F4 |
| SEC-16 (escaping on the new panels) | met | **met** | `NASTY = '<img src=x onerror=alert(1)>'` drives the Growth and Team DOM tests. I ran them: 75 passed |
| SEC-17 (`Employee Performance Feedback` row-scope) | out of scope | **discharged upstream** | Slice 047 / ALV-117 landed on `dev` (`79b53d1`…`42f89c4`) with `feedback_access.py`, two hooks and 918 lines of tests. Wave 4 must rebase onto it |

### The People directory — the three questions asked

**Is the reversal really one line?** **Yes, proven.**
`staff_api.DIRECTORY_SCOPE_FOR_EMPLOYEES = "own_company"` selects between two
branches that are **both implemented**, and
`test_one_constant_reverses_the_decision_to_store_only` sets the constant and
asserts the scope really moves — with a positive control first (*"the wide scope
does not contain the other store, so narrowing it would prove nothing"*). That
is a switch, not a comment.

**Does an unknown value fail closed?** **Yes, proven.**
`dict(_SCOPE_FIELDS).get(...)` returns `None` for anything unknown and
`_own_scope_filters` returns `NO_EMPLOYEES`, which `get_staff_list` then refuses.
`test_an_unknown_value_in_the_constant_fails_closed` sets `"own_planet"` and
asserts a `PermissionError`. The docstring says why falling back to
`own_company` would be the worse failure, and it is right.

**Is the count honest?** **Yes.** `get_all` and `db.count` take the same filter
dict, and every condition in it is `=` or `like` — no negation, so Frappe's two
query paths cannot disagree. Lesson 3 held. `test_the_count_equals_the_list_it_is_the_total_of`
asserts it directly.

**One thing to note without calling it a finding:** the new `work_email` key is
a genuine visibility widening — a field that used to reach HR now reaches every
employee in the company. It is spec'd, it is the one work-shaped contact field
in the model, the reasoning about NDAs in `staff_api.py:65-81` is correct
(an NDA binds the person looking, not the employer's duty to the person looked
at), and no phone number ships because none exists. Recorded as a widening, with
its decision attached, which is exactly what should happen.

---

## 4. The seven dimensions — the impact analysis's claim beside my finding

| Dimension | Claimed | I find | Note |
|---|---|---|---|
| Performance | improves | **improves, proven on counts** | `get_growth` 7, `get_team` 3/6, `get_staff_list` 2/3 — **identical at 20 people and at 981**, `queries_min == queries_max` over 20 repeats. The employee directory's extra query is one `get_value` on the caller's own row: constant, not per person. This is the evidence; the milliseconds are not |
| Security | improves | **improves, with F1 outstanding** | A whole Employee row removed from the Team payload, raw SQL replaced, the leave reason withheld at the read. Against that, one required deletion did not happen |
| Reliability | neutral | **improves slightly** | `request_fields()` degrades a missing column to a working read; `hr_may_act_from`'s loop is bounded by its own 30-day holiday window (I checked — `window_end` is used at `:916`); notification failures do not fail a send |
| Scalability | neutral | **neutral, with F5** | Flat in headcount everywhere measured. The one unbounded shape is `_section`'s `cap * 2` assumption |
| Maintainability | improves | **improves** | The matrix as data rather than branching is the right call, and it is what made an eleven-row test possible |
| Data integrity | improves | **improves** | The Send writes through `set_item_rating`, which stores the basis figures the person was looking at — so a later edit to a goal cannot retro-change what was rated. `test_nothing_outside_the_review_is_written` snapshots the whole `Individual Goal` and `KPI` rows before and after |
| Compliance / privacy | improves | **improves, with F1** | See §5 |

---

## 5. Compliance verification

| Obligation | Mechanism in the diff | Test that proves it | Verdict |
|---|---|---|---|
| Purpose limitation — a colleague's leave reason | `_pending_leave_for_approver` reads `leave_type`/`description` only on an own-report approval row; two queries, not one and a blank-out | `test_leave_privacy_045.py`, asserted against the serialised payload by value | **discharged** |
| DPDP minimisation on the Team payload | `ROW_FIELDS` + `me_block`, replacing a whole Employee row | recursive key and value search over the real payload, with the fixture populating all six forbidden fields | **discharged** |
| **Minimum-group suppression on feedback** | **none on `get_upward_feedback`** | — | **not discharged.** F1 |
| Audit — who approved, and in what capacity | `alvoraa_decided_as`, derived server-side, survives a later `reports_to` change | `test_decided_as_045.py` — including a request that supplies `decided_as` and is ignored | **discharged** |
| A refusal must not be an oracle | one `REFUSAL` constant in `team_api`; `staff_api._refuse` for feature-off, no-scope and Guest alike | `test_the_refusal_reads_the_same_whichever_the_cause`, two causes compared byte for byte | **discharged** |
| Subject access — the employee sees their own record | Growth reads the caller's own goals, KPIs and review; no `employee` argument anywhere on the panel | per-persona payload tests | **discharged** |
| Decision record replayable from stored inputs | `self_basis_actual` / `_target` / `_weightage` stored with the rating | asserted against a `before` snapshot | **discharged** |
| Retention | no new DocType, no derived store, two custom fields both outside PRIV-10's scope | `03` §15.12 | **discharged** |
| Feedback row-scope before the staff load (SEC-17) | **not in this diff** — landed on `dev` as slice 047 | `test_feedback_access_047.py`, 841 lines | **discharged upstream.** Rebase is what keeps it true |

**No AI in this slice.** PRIV-13 asks for a static check that no Wave 4 module
imports a model client; I read both new modules and there is none. The
AI-specific axis does not apply.

---

## 6. What to delete

* **`goals_api.get_upward_feedback`** — F1. This is the deletion the slice
  already agreed to.
* Nothing else. This wave built less than it was asked to in two places (the
  person sheet, the design pass) and said so both times.

---

## 7. What was done well

* **A test was believed over two people who disagreed, and it was the test that
  was wrong.** §15.11b: the engineer's browser run said the draft survived a
  reload; the analyst, reading the code, said it could not. Both were reported,
  the run was repeated with `page.reload()` and a window marker proving the
  document was really thrown away — and the analyst was right. The marker
  (`browser_check_self_review.js:58-60`) is now the pattern: **every reload in
  that script proves it reloaded.** That is lesson 1 turned into a mechanism.
* **A browser check that fails rather than skips.** `up.rates >= 5` is asserted
  before anything else, and the script exits 2 rather than 0 when it cannot run.
  Wave 3's F5 was a script that skipped itself and read as a pass; this one
  cannot.
* **The count-versus-list defect was found by asserting it, not by guessing.**
  Nine cards under a heading that said four, because five people in a shop have
  no manager recorded and `frappe.db.count` and `get_all` disagree about NULL on
  a `!=`. The fix does the subtraction in Python on two equalities rather than
  bending the SQL. The same defect was then found and fixed a second time, in
  `goals_api`'s KPI chip. **Lesson 3 held twice.**
* **The fixture owns its roles, its companies and its people.** `own_user`
  *asserts* that the login holds no role the fixture did not give it, and the
  second company is backdated so it cannot hijack another suite's default. The
  comments record exactly which earlier failure each line is paying for.
* **The old decision's tests were found and turned over, with the reason in the
  docstring** rather than quietly deleted —
  `test_a_plain_employee_is_refused` became
  `test_a_plain_employee_now_gets_their_own_company`, naming D-10 and the date.
  Lesson 9.
* **Three page fragments pinned at 0 in the tag-balance check, with the reason
  why 0 is the number the file *is* rather than the number that made it pass.**
  Lesson 11, and Wave 3's F1 is closed.

---

## 8. Confidence

* **Proven** (I read the code or ran the command): F1, F2, F4, F5, F6, the
  People-directory answers, the DOM and static-check results, the tag balance,
  the branch positions.
* **Read, not re-run:** every `bench run-tests` figure, and the §11/§18
  measurements. There is no bench here.
* **Inferred:** F3's claim that nobody reads the value ratings rests on
  `page_config` not knowing the `wizard` key, which the slice's own test
  asserts, plus my reading that no other screen consumes them.
* **Not checked:** whether any `Upward Feedback` row exists on the two live
  tenants — this is what decides F1's rank. Also not checked: both browser
  scripts, the Hindi wizard path, and anything needing a served site.
* **Unreviewable here:** whether the wizard is usable on a real phone. There is
  no design artifact for it by decision, so there is nothing to compare the
  built screen against. That is a gap in the inputs, not a finding in the code —
  but it does mean this slice has **no reviewable UX axis**, and F7 is the best
  I can do by reading.

---

## 9. The questions I would put to you, must-know first

1. **Are there any `Upward Feedback` rows on `dtc` or `aahr`?** (F1) One
   read-only count. Empty on both → F1 drops to P2 and the wave is
   SHIP WITH FIXES today. Not empty → P1 stands, and the deletion goes in first.
2. **The company-values step: required, or drawn?** (F3) I am reading the
   product as "Rahul must rate six values that nobody will ever read". If that
   is intended for a later wave to draw, make the step optional in the meantime —
   one line. If the manager screen is being fixed this week, leave it required.
   **Ranked P2 provisionally**, on my reading.
3. **Should a failed autosave stop a Send?** (F2) I am assuming yes — that is
   what US-21 is about. If you would rather Send always goes through and the
   person is warned, say so and it becomes a wording change instead of a
   behaviour change.
