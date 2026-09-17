---
slice: 009-ess-portal-redesign
artifact: appendix-d-growth-team-people
author: hrms-business-analyst (read-only review, run 2026-09-14)
date: 2026-09-14
status: ready
inputs: [prototype a78f9f44 (p3-data.js, p4-core.js, p7-growth-people-team.js), hrms-employee.html, performance_api.py, goals_api.py, kra_api.py, hr_api.py, alvoraa_goals, hrms/alvoraa_org_structure, ppj.localhost data]
---

# Appendix D — Growth, self-review, Team and People

Read-only review. Every query on `ppj.localhost` was a SELECT or read-only call as Rahul
or Sandeep, rolled back. Test scripts were kept in the session scratchpad, not the repo.

## The worst news first

1. **The self-review can change other people's records.** `submit_employee_review` (performance_api.py:3575-3597) takes KPI and goal names from employee-saved JSON and writes `self_rating` and `actual_progress` with `frappe.db.set_value`, never checking ownership. No Version history is written.
2. **Evidence approves itself.** `goal_api.submit_goal_evidence` (alvoraa_goals/api/goal_api.py:66) saves every row as "Approved" and updates progress at once; the page says "progress updated" (hrms-employee.html:9067). "Progress moves when evidence is approved" is not true today. Every evidence row in demo data is Approved.
3. **Evidence files are public** — `is_private=0` (hrms-employee.html:9084).
4. **Managers can read a self-review before it is sent** — `get_manager_review` (3649) and `get_appraisal_extension` (2310) have no stage check.
5. **Employees can read manager-only fields on their own review** — through the list API Rahul read `manager_internal_notes`, `potential_rating`, `overall_rating` (empty today). `get_my_appraisals` (3195) returns the overall rating before release.
6. **Org chart and reporting line disagree about Rahul's manager** — chart: Sandeep Gupta; `Employee.reports_to`: Sakshi Verma. Reviews, leave and approvals use `reports_to`.
7. **The current self-review wizard shows no goals page for Q2** — Q2 cycle `page_config = []`; code (14328-14353) builds only "Feedback for Reporting Manager" and "Summary & Submit".

## A. Requirement table

Personas: E employee, M manager, HR.

### Growth

| ID | What the person sees or does | Personas | Data needed | Existing source (verified) | Status | Work needed | Size | Risk / open question |
|---|---|---|---|---|---|---|---|---|
| G-01 | Cycle header: name, dates, "Day 73 of 92", days left, stage | E, M | Active cycle; own review status | `get_performance_context` :199; `get_my_appraisals` :3146 | partial | Client computes days; stage from own review status | S | Due date: cycle end or separate deadline? None enforced |
| G-02 | Start / Continue "step n of 5" / "Sent to Sakshi" | E | Status, steps done | `get_my_review` :3255 (`pages_completed`) | partial | A page counts done on any save, even empty (:3541); read creates a record (:3273) | S | — |
| G-03 | Goal cards: %, "28.4 of 39.7", pace per day | E, M | Goal fields, trajectory, unit | `hr_api.get_goals_portal_data` :1923 (5 queries); `goals_api.get_my_goals` :140 (10 for 2 goals) | exists | Client pace; use first endpoint | S | `unit` free text; chip from stored `trajectory` |
| G-04 | Evidence rows with status | E | Evidence + status | `get_goals_portal_data` (`validation_status`) | partial (never Pending) | Stop self-approval | M | Approver: manager (`can_validate_evidence`, evidence.py:99) or HR (:62)? |
| G-05 | Add evidence: type, from/to, amount, file, Send for approval | E | Type, range, value, private file | `submit_goal_evidence_portal` :2008 → `goal_api.submit_goal_evidence` | partial | Pending status, notify manager, private file; types differ; no "to" date | M | New "covers to" field or note? |
| G-06 | "Progress moves when evidence is approved" | E, M | One progress model | Three models: Goal Evidence, Goal Progress Update (`submit_goal_update` :977 moves progress before approval :1000-1006), KPI Progress Log | missing | Choose one source of truth and one approval rule | M–L | Product decision |
| G-07 | Give / Ask feedback, optional value; received feedback | E, M | Feedback record (from, to, text, value, mode, visibility) | None fits: Upward Feedback (`submit_upward_feedback` :908) is manager-only with 0–5 rating; HRMS Employee Performance Feedback tied to appraisal (403 rows) | missing (received card is sample) | New model or extend Employee Performance Feedback | L | Build vs extend; visibility rules |
| G-08 | Manager sees upward feedback about themselves | M | Aggregate + comments | `get_upward_feedback_received` :2810 (hides detail below 3) | exists (unused) | Client | S | Unused `goals_api.get_upward_feedback` :942 has no minimum — remove |
| G-09 | "What your manager will see" | E | Honest list | Static copy | partial | Copy, or server work | S/M | False today (B6, B7) |
| G-10 | "Still open from last time" | E, M | Open action items | `get_appraisal_extension` :2310 (one appraisal); `add_action_item` :2527; `update_action_item_status` :2550 (unused) | partial (sample) | "My open action items" query, and per report | M | 2 items in demo; employee closes only if assigned |
| G-11 | 5-point scale with labels | E, M | Scale items | Rating Scale "PPJ 5-Point" matches; `get_rating_scales` :1491 | exists | `get_my_review` omits scale; current input is 1–5 number box, 0.5 steps (:14760) | S | Whole or half steps? |
| G-12 | Values and principles in the review | E | Values | `get_company_values` :2644 (5); `get_leadership_principles` :2755 (3, manager-oriented); HRMS template "PPJ Standard" rates 7 criteria via `self_ratings` | partial | Current wizard hard-codes 7 generic principles (15326-15334) | M | Two sources of truth |

