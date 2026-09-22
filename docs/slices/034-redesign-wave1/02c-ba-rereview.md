---
slice: 034-redesign-wave1
artifact: 02c-ba-rereview
author: hrms-business-analyst (re-review of revision 2, commit 6ad7936)
date: 2026-09-22
status: ready
inputs: [02b-ba-review.md, 02-functional-spec.md (revision 2), 01c-security-privacy-requirements.md (revision 2), 07-devops-inputs.md §3b, 00-impact-analysis.md (revision note), alvoraa_portal/alvoraa_portal/hr_api.py, alvoraa_portal/alvoraa_portal/subscription.py, alvoraa_portal/alvoraa_portal/www/hrms-employee.html]
---

# Re-review of the Wave 1 frame spec, revision 2

## Verdict: **closed with notes**

All four blockers, all eight majors and all eight minors from `02b` are answered. Nothing
was declined, and nothing I asked for was quietly dropped. The spec is now buildable.

**Two things must be corrected before anyone writes the bottom-bar code.** Neither needs a
redesign and neither needs another review round; one is a line in the persona table, the
other is one sentence plus a decision from Surbhi about a leak the spec claims it closed
but does not.

1. **The persona table's "first match wins" gives Asha the wrong bar.** A platform
   operator with no Employee record is a System Manager, so `is_hr` is true and
   `has_reports` is false. She matches **row 2** before row 6 and gets a **Time** button —
   which §3 hides for her and AC-63 forbids. **AC-10 and AC-63 cannot both be true.**
   Fix: make "no Employee record" rule 1, or add "rules 1–5 apply only to a person with an
   Active Employee record".
2. **Dropping the stand-in rule does not close the leak the spec says it closes.** §2 says
   removing the Team group from HR-without-reports "closes the leak the analyst found".
   It does not. The Team panel's data comes from `get_manager_dashboard`
   (`alvoraa_portal/alvoraa_portal/hr_api.py:291-307`), which still adds **every Active
   employee with no manager**, with `ignore_permissions=True` and no company or branch
   filter, for anyone holding HR Manager or HR User. A store HR person who has **one**
   direct report is row 1 — they keep the Team group, and they still see head-office
   people. §12 also puts the Team screen out of Wave 1, which contradicts the claim.
   Fix: either add one AC that the orphan block is narrowed to `permitted_employees()`, or
   say plainly that the leak stays in Wave 1 and give it a ticket, as ALV-86 and ALV-87
   were given. **Surbhi's call** — it is a small change, but it is scope.

Everything else below is a note, not a stop.

---

## 1. The four blockers

### B1 · Pay without payroll — **closed**

Checked in the source, not taken on trust:

| Claim in the spec | What the code says |
|---|---|
| `expenses` is required on every plan | `subscription.py:83-90` — `"required": True`; also in `_STARTER` (line 239) |
| Pay holds three tabs | `hrms-employee.html:2788-2790` — Salary Slips, Expenses, Leave Encashment |
| Leave encashment has its own flag | `hr_api.py:1240-1244` sets `leave_encashment`; the tab is hidden by it at `hrms-employee.html:7828` |
| Request advance has its own flag | `hr_api.py:1273-1277` sets `advance_request`; the nav item is hidden by it at `hrms-employee.html:7825` |

AC-1 (no salary parts) and AC-44 (Expenses still reachable and a claim can be created)
carry it, and §3's matrix row matches. Your check — Expenses, Leave encashment and Request
advance stay, only the salary parts go — is met, with encashment and advance on the flags
they already have today. That is right, not a weakening: those two are hidden today on
tenants that do not have them, and Wave 1 should not change that.

**Notes (small):**

- **n1 · Which page does Pay open without payroll?** §4's route table still maps *My pay*
  to `#pay` → `finances`, salary tab, and the page opens on the salary tab today
  (`fin-tab-salary` is the active one, `hrms-employee.html:2788`). AC-44 says opening Pay
  lands on Expenses. Add one line to §4: without `plan_payroll`, the Pay group opens
  `#pay/expenses`, and `#pay` shows the no-permission state (§9 already assumes this).
- **n2 · The missing-key rule does not cover these two flags.** §3 gives the rule for
  `plan_*` and `goals` only. Say what happens when `leave_encashment` or `advance_request`
  is absent, or the features call fails. Today absent behaves as false (the JavaScript
  reads `f.leave_encashment` straight), so "absent means hidden" matches today. Write that
  down, and add it to AC-45.

