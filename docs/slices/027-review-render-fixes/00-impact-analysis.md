# Slice 027 — Review render fixes: impact analysis and strategy

Written 2026-09-19. Branch `slice/027-review-render-fixes`, worktree
`.claude/worktrees/027-review-render-fixes`, cut from local `dev` at `3f5ce3d`.

There is no `02-functional-spec.md` for this slice. The user's bug report of
2026-09-19, from her own testing on `ppj.dev.alvoraa.co`, is the spec. Everything
below is measured against it.

---

## 0. What moved while I worked (start-of-work check)

- `git fetch origin dev`: **nothing came in.** `origin/dev` is `baa9f68`; local
  `dev` is `3f5ce3d` and holds four commits that were never pushed
  (`d1fd9c6`, `4f35960`, `99a17a4`, `3f5ce3d`). `git log dev..origin/dev` is empty,
  so there is no incoming diff to read.
- Main checkout has other sessions' work in progress. **None of it is mine and I
  touched none of it**: `.claude/context/ux-learnings.md`,
  `backlog/KPI_AUTOMATION_BACKLOG.md`,
  `docs/slices/009-ess-portal-redesign/00-assessment-and-plan.md`,
  `hrms/.../alvoraa_position.py`, a deleted `OBJECTIVES_KPI_REQUIREMENTS.md`, and
  several untracked docs folders.
- Work board read. Row added for this slice.
- Bench: `pgrep -af run-tests` found nothing. Free at the time of writing.

---

## 1. The real cause of each blocker — verified, not assumed

### Blocker A — half-point ratings fall to the lowest band

**Her inference is correct, and it is client-side only.** The server is innocent:
`get_calibration_matrix` returns the raw `overall_rating` / `potential_rating`
floats and the scale's items. All the banding happens in
`alvoraa_portal/.../www/hrms-employee.html`.

The defect is one function, `_toZone` (line ~12266):

```js
var v = parseFloat(val), idx = sorted.indexOf(v);
if (idx < 0) idx = 0;                      // <- anything not an exact scale value
var norm = sorted.length > 1 ? idx / (sorted.length - 1) : 0.5;
return norm < 0.34 ? 0 : (norm < 0.67 ? 1 : 2);
```

`sorted` is `[1,2,3,4,5]`. A 4.5 is not in it, so `indexOf` returns `-1`, which is
forced to index `0` — the bottom of the scale. This reproduces her table exactly:

| value | `idx` | `norm` | zone today | zone it should be |
|---|---|---|---|---|
| 1 | 0 | 0.00 | Low | Low |
| 1.5 | **-1 → 0** | 0.00 | Low | Low (right by accident) |
| 3 | 2 | 0.50 | Moderate | Moderate |
| 3.5 | **-1 → 0** | 0.00 | **Low** | Moderate |
| 4 | 3 | 0.75 | High | High |
| 4.5 | **-1 → 0** | 0.00 | **Low** | High |
| 5 | 4 | 1.00 | High | High |

Only an exact 3 reaches the Moderate column, which is why the whole Moderate
column is empty for all 403 people — her strongest tell.

The same exact-match assumption appears in **four more places on these two tabs**,
and each one drops or mislabels the same half-point ratings:

1. **The 1D fallback grid** (`_calRender`, no potential scale):
   `rows.filter(r => parseFloat(r.overall_rating) === parseFloat(col.value))` —
   a 4.5 lands in no column at all and vanishes from the page.
2. **`_pdBuildDist`** (both bell curves): counts into a map keyed by the exact
   value, then reads only the keys that are scale items. 204 of 403 overall and
   99 of 403 potential are counted and then never read. This is why the curves
   plot 199 and 303.
3. **`_pdStats`** computes the average, the median and "% above expectations"
   **from that same dist array**, so the stats inherit the loss. That is precisely
   her exclusion arithmetic: 833/199 = 4.186 → displayed 4.2, against a true
   1734/403 = 4.303; and 996/303 = 3.287 → displayed 3.3, against a true
   1264.5/402 = 3.146.
