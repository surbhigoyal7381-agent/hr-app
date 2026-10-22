# 066 - Approve and Decline only when the caller can decide today

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

## The three commits (local only, branch `slice/066-attendance-decide`)

| Commit | What it does | Approval |
|---|---|---|
| Fix B | One server function, `not_yours_yet`, gives the reason a caller cannot decide today. `decide()` refuses with it; every review row carries `can_decide` and `not_yet`. The Attendance page and the Inbox show the buttons only when `can_decide` is true, and the server's sentence otherwise. | Asked for by Surbhi |
| Raiser rule | `decide()` refuses the person who raised the request ("You raised this request, so someone else decides it."). Before this, a manager who also holds an HR role could raise a correction and approve it themselves. | **Needs Surbhi's yes** - a new server rule, droppable on its own |
| Fix A | A correction raised by the employee's own manager skips the HR two-working-day wait. | **Approved by Surbhi on 22 Oct 2026**; 045 AC-81 amended |

## Impact

- **Security:** better. The screen now matches the server; the server stays the only
  control. The raiser rule closes a self-approval path. Fix A makes HR able to act sooner
  on manager-raised requests only. No new endpoint, no permission bypass, no new
  `ignore_permissions`.
- **Privacy:** neutral. The raiser's login is read to work out the flag and is never sent
  to the browser (a test pins it). The Inbox row gains two keys only.
- **Performance:** the flag costs a few queries per distinct person and day in the queue,
  not per row. The 044 query-count and scale tests pass unchanged.
- **Cross-module:** `attendance_correction.py`, `inbox_api.py` (attendance part only),
  `portal.js` (review queue rows only), `next-inbox.js` (row buttons). Slice 060's manager
  on-behalf flow is unchanged; its requests now go straight to HR (Fix A). Slice 063's
  leave rows already follow the same rule and were not touched.
- **Personas:** Employee - unchanged. Manager - unchanged unless they also hold an HR role
  (then they cannot decide what they raised). HR - sees who has a request and from when,
  instead of a button that fails; decides manager-raised requests at once.

## Still showing something that will be refused (not changed here)

- The bell and the Inbox count still include corrections HR cannot decide yet, so "2
  attendance fixes to decide" can mean "2 to look at, 0 to press". Fixing it means
  working the flag out inside the count.