### B2 · The language row — **closed, and better than I asked for**

`set_my_language` is dropped from Wave 1 (decision 4), so there is no write path to argue
about. AC-18 defines "offered language" and pins the 17-enabled-language case; AC-49 pins
that no frame module writes a `User` record and that a user whose `User.language` is
already `de` still gets the English frame. `01c` SEC-9 matches, and the data inventory
row for `User.language` says "not written in Wave 1".

**Does anything else still depend on it? No.** I searched all five documents: the only
mentions are the gap-analysis row ("Drop from Wave 1"), AC-18, AC-49, the edge-case row,
§12's out-of-scope list and `01c` SEC-9. No story, no AC, no security or DevOps item needs
it. The profile-sheet AC (AC-17) lists name, role line, My account, desk switch and Tenant
admin — no language row. Clean.

- **n3 (cosmetic).** AC-18 reads as though the frame still computes an offered-language
  list. If no row is built at all, the honest oracle is "no language control is in the
  profile sheet on a site with the Frappe default 17 enabled languages". Say which it is,
  so the test engineer does not build a list that nothing reads.

### B3 · The persona table — **closed in substance, one correction**

The flags are real and buildable. `has_reports` is exactly the first condition in today's
code (`hr_api.py:121`: `frappe.db.count("Employee", {"reports_to": emp.name, "status":
"Active"}) > 0`), and the stand-in rule the spec refuses to use is lines 122-127, as I
described it. `is_hr` is line 116 (System Manager or Administrator, HR Manager, HR User).
AC-47 pins the difference. Good.

**Is every persona covered?** Yes, on the two flags plus "no Employee record":

| Flags | Row | Bar |
|---|---|---|
| is_hr, has_reports | 1 | Home · Inbox · Company · Team |
| is_hr, no reports | 2 | Home · Inbox · Company · Time |
| reports, not HR | 3 | Home · Team · Inbox · Time |
| neither, payroll | 4 | Home · Time · Pay · Goals |
| neither, no payroll | 5 | Home · Time · Inbox · Goals |
| no Employee record | 6 | Home · Inbox · Company |

**Is precedence unambiguous? No — see the verdict, point 1.** Row 6 is last, so Asha
matches row 2. Rows 1-5 also need "Active Employee": a leaver with an enabled login
(AC-68) has an Employee record that is not Active, and no row names him. Add "Active" to
rows 4 and 5 and say a non-Active employee falls to row 5 (or row 6) — one line.

**Is the stated consequence acceptable? Yes, with one line added — a seventh row is not
needed.** An HR user with no direct reports losing the Team panel is the right call: the
panel they see today is built from the stand-in list, which for store HR is head office —
people outside their store. Taking it away is a narrowing, and narrowing is what decision
7 asked for. But the spec should say **what they get instead**: Company › People. That is
gated by `plan_org_structure` (§3), so **on a tenant without that plan, a store HR person
ends up with no people list at all**. That is a real loss of a page they use today. It is
a line for Surbhi to see, not a redesign — and it is cheaper to say it now than to hear it
from DTC.

- **n4.** §2's sentence "it closes the leak the analyst found" is wrong as written — see
  verdict point 2. Also, nothing in the spec says `get_manager_dashboard` refuses a caller
  with no reports; the Team gate is in the browser only. Say whether that is accepted in
  Wave 1 (it is consistent with §12 putting the Team screen out of scope), so a tester
  does not file it.

### B4 · The fallback order — **closed, and deterministic**

I walked the order Home → Inbox → Time → Goals → Pay → Team → Company for each row:

| Persona | Missing page | Bar that comes out |
|---|---|---|
| Rahul, payroll, no goals app | Goals | Home · Time · Pay · Inbox |
| Rahul, no payroll, no goals app | Goals | Home · Time · Inbox · Pay (Pay exists — Expenses) |
| Priya, store HR, no reports | — | Home · Inbox · Company · Time |
| Asha, no Employee record | Time, Goals, Pay, Team | Home · Inbox · Company (three buttons) |
| Sandeep | — | Home · Team · Inbox · Time |

Every case lands in one place only, and More is always last. That answers B4.