4. **Both CSV exports** and `_pdLabel` look the label up by exact value, so a 4.5
   exports with a blank band label.

**The null potential row.** `get_calibration_matrix` sends
`flt(ext.get("potential_rating"))`. `potential_rating` is a **Float** on
`Alvoraa Appraisal Extension`, so "never rated" is stored as `0.0` and `flt`
cannot tell it from a real zero. `0.0` then goes through `_toZone` → index 0 →
Risk. That is the one person sitting in Risk while the header still claims 403
plotted.

### Blocker B — `page_config` empty, so review items never render

**Not the cycle wizard, and not slice 010's code. It is the PP Jewellers demo
seed script.**

`demo/pp_jewellers/seed_performance.py`, line 112, creates the
`Alvoraa Cycle Config` for both cycles with the page list hard-coded empty:

```python
"employee_fields": "{}", "page_config": "[]",
"page_settings": json.dumps({"manager-feedback": {...}, "scoring": {...}}),
```

Three things make this conclusive rather than likely:

- It writes a literal `"[]"` — an empty **list**. That is exactly the shape she
  saw come back (`page_config: []`). The wizard never writes a list; it sends
  `JSON.stringify({key: true})`, an object, and `save_cycle_wizard` stores that
  string unchanged.
- The same `insert` call populates `page_settings` with the rating scales and
  weights **targets 50 / manager feedback 30 / attendance 20** — byte-for-byte
  what she reported, and what lines 113–116 of the seed write.
- The cycle names `Q1 FY27 Performance Cycle` and `Q2 FY27 Performance Cycle`
  are the seed's own `Q1` / `Q2` constants.

So "both cycles are empty" does not point at Launch Cycle failing to persist —
it points at both cycles having been created by the same seed script, which
never filled the field. The wizard path is sound but has **no test proving it**,
which is why nobody caught this.

The client handles both shapes correctly (`prOpenReview` and the manager view
both normalise object-or-array), so with a correct `page_config` the pages appear.

**The silent part is a real second defect.** `prOpenManagerReview` builds its page
list from `page_config`, appends its three hardcoded pages, and renders. If the
review holds goals and KPIs but the list yields no page for them, **nothing says
so** — Kamal Gupta's three active Q2 KPIs simply were not there. Her rule
applies: that is a fault to surface, not to swallow.

**`numbers_frozen` at Manager Review — the code is right.** `FREEZE_STEP` maps
`Self-review sent → 1`, `Manager review sent → 2`, `HR sent → 4`, and
`STAGE_STEP` puts `Manager Review` at 1. The default freeze point is
`FREEZE_HR_SENT` (`review_items.py` line 64), so `1 >= 4` is false and `0` is the
correct answer for a cycle left on the default. The setting is stamped onto the
extension when the review is first opened (`ext.freeze_point`) and honoured by
`_refreeze`, so the code does follow Org Settings. I cannot read PPJ's dev tenant
(forbidden), so I will prove the behaviour locally at each of the three settings
instead of reading her tenant.

### The four smaller items

| Item | Verified cause |
|---|---|
| Stepper icon prints as text | `.ic-check` is a real CSS mask icon (`design_system.html` line 48). It is being used where only text can go: `.psb-dot.done::after{content:"<i class=ic-check></i>"}` (line 1634) and `dot.textContent = "<i class=ic-check></i>"` (line 14835). Three more `textContent` sites have the same bug: lines 11189, 14916, 16293. |
| Two dropdowns both "PPJ 5-POINT" | `prRenderManagerSubmitPage` labels each picker with `scale.scale_name`. Both pickers use the same scale, so both labels read the same. The labels are also plain `<label>` with no `for`, so a screen reader gets nothing either. |
| Sign-off date not printed | Field-name mismatch. `get_calibration_signoff` returns `signed_on`; `_calShowSignoffBanner` reads `d.signed_at`, which is `undefined` → the string ends at "on ". |
| 500 instead of 400 | Reproduced in-process on `test_site` (Frappe 16.33.1). `frappe.call(hr_list_appraisals)` → `TypeError: missing 1 required positional argument: 'cycle'` → no `http_status_code` → **500**. **Her second half is a misdiagnosis**: unknown keyword arguments do *not* 500 — `frappe.get_newargs` drops them, and `frappe.call(get_manager_review, appraisal="NOPE", bogus=1)` gave the normal 404. The 500 comes from the *required* argument being absent (`get_manager_review()` with no `appraisal` → 500). Both endpoints need a missing-argument guard, not an unknown-argument one. |

