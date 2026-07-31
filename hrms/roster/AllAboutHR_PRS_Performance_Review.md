# **Product Requirements Specification — Performance Review Process**

**Product:** AllAboutHR — Performance Management System (PMS) module  
**Document:** PRS v0.7 (draft for review)  
**Author:** Product Management (drafted with AI assistance; pending review by Surbhi Goyal & Mahavir Singh)  
**Date:** 29 July 2026  
**Status:** Draft — for internal review and tailoring per client engagement  
**Baseline reference:** CatalystOne Continuous Performance (Appraisals & Goals, One-to-One Meetings, Fast Feedback) and CatalystOne Calibrator, as publicly documented; extended with AllAboutHR’s dialogue-first process philosophy.

*Change log — v0.2:* manager-led vs employee-led process orientation; page-level template composition; past-goals date-window inclusion; goal weighting; extra-initiative goals with highlighted section; per-goal/KPI/action rating against HR-defined scales; two-party progress updates during the review; carry-over of unfinished goals into future goals; leadership-principles \+ expected-behaviours configuration for the manager’s feedback page; template save-and-reuse.  
*Change log — v0.3:* company values defined globally in application administration; employees and managers can tag company values on objectives and KPIs.  
*Change log — v0.4:* future goals stay in review-draft state until complete submission; additional-manager (multi-manager) review configuration and invite flow; detailed dialogue → adjustment → read-only form → employee accept/return loop with final employee submission and HR notification; HR-initiated manual reminders to incomplete participants.  
*Change log — v0.5:* many-to-many objective cascade with accountable persons per objective/KPI; contextual cascaded view on all pages (own items \+ upper hierarchy only); owner-or-their-manager edit rights; draft isolation extended to all in-review objective/KPI changes; multi-cycle-per-year re-runs vs check-in-driven continuation between annual cycles.  
*Change log — v0.6:* §7 restructured as the Annual PMS cycle of four independent processes (goal setting, self-review and dialogue merged into one review process), each run at the frequency the organisation’s strategy demands; §7.1 review record states updated to the dialogue/return-loop flow; cycle diagram redrawn without sequence arrows.  
*Change log — v0.7:* overall rating and potential rating recorded by the manager when sending the review for the employee’s final review; overall rating hidden from the employee until their final submission; potential rating never visible to the employee.

---

## **1\. Problem statement**

Mid-size and large organisations run performance reviews as annual, one-sided, form-driven events: managers rate employees, employees sign, and the output rarely connects goals to KPIs, values to behaviour, or assessment to development. Employees experience the process as something done *to* them rather than *with* them; managers experience it as paperwork; HR cannot demonstrate fairness or link outcomes to salary decisions defensibly. The cost is real: invisible high performers, unmanaged low performers, ratings that vary by manager rather than by performance, and appraisal data that no one trusts enough to act on.

AllAboutHR’s PMS module exists to replace this with a **continuous, dialogue-based performance review process** — highly configurable to each organisation’s own framework, but always transparent, data-driven, two-way, and closed with concrete action items.

## **2\. Product principles**

These principles are non-negotiable regardless of client configuration; every requirement in this document must be consistent with them.

1. **A dialogue, never a one-sided process.** The employee always gets a structured opportunity to present their complete picture of the period before the manager’s assessment is finalised.

2. **Transparent and data-driven.** Both parties see the same goals, KPIs, evidence and history. Assessments reference evidence, not impressions.

3. **Every dialogue ends in action.** No review, check-in or calibration closes without concrete, owned, dated action items.

4. **Continuous, not one-time.** Frequent lightweight check-ins — run with the intent to help — carry the process between formal reviews.

5. **Highly configurable process, fixed philosophy.** Cycles, templates, scales, sections and workflows adapt to the organisation; the principles above do not.

6. **Fair by design.** HR-led calibration precedes any compensation consequence; upward feedback keeps managers accountable to the organisation’s leadership principles.

## **3\. Goals**

| \# | Goal | Measure of success |
| :---- | :---- | :---- |
| G1 | Every employee in scope completes a two-way review each cycle | ≥ 95% cycle completion, with both self-review and manager assessment present |
| G2 | Goals are meaningfully linked to measurable KPIs | ≥ 90% of active business goals have ≥ 1 linked KPI at the moment of goal approval |
| G3 | The process is continuous, not annual | Median ≥ 1 recorded check-in per employee per configured check-in period |
| G4 | Assessments are calibrated before compensation decisions | 100% of ratings feeding salary review pass through a completed calibration session |
| G5 | Reviews produce action | ≥ 90% of closed review dialogues contain ≥ 1 action item with owner and due date |
| G6 | Talent signals surface early | Potential and support-plan flags available to HR ≥ 4 weeks before salary review window opens |

## **4\. Non-goals (this version)**

1. **Compensation planning / salary revision execution.** The PMS outputs calibrated ratings and recommendations *into* the salary review; it does not compute or administer salary changes. (Separate module / client payroll process.)

2. **Full 360° multi-rater feedback (peers, subordinates beyond upward feedback, external raters).** V1 supports self, manager and structured upward feedback only; broader 360° is a future consideration (P2).

