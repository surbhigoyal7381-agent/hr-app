---
title: Report access by persona - employee and manager
date: 2026-09-14
author: hrms-product-manager (agent)
status: recommendation - Surbhi decides
tenant measured: PP Jewellers, local copy (ppj.localhost), 403 active employees, 6 branches
---

# Report access by persona: is it right?

## The answer first

**The employee's access is right. The manager's is too wide, and in two places it breaks our own product rules.**

- **Employee (Nandini, Cashier): right as it is.** Every report she can open shows only her own record. The portal already shows her the same things more clearly. Nothing to take away urgently.
- **Manager (Balwinder, Floor Manager - Gold): too much.** He has 18 people in his team. The desk shows him 72 people (his whole branch) in three reports. It shows him **all 403 people's attendance, including leave type**, in the Attendance list. On the code's evidence it also shows him **every salary advance and every unpaid expense claim in the company**.
- **The portal already covers what he actually needs for his 18**, scoped by who reports to him. Taking the desk access away loses him nothing he uses for his job.
- **The root cause is not a single wrong setting.** Alvoraa has no defined access model for a manager. PPJ's model came from the demo setup script (`demo/pp_jewellers/seed_employees.py`, lines 136-163). It gave store managers a Branch permission "so they can see their team". Branch was the nearest thing Frappe offered, not the right boundary.
- **The owner seeing everything is not a permission bug. It is a missing product: we have no leadership view.** So he borrows HR's key.

I am not a lawyer. Where I mention DPDP below, it is a product reading, not legal advice.

---

## 1 · Verdict per report

"Colleague" below means someone the manager does not manage. The one-way rule is in `product-context.md` §2: *a slice that improves the manager's convenience by degrading the employee's experience has failed.*

| Report | Employee | Manager | Why |
|---|---|---|---|
| Employee Leave Balance Summary | **Right** (own only) | **Too much** (72, needs 18) | He approves leave for his 18. He sees their balances in the portal team view (`get_employee_detail_for_manager`). The other 54 people's leave use is none of his business. For those 54 he is a colleague, not their manager. |
| Employee Analytics | **Right** (own only; no job need, harmless) | **Too much** (72) | The report lists **date of birth and gender** for everyone in his branch (`employee_analytics.py`, columns). A Floor Manager - Gold does not need the age or gender of 72 people to run a counter. Year of birth reveals age, which lets someone make age-based judgements. |
| Employee Birthday | **Right** (own only; pointless) | **Too much** (72, full date of birth including year, plus gender) | The team-culture need is real, and Frappe HR already meets it without this report. See §4. |
| Employee Leave Balance | **Right** (refused) | **Right** (refused) | The portal covers self and team. |
| Employee Advance Summary | **Right** (own only) | **Too much, serious** (whole company - inferred) | A salary advance often signals money trouble. That is a sensitive thing to infer about a person. A floor manager has no job need for anyone's advance, not even his own team's. It is paid and recovered by accounts. See §5. |
| Unpaid Expense Claim | **Right** (refused) | **Too much** (whole company - inferred) | This report helps accounts chase unpaid claims. It is not a manager's job. The manager approves a claim. He does not track its payment. |
| *Attendance list (not a report)* | **Right** (own only) | **Too much, most serious measured finding** (all 403, with leave type) | This breaks the rule that **presence can be shown but the reason for absence is never shown to colleagues**. A floor manager in South Extension can see that a cashier in another branch took Sick Leave or Leave Without Pay. Leave type can point to illness, pregnancy or money trouble. |
| HR-only reports (payroll, tax, PF/ESI, exits, recruitment, attendance sheets) | **Right** (refused) | **Right** (refused) | Keep "option B" (it removed report and export rights on Attendance). Without it, both could run Shift Attendance and export Attendance. |

**Nothing is "too little".** I looked for a manager job the desk refuses and the portal does not cover. The one possible gap is **approving expense claims**. The portal has no expense-approval screen (no `expense_approver` anywhere in `alvoraa_portal`). If Balwinder approves claims, he does it in the desk form, not through a report. See the open questions.

**A note on the rule itself.** "Presence can be shown; the reason for absence is never shown to colleagues" is **not written in `product-context.md` §6** today. It lives in a code comment on `get_week_presence` (`hr_api.py`, line 2701) and follows from our refusal to let a manager watch or rank individuals. I recommend adding it to §6 so it binds every slice.

---

## 2 · Is branch the right boundary for a manager?

**No, not for records. Reporting line is the boundary for anything with a reason, a number about money, or personal details. Branch is fine for presence only (in or away), and only where people share a floor.**