### Self-review wizard

| ID | What | Personas | Existing source | Status | Work | Size | Risk |
|---|---|---|---|---|---|---|---|
| SR-01 | Five steps, guidance, step rail | E | Cycle-driven pages (:14313) | partial | New fixed 5-step UI, or HR sets `page_config` | M | Q2 setup empty |
| SR-02 | Rate each goal 1–5 + note | E | KPI `self_rating`/`self_comment`; goal reflection only in JSON (:14519) | partial | JSON (no schema change) or field | S–M | Rahul has 11 Q2 KPIs (6 linked). Goals or KPIs? |
| SR-03 | Pick up to 2 values + example | E | Nothing stores chosen values; HRMS rates all 7 | missing | New JSON key + client | S | Conflicts with HRMS criteria / Q1 data |
| SR-04 | Went well / would do differently | E | `achievements_text`, `challenges_text` (copied on submit :3601) | exists | Client | S | "Differently" ≠ "challenges" |
| SR-05 | One thing to get better at + what would help | E | `development_needs_text`, `support_needed`; HRMS Skill (9); Designation Skill empty | partial | Options from Skill / Designation Skill | S–M | Prototype options invented |
| SR-06 | Check and send; empty-answer list | E | `submit_employee_review` :3554 | partial | Notify manager; fix ownership (B4); stage and deadline check | M | — |
| SR-07 | "Saved at HH:MM" | E | `save_review_page` :3521 on page change/Next only | partial | Debounced save; server-confirmed time | S | See B |
| SR-08 | "Your self-review is with Sakshi" | E | Status → Manager Review | exists | Client | S | Name from `reports_to` |

### Team (manager page)

| ID | What | Personas | Existing source (verified) | Status | Work | Size | Risk |
|---|---|---|---|---|---|---|---|
| TM-01 | Stats: reports, in now, still to come, waiting on you | M | `get_manager_dashboard` :267 (7 queries); "today" from Attendance (0 today; last 9 Sep) | partial | "In now" from Checkin + shift + leave | M | HR roles also get everyone with no manager (:282) |
| TM-02 | Waiting on you with approve/decline | M | Leave by `leave_approver`; corrections `to_review` :707 (Sandeep cannot: `_may_review` False); evidence broken (F1) | partial | One approvals list shared with Inbox | L | Same list as Inbox |
| TM-03 | Needs attention (Q2 < 75%) | M | No rule; 75% invented (p5 :62) | missing | Rule | S | Use trajectory; new joiners |
| TM-04 | Late this week | M | `get_team_late_list` :2473 (31 queries for 19) | exists | Batch | S–M | First person's rule used for all (:2482) |
| TM-05 | On leave this month | M | `month_leaves` :351 | partial | Fix date overlap | S | Misses leave begun last month; includes future months |
| TM-06 | New this month | M | None | missing | `date_of_joining` filter | S | 3 joiners 1 Sep |
| TM-07 | Team cards: today chip, Q2 % bar | M | `get_team_scorecard` :876 mixes cycles (Kabir 50%); `get_team_goals` :785 (22 queries) | partial | One batched query per cycle | M | Karigars have no sales goal |
| TM-08 | Tap person → profile / 1:1 / feedback | M | `get_employee_scorecard` :691 or `get_employee_detail_for_manager` :978; notes :2279 / :2332 | exists / partial | Pick one profile endpoint | M | Returns `personal_email`, `cell_number`, `gender` to manager |
| TM-09 | Direct vs all reports | M | Direct: dashboard, scorecard, notes, `_reports_of`. Any level: `_is_manager_of` :3739, `_subordinates` | inconsistent | One rule | M | Product decision |