3. **Learning management (course delivery).** Development goals may reference trainings, but the PMS does not host or deliver learning content.

4. **Succession planning workflows.** V1 surfaces talent signals (potential / support flags); formal succession slates and 9-box workflows are future scope.

5. **Consulting deliverables** (leadership-principles enablement workshops, framework design). These are AllAboutHR expert services that surround the product; the product supports them (e.g., configurable leadership-principle items) but does not replace them.

6. **Continuous anonymous engagement surveys.** Distinct product area.

## **5\. Users and roles**

| Role | Description | Core permissions (summary) |
| :---- | :---- | :---- |
| **Employee** | Any person under an active review cycle | Own goals, self-review, check-in records, own review history, upward feedback submission |
| **Manager** | Direct manager with one or more reportees | Team goals, check-ins, assessments, dialogue records, own upward-feedback summary |
| **Additional manager** | Second reviewing manager for employees working under multiple managers (template-configured) | Invited access to the specific review: read the primary manager’s preparation, enter an overall comment; no edit rights on ratings |
| **HR Manager / HR Admin** | Owns process configuration and calibration | Cycle & template configuration, calibration facilitation, org-wide dashboards, exports, manual reminders |
| **Steering committee / Leadership** | Reviews progress on objectives & goals | Read access to aggregated objectives & goals dashboards; no access to individual assessment content unless separately granted |
| **System Administrator** | Technical administration | User/role management, integrations, audit access |

Skip-level managers and matrix (“dotted-line”) reviewers are configuration options (P1), disabled by default.

## **6\. Definitions**

* **Cycle** — a configured review period (e.g., annual with mid-year checkpoint) with defined stages and deadlines.

* **Business goal** — an outcome-level objective cascaded from company / plant / function objectives.

* **KPI** — a measurable indicator linked to a business goal (target value, unit, direction, data source).

* **Development goal** — a growth objective (skill, behaviour, exposure) linked to the business goal(s) it enables.

* **Check-in** — a lightweight, recorded follow-up conversation between employee and manager between formal reviews.

* **Review dialogue** — the formal two-way conversation concluding an assessment stage.

* **Calibration** — the HR-led session aligning manager assessments across teams before ratings become final.

* **Leadership principles** — the organisation’s defined managerial behaviours, used as the framework for upward feedback.

* **Company values** — the organisation’s values, defined once globally by the HR manager in application administration; taggable on objectives and KPIs, and the basis of the values & behaviours assessment.

* **Accountable person (owner)** — the single person responsible for an objective or KPI; every objective and KPI has exactly one owner.

* **Objective cascade** — the linked structure of objectives: one objective can be linked with multiple objectives and KPIs, owned by the same or different accountable persons, forming the chain from company objectives down to individual ones.

## **7\. Process overview — the Annual PMS cycle**

![Annual PMS cycle][image1]

*Annual PMS cycle*

The Annual PMS cycle consists of four processes. **Each process is independent of the others**, and how frequently each runs is at the discretion of the organisation’s strategy (FR-1: multi-cycle re-runs vs check-in continuation).

1. **Employee self-review-led review dialogue & feedback** — the employee presents their complete picture of the period, with evidence. Business goals are cascaded and approved, each linked to KPIs; development goals are linked to business goals. Manager assessment plus two-way dialogue: values & behaviours, goals vs KPIs, development review and forward planning; structured upward feedback on leadership principles.

2. **Frequent lightweight check-ins** — manager-employee follow-ups run with the intent to help: support and direction for the employee, progress updates for the organisation.

3. **HR-led calibration & outcomes** — assessments aligned across managers before salary review; action items, growth and support decisions recorded; outputs feed the next cycle.

4. **Steering-committee reviews** — leadership reviews progress on objectives & goals dashboards at a cadence set by the goals themselves.

### **7.1 Review record states**

Each employee’s review per cycle progresses through explicit states:

Not started → Self-review open → Self-review submitted & Manager preparation in progress → \[Additional-manager review → Joint manager discussion\]\* → Employee invited to dialogue & Dialogue held & Manager adjustments → Send to employee for final review (Final read-only form with employee) → (Returned for amendment ⇄ Manager adjustments)\* → Submitted by employee (HR notified) → In calibration → Calibrated (final) → Closed

*Stages in brackets apply only when the template enables additional managers (FR-7b); the return-for-amendment loop may repeat.*

The order of the self-review and manager-assessment stages follows the template’s process orientation (FR-1): in **employee-led** templates the self-review opens first and the manager assessment cannot be finalised before it is submitted (or its grace deadline passes); in **manager-led** templates the manager’s assessment opens first and the record cannot progress to dialogue completion until the employee’s response is recorded. In both modes: ratings are provisional until calibration completes; sign-off requires both employee and manager acknowledgement, with the employee comment field always available; closed records are immutable except through an audited HR correction flow.

## **8\. User stories (prioritised)**