| Role | Their job | Right boundary | Does branch fit? |
|---|---|---|---|
| **Floor Manager - Gold** (18 reports, 72 in branch) | Approve leave, keep counters staffed, deal with late arrivals on his floor | **His direct reports** for leave, balances, lateness and notes. Possibly **branch presence (in/away only)** to borrow cover from Diamond on a busy Saturday | **No.** Branch shows him 4 times the people, with reasons. |
| **Store In-charge** (everyone in the branch reports up to them) | Answerable for the whole store | **Everyone below them in the reporting line** | Nearly. Here branch and reporting line are almost the same set. Reporting line is still correct when someone on the floor reports to a head-office function, such as security or a visiting auditor. |
| **Department head** (e.g. Head - Sales across 6 branches) | Answerable for a function across sites | **Everyone below them in the reporting line** | **No.** One branch is far too narrow. The whole company is far too wide. |

**Retail vs office.** Retail differs in one real way. People share a physical floor, and cover is a branch question: "who is on the floor today?" A typical office tenant has teams spread over cities. There a branch boundary is wrong both ways: it shows the whole office and misses remote team members. So:

- **Records (leave type, balances, money, date of birth): reporting line, in every tenant.** One rule.
- **Presence (in / away / off): may extend to the branch for store roles.** This is a later idea. Build it only if PPJ asks. The portal's weekly presence card already shows in/away for a manager's team without reasons.

**A trap for whoever fixes this.** Frappe has no built-in "me plus my reports" permission. This repo already built one for a single doctype: Attendance Deduction uses the employee tree to scope a manager to their reporting line (`hrms/hrms/alvoraa_late_rules/permissions.py`). That pattern exists. But two cautions for the engineer, from reading the code:

1. The Birthday, Advance Summary and Unpaid Expense Claim reports query the database directly (`frappe.qb ... .run()`). A reporting-line rule on the doctype would probably **not** narrow them. Removing the manager's access to those reports is the reliable fix. `[code read - engineer to confirm]`
2. Do **not** "fix" the manager by giving him a permission on his own Employee record, like the cashier. Portal leave approval also runs Frappe's own permission check (`_can_action_leave`, `hr_api.py` line 561). It might stop him approving his team's leave. Frappe may still allow it because leave is shared with the approver, but I could not check that. `[not verified]`

---

## 3 · The Leader question

**Kamal Gupta (Owner & MD) holds HR Manager. That is why he can read every payslip and every leave reason. Our CXO persona does not need that. It needs trustworthy totals.** `product-context.md` §2 says the CXO wants "one number they can trust", "company and BU roll-ups", "phone, five minutes".

- **This is a product gap, not a permission to take away.** There is no leadership view anywhere in the portal. I searched `alvoraa_portal` for cxo, leadership and executive and found only "Leadership Principles" (a values list). The only company-wide dashboard, `get_hr_analytics`, is for HR roles only. So an owner who wants headcount or attendance rate has to become HR.
- **We should not take it from him.** He is the employer. Under DPDP, deciding who inside the company sees staff data is the employer's decision, not ours. `[product reading - not legal advice]`
- **What we can do is make the smaller key possible.** Give the owner the totals he actually wants without HR Manager. Then limiting access becomes a choice the customer can make. Today they cannot. That also helps them meet their own data minimisation duty, and it is the answer a security reviewer wants.
- **A cheap start already exists.** The attendance analytics organisation view reads its allowed roles from a setting (`alvoraa_attendance_org_roles`, `attendance_analytics.py` line 43). A tenant can add a leadership role there with no code change. But note the view names individuals, not just totals.
- One more thing: in the portal, anyone with HR Manager is treated as HR (`get_portal_context`, `hr_api.py` line 128). So Kamal also gets HR's approval and admin screens.

