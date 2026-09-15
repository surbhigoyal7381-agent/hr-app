---
slice: 010-portal-security-fixes
artifact: 01d-security-privacy-group-d
author: hrms-security-privacy-engineer
date: 2026-09-15
status: draft
inputs: [00c-review-copies-decisions.md (R1-R16, wins over 00b), 00b-review-copies-analysis.md (§4 VIS-1..VIS-15, §2 screen inventory), 01c-security-privacy-requirements.md (SEC-1..SEC-17, PRIV-1..PRIV-8), 03-implementation-notes.md §10, 00-impact-analysis.md (shared helpers in hrms/hrms/alvoraa_hr_core/access.py), .claude/context/security-compliance-baseline.md (entries of 24 Aug 2026 and 6 Sep 2026), .claude/context/compliance-feature-map.md, .claude/context/nfr-budget.md, .claude/context/parallel-work.md, .claude/context/handoff-contract.md, code at slice/010-portal-security-fixes = origin/dev c27fb56 + docs commit e58ffa2 (line numbers are at c27fb56), read-only checks on hrlocal-bench sites ppj.localhost and test_site, rolled back]
---

# 010 group D — Review copies and review access: security and privacy requirements

## The short answer

**Group D is not only "hide the copies". Four things are broken today, before any copy exists.**

1. **The employee can already see their own potential rating.** It sits on the live `KPI`
   record, which the Employee role can read. On ppj, Rahul (PPJ-0058) can list his own 12
   KPIs through the normal list API. 6 of them carry a potential rating and a manager
   rating. 601 potential ratings sit on Q2 KPIs while 403 Q2 reviews are still open.
   `get_my_kpis` returns the same fields. This breaks the user's rule "potential rating
   never", and it is on `main`.
2. **Any logged-in employee can move every goal and KPI in the tenant into another
   cycle.** `attach_ongoing_to_cycle` is a public endpoint with no role check. It uses
   `ignore_permissions` and `frappe.db.set_value`. On `main`.
3. **People who hold an HR role can finish their own review.** On ppj, 11 open reviews
   belong to people holding HR Manager, HR User or System Manager. `advance_review_status`
   (HR Review → Completed), `submit_appraisal` and `sync_appraisal_from_kpis` pass on the
   role alone. On `main`.
4. **Ratings show on screens outside the review.** Scorecards, "My KPIs", the HRMS
   appraisal summary and the "My reviews" list return ratings or scores at any stage.
   Decision R14 says outside screens show no rating at all.

**The copy design is the right shape, but only if the lock lives in the document layer.**
A lock placed only in the portal endpoints is bypassed by the desk, the REST API, and by
three portal functions that write with `frappe.db.set_value`. One more
(`set_goal_progress`) saves with `ignore_validate`, which skips Frappe's `validate` step.

**This file sets:** 15 `VIS` rules (none dropped: 6 adopted as written, 2 adopted with an added clause,
7 amended), 8 re-stated group D
items from `01c`, **13 new `SEC` items (SEC-18 to SEC-30)** and **7 new `PRIV` items
(PRIV-9 to PRIV-15)**. Each has a test that refuses the bad case.

**Two decisions change what `01c` said:**
- **SEC-2 is tighter.** `01c` let a manager write a rating on the live KPI. Under R13
  nobody writes ratings on the live KPI any more, so the rule is now "nobody, whatever
  the path".
- **SEC-5 is not enough on its own.** HR still reads the whole Extension, drafts and
  copies included, through the desk at any stage. The portal's stage rule does not
  apply there. SEC-27 closes it, or the product owner accepts it in writing (Q-D3).

The baseline entries I rely on were verified on 24 Aug 2026 and 6 Sep 2026. That is
under 90 days, so none is stale. I am not a lawyer. Where an answer turns on the law,
there is a question for counsel in section 7.

---

## 1 · Threat model in four lines

1. **Who wants this data, and what is the cheapest way in?** Insiders with a valid
   session. An employee who wants a better score edits the numbers or definitions that
   feed it, through the desk, REST, or a public endpoint called from the browser. A
   manager who wants to hide a bad quarter removes the item from the review. An HR-role
   holder who is also a subject rates or closes their own review. A curious colleague,
   or an invited reviewer, reads ratings through a screen that was never meant to show
   them.
2. **Blast radius of one mistake.** One review for most paths. **The whole tenant** for
   `attach_ongoing_to_cycle` (every live record re-tagged), for any tenant setting that
   unfreezes reviews, and for a write-back bug that overwrites live definitions at cycle
   close. No path here crosses tenants: each tenant is its own database.
3. **What does this make possible that was impossible before?** A second, frozen record
   of every rated item. That is good for fairness and for grievances, and it is a **new
   store of decision-bearing personal data** that needs a delete rule, a retention answer
   and a legal-hold answer. It also adds four new decisions to guard: freeze, removal,
   rating-stamp answers, and write-back to live records.
4. **How would we find out?** **Today, we would not.** KPI has no change history
   (`track_changes = 0`; 0 Version rows for KPI on ppj). `frappe.db.set_value` writes
   leave no trace. Refusals are now logged (SEC-17), but a successful self-rating, a
   removal or a write-back would not be. Group D must write an audit entry for every
   freeze, removal, stamp answer and write-back (SEC-21, SEC-23, SEC-24, SEC-25).

---

## 2 · Data inventory

Classes are from the baseline and feature map A1: `public / internal / sensitive /
statutory-id`. **No code applies these classes today** (see `01c` §2). They are a
declaration, and each requirement below says what enforces them.

### 2.1 The new copy table

Name as in `00b` §5 M2: child DocType **`Alvoraa Review Item`** on `Alvoraa Appraisal
Extension`. The engineer may rename it; the rules follow the table, not the name.

| Field or group | Class | Purpose | Retention | Who may see it (details in §3) |
|---|---|---|---|---|
| `item_kind`, `parent_item`, `added_in_review` | internal | Review structure | Decision record (see 2.3) | Everyone who may open that review |
| `source_doctype`, `source_name` (link to the live record) | internal | Fact routing, lock check, write-back | Decision record | **Server only.** Never in any response (VIS-3) |
| Wording: `label`, `description`, `unit`, `direction`, `category`, `progress_mode` | internal (may hold commercial detail in the goal name) | What was reviewed | Decision record | Everyone who may open that review |
| Definition numbers: `target_value`, `baseline_value`, `weightage`, `period_start`, `period_end` | sensitive (feeds the rating) | What was reviewed | Decision record | Same |
| Definition changes agreed in the review, waiting for write-back (R15) | sensitive | Carry the agreed change to the live record | Until write-back, then kept in the audit entry | Same |
| Result numbers: `actual_value`, `attainment_pct` / `progress_pct`, count of facts used | sensitive (feeds the rating) | Score | Decision record | Same |
| `self_rating`, `self_comment` | sensitive | Self-review | Decision record | Subject always. Manager line, HR and allowed invited reviewers **only after sending** (PRIV-2) |
| `manager_rating`, `manager_comment` | sensitive, decision-bearing | Manager review | Decision record | Manager line and HR. Subject from Employee Final Review [proposed, Q-D1] |
| `potential_rating`, `potential_comment` | sensitive, decision-bearing | Talent calibration | Decision record | Manager line and HR. **Never the subject** (user decision) |
| Additional or invited reviewer ratings per item | sensitive, decision-bearing | 360 input | Decision record | Manager line and HR. Each reviewer sees their own entry only |
| **Rating stamp** (R7): the numbers the rating was given on, rater, time | sensitive, decision-bearing | Proves what the rater saw | Decision record | **Same people as the rating it belongs to** (PRIV-13) |
| **Stamp flag** and its answer (keep / change, by whom, when) | sensitive, decision-bearing | Makes a rater face changed numbers | Decision record | The rater, manager line, HR. Not the subject, not invited reviewers |
| `frozen`, `frozen_on`, freeze point used | internal (audit) | Proves when the numbers were fixed | Decision record | Everyone who may open that review |
| **"Arrived after this review closed"** flag and the late value (R10) | sensitive | Tell HR about late data without changing the score | Decision record | **HR only** (PRIV-11) |
| **Removal record** (keep mode, R12): removed by, on, reason | sensitive, decision-bearing (the reason is a judgement about performance) | Show what was taken out and why | Decision record | Manager line and HR. Subject: Q-D5 |
| Snapshot of a removed item (keep mode) | sensitive, decision-bearing | Same | Decision record | Same as the removal record |

### 2.2 Other records group D creates or changes

| Record | Class | Purpose | Retention | Who may see it |
|---|---|---|---|---|
| **Write-back audit entry** (R15): live record, field, old value, new value, review, who agreed, when | sensitive, decision-bearing (feature map E6) | Prove the goalposts moved openly | Decision record, and **longer than the live record** | HR, System Manager. Manager line of the subject through the review |
| **Removal audit entry**, also in discard mode | sensitive, decision-bearing | Prove a removal happened, even when the copy is gone | Decision record | HR, System Manager |
| Extension: stamped review window, freeze point and removal mode for this review (SEC-21) | internal | Stop settings changes rewriting a live review | Decision record | HR; shown read-only in the review |
| "In a review" badge on the live record (R5) | internal | Tell editors the definition is locked | Life of the lock | Anyone who may see the live record. **Nothing else about the review** (PRIV-10) |
| **Tenant settings**: freeze point (R6), lock release days (R9), removal behaviour (R12) | internal, no personal data | Organisation policy | Life of tenant; every change kept in history | Read: anyone (HR Settings already gives Employee read). Write: HR Manager, System Manager (SEC-28) |
| Security log lines from new refusals | internal (names only) | Detection (SEC-17) | 180 days, **in France today, so CERT-In residency is still unmet** (baseline §3a) | System Manager on the bench |