**Employee** \- As an employee, I want to see my goals, their KPIs and my progress at any time, so that I always know where I stand before anyone reviews me. \- As an employee, I want a structured self-review where I can present everything I did since the last review — with evidence attached — so that my complete picture is on the table, not just what my manager remembers. \- As an employee, I want every check-in and review to end with agreed action items, so that conversations produce support, not just judgement. \- As an employee, I want to give structured feedback on my manager against our leadership principles, so that leadership behaviour is accountable too. \- As an employee, I want to see the final assessment only after calibration, with my manager’s reasoning, so that I can trust the outcome is consistent across teams.

**Manager** \- As a manager, I want goal templates that cascade from my unit’s objectives with KPI linkage enforced at creation, so that my team’s goals are measurable from day one. \- As a manager, I want lightweight check-in records (agenda, notes, action items) that take minutes to complete, so that continuous follow-up is sustainable. \- As a manager, I want the employee’s self-review, goal data, KPI actuals and check-in history in one assessment view, so that my evaluation is grounded in evidence. \- As a manager, I want to see my aggregated upward feedback against the leadership principles, so that I know which behaviours to grow. \- As a manager, I want calibration to show me how my ratings compare with peers — with the chance to justify or adjust — so that I learn the organisation’s assessment parameters. \- As a manager of a shared employee, I want to invite the additional manager after my preparation and discuss jointly before the employee dialogue, so that the employee hears one aligned assessment, not two conflicting ones.

**Employee (dialogue loop)** \- As an employee, I want to receive the final form read-only after our dialogue and either submit it or return it with my comments, so that nothing is finalised about me without my explicit response.

**HR Manager** \- As an HR manager, I want to configure cycles, templates, sections, rating scales and workflows per entity or unit, so that the process matches our organisation without code changes. \- As an HR manager, I want to choose per template whether the review runs manager-led or employee-led, and which pages it contains (past goals with KPIs and action items, past development goals, future goals, manager’s feedback), so that each population gets the process that fits it. \- As an HR manager, I want to set the date window that decides which goals and KPIs appear on the past-goals page, so that the review covers exactly the intended period. \- As an HR manager, I want to save a template once and reuse it for future review cycles, so that recurring reviews take minutes to launch, not days. \- As an HR manager, I want to run calibration sessions with distribution views and employee scorecards, so that assessments are fair and consistent before salary review. \- As an HR manager, I want completion and quality dashboards (participation, overdue stages, goals without KPIs, dialogues without action items), so that I can intervene where the process is failing. \- As an HR manager, I want potential and low-performer support flags surfaced from reviews, so that talent actions start early, not at year-end.

**Steering committee / Leadership** \- As a steering-committee member, I want an objectives & goals dashboard aggregated by company / plant / function, refreshed continuously, so that we can review progress at the cadence the goals demand and correct course in-period.

## **9\. Functional requirements**

Priorities: **P0** \= must-have (module not viable without), **P1** \= should-have (fast follow), **P2** \= future consideration (design for, do not build).

### **FR-1 Cycle & template configuration — P0**

The system shall allow HR admins to configure, without code:

* **Review cycles** — frequency, stages, deadlines, grace periods.

* **Process orientation per template** — the review runs either **manager-led** (manager’s assessment initiates the review; the employee responds) or **employee-led** (employee’s self-assessment initiates; the manager responds). The dialogue principle (§2, principle 1\) holds in both modes: the responding party always contributes before the record can close.

* **Page composition** — the HR manager selects which pages/items the template includes: past business goals (with their linked KPIs and action items), past development goals, future goals page, manager’s feedback page (leadership principles), values & behaviours, free-text and custom sections. Excluded pages do not appear for either party.

* **Past-goals inclusion window** — for the past-goals page, the HR manager sets a date range (between two dates); goals and KPIs whose period falls within that window are automatically included on the page.

* **Rating scales** — defined on the configuration page (n-point scales with labelled and behaviourally anchored levels, or unrated) and bound to sections; the same defined scales are used wherever the manager rates goals, KPIs and actions (FR-7).

* **Workflow rules** — who acts at each stage, visibility rules, mandatory/optional sections.

* **Applicability** — by entity, unit, grade, location.

* **Template save & reuse** — a template, once saved, is stored in a template library and can be reused for any number of future performance reviews; templates are versioned, edits create a new version, and in-flight cycles remain locked to the version they started on.

* **Multiple cycles per year vs check-in continuation** — if the organisation runs more than one performance review cycle in a year, the HR manager can simply set up the process again from a saved template (e.g., half-yearly or quarterly runs). If the organisation runs a single cycle, the period between reviews is carried by the lightweight check-in process (FR-4), in which follow-ups run against the objectives, KPIs and action items finalised as the employee’s future planning in the last submitted review.

