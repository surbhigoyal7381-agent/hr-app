# 09 — Performance management

PP Jewellers has no appraisal process in any system today. On paper they want three things to count: attendance regularity, the manager's feedback, and targets achieved. This file defines the whole thing in their context: core values, quarterly store targets cascaded to every role, KPIs with 0 to 5 ratings, an attendance score that comes from the attendance data by itself (build B6), manager feedback on values and behaviours, potential rating, overall rating and the 9-box.

## 1. Which performance stack, and what the PMS module is

The repo carries three separate performance systems that do not share data. The choice matters, so here is the short version.

| Stack | Where | What it is | Computes a score? |
|---|---|---|---|
| Frappe HR Appraisal | `hrms/hr/doctype/appraisal*` | Stock Frappe HR: Appraisal Cycle, KRAs, goals, self rating, Employee Performance Feedback, final score with a **configurable formula** | Yes |
| Alvoraa Goals | `alvoraa_goals` + `alvoraa_portal/performance_api.py` | Our product's own layer: Goal Cascade, Individual Goal, KPI (target, actual, attainment, 0 to 5 manager rating, weightage), potential rating, overall rating, calibration matrix, company values, upward feedback. The portal's Performance tab. It **bridges into** Frappe HR Appraisal: KPI ratings are written into the Appraisal's goal table and the Appraisal computes the final score. | Yes, through the bridge |
| PMS module | `hrms/hrms/performance_management` (36 doctypes) + `hrms/hrms/pms` + portal pages `pms-employee`, `pms-manager`, `pms-steering`, `pms-calibration` | A newer, richer **review-process** engine: templates, 15-state review record with employee–manager dialogue and return loops, calibration sessions, anonymous upward feedback, talent flags, check-ins | **No.** Its `overall_rating_formula` field is stored but no code reads it. Overall and potential ratings are typed in by the manager. |

**Where the PMS came from.** It was built from the Product Requirements Specification `hrms/roster/AllAboutHR_PRS_Performance_Review.md` (PRS v0.7, dated 29 July 2026, "AllAboutHR — Performance Management System (PMS) module", drafted with AI assistance and marked "pending review by Surbhi Goyal & Mahavir Singh"). That document takes CatalystOne's continuous-performance product as its baseline and describes a dialogue-first annual review process. The whole module arrived in the repo in a single commit on 2026-08-18 ("Add the deployment runbook and the pre-migrate rename it depends on"), together with the deployment runbook, so there is no incremental history for it. `ARCHITECTURE.md` §11 notes it has never been run. It is a process engine without a scoring engine, and it is not connected to Alvoraa Goals or to Frappe HR Appraisal.

**Recommendation, as agreed:** use **Alvoraa Goals bridged into Frappe HR Appraisal**. It is the product's face, it has KPIs, potential and overall ratings and the 9-box already, and the Appraisal Cycle formula is the one place where weights are configurable and actually run. The PMS module stays out of this demo. Its dialogue and calibration ideas can be brought into the goals path later, one at a time.

## 2. Core values

Create these as **Company Value** records (alvoraa_goals) with an emoji and a description. They appear as tags on goals and KPIs, on the induction Day 1 agenda, and as the criteria of the manager feedback form.

| Value | In one line | What it looks like on the floor |
|---|---|---|
| Purity & Trust | We sell exactly what we say we sell. | Hallmark and certificate shown before the customer asks. No pressure selling. Old-gold valuation explained openly. |
| Craftsmanship | We respect the work behind every piece. | Karigar repair done right the first time. Product knowledge kept sharp. Displays handled with care. |
| Customer Delight | Every visit should feel like a family occasion. | Greeting within 30 seconds. Follow-up before the wedding date. Complaints closed within 48 hours. |
| One Family | We win as a store, not as individuals. | Coaching juniors. Covering a colleague's counter. No poaching of walk-ins. |
| Discipline & Safety | Gold demands discipline. | On time, in uniform, vault rules followed, checklists signed. |

## 3. Rating scales

**Alvoraa Rating Scale "PPJ 5-Point"** (default): 5 Outstanding, 4 Exceeds Expectations, 3 Meets Expectations, 2 Needs Improvement, 1 Unsatisfactory.

