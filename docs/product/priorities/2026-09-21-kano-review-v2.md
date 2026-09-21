---
artifact: kano-review
scope: whole product — v2, incorporating UX usability evidence and DevOps effort/run-cost notes
author: hrms-product-manager
date: 2026-09-21
status: draft
supersedes: docs/product/priorities/2026-09-21-kano-review.md
inputs: [docs/product/priorities/2026-09-21-kano-review.md (v1, superseded),
  docs/product/priorities/2026-09-21-ux-evidence.md, docs/product/priorities/2026-09-21-ops-notes.md,
  alvoraa_goals/alvoraa_goals/alvoraa_goals/doctype/kpi/kpi.py (direct read, this session),
  alvoraa_goals/alvoraa_goals/controllers/kpi.py (direct read, this session),
  alvoraa_goals/alvoraa_goals/hooks.py (direct read, this session)]
---

# Kano review v2 — corrected for UX and DevOps evidence

**Bad news first: the v1 draft got one fact wrong, and it changes a ranking.** v1 said
`KPI.py` was "an empty `pass` controller" with the weightage-must-total-100 rule
"enforced nowhere." That was true of the file it checked
(`alvoraa_goals/alvoraa_goals/doctype/kpi/kpi.py`) but that file is normal Frappe
boilerplate — every doctype gets one, and the real logic usually lives elsewhere.
`hrms-devops-engineer` found the real controller
(`alvoraa_goals/alvoraa_goals/controllers/kpi.py`, 212 lines) already enforces the rule,
and I verified this myself rather than taking either subagent's word for it:

- I read `controllers/kpi.py` directly. `_validate_weightage_budget()` sums an
  employee's KPI weightages for one appraisal cycle and throws if the total would pass
  100%. `refuse_rating_changes()` also blocks a rating being written on the live KPI —
  ratings now live only on a review's own copy.
- I read `hooks.py` directly (lines 33–47). `"KPI": {"validate":
  "alvoraa_goals.controllers.kpi.validate_kpi", ...}` — `validate_kpi` calls
  `_validate_weightage_budget` as one of its steps. `refuse_rating_changes` is wired on
  `before_validate`. Both are live wiring, not dead code.
- **What I could not independently re-run:** I do not have shell access in this
  session, so I could not personally execute `git diff origin/dev` or `git merge-base
  --is-ancestor` the way DevOps did. I'm relying on DevOps's stated method for the
  "already on `origin/dev`" claim specifically. The functional claim — that the
  enforcement code exists and is wired — I confirmed myself, independent of DevOps,
  by reading the files. `[ASSUMPTION]` DevOps's git-ancestry check was run correctly;
  worth a second pair of eyes only if anyone doubts it, since I can't re-run it here.

**Net effect: C1 is not "not built." Its backend is built, wired, and already on
`dev`.** What's actually left is much smaller — see the corrected §5 and §6 below.

---

## 1 · Current state — correction to v1 §1

Everything in v1 §1 stands **except** the "Correction to §3's authoring-layer claim"
paragraph, which is itself wrong and is replaced:

