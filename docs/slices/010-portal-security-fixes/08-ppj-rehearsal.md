# Slice 010 group D — release rehearsal on ppj.localhost

Date: 2026-09-17. Who: test automation engineer. Where: the local bench `hrlocal-bench`,
site `ppj.localhost` only. Code: local `dev` at `370189d` (nothing pushed; origin/dev is
`c27fb56`). Approved by the user on 2026-09-17 ("2. ok"). PPJ data is dummy.

## The short answer

**Not ready to ask for "push to dev" yet. Two release blockers, one in the code and one
in the checklist.**

1. **Code blocker — a review can get stuck in HR Review with no button to free it.**
   When the manager who gave the overall rating also holds an HR role, and the numbers
   change in HR Review (here: another HR person removed a rated item), the overall rating
   is flagged. HR's Finish button is then disabled. HR cannot answer the flag (the server
   says "Only the person who gave this rating can answer for it"), and the manager's own
   screen shows only the read-only "Another HR person…" page, with no "Keep the rating"
   button. Nothing on any screen can finish the review. Reproduced on
   `HR-APR-2026-00417` (left stuck on ppj on purpose).
2. **Checklist blocker — the step 2 dry run cannot run before migrate.**
   `bench --site <site> execute alvoraa_goals.review_backfill.report` fails on a site
   that does not have group D's tables yet: `Unknown column 'items_taken_on'`. Dev
   tenants are at `c27fb56`, so the same thing will happen on every one of them. The
   "stop if…" gate in step 2 cannot be applied as written.

Everything else worked:

- **Migrate: passed**, 101 seconds, 4 patches, 0 failures, no new Error Log rows.
  "Review copies: 806 reviews, 3934 copies, 0 failed".
- **The release-risk fix holds.** 134 open reviews have old manager ratings (601 rated
  KPIs). After migrate, a simulated first open of all 403 open reviews raised **0**
  rating questions, and managers' review lists show no "Rating needs your answer".
- **Browser trace: all asked-for screens walked**, 80 screenshots, 0 page errors.
  Three failed network calls, all caused by the trace on purpose or by its own order
  (explained below). No product 5xx.
- **Calibration note save works** (decision 35), and the `calibration_notes` column
  exists. But **no screen has a button that opens the note box** (see finding F3).
- **Rollback dry runs ran.** One gap: ratings given in the portal on a review that was
  then completed are not copied back (F5).

**Backup (restore point):** taken before anything changed, 2026-09-17 12:57 IST.

| File | Size |
|---|---|
| `20260917_125725-ppj_localhost-database.sql.gz` | 10.3 MiB |
| `20260917_125725-ppj_localhost-files.tar` | 10 KiB |
| `20260917_125725-ppj_localhost-private-files.tar` | 10 KiB |
| `20260917_125725-ppj_localhost-site_config_backup.json` | 808 B |

In the bench: `sites/ppj.localhost/private/backups/` (the `hrlocal-sites` volume).
A second copy: `C:/Surbhi-Git/hrlocal-data/backups/ppj-rehearsal-2026-09-17/` (gzip
checked; it holds the site config with its database password, so keep it local).

ppj.localhost is **left migrated** (step 4 did not fail), with the trace's changes in it.

---

## 1. What ran, in order

| # | Step (checklist §8) | Command | Time | Result |
|---|---|---|---|---|
| 1 | Back up | `bench --site ppj.localhost backup --with-files` | 12 s | done |
| 2 | Before counts | read-only SQL | — | §2 |
| 3 | Dry run | `bench --site ppj.localhost execute alvoraa_goals.review_backfill.report` | 2.5 s | **failed**: `MySQLdb.OperationalError: (1054, "Unknown column 'items_taken_on' in 'field list'")` |
| 3b | Dry run, workaround | same `report()`, in a throwaway Python process piped into the bench, with the review-record read told to skip the one missing column and "already has copies" treated as none. Read-only, rolled back, no file copied, no repo file changed | 1.3 s | §3 |
| 3c | Permission report (step 5, run early too) | `bench --site ppj.localhost execute alvoraa_goals.review_items.custom_docperm_report` | 2 s | printed **nothing** (an empty list prints nothing — see C4) |
| 4 | Migrate | `bench --site ppj.localhost migrate` | **101 s** (12:59:39 → 13:01:20 IST) | exit 0 |
| — | Clear cache (step 4 of §8) | not run | — | see C5 |
| 5 | After counts, reports | read-only SQL and scripts | — | §4 |
| 6 | Browser trace | `trace_review_copies_010d_v2.py` | ~20 min over 6 runs | §5 |
| 7 | Rollback dry runs | `copy_ratings_back_for_rollback` and `undo_backfill`, both `{'dry_run': 1}` | 3 s each | §6 |

