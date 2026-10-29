---
slice: 076-home-notices
artifact: 06-review-C (senior architect review, step 5, Part C)
author: hrms-technofunctional-reviewer
date: 2026-10-29
branch: slice/076-part-c (worktree .claude/worktrees/076-part-c), 2 commits on origin/dev cf65c663
status: advice. Surbhi decides whether Part C ships.
---

# 076 Part C review: expenses from Pending, and birthdays

## Verdict: SHIP WITH FIXES

**The code is sound and the money path is safe, but one data shape leaves an expense claim stuck where nobody in the portal can see it.** That is a small fix. Three screen differences also need Surbhi's yes, and two release gates sit outside the code.

**What I ran, and what I did not:**

- **Ran (Proven):** the full DOM suite (19 run, 0 failed; Part C file 56 of 56). `check_scope_traps.py` and its `--self-test` (both OK). `check_app_integrity.py` (860 checks, OK).
- **Did not run:** any Python test. I did not start `hrlocal-076c`. Every Python result below is the engineer's report, or my reading of the test code. I say which each time.
- **No real two-connection race** was run by anyone (see Minor 3).

**Incoming work:** none. The branch sits on `origin/dev` `cf65c663`, and `origin/dev` has not moved since. Both commits are the engineer's own. Nothing touches `deploy/`, `demo/` or `.github/` (Proven, `git diff --name-only`).

---

## Bad news first

1. **Major (P2): a claim whose approver is the claimant is filed, then nobody in the portal can see it or decide it.** Details in Major 1.
2. **Release gate (not code): DTC's expense approvers have never been counted.** Decision 4 refuses any portal claim with no approver. If DTC staff have none, every portal claim at DTC is refused from day one. That is a button that fails in a client's first week. I agree with the engineer: count it, read-only, before Part C reaches production.
3. **Release gate (not code): counsel's written note on birthdays is still missing.** The switch ships off (Proven, field default `"0"`, and `get_single_value` returns nothing on a site that never saved it, so `cint` gives 0). It must stay off until the note arrives.
4. **Escalation, older than Part C: a colleague may read anyone's date of birth through Frappe's own API** when their login has no Employee User Permission. `employee_field_rights.py` says level 2 is read by "every role that reads Employee". So the record-level User Permission is the only thing in the way. The engineer found this; I did not run it. It is not caused by Part C, but switching birthdays on makes the dates more interesting. Owner: `hrms-security-privacy-engineer`, with a read-only check at DTC.

---

## Blockers

None in the code.

---

## Majors

### Major 1 (P2): the claimant can be their own approver at filing, and the claim then sits where no portal screen shows it

- **Proven, by reading.** `hr_api.py:2406` takes `expense_approver_for(emp.name)` and only checks that it is not empty. `expense_approver_for` (`hr_api.py:2449`) returns the Employee's own approver, or the Department's first approver. Neither path checks that the approver is someone other than the claimant.
- **What happens.** HR sets "expense approver = the store manager" for everyone in the store, including the store manager. Or the department head is the department's first expense approver. That person files a claim in the portal:
  - The claim is filed, with themselves as approver. They see "filed".
  - Their own Pending never shows it (`inbox_api.py:544`, `employee != own`).
  - `decide_expense` refuses them (`hr_api.py:2486`). So does the Desk submit hook.
  - Nobody else is the named approver, so no other Pending shows it either.
- **Why it is wrong.** Decision 4 was made to stop exactly this: "a claim carries its approver, or it is not filed. Without one it would sit where nobody can see it." This shape gets past it. The person waits for money that no screen will ever ask anyone to approve. Only HR in Desk can rescue it, and only if they go looking.
- **Ranking rung:** correctness of what the business asked (rung 3).
- **Smallest fix.** In `apply_expense_claim`, treat an approver equal to the caller's own login as "no approver". Refuse with the same words ("Ask HR to set your approver."). In the backfill patch, count such claims as unresolvable and do not set them. Add one test: a claimant whose own login is their approver is refused, and no claim is made.
- **The same family, lower risk:** an approver who has left, or whose login is disabled, also gets new claims they can never decide. The spec accepted this for *existing* claims ("HR re-assigns in Desk"). Whether *new* claims to a leaver should be refused is Surbhi's call. I would not add it to this fix without her yes.

---

## Minors

### Minor 1 (P3): one more screen difference from the prototype, not in the engineer's list