### People (directory)

| ID | What | Personas | Existing source (verified) | Status | Work | Size | Risk |
|---|---|---|---|---|---|---|---|
| PE-01 | You and your manager | E, M | `org_structure.api.my_view` :392 (31 queries) | partial | Manager from `reports_to` | S | Chart vs reports_to mismatch |
| PE-02 | Your team ("also reporting to Sakshi") | E | `my_view.peers` = same position (11) | partial / wrong meaning | Peers by `reports_to` | S | Sakshi has 13 reports; prototype shows 8, says 9 |
| PE-03 | Manager: your team with today chips | M | `my_view.team` = 4 positions, 32 people (reports_to 19) | partial | = TM-01 | M | — |
| PE-04 | New this month | E, M | None | missing | Server | S | — |
| PE-05 | Leadership / other floors | E, M | No flag; `subtree` :686 limited to 2 levels | missing | Server + definition | M | Product decision |
| PE-06 | Search by name or role | E, M | `search_people` :547 name only | partial | Add designation | S | No company filter |
| PE-07 | Person sheet incl. contact "when they choose" | E, M | `_card` name, designation, department, branch, image; no consent field | partial / missing | Consent field | M | Privacy decision |
| PE-08 | Org-health numbers | HR | `metrics.org_health` :39 HR only | exists, called for everyone (F3) | Client | S | — |

## B. Self-review wizard mapped onto the existing review model

**Mostly a new screen on existing endpoints**, but needs server fixes first: ownership hole, stage check on manager reads, manager notification, somewhere to store chosen values.

| Step | Prototype field | Endpoint | Where it lands |
|---|---|---|---|
| Load | Everything | `get_my_review(appraisal)` :3255 | Goals, KPIs, JSON, done pages, status (no scale, no values) |
| 1 Goals | `{goal}_rating`, `{goal}_note` | `save_review_page(key="past-objectives")` | JSON `objectives[goal].reflection`; KPI `self_rating`/`self_comment` if KPIs rated. Goal-level rating stays in JSON |
| 2 Values | `values[]` (≤2), `values_note` | `save_review_page(key="company-values")` (new key) | JSON only; alternative HRMS `self_ratings` (all 7) |
| 3 Went well | `well`, `improve` | `save_review_page(key="past-dev")` or `save_self_review_narrative` :2351 | `achievements_text`, `challenges_text` |
| 4 Next quarter | `next_skill`, `next_help` | `save_review_page(key="past-dev" / "future-dev")` | `development_needs_text` + `support_needed`, or `next_period_goals_text` |
| 5 Check and send | — | `submit_employee_review(overall_comment)` | Status → Manager Review. **No notification** (`advance_review_status` :2437 notifies; this does not) |

Status flow: Not Started → Employee Review (first save) → Manager Review → Employee Final Review → HR Review → Completed; return paths `return_for_revision`, `return_to_manager`.

**Remove from the new UI and restrict server-side:** editing `actual_progress` in the review (:14686); adding/removing goals (`set_review_selection` :3452 uses `db.set_value`); duplicate overall comment.

**Autosave:** each `save_review_page` ≈ 8–10 queries plus a Version row (change tracking on). Save after 3–5 s idle, at most every 15 s, plus on step change, blur and page hide; skip unchanged. `page_data` is Text (~64 KB) — not tested with long answers.