### 2.3 What retention, erasure and legal hold mean for copies

- **A review copy is the record of a decision about a person** (R13: "the frozen copy is
  the record of that review"). Treat it as decision-bearing, like the rating itself.
- **There is no retention engine and no legal hold in the product** (feature map A6 is
  missing; nothing in the repo purges these doctypes). So the only safe rule today is:
  **no role can delete a copy, a removal record or a write-back audit entry through the
  desk, REST, or by deleting the parent** (PRIV-14). A future purge job, with legal hold,
  is the only allowed delete path, and it does not exist yet.
- **Erasure requests** under DPDP do not become "delete the copy rows". They go to HR and
  counsel, because the baseline (§6, "erasure vs defensibility") says counsel signs the
  boundary. Question C-D1.
- **R12's default "discard the copy"** is a deletion inside a live review. Before anyone
  has rated the item, nothing decision-bearing is lost. **After a rating exists, discard
  destroys evidence** that could defend or challenge that rating. SEC-24 proposes that a
  rated copy is always kept marked "Removed", whatever the setting. That is my
  recommendation, not a decision (Q-D4, C-D2).
- **Live records after the lock is released** (R9) are still the source of later reviews.
  They are not decision records for the finished review; the copy is.

### 2.4 Obligations engaged

I am not a lawyer. These are engineering requirements taken from the baseline.

| Obligation | What it asks of group D | Baseline section, verified |
|---|---|---|
| DPDP Act 2023 + Rules 2025: reasonable security safeguards, access control | Server-side, fail-closed checks on every copy read and write; no rating leaks (SEC-1..30, PRIV-9) | §2, 24 Aug 2026 |
| DPDP: purpose limitation, minimisation | Potential rating kept from the subject; ratings not spread to outside screens (PRIV-1, PRIV-9, PRIV-10) | §2, 24 Aug 2026 |
| DPDP erasure vs a rating that must stay defensible | Copies are decision records; no delete path; counsel signs the boundary (PRIV-14, C-D1) | §2 and §6, 24 Aug 2026 |
| GDPR Art 22 (anticipatory until the founder confirms EU exposure): a named human decides; the person can contest | Rating stamps name the rater; nobody rates their own review; removals carry a named person and reason (SEC-10, SEC-23, SEC-24) | §4, 24 Aug 2026 |
| ISO/IEC 27001:2022: segregation of duties, logging | SEC-10, SEC-23, SEC-25, PRIV-15 | §5, 24 Aug 2026 |
| CERT-In: logs 180 days in India | New refusal and audit logs exist; residency gap unchanged (not this slice) | §3a, 6 Sep 2026 |
| Feature map E6 (locked definitions, definition-change audit), D6 (period freeze), E1 (rating replayable from stored inputs), E5 (change log), B7 (segregation of duties), A6 (retention with legal hold), I1 (permission tests in CI) | R2, R6, R7, R15 are these features. Group D should build them so they can be shown to a reviewer: SEC-19, SEC-21, SEC-24, SEC-25, PRIV-14 | feature map, 24 Aug 2026 |

---

## 3 · Access intent, including who must NOT see what

Words used:
- **Copy** = a review item row. **Original** = the live `KPI` or `Individual Goal`.
- **Stages:** ER = Not Started / Employee Review (also after "return for revision"),
  MR = Manager Review, EFR = Employee Final Review, HRR = HR Review, C = Completed.
- **Manager line** keeps the rule each endpoint uses today (`01c` Q11 still open: direct
  manager for rating and advancing, whole line for reading).
- **HR** = HR Manager or HR User acting for a subject in `permitted_companies()` who is
  not in their own line.

### 3.1 By persona

| Persona | May see and do | Must NOT see or do |
|---|---|---|
| **Employee (subject)** | ER: their copies, their own self fields, add or remove items (R12), definition changes inside the review. From MR: copies read-only. From EFR: overall rating, manager feedback, and item manager ratings [proposed, Q-D1]. Outside the review: originals, with the "in a review" badge, and log facts on them (R3) | The originals **inside** the review. Their own potential rating or comment, anywhere, ever (item, Extension average, category). Manager internal notes, calibration notes, rating stamps and flags, late-arrival flags. Any rating on any outside screen (R14). Edit a copy after sending. Change an original's definition while it is held, by any path. Remove an item after ER |
| **Manager line** | MR: copies, the sent self fields, rate, potential, answer their own stamp flags, invite reviewers, remove items with a reason (R12). EFR, HRR, C: read the review | Anything in the review while it is in ER (PRIV-2), including which items the employee added or removed. Their **own** review's manager fields. Ratings on outside screens (R14). Late-arrival flags (HR only, R10). Change an original's definition while held. Answer a stamp flag on a rating they did not give |
| **Invited reviewer** | MR only: the pages allowed for them in that one review. Copies only if `past-objectives` is allowed. Their own comments and ratings | Any other page. Manager ratings, potential, overall rating, internal notes, stamps, flags, other reviewers' entries, removal records. Anything after MR [proposed, Q-D6]. Any other review |
| **HR Manager / HR User** | HRR and C for subjects in their permitted companies: everything in the review, including stamps, flags, late-arrival flags, removal records and write-back audit. Remove items with a reason before C. Send HRR → C when no stamp flag is open. Cycle screens (R8) built from copies | A stranger's review **before HRR**, through the portal, the desk, REST or the cycle screens (today the desk and three cycle screens let them). Subjects in companies they are not permitted. Their **own** review as a decider: rating, calibrating, answering flags, removing items, completing it. Editing any copy after C |
| **System Manager / CXO** | Same as HR, across the companies they are permitted | **Same limits as HR.** Today `_assert_hr_can_view` lets System Manager read any draft at any stage (`performance_api.py:68-69`). Fail closed: the stage rule applies to them too [proposed, Q-D7]. No exemption from separation of duties |
| **Dotted-line manager** (hrms `dotted_line.py`, Employee Performance Feedback) | Their own feedback record, as built | Copies, ratings or stamps through that path. Not changed by group D; listed as a worry (§6) |
| **Login with no Employee record** | Nothing | Every review endpoint refuses (as `01c`) |

### 3.2 By object and stage

"—" means refused or absent from the response. "HR" means HR as defined above.

| Object | ER | MR | EFR | HRR | C |
|---|---|---|---|---|---|
| Copies: definition and result numbers | Subject | Subject, line, allowed reviewer | Subject, line | Subject, line, HR | Same, read-only for all |
| Copies: self fields | Subject | + line, allowed reviewer | + line | + HR | Same, read-only |
| Copies: manager rating and comment | — | Line | Line, subject [Q-D1] | + HR | Same, read-only |
| Copies: potential | — | Line | Line | Line, HR | Line, HR. **Never subject** |
| Rating stamps and flags | — | Line (the rater answers) | Line | Line, HR | Line, HR. Never subject, never reviewer |
| Late-arrival flag (R10) | — | — | — | HR | HR |
| Removal record (keep mode) | Subject's own removals: subject | Line | Line, subject [Q-D5] | + HR | Same |
| Originals | **Outside only.** Never returned by a review endpoint | same | same | same | same |
| Items that arrived after the review closed | never inside the copy | | | | |

**After "return for revision"** the review is back in ER: line and HR lose access to the
self fields again until it is re-sent (`01c` PRIV-2 assumption, still open as `01c` Q5).

**Overlapping reviews (R16):** an original can have copies in two reviews. Each copy
follows its own review's rules. Seeing one review never grants access to the other.

---

## 4 · Requirements

Rules for every item, as in `01c` §6:
- **Enforcement is on the server.** A hidden button does not count.
- **Fail closed:** any doubt (unknown stage, missing setting, unknown row, no Employee
  record, company not permitted) → refuse with `frappe.PermissionError`, write nothing,
  and log through `hrms.alvoraa_hr_core.access.refuse` (SEC-17).
- **One mechanism per rule.** The copy helper (`00b` §5, `review_items.py`), the
  review-field filter (`01c` handoff item 3), the decision guard (`access.py`), and one
  new **lock guard** on the two DocTypes.
- **Tests** live in `alvoraa_portal/alvoraa_portal/tests/`, because CI runs only
  `alvoraa_goals` and `alvoraa_portal` (`01c` SEC-15). `VIS` tests go in
  `test_review_copies.py`. `SEC` and `PRIV` tests go in `test_portal_security_010.py`.
  Each test builds its own synthetic employees, manager, HR user, cycle and items, in the
  style of `test_appraisal_visibility.py`. Never real people's data.

### 4.1 Visibility rules from `00b`, under R1–R16

| ID | Verdict | Rule (one sentence) | Server enforcement point | Fail closed | Automated test (persona → action → expected; negative case) |
|---|---|---|---|---|---|
| **VIS-1** | **Adopt, amended** | No outside endpoint (00b O1–O14) and no desk or REST read of `KPI` or `Individual Goal` returns a copy **or any rating** (the rating half is PRIV-9). | Structural: copies live only on the Extension. PRIV-9 for ratings | n/a (structural) | Employee, manager, HR each call `get_performance_tree`, `get_my_kpis`, `get_team_kpis`, `goals_api.get_my_goals`, `hr_api.get_goals_portal_data`, `get_employee_scorecard`, `get_team_scorecard` after a snapshot → no response string equals a copy row name; row counts equal originals. Static: `Alvoraa Review Item` / `review_items` appears only in the allowed review functions |
| **VIS-2** | **Adopt** (depends on SEC-5 and SEC-27) | Copies are readable only through review endpoints; no Employee-role user reaches them through `/api/resource`, `frappe.client` or report view, and HR reaches them through the desk only when the stage rule allows. | DocType JSON (SEC-5); `has_permission` + `permission_query_conditions` for the Extension (SEC-27); child DocType has no permissions of its own (`istable`) | No Extension read → no child read | Employee, then manager: `frappe.client.get("Alvoraa Appraisal Extension", own/report's)` and `frappe.get_list("Alvoraa Review Item", parent_doctype="Alvoraa Appraisal Extension")` → `PermissionError`. HR User outside the line, subject in MR → `frappe.client.get` refused. **Negative:** HR, subject in HRR → succeeds |
| **VIS-3** | **Amend** | Every review endpoint returns copies only, addressed by copy row name; no response holds an original's name, and every review write accepts copy row names only. `source_name` never leaves the server (00b's "if D-2 allows" is dropped). | The copy helper's payload builder (`review_payload`) and every review write | An unknown or foreign row name → refuse the whole call | Subject `get_my_review`, manager `get_manager_review`, reviewer `get_reviewer_view`, manager `get_cycle_items` and `get_team_appraisal` → a recursive string scan of the JSON finds no `KPI` or `Individual Goal` name. **Negative:** subject calls the self-rating write with an original KPI name → refused, original unchanged |
| **VIS-4** | **Amend** | A copy is created once per (review, original) when the appraisal is generated or when the item is added inside the review; a second attempt changes nothing; an original may have copies in two different reviews (R16). | Copy helper, called from `hr_generate_appraisals` and the add path; unique check on (parent, `source_name`) | Duplicate → no-op, logged | HR runs `hr_generate_appraisals` twice → copy count unchanged. Two reviews overlapping in time (Q1 still open, Q2 generated) → the original has exactly one copy in each |
| **VIS-5** | **Amend** (R2, R11, R12) | The add/remove dialog may list originals; adding creates a copy, removing follows SEC-24, and neither ever changes the original's `appraisal_cycle`; the subject may add or remove only in ER, the manager line and HR may remove later with a reason, and nobody adds after ER until Q-D8 is answered. | `get_available_for_review`, `set_review_selection` (both rewritten on copies) | Stage unknown → refuse. After ER, an add → refuse | Subject in ER adds → copy created, original's `appraisal_cycle` unchanged. Subject in MR calls `set_review_selection` → refused, copies unchanged. Manager in MR removes without reason → refused; with reason → SEC-24 outcome. HR User outside line in MR → refused (stage rule) |
| **VIS-6** | **Adopt** (R13) | Every rating and comment made in a review is saved on the copy, and no rating field on an original changes. | Copy helper `save_item_rating`; SEC-2 guard on KPI | Any write to an original rating field → refused | Subject self-rates 4, manager rates 3 → copy holds 4 and 3; original `self_rating` and `manager_rating` unchanged |
| **VIS-7** | **Adopt** | Scoring (`_scored_items`, `_apply_kpis_to_appraisal`, `sync_appraisal_from_kpis`, `submit_appraisal`, `suggest_ratings`, `_sync_potential_to_extension`) reads copies only. | Those functions | A review with no copies → refuse to score, never fall back to originals | Manager rates copies, then admin sets the original's `actual_value` and `manager_rating` directly, then `sync_appraisal_from_kpis` → `Appraisal.goals` scores match the copies |
| **VIS-8** | **Amend** (R2, R3, R4, R6, R11) | Facts are stored on the original; a fact dated inside the review window reaches the copy until that review freezes, counted by the item's `progress_mode`; the original's definition is locked while held (SEC-19); a pre-existing item cannot be deleted while held. | Fact routing in the copy helper (SEC-21); lock guard (SEC-19) | Fact with no date → does not reach any copy, and shows to HR as "undated" (Q-D9) | Subject in ER logs progress dated in the window → original and copy change. Same after freeze → original changes, copy does not. Fact dated one day after window end → copy unchanged. `delete_kpi` on a held pre-existing original → refused, both exist. Item added inside the review → its original may be deleted (R11) |
| **VIS-9** | **Amend** | "Return for revision" never unfreezes a frozen copy and never refreshes it by hand; the "Refresh numbers" button in 00b is dropped, because under R3 numbers flow by date until the freeze. | Copy helper; `return_for_revision` | Frozen stays frozen | Freeze point set to "self-review sent"; employee sends; manager returns → copies still frozen; a fact dated in the window logged afterwards does not reach the copy. With the default freeze point (HR sent) → the copy still receives it |
| **VIS-10** | **Adopt** | When a review is Completed its copies, stamps, flags and removal records are read-only for everyone, HR and System Manager included, and are shown only to people who may open that review. | Copy helper writes; `save_calibration_note`, `save_overall_rating`; lock on the Extension's child rows in `validate` of the Extension | Any write on a Completed review → refuse | HR calls `save_item_rating`, `save_calibration_note(calibrated_rating=5)` and a desk save of a copy row on a Completed review → refused, values unchanged |
| **VIS-11** | **Amend** | Nothing done to an original after a review closes changes that review's copies or score, and while an open review holds an original, generation of a later cycle adds a copy in the new review instead of moving the original (R16). | `attach_ongoing_to_cycle`, `hr_generate_appraisals` (SEC-20) | Held original → never re-tagged | After C, HR edits the original's target and runs `hr_generate_appraisals(next)` → the finished review's copies and `Appraisal.goals` unchanged. Original held by an open Q1 review → Q2 generation leaves its `appraisal_cycle` alone and creates a Q2 copy |
| **VIS-12** | **Adopt** (R8) | Desk lists of `KPI` and `Individual Goal` show originals only, labelled "Live records, not the review record". | Structural; list view label in the DocType list settings | n/a | HR Manager desk `get_list("KPI")` count unchanged after 5 snapshots. Static check for the label text |
| **VIS-13** | **Amend** (R8) | HR KPI list, cycle summary, CSV export and calibration read copies, and apply SEC-26 (company scope and stage rule). | `hr_list_kpis`, `hr_cycle_summary`, `export_cycle_kpis_csv`, `get_calibration_overview`, `get_calibration_matrix` | Unknown stage → row counted, ratings left out | See SEC-26 |
| **VIS-14** | **Adopt** | An original not selected for a review has no copy and appears only outside. | Copy helper | n/a | Unselected original → no copy; present in `get_my_kpis` |
| **VIS-15** | **Adopt, amended** | Objectives created from the wizard's "Future Objectives" page are originals, not copies, created through `doc.insert` with the subject as employee, never tagged into the current review. | `submit_employee_review` | A failed insert refuses the submission (no `except: pass`) | Subject sends with one future objective → a new `Individual Goal` exists, not in the current review's copies, and its `appraisal_cycle` is not the current cycle |