*Acceptance criteria (selected):* \- \[ \] An HR admin can create a new cycle from a saved template and apply it to a chosen population; affected users are notified. \- Given a template configured as employee-led, when the cycle stage opens, then the self-assessment stage precedes the manager stage; given manager-led, the order is reversed — in both cases the record cannot close without the responding party’s input. \- Given a past-goals window of 1 Apr 2026–31 Mar 2027, when the past-goals page renders, then exactly the goals/KPIs whose period falls in that window appear, and others do not. \- \[ \] Sections can be added, removed, reordered and marked mandatory per template version; in-flight cycles are version-locked. \- \[ \] A saved template can be selected unchanged for a later cycle, and its reuse count/history is visible to HR. \- \[ \] At least two live configurations can run in parallel (e.g., staff vs. workers) without interference. \- \[ \] Rating scales support 3–7 points with per-level descriptions and optional behavioural anchors.

### **FR-2 Business goal setting with linked KPIs — P0**

Goal creation shall support cascading from company / plant / function objectives; each business goal must carry ≥ 1 linked KPI (name, unit, baseline, target, direction, review frequency, data source — manual entry in v1, integration-fed in P1). Goal approval workflow (employee proposes / manager proposes → counterpart accepts) is configurable. Goals and KPIs may be adjusted mid-cycle through a tracked change flow (both parties notified; history retained).

**Objective cascade model:**

* **Many-to-many linkage.** One objective can be linked with multiple objectives and KPIs, and those linked items can be assigned to different or the same accountable person. Every objective and KPI carries exactly one accountable owner; the cascade is the resulting linked structure from company objectives down to individual ones.

* **Contextual cascaded view.** The cascaded view of linked objectives and KPIs is available on all pages (goal pages, self-review, manager assessment, dialogue, dashboards) — but each user sees only the objectives and KPIs relevant in their context: their own items plus the upper-hierarchy chain those items link to. Sibling branches and other individuals’ items are not shown (aggregate views for HR/steering per FR-5 permissions).

* **Edit rights follow ownership.** Only the accountable owner of an objective/KPI, or that owner’s manager(s), can edit or update it. All other users have view-only access per the visibility rules above.

* **In-review draft isolation (all changes).** Any change made to objectives and KPIs *inside* a performance review process — edits, re-weights, progress corrections, carry-overs, new links — is held within the review record and is not reflected outside (live cascade, dashboards, integrations) until the review is finally submitted (FR-9). On submission, changes activate atomically.

In addition:

* **Goal weighting** — each goal can carry a weight; the template defines whether weights must sum to 100% per employee (validated at approval) or are free-form. Weights feed the overall-rating computation (FR-7, open question Q1).

* **Extra initiatives** — any goal can be marked as an *extra initiative* (work beyond the agreed goal set). Extra-initiative goals are highlighted and grouped in a distinct section on every goals page, so additional effort is visible rather than buried; whether they contribute to the weighted overall rating or count as additive recognition is template-configurable (default: additive, excluded from weight validation).

* **Company-values tagging** — both the employee and the manager can tag one or more company values on any objective and on any KPI. The available values come exclusively from the global company-values list maintained by the HR manager in application administration (FR-14a) — no free-text values. Tags are visible wherever the goal/KPI appears, including self-review, manager assessment and dialogue views, so “living the values” is discussed against concrete work; goals pages can be filtered by value tag.

*Acceptance criteria (selected):* \- Given a goal without any linked KPI, when the user attempts to submit it for approval, then submission is blocked with a clear message (HR-configurable override allowed, logged). \- Given a template requiring weights to sum to 100%, when goals are submitted for approval with a different total, then approval is blocked and the current total is shown. \- Given a goal marked as extra initiative, when any goals page renders, then it appears in the highlighted “Extra initiatives” section, visually distinct from weighted goals. \- Given the global values list, when either party tags a value on a goal or KPI, then the tag is stored with attribution and appears on every view of that goal/KPI; values not on the global list cannot be tagged. \- Given an employee viewing any cascaded view, when the view renders, then it contains exactly their own objectives/KPIs and the upstream chain they link to — no sibling or unrelated branches. \- Given a user who is neither the owner nor the owner’s manager, when they open an objective/KPI they can see, then edit controls are absent. \- Given objective/KPI edits made inside an open review, when any user views the live cascade or dashboards, then pre-review values are shown until the review is submitted, after which the updated values appear. \- \[ \] Every goal displays its parent objective chain (company → plant/function → individual). \- \[ \] Mid-cycle goal changes require counterpart acknowledgement and are visible in the review record.

### **FR-3 Development goals linked to business goals — P0**

Development goals shall be creatable by employee or manager, linked to one or more business goals they enable (link optional but prompted), with actions, owners and target dates. Past development goals and their completion status shall auto-appear in the next review’s “development review” section.

### **FR-4 Continuous check-ins (lightweight follow-ups) — P0**

The system shall provide a check-in record: date, shared agenda (prefilled with the objectives, KPIs and action items finalised as the employee’s future planning in the last submitted review — plus KPIs off-track and open action items from previous check-ins), shared notes, private notes per party, and action items (owner, due date, status). Where the organisation runs a single review cycle per year, this check-in process is the continuation mechanism between cycles (FR-1). Check-in frequency targets are configurable (e.g., monthly); nudges are sent when a pair exceeds the target interval. Check-ins are visible to the pair and summarised (count/recency only, not content) to HR dashboards. The stated intent — support and direction, not evaluation — shall be reflected in the UI copy and in the fact that check-in content is *not* rated.

