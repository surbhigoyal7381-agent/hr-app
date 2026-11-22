# Slice 089 — Manager profile edits: UX opportunities scan

**Mode:** opportunities scan, before the product brief · **Date:** 22 Nov 2026
**Read:** worktree `.claude/worktrees/089-manager-profile-edits`, branch `slice/089-manager-profile-edits`, based on `origin/dev` c9d702f0. Code and docs only.
**Not done:** I did not open the running portal, so I did not look at any screen. No login, no tenant, no screenshots. Every "today" statement below is from code, and says so.
**Labels:** **proven** = read in the file named. **inferred** = my reasoning from what I read. **not checked** = I did not look.
**Tier for the build (my view):** Tier 1. It changes who can change what on a person's record and it sets a leaving date that stops pay (usage-discipline §1).

## 1. The job, in one sentence

A store manager on a phone, who is the first to know someone has left, tells payroll in under a minute. Payroll confirms it in Desk. Nobody at the store ever sees a payroll screen.

Personas in scope: store manager (frontline supervisor), payroll team, employee (the person being reported), Administrator. Left out on purpose: CXO (no change; nothing here is an aggregate).

## 2. What exists today

| What | Fact | Label |
|---|---|---|
| Employee corrects own details | `my_profile.py`: six fields (`cell_number`, `personal_email`, `current_address`, `person_to_be_contacted`, `relation`, `emergency_phone_number`) in `people_fields.MY_PROFILE_WRITE_FIELDS`. The org ticks which, key `alvoraa_my_profile_fields`. Saved with `db.set_value`, plus a hand-written Version row. Required marks never refuse a save. | proven |
| Manager sees a report | `positions_profile.get_positions_profile`: eleven work facts, ticked by the org (`alvoraa_positions_profile_fields`). Deny list (`NEVER`) holds pay, bank, IDs, date of birth, home, next of kin. | proven |
| The leaving date a manager sees | Only a sentence: `left_on` and `still_here`, built from `relieving_date`. It is never a row, and the reason for leaving is never recorded. | proven |
| Manager changes a report | **Refused.** `employee_field_rights.employee_has_permission` (ALV-266): only HR changes another person's record. | proven |
| A hook already waiting for this slice | `MANAGER_EDITABLE = ()` in `employee_field_rights.py` line 94. Empty today. A save that touches only fields named there passes the refusal. | proven |
| Team panel actions | `team_api.ACTION_MATRIX` decides each action once, for a direct report or an HR-covered person. It has no "report a leaver" or "edit details" action. | proven |
| Settings card for ticked fields | `templates/includes/ess/parts/org-settings.html` and `public/js/ess/portal.js` (the 078 pattern: tags on the page, one button, a dialog). I did not read the card line by line. | proven (exists), not checked (details) |
| Role "Payroll team" | Named in the ALV-328 slice docs as a Desk role. I found no portal screen for it, and I did not look in Desk. | proven (named in docs), not checked (what it can open in Desk) |
| Any leaver or "left" flow in the portal | Searched: `alvoraa_portal/*.py` for "resign", "Separation"; `positions_profile.py`; `team.html`; `team_api.py` function list. Only hit is the Employee Separation workspace-link note in `subscription.py`. **I searched code only, not the running portal or Desk**, so "none" is limited to those places. | proven (searched, limited) |

**What this means.** Today a store manager has no way to say "she left" except a call or message to someone. Payroll hears late and pay may run for a person who has gone. **inferred** from Surbhi's brief, not measured.

## 3. How others handle it

**Honest limit:** one search for manager-started exits returned Oracle, Infor and Workday pages, and **nothing** on Keka, Zoho People, greytHR, Darwinbox or BambooHR. I have no trial accounts. Every claim about those five is **not checked** and must not enter the brief as fact. A second pass of their help pages is needed if the PM wants it.