### Migrate output (progress bars removed)

```
Migrating ppj.localhost
Executing alvoraa_portal.patches.v1_0.fill_branch_on_hr_records ... Done in 11.266s
Executing alvoraa_goals.patches.v1_0.make_evidence_files_private
make_evidence_files_private: 0 links made private, 0 failed, 0 rows with no File record ... Done in 0.113s
Executing alvoraa_goals.patches.v1_0.take_review_copies
Review copies: 806 reviews, 3934 copies, 0 failed ... Done in 8.226s
Executing alvoraa_goals.patches.v1_0.stamp_lock_release_days ... Done in 0.024s
Syncing jobs / fixtures / dashboards / customizations / languages
Removing orphan doctypes...
Command: Sleep | Time: 5s / 15s / 25s        <- waiting about 25 s on another DB connection
Removing orphan Workspaces / Dashboards / Pages / Reports / Notifications / ...
Updating installed applications...
Executing `after_migrate` hooks...
Queued rebuilding of search index for ppj.localhost
```

No warnings, no errors. Error Log: 0 new rows since 12:59; 0 "Review copy backfill failed".
Full log: `C:/Surbhi-Git/hrlocal-data/mobile-audit/2026-09-17-ppj-rehearsal/migrate.log`.

**ppj ran more than dev will.** ppj was last migrated on 2026-09-08, so it also ran groups
A–C's two patches (`fill_branch_on_hr_records`, `make_evidence_files_private`). Dev
tenants already have those; on dev only the two group D patches should run.

**Someone else's uncommitted change was live during the migrate:** the main checkout has a
local edit to `hrms/.../alvoraa_position/alvoraa_position.py` (not mine, not committed).
The bench mounts the checkout, so that file was in use. Nothing in the output points at it.

---

## 2. Before counts (read-only, before migrate)

| What | Count |
|---|---|
| Appraisals | 806 (403 submitted = Q1, 403 draft = Q2) |
| Review records by stage | Q1: 403 Completed · Q2: 269 Employee Review, 134 Manager Review |
| Review records with an overall rating | 403 (all Completed; 0 open) |
| KPIs | 3,510 (all Cumulative): 1,755 Active, 694 Achieved, 1,061 Missed |
| KPIs rated, Q1 | self 1,755 · manager 1,755 · potential 1,755 |
| KPIs rated, Q2 (open reviews) | self 0 · manager **601** · potential 601 |
| Open reviews holding a rated KPI | 134 (every Manager Review) |
| Individual Goals | 425 (212 Q1, 212 Q2, 1 with no cycle); none future plans |
| KPI readings | 380 Approved, 1 Pending |
| Custom DocPerm on Appraisal / Extension / KPI / Individual Goal | 1 row: Appraisal, System Manager, level 0 (HR role, so not reported) |
| Error Log | 3,074 rows, newest 2026-09-14 |
| Patch log, custom apps | last custom patch 2026-09-08 |

---

## 3. Dry run counts (before migrate, workaround in §1 row 3b)

```
reviews 806; by cycle: Q1 Completed 403 · Q2 Employee Review 269, Manager Review 134
will_copy: reviews 806, items 3934, completed 403, open 403, open_already_frozen 0
items_per_review: average 4.9, most 7
skipped {} · cannot_copy_nothing_tagged: completed [], open [] · reviews_with_no_period 0
rated_items_copied 2356
approved_facts_dated_outside_the_review_period: KPI readings 0, goal updates 0
open_items_counted_from_facts_differ_from_live 1161
ratings_stamped_on_counted_numbers 402
draft_keys_dropped 0 · cumulative_kpis_whose_readings_look_like_running_totals 0
extensions_missing_employee_or_cycle 0 · kpi_additional_reviewer_rows 0
custom_docperm_rows_to_look_at []
```

