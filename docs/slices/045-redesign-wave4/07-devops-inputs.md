---
slice: 045-redesign-wave4
artifact: 07-devops-inputs
author: hrms-devops-engineer
date: 2026-09-24
status: draft — §3 (requirements) and an early §4 (strategy). §5 (release readiness) is written when the build is done
inputs: [02-functional-spec.md revision 2 (`76bc73d`, US-1 to US-20, AC-1 to AC-86), 01c-security-privacy-requirements.md revision 2 (`d1ef233`), ../034-redesign-wave1/07-devops-inputs.md (OPS-1 to OPS-19, §3b, §4.6 OPS-35/36), ../042-redesign-wave2/07-devops-inputs.md, ../043-redesign-wave3/07-devops-inputs.md, ../042-redesign-wave2/03b-implementation-notes-044-followups.md, ../044-scale-fixtures/04-test-report.md, .claude/context/nfr-budget.md, deploy/nginx.conf, deploy/compose/docker-compose.app.yml, deploy/compose/docker-compose.devstack.yml, .github/workflows/ci.yml, .github/workflows/deploy.yml on dev and on origin/main, scripts/, alvoraa_portal ess_parts.py, alvoraa_portal hr_api.py]
---

# Wave 4 — Growth, Team and People: DevOps inputs

**I advise. Every Decision column below is blank and is Surbhi's.** I changed no code, ran
nothing on any server, touched no bench and pushed nothing. **I measured nothing today.**
Every number here is either quoted from slice 044's or slice 042's measurements, with their
date, or read out of a file in this repository, or labelled an estimate. What I checked and
what I did not is listed at the end.

Item IDs are `OPS-W4-n`, namespaced so they cannot collide with Wave 1's `OPS-n` or with
Waves 2, 3 and 5. Where an item is the same as Wave 3's I say so rather than re-argue it.

---

## Two things Waves 2 and 3 said that I am withdrawing

Said first, because both documents are still being read.

**1. "No fifth include file" is withdrawn.** OPS-31 landed. Style and script are cached
static files, HTML per visit fell from 1,071,272 bytes to 209,574, and the server render is
about 22 % faster (Wave 1 `03-implementation-notes.md` §4 and `07` §4.6, measured
2026-09-23). Markup parts are pasted by `ess_part()` and **take no template cache slot**:
`ess_part()` reads a file, caches the bytes under `ess_part:<build_version>:<name>` in
`frappe.cache()` for 24 hours, and refuses any file containing `{{`, `{%` or `{#`
(**Fact**, `ess_parts.py:44-70`, read today). No Jinja tags means no compiled template, so
the cliff is gone. **Growth, Team and People each get their own markup, style and script
file, and that is free.** Wave 4's AC-52 already says so.

**The constraint that replaced it, and it is a cheaper one:** a markup part may never
contain a Jinja tag, so it can never contain a translatable sentence either. Wave 4's three
new parts must hold no user-visible words — the words go in the script. That is Wave 5's
AC-21 and it starts mattering in Wave 4, because Wave 4 writes the parts.

**2. "Estimates are acceptable where nothing is measured" is withdrawn.** Two reusable
fixture sites now exist: **`test044`, 981 people, 4 companies, 16 stores, about 26 minutes
to build**, and **`test044s`, 20 people, 59 seconds** (slice 044 `04-test-report.md` §1,
built and timed 2026-09-24). They are the artifact; `build()` returns immediately on a site
that already has them, and a backup-and-restore hands one to somebody else in minutes.
**So there is no longer an excuse for a budget nobody counted.** Four budgets were wrong the
day they were written and **failed at twenty people as badly as at 981** — they were never
scale failures. Wave 4's §14 is right to carry no invented number, and OPS-W4-6 says what
to put there instead.

---

## Read this first — the four that stop the build

**1. P0, unchanged and still open: OPS-31 must not reach production before ALV-112's asset
refresh is on `main`.** **Fact, checked today:** `origin/main` is **`78082fb`**, and it
carries the workflow files only — `scripts/refresh_bench_files.sh` is **absent from the
`main` tree**, and `main`'s copy of `.github/workflows/deploy.yml` mentions it **zero**
times. On `dev` it is mentioned once. **Lesson 14: the automatic Deploy runs `main`'s copy
of the workflow, not the branch being deployed.** So a production deploy today does not
refresh the sites volume, and after OPS-31 the portal's style and script come **from that
volume**. Production would serve Wave 4's HTML against August's script, nothing would error,
and the screen would look almost right. Full reasoning in Wave 2's `07` §3.7; not repeated.

**2. Wave 4 needs `bench migrate`, and Wave 3 did not. This is the first wave in the
redesign that changes the schema.** `alvoraa_decided_as` is a custom field installed the
way `install_review_fields:135` installs the other three — wired to `after_migrate` **and**
`after_install` (spec §15). **The trap is not the field; it is a deploy with migrations
off.** The code that stamps it would then write to a column that does not exist, and
`decide()` fails for every attendance correction on that tenant — the manager path as well
as the HR one. §4.2 and OPS-W4-3.

**3. The self-review wizard puts repeated writes on the web tier, at a synchronised moment,
and nobody has measured one.** Autosave fires 3–5 s after typing stops, at most once every
15 s, plus on step change, blur and page hide (AC-37). Production's web tier is
**gunicorn, 4 workers × 2 threads = 8 requests at a time**, one backend replica, request
timeout 120 s (**Fact**, `deploy/compose/docker-compose.app.yml:223-225`). A review window
is not a random moment: it opens for a whole tenant on one day. **Inference:** this is
Wave 3's payslip problem in a different shape — a write instead of a PDF, many small ones
instead of one big one. §3.5 says what to measure.

