---
slice: 064-organogram-improvements
artifact: 01d-security-privacy-requirements (the 01c role; 01c in this folder is the engineer's bug findings)
author: hrms-security-privacy-engineer
date: 2026-10-21
status: draft - written before the functional spec
inputs: 01-product-brief.md (D1-D11); 01c-engineer-findings.md; 02-design.md (Q1-Q11); prototype-v1.html; security-compliance-baseline.md; compliance-feature-map.md; nfr-budget.md; memory legal-retention-rules-2026-09.md; 063's 01c as the model. Code read in worktree 060-manager-review (branch slice/062-widget-after-checkin, same Positions code as origin/dev 76f15e1d) and origin/main a473c191, 21 Oct 2026. Frappe source read on the local bench. Two read-only scripts on dtc.alvoraa.co, 21 Oct 2026 (settings and counts only, no names, nothing written, rolled back).
---

# 064 · Security and privacy requirements: the Positions organogram at 90 seats

*I did not write the brief or the design. I am specifying here, not reviewing. SEC-8 (the check on
the seat link) and the Job Opening change history in PRIV-3 are my own mechanisms, so at `06`
somebody other than me should check those two.*

**Treated as settled:** Surbhi's approval of the design, 21 Oct 2026 ("the proposed design of the
positions look amazing"). **Treated as accepted, flagged for her to confirm:** the designer's Q1-Q11
(so "No reporting manager" holds **people** with no manager plus any non-top seat with no parent;
"In no seat" is in 064; print is later), and the PM's D1-D6 where the design does not differ.
**Out of scope:** slice 065 (Plan a replacement). §8 lists only what 064 must not get in its way.

---

## 0 · Bad news first

**1. The design's statement of who can open Positions at DTC is wrong for production today.**
DTC runs `main`, and on `main` the page is opened by a **setting**, not by Frappe permissions.
DTC's settings let **HR Manager (6 users) and Org Structure Editor (2 users)** open it, and HR
Manager, System Manager and Org Structure Editor edit it. *(Verified by running it, 21 Oct 2026;
`main`'s `register.py` reads `alvoraa_org_positions_view_roles`.)* The design describes the `dev`
model (slice 061, "Positions by Frappe permission"). **When 061 reaches `main`, DTC's own Custom
DocPerm rows take over, and the 6 HR Managers lose the page.** Only System Manager (1 account, with
no Employee record) and the 2 editors keep it. *(Verified in DTC data and in Frappe's
`permissions.py:507-520`: Custom DocPerm rows replace the shipped ones.)*

**2. So, with the fail-closed rule in SEC-2, after 061 nobody at DTC except one System Manager
account would see the new people lists.** Both Org Structure Editors hold **no HR role** and are
**limited to one branch** by a Branch User Permission. The "In no seat" and "No reporting manager"
lists are lists of named people, so I give them only to HR (SEC-2). That is the right default, and
it makes the feature invisible at DTC until Surbhi decides who should see it. **Must-know Q1.**

**3. The automatic placement trusts a link that any HR User can already set through the API.**
The seat link on Job Opening is `read_only` (`org_job_link.py:39-41`), but Frappe does not enforce a
field's `read_only` on the server. Only `permlevel` is enforced. *(Verified in the installed Frappe
source on the local bench: no server check on a field's `read_only` in `base_document.py`,
`document.py` or `client.py`.)* Today that link only changes what the chart says. Once the hook
places a hire from it, **the link decides who sits in which seat**, and a seat with seats under it
gives its holder the manager's view of the whole Organisation chart (`api.py:777-807`, `reach()`).
**SEC-8 must ship with the hook, or before it.**

**4. `reporting_mismatches` is unscoped as well as slow.** It checks only the role
(`frappe.only_for`, `api.py:415`). It reads every company and every branch on the site, and it runs
about three to five queries per seated person (`api.py:418-438`). At DTC that is **about 1,100 to
1,800 queries per call** for 364 assignments *(inference from the code and the DTC count; not
timed)*. The "records disagree" chip **must not ship on it as it stands** (SEC-5).

**5. Most of these controls cannot be seen working on DTC's real data.** DTC has 1 company, 0 HR
users with a Branch permission, 0 people on notice, and **0 employees who came through Frappe
hiring** (2 openings, 1 applicant, 0 offers). The tests must build their own data. Each
requirement says what data it needs.

None of this is a leak today. Nothing in this slice is live.

---

## 1 · What I checked, and how

| Fact | Where | Label |
|---|---|---|
| `position_table` gates on `may_view()`, then filters seats by `_scope()`: companies, plus branches for a store-tied reader; a seat with no branch is outside every store | `register.py:251-283`, `_scope` `35-60` | Verified in code |
| `_scope()` on `dev` falls back to Company User Permissions, then the caller's own **Active** Employee, for a non-HR reader | `register.py:52-60` | Verified in code |
| "Leaving" is suppressed on the server unless the reader is in the full-reach roles or the leaver is in their reporting line | `register.py:179-229`, `327-341` | Verified in code |
| `permitted_employee_filters()` is the one fail-closed definition of "people this user may see as HR" (companies, narrowed by branch; never an empty filter) | `access.py:252-286` | Verified in code |
| `reporting_mismatches`: role check only, no company or branch filter, queries inside a loop | `api.py:405-439` | Verified in code |
| `_descendant_count` (a server roll-up) filters by company only, not branch | `api.py:199-203` | Verified in code |
| `metrics.org_health` is scoped properly (companies and branches) | `metrics.py:21-62` | Verified in code |
| Assignment rules still run on an `ignore_permissions` insert: weight, dates, not before joining, seat not closed, load cap, one primary; over-fill is checked in `on_update` against **today**, not the start date | `alvoraa_position_assignment.py:38-50`, `227-234`; `alvoraa_position.py:137-143` | Verified in code |
| A Permanent assignment never moves approvals: `_apply_delegation` returns at once unless it is cover | `alvoraa_position_assignment.py:269-270` | Verified in code |
| Frappe HR's Employee `after_insert` marks the applicant and offer Accepted | `hooks.py:260-263`, `employee_master.py:54-85` | Verified in code |
| Closing a Job Opening marks a linked Job Requisition "Filled", as the server | `job_opening.py:126-134` | Verified in code |
| `ignore_permissions` in code (SEC-16 counting method): `api.py` 2 (ceiling 2), `register.py` **4 with no ceiling**, `settings.py` 1, `dotted_line.py` 1, the doctype controllers 0, `org_job_link.py` 0 | counted with the method of `test_portal_security_010.py:810-844` | Verified by running it |
| Job Opening keeps **no** change history (`track_changes` off, no Property Setter at DTC); Alvoraa Position and Assignment do (`track_changes: 1`); Employee does | JSON files; DTC read | Verified in code and by running it |
| Shipped permissions: Job Opening - HR User, HR Manager, System Manager write; Alvoraa Position Assignment - HR Manager, System Manager. DTC overrides the Assignment to System Manager and Org Structure Editor only | JSON; DTC Custom DocPerm | Verified in code and by running it |
| DTC: 1 company; 90 seats, 1 with no parent; 364 assignments, 0 delegating; 445 Active employees, 20 with no manager, 0 with no branch; 0 enabled logins tied to a non-Active Employee | read-only query | Verified by running it, 21 Oct 2026 |
| DTC users: HR Manager 6 (0 with a Branch permission), HR User 6 (0), System Manager 1 (no Employee record), Org Structure Editor 2 (both with a Branch permission applying to Employee, neither with an HR role) | read-only query, counts only | Verified by running it |
| DTC recruitment: 2 Job Openings (both Open, 1 published), 1 linked to a seat; 1 Job Applicant; 0 Job Offers; 0 Employees with a job applicant | read-only query | Verified by running it |
| Find in the design runs in the browser over rows already loaded | `02-design.md` §6.4 item 3 | Verified in the design, not in code (nothing built) |

---

## 2 · Threat model, four lines

**Who wants this, and what is the cheapest way?** Not an outsider. (1) A **store head or department
head** given Positions, curious about the rest of the company - cheapest by reading the network
response of the page, or by calling `reporting_mismatches` directly. (2) An **HR User who cannot edit
Positions** but wants someone placed in a senior seat - cheapest by setting the seat link on a Job
Opening through the API, then creating the Employee from an applicant. (3) An **HR person at one
store** reading the "in no seat" list for every store. (4) A **departing HR person** whose login is
still enabled.

**Blast radius of one mistake.** Cross-tenant: not reachable; one site per tenant. **Cross-company is
the top of the scale here:** a multi-company site (not DTC) where the people lists or the mismatch
chip ignore the company would show one company's HR another company's staff by name. Inside one
company: one branch's names to another branch's HR. Placement: one person in one wrong seat, which
moves the chart and that person's Organisation-page view.

**What becomes possible that was impossible before.** A named list of people with no seat and no
manager, on a page some non-HR roles open. An **automatic write** of a seat assignment on Employee
save, by someone who may have no right to place people. A **public job advert closed automatically**.
A count line that sums people and holes under a seat.

**How would we find out?** The assignment row itself: owner, creation, and a reason naming the
opening and the applicant (PRIV-3). Who pointed the opening at the seat: today **nothing records it**,
because Job Opening keeps no history - PRIV-3 fixes that. A wrong list or a wrong count: only if a
customer notices. That is why SEC-1 and SEC-2 are proven by tests with two companies and two
branches, not by eye.

---

## 3 · Data inventory

Classes follow `compliance-feature-map.md` A1. A1 is not built, so they are declared here and
applied by hand.

| Field or object | Class | Purpose | Retention | Who may see it |
|---|---|---|---|---|
| Seat rows (title, branch, department, job role, places, parent) | internal | Draw the structure | Existing; not changed | Positions readers, within `_scope()` |
| People in seats (employee id, name, share, type) | internal | Who sits where | Existing | As today |
| **new** "In no seat" list: employee id, name, job role, branch, joining date, the matching seat (worked out from loaded seats) | internal (personal) | Say who is missing from the chart | **Not stored.** Worked out on each load | HR within `permitted_employee_filters()` only (SEC-2) |
| **new** "No reporting manager" list: the same fields, for people with no manager | internal (personal) | Item 5 | Not stored | As above |
| **new** roll-up line: seats below, people, to fill, leaving | internal; "leaving" is **sensitive** (a person's own news) | Item 2 | Not stored | Seat and people figures: over the rows the reader already got. "Leaving": only readers the server already lets see leavers (SEC-4) |
| **new** "records disagree" chip: the people whose manager on record differs from the seat tree, with both managers' names | internal (personal) | Show silent faults like bug 3 | Not stored | HR within scope (SEC-5) |
| **new** automatic assignment from a hire | internal | Item 6 | Same as any assignment (kept, ended, never deleted once used - `register.py:484-517`) | As any assignment |
| Job Opening seat link (now editable) | internal - but it now **decides placements** | Link hand-made openings | Life of the opening | HR; changeable only as SEC-8 says |
| Job Applicant (CV, contact details) | sensitive | Frappe HR hiring | Not changed | Not read by 064, except `job_title` to find the opening (PRIV-3) |
| `relieving_date` | sensitive | Already used for "leaving" | Not changed | No new reader in 064 (SEC-4) |

**Nothing new is collected about anyone.** The lists show Employee fields HR can already read in the
desk. What is new is **where** they appear, and that is what SEC-2 and SEC-11 bound.

---

## 4 · Access intent, including who must NOT see what

| Actor | May | Must NOT |
|---|---|---|
| HR Manager / HR User, company-wide, with Positions access | Seats and seated people in their companies; both people lists for their companies; the mismatch chip; Find over all of that | See another company's people, seats or mismatches |
| HR person tied to a store (Branch permission) | The same, for their branches only. An employee with no branch is outside it (DEF-6) | See other branches' unseated people, mismatches or seats |
| Org Structure Editor with no HR role (DTC's owners) | Seats and seated people within `_scope()`, as today; Find over those; roll-ups over those | Receive either people list or the mismatch chip, **until Surbhi decides otherwise (Q1)** |
| Department or store head given Positions read by a tenant | As the editor row above | The people lists; "No reporting manager" for anything outside their rows; a seat whose parent is outside their view counted as "no reporting manager" |
| HR User who cannot edit Positions | Create an Employee from an applicant; be told where the hire was placed or why not | Set or change the seat link on a Job Opening (SEC-8); place anyone in a seat by any other route |
| Positions editor tied to one branch | Link an opening to a seat in their branch | Link one to a seat in another branch or company |
| The new hire | Appear in the seat from the joining date | Gain approvals or a reporting line from the placement (SEC-9) |
| Leaver with a live login | Nothing new | Any list here (the scope helpers use the Active record; see §10 F5 for the gap that remains) |
| Guest | Nothing | Reach any endpoint here. None may be `allow_guest` |

**New-Frappe-app checklist: not engaged.** No app is installed. No public page, no guest access, no
self sign-up, no new role.

---

## 5 · Obligations engaged

I am not a lawyer. These are engineering readings of published sources.

| Obligation | What it asks of this slice | Source and date checked |
|---|---|---|
| **DPDP Act 2023 + Rules 2025** - reasonable security safeguards; purpose limitation; minimisation | Named lists only to people with an HR purpose; fixed field lists; no new copy | Baseline §2, verified 24 Aug 2026 (58 days old - inside the 90-day rule, not stale) |
| **DPDP - phase dates and our role** | Unchanged and still open | Baseline §2 open questions - counsel |
| **Counsel's retention rules of 18 Sep 2026** | Cover driver GPS and performance records only. Seat history is neither. Do not apply the 6-month rule by analogy | Memory `legal-retention-rules-2026-09.md` |
| **GDPR Art 22 / AI Act** | **Not engaged.** The placement copies HR's own choice (the opening's seat); it scores or ranks nobody | Baseline §4 (applicability itself still open with the founder) |
| **CERT-In 180-day log residency** | Unchanged gap (baseline §3a). No new log stream | Baseline §3, verified 24 Aug 2026 |
| **OWASP ASVS 5.0 L2** - access control on every request; no data beyond need | SEC-1, SEC-2, SEC-5, SEC-8 | Baseline §5 |

**DPIA: not needed for this slice.** No new collection, no evaluation of anyone, no new recipient
outside HR. I would change that answer if the lists reached non-HR readers by default.

---

## 6 · Abuse cases

| Who | Tries | What stops it |
|---|---|---|
| **Store head** with Positions read | Reads the page's network response for other stores | SEC-1: the payload holds only seats in their `_scope()`. SEC-2: no people list for a non-HR reader |
| **Store head** | Calls `reporting_mismatches` from the browser console | Refused today by role; after SEC-5, scoped and gated the same as SEC-2 |
| **Store HR** (Branch permission) | Reads the "in no seat" list for every store | SEC-2: the list uses `permitted_employee_filters()`, which narrows to their branches |
| **HR User** without Positions edit | Points a Job Opening at the Owner's seat through the API, then hires a friend from an applicant | SEC-8: the link change is refused unless they may place people in that seat |
| **Positions editor** of one branch | Points an opening at a seat in another branch | SEC-8: the seat must be in their `_scope()` |
| **HR User** | Creates two Employees from one applicant to fill two places | SEC-6: no placement if another Employee already carries that applicant |
| **HR User** | Sets `job_applicant` on an existing employee to move them into a seat | SEC-6: placement runs on insert only |
| **Script / data import** | Imports 400 Employees with a `job_applicant` column | SEC-6/7: each placement checks room and refuses quietly when full; constant queries per row |
| **Anyone** | Expects a placement to move approvals | SEC-9: no approver or `reports_to` is written |
| **Departing HR person** with a live login | Opens Positions after leaving | `permitted_companies` falls back to the Active record only when no Company permission exists; see §10 F5 |
| **Guest** | Any of it | No endpoint here is `allow_guest` |

---

## 7 · Requirements

Each says what must be true and how a test proves it. The analyst must trace every one to an
acceptance criterion, or record Surbhi's decision not to adopt it.

### Security

**SEC-1 · Every new figure rides on the scope `position_table` already applies.**
The roll-up line, the compact card, the "No reporting manager" seats and Find are worked out **in the
browser from the rows `position_table` returned**. No new endpoint for seats or seated people. No
server-side roll-up. In particular `_descendant_count` (`api.py:199-203`) must not be reused - it
filters by company only. A seat whose children sit in a branch the reader cannot see shows only the
children they can see; the count is "over the rows you can see" (design AC 9), never the company
total.
*Test:* (a) Python: a store-tied reader's `position_table` payload holds no seat and no person from
another branch, and none from a second company; (b) JS harness (`scripts/check_positions_tree.js`):
roll-up figures on a given payload equal the counts of the rows in it, including a parent whose
child seat is missing from the payload.
*Observable only if* the fixture has **two companies, two branches, and a seat in branch A with a
child seat in branch B holding people**. DTC has one company and no store-tied HR, so DTC data
proves none of this.

**SEC-2 · The two people lists come from one scoped query, for HR only, and fail closed.**
"In no seat" and "No reporting manager" (people) are returned by `position_table` from **one** query
over Active Employees, filtered by `permitted_employee_filters()` (`access.py:252-286`). That helper
already means "people this user may see as HR": companies, narrowed by branch, nothing for a non-HR
role, never an empty filter. When it returns `NO_EMPLOYEES`, the response carries **no list key at
all**, and the page shows **no tile** - not "0", which would be false. The scope stays inside the
query (a `NOT EXISTS` against current assignments), not a list of 363 ids sent back as `IN (...)`
(nfr-budget §2). The query count of `position_table` is the same for 20 people as for 1,000.
The seat half of "No reporting manager" counts **only seats whose `reports_to_position` is empty**,
other than the top. A seat whose parent is set but outside the reader's rows is "reports above your
view" (K7), **never** "no reporting manager".
*Test:* (a) company-wide HR gets every Active unseated person in their company; (b) a store HR gets
only their branch, and an employee with no branch is excluded; (c) a Positions reader with no HR
role gets no list key; (d) a Left employee with no seat is absent; (e) HR of company 1 never sees
company 2's unseated person; (f) a store reader's top seat with a parent outside their view is not
in the box; (g) query count equal at 20 and 200 employees.
*Observable only if* the fixture has two companies, a store-tied HR user, a Left employee with no
seat, an Active employee with no branch, and a non-HR Positions reader. At DTC only (a) is observable.

**SEC-3 · Find sends nothing to the server.**
Find searches the payload already in the page: seats, seated people and (for HR) the "in no seat"
list. The typed text never leaves the browser - no request, no URL, no log. If a server search is
ever added it must use `_scope()` and POST, like `search_people` (`api.py:628-650`), and that is a
new decision, not part of 064. Find must not call `search_people`: its scope is the Organisation
page's, which differs from Positions' for a non-HR editor.
*Test:* (a) JS harness: a name that is not in the payload returns "No seat or person called that.";
(b) browser check (`scripts/browser_check_positions.js`): typing three letters makes no network
request.

**SEC-4 · "Leaving" appears only where the server already allowed it.**
Every "leaving" word or count - roll-ups, compact-card rows, tiles - is built from the per-person
`leaving` value `position_table` already suppresses (`register.py:327-341`). 064 adds **no new read
of `relieving_date`** anywhere.
*Test:* (a) a reader outside the full-reach roles and outside the leaver's line gets `leaving` empty
and no "leaving" word in any roll-up; (b) review check at `06`: no new `relieving_date` in the diff.
*Observable only if* the fixture has someone with a future relieving date. **DTC has 0 people on
notice today.**

**SEC-5 · The "records disagree" chip does not ship on today's `reporting_mismatches`.**
Before any screen calls it, it is rewritten so that: (a) the query count is **the same at 20 and
1,000 people** - grouped reads of assignments, seats and Employee `reports_to`, joined in Python
from those few reads; today it is about 3-5 queries per seated person, roughly 1,100-1,800 at DTC;
(b) seats come from `_scope()` and people from `permitted_employee_filters()` - today it reads every
company and branch on the site; (c) it returns a fixed field list: employee id and name, seat, the
seat-tree manager's id and name, the record's manager id and name; (d) it is offered to the same
readers as SEC-2 (Q1 decides whether that grows to the owners). It is loaded **only when the reader
asks** (opening the chip's sheet), or once with `position_table` - never once per box.
**If the rewrite is not in the build, the chip is dropped from 064.** It is a "should" in the design,
and shipping it as it stands is a P1: one HR click costs the database about a thousand round trips,
and anyone with HR Manager can call it in a loop.
*Test:* (a) query count equal at 20 and 200 assignments, with the number recorded; (b) HR of company 1
gets no mismatch from company 2; (c) a store HR gets only their branch; (d) a non-HR caller is
refused; (e) a p95 under 500 ms on a copy of DTC (nfr-budget, "whitelisted API call").
*Observable only if* each company and each branch in the fixture holds at least one real mismatch.

**SEC-6 · A hire is placed only when every condition holds - otherwise nobody is placed.**
On Employee **`after_insert` only** (later edits never place anyone), the hook places the new
employee when **all** of these are true, read from the database:
1. The Employee is Active and has `job_applicant` and `date_of_joining`.
2. No other Employee carries the same `job_applicant`.
3. The applicant's `job_title` names a Job Opening with a seat link.
4. The seat is not Closed, and its company equals the Employee's and the opening's.
5. The Employee holds no current assignment.
6. The seat has room **on the joining date and today**. The doctype's own over-fill check
   (`on_update`) counts today's occupants only (`alvoraa_position.py:137-143`), so the hook checks
   the joining date itself; both must pass.

It writes: Permanent, 100%, `from_date` = joining date, `delegate_authority` 0, no `covering_for`.
When any condition fails, it writes nothing and the Employee save goes on, with the message the
brief gives ("…that seat is full until 30 Nov. Put him in from Positions when it frees up.").
*Test:* one passing case, then one case per condition that fails (seven), each asserting **zero**
assignment rows and a saved Employee; plus: a seat full today but free on a later joining date; a
seat free today but full on the joining date because of a future-dated assignment; a seat in
another company.
*Observable only if* the fixture runs the real chain: Job Opening with a seat link → Job Applicant →
Employee with `job_applicant`. **DTC has 0 such Employees**, so nothing on DTC shows this working.

**SEC-7 · The placement is one bounded bypass, keeps every rule, and leaves no half-record.**
The hook runs as the user who saved the Employee. At DTC that is an HR user with **no create on
Alvoraa Position Assignment** (DTC's Custom DocPerm gives it to System Manager and Org Structure
Editor only), so it needs exactly **one** `ignore_permissions`, on the insert. It must not also set
`ignore_validate`, `ignore_mandatory` or `ignore_links`: every assignment rule still runs. The
insert runs inside a **savepoint**; any refusal (including the over-fill throw in `on_update`)
rolls back to it, so no assignment is left half-written, and the hook never raises out to the
Employee save. On failure the Error Log names ids only.
**The counter:** `register.py` has 4 `ignore_permissions` today and **no ceiling** in the SEC-16 test
(`test_portal_security_010.py:731-808`). Add it - at 4, or 5 if the hook lives there. A new file
starts at its true count (1). `api.py` stays at 2. `alvoraa_position_assignment.py`,
`alvoraa_position.py`, `metrics.py` and `org_job_link.py` are added at 0. `employee_master.py` is
Frappe HR's and is not touched; the hook is registered from our own code.
*Test:* (a) SEC-16 with the new rows passes; (b) a seat that fails the over-fill check → Employee
saved, no assignment row, no orphan child row; (c) the passing case run **as an HR User with no
create on the Assignment**. Run as Administrator it passes and proves nothing.

**SEC-8 · Only someone who may place people in a seat may point an opening at it.**
Because the hook turns the seat link into a placement, the link carries the same authority as
`assign_person`. Whenever `alvoraa_position` **changes** on a Job Opening - desk, REST, import or
`post_job` - the server checks: `may_edit()`; the seat is inside the caller's `_scope()` (company and
branch); the seat's company equals the opening's. Otherwise it refuses through `refuse()`, so the
security log records it. A save that does not change the link (closing the opening, editing the
description) is not checked.
*Ladder:* rung 4, a `validate` on Job Opening. Rejected below it: `read_only` (not enforced by the
server - §0 point 3); `permlevel` 1 (enforced, but cannot express a branch scope, and a Custom
DocPerm row on Job Opening at DTC would replace all its shipped rows). This is a hook on a shared
doctype; it is justified because the link now writes an assignment without a person choosing it.
**This holds whether or not the field is made editable on the desk** - the API can set it today.
*Test:* (a) an HR User without Positions edit sets the link with `frappe.client.set_value` → refused,
logged; (b) an editor in scope → allowed; (c) a branch-tied editor, seat in another branch →
refused; (d) seat in another company → refused; (e) an HR User closes a linked opening → allowed;
(f) `post_job` by an editor in scope still works.
*Observable only if* the fixture has a user with Job Opening write and **no** Write on Alvoraa
Position. On `dev` that is any HR User; at DTC after 061, every HR user.

**SEC-9 · A placement changes no approver and no reporting line.**
The hook writes nothing on Employee: not `reports_to`, `leave_approver` or `expense_approver`.
Stated consequences, so nobody is surprised:
- From the joining date the hire is among `_people_under` the parent seat
  (`alvoraa_position_assignment.py:237-255`). A **later** cover of the parent seat with "also move
  approvals" moves theirs - intended. A cover **already running** does not, because it recorded its
  list when it started - the safe direction.
- A seat with seats under it gives its holder the manager's view of the Organisation chart while
  `alvoraa_org_managers_see_all` is on (`api.py:769-807`; DTC uses the default, on). That is the same
  as a manual placement today, and it is why SEC-8 exists.
*Test:* (a) after placement, the three Employee fields equal what HR saved; (b) placement under a
parent seat with a running delegating cover → the hire's approvers unchanged; (c) a hire placed in a
seat with nothing under it gets bounded reach, not full reach.

**SEC-10 · An opening closes only when it is really filled, and with no new bypass.**
After a placement attempt (placed or skipped), the opening is set to Closed when the number of
Employees created from its applicants reaches `vacancies`, and `vacancies` is at least 1. Blank or 0
never closes. The save runs as the user, with **no `ignore_permissions`**. If they lack write, the
opening stays open and the message says so. It never reopens anything. Closing also takes it off the
careers page, and Frappe HR then marks a linked Job Requisition "Filled" (`job_opening.py:126-134`)
- intended, and named here so nobody is surprised.
*Test:* (a) vacancies 2, first hire → still Open; second → Closed; (b) vacancies 0 → stays Open;
(c) a user without write → stays Open, message shown, Employee saved.

**SEC-11 · No new way in, and who opens Positions stays a setting.**
Every new or changed whitelisted function in 064 calls `may_view()` or `may_edit()` first. No
`allow_guest`. 064 changes **no** shipped or tenant permission: not on Alvoraa Position, the
Assignment, Job Opening or Employee, and not the full-reach roles. Who opens the page at DTC is
Surbhi's choice, made as configuration (Q1).
*Test:* (a) a user without Read on Alvoraa Position calling `position_table` is refused (existing
SEC-8 rule); (b) review check at `06`: no permission JSON or fixture change in the diff.

### Privacy

**PRIV-1 · Each person in the new lists carries a fixed set of fields.**
Allowed: employee id (the link key), name, job role, branch, joining date, and the matching seat
(id and title, worked out from seats already loaded). **Never:** `user_id`, email, phone, date of
birth, gender, image, `relieving_date`, status reason, salary or grade, `reports_to` names (the
mismatch chip in SEC-5 has its own list). Built by naming each field, never by sending a row whole.
*Test:* the keys of each row **equal** the allowed set exactly, so a field added later fails the
test rather than leaking.

**PRIV-2 · No copy of the lists or counts anywhere.**
Worked out on each load. No stored field, cache, `localStorage`, export, CSV, print format or log
line holding them. Find's typed text is not stored. "Print this view" is **later** (design Q8) and
is not built in 064.
*Test:* review check at `06`: no `frappe.cache()`, no new field, no `localStorage` key, no new report
or print format on this path.

**PRIV-3 · A placement can be explained a year later, from records, in ids.**
- The assignment's `owner` is the user who saved the Employee; its `reason` is a fixed sentence with
  **ids only**: "Placed on joining from Job Opening {opening} (applicant {applicant})". No name, no
  applicant field. The hook reads only the applicant's `job_title`.
- **Who pointed the opening at the seat** is recorded: turn on `track_changes` for Job Opening with
  a Property Setter, from the existing `org_job_link.after_migrate` (rung 2, configuration). Today a
  change to the link leaves no trace. *Rejected:* a Comment (can be deleted, not queryable); a new
  log doctype (more surface for one field).
*Test:* (a) placed assignment → owner = saver, reason holds both ids and no name from the fixture;
(b) changing the link → a Version row naming the user, old and new seat.

**PRIV-4 · Retention: no new rule, no deletion, no "keep for ever" setting.**
Assignments are kept as today (ended, not deleted, once used). The lists are not stored. 064 adds no
purge and no retention setting. The 18 Sep counsel rules do not cover seat history; do not apply them
by analogy. Seat history becomes more sensitive in 065 (a planning note on the assignment), which is
065's question.
*Test:* review check at `06`: no delete, purge or retention code in the diff.

---

## 8 · What 064 must not get in the way of

**Print, later (design Q8).** Nothing to build now. 064 must keep it possible to print only what is
on screen: no data in the page that the reader may not see (SEC-1, SEC-2), and anything private
marked so a print stylesheet can drop it.

**Slice 065, Plan a replacement.** 064 must not:
1. Widen who can read Alvoraa Position Assignment, Job Opening or Job Requisition. 065's note sits on
   the assignment, and its "unpublished opening" is readable by every Job Opening reader.
2. Send assignment rows whole anywhere. `position_table` and the Organisation page keep naming each
   field, so a later HR-only field can be added behind its own gate.
3. Add any export, report or print of per-person seat data.
4. Leave HR without Positions at DTC by accident. 065's "HR Manager only" assumes HR Manager can open
   the page; after 061 at DTC it cannot (§0 point 1, Q1).
5. Add more change history to the assignment than exists. It already keeps Versions; 065 must work
   out how a cleared note is purged from them, and 064 should not make that harder.

---

## 9 · Questions

### Must know (blocks the release, not the spec)

**Q1 · At DTC, who should see the people lists and the mismatch chip?**
*My reading:* HR, as the design says ("HR and CXO"), within their scope. *Unclear:* at DTC the "CXO"
are the 2 Org Structure Editors, who hold no HR role and are tied to one branch; and once 061 reaches
`main`, the 6 HR Managers cannot open Positions at all. *Why it changes the control:* SEC-2 and SEC-5
give the lists to HR only. After 061, at DTC that is one System Manager account and nobody else.
*The question:* "Should DTC's HR Managers keep Positions after 061 (one Custom DocPerm row: Read on
Alvoraa Position, and Write if they should change seats), and should the two owners see company-wide
people lists?" **My recommendation:** give HR Manager Read on Alvoraa Position at DTC; leave the
owners on seats only, unless you want them to see named lists - then they need an HR role or a
company-wide scope, which is a wider change than this page. **Fail-closed default meanwhile:** lists
for HR only, within scope.

**Q2 · Release order.** 064 is built on `dev`'s permission model (061). It must not reach `main`
before 061 does, or the page will run against the settings model it was not tested on.

### Should know

- **Designer Q1 and Q2** (people-based "No reporting manager"; "In no seat" in 064) are assumed
  accepted. SEC-2 and PRIV-1 hold either way.
- **Item 6 at DTC.** 0 employees came through Frappe hiring; 1 applicant, 0 offers. The PM's kill
  criterion is "no Job Openings and no plan to use them". DTC has 2 openings, so it does not fire,
  but the hook will do nothing there until DTC hires through Frappe. Worth asking if they plan to.
- **Joining date moved after placement.** The "not before joining" rule runs only on insert, so a
  joining date pushed out after placement leaves the person in the seat before they start. Small,
  not a leak; the analyst can decide whether the hook follows a changed date.

### For counsel

None for 064. 065's questions (purging a cleared note from history; whether an access request must
include it) stay with 065.