**Corrected:** The KPI weightage-must-total-100 rule **is enforced**, server-side, on
the `KPI` doctype, as of a commit already on `origin/dev` (introduced as part of slice
010 group D — the code's own comments say so: "SEC-2, R13, PRIV-9"). Direction-aware
attainment (`Higher is Better` vs `Lower is Better`), a non-zero-target check, and a
status engine are also there. What is **not** enforced, confirmed by
`hrms-ux-designer`'s direct read of `hrms-employee.html:4703-4707`: the authoring
screen has a `<div id="pf-k-weight-hint">` — a place to tell someone their running
total as they type a KPI's weightage — that has never had text put in it. The only
places a weightage total is shown today are all downstream of authoring (a goal-picker
dropdown hint, an appraisal review card, an HR table that colours a number amber with
no link to the offending row) — none at the point of data entry, none offering "fix it
here." **The practical risk this creates: a Must-be fix that lands as a worse
experience than today's** — a save that used to silently accept a wrong total now
silently fails with no explanation, the first time the new rule bites someone typing
their third KPI.

---

## 2 · Pending — unchanged from v1 §2, with one addition

v1 §2's slice table stands. Two things DevOps and UX found that materially affect
sequencing, not the list itself:

- **Slice 012's gzip-compression fix is measured, tested, staged as two commits — and
  not yet pushed.** It directly blocks candidate C5 (frontline two-minute review):
  the current portal shell is 977 KB uncompressed, 18.4 s cold load on throttled 3G,
  5.7 s even warm (the page is `no_cache`). A two-minute review target cannot survive
  an 18-second page load on the same phone, for a reason that has nothing to do with
  C5's own code. This is a small, already-done fix sitting idle.
- **The existing performance-review wizard is confirmed unreadable on a phone today**
  (slice `003`'s M04 finding, re-confirmed by UX this session, not just a dated note):
  step labels run together ("EMPLOYEEMANAGER"), the desktop two-column layout squeezes
  the right column to two visible letters. This is broken **today**, for every
  employee, independent of any redesign — it is not merely "rough."

---

## 3 · New candidates — unchanged from v1 §3

No new candidates identified this round; the evidence rounds sharpened scope and
effort on the existing eleven (C1–C11), they didn't add or remove any.

---

## 4 · Market demand — unchanged from v1 §4, plus two load-bearing additions

- **C11 (ship slice 010):** the two worst of its ten holes **directly contradict
  privacy decisions Surbhi already made in writing**, not just abstract risks:
  - **S4** — a manager can read a colleague's **draft** self-review before it is sent.
    `009`'s own plan already answered this question in writing (Q-d: "May managers see
    a self-review before it is sent? **No**"). The product is currently doing the
    opposite of an agreed rule.
  - **S5** — a manager's browser receives a report's exact loss-of-pay amount
    (₹548.39 for a named employee in the test data), even though Surbhi already decided
    (Q-b) "days at most, never the amount." Same pattern: a decision already made, not
    yet reflected on screen.
  - Two more (S3: an employee can write their own `overall_rating` via a plain REST
    call; S8: an unescaped evidence note runs as a planted script in the *manager's*
    session) round out why this is confirmed **seen**, not merely read, evidence —
    verified by direct code read this session, both by UX and previously by the
    engineer's own impact analysis.
- **C7 (PMS vs `alvoraa_goals`):** this is not "an unused module" to tidy up. It is a
  **written product decision** (`ARCHITECTURE.md` §11: "all modules ship enabled in
  production... enabling both is the stated intent"), it already creates **37 tables
  and four public routes** (`/pms-employee`, `/pms-manager`, `/pms-calibration`,
  `/pms-steering`) the moment `install-app`/`migrate` runs against the current
  Dockerfile, it already registers **live hourly and daily scheduler jobs**
  (`process_notification_queue`, `send_overdue_stage_alerts`, `send_checkin_nudges`)
  against every tenant, and our own CI integrity gate
  (`scripts/check_app_integrity.py`) **does not cover the `hrms` fork at all** — only
  `alvoraa_goals` and `alvoraa_portal`. Whether this is live on `dev`/production today
  is unknown from the repo alone and needs a one-line, read-only, zero-cost check
  before anything else about C7 is decided. See the escalation below.
- **C10 (adapters):** DevOps confirms this is **the highest new-infrastructure-risk
  item on the page** — the first outbound integration this product would ever have. No
  existing pattern to extend (`import requests` / `frappe.integrations` / OAuth /
  `make_post_request` — none found anywhere in application code). Every relevant
  control (queue isolation, credential storage, idempotency, timeouts/circuit-breaking,
  data residency) is currently **unimplemented**, not merely unused. DevOps recommends
  resizing this toward the **top** of the L–XL band, not the middle.

---

## 5 · Kano classification — updated

| Candidate | Class | What changed |
|---|---|---|
| C11 ship slice 010 | **Must-be** | Unchanged class; evidence sharpened (two holes now confirmed to contradict written decisions, not just abstract risk) |
| **C1 weightage/KPI validation** | **Must-be** | **Unchanged class, materially smaller remaining scope.** Server-side enforcement is done and on `dev`. What remains: wire `pf-k-weight-hint` to a running total (markup already exists — this is a UI task, not new backend), plus a line-by-line re-check of `OBJECTIVES_KPI_REQUIREMENTS.md`'s FR-1–24 against `controllers/kpi.py` to name anything genuinely still open, rather than re-scoping as if nothing exists. Effort revised from **S–M down to XS–S** |
| C7 PMS-vs-`alvoraa_goals` decision | **Must-be** (as a risk) | Unchanged class; now known to be a written decision already creating live operational surface (scheduler jobs, untested public routes) the moment the current image deploys, not a hypothetical. Effort for the *implementation* (whichever path) revised **up**, not down — see §6 |
| C2 Goal/KPI Library + rating lookup | **Performance** | Unchanged. Effort (L) confirmed by DevOps as roughly right for the shape of work found |
| **C3 Rating Derivation + explanation** | **Attractive** | Unchanged class. **Effort revised down, from M–L to M** — slice 010 already built the reusable snapshot (`Alvoraa Review Item`, a per-review, point-in-time copy of each KPI/Objective) that a "replayable" derivation needs; C3 can build the explanation layer on top rather than inventing a new snapshot mechanism |
| C4 leniency/severity pre-calibration | **Attractive** | Unchanged class; confirmed dependency — slice 012 already found and documented the missing indexes (`Appraisal.appraisal_cycle`, `KPI.employee`/`appraisal_cycle`) this report would need; build after those exist, not before |
| C5 frontline two-minute review | **Attractive**, leaning Must-be for frontline-heavy buyers | Unchanged class; confirmed hard prerequisite — the portal shell's own load time (18.4 s cold on 3G) must be fixed first (gzip fix already staged, not pushed) or C5 cannot hit its own two-minute promise regardless of its own code |
| C6 pulse/eNPS | Performance, proxy, weak evidence | Unchanged |
| C8 learning & competence | Indifferent, proxy | Unchanged — do not build |
| C9 talent/succession | Indifferent for our segment, proxy | Unchanged — do not build |
| C10 adapters | **Attractive**, proxy | Unchanged class; effort band resized toward the **top** of L–XL — confirmed as the single highest new-infrastructure-risk candidate on this page |

---

## 6 · Priority order — updated

**Ranking changes from v1: none in position, one in scope/effort that matters for
sequencing (C1), one in urgency framing (C7), and cost corrections on C3/C10.** No
candidate moved past another — the evidence corrected *what each item costs and means*,
not *which one matters more*. The one thing worth calling out explicitly: **C1's
remaining scope is now so small (a UI wiring task, not new backend logic) that it could
be scheduled alongside C11 or C7 rather than waiting its turn** — it no longer
competes for the same engineering time the original S–M estimate implied.

| Rank | Candidate | Current state | Kano (survey/proxy) | Demand evidence | Effort | Fit / what changed |
|---|---|---|---|---|---|---|
| 1 | **C11 — push slice 010 to `dev`, then `main`** | Built, tested locally, rehearsed against a real PP Jewellers data copy | Must-be, proxy | seen — two holes confirmed to contradict written privacy decisions (S4, S5) | S (release decision) | DevOps: ready to recommend for `dev`; pipeline takes its own backup, runs a copy-not-rewrite migration, survivable rollback. Confirm the GitHub `production` environment's required-reviewer rule before any future `main` push (a live setting, not provable from the repo) |
| 2 | **C7 — decide PMS vs `alvoraa_goals`, and confirm today's live status first** | Both live in the same enabled product; whether PMS is *already* active on `dev`/production is unknown | Must-be (risk), proxy | seen — direct code read; `ARCHITECTURE.md` §11 names this as a written decision, not a gap | Decision: S. Implementation of either path: **revised up** from S–M — "keep and exercise" needs new test coverage + a security pass on 4 untested public routes; "disable" is blocked by an unresolved tension between the Dockerfile's framing of `hrms` as ours to edit and `nfr-budget.md` §9's "never edited" rule | **⚠ DECISION — see escalation below.** The founder call is cheap; the follow-through is not |
| 3 | **C1 — finish the client-side weightage UI; confirm nothing else in FR-1–24 is open** | Backend done, wired, on `dev`. Client hint element exists in markup, never wired | Must-be, proxy | read + seen — UX confirmed the dead hint element by direct code read | **XS–S** (down from S–M) | Cheapest Must-be fix left to close on the page; can run in parallel with C7's decision-making, not blocked by it |
| 4 | **Wave 0 remaining — wrong numbers (W2/W3/W4/W5/W7) + the approvals-bell performance fix (P1) + broken calls (B1–B10) as a second batch** | Wrong-numbers batch scoped, evidence-backed, unbuilt. P1 newly quantified: 706 queries, 11.6–16.4 s per HR page load, already 5–8× over the ≤3 s budget, and DevOps sizes the fix at 1 day. B1–B10 are outright crashes/500s, a different risk shape (a dead end, not a misleading number) | Must-be, proxy | seen — measured against real PP Jewellers data (W-items) and a direct query-count measurement (P1) | S each; P1 alone is the single cheapest, most over-budget item on this whole page | Batch W2–W7 as one slice (read paths only, no schema change) per the original plan; DevOps recommends **P1 goes first** within this batch — it's already quantified as the worst-over-budget item found this round |
| 5 | **C2 — Goal/KPI Library + attainment→rating lookup** | Requirements written, nothing built; no template picker, no library search on the current New KPI form (confirmed, direct code read) | Performance, proxy | read, named competitors | L | Only useful once C1's running-total problem is fixed — a library that speeds up typing a KPI set that still silently fails to sum to 100 is not progress. Sequencing unchanged from v1 |
| 6 | **C3 — Rating Derivation + plain-language explanation** | Not built, but the reusable snapshot it needs (`Alvoraa Review Item`) already shipped as part of slice 010 | Attractive, proxy | read, whitespace; also the specified answer to EU AI Act Art 86 if EU exposure is confirmed (open question) | **M** (down from M–L) | Reuse an existing snapshot rather than build a parallel one. Decide retention/partitioning for the snapshot's growth in the same slice, not after — it is the pattern `nfr-budget.md` calls "the biggest table in the system" for the equivalent case |
| 7 | **009 ess-portal-redesign, Waves 1–4** | Wave 0 partly done via slices 010–028; new screens not started | Performance, proxy | seen — 137 requirements against real PPJ data; confirmed at 33–44 build days across waves, consistent with the stated 8–11-week total | XL | Confirmed as a hard math check by DevOps, no change. Wave 4 explicitly lists slice 010 (C11) as a prerequisite in its own plan — don't start Wave 4 before C11 ships. Wave 4's Growth items likely overlap C2/C3/C4/C5; re-scope Wave 4 against whichever of those ship first rather than building it cold |
| 8 | **C4 — leniency/severity before calibration** | Not built; no leniency/severity screen found anywhere in the portal | Attractive, proxy | read, whitespace | M | Reuses slice 012's already-documented finding: no index on `Appraisal.appraisal_cycle` or `KPI.employee`/`appraisal_cycle` — add these as part of this slice if still missing. Decide at the requirements stage whether managers may see how they compare to peers, or HR/CXO only |
| 9 | **C5 — frontline two-minute review** | Not built | Attractive (Must-be for frontline-heavy buyers), proxy | seen, PP Jewellers | M | **Hard prerequisite found:** land the already-staged gzip fix (slice 012 §2a) first or alongside — the current portal shell alone (18.4 s cold on 3G) can defeat a "two minutes on a phone" promise regardless of C5's own code. Build from slice 008's type scale and one-screen-per-step shape, not the current desktop wizard, which is confirmed unreadable on a phone today |
| 10 | **C6 — pulse/eNPS** | Not built | Performance, proxy, weak evidence | read, secondhand | M | Unchanged. Run the survey kit (§8) before committing |
| 11 | **C10 — Tally/Zoho/CRM adapters** | Not built | Attractive, proxy | read | **L–XL, revised toward the top of the band** | Confirmed as the highest new-infrastructure-risk candidate here: first outbound integration in the product, zero existing pattern to extend, every relevant control (queue isolation, per-company encrypted credentials, idempotency, circuit-breaking, data residency) still to be designed. Also adds a new class of externally-sourced business data on top of an already-open, unmet CERT-In residency gap (hosting confirmed France, not India) — flag to whoever owns that gap before this starts |
| — | **C8 — learning & competence** | Not built | Indifferent, proxy | none found | — | **Do not build without evidence** |
| — | **C9 — talent/succession (9-box)** | Stub | Indifferent for our segment, proxy | none found | — | **Do not build without evidence** |

---

## ⚠ DECISION — C7: the PMS module reverses a written decision, and its current live status is unknown

**Decision needed:** whether to keep the `hrms` fork's Performance Management module
(PMS) enabled and exercised (the documented intent in `ARCHITECTURE.md` §11), or
disable it in favour of the live `alvoraa_goals` path.

**Context:** `ARCHITECTURE.md` §11 already states, in writing, "all modules ship
enabled in production... enabling both is the stated intent." Deciding to disable PMS
would **overturn** that written decision, not just clean up dead code.

**What's actually true, operationally, right now:**
- The current `deploy/Dockerfile` copies the real `hrms` fork including `pms/` and
  `performance_management/`. The **next** image built from it will create 37 tables and
  activate four public routes (`/pms-employee`, `/pms-manager`, `/pms-calibration`,
  `/pms-steering`) and two scheduler jobs (hourly, daily) on every tenant, the moment
  `install-app`/`migrate` runs.
- Whether this has **already** happened on `dev` or production is unknown from the repo
  alone — it depends on when each site was last built and migrated. A single, zero-cost,
  read-only check (`frappe.db.count("DocType", {"module": "Performance Management"})`
  on the relevant site) answers it in under a minute.
- Our own CI integrity gate does not cover the `hrms` fork at all, only `alvoraa_goals`
  and `alvoraa_portal` — so nothing in CI would catch an accidental change here either
  way.
- There is a real, unresolved tension between two of our own documents: the Dockerfile
  treats `hrms` as a first-party fork that's ours to edit; `nfr-budget.md` §9 says
  `apps/hrms` is "never edited... that is an escalation, not a coding decision." That
  tension has to be resolved **before** anyone touches
  `hrms/hrms/performance_management` for either path.

**Options:**
1. **Keep enabled, exercise it for real** — write functional test coverage (currently
   zero), give the four public routes a security pass, prove the two scheduler jobs
   safe at scale. Real, non-trivial engineering, not a config flip.
2. **Disable it** — hide from workspaces/role access, don't touch files inside
   `apps/hrms`. Needs the founder's sign-off (it reverses a written decision) and needs
   the Dockerfile-vs-`nfr-budget.md` tension resolved first with the engineer.

**Recommendation:** run the one-minute read-only check first, on whichever site
matters most (I'd start with `dev`), so the founder is deciding with today's real
state in hand, not a hypothetical. I lean toward Option 2 (disable) on product grounds —
two live "do a review" paths in one enabled product is exactly the confused-user,
support-ticket risk this review already flags as a Must-be problem — but this is a
security- and architecture-adjacent call that sits above what I decide alone.

**Who decides:** the founder, on the disable-or-keep call; the engineer, jointly, on
resolving the Dockerfile/`nfr-budget.md` tension before either path is implemented.

**Deadline:** before the next image build/deploy, since that is the event that would
change PMS's live status either way.

---

## 7 · Do-not-build list — unchanged from v1 §7

No changes. C8 (learning & competence) and C9 (talent/succession) remain off the build
list; the other refusals (AI-set ratings, emotion/voice/facial analysis, telemetry
feeding a performance score, a forced bell curve, a second OKR data model, a generic
LMS as a differentiator claim) are unchanged and unaffected by this round's evidence.

---

## 8 · Kano survey kit — unchanged from v1 §8

The kit for C2, C3, C4, C5, C6, C8 and C9 stands as written. Recommend running it
before committing further effort to C2, C6, C8 or C9 specifically — those are the four
candidates on the page still resting on `proxy`-only evidence with no direct customer
quote on file.

---

## What the human gate needs to see, in one place

- **Built / partial / missing**, corrected: C1's backend is **built** (not missing);
  only the client UI hint is missing. C7's operational footprint (tables, routes,
  scheduler jobs) may already be **live**, not merely installed — needs a one-minute
  check before anyone scopes further work.
- **Top candidates**, with Kano class + demand evidence + effort, all `proxy` except
  none are `survey` yet — no Kano survey has been run with real customers this round
  either.
- **What UX added:** the dead `pf-k-weight-hint` finding (changes C1's definition of
  done); confirmation the current review wizard is unreadable on a phone **today**;
  the gzip-fix dependency for C5; the two slice-010 holes that contradict written
  privacy decisions.
- **What DevOps added:** the KPI.py correction (changes C1's rank-worthy effort); C7's
  real operational footprint and the Dockerfile/`nfr-budget.md` tension; C3's reusable
  snapshot from slice 010 (cuts its effort); C10 confirmed as the highest
  new-infrastructure-risk candidate; the P1 approvals-bell performance number
  (5–8× over budget, 1-day fix).
- **Should a Kano survey run before committing further?** Yes, for C2, C6, C8 and C9 —
  none of the four has direct customer evidence on file, and C8/C9 are on the
  do-not-build list until that changes. C1, C7, C11 and the Wave 0 batch do not need a
  survey — they are corrections to things already shipped or already wrong, not
  discretionary new features.

---

## Tracked in YouTrack

All candidates from §6, plus the Wave 0 sub-batches and the Waves 1–4 / C10 splits, are
now tracked as issues in YouTrack project `ALV` (`https://alvoraa.youtrack.cloud`),
created 2026-09-21. `Ideal days` didn't accept a value on a few issues — permission,
not data loss; the estimate is still in each issue's description.

| Rank | Candidate | YouTrack |
|---|---|---|
| 1 | C11 — ship slice 010 | `ALV-1` |
| 2 | C7 — PMS decision | `ALV-2` (⚠ decision), `ALV-14` (live-status check), `ALV-15`/`ALV-16` (the two paths, both blocked on `ALV-14`) |
| 3 | C1 — KPI weightage UI | `ALV-3` |
| 4 | Wave 0 remaining | `ALV-4` epic → `ALV-17` (P1 perf), `ALV-18` (wrong numbers), `ALV-19` (broken calls) |
| 5 | C2 — Goal/KPI Library | `ALV-5` epic (depends on `ALV-3`) → `ALV-20` (library), `ALV-21` (lookup tables) |
| 6 | C3 — Rating Derivation | `ALV-6` |
| 7 | 009 Waves 1–4 | `ALV-7` epic → `ALV-22`/`ALV-23`/`ALV-24`/`ALV-25` (Waves 1–4; Wave 3 depends on `ALV-18`, Wave 4 depends on `ALV-1`) |
| 8 | C4 — leniency/severity | `ALV-8` |
| 9 | C5 — frontline review | `ALV-9` (depends on `ALV-10`) |
| — | gzip fix (C5 prerequisite) | `ALV-10` |
| 10 | C6 — pulse/eNPS | `ALV-11` |
| 11 | C10 — adapters | `ALV-12` epic → `ALV-26` (foundation), `ALV-27`/`ALV-28`/`ALV-29` (Tally/Zoho/CRM, each depends on `ALV-26`) |
| — | Kano survey kit | `ALV-13` |

**Deliberately not created:** build issues for C8 (learning) and C9 (talent/succession) —
both are on the do-not-build list; `ALV-13` (the survey) is the path to changing that,
not a build task.

## Open questions

| Question | Owner | Blocks |
|---|---|---|
| Does `frappe.db.count("DocType", {"module": "Performance Management"})` return 0 or 37 on `dev` today? | Whoever can run a read-only check on `dev` | Whether C7 is an emergency (already live) or a decision with runway (not yet deployed) |
| Is `apps/hrms` "ours to edit" (Dockerfile's framing) or "never edited" (`nfr-budget.md` §9)? | Founder + `hrms-fullstack-engineer` | Any implementation work for C7, either direction |
| Is the GitHub `production` Environment's required-reviewer rule actually turned on? | Whoever administers GitHub repo settings | Whether the documented gate for a future `main` push is real |
| Does `dev`'s Patch Log already carry `fill_branch_on_hr_records` and `make_evidence_files_private`, so the real migration for C11 is the expected 2-patch case, not 4? | Whoever can run a read-only check on `dev` | Migration-window sizing for C11's push |
| Is there anything genuinely still open in `OBJECTIVES_KPI_REQUIREMENTS.md`'s FR-1–24 once checked line-by-line against `controllers/kpi.py`? | `hrms-product-manager`, next session | C1's exact remaining scope beyond the client UI hint |
| Is EU exposure current, target, or anticipated? | Founder (repeated from v1 — directly changes C3's priority; Art 86 only binds if EU exposure is real) | Whether C3 is P1 compliance work or P3 differentiation |
| Is there a real customer request behind pulse/eNPS (C6), learning (C8) or talent/succession (C9)? | Founder | Whether C6/C8/C9 move up the list or stay on hold pending the survey kit |
| Is the `alvox_compensation` app (v1's §3 correction, carried forward, unresolved) real anywhere? | Founder | Whether "Compensation/reward: built" is corrected in `product-context.md` |

## Assumptions

- `[ASSUMPTION]` DevOps's git-ancestry verification (`git diff origin/dev`, `git
  merge-base --is-ancestor`) was run correctly and against the right commit. I could
  not re-run it myself — no shell tool was available in this session — so I verified
  the functional claim directly (the code exists and is wired) but am relying on
  DevOps's stated method for the "already on `origin/dev`" part specifically.
- `[ASSUMPTION]` Nothing has changed in the cited screens (`009`, `003`, `010`) between
  their capture dates and today, carried forward from the UX evidence document's own
  assumption.
- `[ASSUMPTION]` All effort estimates in §6 remain engineering judgement, not committed
  sizing — none of these candidates has started `/slice-start`, so no formal sizing
  exists for any of them yet, same caveat as v1.
- `[ASSUMPTION]` Target tenant size (50–1,000 employees, India-first) is still the
  operative target, carried forward from v1 — it underpins C9's Indifferent
  classification.
