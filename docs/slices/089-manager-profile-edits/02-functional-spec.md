---
slice: 089-manager-profile-edits
artifact: 02-functional-spec
author: hrms-business-analyst
date: 2026-11-22
status: draft, for Surbhi
risk tier: 1 (who can see or change what, personal data, a date that stops pay)
inputs: 01-product-brief.md, 01b-ux-design.md, prototype-v4.html, 01c-security-privacy-requirements.md, 07-devops-inputs.md §3
---

# 089 · A manager reports a leaver; managers see a little more of their team

**What I read.** Worktree `.claude/worktrees/089-manager-profile-edits`, branch `slice/089-manager-profile-edits`, HEAD `01644e17`. In this worktree I opened: `alvoraa_portal/alvoraa_portal/hr_api.py`, `employee_field_rights.py`, `team_api.py`, `hooks.py`, and `hrms/hrms/alvoraa_org_structure/settings.py`, `people_fields.py`, `alvoraa_hr_core/access.py`. **Frappe and ERPNext source is not in this worktree and I did not open it.** Every claim about `ToDo`, `assign_to`, `Notification Log` or ERPNext's Employee is taken from `01c` (which read Frappe 16.33.1 in the shared bench) and is marked *per 01c*. No site was opened. No code was run.

**Labels.** **Confirmed** = I read the line named. **Per 01c** = security engineer read it, I did not. **[ASSUMPTION]** = my guess. **[UNVERIFIED]** = engineer must check.

## Bad news first

1. **Three of Surbhi's four open items change what is built, not just the paperwork.** If the Employee timeline line is not written (Security Q1 default), the Desk timeline line drawn in prototype v4 is **not built**. That is a difference from the approved prototype and needs her yes (see §6, row P-12).
2. **The default recipient route may break two requirements at once.** Per 01c, Frappe's `assign_to.add` quietly shares the Employee record with the assignee and emails the ToDo text. SEC-7 forbids the share and OPS-19 forbids email. The engineer must create the ToDo in a way that does neither (AC-12, AC-26). I did not read how, so it is `[UNVERIFIED]`.
3. **The "change" half is where all the risk sits and none of the brief's evidence.** The brief calls it "Indifferent to Reverse risk (proxy)". Recommendation in §3: build it last, behind the fallback Surbhi already approved.
4. **Retention of the notice (PRIV-4) blocks the release to main, not the build.**
5. **Two ToDo `validate` hooks already exist** (`alvoraa_portal/hooks.py` line 579 `grooming.refuse_side_record`; `hrms/hooks.py` line 340 `plans.refuse_side_record`). Confirmed. A third on the same event must be added to the list, not replace either. Test that all three still run.

## 0 · Cross-module reach

| App | Touched? | How |
|---|---|---|
| `alvoraa_portal` | **Yes, main home** | `hr_api.get_employee_scorecard` (l.1152) and `get_employee_detail_for_manager` (l.1491); `team_api` (Team list status line); `employee_field_rights.py` (read only, must stay unchanged: `MANAGER_EDITABLE = ()` at l.94); new report, emergency-contact and "my open report" methods; `hooks.py` |
| `hrms` (alvoraa_org_structure) | **Yes** | `settings.py`: three keys added to `ACCESS_GRANTING` (l.250) and saved through `set_cover_setting` (l.425); the Administrator card next to the 078 card; `people_fields.py` read only |
| `alvoraa_goals` | Read only | `get_effective_manager` fallback is deliberately **not** used (SEC-2) |
| `frappe` | Reused, not changed | ToDo, Comment guard doors, Notification Log, Version, Employee `status` / `relieving_date` |
| `erpnext` | Reused, not changed | Employee save and its Left hooks (not read; dry run OPS-16) |
| `alvox_compensation` | No | – |

HRMS domains: **org structure** (reporting line, Left status), **payroll** (a confirmed leaver stops pay; also the nightly draft-slip job, OPS-16), **attendance** (Left stops attendance marking: `[UNVERIFIED]`), **appraisals and goals** (Scorecard page only). Not leaves, not learning.

Personas: **Line manager** (acts), **Confirmer** (a user holding the set role; default HR Manager), **Employee** (sees the line), **Administrator / System Manager** (settings). **HR Manager** is also the default confirmer. **CXO:** no change, nothing here is a total.

## 1 · Gap analysis

| # | Requirement | What exists today (source) | Verdict | Cost |
|---|---|---|---|---|
| G1 | A place to store "reported, not yet confirmed" | Frappe `ToDo` with `reference_type` / `reference_name` / `allocated_to` / `assigned_by` (per 01c; field list **[UNVERIFIED]** in `todo.json`). Frappe HR **Employee Separation** exists for HR in Desk but is a full exit process (brief §3, not read in source) | **Configure** (reuse ToDo, no new DocType) + **one Custom Field** on ToDo (see G1a) | S |
| G1a | Which ToDos are leaver reports, and what last working day they carry | ToDo has no type field and no date for it (per 01c). Parsing the description is fragile, and SEC-11 builds the description from record values. | **Extend**: one hidden read-only Custom Field `alv_leaver_last_day` (Date) on ToDo; its presence marks a leaver report. Existing fields cannot carry a typed date. `[ASSUMPTION]` engineer may pick a cheaper marker if it is as safe | S |
| G2 | Tell each confirmer | `assign_to` exists and is a role-wide helper only per user (per 01c); it adds a DocShare and sends email (per 01c) | **Extend**: create one ToDo per qualifying user without a share and without email | M |
| G3 | Confirm in Desk | Employee `status` (Left) and `relieving_date` saved by HR User / HR Manager / System Manager only (`LEVEL_2_WRITERS`, `employee_field_rights.py` l.96, confirmed) | **Configure**: the normal Employee save stays the confirm. **Extend**: one Employee `on_update` hook closes the open ToDos | S |
| G4 | Tell the reporter the outcome | `Notification Log` exists, readable only by `for_user` (per 01c) | **Extend**: one row written on ToDo close | S |
| G5 | Manager action only for direct reports | `ACTION_MATRIX` / `allowed()` in `team_api.py` (l.90, l.109): 11 actions, none for reporting a leaver (confirmed) | **Extend**: server check is `reports_to` = caller's Active Employee. Not `get_effective_manager` | S |
| G6 | Stop the Scorecard leak (ALV-433) | `get_employee_scorecard` (l.1172) and `get_employee_detail_for_manager` (l.1510) read `cell_number, personal_email, company_email, ...` (confirmed) | **Extend**: cut the field list, one shared helper | S |
| G7 | Admin picks what managers see / change, and the confirming role | The 078 card and `set_cover_setting` pattern, `ACCESS_GRANTING` frozenset (confirmed) | **Configure + Extend**: three keys, one card, same pattern | M |
| G8 | Manager changes emergency contact | `MANAGER_EDITABLE = ()` (l.94, confirmed); `my_profile.save_my_profile` is the model (named in 01c; **not opened by me**) | **Build new**: one whitelisted method. Justification: `MANAGER_EDITABLE` checks no reporting line, tick or status (01c, `employee_has_permission` l.307) so it cannot carry the rule | M |
| G9 | Employee is told | Version rows exist per 01c; no employee-side screen for a manager's report | **Extend**: one method, own record only; text on My profile | S |
| G10 | Reporter cannot edit or delete the notice | ToDo/Comment `validate` hooks exist (confirmed, above) | **Extend**: add guards on four doors + `on_trash` | M |
| G11 | Rate limit | `field_app_limits._limited` pattern named by 01c / OPS-12 (**not opened by me**) | **Configure** (reuse) | S |
| G12 | A reason-for-leaving box, withdraw/undo, history page, notice period, reminder job, new DocType, purge job, email, push | – | **Drop** (already out of the brief) | – |