**Potential categories** (already in Alvoraa Appraisal Extension): Low / Moderate / High / Exceptional Potential, mapped from the average potential rating (< 2 Low, 2 to 3 Moderate, 3 to 4 High, above 4 Exceptional).

**KPI attainment to rating** (what the manager sees as a suggestion, then rates): the product's linear rule `min(5, attainment / 100 × 5)`. The band table in `OBJECTIVES_KPI_REQUIREMENTS.md` FR-24 (≥ 120% → 5, 100 to 119% → 4, 90 to 99% → 3, 75 to 89% → 2, below → 1) is not built; write it into the Performance Appraisal Policy as the manager's guidance and let the manager rate.

## 4. Cycles

| Appraisal Cycle | Dates | Status in the demo | Purpose |
|---|---|---|---|
| Q1 FY27 Performance Cycle | 2026-04-01 to 2026-06-30 | Completed | The finished appraisal: every employee has a final score, overall rating, potential rating; 9-box populated; calibration signed off |
| Q2 FY27 Performance Cycle | 2026-07-01 to 2026-09-30 | In Progress | Live targets with July and August progress; manager ratings partly done; the Store In-charge rates one person live in the demo |

Create both through the portal **cycle wizard** (HR persona) so the demo can show the wizard: name, dates, employees (all 400), page configuration, and the new **scoring weights step** from build B6: Targets 50%, Manager feedback 30%, Attendance 20%.

For Q1 the appraisal data (KPI actuals, ratings, feedback) is seeded by script (file 11), then the cycle is completed.

## 5. Goal Cascade and store targets

One **Goal Cascade** per quarter: "Q2 FY27 Company Sales", company PP Jewellers Pvt Ltd, unit Revenue, period 1 Jul to 30 Sep 2026, company target 58 crore (entered as 5,800 lakh, unit Lakh, to keep numbers readable). Same for Q1 with 53.4 crore (92%).

Goal Cascade has no branch field, so a store is modelled as an **Individual Goal owned by the Store In-charge**, and floors as goals owned by Floor Managers under it:

```
Goal Cascade: Q2 FY27 Company Sales — 5,800 lakh
├── Individual Goal "Chandigarh store sales Q2" — owner PPJ-0041, 1,200 lakh
│   ├── "Gold floor sales Q2" — Floor Manager Gold, 720 lakh
│   │   ├── "Own sales Q2" — each Senior Sales Executive, 74.5 lakh
│   │   ├── "Own sales Q2" — each Sales Executive, 49.7 lakh
│   │   └── "Own sales Q2" — Trainee, 24.8 lakh
│   ├── "Diamond & Platinum floor sales Q2" — 384 lakh
│   └── "Silver & Fashion floor sales Q2" — 96 lakh
├── "Ambala store sales Q2" — 700 lakh …
├── "Noida store sales Q2" — 1,000 lakh …
├── "Karol Bagh store sales Q2" — 1,500 lakh …
└── "South Extension store sales Q2" — 1,400 lakh …
```

Every goal has `parent_goal` set, `goal_type` Business, `weightage` 0 (the KPI carries the weight, the goal carries the cascade), `company_value` = Customer Delight, and `goal_cascade` set on every level, which is what the portal itself does when a child goal is created under a parent.

**Bug found while testing:** the **Cascade Alignment Report** sums the targets of *every* goal on the cascade, so a three-level tree reports a variance of about 200% and "Misaligned", even though the five store targets add up exactly to the company target. The check should sum only top-level goals (those with no `parent_goal`). It is a two-line fix in `alvoraa_goals/controllers/cascade.py` and is listed in file 10. Until it lands, do not open the alignment report in the demo; the cascade's own progress figure is correct.

Goal progress comes from **Goal Evidence** rows (Manual Entry, value = monthly sales in lakh, approved by the Floor Manager). Seed July and August evidence for every salesperson from `sales_actuals_july.csv` (August = July × a small random factor). Store and floor goals roll up by the hourly job; run `recalculate_progress` once after seeding.

## 6. KPIs per role

`data/kpi_library.csv` has the KPI set for 22 designations; weights total 100 for every role. Every role has a "Living our values" KPI (manager rated, 10%) tagged to a core value. Sales roles carry "Own sales value vs target" at 50 to 55%, linked to their Individual Goal so attainment shows on both.