*Acceptance criteria (selected):* \- \[ \] A manager can complete a check-in record in under 3 minutes for the happy path (prefilled agenda, add one note, one action item). \- \[ \] Open action items from previous check-ins appear automatically until closed. \- \[ \] HR sees check-in cadence compliance without seeing note content.

### **FR-5 Objectives & goals dashboards \+ steering-committee view — P0**

Dashboards shall aggregate goal progress and KPI status by company, entity, plant, function and team: % on-track / at-risk / off-track, KPI actual vs target, trend over time, and drill-down to goal level (respecting permissions). A steering-committee view presents the aggregated picture without individual assessment content, supports meeting cadence set by goal review frequency, and allows a decision/action log per steering review (P1 for the log).

### **FR-6 Employee self-review — P0**

At each formal review stage, the employee shall receive a structured self-review: achievements against each goal and KPI (with system-shown actuals where available), contributions beyond goals, blockers and context, evidence attachments (files/links), self-assessment against the same sections the manager will rate (configurable), and a “what support do I need” field. Submission locks the self-review and releases the manager assessment stage. If the employee does not submit within the grace period, the manager may proceed; the record permanently shows self-review as absent.

*Acceptance criteria (selected):* \- Given the self-review is not yet submitted and the grace period is active, when the manager opens the assessment, then rating inputs are disabled and the reason is displayed. \- \[ \] The employee can attach at least 10 evidence items per review; all remain visible to both parties permanently.

### **FR-7 Manager assessment — P0**

The manager assessment view shall present, side by side with the employee’s self-review (or ahead of it, in manager-led templates): values & behaviours ratings against the organisation’s framework (with anchors); past business goals with linked KPI target vs actual; past development goals with completion review; and free-text justification per section (mandatory where rating deviates from KPI-suggested outcome, configurable).

The manager shall be able to **rate at three levels of granularity — each goal, each linked KPI, and each action item** — using the rating scales defined by the HR manager on the configuration page (FR-1); which levels are rated is template-configurable. Extra-initiative goals are rated in their own highlighted section. Overall rating computation (goal-weighted / manual / hybrid) is configurable per template and respects goal weights (FR-2); the system may suggest a computed overall rating, but the manager confirms or provides the **overall rating**, together with the **potential rating**, at the point of sending the review for the employee’s final review (FR-9 step 4, including its visibility rules). All manager ratings remain provisional and are marked as such until calibration completes.

*Acceptance criteria (selected):* \- Given a template with goal-, KPI- and action-level rating enabled, when the manager opens a past goal, then each of its KPIs and action items presents a rating input using the configured scale — no free-form numeric entry. \- Given goal weights defined, when all goal ratings are entered under a weighted template, then the computed overall rating reflects the weights, shown with its computation breakdown.

### **FR-7a Progress updates during the review — P0**

On every goals page (past and future), **both the employee and the manager shall be able to update goal progress during the performance review process itself** — progress %, status and comments per goal/KPI — not only between reviews. Each update is attributed and time-stamped, both parties see updates immediately, and the review record keeps the progress trail so the dialogue happens against current, shared numbers.

*Acceptance criteria (selected):* \- Given an open review, when the employee updates progress on a goal, then the manager’s view reflects it without page reconfiguration, attributed to the employee with timestamp — and vice versa. \- \[ \] Progress updates made during the review appear in the consolidated closed-review record.

### **FR-7b Additional managers (multi-manager review) — P0**

The HR manager can configure a template to include **additional managers** in the review, for employees who work under multiple managers. When this configuration is enabled:

1. The primary manager completes their review preparation, then **invites the additional manager** from within the review.

2. The additional manager receives the invite, reads the prepared review, and **enters their overall comment** on the page (comment-level input; ratings remain the primary manager’s).

3. The two managers **discuss together** (the joint discussion is acknowledged in the record) before the employee is invited to the dialogue.

*Acceptance criteria (selected):* \- Given a template without this configuration, when a manager prepares a review, then no additional-manager step appears anywhere in the flow. \- Given the configuration enabled, when the primary manager attempts to invite the employee to the dialogue before the additional manager’s comment is recorded, then the invite is blocked with an explanatory message (HR-configurable override, logged). \- \[ \] The additional manager’s comment is visible to the employee in the final form, attributed by name and role. \- \[ \] More than one additional manager can be configured (cap configurable, default 2).

### **FR-8 Forward planning within the review — P0**

The same review flow shall conclude with next-cycle planning: future business goals (cascaded, KPI-linked per FR-2) and linked development goals (per FR-3), so that looking back and planning forward happen in one conversation. A review cannot be closed without next-cycle goals in at least “proposed” state (HR-configurable).

**Draft isolation:** goals created on the future-goal planning page remain in a **review-draft** state, visible only inside the review record. They do not reflect anywhere outside the review — goal lists, dashboards, KPI views or integrations — until the review’s complete submission (employee submission per FR-9) is done, at which point they activate for the new period.