---

## 10 · Findings against existing code (not SEC items here, because they predate this slice)

| # | Finding: who, in what state, by what path, sees what | Where | Live at DTC? | Level |
|---|---|---|---|---|
| F1 | An HR Manager of company A calls `reporting_mismatches` and gets the names and managers of company B's people, and a store's HR gets every store's | `api.py:405-439` | No: 1 company, 0 HR with a Branch permission | P2 - **closed by SEC-5 if the chip is built**; otherwise still open |
| F2 | Any Positions reader calls `what_they_hold(employee)` for any employee in any company or branch, and learns which seats they hold | `register.py:552-589` (only `may_view()`) | No: 1 company | P3, owner `hrms-fullstack-engineer` |
| F3 | Any HR User sets `Job Opening.alvoraa_position` through the API, though the desk shows it read-only | `org_job_link.py:39-41` | Yes, but today it only changes what the chart says | P2 - **closed by SEC-8** |
| F4 | `register.py` has 4 `ignore_permissions` and no ceiling, so a fifth would pass CI | `test_portal_security_010.py:731-808` | n/a | P3 - **closed by SEC-7** |
| F5 | An HR user with a Company User Permission keeps HR scope after they leave, if their login stays enabled: `permitted_companies` checks the Active record only when no Company permission exists (lesson 3) | `access.py:211-215` | No: 0 enabled logins tied to a non-Active Employee today | P3; the fix touches every HR reader, so it is a separate decision |