**Single source of truth:** a leaver report is the open ToDo. The Employee `status` and `relieving_date` stay the only leaving facts. The two never share a value until a confirmer saves.

**Rung:** customisation and new code on existing doctypes. **No new DocType, no new app, no queue job, no scheduler job, no nginx change.** One Custom Field on ToDo (G1a) is the only schema change.

## 2 · Process flow

1. Store manager opens Team, taps a direct report's card. The Scorecard opens (as today).
2. Manager taps the exit icon beside the name. Sheet: last working day (today by default), preview line, **Report that Ravi left** or **Not now**.
3. Server checks (SEC-6). On any refusal: a plain sentence, nothing written.
4. Server writes, in one transaction, one ToDo per qualifying confirmer. Nothing is written to Employee `status` or `relieving_date`.
5. Manager sees "Sent for confirmation". Team card shows "⏳ Reported, not yet confirmed". The employee, if they have a login, sees the quiet line on My profile.
6. Confirmer opens the ToDo in Desk, opens the Employee, sets Status Left and Relieving Date, saves.
   - **Confirm:** the ToDos close; the manager gets one bell line; the person leaves the Team list.
   - **Decline:** the confirmer closes the ToDo; the manager gets one bell line "closed without being confirmed"; the person stays on the team.
   - **HR sets Left first:** the Employee save closes the ToDos the same way.
   - **No one acts:** the ToDo stays open. There is no reminder (dropped).
7. Unhappy paths: no signal (draft kept); not a direct report; already reported; bad date; nobody can confirm.

## 3 · What I recommend dropping