Step 2's stop rules: `cannot_copy_nothing_tagged.open` is empty and
`custom_docperm_rows_to_look_at` is empty, so **go**.

**The 363 / 403 estimates.** They come from `05-review-group-d.md`: 363 open reviews on
dev.alvoraa.co, 403 on ppj.dev. ppj.localhost is a copy of ppj, and it has **403 open —
a match**. 363 is a different tenant, so it cannot be checked here. The patch then copied
exactly what the dry run said: 806 reviews, 3,934 copies.

**What the big number means (PPJ data).** 1,161 open items get a number different from
the live record, because the copy counts only approved readings dated in the period and
PPJ's seeded KPIs carry a live number with few readings behind it. On screen, Vinod
Gupta's KPIs show 0.0% in his review while the live KPI says 58.8%. On a real tenant this
count is the one to read before migrate: it says how many review numbers people will see
change.

---

## 4. After counts

| What | Result |
|---|---|
| Copies taken | 3,934 rows, all `backfilled`; 3,510 KPI, 424 Objective |
| Review records with `items_taken_on` | 806 of 806 |
| Frozen | 403 (Completed only); 0 open |
| `stamp_lock_release_days` | 806 records = 30 (HR Settings value 30) |
| Overall rating basis stamped | 403 (the Completed ones that had a rating) |
| Ratings stamped on copies | Completed: 1,755 manager + 1,755 self, all with `rated_on` · Manager Review: 601 manager, all with `manager_rated_on` · Employee Review: 0 |
| `ratings_stamped_on_counted_numbers` (dry run) | 402 |
| `open_items_counted_from_facts_differ_from_live` (dry run) | 1,161 |
| `report()` after migrate | 806 skipped "already has copies"; every count 0 (as expected) |
| **Rating questions on first open** | Simulated in memory for all 403 open reviews (`refresh_review_items(save=False)`, rolled back): **0 manager flags, 0 self flags, 0 overall flags, 0 reviews changed**. Stored flags: 0 |
| "Rating needs your answer" on screen | Not shown on Gurpreet Dhillon's or Arjun Bhatia's review lists before the trace changed anything (Arjun manages three Manager Reviews with old ratings) |
| `calibration_notes` column | exists (`text`) on `tabAlvoraa Appraisal Extension`; also `lock_release_days`, `items_taken_on`, `frozen` |
| HR Settings fields | freeze point "HR sent", lock release 30, removal "Discard the copy" |
| KPI rating fields | `self_/manager_/potential_rating` and their comments at permission level 1 |
| "Cumulative KPI Readings Check" report | installed (Script Report, standard). Run as Administrator: **125 rows** for PP Jewellers Pvt Ltd (125 with no filter) |
| Error Log | 0 new rows |

**Why the report says 125 and the dry run says 0** (not a defect, but confusing — see C3):
the dry run counts Cumulative KPIs whose live number differs from the sum of readings;
the desk report lists every Cumulative KPI with two or more readings that never go down.
They answer different questions.

---

## 5. Browser trace

### The script

`trace_review_copies_010d.py` was **out of date** and was not run as it stood:

- it read a KPI list that is private inside the page (`_pfMyKpis`), so the log dialog step
  would have been skipped;
- it never reached HR Review, and did not cover decision 34 (manager who holds HR),
  decision 35 (a different HR person calibrates, removes, finishes), the reviewer picker,
  or failed network calls;
- `ppj.localhost` does not resolve for Playwright; `http://localhost:8010` serves the
  same site (it is the default site).

So I wrote **`C:/Surbhi-Git/hrlocal-data/mobile-audit/trace_review_copies_010d_v2.py`**
(outside the repo; the old file is unchanged). It runs in named stages, records every
4xx/5xx API call, console error, page error and browser dialog, and checks labels and
sideways overflow on each screen.

**One thing it does that a user cannot:** PPJ's Q2 cycle config has `page_config []`
(dummy data), so the review wizard shows no "Past Objectives & KPIs" page at all. In the
trace browser only, the script adds that page to the `get_my_review` /
`get_manager_review` answer. The server is unchanged, and every item action still goes to
the real endpoints and their checks. (I tried to set the page on the cycle record directly
and that was refused, rightly; I did not change the cycle.)

