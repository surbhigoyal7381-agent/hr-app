# Grace Group HRMS — Field-by-Field User Manual

**System:** Grace Drinks HRMS (Frappe / ERPNext)  
**Base URL:** `http://hrms.localhost:8000`  
**Login:** Administrator / admin

Every field in every form is explained below — what it means, what to type or select, where the data comes from, and a worked example. Fields marked **System** are filled automatically; do not type into them.

---

## Table of Contents

**Part 1 — Alvoraa Goals**

1. [Goal Cascade](#1-goal-cascade)
2. [Goal Cascade Version (child table)](#2-goal-cascade-version-child-table-inside-goal-cascade)
3. [Individual Goal](#3-individual-goal)
4. [Goal Evidence (child table)](#4-goal-evidence-child-table-inside-individual-goal)
5. [Goal Progress Audit Log](#5-goal-progress-audit-log-read-only)
6. [Cascade Alignment Report](#6-cascade-alignment-report-read-only)
7. [Evidence Validator](#7-evidence-validator-admin-config)
8. [Evidence Duplicate Check](#8-evidence-duplicate-check)

**Part 2 — Alvoraa Portal**

9. [Vendor](#9-vendor)
10. [Vendor Address (child table)](#10-vendor-address-child-table-inside-vendor)
11. [Vendor User](#11-vendor-user)
12. [Vendor Order](#12-vendor-order)
13. [Vendor Order Item (child table)](#13-vendor-order-item-child-table-inside-vendor-order)
14. [Delivery Assignment](#14-delivery-assignment)
15. [Delivery Tracking (child table)](#15-delivery-tracking-child-table-inside-delivery-assignment)
16. [Order Rating](#16-order-rating)
17. [Driver Rating Summary](#17-driver-rating-summary-read-only)

---

## Part 1 — Alvoraa Goals

---

### 1. Goal Cascade

**Path:** `http://hrms.localhost:8000/app/goal-cascade/new`  
**Who fills it:** HR Manager or System Manager  
**Purpose:** Defines the company-wide or division-wide target for a measurement period. All individual employee goals are children of exactly one cascade.

---

#### Document Name (auto)

| | |
|---|---|
| **Set by** | System |
| **Format** | `GD-GC-YYYY-####` |
| **Example** | `GD-GC-2026-0001` |

The system assigns this ID when you save for the first time. Never edit it manually. This ID is what you type into the `Goal Cascade` field on each Individual Goal.

---

#### Cascade Name

| | |
|---|---|
| **Required** | Yes |
| **Type** | Free text |
| **What to enter** | A human-readable name that describes the objective and period. Include the quarter or month so it is unambiguous when looked up from an Individual Goal form. |
| **Example** | `Q3 FY26 — Sales Orders (North Region)` |

Keep it short enough to fit in a dropdown without truncation — roughly 50 characters or fewer.

---

#### Company

| | |
|---|---|
| **Required** | Yes |
| **Type** | Link → Company |
| **What to enter** | Type to search and select the legal entity this cascade belongs to. In the Grace Group setup this will normally be `Grace Drinks India Pvt. Ltd.` or the specific sub-entity. |
| **Where it comes from** | The Companies list in ERPNext — `http://hrms.localhost:8000/app/company`. If the company is not listed there, ask the System Manager to create it. |
| **Example** | `Grace Drinks India Pvt. Ltd.` |

---

#### Unit

| | |
|---|---|
| **Required** | Yes |
| **Type** | Select (dropdown) |
| **Options** | `Orders`, `Revenue`, `Skill Score`, `Units Sold` |
| **What to enter** | Choose the unit that matches what is being measured. This same unit is inherited by every Individual Goal under this cascade and determines how evidence is counted. |

| Choice | Use when |
|--------|----------|
| `Orders` | You are counting the number of sales/delivery orders fulfilled (e.g. a KAM's monthly order count). Evidence uses `Extracted Order Count`. |
| `Revenue` | You are measuring rupee/dollar value of sales. Evidence uses `Extracted Amount`. |
| `Skill Score` | You are tracking training or competency scores. Evidence uses `Extracted Order Count` as a proxy score. |
| `Units Sold` | You are counting physical product units dispatched. Evidence uses `Extracted Order Count`. |

| **Example** | `Orders` (for the Q3 sales target) |

---

#### Period Start

| | |
|---|---|
| **Required** | Yes |
| **Type** | Date |
| **What to enter** | The first day of the period this cascade covers. Individual Goal start dates must fall within this range. |
| **Format** | `YYYY-MM-DD` or use the calendar picker |
| **Example** | `2026-07-01` (start of Q3 FY26) |

---

#### Period End

| | |
|---|---|
| **Required** | Yes |
| **Type** | Date |
| **What to enter** | The last day of the period. The system validates that this is after Period Start. Individual Goal end dates must fall within this range. |
| **Example** | `2026-09-30` (end of Q3 FY26) |

---

#### Company Target

| | |
|---|---|
| **Required** | Yes |
| **Type** | Float (decimal number) |
| **What to enter** | The total number the entire company or division must achieve, in the unit chosen above. This is the denominator for alignment checks — the sum of all individual goal targets is compared against this figure. |
| **Example** | `10000` (meaning 10,000 orders must be fulfilled across all employees in Q3) |

Tip: Set this to the realistic stretch target agreed in the business review, not the minimum floor. The alignment check flags a warning if individual targets collectively deviate from this by more than 5%.

---

#### Status

| | |
|---|---|
| **Required** | No (defaults to `Draft`) |
| **Type** | Select |
| **Options** | `Draft`, `Active`, `Completed`, `Archived` |

| Status | Meaning | When to use |
|--------|---------|-------------|
| `Draft` | Cascade is being set up; individual goals can still be added or edited | While you are configuring goals before the period begins |
| `Active` | Period is live; new goals cannot be added to a Completed or Archived cascade | Change to this on the period start date |
| `Completed` | All goals under this cascade have been evaluated | Change at period end after final scores are recorded |
| `Archived` | Historical record; read-only for most users | Use for old cascades you want to keep but not show in active lists |

> The system blocks adding Individual Goals to a cascade that is `Completed` or `Archived`.

---

#### Final Score Formula

| | |
|---|---|
| **Required** | No |
| **Type** | Free text (short string) |
| **What to enter** | An optional formula expression used by a scoring engine or report. Leave blank if not using weighted scoring. This field is informational — the system does not evaluate it automatically. |
| **Example** | `0.6 * orders_pct + 0.4 * revenue_pct` |

---

#### Description

| | |
|---|---|
| **Required** | No |
| **Type** | Short text (multi-line) |
| **What to enter** | A plain-English explanation of what this cascade is measuring and why. This shows on reports and alignment documents. |
| **Example** | `North region KAM team must collectively close 10,000 delivery orders in Q3 FY26 as part of the market expansion initiative.` |

---

### 2. Goal Cascade Version (child table inside Goal Cascade)

This table is inside the **Version History** section of the Goal Cascade form. **You never fill this manually.** Every time the cascade definition is changed and saved, the system appends a new row automatically.

---

#### Version No

| | |
|---|---|
| **Set by** | System |
| **What it contains** | An incrementing integer starting at 1. Version 1 is the first saved definition; version 2 is after the first edit; and so on. |
| **Example** | `3` (meaning this cascade has been edited twice since creation) |

---

#### Changed By

| | |
|---|---|
| **Set by** | System |
| **What it contains** | The Frappe username (email) of whoever saved the change. Pulled from the active session. |
| **Example** | `hr.manager@gracedrinks.in` |

---

#### Change Date

| | |
|---|---|
| **Set by** | System |
| **What it contains** | The exact timestamp when the change was saved. |
| **Example** | `2026-07-15 11:42:08` |

---

#### Previous Definition

| | |
|---|---|
| **Set by** | System |
| **What it contains** | A snapshot of the cascade's key fields before the edit, stored as a JSON or text string. Allows reconstruction of what the cascade looked like at any past version. |
| **Example** | `{"company_target": 8000, "period_end": "2026-09-30", "status": "Draft"}` |

---

#### Reason for Change

| | |
|---|---|
| **Set by** | System or User |
| **What it contains** | A short explanation of why the cascade was modified. If you want this to be useful for audits, type a reason in this field before saving. |
| **Example** | `Target revised upward from 8,000 to 10,000 after board approval on 12-Jul` |

---

### 3. Individual Goal

**Path:** `http://hrms.localhost:8000/app/individual-goal/new`  
**Who fills it:** HR Manager or HR User  
**Purpose:** Assigns a personal performance target to one employee within a cascade.

---

#### Document Name (auto)

| | |
|---|---|
| **Set by** | System |
| **Format** | `GD-IG-YYYY-####` |
| **Example** | `GD-IG-2026-0047` |

---

#### Employee

| | |
|---|---|
| **Required** | Yes |
| **Type** | Link → Employee |
| **What to enter** | Type the employee ID or name to search. Select the correct person from the dropdown. |
| **Where it comes from** | The Employee master list at `http://hrms.localhost:8000/app/employee`. The employee must already exist in the HRMS with an active status. |
| **Example** | `HR-EMP-00023` (Kavita Sharma, KAM North) |

---

#### Employee Name

| | |
|---|---|
| **Set by** | System (fetched from Employee record) |
| **What it contains** | The full name of the employee, automatically filled when you select the Employee field. |
| **Example** | `Kavita Sharma` |

Do not edit this field — it re-fetches automatically if you change the Employee.

---

#### Goal Name

| | |
|---|---|
| **Required** | Yes |
| **Type** | Free text |
| **What to enter** | A short, descriptive label for this specific goal. Should be specific enough to distinguish from other goals the same employee may have in the same period. |
| **Example** | `KAM North — Q3 FY26 Delivery Orders` |

---

#### Goal Cascade

| | |
|---|---|
| **Required** | Yes |
| **Type** | Link → Goal Cascade |
| **What to enter** | Type the cascade ID or name to search. Select the cascade this goal belongs to. The cascade must be in `Draft` or `Active` status — goals cannot be assigned to `Completed` or `Archived` cascades. |
| **Where it comes from** | The cascade you created in Step 1. Its ID looks like `GD-GC-2026-0001`. |
| **Example** | `GD-GC-2026-0001` (Q3 FY26 — Sales Orders, North Region) |

Once selected, the **Unit** field is automatically filled from the cascade.

---

#### Parent Goal

| | |
|---|---|
| **Required** | No |
| **Type** | Link → Individual Goal |
| **What to enter** | Only fill this if you want to build a hierarchy — for example, a team lead's goal is the parent and each team member's goal is a child. The parent goal must belong to **the same employee**. Linking to a goal owned by a different employee will be blocked on validation. |
| **When to leave blank** | For most individual contributors. Only team leads who have their own sub-goals need this. |
| **Example** | Leave blank for Kavita Sharma. If she manages a team, her team members' goals would point to her goal ID here. |

---

#### Target Value

| | |
|---|---|
| **Required** | Yes |
| **Type** | Float (decimal number) |
| **What to enter** | The employee's personal share of the cascade's company target. Enter the numeric value in the same unit as the cascade. |
| **Rule** | Must be greater than 0. Cannot be changed after evidence has been submitted against this goal. |
| **Example** | `1500` (Kavita is responsible for 1,500 of the 10,000 total orders) |

---

#### Unit

| | |
|---|---|
| **Set by** | System (fetched from the Goal Cascade) |
| **What it contains** | Automatically copied from the cascade's Unit field when you select the Goal Cascade. |
| **Example** | `Orders` |

---

#### Start Date

| | |
|---|---|
| **Required** | Yes |
| **Type** | Date |
| **What to enter** | When Kavita's personal target period begins. Should be within the cascade's Period Start–Period End range. Typically the same as the cascade's Period Start unless you are mid-period onboarding someone. |
| **Example** | `2026-07-01` |

---

#### End Date

| | |
|---|---|
| **Required** | Yes |
| **Type** | Date |
| **What to enter** | The last day of this employee's target period. Must be after Start Date and within the cascade's Period End. |
| **Example** | `2026-09-30` |

---

#### Status

| | |
|---|---|
| **Required** | No (defaults to `Active`) |
| **Type** | Select |
| **Options** | `Active`, `Completed`, `Cancelled` |

| Status | How it is set |
|--------|---------------|
| `Active` | Default — goal is live |
| `Completed` | Set **automatically by the system** when Progress % reaches 100% |
| `Cancelled` | Set manually if the goal is withdrawn (e.g. employee transferred) |

Do not manually set `Completed` — the system does this to ensure it happens only when evidence genuinely covers the full target.

---

#### Actual Progress

| | |
|---|---|
| **Set by** | System |
| **What it contains** | The running total calculated from all **Approved** evidence rows. For `Revenue` or `Amount` unit goals, this is the sum of `Extracted Amount` across approved rows. For all other units, it is the sum of `Extracted Order Count` across approved rows. |
| **Example** | `420` (Kavita has had 420 approved orders so far) |

---

#### Progress %

| | |
|---|---|
| **Set by** | System |
| **What it contains** | `(Actual Progress / Target Value) × 100`, capped at 100%. Updated every time evidence is approved or the hourly recalculation job runs. |
| **Example** | `28.0%` (420 out of 1,500) |

---

#### Trajectory

| | |
|---|---|
| **Set by** | System |
| **What it contains** | A status label computed by comparing the employee's actual progress against where they *should* be at this point in time, assuming linear progress is expected. |

The system first calculates the "expected %" based on how many days have elapsed:

```
expected_pct = (days elapsed since start / total days) × 100
```

Then:

| Trajectory shown | Condition |
|-----------------|-----------|
| `Not Started` | Today is on or before the Start Date |
| `On Track` | Actual % ≥ expected % |
| `At Risk` | Actual % is between 75% and 99% of expected % |
| `Off Track` | Actual % is below 75% of expected % |

**Example:** It is 15 July (day 15 of 92). Expected % = 16.3%. Kavita is at 28%. → `On Track`.  
If by 31 August (day 62 of 92, expected 67%) Kavita is only at 30% → `Off Track`.

---

#### Evidence (child table)

Covered in detail in section 4 below.

---

### 4. Goal Evidence (child table inside Individual Goal)

This table appears inside the **Evidence** section of the Individual Goal form. Each row represents one piece of proof submitted toward the goal. You add rows here; the system validates and processes them.

---

#### Evidence Type

| | |
|---|---|
| **Required** | Yes |
| **Type** | Select |
| **Options** | `Invoice`, `Sales Order`, `Manual Entry` |
| **What to enter** | Choose the type of document you are uploading as proof. The choice determines how the system validates the evidence and whether it is auto-approved. |

| Type | Auto-approval | Validation applied |
|------|--------------|-------------------|
| `Invoice` | Only if all invoice validator rules pass | Checks age (not older than `max_age_days`), amount range, and required fields |
| `Sales Order` | Always | No additional checks |
| `Manual Entry` | Never — always goes to Pending | Requires HR review |

**Example:** Kavita uploads a customer invoice from 3 July → choose `Invoice`.

---

#### Upload Date

| | |
|---|---|
| **Set by** | System (defaults to now when the row is inserted) |
| **What it contains** | The date and time the evidence row was added. |
| **Example** | `2026-07-15 14:32:00` |

If you are back-entering historical evidence, you can overwrite this to the actual date of the original transaction.

---

#### Uploaded By

| | |
|---|---|
| **Set by** | System (filled with the logged-in user) |
| **What it contains** | The Frappe username of whoever added this evidence row. |
| **Example** | `kavita.sharma@gracedrinks.in` |

---

#### Evidence File

| | |
|---|---|
| **Required** | No (recommended) |
| **Type** | File attachment |
| **What to enter** | Upload the source document — PDF invoice, Excel order sheet, photo of a signed delivery note, etc. Click the attachment icon, choose your file, and upload. Maximum size depends on your server configuration (typically 10 MB). |
| **Accepted formats** | PDF, XLSX, DOCX, PNG, JPG, or any file type the server accepts |
| **Example** | `Invoice_RajTraders_20260703.pdf` |

Attaching the file is strongly recommended for `Invoice` and `Manual Entry` types so HR can verify during review.

---

#### Extracted Order Count

| | |
|---|---|
| **Required** | No (but needed for all non-revenue goals) |
| **Type** | Integer |
| **What to enter** | The number of orders/units this one piece of evidence covers. For an invoice that covers 45 delivery orders, enter `45`. For a single order, enter `1`. |
| **How it is used** | For `Orders`, `Skill Score`, and `Units Sold` unit goals, this number is summed across all Approved rows to produce `Actual Progress`. |
| **Example** | `45` |

---

#### Extracted Amount

| | |
|---|---|
| **Required** | No (but needed for Revenue goals) |
| **Type** | Currency (INR) |
| **What to enter** | The rupee value of the transaction in this evidence row. For a ₹1,12,500 invoice, enter `112500`. |
| **How it is used** | For `Revenue` unit goals, this is summed across all Approved rows to produce `Actual Progress`. |
| **Example** | `112500` |

---

#### Extracted Date

| | |
|---|---|
| **Required** | No |
| **Type** | Date |
| **What to enter** | The date on the source document — the invoice date, order date, or transaction date. This is what the invoice validator uses to check the age of the document (it rejects invoices older than `max_age_days` set in the Evidence Validator configuration). |
| **Example** | `2026-07-03` |

---

#### Extracted Customer

| | |
|---|---|
| **Required** | No |
| **Type** | Free text |
| **What to enter** | The name of the customer or buyer from the source document. Used by the duplicate detector to compare against previously submitted evidence — two rows with identical customer + date + amount trigger a duplicate warning. |
| **Example** | `Raj Traders, Connaught Place` |

---

#### Validation Status

| | |
|---|---|
| **Set by** | System (on insert) or HR (manual review) |
| **Options** | `Pending`, `Approved`, `Rejected` |
| **What it means** | Only `Approved` rows count toward `Actual Progress`. `Pending` rows are waiting for HR review. `Rejected` rows are permanently excluded. |

| Status | When it is set |
|--------|---------------|
| `Pending` | Invoice that failed validator rules, Manual Entry type, or a duplicate was detected |
| `Approved` | Invoice that passed all rules, or any Sales Order, or HR manually approved |
| `Rejected` | HR reviewed and rejected with a reason |

You cannot manually set this to `Approved` on the form — use the approve/reject API endpoints or HR workflow described in the main guide.

---

#### Rejection Reason

| | |
|---|---|
| **Set by** | HR (when rejecting) |
| **Type** | Short text |
| **What it contains** | The reason the HR reviewer rejected this evidence row. Visible to the employee and recorded in the audit log. |
| **Example** | `Invoice date (2026-06-28) falls outside the Q3 goal period starting 2026-07-01.` |

---

#### Approved By

| | |
|---|---|
| **Set by** | System |
| **What it contains** | Username of the person or system that approved the row. `System` if auto-approved by validator rules; the HR user's email if approved manually. |
| **Example** | `hr.manager@gracedrinks.in` or `System` |

---

#### Approved On

| | |
|---|---|
| **Set by** | System |
| **What it contains** | Timestamp when the row was approved. |
| **Example** | `2026-07-15 16:05:22` |

---

#### Synced from External

| | |
|---|---|
| **Set by** | System (when evidence is pulled from an external integration) |
| **Type** | Checkbox |
| **What it contains** | Ticked if this row was inserted by an automated sync from an external ERP or order management system rather than by a human. Unticked for all manually entered rows. |
| **Example** | Unticked for most entries. Ticked if you build an ERP integration that auto-pushes approved orders. |

---

#### Raw Extracted Data

| | |
|---|---|
| **Set by** | System or Integration |
| **Type** | Long text |
| **What it contains** | A JSON or plain-text dump of the raw data pulled from an external system at the time of sync. Used for debugging and audit purposes. Leave blank for manual entries. |
| **Example** | `{"order_id": "SO-2026-4423", "customer": "Raj Traders", "amount": 112500, "date": "2026-07-03"}` |

---

### 5. Goal Progress Audit Log (read-only)

**Path:** `http://hrms.localhost:8000/app/goal-progress-audit-log`  
**Who fills it:** Nobody — 100% system-generated. Every significant event on every Individual Goal writes a row here automatically.  
**Purpose:** Immutable audit trail for compliance, disputes, and HR review.

---

#### Goal

| | |
|---|---|
| **Set by** | System |
| **What it contains** | The ID of the Individual Goal this log entry relates to. Click it to open that goal directly. |
| **Example** | `GD-IG-2026-0047` |

---

#### Event Type

| | |
|---|---|
| **Set by** | System |
| **Options** | `Created`, `Progress Updated`, `Evidence Added`, `Evidence Approved`, `Evidence Rejected`, `Cascade Changed`, `Status Changed` |

| Event Type | When it is written |
|------------|-------------------|
| `Created` | The goal record is first inserted |
| `Progress Updated` | `recalculate_progress` runs (hourly scheduler or manual trigger) |
| `Evidence Added` | Any evidence row is inserted into the goal |
| `Evidence Approved` | HR approves a pending evidence row |
| `Evidence Rejected` | HR rejects a pending evidence row |
| `Cascade Changed` | The `goal_cascade` field on the goal is changed |
| `Status Changed` | Goal is submitted, completed, or cancelled |

---

#### Changed By

| | |
|---|---|
| **Set by** | System |
| **What it contains** | The username who triggered the event. `System` for scheduler-driven events (hourly recalculation). The logged-in user's email for all human-triggered events. |
| **Example** | `hr.manager@gracedrinks.in` (for an approval) or `System` (for hourly recalc) |

---

#### Change Date

| | |
|---|---|
| **Set by** | System |
| **What it contains** | The exact timestamp the event occurred. |
| **Example** | `2026-07-15 17:00:03` |

---

#### Old Value

| | |
|---|---|
| **Set by** | System |
| **What it contains** | What the relevant field contained *before* the event. For `Progress Updated` this is the previous `actual_progress` number. For `Status Changed` this is the previous status. For `Evidence Added` this is blank (there was no previous value). |
| **Example** | `360` (previous order count before recalculation added 60 new orders) |

---

#### New Value

| | |
|---|---|
| **Set by** | System |
| **What it contains** | What the relevant field became *after* the event. |
| **Example** | `420` |

---

#### IP Address

| | |
|---|---|
| **Set by** | System |
| **What it contains** | The IP address of the client that made the change. Useful for security audits. Empty for scheduler-triggered events. |
| **Example** | `192.168.1.45` |

---

#### Reason

| | |
|---|---|
| **Set by** | System (passes a brief description of the trigger) |
| **What it contains** | A short English description of why this event occurred. |

| Event | Reason written by system |
|-------|--------------------------|
| `Created` | `Goal created` |
| `Evidence Added` | `Evidence type: Invoice, status: Approved` |
| `Progress Updated` | `Recalculated from approved evidence` |
| `Evidence Approved` | (blank — written by HR controller) |
| `Evidence Rejected` | The rejection reason HR typed |
| `Status Changed` | `Goal submitted` |

---

### 6. Cascade Alignment Report (read-only)

**Path:** `http://hrms.localhost:8000/app/cascade-alignment-report`  
**Who fills it:** System — generated automatically when you call the alignment check API or when the daily scheduler runs. HR Managers can also trigger it manually.

---

#### Goal Cascade

| | |
|---|---|
| **Set by** | System |
| **What it contains** | The cascade this report analyses. |
| **Example** | `GD-GC-2026-0001` |

---

#### Report Date

| | |
|---|---|
| **Set by** | System |
| **What it contains** | The timestamp when this report was generated. |
| **Example** | `2026-07-15 09:00:04` |

---

#### Generated By

| | |
|---|---|
| **Set by** | System |
| **What it contains** | Username of whoever triggered the report, or `System` for scheduler-generated reports. |
| **Example** | `System` |

---

#### Company Target

| | |
|---|---|
| **Set by** | System (copied from the cascade at report time) |
| **What it contains** | The cascade's `Company Target` value at the moment this report was run. |
| **Example** | `10000` |

---

#### Sum of Division Targets

| | |
|---|---|
| **Set by** | System |
| **What it contains** | The arithmetic sum of `Target Value` across all submitted Individual Goals under this cascade at report time. |
| **Example** | `9800` (all 8 KAMs combined are targeting 9,800 — short of 10,000) |

---

#### Variance %

| | |
|---|---|
| **Set by** | System |
| **Formula** | `|Company Target − Sum of Division Targets| / Company Target × 100` |
| **What it contains** | How far off the sum of individual targets is from the company target, expressed as a percentage. |
| **Example** | `2.0%` (200 orders gap on a 10,000 target → 2% variance) |

---

#### Status

| | |
|---|---|
| **Set by** | System |
| **Options** | `Aligned`, `Misaligned`, `Not Enough Data` |

| Status | Condition |
|--------|-----------|
| `Aligned` | Variance % is less than 5% |
| `Misaligned` | Variance % is 5% or more |
| `Not Enough Data` | No submitted Individual Goals exist under the cascade yet |

**Example:** 2% variance → `Aligned`. Action: none needed.  
If status is `Misaligned`, review which employees are under-targeted and adjust their `Target Value` fields (only possible before evidence is submitted).

---

#### Details

| | |
|---|---|
| **Set by** | System |
| **What it contains** | A plain-English summary sentence of the numbers. |
| **Example** | `Company target: 10000, Sum of individual goal targets: 9800.00, Variance: 2.0%` |

---

### 7. Evidence Validator (admin config)

**Path:** `http://hrms.localhost:8000/app/evidence-validator`  
**Who fills it:** System Manager (one-time setup). Employees and HR Users cannot access this form.  
**Purpose:** Defines the rules the auto-validator applies to `Invoice` type evidence. Multiple validators can exist — all enabled validators matching the evidence type are applied.

---

#### Validator Name

| | |
|---|---|
| **Required** | Yes |
| **Type** | Free text |
| **What to enter** | A unique, descriptive name for this rule set. |
| **Example** | `Grace Drinks Invoice Rules v1` |

---

#### Evidence Type

| | |
|---|---|
| **Required** | Yes |
| **Type** | Select (`Invoice`, `Sales Order`, `Manual Entry`) |
| **What to enter** | The type of evidence this validator applies to. Currently, meaningful validation is only implemented for `Invoice`. |
| **Example** | `Invoice` |

---

#### Enabled

| | |
|---|---|
| **Required** | No (defaults to ticked) |
| **Type** | Checkbox |
| **What to enter** | Leave ticked to activate this validator. Untick to temporarily disable without deleting. |

---

#### Validator Logic

| | |
|---|---|
| **Required** | No |
| **Type** | Long text (JSON) |
| **What to enter** | A JSON object defining the rules. The invoice validator reads these keys: |

| JSON key | Meaning | Example value |
|----------|---------|--------------|
| `max_age_days` | Reject invoices older than this many days relative to today | `30` (invoices more than 30 days old are rejected) |
| `min_amount` | Reject invoices below this amount (INR) | `1000` |
| `max_amount` | Reject invoices above this amount (INR) | `5000000` |
| `require_amount_match` | If true, `Extracted Amount` must match the goal's expected range | `false` |

**Full example value for this field:**

```json
{
  "max_age_days": 30,
  "min_amount": 1000,
  "max_amount": 5000000,
  "require_amount_match": false
}
```

---

#### Description

| | |
|---|---|
| **Required** | No |
| **Type** | Short text |
| **What to enter** | A human-readable note explaining what this validator does and when it was set up. |
| **Example** | `Standard invoice rules for Grace Drinks KAM goals — approved by Head of Sales 2026-07-01` |

---

### 8. Evidence Duplicate Check

**Path:** `http://hrms.localhost:8000/app/evidence-duplicate-check`  
**Who fills it:** Mostly system-generated. HR Managers update the `Action Taken` field after reviewing.

---

#### Evidence 1 / Evidence 2

| | |
|---|---|
| **Set by** | System |
| **What it contains** | Internal identifiers (row indices or keys) of the two evidence rows that the duplicate detector determined are similar. |
| **Example** | `GD-IG-2026-0047 row 3` and `GD-IG-2026-0031 row 7` |

---

#### Goal 1 / Goal 2

| | |
|---|---|
| **Set by** | System |
| **What it contains** | The Individual Goal documents that contain the two suspicious evidence rows. |
| **Example** | `GD-IG-2026-0047` (Kavita's goal) and `GD-IG-2026-0031` (Priya's goal) |

---

#### Similarity Score

| | |
|---|---|
| **Set by** | System |
| **What it contains** | The percentage similarity the duplicate detector calculated between the two evidence rows. Higher = more likely to be the same underlying document submitted twice. |
| **Example** | `94%` (very likely the same invoice submitted by two different employees) |

---

#### Flagged By

| | |
|---|---|
| **Set by** | System |
| **Options** | `System`, `Manual` |
| **What it contains** | Whether the flag was raised by the automatic duplicate detector or by an HR user manually. |

---

#### Action Taken

| | |
|---|---|
| **Set by** | HR Manager (after review) |
| **Options** | `Pending Review`, `Merged`, `Rejected`, `Approved as Separate` |

| Action | Meaning | What to do next |
|--------|---------|-----------------|
| `Pending Review` | Default — HR has not yet looked at this | Review both evidence rows and the uploaded files |
| `Merged` | Both rows describe the same transaction — keep one, reject the other | Manually reject the duplicate evidence row on the Individual Goal |
| `Rejected` | Both rows are invalid | Reject both evidence rows on the respective goals |
| `Approved as Separate` | Investigation confirmed they are genuinely different transactions | Approve both evidence rows normally |

---

#### Notes

| | |
|---|---|
| **Set by** | HR Manager |
| **Type** | Short text |
| **What to enter** | Your findings after reviewing the two documents. |
| **Example** | `Both employees submitted the same Raj Traders invoice from 3-Jul. Kavita submitted it first — kept. Priya's submission rejected as duplicate.` |

---

## Part 2 — Alvoraa Portal

---

### 9. Vendor

**Path:** `http://hrms.localhost:8000/app/vendor/new`  
**Who fills it:** HR Manager or System Manager  
**Purpose:** Master record for each company or individual that supplies goods or services to Grace Group.

---

#### Document Name (auto)

| | |
|---|---|
| **Set by** | System |
| **Format** | `GD-VND-YYYY-####` |
| **Example** | `GD-VND-2026-0012` |

---

#### Vendor Name

| | |
|---|---|
| **Required** | Yes |
| **Type** | Free text |
| **What to enter** | The display name you will use internally to refer to this vendor. This is what appears in dropdowns on Vendor Order forms. Keep it short and recognisable — not necessarily the full legal name. |
| **Example** | `Raj Beverages` |

---

#### Company Name

| | |
|---|---|
| **Required** | Yes |
| **Type** | Free text |
| **What to enter** | The full registered legal name of the vendor's entity, as it appears on their GST certificate and invoices. This is used on formal documents. |
| **Example** | `Raj Beverages Private Limited` |

---

#### Email

| | |
|---|---|
| **Required** | Yes |
| **Type** | Email address |
| **What to enter** | The primary business email of the vendor's account manager or operations contact. Order notifications and system alerts are sent here. |
| **Validation** | Must be a valid email format (contains `@` and a domain). |
| **Example** | `orders@rajbeverages.in` |

---

#### Phone

| | |
|---|---|
| **Required** | Yes |
| **Type** | Free text (phone number) |
| **What to enter** | The main phone number for placing orders or escalating issues. Include country code for international vendors. |
| **Example** | `+91-98101-55234` |

---

#### GST Number

| | |
|---|---|
| **Required** | No (recommended) |
| **Type** | Free text |
| **What to enter** | The vendor's 15-character GST Identification Number (GSTIN). Format: `2-digit state code + 10-char PAN + 1-char entity number + 1-char Z + 1-char check digit`. Required for GST compliance on purchase invoices. |
| **Example** | `07AABCR1234M1Z5` |

Leave blank only for vendors who are GST-exempt (e.g. small unregistered suppliers below the threshold).

---

#### Account Status

| | |
|---|---|
| **Required** | No (defaults to `Active`) |
| **Type** | Select |
| **Options** | `Active`, `Inactive`, `Suspended` |

| Status | Meaning | When to use |
|--------|---------|-------------|
| `Active` | Vendor is approved to receive orders | Standard state for all working vendors |
| `Inactive` | Vendor has paused operations or the relationship is on hold | Seasonal vendor not currently supplying |
| `Suspended` | Vendor has been blocked — e.g. compliance failure, fraud, or major dispute | Use with caution; requires management approval |

New Vendor Orders can only be placed for `Active` vendors.

---

#### Account Balance

| | |
|---|---|
| **Required** | No (defaults to `0`) |
| **Type** | Currency (INR) |
| **What to enter** | The current outstanding balance owed to or by the vendor. Positive = Grace owes the vendor money. Negative = vendor owes Grace a refund or credit note. |
| **Maintenance** | Update this manually as payments are processed, or integrate with ERPNext's Accounts Payable for automatic reconciliation. |
| **Example** | `45000` (Grace owes ₹45,000 against recent orders not yet paid) |

---

### 10. Vendor Address (child table inside Vendor)

Located in the **Addresses** section of the Vendor form. Add as many rows as the vendor has relevant addresses — at minimum one Billing address.

---

#### Address Type

| | |
|---|---|
| **Required** | Yes |
| **Type** | Select |
| **Options** | `Billing`, `Shipping` |

| Type | Meaning |
|------|---------|
| `Billing` | Address to use on purchase orders and invoices sent to this vendor |
| `Shipping` | Address where goods from this vendor are dispatched from (their warehouse) |

**Example:** Add one `Billing` row for the vendor's registered office, then a `Shipping` row for their warehouse in a different location.

---

#### Address Line 1

| | |
|---|---|
| **Required** | Yes |
| **Type** | Free text |
| **What to enter** | Building number, street name, or plot/door number — the first line of the postal address. |
| **Example** | `Plot 14, Sector 5, Industrial Area` |

---

#### Address Line 2

| | |
|---|---|
| **Required** | No |
| **Type** | Free text |
| **What to enter** | Apartment, floor, landmark, or any continuation of the address that does not fit on line 1. |
| **Example** | `Near Metro Station, Opp. Sadar Bazaar` |

---

#### City

| | |
|---|---|
| **Required** | Yes |
| **Type** | Free text |
| **What to enter** | The city name as used in postal addressing. |
| **Example** | `New Delhi` |

---

#### State

| | |
|---|---|
| **Required** | No |
| **Type** | Free text |
| **What to enter** | The Indian state or union territory. |
| **Example** | `Delhi` |

---

#### Pincode

| | |
|---|---|
| **Required** | No |
| **Type** | Free text (6-digit string) |
| **What to enter** | The Indian postal code (PIN). |
| **Example** | `110005` |

---

#### Is Default

| | |
|---|---|
| **Required** | No (defaults to unticked) |
| **Type** | Checkbox |
| **What to enter** | Tick on the address that should be pre-selected when this vendor is linked in an order or communication. Only one address per vendor should have this ticked. |
| **Example** | Tick on the Billing address row. |

---

### 11. Vendor User

**Path:** `http://hrms.localhost:8000/app/vendor-user/new`  
**Who fills it:** System Manager  
**Purpose:** Gives a specific contact person at a vendor company a login to the Grace Group vendor portal (`/vendor-portal`). Each Vendor User maps one vendor-side contact to one Frappe system user.

---

#### Document Name (auto)

| | |
|---|---|
| **Set by** | System |
| **Format** | `GD-VU-YYYY-####` |
| **Example** | `GD-VU-2026-0003` |

---

#### Vendor

| | |
|---|---|
| **Required** | Yes |
| **Type** | Link → Vendor |
| **What to enter** | The vendor company this user contact belongs to. |
| **Example** | `GD-VND-2026-0012` (Raj Beverages) |

---

#### Email

| | |
|---|---|
| **Required** | Yes |
| **Type** | Email address |
| **What to enter** | The vendor contact's personal email address. This becomes their login username in the portal. Must be unique — no two Vendor Users can share the same email. |
| **Example** | `priya.sharma@rajbeverages.in` |

---

#### Phone

| | |
|---|---|
| **Required** | No |
| **Type** | Free text |
| **What to enter** | The vendor contact's direct phone number. Used by Grace ops team for delivery coordination. |
| **Example** | `+91-99110-42367` |

---

#### Frappe User

| | |
|---|---|
| **Required** | No |
| **Type** | Link → User |
| **What to enter** | The corresponding Frappe system user account (`User` doctype). Create the Frappe user first at `http://hrms.localhost:8000/app/user/new`, then link it here. |
| **Where it comes from** | The Users list at `http://hrms.localhost:8000/app/user`. |
| **Example** | `priya.sharma@rajbeverages.in` (the Frappe User record with this email) |

---

#### 2FA Enabled

| | |
|---|---|
| **Required** | No (defaults to ticked) |
| **Type** | Checkbox |
| **What to enter** | Leave ticked for all portal users — two-factor authentication is mandatory for vendor portal security. Only untick during initial onboarding testing, then re-enable. |

---

#### Last Login

| | |
|---|---|
| **Set by** | System |
| **What it contains** | The timestamp of this vendor user's most recent successful login to the portal. |
| **Example** | `2026-07-14 09:15:33` |

---

#### Account Locked

| | |
|---|---|
| **Set by** | System (after too many failed login attempts) |
| **Type** | Checkbox |
| **What it means** | When ticked, this account cannot log in. |
| **To unlock** | Untick this field manually, then save. |
| **Example** | Ticked after 5 consecutive wrong passwords. |

---

#### Failed Attempts

| | |
|---|---|
| **Set by** | System |
| **Type** | Integer |
| **What it contains** | The number of consecutive failed login attempts since the last successful login. Resets to 0 on successful login. Triggers account lock above a threshold. |
| **Example** | `3` |

---

### 12. Vendor Order

**Path:** `http://hrms.localhost:8000/app/vendor-order/new`  
**Who fills it:** HR Manager or the vendor through the portal  
**Purpose:** Records a single purchase or supply request from a vendor, from order placement through to delivery and rating.

---

#### Document Name (auto)

| | |
|---|---|
| **Set by** | System |
| **Format** | `GD-VO-YYYY-####` |
| **Example** | `GD-VO-2026-0023` |

---

#### Vendor

| | |
|---|---|
| **Required** | Yes |
| **Type** | Link → Vendor |
| **What to enter** | Type to search and select the vendor who is supplying this order. Only `Active` vendors should be used. |
| **Example** | `GD-VND-2026-0012` (Raj Beverages) |

---

#### Vendor Name

| | |
|---|---|
| **Set by** | System (fetched from the Vendor record) |
| **What it contains** | The `Vendor Name` field from the linked Vendor, filled automatically. |
| **Example** | `Raj Beverages` |

---

#### Order Date

| | |
|---|---|
| **Required** | Yes |
| **Type** | Date |
| **Default** | Today |
| **What to enter** | The date the order is being placed. Defaults to today — change this only when back-entering a historical order. |
| **Example** | `2026-07-15` |

---

#### Delivery Address

| | |
|---|---|
| **Required** | Yes |
| **Type** | Short text (multi-line) |
| **What to enter** | The full address where Grace Drinks needs the goods delivered. Write clearly — the driver uses this as their navigation destination. Paste from an address in the vendor's address table or type a Grace warehouse address. |
| **Example** | `Grace Drinks Warehouse, Plot 22, Sector 18, Gurugram, Haryana - 122015` |

---

#### Delivery Slot

| | |
|---|---|
| **Required** | Yes |
| **Type** | Select |
| **Options** | `Today`, `Tomorrow`, `Next 2 Days`, `Next 3 Days` |
| **What to enter** | Choose the expected delivery window relative to the order date. |

| Slot | Meaning |
|------|---------|
| `Today` | Delivery expected on the order date itself |
| `Tomorrow` | Delivery expected the day after order date |
| `Next 2 Days` | Delivery within two days of order date |
| `Next 3 Days` | Delivery within three days of order date |

**Example:** An emergency restocking order placed on 15-Jul → choose `Today`.

---

#### Special Instructions

| | |
|---|---|
| **Required** | No |
| **Type** | Short text |
| **What to enter** | Any handling, storage, or delivery instructions specific to this order. The driver and warehouse team can read this. |
| **Example** | `Cold chain required — deliver directly to the cold storage bay. Do not leave unattended.` |

---

#### Order Status

| | |
|---|---|
| **Required** | No (defaults to `Draft`) |
| **Type** | Select |
| **Options** | `Draft`, `Under Review`, `Approved`, `Packing`, `Ready for Dispatch`, `Dispatched`, `In Transit`, `Delivered`, `Cancelled` |

Update this field manually as the order progresses. Each status represents a stage in the fulfillment lifecycle:

| Status | Who updates it | Meaning |
|--------|---------------|---------|
| `Draft` | Creator | Order is being entered; can still be edited freely |
| `Under Review` | Operations / HR | Order sent for internal approval |
| `Approved` | HR Manager | Order confirmed, vendor notified to prepare |
| `Packing` | Warehouse team | Vendor is packing the goods |
| `Ready for Dispatch` | Warehouse team | Goods are packed and ready for driver pickup |
| `Dispatched` | Logistics | Vendor has handed off to driver |
| `In Transit` | Driver / System | Goods are on the road |
| `Delivered` | Driver / System | Recipient has confirmed receipt |
| `Cancelled` | Authorised user | Order voided at any stage before Delivered |

---

#### Total Amount

| | |
|---|---|
| **Set by** | System |
| **What it contains** | The sum of all `Line Total` values across the Items child table. Recalculated automatically whenever an item row is added or changed. |
| **Example** | `₹85,500` |

---

#### Items (child table)

Covered in detail in section 13 below.

---

#### Delivery Assignment

| | |
|---|---|
| **Set by** | System |
| **Type** | Link → Delivery Assignment (read-only) |
| **What it contains** | Automatically filled when you create a Delivery Assignment document for this order. Shows the ID of the assignment — click it to open the assignment form. |
| **Example** | `GD-DA-2026-0007` |

---

#### Rating Submitted

| | |
|---|---|
| **Set by** | System |
| **Type** | Checkbox (read-only) |
| **What it contains** | Ticked automatically when an Order Rating document is saved for this order. Prevents duplicate ratings. |
| **Example** | Unticked until after delivery when a rating is submitted. |

---

### 13. Vendor Order Item (child table inside Vendor Order)

Located in the **Items** section. Each row is one line item in the order.

---

#### SKU

| | |
|---|---|
| **Required** | Yes |
| **Type** | Free text |
| **What to enter** | The product's Stock Keeping Unit code — the unique identifier for this product in Grace Group's inventory or the vendor's catalog. If no formal SKU exists yet, use a meaningful short code. |
| **Example** | `GD-COLA-2L-CASE12` (Grace Drinks cola 2L, case of 12 bottles) |

---

#### Quantity

| | |
|---|---|
| **Required** | Yes |
| **Type** | Float |
| **Default** | `1` |
| **What to enter** | How many units of this SKU are being ordered. Can be a decimal for weight-based items (e.g. `2.5` for 2.5 kg). |
| **Example** | `500` (500 cases) |

---

#### Unit Price

| | |
|---|---|
| **Required** | Yes |
| **Type** | Currency (INR) |
| **What to enter** | The price per one unit of this SKU as agreed with the vendor. This is the price per case, per kg, or per item — matching the unit of `Quantity`. |
| **Example** | `171` (₹171 per case) |

---

#### Line Total

| | |
|---|---|
| **Set by** | System |
| **What it contains** | `Quantity × Unit Price`. Recalculated automatically when either field changes. |
| **Example** | `85,500` (500 × ₹171) |

---

### 14. Delivery Assignment

**Path:** `http://hrms.localhost:8000/app/delivery-assignment/new`  
**Who fills it:** Logistics coordinator or warehouse supervisor  
**Purpose:** Assigns a specific driver and vehicle to deliver a Vendor Order. Created once the order reaches `Ready for Dispatch` status.

---

#### Document Name (auto)

| | |
|---|---|
| **Set by** | System |
| **Format** | `GD-DA-YYYY-####` |
| **Example** | `GD-DA-2026-0007` |

---

#### Vendor Order

| | |
|---|---|
| **Required** | Yes |
| **Type** | Link → Vendor Order |
| **What to enter** | The order being dispatched in this assignment. Type the order number to search. Only one Delivery Assignment should exist per Vendor Order. |
| **Example** | `GD-VO-2026-0023` |

---

#### Driver

| | |
|---|---|
| **Required** | Yes |
| **Type** | Link → Employee |
| **What to enter** | Search for the employee who is assigned to drive this delivery. The employee must exist in the HRMS with an active status. Choose from employees whose designation is in the Logistics/Driver category. |
| **Where it comes from** | The Employee list at `http://hrms.localhost:8000/app/employee`. |
| **Example** | `HR-EMP-00089` (Ranjit Singh, driver) |

---

#### Driver Name

| | |
|---|---|
| **Set by** | System (fetched from the Employee record) |
| **What it contains** | The employee's full name, auto-filled when you select the Driver. |
| **Example** | `Ranjit Singh` |

---

#### Driver Phone

| | |
|---|---|
| **Required** | No |
| **Type** | Free text |
| **What to enter** | The driver's mobile number for this delivery. The vendor and recipient can use this to coordinate. Pre-fill from the driver's employee record if available; update if the driver is using a different number for this delivery. |
| **Example** | `+91-93110-87654` |

---

#### Vehicle Registration

| | |
|---|---|
| **Required** | Yes |
| **Type** | Free text |
| **What to enter** | The vehicle's registration plate number exactly as it appears on the vehicle. Used for security checks at delivery points and for audit records. |
| **Example** | `DL-1C-AB-4567` |

---

#### Assigned Datetime

| | |
|---|---|
| **Required** | Yes |
| **Type** | Datetime |
| **What to enter** | The exact date and time the driver was briefed and the delivery assignment was officially created. Use the calendar/time picker. |
| **Example** | `2026-07-15 13:00:00` |

---

#### Estimated Delivery

| | |
|---|---|
| **Required** | No |
| **Type** | Datetime |
| **What to enter** | The expected date and time the driver will reach the delivery address. Calculated from the delivery slot on the order and the route. This is communicated to the recipient. |
| **Example** | `2026-07-15 16:30:00` (3.5 hours after dispatch) |

---

#### Status

| | |
|---|---|
| **Required** | No (defaults to `Assigned`) |
| **Type** | Select |
| **Options** | `Assigned`, `In Transit`, `Arrived`, `Delivered`, `Failed` |

Update this as the delivery progresses:

| Status | When | Who updates |
|--------|------|-------------|
| `Assigned` | Driver has accepted the job | Auto on creation |
| `In Transit` | Driver has picked up the goods from vendor/warehouse | Logistics or driver via app |
| `Arrived` | Driver is at the delivery address | Driver |
| `Delivered` | Goods handed over; OTP verified | Driver after verification |
| `Failed` | Delivery could not be completed | Driver/Logistics; must add a Tracking History remark |

---

#### Delivery OTP

| | |
|---|---|
| **Required** | No |
| **Type** | Free text |
| **What to enter** | A 4-6 digit one-time password sent to the recipient's registered mobile at dispatch. The driver must collect this from the recipient at the doorstep to confirm identity before handover. |
| **How to generate** | Create the OTP externally (SMS service or in-app generator) and paste it here. The system stores it for verification records but does not send SMS natively. |
| **Example** | `847263` |

---

#### OTP Verified

| | |
|---|---|
| **Required** | No (defaults to unticked) |
| **Type** | Checkbox |
| **What to enter** | Tick this after the driver confirms the recipient quoted the correct OTP. This is proof of delivery to the right person. Do not tick until the driver physically verifies it at the door. |

---

#### Delivery Photo

| | |
|---|---|
| **Required** | No (strongly recommended) |
| **Type** | File attachment |
| **What to enter** | A photograph taken by the driver at the point of delivery — showing the goods placed at the address, or the recipient signing/acknowledging. Upload via the attachment icon. |
| **Accepted formats** | JPG, PNG, PDF |
| **Example** | `delivery_GD-VO-0023_15jul.jpg` |

---

#### Tracking History (child table)

Covered in detail in section 15 below.

---

### 15. Delivery Tracking (child table inside Delivery Assignment)

Located in the **Tracking History** section. Each row is one GPS/status ping. Under normal operation these rows are added automatically by the `update_delivery_tracking` scheduler job. You can also add rows manually to record milestones.

---

#### Current Latitude

| | |
|---|---|
| **Required** | No |
| **Type** | Float (decimal degrees) |
| **What to enter** | The driver's GPS latitude at the time of this update. Positive for north, negative for south. Sourced from the driver's mobile app or GPS tracker. |
| **Example** | `28.6139` (New Delhi area) |

---

#### Current Longitude

| | |
|---|---|
| **Required** | No |
| **Type** | Float (decimal degrees) |
| **What to enter** | The driver's GPS longitude. Positive for east, negative for west. |
| **Example** | `77.2090` (New Delhi area) |

---

#### Updated Timestamp

| | |
|---|---|
| **Required** | Yes |
| **Type** | Datetime |
| **What to enter** | The exact moment this location or status reading was taken. For automated entries this is set by the scheduler. For manual entries use the current time. |
| **Example** | `2026-07-15 14:45:22` |

---

#### ETA (minutes)

| | |
|---|---|
| **Required** | No |
| **Type** | Integer |
| **What to enter** | The estimated number of minutes remaining until the driver reaches the delivery address, as calculated at the time of this update. |
| **Example** | `35` (driver is 35 minutes away at this ping) |

---

#### Delivery Status

| | |
|---|---|
| **Required** | No |
| **Type** | Select |
| **Options** | `In Transit`, `Arrived`, `Delivered` |
| **What to enter** | The delivery stage at the time of this tracking ping. This is a snapshot per row — the overall delivery status is on the parent Delivery Assignment form. |
| **Example** | `In Transit` at 14:45; then `Arrived` at 16:20; then `Delivered` at 16:35. |

---

#### Remarks

| | |
|---|---|
| **Required** | No |
| **Type** | Short text |
| **What to enter** | Any notes relevant to this tracking event — traffic delays, re-routing, driver calling the recipient, access issue at delivery point, etc. |
| **Example** | `Heavy traffic on NH-8; ETA pushed by 20 minutes. Recipient notified.` |

---

### 16. Order Rating

**Path:** `http://hrms.localhost:8000/app/order-rating/new`  
**Who fills it:** Recipient / HR / Operations team after delivery is confirmed  
**Purpose:** Collects structured feedback on a completed delivery across three dimensions. Automatically calculates an average and flags low-quality deliveries for escalation.

---

#### Document Name (auto)

| | |
|---|---|
| **Set by** | System |
| **Format** | `GD-OR-YYYY-####` |
| **Example** | `GD-OR-2026-0031` |

---

#### Vendor Order

| | |
|---|---|
| **Required** | Yes |
| **Type** | Link → Vendor Order |
| **What to enter** | The order being rated. Only one rating per order is allowed — the system sets the `Rating Submitted` flag on the order after this is saved. |
| **Example** | `GD-VO-2026-0023` |

---

#### Vendor

| | |
|---|---|
| **Required** | Yes |
| **Type** | Link → Vendor |
| **What to enter** | The vendor who fulfilled this order. Usually the same vendor as on the linked Vendor Order — link it explicitly for reporting purposes. |
| **Example** | `GD-VND-2026-0012` (Raj Beverages) |

---

#### Driver

| | |
|---|---|
| **Required** | No |
| **Type** | Link → Employee |
| **What to enter** | The driver who made the delivery, linked from the Delivery Assignment. Look up the driver from the linked Delivery Assignment and select their employee ID here. |
| **Example** | `HR-EMP-00089` (Ranjit Singh) |

---

#### Rating Date

| | |
|---|---|
| **Required** | Yes |
| **Type** | Datetime |
| **What to enter** | The date and time when this feedback was collected. Use the current timestamp for real-time ratings. For delayed feedback, use the actual date the recipient provided it. |
| **Example** | `2026-07-15 17:10:00` |

---

#### Order Quality Rating

| | |
|---|---|
| **Required** | Yes |
| **Type** | Integer |
| **Scale** | 1 (very poor) to 5 (excellent) |
| **What to rate** | The quality and condition of the goods delivered — were they correct, undamaged, properly packaged, and as ordered? |

| Score | Meaning |
|-------|---------|
| `5` | Perfect — exactly what was ordered, pristine condition |
| `4` | Good — minor issue such as slight packaging damage but goods intact |
| `3` | Acceptable — some items wrong or slightly damaged |
| `2` | Poor — significant portion of order wrong or damaged |
| `1` | Unacceptable — major items missing, severely damaged, or wrong goods |

**Example:** `4` — correct items delivered but two cartons were slightly dented.

---

#### Delivery Timeliness Rating

| | |
|---|---|
| **Required** | Yes |
| **Type** | Integer |
| **Scale** | 1 to 5 |
| **What to rate** | How on-time the delivery was relative to the agreed Delivery Slot or Estimated Delivery time. |

| Score | Meaning |
|-------|---------|
| `5` | Arrived exactly on time or early |
| `4` | Arrived within 30 minutes of estimated time |
| `3` | Arrived 30–60 minutes late |
| `2` | Arrived 1–2 hours late |
| `1` | Arrived more than 2 hours late or did not arrive on the agreed day |

**Example:** `3` — driver arrived 45 minutes after the estimated 16:30 slot.

---

#### Driver Professionalism Rating

| | |
|---|---|
| **Required** | Yes |
| **Type** | Integer |
| **Scale** | 1 to 5 |
| **What to rate** | The driver's conduct, communication, and professionalism during the delivery interaction. |

| Score | Meaning |
|-------|---------|
| `5` | Excellent — courteous, proactive communication, followed all instructions |
| `4` | Good — polite and helpful |
| `3` | Neutral — professional but minimal interaction |
| `2` | Poor — impolite or failed to follow delivery instructions |
| `1` | Unacceptable — rude, unresponsive, or created a safety concern |

**Example:** `5` — Ranjit called ahead, arrived with OTP, and helped unload carefully.

---

#### Average Rating

| | |
|---|---|
| **Set by** | System |
| **What it contains** | `(Order Quality + Delivery Timeliness + Driver Professionalism) / 3`, rounded to two decimal places. Calculated automatically on save. |
| **Example** | `4.0` (from scores 4 + 3 + 5 = 12, divided by 3) |

---

#### Comments

| | |
|---|---|
| **Required** | No |
| **Type** | Short text (free text) |
| **What to enter** | Any additional feedback that does not fit the rating scores — specific praise, a complaint narrative, or context for a low score. This text is reviewed by operations managers for escalated orders. |
| **Example** | `Delivery was late because the driver had a tyre puncture on the expressway. He called ahead and managed the situation well. Dented cartons appear to have been loaded by the vendor, not the driver.` |

---

#### Issue Category

| | |
|---|---|
| **Required** | No (defaults to `None`) |
| **Type** | Select |
| **Options** | `None`, `Damaged Goods`, `Late Delivery`, `Unprofessional Driver`, `Wrong Items`, `Other` |
| **What to enter** | If there was a specific type of problem with this delivery, categorise it here. This drives escalation logic and reporting — orders with any category other than `None` appear in the issues dashboard. |

| Category | When to select |
|----------|---------------|
| `None` | Delivery was satisfactory or better |
| `Damaged Goods` | Physical damage to packaging or product |
| `Late Delivery` | Arrived significantly outside the agreed window |
| `Unprofessional Driver` | Conduct issue with the driver |
| `Wrong Items` | Incorrect products or quantities delivered |
| `Other` | Any issue not fitting the above — explain in Comments |

**Example:** `Damaged Goods` — two cartons arrived with crushed corners.

---

#### Escalated

| | |
|---|---|
| **Set by** | System |
| **Type** | Checkbox (read-only) |
| **What it contains** | Ticked automatically by the system if the `Average Rating` falls below an escalation threshold OR if `Issue Category` is not `None`. When ticked, the order appears in the escalation queue for management review. |
| **Example** | Unticked for Average Rating 4.0 with `None` issue. Ticked for Average Rating 2.3 with `Damaged Goods`. |

You do not set this manually. To de-escalate an order after it has been resolved, add a note in Comments explaining the resolution — the system does not automatically remove the flag.

---

### 17. Driver Rating Summary (read-only)

**Path:** `http://hrms.localhost:8000/app/driver-rating-summary`  
**Who fills it:** System only — the `calculate_driver_ratings` scheduler job (runs hourly) creates or updates one summary record per driver.  
**Purpose:** Aggregates all Order Ratings for a single driver into a rolling performance summary. Use this to identify top and bottom performers, assign priority deliveries, or trigger HR action.

---

#### Driver

| | |
|---|---|
| **Set by** | System |
| **What it contains** | The Employee record of the driver this summary covers. |
| **Example** | `HR-EMP-00089` |

---

#### Driver Name

| | |
|---|---|
| **Set by** | System (fetched from Employee) |
| **What it contains** | The driver's full name. |
| **Example** | `Ranjit Singh` |

---

#### Avg Quality Rating

| | |
|---|---|
| **Set by** | System |
| **What it contains** | The arithmetic mean of `Order Quality Rating` across all Order Rating records where this driver is linked, calculated at the time of the last hourly update. |
| **Example** | `4.2` |

---

#### Avg Timeliness Rating

| | |
|---|---|
| **Set by** | System |
| **What it contains** | The mean of `Delivery Timeliness Rating` across all ratings for this driver. |
| **Example** | `3.8` |

---

#### Avg Professionalism Rating

| | |
|---|---|
| **Set by** | System |
| **What it contains** | The mean of `Driver Professionalism Rating` across all ratings for this driver. |
| **Example** | `4.7` |

---

#### Total Ratings

| | |
|---|---|
| **Set by** | System |
| **What it contains** | The count of Order Rating records included in this summary. A higher count means the averages are more statistically reliable. |
| **Example** | `47` (driver has completed 47 rated deliveries) |

---

#### Last Updated

| | |
|---|---|
| **Set by** | System |
| **What it contains** | The timestamp when the scheduler last recalculated this summary. Recalculates every hour. |
| **Example** | `2026-07-15 17:00:06` |

---

*End of field reference. For workflow steps and URLs see the accompanying step-by-step guide.*