**4. A half-finished wizard leaves a real, sensitive record behind, and there is no
operational answer for it yet.** The review record is **created on first save, not on read**
(spec §5a), and the five steps live in the extension's `page_data` JSON. So somebody who
starts, types two sentences and never returns leaves a Draft Appraisal extension holding
part of a self-assessment, plus Frappe Version rows for every autosave. That is among the
most sensitive free text an employee writes (spec §14), it falls under counsel's
"employment + 6 months, then erased" rule, and **no job enforces that period today** — the
`01c` says so and could find none. It is not a Wave 4 defect. It is a Wave 4 **consequence**
that needs naming before 400 people start abandoning wizards. OPS-W4-14.

---

## §3 Requirements · 2026-09-24 · hrms-devops-engineer

### 3.1 What a Wave 4 panel costs now that OPS-31 has landed

| | Answer |
|---|---|
| A new Jinja include template | Wave 4 adds **none**, and should add none. The pinned include set stays at three (AC-52) |
| A new markup part under `parts/` | **Free.** One `frappe.cache()` read per part per page, keyed by build version, 24-hour expiry (**Fact**, `ess_parts.py:51-56`). Twelve parts measured faster than one include |
| A new style file | One more `/assets/` request, `expires 30d` with `Cache-Control: public, immutable` and gzip (**Fact**, `deploy/nginx.conf:207-211` for production and `:391-395` for dev) |
| A new script file | The same — **and it is now on the critical path.** If `/assets/` serves the wrong thing the portal is a page that does nothing. Wave 1's OPS-35 and OPS-36 are the checks for that, and §4.6 below is my view on them |
| HTML per visit | 209,574 bytes today, down from 1,071,272. Three new parts add markup, so **record the number again after Wave 4's parts exist** — the page's own size is the one thing OPS-31 did not remove |

### 3.2 Measure it on both fixtures, or do not write a number

**The budgets, as re-measured after slice 042's follow-ups** (042 `03b` §3, measured
2026-09-24 on `test044` and `test044s`): `get_home` ≤ **28**, `get_nav_counts` ≤ **21**,
`get_inbox` ≤ **26**, `get_frame` ≤ **5**, p95 ≤ **500 ms** with the worst reading
**215 ms**. **Quote these; do not invent competing ones.**

**And read them the right way round: flatness in headcount is the gate, the count is a
note.** A change that moves a count by one and keeps the count identical at 20 and at 981
people is fine. A change that keeps the count and breaks flatness is not. That is
`nfr-budget.md`'s "queries per request" row as it now reads, and slice 044's
`test_scale_flatness_044.py` is the guard — 11 tests, and **one of them proves the guard can
fail**, which is why a green run of the other ten means anything.

