# 063 · Surbhi's answers, 25 Oct 2026

Surbhi said "go with recommendations" on the leave strategy (04-impact-and-strategy.md v2) and on
03a-surbhi-decisions.md. So every item below is decided as the recommendation in those files.

## Strategy (04-impact-and-strategy.md v2)

| Item | Decision |
|---|---|
| Strategy | Approved |
| A-1 | HR sees the same on-behalf figure for office staff |
| A-2 | The Housekeeping designation name comes from the data, not the code |
| A-3 | Slice 070 (seats follow reporting) lands on dev first |
| A-4 | Field rights (ALV-215) lands on dev first |
| A-5 | Do NOT remove the old `slice/063-dtc-leave` worktree now (all 17 commits are on dev) |
| Q-S1 | HR removes the 42 Housekeeping rows from each month's payroll run, with a check afterwards |
| Q-S2 | HR may see Housekeeping leave DAYS when applying on their behalf, never pay. A branch check is added. |
| Q-S7 | Slice 067's red and green marks wait for the same five gates as the rule set |

## The 14 differences from prototype v4 (03a-surbhi-decisions.md)

- Change three: let HR see the figure when filing for someone; fix the three Hindi drafts (one promises pay,
  one says "charged double", one lacks the "of 5" sentence); approve the HR notice wording as drafted
  (name, dates and number of days only; no free text).
- Keep the build as specified for the other 11.
- "Leave encashed" for Housekeeping shows 0, with a note saying why.

## The 13 open questions in spec section 19

All decided as the analyst's recommendation in 03a-surbhi-decisions.md.

## Order and gates

- The build starts after 070 and field rights are on dev. Local first, nothing pushed.
- The rule set stays OFF at DTC until the five gates pass: field rights fixed, rehearsal on synthetic data
  passes, slab rows checked by Surbhi, a fresh checked DTC backup (one was taken 25 Oct 2026 14:41, copied
  to Surbhi's PC), and Surbhi's word.
- The office part of leave is already on dev but not on main. It needs its own release to DTC.