*Acceptance criteria (selected):* \- Given future goals drafted in an open review, when any user views live goal lists or dashboards, then those drafts are absent; when the employee submits the final form, then they appear as active goals for the agreed tenure.

**Carry-over of unfinished goals:** on the future goals page, old unfinished goals assigned to the employee can be added by **either the manager or the employee**, with an agreed tenure (new target date) for achieving them. A carried-over goal retains its history and link to the original (original period, progress and ratings visible), is marked “carried over”, and its KPIs/weights can be re-agreed for the new tenure.

*Acceptance criteria (selected):* \- Given an unfinished goal from the closing period, when either party adds it to the future goals page, then it appears marked “carried over” with a mandatory new target date and a link to its original record. \- \[ \] Carried-over goals are counted once in the new period’s weighting (never double-counted across periods).

### **FR-9 Review dialogue, adjustment loop & final submission — P0**

Once manager preparation (and, where configured, the additional-manager step) is complete, the review proceeds through a defined dialogue-and-agreement loop:

1. **Employee invite** — the manager sends the employee an invite for the dialogue; the employee receives it as email \+ in-app notification, with the shared preparation view (both parties’ inputs visible per configuration).

2. **Dialogue** — manager and employee hold the dialogue; dialogue notes and mandatory action items (≥ 1, with owner and due date) are recorded before the dialogue can be marked complete.

3. **Manager adjustments** — following the discussion, the manager makes adjustments to ratings, comments and plans as per the dialogue outcomes (all changes tracked against the pre-dialogue version).

4. **Final read-only form** — at the time of submitting the review for the employee’s final review, the manager **provides the overall rating and selects the potential rating** (both on scales configured by the HR manager), then sends the employee the final form in read-only view. **Visibility rules:** the overall rating is *not* visible to the employee until they finally submit the review — it stays hidden throughout any return-for-amendment loops; the potential rating is **never** visible to the employee at any point (management chain and HR only).

5. **Employee decision** — the employee either **(a) returns the form to the manager for amendments with a comment** (points of disagreement, or something missed — the manager amends and re-sends; the loop may repeat), or **(b) marks the form submitted** if aligned.

6. **HR notification** — on employee submission, the HR manager is notified and the record proceeds (calibration/closure per §7.1 and Q10).

The employee comment field remains available at every step and cannot be edited by the manager. Registered disagreement is visible to HR and in calibration.

*Acceptance criteria (selected):* \- Given the dialogue invite is sent, when the employee opens it, then both email and in-app notification link to the same shared preparation view. \- Given a dialogue with zero action items, when the manager attempts to mark it complete, then completion is blocked with an explanatory message. \- Given the final read-only form, when the employee returns it, then a comment is mandatory, the manager is notified, and the form re-opens for the manager only. \- Given the employee marks the form submitted, when submission completes, then the record locks for both parties, the HR manager is notified, and the future goals activate per FR-8. \- Given the manager attempts to send the final read-only form, when the overall rating or potential rating is missing, then sending is blocked with an explanatory message. \- Given the final read-only form is with the employee (including during return loops), when the employee views it, then the overall rating is absent from their view; when the employee finally submits, then the overall rating becomes visible to them (subject to Q10 on calibration timing). \- Given any employee-facing view at any time, when it renders, then the potential rating is never present — including in the consolidated closed-review record’s employee copy, exports and notifications. \- \[ \] Every adjustment after the dialogue is version-tracked; the employee can view what changed between the dialogue and the final form. \- \[ \] The number of return-for-amendment loops is unlimited by default; HR can configure an escalation alert after N returns (default 3).

### **FR-10 Manager’s feedback page — upward feedback on leadership principles — P0**

On the manager’s feedback page configuration, the **HR manager defines the leadership principles, the expected behaviours associated with each principle, and the rating scales** used to assess them — all on the configuration page, per template. Per cycle, each employee then receives a structured upward-feedback form about their manager built on exactly those principles and expected behaviours (ratings per the configured scale and/or comments per principle).

Responses are anonymised and aggregated; a manager sees their summary only when a minimum respondent threshold (default 3, configurable) is met. Aggregated results are visible to the manager, their manager, and HR; they inform the manager’s own review and development goals but are not auto-scored into ratings in v1.

*Acceptance criteria (selected):* \- \[ \] HR can define, per template: principles, expected behaviours per principle, and the rating scale bound to the page; the employee-facing form renders exactly this structure. \- \[ \] The manager’s feedback page can be included or excluded per template (FR-1 page composition).

### **FR-11 HR-led calibration — P0**

Before ratings become final and before any salary-review export, HR managers shall be able to run calibration sessions: define session scope (population \+ participating managers), distribution views (rating spread by team/manager vs reference distribution — guideline only, no forced distribution in v1), employee scorecards (provisional ratings, goal/KPI attainment, values ratings, potential/support flags, manager justification), rating adjustment proposals with mandatory justification, and a session decision log. All changes made in calibration are audited (who, what, when, why) and the final rating is marked “calibrated”. The session view is designed to be projected in a room: it supports walking through managers’ assessments so managers learn assessment parameters from peers and HR.

