# 085 baseline diff: full `bench run-tests --app alvoraa_portal`, base vs slice (20 Nov 2026)

**Result: the 24 payslip/pay-screen/feature-gate/plan failures and the ~142 setUpClass failures are NOT caused by slice 085. They fail the same way on the base. (Proven by the name-set diff below.)**

## Runs (all run by me or read from the engineer's log)
- Base: commit 101fd29b (worktree `085-base-check`), container `alv085-base-run`, `bench --site test_site run-tests --app alvoraa_portal`. Three summaries: 71 OK; 3,092 tests, 15 failures + 236 errors; 1,256 tests, 16 failures + 14 errors = 281 failing rows. Ran it.
- 085: engineer's log `/tmp/full2.log` on alv085-bench2 (code 487867d0): 71 OK; 3,101 tests, 16 failures + 228 errors; 1,311 tests, 16 failures + 14 errors = 274 failing rows. I read it and did not repeat it.
- Site setup difference: the base ran on a COPY of bench2's `test_site` (new volume `alv085c-sites`, database `base_clone` cloned from bench2's by mysqldump, own redis `alv085-redis-base`), because bench2 shares a database with the engineer, who was working there. So the copy already carries 085's schema and the leftovers of earlier runs; the base code ran on top of it. Same image, same installed apps (frappe, erpnext, hrms, alvoraa_portal; alvoraa_goals not installed). The clone is a snapshot taken after bench2's runs, not the exact state at the time of the engineer's full run.

## Name diff (failing test names, base vs 085)
- Failing on both: **273**.
- Failing on 085 only: **1** - `test_punch_rights_alv332.ReadOnlyOutsideHR.test_alv332_the_refusal_is_real`. Already known (round-2 report, defect 1); it passes alone on base and fails alone on 085.
- Failing on base only: **8** - five in `test_expense_evidence_081`, two in `test_own_record_permission_alv249` (SafeToRunTwice), one in `test_joiner_079`. Not 085 code; most likely order or site-state effects on the base run [inference, not investigated].
- So none of the 24 fail only on 085, and no new class failure was introduced by 085 beyond the alv332 test.

## What this does not show
- Both runs share the same pre-existing environment failures (alvoraa_goals not installed, missing doctype in setUpClass). They hide any 085 regression inside those classes, because those tests never ran on either side. Not checked.
- Why the 24 pass alone but fail in the full run is not explained here; it is the same on base, so it is a pre-existing order/leak problem, not 085.
