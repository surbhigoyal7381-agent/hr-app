---
slice: 063-dtc-leave-credit-and-lwp
artifact: rehearsal and release runbook (US-22, US-23, US-24)
author: hrms-fullstack-engineer
date: 2026-10-21
status: written, NOT run against DTC data. Nothing here has been done on any server.
---

# 063 · Rehearsal and release runbook

**Nothing in this file has been run against DTC data.** The code is built and tested on a
local test site only. Every step below that touches DTC data needs Surbhi's word first,
and the order matters: the DTC pay rule set is switched on **last**, and only after the
rehearsal passes and Surbhi has seen the extra cost.

The tool is `scripts/rehearsal_063.py`. Its read-only steps (`checks`, `cost`) are safe on
any site. Its writing steps refuse any site whose name ends in `alvoraa.co`: on
production a System Manager makes the same changes **in the desk**, from the lists below
(AC-105: no script on production).

## 1 · Data: synthetic, not a copy of production (Surbhi, 22 Oct 2026)

The rehearsal runs on a **synthetic, DTC-shaped** dataset (07a section 3). No production backup is
downloaded. `STEP=shape` reads the shape from DTC as counts only (read-only, on her word);
`scripts/seed_rehearsal_063.py` builds the named cases Test-901..912 on a throwaway local site and
checks each. Done on 22 Oct on the local test site: **30 of 30 pass** (04b section 9a). Wherever the
table below says "local copy", read "the synthetic site".

## 2 · The order

| # | Step | Where | Command / action | Evidence to keep (outside the repo if it names people) |
|---|---|---|---|---|
| R-1 | Read-only checks | local copy, then **production** (read-only) | `STEP=checks` | RC-6..RC-11 counts |
| R-2 | Credits on the 1st | local copy | `STEP=settings` | Version row; comment quoting the decision |
| R-3 | "Paid Leaves" type | local copy | `STEP=paid-type` | flags read back by `STEP=checks` |
| R-4 | Switch the rule set on | local copy only | `STEP=switch-on` | Version row |
| R-5 | The ten checks (section 3) | local copy | by hand on the portal and the desk report, plus `STEP=cost` | one line per check: pass / fail, with the number |
| R-6 | Rollback, timed | local copy | `STEP=switch-off`, then `STEP=rollback` | the two times |
| R-7 | Surbhi sees the cost and the ten checks | - | - | her word, dated |
| R-8 | On **DTC**: deploy the code with the rule set still **off** (AC-25 holds: both types refused, no card) | dev, then production, each on her word | normal deploy | AC-25 on the site |
| R-9 | On DTC: a System Manager changes the rule set values **in the desk** from the list in section 4, adds the decision as a comment | production desk | by hand | Version row |
| R-10 | On DTC: create "Paid Leaves" in the desk with the section 4 flags | production desk | by hand | `STEP=checks` read back |
| R-11 | DTC HR name Paid Leaves approvers for the staff with none (RC-8) | production desk | by hand | `STEP=checks` count = 0, or her decision to leave some |
| R-12 | **Switch the DTC rule set on** - only on Surbhi's word after R-7 | production desk | tick `enabled` | Version row |
| R-13 | Go-live check: two named staff with logins - card equals the desk report (AC-104) | production | look | screenshots outside the repo |

## 3 · The ten rehearsal checks (SEC-14, AC-108)

| # | Check | How | Pass when |
|---|---|---|---|
| 1 | A half-day leave approved on the portal gives 0.5 leave and no red, late or early charge | approve one; open the desk report row | Worked shows .5, On leave .5, no red for that day |
| 2 | An automatic "Half Day" with no leave is judged as before | pick one of the existing automatic half days (22 at DTC on 21 Oct) | same quarters and reds before and after the code |
| 3 | Five named staff with half days match a hand calculation | report rows vs paper | equal |
| 4 | Slip paid days equal the report's; saving twice gives the same | draft slip, save twice | equal both times |
| 5 | An Absent day later changed by a half-day leave is judged right on slip save | approve a back-dated half day over an Absent | the slip counts 0.5 + the punched half |
| 6 | Half-day LWP pays the same as half-day Paid Leaves | two staff, same punches | equal paid days |
| 7 | Credits on the 1st (01e section 5): full month 4/3/2; 15-30 days the full figure; 14 gives 0; zero classes 0; the report's "Leave earned" equals the card; slip equals report; 28 + 3 Paid Leaves gives used 3, paid out 1, paid days 32; **the extra October cost** | `STEP=cost MONTH=2026-10` plus the report | every figure as stated; the cost line shown to Surbhi |
| 8 | E6: 13 attended + 2 approved Paid Leaves reaches 15 and gets 4; with 2 Open it does not | two staff | as stated |
| 9 | **OD-1 remedy (iv):** a past half-day leave day with a punch missing; the employee asks on the Attendance page (the ordinary one-day form); HR approves; the next slip save counts the other half as worked, not doubled | on the copy, as the employee then as HR | the attendance row's other half reads Present and is linked to the request; the half is paid |
| 10 | Special days: an approved leave on a special day is not doubled; an absence on one is | the special-day list's date | as stated |

Also on the copy, because the code review could not settle them:

- a half-day correction approved and **then cancelled** on the desk: Frappe's own cancel removes
  every attendance row linked to the request, which here is the half-day leave's own row. Record
  what happens; HR should decline rather than cancel after approving.
- AC-15 timing: the Leave page card on the copy, for a person with a full month of attendance
  (budget 500 ms per call).

## 4 · The lists HR and the System Manager work from

**Rule set "Durga Trading Company"** (old values read on DTC, 21 Oct 2026):

| Field | Old | New | Rollback |
|---|---|---|---|
| `leave_threshold_days` | 15 | 15 | - |
| `accrual_month_days` | 30 | **15** | 30 |
| Class A `period_days` / `credit_per_period` / `monthly_credits` | 7.5 / 1 / 4 | **15 / 4 / 4** | 7.5 / 1 / 4 |
| Class B | 10 / 1 / 3 | **15 / 3 / 3** | 10 / 1 / 3 |
| Class C | 7.5 / 0.5 / 2 | **15 / 2 / 2** | 7.5 / 0.5 / 2 |
| `enabled` | 0 | 1 **last, on Surbhi's word** | 0 (the fastest rollback) |

Comment to add: *Surbhi, 21 Oct 2026, after checking with DTC: "there is no process of
accrual, all leaves are credited in the beginning of the month and remaining ones encashed
with the salary." The 15-day minimum stays.*

**Leave Type "Paid Leaves"**: not leave without pay; negative balance allowed; include
holidays (as Leave Without Pay at DTC); no encashment; no carry forward; not earned leave; no
maximums. Once created it is locked: only Administrator can change or delete it.

**Rollback, in one move:** untick `enabled`. The card disappears, both types are refused, and
no limit, month rule, HR approval of LWP, chain notice or half-day treatment applies. Requests
still Open stay Open; HR declines them. Then, if wanted, put the old values back.