- **Proven.** For a CXO, the drawing's "Expense claims" row says "N waiting · across your companies" and opens the existing Expense claims screen. The build says "N waiting · opens the oldest" and opens the oldest claim's sheet (`portal.js` `hmPendingRows`; DOM test line 152).
- **Why it differs.** There is no approver expense screen in the portal to open. The build copies Part A's goal-update row, which Part A's review accepted. That is a sensible choice.
- **Still a difference** under the prototype parity rule. Add it to the parity table for her yes.

### Minor 2 (P3): the new file's permission bypasses are not registered anywhere

- **Proven.** `home_people.py` reads Employee with `frappe.qb.from_` (line 96, no permission check, on purpose). It also uses `frappe.get_all` on Version and `frappe.db.count`. It is **not** in `test_portal_security_010.CEILINGS`. It is not in the endpoint registry in `test_frame_endpoint_registry_034` either, which only scans a fixed list of files. Nor is the new patch file.
- **Why it matters.** The spec said the birthdays read is "one counted bypass". It is a bypass, but it is not counted. If someone later adds `ignore_permissions` to this file, no test turns red. The existing rule is "new files start at zero, so it is proven for them too". It only works if the file is listed.
- **Smallest fix.** Add `("alvoraa_portal", "home_people.py"): 0` and the patch file to `CEILINGS`, with a one-line comment that the birthdays query is the deliberate bypass. Two lines.

### Minor 3 (P3): "approve and decline at the same moment" is proven by reading, not by a run

- **Inferred, and I think correctly.** `decide_expense` does the locked read first (`hr_api.py:2481`, `for_update=True`). So a second request waits, then sees `docstatus 1` and gets "already decided". Tests prove one call after the other.
- **Not checked:** two live connections. The engineer called this an acceptable simplification. I agree, as long as it is written down as such.

### Minor 4 (P3): AC-83 is only partly met

- **Proven, by reading.** AC-83 asks that the *existing* inbox tests run over the new part with a real portal claim in their data. Their data was not changed, so for this part they run over zero claims. "0 rows" proves nothing (lesson 1). Part C's own tests do cover count equals rows and the nav total (`test_the_approver_sees_…`, `test_the_count_and_the_total_add_up`). So the gap is small. Write it down as partial, not met.

### Minor 5 (P3): AC-102 timed at 245 people in one branch, not 5,000

- **Reported by the engineer, not re-measured.** One query, every filter in SQL (Proven, `home_people.py:95-102`). The time grows with the size of one branch. Acceptable simplification, written down.

### Minor 6 (P3): an empty Birthdays card cannot be told apart from "nobody in your branch"

- **Proven.** A viewer with no branch gets `rows: []` (`home_people.py:131`). The page then says "No birthdays or anniversaries this month." That matches AC-97. But if DTC records have no branch filled in, switching on shows an empty card to everyone, and HR would think it works (lesson 3).
- **Fix:** none in code. **Before switching on at a tenant**, count Active employees with no branch, read-only. Add it to the switch-on checklist beside counsel's note.

### Nits

Omitted. The repo's own checks cover style.

---

## Prototype parity (02-design section 14, Part C rows)

I read `prototype-v1.html` lines 296-316, 420-447 and 518-612 against the build.