**None dropped.** 6 adopted as written (VIS-2, VIS-6, VIS-7, VIS-10, VIS-12, VIS-14),
2 adopted with an added clause (VIS-1, VIS-15), 7 amended (VIS-3, VIS-4, VIS-5, VIS-8,
VIS-9, VIS-11, VIS-13).

### 4.2 Group D items from `01c`, re-stated against the copy design

**SEC-1 · The self-review writes only this review's copies. (S1)** — *amended*
- *Rule:* `save_review_page`, `submit_employee_review` and the self-rating dialog write
  self fields only to copy rows whose `parent` is this appraisal's Extension, only in ER,
  and only when the caller is the subject. They never write `KPI` or `Individual Goal`,
  and never write `actual_progress`. `save_kpi_self_review` (writes the original today,
  `performance_api.py:444-458`, no stage check) is removed or redirected to the copy.
- *Enforcement:* copy helper `save_item_rating(as_role="self")`, called by all three.
- *Fail closed:* one row name that is not a copy of this review refuses the whole save or
  submission. Status stays ER. No exception is swallowed (today `:3594`, `:3604`).
- *Test:* Subject A saves page data naming colleague B's copy row and B's original KPI,
  then submits → `PermissionError`; B's copy and original unchanged; A still in ER.
  **Negative:** A names an original goal's `actual_progress` → refused, value unchanged.
  **Positive:** A self-rates own copy → saved; a Version row exists on the Extension.
  A calls `save_kpi_self_review` on own original → refused or copy-only.