## C. Permission and privacy rules

| Data | Employee | Manager | HR | Must not see |
|---|---|---|---|---|
| Own draft self-review | Read/write until sent | **Not until sent** (today can, B7) | HR Review/Completed only (`_assert_hr_can_view` :48; skipped in manager-review endpoints) | Peers |
| Overall and potential rating | After release only (today leaks, B6) | Yes | Yes | Peers; employee before release |
| `manager_internal_notes` | **Never** (readable today via list API) | Yes | Yes | Employee |
| Manager 1:1 notes (Comment on Employee) | Could not check (no notes) | Author only | Anyone who reads the Employee in desk | Employee (unverified) |
| Invited reviewer | Allowed pages only (today whole JSON, :3895) | | | |
| Upward feedback | Own given | Totals, 3+ responses | All | Who wrote it |
| Evidence files | Own | Direct reports | All | Public links (B3) |
| Directory card | Name, designation, department, branch, photo | + today status, personal email, phone, gender (scorecard) | All | Leave reason, absence type |
| Org structure | 2 levels up/down (`reach`) | Whole org (`alvoraa_org_managers_see_all` = 1) | All | `my_view(employee=any)`, `chain_to_top(node=any)` skip reach (B11) |

Row protection on the extension, Upward Feedback and Goal Check-In relies on each employee's User Permission — tenant setup, not code.

## D. Speed and scale (measured as Sandeep, Rahul)

| Call | Queries | At 400+ employees |
|---|---|---|
| `goals_api.get_pending_approvals` | **706** | HR ≈ 37 per employee → **~15,000**, will time out |
| `goals_api.get_my_goals(include_team=1)` | 138 | Grows with every goal |
| `get_team_late_list` | 31 | Loops per person |
| `my_view` | 31 | Walks tree step by step |
| `get_team_goals` | 22 | Loops per person |
| `get_my_appraisals` | 19 | LIKE on Text column |
| `get_manager_dashboard` / `get_team_scorecard` | 7 / 7 | OK |
| `get_week_presence` | 5 | Capped at 40 |

Team page today: 4 calls; redesign as drawn ~6–7. **Recommendation:** one Team call, batched, ≤ 15 queries whatever the team size. Growth: 3–4 calls, fine once `get_my_goals` stops per-goal queries. Directory "Everyone" needs paging; no listing endpoint exists.

## E. Bugs found

**F1 — still broken, worse than reported:** `hr_api.get_pending_approvals` :2036 ImportError; `approve_kpi_progress`/`reject_kpi_progress` (:2056-2064) import missing functions; page expects `{goals:[{evidence:{idx}}], kpis:[{log:{idx}}]}` (8417) but the working `goals_api` function has a different shape and model — cannot simply be re-pointed.

**F2 — still broken, with a second bug:** now at hrms-employee.html:9798, builds `alvoraa_portal.performance_api.kra_api.get_my_kras`. Behind it, `get_my_kras` passes the whole employee record to `_employee_template`, so no template is ever found (Rahul has "PPJ Standard" but got `template: null`). Any caller can pass another `employee` id.

**F3 — still broken:** `metrics.org_health` at 5157 from `ocStats`, run on every chart move (5121); 403 on each Up/Top/Back/search for non-HR.