⚠ **DECISION (Surbhi):** Is a leadership view (company and branch totals, no named individuals' pay or leave reasons, suppressed below a minimum group size) a slice we want? It blocks any honest advice to PPJ to take HR Manager off the owner.

---

## 4 · Birthdays

**Showing a floor manager 72 full dates of birth, with year and gender, is unnecessary personal data. Wishing people a happy birthday is good team culture. The two are different things.**

- The culture need is **already met by Frappe HR's built-in birthday reminder** (HR Settings, "Send Birthday Reminders"). It emails the company on the day, "Today is X's birthday", with **no year and no age** (`hrms/hrms/controllers/employee_reminders.py`, lines 87-127).
- The desk report adds the **year** (so age) and **gender**, for a whole month, for 72 people. No job needs that.
- What neither gives today is a way for an employee to **opt out**. Some people do not want their birthday announced. `[recall - verify: HiBob and similar tools let employees hide birthday or age]`
- **Verdict: remove the Employee Birthday report from the Employee role.** Tell tenants the HR Settings reminder exists. An opt-out and a "birthdays this week" card for a manager's own team (day and month only) is a small portal idea for later, if customers ask.

---

## 5 · The two money reports (advances, expense claims)

**Serious if true. The code makes it very likely true. The real exposure at PPJ today is zero, because no advance or claim records exist.**

- **Why I believe the inference.** Neither doctype has a Branch field. I checked `employee_advance.json` and `expense_claim.json`. Both reports query the table directly and filter only by the choices typed into the report (`employee_advance_summary.py` lines 105-143, `unpaid_expense_claim.py` lines 28-52). Frappe then hides rows only by the linked records the user is limited on. The manager is limited on Branch, and these rows carry no Branch. This matches what was measured for the Birthday report, which does have a Branch column.
- **Why it is serious.** It is money, it crosses every branch, and it points to people in financial difficulty.
- **It is wider than PPJ.** Standard Frappe HR gives the Advance Summary to the **Employee** role, and Unpaid Expense Claim to **Expense Approver** (the report `.json` files). So an employee is protected only because someone created a permission on her own record. **Any employee whose permission was never created would see every advance in the company.** `[inferred - not tested]`
- **Must it be proven before acting?** **Not before removing the access.** No manager or employee job needs these reports, so removing access costs nothing, even if the inference is wrong. **Yes before calling it a data leak** to PPJ, in a security questionnaire, or in any incident assessment. Proof is cheap: create one advance and one claim in another branch on the local copy, then run both reports as Balwinder. That test should stay as an automated check afterwards.

---

## 6 · What the ESS portal already gives each persona

Checked in `alvoraa_portal/alvoraa_portal/hr_api.py`, `attendance_analytics.py` and `www/hrms-employee.html`. The portal fetches its own data and scopes it by who reports to whom, not by Frappe User Permissions.

| Need | Employee (portal) | Manager (portal) | Desk report it replaces |
|---|---|---|---|
| Leave balances | Own (`get_leave_summary`) | Each direct report (`get_employee_detail_for_manager`) | Leave Balance Summary, Leave Balance |
| Who is off / on leave | Weekly presence of team or department, in/away only, no reasons (`get_week_presence`) | Today's attendance, who is on leave with leave type, the month's approved leave, for direct reports and one level below (`get_manager_dashboard`) | Attendance list, Shift Attendance |
| Approve leave | - | Pending requests with reason; approve or reject (`action_leave`) | - |
| Attendance patterns | Own view | Team view, direct or whole line; refuses anyone outside the team (`attendance_analytics._population`) | Shift Attendance, Monthly Attendance Sheet |
| Late arrivals | Own deductions | Team late list (`get_team_late_list`) | - |
| Payslips, advances, expense claims | Own (`get_payslips`, `get_requests_history`, `get_expense_claims`) | **Not shown for the team, and should not be** | Advance Summary |
| Goals, scorecard, 1:1 notes | Own | Direct reports only | - |
| Birthdays | Not in portal (email reminder in HR Settings) | Not in portal | Employee Birthday |
| **Approve expense claims** | - | **Not in portal** | none (done in desk form) |

**Result: removing the manager's desk reports loses him nothing the portal does not already do better, for the right 18 people.** The one thing to check is expense approval, which is a form, not a report.

The manager portal does show his own team's **leave type**. I think that is right. A manager has a duty of care his colleagues do not, and the `get_week_presence` comment already draws that line. It is worth a sentence in §6 of the product context.

---

## 7 · Priority order

| # | Change | Class | Type | What it protects |
|---|---|---|---|---|
| 1 | **Stop the manager reading all 403 Attendance records in the desk** (reason for absence visible to colleagues) | **Must** | Permission / configuration | Employees' health, pregnancy and money privacy; our absence rule |
| 2 | **Keep option B** (no report or export on Attendance for Employee and Employee Self Service). Commit it through the normal process | **Must** | Configuration, already done locally | Same as 1 |
| 3 | **Remove Employee Advance Summary from the Employee role, and Unpaid Expense Claim from Expense Approver**, unless a finance role needs them. Then prove the inference with one test record each | **Must** | Report role configuration | Money data across all branches |
| 4 | **Test the people nobody tested.** The seed script gives "Head - ..." roles, Store Accountant and Store HR & Admin Executive (who holds **HR User**) **no User Permission at all** (`seed_employees.py` lines 148-163). They may see far more than Balwinder | **Must** (test, not change) | Measurement | Knowing the real exposure before advising PPJ |
| 5 | **Remove Employee Analytics, Employee Birthday and Leave Balance Summary from the manager's desk access**. The portal covers his team | **Should** | Report role configuration | Date of birth, gender and leave use of 54 colleagues |
| 6 | **Write down Alvoraa's default access model per persona** (employee = self; manager = reporting line for records; HR = company; leader = totals). Replace the demo seed's Branch permission with it, and add the absence rule to `product-context.md` §6 | **Should** | Product decision + documentation | Every future tenant, not just PPJ |
| 7 | Remove the three self-only reports from the Employee role (they add nothing to the portal) | **Could** | Configuration | Less to secure and explain |
| 8 | Leadership totals view for the CXO | **Could** (as a slice) | New code | Lets owners drop HR Manager |

Everything in 1-5 and 7 is configuration. Nothing needs a new app or module.

### Decisions only Surbhi can make

- ⚠ **DECISION - Manager boundary.** Is "reporting line for records, branch presence only" the Alvoraa default for every tenant? **Blocks:** item 6, and how the next tenant is set up.
- ⚠ **DECISION - Desk or portal for managers.** Should a line manager use the desk at all, or is the portal their whole product? If portal-only, most of this becomes "give managers no desk reports". **Blocks:** items 5 and 7, and whether expense approval needs a portal screen.
- ⚠ **DECISION - Leadership view.** Build one (§3)? **Blocks:** any advice to take HR Manager off an owner.
- ⚠ **DECISION - What we tell PPJ.** Whether and how to tell PP Jewellers that their manager access was wider than intended. Nothing is known to have been seen, and this is a local copy. ⚠ COMPLIANCE: whether any of it counts as a reportable event is for the named compliance owner, who is not yet named (`product-context.md` §5). **Blocks:** nothing technical; it shapes the customer conversation.

---

## Thriving-workplace lens

| Lens | One line |
|---|---|
| Engagement | A cashier who trusts that her Sick Leave is not visible across six branches is more likely to take it honestly. |
| Collaboration | No effect. Team work already happens in the portal. |
| Inclusiveness | The people most exposed are frontline staff with the least power: cashiers and sales staff whose leave type and advances were visible. |
| Transparency | Presence stays visible (good for cover). Reasons, money, age and gender stop being visible to people with no duty of care. |

## Regulatory read

1. **Regime:** DPDP Act 2023 and Rules 2025 (purpose limitation, data minimisation, reasonable security safeguards). No AI or employment-law angle.
2. **Whose duty:** mainly the employer's (PPJ). Ours is to ship a default that does not over-share, and to make least access possible.
3. **What this makes possible:** nothing new is collected. It narrows visibility.
4. **Front page test:** "Jewellery chain's floor managers could see which colleagues in other stores took sick leave" is not something we would defend. The fix is.

---

## Open questions

| Question | Owner | Blocks |
|---|---|---|
| Does Balwinder (or any floor manager) approve expense claims, and where? The seed does not give Floor Managers Expense Approver, yet he could open Unpaid Expense Claim. Which role gave it? | Surbhi / engineer | Item 3; whether the portal needs expense approval |
| Why did the setup choose Branch permission? Does anything else rely on it (check-ins, leave approval in the desk)? | Engineer | Items 1 and 5 |
| Would a reporting-line rule on Attendance break portal leave approval (`_can_action_leave`)? | Engineer | How item 1 is built |
| Does a Frappe User Permission allow more than one record per doctype (several branches)? The brief says one; I recall several are allowed. `[recall - verify]` | Engineer | Regional-manager setups |
| Who else at PPJ has no User Permission, and what do they see? | Tester | Item 4 |
| Named compliance owner | Founder | The PPJ conversation |

## Assumptions

- `[ASSUMPTION]` The four people tested are typical of their persona. Heads, accountants and store HR were not tested.
- `[ASSUMPTION]` PPJ's live tenant has the same permissions as the local copy.
- `[ASSUMPTION]` Floor managers do their team work in the portal, not the desk, as the brief says.
- `[ASSUMPTION]` A manager having visibility of their own team's leave type is acceptable (duty of care). Not yet written as a product rule.
- `[ASSUMPTION]` The advance and expense inferences hold. Strongly supported by the code, not proven by running.
- Competitor practice was not researched for this review. The one competitor claim above is `[recall - verify]`.