**SEC-2 · Nobody writes rating fields on an original, whatever the path. (F-18)** — *amended; stricter than `01c`*
- *Rule:* after group D ships, `self_rating`, `self_comment`, `manager_rating`,
  `manager_comment`, `potential_rating`, `potential_comment` on `KPI`, and the rating
  fields of `KPI Additional Reviewer`, cannot change by portal, desk, REST or import. The
  only exception is the backfill patch, running as Administrator with an explicit flag.
- *Enforcement:* a `before_validate` doc event on KPI (runs even when a caller sets
  `flags.ignore_validate`, checked in Frappe `document.py:1403-1408`), plus a static test
  that no code calls `frappe.db.set_value("KPI", …)` with those fields.
- *Fail closed:* yes, for every role.
- *Test:* Employee who created their own KPI, manager, HR Manager and System Manager each
  call `frappe.client.set_value("KPI", k, "manager_rating", 5)` → refused, value unchanged.
  A save with `flags.ignore_validate = True` changing `potential_rating` → refused.
  **Negative:** saving a KPI's `actual_value` (a fact) still works.

**SEC-5 · No Employee-role DocPerm on the Extension, and tenants that re-grant it are reported. (S3, F-1, M3)** — *adopted, extended*
- *Rule:* as `01c`. The copy child DocType inherits it. The deploy runs a read-only check
  listing any tenant whose Custom DocPerm on `Alvoraa Appraisal Extension` grants
  Employee (or any non-HR role) read, write or create. It removes nothing.
- *Checked 2026-09-15:* ppj.localhost and test_site have **no** Custom DocPerm on the
  Extension. On ppj, Rahul still has read **and write** on his own Completed review
  (`has_permission` True, rolled back). Dev tenants were not checked (no access, and not
  needed before deploy).
- *Test:* as `01c` SEC-5, plus `frappe.get_list("Alvoraa Review Item",
  parent_doctype="Alvoraa Appraisal Extension")` as an employee → refused. A unit test
  feeds the M3 check a fake Custom DocPerm row and asserts it is reported, not deleted.

**SEC-6 · Manager-review endpoints check relationship, stage and the HR guard before
touching or creating anything. (S4)** — *adopted, extended to copies*
- *Rule:* as `01c`, for `get_manager_review`, `save_manager_review`,
  `submit_manager_review`, `save_overall_rating`, `invite_reviewer`,
  `invite_reviewers_batch`, `add_action_item`, `return_for_revision`,
  `advance_review_status`, `update_action_item_status`, **and** every copy read or write a
  manager or HR can call (item rating, remove, stamp answer, definition change). Today
  `get_manager_review` has no stage check (`:3657-3668`) and creates the Extension before
  deciding (`:3668`).
- *Fail closed:* no Extension and caller not allowed → refuse, create nothing.
- *Test:* as `01c` SEC-6, plus: manager calls the copy rating write while the review is in
  ER → refused; Extension and copy counts unchanged after an unauthorised call.

**SEC-7 · An invited reviewer sees only allowed pages of one review, during Manager
Review, and invitees come from the subject's company. (S4c, F-12, F-13)** — *amended*
- *Rule:* `get_reviewer_view` and `submit_reviewer_comments` check the invitation before any
  read, never create an Extension (today `:3897`, `:3954`), and cut `page_data` to
  `allowed_pages`. **Copies are returned only if `past-objectives` is allowed** (today the
  goal list is returned whatever the pages, `:3906-3912`, `:3936`), and never with
  manager ratings, potential, stamps, flags, removal records or other reviewers' entries.
  Access ends when the review leaves MR [proposed, Q-D6]. Invitees must be active
  employees of the subject's company, not the subject.
- *Fail closed:* empty `allowed_pages` → no pages and no copies.
- *Test:* non-invited employee → refused, Extension count unchanged. Invited with
  `["past-dev"]` → `page_data` keys exactly `{"past-dev"}`, no copies. Invited with
  `["past-objectives"]` → copies present, and a key scan finds no `manager_rating`,
  `potential_rating`, stamp or flag keys. Review moved to EFR → reviewer refused.
  Manager invites an employee of another company → refused.

**SEC-10 · Nobody decides anything in their own review. (F-2)** — *amended, wider*
- *Rule:* the subject cannot, whatever roles they hold: rate or comment as manager on any
  copy; set potential; `save_manager_review`, `submit_manager_review`, `save_overall_rating`,
  `save_calibration_note`; rate as an additional or invited reviewer; answer a stamp flag;
  remove an item after ER; approve a definition change for write-back; `sync_appraisal_from_kpis`,
  `submit_appraisal`, `suggest_ratings`; `return_for_revision`; or move their own review
  forward from MR or from HRR to Completed.
- *Enforcement:* one guard in `access.py` (extend `refuse_own_decision` or add
  `refuse_own_review`), called from each path. `advance_review_status` today checks only
  `_require_hr()` for HRR → C (`:2431-2432`); `submit_appraisal` passes on
  `_require_can_review`, which returns early for any HR role (`:133-136`).
- *Data:* on ppj, **11 open reviews** belong to people holding HR Manager, HR User or System
  Manager.
- *Test:* HR Manager with own review in MR, then in HRR, calls each endpoint above →
  `PermissionError`, nothing changed. A second HR Manager → succeeds. The existing
  `test_a_manager_who_is_also_hr_can_still_do_a_manager_review` still passes.

**PRIV-1 · One field filter decides what each viewer receives, and the subject never
receives potential. (S3)** — *amended*
- *Rule:* the review-field filter (relationship × stage → allowed keys) covers Extension
  fields **and** copy fields, stamps, flags and removal records, as in §3.2. For the
  subject: potential (item, `potential_rating`, `avg_potential_rating`,
  `potential_category`), `manager_internal_notes`, `calibration_notes`, stamps, flags and
  late-arrival flags are **never** returned. Overall rating and manager feedback from EFR
  (user decision). Every endpoint serialises through it: `get_my_appraisals` (today
  returns `overall_rating` at any stage, `:3203`), `get_appraisal_extension` (today releases
  it only at C, `:2347-2349`, and returns potential to the subject, `:2340-2341`),
  `get_employee_final_review` (**today returns `potential_rating` and `potential_category`
  to the subject, `:4094-4095`**), `get_my_review`, `get_manager_review`,
  `get_team_reviews` and the calibration screens when the viewer is the subject.
- *Fail closed:* unknown stage → narrowest set.
- *Test:* parameterised over every stage × each endpoint: as subject, the forbidden keys are
  **absent**, not just empty. As the manager, present. HR Manager who is the subject calls
  `get_team_reviews`, `get_calibration_overview`, `get_calibration_matrix` → their own row
  has no potential keys.

**PRIV-2 · Nobody but the subject sees a self-review, or the copy set, before it is
sent. (S4, decision Q-d)** — *amended to copies*
- *Rule:* as `01c`, plus: in ER, nobody but the subject receives copies at all (which items
  were added or removed is part of the draft), nor copy self fields. After return for
  revision, hidden again until re-sent (`01c` Q5, still an assumption).
- *Enforcement:* the PRIV-1 filter inside `review_payload`, so every review reader inherits it.
- *Test:* manager `get_manager_review` in ER → refused. HR outside line, desk read in ER →
  refused (SEC-27). HR `export_cycle_kpis_csv` in ER → no self rating or comment for that
  subject (SEC-26). Employee sends → manager receives them. Manager returns → hidden again.

### 4.3 New security requirements

**SEC-18 · The reviewer picker finds active employees of the subject's company only,
not limited to the manager's line. (decision 2)**
- *Rule:* `performance_api.search_employees` takes the appraisal (or subject) it is picking
  for, checks the caller may invite for that review (SEC-6), and returns active employees of
  the subject's company, excluding the subject. Fields: id, name, designation, department.
  Limit ≤ 50. Today it returns up to 100 active employees from every company to any
  logged-in user (`:1466-1493`).
- *Fail closed:* no appraisal given, or caller may not invite → empty list or refusal.
- *Test:* on test_site with two companies: manager of a Company A subject searches a name
  that matches A and B employees → only A. An employee with no invite right calls it →
  refused. The subject never appears. The invite endpoints refuse a B employee even if
  the picker is bypassed (SEC-7).

**SEC-19 · While a review holds an original, its definition cannot change by any path.
(R2, R11, feature map E6)**
- *Rule:* for an original with a copy in an open review, before the lock release date
  (SEC-22), these fields cannot change: KPI `kpi_name`, `target_value`, `weightage`,
  `period_start`, `period_end`, `appraisal_cycle`; Individual Goal `goal_name`,
  `target_value`, `weightage`, `start_date`, `end_date`, `appraisal_cycle`. Also
  `progress_mode`, `direction`, `baseline_value`, `unit` and the parent link
  (`individual_goal` / `parent_goal`), because they change how the copy counts or where
  it sits [proposed, Q-D10]. A pre-existing held original cannot be deleted.