| Drawn | Built | Needs her yes? |
|---|---|---|
| Expense row "Expense claim · ₹2,300 · Travel · waiting N days", Review | Same (DOM test line 102) | No |
| Expense sheet: name, "Expense claim", large amount, type and date, note, "Waiting N days. Approving passes it to accounts…", the decline label, "Send decline", both toasts | Same | No |
| CXO "Expense claims" row opens the Expense claims screen | Opens the oldest claim's sheet, "opens the oldest" | **Yes (Minor 1, not in the engineer's list)** |
| Birthdays card, rows, "earlier this month", "Showing 5 of N", "See all N", sheet title and footnote, both empty sentences, cake icon | Same | No |
| "Work anniversaries" card when birthdays are off and anniversaries on | Not built: one switch covers both (spec Q2) | **Yes (engineer's difference 2).** D10 first said "anniversaries on". Under the build, anniversaries are also off at DTC until counsel writes. |
| "My profile" in the left menu, and "Me" on the phone bar | Phone account menu; on a laptop, the name at the foot of the sidebar | **Yes (engineer's difference 1)** |
| Opt-out tick text | Adds "on Home" | No: decision 5 already approved it |
| Org switch, On/Off in words, hints, confirm with "(412 people)", "Keep it on" / "Switch off", one tap on | Same, plus "Last changed by …" | No: AC-103 asks for the extra line |
| "Declined: <reason>" on the employee's claim | Built (spec words; not drawn) | No |

**Confirmed: no other differences** beyond the three marked "Yes". Of those, one was not in the engineer's notes.

---

## Acceptance criteria

"Engineer ran" means the engineer reports it passed and I read the test to check it would catch the fault. I did not run it.

| AC | Result | Evidence |
|---|---|---|
| 77 approver set at filing, shared | Met | Code 2406-2433. `test_filing_sets_the_approver`, `test_an_approver_without_the_role_gets_a_share` (engineer ran) |
| 78 | Replaced by decision 4 | `test_a_claim_with_no_approver_is_refused` checks the words and that no claim was made |
| 79 backfill | Met | Savepoint per claim; second run leaves `modified` unchanged (test reads that) |
| 80, 81 part filter and keys | Met | `inbox_api.py:538-588`; exact key set asserted |
| 82 nobody else; no Active Employee | Met | Four other users get count 0; `no_rows()` asserted on the filter itself |
| 83 existing inbox tests over real claims | **Partial** | Minor 4 |
| 84 only the named approver, HR included | Met | Pin test; a guessed id gets the same refusal (no hint that it exists) |
| 85 approver who has left | Met | `_get_employee` requires Active (Proven, `hr_api.py:300`) |
| 86 approve submits, GL entries, no shortcuts | Met | Test asserts 2 or more GL rows; a source-scan test bans `ignore_permissions`, `db_set`, `set_value`, `frappe.db.sql` |
| 87 decline reason 1-140, stored, no GL | Met | Bad reasons tried; escaped value and zero GL asserted |
| 88 twice, "already decided" | Met in sequence | Minor 3 |
| 89, 90 sheet text, escaping, toasts | Met | DOM, **ran it**: hostile name and note stay text; the payload sent is asserted |
| 91 no self-approval on portal, doc API and REST | Met | Pin test with the HR Setting at 0; the engineer broke the hook and saw it fail |
| 92-94 decline reason on own claim, privacy, title | Met | DOM (ran) and Python |
| 95-98 fixed keys, no year, branch, leavers, opt-out | Met | `test_birthday_reply_has_no_year` scans every value for a year and for each seeded date |
| 99 order, cap, See all, empty | Met | Python and DOM |
| 100 completed years, this year's joiners, 29 Feb | Met | `_day()` tested for 2027 and 2028 |
| 101 off: no Employee query | Met | Statement spy asserts no `tabEmployee` query |
| 102 one query; 5,000 timed | **Partial** | Minor 5 |
| 103 ships off; HR only; Version history | Met | Plain employee and HR User refused; `changed_by` asserted |
| 104 confirm before off | Met | DOM (ran) |
| 105 own tick only | Met | Signature asserted; HR's doc save and `set_value` both tried. Inferred, not hollow: the `set_value` path has no other reason to fail. The engineer did not break `keep_hide_birthday` on purpose to prove it |
| 106 wording; hidden when off | Met | DOM (ran) |
| 120 dates not readable through Frappe | Met **only with** the Employee User Permission | Bad news 4 |
| 121 own claims only; guessed id refused | Met | As 84 |

**Decision 4 (no approver = refused):** met, except for the self-approver shape (Major 1).

---

## Correctness and races in `decide_expense` (`hr_api.py:2462`)

All Proven by reading unless marked.

- **Lock first.** The locked read is the first read of the claim in the request. A second tap waits, then sees it decided. This is the lesson from slice 021, applied correctly.
- **Check order.** Guest, then a valid action, then exists-and-yours, then Active employee, then not-your-own, then still Draft, then the role check. A stranger never learns whether a claim exists or is decided.
- **The role check** (`has_permlevel_access_to`) is needed. Without it, Frappe silently resets `approval_status` for a user without level-1 write, and Frappe HR then throws its own confusing message. Keeping it is right, and it adds no bypass.
- **Decline** zeroes the sanctioned amount through Frappe HR's own `calculate_total_amount`, so nothing posts. The test asserts that.
- **Desk side effect (Inferred):** Frappe HR's `notify_approval_status` writes one "PWA Notification" to the claimant on approve or decline. That is Frappe HR's own app, not our bell, and it sends no email. It is harmless, but the claimant gets no notice in our portal (decision 7: grooming only).

## Field rights on date of birth

- Part C does not change field rights (Proven, `employee_field_rights.py` not in the diff).
- The birthdays endpoint reads the two dates on the server and returns only name, kind, day, month and years (Proven, `home_people.py:103-112`).
- Years plus day plus month gives away the full joining date. The spec approved "years of service", so this is agreed, not a finding. I am naming it so nobody is surprised.

## Opt-out and switch-off paths

- **Switch off:** returns `{"on": 0}` before any Employee query (Proven, line 126). On the page the card stays hidden. My profile says "There is nothing to set here right now."
- **Opt-out:** filtered inside the SQL (line 99). The person's own endpoint takes no employee argument and writes only the caller's Active record (lines 137-145). Any other save puts the old value back (`keep_hide_birthday`, Employee `validate`).
- **Switch:** HR Manager or System Manager only. It is saved through the HR Settings document, so a Version row records who changed it. HR User is refused (test).

## Hooks: order and side effects

- `hooks.py` has no repeated keys (Proven: I parsed it with `ast`). A repeated key in a Python dict would silently drop the first one.
- Employee `validate` became a list. The field-rights check still runs first; `keep_hide_birthday` runs second. They do not interact.
- Expense Claim `before_submit` reuses `refuse_own_submit`. Frappe HR's own `before_submit` runs first (payable account, then its own self-approval check), then ours. This hook covers Desk, REST and imports. **Side effect:** on a tenant, an Expense Approver can no longer submit their own claim in Desk, whatever HR Settings says. That is the rule asked for (SEC-13).
- Frappe HR's own Expense Claim tests run in CI on a site **without** `alvoraa_portal` (Proven, `ci.yml`). So they can neither be broken by this hook nor prove it compatible. The engineer could not run them locally.
- `after_migrate` and `after_install` each gained one line. `create_custom_fields` is safe to run twice.

## Patch: safe to run twice?

- **Yes (Proven, by reading and by the test).** It only picks Draft claims with no approver. It saves through the document, so Frappe HR makes the share. A claim that will not save is rolled back to its own savepoint and counted. It names nobody.
- `patches.txt` has no sections, so this runs **before** the model sync and before `after_migrate`. It does not need the new fields, so that is fine.
- Gap: Major 1 (it can set the claimant as their own approver).

## `scripts/check_scope_traps.py`

Not changed in Part C. Ran it: OK. Ran `--self-test`: it fails on the three unsafe shapes. Part C adds no `permitted_employee_filters` call at all. The birthdays scope is the viewer's own company and branch, read from their own record.

---

## NFR check

The numbers are the engineer's (`05-implementation-notes-C.md`, measured on `hrlocal-076c`). I did not re-measure.

| Budget | Result | Pass? |
|---|---|---|
| Query count flat from small to large | Pending: +1 or +2 statements at both 20 and 980 people | Pass (reported) |
| API p95 ≤ 500 ms | Slowest Pending 141.6 ms; birthdays card p95 24.7 ms at 245 in one branch | Pass (reported; not at 5,000) |
| Switch off costs nothing | 1 statement, no Employee query | Pass (tested) |

| Dimension | Impact analysis said | What the code does | Agree? |
|---|---|---|---|
| Performance | Degrades slightly | One inbox part (2 queries plus one child-row read when there are rows), one birthdays call | Yes |
| Security | Degrades by design, then held | Named approver after the lock, Active check, self-approval on every door, no `ignore_permissions` | Yes. One gap: the new file's bypass is not registered (Minor 2) |
| Reliability | Neutral | "Already decided" on a second tap; backfill cannot stop a migrate | Yes, except Major 1 (a claim can be filed into a dead end) |
| Scalability | Neutral | All filters in SQL; one branch read | Yes |
| Maintainability | Neutral | One module, one endpoint, one part, three Custom Fields, no new DocType | Yes |
| Data integrity | Improves | Claims carry an approver; reason has its own field; title untouched | Mostly. Major 1 is the exception |
| Compliance / privacy | Degrades by design, then held | Off by default, opt-out in SQL, fixed keys | Yes. Counsel's note is still needed |

---

## Compliance

| Obligation | Mechanism in the diff | Test | Result |
|---|---|---|---|
| Minimisation: no year or age (PRIV-5) | Fixed key list, built on the server | `test_birthday_reply_has_no_year` | Discharged |
| Switch off reads nobody (PRIV-6) | Early return before any query | Statement-spy test | Discharged |
| Per-person opt-out (PRIV-6) | SQL filter; own-record endpoint; `keep_hide_birthday` | Two tests | Discharged |
| Own branch, Active only (PRIV-7) | Viewer's own Active record gives company and branch | Two tests | Discharged |
| Written consent basis for birthdays | None possible in code | — | **Not discharged.** Counsel's note; switch stays off |
| Segregation of duties on expenses (SEC-13) | `decide_expense` check and the `before_submit` hook | Pin test, three doors | Discharged |
| Only the named approver decides (SEC-12) | Check after the lock | Pin test | Discharged |
| A decision happens once, through Frappe (SEC-14) | Lock, Draft check, `doc.submit()` | Sequential test and source scan | Partial (no live race; Minor 3) |
| Decline reason private and safe (SEC-15) | Escaped on store; own claims only | Python and DOM | Discharged |
| Who decided, and why, recorded | `modified_by` and submit history; `alvoraa_decline_reason`; Expense Claim is in Frappe HR's audit trail list | Not tested directly | Inferred discharged |
| Refusal logs hold no personal data (SEC-21) | `refuse()` logs user id, claim id and rule only | Not tested for this endpoint | Inferred discharged |

---

## What to delete

Nothing. I looked for it on purpose:

- **The role check in `decide_expense`** earns its place (a clear message, no bypass).
- **The backfill** is needed: old portal claims have no approver and no screen shows them.
- **`birthdays_switch_state`** serves the head count and "last changed by".
- **The clickable sidebar name** exists only because of parity difference 1. If Surbhi picks the drawn menu item instead, delete it then.

---

## What was done well

- **The locked read comes first** in `decide_expense`, so double taps and two-person races end in one decision without extra code.
- **No `ignore_permissions` on the money path.** When a Department approver without the role could not decide, the build gave a clear refusal instead of a bypass.
- **Switch off returns before any Employee query**, and a test counts the statements to prove it.
- **The DOM test asserts what is sent** (`{name, action}`, the trimmed reason, sent once even on two taps), not only what is drawn.
- **The engineer broke each guard on purpose** and showed the tests fail. They also found that Part A's balance check had never filled the Pending and Notices cards, fixed it and re-ran it.

---

## Confidence

- **High** on the code paths: I read every changed server file in full, the hooks, the patch and the tests.
- **Medium** on the Python test results: I read the tests but did not run them. To prove them myself I would need to run `test_expense_birthdays_076` in `hrlocal-076c`.
- **Not checked:** a real two-connection race; birthdays at 5,000 people in one branch; Frappe HR's own Expense Claim tests with this app installed; DTC's real data (approvers, branches, User Permissions). Production is off limits.

## Open questions

**Must know (changes the verdict):**

1. **Major 1: refuse a claim whose approver is the claimant?** My reading: yes, it is the same case decision 4 already refuses. If Surbhi prefers to accept it and let HR fix it in Desk, Major 1 becomes a written trade-off. Ranked P2 until she says.

**Should know (for her yes, not for the verdict):**

2. The three parity differences above (CXO expense row, no anniversaries-only state, where My profile opens).
3. Should new claims to an approver who has left also be refused?

## Escalations

- **Decision needed:** a read-only DTC check of (a) Active employees with no expense approver on their record or Department, (b) approvers without the Expense Approver role, (c) Active employees with no branch, (d) logins with an Employee record but no Employee User Permission.
  - **Context:** (a) decides whether every DTC claim is refused on day one. (d) is an existing date-of-birth exposure.
  - **Who is affected:** every DTC employee.
  - **My recommendation:** run it before Part C goes to production.
  - **Risk if it waits:** a broken expense button in the client's first week; a possible exposure that already exists.
  - **Owner:** `hrms-devops-engineer` to run it, `hrms-security-privacy-engineer` for (d), Surbhi to decide.

## Subtract pass on this review

**Removed:**

- Three nits: `set_birthday_hide` bumps the Employee's `modified` time; saving HR Settings re-writes Frappe HR's naming settings; the opt-out tick is visible to anyone who can already read that Employee record.
- One worry that turned out wrong: that Frappe HR's notification might email the claimant (it writes a PWA Notification, no email).

**Kept:** the rest. Each finding has a concrete failure and a fix.
