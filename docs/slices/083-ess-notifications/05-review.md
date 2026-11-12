---
slice: 083-ess-notifications
artifact: 05-review
author: hrms-technofunctional-reviewer
date: 2026-11-12
reviewed: branch `slice/083-ess-notifications`, HEAD **`e8ccc232`** (the task named
          `45e9b1c7`; a ninth commit from the parallel security review landed while I
          read — see §0), rebased on `origin/dev` `75149184`
inputs: [00-impact-analysis.md, 01-product-brief.md, 01a-ux-opportunities.md,
         01b-ux-design.md, 01c-security-privacy-requirements.md, 02-functional-spec.md,
         03-implementation-notes.md, 07-devops-inputs.md §1–4, 08-dtc-counts.md,
         prototype-v1.html, git diff origin/dev...HEAD (27 files)]
note: no 04-test-report.md exists. See M3.
---

# 083 · Senior architect review

## Verdict

**BLOCK — two one-line front-end faults mean two acceptance criteria are not met, and
both are invisible to the test suite by construction.** Everything else in this slice is
in good shape: the server change is small, correct and genuinely well tested, the
riskiest write is bounded on both terms with three independent assertions, and I
reproduced the permission doors myself. **Nothing here is a rethink.** Fix `position:static`
→ `position:relative` on one CSS rule, delete one branch in `hmPaintPending`, re-run, and
I would say SHIP.

To be plain about what BLOCK means here: it is not "this is dangerous". It is "AC-2 and
AC-23 are not met, the fixes are two lines, and shipping them unfixed puts a stray number
in the corner of every desktop screen at two live tenants in their go-live month".

