# 08 — Feature: central Policy Library (core module)

Decision from the review: this is a **core product feature**, not a demo hack. HR, System Managers and every department head keep their department's policies here, choose who may read and who may edit, and every employee sees the policies that apply to them in a **Policies widget on the portal home page**.

Today nothing like this exists in the product (no policy doctype, no portal tab, only raw File attachments).

**Status: built and tested 2026-09-07 (file 10, B5).** Module **Alvoraa Policy Library** (`hrms/hrms/alvoraa_policy_library`), opt-in feature key `policy_library`. Differences from the text below: the policy code is `POL-00001` style (no department abbreviation); "Top Leadership" is the set of **Department Heads**, a new custom field on Department, plus anyone with the `Alvoraa CXO` role if a site has one; HR Managers, department heads and System Managers can always read, and HR Managers, the owning department's head and System Managers can always write; the read-only "current version" a reader sees is the last snapshot in the versions table, and the working copy carries a "Has Unpublished Changes" flag; attachments are private files whose download goes through Frappe's own permission check on the policy, so no separate streaming endpoint was needed; acknowledgement requests are not stored as records, a pending acknowledgement is simply "no Policy Acknowledgement for the current version".

## 1. Requirements in plain words

1. Any department head can create a policy for their department. HR and System Manager can create for any department.
2. Each policy says who can **read** it: everyone, reporting managers, HR only, only the owning department, or top leadership. Combinations are allowed.
3. Each policy says who can **write** it (edit, publish new versions) within the department: the department head, named roles, or named users.
4. Top leadership (Owner) and HR can read every policy regardless of the read rule.
5. Policies are versioned. Employees see the current published version. Old versions stay for audit.
6. Some policies must be acknowledged on joining, and when a new version is published.
7. Policies appear on the employee portal home page in a Policies widget, filtered by the viewer's role and department. Also a full Policies page.
8. Search by title and text; filter by department and category.

## 2. Doctypes (module `alvoraa_hr_core` in the `hrms` fork)

### `Policy Document`

| Field | Type | Notes |
|---|---|---|
| title | Data, required | |
| policy_code | Data, unique, auto `POL-{department abbr}-{####}` | |
| owner_department | Link Department, required | the department that owns it |
| category | Select: HR / Compliance / Finance / Operations / IT / Marketing / Safety / Other | |
| company | Link Company | blank = all companies (CXO persona) |
| status | Select: Draft / Published / Archived | only Published shows to readers |
| current_version | Int | bumped on publish |
| effective_from | Date | |
| review_due | Date | reminder to the owner |
| summary | Small Text | shown on the widget card |
| content | Text Editor | the policy body; optional if a file is attached |
| attachment | Attach | PDF version |
| read_access | Table `Policy Access Rule` | who may read (see §3) |
| write_access | Table `Policy Access Rule` | who may edit |
| acknowledge_on_joining | Check | |
| acknowledge_on_new_version | Check | |
| pinned | Check | shows first on the widget |
| versions | Table `Policy Document Version` (read only): version, published_on, published_by, change_note, content_snapshot, attachment_snapshot |

### `Policy Access Rule` (child)

| Field | Type |
|---|---|
| access_type | Select: All Employees / Reporting Managers / HR Only / Department Only / Top Leadership / Role / User / Designation / Branch |
| role, user, designation, branch, department | Links, shown depending on `access_type` |

A policy is readable by a user if **any** read rule matches them. Definitions:

| Rule | Who matches |
|---|---|
| All Employees | any active Employee |
| Reporting Managers | any employee who is `reports_to` of at least one active employee |
| HR Only | roles HR Manager, HR User |
| Department Only | employee's department = the policy's owner department (or any department listed) |
| Top Leadership | role `Alvoraa CXO` and the Department Heads of every department |
| Role / User / Designation / Branch | the named value |

Top leadership and HR always read everything (rule 4 above). Write access follows the same rule types; the owner department's Department Head and System Manager always have write.

### `Policy Acknowledgement`

| Field | Type |
|---|---|
| policy_document, version | Link, Int |
| employee, user | Link |
| acknowledged_on | Datetime |
| source | Select: Onboarding / New Version / Manual |

Unique on (policy, version, employee).

## 3. Permissions, the Frappe way

- **Row-level read** is a `permission_query_conditions` hook on Policy Document that expands the read rules into SQL for the current user (same technique the goals app uses for row scoping). `has_permission` re-checks on open.
- **Write** is `has_permission` for write/submit against `write_access` plus owner-department-head plus System Manager.
- Employees get the `Employee` role's normal read on Policy Document; the query condition does the filtering. No `ignore_permissions` anywhere in the read path.
- Attachments are private files; the portal streams them through a whitelisted endpoint that runs the same read check.

## 4. Workflow

Draft → Published (by anyone with write; sets `current_version += 1`, snapshots into `versions`, creates acknowledgement requests if `acknowledge_on_new_version`) → Archived. Editing a Published policy creates a new Draft version in place; readers keep seeing the last published snapshot until the new one is published.

## 5. Portal

**Home page widget "Policies"** (all personas): up to 6 cards, pinned first, then newest published, filtered by the viewer. Each card: title, department, version, effective date, "Acknowledge" button if pending. Link "All policies".

**Policies page** (`/hrms-employee#policies`): search, filter by department and category, list with status badges (Acknowledged / To acknowledge / New version). Opening a policy shows the content or the PDF inline, the version history, and the acknowledge button.

**Department head view** (same page, extra "Manage" tab when the user has write on any policy): my department's policies, drafts, publish, set access rules with a simple picker ("Who can read: All employees / Managers / HR / My department / Leadership / Custom"), see acknowledgement counts.

**HR view**: all policies, acknowledgement compliance by store, policies due for review.

APIs in `alvoraa_portal/hr_api.py`: `get_my_policies(limit)`, `list_policies(filters)`, `get_policy(name)`, `acknowledge_policy(name)`, `save_policy(...)`, `publish_policy(name, change_note)`, `get_policy_compliance(branch)`.

## 6. Onboarding link

Onboarding activity 8 in file 07 ("Portal login and policy acknowledgement") auto-completes when every policy with `acknowledge_on_joining` has an acknowledgement from the new joiner.

## 7. Demo content

`data/policies.csv` has 16 policies with owner department, visibility, acknowledgement flag, version and a one-line summary. Publish all 16. Write 2 to 3 paragraphs of real content for the five that will be opened in the demo: Attendance and Late Coming, Leave, Category Incentive, Vault and Security, Performance Appraisal. The rest can carry the summary as content.

Demo moments:

- Employee (Suresh Sethi) sees 9 policies: the 9 "All Employees" ones and none of the manager, HR or leadership ones. (Verified on the local demo site 2026-09-07: Suresh 9, Store In-charge 12, Owner 16, Ritika 9 with 8 acknowledgements pending; 3,200 acknowledgements seeded for existing staff.)
- Store In-charge sees 12: the 9 above plus the 3 "Reporting Managers" ones. Not the Purchase or Marketing department policies, not Payroll, not Compensation.
- Owner sees all 16.
- Head - Purchase & Sourcing opens "Old Gold Exchange and Valuation Policy" in Draft v1.1, changes the deduction norm, publishes with a change note, and the Gold Valuers in every store get a "new version to acknowledge" badge.

## 8. Impact analysis

See file 10, build B5. Additive: three new doctypes, hooks only on the new doctypes, one portal widget and page, seven APIs. No existing doctype is changed.