| # | Bug | Evidence |
|---|---|---|
| B1 | `goals_api.get_checkins` 500; `create_checkin` drops % and outlook | "Unknown column 'completion_pct'"; Goal Check-In has only `progress_value`, `note` |
| B2 | Evidence approves itself | goal_api.py:66; child `before_insert` hook doesn't run on parent save (inferred) |
| B3 | Evidence files public | 9084 |
| B4 | Self-review writes records the employee does not own | performance_api.py:3575-3597 |
| B5 | Future goals created with invalid status "Not Started"; error swallowed | :3631-3634 (not run — writes) |
| B6 | Rating leaks before release; manager-only fields via list API | :3195; checked as Rahul |
| B7 | Manager reads draft self-review | :3649, :2310 |
| B8 | Reviewer view returns all pages; creates record before permission check | :3889-3895 |
| B9 | HR guard skipped in manager-review endpoints | :3649, :3754, :3976 |
| B10 | Direct vs any-level report checks mixed | `_reports_of` vs `_is_manager_of` |
| B11 | `my_view`, `chain_to_top` skip reach | Rahul got Sandeep Sodhi's full view up to Owner |
| B12 | Org chart manager ≠ `reports_to` | Sandeep Gupta vs Sakshi Verma; `reporting_mismatches` exists for HR |
| B13 | Wizard hard-codes generic principles | 15326 |
| B14 | Q2 wizard has no goals page | `page_config = []` + 14350 |
| B15 | "Saved `<i class=ic-check></i>`" shows raw markup | 14485, 15447, 14404 |
| B16 | Scorecard goal % mixes cycles | hr_api.py:913-930 |
| B17 | `get_team_reviews` without cycle picks arbitrary appraisal | :721 (Kabir showed Q1 rating) |
| B18 | "In now" never counts today; month leave filter wrong | hr_api.py:314, :351 |
| B19 | Non-manager presence = first 40 of department across stores, viewer's holiday list | Rahul's list included Noida staff |
| B20 | Late list uses first person's rule for all | :2482 |
| B21 | Unescaped goal and employee names in goal drawer — a script could be planted in a goal name | 8742-8745 |
| B22 | Unused upward feedback endpoint has no response minimum | goals_api.py:942 |
| B23 | Debug popups and Error Log writes in evidence hook | evidence.py:11-26, :64-77 |
| B24 | Goal update moves progress before approval; reject does not undo | goals_api.py:1000-1071 |
| B25 | No manager notification on self-review send | performance_api.py:3554 |
| B26 | Notification helper pushes `eval_js` script to the browser | :3121 |
| B27 | `save_forward_planning` has no stage check | :2374 |
| B28 | `goals_api`, `performance_api` not behind "goals" plan check; `hr_api` goal endpoints are | e.g. hr_api.py:1922 vs goals_api.py |

## F. Dependencies

- **Approvals** (TM-02, G-04, G-05, F1) = the Inbox list; build one approvals service first (leave, attendance correction, evidence, goal updates, KPI updates). Manager corrections need a new rule.
- **Today status** (TM-01, PE-03) = Home presence = Time check-in; one "today" function.
- **Global search** reuses `search_people` + designation (after scoping fix).
- **Person sheet** shared by Team, People, search, Inbox — one profile endpoint.
- **Feedback sheet** shared by Growth, Team, People — depends on G-07.
- **Notifications** depend on Inbox; review mail uses `frappe.sendmail` today.
- **Manager name everywhere** depends on fixing B12 in data or choosing one source.

## G. Open questions

| Question | Blocks |
|---|---|
| Which is the manager: `reports_to` or position chart? (HR must fix mismatch) | People, Team, review routing |
| Who approves evidence; progress only after approval? | G-04..G-06 |
| Values: pick 2 + example, or rate all 7 criteria? Master: Company Value or Employee Feedback Criteria? | SR-03, G-12 |
| Rate goals or KPIs; whole or half points? | SR-02 |
| Self-review due date and lock? | G-01, SR-06 |
| Peer feedback: new record type or extend? Visibility? "Ask" in scope? | G-07 |
| Manager sees draft before send? (Recommend no) | B7, G-09 |
| Team scope: direct or everyone below? | TM-09, B10 |
| Needs-attention rule; new joiners on full-quarter targets? | TM-03 |
| What "Leadership" means | PE-05 |
| Colleagues see work phone/email? Opt-in field? | PE-07 |
| Managers see personal email, phone, gender? | TM-08 |
| Skill list source | SR-05 |

**Could not check:** browser rendering; mail/realtime delivery; employee access to 1:1 notes; the child-row hook skip (inferred); response times at 400+ (estimated); B5 and anything that writes. Privacy points are flags for the security engineer, not legal rulings.

## Open questions / Assumptions / Handoff note

- **Open questions:** section G (owner: product owner; privacy items also security engineer).
- **Assumptions:** [ASSUMPTION] query counts from single runs as Sandeep and Rahul.
- **Handoff note:** B4, B2/B3, B6–B9, B11 and B21 are live security and privacy holes that exist today, independent of the redesign. They should not wait for Wave 4.