Create the KPIs for **Q2** for all 400 employees by script from the library (designation → KPI rows, target from the cascade for sales KPIs, library target for others). Create the same for **Q1** with actuals and manager ratings filled.

For head-office roles not in the library (Accountant, HR Executive, Driver, etc.), use three generic KPIs: "Core responsibilities delivered on time" 50%, "Quality and accuracy" 40%, "Living our values" 10%.

Progress: **KPI Progress Log** rows for July and August on the sales KPIs (same figures as the goal evidence), and one or two rows on non-sales KPIs so nothing looks empty.

## 7. The three-part score, and how each part is produced

| Part | Weight | Where it comes from | 0 to 5 scale |
|---|---|---|---|
| Targets achieved | 50 | `goal_score`: weighted average of KPI `manager_rating` (and goal attainment ratings) via the Alvoraa → Appraisal bridge. Weights must total 100, which the library guarantees. | manager rating 0 to 5 |
| Manager feedback | 30 | `average_feedback_score`: **Employee Performance Feedback** submitted by the manager with **Employee Feedback Criteria** = the five core values plus "Customer handling" and "Teamwork and coaching", each with a weight (values 12% each = 60, customer handling 25, teamwork 15). Frappe HR computes `total_score` from the star ratings. | stars 1 to 5 |
| Attendance regularity | 20 | `attendance_score`: **new read-only field on Appraisal**, computed by the generalised attendance hook (build B6) from Attendance, late flags and Attendance Deductions in the cycle window. | computed 0 to 5 |

**Final score formula** written onto the Appraisal Cycle by the wizard:

```
goal_score * 0.5 + average_feedback_score * 0.3 + attendance_score * 0.2
```

Frappe HR evaluates it with `frappe.safe_eval`; `attendance_score` is available because every Appraisal field is in the formula context.

**Attendance score definition** (defaults, configurable in the wizard):

```
reliability  = 1 − (absent_days + lwp_days) / scheduled_days        # approved paid leave does not hurt
punctuality  = 1 − late_entry_days / present_days                   # the 15-minute flag
raw          = 5 × (0.6 × reliability + 0.4 × punctuality)
attendance_score = max(0, min(5, raw − 0.25 × deduction_days))     # each quarter-day-rule day costs 0.25 points
```

Worked example, PPJ-0054, Q2 to 6 September: scheduled 58, absent 0, LWP 0 → reliability 1.00; present 58, late-flag days about 8 → punctuality 0.86; raw = 5 × (0.60 + 0.345) = 4.72; deduction days 0.5 → score 4.60. (Exact late-flag count depends on the generated punches.)

## 8. Build B6: generalise the attendance hook and make it configurable

### 8.1 What exists

`hrms/hrms/grace_group/hooks/appraisal_metrics.py` runs on `Appraisal.before_save`. It returns early unless the employee's designation is "Delivery Executive", computes a reliability percentage, reads a client-specific `Daily Route Log`, writes a text block into `Appraisal.remarks`, and pushes numbers into `Appraisal KRA.goal_completion` by matching KRA titles. It is a client hack, not a feature.

### 8.2 What to build

