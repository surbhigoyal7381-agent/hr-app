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
