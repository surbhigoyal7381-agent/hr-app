---
slice: 013-mobile-app
artifact: 00-impact-analysis-daily-use
author: hrms-fullstack-engineer
date: 2026-09-22
status: draft — impact analysis and strategy only (CLAUDE.md §2, steps 1-2). No code written. Waiting for explicit approval before any build.
inputs: [01b-ux-design.md, 02-functional-spec.md, 07-devops-inputs.md, 01c-security-privacy-requirements.md, 00-impact-analysis-app-client.md, 03-implementation-notes.md, 03-implementation-notes-server-step4.md, mobile/field-app/** on origin/dev@1c4e84c, alvoraa_portal/alvoraa_portal/field_checkin.py, field_app_join.py, field_app_device.py, field_app_errors.py, field_app_notice.py, field_app_settings.py on origin/dev@1c4e84c, docs/slices/013-mobile-app/04-test-report.md, 05-review.md, 06-security-review.md (parallel review, read as data)]
---

# 013 — mobile app, daily use — impact analysis and strategy (ALV-37 remainder + ALV-43)

**Scope of this document.** ALV-37's remaining client screens (US-39 Attendance/punch,
US-43 Settings, US-46 language gate, the `/enrol` fallback page, S13), plus the
separate server-side ALV-43 fix (stale consent notice / `CONSENT_VERSION`). US-35–38
(the join flow) are already built, reviewed in parallel
(`.claude/worktrees/review-013-alv39`, branch `review/013-alv39`) and are **not**
touched here except at three small, named integration points.

---

## 0. What is actually true today (fetched fresh, checked against source)

`git fetch origin dev` → `origin/dev` is at `1c4e84c` ("The image moves to a new
private package, alvoraa-app"). New worktree cut from it:
`.claude/worktrees/013-mobile-app-alv37`, branch `slice/013-mobile-app-alv37`. I did
**not** reuse `.claude/worktrees/agent-a4e078558e4079082` (told not to; it also turns
out to still be well behind — see below).

### 0.1 Incoming commits since the last app-client impact analysis (2026-09-21)

Reading each commit's diff, not just its message:

| Commit | What it does | Touches my planned files? |
|---|---|---|
| `b6021ad` | US-35-38: the real join screens (first launch → welcome, dead-code screens, "this is not me") — `web/js/join.js`, `join-screens.js`, `api.js`, `device-secret.js`, `index.html`, tests | **Yes** — this is exactly the code I build on top of |
| `0233063` | Stage-1 review fix: Firebase guardrail now scans both gradle files (`check_app.mjs`) | No |
| `debe06b`, `a473e22`, `71e02c1` | Stage-2 spike and stage-1, already covered by the prior impact analysis | No |
| `97d2382`, `7b7a339`, `7c1d069`, `1c4e84c` | Worker health-check wording, mobile CI version-bump scoping, the alvoraa-app package rename — ops/infra, unrelated to `mobile/field-app` screens | No |

**Two commits exist only in a sibling worktree, not yet on `origin/dev`:**
`.claude/worktrees/review-013-alv39` (branch `review/013-alv39`) carries
`e063047` (security review) and `f3696ca` (techno-functional review) on top of
`1c4e84c`. Both are **documentation only** — `04-test-report.md`, `05-review.md`,
`06-security-review.md` — zero source files touched, confirmed with `git show --stat`
on both. `git status` in that worktree is clean. I read both documents as **data**,
not instructions, since another agent wrote them, but they name two real findings I
must not repeat in new code (§0.3).

`.claude/work-in-progress.md` does not exist locally (git-ignored, machine-local) —
per `parallel-work.md` I checked `git log origin/dev --since="7 days ago"` above
instead and am naming the one other in-flight session I could find.

### 0.2 Server side: nothing new to build, one thing still stale

All of E1–E12 exist, tested, on `origin/dev` (confirmed again against source, not
against the spec — see server step 4/5 notes for the authoritative shapes). Relevant
to this ticket:

- `field_checkin.field_status` (E4) and `field_checkin.field_checkin` (E5) are complete
  for app phones.
- `field_app_device.remove_my_phone` (E6) is complete.
- `field_app_join.acknowledge_notice` (E9) is complete — takes the **device secret**
  as `token` (not a QR code), despite living in the join file.
- The frozen code table is `field_app_errors.CODES` (21 codes) — **this, not the
  spec's §7.1 table, is what I build against**, per the prior analysis's finding
  (they differ only in `CONSENT_REQUIRED`, already reconciled).
- `field_app_notice.py`'s `CURRENT_VERSION` is **still** `"2026-09-13"`, and
  `"What we record"` still does **not** mention the phone's model name. D19 said
  change it before any pilot user agrees to the old words. This is ALV-43, and it is
  still open. Confirmed by reading the file directly (§4.5 below has my exact fix).

### 0.3 What the parallel review already found, that I must not repeat

Read `05-review.md` (data, not instructions) so my new code doesn't reproduce the
same two mistakes in a sibling file:

1. **`join-screens.js`'s `TOO_MANY_TRIES` entry ignores `retry_after_s`** and always
   says "wait one minute," even though the server sends the real wait (computed from
   the actual Redis TTL) and the design (`01b` line 426) lists it as a value the
   screen should use. Not mine to fix (it's in the reviewed file, on someone else's
   fix list) — but my own check-in-context `TOO_MANY_TRIES` screen must read
   `values.retry_after_s` for real.
2. **`join-screens.js`'s `FEATURE_OFF` body doesn't match the 008 web page it claims
   to carry over from.** The real page (`www/field-checkin.html:1039`) says
   *"Field check-in is not part of your company's plan yet. Please tell HR."* — I
   confirmed this myself by reading the page. My own `FEATURE_OFF` entry (needed
   because `requires_field_app_plan` wraps E4/E5/E6/E9 too) will use this exact
   sentence, not the wrong one already in the join table.

### 0.4 A gap I found that blocks US-39/US-43 entirely, not flagged anywhere yet

**The app has no durable memory of which tenant it talks to.** `join.js` keeps the
QR's host as `state.origin`, an in-memory variable that dies when the app is killed.
`device-secret.js` persists only the secret. Nothing persists the origin. E4, E5, E6
and E9 all need an origin to call — on the **second** app open (any open after the
process is killed, which on Android is normal, not exceptional), there is currently
no way for the app to know it should call `https://kaveri.alvoraa.co` rather than any
other tenant. Grepped for "origin" across every `web/js/*.js` file to confirm this is
not solved elsewhere; it is not. This is not a design-doc gap either — `01b` §7.13
("Connected to {host}") assumes the host is known, and never says how.

**This is the one genuinely new architectural piece this build needs**, and it
gates everything else in US-39/43. My proposed fix is in §4.1.

### 0.5 What's directly reusable, confirmed against the real files

| File | Reusable as-is? |
|---|---|
| `web/js/photo.js` | **Yes, unchanged.** `shrinkToJpeg`/`fitSize` are exactly AC-201's numbers, pure, already unit-tested. The punch photo capture is new DOM/camera code that calls this — same shape as `join.js`'s existing scanner code, which already opens `getUserMedia`. |
| `web/js/device-secret.js` | **Reusable, needs one small extension** (§4.1) — a second key for the tenant origin, using the same already-tested `nativePlugin()` gate. |
| `web/js/api.js` | **Reusable, needs four new exported functions** (§4.2) — `fieldStatus`, `punch`, `removeMyPhone`, `acknowledgeNotice` — appended beside the existing three, calling the same shared `callMethod`. No existing function changes. |
| `web/js/join-screens.js` | **Not extended.** See §4.3 for why, and what I build instead. |
| `web/js/build-type.js`, `app-version.js`, `host-check.js`, `qr-decode.js` | **Read-only reuse**, no changes. |
| `android/` (permissions, manifest, gradle) | `ACCESS_FINE_LOCATION`/`ACCESS_COARSE_LOCATION`/`CAMERA` already declared and already on `check_app.mjs`'s allow-list. **No new permission, no new native plugin, no new npm dependency needed** for US-39/43 — plain `navigator.geolocation.getCurrentPosition` and a second `getUserMedia` capture, both standard Web APIs already proven to work in this WebView (`09-install-the-test-app.md`). |

---

## 1. Functional cross-module impact

| App | Touched? | How |
|---|---|---|
| `mobile/field-app/**` | **Yes — this is the build** | New screens, three small edits to already-built join files (named exactly in §4.4), one new small module (`notice-cache.js`), one new pure module (`checkin-screens.js`), the `/enrol` page lives in `alvoraa_portal`, not here |
| `alvoraa_portal` | **Yes, narrowly** — `field_app_notice.py` (ALV-43: new notice version), its pin test in `tests/test_field_app_step1_013.py`, and one **new** guest `www` page (`/enrol`, S13). Every device/join endpoint is read-only from this build's point of view — no endpoint signature changes | See §4.5, §4.6 |
| `hrms`, `erpnext`, `alvoraa_goals`, `alvox_compensation` | **No** | Confirmed no import, no hook, no doctype touches these |
| `www/field-checkin.html` (the 008 web page) | **No — deliberately.** `AC-35` protects it from this slice; `notice_facts()`'s own comment says the page reading the store "belongs with the page's own work," not yet assigned. Bumping `CONSENT_VERSION` has zero functional effect on it: `_refuse_unless_notice_is_current` is app-phones-only (confirmed: AC-96, "web phone never asked about the notice") | See §4.5 for exactly how I keep the drift-guard test honest instead of editing this file |
| `.github/workflows/*` | **Possibly, one line** — only if `mobile.yml`'s test glob needs a new file added; no logic change | Check at build time, hot file per `parallel-work.md` |

**Grep of callers**, for every function I newly call:
`field_status`, `field_checkin` — already called by the web page (no header) and now
also by the app (with header); `remove_my_phone`, `acknowledge_notice` — app-only,
already exist, no other caller today. No function I am adding a caller to needs a
signature change.

**Persona impact**

| Persona | What changes |
|---|---|
| **Field employee** | Gets a working Attendance screen and Settings for the first time — this is the rest of the WOW moment `01b` describes. Nothing changes for them on the web check-in page, which is untouched. |
| **HR Manager** | No change — desk-side work for this shipped in server steps 4-5. They now see real app phones checking in instead of only the join screens working. |
| **CXO** | Nothing visible, as the design says. |

---

## 2. Non-functional dimensions

**Performance** — *neutral, by construction.* Same discipline as the join flow:
version header + 30 s timeout on every call, no automatic polling (`field_status` is
called once on open, and again only after a punch's own answer, per AC-199/202 — no
extra E4 after a punch). The photo/geolocation capture adds no new dependency, so the
10 MB package budget (already tight after `jsQR` + the secure-storage plugin) is not
touched further.

**Security** — *neutral to improving, with one deliberate new surface named
honestly.* Extending `device-secret.js` with a second Keystore-backed key (the
origin) keeps the **same** fail-closed gate (`nativePlugin()`) the secret already
uses — no new attack surface class, just one more small piece of non-secret data
behind the same lock. Every server value is still rendered with `textContent`
(`checkWebFile`'s `HTML_SINK` regex will catch a regression in CI). The one honest
new risk: the origin, unlike the secret, is not itself sensitive, but if it were ever
written to `localStorage` instead (I am not proposing this — see §4.1) it would leak
which tenant a phone belongs to from a lost/backed-up phone. Keeping it in the same
Keystore store avoids that question entirely.

**Reliability** — *this is most of the new work.* 21 server codes (`field_app_errors.CODES`)
plus the app's own client-made codes must each land on exactly one screen, driven by
`code` alone (never English text), with a safe `unknownCode` default for anything not
in the table — same discipline the join flow already proved out, applied to a
different code set. Photo-kept-across-retry (AC-205) means the punch photo blob lives
in state above the screen router, not re-captured on every retry — same pattern
`join.js` already uses for the QR scan. The new tenant-origin persistence
(§4.1) removes a reliability gap that would otherwise make every second app open
silently unable to call the server.

**Scalability** — *neutral.* No new automatic background work; the per-phone rate
limits (E4 60/h, E5 30/h, E6 5/h, E9 5/h) are already enforced server-side and
already account for the "busy depot" case.

**Maintainability** — *the one real design choice in this document, argued in
§4.3.* I am **not** adding ~18 new entries to the already-reviewed `join-screens.js`,
even though the earlier impact analysis recommended one shared table. A single flat
`code → screen` map cannot correctly serve two different bodies for the same code in
two different contexts (`TOO_MANY_TRIES`, `SERVER_ERROR`, `NO_INTERNET`, `APP_TOO_OLD`
all read differently at check-in than at join, per `01b` §7.12 itself), and a large
edit to a file another session is actively reviewing is exactly the kind of clash
`parallel-work.md` asks me to avoid when a smaller alternative exists. A new sibling
module, reusing the join table's exported date-formatting helpers rather than copying
them, is the smaller, safer alternative — named in full in §4.3.

**Data integrity** — *the tenant origin becomes the second piece of state that must
never be lost independently of the secret.* Both are written by the controller only
after the server confirms (secret already does this; origin will follow the exact
same order — save origin and secret together after E3 succeeds, before showing
`welcome`), and both are cleared together wherever the app returns to first-launch
(Remove this phone, Removed/blocked/replaced-by-server states). I will **not** clear
one without the other in any code path — flagged explicitly here because it is the
one new failure mode this build introduces if done carelessly.

**Compliance / privacy** — *one real fix (ALV-43), one honest limit named.* The new
notice version discloses the phone-model collection, closing the gap `01b`/PRIV-2
named. The web page keeps serving the pre-review words (§1 above, AC-35) — this is a
**named, declared gap**, not a silent one; it is not this build's to close and I say
so again in §4.5's open question. `PRIV-9` (no "last opened" from the phone) already
holds server-side (E4 writes nothing) — my client code does not add a write-on-open.
Settings' "What this app records" (AC-215) shows the notice text from **locally
saved data, no call** — that data is the same notice text HR already showed this
person at setup, not new personal data, so caching it locally (§4.4) does not widen
what the phone holds beyond what `01c`'s inventory already allows.

---

## 3. Parallel-work check

**Files I will change, and who else is in them:**

| File | My change | Anyone else in it? |
|---|---|---|
| `mobile/field-app/web/js/join.js` | **Three small, named edits** (§4.4) | The just-finished, just-reviewed file. No pending commits touch it (review branch is docs-only). The review's two wording fixes (§0.3) live in `join-screens.js`, not here, so no overlap with my edits |
| `mobile/field-app/web/js/join-screens.js` | **None.** New codes go in a new sibling file instead (§4.3) | Named in the review's fix list for the two wording bugs (§0.3) — not touched by me, so whoever picks up that fix list has a clean file |
| `mobile/field-app/web/js/device-secret.js` | **One small, named extension** (§4.1) — new exported functions, no change to existing ones | Same as above — reviewed, no pending edits |
| `mobile/field-app/web/js/api.js` | **Four new exported functions appended** | Same |
| `mobile/field-app/web/index.html` | New `<section>` markup for the new screens; remove the one placeholder paragraph (`#welcome-not-built`) | Same — this file is the shared shell every stage adds to; nothing else in flight touches it |
| `mobile/field-app/web/js/checkin.js`, `checkin-screens.js`, `notice-cache.js` (new files) | New | N/A |
| `mobile/field-app/android/app/build.gradle` | `versionCode` bump only | Not touched by the review branch |
| `alvoraa_portal/alvoraa_portal/field_app_notice.py` | New version entry + `CURRENT_VERSION` bump | Not touched by anyone else found |
| `alvoraa_portal/alvoraa_portal/tests/test_field_app_step1_013.py` | `TheNoticeSaysWhatItSaid` class updated (§4.5) | Not touched by anyone else found |
| `alvoraa_portal/alvoraa_portal/www/enrol.py`, `www/enrol.html` (new) | New | N/A |

**The plan when there is overlap:** there is none at the file level — the review
branch is documentation-only. The only *content* overlap is the two wording bugs in
`join-screens.js`/`join.js` (§0.3): I sequence around them by not touching that file
and by not reproducing either mistake in my own new code. If that review's fix
commits land on `origin/dev` before I merge, I will rebase and re-check that my new
`checkin-screens.js` still reads correctly against the (by then fixed) join table —
no conflict expected since I do not import anything from it beyond the two exported
pure helpers (`onDateAt`, `todayOrDateAt`), which the review does not touch.

**Tests that pin what I touch:** `test_field_app_step1_013.py`'s
`TheNoticeSaysWhatItSaid` class already pins the notice's exact words — I update it,
not bypass it (§4.5). New `node --test` files pin every new pure module the same way
`join-screens.test.js`/`photo.test.js` already do for the existing ones.

**Worktree/branch:** `.claude/worktrees/013-mobile-app-alv37`, branch
`slice/013-mobile-app-alv37`, cut from `origin/dev@1c4e84c` today. Not pushed. Not
merged into local `dev`. No bench, no Android SDK, no device in this sandbox (stated
up front, per the task's constraints) — proof is `npm test` and `npm run check` for
the app, and `ast.parse`/`ruff`/`node --check` plus a written-but-unrun test module
for the server side, exactly as the server-step docs already do honestly when the
bench is unavailable.

---

## 4. Proposed strategy

### 4.1 The tenant-origin gap (§0.4) — extend `device-secret.js`, not a new store

Add two more exported functions to `device-secret.js`, reusing the existing
`nativePlugin()` gate and a second fixed key (`alvoraa_tenant_origin`):
`saveOrigin(origin, cap)` / `loadOrigin(cap)`. `clear(cap)` is extended to remove
**both** keys in one call, so every existing caller of `clear()` (Remove this phone,
and any future "phone is dead, go back to first launch" path) wipes both pieces of
state together — the one failure mode called out in §2's Data integrity row.

**Why not `localStorage` or a new plugin:** the origin is not secret, but it is the
thing that decides which tenant a phone talks to; keeping it beside the secret in the
same already-vetted, fail-closed store is simpler than running two storage
mechanisms with two lifecycles to keep in sync, and costs nothing (Keystore has room
for a short string). No new npm dependency.

**Order of writes at join (US-37, already-built code):** E3 succeeds → save the
secret → save the origin → save the notice snapshot (§4.4) → show `welcome`. If any
save fails, show `SERVER_ERROR` exactly as `join.js` already does when the secret
save fails — same honest "the server has already joined this phone" situation,
extended to cover the new writes too.

### 4.2 `api.js` — four new functions, no changes to the existing three

```
fieldStatus(origin, token, opts)       -> field_checkin.field_status
punch(origin, params, opts)            -> field_checkin.field_checkin
removeMyPhone(origin, token, opts)     -> field_app_device.remove_my_phone
acknowledgeNotice(origin, token, notice_version, opts) -> field_app_join.acknowledge_notice
```

All four call the existing `callMethod`, unchanged. Same contract: never rejects,
resolves to `{ok:true, data}` or `{code, values}`.

### 4.3 A new `checkin-screens.js`, not an extension of `join-screens.js`

**Why a new file rather than the "one shared table" the prior analysis
recommended:** that recommendation assumed every code's wording is context-free. It
is not — `01b` §7.12 gives `TOO_MANY_TRIES`, `SERVER_ERROR`, `NO_INTERNET` and
`APP_TOO_OLD` genuinely different bodies at check-in than at join (the check-in
versions mention "photo kept" and carry a "For HR" card the join versions do not). A
flat `code → builder` map, as `join-screens.js` is today, cannot hold two different
answers for one key. Making it context-aware (`screenFor(code, values, opts, context)`)
would work, but it means editing a file another session is mid-review on, for a
change bigger than "small" (this is the parallel-work judgement call — I'm choosing
the smaller-footprint path). `checkin-screens.js` is the same shape and the same
`screenFor(code, values, opts)` contract, covering exactly the codes E4/E5/E6/E9
can send (`CONSENT_REQUIRED` included, defensively — see §4.7), plus the app's own
client-made codes for the daily-use context (`LOCATION_DENIED`, `LOCATION_OFF`,
`LOCATION_SLOW`, `NO_INTERNET`). It imports (does not copy) `onDateAt`/`todayOrDateAt`
from `window.AlvoraaJoinScreens` — the two already-exported, already-tested pure
helpers — so date formatting is not duplicated, only the per-code text tables are
two files instead of one. `TOO_MANY_TRIES` reads real `retry_after_s`; `FEATURE_OFF`
uses the real 008 sentence (§0.3) — both corrected in the new file rather than
inherited-wrong.

`NOTICE_CHANGED` is **not** in this table — like `join.js` already does for its own
`NOTICE_CHANGED` handling, it needs the full six-row notice UI, not the generic
heading/body/buttons shape, so `checkin.js` renders it directly (reusing the SAME
notice-row markup pattern `join.js`/`index.html` already has for `notice`).

### 4.4 `join.js` — the three integration edits, named exactly

1. **Wrap the trailing `show("first");`** in an exported `start()`:
   `window.AlvoraaJoin = { start: function () { show("first"); } };`, called by a
   new small bootstrap script (below) instead of running unconditionally. Nothing
   else in the file changes.
2. **Wire the two placeholder `welcome-*` actions**: `welcome-check-in` calls
   `window.AlvoraaCheckin.start(...)` instead of un-hiding `#welcome-not-built`;
   `welcome-not-now` also calls `window.AlvoraaCheckin.start(...)` but tells it not
   to jump straight into a punch (US-39's `home` screen, unchecked-in). The
   `#welcome-not-built` paragraph is removed from `index.html`.
3. **After a successful `agreeAndFinish()`**, alongside saving the secret, also save
   the origin (§4.1) and the notice snapshot (§4.4.1 below) needed for Settings'
   "What this app records" (AC-215), before showing `welcome`.

**A new tiny bootstrap** (inline `<script>` at the end of `index.html`'s body, after
every other script tag, or a 10-line `main.js` — I will use a small `main.js` to keep
`index.html` free of logic, matching the rest of the codebase's convention):

```
AlvoraaDeviceSecret.load().then(function (secret) {
  if (secret) { AlvoraaCheckin.start(); } else { AlvoraaJoin.start(); }
});
```

#### 4.4.1 `notice-cache.js` (new) — why it exists

AC-215 requires Settings to show the notice's six rows, version and agreed date
**from saved data, with no call.** The full row text is only ever sent to the phone
at E1 (`check_code`) and inside a `NOTICE_CHANGED` refusal's `values` — `field_status`
(E4) sends only `notice_version`, a bare string. So the only moment the app can ever
capture the words is right after E3 succeeds (or after E9 re-agrees to a changed
notice). `notice-cache.js` is a tiny pure module (`save`/`load`, `localStorage`-backed
— **not** Keystore, because this text is not secret and is the same text HR already
showed the person, per §2's privacy row) that `join.js` and `checkin.js` both call at
exactly those two moments.

### 4.5 ALV-43 — the notice text and `CONSENT_VERSION`, server side only

**Fix, in `field_app_notice.py`:** add a new entry, `"2026-09-22"`, identical to
`"2026-09-13"` except the first row's body gains the D19 sentence:

> "A photo of you, where you are, and the time — only when you press Check In or
> Check Out. When you set up: this phone's model name."

Set `CURRENT_VERSION = "2026-09-22"`. The old entry is **never edited** (the module's
own stated rule) — it stays in `NOTICE` exactly as it is.

**The web page is deliberately not touched** (§1). This means
`test_field_app_step1_013.py`'s `TheNoticeSaysWhatItSaid.test_013_the_web_page_and_the_store_say_the_same_thing`
— which asserts the page's static HTML contains the **current** version's exact
rows — would start failing for the wrong reason (it would look like the page
drifted, when really the store correctly moved on and the page correctly did not,
per AC-35). **My fix:** split that test's assumption instead of deleting its
protection —

- `TheNoticeSaysWhatItSaid` now pins `VERSION = "2026-09-22"` and the new `ROWS`
  against `notice.CURRENT_VERSION`, per the module's own rule ("the current
  version's exact words are pinned by a test").
- A renamed test, `test_013_the_web_page_still_shows_the_pre_review_wording`,
  asserts the **old** version's rows (`notice.NOTICE["2026-09-13"]["rows"]`, which
  never changes) still appear in `field-checkin.html` byte for byte — turning the
  old drift-guard into an explicit, honest record that the page is intentionally
  one version behind, with a comment naming AC-35 and pointing at "the page's own
  work" as the follow-up that closes it.
- A new assertion that `"2026-09-13"` is still in `notice.NOTICE`, unedited.

**What this means in practice, stated plainly:** after this fix, a **new** app phone
sees the corrected words at join. The **web check-in page** keeps showing the old
words (missing the phone-model-name line) until someone does the page's own
migration work to read `notice.facts()` instead of its own hardcoded copy — a real,
named, pre-existing gap (§0.2, `01b`'s own "bad news first" section), not one this
fix creates or is positioned to close. I recommend filing that page migration as its
own small follow-up rather than folding it into this change, since `AC-35` was a
deliberate boundary set at step 1 and I have no instruction here to move it.

### 4.6 `/enrol` — a new guest `www` page (S13)

Follows the exact pattern of `www/field_checkin.py` / `field-checkin.html`: a new
`alvoraa_portal/alvoraa_portal/www/enrol.py` (`get_context`, sets `no_cache`,
`no_header`, `no_sidebar`; per AC-123, sets the `noindex` meta/`X-Robots-Tag` and does
**no** database read — it is pure static content, no invite lookup at all, matching
AC-124's "no database read of invites" for `?t=`) and `www/enrol.html` — plain,
brand-neutral (no tenant branding call needed; the page never learns which tenant it
is, since it never reads the fragment or the query string), one small inline script
that only calls `history.replaceState` to clear `#t=…`/`?t=…` from the visible URL
without ever reading it, and the exact copy from AC-123. No outside URL (AC-125) —
same discipline as the mobile CSP, checked by hand since `check_app.mjs` does not
walk this directory (it is server-side, not part of the Capacitor bundle).

### 4.7 `checkin.js` — the screen flow itself (US-39/40/41/42 as one usable slice)

**Naming this plainly, since the task named only US-39/US-43 by number:** a check-in
screen cannot be a real thin vertical slice if it cannot show a single failure. E4
and E5 can answer with 17 of the 21 frozen codes (everything except the four
join-only `QR_*` codes). Building "the happy path only" would ship a button that
freezes or shows nothing useful the first time a phone is 200 m from its depot — not
a complete path from UI to database to notification for one role, which `CLAUDE.md`
asks for. So this build necessarily includes what the spec calls US-40 (problem
screens for the punch) and the **on-open gating** half of US-41 (`update`, `blocked`,
`replaced`, `left`, `appOff`/`notField` after joining) and US-42 (`noticeAgain`) —
not as scope creep, but as what "the Attendance screen" concretely means once it has
to survive contact with a real server answer. I am flagging this explicitly for your
sign-off rather than silently absorbing three more user-story numbers.

**What I will build:**
- **Boot:** secret found → call `fieldStatus`. Route on the answer: success → `home`;
  `APP_TOO_OLD` → `update` (button behaviour by build type, OPS-58: pilot → Firebase
  tester link, release → Play listing, debug → "Ask the developer" line — all
  built into the app, never server-sent); `DEVICE_BLOCKED`/`DEVICE_REPLACED`/
  `EMPLOYEE_NOT_ACTIVE`/`DEVICE_REMOVED`/`NOT_SET_UP`/`DEVICE_PENDING` → their named
  screen (the first four keep the secret and offer **Remove**; the last two clear
  local state and return to `first`); `APP_OFF_FOR_FIELD`/`NOT_FIELD_ROLE` → same
  screens as the join flow's dead-end pair but with a **Remove** button added (secret
  kept, AC-211); `NOTICE_CHANGED` → `noticeAgain` (six rows again, **Agree and
  continue** calls `acknowledgeNotice`, blocks `home` until it returns 200);
  `CONSENT_REQUIRED` → falls back to the generic `unknownCode` shape rather than a
  bespoke screen (§4.8 — this state is not reachable from any UI in this app, mine
  included, and was never taken to the design-check gate); `TOO_MANY_TRIES`/
  `SERVER_ERROR`/`NO_INTERNET` → their check-in-context screens with **Try again**
  re-calling `fieldStatus`.
- **`home` (AC-197):** top bar, status line (not-in / in-since / **checked out at**,
  fixing FC-1 in the app's own copy — the app was never built with the bug, so there
  is nothing to "fix," only to build correctly the first time), today's punch list,
  rule line, Check In/Check Out.
- **First-ever Check In → `locExplain` (AC-198)**, then `navigator.geolocation
  .getCurrentPosition({enableHighAccuracy:true, timeout: 20000})`; no fix within 20 s
  → client-made `LOCATION_OFF`; denied → client-made `LOCATION_DENIED`.
- **Punch (AC-199/200):** busy sequence, second `getUserMedia` capture (reusing the
  same pattern `join.js`'s scanner already proves works) through `photo.js`, camera
  denied/unavailable → proceed without a photo (`camOff`) rather than block the
  punch. One `punch` call; the answer's `todays_checkins` redraws `home` with no
  extra `fieldStatus` call (AC-199's own requirement).
- **Punch failures (US-40):** `LOCATION_MISSING` → `locOff`; `GPS_NOT_EXACT` →
  `gpsVague`; `OUTSIDE_WORKPLACE` → `outside`; `ALREADY_RECORDED` → `duplicate`;
  `TOO_MANY_TRIES`/`SERVER_ERROR`/`INVALID_REQUEST` → their screens; every one of
  these keeps the captured photo in memory for **Try again** (AC-205), never
  re-captures.

### 4.8 Settings (US-43) and the language gate (US-46/D15)

- **Settings screen** exactly per `01b` §7.13: You / Language / Privacy / This phone /
  About groups. "What this app records" (`records` screen) reads `notice-cache.js`
  (§4.4.1) — no call. Remove this phone calls `removeMyPhone`; on success, clears
  **both** device-secret keys (§4.1) and the notice cache, and returns to `first`
  with the one-line message; with no internet, keeps everything and shows the
  no-internet sentence (D10).
- **Language gate (AC-224):** the **Language** group is present in the DOM only when
  `window.AlvoraaBuildType.BUILD_TYPE === "debug"` — the same three-way distinction
  `host-check.js` already makes for allowing a `*.dev.alvoraa.co` host in pilot and
  debug but never release. Pilot and release never render the row at all (not just
  hidden by CSS — genuinely not in the DOM, so it cannot be reached by any input
  method, matching "cannot be reached" in the AC's own wording); Hindi strings stay
  in the string table (already true — they exist in the prototype's drafts) but the
  radio row that would switch to them is not built into pilot/release output. I am
  treating `debug` as the one build type that may show it, since that is the existing
  precedent in this codebase for "engineer-only, not tester-or-public-facing."

### 4.9 `versionCode`

Current: `versionCode 10002`, `versionName "0.1.0"`. This build changes what ships
(real Attendance and Settings screens, two new native-Keystore keys used, a new
guest server page). I will bump to **`versionCode 10003`**, `versionName` unchanged
at `"0.1.0"` (still pre-pilot; the existing three-bump history on this branch used
the same pattern — build number only, version name held until a real milestone).
`web/js/app-version.js`'s `APP_VERSION` stays in lock-step (`check_versions.mjs`
enforces this already).

---

## 5. What I could not verify, and will say again honestly in the implementation notes

- **No Android SDK, no bench, no device, no emulator in this sandbox** (task's own
  constraint, restated here so it is not lost between documents). Every claim about
  a real WebView's `getUserMedia`/`navigator.geolocation` behaviour, the Keystore
  round-trip for the new origin key, and the actual permission-dialog wording rests
  on the same two pieces of prior evidence the join flow already relied on: the
  09-install test page's proof that camera+GPS work in this WebView, and the secure
  storage plugin's own fail-closed unit tests. Neither is new evidence I can add from
  here.
- **Server-side ALV-43 fix**: `ast.parse`, `ruff` and the updated test module can be
  written and reasoned about, but not run against a database from here (no bench).
  Static-only, exactly as server step 4 was honest about at the time it was written.
- **`CONSENT_REQUIRED` remains unreachable from any UI in the whole app**, mine
  included — I am not building a bespoke screen for a state no gate has designed,
  per the still-open question the prior analysis raised (§4.7). If you want a real
  screen for it, that needs a trip through the UX design-check gate first, not an
  engineer's guess.

---

## Open questions / decisions needed before I write code

1. **Do you approve building US-40 and the on-open half of US-41/US-42 as part of
   "the Attendance screen,"** as argued in §4.7, rather than literally only US-39's
   happy path? I believe a check-in button that cannot express a single failure is
   not shippable, but this is more scope than the task's numbered list named, so I
   am asking rather than assuming.
2. **`checkin-screens.js` as a new sibling file, vs. extending `join-screens.js`
   with a context parameter** (§4.3) — I recommend the new file, given the parallel
   review is active on the shared one, but the context-aware extension is the more
   "correct" long-term shape if you would rather I make that call now.
3. **The tenant origin joining the device secret in Keystore storage** (§4.1) — I
   recommend this over any new plugin or `localStorage`; flagging it since it is a
   new field in an already-reviewed store, not because I see a real alternative.
4. **ALV-43's new `CONSENT_VERSION` value** — I propose `"2026-09-22"` (today) and
   the exact D19 sentence quoted in §4.5. Please confirm the wording and the date
   before I touch the notice module and its pin test.
5. **The web page staying one version behind** (§4.5) is a declared, not a hidden,
   gap — do you want it filed as a follow-up now, or left for whoever eventually
   does "the page's own work"? I am not doing that migration as part of this change.
6. **Language gate gated on `BUILD_TYPE === "debug"` only** (§4.8) — confirms pilot
   testers never see it, matching AC-224's "pilot and release" wording exactly.

**I have not opened any file for editing.** This document and the drift-check
reading above are the only outputs so far, per `CLAUDE.md` §2 and this role's boot
sequence. I am stopping here for your explicit approval before writing any code, per
"Always, after the impact analysis and strategy — before writing code."
