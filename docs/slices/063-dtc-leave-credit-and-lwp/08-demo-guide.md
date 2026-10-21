# 063 · Try the new leave rules (local demo)

**This is a throwaway local site with made-up people.** It is not DTC, dev or production.
The passwords below only work on this one demo site.

## How to open it

| From | Address |
|---|---|
| Your PC | http://localhost:8063/login |
| Over Tailscale (phone or another device) | http://100.99.86.42:8063/login |

Sign in, and the portal opens. The Leave page is **Leave** in the menu.

| Who | Login | Password | What they are |
|---|---|---|---|
| Priya | priya@l063.test | Priya@063demo | Class A employee, 16 days attended this month |
| Ritika | ritika@l063.test | Ritika@063demo | HR Manager (approves Leave Without Pay) |
| Sunil | sunil@l063.test | Sunil@063demo | Store manager, Priya's leave approver (approves Paid Leaves) |
| *(extra)* Rohit | rohit@l063.test | Rohit@063demo | Class A, only 10 days attended |
| *(extra)* Kavita | kavita@l063.test | Kavita@063demo | Top of the chain (Priya → Sunil → Kavita) |

Use a private browser window for each person, or sign out in between.

## Try these

**1 · The monthly card.** Sign in as **Priya**, open Leave. The card says "Paid Leaves -
October", 4 given on 1 Oct, 0.5 used (her half day on 3 Oct), "To be paid out 3.5 with October
salary". Then sign in as **Rohit**: he has attended only 10 days, so the card adds "These count
once you have attended 15 days in October. You have attended 10 so far (up to 10 Oct)" and
"once you reach 15 days".
*Partly:* the demo cannot show "day 1 of the month" live. Rohit is the "under 15" view; on the
1st the same card shows 0 attended.

**2 · A half day of Paid Leaves.** As Priya, **+ Apply Leave** → Paid Leaves → a date later this
month → tick Half day. Read the preview (half the shift, no green mark, what a missed punch
means). **Send to Sunil**. The pop-up shows the result; the card now shows 0.5 "Waiting for
approval" and "To be paid out" drops by 0.5.

**3 · Leave without pay.** As Priya, Apply → Leave Without Pay → two dates → **Send to HR**.
The list says "Waiting for HR". Ask again for 4 more days: the preview stops you at the
5-day limit and says what to do. Pick a date in September: "Leave can only be asked for days
in October. September is closed." There is no send button either time.

**4 · HR approves; the managers are told.** Sign in as **Ritika** → **Team** page → "Pending
Leave Approvals" (also the Home page card). Priya's Leave Without Pay row shows "N of 5 Leave
Without Pay days in October" and "Once it is approved, Priya's managers up to Kavita are told".
Approve it: the row says who has been told. Sign in as **Kavita** and open the bell in the desk
(http://localhost:8063/app): the notice says only name, dates, days and "approved".
As **Sunil**, his Team page shows Priya's Paid Leaves request from step 2; approve it the same way.

**5 · Cancelling.** As Priya: on a **waiting** request press "Cancel request" (confirm, "Keep"
is first); on an **approved** leave that starts tomorrow or later press "Cancel this leave".
A leave that has started says "speak to HR" and has no button.

**6 · The missed punch on a half day.** Priya's half day on **3 Oct** has only one punch on the
other half. Her Leave list shows "Your check-out for the other half of Sat 3 Oct is missing" and
**Ask HR to correct 3 Oct**, which opens the Attendance page at that day. Send the correction
there; **Sunil** (or HR once the manager's window has passed) approves it on the Attendance
page. The half then counts as worked. The desk report *Salary Components and Workings* (as
Ritika, company "L063 Rules Co", this month) shows it, beside Test-901 to Test-905, which are
07a's worked cases.

## What the demo shows only partly

- **Day 1 of the month** (step 1): shown through Rohit's "under 15", not live.
- **Emails** are switched off on this site; the chain notice shows as a desk bell, not an email.
- **The pay effect** of steps 2-6 is in the desk report, not on a payslip: the demo people have
  no salary, so money columns read 0. Days are right; rupees are not shown.
- **Approvals in an Inbox** do not exist on the live portal; they are on the Team page and the
  Home card (a difference from prototype v3, for your sign-off).
- **Hindi** is not switched on.
- The demo site is a copy of the test site, so the desk also holds other test companies and an
  old August request for Test-908 in Sunil's list. Approving that one is refused ("before
  1 October") - which is the month rule working.
- The class shows as "L063-A" because the demo's classes carry a prefix; at DTC it reads "A".
