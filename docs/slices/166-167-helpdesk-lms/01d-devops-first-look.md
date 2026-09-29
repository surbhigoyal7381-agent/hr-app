# DevOps first look — ALV-166 Frappe Helpdesk, ALV-167 Frappe LMS

**Author:** hrms-devops-engineer · **Date:** 28 Sep 2026 · **Advice only — no server
commands run, nothing pushed.**

All version, dependency and settings facts below were read from the apps' own GitHub
repositories today (28 Sep 2026) with `curl`/`gh` — marked **Fact** with the source.
Build-time and disk numbers are **Measured**, read from real `Build Image` workflow
runs in this repo (also **Fact** — dated, with the run link). Everything else is
**Inference** or **Estimate**, labelled as such. I did not run `bench` anywhere. I did
not touch dev or production.

Surbhi's decisions from the brief are treated as settled: Helpdesk is a resold customer
support desk; LMS is internal training only, feeds Frappe HR's training records, no
payment gateway; both are opt-in per tenant; first tenant is ppj.dev; prospect is Amata.

---

## Top line

**LMS can follow the CRM/WhatsApp pattern with one extra hop (Payments). Helpdesk needs
two extra hops (Payments-free, but Telephony, which itself has no release tag at all)
and its upstream app has no version-16 branch — pin it more carefully than CRM was.**
Both apps vendor their own copy of `frappe-ui` as a **git submodule**, which neither CRM
nor WhatsApp do — that is new and untested in this Dockerfile. **Do not add the
Dockerfile lines until that is proven on a throwaway build.**

**P1 — before any Dockerfile change:** prove `bench get-app` correctly pulls each app's
`frappe-ui` submodule. If it does not, the Vite build fails with a missing-module error
that looks like a code problem, not a missing checkout — exactly the `html2canvas`
trap already written up in this Dockerfile's own comments for a different reason.

---

## 1 · Versions — read from the repos today, 28 Sep 2026

| App | Branch/tag checked | Frappe constraint declared | v16 compatible? |
|---|---|---|---|
| **Payments** (`frappe/payments`) | `version-16` branch, HEAD `cca07d9f` (26 May 2026) | Frappe's own version-16 maintenance branch — same convention as our `FRAPPE_BRANCH`/`ERPNEXT_BRANCH` | Yes — it is Frappe's own v16 line |
| **LMS** (`frappe/lms`) | `version-16` branch, HEAD `87168fc7` (10 Sep 2026) | `pyproject.toml` on this branch states **no** `frappe` version bound at all | Yes, by branch name and by the `assets-version-16` asset tag (16 Sep 2026) built from it |
| **LMS** (`develop`, for contrast) | HEAD is what `v2.63.0` etc. track | `frappe = ">=17.0.0-dev,<18.0.0"` | **No** — `develop`/the numbered tags (`v2.6x`) track Frappe v17-dev, not our v16.35 |
| **Telephony** (`frappe/telephony`) | only branch is `develop`, HEAD `039cf39f` (18 Aug 2026) | `frappe = ">=14.101.0,<=17.0.0-dev"` | Yes, within range, but **no tag ever cut** — one branch, no release history |
| **Helpdesk** (`frappe/helpdesk`) | tag `v1.30.1` (3 Sep 2026, sha `1c3361cc`) | `frappe = ">=15.116.1,<17.0.0"` | Yes |
| **Helpdesk** (`main-hotfix`, for contrast) | HEAD 24 Sep 2026 | same constraint as `v1.30.1` | Yes, and 21 days newer, but it is a moving branch |