Lesson 2 check: `metrics._positions` and `position_table` are scoped; `reporting_mismatches`,
`what_they_hold` and `_descendant_count` are the unscoped siblings. 064 must not read through any of
those three without the scope (SEC-1, SEC-5).

---

## 11 · Worries (not findings - I cannot yet write "this actor, this path, sees this")

- **Two branch records for one store at DTC** ("DTC Pitampura" for people, "DTC - PITAMPURA" for
  seats). A store HR person tied to one of them would see the people or the seats, not both. Not a
  leak, but it would make the store's "in no seat" list look worse than it is. Data work (design Q11).
- **`position_table` returns everyone in a seat the reader may see, whatever that person's own
  branch.** A Delhi seat holding a Noida person shows the Noida person to Delhi's HR. Existing, and
  probably right, but nobody has said so.
- **An unpublished Job Opening is readable by every Job Opening reader.** Not 064's problem; it is
  065's first question.

---

## 12 · What I could not verify, and what I would need

- **That production's Frappe also ignores a field's `read_only` on the server.** I read the local
  bench's Frappe. Needs one look at the production version's `document.py`, or one test on a copy.
- **That a savepoint inside an Employee `after_insert` rolls back only the assignment.** Inference
  from Frappe's transaction handling. Needs one bench run.