People used (dummy): Vinod Gupta (employee, iPhone 13), Kavita Jain (employee, iPhone 13),
Gurpreet Dhillon (manager, no HR role), Arjun Bhatia (HR Manager, manages Sumit Dhillon and
Renu Gupta), Sumit Dhillon and Renu Gupta (subjects), Sumit Kumar (HR User, not in their
line).

Screenshots and `report.json`:
**`C:/Surbhi-Git/hrlocal-data/mobile-audit/2026-09-17-ppj-rehearsal/trace/`**

### Results

| Flow | Result | Screenshots |
|---|---|---|
| KPI log dialog (Vinod, phone) | **Pass.** Label "Amount since your last update *", box starts empty, hint "Not the running total…", date picker (`type=date`) defaults to today with today as the max, "In review · updates dated after 30 Sept 2026 don't change it" shown. Logged 2 for 14 Sep: the reading is **Pending**, live number unchanged (0.00) | 02, 03, 04 |
| Objectives screen outside a review | **Pass.** 3 "In review" badges, the word "rating" nowhere | 01 |
| Employee self-review wizard (Kavita, phone) | **Pass.** Review's own copies (no live record names on screen), edit and remove on each item, remove dialog says reason "(optional)" and warns what is lost; removal worked; 200% zoom has no sideways scroll | 09–14 |
| Self-review sent (Vinod) | **Pass.** Stage moved to Manager Review | 05–08 |
| Manager review, item controls (Gurpreet, no HR) | **Pass.** 3 edit, 3 remove, 3 rating boxes. Target changed to 120 on the copy only (live stayed 95 until completion); rating 4 saved with comment; removal without a reason refused ("Say why…"), with a reason done | 16, 20–24 |
| Reviewer picker | **Pass.** Typing "Yogesh Ya" found Yogesh Yadav, the last name alphabetically of 403 | 25 |
| Manager submit, employee acknowledge | **Pass** (after the trace pressed Save Draft — see F4) | 30–33 |
| Manager who holds an HR role (Arjun) in Manager Review | **Pass.** Manager controls visible (3 edit, 3 remove, 3 rating), no "Rating needs your answer" on three reviews with old ratings | 34–40 |
| Same manager, report in HR Review | **Pass.** HR table row shows "Another HR person needs to do the HR steps…" and no Finish button; inside the review the Finalize page shows the note and no Finish button; no remove or edit buttons | 43–48 |
| Different HR person (Sumit Kumar): calibration note | **Pass on save** — "Calibration note saved.", stored with rating 3.5. **But no screen has a button to open it** (F3); the box was opened by calling the page function | 49–52 |
| Different HR person: remove item | **Pass.** Remove buttons only (no edit, ratings read-only), reason required, item kept as Removed with reason and name | 53, 57, 58 |
| Different HR person: finish review | **Pass** on a review with no open flag (`HR-APR-2026-00407` → Completed; live KPI target written back to 120). On `00414` the finish was blocked by a flag the trace itself caused (calibrate, then remove a rated item) — see F1/F2 | 59–69 |
| Stuck-review check (F1) | **Fail** — `HR-APR-2026-00417` cannot be finished from any screen | 70–79 |
| Org Settings review block (Arjun) | **Pass.** Card shown with freeze point "HR sent", lock 30, removal "Discard the copy", all editable | 61 |

### Console errors and failed calls

0 page errors. 3 failed API calls, each with a matching console "Failed to load resource":

| Call | Status | Cause |
|---|---|---|
| `acknowledge_final_review` (Vinod) | 417 "Review is not in Employee Final Review stage." | The trace ran the acknowledge before the manager had submitted (my run order). Not a product fault |
| `advance_review_status` (Sumit Kumar, `00414`) | 403 "1 rating(s) were given on numbers that changed since…" | The trace called Finish while the button was disabled. The server refused correctly |
| `answer_rating_flag` (Sumit Kumar, `00417`) | 403 "Only the person who gave this rating can answer for it." | Deliberate probe for F1. Correct server rule; it shows the dead end |

No 5xx. The error answers carry a full Python traceback to the browser (Frappe's default
when `allow_tracebacks` is not set). That is older than this slice; worth checking on dev
tenants.

---

## 6. Rollback rehearsal (dry runs only)

```
copy_ratings_back_for_rollback {'dry_run': 1} -> kpis_to_change 0, kpis [], failed []
undo_backfill {'dry_run': 1}                  -> undone 803, kept_because_changed_since
                                                 [HR-APR-2026-00417, 00414, 00407]
```

