# Late rules and attendance scoring become Organisation Settings switches

Built locally on 26 Sep 2026, on branch `slice/org-attendance-switches` (from
`origin/dev` 1934fef), in its own worktree. **Nothing pushed. No pull request. No
server, no tenant, no `docker cp`.** Tested in a throwaway container `hrlocal-oas`
with its own Redis (`hrlocal-oas-redis`) and its own fresh site `testoas`
(bind-mounted worktree apps). `hrlocal-bench`, `hrlocal-wa042` and `hrlocal-128`
were not used.

Surbhi approved the strategy on 26 Sep 2026. Her words: *"Every company has their
own rules so we can't have these as features on tenant configurations … move these
to organisation settings and make them toggleable, by default keep them off."*

## What changed, in one paragraph

`late_rules` ("Late Coming Rules") and `attendance_scoring` ("Attendance in
Appraisals") are gone from the tenant feature registry, so the admin console no
longer offers them. In their place HR has two switches on the portal's
Organisation Settings page, in a new "Attendance rules" card: **Late coming and
early exit rules** and **Attendance in appraisal score**. Both are off until HR
turns them on. A switch can be turned on only when the plan has what it needs.
When a switch is off, nothing is deducted or scored, the weekly job does nothing,
and the related screens are hidden. Existing Attendance Deduction records are kept.
A patch turns the switches on for any site whose config named the old features, so
PP Jewellers carries on unchanged.

## File by file

| File | What | Mechanism |
|---|---|---|
| `hrms/hrms/alvoraa_hr_core/features.py` | `org_switch(key)`, `late_rules_on()`, `attendance_scoring_on()`, the two key names. Unset or anything but `"1"` is off (fails closed). | Extend. Frappe's Default store, the one `set_org_setting` already writes. |
| `hrms/hrms/alvoraa_hr_core/attendance_score.py` | Cycle validate and appraisal hook ask `attendance_scoring_on()` instead of the tenant feature. The refusal now says where to switch it on. | Extend |
| `hrms/hrms/alvoraa_late_rules/late_rules.py` | `process_previous_week` (the Monday 02:00 job) returns at once when off. `run_for_range` (HR's catch-up, also behind the rule's desk button) refuses when off, with a sentence saying where to switch it on. `process_week` itself is untouched. | Extend |
| `alvoraa_portal/subscription.py` | The two features removed. **Module ownership:** `Alvoraa HR Core` now belongs to the required `attendance` feature (never hidden, on any plan). `Alvoraa Late Rules` now belongs to `payroll` (attendance and leaves are always sold, so payroll is the one that decides). | Configure |
| `alvoraa_portal/hr_api.py` | Both keys join `ALLOWED_ORG_SETTINGS` as `("0","1")`. `ORG_SWITCH_NEEDS` + `set_org_setting` refuse turning one on without its prerequisites (`has_feature`); turning off is always allowed. New `get_attendance_rule_switches` (HR only) for the card. `_late_rule_for` returns None when off, which hides my deductions, the team list and the Time tab. `get_available_features` adds `org_late_rules` and `org_attendance_scoring` (read live, not from the cached block). | Extend |
| `alvoraa_portal/performance_api.py` | The cycle wizard's scoring step follows the switch. | Extend |
| `alvoraa_portal/time_api.py` | `_rule_explained` answers `switched_on: False` when off. | Extend |
| `templates/includes/ess/parts/org-settings.html`, `public/js/ess/portal.js` | The "Attendance rules" card, `orgLoadAttendanceRules`, `orgSaveAttendanceSwitch`; one call added in `switchPanel('org-settings')`; `apsScoringSold()` reads `org_attendance_scoring`. | Build (small) |
| `public/js/ess/next-time.js` | The preview portal's Time screen drops the Late rule tab when `switched_on` is false. | Extend |
| `patches/v1_0/org_attendance_switches_from_features.py` + `patches.txt` | Sets a switch to `"1"` where the site's `features` named the old key, unless HR already set it. | Patch |
| `demo/pp_jewellers/provision_ppj.sh` | Drops the two keys from the feature list; a new step 2b sets both switches on. | Demo only |

**Why a module import in `hr_api.py` and the patch:** `scripts/check_app_integrity.py`
only recognises functions and classes when one app imports from another, so the two
key constants are read as `org_features.LATE_RULES_SWITCH` through
`import hrms.alvoraa_hr_core.features as org_features`. The integrity check passes.

**The preview portal's `company/settings`** (`next-frame.js`) still shows the "keeps
the screen it has today" note and no screen of its own, so it needed no change.

## The approved points, and how each is met

| Point | Met by | Pinned by |
|---|---|---|
| 1. Registry no longer offers either key | `subscription.py` | `TestTheConsoleNoLongerSellsThem` (5 tests) |
| 1. HR Core never hidden; Late Rules wherever attendance, leaves, payroll are sold | module_defs on `attendance` and `payroll` | `TestTheModulesStayAvailable` (3), `TestSyncSiteDoesNotHideThem` (real `sync_site` on the business plan: neither module hidden in either profile, none of their doctypes denied) |
| 2. Two switches, default off, HR only | `ALLOWED_ORG_SETTINGS`, `org_switch` | `TestTheSwitchesDefaultOff` (4), `TestOnlyHrReadsAndChangesThem` (4) |
| 2. Old gates replaced | 7 call sites listed above | `TestOffMeansNothingHappens` (9) |
| 3. Prerequisites, and why unavailable | `ORG_SWITCH_NEEDS`, `get_attendance_rule_switches` | `TestPrerequisitesAreEnforced` (3) |
| 4. UI card, neutral wording | `org-settings.html`, `portal.js` | portal checks (below); DOM test for the Time tab |
| 5. Patch for existing tenants | patch file | `TestThePatchTurnsOnExactlyTheSitesThatHadThem` (6) |
| 6. Old labels renamed | The two labels existed only in the registry, which is gone. The card uses the new names. | — |
| On means today's behaviour | unchanged engine | `test_late_minutes_017`, `test_time_api_043`, hrms `test_attendance_score` switch the rule on for their classes and pass unchanged; plus the "when on" tests in the new file |

## Seven dimensions, against the code as written

| Dimension | Verdict | Why |
|---|---|---|
| Performance | neutral | `org_switch` reads Frappe's cached defaults: no query on a warm cache. `_late_rule_for` returns before any query when off. |
| Security | improves | Server refuses a switch the plan cannot support; HR only; store HR refused like every other org setting; no new visibility. |
| Reliability | neutral | Fails closed. The weekly job is a no-op when off. Records are never deleted. |
| Scalability | neutral | One cached read per request or per weekly run. |
| Maintainability | improves | One helper both apps use; the two rules no longer ride on the tenant feature machinery. |
| Data integrity | neutral | Existing deductions and scores untouched. Patch never overwrites a value HR set. |
| Compliance / privacy | neutral | No personal data in any new response or log. Deduction of pay now needs an explicit HR decision per company. |

## Proof: what was run, and what it said

All in `hrlocal-oas` / `testoas`, a fresh site built the way CI builds one, one module
at a time.

| Run | Result |
|---|---|
| New `test_org_attendance_switches` | **34 tests, OK** |
| hrms `test_attendance_score` (now 12, one new switch-off test) and `test_late_rules` | **17 tests, OK** |
| Neighbours: opt_in_features, late_minutes_017, time_api_043, why_sheet_043, portal_security_010, module_access, subscription_access, org_settings_allowlist_012, org_setting_scope_030, frame_api_034, personas_012, payslips_payload_043, frame_endpoint_registry_034, scale_flatness_044, portal_call_paths | **426 tests, OK** (1 skipped in scale_flatness, as before) |
| **Total** | **477 tests, 0 failures** |

- `check_app_integrity.py`: OK (first run failed on the cross-app constant imports; fixed as described above).
- CI portal checks: design system, portal handlers, undefined JS, rating bands, tag
  balance, preview flag, assets gate, API paths (`--max 2`), min app version, demo
  passwords, tracked keys: all OK.
- jsdom DOM tests (`run_dom_tests.js`): 8 files, 0 failed. `next_time_pay_test.js`: 63
  passed, including the two new "switched off: no Late rule tab" checks.
- ruff 0.6.9 on the changed files: no new findings on my lines. The files carry older
  findings and older formatting, which CI does not block on.
- The whole `alvoraa_portal` suite was **not** run end to end; the modules above are the
  ones that touch the registry, module access, org settings, the late rule, the Time
  screen and scoring.

## Parallel work

- Work board row added. Incoming from `origin/dev` at start: none beyond 1934fef.
- `portal.js`, `hr_api.py` and `org-settings.html` are also touched by the unpushed
  redesign wave branches (034/042/043/045) and slice 050. My edits are additions in
  their own blocks (one line in `switchPanel`, one function body in `apsScoringSold`).
  Expect small, easy rebase conflicts there; keep both sides.

## Known gaps and shortcuts

- **Acceptable simplification:** the switch is checked only when set. If a tenant later
  loses payroll while late rules are on, the rule keeps acting until HR turns it off
  (the Late Rules module itself becomes blocked in the desk by the normal sync). Turning
  off is always allowed.
- **Intentional trade-off:** the Alvoraa Late Rules module (the rule form and the
  "Late Coming Deductions" report) is now visible in the desk to every payroll tenant,
  even with the switch off. With the switch off the rule does nothing.
- **Intentional trade-off:** a cycle that already includes attendance cannot be saved
  while the switch is off (same as before, when the feature was off). The message says
  how to switch it on.
- **Not done:** no hand check in a real browser of the new card (the portal checks and
  jsdom tests ran; no running portal in this container).
- Old keys in site config are left in place and ignored, as approved.

---

## Review fixes (26 Sep 2026, "fix all as suggested")

The review said SHIP WITH FIXES. Five fixes, each its own commit on the same branch,
rebased first onto `origin/dev` 0ed32b7. **What came in:** four ALV-127 commits
(2894a1d, e93f280, 17dcd9e, 0ed32b7). They add a read-only permission-freeze check
(`permission_health.py`), its tests (048), a runbook, and one line in
`DEPLOYMENT_RUNBOOK.md`. None of those files overlap with this slice, and the rebase
ran without conflicts.

| # | Problem | Fix | Test |
|---|---|---|---|
| 1 (P2) | A tenant synced before the move kept its deny rows on Alvoraa Late Rules. Turning late rules on left Attendance Deduction Rule with no permissions, because nothing re-runs `sync_site` on a deploy. | New patch `resync_access_after_attendance_switches`. It runs `sync_site` once, only on a site that currently has recorded restrictions. It skips the control plane, and it skips sites never synced (developer and test sites), so it cannot bring deny-by-default to a site that never had it. It is safe to run twice. A failure is logged and does not stop the migrate. | `TestTheResyncPatchMovesExistingTenants` (5): the old deny state is rebuilt, then after the patch HR Manager can read the rule on a payroll site and still cannot on starter. Also covered: running twice, never synced, control plane, a failure. |
| 2 (P2) | Turning scoring off in the middle of a cycle broke open cycles: the formula kept using a stale score, and "complete cycle" would be refused. | `set_org_setting` refuses to turn `attendance_scoring_enabled` off while any cycle that is not Completed has `include_attendance_score = 1`. The message names the cycles: "Finish or change these appraisal cycles first: …". | `TestScoringCannotBeSwitchedOffUnderAnOpenCycle` (4), both ways, on a real cycle record. |
| 3 (P2) | Turning late rules off hid deductions already taken. | Off, with past records: `get_my_attendance_deductions` still returns the history (no rule terms, no this-week projection). The Time tab stays, read-only, when `record_this_year` has weeks, and says the rule is off. Off with no records: hidden, as before. | 2 server tests; 3 new jsdom checks in `next_time_pay_test.js`. |
| 4 (P3) | A store's HR person saw a live box that flipped back when they saved. | `get_attendance_rule_switches` returns `can_edit`, from the same rule `set_org_setting` uses (`frame_api._may_save_settings`). When it is false, both boxes are greyed out, with "Only HR with company-wide access can change these." | `TestAStoreHrPersonSeesThemGreyedOut` (2). |
| 5 (P3) | Notes | This section. | — |

**Still hidden when off (a deliberate choice):** the manager's team late list. It is
mostly this week's projection, and its "last 4 weeks" line is about other people, so
it stays hidden when the switch is off.

### Release notes for this change

- **Visible to HR on every payroll tenant:** the "Late Coming Deductions" report and
  the Attendance Deduction list and rule form. After the resync patch, HR sees them in
  the desk wherever payroll is sold, even with the switch off. With the switch off,
  nothing new is added to them.
- The resync patch changes permissions on every tenant that has been synced before. It
  applies the tenant's current plan, the same way a plan change in the console does.
  If it fails on a site, the Error Log shows "module_access: resync after attendance
  switches failed". The fix is to run
  `bench --site <site> execute alvoraa_portal.module_access.sync_site`.
- Attendance scoring cannot be turned off while an open appraisal cycle counts
  attendance. HR finishes or changes those cycles first.

### Design notes

- **The switch covers the whole tenant; the rule values are set per company.** The
  switch is one Frappe default for the whole site. The rules themselves (threshold,
  free lapses, deduction, leave order, exempt grades) stay on Attendance Deduction Rule,
  one per company and shift, and the cycle weights stay per cycle. This is deliberate.
  A group that wants a rule for only one company turns the switch on and enables a rule
  for that company only.
- **Rebase warning.** Branches 034, 042, 043 and 044 carry
  `return !!f.plan_attendance_scoring;` in `portal.js` (`apsScoringSold`). When they are
  merged or rebased onto this change, **keep `return !!f.org_attendance_scoring;`**.
  `plan_attendance_scoring` no longer exists, so keeping it would hide the attendance
  step of the cycle wizard for everyone, and nothing would error.