*Acceptance criteria (selected):* \- Given a rating not yet through calibration, when HR attempts to export to salary review, then the export excludes it and reports why. \- \[ \] Every calibration adjustment stores original value, new value, justification and session reference. \- \[ \] Distribution view can be filtered by manager, unit, grade and location.

### **FR-12 Talent signals — P1**

The **potential rating** recorded by the manager at final-review submission (FR-9) is the primary input here; it is visible only to the management chain and HR, never to the employee. From potential ratings, review and calibration data, the system shall support flagging: **potential** (candidate for larger / new roles, with note) and **needs support** (low performance, triggering a support-plan record: concrete actions, owner, checkpoint dates — reviewed in subsequent check-ins). Flags are visible to HR and the management chain per permission rules, and exportable to talent processes. (Formal PIP legal workflows and succession slates remain out of scope — see Non-goals.)

### **FR-13 Notifications, reminders & sign-off — P0**

Configurable notifications for stage openings, deadlines, overdue stages, dialogue invites, form returns/submissions, and check-in cadence nudges (in-app \+ email; WhatsApp/SMS P2). In addition to automatic notifications, **the HR manager can send manual reminders during the review process to any participants whose steps are incomplete** — individually or in bulk from the completion dashboard, with an optional personal message; manual reminders are logged and rate-limited (configurable) to avoid spam. Final submission per FR-9 is captured with timestamps; the closed review is rendered as a single consolidated record (exportable PDF).

*Acceptance criteria (selected):* \- Given the completion dashboard filtered to overdue participants, when HR selects them and sends a reminder, then each receives email \+ in-app notification and the action is logged with sender and time.

### **FR-14 Roles, permissions & administration — P0**

Role-based access per §5, with org-structure-driven visibility (manager sees direct and, configurably, indirect reports), delegation for manager absence (P1), and full segregation between entities where configured. All permission grants are auditable.

### **FR-14a Global company-values administration — P0**

On the **application administration page**, the HR manager shall maintain the company values at **global level**: name, description, optional behavioural descriptors, and active/retired status. This single global list feeds values tagging on objectives and KPIs (FR-2) and the values & behaviours assessment section (FR-7). Retiring a value stops new tagging but preserves existing tags and historical assessments; all changes are audited.

*Acceptance criteria (selected):* \- \[ \] Values created here appear immediately as tag options for all users in scope; per-template overrides are not permitted (single source of truth). \- Given a retired value, when a user opens the tag picker, then it is absent — while past goals/reviews still display it with a “retired” marker.

### **FR-15 Integrations — P0 (foundation)**

Employee master, org structure and manager relationships synced from the client HRMS/ERP (API or scheduled file, per deployment). KPI actuals ingestion from source systems is P1 (manual entry supported in v1). Calibrated-ratings export to salary review (file/API) is P0. All integrations are logged with sync status surfaced to admins.

### **FR-16 Reporting, audit & data export — P0**

Standard reports: cycle completion, section-level rating distributions, goals-without-KPI exceptions, dialogues-without-action-items exceptions, check-in cadence, upward-feedback participation, calibration adjustment summary. Full audit trail on assessment records. Data export respects permissions and is logged.

## **10\. Non-functional requirements**

* **Scale & performance:** support ≥ 25,000 active employees per tenant; assessment views load in ≤ 3 s at P95; dashboards in ≤ 5 s at P95 on standard broadband.

* **Security:** role-based access enforced server-side; encryption in transit and at rest; private notes readable only by their author; no assessment data in URLs or logs.

* **Privacy & compliance:** appraisal data is personal data — design for India’s DPDP Act obligations (consent/notice via employer, purpose limitation, retention schedule, data-principal access) and GDPR-readiness for multinational tenants; configurable retention and deletion policy per tenant.

* **Auditability:** every state change, rating change and calibration decision is time-stamped, attributed and immutable; supports defensible documentation in employment disputes.

* **Availability:** ≥ 99.5% monthly uptime target; review-period freeze windows announced for maintenance.

* **Usability & accessibility:** check-in happy path ≤ 3 minutes; mobile-responsive web for employee and manager flows (native apps P2); WCAG 2.1 AA for core flows.

* **Localisation:** UI language packs (English v1; Hindi P1); date/number formats per locale; template content is client-authored and multilingual-capable.

## **11\. Fairness & governance notes**

* Rating scales and behavioural anchors are client-authored; AllAboutHR provides starter frameworks, and recommends professional (I-O / psychometric) review before ratings drive employment decisions.

* Calibration is the fairness gate: no forced distribution in v1; distribution views are decision support, and every deviation is justified and logged.

* Upward feedback anonymity thresholds protect respondents; principle-level aggregates only.

* The potential rating is a confidential management/HR judgement: it is excluded from every employee-facing surface, is used for development and opportunity decisions rather than disclosed scoring, and its access is logged like all assessment data. (Note for legal review: under data-subject access rights such as DPDP/GDPR, an employee may lawfully request personal data held about them — confidentiality in-product does not override statutory access; retention and disclosure policy for potential ratings should be defined with counsel.)