**Appraisal Cycle** gets a new section "Attendance in the score" (custom fields via the hrms fork's `alvoraa_hr_core` module, so the stock JSON is untouched):

| Field | Type | Default |
|---|---|---|
| include_attendance_score | Check | 0 |
| attendance_weight | Percent | 20 |
| goal_weight | Percent | 50 |
| feedback_weight | Percent | 30 |
| attendance_reliability_weight | Percent | 60 |
| attendance_punctuality_weight | Percent | 40 |
| attendance_deduction_penalty | Float (score points per deducted day) | 0.25 |
| count_paid_leave_as_absent | Check | 0 |
| attendance_exempt_grades | Table MultiSelect Employee Grade | blank |

Validation: the three weights total 100. On save, if `include_attendance_score` is on, the cycle sets `calculate_final_score_based_on_formula = 1` and writes the formula shown in §7 from the three weights. If off, it leaves the formula alone.

**Appraisal** gets read-only fields: `attendance_score` (Float), `attendance_reliability_pct`, `attendance_punctuality_pct`, `attendance_deduction_days`, `attendance_summary` (Small Text, the plain-words breakdown).

**Hook** `alvoraa_hr_core.attendance_score.compute(doc, method)` on `Appraisal.before_save` and `before_submit`: if the cycle has `include_attendance_score`, compute the four numbers for `doc.employee` between `doc.start_date` and `doc.end_date`, using submitted Attendance (status, late_entry), Leave Ledger Entries with `is_lwp`, and Attendance Deductions (file 03). Scheduled days = days in window minus the employee's holiday-list days. Exempt grades get 5.0 with a note. Never touches `remarks`, KRAs or goals.

Move the Grace Group hook to call the new function for its attendance part and keep only its route-log logic, so nothing there breaks.

**Portal:**

- Cycle wizard (HR): a new step "How the score is built" with three sliders (Targets / Manager feedback / Attendance) that must total 100, an "Include attendance" switch, and an "Advanced" fold for the reliability/punctuality split, the penalty and exempt grades. Saved by `save_cycle_wizard` into the new cycle fields. Shown again on the cycle summary.
- Employee's appraisal page: a "Score breakdown" card: three bars with weights, the attendance numbers and the plain-words summary. Managers see the same for their team.
- HR cycle summary: average attendance score by store.

`performance_api.hr_create_cycle` and `save_cycle_wizard` stop hard-coding `final_score_formula = "goal_score"`; they call the cycle's formula builder.

### 8.3 Verification

- Q1 cycle: every submitted Appraisal has `attendance_score` between 0 and 5 and `final_score = 0.5 × total_score + 0.3 × avg_feedback_score + 0.2 × attendance_score` to two decimals.
- Changing the weights on the Q2 cycle and re-saving one Draft appraisal changes its final score accordingly.
- An exempt-grade employee (Owner) shows attendance score 5.0 with the "exempt" note.

## 9. Manager feedback, potential and overall rating

**Employee Feedback Criteria** (7 records) as in §7. **Appraisal Template "PPJ Standard"** carries them as `rating_criteria` with the weights; every Appraisal uses it.

For Q1, seed one **Employee Performance Feedback** per employee from their manager, submitted, with star ratings around the employee's KPI performance plus noise, and a two-line comment in the manager's voice for the persona employees.

**Potential rating**: the manager sets `potential_rating` (0 to 5) on each KPI in the portal; the extension averages them and sets the category. For Q1 seed potential ratings so the 9-box has a spread: about 10% Exceptional, 25% High, 50% Moderate, 15% Low.

**Overall rating**: the manager's summary rating on the Alvoraa Appraisal Extension (0 to 5, PPJ 5-Point scale), set at Manager Review. For Q1 seed it as the rounded final score ± 0.5 for realism, then "calibrate" a few in the calibration screen.

**9-box / calibration**: `get_calibration_matrix` builds overall × potential. Owner opens it for all stores; HR filters by store. Save a calibration sign-off for Q1 with the summary "Q1 calibrated 2026-07-12; 6 ratings adjusted".

**Upward feedback**: enable **Leadership Principles** (3: "Leads by example on the floor", "Coaches every day", "Fair with targets and offs") and seed Upward Feedback from 30% of store staff about their Floor Managers for Q1.

## 10. Persona walk-through

| Persona | Q1 (completed) | Q2 (live) |
|---|---|---|
| Employee PPJ-0054 | Appraisal: goal score 4.1, feedback 4.3, attendance 4.6 → final 4.26; overall 4; potential High. Action items: "Lead Dhanteras solitaire counter". | KPIs with July/August progress bars; "Own sales" at 104% cumulative; evidence list; check-in notes |
| Store In-charge Chandigarh | Team results table, distribution, who was calibrated | Rates PPJ-0054's KPIs live, sets potential, writes feedback |
| Owner | 9-box for 400, by store; store-level target attainment Q1 (104 / 92 / 111 / 97 / 118) | Cascade tree with progress; alignment report; store comparison |
| HR | Cycle summary, completion 100%, calibration sign-off | Wizard with the weights; completion 38%; reminder button |

## 11. Verification after this block

- 400 Q1 Appraisals submitted, all with `final_score` > 0, 400 Alvoraa Appraisal Extensions with `review_status` Completed, `overall_rating` and `potential_category` set.
- 400 Q2 Appraisals in Draft, KPIs with progress logs, ~150 with manager ratings.
- Cascade Alignment Report for both cascades = Aligned.
- Calibration matrix for Q1 shows all nine cells populated.
