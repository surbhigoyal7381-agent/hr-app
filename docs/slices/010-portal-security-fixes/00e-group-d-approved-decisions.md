---
slice: 010-portal-security-fixes
artifact: 00e-group-d-approved-decisions
date: 2026-09-15
status: approved by the user ("I go with your recommendations", 2026-09-15)
inputs: [00c-review-copies-decisions.md, 00d-impact-analysis-group-d.md, 01d-security-privacy-group-d.md]
---

# Group D: approved strategy and decisions

The user approved the group D strategy in `00d` and the requirements in `01d`, taking every
recommendation below. These answer the open questions in both documents. Where this file
and `00d`, `01d` or `00c` disagree, this file wins.

## Approved

- **Strategy:** as written in `00d-impact-analysis-group-d.md`. Build order is `00d` §16
  (12 commits), run locally in four phases. No push without the user's word.
- **Requirements:** every `VIS`, `SEC` and `PRIV` item in `01d-security-privacy-group-d.md`,
  with the open questions answered as below.

## Decisions (2026-09-15)

| # | Question | Decision |
|---|---|---|
| 1 | R4 and the running-total wording of "Log progress" | Keep R4. Change the KPI dialog to ask for **"the amount since your last update"**. Objectives: evidence is summed; goal updates count as readings. |
| 2 | May a person pick the date a reading is for? | **Yes** (adds about 0.5 day) |
| 3 | The review number and the live number can differ | **Accepted**; the R5 badge explains it |
| 4 | When copies are taken | **The first time the review is opened** |
| 5 | Evidence with no date of its own | **Use the upload date**, and show HR that it was dated by upload |
| 6 | Who changes a definition inside the review | **Employee during Employee Review; manager during Manager Review.** The manager's submit counts as "agreed". |
| 7 | Adding items after Employee Review | **No** |
| 8 | Lock more than R2's fields | **Yes:** also progress mode, direction, baseline, unit and the parent link (`01d` Q-D10) |
| 9 | Discarding a copy that already has a rating | **Never.** A rated copy is always kept, marked "Removed" (`01d` SEC-24, Q-D4) |
| 10 | Does the employee see why an item was removed | **Yes:** label, date and reason, from Employee Final Review (Q-D5) |
| 11 | Item-level manager ratings for the employee | **Yes, from Employee Final Review.** Rating stamps and flags: no (Q-D1) |
| 12 | A number changed after a rating was given | **The manager answers the flag. If the manager has left or changed role, HR answers with a reason** (the answerer is recorded). Email the employee if the overall rating changes. (Q-D11) |
| 13 | Self-rating flags | **Information only**; they do not block HR |
| 14 | R14 scope | **Covers Objective and KPI ratings.** The overall rating follows the existing release rule |
| 15 | HR Manager, HR User and System Manager in the desk | **Same stage rule as the portal** at every stage (`01d` SEC-27, Q-D3, Q-D7) |
| 16 | HR scope across review endpoints | **`permitted_companies()`**, as in groups A–C (Q-D14) |
| 17 | Invited reviewer access after Manager Review | **No** (Q-D6) |
| 18 | Returning a review to an earlier stage | **Unfreezes the numbers** |
| 19 | Future Objectives | **No cycle tag.** "Remove" on a carried-forward goal no longer deletes the earlier goal (Q-D2) |
| 20 | Cancelling a live record a review holds | **Allowed** |
| 21 | `set_goal_progress` (progress with no approval) | **Blocked while a review holds the goal** (Q-D13) |
| 22 | Employee write on HRMS `Appraisal` in our fork | **Remove it;** reads go through our endpoints only (Q-D12) |
| 23 | Where the three settings live | **HR Settings, plus the portal Org Settings screen** (adds about 0.5 day) |
| 24 | Custom DocPerm check (M3) on dev tenants | **Yes, read-only, before any push to dev** (Q-D15) |
| 25 | Other work in the review screens / `hrms-employee.html` | None known; Wave 1's split of the page has not started. Follow `parallel-work.md` and re-check the work board and `origin/dev` before each phase |

Earlier decisions still binding: overall rating visible from Employee Final Review,
potential rating never; nobody sees a self-review before it is sent; reviewer picker in
the reviewed person's company, not limited to the manager's line; nobody decides or rates
their own; the self-review stops changing goal progress.

## Decisions after phase 1 (2026-09-15)

Asked in `03d-implementation-notes-group-d.md` §9; the user took every recommendation.

| # | Question | Decision |
|---|---|---|
| 26 | Should Employee also lose **read** on HRMS `Appraisal` (scores are still readable through REST)? | **Yes.** Remove read too, in commit 8 (phase 3). Reads go through our endpoints only. |
| 27 | HR opening **their own** review record in the desk (it holds their own potential rating) | **Refused**, as built in phase 1. |
| 28 | `hr_api.get_employee_scorecard` lets any HR person open an employee from any company | **Fix inside 010**, in phase 3: scope to `permitted_companies()`, as in groups A–C. |

## Decisions after phases 2 and 3 (2026-09-15)

Asked in `03d-implementation-notes-group-d.md` (Phase 2 and Phase 3 sections); the user took every recommendation.

| # | Question | Decision |
|---|---|---|
| 29 | When may managers and HR remove items from a review? | **As built:** manager during Manager Review, HR during HR Review. Not during Employee Final Review. |
| 30 | Should an Objective target change agreed in the review get past the older "no target change once progress exists" rule on write-back? | **Yes.** The agreed change is written back at completion, with its audit entry. The older rule still applies to changes made outside a review. |
| 31 | Email the employee when their overall rating changes | **Only once the rating has been released to them**, as built. |
| 32 | Lock release set to 0 (never released): repeating reminder? | **No reminder** when the setting is 0. |
| 33 | `hr_api.get_goal_detail` lets any HR person open a goal from any company | **Fix inside 010:** scope to `permitted_companies()` for HR, keeping the manager-line rule. |

## Coordination

- Slice 012's plan adds the same KPI indexes. **010 claims the KPI DocType file** on the
  work board and adds the indexes in commit 1.

## For counsel (not blocking the build)

C-D1 retention and erasure of review copies; C-D2 discarding rated copies (resolved in
product by decision 9); C-D3 withholding potential on a data-access request; C-D4 telling
employees about removals (decision 10 shows the reason).

## Open questions

None blocking. Counsel questions above. Owner: user.

## Assumptions

- [ASSUMPTION] The four build phases follow `00d` §16's dependencies: phase 1 = commits
  1–3, phase 2 = 4–7, phase 3 = 8–10 and 12, phase 4 = 11 plus the page items from
  decisions 1, 2 and 23, whole suites, browser trace and notes.

## Handoff note

To the fullstack engineer: build from `00d`, `01d` and this file. Stop after each phase with
tests passing and notes updated. Never push. Before each phase, fetch `origin/dev`, read
the work board, and say what came in.