- **That the public job page never shows the seat link.** The template renders named fields and I
  saw no loop over all fields (`job_opening.html`). Inference.
- **No timing.** "1,100-1,800 queries" for `reporting_mismatches` is counted from the code against
  DTC's 364 assignments, not measured.
- **Whether DTC means to hire through Frappe.** Needs Surbhi or DTC.

---

## 13 · Subtract pass

Removed on the final read:

- A test that the public careers page never renders the seat link: the template names its fields,
  and nothing in 064 changes it.
- A new "placed automatically" field on the assignment: the reason sentence plus `owner` answer the
  same question.
- A separate privacy requirement for Job Applicant data: folded into PRIV-3 (the hook reads
  `job_title` only).
- A requirement that the placement follows a changed joining date: moved to "should know".
- Using the full-reach roles setting as the gate for the lists: replaced by
  `permitted_employee_filters()`, the one existing fail-closed rule, so there are not two rules for
  "may see people as HR".
- A rate limit on `position_table`: it is behind login and its query count is flat (SEC-2).
- A requirement for the "Joined 14 Oct, hired for this seat" chip: it shows nothing new beyond the
  seat's own data, and it shows nothing at DTC.

Kept, and why: SEC-8 (without it the hook trusts a field the API can already set); the Job Opening
history in PRIV-3 (without it nobody can say who pointed an opening at a seat); SEC-5's "drop the
chip if not rewritten" (otherwise one click is a thousand queries).

