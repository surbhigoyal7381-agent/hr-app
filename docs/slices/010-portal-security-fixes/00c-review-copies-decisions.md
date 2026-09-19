---
slice: 010-portal-security-fixes
artifact: 00c-review-copies-decisions
date: 2026-09-15
status: decided by the user
inputs: [00b-review-copies-analysis.md, product manager assessment of 2026-09-15, user decisions of 2026-09-15]
---

# 010 group D — Review copies: the decisions

These replace the open questions D-1 to D-6 in `00b-review-copies-analysis.md`. Where this
file and `00b` disagree, this file wins. Nothing is built yet: group D still goes through
impact analysis → strategy approval → local build → tests → review.

## How it came about

1. The analyst found the portal makes no review copies. A review reads and writes the
   live Objectives (`Individual Goal`) and `KPI` records (`00b`).
2. The user answered D-1 to D-6: build copies, lock the originals during the review,
   freeze when HR sends, all changes inside the review, copy the rest back at the end.
3. The product manager assessed those answers against every persona. The main finding:
   together they would stop everyday goal work for the whole review window. An employee
   cannot open their review after sending the self-review, so they would have nowhere to
   log progress. Outside screens and leadership roll-ups would go stale. Annual goals
   reviewed quarterly would sit in two open reviews at once. Competitors checked
   (Lattice, SAP SuccessFactors, Workday, Keka) lock the review form and ratings, not
   goal work.
4. The user chose the product manager's recommendations, with the changes marked
   **(user)** below.

## The decisions

| # | Decision |
|---|---|
| **R1 · Copies** | Build real review copies (option A), stored on the review record: a child table on `Alvoraa Appraisal Extension` (method M2 in `00b` §5). The review shows and rates only the copies. |
| **R2 · What is locked** | While a review is open, lock only the **definition** of a reviewed item: target, weight, period, title, deleting it, and moving it to another cycle. Definition changes are made inside the review. |
| **R3 · Facts keep flowing** | Progress readings, evidence, approvals and synced values are entered from the normal screens and stored on the **original**, as today. Until the freeze, facts **dated inside the review period** also reach the copy. Facts dated after the period stay with the original only. |
| **R4 · How the copy counts progress** | Follows each KPI's existing `progress_mode` setting **(user)**: *Cumulative* = sum of approved entries dated in the period; *Absolute* = latest approved reading dated in the period. |
| **R5 · Badge** | A reviewed original shows that it is in a review, and that updates dated after the period do not change it. |
| **R6 · Freeze point** | Tenant setting: freeze review numbers at *self-review sent* / *manager review sent* / *HR sent*. **Default: HR sent** (from HR Review to Completed). |
| **R7 · Rating stamp** | Every rating stores the numbers it was given on. If a number changes afterwards, the review shows the change and asks the rater to keep or change their rating. HR cannot send the review while such a flag is unanswered. |
| **R8 · HR cycle screens** | Calibration, cycle summary, HR KPI list and CSV export read the copies. The desk KPI list stays on originals and is labelled "Live records, not the review record". |
| **R9 · Lock release** | Tenant setting: release the definition lock N days after the cycle end date. **Default 30**, 0 = never. HR is reminded from day 15. |
| **R10 · Auto-sync** | Synced values write to the original, like every other fact, and reach the copy by date (R3). Data dated in the period that arrives after the freeze is shown to HR as "arrived after this review closed". It never changes the score silently. (No sync code exists yet; this is the rule for when it does.) |
| **R11 · Delete** | Items added inside the review can be deleted. Items that existed before the review cannot be deleted while a review holds them; they can only be removed from the review. |
| **R12 · Remove** | **Configurable (user).** Tenant setting: on removal, *discard the copy* (**default, user 2026-09-15**) or *keep the copy marked "Removed by … on …" with a reason*. **Always show a warning before removal** that the changes made inside the review for that item will be lost. Either way the item's progress and evidence stay on the original (R3). The employee may remove only during Employee Review; manager or HR later, with a reason. |
| **R13 · Ratings after completion** | Ratings are **not** written back to the originals. The frozen copy is the record of that review. |
| **R14 · Ratings outside the review** | **Nothing (user).** Outside screens show no rating and no "rated in" link. A rating is visible only when a person allowed to open that review opens it. |
| **R15 · What is copied back** | Only definition changes agreed inside the review are written back to the original, once, at completion, with an audit entry. Facts need no write-back (R3). |
| **R16 · Overlapping cycles** | If an item's earlier review is still open when the next cycle is generated, the item may be in both reviews. Facts are split between them by date. |

## Settings this adds

All organisation-level, with the defaults above: freeze point (R6), lock release days (R9),
removal behaviour (R12, default discard with a warning).

**Who builds it:** the slice 010 session carries on with group D (user, 2026-09-15). Read
this file before the impact analysis. The lock scope itself is fixed at "definition only"; a
"lock everything" option is not built unless a customer asks for it.

## Still to confirm during the build

- Security owner adopts the visibility rules from `00b` §4, amended by R1–R16.
- Which date a fact is sorted by: progress log `log_date`, evidence `extracted_date` —
  engineer to confirm both are always set, and what to use when one is empty.
- Size: the product manager estimates the analyst's ≈ 8 days plus about 1.5–2.5 days.
  The engineer's impact analysis gives the real figure.
