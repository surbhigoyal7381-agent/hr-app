---
slice: 034-redesign-wave1
artifact: 00g-decision-register
author: hrms-fullstack-engineer (recording the user's decisions)
date: 2026-09-23
status: decided
closes: security re-review N4 (06b-security-rereview.md §3)
inputs: [06-security-review-of-requirements.md, 02b-ba-review.md, 02c-ba-rereview.md, 06b-security-rereview.md, 01c-security-privacy-requirements.md, 02-functional-spec.md, ../009-ess-portal-redesign/00f-decisions-2026-09-22.md]
---

# Wave 1 decision register

**Why this file exists.** `01c` and `02` closed several security and analyst findings by
citing "decision 4", "decision 5", "decision 7" and so on. Those bare numbers pointed at
nothing. The one decisions file in the tree,
`../009-ess-portal-redesign/00f-decisions-2026-09-22.md`, holds **two different**
numbered sets of its own, and its decision 3 and decision 4 mean something else entirely.
Three sets of numbers, all called "decision n", in the same sentence in places. The
security re-review called this N4 and asked for it to be written down and cited by name.

**The reference to use from now on is `W1D-nn`.** One series, one file, no clashes. Every
citation in `01c` and `02` now uses it. The two sets in `00f` keep their own names and
are cited as **"009 design decision n"** and **"009 strategy decision n"** — never as a
bare number.

## How to read this file

| Prefix | Means | Lives in |
|---|---|---|
| `W1D-01` … `W1D-12` | The review decisions of **22 September 2026** — the ones taken on the analyst, security and DevOps reviews of revision 1 | this file |
| `W1D-13` … `W1D-18` | Surbhi's decisions of **23 September 2026** — taken on the analyst and security **re-**reviews of revision 2 | this file |
| `W1D-19` … `W1D-21` | Surbhi's three further decisions of **23 September 2026**, later the same day — the desk link, the Team screen's scope, and the staff-list switch | this file |
| `W1D-22` … `W1D-23` | Surbhi's decisions of **24 September 2026**, taken on the senior architect review — the tenant System Manager's Team screen, and the query budget | this file |
| 009 design decision 1–7 | The design run's seven decisions, 22 Sep | `00f-decisions-2026-09-22.md`, first table |
| 009 strategy decision 1–14 | The Wave 1 strategy's fourteen, 22 Sep | `00f-decisions-2026-09-22.md`, second table |

## Provenance — read this before relying on W1D-01 to W1D-12

`[ASSUMPTION]` **The twelve decisions of 22 September are reconstructed, not transcribed.**
No contemporaneous record of them was written on the day — that is the defect the security
review found. The text below is rebuilt from the places `01c` revision 2 and `02` revision
2 acted on them: the requirement or acceptance check each one produced, plus the
traceability row in `02` §17 that mapped decision 1 to 12 onto those checks. Every entry
names the artifact it was rebuilt from, so anyone can check the rebuild against the code
and the documents.

Where a rebuilt decision differs from what Surbhi remembers, **her memory wins and this
file is corrected.** W1D-13 to W1D-21 need no such warning: they were recorded on the day
they were taken.

---

## The decisions of 22 September 2026 (reconstructed)

| # | Decision | Rebuilt from |
|---|---|---|
| **W1D-01** | **Pay stays without payroll.** Without `plan_payroll`, hide the salary parts only — the My pay entry, the salary tab and payslip search results. Expenses stays (it is a required feature on every plan), and Leave encashment and Request advance stay on the flags they already have | `02` §1 Pay row, AC-1, AC-44; `02c` B1 |
| **W1D-02** | **The bottom bar is decided by two flags, `is_hr` and `has_reports`.** Today's stand-in rule — which makes `is_manager` true for any HR user whenever somebody in the tenant has no manager — is not used to give anyone a Team panel. An HR user with no direct reports loses the Team panel they see today; that is intended | `02` §2, AC-10, AC-47 |
| **W1D-03** | **Org settings is read only for store HR and for an HR User.** The Save controls are not rendered for them; company-wide HR keeps them | `02` AC-67, US-13. **Not** the preview-page decision — that is 009 strategy decision 3 |
| **W1D-04** | **`set_my_language` is not built in Wave 1.** No frame code writes a `User` record. The language row is hidden until a translation ships | `01c` SEC-9; `02` AC-18, AC-49 |
| **W1D-05** | **The corrections queue is scoped the same way its count is.** `attendance_correction.to_review` gains the same filter as the Inbox count, so a store's HR person never sees a head-office correction | `01c` SEC-5 attendance row; `02` AC-52. **Narrowed by W1D-14 below** |
| **W1D-06** | **The leaver fix goes inside the two helpers this slice already touches** — `_search_scope` and `_pending_approvals_scope` find the caller's Employee with status Active only. `_me()` is not changed globally. The wider fix across `goals_api` is `ALV-87` | `01c` SEC-14, A9; `02` AC-68 |
| **W1D-07** | **Store HR's people search is their store plus their own reporting line.** An employee with no branch is outside every store (slice 030, DEF-6). System Manager is not narrowed | `01c` SEC-3, SEC-4; `02` AC-26, AC-50 |
| **W1D-08** | **The org chart showing every company and store is not accepted.** It is `ALV-86`, Critical, before DTC's go-live. Wave 1 does not wait for it and does not work around it; its state is recorded on the day of the swap | `01c` "Dependency, not designed around" and R1; `02` release gate 5 |
| **W1D-09** | **Speed is measured on "Slow 4G" with a 4× CPU slow-down**, cache off — not on an undefined "3G" | `02` §13, OPS-17 |
| **W1D-10** | **Rollback is a redeploy of the previous production image tag**, and that tag is written down before the swap. About ten minutes | `02` release gate 4, OPS-14 |
| **W1D-11** | **The swap ships in a release of its own**, and reaches production only when all five conditions hold: at least 10 working days after DTC goes live, no client-blocking issue for 5 days, outside payroll close, compression live, and the frame on dev for 5 days | `02` release gates 2 and 3, OPS-4, OPS-16 |
| **W1D-12** | **Hindi is measured in test fixtures only.** No Hindi is shipped to users in Wave 1 | `02` AC-48 |

---

## Surbhi's decisions of 23 September 2026

Taken on the analyst re-review (`02c-ba-rereview.md`) and the security re-review
(`06b-security-rereview.md`), both of revision 2. Recorded the day they were given.

| # | Decision | Answers |
|---|---|---|
| **W1D-13** | **Narrow the orphan query in Wave 1.** The Team panel's "employees with no manager" list must respect the caller's company and store, so a store's HR person no longer sees head office. `get_manager_dashboard` (`alvoraa_portal/alvoraa_portal/hr_api.py:291-307`) is added to this slice's files, with an acceptance check. Surbhi was told this is about half a day | `02c` verdict point 2 and open question 1 |
| **W1D-14** | **The corrections-queue filter applies only when the caller is HR.** A non-HR reviewer who holds submit permission on Attendance Request — for example a Shift Supervisor — keeps the queue they have today, scoped by Frappe's own permissions. AC-52 gains that case. This is the security review's option (a), and it narrows W1D-05 | `06b` N2 |
| **W1D-15** | **The preview page never exists on production.** It renders only when `frappe.conf` carries `portal_preview: 1`, which is set on the local bench and the dev stack and never on production. The System Manager role check stays as a second lock. A "flag off → 404" check is added. This replaces the earlier position that a tenant System Manager may see it (009 strategy decision 3) | `06b` R5, option 1 |
| **W1D-16** | **R6's live-tenant check happens before DTC go-live — by 2026-09-30, owned by Surbhi with the tenant admin.** The code fix stays in `ALV-86`, by 2026-11-15 | `06b` §5, R6 |
| **W1D-17** | **R3 and R4 dates accepted as recommended.** R3: a cheap logging first step by 2026-10-15, the full detection slice by 2026-11-30, owned by the security engineer with DevOps. R4: baseline script by 2026-10-31, the blocking gate on the next commit after that, before Wave 2 adds endpoints, owned by the security engineer | `06b` §5, R3 and R4 |
| **W1D-18** | **Alvoraa staff do not hold System Manager on client tenants.** Our access is the shared `Administrator` account. The client's own System Manager has full access to their own data, which is correct. Two follow-ups — named logins instead of the shared `Administrator`, and turning on the access log on the two client tenants — are **`ALV-93`**, out of Wave 1's scope | `06b` R5 point 1, §6 |

### What W1D-18 does and does not settle

It settles the question the security review could not answer from the code: our support
people are not tenant System Managers, so "System Manager only" never meant "our staff on
a customer's live data".

It does not make the shared `Administrator` account safe. One shared login across client
tenants means a read of a customer's data cannot be traced to a person. That is what
`ALV-93` is for, and until it ships the gap is real. W1D-15 removes the preview page from
production entirely, so this slice no longer depends on the answer either way.

---

## Surbhi's further decisions of 23 September 2026

Taken later the same day, after W1D-13 to W1D-18. **Recorded on the day they were given.**
They close the two open questions revision 3 left, and one of them replaces W1D-13.

| # | Decision | Answers |
|---|---|---|
| **W1D-19** | **The desk link is for HR and System Manager only.** A plain manager — someone with direct reports who holds neither an HR role nor System Manager — **does not get the link at all**. The labels stay exactly as the server already produces them: **"Switch to HR Core"** for HR (`/app/hr`) and **"Switch to Admin"** for a System Manager (`/app`). **The prototype was wrong, not the code** — see the note below. No code change: `module_access.get_switch_target` (`alvoraa_portal/alvoraa_portal/module_access.py:1099-1115`) already behaves this way. What is added is a test | `02` open question 1; `02` §11 difference (a); `01c` SEC-7 |
| **W1D-20** | **For an HR user the Team screen follows HR scope, not direct reports.** It is built from `access.permitted_employees()` (`hrms/hrms/alvoraa_hr_core/access.py:237-267`), which already encodes the rule: System Manager and Administrator see everyone; HR with no Branch permission sees everyone in their companies; HR carrying a Branch permission sees that branch only; anyone else nobody. **A manager who is not HR is unchanged** — still their own direct reports. An HR user who also has direct reports sees their HR scope, which contains those reports. **This REPLACES W1D-13**: the "employees with no manager" list is not narrowed, it is removed, because the screen is no longer built that way | `02c` verdict point 2; `02` open question 5; replaces W1D-13 |
| **W1D-21** | **The staff list gets its own feature switch, separate from the org chart.** Today one flag, `plan_org_structure`, gates both (`alvoraa_portal/alvoraa_portal/www/hrms-employee.html:7813`). Split them: **the org chart stays behind `plan_org_structure`** as a paid feature, and **a plain searchable staff list for HR gets its own key in the same registry** (`alvoraa_portal/alvoraa_portal/subscription.py` `FEATURES`, surfaced by `hr_api.get_available_features` as `plan_<key>`), **switched on for both current client tenants**. The commercial question — free or paid, and on which plans — is **deliberately left open**; the switch exists so it can be settled by configuration later instead of by another code change | `02` open question 5; `02` §3 and §11 difference (e) |

### W1D-19 — why the code is right and the prototype is wrong

**Write this down so nobody "fixes" the code back towards the prototype later.**

The prototype shows "Switch to the full desk" for every manager, with one generic label.
The server does something different and better: `get_switch_target` returns `None` for
anyone who is neither HR nor a System Manager, so the portal hides the control rather than
offering a door that leads nowhere. A plain manager who followed that link would land in a
desk where almost every list refuses them.

The labels are also the server's, not the prototype's, and they say where the person is
actually going: **"Switch to HR Core"** opens Frappe HR's own workspace, **"Switch to
Admin"** opens the whole desk. "The full desk" would be a lie for the HR case.

A person who is **both** HR and a System Manager gets **"Switch to Admin"**, because
`ADMIN_ROLES` is tested first (`module_access.py:1108-1114`). That is intended and stays.

**The prototype is not changed to match** — it is a review artifact, already approved, and
Wave 1 does not re-open it. This entry is the record of the difference.

### W1D-20 — what happens to the orphan list, checked in the source

Today `get_manager_dashboard` (`alvoraa_portal/alvoraa_portal/hr_api.py:291-307`) builds
the Team panel as direct reports, and then, **only when the caller holds `HR Manager` or
`HR User`**, adds every Active employee in the tenant whose `reports_to` is empty — with
`ignore_permissions=True` and no company or branch filter.

I read that block again before writing this, because it decides whether anything leaks
after the change:

- **For an HR caller** the orphan block is gone. The HR branch of the function is rebuilt
  from `permitted_employees()`, so "people with no manager" still appear — they are inside
  the HR person's scope — but so does everyone else in that scope, and nobody outside it.
- **For a manager who is not HR the orphan block never ran.** The `if` at line 296 tests
  `{"HR Manager", "HR User"} & set(frappe.get_roles())`. A plain manager fails it, so their
  Team panel is, and always was, their own direct reports plus the L2 rows read from them.
  **No leak remains on that path.** Not "probably gone" — it was never reachable for them.
- **The block is deleted, not left behind a condition.** Dead code that once handed out the
  whole tenant is how the leak comes back the next time somebody debugs an empty screen.

Two things the rebuild must keep, or it widens instead of narrowing:

1. **`status = "Active"` stays on the Team query.** `permitted_employees()` returns *every*
   status on purpose (its docstring says so — a leaver's records still belong to the store).
   Without the Active filter the Team screen would start listing leavers, which is wider
   than today.
2. **The list is capped.** Company-wide HR on a 1,000-person tenant would otherwise get a
   thousand cards, and the attendance query behind them would carry a thousand ids. The
   cap and its "showing the first 50 of 412" line are part of this decision's cost.

### W1D-20 — the one consequence nobody asked for, said plainly

`is_hr` includes **System Manager**, and `permitted_employees()` gives a System Manager
**everyone**. So a tenant System Manager who has an Employee record gets a Team screen
listing the whole tenant, where today they get their own direct reports only (they hold no
HR role, so the orphan block never ran for them either).

No new data: a System Manager can already list every Employee in the desk. But it is a
**wider screen** than today, and this slice's rule is that nothing gets wider as a side
effect. It is recorded in `01c` PRIV-7 as the one wider row, and as **open question 6** —
one line of code either way:

- as decided (`is_hr`): the tenant owner opens Team and sees their company. Simple, and it
  matches the helper.
- the alternative: HR scope on the Team screen means `HR Manager` / `HR User` only, and a
  System Manager with no HR role keeps their direct reports.

**Recommendation: leave it as decided.** The owner-CXO seeing their own company on their
own Team screen is what Kamal asks for, and the helper is the single rule we do not want
two versions of. Flagged rather than assumed.

## Surbhi's decision of 24 September 2026

Taken on the senior architect review (`05-review.md`, finding F3). **Recorded on the day
it was given.**

| # | Decision | Closes |
|---|---|---|
| **W1D-23** | **The query budget moves; `goals_api` is not edited now.** AC-24 becomes **20 queries for an HR caller and 15 for everyone else**, and the `goals_api` tidy-up is raised as **ALV-113** for after go-live. The reason is the property the budget existed to protect, which is true and proven: `get_nav_counts` is **flat in headcount** — every part is an aggregate, none walks a list of people, and store HR (20 queries) and company-wide HR (19) differ by one on the same site. 35–41 ms against a 500 ms p95 on the same line of the budget is not a performance problem. Editing a module this slice does not otherwise touch, in the week before go-live, to save four queries worth about 6 ms is the worse trade. **Memoising `permitted_companies` is explicitly NOT the answer** — a memo that outlives a request hands a background job a stale scope | `05-review.md` F2; `02` AC-24 and §13; `03-implementation-notes.md` §6; ALV-113 |
| **W1D-22** | **Yes — leave it as decided. A tenant System Manager who has an Employee record sees the whole tenant on the Team screen.** `is_hr` keeps System Manager in it, and `access.permitted_employee_filters()` keeps returning `ALL_EMPLOYEES` for them. No second version of `permitted_employees()` is written. It is what Kamal the owner wants from his own Team screen, and no data crosses a tenant boundary — that person's desk already lists every employee in the tenant. **It stays recorded as a widening, not quietly accepted**: `01c` PRIV-7 keeps its row naming this as the one screen that gets wider on release, so nobody has to rediscover it in six months | `02` **open question 6**; `05-review.md` F3; ALV-102 |

### W1D-22 — what was decided, and what was deliberately not

**Decided.** The screen gets wider for exactly one kind of person: a tenant System
Manager who also has an Employee record. Today they see their own direct reports. On
release they see their whole tenant, capped at 50 with the true total beside it.

**Not decided, and not changed.** Nothing about who may *read* an employee record. The
Team screen shows what `permitted_employee_filters()` already allows, which for a System
Manager is everyone in their own tenant and nobody outside it. A support engineer is not
a System Manager on a client tenant (W1D-18), so this does not touch Alvoraa staff.

**Why it is worth a line rather than a shrug.** The alternative — HR scope on the Team
screen meaning `HR Manager` / `HR User` only — would have meant two rules for "who may
this person see", and the three readers in slice 030 drifted apart for exactly that
reason. One rule, one helper, and the one screen that widens is written down.

### W1D-21 — how the switch is built, and what it costs

**Reuse, not a parallel mechanism.** One new key in `subscription.FEATURES`, shaped like
`org_structure` next to it:

- `opt_in: True` — so it is **off** for every tenant until somebody ticks it. This is what
  makes the commercial question deferrable: `plan_features()` strips opt-in keys from every
  plan bundle (`subscription.py:503-505`), and `enabled_features()`'s fallback excludes
  them too, so shipping the key hands it to nobody by accident.
- `requires: ["portal"]` — it is a portal screen and needs nothing else.
- **No `workspaces`, no `roles`, no `app`** — there is no desk workspace behind it, which
  the registry already allows (`spec.get("workspaces") or []`).
- It reaches the page the way every other plan flag does: `get_available_features` loops
  `FEATURES` and returns `plan_<key>` (`hr_api.py:1289-1295`). **No new call, no new
  pattern.**

**Which plans it belongs to: none yet, and that is the point.** It is switched on per
tenant by the one tick in the admin console, which writes the key into that tenant's own
`features` list — explicit always wins over the default. **Both current client tenants get
the tick** (`dtc` and `aahr`; the local PP Jewellers copy too, so the screen is testable).
When the commercial answer comes, it is either added to the plan bundles and loses
`opt_in`, or it stays an add-on. Either is a config or registry change, not a redesign.

**The org chart is untouched.** It stays on `plan_org_structure`, which is the paid
`org_structure` feature — positions, vacancies and seats. The staff list is a list of
people, which is a different thing to sell.

**What an HR user on a tenant with the switch off sees.** Not a blank screen and not a dead
menu entry:

- no staff-list entry in the Company group at all, exactly as an unsold feature behaves
  today;
- they still have the **Team screen**, which after W1D-20 is their whole HR scope — so an
  HR person is never left with no way to see their people, whatever the two flags say;
- and if they reach the address anyway (an old bookmark, a typed route), they get the
  frame's plain no-permission line — what the page is and who to ask — never an empty list
  and never an error.

### W1D-20 and W1D-21 — the size, said honestly

Surbhi was told W1D-20 **replaces** the half-day of W1D-13 and costs **about a quarter of
a day more than it, not on top of it**. The replacement part is right. **The quarter-day
is too low — I would say half a day more, so about 1 to 1¼ days in place of the 0.5.**

| Part | Was it inside W1D-13's half day | Cost |
|---|---|---|
| The query change itself | yes | about the same — one filter swapped for another |
| Two-store fixture and the scope tests | yes | same |
| The cap, the total, and the "showing the first 50 of 412" line | **no** | the real addition — a company-wide HR user now gets a list that can be a thousand long |
| Keeping `status = Active` and proving it (leavers must not appear) | **no** | one more fixture and one more test |
| The bottom bar and rail change — HR with no reports now has a Team button, so §2's rules, AC-10, AC-11 and AC-47 and their fixtures all move | **no** | small each, but it is four checks and five named bars |

W1D-21 is new work, not a replacement: **1½ to 2 days** — the registry key and the split
gate are about half a day, the plain searchable list screen about a day, and its tests
(flag on, flag off, store HR's list is their store) the rest.

---

## Superseded and corrected

| What | Now |
|---|---|
| 009 strategy decision 3 — "the preview page is open to System Manager only" | **Superseded by W1D-15.** The role check survives as the second of two locks; the site flag is the first |
| W1D-05 — the corrections queue is scoped like its count | **Narrowed by W1D-14.** The filter applies to HR callers only |
| **W1D-13 — narrow the Team panel's "employees with no manager" list** | **Replaced by W1D-20.** Not kept alongside it: the list is not narrowed, it is gone, because for an HR caller the screen is built from `permitted_employees()` instead. SEC-13 and AC-72 are rewritten to the new approach and keep both must-not-break tests — a store HR person's screen must not come back **empty**, and a store HR person must not see head office |
| W1D-02 — an HR user with no direct reports loses the Team panel | **Reversed by W1D-20.** They keep a Team screen; what changed is what it is built from. The rest of W1D-02 stands: the bars are still decided by `is_hr` and `has_reports`, and today's stand-in `is_manager` rule is still not used |
| `02` §11 row d cited "decision 5" for the empty-search wording | Corrected to **W1D-07** — it is the search-scope decision, not the queue one |
| `01c` A10 — "a tenant System Manager **or a support engineer**" | Corrected by **W1D-18**: support engineers are not System Managers on client tenants; the shared `Administrator` is a separate concern, `ALV-93` |
| `02` §17 — "22 Sep review decisions 1–12" | Replaced by a row citing this file by name |