| Product | What I can say | Label |
|---|---|---|
| Infor GHRTM | Direct manager or admin can start a resignation on the person's behalf. When the manager starts it, the notice goes to the HR administrator only. [Infor docs](https://docs.infor.com/ghrtm/2026.x/en-us/ghrtmolh/ghrtmmgrug/jnl1521652337849.html) | read, 22 Nov 2026 |
| Workday (Waterloo guide) | A delegate can start a termination for someone who resigned by email. [Waterloo](https://uwaterloo.ca/workday/workday-user-guides/delegate-termination-and-resignation-tasks) | read, 22 Nov 2026 |
| Oracle Fusion | Managers start a termination after the employee has resigned; a thread says a manager-submitted resignation was hard to grant. [Oracle support note](https://support.oracle.com/knowledge/Oracle%20Cloud/2759579_1.html) | read, 22 Nov 2026 |
| Keka, Zoho People, greytHR, Darwinbox, BambooHR | Not checked. `[recall — verify]`: most let a manager start an exit for a report and route it to HR for approval. | recall — verify |

**Pattern across the three I did read:** the manager *starts* it, HR *finishes* it. That is Surbhi's Option A, so the shape is normal. The common word is "initiate" or "on behalf of".

## 4. Ideas, persona by persona

| # | Persona | Idea | Job it serves | Evidence | Size |
|---|---|---|---|---|---|
| A | Store manager, phone | **"Report that someone left"** on the report's row in Team. Two inputs: last working day (date picker, default today) and a Send button reading "Tell payroll that Ravi left". One screen, no reason box. After sending: "Sent to the payroll team on 22 Nov. Ravi is still shown as working until they confirm." | Tell payroll in under a minute | Brief; `ACTION_MATRIX` is the one place actions are decided | S–M |
| B | Payroll team, Desk | The report arrives as a **to-do for the Payroll team role**, with who, the last working day, who reported, and when. Payroll presses Confirm; only then does the normal Employee save set Left and `relieving_date`. Decline or "date is wrong" goes back to the manager in words. | Confirm once, in the tool they already use | Brief; one-way save rule | M |
| C | Administrator | Extend the existing 078 tag-and-dialog card: two lists, **"Managers can see"** and **"Managers can change"**, each from a closed list. Save button names the effect ("Save — managers can change 2 fields for 45 people"). Default: both empty. | Control who sees and changes what, in one place | ux-learnings: widening-audience pattern; `my_profile` default empty | M |
| D | Employee | When a manager reports them as left, they are **not** silently changed. Their own page says "Your manager reported a last working day of 30 Nov. Payroll has not confirmed it yet. Not right? Tell HR." | Understand every change that affects them | Principle: explain every number that touches pay; one-way rule | S |
| E | Employee | Any field a manager changes shows on **their** My profile as "Changed by your manager on 22 Nov" (from the Version row). | Never find out by surprise | `my_profile.py` already writes Version rows | S |
| F | Store manager | Manager "can see" fields reuse the existing 078 mini profile (same component), not a second profile view. | One component, shown everywhere | ux-learnings: one component pattern | S |

## 5. Risks and decisions for the brief

- **Risk, P1 if missed: a manager marking someone Left by mistake or in anger.** Option A stops it: the manager only sends a request. The screen must say plainly "payroll confirms this" so the manager is not told it is done. **inferred**
- **Risk: the person is still paid and still signs in until payroll confirms.** The brief should say what a reported-but-unconfirmed person looks like to everyone (my suggestion: unchanged, with a small "last day reported: 30 Nov" line for the manager and payroll only).
- **⚠ DECISION (Surbhi / hrms-product-manager): how does payroll learn about the request?** Options: (1) a Frappe ToDo or Notification to the Payroll team role, (2) a new small DocType, (3) reuse Employee Separation. I recommend (1), the cheapest rung. Not checked: whether the Payroll team role can open Employee in Desk; the BA must verify.
- **⚠ DECISION: "can change" fields.** The only fields that make sense for a store manager are on the existing six-field list (e.g. phone, address). Allowing job title, branch or shift would reach field rights and ALV-266. Recommend a closed list that is a subset of the six plus nothing else, and `NEVER` stays untouched. Whether a manager may change a report's personal phone at all is a privacy question for `hrms-security-privacy-engineer`.
- **Risk: write path.** 078 writes with `db.set_value`, which skips Employee validate hooks. A manager write over another person's record needs the security engineer to choose that route, not the UX.
- **Risk: a manager who is also HR.** Reuse the 009 pattern (two lists, never merged); a manager cannot be the only confirmer of their own report's exit.
- Words: the product uses "manager" in the notice, and the code uses "supervisor" in places (ux-learnings MA2). Use one word. Use "last working day", not "relieving date" or "separation", on every portal screen.

## 6. Three strongest opportunities

1. **A (with B): "Report that someone left" in Team on the phone, confirmed by payroll in Desk.** It is the whole reason for the slice and matches what the three vendors I read do.
2. **`MANAGER_EDITABLE = ()` already exists.** The permission gate has a place for exactly this; the build can reuse it instead of loosening ALV-266. Saves time and keeps the one-way rule visible. (proven in code; the fit is inferred)
3. **C: one settings card for "can see" and "can change", default empty, reusing the 078 dialog.** Keeps this narrow and avoids slice 077's complexity: no new roles.

## 7. Not copying

- A manager-facing HR profile with every field. Competitors' manager views vary; I did not check them. We show only what the org ticks.
- A reason-for-leaving box on the manager's screen. `positions_profile.py` already refuses to record it, and a store manager should not be recording it.
- Instant status change on the manager's tap. It would put pay and sign-in at the mercy of one tap.

## 8. Not in this slice (for Surbhi to decide, not built)

Notice-period tracking, exit interview, asset recovery checklist, a manager "undo" after sending, other changes managers might report (transfer, shift), Hindi translations of the new words (needed before store use; machine-drafted copy needs native review).

## 9. Subtract pass

Removed from my own list before saving: a prototype (not required in scan mode), a "my reports who left" history page, push notifications to the employee, and a bulk "report several leavers" screen. None is needed to meet the stated requirement.