- *Enforcement:* a lock guard hung on `before_validate` (not `validate`, which
  `set_goal_progress` skips with `flags.ignore_validate`, `goals_api.py:687`, `:693`) and
  `on_trash` doc events for both DocTypes. That covers the portal (`save_kpi`,
  `hr_save_kpi`, `relink_kpi`, `delete_kpi`, `update_goal`, `delete_goal`), the desk, REST
  and import. A static test fails if any code writes those fields with
  `frappe.db.set_value` or `frappe.db.sql` (today: `attach_ongoing_to_cycle` `:956`,
  `:968`; `set_cycle_membership` `:996`, `:999`; `set_review_selection` `:3498-3522`).
  The lookup "is it held?" needs an index on the copy's `source_name` (`00b` §9).
- *Fail closed:* cannot tell whether it is held (lookup error) → refuse. No role is exempt.
- *Test:* employee who created their own KPI, held in an open review → REST
  `PUT /api/resource/KPI/<name>` changing `target_value` → refused; `delete_kpi` → refused.
  HR Manager `hr_save_kpi` changing `weightage` → refused. Desk save with
  `flags.ignore_validate` changing `target_value` → refused. **Negative:** logging a
  progress fact on the same original → succeeds. An item added inside the review → its
  original can be deleted. After the release date → the edit succeeds and the copy is
  unchanged.

**SEC-20 · No code moves or re-tags a held original, and only HR may pull work into a
cycle. (F-D1)**
- *Rule:* `attach_ongoing_to_cycle` requires HR (today any logged-in user,
  `:915-973`), is scoped to `permitted_companies()`, and skips held originals.
  `set_cycle_membership` refuses a held original. `set_review_selection` never touches
  `appraisal_cycle` (VIS-5).
- *Fail closed:* yes.
- *Test:* plain employee calls `attach_ongoing_to_cycle(cycle)` → `PermissionError`, zero
  records re-tagged (count `appraisal_cycle` before and after). HR permitted Company A →
  Company B records untouched. Held original → `set_cycle_membership(include=0)` refused.

**SEC-21 · Each review stamps its own window, freeze point and removal mode when it
opens; facts are routed by date; freezing is one-way. (R3, R4, R6, R16, feature map D6)**
- *Rule:* when a review's copies are first created, the Extension records the review window
  (start and end), the freeze point and the removal mode in force. Later changes to tenant
  settings or to the cycle's `page_settings` (`past-objectives.period_from/to`, read today
  at `:3411-3413`) do not change an open review. A fact reaches a copy only if its date is
  inside that review's window and the review is not frozen. With overlapping reviews (R16)
  each fact reaches at most one review's copy. Freezing writes `frozen_on` and an audit
  entry. No endpoint unfreezes.
- *Dates:* progress logs by `log_date`; evidence by `extracted_date`. On ppj all 381 KPI
  progress logs have `log_date` and all 996 evidence rows have `extracted_date` (checked).
  A fact without a date goes nowhere and is shown to HR (Q-D9).
- *Fail closed:* missing or unknown stamped freeze point → treat as frozen at the earliest
  point (no new facts reach the copy) and alert HR.
- *Test:* HR changes the freeze point from "HR sent" to "self-review sent" while a review is
  in MR → that review keeps flowing facts; a new review uses the new point. HR edits
  `past-objectives.period_to` after the review opens → a fact dated after the original
  window still does not reach the copy. Q1 open (window to 30 Jun) and Q2 open (from 1 Jul):
  a fact dated 30 Jun reaches Q1's copy only; 1 Jul reaches Q2's only.

**SEC-22 · The lock releases on the server's date, and releasing it never touches a
copy. (R9)**
- *Rule:* the lock ends at cycle end date + the stamped lock release days; 0 means never.
  The date is taken from the server, not from the caller. Release changes nothing on the
  copies. Reminders to HR from day 15 carry no names of subjects, only the cycle and a count.
- *Fail closed:* setting missing or not a whole number ≥ 0 → treat as never released.
- *Test:* freeze the clock at end + 29 → edit refused; end + 30 → allowed; setting 0 →
  refused at end + 400. A client-supplied date is ignored. Reminder email body contains no
  employee name (PRIV-15).

**SEC-23 · Rating stamps are written by the server, and HR cannot send while a flag is
open. (R7, feature map E1)**
- *Rule:* every rating write stores, from the copy's numbers at that moment, the values
  rated on, the rater and the time. The server, never the client, raises a flag when those
  numbers change afterwards. Only the person who gave that rating can answer it (or their
  replacement manager, Q-D11), never the subject. HRR → C is refused while any flag is open.
  Each answer writes an audit entry.
- *Fail closed:* stamp missing on a rating → treated as an open flag.
- *Test:* manager rates at actual 80; a fact moves the copy to 90 → flag open; HR calls
  `advance_review_status` HRR → C → refused. The subject answers the flag → refused. HR
  answers someone else's flag → refused. The rater keeps the rating → flag closed, audit
  entry written, HR send succeeds. Client posts its own stamp values → ignored.

**SEC-24 · Removing an item is a named, reasoned, audited act, and a rated copy is never
silently discarded. (R11, R12)**
- *Rule:* the subject may remove only in ER. The manager line or HR may remove in MR, EFR or
  HRR, with a non-empty reason. The server refuses a removal call without an explicit
  acknowledgement that in-review changes will be lost (the UI warning is not enough on its
  own). Every removal writes an audit entry (who, when, reason, copy row name, whether any
  rating existed), **also in discard mode**. If the copy carries any manager, potential,
  reviewer rating or stamp, it is kept and marked "Removed by … on …" whatever the
  setting [proposed, Q-D4]. Nobody removes after C. The original keeps its facts.
- *Fail closed:* unknown removal mode → keep mode.
- *Test:* subject removes in MR → refused. Manager removes in MR without reason → refused;
  without acknowledgement → refused. Discard mode, unrated copy → row gone, audit entry
  exists. Discard mode, manager-rated copy → row kept and marked, audit entry exists. HR
  removes on a Completed review → refused. Manager removes from their own review → refused
  (SEC-10).

**SEC-25 · Definition changes are written back once, at completion, without overwriting
someone else's change, with an audit entry. (R15, feature map E6)**
- *Rule:* on HRR → C, for each copy with an agreed definition change, the server compares
  the original's current value with the value the copy started from. If they match, it
  writes the new value through `doc.save` and writes an audit entry (live record, field,
  old, new, review, who agreed, when). If they differ (someone changed the original after
  the lock released), it does not write that field, and it tells HR. It runs once: a
  second completion attempt writes nothing. Ratings are never written back (R13). KPI has
  no change history today (`track_changes = 0`), so the audit entry is required, not
  optional.
- *Fail closed:* any error → no field of that original written; the review still completes
  and HR sees what was not written.
- *Test:* agreed target 100 → 120, original untouched → original 120, one audit entry.
  HR changed the original to 110 after release → original stays 110, HR sees the conflict,
  no audit "write" entry. Completion run twice → one audit entry. After write-back the
  original's `manager_rating` is unchanged.