---

## Residual risk

| Risk | Kind | Level | Who accepts | Date |
|---|---|---|---|---|
| After 061, at DTC only one System Manager account sees the people lists (Q1) | Intentional trade-off (fail closed) until Q1 is answered | P2 | **Surbhi - to decide** | open |
| A hire placed under a seat whose cover is already running keeps their own approver (SEC-9) | Acceptable simplification (safe direction) | P4 | **Surbhi - to confirm** | open |
| `what_they_hold` is unscoped by company (F2) | Temporary debt; not live at DTC | P3 | `hrms-fullstack-engineer` to propose | open |
| HR scope survives a leaver with a Company permission and an enabled login (F5) | Temporary debt; not live at DTC | P3 | **Unowned - Surbhi to name an owner** | open |
| The hook, the branch scope and the leaving suppression cannot be seen working on DTC's own data (§0 point 5) | Acceptable simplification; tests carry the proof | P3 | `hrms-test-automation-engineer` | open |
| CERT-In log residency (baseline §3a) | Existing gap, unchanged | - | Founder (baseline) | open |

Nothing here is **dangerous debt** as long as SEC-5 (or dropping the chip) and SEC-8 hold.

---

## Handoff note

To the business analyst: trace every SEC and PRIV item to an acceptance criterion. The five that
matter most are **SEC-2** (the people lists, scoped and HR-only), **SEC-8** (the seat link needs the
right to place), **SEC-7** (one bounded bypass, a savepoint, the counter), **SEC-5** (rewrite the
mismatch report or drop the chip) and **SEC-1** (every count over the rows already scoped). Write
Q1's fail-closed default into the spec until Surbhi answers.

To the engineer: put the people lists inside `position_table`, not in a new endpoint. Do not reuse
`_descendant_count`, `reporting_mismatches` as it stands, or `search_people`. Ship SEC-8 in the same
change as the hook. The hook must never block an Employee save, and must never leave a half-written
assignment.

To the test engineer: every test above that says "observable only if" passes silently on the wrong
fixture. Build two companies and two branches; run the hook as an HR User with no create on the
Assignment; give someone a future relieving date.