| Item | Recommendation | Why |
|---|---|---|
| **The "change" half** (US-10, US-11, `Managers can change` row, emergency-contact endpoint, ACs 42-47) | **Defer. Ship "see" only first**, as Surbhi's D1 fallback already allows | Evidence is a proxy; the smaller group of personal data; most new code and most security tests (SEC-4); can follow when a tenant asks. Saves 7 of 51 points |
| The Employee timeline line | **Do not write it** (Surbhi's default for Security Q1) | A skip-level manager could read it. The ToDo alone carries the notice. Also removes the Comment guard from SEC-9 |
| The `Changed by <name>` line under the Administrator card for the role row | Keep (it is the 078 pattern), no extra work | – |
| A cap check **and** a "count shown" on the Save button | Do one: **refuse above the cap**, and show the real count as text | One rule is testable |

Nothing else in the brief or design needs dropping.

## 4 · Epic and stories

**Epic E-089: A manager tells the people who confirm leavers that someone has left, from a phone, in under a minute; and sees a little more of their own team, only when the organisation allows it.**

Story sizes are story points; every story is one persona's one outcome.

| ID | As a | I want | So that | Pts | Screen | SEC / PRIV / OPS |
|---|---|---|---|---|---|---|
| US-1 | Line manager | to report that a direct report left, from the Scorecard | the confirmer hears the day I know | 5 | Scorecard icon, report sheet, sent message | SEC-6, OPS-7 |
| US-2 | Line manager | **must not** be able to report anyone who is not my Active direct report, myself, or someone already reported | nobody's pay is stopped by a stranger or a repeat | 3 | failure sentences | SEC-6, SEC-5 |
| US-3 | Confirmer | a to-do for this person, only if I can confirm and cover the company | I can act, and nobody else is told | 5 | Desk ToDo | SEC-7, SEC-11, OPS-11, OPS-19, OPS-20 |
| US-4 | Confirmer, then Line manager | the report to close itself when the Employee is saved as Left, and the manager to hear the result | the list stays true and no one chases | 5 | Desk save; bell line; Team row | PRIV-3, D3 |
| US-5 | Line manager | **must not** be able to change or delete my own notice after sending | the date cannot be quietly rewritten | 3 | – | SEC-9 |
| US-6 | Employee | to see that my manager reported a last working day, in plain words | I am never surprised about my pay | 3 | Employee line (My profile) | PRIV-2 |
| US-7 | Colleague / other-team manager / other-company HR / guest | **must not** be able to read the notice | a leaver's name is not gossip | 2 | – | SEC-10, OPS-9, OPS-15 |
| US-8 | Administrator | one card to choose what managers see and change, and who confirms | I control it, and both lists start empty | 5 | Administrator card + dialogs | SEC-3, SEC-8, PRIV-1, OPS-11 |
| US-9 | Line manager | to see a direct report's ticked personal details on the Scorecard, and **only** those | I can reach them; the page holds nothing it does not draw | 5 | Personal details card | SEC-1, SEC-2, SEC-5, PRIV-1, OPS-14 |
| US-10 | Line manager *(deferrable)* | to change a direct report's emergency contact, if ticked | it stays current | 5 | in-place form | SEC-4, OPS-12 |
| US-11 | Employee *(deferrable)* | to be told when my manager changed my emergency contact | nothing changes behind my back | 2 | "Changed by your manager" | PRIV-2 |
| US-12 | Line manager | the Team card and the Scorecard to show "Reported, not yet confirmed" | I do not report twice, and I know where it stands | 3 | Team card line, Scorecard note | PRIV-3, OPS-5, OPS-6 |
| US-13 | Security engineer / Administrator | the three new write paths to be POST-only, CSRF-checked, rate limited and refusal-logged | a loop or a forged page cannot flood or act | 2 | – | SEC-5, SEC-12, OPS-12, OPS-13 |
| US-14 | Release owner | proof on a copy before main: the Left dry run, cache check, error watch, DocPerm read | a leaver is never half-applied | 3 | – | OPS-15, OPS-16, OPS-17, OPS-18, SEC-10 |

**Total: 14 stories, 51 points.** US-10 (5) and US-11 (2) are deferrable, so **44** points ship first. *Size check:* nothing is above 5. INVEST: US-4 is the largest by moving parts; if it grows, split "outcome bell line" (2) from "auto-close" (3).

**"Must not" stories:** US-2, US-5, US-7. Plus the negative rows of the permission matrix.

### YouTrack-ready table

| Summary | Description (short) | Persona | Pts | ACs | Requirements |
|---|---|---|---|---|---|
| Report a leaver from the Scorecard | Icon, sheet, send; writes ToDos only | Line manager | 5 | AC-1 to AC-5 | SEC-6, OPS-7 |
| Refuse the wrong reports | Not direct report, self, left, already open | Line manager | 3 | AC-6 to AC-9 | SEC-5, SEC-6 |
| ToDo for the right confirmers | Scoped, no share, no email, capped | Confirmer | 5 | AC-10 to AC-13, AC-26 | SEC-7, SEC-11, OPS-11, 19, 20 |
| Auto-close and outcome line | Employee save closes; bell line | Confirmer, Manager | 5 | AC-14 to AC-19 | PRIV-3 |
| Reporter cannot alter the notice | Four doors guarded | Line manager | 3 | AC-20, AC-21 | SEC-9 |
| Employee sees the open report | Plain line, no button | Employee | 3 | AC-22 to AC-24 | PRIV-2 |
| Others cannot read the notice | Read matrix | Colleague etc. | 2 | AC-25, AC-27 | SEC-10 |
| Administrator card | Three rows; refusals; Version | Administrator | 5 | AC-28 to AC-35 | SEC-3, 8; PRIV-1; OPS-11 |
| Scorecard sends only ticked fields | ALV-433 fix + Personal details card | Line manager | 5 | AC-36 to AC-42 | SEC-1, 2, 5; PRIV-1; OPS-14 |
| Change emergency contact (deferrable) | One endpoint | Line manager | 5 | AC-43 to AC-47 | SEC-4, OPS-12 |
| "Changed by your manager" (deferrable) | Employee line | Employee | 2 | AC-48 | PRIV-2 |
| Team and Scorecard status lines | Grey line, note, one query set | Line manager | 3 | AC-49 to AC-52 | PRIV-3, OPS-5, 6 |
| Write paths hardened | POST, CSRF, rate limit | Security | 2 | AC-53 to AC-55, AC-63 | SEC-5, 12; OPS-12, 13 |
| Proof before main | Dry run, cache, monitoring, DocPerm | Release owner | 3 | AC-56 to AC-60 | OPS-15 to 18, SEC-10 |
| Words, phone layout, nothing extra built | Translatable, 360 px | All | (inside above) | AC-61, AC-62, AC-64 | OPS-11, 13 |

## 5 · Data model

**No new DocType.** One new field. Every other field is read from source.

| DocType | Field | Type | Why an existing field cannot carry it |
|---|---|---|---|
| ToDo | `alv_leaver_last_day` (Custom Field, Date, read-only, hidden, no default, mandatory only for this kind) | Date | ToDo has no typed date; parsing text is fragile `[ASSUMPTION per 01c; todo.json not opened by me]` |

**Settings** (three keys; exact key names are the engineer's to choose, `[UNVERIFIED]`; they must be added to `ACCESS_GRANTING` in `settings.py` l.250):

| Setting | Holds | Default | Rules |
|---|---|---|---|
| Managers can see | list of tags | empty | candidates only: `cell_number`, `current_address`, emergency contact trio (`person_to_be_contacted`, `relation`, `emergency_phone_number`) |
| Managers can change | list of tags | empty | candidate: emergency contact trio only; must also be in "see" |
| Leaver notices are confirmed by | one role | `HR Manager` | SEC-8 |

**Fields read, none written, by this slice:** Employee `reports_to`, `status`, `date_of_joining`, `company`, `employee_name`, `user_id`. **Fields written:** only `person_to_be_contacted`, `relation`, `emergency_phone_number` (US-10 only), and only through the new endpoint, one Version row per save.

`current_address`, `personal_email`, `permanent_address`: `personal_email` and `permanent_address` never offered. `[ASSUMPTION]` "home address" = `current_address` (01c Q2 default).

**Other rows written per report:** ToDo (one per qualifying confirmer); Notification Log (one, later, on close). No Comment, no DocShare, no Email Queue.

## 6 · Prototype parity table (every v4 feature; build exactly as drawn)

"Exactly" means words, order, state and tap target. The viewer bar ("view", "device", "theme", "language", "When sending", "Settings: example", "Start again") is **not** product. Sample names, counts and dates (Ravi Kumar, Meena Sharma, 45 people, Raj Kumar) are replaced by real values.

| # | Drawn in v4 (file `prototype-v4.html`, `01b` §) | Built as drawn? | AC |
|---|---|---|---|
| P-1 | Team card: avatar, name, job, presence in plain words, nothing else; whole card opens the Scorecard as today; no icon, no button, no Details link (4.1.1) | Yes | AC-49 |
| P-2 | Team card grey line "⏳ Reported, not yet confirmed" while a report is open (4.1.4) | Yes | AC-49 |
| P-3 | Scorecard header: Back, avatar, name, job and department, "Joined" badge, **exit icon beside the name**, 22 px grey, 44 × 44 target, label and hover tip "Report that Ravi left"; icon gone while a report is open (4.1.1) | Yes | AC-1 |
| P-4 | Report sheet: `role=dialog`, title "Ravi Kumar left?", **Last working day** (today default, 16 px), preview "You are reporting: Ravi Kumar · last working day 22 Nov 2026.", explanation sentence, button **Report that Ravi left**, link **Not now** (4.1.2) | Yes | AC-2 |
| P-5 | Sent message "✓ Sent for confirmation. You reported this on 22 Nov 2026. Ravi shows as working until it is confirmed. Wrong person or date? Ask HR." and **Done** (4.1.3) | Yes | AC-3 |
| P-6 | Failure sentences (5): no signal (with Try again), not direct report, already reported, too old, too far (4.2) | Yes | AC-4, AC-6, AC-8 |
| P-7 | Scorecard reported note at top: "Reported, not yet confirmed. You reported on 22 Nov 2026 that Ravi's last working day is 30 Nov 2026. Ravi stays on your team until it is confirmed." (4.6.2) | Yes | AC-50 |
| P-8 | Personal details card, last on the page, full width; caption "Your organisation lets managers see these. Only you and HR can see them. Staff can see that you can."; rows for ticked items; absent if nothing ticked (4.6.3) | Yes | AC-40 |
| P-9 | Change emergency contact: outlined 44 px button in the card, only if "change" ticked and no report open; opens Name, Relation, Phone in place; "Save emergency contact for Ravi" and Cancel; toast "Saved. Ravi will see that you changed it." (4.6.4) | Yes, **only if US-10 ships** | AC-43, AC-45 |
| P-10 | Stats row and the four cards on the Scorecard are Sample | **Not changed.** Today's page stays | – |
| P-11 | Desk ToDo "Confirm that Ravi Kumar left. Last working day 30 Nov 2026. Reported by Meena Sharma on 22 Nov 2026." linking to the Employee; closes on Save with Status Left (4.3) | Yes. Look is Frappe's own | AC-10, AC-14 |
| P-12 | Desk **timeline line** "Meena Sharma reported that Ravi left, last working day 30 Nov 2026 · 22 Nov 2026" (4.3) | **NOT built, by Surbhi's open default (Security Q1).** A difference from the approved prototype. **Needs her yes** | AC-27 |
| P-13 | Employee line on My profile: "Your manager Meena Sharma reported that your last working day is 30 Nov 2026. It has not been confirmed yet. Nothing about your pay or sign-in has changed. Not right? Speak to HR." Thin grey left edge, no button (4.4) | Yes | AC-22 |
| P-14 | "Changed by your manager Meena Sharma on 22 Nov 2026. Not right? You can correct it here, or speak to HR." under the emergency row (4.4) | Yes, **only if US-11 ships** | AC-48 |
| P-15 | Administrator card "What managers can see and change about their team": three rows, empty-state sentences, buttons "Change what managers see" / "Change what managers change", role row with live holder count, "Changed by <name> on <date>" line (4.5) | Yes | AC-28 to AC-35 |
| P-16 | "See" dialog: three ticks, hint per tick "Staff can already correct this on My profile.", sentence "Personal email, pay, bank, ID numbers and date of birth are never offered.", live Save button "Save — managers see 2 details about 45 people" with the real count (4.5) | Yes | AC-30 |
| P-17 | "Change" dialog: one tick; sentence "A manager can change only what they can also see. Personal phone and home address can never be changed by a manager."; implied see; removing see removes change, and says so (4.5) | Yes, **only if US-10 ships** | AC-31 |
| P-18 | Role refusal: "Nobody holds Accounts team, so nobody would be told. Pick a role that someone holds. Nothing was saved." (4.5) | Yes (role name varies) | AC-32 |
| P-19 | Bell line on confirm and on close (D3). Words drawn only in `01b` 4.1.5 and 4.1.6 | Yes, words in §10 | AC-17, AC-18 |
| P-20 | Hindi strings (manager and employee words) | Machine draft; **native review before store use** (not code) | AC-61 |
| P-21 | 360 px, 44 px targets, 16 px text, Escape, focus return on every sheet (§7) | Yes | AC-62 |
| P-22 | The word "payroll" never appears on any screen; "manager", "last working day" only (§2) | Yes | AC-64 |

## 7 · States and transitions

No workflow. The state is the ToDo.

| State | Meaning | Who may move it | Next | Notified |
|---|---|---|---|---|
| (none) | no report | – | Open | – |
| ToDo **Open** (with `alv_leaver_last_day`) | reported, not confirmed | created by the report method only | Closed (confirm or decline) | confirmers see ToDo; reporter and person see lines |
| ToDo **Closed**, Employee `status` = Left | confirmed | confirmer saving Employee, or any Employee save to Left | terminal | reporter: bell line |
| ToDo **Closed**, Employee `status` ≠ Left | declined | a confirmer (System Manager included) | terminal; a new report may be made | reporter: bell line |
| ToDo deleted | removed | a confirmer only | – | none `[residual risk]` |

Irreversible: a closed ToDo is never reopened by this slice. Wrong date: "Ask HR".

## 8 · Permission and visibility matrix

Legend: **Y** yes, **N** no, **own** own record only. "Report" is the new method.

| Who | Report a leaver | See personal-details card | Change emergency contact | Read the ToDo | Read bell line | See employee line | Change the three settings |
|---|---|---|---|---|---|---|---|
| Direct manager of an **Active** person (own Active Employee = `reports_to`) | Y | Y, ticked only | Y, ticked only (US-10) | own ToDos only (reporter's own) | Y (own) | – | N |
| Skip-level manager | **N** | **N** | **N** | **N** | N | – | N |
| Manager of a person with **no `reports_to`** (HR-covered) | **N** | **N** (not via `get_effective_manager`) | **N** | N | N | – | N |
| Manager of a **Left** person | **N** | **N** | **N** | N | N | – | N |
| Left manager | **N** | **N** | **N** | N | N | – | N |
| Colleague / another team's manager | **N** | **N** | **N** | **N** | **N** | **N** | N |
| Confirmer (holds the set role **and** an `LEVEL_2_WRITERS` role **and** covers the company) | N (unless also their direct manager) | via HR's own rights, unchanged | N | **Y** | – | – | N |
| HR of **another** company | N | N | N | **N** (no ToDo, no share) | N | N | N |
| The person reported | N (not themselves) | – | – | N | – | **Y**, own only | N |
| HR Manager (not System Manager) | – | – | – | – | – | – | **N** (refused, logged) |
| System Manager | – | – | – | Y (ToDo role row) | – | – | **Y**, Version row |
| Guest | N | N | N | N | N | N | N |

Scope words, counted: "enabled holders" is bounded by the cap (default 10, OPS-11, open). "Direct report" means `reports_to` equals the caller's **own Active Employee** (`_get_employee` filters `status = "Active"`, per 01c, `hr_api.py` l.304-307 region **[line read: function defined at l.304; filter not read by me]**).

## 9 · Acceptance criteria

Test conditions that apply to every AC below (from 01c §7): a manager **with a direct report who has phone and address**; **two companies** with an HR Manager in each; the reporter's **own session** (not Administrator); **real HTTP** for CSRF; at least one **allowed** case per matrix so a pass cannot mean "nobody is allowed".

### US-1 Report a leaver

- **AC-1.** *Given* a signed-in manager on the Scorecard of an **Active** direct report with no open report, *when* the page loads, *then* the exit icon (aria-label "Report that Ravi left", 44 × 44 px target) shows beside the name. *And* it is absent on: a person with an open report, a Left person, a person with no `reports_to`, a skip-level report, the manager's own Scorecard.
- **AC-2.** *Given* the icon is tapped, *when* the sheet opens, *then* it has `role=dialog`, focus is on Last working day, the date is today, and the preview reads "You are reporting: Ravi Kumar · last working day 22 Nov 2026." *And* **Not now** closes it, writes nothing, and returns focus to the icon.
- **AC-3.** *Given* a valid date, *when* **Report that Ravi left** is tapped, *then* the response is success, the sheet shows "✓ Sent for confirmation. You reported this on <today>. Ravi shows as working until it is confirmed. Wrong person or date? Ask HR.", and on the Employee `status` is still "Active" and `relieving_date` is unchanged (read back by `frappe.db.get_value`).
- **AC-4.** *Given* the network drops, *when* Send is tapped, *then* the sheet shows exactly: "Not sent. We kept your date. Try again when you have signal.", the date field keeps its value, and a **Try again** button is shown. *And* no ToDo exists after the failed call.
- **AC-5.** *Given* the manager taps Send twice quickly, *when* both calls reach the server, *then* exactly one report exists (one ToDo per confirmer, not two) and the second call gets the "already reported" sentence.

### US-2 Refusals (must not)

- **AC-6.** *Given* a caller who is a skip-level manager, a colleague, another team's manager, the manager of an HR-covered person, or in another company, *when* they call the report method for that person, *then* the answer is "Ravi Kumar does not report to you, so you cannot report this. Ask HR.", the ToDo, Comment and DocShare counts are unchanged, and `security.log` holds one line naming caller, rule ID, endpoint and employee ID and no phone, address or contact. *And* the matrix includes one direct manager who succeeds.
- **AC-7.** *Given* a manager reports themselves, a Left person, or a caller with no Active Employee, *when* the method runs, *then* it is refused with a sentence, nothing is written, and the refusal is logged.
- **AC-8.** *Given* a last working day before the joining date, or more than 31 days before today, *then* "The last working day cannot be more than 31 days ago. Check the date." (before joining: refused the same way `[sentence for before-joining: engineer to reuse the 31-day sentence; Surbhi to confirm]`); more than 60 days ahead: "The last working day cannot be more than 60 days ahead. Check the date." The sheet stays open. Exactly 31 days ago and exactly 60 days ahead are accepted.
- **AC-9.** *Given* an open report already exists on the person, *when* the same manager reports again, *then* "You already reported Ravi Kumar on 20 Nov 2026. It has not been confirmed yet." *And* when a **different** user reports the same person, they get "Ravi Kumar already has an open report. Ask HR." (no reporter name). `[ASSUMPTION: second sentence is mine; Surbhi to confirm]`

### US-3 Confirmer ToDo

- **AC-10.** *Given* a valid report, *when* it is saved, *then* each qualifying user has one Open ToDo whose description is "Confirm that Ravi Kumar left. Last working day 30 Nov 2026. Reported by Meena Sharma on 22 Nov 2026.", references the Employee, and carries `alv_leaver_last_day`.
- **AC-11.** *Given* two companies each with one HR Manager, *when* a manager in company A reports, *then* only A's HR Manager gets a ToDo. *And* neither the reporter nor the person reported gets one even if they hold the role.
- **AC-12.** *Given* a report, *then* the DocShare row count for that Employee is unchanged, and the confirmer cannot open any other record because of it.
- **AC-13.** *Given* the ToDo insert fails for the third confirmer, *then* no ToDo exists for anyone and the manager gets a plain sentence. *And* the report writes in **one request**: no queue job and no scheduler job is added (`hooks.py` diff holds none).

### US-4 Confirm, decline, outcome

- **AC-14.** *Given* an open report, *when* a confirmer saves the Employee as **Left** with a Relieving Date, *then* every open leaver ToDo for that Employee is Closed in the same save, and the confirmer's date (not the manager's) is the one stored.
- **AC-15.** *Given* a Save with Status left on Active, *then* the ToDo stays Open.
- **AC-16.** *Given* HR sets Left on that Employee with no ToDo opened by them, *then* the open leaver ToDos close in the same save.
- **AC-17.** *Given* a confirmer closes the ToDo and the Employee is not Left, *then* one Notification Log row is written for the reporter only: "The report about Ravi Kumar was closed without being confirmed on 24 Nov 2026. Ravi stays on your team. Ask HR why." *And* the Team row loses its grey line and the Scorecard icon returns.
- **AC-18.** *Given* the Employee is saved as Left, *then* one Notification Log row for the reporter only: "Confirmed: Ravi Kumar left on 30 Nov 2026." *And* the person is gone from the Team list on next load.
- **AC-19.** *Given* a leaver who has direct reports, *when* Left is saved, *then* this slice's code writes nothing to their reports' `reports_to`. (What ERPNext does is read in the dry run, OPS-16, and recorded as brief decision 5.)

### US-5 Reporter cannot alter (must not)

- **AC-20.** *Given* an open report made by the manager's own session, *when* that manager calls `frappe.client.set_value` or `save` on the ToDo, `frappe.client.delete` on it, or `frappe.desk.form.assign_to.remove`, *then* each is refused and the ToDo is unchanged. *And* the reporter, by the same four calls, cannot reopen or edit a Closed one.
- **AC-21.** *Given* a confirmer, *when* they close the ToDo, *then* it works.

### US-6 Employee line

- **AC-22.** *Given* a person with a login and an open report, *when* My profile loads, *then* the line in P-13 shows with the reporter's name and the date, and there is no button. *And* the response holds no confirmer user ID.
- **AC-23.** *Given* a colleague calls the same method, *then* they receive only their own (empty) state.
- **AC-24.** *Given* the report is confirmed or closed, *then* the line is gone on next load.

### US-7 Others cannot read (must not)

- **AC-25.** *Given* one open report, *when* a colleague, another team's manager, a skip-level manager, an HR user of another company and a guest each call `get_list("ToDo")`, `get_list("Notification Log")` and `getdoc("Employee", person)`, *then* the report text (name with last working day) appears for none of them. *And* a confirmer of the right company sees the ToDo (the allowed case).
- **AC-27.** *Given* a report, *then* no Comment row is written on the Employee (Security Q1 default). *If Surbhi says yes to the line,* this AC is replaced by AC-25 extended to the comment and by a guard on `update_comment`.

### US-3 (content)

- **AC-26.** *Given* an employee whose name is `<b>x</b>`, *then* the ToDo description holds the escaped text. *And* no phone, address, emergency contact, free text or Email Queue row is created by the report, on a tenant where outgoing email is on.

### US-8 Administrator card

- **AC-28.** *Given* a System Manager, *then* the card with its three rows is shown. *Given* any other role, including HR Manager, the card is absent (not greyed).
- **AC-29.** *Given* a fresh test site, *then* "see" is empty ("None. Managers see no personal details of their team."), "change" is empty ("None. Managers change nothing."), and the role is "HR Manager".
- **AC-30.** *Given* the "see" dialog, *then* exactly three ticks are offered (Personal phone, Home address, Emergency contact), personal email is not offered, the hint and sentence from P-16 show, and the Save button names the effect with the real count of active employees who have a manager.
- **AC-31.** *Given* the "change" dialog, *then* one tick (Emergency contact) is offered; ticking it when it is not in "see" adds it and says "Managers will also be able to see it."; unticking it from "see" removes it from "change" and says so. *(Ships with US-10.)*
- **AC-32.** *Given* a role save, *then* it is refused, with "Nobody holds <role>, so nobody would be told. Pick a role that someone holds. Nothing was saved." for: `Guest`, `All`, `Administrator`, `Desk User`, `Employee`, `Employee Self Service`; a role held only by disabled users; and a role whose enabled holders all lack an `LEVEL_2_WRITERS` role. `HR Manager` with one qualifying holder is accepted.
- **AC-33.** *Given* an HR Manager (not System Manager) calls the save for any of the three keys, *then* it is refused, logged, and nothing is written. *Given* a System Manager, *then* one Version row holds old and new value. A "see" save carrying `personal_email`, `permanent_address` or any `NEVER` field, or a "change" save with `cell_number` or `current_address`, or a change field not in see, is refused with a sentence and nothing is written.
- **AC-34.** *Given* a role with more than the cap (default **10**, open) enabled qualifying holders, *then* the save is refused with the count in plain words.
- **AC-35.** *Given* a save, *then* "Changed by <name> on <date>" appears under the card.

### US-9 Scorecard

- **AC-36.** *Given* a manager and both lists empty, *when* `get_employee_scorecard` **and** `get_employee_detail_for_manager` are called for a direct report through `/api/method/...`, *then* none of the eight keys `cell_number, personal_email, company_email, gender, current_address, person_to_be_contacted, relation, emergency_phone_number` appear anywhere in the JSON.
- **AC-37.** *Given* "Personal phone" is ticked, *when* the call is repeated with no restart, *then* only `cell_number` appears; after unticking, it is gone on the next call. `personal_email` and `permanent_address` never appear in any state.
- **AC-38.** *Given* the caller matrix (direct manager, skip-level manager, colleague, other team's manager, manager of a Left person, Left manager, HR same company, HR other company), *then* personal fields reach only: the direct manager of an Active person, for ticked fields; and HR of the same company by HR's existing rights. Everyone else gets the refusal, logged.
- **AC-39.** *Given* the two existing "Access denied" throws, *then* each now writes a `security.log` line through `access.refuse` (read from the log handler, not a mock), with no value from the record in it.
- **AC-40.** *Given* at least one item is ticked and the person is Active, *then* the Personal details card is the last, full-width card, shows the P-8 caption and only ticked rows. *Given* nothing ticked, or the person Left, *then* no card is drawn and no placeholder shows.
- **AC-41.** *Given* the Employee has no phone or address set, *then* the row shows an empty value in words (engineer: "Not set"; `[ASSUMPTION]`), not a blank gap.
- **AC-42.** *Given* the build, *then* `MANAGER_EDITABLE` is still `()` (`employee_field_rights.py` l.94).

### US-10 Change emergency contact *(deferrable)*

- **AC-43.** *Given* "change" ticked, an Active direct report, and no open report, *when* the manager taps **Change emergency contact**, *then* Name, Relation, Phone open in place, labelled, 16 px; **Save emergency contact for Ravi** writes the three fields, the page stays, the toast "Saved. Ravi will see that you changed it." shows, and one Version row is owned by the manager with old and new values.
- **AC-44.** *Given* each of: unticked, skip-level manager, Left person, an extra key such as `cell_number`, the caller's own record, *when* the endpoint is called, *then* it is refused and logged, and nothing changes (a break test: remove the `reports_to` check and the skip-level case must fail, then restore).
- **AC-45.** *Given* a report is open on the person, *then* the Change button is not shown and the endpoint refuses.
- **AC-46.** *Given* the manager, by `frappe.client.set_value("Employee", report, "emergency_phone_number", ...)`, *then* ALV-266 still refuses.
- **AC-47.** *Given* 21 saves in an hour by one user, *then* the 21st is refused with the wait in plain words (limit 20/hour, open numbers per OPS-12).

### US-11 *(deferrable)*

- **AC-48.** *Given* a manager changed the emergency contact, *then* the person's My profile shows P-14 with the manager's name and date, from the Version row.

### US-12 Team and Scorecard lines

- **AC-49.** *Given* the Team list, *then* a card tap opens the Scorecard as today; no icon, no button, no Details link on the card; the grey line "⏳ Reported, not yet confirmed" shows only for a person with an open report made by this manager.
- **AC-50.** *Given* an open report, *then* the Scorecard shows the P-7 note and no icon.
- **AC-51.** *Given* an open report, *then* `positions_profile` shows no leaving sentence for the person; their `relieving_date` is unchanged; a colleague's Team call shows nothing new; no export or report carries the date.
- **AC-52.** *Given* a manager with 50 reports, *then* the number of queries to build Team, including report state, does not grow with the number of reports (compare 5 and 50 reports).

### US-13 Hardening

- **AC-53.** *Given* a real signed-in portal session, *when* each of the three new write methods (report, emergency contact, settings setter) is POSTed **without** `X-Frappe-CSRF-Token`, *then* it is refused and nothing is written; with the token it works. *Break test:* make a method GET-able and watch the test fail.
- **AC-54.** *Given* a GET to any new write method, *then* it is refused.
- **AC-55.** *Given* 11 reports in an hour by one user, *then* the 11th is refused with the wait in plain words (10/hour, OPS-12). The limiter key is a hash of the user, never an employee ID or personal value.
- **AC-63.** *Given* any `except` in the new calls, *then* it calls `frappe.log_error` with the employee ID only (OPS-18).

### US-14 Proof before main

- **AC-56.** *Given* a copy of a real tenant, *then* the dry run of OPS-16 (cases a, b, c) is recorded with stdout and stderr, the nightly draft-slip job runs afterwards and does not roll back, and the save time is reported.
- **AC-57.** *Given* the Team and Scorecard ESS parts, *then* rendering them for two users gives strings that differ nowhere (OPS-15), and no cache is added to the Scorecard call.
- **AC-58.** *Given* each tenant (DTC, Grace, PPJ, others), *then* a read-only query lists Custom DocPerm rows on ToDo before main (SEC-10).
- **AC-59.** *Given* the release plan, *then* it holds the runbook backup with files and a size check (OPS-17), and the Error Log watch list of OPS-18 for the first hour and working day.
- **AC-60.** *Given* ALV-391's logger fix, *then* the release plan states whether it is on the target branch. Until it is, refusals are not observable there (SEC-5 residual risk).

### Across stories

- **AC-61.** *Given* every new user-facing string, *then* it is wrapped for translation, and the Hindi strings are tagged "machine draft, native review needed" in the release note.
- **AC-62.** *Given* a 360 px phone: no sideways scroll, targets at least 44 px, field text at least 16 px, Escape closes every sheet, focus returns to the opener, 200% text does not clip buttons (the last is not yet tested anywhere, so it is checked here for the first time).
- **AC-64.** *Given* the whole diff, *then* no screen string names "payroll" or a fixed confirmer role (only the Administrator's role picker shows role names); `git diff` has no `deploy/nginx.conf` change, no new route path, no new DocType, no queue or scheduler job, no purge job.

**AC count: 64 here, plus AC-65 added in the traceability gaps (§18): 65 in all.** (Numbers AC-26, AC-27 and AC-63 sit out of order under their stories; each is used once.)

## 10 · Notifications and messages

| Message | Trigger | Recipient | Exact copy | Must never contain |
|---|---|---|---|---|
| ToDo | report saved | each qualifying confirmer | "Confirm that Ravi Kumar left. Last working day 30 Nov 2026. Reported by Meena Sharma on 22 Nov 2026." | phone, address, emergency contact, free text, email send |
| Bell: confirmed | Employee saved Left | reporter only | "Confirmed: Ravi Kumar left on 30 Nov 2026." (my wording, `01b` 4.1.5 line; **Surbhi to confirm**) | any value from PRIV-1 list |
| Bell: closed | ToDo closed, Employee not Left | reporter only | "The report about Ravi Kumar was closed without being confirmed on 24 Nov 2026. Ravi stays on your team. Ask HR why." | – |
| Employee line | open report | the person | P-13 | confirmer names |
| Email | none | – | none (OPS-19) | – |
| Toast / sheet / failure text | §6 P-4 to P-9 | – | as drawn | "Something went wrong" |

## 11 · Edge cases that can happen

| Case | Rule |
|---|---|
| HR sets Left first, ToDo open | closes on that save (AC-16) |
| Manager changes (`reports_to` moves) while report open | the new manager sees nothing; the ToDo stays with the confirmers; a new report by the new manager gets the AC-9 second sentence |
| Reporter leaves | the ToDo stays open; the outcome bell goes to a disabled user and is harmless |
| Role loses its last holder after being saved | the report is refused at send time, nothing written (AC-9 sibling: the "Nobody can confirm this yet. Ask HR." sentence, SEC-7) |
| Confirmer enters a different date | theirs is used (AC-14) |
| Person has no login (agency staff) | manager reports as normal; nothing shown to the person; no harm |
| Person rehired or already Left | Left blocks a report; a rehire is a new Active status and may be reported again |
| Backdated joining date | before-joining date refused (AC-8) |
| Two confirmers save at once | the second save finds the ToDos already Closed; no error |
| Deleted ToDo | the report disappears; the manager's row returns to normal; no bell line (residual risk, listed) |
| Leaver with direct reports | nothing automatic (AC-19); dry run decides |
| Half-day, hourly leave, holidays, DST, time zones | not applicable: a last working day is a date only, no time |
| Multi-company | recipients scoped by `access.permitted_companies` (AC-11) |
| Bulk imports | not in scope; no bulk path |

## 12 · Non-functional requirements (nfr-budget numbers read via 07 §1-3; I did not reopen `nfr-budget.md` beyond the figure the DevOps file quotes)

| Item | Requirement |
|---|---|
| Volume | a manager has about 5 to 50 reports; one report writes at most the cap (10) ToDos; a handful of reports per tenant per month `[ASSUMPTION]` |
| Response | Team part under 2.5 s on throttled 3G (OPS-10, to be measured once built); the report call is one request (OPS-7) |
| Queries | one query set for all reports' states, not one per report (AC-52, OPS-5) |
| Background jobs | none; no queue, no scheduler (AC-13, AC-64) |
| Cache | none added; no per-user text in the 24-hour ESS part (AC-57) |
| Personal data | phone, address, emergency contact are personal contact data; protected by SEC-1/2/4; never in logs |
| Rate limits | report 10/h, emergency save 20/h per user (OPS-12, open numbers) |
| Monitoring | OPS-18, no new dashboard |

## 13 · Migration / backfill

- **Existing tenants:** one Custom Field on ToDo (G1a); three settings keys, defaults empty / empty / `HR Manager`. Both lists empty means **nothing visible changes** for any tenant at release except the ALV-433 cut (a manager's browser stops receiving four fields).
- **Backfill:** nothing. No existing record is touched. **Rollback:** revert the change; the custom field and any ToDos stay as harmless rows. Remove nothing by script without approval.
- `migrate` adds the field: needs the usual explicit approval; check the migrate queue first (memory: permission clean-up once filled it).

## 14 · Audit and traceability of change

| What | Recorded how |
|---|---|
| Who reported whom, when, which date | ToDo `assigned_by`, `creation`, `alv_leaver_last_day` (as read by 01c; engineer to confirm) |
| Outcome | ToDo closed time and the Employee `status`; one bell line |
| Settings change | Version row (SEC-3), "Changed by" line |
| Emergency-contact change | Version row owned by the manager (US-10) |
| Refusals | `security.log` through `access.refuse` (SEC-5), only where ALV-391 is deployed |
| A manager **reading** a phone or address | **not logged** (residual risk 1 in 01c, not yet accepted by Surbhi) |

## 15 · Compliance-impact sub-analysis

*I am not a lawyer. Every ⚠ row needs counsel or Surbhi. This builds on `01c`; it does not redo it.*

### 1 · Data touched

| Field | Class | Purpose | Lawful basis (as recorded) | New collection? |
|---|---|---|---|---|
| Last working day (reported) | employment, affects pay | tell the confirmer | not recorded in 01c; ⚠ | **Yes.** Impossible to do the job without it: it is the one fact the confirmer needs |
| Reporter, date sent | employment | accountability | as above | Yes, from the ToDo's own fields |
| `cell_number`, `current_address`, emergency trio | sensitive (personal contact; trio also a third person) | reach a team member | already on the Employee record | No new collection; a new **reader** |
| `personal_email`, `permanent_address`, `company_email`, `gender` | sensitive / internal | none in this slice | – | **No longer sent** to a manager |

### 2 · Obligations engaged

| Obligation | Source | What this slice does | Feature |
|---|---|---|---|
| Reasonable security safeguards, minimisation | DPDP Act 2023 (01c §4, read 22 Nov 2026) | send only ticked, closed-list fields | SEC-1, SEC-2, AC-36 to AC-38 |
| Notice to the person | DPDP, baseline | employee line; the privacy-notice wording is open | AC-22, AC-48; ⚠ below |
| Keep logs at least one year (secondary source, unread Gazette) | DPDP Rules 2025 per 01c | ⚠ counsel: does it apply? | PRIV-4 |
| `compliance-feature-map.md` | **I did not reopen it for this draft.** Engineer and reviewer to check that no feature there already covers "refusal logging" beyond ALV-391 | – | – |

### 3 · Visibility delta

New: a direct manager can see ticked personal fields of an Active direct report. **Negative cases are the matrix in §8:** skip-level, HR-covered, colleague, other team, Left person, other company, guest see nothing new. Removed: four fields no longer reach managers' browsers.

### 4 · Decision automation

None. The system does not decide anything. A human manager reports; a human confirmer decides; the employee is told. No AI, no scoring, no surveillance.

### 5 · Retention and deletion

Notice kept as ToDo rows + one bell line, one copy, no purge job (PRIV-4, open). Whether deleting an Employee removes its ToDos is **not checked**. Version rows are not cleared by Log Settings (per 01c).

### 6 · Open compliance questions

| Question | Who decides | Blocks |
|---|---|---|
| Retention of the leaver notice; does a one-year floor apply | counsel via Surbhi | **release to main** |
| Does the privacy notice need a line that managers may see phone and address when ticked | counsel via Surbhi | main |
| Lawful basis wording for the notice | counsel | main |

### 7 · AI features

None.

### Prohibitions check

Nothing here needs AI-set ratings, emotion inference, passive monitoring or surveillance. A report is a human's explicit request, not inferred.

## 16 · Open for Surbhi (specced with the recommended default)

| # | Open item | Default I specced | If she says otherwise | Blocks |
|---|---|---|---|---|
| O-1 | OPS-11: cap on ToDos per report | **10**, refuse above it (AC-34) | change one number; refuse vs show count | nothing |
| O-2 | OPS-14 / ALV-433: stop sending personal email, company email and gender; phone and address only when ticked | **Yes** (AC-36 to AC-38). Specced as a P1 | if she wants gender or company email kept, AC-36 loses those keys | nothing |
| O-3 | OPS-17 / PRIV-4: retention of the notice | one copy, no purge | counsel's number | **release to main** |
| O-4 | Security Q1: write the Employee timeline comment? | **No** (AC-27); prototype row P-12 is not built | AC-27 swaps for a comment guard and a leak test; +2 points | build is unaffected; **P-12 needs her yes** |
| O-5 | 31-day / 60-day sentences for "before joining" | reuse the 31-day sentence | write a new sentence | nothing |
| O-6 | AC-9's second sentence for a different reporter | as written | – | nothing |
| O-7 | `current_address` only for "home address" (01c Q2) | yes | add `permanent_address`: one more tick and a PRIV-1 change | nothing |

## 17 · Assumptions

- `[ASSUMPTION]` One Custom Field on ToDo is the smallest marker (G1a).
- `[ASSUMPTION]` Frappe 16.33.1 in the shared bench matches dev and production (01c did not check).
- `[ASSUMPTION]` ToDo can be created without a share and without email by a direct insert (`[UNVERIFIED]`, AC-12, AC-26).
- `[ASSUMPTION]` The Scorecard JSON can drop the four fields without breaking any caller. **Engineer must grep every caller** of both methods (01c found no caller of `openEmpDrawer`).
- `[ASSUMPTION]` DTC's two Payroll team users already hold HR User (Surbhi's decision 1, read on production 22 Nov 2026); other tenants not counted.

## 18 · Traceability

| Source | ID or line | Story | AC | Status |
|---|---|---|---|---|
| Brief | Job: manager tells the confirmer from a phone, under a minute | US-1 | AC-1 to AC-5 | covered (the "under a minute" is a usability test, not an AC; **gap: no measurable AC**; see note) |
| Brief | Employee sees a plain line (idea D) | US-6 | AC-22 to AC-24 | covered |
| Brief | "Changed by your manager" (idea E, only if change ships) | US-11 | AC-48 | covered |
| Brief | Administrator two tag lists, empty by default (idea C) | US-8 | AC-28 to AC-35 | covered |
| Brief | Mini-profile reuse (idea F) | – | – | **not adopted by design:** v4 puts the fields on the Scorecard (Surbhi, round 3). The 078 mini profile is unchanged. Decision recorded in `01b` |
| Brief | Confirmer's to-do with who, last day, who reported, when (idea B) | US-3, US-4 | AC-10, AC-14 | covered |
| Brief | Success measures (days to confirm, share reported, etc.) | – | – | **gap: no AC.** They are measures, taken after release from the ToDo and Employee dates. Not built; no instrument is added (no login or page-view counting, per brief) |
| Brief | Not doing: reason box, notice period, undo, history, push, bulk, AI, new role, new DocType | – | AC-64 | covered (negative check) |
| Brief | Surbhi decision 1: role setting, default HR Manager | US-8 | AC-29, AC-32 | covered |
| Brief | Decision 2: ToDo per enabled holder | US-3 | AC-10, AC-11 | covered |
| Brief | Decision 3: phone and address see only, never change | US-9, US-8 | AC-31, AC-33, AC-44 | covered |
| Brief | Decision 4: retention open | – | – | **open, O-3**, blocks main |
| Brief | Decision 5: Reports To of leaver's reports decided by dry run | US-4, US-14 | AC-19, AC-56 | covered |
| Brief | Fallback: ship "see" only | US-10, US-11 | marked deferrable | covered; recommended (§3) |
| Brief | Risk: manager who is also HR cannot be the only confirmer | US-3 | AC-11 | covered (reporter excluded) |
| Brief | Risk: slow/rolled-back nightly slip job | US-14 | AC-56 | covered |
| 01b | 4.1 Team card, icon, sheet, sent, closed, confirmed (P-1 to P-6) | US-1, US-12 | AC-1 to AC-5, AC-17, AC-18, AC-49 | covered |
| 01b | 4.2 failure table (5 rows) | US-1, US-2 | AC-4, AC-6, AC-8, AC-9 | covered |
| 01b | 4.3 Desk ToDo, auto-close, decline | US-3, US-4 | AC-10, AC-14, AC-17 | covered |
| 01b | 4.3 timeline line | – | AC-27 | **not built (O-4); needs Surbhi's yes** |
| 01b | 4.4 Employee line, "Changed by" | US-6, US-11 | AC-22, AC-48 | covered |
| 01b | 4.5 Administrator card, both dialogs, role row | US-8 | AC-28 to AC-35 | covered |
| 01b | 4.6 Scorecard: icon, note, Personal details, Change | US-1, US-9, US-10, US-12 | AC-1, AC-40, AC-43, AC-50 | covered |
| 01b | §7 accessibility | all | AC-62 | covered |
| 01b | D3 bell line | US-4 | AC-17, AC-18 | covered |
| 01b | D4 31 / 60 days | US-2 | AC-8 | covered |
| 01b | D5 no button | US-6 | AC-22 | covered |
| 01b | §9 usability test | – | – | **not an AC; test plan only.** Needs a person, not code |
| 01b | Hindi strings | – | AC-61 | covered (tagging only; native review is not code) |
| Prototype v4 | every P-row in §6 | see §6 | see §6 | covered, P-12 excepted |
| SEC | SEC-1 | US-9 | AC-36, AC-37 | covered |
| SEC | SEC-2 | US-9 | AC-38, AC-40 | covered |
| SEC | SEC-3 | US-8 | AC-33 | covered |
| SEC | SEC-4 | US-10 | AC-42, AC-44, AC-46 | covered (deferrable) |
| SEC | SEC-5 | US-2, US-9 | AC-6, AC-7, AC-39 | covered |
| SEC | SEC-6 | US-1, US-2 | AC-3, AC-6 to AC-9 | covered |
| SEC | SEC-7 | US-3 | AC-11, AC-12 | covered |
| SEC | SEC-8 | US-8 | AC-32 | covered |
| SEC | SEC-9 | US-5 | AC-20, AC-21 | covered |
| SEC | SEC-10 | US-7, US-14 | AC-25, AC-58 | covered |
| SEC | SEC-11 | US-3 | AC-26 | covered |
| SEC | SEC-12 | US-13 | AC-53, AC-54 | covered |
| PRIV | PRIV-1 | US-8, US-9 | AC-29, AC-30, AC-33 | covered |
| PRIV | PRIV-2 | US-6, US-11 | AC-22 to AC-24, AC-48 | covered; ⚠ notice wording open |
| PRIV | PRIV-3 | US-12 | AC-51 | covered |
| PRIV | PRIV-4 | – | – | **open, O-3.** No test until counsel answers (01c says so) |
| OPS | OPS-1 (§1, = OPS-16) | US-14 | AC-56 | covered |
| OPS | OPS-2 (no new DocType) | – | AC-64 | covered |
| OPS | OPS-3 (role exists / fallback) | US-8 | AC-32 | covered |
| OPS | OPS-4 (no nginx change) | – | AC-64 | covered |
| OPS | OPS-5 | US-12 | AC-52 | covered |
| OPS | OPS-6 | US-12, US-14 | AC-57 | covered |
| OPS | OPS-7 | US-1 | AC-13 | covered |
| OPS | OPS-8 (read the served part after deploy) | US-14 | AC-57 | covered (release step) |
| OPS | OPS-9 | US-7 | AC-25 | covered |
| OPS | OPS-10 (3G measure) | – | AC-61 area | **gap: no AC.** Added to §12 as a "to be measured"; needs a built page. Recommend a release-time measurement, not an AC |
| OPS | OPS-11 | US-3, US-8 | AC-13, AC-34, AC-64 | covered; cap open (O-1) |
| OPS | OPS-12 | US-13, US-10 | AC-47, AC-55 | covered |
| OPS | OPS-13 | US-13 | AC-64 | covered |
| OPS | OPS-14 | US-9 | AC-36 to AC-38 | covered; open (O-2) |
| OPS | OPS-15 | US-14 | AC-57 | covered |
| OPS | OPS-16 | US-14 | AC-56 | covered |
| OPS | OPS-17 | US-14 | AC-59 | covered; retention open |
| OPS | OPS-18 | US-13, US-14 | AC-59, AC-63 | covered |
| OPS | OPS-19 | US-3 | AC-26 | covered |
| OPS | OPS-20 | US-3, US-8 | AC-32 and the "Nobody can confirm this yet. Ask HR." sentence (no separate AC; **add AC-9 sibling**, see note) | **gap: partly covered.** The refusal when no one can confirm at send time (SEC-7) has the sentence in §11 but no numbered AC. **Fix before build:** add the AC below |

**Gaps to fix before build, stated plainly:**
1. **Missing AC (OPS-20, SEC-7):** *Given* the set role has no qualifying holder at send time, *when* a manager reports, *then* the answer is "Nobody can confirm this yet. Ask HR.", no ToDo, Comment, DocShare or Notification Log row is written. I number it **AC-65**. Total ACs: **65**.
2. "Under a minute" (brief), the success measures, the usability test and the 3G measure (OPS-10) have **no AC**; each is a test with a person or a release-time measurement, not code. Surbhi to accept or require an AC.
3. Every row marked "covered" above names an AC, **not a written test**. No test file exists yet. The test-automation engineer will write them; until then these rows are a plan, not proof.

## 19 · Subtract pass

Removed from my own first draft: a per-story "dashboard of leavers", a "reminder after 2 days" ToDo, a separate state column on Employee, a bell line to the confirmer, and a "reason" field on declining. Moved to deferrable: US-10 and US-11 (7 points). Nothing else could go and still meet the approved design.

## 20 · Definition of Ready check

| Box | State |
|---|---|
| Brief: one persona, one outcome, JTBD, competitive analysis, Kano, enhancements, WOW, out-of-scope, approved | **Pass** (brief approved 22 Nov 2026; competitive claims are partly `[recall]`, labelled as such by the PM) |
| Design: clickable prototype reviewed | **Pass** (v4 approved 22 Nov 2026) |
| Design: Surbhi's feedback logged in `.claude/context/ux-learnings.md` | **Not checked by me** |
| Design: every state designed | **Partial**: Left-person after confirm, and the outcome bell line, are words only, not drawn |
| `01c` with SEC and PRIV | **Pass** |
| `07` §1-3 with OPS | **Pass** |
| Gap analysis from source | **Partial**: ToDo, `assign_to`, Notification Log, Employee-save hooks rest on 01c, not my own reading of Frappe/ERPNext source |
| Epic and stories, INVEST, sized, "must not" stories | **Pass** (14 stories, 51 points, 3 must-not) |
| Every story has an AC with an oracle | **Pass** |
| Traceability complete | **Fail, narrowly**: OPS-20 / SEC-7 needed AC-65 (added above); OPS-10, brief success measures, "under a minute" and the usability test have no AC (named as gaps, not hidden); PRIV-4 open |
| Permission matrix incl. negatives | **Pass** |
| Edge cases | **Pass** |
| NFR numbers | **Pass** (figures taken from 07; `nfr-budget.md` not reopened) |
| Migration/backfill | **Pass** ("nothing" and the one field) |
| Compliance sub-analysis | **Pass** |
| Every ⚠ names a human and what it blocks | **Pass** |
| No prohibited capability | **Pass** |
| Existing Frappe app installed | **n/a** |
| Open questions owned; none blocks day one | **Pass**: O-1 to O-7 all have a default; PRIV-4 blocks main only |

**Verdict: FAIL on the strict reading of the Ready list, by one box (traceability), with two partial boxes.** Not soft: the five items under "Gaps to fix before build" are named. The one that matters for correctness (AC-65) is already written here. The rest need Surbhi's decision (accept "no AC for a human test") or a reader to check ToDo / `assign_to` in Frappe source. **Per the rule "more than two boxes fail, the slice goes back" it is not triggered (one fail, two partial).** Build may start once Surbhi answers O-4 (the prototype row P-12) and accepts or rejects the five named gaps.

## Surbhi's spec decisions, 22 Nov 2026: all recommendations

1. **Defer the "change" half** (US-10, US-11, 7 points). Ship "see" only first, the fallback she approved at the brief.
2. **No Employee timeline comment** (P-12 is not built). Only the ToDo is created. She accepts this one difference from prototype v4.
3. **OPS-11:** at most 10 ToDos per report. A confirming role held by more enabled users than that is refused.
4. **OPS-14 / ALV-433:** the Scorecard, and `get_employee_detail_for_manager`, stop sending personal email, company email and gender. Phone and address are sent only when ticked in "Managers can see".
5. **The human-checked items are accepted** as release-time checks: the success measures, "under a minute", the usability test and OPS-10 timing. With this, the Definition of Ready passes.

Still open: PRIV-4 / OPS-17, retention of the notice. Counsel decides. It blocks main, not the build.