| # | Measurement | Pass line | Who, and when |
|---|---|---|---|
| **M1** | `get_team`, `get_growth` and the person sheet, per persona, on **`test044` and `test044s`**, slice 044's `measure_044.run` — 3 warm-ups then 20 measured, nothing written in between | **Identical query count on both sites**, every persona. p95 ≤ 500 ms | engineer, at the commit, in `03-implementation-notes.md` with the date |
| **M2** | `get_team_goals` and `my_view` **first**, before anything else | Same. These were 22 queries for 19 people and 31 queries on 14 September and **slice 044 did not re-measure them** — they are the two most likely to be not flat (the spec's own assumption) | engineer, first |
| **M3** | Payload bytes for `get_team` at **100 rows** (50 per section), `get_growth`, the person sheet | `get_team` ≤ 40 KB, `get_growth` ≤ 40 KB, sheet ≤ 8 KB, **asserted in bytes** | same test as M1 |
| **M4** | HTML bytes on the wire, and the `?v=` value on two loads in a row | ≤ 250 KB uncompressed; **`?v=` identical on both loads** | engineer locally, me on dev |
| **M5** | Calls per session on Team and on Growth, against nginx's limit | See §3.6 | me, on dev, at release readiness |

**One trap specific to the fixtures, and it cost slice 044 its first large run.** The staff
list is an **opt-in** feature and is off on a fresh site; every persona including System
Manager is refused until `staff_list` is added to the site's `features` (044 D7). People's
measurements will read "refused" and look like a permission bug. And `throttle_user_limit`
must be raised before a fresh fixture is built, because Frappe throttles user creation to
sixty an hour.

### 3.3 The two banned shapes Wave 4 inherits, and what they cost

`nfr-budget.md` now carries the rule: **a scope belongs in the query, never in an
`IN (...)` of ids.** It came from a measured ×5.1 slope. Wave 4 opens the two surviving
instances.

| Where | What is there today (**Fact**, read today) | What it costs |
|---|---|---|
| `hr_api.py:496-504`, `on_leave_today` | Raw SQL with `",".join(["%s"] * len(team_ids))` — **one bound parameter per person**, plus `tuple(team_ids)` | At 981 people this is the exact shape slice 044 profiled: `COUNT(*) … WHERE employee IN (981 parameters)` at **11.8 ms**, against **1.1 ms** for the subquery form. One query either way, so **the count stays flat and the clock does not**. Measured 2026-09-24, 042 `03b` §2 |
| `hr_api.py:1172-1181`, `get_team_scorecard` | The same `.format(placeholders)` shape, **plus a correlated subquery per row** (`SELECT a2.total_score FROM tabAppraisal a2 WHERE a2.name = ae.name`), **plus `ORDER BY ae.creation DESC` over every extension row for the team with no `LIMIT`**, then filtered in Python at `:1183` | Worse than the first, and in three ways at once. **Estimate:** at 981 people with four reviews a year that is the whole team's appraisal history read into the worker so Python can drop most of it. The `01c`'s PRIV-5 says the released-status condition belongs in the query for a privacy reason; the same change is the performance fix |

**My recommendation, and it agrees with AC-14 and the `01c`:** both become subqueries, with
the `status = "Active"` and the released-review conditions **inside** the SQL, and
`get_team_scorecard` gains a bound on what it reads. That is one change with three payoffs —
the slope, the privacy control and the flatness gate. **The engineer already proved the
pattern works** (`frappe.qb.get_query`, verified in the installed source at
`apps/frappe/frappe/database/query.py:215`), so this is not new machinery.

### 3.4 The two-section Team payload, and a budget for it

§6a turns one capped list into two. **The thing to watch is not the size; it is that two
sections stay one call and two constant subqueries.**

| | Recommended budget | Basis |
|---|---|---|
| Calls on Team | **1** beyond the frame's two, carrying both sections | Spec §14. Two sections must not become two calls |
| Queries for the scope | **2 constant subqueries** — `direct` and `covered` — never one per person | AC-14 |
| Rows | up to **100** (50 per section) | `TEAM_LIST_CAP = 50`, applied twice |
| Payload | **≤ 40 KB**, asserted in bytes | **Estimate.** Slice 044 measured `get_inbox` at **18,351 bytes for 50 drawn rows** with more keys per row than a team row has, so 100 six-key rows plus two totals should land well inside 40 KB. **That is arithmetic from a measured number, not a measurement** — M3 settles it |

**`nfr-budget.md` carries no payload number anywhere.** The 40 KB is the spec's and I agree
with it; I am recording that it is a judgement, not a standard.

### 3.5 The wizard — the one piece of this wave nobody has measured

Autosave is a **write** on the **foreground** path, by design (spec §14: "a person needs to
know it saved"), and I agree with that design. What follows from it:

| What | Number | Label |
|---|---|---|
| Autosave interval | ≥ 3–5 s idle, at most 1 per 15 s, plus step change, blur, page hide | **Fact**, AC-37 |
| Writes per completed review | **Estimate 10–25** — five steps, a few saves each, plus the step transitions |
| Concurrent web requests production can serve | **8** (4 gunicorn workers × 2 threads), one backend replica | **Fact**, compose `:223-225` |
| Request timeout | 120 s | **Fact**, same lines |
| Tenant to design for | 1,000 employees, 4 reviews per person per year | `nfr-budget.md` §1, spec §14 |

**What to measure before the production release, and I am asking for two numbers, not a
report:**

1. **Autosave p95**, 20 warm calls on a real review on `test044`, with a realistic
   `page_data` payload. **Pass line: ≤ 500 ms** (`nfr-budget.md` §2, whitelisted API).
2. **Ten concurrent autosaves**, and whether an ordinary portal request still answers inside
   its 500 ms budget. **Pass line: it does.** If it does not, the answer is not more
   workers — it is a longer idle window and a hard cap of one save in flight per session.

**And one correctness question with an operational answer, which is the one I would chase
first.** AC-40 wants a 60 KB answer in one step to save and reload unchanged, against an
`[ASSUMPTION]` that `page_data` is a Text field of about 64 KB. **MariaDB's `TEXT` is 65,535
*bytes*, not characters** — and **Devanagari and Gurmukhi are three bytes per character in
UTF-8**. So a Hindi answer reaches the ceiling at roughly a third of the characters an
English one does, and `page_data` is JSON, which adds escaping on top. **Unknown, and it
matters:** does an oversize write throw, or does the column silently truncate? MariaDB in
strict mode errors "Data too long"; without strict mode it truncates and warns. **I could
not check which our image runs.** A silent truncation would eat part of somebody's
self-assessment and tell nobody. OPS-W4-9 asks for the one bench check that settles it, in
**both** scripts, and a client-side cap with a sentence rather than a lost answer.

### 3.6 Rate limits, and a store of twenty people

**Fact**, `deploy/nginx.conf:70` and `:270`: `location /api/` is `rate=120r/m`,
`burst=30 nodelay`, keyed on `$binary_remote_addr`. **A store is one address.**

**Inference, from measured numbers:** a Home load is three calls (slice 044). Team is the
frame's two plus one. Growth is the frame's two plus one, **plus an autosave every 15 s for
as long as somebody is typing** — four a minute, per person. Twenty people in one store
doing their reviews in the same half-hour behind one address is 80 autosaves a minute before
anybody loads a page. That is inside 120 r/m and it is not comfortably inside it. **Nobody
has tested the limit against a real nginx** — slice 044 recorded it as out of scope and so
did Wave 2's OPS-W2-10. It is my rig and I have not built it.

**Any change to the limit is its own slice with the `nginx -t` gate** — one nginx serves
production and dev from one `deploy/nginx.conf`, so a Wave 4 push that edited it would
change the live site's proxy and restart it (lesson 13). **Wave 4 must not touch that file.**

### 3.7 Caching — and what must never be public

| Thing | May it be cached? | What clears it |
|---|---|---|
| The portal HTML | **No.** `context.no_cache = 1` in `hrms_employee.py` stays, pinned by a test | — |
| `get_team`, `get_growth`, the person sheet | **Never anywhere shared.** They carry ratings, trajectories and free-text self-assessments. Frappe keeps a `www` page's HTML for 30 minutes **keyed by address only, not by user** — that mechanism must never come near these screens | — |
| Within one request: the caller's Employee row, the reports list, the HR scope | **Yes** — `call_cache`, which is a memo and not a cache: no key outlives the call, teardown in a `finally`, and with no call open it does not memoise at all (042 `03b` §1) | the request |
| Markup parts | Already cached by build version for 24 h, and they hold no data | a release |
| Anything about a person, in a module-level dictionary | **Never.** One worker serves several sites — `01c` SEC-13 | — |

**Nothing in Wave 4 is public.** All three screens are behind a session. The one thing that
becomes public is the **style and script under `/assets/`**, served to a signed-out client
with no session — that is how OPS-35's check works. **So no sentence about a person, no
tenant name and no id may be baked into a Wave 4 asset file.** It goes out with
`Cache-Control: public, immutable` for 30 days, and there is no way to recall it.

### 3.8 The three dead browser tests are an operations problem, not only a test one

**Fact**, spec bad-news 4: `scripts/run_dom_tests.js` skips `portal_tree_test.js`,
`portal_redesign_test.js` and `portal_appraisal_test.js`, and they are counted as coverage.
**A gate that cannot fail is the failure mode this project keeps paying for** — it is
lesson 19 in a different costume: a zero from a skipped test looks exactly like a zero from
a passing one. The operational requirement is one line: **the runner must print what it ran
and what it skipped, assert a non-zero count, and fail on any skip it was not told about.**
That belongs in the same commit as the fixtures (AC-62 to AC-64).

---

## §4 Strategy, early · the release plan and the rollback

### 4.1 Order of release

| # | Step | Why it is here |
|---|---|---|
| 1 | ALV-112's refresh step reaches **`main`**, proved by one deploy | Otherwise no production deploy refreshes assets. `origin/main` is `78082fb` and does not have it |
| 2 | Wave 1's swap on `dev`, under its five agreed conditions (034 §3b) | Unchanged |
| 3 | Wave 2, then Wave 3, then Wave 4 on `dev` | Three waves in one script file at once is what the split was meant to prevent |
| 4 | Wave 4's **server** commits first — the six-key `me`, the month filter, the two subqueries, the two deletions | Independent of every open decision, and one of them closes a live leak |
| 5 | Wave 4 to production **in a release of its own**, with migrations **on** | A rollback rolls back the whole image, not one commit (Wave 1's OPS-16) |
| 6 | **On the day, per tenant:** the `staff_list` tick, the demo seeding on the local copy, the reporting-line data fix | Configuration and data actions on Surbhi's word. **None of them is covered by a rollback** |

### 4.2 What a Wave 4 deploy needs

| | Answer |
|---|---|
| `bench migrate` | **Yes — this is the change from Wave 3.** `alvoraa_decided_as` is a custom field installed from `after_migrate`/`after_install`. The release that carries AC-82 is deployed with **`run_migrations: true`**, and the field's presence is confirmed afterwards |
| `bench build` | Not for Wave 4's own Python — but the new style and script must reach the **volume**, which is step 1 |
| `bench clear-cache` | Only for a remembered "not found" on a new route. The narrow command is `bench --site <site> clear-website-cache`, and it needs approval (CLAUDE.md §2) |
| Compose, image, nginx | **No change. Wave 4 must not touch `deploy/nginx.conf`** |
| New queues or workers | **None for the wave as specified.** If D-3's nightly trajectory recompute is taken, see §4.5 |
| Configuration, per tenant | **Yes** — the `staff_list` tick (W1D-21, D-10). Not a deploy step, not rolled back |
| Data actions | **Yes** — demo seeding on the local copy before the test run, and the reporting-line fix on the tenant (D-9). Neither is code |

### 4.3 Rollback, and the two things it does not undo

**Redeploy the previous image tag with migrations off — about 10 minutes of machine time,
12–15 minutes from the moment somebody decides.** Measured by me on dev on **2026-09-22**:
9 min 33 s, of which **6 min 54 s is the deploy waiting for `bench version`, a command that
never succeeds on our image** (Wave 1's OPS-15, still open). Production has not been timed
with migrations off; **estimate 9–11 minutes**.

The command, **for Surbhi to approve and run** — I do not run it:

*Actions → Deploy → Run workflow* · `environment: production` ·
`image_tag: <the tag production ran before this release>` · `image_package: alvoraa-app` ·
`run_migrations: false`.

**What the rollback does not undo, and both need saying out loud on the day:**

1. **`alvoraa_decided_as` stays.** An image rollback rolls back code, not schema. The custom
   field remains on the tenant and **every value already stamped in it remains**. That is
   harmless — the old code neither reads nor writes it — but the screen loses the "(HR)"
   label while the record keeps the fact. **What is not harmless is the other direction:**
   rolling forward again with migrations off would leave newer code writing to a field a
   fresh tenant does not have. The installer is idempotent by design; **confirm it**,
   because "safe to run twice" is `nfr-budget.md` §9's rule and not an observation.
2. **The leave-type narrowing comes back.** Rolling the image back restores today's
   `on_leave_today` and `month_leaves`, so HR and managers start receiving colleagues'
   leave types again. **That is a privacy rule reopening by rollback**, exactly as Wave 3's
   OPS-W3-9 describes for its email. Say it on the day and check the payload afterwards.

Before the release, not after: **write the previous production tag down and confirm it
exists in `alvoraa-app`** — production pulls an image only during a deploy, there is no
`pull_policy` in the compose files, so a rollback tag that is not in the package you are
pulling from is not a rollback. And no pushes to `dev` in the hour after: one runner, one
job at a time (Wave 1's OPS-19).

### 4.4 After the deploy — what to look at

Disk headroom **before** the pull (lesson 16: a full disk breaks redis, kills the workers and
defeats `restart: unless-stopped`, which fired once and failed because restarting a
container needs disk); `docker top` plus the rq worker registration and the heartbeats,
**never `docker ps` alone** (lesson 15); `scripts/check_workers.sh`; every app container
reporting the same image tag (lesson 2); M4 from §3.2; Wave 1's OPS-35 and OPS-36. Then
Wave 4's own four:

1. **The custom field exists**, on every tenant that was migrated, and one attendance
   correction decides cleanly.
2. **One Team payload, read from a signed-in browser**, searched for a Leave Type name. The
   narrowing is the change most likely to be half-deployed, because it lives in two places.
3. **The Error Log count** for `growth_api` and `team_api` in the first hour, and any
   "Data too long" among them.
4. **A named alert with a named owner** for a failed autosave. An autosave that fails
   silently loses somebody's review and they find out later (`nfr-budget.md` §8).

### 4.5 The trajectory is stale, and the operational answer is a job

`trajectory` is stored and recomputed **only when a goal is saved**
(`controllers/goal._update_trajectory:39`, spec D-3). A goal nobody touches keeps an old
answer for ever, and Wave 4 puts that answer on a card called **"Needs attention"**. So a
stale value stops being cosmetic: it decides whether a manager has a conversation with
somebody.

**I agree with the analyst's two-part answer and I am adding the operational half.** Ship
AC-24 — show the date it was worked out, and do not count a stale On Track as
attention-worthy — and raise the recompute as its own ticket. **Recomputing on read is a
write on a read path** and both spec §19.5 and `nfr-budget.md` rule it out.

If the nightly job is taken, here is its shape, so it is not designed at 11pm:

| | Recommendation |
|---|---|
| Where | A **scheduler** job, per site, not a hook |
| Which queue | **`long`.** `worker-long` runs `bench worker --queue long` (**Fact**, compose `:274`) — no new service. And **never a hand-listed `docker compose up`**: a list missing `worker-long` left tenant provisioning queued for an hour (lesson 1) |
| Volume | **Estimate** 2,000–4,000 goal rows a night on a 1,000-person tenant (1,000 people × 2–4 goals, spec §14). **Measure it on `test044`, which has 240 goals**, and scale from a measured rate rather than from this sentence |
| The rule that must be in it | **Writes only on change** (`nfr-budget.md` §2). A quiet tenant must not generate thousands of pointless Version rows a night |
| Observability | One log line per run: rows read, rows changed, duration. No employee name, no rating (`01c` PRIV-7) |
| Interaction with AC-24 | If the job runs nightly, **nothing is ever 14 days stale**, so AC-24's constant becomes a safety net rather than a normal path. Keep it; it is the thing that shows when the job has stopped |

### 4.6 The two browser numbers — should they gate production?

Asked directly, so here is a direct answer.

**Fact:** Wave 1 built `scripts/browser_check_frame.js` — 143 lines, Chromium 153 via
`puppeteer-core`, a real login, 14 checks. It found four things `curl` and jsdom could not,
including that website.js's `frappe.call` **never** calls `opts.error`, which would have left
the frame on "Loading" for ever with nothing in any log. **It is deliberately not in CI**;
its own header says it needs a running site, a real login and a browser. **Fact:** it is
**not in the `dev` checkout at all** — it exists only in the slice worktrees. That is worth
knowing before anybody plans a CI step around it.

**Fact:** AC-31 (skeleton ≤ 300 ms) and AC-40 (Home usable ≤ 2.5 s) have **never been
measured**. Slice 044 said so, slice 042's follow-ups said so again, and Wave 4 repeats both
numbers in its §14 and its AC-42.

**My recommendation, in two parts:**

**Yes — the 2.5 s "usable" number should gate the first production release of the redesign,
as a hand check, once, on the W1D-09 rig** (Chrome "Slow 4G", 4× CPU slow-down, cache off).
It is the only number in five waves that describes what the person the redesign is for
actually feels, and it has been asserted in four documents and measured in none. One run,
20 loads, p95, written down with the date. The 300 ms skeleton rides along free in the same
session.

**No — neither should be a blocking CI gate yet.** A timing gate on a shared GitHub runner
is flaky, and I have the project's own evidence: the engineer measuring on this machine on
24 September recorded `get_frame`'s p50 moving by up to **×2.6 between runs** on work that
did not touch it, and said in writing which numbers he would and would not defend. A gate
that goes red for the weather gets ignored, and then it is worse than nothing.

**What it would take to run them in CI, concretely, because the answer is "less than you
think".** CI's `test-python` job already builds a full bench with a real site (`test_site`),
Node 24, a cached `~/frappe-bench`, `timeout-minutes: 90` (**Fact**, `.github/workflows/ci.yml`,
read today). On top of that it needs: `apt-get install -y chromium`; `npm install
puppeteer-core`; a probe user who is a System Manager **and** has an Employee record;
`bench --site test_site serve` in the background; and the throttling applied through Chrome
DevTools Protocol rather than by hand. **Estimate +4–8 minutes per run**, most of it the
Chromium install, and cacheable.

**So my recommendation for CI is a third thing, not a yes or a no:** add it as a
**non-blocking job that prints the numbers** and records them, run it for two weeks, and
make it blocking only if the spread is small enough to set a line. That is a workflow-file
change, which sits outside a feature slice on the same line as Wave 1's OPS-18 — **Surbhi's,
not mine.**

### 4.7 Where I agree and disagree with the engineer and the analyst

| Item | My view |
|---|---|
| Two sections stay one call and two subqueries | **Agree**, and it is the single thing in this wave most likely to be built the old way |
| Payload 40 KB at 100 rows | **Agree it is the right starting line, and it is an estimate.** Slice 044's 18,351 bytes for 50 richer rows is the basis |
| The wizard's autosave stays in the foreground | **Agree**, on the condition that §3.5's two measurements pass. If they do not, this stops being a trade-off and becomes a defect |
| `alvoraa_decided_as` rather than deriving from `reports_to` | **Agree, and I would go further:** deriving it would also make the answer depend on *when* you ask, which no log and no backup can repair |
| Wave 1's OPS-35 and OPS-36 (the two asset checks) | **Agree, and I am adding to them.** From Wave 4 on, **every** visible change depends on the volume refresh, so doing these by hand on every deploy for ever is not a plan. **My recommendation: automate both inside the Deploy workflow once the ALV-112 step is on `main`** — four fetches and one timestamp. It edits a workflow file, so it is Surbhi's call, not a slice's |
| The demo seeding (release gate 4) | **Agree, and it is stronger than a gate.** Without it most of §11 passes for the wrong reason, which is a green test run that proves nothing |

---

## OPS items

Every Decision is blank and is Surbhi's.

| ID | Recommendation | Why | Cost of ignoring it | Level | Decision |
|---|---|---|---|---|---|
| **OPS-W4-1** | **OPS-31 does not reach production until ALV-112's refresh step is on `main`**, proved by one deploy. Same as OPS-W2-2 and OPS-W3-2 | `origin/main` is `78082fb`; `refresh_bench_files.sh` is absent from that tree and `main`'s `deploy.yml` mentions it zero times — **Fact**, checked today. Lesson 14: the automatic Deploy runs `main`'s workflow | Production serves Wave 4's HTML against August's script, nothing errors, and nothing on screen says so | **Require · P0** | |
| **OPS-W4-2** | **Prove the deployed assets are the ones just built, every release** — Wave 1's OPS-35 and OPS-36 — and **automate both in the Deploy workflow** once ALV-112 is on `main` | From Wave 4 on, every visible change depends on the volume refresh. A stale asset is invisible: the page renders, nothing errors, the product is a month old | ALV-112 again — it hid for four weeks, dev serving 27 August and production 19 August | **Require · P1** (the checks) · **Recommend · P2** (automating them) | |
| **OPS-W4-3** | **The release carrying AC-82 is deployed with `run_migrations: true`**, and the custom field's presence is confirmed on every tenant afterwards | `alvoraa_decided_as` installs from `after_migrate`/`after_install`. Wave 4 is the first redesign wave that needs a migration | With migrations off, `decide()` writes to a column that does not exist and **every** attendance correction fails — the manager path too, not only HR's | **Require · P1** | |
| **OPS-W4-4** | **Confirm the field installer is safe to run twice**, and say so in the notes | `nfr-budget.md` §9: a migration is safe to run twice or it states honestly that it is not | A second migrate errors mid-deploy, on a step nobody expected to be risky | **Require · P2** | |
| **OPS-W4-5** | **Say on release day that a rollback does not undo the custom field, and does reopen the leave-type narrowing.** Check the Team payload after any rollback | An image rollback rolls back code, not schema — and it rolls the privacy fix back with the code | A decided privacy rule quietly reopens (Wave 3 hit the same shape with its email), and nobody expects a field to survive a rollback | **Require · P1** | |
| **OPS-W4-6** | **Measure on `test044` (981) and `test044s` (20) with `measure_044.run` before writing any number into §14**, and record it with the date. Start with `get_team_goals` and `my_view` | Four budgets were wrong the day they were written and failed at twenty people as badly as at 981. Both fixtures exist and cost nothing to reuse | A budget nobody counted reads as proof. That is how §13 got four wrong numbers | **Require · P1** | |
| **OPS-W4-7** | **Flatness is the gate; the count is a note.** The pass line is "identical at 20 and at 981, every persona", against `get_home` ≤ 28, `get_nav_counts` ≤ 21, `get_inbox` ≤ 26, `get_frame` ≤ 5, p95 ≤ 500 ms | The property protects the product; the number is a proxy. Slice 044's guard is proved able to fail, which is what makes a green run mean something | A change keeps the count and breaks flatness, and every check still passes | **Require · P1** | |
| **OPS-W4-8** | **Both `IN (...)` scopes become subqueries** — `hr_api.py:496-504` and `hr_api.py:1172-1181` — and `get_team_scorecard` gains the released-review condition **in the query** and a bound on what it reads | Measured: the `IN (981 parameters)` form cost **11.8 ms**, the subquery form **1.1 ms** (042 `03b`, 2026-09-24). The second site also runs a correlated subquery per row with no limit | The widest slope in the product stays, and the privacy control stays one `return rows` away from a leak | **Require · P1** | |
| **OPS-W4-9** | **Settle `page_data`'s real ceiling on the bench, in English *and* in Hindi, before the wizard commit** — and find out whether an oversize write throws or truncates | MariaDB `TEXT` is 65,535 **bytes**; Devanagari and Gurmukhi are three bytes per character, and `page_data` is JSON on top. **I could not check whether our image runs strict mode** | A silent truncation eats part of somebody's self-assessment and tells nobody. In Hindi it happens at a third of the characters | **Require · P1** | |
| **OPS-W4-10** | **Cap the wizard's input client-side below the measured ceiling, with a sentence**, rather than letting a save fail or truncate | AC-40 already asks for "it saves, or it refuses with a sentence before it is lost" | The worst outcome on the most sensitive text in the product: lost silently | **Require · P2** | |
| **OPS-W4-11** | **Time one autosave (20 warm calls, p95 ≤ 500 ms) and run 10 concurrent autosaves** before the production release. If an ordinary request misses 500 ms under that load, lengthen the idle window and cap one save in flight per session | 8 concurrent request slots on one backend replica, on a day a whole tenant is reviewing at once | The portal slows for everybody during review week, and it looks like an outage rather than a queue | **Require · P1** | |
| **OPS-W4-12** | **Count the calls per session on Growth and Team against nginx's `120r/m` per address, `burst=30`** | **Fact**, `nginx.conf:70` and `:270`. A store is one address; an autosave every 15 s is four a minute per person, before page loads | Twenty people reviewing in one store get 429s, and it reads as the product being broken | **Recommend · P2** | |
| **OPS-W4-13** | **Payload budgets asserted in bytes**: `get_team` ≤ 40 KB at 100 rows, `get_growth` ≤ 40 KB, the person sheet ≤ 8 KB | `nfr-budget.md` has no payload number at all, and the 2.5 s phone budget is mostly bytes | The query count stays honest while the payload grows | **Recommend · P2** | |
| **OPS-W4-14** | **Name the half-finished wizard as a retention item now.** A review record is created on first save, holds partial free text and a Version row per autosave, and **no job enforces counsel's "employment + 6 months, then erased"** | The `01c` looked for that job and could not find one. Wave 4 is the wave that starts producing abandoned drafts at scale | An unbounded store of partial self-assessments with no enforced period, found during a security questionnaire rather than before one | **Require · P2** to name and ticket it; escalate if still open at GA | |
| **OPS-W4-15** | **Run the two browser numbers by hand once, on the W1D-09 rig, before the first production release** — the 300 ms skeleton and the 2.5 s usable | Asserted in four documents, measured in none. They are the only numbers describing what the person the redesign is for actually feels | We promise 2.5 s on a phone with no evidence, on the product's landing page | **Require · P1** | |
| **OPS-W4-16** | **Do not make either browser number a blocking CI gate yet.** Add a **non-blocking** job that prints them, run it two weeks, then decide | A timing gate on a shared runner is flaky: the engineer measured `get_frame`'s p50 moving ×2.6 between runs on untouched code. It needs chromium + puppeteer-core + a probe user + `bench serve` on the existing `test-python` job — **estimate +4–8 min** | A red-for-the-weather gate gets ignored, and then it is worse than no gate | **Recommend · P3** | |
| **OPS-W4-17** | **`run_dom_tests.js` must print what it ran and what it skipped, assert a non-zero count, and fail on an undeclared skip** — in the same commit as AC-62 to AC-64's fixtures | Three tests have been skipped and counted as coverage for months. Lesson 19: **a zero from a failed command looks exactly like a zero from a clean file** | A gate that cannot fail, believed for another six months | **Require · P1** | |
| **OPS-W4-18** | **Wave 4 does not touch `deploy/nginx.conf`.** If a route ever needs its own limit, that is its own slice, tested first with `scripts/check_nginx_parses.sh` | One nginx serves production and dev from one file; a dev deploy that edits it restarts the live site's proxy (lesson 13) | A Wave 4 push changes the live site's proxy behaviour | **Require · P1** | |
| **OPS-W4-19** | **Wave 4 ships to production in a release of its own**, with the previous image tag written down and **confirmed present in `alvoraa-app`**, and the two deletions in their own commits | Production pulls only during a deploy — no `pull_policy` in the compose files. A rollback rolls back the whole image | Rolling back Wave 4 also rolls back unrelated fixes, or the tag is not in the package you are pulling from | **Require · P1** | |
| **OPS-W4-20** | **If D-3's nightly trajectory recompute is taken:** a scheduler job on the **`long`** queue, which `worker-long` already listens to; writes only on change; one log line per run with no personal data; volume measured on `test044` first | No new service, no new worker, and **never a hand-listed `docker compose up`** (lesson 1) | A stale "needs attention" chip decides who gets a conversation — or a new job writes thousands of pointless Version rows a night | **Recommend · P2** | |
| **OPS-W4-21** | **A named alert with a named owner for a failed autosave**, and for the Error Log count on `growth_api` and `team_api` in the first hour | `nfr-budget.md` §8. An autosave that fails silently loses somebody's review | We learn about it from the person whose review vanished | **Recommend · P2** | |
| **OPS-W4-22** | **The three release-day actions are named, owned, and recorded as not covered by the rollback:** the `staff_list` tick, the demo seeding on the local copy, the reporting-line data fix | They are settings and data on a tenant, not code | A rollback leaves a half-configured tenant and nobody knows which half | **Recommend · P2** | |
| **OPS-W4-23** | **No sentence about a person, no tenant name and no id is baked into a Wave 4 asset file** | `/assets/` is served to a signed-out client with `Cache-Control: public, immutable` for 30 days | Tenant data on a public, month-cached URL, and no way to recall it | **Require · P1 if it is ever done; a standing rule otherwise** | |
| **OPS-W4-24** | **Wave 1's OPS-15 (the ~7 wasted minutes on `bench version`) is still open** | Measured 6 min 54 s on dev and 7 min 09 s on production, read from the run logs on 2026-09-22. It is most of the rollback time | Every deploy and every rollback stays about seven minutes longer than it needs to be | **Recommend · P2** | |

### Labelled gaps

- **Dangerous debt:** a production deploy does not refresh the sites volume's assets
  (OPS-W4-1). Harmless before OPS-31; dangerous from the release that carries it.
- **Dangerous debt:** `page_data`'s real ceiling, and whether an oversize write truncates
  silently (OPS-W4-9). It is the one gap in this wave that can destroy something a person
  wrote, and it gets worse in Hindi. **One bench check removes it.**
- **Temporary debt:** the wizard's autosave is unmeasured (OPS-W4-11). Removed by one timing
  run and one concurrency run.
- **Temporary debt:** the two browser numbers (OPS-W4-15). Removed by one hands-on session.
- **Intentional trade-off:** autosave stays a foreground write, **conditional on OPS-W4-11
  passing**.
- **Intentional trade-off:** no CI browser gate yet (OPS-W4-16). The cost is that the two
  numbers are checked by a person, once, rather than continuously.
- **Acceptable simplification:** no new service, no new queue, no nginx change.
- **Recorded debt, not ours to close here:** no job enforces the retention period on
  performance records (OPS-W4-14), and there is still no repo-wide `ignore_permissions`
  counter in CI — the fifth wave in a row to say so.

---

## Readiness verdict

**Ready to build the server side today. Not ready to build the wizard, and not ready to
finish the wave.** That matches the analyst's own verdict, and the missing `07` was one of
the reasons — this document closes that box and opens three others.

| Question | Answer |
|---|---|
| Can the six-key `me` block, the month filter, the two subqueries and the two deletions start now? | **Yes.** None of it is a template, none needs a migration, and one closes a live leak |
| Can §6a's two-section payload start now? | **Yes** — and it must be measured on both fixtures as it is built, not afterwards |
| Can the wizard start now? | **No.** D-4, D-5 and D-8 are the analyst's blockers; **OPS-W4-9 is mine**, and it is one bench check |
| Can Wave 4 go to `dev`? | Yes, once built, when Surbhi says so — and after Waves 2 and 3, not beside them |
| Can Wave 4 go to production? | Only after OPS-W4-1, OPS-W4-2, OPS-W4-3, OPS-W4-6, OPS-W4-9, OPS-W4-11, OPS-W4-15, OPS-W4-17 and Wave 1's five swap conditions |
| Is the rollback written, and does its tag exist? | The method is written (§4.3). **The tag is not known yet** — it is written down on the day and confirmed present in `alvoraa-app`. And the rollback reopens the leave-type narrowing and leaves the custom field behind |
| Is anything in this wave one-way? | **The custom field, in practice.** Nothing removes it on a rollback, and nobody should try during a release |

---

## What needs Surbhi's decision, not mine

1. **The workflow change that puts ALV-112's asset refresh on `main`** (OPS-W4-1). My
   recommendation: land it on `main` on its own, with `[skip ci]`, and prove it with one
   deploy before Wave 4 goes anywhere.
2. **Whether the two asset checks are automated inside the Deploy workflow** (OPS-W4-2). My
   recommendation: yes, once step 1 has landed. It edits a workflow file, which is outside a
   feature slice.
3. **Whether the browser numbers gate the production release, and whether a non-blocking CI
   job is worth +4–8 minutes a run** (OPS-W4-15, OPS-W4-16). My recommendation: gate the
   release by hand, once; non-blocking in CI for two weeks; decide after that.
4. **D-3's nightly trajectory recompute** — a stale "needs attention" chip decides who gets
   a conversation. My recommendation: ship AC-24 now and take the job as its own ticket
   (OPS-W4-20).
5. **The payload budgets** (OPS-W4-13), since `nfr-budget.md` has none. My recommendation:
   take the three numbers as a starting line and correct them after the first measurement.
6. **The retention gap on performance records** (OPS-W4-14). Not Wave 4's to fix, and Wave 4
   is what makes it visible. My recommendation: a dated ticket with an owner, now.
7. **Wave 1's OPS-15** — the seven wasted minutes in every deploy and every rollback, open
   since 22 September.

D-12 / 042 D-2 (may HR decide a covered person's attendance correction, and from when) is
also Surbhi's, but it is a permission question and the analyst's framing of it is right; I
add nothing except that the fail-closed default is the correct default for a release.

---

## What I checked today, and what I did not

**Checked, all read-only, 2026-09-24, on this machine:** `deploy/nginx.conf`,
`deploy/compose/docker-compose.app.yml`, `deploy/compose/docker-compose.devstack.yml`,
`.github/workflows/ci.yml`, `.github/workflows/deploy.yml` on `dev`, and on `origin/main`
(`78082fb`) both the tree and that file; `scripts/` (the 19 checks present on `dev`, and
that `browser_check_frame.js` is **not** among them); `alvoraa_portal`'s `ess_parts.py`;
`hr_api.py` lines 494–524 and 1168–1190; `scripts/browser_check_frame.js` in this worktree;
this slice's `02-functional-spec.md` revision 2 and `01c` revision 2; Wave 1's `07`
including §3b and §4.6; Waves 2 and 3's `07`; slice 042's `03b`; slice 044's
`04-test-report.md`; and `.claude/context/nfr-budget.md`.

**Not checked, and therefore not claimed.** Nothing was run on production, on dev or on any
bench. **I measured nothing today.** Every number above is quoted with its date and its
owner, or read from a file, or labelled an estimate. I did not time an autosave. I did not
confirm `page_data`'s column type, MariaDB's strict-mode setting, or what an oversize write
does. I did not test the nginx rate limit. I did not run the browser script. I did not check
how many sites production serves. **I left nothing behind:** no container, no file on a
bench, no changed setting, no push. Nothing above is a secret or a path to one.

## Assumptions

- `[ASSUMPTION]` Production's template chain and its markup-part cache behave as the local
  bench's do. OPS-31's numbers were taken locally, not on the image.
- `[ASSUMPTION]` `frappe.cache()` is site-scoped, so the markup-part key does not need the
  site in it. Confirm once on the bench; the `01c`'s SEC-13 rests on the same fact.
- `[ASSUMPTION]` 10–25 autosave writes per completed review, from AC-37's timing rules.
- `[ASSUMPTION]` `get_team` at 100 six-key rows lands well inside 40 KB, from slice 044's
  measured 18,351 bytes for 50 richer rows.
- `[ASSUMPTION]` Production pulls an image only during a deploy — no `pull_policy` in the
  compose files — so the rollback tag must already exist in `alvoraa-app`.

## Handoff note

**To the engineer:** the four numbers I most want back, in `03-implementation-notes.md` with
the date and the commit — `get_team`'s query count on both fixtures for all five personas;
the same for `get_team_goals` and `my_view`, **first**; the autosave p95 under ten
concurrent saves; and `page_data`'s real byte ceiling with what happens when it is exceeded,
in English and in Devanagari.

**To the security engineer:** three things here belong in the `01c` as requirements with
tests rather than as DevOps advice — that no Wave 4 asset file may carry a sentence about a
person or a tenant name (§3.7; it is served public and immutable for 30 days); that the
abandoned-wizard draft is a retention question with no job behind it (OPS-W4-14); and that a
rollback reopens PRIV-2's narrowing, which is a decided privacy rule coming back by deploy
(OPS-W4-5).

**To the test engineer:** the query-count assertions and the byte assertions go in the same
test as the persona checks, **on both fixtures**, and the pass line is *identical on both*,
not *under a number*. And the staff list is opt-in: a run on a site without `staff_list` in
its `features` refuses every persona and looks like a permission bug.