---

## 2. Functional impact

**Cross-module reach.** `alvoraa_portal` (the portal page and `performance_api.py`),
`alvoraa_goals` (`review_items.py` — read only, no change planned), and `demo/`.
No reach into `hrms`, `erpnext` or `alvox_compensation`.

**Callers grepped.**

| Thing I will change | Callers found | Effect |
|---|---|---|
| `_toZone`, `_calRender`, `_pdBuildDist`, `_pdStats`, `_pdLabel` | Private to their two IIFEs in `hrms-employee.html`. No external caller. | None outside the two tabs |
| `get_calibration_matrix` return payload | `hrms-employee.html` (calibration tab, distribution tab) and `tests/test_review_outside_010d.py` lines 439, 480, 529 | `potential_rating` may now be `None` instead of `0.0`. Line 480 reads a plotted row; I will check it still passes |
| `hr_list_appraisals` signature | `hrms-employee.html` (HR review list) and the portal call-path tests | `cycle` gains a default of `None`; every existing caller passes it |
| `get_manager_review` signature | `hrms-employee.html` (manager and HR review) | `appraisal` gains a default of `None` |
| `seed_performance.py` | Run by hand for the PPJ demo only | New cycles get a real page list |

**Persona impact.**

| | CXO | HR Manager | Employee |
|---|---|---|---|
| A (9-box + charts) | Sees a correct grid for the companies they oversee. No change to *which* rows they see — `_hr_cycle_reviews` is untouched. | The promotion/succession grid becomes correct for half the company, and mostly in the upward direction. **Q1 was signed off on the wrong grid** — see §6. | No change. Employees never see the calibration tab, and PRIV-1 (never your own potential rating) is untouched. |
| B (page_config) | No change. | New cycles launched from the wizard carry their page list; a review that holds items but has no page now shows a warning instead of nothing. | Self-review finally shows the objectives and KPIs page. Kamal Gupta's three Q2 KPIs appear. |
| Smaller items | Sign-off date reads correctly. | Correct stepper tick; the two rating pickers are told apart. | Correct stepper tick in their own review. |

**HRMS domain impact.** Appraisals and calibration only. Nothing touches leaves,
attendance, payroll or org structure. No DocType change, no schema change, no
patch, no migration.

---

## 3. Non-functional verdict

| Dimension | Verdict | Why |
|---|---|---|
| **Performance** | neutral | All client work. `_toZone` currently re-sorts the scale on every single cell lookup — 403 rows × 2 = 806 sorts per render. I will hoist that to one sort per render, so if anything it improves. No new server query; query count on both endpoints is unchanged. |
| **Security** | neutral | No permission path touched. `_require_hr()`, `_hr_cycle_reviews` and `_assert_hr_can_view` stay exactly as they are. The 400 guards run before any data is read, and say only which argument is missing — no record names, no data. |
| **Reliability** | improves | Two silent failures become loud: a review with items and no page now warns, and a missing required argument becomes a clean 400 instead of an uncaught `TypeError`. |
| **Scalability** | neutral / slight improve | Same data volume, fewer sorts per render. |
| **Maintainability** | improves | The banding rule becomes one named, exported, testable function instead of four copies of an exact-value comparison. |
| **Data integrity** | **improves, materially** | The grid stops misreporting half the company. A "not rated" potential stops being indistinguishable from a rating of zero. |
| **Compliance / privacy** | neutral, watched | This is an automated-decision surface (promotion, succession, pay banding), so the obligation is that the derivation is replayable and that a named human is accountable — both already exist via the calibration note and sign-off, and I am not changing them. **I will not widen visibility**: no new field enters any row, list, export or notification. The one payload change is a *narrowing* — `potential_rating` becomes `None` rather than a misleading `0.0`. No personal data enters any log line I add. |

