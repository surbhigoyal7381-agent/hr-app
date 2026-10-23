# 068 - Approve and Decline only when the caller can decide today

(Branch `slice/066-attendance-decide`; the slice is numbered 068 because 066 is the
grooming slice.)

**The bug (DTC production, 22 Oct 2026).** Ritika Arora (HR User) pressed Approve on
Attendance Request HR-ARQ-26-10-00003 on the Attendance page and got a 403 from
`attendance_correction.decide`. Vaneet Garg had raised it the day before for his own
report. `decide()` made HR wait two working days for the employee's manager (045 AC-81),
and the row offered the button anyway. On screen she saw a red toast for three seconds:
"This is still with Vaneet Garg until <date>. You can decide it as HR from then, counted as
two working days on this person's own holiday list."

042 AC-17 already said "a row that is drawn never returns a refusal", and 045 AC-81 said
the row should be "visible and not actionable, labelled with the manager and the date".
Neither screen did that.

## The changes (local only)

| # | What it does | Approval |
|---|---|---|
| Fix B | One server function, `not_yours_yet`, gives the reason a caller cannot decide today. `decide()` refuses with it; every review row carries `can_decide` and `not_yet`. The screens show the buttons only when `can_decide` is true, and the server's sentence otherwise. | Asked for by Surbhi |
| Raiser rule | `decide()` refuses the person who raised the request: "You raised this request, so someone else decides it." Before this, a manager who also holds an HR role could raise a correction and approve it themselves. | Surbhi, 23 Oct 2026 |
| Fix A | A correction raised by the employee's own manager skips the HR two-working-day wait. | Surbhi, 22 Oct 2026; 045 AC-81 amended |
| Wait only for a manager who can decide | The wait applies only when the employee's manager holds the submit permission on Attendance Request. Most line managers (Employee role only) can never decide, so HR no longer waits for them. | Surbhi, 23 Oct 2026; 045 AC-81 amended |
| Counts match the buttons | The bell and the Inbox count only the corrections the caller can decide today, and the Inbox lists exactly those. The Attendance page still lists every waiting correction, with the sentence on the ones that are not yet the caller's. | Surbhi, 23 Oct 2026 |

## What each row says

| Who is looking, and the request | Attendance page | Inbox and bell |
|---|---|---|
| HR; the manager can decide; inside two working days | No buttons. "This is still with <manager> until <date>. You can decide it as HR from then, counted as two working days on this person's own holiday list." | Not listed, not counted |
| HR; the manager cannot decide (Employee role only), or there is no manager, or the manager has no login | Approve and Decline | Listed and counted |
| HR; the manager raised it | Approve and Decline | Listed and counted |
| HR; after the two working days | Approve and Decline | Listed and counted |
| The person who raised it | No buttons. "You raised this request, so someone else decides it." | Not listed, not counted |
| No right to decide | No review queue | No attendance part |

## Impact

- **Security:** better. The screen and the counts follow the server, and the server stays
  the only control. The raiser rule closes a self-approval path. HR acts sooner where the
  manager could never act. No new endpoint, no new `ignore_permissions`.
- **Privacy:** neutral. The raiser's login is read to work out the flag and never sent to
  the browser (a test pins it).
- **Performance:** the count now reads every waiting correction in the caller's scope, not
  only how many there are. The managers behind those rows are read in two queries for the
  whole list, not per row, inside a memo that lives for one call. The 044 query-count and
  flatness tests stay green.
- **Cross-module:** `attendance_correction.py`, `inbox_api.py` (attendance part only),
  `portal.js` (review rows), `next-inbox.js` (row buttons). Slice 060's on-behalf requests
  now reach HR at once. Slice 063's leave rows already follow their own rule and were not
  touched.
- **Personas:** Employee - unchanged. Manager - unchanged unless they also hold an HR role,
  in which case they cannot decide what they raised. HR - no dead buttons, a bell that
  counts only what they can press, and no waiting for managers who cannot act.
