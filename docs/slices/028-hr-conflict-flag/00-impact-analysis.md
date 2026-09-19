# 028 — the HR conflict flag that "never fires"

## Verdict: nothing is broken. The rule is alive; the data never reaches the stage where it applies.

Investigated 2026-09-19 against the local copy of PP Jewellers
(`ppj.localhost`, 403 employees, 806 appraisals — the same shape as the numbers
measured on ppj.dev). **No code was changed.** This document is the finding and
the proposal; per CLAUDE.md §2 nothing is built without approval, and there is
nothing here that needs building.

## 1. Why the flag reads 0 on all 806 reviews

`hr_steps_elsewhere` is set in three places, and all three say the same thing:

- `performance_api.py:2021` (`hr_list_appraisals`)
- `performance_api.py:3706` (`get_calibration_overview`)
- `performance_api.py:4778` (`get_manager_review`)

```
"hr_steps_elsewhere": int(a.status == "HR Review" and a.employee in elsewhere)
```

Two conditions. The second one — "is the caller above this person?" — works.
The first one is never true on PPJ:

| Cycle | Stage | Reviews |
|---|---|---|
| Q1 FY27 | Completed | 403 |
| Q2 FY27 | Employee Review | 268 |
| Q2 FY27 | Manager Review | 131 |
| Q2 FY27 | Completed | 4 |
| **any** | **HR Review** | **0** |

The stage machine (`_REVIEW_STATUS_FLOW`, line 2914) runs
Employee Review → Manager Review → **Employee Final Review** → **HR Review** →
Completed. Q2's furthest reviews sit at Manager Review, two steps short of HR
Review, and the next step is the employee's own acknowledgement. So no review in
either cycle is at the stage the flag is about.

That gate is not arbitrary. Every HR step the rule protects is itself confined
to HR Review:

| HR step | Where the stage is enforced |
|---|---|
| calibration note | `_calibration_record` — "only while the review is in HR Review" |
| HR removal / deletion of items | `_ITEM_STAGES["hr"] = ("HR Review",)` |
| HR's answer to a rating question | `answer_rating_flag` — HR path needs `status == "HR Review"` |
| HR Review → Completed | `advance_review_status`, `current == "HR Review"` branch |
| return for revision | `return_for_revision`, HR Review only |

So the flag is 1 exactly when an HR step exists to be blocked. At Manager Review
there is no HR button to hide, and at Completed there is none either.

## 2. The server refusals are NOT dead

This was the thing worth being loud about, and the answer is the good one.
Run as Arjun Sodhi (HR User, 12 direct reports) on real PPJ rows:

- `subjects_in_my_line` over all 403 employees returns exactly his 12 reports.
- `refuse_hr_step_in_line` raises `PermissionError` for a report, and allows a
  non-report.
- With one review moved to HR Review inside a transaction (rolled back
  afterwards), `_calibration_record` **refused** for his own report and
  **allowed** the outside one.

Counts of who the walk finds, over the whole company:

| Person | Direct reports | `subjects_in_my_line` over all 403 |
|---|---|---|
| Kamal Gupta | 15 | **403** |
| Arjun Bhatia | 5 | **5** |
| Arjun Sodhi | 12 | **12** |

Note Kamal: decision 34 is the whole reporting line, not direct reports. He sits
near the top of the PPJ tree, so he is above everyone. The expectation of 15 rows
for him is the wrong number — it should be 403.

## 3. The observation that looked like a failure

Opening item 16 (Sakshi Rana, his report) and item 17 (Aarti Dhillon, not his) as
HR gave identical output. Two reasons, both benign:

1. Both reviews are Q1/Completed, so `hr_steps_elsewhere` is 0 for both — correct.
2. `viewer_role` in the payload is the **requested** view, not the effective one.
   When the caller is in the line, `get_manager_review` quietly downgrades the
   data to the manager view (`viewer = VIEWER_MANAGER`, line ~4775) but still
   reports `viewer_role: "hr"`. So the response cannot show the distinction even
   when the code is making it.

That second point is a real observability weakness, and it is why the test looked
like it failed. It is not a security hole — the data restriction happens — but
the payload does not admit it.

## 4. The old tests

`test_review_line_hr_010d.py` and `test_review_fixround2_010d.py` build a real
three-level chain (top → mid → leaf), give `top` a real HR Manager role, drive the
review to **HR Review** through the real endpoints, and open it with
`view="hr"`. They assert the flag is 1 there and 0 for someone outside the line.
They were asserting the right thing and passing for the right reason. They are not
the deeper failure — they are the reason we can be confident the rule works. What
they do not cover is "the flag is 0 at the earlier stages, and that is correct",
which is the behaviour that caused the confusion.

## 5. What has to be true on ppj.dev to see it

At least one Q2 review must reach **HR Review**, and its subject must report
(directly or indirectly) to the HR person doing the looking. The path for one row:

1. Pick a Q2 review of someone under Arjun Sodhi that is at **Manager Review**.
2. Arjun (or the direct manager) adds an action item and advances it →
   Employee Final Review.
3. The **subject employee** signs in and acknowledges → HR Review.
4. Arjun opens the HR review list. That row now shows the "another HR person"
   note, the HR buttons are hidden, and calibration is refused server-side.

A second row outside his line, taken to HR Review the same way, is the control:
buttons present, calibration allowed.

Until step 3 happens for at least one review, items 12, 13, 14, 16 and 17 cannot
be observed, and nothing about them is evidence of a defect.

## Proposal (needs approval — no code written)

Only one change is worth considering, and it is small:

- **Report the effective viewer.** Add `effective_viewer` to the
  `get_manager_review` payload (or make `viewer_role` the resolved viewer and keep
  the requested view separately). Today the downgrade is invisible, which is what
  made a working rule look dead. This changes what the page receives, so it needs
  a decision before it is built.
- **Add a pin test** that the flag is 0 at Employee Review, Manager Review and
  Completed, and 1 at HR Review, for the same in-line subject. That records the
  current behaviour as intended rather than accidental.

Neither is a fix, because there is nothing to fix.