**SEC-26 · HR cycle screens obey company scope and the stage rule. (R8, VIS-13)**
- *Rule:* `hr_list_kpis`, `hr_cycle_summary`, `export_cycle_kpis_csv`,
  `get_calibration_overview`, `get_calibration_matrix` return only subjects in
  `permitted_companies()`. For subjects before HRR (and not in the caller's own line), they
  return status and counts but **no** self, manager or potential rating, comment, overall
  rating or score. The caller's own row never includes potential. Each CSV export writes one
  security log line (user, cycle, row count; no values). Today all five return every company,
  and `get_calibration_overview` and the CSV return ratings, self comments and potential at
  any stage (`:2704-2753`, `:2884-2947`).
- *Fail closed:* unknown stage → no ratings for that row.
- *Test:* HR User permitted Company A → no Company B rows in any of the five. Subject in MR →
  CSV row has empty rating and comment columns; `get_calibration_overview` row has no
  `overall_rating`, `avg_potential_rating`. Subject in HRR → present. HR Manager who is a
  subject → own row has no potential. Export → one log line without values.

**SEC-27 · HR's desk and REST access to the Extension follows the same stage and company
rule as the portal. (F-D6)**
- *Rule:* add `has_permission` and `permission_query_conditions` hooks for `Alvoraa Appraisal
  Extension` (and so its copy rows): HR Manager and HR User may read a subject's Extension
  only if the subject is in `permitted_companies()` and the review is in HRR or C, or the
  subject is in their own line, or it is their own. System Manager: same rule [proposed,
  Q-D7]. Write in the desk: refused for everyone below Administrator; all review writes go
  through the portal endpoints and their guards.
- *Fail closed:* no Extension row visible; unknown stage → not visible.
- *Test:* HR User, stranger's review in ER → `frappe.client.get` refused, `get_list` excludes
  it, the desk form does not open. Same subject in HRR → allowed. HR User in Company A, B
  subject in HRR → refused. HR Manager `frappe.client.set_value(ext, "overall_rating", 5)` →
  refused. If the product owner rejects this rule, record the decision and replace the test
  with one that pins the accepted behaviour.

**SEC-28 · The three review settings live in one audited place and are validated.
(R6, R9, R12)**
- *Rule:* store freeze point, lock release days and removal behaviour as fields on
  **HR Settings** (Single DocType, `track_changes = 1`, HR Manager and System Manager write;
  checked in its JSON). Not in Global Defaults: `hr_api.set_org_setting` lets an HR Manager
  write **any** Global Default key with no history (`hr_api.py:2206-2210`, `01c` F-15).
  Select fields with fixed options; days a whole number ≥ 0.
- *Fail closed:* a value outside the options → save refused; a missing value at read time →
  the default (HR sent, 30, discard-but-SEC-24).
- *Test:* HR User saves HR Settings → refused. HR Manager sets freeze point "anything" →
  refused. HR Manager changes a setting → a Version row exists. `set_org_setting` with the
  setting's key → no effect on the review settings.

**SEC-29 · A reviewer's rating is written only to their own entry, on the copy. (F-D4)**
- *Rule:* additional-reviewer and invited-reviewer ratings are stored per copy and per
  reviewer. The server picks the entry from the caller's Employee, not from a row name the
  client sends. Today `save_additional_reviewer_rating` takes any `row_name`, so one
  reviewer can overwrite another's rating on the same KPI (`:2623-2642`), and HR passes as
  anyone (`:2588-2589`). 0 such rows on ppj.
- *Fail closed:* caller has no entry → refuse.
- *Test:* reviewer X sends reviewer Y's entry id → refused, Y unchanged. X rates → only X's
  entry changes. Subject tries to add themselves as reviewer → refused.

**SEC-30 · The calibration sign-off is read by HR only. (F-D5)**
- *Rule:* `get_calibration_signoff` requires an HR role (today no check at all,
  `:4177-4190`); `save_calibration_signoff` refuses a cycle containing the caller's own open
  review from being signed by them [proposed].
- *Fail closed:* yes.
- *Test:* plain employee calls `get_calibration_signoff(cycle)` → `PermissionError`. HR →
  returns. 1 sign-off row exists on ppj; I did not read its text.

### 4.4 New privacy requirements

**PRIV-9 · No rating or score appears outside a review. (R14, F-D2, F-D3)**
- *Rule:* no outside endpoint returns a self, manager, potential or reviewer rating or
  comment, an overall rating, or an appraisal score, for any persona. That covers:
  `get_my_kpis`, `get_team_kpis` (via `KPI_FIELDS`, `:243-250`), `get_cycle_items`
  (`manager_rating`, `:1038`), `hr_api.get_employee_scorecard` and `get_team_scorecard`
  (`overall_rating` and `total_score`, `hr_api.py:836-853`, `:949-982`), `get_my_appraisal`,
  `get_appraisal`, `get_team_appraisal` and `goals_api.get_appraisal_data` (`Appraisal.goals`
  scores, `total_score`, `final_score`, `:496-520`, `goals_api.py:726-767`). A rating is
  shown only inside the review, to someone allowed to open it, at the stage allowed (§3.2).
  **At the DocType layer:** KPI rating fields move to permlevel 1, readable by HR Manager,
  HR User and System Manager only, so the desk, REST, report and print stop returning them
  to employees and managers. Legacy values are **not deleted** (they are decision
  records; PRIV-14).
- *Why now:* on ppj Rahul reads 6 potential ratings on his own KPIs through `get_list`;
  2,356 KPIs carry a potential rating, 601 of them in Q2 with reviews open.
- *Also:* HRMS `Appraisal` ships with Employee read/write/create and no row rule in our code.
  ppj is protected only by its own Custom DocPerm (System Manager only). On a tenant with the
  shipped permissions the subject reads `Appraisal.goals` scores through REST at any stage.
  Q-D12 decides whether our fork changes that JSON or the release rule covers it.
- *Fail closed:* an outside endpoint that cannot prove the review is released → no rating.
- *Test:* on test_site (shipped permissions), subject in MR with copies rated → each endpoint
  above, recursive key scan finds none of the rating or score keys (or they are null).
  Subject `frappe.get_list("KPI", fields=["potential_rating"])` → field absent or refused.
  Manager desk read of a report's KPI → no rating fields. HR Manager → present. Static
  test: `KPI_FIELDS` contains no rating field.

**PRIV-10 · The "in a review" badge reveals nothing else. (R5)**
- *Rule:* the badge on an original says only that it is in a review and that later-dated
  updates do not change it. It carries no review name, stage, rating, reviewer, freeze date
  or removal state to anyone who may not open that review.
- *Test:* a colleague in the manager line of a peer (sees the original, cannot open the
  review) → badge payload keys are exactly the allowed ones (for example
  `{"in_review": 1}`).

**PRIV-11 · "Arrived after this review closed" is for HR only, and never changes a score
by itself. (R10)**
- *Rule:* a fact dated inside a frozen review's window that arrives later is recorded
  against that review as a flag with its value, visible to HR in HRR and C only. It never
  appears in subject, manager, reviewer or outside payloads, and the copy and score do not
  change.
- *Test:* after freeze, log a fact dated inside the window → HR sees the flag; subject's
  `get_my_review`, manager's `get_manager_review`, reviewer's view → no flag keys; copy and
  `Appraisal.goals` unchanged.

**PRIV-12 · Removed items are visible to the right people, and the subject finds out.
(R12)**
- *Rule:* in keep mode, a removed copy and its reason are shown to the manager line and HR,
  marked "Removed by … on …". The subject is told an item was removed, with its label and
  date, no later than EFR; whether they also see the reason is Q-D5. Notifications say only
  that an item was removed and link to the portal: no reason text, no numbers, no ratings.
  Invited reviewers never see removal records.
- *Fail closed:* until Q-D5 is answered, the subject sees label and date, not the reason.
- *Test:* manager removes with reason "x-reason" in MR → subject in EFR sees the item label
  and date, and a string scan finds no "x-reason"; manager and HR see it; the Email Queue
  message contains neither the reason nor any number.

**PRIV-13 · Rating stamps and flags follow the visibility of the rating they belong to.
(R7)**
- *Rule:* a stamp or flag is returned only to someone who may see that rating at that stage
  (§3.2). The subject never receives stamps or flags [proposed, Q-D1]. Invited reviewers
  never do.
- *Test:* subject in EFR → item manager rating present [if Q-D1 = yes], stamp and flag keys
  absent. Reviewer → absent. Manager and HR in HRR → present.

**PRIV-14 · Copies are decision records: no role can delete them, and erasure is routed,
not executed. (feature map A6, baseline §6)**
- *Rule:* no desk, REST or code path deletes a copy, a removal record, a stamp or a
  write-back audit entry, except discard-mode removal of an unrated copy in an open review
  (SEC-24). Deleting an Extension that has copies is refused (`on_trash`), for System
  Manager too. Deleting or cancelling the linked `Appraisal` leaves the Extension and copies
  in place. No purge job is built in this slice. An erasure request for a subject is routed
  to HR and counsel (C-D1).
- *Fail closed:* yes.
- *Test:* System Manager `frappe.delete_doc("Alvoraa Appraisal Extension", ext)` with copies →
  refused. HR User deletes the draft `Appraisal` → the Extension and copies still exist (or
  the delete is refused: pick one in the strategy and pin it). A desk save that drops a
  rated copy row from the table → refused.

**PRIV-15 · Group D code puts no personal or performance values in logs, audit titles or
notifications. (baseline §6, `01c` PRIV-8)**
- *Rule:* security log lines, error logs, audit entry titles, and emails from freeze, stamp
  flag, removal, write-back and lock reminders carry document and row names, counts and
  stages only. No item labels, targets, actuals, ratings, comments or reasons. Audit entry
  bodies may hold old and new values, because they are HR-only decision records.
- *Test:* trigger each event with a unique marker in the label, reason and comment → no Error
  Log, security log line or Email Queue message contains the marker.

---

## 5 · Abuse cases specific to the copy design

"Today" means the path exists at `c27fb56` and I read the lines. "Design" means it becomes
possible only once copies exist, and the requirement stops it.

| # | Actor, state, path, result | Today or design | Stopped by |
|---|---|---|---|
| **AB-1** | **Editing a copy after freeze.** Subject's review frozen (freeze point "self-review sent"). The subject, or the manager, sends a save of a copy row's `actual_value` through a review endpoint, a desk save of the Extension, or `frappe.client.set_value` on the child row. The score changes after the numbers were fixed | Design (today there is no copy; the equivalent is `save_kpi_self_review` with no stage check, `:444-458`) | VIS-9, VIS-10, SEC-21, SEC-27 |
| **AB-2** | **Changing an original's definition during a review.** An employee who created their own goal (1 on ppj) calls `PUT /api/resource/Individual Goal/<name>` with a lower `target_value`; `has_employee_permission` allows write to the creator (`permissions.py:140-160`). Or HR uses `hr_save_kpi` (`:2079-2091`). Or code uses `set_goal_progress`, which saves with `ignore_validate` (`goals_api.py:687`). Outside screens and the next cycle show the lowered target; write-back later conflicts | Today (no lock exists) | SEC-19 (hook on `before_validate`, static test on `db.set_value`) |
| **AB-3** | **Removing an item to hide a bad result.** Manager, report in MR, KPI at 40% attainment. Manager calls `set_review_selection` without that KPI; it clears `appraisal_cycle` on the original (`:3521-3522`). No stage check, no reason, no record. The review scores without it. HR (any company, any stage) can do the same (`:3465`) | **Today** | VIS-5, SEC-24, PRIV-12, SEC-10 |
| **AB-4** | **Overlapping cycles leak facts.** Q1 review still open, Q2 generated. A sale dated 30 Jun is counted in both Q1's and Q2's copies, or moved by HR changing `past-objectives.period_to` (`:3411-3413`) so a bad month falls outside the window | Design; the window edit is today | SEC-21 |
| **AB-5** | **Write-back overwrites someone else's change.** Cycle ended 30 Jun; lock released 30 Jul (R9 default 30). HR corrects a target on the original on 2 Aug. The review completes on 10 Aug and writes back the value agreed in May, silently undoing HR's correction | Design | SEC-25 |
| **AB-6** | **Copies exposed through the desk and REST.** Rahul `GET /api/resource/Alvoraa Appraisal Extension/HR-APR-2026-00058` today returns his Completed review, and `has_permission` says he can **write** it (checked on ppj). Once copies are child rows, the same call returns every copy with manager ratings and potential. An HR User in another store opens a stranger's Extension in the desk during ER; `_assert_hr_can_view` is a portal-only check. The Extension has `track_changes = 1`, so the form timeline also shows old values of every changed field to whoever opens it | **Today** (Employee DocPerm; HR desk at any stage) | SEC-5, SEC-27, VIS-2 |
| **AB-7** | **Report, print and export.** HR Manager has no export, print or report flag on the Extension (JSON), so Report Builder and Data Export are closed. The portal CSV (`export_cycle_kpis_csv`) is the open export: every company, self comments and potential at any stage | **Today** (CSV) | SEC-26, PRIV-9 |
| **AB-8** | **Ratings leak to outside screens against R14.** Subject calls `get_my_kpis` → own `potential_rating` and `manager_rating` (`KPI_FIELDS`, `:243-250`); on ppj 6 of Rahul's 12 KPIs carry both. A manager's scorecard of a report returns `overall_rating` and `total_score` for every cycle at any stage (`hr_api.py:836-853`). `get_employee_final_review` returns potential to the subject (`:4094-4095`) | **Today** | PRIV-9, PRIV-1 |
| **AB-9** | **HR subject closes their own review.** An HR Manager whose own review is in HRR calls `advance_review_status` → Completed (`:2431-2432`); or in MR calls `submit_appraisal` on their own appraisal (`:1139-1154`, guard `:133-136`). 11 open reviews on ppj belong to HR or System Manager role holders | **Today** | SEC-10 |
| **AB-10** | **Unfreezing through settings.** HR Manager changes the freeze point, or writes a Global Default through `set_org_setting` (`hr_api.py:2206`), so that reviews already frozen take new facts, or the lock days to 0 then back | Design (settings do not exist yet); `set_org_setting` is today | SEC-21 (stamped per review), SEC-28 |
| **AB-11** | **Any employee re-tags the tenant.** Rahul calls `attach_ongoing_to_cycle(cycle="Q2 FY27 Performance Cycle")` from the browser. Every live goal and KPI in the tenant whose dates overlap and whose cycle is empty or Completed is moved to Q2 (`:915-973`, `ignore_permissions`, `db.set_value`, commit). Q1's finished reviews lose their records (on ppj Q1 is Completed) | **Today, on `main`** | SEC-20 |
| **AB-12** | **One reviewer overwrites another.** Additional reviewer X calls `save_additional_reviewer_rating(kpi, row_name=<Y's row>, rating=1)` (`:2633-2640`) | **Today** (0 rows on ppj) | SEC-29 |
| **AB-13** | **Answering a stamp flag to unblock sending.** The subject, or an HR user who did not give the rating, answers "keep rating" so HR can send the review | Design | SEC-23 |
| **AB-14** | **Invited reviewer keeps reading.** Invited for MR with `allowed_pages=["past-dev"]`, the reviewer calls `get_reviewer_view` after Completed and receives all goals with progress (`:3906-3912`) and the whole `page_data` (`:3935`) | **Today** | SEC-7 |
| **AB-15** | **Curious colleague reads calibration.** Any employee calls `get_calibration_signoff(cycle)` and reads HR's free-text calibration summary (`:4177-4190`) | **Today, on `main`** | SEC-30 |
| **AB-16** | **Discard removes the evidence.** Tenant on the default "discard". After the manager rated an item 1, HR removes the item "on request". The copy and its rating are gone; the appraisal re-scores without it; nothing records that a rating of 1 existed | Design | SEC-24, PRIV-14 |

---

## 6 · Found while verifying

Same class, same code. "Include" means I recommend it goes into group D under the
requirement named. The user decides.

| # | Finding | Evidence | Recommend |
|---|---|---|---|
| **F-D1** | **`attach_ongoing_to_cycle` has no role check.** Any logged-in user re-tags every overlapping live goal and KPI in the tenant, including records of Completed cycles | `performance_api.py:915-973`; confirmed 00b D-9; present on `origin/main` (`42c165d`) | **Include** (SEC-20). Blast radius is the whole tenant |
| **F-D2** | **The subject reads their own potential rating on the live KPI** through `get_my_kpis` and the list API | `KPI_FIELDS` `:243-250`; KPI JSON: all fields permlevel 0, Employee read; ppj: Rahul `get_list("KPI")` → 12 rows, 6 with potential; 2,356 KPIs with potential, 601 in Q2 | **Include** (PRIV-9). Breaks a user decision |
| **F-D3** | **Ratings and scores on outside screens at any stage**: scorecards (`overall_rating`, `total_score`), `get_my_appraisal` / `get_appraisal` / `get_team_appraisal` / `goals_api.get_appraisal_data` (`Appraisal.goals` scores), `get_my_appraisals` (`overall_rating`), `get_cycle_items` (`manager_rating`). HR scorecard reach is every company | `hr_api.py:700-711`, `:836-853`, `:949-982`; `performance_api.py:496-520`, `:1038`, `:3203`; `goals_api.py:726-767` | **Include** (PRIV-9) |
| **F-D4** | **One additional reviewer can overwrite another's rating**; HR passes as any reviewer | `:2586-2596`, `:2633-2640` | **Include** (SEC-29). Small, and the code moves to copies anyway |
| **F-D5** | **`get_calibration_signoff` has no permission check** | `:4177-4190`; on `main` | **Include** (SEC-30). One line |
| **F-D6** | **HR reads any Extension in the desk at any stage and any company**; the stage rule exists only in the portal (`_assert_hr_can_view`). System Manager is exempt from the portal stage rule too | Extension JSON perms (HR Manager and HR User read/write/create); no `has_permission` hook for it in `alvoraa_goals/hooks.py:29-36`; `:68-69` | **Include** (SEC-27), or record the product owner's acceptance (Q-D3, Q-D7) |
| **F-D7** | **HR cycle screens ignore stage and company**: `get_calibration_overview` and `export_cycle_kpis_csv` return self comments, manager ratings, potential and overall rating for reviews still in ER and MR, for every company. This is the same leak PRIV-2 closes in the review screens | `:2704-2753`, `:2884-2947`; ppj: 601 manager ratings on reviews not yet in HRR | **Include** (SEC-26) |
| **F-D8** | **`save_calibration_note` writes `overall_rating` at any stage, including Completed**, and does it with `frappe.db.set_value` when the doc has no `calibration_notes` attribute. **The Extension has no `calibration_notes` field in its JSON**, so that branch runs, and the note itself would fail on a missing column. No reason or change log is kept (feature map E5) | `:2950-2969`; Extension JSON field list | **Include** under VIS-10 and SEC-10 (stage and self checks). The missing field and a calibration change log are a functional bug and E5: **raise separately**, not in 010 |
| **F-D9** | **`get_employee_final_review` returns `potential_rating` and `potential_category` to the subject**; the page shows it when `show_potential` is set (`hrms-employee.html:15656`) | `:4089-4100` | **Include** (PRIV-1; already in `01c` scope, recorded here with the line) |
| **F-D10** | **HRMS `Appraisal` ships with Employee read, write and create, and no row rule in our code.** On a tenant with shipped permissions the subject may read their own appraisal's scores at any stage, and write a draft one. ppj is protected only by a Custom DocPerm (System Manager only). test_site has none | `hrms/hr/doctype/appraisal/appraisal.json` perms; no Appraisal entry in `hrms/hooks.py` permission hooks; bench: ppj Custom DocPerm present, test_site absent; Rahul `has_permission` read False on ppj | **Include as a question** (Q-D12). It is stock HRMS behaviour limited by User Permissions; changing it touches every HRMS appraisal screen |
| **F-D11** | **`set_goal_progress` lets a goal's creator set progress directly, skipping validation.** With copies, that number flows into the review until the freeze (R3). Same class as `01c` F-14, which decision 10 kept out of 010 | `goals_api.py:677-699` | **Not in 010** by decision 10, but **the product owner should know it now feeds review scores**. Q-D13 |
| **F-D12** | **`get_team_reviews` for HR lists every active employee in the tenant with `overall_rating` and `potential_rating`** at any stage | `:683-686`, `:720-743` | **Include** (SEC-26 scope and PRIV-1) |

**Worries, not findings** (I cannot write a full actor-and-path sentence for these):
- **Departed employees.** `_employee_id` does not check `Employee.status` (`:30-34`). A person
  marked Left whose user stays enabled could still call review endpoints. I did not check
  whether leaving disables the user on any tenant.
- **Dotted-line managers** get an HRMS `Employee Performance Feedback` record linked to the
  appraisal when `total_score` is set (`hrms/alvoraa_org_structure/dotted_line.py:114-138`).
  I did not check what the stock HRMS feedback form shows them about the appraisal's scores.
  If `_apply_kpis_to_appraisal` now reads copies, it must still set `total_score`, or this
  trigger stops.
- **Version history on the Extension** (`track_changes = 1`) will record every copy row change
  with old and new values. That is good audit. It also means anyone who can open the desk form
  sees history of fields hidden from them in the portal. SEC-27 limits who opens it.
- **`get_calibration_matrix` returns `gender` and `employment_type` per rated person** and
  offers them as filters (`:3056-3086`). That is fairness-reporting territory (feature map E7,
  "counsel before building"). Not this slice.

---

## 7 · Questions for the product owner and counsel

I am not a lawyer. Each question names what it blocks.

### Product owner

| # | Question | Proposed answer (fail closed) | Blocks |
|---|---|---|---|
| Q-D1 | Does the subject see **item-level** manager ratings from Employee Final Review, like the overall rating? Do they see the rating stamps? | Item ratings from EFR, yes. Stamps and flags, no | PRIV-1, PRIV-13 |
| Q-D2 | **Future Objectives:** tagged to the next cycle, or to no cycle? (00b D-6, not answered in 00c) | No cycle | VIS-15 |
| Q-D3 | May HR Manager and HR User keep opening any Extension in the **desk** at any stage? | No: same rule as the portal (SEC-27) | SEC-27, VIS-2 |
| Q-D4 | May a copy that already has a rating be **discarded** on removal, or is it always kept marked "Removed"? | Always kept | SEC-24, PRIV-14 |
| Q-D5 | Does the subject see **why** an item was removed, and when? | Label and date at EFR; reason: your call | PRIV-12 |
| Q-D6 | Does an invited reviewer keep access after Manager Review? | No | SEC-7 |
| Q-D7 | Does **System Manager** obey the stage rule for strangers' reviews (today exempt, `:68-69`)? | Yes | SEC-27, §3 |
| Q-D8 | After Employee Review, may the manager or HR **add** an item to the review? | No, until decided | VIS-5 |
| Q-D9 | A fact with **no date**: ignore it for copies and show it to HR, or use its upload or creation date? | Ignore and show to HR | VIS-8, SEC-21 |
| Q-D10 | Is the lock only target, weight, period, title, delete and cycle (R2), or also `progress_mode`, `direction`, `baseline_value`, `unit` and the parent link, which change how the copy counts? | Lock them too | SEC-19 |
| Q-D11 | If the rater has left or changed role, who answers their stamp flag? | The subject's current manager, recorded as a different person | SEC-23 |
| Q-D12 | Should our `hrms` fork remove Employee write (and scope read) on HRMS `Appraisal`, or should the release rule be enforced only through our endpoints? | Remove Employee write; read through endpoints only | PRIV-9, F-D10 |
| Q-D13 | Now that goal progress feeds the review copy, should `set_goal_progress` (creator sets progress with no approval) stay out of 010? | Bring it in, or block it on held originals | F-D11 |
| `01c` Q5, Q11 | Still open: hide the self-review again after return for revision; direct reports or whole line | As in `01c` | PRIV-2, SEC-6 |

### Counsel

| # | Question | Blocks |
|---|---|---|
| C-D1 | Review copies, stamps, removal records and write-back audit entries are decision records about a person. **How long must or may the employer keep them, and what does an erasure request by a former employee do to them** (DPDP erasure on purpose completion vs defending a rating)? As a likely processor, do we delete on the employer's instruction only? | PRIV-14; any future purge job. **Does not block the build**: no delete path is built |
| C-D2 | If the tenant chooses "discard" and a **rated** copy is removed, is destroying that evidence a problem if the rating is later disputed? | SEC-24's "always keep" proposal |
| C-D3 | Is the **potential rating** something the employer may withhold from the employee on a data-access request? (`01c` C4, still open.) PRIV-1 hides it in the product; an access request is a separate route | Whether "never the subject" is final |
| C-D4 | Must the employee be told when an item is **removed from their review** after they sent it, and why (fairness, the right to contest under GDPR Art 22 if EU exposure is confirmed)? | PRIV-12 reason visibility |

---

## Residual risk

Nothing here is accepted yet. Each line needs a name and a date from the user.

| Risk | Why it remains | Accepted by | Date |
|---|---|---|---|
| Existing ratings on originals stay readable to HR in the desk after PRIV-9 | They are decision records and are not deleted | — | — |
| Tenants with a Custom DocPerm re-granting Employee on the Extension, or with shipped HRMS Appraisal permissions | Custom DocPerm replaces our JSON; M3 reports, it does not fix | — | — |
| No retention engine or legal hold (feature map A6) | Out of scope; PRIV-14 blocks deletion instead | — | — |
| Security log and audit in France, not India (CERT-In) | Infrastructure gap, baseline §3a | — | — |
| Line-level rule for managers still mixed (`01c` Q11) | Product decision open | — | — |

---

## Open questions

| # | Question | Owner | Decision it blocks |
|---|---|---|---|
| Q-D1 … Q-D13 | See §7, product owner table | Product owner | As listed in §7 |
| C-D1 … C-D4 | See §7, counsel table | Counsel | As listed in §7 |
| Q-D14 | Is the review endpoints' HR scope `permitted_companies()` (as group A) for every review path, including `get_my_review` opened by HR (`:3268`) and `list_appraisals` (`:536-545`)? | Product owner | SEC-26, SEC-27 |
| Q-D15 | Should the M3 check also run against dev tenants before the push to dev, or only at deploy? | User | SEC-5 evidence |

## Assumptions

- [ASSUMPTION] The copy table is the M2 child table on `Alvoraa Appraisal Extension`, as R1
  says. If the engineer chooses another shape, VIS-1 and VIS-2 must be re-checked.
- [ASSUMPTION] Frappe v16 applies the parent's permission to child rows read through
  `frappe.client` and `get_list(parent_doctype=…)`. VIS-2's test proves or disproves it.
- [ASSUMPTION] `before_validate` runs for desk saves, REST saves, imports and
  `doc.save(ignore_permissions=True)`. I read Frappe `document.py:1403-1408`; I did not run it.
- [ASSUMPTION] Line numbers are at `c27fb56`. `origin/dev` was still `c27fb56` when I fetched
  on 2026-09-15.
- [ASSUMPTION] Bench results (`has_permission`, `get_list` as a user, counts) reflect what REST
  would allow. Every check was read-only and rolled back. I did not send any write.
- [ASSUMPTION] ppj.localhost data is a demo copy and matches the counts in `00b`. Other tenants
  were not checked, and I did not try to reach them.
- [ASSUMPTION] "HR sent" (R6 default) means the move from HR Review to Completed, as 00c states.
- [ASSUMPTION] After "return for revision" the self-review is hidden again (`01c` Q5, open).
- [ASSUMPTION] No sensitivity-class mechanism (A1) and no retention engine (A6) exist, so the
  classes in §2 are declarations enforced only by the requirements that name them.

## Handoff note

To the hrms-fullstack-engineer: **put the lock in the document layer, not the endpoints.**
One guard on `before_validate` and `on_trash` for `KPI` and `Individual Goal` covers the
portal, desk, REST and import. `validate` is not enough, because `set_goal_progress` saves
with `ignore_validate`. Then remove every `frappe.db.set_value` that re-tags or redefines
originals (`attach_ongoing_to_cycle`, `set_cycle_membership`, `set_review_selection`) and pin
it with a static test. **Ship the three "today" holes first, in their own commits, before the
copy table:** SEC-20 (`attach_ongoing_to_cycle` role check), PRIV-9's `KPI_FIELDS` and
permlevel change (potential visible to the subject), and SEC-10 (HR completing their own
review). They are live on `main` and do not depend on copies. Put the stage and relationship
filter inside `review_payload`, so the three review readers and the five HR cycle screens
cannot drift. Stamp the window, freeze point and removal mode on the Extension when copies
are first made; never read tenant settings for an open review. The settings belong on HR
Settings (it keeps history), not in Global Defaults. SEC-5, PRIV-9 (permlevel) and the new
child DocType need `bench migrate`, which is a deploy command that needs the user's word.
`hrms-employee.html` and `performance_api.py` are hot files: follow `parallel-work.md` §6, and
read `00d-impact-analysis-group-d.md` (being written now) before you start. **I disagree with
one default in 00c:** R12 "discard" should never apply to a copy that already carries a
rating. I have written SEC-24 that way as a proposal. If the user keeps discard for rated
copies, change the test to pin their decision and record it; do not quietly build either one.