**NFR budget.** No new query, no new index needed, no background job, no external
call. Render cost for 403 rows stays well inside the budget.

---

## 4. Parallel-work check

| File | Who else is in it | Plan |
|---|---|---|
| `alvoraa_portal/.../www/hrms-employee.html` | The hottest file in the repo (37 commits in 30 days). Slices 010, 024, 025 and 013 all have rows on the board. | My edits are confined to four already-named regions: the distribution IIFE, the calibration IIFE, `prRenderManagerSubmitPage`, and five icon lines. I move and re-indent nothing else and rename nothing shared. Rebase on `dev` before handing off. |
| `performance_api.py` → **`get_calibration_matrix`** | **Another session owns the branch-scoping leak in this same function** (403 rows instead of 72). | **Real overlap.** Their change is inside `_hr_cycle_reviews` / the scoping filter; mine is two lines in the row-building block (`potential_rating` null) and nothing else. Different lines, same function. I will say so in the commit message. If git puts a conflict here, the resolution is: keep their scoping filter *and* my null handling — both, never one. |
| `performance_api.py` → **`hr_list_appraisals`** | Same other session owns its scoping leak. It also carries the `hr_steps_elsewhere` flag, which is a **separate brief and not mine**. | I add a default and a guard on the **signature line and the first line of the body only**. I do not touch `_hr_cycle_reviews`, the scoping, or `hr_steps_elsewhere`. |
| `demo/pp_jewellers/seed_performance.py` | Nobody on the board. | Mine for this slice. |
| `scripts/` | Nobody on the board. | New file only. |

**Not mine, and I will not touch them:** the store-HR scoping leak in
`hr_list_appraisals`, `get_calibration_matrix` and the Cumulative KPI report; and
the dead `hr_steps_elsewhere` flag.

---

## 5. What I recommend — and the two decisions you asked me to make

### Decision 1 — the null potential row: **exclude it from the grid, and say so**

Recommendation: **exclude, visibly.** A 9-box cell is a claim about a person. Placing
someone in "Risk" because nobody filled in their potential rating is a false claim
in the worst direction, and it is the same class of error as Blocker A. Silently
dropping them is no better, because the header already lies about 403.

So: the server sends `potential_rating: null` when nothing was rated (stored `0.0`,
since the field is a Float and a real rating is 1–5), the grid plots only rows that
have both ratings, and the summary line reads:

> **402** employees plotted · **1** not plotted — no potential rating

with the unplotted people named under it, so HR can go and fix the cause. The 1D
fallback (no potential scale) keeps plotting on overall alone, as it does today.

### Decision 2 — `numbers_frozen` at Manager Review: **0 is correct, leave the logic alone**

With the shipped default ("HR sent"), numbers close when HR sends, so a review
sitting at Manager Review is genuinely still open. The code reads the Org Settings
value, stamps it on the review when it opens, and honours it. I will add a pin test
covering Manager Review under all three settings rather than change behaviour. If
PPJ's tenant has deliberately chosen "Self-review sent" and still reads 0, that is a
different bug and I will need you to tell me the setting — I will not read the dev
tenant.

### The banding rule I propose

One exported function, `pfRatingBand(value, scaleValues)`, used by every place that
bands a rating:

```
norm = (value - min) / (max - min)        // position on the scale, not index
zone = norm < 1/3 ? Low : norm < 2/3 ? Moderate : High
```

On a 1–5 scale that gives exactly her expected table: 4.5 → High, 3.5 → Moderate,
4 → High, 1.5 → Low, 3 → Moderate. The Moderate column stops being empty.

**The bell curves: one extra decision worth naming now.** A bar chart's bars are the
scale's five bands, and 204 people do not sit on a band. Two options:

- **(a) Round each rating to a band.** 4.5 is exactly between 4 and 5, so a tie rule
  has to be invented, and either choice moves 187 people. Rounding up would invent
  187 "Outstanding" ratings. **I do not recommend this.**