**What I ran, and what I could not.** I ran all 24 jsdom suites (exit 0, 24 run, 0
failed; the 083 file alone: 80 passed, 0 failed) and all nine static gates (all exit 0). I
reproduced seven Frappe doors on `Notification Log` myself, in the
`a83-bench` `test_site`, as a plain `Employee` login and as the row owner, read-only with
a rollback — output in §8. **I did not run the Python suite** (it writes to another
session's bench) and **I have not seen this page in a browser**, which is exactly why B1
is in this review and not in the test report.

---

## 0 · Process and incoming work, first

**The impact analysis exists and is unusually honest.** Its seven-dimension table (§282–288)
matches the code that was written, with one exception I am raising as a finding: it calls
Scalability **neutral**, and the new read is unbounded in rows (see m1). Everything else —
Performance *degrades, accepted*, Security *improves*, Data integrity *improves* — I
checked against the diff and agree.

**Three things moved while this slice was being built, and only two were named.**

| What came in | Named by the engineer? | Does it touch this slice's files? |
|---|---|---|
| `37d921ec`, `dcd9353f`, `0afd3f45` + 3 docs commits — ALV-318/319, the joiner role | **Yes**, §7 of `03`, with the `hooks.py` diff read | No |
| `7e663d7f`…`75149184` — ALV-326 shift hours, ALV-329 grooming test clock, ALV-309 | **No.** `03` §7 stops at `dd609e0d` | **Yes.** `portal.js` (+34), `test_grooming_066.py` (+94), `test_inbox_counts_034.py` (+50) |
| `e8ccc232` — the parallel security review's own commit, on this branch, during my run | n/a | **Yes.** `test_notices_076.py` (+37) |

Proven: `git merge-base --is-ancestor` says all of `37d921ec dcd9353f 0afd3f45 dd609e0d
75149184` are ancestors of HEAD; `git log HEAD..origin/dev` is empty; the tree is clean.
Nothing of anyone else's was lost. But **`03` §7's claim "no file this slice changes was
touched by those six commits" is now stale** — ALV-329 rewrote the very `Case.setUp` and
`_wipe()` this slice edits. The four green suites the task reports were run on the current
base, so this is a documentation correction, not a re-run request. Say it out loud rather
than let the artifact stand.

`e8ccc232` is good work and I reviewed it: it adds the positive anchor to the link-search
door (`assertIn(self.mine, names)` — without it the check could not fail if link search
ever returned nothing), clears `frappe.response` before the export door, corrects a
docstring that named the wrong assertion, and adds the two SEC-6 tests nobody had written,
proved by breaking them. All three faults it names are real; I had the first of them in my
own draft.

---

## 1 · Blockers

### B1 · P1 · The desktop badge is drawn on the navbar, not on the bell — and no test can see it

**Proven from source; not rendered (I have no browser).**

- `frame.css:422` — `.nf-bell.nf-bell-set{position:static;margin-right:8px}`
- `panels.css:1496` — `.notif-badge{position:absolute;top:-4px;right:-4px;…}`
- `frame.css:30` — `nav.navbar{position:fixed !important;top:0;left:0;right:0;z-index:1100}`
- `nfHomeTheBell` in `portal.js` inserts `#nf-bell` before the avatar's `<li>`
  and adds `.nf-bell-set`
- `hrms-employee.html:80` — `portal.js` is loaded with `defer`, so the server-rendered
  navbar (`frappe/templates/includes/navbar/navbar_login.html:6` carries
  `a.nav-link.nav-avatar`) is in the DOM when `nfHomeTheBell` runs

**Failure scenario.** An HR Manager signs in on a laptop. `nfHomeTheBell` finds the
avatar, moves the bell into Frappe's navbar and sets `.nf-bell-set`, which makes the bell
`position:static`. The badge is `position:absolute`, so it resolves against the nearest
*positioned* ancestor. Going up from the bell: `ul.navbar-nav` (static) → the collapse div
(static) → `div.container` (static) → **`nav.navbar`, which is `position:fixed`**. The
number is therefore painted 4 px above and 4 px to the right of the whole fixed top bar —
the top-right corner of the viewport, partly off-screen — and **the bell itself carries no
visible count**. AC-2 ("the badge is drawn **outside** the bell glyph at its top-right
corner, 18 × 18 px") is not met on the only path a browser takes.

**Why the suite is green anyway, and this is the important part.** The jsdom harness loads
`www/hrms-employee.html` alone, with no `templates/web.html` wrapper and therefore no
`.navbar`. So `nfHomeTheBell` returns early, `.nf-bell-set` is **never added**, and all 80
assertions — including the two about the badge — run against the `position:fixed` fallback,
the one case where the badge is correct. The evidence could never have shown the
behaviour.

**Smallest fix.** One word: `.nf-bell.nf-bell-set{position:relative;margin-right:8px}`.
Then confirm it in the browser pass that is already a release gate. (The phone bell is
fine — `.mob-notif{position:relative}` at `panels.css`. The sidebar badge is fine —
`.nav-badge` uses `margin-left:auto` inside `.nav-item`, which is `position:relative`.)

### B2 · P1 · For a CXO, Home says "278 waiting" and the bell says 4 — the exact drift this slice exists to remove

**Proven. I ran it.** I copied the slice's own jsdom harness, added a probe to the CXO
payload the test already uses, and read all three surfaces on one load:

```
PROBE cxo: home chip   = "278 waiting"
PROBE cxo: bell badge  = "4"
PROBE cxo: page head 1 = "3 waiting on youcounts by kind"
```

(Run in the worktree against the real `portal.js`; the probe file was deleted, the tree is
clean. The 80 real assertions still passed in the same run.)

**Where it comes from.** `portal.js` in `hmPaintPending`:

```js
var total = hmIsCxo() ? rows.reduce(function (n, v) { return n + v.count; }, 0) : ntWorkOwed(d);
NT.work = ntWorkOwed(d);
```

The CXO branch is pre-existing and sums the per-kind counts (214 + 63 + 1 = 278).
`ntWorkOwed` for a CXO counts **kinds** (3), which is what AC-49 requires of the badge.
So the chip and the badge are computed from two different definitions, for one persona,
on the same payload.

**Why this is a blocker and not a nit.** AC-23 is explicit: *"Given any payload, then the
Home chip and the bell show the same number on the same load."* It is not met. The slice's
own headline promise — "one number, no drift" — fails for the persona most likely to be
demonstrating the product. At DTC that is 2 System Manager logins (`08-dtc-counts` §5);
small, but these are the two people who show the portal to other people. And the CXO case
in the test file asserts only the badge, so the suite walked straight past it.

**Smallest fix — a deletion.** Drop the ternary:

```js
var total = ntWorkOwed(d);
```

The CXO chip then reads "3 waiting", matching the badge, the page heading and AC-49's own
reasoning. One line shorter, and one fewer definition of "work owed" in the file.

**Question that could downgrade this** (must-know, Q1 in §9): if Surbhi decides the CXO's
Home chip is *meant* to say 278 because a CXO wants volume, then B2 becomes a Minor
wording gap plus an undeclared tenth departure, and AC-23 needs rewording. Until somebody
says, I am ranking it a Blocker, and I say so as provisional.

---

## 2 · Majors

### M1 · P2 · Nothing at DTC can show half of what this slice does, including its riskiest line

`08-dtc-counts.md` §1 is unambiguous and the engineer quoted it: DTC holds **zero** rows of
all three notice kinds. Consequences nobody has written down as release behaviour:

- the notices group is permanently the empty state ("You have read everything.");
- "Mark all as read" **never appears**, because `nfPaint` only draws it when `unread` is
  non-zero (`nfPaint`, the notices group's head);
- `mark_all_seen` — the write the whole security case is built around — will match zero
  rows at DTC, so **production can never confirm it works, only that it did no harm**;
- the badge is work-owed only, which means the number people learn to trust is the one
  half of it that *is* exercised.

This is not a code defect. It is a release fact and a verification gap. **What I would
require before release:** (a) tell DTC the notices half will look empty, before they find
it (the engineer already flagged this as "a product fact worth stating"); (b) prove
`mark_all_seen` once on a seeded tenant — PPJ or a throwaway — with the three assertions'
shapes present in real data, not only in fixtures. This is slice 028's lesson verbatim: ask
what must be true in the data for the claim to be observable, and at DTC the answer is
"nothing here could have shown it".

### M2 · P2 · SEC-5 asked for six doors; the test has five. I proved the sixth is closed

SEC-5 names six assertions and explicitly includes
`has_permission(..., "share", doc=<colleague's row>)`; `data-doors.md` row 6 says sharing
opens a record to anyone. `TestTheDoorsToSomebodyElsesNotices` covers the list API, a
hostile filter, `reportview.get`, `reportview.get_count`, three `frappe.client` readers,
`export_query` and link search — **but not share, and not `get_count` with
`reference_doctype`.** The requirement is not discharged.

**I reproduced the share and write doors myself** (§8): as a plain `Employee` login,
`has_permission` is `False` for share, write, delete, read, email, print, export and
report on a colleague's row; `frappe.share.add` raises `PermissionError: No permission to
share Notification Log …`; `frappe.client.set_value` raises `PermissionError`. So **there
is no exposure** — this is a hole in the canary, not an open door. Two lines close it, and
the canary is the entire point: `Notification Log` grants role `All` `read`, `report`,
`export`, `print`, `email` **and `share`** (I read the DocPerm row), so the only thing
standing between a plain login and 597 colleagues' notice subjects is Frappe's own
`get_permission_query_conditions` and `has_permission` — code that moves on every upgrade.

The parallel security review is editing this file as I write; it may land these two lines
itself.

### M3 · P2 · The artifacts now say the opposite of the truth about the riskiest code

`03-implementation-notes.md` says, in its header and in §5, §6 and G-1: *"The Python suite
did not run… I wrote 23 new Python assertions and have not seen one of them execute"*, and
G-2: *"AC-55's six-door list is not written — dangerous debt, escalating"*. Both have since
happened — `45e9b1c7` writes AC-55, and the task reports four suites green on a fresh site
today. **And there is no `04-test-report.md` in the slice folder at all** (`ls` confirms:
the directory jumps from `03` to `07`).

A reader going by the artifacts would conclude that a write which can silently clear other
people's notifications has never been executed. That is the opposite of the current state,
and it is the sort of mismatch that gets a slice shipped on a wrong belief in either
direction. **Fix:** write `04-test-report.md` with the four suite results, the fresh-site
detail, and the fact that the guard was proved by breaking it; correct `03` §5, §6, G-1,
G-2 and §7's "no file was touched" line.

---

## 3 · Minors

**m1 · P3 · The second read is unbounded in rows, on every page load, and no test can see it.**
`notices.py`, the `open_alerts` read reads unread grooming notices with `limit_page_length=0`, and every row
goes into the `gate` list handed to `grooming._readable`, which turns it into
`name IN (…)`. The statement count stays flat — which is what `assertEqual(small.n, big.n)`
and `assertLessEqual(big.n, 14)` measure — so the tests are right and blind at the same
time. Concrete scenario: a line manager with 20 reports who never taps "Mark all as read"
gains roughly one unread mark notice per report per working day (a manager's mark notice
becomes *unreadable* the next day but is never *read*, so it stays in this query for ever);
after a year that is ~5,000 rows fetched and a 5,000-item `IN` list, on **every page load**,
because `ntBellBoot` calls `notices_feed` on every non-Home page. This shape was chosen
deliberately — OPS-13 recommends exactly it and names the alternative's cost — and DTC
holds zero rows, so there is nothing to panic about. **What is missing is a number.**
Smallest answer: measure it once on a seeded site and write it down, or cap the read and
report `capped` the way the list already does. Label: **intentional trade-off, with the
measurement still owed.**

**m2 · P3 · The new tests leak `Employee` notification rows into a reused site.**
`_wipe()` (`test_grooming_066.py`, `_wipe()`) deletes `Notification Log` rows of
`Grooming Mark`, `Grooming Review` and `Announcement` — the slice correctly added the
third. It does **not** delete `document_type = "Employee"`, and
`test_assertion_two_my_own_desk_notifications_are_untouched` and
`test_it_takes_no_arguments_at_all` create three such rows per run and commit them in
`tearDown`. **Measured:** the `a83-bench` `test_site` currently holds **36 unread
`Employee` rows for `rahul@g066.test`** and nothing else — three per suite run, accumulating.
Harmless today (no production code and no assertion counts them), but it grows without
bound on a reused site and it is precisely the shape that makes a future count assertion
drift for reasons nobody can find. One word in `_wipe`'s list, or a `finally` in the two
tests.

**m3 · P3 · Home's footer can still disagree with Home's own chip when a part is capped.**
*Inferred from `hmPaintPending`'s chip and footer, not run.* The chip is `ntWorkOwed(d)` —
uncapped `p.count`s. The footer is `rows.length` — the rows the server actually sent,
capped at 50 per part. With 63 attendance fixes the card reads "63 waiting" above "Showing
5 of 50 · See all 50". The notifications page explains this ("Showing the first 50 of 63
attendance fixes", AC-18a, asserted); **Home does not.** No AC covers it and the footer fix
in this slice made the two footer numbers agree with each other, which was the stated goal.
Label: **acceptable simplification** — but it is the same family of fault as the one this
slice was built to kill, so it belongs on a list.

**m4 · P3 · After "Mark all as read", Home's card still lists five notices with nothing to
say about them.** `nfMarkAll` sets `HM.notes.items[*].read = 1` and repaints
(`nfMarkAll`); `hmPaintNotices` draws them with `withRead = false`, so no "Read"
label appears and the chip is empty. The card reads as five unlabelled notices under a
blank heading. Cosmetic; it self-corrects on the next `get_inbox` refresh.

---

## 4 · Nits

<details><summary>Four, none worth a commit of its own</summary>

- `nfOpen` resets `NF.chip` to `"all"` on every entry, so coming Back from a tapped row
  loses "To do" / "Unread notices". No AC covers it.
- `notices_feed` computes and returns `capped` when `see_all=0` as well, where nothing
  reads it. One expression; harmless.
- The AC-11 jsdom fixture gives `expense_approvals` `count: 1` with `rows: []` and
  `capped: false`, which the real `get_inbox` cannot produce (it sets
  `capped = n > len(rows)`). The assertion is still right; the fixture is not a shape the
  server emits.
- `03` §1 row 5 says the `nf` block is "~290 lines"; the diff is 521 lines on `portal.js`.
  Both numbers are defensible (new block vs. total hunks); say which.

</details>

---

## 5 · AC verification

Walked one by one against the code. 67 ACs; the ones not listed are met and asserted, and
I checked the assertion rather than counting it.

| AC | Verdict | Evidence |
|---|---|---|
| AC-1 | **partial** | `#nf-bell` is a 36 × 36 `<button>`, moved left of the avatar by `nfHomeTheBell`; name from `ntPaintBadge`. Asserted in jsdom. **The 1180 px placement is not rendered by anybody** |
| **AC-2** | **not met** | **B1.** The badge resolves against `nav.navbar`, not the bell, on the real desktop path |
| AC-3 | met | `display:none` at zero, name still carries 0; asserted |
| AC-4, AC-5, AC-6 | met | I re-ran the assertions: the item exists, is visible, is index 1, is a `BUTTON`, carries the word, and `mayOpenPanel("notifications")` is true |
| AC-7 – AC-10 | met | title, sub-line, three groups in fixed order, oldest-first across kinds, group 3 rows are `DIV`s with no button inside |
| AC-11 | met | badge 7 on the spec's own payload, and asserted to be neither 12 nor 9 |
| AC-12 | met, wording changed (D-1) | **I grepped it myself:** exactly one line in 24,575 names the badge ids (`portal.js`, `NT_BADGES`), and `ntPaintBadge` is called 8× always with no argument. The intent — one computing place — holds |
| AC-13 – AC-18a | met | chips send zero requests (fetch spy), five rows per group, footer total 150 not 100, "Showing the first 50 of 63 attendance fixes" |
| AC-19 | met | the two headings reconcile the badge, asserted arithmetically |
| AC-20 | met | disjoint sets, with a tripwire on `len(ROW_KEYS) == 7` |
| AC-21, AC-22 | met | "4 waiting", own requests under their own sub-heading, DOM order asserted, on the `my_requests > 0` fixture that never existed before |
| **AC-23** | **not met** | **B2.** 278 vs 4 for a CXO, measured |
| AC-24 – AC-27 | met in code, **Python not run by me** | the count is split by kind, folded into the one `_readable` call; `capped` added; ceiling 12 → 14 with the flatness line untouched. I read all six tests and each would fail if its own term were removed |
| AC-28, AC-29 | met | one `nf-mark`, and its `.nf-grp` **is** group 2; absent, not greyed, when nothing is unread |
| AC-30, AC-31, AC-32 | met in code, **not executed by me** | I traced the three assertions and they are genuinely independent: drop `document_type` and only AC-31 fails; drop `for_user` and only AC-32 fails; AC-30 passes in both of those worlds, so it cannot mask either |
| AC-33 | met | `frappe.db.set_value` with a dict filter is **one** `UPDATE` — verified in `frappe/database/database.py`: dict filters go to `frappe.qb.get_query(update=True)` and `clear_document_cache(dt)` whole, with no permission condition. The docstring's claim is exactly right |
| AC-34 | **partial** | The POST half is **proven twice over**: `@frappe.whitelist(methods=["POST"])` is enforced at `frappe/handler.py:109`, and `gpSend` picks POST because `{}` is passed (`gpSend`). jsdom asserts the real request method and body. **The refusal by exceeding 30 is still not written** — G-3 stands |
| AC-35, AC-36 | met | the existing leave sheet opens in place; any other row navigates with zero calls |
| AC-37, AC-38 | met | word for word, including no toast and the badge unchanged; I re-ran them |
| AC-39 | **not met** | no test makes one part raise. Behaviour is right by inspection (`ntBellBoot`'s handler does nothing on failure) |
| AC-40 – AC-44 | met | four `aria-busy` bars, the spinner always ends, four empty states word for word. **AC-44 reads "first morning" as `any === false`** — D-3, needs Surbhi's word on the reading |
| AC-45, AC-46 | **changed (D-2)** | the server's own sentence is shown and both feeds re-asked. I agree with the reasoning — string-matching a refusal to choose between two of our sentences would get "No leave approver is set for Rakesh" wrong, where the row must stay. **Still needs her word** |
| AC-47 | met | by saying nothing |
| AC-48, AC-49, AC-49a | met | badge 4 not 279, "counts by kind", no colleague named. **But see B2: the chip beside it says 278** |
| AC-50 – AC-54a | **unverifiable here** | every string goes through `drT()`; 12 px and `--primary` on `--primary-lt` are set in `.notif-badge`'s own rule. Hindi, 200 % text, the contrast pairs and a no-brand-seed tenant are **arguments from tokens, seen by nobody**. Release gates, correctly declared |
| AC-55 | **partial** | **five doors of six, and I reproduced seven myself** — see M2 and §8. The missing one (`share`) I proved closed |
| AC-56 – AC-56e | met in code | own-count strictly less than site-wide; `inspect.signature` empty; exact key set including `capped`; `ignore_permissions` ceiling green (`check_scope_traps.py` exit 0); net whitelisted endpoints **zero** — I grepped, `my_notices_seen` has no caller left anywhere |
| AC-57 – AC-59 | met | zero calls on a tap, no dismiss/snooze/mark-done, and the storage assertion runs on **comment-stripped** code, which is the right way to write it |
| AC-60 – AC-62 | **not checked** | pre-existing behaviour; the engineer declared it as a gap and I did not re-derive it |
| AC-63, AC-63a | **partial** | the route is a fixed word (asserted); Chrome Android Back after sign-out is a declared release gate. `e8ccc232` has since added the `no_cache` and Guest-redirect tests that were missing |
| AC-64 – AC-67 | met | no `setInterval`, no `enqueue`, no `nginx.conf` in the diff, the flatness line untouched, all nine gates exit 0 (I ran them) |

**Count: 59 met · 5 partial · 2 not met (AC-2, AC-23) · 1 changed and awaiting her word
(AC-45/46) · AC-50–54a and AC-60–62 unverifiable without a browser and a bench I do not have.**

---

## 6 · NFR verification, and the seven dimensions before vs. after

| Budget (`nfr-budget.md`) | Measured or reasoned | Verdict |
|---|---|---|
| `notices_feed` statements, flat in headcount | the flatness line `small.n == big.n` is untouched; the note raised 12 → 14 with the reason in the commit. **Reasoned; I did not execute it** | pass |
| `notices_feed` ≤ 14 statements | two new statements, one `COUNT` + one `get_list`, both outside `_readable`, which is called **once** for both sets. Read line by line | pass, reasoned |
| `get_nav_counts` flat in backlog depth | a **standing assertion** now exists (3 rows → 40, `deep ≤ shallow + 1`) with a guard that the backlog really deepened. Better than the one-off number DevOps asked for | pass, reasoned |
| `get_nav_counts` p95 ≤ 500 ms in DTC's configuration | **not measured. OPS-3 is a P1 and it is open** (G-11). Surbhi's E-6 ruled out copying DTC, and the fixture-site run in `07` §4.6 was not done | **open** |
| No timer, no cache, no job | asserted in the built source, comments stripped. I re-ran it | pass, proven |
| One `UPDATE` for any backlog | `spy.n ≤ 2` for 86 unread rows | pass, reasoned |
| Rollback ≤ 15 min | no migration, no patch, no DocType JSON — I ran `git diff --name-only` and confirmed. OPS-29's asset-stamp trap applies and is written up | pass |

| Dimension | Impact analysis claimed | What I found | Agree? |
|---|---|---|---|
| Performance | **degrades, accepted**: +21 statements / 638 B on every non-Home load, `notices_feed` 12 → 14 | the same, and slightly better than proposed — `ntBellBoot` now skips each half Home already asked for, keyed on a flag set when the request *goes out*. `get_nav_counts` (numbers) for the bell, never `get_inbox` (rows) — OPS-1 honoured | **yes** |
| Security | **improves** | yes, and the strongest part of the slice. Two unprotected tools gained a tested contract; the GET trap is closed in two independent places; zero new whitelisted endpoints | **yes** |
| Reliability | **improves slightly** | yes — each call fails alone, neither blanks anything, the spinner always ends, the write is safe to run twice, and a refused decision re-asks rather than guessing from the words | **yes** |
| Scalability | **neutral** | **no — one row axis is unbounded.** `limit_page_length=0` on the new read, growing with one person's own unread grooming backlog, on every page load (m1). Flat in *queries*, which is what the tests measure. OPS-13 chose this knowingly; the analysis should have said "flat in queries, unbounded in rows" | **no — correct to "neutral in queries, unbounded in rows"** |
| Maintainability | **improves, narrowly** | agreed, and the narrowness is real: `portal.js` is now 24,575 lines (+~500). Against that: a dead endpoint deleted, a `WRITE_CALL` special case deleted, two expressions for one number collapsed to one. **B2 means there is still a second definition of "work owed" in the file** — fixing it makes this claim true | **yes, once B2 is fixed** |
| Data integrity | **improves** | agreed, and it is the headline fix: the count equals the list it links to. `update_modified=False` means nothing records *when* a bulk clear happened — named, accepted in spec §14 | **yes** |
| Compliance / privacy | **neutral on entitlement, one change in exposure shape** | agreed. No new field, no DocType JSON, no Custom Field — I checked the diff. Nothing personal reaches a log: the new code is a `COUNT`, a three-field read and an `UPDATE`, none of which handles a name or a subject | **yes** |

---

## 7 · Compliance verification

The spec carries a real compliance-impact sub-analysis (§13.1–13.6), so this axis **is**
reviewable. Row by row:

| Obligation | Mechanism in the diff | Test that proves it | Verdict |
|---|---|---|---|
| Reasonable security safeguards — access control (DPDP) | explicit `for_user` **and** `document_type` on the count; the same two terms on the bulk write; `get_list` never `get_all` for the counted set | `TestTheTrueUnreadCount` (6) + `TestMarkAllSeen` (8) + `TestTheDoorsToSomebodyElsesNotices` (4). **I reproduced the doors myself** | **discharged**, less the share assertion (M2) |
| Purpose limitation — read state stays with the recipient | no endpoint returns per-recipient read state; the write returns `{"ok": 1}` | the exact key-set assertion on `notices_feed` | **discharged** |
| Data minimisation | no new field, no new store, no new copy; `ROW_KEYS` unchanged | exact key set including `capped`; no `.json` and no Custom Field in the diff (I checked) | **discharged** |
| Breach intimation / CERT-In 6 h | nothing new to log; the clock binds only if the write goes wide | AC-30/31/32, written to fail when either term is removed | **discharged as far as this slice can** |
| Passport / health not for managers | none reaches any row; `explanation` is not in `ROW_KEYS` | the existing `ROW_KEYS` tests | **discharged** |
| Performance records: employment + 6 months, then permanent erasure | **nothing in this slice** | none | **not discharged — pre-existing, routed as ⚠ SEC-R1.** Correctly named rather than inherited quietly. Needs her written acceptance with a date |
| EU AI Act / GDPR | no surface | — | **n/a, and said so rather than left blank** |
| Audit: who cleared a notice, and when | `modified_by` is set for a single `mark_as_read`; the **bulk** write deliberately does not stamp `modified` | none, by design | **partial, accepted in spec §14.** Nobody's pay or rating turns on it. If Surbhi wants it auditable, it costs a statement per row — her call, not a defect |

**No prohibition is enforced by a sentence here.** The two that matter are structural: the
write takes **no arguments at all** (`inspect.signature` is empty, so there is no parameter
for a crafted doctype, user or filter to arrive in — and Frappe drops unknown kwargs
anyway), and the mark-all control is a selector that exists in one group only, asserted by
its `closest(".nf-grp")` **being** group 2. That is the right shape.

**One compliance consequence of B1 and M1 worth naming:** none. Neither changes who can
see what.

---

## 8 · The door I reproduced myself

Required by `data-doors.md` ("Reviewer: reproduce one door yourself"). Run in
`a83-bench` / `test_site`, read-only, ending in `frappe.db.rollback()`. `deepa@g066.test`
holds `['All', 'Desk User', 'Employee', 'Guest']` — a plain staff login.
`rahul@g066.test` owns all 36 rows.

```
==== as deepa@g066.test (plain Employee) ====
1 get_list                      -> 0 rows, set()
2 get_list filters for_user=rahul -> 0 rows
3 reportview.get                -> 0 rows (empty list; compress() passes it through)
4 reportview.get_count          -> 0
5 client.get_list               -> 0
  client.get_value(rahul's subject) -> {}
  client.get(rahul's row)       -> PermissionError
6 search_link                   -> 0 results; rahul's row present: False
7 export_query (CSV)            -> 73 bytes; contains rahul's user id: False
  has_permission(read/write/share/delete/submit/email/print/export/report) -> all False
  frappe.share.add on rahul's row   -> PermissionError: No permission to share Notification Log
  client.set_value on rahul's row   -> PermissionError

==== as rahul@g066.test (the owner) ====
1 get_list                      -> 36 rows, {'rahul@g066.test'}
3 reportview.get                -> 36 rows, {'rahul@g066.test'}
4 reportview.get_count          -> 36
6 search_link                   -> 36 results; rahul's row present: True
7 export_query (CSV)            -> 2476 bytes; contains rahul's user id: True
```

**Three things this run establishes beyond the test file.**

1. **The gate is real and it is Frappe's, not ours.** `Notification Log`'s DocPerm grants
   role `All`: `read`, `report`, `export`, `print`, `email`, `share` — and `write: 0`,
   `delete: 0`. The limit lives in `get_permission_query_conditions` and `has_permission`,
   which is the permission layer `data-doors.md` demands. The portal adds convenience on
   top. Correct way round.
2. **`get_list` is the right door to test**, and the test's reasoning is sound: `get_all`
   is `get_list` with the check off, so asserting on it would prove nothing. Confirmed by
   running both shapes.
3. **The export assertion does prove what it claims.** The owner's export is 2,476 bytes
   and contains their own subject; the stranger's is 73 bytes — a header row and nothing
   else. A negative-only assertion would have been weak, which is exactly the fault
   `e8ccc232` fixed on the link-search door. Note for the record: `reportview.get()`
   returns a **bare empty list** when the caller may see nothing (`compress()` returns
   `data` unchanged if falsy), so any future door assertion must handle both shapes —
   the current test only ever runs it as the owner, so it is fine today.

---

## 9 · Questions

**Must know — these hold the verdict.**

- **Q1 (B2).** I read AC-23 as "the Home chip and the bell are the same number for every
  persona". The code gives a CXO 278 on Home and 4 on the bell. **If that is deliberate**
  — a CXO wants volume on Home and movement on the bell — then B2 is a Minor wording gap,
  AC-23 needs rewording, and it becomes a tenth declared departure. **If not, it is a
  Blocker and the fix is deleting one ternary.** Ranked provisionally as a Blocker.
  *Owner: Surbhi, on the product rule; `hrms-fullstack-engineer` for the one line.*
- **Q2 (D-2, D-3, D-4).** Three departures the engineer flagged as needing her word, and
  none has it yet: showing the server's own refusal sentence instead of AC-45/46's two
  (I agree with his reasoning, strongly); reading AC-44's "first morning" as "has never
  had a notice"; and collapsing five capped-work strings into one with the kind as a
  placeholder (which changes §11.1's Hindi draft). The parity rule of 21 Oct says a
  difference needs her yes first. *Owner: Surbhi.*

**Should know.**

- **Q3 (SEC-R1).** The written, dated acceptance that `Notification Log` rows — including
  grooming-mark notices, which counsel classes as performance records — are kept for ever
  as pre-existing debt. The spec says it blocks nothing here; it is still unsigned.
  *Owner: Surbhi, with counsel already briefed.*
- **Q4 (OPS-3).** `get_nav_counts` has never been measured in DTC's configuration, and
  after this slice it runs on every non-Home page load for 483 logins. The standing
  assertion is the better half and it is in. Does the fixture-site measurement in `07` §4.6
  happen before or after this ships? *Owner: `hrms-devops-engineer`, deciding with Surbhi.*

**Nice to know.** Whether the notices half being empty at DTC should be said to them in
writing before release (M1), or left to the first person who asks.

---

## 10 · What to delete

The engineer's own subtract pass was good — it removed two window exports, a dead test
branch and an unmatchable CSS rule, and it names nine things dropped while building
(an `nf_api.py`, a second bell element, a `resize` listener, a `NF_STALE_MS`). I looked for
more and found **one**:

- **The CXO branch in `hmPaintPending`.** `hmIsCxo() ? rows.reduce(…)`
  is the second definition of "work owed" in a file whose whole point this slice is to make
  single. Deleting it fixes B2, removes a line, and leaves exactly one function computing
  the number. **This is the most valuable line in this review.**

Everything else I considered and would keep: `HM.askedPend` / `HM.askedNotes` (two booleans
that stop a slow Home being asked twice, and performance is this slice's named cost);
`NF.busy` (the write is rate-limited, a double tap should not spend two of thirty); the
three separate write assertions (a combined one would not name the cause); the
`my_requests > 0` fixture; and both gate-script entries, which are required, not extra.

**Nothing in this slice is over-engineered.** No new DocType, no new field, no new app, no
new module, no settings page, no feature flag, no abstraction, no dependency, no hook on a
shared doctype, no cache, no timer, no job, no new address, no migration. Net whitelisted
endpoints: zero — one added, one deleted. Rung 4 is argued per file and the cheaper rungs
are named. That is the ladder applied properly, not recited.

**Subtract pass on this review:** I cut a hollow finding about the link-search door being a
negative-only assertion (`e8ccc232` had already fixed it, and my own run showed it returns
36 results for the owner, so it could fail); a finding about the door test leaking
committed Announcement rows (`Case.tearDown` wipes them — I checked before writing it); and
a finding about `button.nav-item` losing the rail's styling (`frame.css:19` carries a global
`button{border:none;background:none;font:inherit;color:inherit}` reset, so it does not).
Three maybes removed. What is left I traced.

---

## 11 · What was done well

Named as decisions, because these are the patterns worth copying.

- **The write's security is two filter terms, and it is defended by three assertions that
  fail independently.** I traced each one: drop `document_type` and only AC-31 breaks; drop
  `for_user` and only AC-32 breaks; AC-30 survives both, so it cannot mask either. That is
  how you test a line that fails silently. The docstring on `mark_all_seen` says exactly
  this in plain words, including *why* Frappe's own `mark_all_as_read` is not called — and
  I verified that claim in Frappe's source.
- **Choosing to *move* the endpoint rather than add one.** Net whitelisted endpoints zero,
  a dead function in the wrong module deleted, and `NOTICE_DOCTYPES` single-sourced so the
  feed's filter and the write's filter cannot drift. `my_notices_seen` has no caller left
  anywhere in the repo — I grepped.
- **Closing the GET trap twice, independently.** `methods=["POST"]` on the whitelist
  (enforced at `handler.py:109`) and `gpSend`'s `args !== undefined ? "POST" : "GET"`, with
  a jsdom assertion on the **actual request method and body** rather than on the decorator.
  That is the 28 Oct "test what it sends, not what it draws" lesson applied without being
  told.
- **`ntPaintBadge()` taking no argument.** The spec asked for one function called from
  three places; the engineer delivered one function callable from anywhere that cannot be
  given a wrong number, and pinned it with a source assertion. **One line in 24,575 names
  the badge elements — I grepped it and it is true.** Better than the spec, and he declared
  the change rather than quietly improving it.
- **Naming that the old assertion passed on a coincidence.** Every pre-existing Home
  fixture had `my_requests = 0`, so "the chip and the badge agree" had never been tested
  against the one payload that could break it. Adding that fixture is worth more than the
  ten assertions around it.
- **Nine departures declared and fifteen gaps labelled**, with three marked as needing her
  word rather than assumed. And `e8ccc232`'s "proved by breaking them: disarm the redirect
  and remove `no_cache`, and exactly those two tests fail" is the right standard of
  evidence for a control.

---

## 12 · Confidence

**Proven — I ran it or read it and saw the result:** all 24 jsdom suites (exit 0, 0 failed;
083 alone 80/80); all nine static gates (all exit 0); the seven-door reproduction in §8 as
two logins; the DocPerm row on `Notification Log`; Frappe's `db.set_value` dict-filter
path, `rate_limit`'s per-`cmd` cache key, `handler.is_valid_http_method` and
`reportview.compress`; the single badge-naming line and the eight no-argument
`ntPaintBadge` calls; `my_notices_seen` having no caller; the CXO drift in B2 (probe output
quoted); the 36 leaked `Employee` rows in m2; the incoming-commit ancestry.

**Inferred:** B1 — the badge's containing block. The three CSS rules and the `defer` script
tag make the chain deterministic, but **I did not render it**, and if `nav.navbar` ever
stopped being positioned the symptom would change (to the page's top-right corner) without
the fault going away. m3 — Home's capped footer, read off the code, not run.

**Not checked, and what I would have needed:**

- **The Python suite.** It writes to a bench another session owns; the task reports four
  suites green on a fresh site today and I have no reason to doubt it, but **I did not see
  one of those 29 assertions execute.** I would need my own throwaway bench.
- **Mutation-testing the three write assertions** — removing a filter term and watching
  exactly one test go red. That would require editing `notices.py` in someone else's
  container. I traced the independence by hand instead and it holds.
- **Anything a browser shows:** B1's actual pixels, the badge contrast across four
  theme × brand combinations (including a tenant with no brand seed), Hindi at 390 px,
  200 % text, the bell at 1180 px, and Chrome Android Back after sign-out. All correctly
  declared as release gates by the engineer. **Every claim in this slice about the badge's
  colour and placement is an argument from a CSS token.** B1 is what that costs.
- **AC-60 – AC-62**, pre-existing behaviour I did not re-derive.
- **`get_nav_counts` in DTC's configuration** (OPS-3, P1, open).

**Unreviewable:** nothing. Every upstream artifact exists and is substantial. The one
missing artifact is `04-test-report.md` (M3), and its absence is why `03` is the only
account of the test state and `03` is now wrong about it.

---

**Written by `hrms-technofunctional-reviewer`, 12 November 2026, against HEAD `e8ccc232`.
This is advice. Surbhi decides whether the slice ships.**