Nothing destructive was run.

- **copy-back found 0**, although Gurpreet gave KPI-2026-01766 a manager rating of 4 in
  the portal. That review was completed in the trace, and copy-back only reads **open**
  reviews. After a code rollback, the old screens would show that KPI's live rating (0).
  See F5.
- **undo_backfill would undo Kavita Jain's review (`00418`)** although she removed an item
  in it. In "Discard the copy" mode an unrated removal deletes the row, so nothing marks
  the review as changed. After undo, her next open would copy that item back. Small,
  but her removal is lost silently.

**Is the rollback order right?** Mostly yes: the two data steps need group D's code, so
they must run before the image goes back, and the checklist says so. Three gaps:

1. It does not say to stop people using reviews first (maintenance mode or a notice).
   Ratings given between step 1 and the image switch are lost to the old code.
2. It does not warn that after `undo_backfill`, a **later re-release will not copy
   Completed reviews again**: the patch is already in the patch log, and first-open
   copying skips Completed reviews. History copies for completed reviews would be gone
   for good unless the patch log row is removed. Safer: do not run `undo_backfill` on a
   tenant that may get group D again.
3. Copy-back skips reviews completed after go-live (F5).

---

## 7. Problems found

### Release blockers — code or checklist

| ID | What | Where | Severity |
|---|---|---|---|
| **F1** | **A review can get stuck in HR Review.** If the overall rating was given by a manager who holds an HR role and it is flagged in HR Review, nobody can answer it on screen. The manager gets `get_manager_review` with `hr_steps_elsewhere` set, so `prRenderManagerSubmitPage` shows `prRenderHrFinalizePage` (no "Keep the rating" buttons); the items page has no overall-flag button; HR is refused by `answer_rating_flag` because the rater still acts. Finish stays disabled. How to reproduce: manager with HR role submits a review with an overall rating → employee acknowledges → another HR person removes a rated item → open as either person. Seen on `HR-APR-2026-00417`. Likely also reached when an approved reading dated in the period arrives during HR Review (the review is not frozen then). ppj has 15 people reporting to Kamal Gupta, who holds HR Manager, so this is not rare. | `hrms-employee.html` `prRenderManagerSubmitPage` / `prRenderHrFinalizePage`; `performance_api.answer_rating_flag` | Major |
| **C1** | **The step 2 dry run fails before migrate** on any site without group D's schema (`Unknown column 'items_taken_on'`; the copy table does not exist either). Every dev tenant is in that state. Needs a code fix (make `report()` work without the new column and table) or a checklist change (run it on a restored copy of the tenant's backup that has been migrated to schema only). As written, the gate cannot be applied. | `review_backfill.report` / `_plan`; checklist §8 step 2 | Major |

### Not blockers, but the user should know

| ID | What | Severity |
|---|---|---|
| F2 | When HR itself gave the overall rating (through a calibration note with a rating) and it is later flagged, HR's Finalize page says "The manager who gave it must keep or change it" and shows no button. The server does let HR answer as the rater: calling the page function from the browser console worked and the review could be finished. Same missing-button cause as F1; the wording is also wrong for this case. | Major (only reachable through F3's hidden box today) |
| F3 | **The calibration note has no button on any screen.** `pfHrCalibration` renders the "Note" button but nothing calls it — also true on origin/dev `c27fb56`. Decision 35's server fix works, but HR cannot reach the box in the portal. | Minor (old) |
| F4 | Manager feedback typed on "Manager Feedback" is lost when moving on with "Save & Continue" (autosave only runs in Employee Review). Submit then says "Please write feedback…". "Save Draft" keeps it. Same on origin/dev. | Minor (old) |
| F5 | `copy_ratings_back_for_rollback` skips reviews completed after go-live, so their portal item ratings are not put back on live KPIs before a code rollback. | Minor (rollback only) |
| F6 | `undo_backfill` treats a review as unchanged after an unrated item was removed in "Discard the copy" mode. | Minor (rollback only) |
| F7 | The review stage bar shows the literal text `<i class=ic-check></i>` (clipped: "ss= eck") on completed stages: `dot.textContent` is given HTML. Same on origin/dev. | Cosmetic (old) |
| F8 | Inputs with no label: the self-review "Feedback for Reporting Manager" and Summary textareas; `mgr-feedback-ta`, `mgr-notes-ta`, `mgr-invite-search`; `mgr-overall-rating`, `mgr-potential-rating`; `pf-calib-note-text`, `pf-calib-rating`; `pf-review-cycle`, `pf-hr-cycle`, `cal-cycle-sel`. Screen readers cannot name them. | Minor (a11y) |
| F9 | Error answers send a full Python traceback to the browser. Platform default, not this slice. Check `allow_tracebacks` on dev tenants. | Minor (security hygiene, old) |

