---
slice: 072-seats-follow-reporting
artifact: 01c-security-privacy-requirements
author: hrms-security-privacy-engineer
date: 2026-10-25
status: draft - I recommend, Surbhi decides
inputs: [01-product-brief.md (24 Oct), 02-design.md (25 Oct, approved on the designer's recommendations Q1-Q6), 04-impact-and-strategy.md (25 Oct, proposal), prototype-v1.html, 069 01c rev 2, 065 01c rev 3 (worktree 060-manager-review), 064 01d (worktree 069-wall-chart). Code read at origin/dev af0b7cdf in worktree 069-wall-chart - hrms/hrms/alvoraa_org_structure/register.py, api.py, hrms/hrms/alvoraa_hr_core/access.py, alvoraa_portal/.../portal.js (posWall*), scripts/check_wall_chart.js, scripts/run_dom_tests.js, .github/workflows/ci.yml, alvoraa_portal/tests/test_portal_security_010.py. Nothing was run; no site, bench or container was touched.]
---

# 072 seats · Security and privacy requirements: Seats follow the reporting line

**I recommend. Surbhi decides.** I also wrote the 065 and 069 requirements this slice leans on.
At `06`, somebody other than me should check SEC-1's gate and PRIV-1 (lesson 6).

## 0 · Bad news first

1. **This slice tells some readers something they cannot see today: who each person's manager is
   on their Employee record.** The brief says reporting lines "are already shown on the Organisation
   chart". At DTC that is not true. A company that keeps seats gets the **seat** tree on the
   Organisation page, not Reports To (`api.py:107-109` → `_position_children`, which hangs seats by
   `reports_to_position`). And slice 064 decided on purpose that the person-to-manager link is
   **HR-only** on Positions: `reporting_mismatches` returns nothing to a reader without HR scope
   (`api.py:434-436`), and the "in no seat" list never names a manager (`register.py:454, 464`).
   The strategy sends `manager` to the owners too. For the 273 of 361 people whose seat agrees with
   their manager, nothing new is learned. For the other 88, it is new. **This needs Surbhi's yes by
   name (Q1), because it reverses a 064 control for one fact.** *Verified in code.*
2. **The strategy's server test would never run in CI.** It is planned at
   `hrms/hrms/alvoraa_org_structure/tests/test_reports_to_072.py`. CI runs the tests of
   `alvoraa_goals` and `alvoraa_portal` only (`ci.yml:495-496`); for `hrms` it runs six payroll
   doctypes (`ci.yml:526-529`). 064's chart tests live in `alvoraa_portal/tests/` for that reason.
   **The 072 server test must live there too** (SEC-1). *Verified in code.*
3. **A leaver can still sit in a seat.** No hook ends an assignment when someone leaves (strategy
   assumption, not contradicted by my read), and the assignment read does not filter on the
   person's status (`register.py:294-299`). So "the manager sits in a seat on this page" does not
   mean "the manager works here" (lesson 3). SEC-1 checks the manager's status, and the person's own.
4. **The 064 connector check is not in CI.** It needs Playwright and a browser
   (`check_positions_connectors.js`). The CI guard for "no false line" must be a jsdom check in the
   DOM suite (SEC-4), with the Playwright check as the second proof.

## 1 · What I checked

| Check | Result | Label |
|---|---|---|
| Who opens Positions | Frappe Read on `Alvoraa Position` (`register.py:68-72`), refused otherwise (`:264-265`) | Verified in code |
| Rows in the reply | Seats filtered by `_scope()` company and branch, and by the `branch`/`department` arguments, narrowed to the reader's branches (`register.py:267-288`) | Verified in code |
| People in the reply | Every current assignment of those seats, **any employee status** (`register.py:294-314`) | Verified in code |
| HR scope | `permitted_employee_filters()` gives `NO_EMPLOYEES` to anyone without an HR role or System Manager (`access.py:252-286`). DTC's owners (Org Structure Editor, no HR role, one branch each - 064 01d) get nothing | Verified in code; DTC roles from 064 01d (run 21 Oct) |
| "In no seat" list | Only for HR scope; Active only; no manager name (`register.py:446-448`, `:454`, `:474-479`) | Verified in code |
| A parent seat outside the reader's view | Its id is still sent in `reports_to`; its title is blank (`register.py:392-395`) | Verified in code. Pre-existing; see §9 |
| `ignore_permissions` in `register.py` | 4 (`:156`, `:544`, `:727`, `:794`); ceiling 4 at `test_portal_security_010.py:819` | Verified in code |
| Wall chart copy | `posWallCopy` gives each person only `{name}`, plus `leaving` on the HR copy, and the HR copy is HR-only (`posWallMayHr`) | Verified in code (`portal.js:2368-2420`) |
| DTC's real data: how many seated people report to a Left employee; which seats the owners' branches hold | **I could not check that.** It needs a read-only count on DTC by someone allowed to run it | Unknown |

## 2 · Threat model, four lines

1. **Who wants it, cheapest way:** a branch-limited owner or store head with Positions, opening the
   browser's network tab to read who manages whom elsewhere; a plan non-reader looking for a plan
   in the shape of the chart.
2. **Blast radius of one mistake:** one tenant. Worst case, a reader in one branch or company learns
   the name or seat of a manager outside their scope. Cross-company is possible only if the
   "already in this reply" rule is skipped, so it is tested directly.
3. **What is new:** the person-to-manager link from the Employee record, on a page that showed only
   the seat tree to non-HR readers. Nothing is collected or stored.
4. **How we would find out:** only if a reader noticed. So the controls are structural and tested in
   CI, with marker values that must never appear.

## 3 · Data inventory

| Item | Class | Purpose | Retention | Who may see |
|---|---|---|---|---|
| `manager` on a person row: the manager's employee id | Personal, internal (a reporting line) | Draw the person under their manager's seat | Not stored; worked out per page load | SEC-1 |
| `manager: ""` (no Reports To on the record) | Personal, internal (a record gap) | Tray line "No manager on their record" | Not stored | HR scope only (SEC-1) |
| Copies, quiet lines, "Where it shows" tray | Derived from the reply | Show where the seat appears | Screen only | Whoever holds the reply |
| Per-person tray line naming the manager | Personal, internal | Say why a person is drawn there | Screen only | Name only if the manager is in the reply; unseated manager only for HR |
| Paper: `copy`, `same`, `more` on a seat | Seat titles and counts | Print what the screen draws | Paper (069 PRIV-3 rules) | Anyone at the wall |

No new field, DocType, log line, cache or endpoint.

## 4 · Who must NOT see what

| Reader | May | Must NOT |
|---|---|---|
| HR / System Manager, company-wide | `manager` for people in their reply, including an unseated Active manager in their "in no seat" list; `""` | A manager in a company outside `_scope()` |
| HR tied to a store | The same, inside their branches | A manager seated or listed outside their branches - not the id, name, seat or title |
| Owner with Positions, no HR role (DTC's 2) | **Only if Surbhi says yes (Q1):** `manager` when the manager is Active and seated in a seat in their reply | `""`; an unseated manager's id or name; any manager outside their branch |
| Anyone, past or future `as_at` | The chart as before | Any `manager` key |
| Plan non-reader (065) | Copies as anyone else | Any plan key, word, flag, order change or count, in a copy or anywhere |
| Visitor at the wall | Names and seat titles (069 PRIV-1) | A manager id, a manager's name in a tray line, any plan or private field |

## 5 · Obligations engaged

| Obligation | What it needs here | Checked |
|---|---|---|
| DPDP Act 2023 and Rules 2025 - reasonable safeguards, purpose limitation | Send the link only where needed and allowed (SEC-1); nothing stored | Baseline §2, verified 24 Aug 2026 (62 days today; stale from 22 Nov 2026) |
| OWASP ASVS 5.0 L2 - access control on every request, nothing beyond need | SEC-1, SEC-2 | Baseline §5 |
| CERT-In, ISO 27001, SOC 2, GDPR, EU AI Act | Not engaged: no new system, log, transfer or automated decision | - |

No question for counsel. Reporting lines are ordinary employment data, shown inside the employer.
I am not a lawyer; nothing here turns on a point of law.

## 6 · Abuse cases

| Who | What they try | What stops it |
|---|---|---|
| Owner tied to branch A | Reads the reply for the manager of a person whose manager sits in branch B | SEC-1: absent; tray says "a manager who is not on this chart" |
| HR of company A (multi-company tenant) | Learns a company-B manager of a company-A person | SEC-1: the manager is not in the reply, so absent |
| HR, company-wide | Calls `position_table(branch="A")` and still gets ids of managers in B | SEC-1: "in **this** reply", after the branch filter |
| Owner | Learns who has no manager on record | SEC-1: `""` goes to HR scope only |
| Anyone | Calls with a past `as_at` to read old lines | SEC-1: absent. Reports To has no history, so a past chart with today's line would be false |
| Leaver still seated as manager | Has people drawn under their seat | SEC-1: a non-Active manager is never sent |
| Plan non-reader | Spots a copy or order change that only a plan explains | PRIV-1 |
| Visitor at the wall | Reads manager names off a printed tray line | PRIV-2: tray lines never print; paper keys are a fixed list |

## 7 · Requirements

Each says what must be true and how it is tested. The analyst traces each to an acceptance criterion.

**SEC-1 · The `manager` key is sent only when it tells the reader nothing about anyone outside their
reply. It fails closed.**
In `position_table`, on a person row:
- The **manager's employee id** only when all hold: `as_at`, read as a date, is today; the person is
  Active; the person's Reports To is set; and the manager is Active and is **already in this reply**
  - seated in a seat of this reply (after the `branch` and `department` arguments), or, for an HR
  -scope reader, in this reply's `unseated` list. **For a reader without HR scope, only the first
  half applies, and only if Surbhi says yes to Q1.** Until then: HR scope only.
- **`""`** only for an HR-scope reader, when the Active person's Reports To is empty.
- **Absent** in every other case. Never `null`, never a name, never a seat.
- Read through the existing assignment query and Frappe's link-field join (constant field strings,
  no SQL built by hand). The manager's status comes from the manager's own row in the reply, or
  from `unseated` (Active only).

*Test (blocking, CI):* a new `alvoraa_portal/alvoraa_portal/tests/test_reports_to_072.py` - **not**
under `hrms/`, which CI does not run. Data built in the test with marker names:
`MGR-OK-SNTL` (seated in scope), `MGR-OUT-SNTL` in seat `SEAT-OUT-SNTL` (another branch),
`MGR-OTHERCO-SNTL` (another company), `MGR-LEFT-SNTL` (Left, still seated), `MGR-UNSEATED-SNTL`
(Active, no seat). For each reader - System Manager, HR company-wide, HR tied to branch A, owner
(Positions Read, no HR role, branch A) - assert:
(a) `MGR-OK-SNTL`'s id is present for its people (proves the test can see a key at all);
(b) `json.dumps(reply)` contains none of the other markers, none of their employee ids, and not
`SEAT-OUT-SNTL`;
(c) `MGR-UNSEATED-SNTL`'s id appears for HR company-wide only, never for the owner;
(d) `""` appears for HR only; the owner's reply holds no `"manager": ""`;
(e) HR company-wide with `branch="A"`: no id of a manager seated only in B;
(f) `as_at` yesterday and tomorrow: no `manager` key anywhere;
(g) a Left person still seated: no `manager` key on their row.
**Shown to fail once:** remove the "in this reply" check on purpose; (b) and (e) must fail. Record it
in the test report, then undo.

**SEC-2 · The reply changes by one key and nothing else, and no new door opens.**
- Each person row's keys **equal** a list written in the test: today's keys plus `manager` (and
  065's `plan` for plan readers once 065 lands). Compared with a literal, not the code's own
  constant, so a further key fails.
- No new `@frappe.whitelist`, no `allow_guest`, no new endpoint, no new log line, no cache, no
  stored copy, no write. `api.py` (`reporting_mismatches`, the Organisation page) is not in the diff.
  The only source of manager facts on the Positions page is the `manager` key - no browser call to
  `reporting_mismatches` or to Employee is added (lesson 2: no unscoped sibling reader).
- `ignore_permissions` in `register.py` stays **4**; the CEILINGS row is not raised.
- **The Organisation page is byte-for-byte unchanged**: `ocNodeCard` without the two new optional
  fields gives identical markup.
*Test:* (a) the literal key-set assertion inside SEC-1's test file, for HR and owner; (b) the
existing `test_portal_security_010.py` counter, unchanged; (c) DOM suite: `ocNodeCard` HTML for an
Organisation node equals a stored expected string; (d) review check at `06`: the diff adds no Python
outside `position_table` and the test, and no `frappe.call`/`gpFetch` in Positions code.

**SEC-3 · Copies, quiet lines and the "Where it shows" tray name only what the reader's reply
holds.**
- A copy exists only under a seat that is drawn. A parent or manager seat outside the reply reads
  "a seat above your view", never a title or id - including the opaque `reports_to` id the reply
  already carries.
- The per-person tray line names a manager only from the reply: a seated manager by name and seat
  title; an unseated manager by name **only** when `POS.unseated` exists and holds them (HR). Every
  other case reads "Reports to a manager who is not on this chart". "No manager on their record"
  shows only when `manager === ""`.
- The tray's "Where it shows" list lists drawn boxes only.
*Test (blocking, CI DOM suite, `check_positions_tree.js`):* a fixture whose reply holds the reader's
seats only, plus marker values in places the page must not echo: a `reports_to` id
`SEAT-HIDDEN-SNTL` on a seat whose parent is not in `rows`, and a person whose `manager` id
`MGR-ABSENT-SNTL` matches nobody in the reply. Open every box's tray and every copy with all folds
open: the page HTML contains neither marker; "a seat above your view" and "not on this chart"
appear where expected. Run twice: with `unseated` holding the unseated manager (name appears) and
with `unseated` absent (name does not appear).

**SEC-4 · No line or word states a false manager.** *(Integrity control: a wrong line is a wrong
statement about a person's manager, which feeds a grievance.)*
- Every person drawn in a box whose seat is under seat P either has their manager seated in P, or
  is in their seat's home box and has no drawn manager seat (home rule).
- A copy has no fold button and nothing under it. Each person is drawn exactly once.
- Branch and Department views are unchanged, so they make no claim about managers.
*Test:* (a) **CI**, jsdom in `check_positions_tree.js`: an oracle written in the test, from
`rows` and the `manager` keys only - not from `posPlace` - checks every drawn person's parent box,
across the five brief cases (split seat; vacancy on home only; hidden empty home; manager in no
seat; manager outside scope), Q5 (manager in the same seat) and a manager in two seats. Shown to fail
once by swapping two managers in the fixture. (b) Playwright `check_positions_connectors.js` with
the new meaning of "real parent", worked out independently of `posPlace` (strategy §2.4), on the
census-shaped fixture. Not CI; its result goes in the implementation notes.

**PRIV-1 · Copies never betray a plan, and 065's plan rules hold unchanged.**
- Copies, their order, their words and every count are worked out from current assignments and the
  `manager` key only - never from `plan`, `opening`, `leaving` or `hired_on`. A plan cannot create,
  remove, move or reorder a box.
- The server's `manager` value never depends on a plan.
- The job opening stays on the home box only, so 065's full-seat opening rule (065 SEC-4 point 3)
  still governs it alone.
- For a plan reader, the plan mark travels with the person into the copy. For anyone else, no plan
  key or word exists anywhere, as 065 SEC-4 says.
*Test:* (a) **CI**, server: 065's byte-for-byte test (non-reader reply with a plan equals the reply
without) still passes with `manager` keys in the data, and the `manager` keys are identical with and
without a plan; (b) **CI**, jsdom: the same fixture with and without `plan`, `opening`, `leaving` and
`hired_on` keys on a person drawn in a copy gives the same list of boxes (seat id, copy or home,
parent, people, quiet line), ignoring only the plan mark elements; (c) 065 SEC-4 (f)'s browser
check (no plan words for a non-reader) re-run with copies on the page. Until 065 lands, (a) and (c)
run on 065's branch at merge (switch-on check C3).

**PRIV-2 · The wall chart's allowed-field copy (069 PRIV-1) still holds with copies.**
- A person on paper stays `{name}`, plus `leaving` on the HR copy only. A seat gains only `copy`
  (true/false), `same` and `more` (seat titles from the reply and counts - never a person's name, an
  employee id or a manager id). Tray lines never print.
- Each person prints once; the footer counts seat records and people once.
*Test (blocking, CI DOM suite, `check_wall_chart.js`):* add `manager:"MGR-SNTL"` and a manager named
`MGRNAME-SNTL` who is drawn only in a tray line, to 069's sentinel fixture, with a person in a copy
who also carries every 069 sentinel and a `plan`. Run tick off and tick on: no sentinel, no
`MGR-SNTL`, no `MGRNAME-SNTL`; every seat's keys equal the literal list for the mode (069's list plus
`copy`, `same`, `more`); printed names = people in seats, each once. Shown to fail once by copying
`manager` onto paper.

## 8 · Questions

| # | Question | For | Blocks | Default meanwhile |
|---|---|---|---|---|
| Q1 | **Must know.** May a Positions reader without HR scope (DTC's 2 owners, any head given Read later) see who reports to whom, when **both** people are already on their page? This reverses 064's "owners: seats only" for this one fact. Without it, owners see no copies at all, and the brief's CXO benefit is gone | Surbhi | Step 1's gate (one condition) | `manager` for HR scope only. **My recommendation: yes** - both people are already on their page by name and seat, the seat tree tells the same story for 273 of 361, and a reporting line is directory-level. Keep `""` and unseated names HR-only either way |
| Q2 | **Should know.** How many seated DTC people report to a Left employee, and how many seated people are themselves Left? | Surbhi, via a read-only count | Release note only | They stay in their home box (SEC-1) |

## 9 · What blocks what

**Blocks the build** (in the spec, passing before `06`): SEC-1, SEC-2, SEC-3, SEC-4 (a), PRIV-1 (b),
PRIV-2. Q1 must be answered before step 1; until then, build the HR-scope default.

**Blocks switch-on at DTC:**
- C1. SEC-4 (b) Playwright result recorded on the census-shaped fixture.
- C2. 069's C2 still holds: someone with access lists the roles with Read on `Alvoraa Position` at
  DTC. Any role added there gets the manager link for its scope. *I could not check that.*
- C3. Merge order with 065: PRIV-1 (a) and (c) pass on the merged code.
- C4. The served `portal.js` contains the new code (deploys do not refresh assets; DevOps check).

**Observability (lesson 1).** DTC has 1 company and 0 HR with a branch limit, so the cross-company
and store-HR cases cannot show on DTC's data; only the 2 branch-limited owners exercise "manager
outside scope", and only if Q1 is yes. The Left-manager case is unknown (Q2). So "no leak" on DTC
proves nothing; the CI tests build every case themselves.

## 10 · Residual risk

| # | Risk | Label | Owner | Accepted |
|---|---|---|---|---|
| R1 | If Q1 is yes, owners learn the Employee-record manager of the 88 people whose seat disagrees | Intentional trade-off | Surbhi | **Waiting** for Q1 |
| R2 | The Organisation page still hangs people by seat at DTC, so it disagrees with Positions for those 88. Kept unchanged on instruction | Temporary debt - removed by a later slice that applies the same rule there | Surbhi | **Waiting** |
| R3 | A Left person can stay seated and is still drawn (no hook ends the seat). 072 does not make it worse | Temporary debt - removed when leaving ends the assignment | Surbhi | **Waiting**; already open since 064 |
| R4 | The reply sends a parent seat's opaque id even when it is outside the reader's view (`register.py:392`). 072 must not use it to name anything (SEC-3) | Acceptable simplification; P4 | Surbhi | **Waiting** |
| R5 | The "no false line" proof in a real browser is not in CI; the jsdom oracle is | Intentional trade-off - no Playwright in CI | Surbhi | **Waiting** |

None of these is dangerous debt.

## Subtract pass

Removed on this pass:
- A permission-aware Employee read (`frappe.get_list`) as the gate. It adds a statement and an id
  list, and DTC owners' Employee rights are unknown; Q1 decides the same thing in one line.
- A separate privacy requirement for `""` - folded into SEC-1.
- A requirement for the new error words - good hygiene, already in the design's acceptance list,
  not a security control.
- A DPIA, a counsel question and an audit or log requirement - nothing is collected, stored or
  changed.
- The statement-count test - DevOps owns it, and it does not prove a control.

Kept: six requirements. Each closes a path I can name with a file and line.