- **(b) Give the chart a bar for every rating value actually present** — 3.5 and 4.5
  get their own bars between the named ones, labelled with the number. Nothing is
  rounded, nothing is invented, all 403 are plotted, and the shape of the curve
  becomes honest for the first time.

**I recommend (b).** `overall_rating` is a computed average and half-points are real
by design, so the chart should show them.

The statistics (average, median, % above expectations) will be computed from the
**raw row values**, not from the bars, which is what makes them come out at her true
4.303 / 3.146 and a median of 4.5 rather than "Exceeds Expectations".

### The rest

| # | Change | Mechanism | Why this one |
|---|---|---|---|
| A1 | `pfRatingBand` + `_toZone`, 1D grid, `_pdBuildDist`, `_pdStats`, `_pdLabel`, both CSVs | extend existing page code | The cheapest thing that fixes all five copies once |
| A2 | `get_calibration_matrix` sends `null` for an unrated potential; grid excludes and reports | extend | Decision 1 |
| B1 | Seed writes a real `page_config` (`past-objectives`, `future-objectives`, `manager-feedback`) matching what the wizard produces | fix the seed | It is the actual cause |
| B2 | A review with items but no page for them shows a warning naming the count, in both the self and manager views | extend | Your rule: surface, never swallow |
| B3 | Pin test that the wizard's own save/read round-trip keeps `page_config` | test only | Proves the wizard was never the cause, and keeps it that way |
| C1 | Stepper tick renders (CSS `content` + four `textContent` sites) | fix | HTML in a text slot |
| C2 | Rating pickers labelled "Overall rating" / "Potential for next role", scale name as a hint, real `for`/`id` pairing | fix | Also the accessibility fix |
| C3 | Sign-off banner reads `signed_on` | fix | Field-name mismatch |
| C4 | `hr_list_appraisals` and `get_manager_review` give a clean 400 on a missing required argument | extend | A local exception class with `http_status_code = 400`; verified Frappe reads that attribute (`app.py` line 388) |

### Tests, and the fail-without-fix proof

- **`scripts/check_rating_bands.js`** — a node pin that loads `hrms-employee.html`,
  extracts the banding and stats functions, and asserts **her own arithmetic**:
  4.5 → High, 3.5 → Moderate, the Moderate column is not empty, all 403 plotted,
  average 4.303 / 3.146, median 4.5. Proof it fails without the fix: run it against
  `git show dev:…hrms-employee.html`.
- **Python pins** in a new `tests/test_review_render_027.py`: the unrated potential
  comes back `None`; a cycle config saved by the wizard reads its `page_config`
  back unchanged; the seed's page list is non-empty; `numbers_frozen` at Manager
  Review under all three freeze settings; the missing-argument 400 on both
  endpoints; `get_calibration_signoff` returns `signed_on`. Each proved to fail
  without its fix by an in-process switch-off from a temp script on stdin.
- `python scripts/check_app_integrity.py`, `check_undefined_js.js` and
  `check_portal_handlers.js` before each commit.

---

## 6. What existing tenants need doing to them — flagged now, not built

Fixing the seed does nothing for the two cycles that already exist in
`ppj.dev.alvoraa.co`, and I will not write to a dev tenant. **Both cycles need their
`Alvoraa Cycle Config.page_config` filled in** before anyone can see an objective
inside a review there. I will ship a short, idempotent repair snippet in the
implementation notes for you to run when you choose, and the new warning banner
means that until it is run, the fault is visible rather than silent.

**Q1 FY27 is the harder one.** It was signed off on a grid that was wrong for 51% of
the company, in the direction that under-rates people. That is a decision-bearing
record. I am not touching it. Deciding whether Q1's calibration has to be re-run is
yours, and it is worth naming before this ships.

---

## 7. Where I would stop and ask

- If the scoping session's change lands in `get_calibration_matrix` or
  `hr_list_appraisals` first and my rebase conflicts on the same lines.
- If PPJ's Org Settings freeze point turns out not to be the default.
- If you prefer option (a) for the bell curves.

**Nothing is built yet. Waiting for approval on §5 before opening a file.**