### PPJ data only (ignore)

- Q2 cycle has no review pages configured (`page_config []`), so the real wizard shows no
  Objectives & KPIs page. The trace added it in the browser only.
- 1,161 open items get a different number in the review than on the live KPI, because the
  seeded live numbers have few dated readings behind them (Vinod's KPIs show 0.0%).
- 125 Cumulative KPIs listed by the readings report.
- 601 Q2 KPIs carry old manager ratings; all were stamped, none flagged.
- ppj also ran groups A–C's patches, which dev tenants already have.

---

## 8. Checklist corrections (§8 of `03d-implementation-notes-group-d.md`)

| ID | Step | Wrong or unclear | Suggested text |
|---|---|---|---|
| C1 | 2 | The dry run cannot run before migrate on a tenant without group D's schema. | Fix the code, or say how to get the counts (for example: restore the tenant backup onto a scratch site, deploy the code, run `report()` there before its migrate). |
| C2 | 2 | "after the code is deployed and before its migrate" — with image deploys it is not said whether the deploy runs migrate by itself. If it does, there is no window for the dry run. | Say which it is for dev, and where the window is. |
| C3 | 2 and 6 | `cumulative_kpis_whose_readings_look_like_running_totals` (dry run) and the "Cumulative KPI Readings Check" report measure different things (ppj: 0 vs 125). | Say that the report is wider on purpose, and that a 0 in the dry run does not mean HR can skip step 6. |
| C4 | 5 | `bench execute … custom_docperm_report` prints **nothing** when the answer is empty. A reader cannot tell "clean" from "did not run". | "No output means no rows to look at." Or print a line. |
| C5 | 4 | `bench --site <site> clear-cache` is listed as its own step, but `bench migrate` already clears the cache. I did not run it (it needs its own approval and the trace showed the new page and report were already served). | Say it is only needed if the page is served stale. |
| C6 | 3 | "It runs two patches" — true for dev; a tenant not migrated since groups A–C also runs `fill_branch_on_hr_records` and `make_evidence_files_private`. "15–20 seconds" is the patch time; the whole migrate took 101 s on ppj. | Give both numbers, and say to expect 4 patches on a stale tenant. |
| C7 | 3 | The migrate waited ~25 s on "Command: Sleep" while removing orphan doctypes (another DB connection open — the running site). | Say this pause is normal, or put the site in maintenance mode first. |
| C8 | Rollback | No "stop people using reviews first"; no warning that `undo_backfill` makes a re-release skip completed-review history; copy-back skips reviews completed after go-live (F5). | Add all three. |
| C9 | 7 | "a manager with no HR role and one who holds an HR role open Manager Review…" does not cover what happens to that second manager's review in HR Review with a flag (F1). | Add: "for a review whose manager holds an HR role, raise a rating question in HR Review and check someone can answer it". |

---

## 9. What I did not check

- A manager **without** an HR role answering an overall flag in HR Review. The code shows
  the buttons on that path; no flag was open when Gurpreet looked, so it is not proven.
- The desk list and desk report screens by hand (the report was run through its Python
  entry point, not clicked in the desk).
- Full test suites (not asked; `07-release-verification.md` has the last full run).
- Anything on dev, production or test_site.

## 10. Data the trace left on ppj.localhost (dummy)

| Review | State now |
|---|---|
| `HR-APR-2026-00407` Vinod Gupta | Completed (manager rating 4 and target 120 on one KPI, written back to the live KPI) |
| `HR-APR-2026-00414` Sumit Dhillon | Completed (calibration note, rating 3.5, one item removed by HR) |
| `HR-APR-2026-00417` Renu Gupta | **Stuck in HR Review with an overall flag (F1)** — kept as the reproduction |
| `HR-APR-2026-00418` Kavita Jain | Employee Review, one item removed, not sent |
| KPI-2026-01768 | one Pending reading of 2, dated 2026-09-14 |

To go back to the pre-migrate state:
`bench --site ppj.localhost restore sites/ppj.localhost/private/backups/20260917_125725-ppj_localhost-database.sql.gz --with-public-files …files.tar --with-private-files …private-files.tar`
(on the user's word).

---

# Re-rehearsal after fix round 2 (decisions 37 and 38)

Date: 2026-09-17. Who: fullstack engineer. Where: `ppj.localhost` on `hrlocal-bench`
only. Code: local `dev` at `8a53522` (nothing pushed; `origin/dev` still `c27fb56`). Part
of the rehearsal the user approved. PPJ data is dummy.

## The short answer

**Both release blockers are cleared on ppj.localhost.**

1. **F1:** `HR-APR-2026-00417` (left stuck on purpose in the first rehearsal) is
   **Completed**. Arjun Bhatia (manager, holds HR Manager) answered the question on his
   own rating from **My team's reviews**; Sumit Kumar (HR User, not in the line) then
   finished it from the **HR review list**.
2. **C1:** the dry run works on a pre-release schema. On ppj it counts **806 reviews,
   3,934 copies**, the same as the first rehearsal's real migrate. The code from before
   the fix still fails there with the same `Unknown column 'items_taken_on'` error.

Also proven in the browser: F2 (HR who gave the overall rating answers it from the HR
view; the manager is told someone else must), F3 (the "Calibration note" button opens
the box, and reopening it shows the saved note), and both lists for a person with both
roles, and one list only for a plain manager and a plain HR person. F5 and F6 were checked with
the rollback dry runs.

**No migrate was run:** fix round 2 adds no patch and no field. No new backup was taken:
the 12:57 IST backup from the first rehearsal is still the restore point.

## 1. Dry run (C1), read-only

Script piped on stdin into the bench (no file copied into the app, no repo change):

| Run | What | Result |
|---|---|---|
| 1 | `report()` as the site is (migrated) | `site_already_has_group_d_tables` 1; 806 skipped "already has copies"; every count 0; 0.6 s |
| 2 | Fixed `report()`, pre-release schema imitated | `site_already_has_group_d_tables` **0**; will_copy **806 reviews, 3,934 items** (405 completed, 401 open, 0 open already frozen); `cannot_copy_nothing_tagged` empty; `open_items_counted_from_facts_differ_from_live` 1,157; `ratings_stamped_on_counted_numbers` 401; `custom_docperm_rows_to_look_at` []; 1.0 s |
| 3 | `report()` from `f51c130`, same imitation | **fails** as in the first rehearsal: `OperationalError(1054, "Unknown column 'items_taken_on' in 'field list'")` |
| — | Before and after | copy rows, review records and their latest `modified` unchanged |

**How the old schema was imitated, honestly:** for that one database session only, a
MariaDB `TEMPORARY` table with the review records minus `items_taken_on` hid the real
table (a temporary table shadows a base table of the same name for that connection;
checked: selecting `items_taken_on` failed), and the two schema lookups were told the
copy table and the column do not exist. Temporary tables are private to the session and
were dropped; the session was rolled back. The counts differ a little from the first
rehearsal (405/401 against 403/403, 1,157 against 1,161) because the first rehearsal's
trace completed two reviews and changed some numbers.

## 2. Browser trace

Script: `C:/Surbhi-Git/hrlocal-data/mobile-audit/trace_review_copies_010d_v2.py`, updated
for decision 37 (every review opened with its list's view; new stages `d37lists`,
`d37unstick`, `d37f2`, which click the real buttons). Screenshots and `report.json`:
**`C:/Surbhi-Git/hrlocal-data/mobile-audit/2026-09-17-fixround2-rehearsal/trace/`**
(29 screenshots, `00`–`28`).

**Result: 29 steps, 0 page errors, 0 console errors, 0 failed API calls.** The first run
stopped twice on a fault in the trace script, not the product: a button search for
"View" also matched "Finish Review". The script was fixed to use the exact button name
and the two stages were split so their HR parts could carry on (`d37unstick_hr`,
`d37f2_flag`). The stops are kept in `report.json` as `stage_failures_first_run`.

| Flow | Result | Screenshots |
|---|---|---|
| Both lists for a person with both roles (Arjun) | **Pass.** Reviews tab shows "My team's reviews"; HR Setup shows "HR review list" | 00, 01 |
| Plain manager (Gurpreet Dhillon) | **Pass.** "My team's reviews" shown; no HR Setup tab | 02 |
| Plain HR person (Sumit Kumar) | **Pass.** No team list; HR Setup shows "HR review list" | 03, 04 |
| F1: Arjun on the HR review list, `00417` | **Pass.** Row: View + the "Another HR person…" note, opens as `hr`; inside, Finalize page with the note, **0** answer buttons, no Finish | 05, 06 |
| F1: Arjun on My team's reviews | **Pass.** Row says "Rating needs your answer" with an "Answer rating question" button, opens as `manager`. Last page: "This review is now at HR Review. Your part as the manager is done, except the rating question below.", **2** answer buttons. Clicked "Keep the rating": the question is gone | 07, 08, 09 |
| F1: Sumit Kumar finishes `00417` from the HR review list | **Pass.** Finish enabled, clicked; the row now reads Completed, 3.0 / 5 | 18, 19 |
| F2 setup: Gurpreet submits `HR-APR-2026-00412` (Manpreet Malhotra) from My team's reviews; Manpreet acknowledges | **Pass** | 10–14 |
| F3: Sumit Kumar's row for `00412` | **Pass.** Buttons: Finish Review, View, **Calibration note**, Remind. Box opened empty the first time; note and rating 3.5 saved; **reopened, the box showed the saved note** | 15, 16, 17 |
| F2: Sumit Kumar removes a rated item | **Pass.** Overall rating (his calibrated 3.5) flagged; his Finalize page shows the question with **2** answer buttons and a labelled box for a new rating; Finish disabled; wording "The person who gave it must keep or change it" | 20–24 |
| F2: Gurpreet (manager) looks at `00412` | **Pass.** Row "View Review", no "needs your answer"; last page shows "The person who gave it must keep or change it…", **0** answer buttons, no submit button | 25, 26 |
| F2: Sumit Kumar answers his own rating, then finishes | **Pass.** Typed 3, "Use the rating I typed" (no reason asked: it is his own rating); question gone, Finish enabled; review Completed, 3.0 / 5 | 27, 28 |

## 3. Stored results and rollback dry runs (read-only)

| Check | Result |
|---|---|
| `HR-APR-2026-00417` | Completed; overall 3.0; flag 0; rated by and answered by Arjun Bhatia |
| `HR-APR-2026-00412` | Completed; overall 3.0; flag 0; rated by and answered by Sumit Kumar; calibration note stored |
| `copy_ratings_back_for_rollback {'dry_run': 1}` | **`KPI-2026-01766`** now found (Gurpreet's portal rating on `00407`, a review completed in the first rehearsal). The first rehearsal found 0: **F5 fixed** |
| `undo_backfill {'dry_run': 1}` | undone 801; kept `00417`, `00412`, `00414`, `00407` and **`00418`** (Kavita Jain's review with a discarded removal). The first rehearsal would have undone `00418`: **F6 fixed** |
| Error Log | 0 new rows |

## 4. Seen on the way, not fixed (all older than this round)

- **HR's view of the "Manager Feedback" page shows editable boxes** (`mgr-feedback-ta`,
  `mgr-notes-ta`, the reviewer search) in HR Review. The server refuses any save outside
  Manager Review, so nothing can change; it is a dead end on screen, as before this
  round. Worth folding into F8's page clean-up.
- The same unlabelled inputs as F8 (`pf-review-cycle`, `pf-hr-cycle`,
  `pf-calib-note-text`, `pf-calib-rating`, `mgr-overall-rating`, `mgr-potential-rating`).
  The new box added in this round (`hr-flag-overall-rating`) has a label.

## 5. Data the re-rehearsal left on ppj.localhost (dummy)

| Review | State now |
|---|---|
| `HR-APR-2026-00417` Renu Gupta | Completed (was the F1 reproduction) |
| `HR-APR-2026-00412` Manpreet Malhotra | Completed (manager feedback, calibration note, one rated item removed by HR, overall 3.0) |

The restore point is unchanged: the 12:57 IST backup listed near the top of this file.