- **n5.** Goals-off tenants exist, so add the two derived bars above as named cases under
  AC-11 rather than leaving AC-11 generic.
- **n6.** AC-20 says the Inbox menu item, the bell **and the Inbox bottom-bar button** show
  the same total. Rows 1, 2 and 4 have no Inbox button. Reword to "where the bar shows one".

---

## 2. Majors and minors from `02b`

| Item | State | Evidence in revision 2 |
|---|---|---|
| M1 security/privacy oracles | Closed | AC-69 (registry: Guest, wrong persona, scope per whitelisted function), AC-46 (SEC-12 field list), AC-49, AC-56, AC-57, AC-58, AC-55, AC-59 |
| M2 decisions without an AC | Closed | AC-53 (corrections stay in HR's queue), AC-26 + AC-52 (store HR search and queue, head-office person with no branch), gate 3 (swap timing) |
| M3 the count | Closed | §5 part table with doctype, filter, audience, row wording and link; bell opens `#inbox`; AC-54 refresh without reload; "count only what the portal can act on" stated, with expense claims and advances named as not counted |
| M4 five states per persona | Closed | §9 plus AC-60 (search fails), AC-61 (zero badge), AC-62 (session ended → `/login`), AC-63 (Asha gets empty parts, not the throw) |
| M5 edge cases | Closed | §10, including the two-Employee-record helper choice (Active record, one helper in both endpoints), the leaver, long names with test values, no photo, two tabs |
| M6 out of scope | Closed | §12, including 01b §14 items 5-12 |
| M7 loose oracles | Closed | Spot-checked AC-6, 8, 9a/b/c, 13, 14, 16, 17, 24, 29, 31, 33, 40, 43 — each now names a value, a status code, a payload or a file |
| M8 prototype differences | Closed | §11, five rows, (a) held as open question 1 |
| m1 stories | Closed | Named personas (Rahul, Sandeep, Kamal, Priya, Asha), points, screen column, "must not" stories US-14 to US-17 |
| m2 matrix | Closed | Growth behind `goals`; System Manager shown as `is_hr`; the no-Employee column added |
| m3 missing plan keys | Mostly | §3 rule covers `plan_*` and `goals`; see n2 |
| m4 compliance | Closed | §15, with "the analyst is not a lawyer" and the theme-retention line |
| m5 copy | Closed | §6, ten messages; AC-29's four scopes match §6's four empty-search sentences |
| m6 AC-43 scope | Closed | Login, admin console, field check-in named; vendor and driver checks pinned to a tenant with `vendor` on |
| m7 numbering | Closed | Open questions run 1-4 |
| m8 own commit | Closed | AC-43 |

**Did closing them break anything?** I checked the mechanics:

- Every AC number from AC-1 to AC-71 is defined exactly once (AC-9 is split into 9a/9b/9c).
  No AC is referenced anywhere in the document without being defined.
- The old numbers keep their old subjects, so `02b`'s tables still read across. Confirmed
  by reading AC-1 to AC-43 side by side with revision 1's subjects.
- Every story has at least one AC. Three security-structure checks — AC-69 (registry),
  AC-70 (no module state), AC-71 (no `ignore_permissions`) — sit in the bundled
  "US-12, US-13, US-14, US-15, US-17" section but belong to none of those stories.
  **n7:** give them a home, or add a short "US-18 · the endpoints are safe to ship on
  their own" story. They are the ones that carry SEC-2, SEC-6 and SEC-15.
- No story points at removed behaviour. US-5 is sign-out and account, and its ACs now hold
  the "no language row" checks rather than a language-change story. Nothing anywhere still
  asks for a language control, a stand-in Team list, or a Pay group that disappears.

---

## 3. Traceability

I re-walked `01c` revision 2 and `07` against §17.

- Every `SEC` and `PRIV` id in `01c` appears in §17 with at least one AC, and each AC
  named does test the thing. **SEC-13 does not exist** — `01c` jumps SEC-12 → SEC-14, and
  the number is used nowhere in any of the six documents. Cosmetic, but say "no SEC-13" so
  nobody hunts for a lost requirement.
- **n8:** §17's SEC-2 row says "plus the Guest and wrong-persona cases inside AC-8, AC-21,
  AC-26". AC-8 does not mention Guest or a 403. AC-69 already carries SEC-2 properly.
  Trim the row to AC-69 rather than pointing at ACs that do not test it.
- Every `OPS` id in `07` §1-4 is placed: OPS-1 to OPS-19 in §17, and OPS-31 in §12.
  OPS-26, 31, 33 and 34 are borrowed from slice 012 and are not this slice's to close.
- §3b's decisions all land: OPS-14 rollback in gate 4 and §13; OPS-17 "Slow 4G with 4× CPU"
  in §13 and in the speed ACs; OPS-4's five conditions in gate 3, which also closes my
  §6 Q1; OPS-13 in AC-64; OPS-12 in AC-65; OPS-16 and OPS-19 in gates 2 and 6.
- The 00 revision note does the right thing: it says the newer documents win, and lists
  each superseded line rather than rewriting history. The size estimate moves honestly
  from "about 11 days" to 11-13.
- `01c` revision 2 does not contradict the spec anywhere I could find. The one place to
  watch is SEC-14: it changes today's **live** bell and org-chart search the moment it is
  released, not at the swap. `01c` says so in its handoff note; the spec's release gates
  do not repeat it. **n9:** add it to §16 so the release note carries it.

---

## 4. What is still with Surbhi

| # | Question | Blocks |
|---|---|---|
| 1 | The Team-panel leak (verdict point 2): narrow `get_manager_dashboard`'s orphan block in Wave 1, or ticket it? | Whether §2's claim stands; one AC |
| 2 | HR with no reports on a tenant without `plan_org_structure` has no people list at all. Accept, or give them Company › People regardless? | §3 matrix row |
| 3 | Open question 1 in the spec: the desk-link label and whether plain managers get it | AC-17, difference (a) |
| 4 | Residual risks R3, R4, R6 in `01c` need an owner | The security review at the end |
| 5 | Confirmation that decision 3 covers real data on the preview page (R5) | The first release carrying the preview page |

Questions 3 to 5 were already open and none of them blocks day 1, which is still the page
split (US-10, AC-36 to AC-39, AC-64). That work can start whenever the coordinator
schedules the freeze.

## 5. Definition of Ready

| Box | Revision 1 | Now |
|---|---|---|
| Brief approved | ✓ | ✓ |
| Prototype reviewed | ✓ | ✓ |
| Every state specified per persona | ✗ | ✓ §9 |
| `01c` written and reviewed | ✓ / not reviewed | ✓ reviewed; re-check pending |
| `07` §1-4 | ✗ §4 missing | ✓ with §3b |
| Gap analysis verified in source | ✗ | ✓ — I re-checked four of its rows myself |
| Stories: personas, INVEST, sized, screens, "must not" | ✗ | ✓ (no YouTrack import table; not needed unless someone imports) |
| Oracles on every check | ✗ | ✓ |
| Traceability complete | ✗ | ✓ with n8 |
| Permission matrix with negatives | Partly | ✓ §3 and `01c` |
| Edge cases | ✗ | ✓ §10 |
| NFR numbers | ✓ | ✓ §13 |
| Migration stated | ✓ | ✓ none |
| Compliance sub-analysis | Partly | ✓ §15 |
| No prohibited capability | ✓ | ✓ |
| Open questions owned | ✓ | ✓ |

Five boxes failed last time. **None fails now.** The slice is ready to build once the two
corrections in the verdict are made — they are edits to the spec, not to the plan.

## The three closing questions

- **The human test.** Yes. A store HR person stops seeing head-office names they cannot
  act on, an employee without payroll can still file an expense, and nobody is shown a
  Save button that refuses them.
- **The AI test.** Nothing AI-shaped in this slice. Correct.
- **The automation test.** The frame automates nothing; it moves navigation. The one
  process risk is the Team panel, which still shows a list built by a rule
  (`reports_to is not set`) that nobody chose — see verdict point 2.

## Assumptions

- `[ASSUMPTION]` Line numbers are as of the worktree at `6ad7936`.
- `[ASSUMPTION]` `get_manager_dashboard` is the endpoint behind the Team panel; I read it
  in `hr_api.py` but did not run the page.
- `[ASSUMPTION]` `leave_encashment` and `advance_request` behave on the frame exactly as
  they do on today's page (absent or false hides the item).

The analyst is not a lawyer; nothing here is a legal ruling.
