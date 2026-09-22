---
slice: 034-redesign-wave1
artifact: 07-devops-inputs
author: hrms-fullstack-engineer (§1–3 written at the coordinator's request; hrms-devops-engineer to review and add §4)
date: 2026-09-22
status: draft
inputs: [00-impact-analysis.md, ../009-ess-portal-redesign/00f-decisions-2026-09-22.md, ../012-leadership-view/07-devops-inputs.md (OPS-26, OPS-31, OPS-33, OPS-34), ../013-mobile-app/00-sequencing-recommendation.md, .claude/context/nfr-budget.md §2 §3, deploy/nginx.conf, deploy/Dockerfile]
---

# Wave 1 frame — DevOps inputs

**Short, and written by the engineer, not the DevOps engineer.** The DevOps engineer
should review §1–3 and write §4 (their view on the strategy). Where they disagree, they
say so; the user decides.

The Decision column holds what the user has already decided (22 Sep). Blank means not
yet decided.

## §1–3 · 2026-09-22 · What the frame needs from the platform

### The speed budget, made specific

The portal is now every tenant's landing page (slice 024), so these are the numbers the
frame is measured against (nfr-budget §2):

| What | Budget | Measured how |
|---|---|---|
| Something on screen (the shell and a page skeleton) | ≤ 300 ms after the HTML starts arriving | Throttled "Slow 3G / low-end phone" profile, local copy, before and after |
| Home usable on a 3G phone, p95 | ≤ 2.5 s | Same profile |
| `frame_api.get_frame` | ≤ 500 ms p95, ≤ 15 queries warm | Timed test with query count, at the "Typical" 250-employee tenant and a 1,000-employee fixture |
| `inbox_api.get_nav_counts` | ≤ 500 ms p95, ≤ 15 queries whatever the team size | Same |
| Start-up calls | 2 (`get_frame`, `get_nav_counts`), down from 4, with no 1.5 s delay | Count in the browser's network log |

### Where the page stands today

| Fact | Value | Source |
|---|---|---|
| Page size | **1.04 MB** (1,042,972 bytes) | the file, `origin/dev` `1c4e84c` |
| Compressed, if it were compressed | 224 KB (gzip on this PC) | measured today |
| Compression on the server | **None** — `deploy/nginx.conf` has no `gzip` lines | read today |
| Of that, inline script / style | 702 KB / 159 KB | measured today |

**So the frame cannot meet the 3G budget on its own.** It adds roughly 30–40 KB. The
two things that move the number are compression and cached script files — neither is
frame code.

### OPS items

| ID | Recommendation | Why | Cost of ignoring it | Level | Decision |
|---|---|---|---|---|---|
| **OPS-1** | **Compression must be live on dev before the swap goes to dev, and on production before the swap goes to production.** This slice depends on the separate compression slice; it does not build it | 1.04 MB → about 224 KB per visit. The biggest speed win available | The first page everyone sees takes many seconds on a phone; the 2.5 s budget is missed by a wide margin | Recommend | **Taken as its own slice (decision 13).** Dependency recorded here |
| **OPS-2** | **Ship by a parallel preview page and one swap commit.** `/hrms-employee-next` exists during the wave; the swap commit points `/hrms-employee` at the new frame and deletes the preview | Keeps `dev` releasable to production every day while the frame is built | A half-built frame reaches the live tenants in the next release, or releases wait | Recommend | **Approved (decision 2)** |
| **OPS-3** | **Rollback is `git revert` of the swap commit and a normal deploy.** No migration, no data change, no `bench build`, so the revert is clean. The DevOps engineer should state in §4 how long a production deploy takes end to end — that is the real rollback time | nfr-budget §3 asks for rollback ≤ 15 min | We promise a rollback time we have never measured | Recommend | |
| **OPS-4** | **The swap reaches production only after the first client's go-live has settled** (decision 4). Proposed meaning of "settled": the go-live week is over and no portal issue from the client is open. The user confirms the date | A frame change during go-live week would mix two causes of trouble | A go-live problem and a frame problem cannot be told apart | Recommend | **Approved: after go-live settles.** Meaning of "settled" still to confirm |
| **OPS-5** | **What a deploy of each step needs.** Include files are templates read from the app folder, and new `www` pages and Python modules need no migration. So no step in Wave 1 should need `bench migrate` or `bench build`. On the local bench, templates are read from the mounted main checkout; **check before the first bench test whether the page cache needs `bench clear-cache`** (that command needs the user's approval) | Keeps each deploy boring | A surprise migration or build on the release day | FYI | |
| **OPS-6** | **The CI static checks must follow the includes in the same commit as the split.** `check_design_system.py`, `check_portal_handlers.js`, `check_undefined_js.js`, `check_contrast_rendered.py`, `check_attendance_strip.js`, `check_rating_bands.js`, and the JS DOM tests get one shared helper that expands the includes. A check that finds no includes where the page has them fails | These checks are CI's only guard on the page's JavaScript | They pass while reading an empty shell — the checks quietly check less, which looks like safety | Recommend | |
| **OPS-7** | **The page split is pushed to `dev` on its own**, as soon as it passes, so other sessions rebase onto it early. It changes nothing on screen, so it is safe to release | Every branch with page edits must re-apply them in the new files; the sooner, the smaller | Long-lived branches drift further from the split and their merges get risky | Recommend | **Freeze approved in principle (decision 11)**; the coordinator schedules it |
| **OPS-8** | **OPS-31 (move script and style into cached files) comes right after the swap, as its own step.** The include files hold no Jinja, so the move is a rename plus one tag each. Before it, check that the address carries a version so phones do not keep old code (012's OPS-34) | Downloaded once per release, not on every visit | Every visit keeps downloading the page's full script | Recommend | **Approved (decision 12)** |
| **OPS-9** | **Measure before and after on the local copy**: first paint, full load on the 3G profile, bytes, and the two endpoints' query counts. Record them in the implementation notes. Re-measure on dev after the swap | A speed claim needs a number | "Faster" with no number | Recommend | |
| **OPS-10** | **The preview page on production** (if a release happens mid-wave) answers only to System Manager (01c SEC-1). No monitoring needed beyond the usual | It exists for 2–3 weeks | — | FYI | **Approved (decision 3)** |
| **OPS-11** | **The `--fs-xs` change reaches six pages at once** (employee, driver and vendor portals use the token). It rides in its own commit so it can be reverted alone | One line with a wide reach | A layout problem on the driver portal cannot be undone without undoing the frame | Recommend | **Applies to every page (decision 10)** |

## Open questions

| # | Question | Owner | Blocks |
|---|---|---|---|
| 1 | How long does a production deploy take, end to end? (the real rollback time) | DevOps engineer, §4 | OPS-3 |
| 2 | What counts as "go-live has settled" for the swap date? | Surbhi | OPS-4, the production swap |
| 3 | Does the local bench need `bench clear-cache` to pick up new include files? | Engineer, checked at the first bench test, with approval if needed | Step 1's bench test |
| 4 | Is anything in front of nginx on production (a CDN) already compressing? I could not check | DevOps engineer | OPS-1's measured "before" |

## Assumptions

- `[ASSUMPTION]` Figures are for the file, not a browser load. No load was measured today.
- `[ASSUMPTION]` Templates in the production image are baked at build time, like the rest
  of the app, so a deploy is enough for them to take effect.

## Handoff note

To the DevOps engineer: please write §4. The three things I most want checked are OPS-3
(the rollback time), OPS-5 (whether any step needs a build, migration or cache clear
anywhere), and whether OPS-1's dependency order — compression first, then the swap — fits
your plan for the compression slice.