**Recommend:**
- Pin **Payments** and **LMS** to a **commit on `version-16`** (not the bare branch —
  the checklist's own rule: never a moving branch). Use the exact commits above,
  re-verified the day the Dockerfile change is written, the same `get-app --branch X &&
  git checkout <sha>` pattern already used for WhatsApp.
- Pin **Helpdesk** to the release **tag `v1.30.1`** — it exists, it is legible in a
  diff, and the checklist prefers a tag over a branch+commit when one exists.
- Pin **Telephony** to **commit `039cf39f`** on `develop` — there is no tag to pin to,
  so this gets the WhatsApp treatment: fetch the branch, then checkout the commit,
  with a comment saying why (no release has ever been cut).

**Decision for Surbhi:** none needed here — this is evidence, not a choice. Flagging
that **Telephony has never had a tagged release**, which is a thinner supply chain than
anything else in the image today; if Helpdesk is approved, re-check this before every
future bump, not just this one.

---

## 2 · Required apps — the real install chain

**Fact**, read from each app's `hooks.py` and `pyproject.toml` today:

- **LMS** declares `required_apps = ["frappe/payments"]` in `hooks.py`. Install order:
  `erpnext → payments → lms`.
- **Helpdesk** declares `required_apps = ["telephony"]` in `hooks.py`, and telephony
  itself declares none. Install order: `erpnext → telephony → helpdesk`.
- Neither declares the other as a requirement — they are independent chains.

**Does LMS work with Payments installed but no gateway configured?**
LMS Settings (the single settings doctype) carries two fields for exactly this case:
`payment_gateway` (free text, blank by default) and an HTML field literally called
`payments_app_is_not_installed`, shown inside a section named `no_payments_app`. That
tells me the LMS authors built for **Payments installed, but not configured** as a
normal state, not an edge case — **Inference**, from reading the field names and their
grouping, not from running the app. Course pages with no price render free; batches
with a price and no gateway are the one place I would test before any tenant sees a
priced course — and per Surbhi's decision **there is no gateway and no priced course
planned**, so this class of bug should never be reached. **Recommend:** the Business
Analyst or engineer confirms in the strategy stage that no LMS course/batch ever gets a
price field filled, since that is the only path that would exercise the missing
gateway.

**Does Helpdesk require anything beyond Telephony?** Fact, from `hooks.py`: no. It does
not require CRM, Payments, or anything already in our image.

---

## 3 · LMS privacy switches — exact fields, read from `lms_settings.json` today

`LMS Settings` is a single (`issingle`) doctype, System Manager and Moderator only.

| Field | Default in the repo | What it controls |
|---|---|---|
| `allow_guest_access` | **Check, default `1` — ON** | Whether someone with no login can view course/lesson pages at all. **This is the one that must flip to 0 on install** — it ships open. |
| `disable_signup` | **Check, default `1` — already OFF-by-default** | Self sign-up. Already safe out of the box; confirm it stays `1` in our fixture rather than assuming. |
| `allow_job_posting` | Check, default `1` | A public jobs board tab — irrelevant to internal training; recommend `0`. |

**Recommend:** a fixture (same mechanism CRM/WhatsApp already use for their own
defaults) that writes `LMS Settings` with `allow_guest_access = 0`, `disable_signup = 1`,
`allow_job_posting = 0` on install, so a tenant is never one missed click away from a
public course catalogue. This is the single most important line in this whole document
— the brief already flagged the risk; this is the exact field that closes it.

**Decision for Surbhi:** none — this is a build requirement, not a choice, given her
"internal only, no public catalogue" decision already made.

---

## 4 · Build cost — measured, not estimated

I read real `Build Image` run logs in this repo (`gh run view <id> --log`), not a
guess.

| What | Measured value | Source |
|---|---|---|
| Current build, warm cache (no new app, e.g. the 27 Sep rename commit) | **6m 18s** | run 36323595557, 27 Sep 2026 |
| Current build, several small dev commits stacked | **9–21 min**, varying with cache state | runs 36298049664 (21m31s), 36298915237 (14m43s), 36300859587 (9m56s), all 27 Sep 2026 |
| **Adding WhatsApp** (one new app + its frontend, no submodule) | **19m 47s** | run 36008417208, 24 Sep 2026 |
| **Adding CRM the first time** (bigger Vue frontend) | **failed at 15m 54s** — ran out of runner disk | run 35857895285, 23 Sep 2026 |
| The fix (move yarn's download cache out of image layers) | **12m 34s**, succeeded | run 35876345149, 23 Sep 2026 |
| Runner disk free, checked on a recent normal run | **86 GB free before the cleanup step, 109 GB after** | run 36323595557, 27 Sep 2026 — this **disagrees with the Dockerfile's own comment**, which says "about 14 GB free"; that comment is now stale, or was measured before the yarn-cache fix. Either way, disk is not the tight constraint it was on 23 Sep, but **re-measure at the time of the actual build**, don't carry my number forward blind. |

**Estimate, not measured:** adding LMS's frontend plus Helpdesk's `desk` frontend — two
more Vue/Vite builds, one more `bench get-app`, two more `bench build --app` steps —
by interpolation from the WhatsApp (+20 min once) and CRM (+disk exhaustion once,
+13 min after the fix) data points, **budget +15–25 min per app, so roughly +30–50 min
on a cold build that touches both**, and a modest but real image-size increase (courses
in LMS bring `cairocffi`/`lxml`/native deps; Helpdesk brings `textblob` and a
search-index build step in `after_migrate` — neither is huge, but neither is zero).
**This is the number to re-measure on a real throwaway build before committing to the
Dockerfile — do not trust the interpolation.**

**ALV-164 — Actions minutes on the private repo.** I could not check the account's
actual remaining minutes or plan tier from here — **Unknown, needs the GitHub billing
page**. What I can say: this repo pushes to `Build Image` many times a day (the run
list shows dozens of runs on 27 Sep alone). Adding 30–50 minutes to *every* cold build,
and some amount to every build that touches these apps' own code later, is a real
addition to a budget that is already named as tight. **This is the number that decides
whether "always in the image" is affordable — ask whoever owns the GitHub billing page
before committing.**

---

## 5 · "Keep other customers' builds lighter" — the options

Her ask, read literally, is about **the shared image**: one thing built once, pulled by
every environment, run by every tenant's containers, whether or not that tenant bought
Helpdesk or LMS.

**What "install-app only" already does and does not do.** The CRM/WhatsApp pattern —
present in the image, `bench install-app` run only for tenants that bought it — already
means a tenant that never buys LMS gets **no extra database tables, no extra doctypes
reachable by URL, no extra migrate time on that site** (Frappe's `bench migrate` only
touches a site's own installed apps, not everything in the bench). So at the
**per-tenant runtime** level, "off by default" already delivers what she is asking for.

What it does **not** solve: the image itself — pulled by dev, by test, by production,
by every container in every stack — carries the extra code and built assets for every
tenant, forever, and every build spends the extra CI minutes, whether or not anyone
bought the feature that day.

| Option | What changes | Ops cost |
|---|---|---|
| **(a) One image, all apps** (today's pattern) | Nothing structural — add Payments, LMS, Telephony, Helpdesk to the same Dockerfile, gate install by feature as CRM/WhatsApp already do | **Cheapest to build and operate.** One image to test, one pull, one rollback tag. Cost is the one-time size/build-time increase measured above, paid on every build forever, whether sold or not. Fits ALV-164 only if the minutes budget has room — **unverified**. |
| **(b) A second image variant** (separate compose stack/backend service for tenants that bought Helpdesk/LMS) | New `deploy.yml` job, a second set of containers, a second `docker compose` file, nginx needs to route those tenants' hostnames to the second backend | **Most expensive.** Two images to build (more CI minutes, not fewer — this makes ALV-164 worse, not better), two things that can drift, two rollback paths, and — per lesson 2 in my own reading list — every container in a stack must report the same tag; a second stack doubles that risk. Only worth it if a tenant needs isolation Helpdesk/LMS cannot get any other way, which is not the case here. |
| **(c) Build the front ends only when needed** | Multi-stage / conditional build so `bench build --app lms` and `--app helpdesk` run only in an image variant, or as a follow-up layer applied post-pull | Saves build minutes **only for images that skip the step**, which means you are back to variant images (option b's cost) or a manual "did anyone buy this yet" build flag that a human must remember to flip — the kind of thing this project has already been burned by (a default that hid a missing setting). Not recommended on its own. |

**Recommend: (a), same as CRM and WhatsApp** — it is the pattern already proven twice in
this repo, it is the cheapest to operate, and per-tenant isolation is already achieved
by `install-app` gating, which is what she actually asked for in the CRM precedent.
**The one open condition:** confirm the ALV-164 minutes budget has room for the
measured +15–25 min per app before this is added — if it does not, the honest fallback
is not option (b) or (c), it is **"wait" or "batch this behind fewer, larger pushes"**,
because both alternatives cost more CI time, not less.

**Decision for Surbhi:** approve option (a), or ask for the ALV-164 minutes number
checked first. My default, if you want to keep moving: proceed with (a) and treat the
minutes question as a must-answer-before-merge gate at the strategy stage, not before
this first look.

---

## 6 · Hosting, nginx, and the shared bench

**Routes.** Fact, from `deploy/nginx.conf`: CRM has **no dedicated `location` block** —
it serves at `/crm` through Frappe's own website page router, caught by the existing
generic `location ~ ^/(hrms-employee|...)?$` and `location /` fallbacks, which already
proxy everything else to `frappe_http`. LMS and Helpdesk both serve themselves the same
way (`/lms`, `/helpdesk` are Frappe website routes, not separate web servers) —
**Inference**, from how CRM already works and from both apps declaring `website_route`
style pages the same way CRM does, not from having deployed either. **Recommend:** no
new nginx `location` block is needed for either app, same as CRM needed none — but
**this must be proven on a real dev deploy before it is assumed true for a live
tenant**, per the standing rule that one `nginx.conf` serves dev and production from the
same file (lesson 13 in my reading list). Test with `nginx -t` on the exact file first.

**Socket / realtime.** Both apps use Frappe's standard `frappe.realtime` (Helpdesk for
live ticket updates, LMS for live-class notices) — the existing `/socket.io` location
already proxies this for the whole site; no separate socket route needed. **Inference**,
from the same "no dedicated app server" reasoning, not measured.

**Helpdesk email-to-ticket.** Fact: Helpdesk turns inbound mail into tickets through
Frappe's own **Email Account** doctype with the "read" side enabled — the same
mechanism every Frappe site already uses for support inboxes, not a new pipeline.
Two consequences for us specifically:
- **Per-tenant Email Account, per-tenant credentials** — the same "secrets never in job
  arguments" rule already in this project's baseline applies; the Email Account's
  password is a normal per-site encrypted setting, not something DevOps configures
  centrally.
- **Mail pull runs on the scheduler**, and this project's own scheduler currently ticks
  every 3–4 minutes on dev instead of every minute (the ALV-141 finding already on
  record). A ticket created by email will lag by that much until ALV-141 is closed —
  **not a blocker for an internal demo tenant, but a real number to tell a resold
  customer-support buyer**, since "how fast does my ticket appear" is exactly the kind
  of question a support-desk buyer asks.

**Shared bench load.** Fact: this compose file already runs one `worker-default`
(`default,short` queues) and one `worker-long`, with the standing rule that a worker
must be listening on any queue a job is pushed to (lesson 1). Helpdesk's search-index
build (`after_migrate`) and LMS's own background jobs use Frappe's normal queues, not a
new one — **Inference**, since neither app's `hooks.py` declares a custom queue. No new
worker is needed on that evidence, but **confirm at the strategy stage** by grepping
both apps for `enqueue(..., queue=` calls, the same way the checklist asks the engineer
to check fixture and doctype clashes.

---

## 7 · Order and size

1. **LMS first, if approved** — one required app (Payments), a real `version-16`
   branch, a release history, no telephony chain. Smaller, lower-risk slice.
2. **Helpdesk stays parked**, per the brief's own recommendation and Surbhi's decision
   that it needs its own scoping (resold support desk vs. internal HR desk) before any
   engineering starts — this first look answers the *technical* questions in case she
   revisits it, but does not change the brief's "not now" call.
3. **Before either reaches a Dockerfile:**
   - Prove the `frappe-ui` submodule pulls correctly on a throwaway `bench get-app`
     (P1, above) — this is new to this Dockerfile and neither CRM nor WhatsApp tested it.
   - Get a real, not interpolated, build time and image-size delta from a throwaway
     build that adds Payments + LMS only.
   - Check the ALV-164 minutes budget before deciding on §5's option (a).
   - Add the LMS Settings fixture (§3) in the same commit that adds LMS to
     `provision_tenant.sh` — never let the app install with guest access on, even for
     one deploy.
4. **Release steps, once LMS is approved for engineering** (mirrors CRM/WhatsApp exactly,
   nothing new): add `PAYMENTS_COMMIT` and `LMS_COMMIT` ARGs to `deploy/Dockerfile`;
   add `lms` as `opt_in: True` under `ERPNEXT_FEATURES` in `subscription.py`, `app: "lms"`,
   `requires: ["payments"]` is not the right key here since Payments is infrastructure,
   not a sold feature — install Payments unconditionally inside the `has_feature lms`
   branch in `provision_tenant.sh`, the same way CRM's own ERPNext prerequisites are
   installed inline rather than sold separately; add the install branch to
   `provision_tenant.sh` guarded by `has_feature lms`; add the LMS Settings fixture;
   build on a throwaway branch first; measure; then, and only then, a real PR to `dev`.

---

## Blockers found today

None that stop the first look itself. Two must-answer-before-Dockerfile items:

- **P1 — the `frappe-ui` submodule question (§ top line).** Untested; could silently
  break the Vite build the way the missing `html2canvas` node_modules did before.
- **P2 — ALV-164 minutes budget unconfirmed (§4, §5).** I could not check it from here.
  Get the number before deciding "always in the image."

---

## Open questions for Surbhi

| Question | Why it matters | My default if you want to keep moving |
|---|---|---|
| Do you want the throwaway build (Payments + LMS only, no Dockerfile commit yet) run now, to get real build-time and size numbers before the strategy stage? | Replaces every "Estimate" in §4 with a "Measured" | Yes — run it on a disposable branch, discard the image, report the numbers, no Dockerfile change lands until you approve the strategy |
| Who checks the ALV-164 Actions-minutes balance — you, or should I ask the fullstack engineer to check GitHub billing? | Decides whether §5 option (a) is affordable at all | I recommend you check it directly (it needs the GitHub org/billing view I don't have) and tell me the number |
| Confirm: no LMS course or batch will ever carry a price, so the "Payments installed, no gateway" state (§2) is never exercised by a real user | If wrong, that state needs an actual test before go-live, not just a read of the field names | Assume no pricing, per your original decision, unless you say otherwise |