* The product records — it does not automate — employment decisions; low-performer support plans are framed as support with checkpoints, consistent with the “intent to help” principle.

## **12\. Success metrics**

**Leading (first 1–2 cycles):** cycle completion ≥ 95%; self-review submission ≥ 90%; goals with linked KPIs ≥ 90%; median check-in interval within configured target for ≥ 70% of pairs; dialogues closed with action items ≥ 90%; upward-feedback participation ≥ 70%.

**Lagging (2–4 cycles):** calibration adjustment rate trending down (assessments converging); % action items closed by next review ≥ 60%; HR-reported reduction in rating disputes; retention of employees flagged “potential” vs baseline; client renewal of PMS module.

Measurement: in-product analytics per event (stage transitions, action-item lifecycle); quarterly metric review with each client’s HR.

## **13\. Release phasing**

* **Phase 1 (MVP):** FR-1–FR-9, FR-13–FR-16 foundations (manual KPI actuals), FR-10 upward feedback, FR-11 calibration. English UI. One reference deployment (e.g., Minda pilot plant/function).

* **Phase 2:** FR-12 talent signals, KPI actuals integrations, steering decision log, skip-level/matrix reviewers, delegation, Hindi UI.

* **Phase 3 (design-for now):** 360° multi-rater, succession/9-box workflows, compensation-module handshake, native mobile apps, WhatsApp nudges.

## **14\. Assumptions & dependencies**

* Client provides org structure, values framework, leadership principles and (with our services) rating anchors before cycle configuration.

* HRMS/ERP master-data feed is available in an agreed format at onboarding.

* Steering-committee cadence and calibration governance are agreed as part of the accompanying expert-services engagement.

* Salary-review process consuming our export is client-owned.

## **15\. Open questions**

| \# | Question | Owner | Blocking? |
| :---- | :---- | :---- | :---- |
| Q1 | Overall-rating formula options for v1: weighted-by-section, manual, or hybrid — which set ships? | Product \+ first client HR | Yes (FR-7) |
| Q2 | Does mid-year checkpoint use the full template or a light subset by default? | Product | No |
| Q3 | Minimum viable KPI data-source integrations for Phase 2 (which ERPs first)? | Engineering | No |
| Q4 | Upward feedback: ratings \+ comments, or comments only, for lowest-threshold teams? | Product \+ HR advisory | No |
| Q5 | Retention defaults per jurisdiction (DPDP vs GDPR tenants) | Legal advisory | Yes (before first production tenant) |
| Q6 | Should employee “registered disagreement” trigger a defined HR SLA in-product? | Product \+ HR advisory | No |
| Q7 | Default weight validation: must weights sum to 100%, or free-form with a warning? | Product \+ first client HR | No |
| Q8 | Do extra-initiative goals ever feed the weighted overall rating, or always additive recognition only? | Product \+ HR advisory | No |
| Q9 | In manager-led mode, is the employee’s response a full self-assessment or a structured reaction to the manager’s assessment? | Product \+ design | Yes (FR-6/FR-7 UX) |
| Q10 | Where does calibration sit relative to the dialogue/submission loop — before the final form is sent to the employee (employee sees calibrated ratings), or after employee submission (pre-salary-review only)? Recommended default: before the final form. | Product \+ HR advisory | Yes (FR-9/FR-11 sequencing) |
| Q11 | In multi-manager reviews, can the additional manager’s comment be marked private to managers/HR, or is it always employee-visible? | Product \+ HR advisory | No |

## **16\. Appendix — CatalystOne baseline mapping**

Publicly documented CatalystOne capabilities used as baseline, and how this specification extends them. (CatalystOne’s public pages describe capabilities at a marketing level; internal workflow details are not public and are **not** claimed here.)

| CatalystOne (public) | This specification |
| :---- | :---- |
| Appraisals & Goals: templated appraisal conversations; individual KPIs aligned to company goals; goals/KPIs adjustable anytime; dashboards for employee/manager/HR | FR-1, FR-2, FR-5, FR-7 — extended with enforced KPI linkage at approval, explicit past/future section structure, and steering-committee view |
| One-to-One Meetings: structured check-ins, pre-meeting prep, documented takeaways, task follow-up | FR-4 — extended with cadence targets, nudges, “intent to help” framing, HR cadence visibility without content access |
| Fast Feedback: real-time feedback and recognition across the organisation | Partially deferred — v1 carries feedback inside check-ins/reviews; standalone instant recognition is P2 |
| Calibrator: quality-assure assessments; managers reflect on and justify ratings; employee scorecards; identify high performers/potential; HR org-wide analysis | FR-11, FR-12 — extended with mandatory pre-salary-review gating, full adjustment audit trail, and support-plan flags |
| (Not publicly detailed by CatalystOne) | Upward feedback on leadership principles (FR-10), mandatory action items per dialogue (FR-9), review-state machine (§7.1) are AllAboutHR-specific requirements from our process philosophy |

[image1]: <data:image/png;base64,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>