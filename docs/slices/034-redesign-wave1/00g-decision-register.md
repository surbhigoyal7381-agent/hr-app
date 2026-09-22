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
file is corrected.** W1D-13 to W1D-18 need no such warning: they were recorded on the day
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

## Superseded and corrected

| What | Now |
|---|---|
| 009 strategy decision 3 — "the preview page is open to System Manager only" | **Superseded by W1D-15.** The role check survives as the second of two locks; the site flag is the first |
| W1D-05 — the corrections queue is scoped like its count | **Narrowed by W1D-14.** The filter applies to HR callers only |
| `02` §11 row d cited "decision 5" for the empty-search wording | Corrected to **W1D-07** — it is the search-scope decision, not the queue one |
| `01c` A10 — "a tenant System Manager **or a support engineer**" | Corrected by **W1D-18**: support engineers are not System Managers on client tenants; the shared `Administrator` is a separate concern, `ALV-93` |
| `02` §17 — "22 Sep review decisions 1–12" | Replaced by a row citing this file by name |
