---
slice: 013-mobile-app
artifact: 05-review-daily-use
author: hrms-technofunctional-reviewer
date: 2026-09-22
scope: the daily-use client build (US-39-46: Attendance screen, punch, Settings,
  debug-only language gate, tenant-origin persistence) and the separate ALV-43
  server fix (stale consent notice). Commits 60892bd, 927b20e, 5e27e24 from
  branch slice/013-mobile-app-alv37, cherry-picked onto origin/dev@1c4e84c in
  this review's own worktree. The join flow (US-35-38) is NOT re-reviewed here -
  see docs/slices/013-mobile-app/05-review.md for that.
---

# 013 mobile app, daily use — techno-functional review

## Verdict: SHIP WITH FIXES

The core work is solid: the code→screen table is genuinely data-driven and
well tested, the tenant-origin fix closes a real "app forgets who it is after
a restart" gap, the ALV-43 notice-text change is exactly as careful as it
claims (I checked the old version's words are byte-for-byte untouched, and
the drift-guard test really does prove the web page still shows the old
wording, not just pass trivially), and the `/enrol` claim is true — it really
did already exist, unmodified. But I found two concrete bugs that were never
tested because they only show up when two files that were built and reviewed
separately share the same screen — exactly the seam a build like this is
most likely to miss. Neither is a security or data-loss problem. Fix both
before a pilot phone gets this build.

This is advice only. The user decides whether this ships.

## How this review was done

Fetched `origin/dev` fresh (`1c4e84c`), cut a new worktree
(`.claude/worktrees/review-013-daily-use`, branch
`review/013-mobile-app-daily-use`) and cherry-picked `60892bd`, `927b20e`,
`5e27e24` from `slice/013-mobile-app-alv37` — clean, no conflicts. Read every
changed file in full: `checkin.js`, `checkin-screens.js`, `notice-cache.js`,
`main.js`, the three-line diff to `join.js`, the extension to
`device-secret.js`, the four new functions in `api.js`, the `index.html`/CSS
additions, `field_app_notice.py`, and the updated
`test_field_app_step1_013.py`. Cross-checked every screen-selection claim
against the real server source it depends on — `field_app_errors.py`
(`CODES`), `field_checkin.py` (`field_status`, `field_checkin`,
`_device_from_token`, `_refuse_unless_notice_is_current`, `_REFUSAL_FOR_STATUS`),
`field_app_join.py` (`join_with_code`, `acknowledge_notice`,
`withdraw_agreement`), `field_app_device.py` (`remove_my_phone`), and
`field_app_desk.py`/`employee_field_app.js` for how HR already sees these
states on the desk. Read `01b-ux-design.md` §7.9-7.13, `01c-security-privacy-requirements.md`,
`02-functional-spec.md`'s AC-197-226 and its compliance section, `07-devops-inputs.md`,
the daily-use impact analysis and implementation notes, and the prior
join-flow review (`05-review.md`) as data. Ran `npm test` myself (96/96 pass —
saw it happen, did not take the count on trust), `node scripts/check_app.mjs`,
`node scripts/check_versions.mjs`, `python3 -c "import ast..."` on both changed
Python files, and `ruff check --config hrms/pyproject.toml` on both. Verified
by `git merge-base --is-ancestor` that `/enrol` (`a7cc42e`) really is already
on `origin/dev`, and by `grep` that the old notice version's exact sentence is
still in `www/field-checkin.html` and the new sentence is not.

## Majors

### M1 — A stale diagnostic card from checkin.js can bleed into a join.js problem screen

`mobile/field-app/web/js/join.js`'s `showProblem` (unchanged by this diff,
lines ~100-124) vs. `mobile/field-app/web/js/checkin.js`'s `renderCard`
(lines 109-124), sharing the new `#problem-card` element added to
`index.html`.

**Failure scenario, traced end to end:** a joined phone hits `TOO_MANY_TRIES`
or `SERVER_ERROR` while checking in — `checkin.js`'s `renderCard()` shows
`#problem-card` with text like "Your photo is kept." or "For HR ·
SERVER_ERROR · [timestamp] · [app version]". The person later has their phone
removed or blocked by HR, or presses "Remove this phone" — `checkin.js` calls
`forgetPhoneLocally()` then `window.AlvoraaJoin.start()`, which shows the
`first` screen. Neither of those steps touches `#problem-card`'s own `hidden`
attribute — I checked `join.js`'s `show()` and `checkin.js`'s `show()`: both
only toggle the `.screen` sections, never a child element inside one. The
person then scans a new QR that turns out expired or already used —
`join.js`'s own `showProblem()` runs (unchanged by this diff) and re-shows
the `problem` section, but it **never references `#problem-card` at all** — I
grepped the whole function. The old, now-wrong card text ("Your photo is
kept.", or a stale timestamp and app version under "For HR") is still sitting
there, visible, underneath the new heading and body, while the footer
correctly says "Code for HR: QR_EXPIRED". A support conversation now has two
different codes in front of it on one screen.

This is a genuine seam bug from splitting the screen tables into two files
(the right call, argued well in §4.3 of the impact analysis) without also
giving the two files shared ownership of the one DOM element they both now
write to. Not a security or data issue — the card only ever holds a code
name, a date and an app version, nothing personal — but it is a real,
reachable, confusing wrong-information bug, and it is exactly the class of
drift the task asked me to check for, just one layer below the code tables
themselves.

**Smallest fix:** `join.js`'s `showProblem()` should set
`el("problem-card").hidden = true` (and clear its children) at the top,
the same one line `checkin.js`'s `renderCard()` already does for the "no
card" case — or better, both files call one small shared `renderCard`
helper. Either way, add a test (can be a small DOM-less contract test, or
flagged for the on-device pass) asserting a card left visible by one flow is
gone by the time the other flow's `showProblem` runs.

### M2 — The on-open gating does not recover a phone stuck in "Consent not given", contradicting HR's own existing message about it

`mobile/field-app/web/js/checkin-screens.js`'s `screenFor` (deliberately,
per its own comment at lines 309-317) has no entry for `CONSENT_REQUIRED`,
and `checkin.js`'s `handleGateRefusal` does not special-case it either — both
fall through to the generic `unknownCode` screen ("Something went wrong...
Check for an update, then try again.").

I traced whether that is really safe. `field_checkin.py`'s
`_device_from_token(token)` — called by both `field_status` (E4) and
`field_checkin` (E5), the two calls this build newly wires up — refuses with
`CONSENT_REQUIRED` for any device whose status is `"Consent not given"`
(`_REFUSAL_FOR_STATUS`, line 272). That status is real and already visible on
the HR desk today: `field_app_desk.py` has a `not_agreed` state, an orange
"Not agreed yet" pill, and its own filter logic; `employee_field_app.js:214`
already tells an HR user, in words already shipped: *"...has not agreed to
the notice yet. **The app asks again each time it opens**; the phone cannot
check in until then."* That sentence describes exactly what `NOTICE_CHANGED`
does — and `field_app_join.py`'s `acknowledge_notice` (E9) docstring
confirms it: *"reading the notice again is how a phone in that state becomes
Active"*, with "no new code from HR needed."

This build's `checkin.js` never calls that recovery path for
`CONSENT_REQUIRED` — a phone in this state would see "Something went wrong...
check for an update", tap "Check for an update" or "Try again" (both just
reload status, per `PROBLEM_ACTIONS.unknownCode`), and loop forever on a
message that is actively wrong about what's needed, with no way to reach the
already-built fix.

**Why this doesn't block today, and why it still matters:** I confirmed
`"Consent not given"` currently has exactly two writers — `join_with_code`
with `agreed=0` (never sent by this app; `api.js`'s `joinWithCode` hardcodes
`agreed: 1`, and the web page's own registration path refuses outright at
`consent=0` rather than creating this state) and `withdraw_agreement` (a
real, live, whitelisted E-endpoint from an earlier slice, but nothing in
this app's UI calls it — Settings' Privacy group only has "What this app
records"). So no real phone can reach this state through anything shipped
today. But the moment anyone wires up "withdraw consent" — which
`01c-security-privacy-requirements.md` (§ "Withdrawal") and its own C-2
decision point already anticipate as a near-term, DPDP-driven requirement —
every phone that uses it hits this exact dead end. This is worth fixing now,
while the file is open, rather than rediscovering it as a live incident
later.

**Smallest fix:** treat `CONSENT_REQUIRED` the same way `NOTICE_CHANGED` is
already treated in `handleGateRefusal` — render the six-row notice-again
screen and call `acknowledgeNotice` on agreement. The `values` shape differs
(`CONSENT_REQUIRED` only carries `version`, not the full `rows`/`what_changed`
`NOTICE_CHANGED` carries — checked against `field_app_errors.CODES`), so this
needs one extra call to fetch the full text (or a small server-side change to
include `rows` on this refusal too) rather than a one-line reroute. Worth a
design-gate pass rather than a silent client fix, since `01b` never specified
this screen either — flagging it for that gate is a legitimate outcome too,
as long as it's flagged, not silently left as `unknownCode` forever.

## Minors

### N1 — `TOO_MANY_TRIES`'s card says "Your photo is kept" even when no photo was ever taken

`mobile/field-app/web/js/checkin-screens.js:227-238`

`TOO_MANY_TRIES` can come from `field_status` (E4, a plain status check, no
photo involved) as well as from a punch (E5). The card note is hardcoded to
"Your photo is kept." regardless of which call triggered it. If a phone hits
the 60/hour status-check rate limit — plausible if something loops on
`loadStatus()` — the person sees a claim about a photo that was never taken.
Low frequency, not misleading in a harmful direction (it doesn't cause a
wrong action), but it is the same class of context-blindness the file's own
design rationale (§4.3 of the impact analysis) says it exists to avoid.
**Smallest fix:** only set the card when `opts` indicates a punch was in
flight, or drop the note for this code and let `checkin.js` add it only when
retrying an actual punch.

### N2 — `main.js` and `checkin.js`'s own `start()` each load the device secret independently

`mobile/field-app/web/js/main.js` and `checkin.js:197-214`

`main.js` calls `AlvoraaDeviceSecret.load()` to decide which flow to start,
then `checkin.js`'s `start()` calls `Promise.all([load(), loadOrigin()])`
again. Harmless (Keystore reads are cheap, not on a hot path), but it means
the secret-vs-origin half-set check that actually matters
(`if (!state.secret || !state.origin)`) only really lives in one place by
accident of load order, not by design. Worth collapsing into one load if
this file is touched again — not worth its own change now.

### N3 — A half-written join (secret saved, origin save fails) leaves an inert secret behind until the next successful join overwrites it

`mobile/field-app/web/js/join.js`'s `agreeAndFinish` (diff hunk)

The write order is secret → origin → notice cache, each chained with
`.then()`, and the whole chain's `.catch()` shows `SERVER_ERROR` but does not
roll back the secret if `saveOrigin` or the notice-cache write fails after
the secret already saved. I traced whether this is exploitable or leaves a
stuck phone: it does not — `checkin.js`'s own `start()` refuses to proceed
with a secret and no origin, and always redirects back to `AlvoraaJoin.start()`
without touching the secret, so the same `KEY` gets overwritten cleanly by
the next successful join. Purely a "slightly untidy intermediate state," not
a bug with an effect. No action needed, noting it because I traced it and
want the trace on record rather than silently passing over a partial write.

## AC verification table

| AC | Met | Evidence |
|---|---|---|
| AC-197 (home: top bar, status, punch list, rule line, checked-out-at fix) | Met | `renderHome()`; the FC-1 "checked out at" fix is correct by construction, not patched |
| AC-198 (locExplain, first check-in only) | Met | `hasSeenLocationExplain()`/`markLocationExplainSeen()`, fail-soft `localStorage` flag |
| AC-199 (busy sequence, one punch call, no extra fieldStatus) | Met | `doPunch()`; `showResult()` renders from the punch's own answer |
| AC-200 (camera denied/unavailable still saves) | Met | `capturePunchPhoto()`'s `.catch()` resolves `null`, punch proceeds |
| AC-201 (photo shrink) | Met (unchanged) | `photo.js` reused, its own tests still pass |
| AC-202/203 (version header, 30s timeout) | Met | `api.js`'s existing `callMethod`, untouched |
| AC-204 (mock-location flag) | **Not met, declared** | Always sends `mock_location: 0`; honestly flagged as a scope decision needing a plugin, in both the notes and a code comment |
| AC-205 (photo kept across Try again) | Met | `state.photoDataUrl` only cleared in `resetPunchState()`, called on success only |
| AC-206-208 (SERVER_ERROR card, OUTSIDE_WORKPLACE no-distance fallback) | Met | Proven in `checkin-screens.test.js`, matches server's two OUTSIDE_WORKPLACE sentences exactly |
| AC-209 (update screen, one button by build type) | Partial, declared | Screen and card correct; the one OPS-58 button is plain text instead, because `check_app.mjs`'s own outside-URL rule correctly has no real URL to embed yet — a real gap, not a workaround of the guardrail |
| AC-210 (blocked/replaced/left: local-only Remove, no server call) | Met | `localRemoveFromGate()` — confirm, then `forgetPhoneLocally()`, no `removeMyPhone` call |
| AC-211 (appOff/notField: secret kept, Remove routes through E6) | Met | `openLeaveConfirm("gate")` → `doRemove()` → real `removeMyPhone` call, matches `_refuse_unless_app_phone_is_eligible` still treating the device as Active underneath |
| AC-212 (NOT_SET_UP/DEVICE_PENDING/DEVICE_REMOVED clear and return to first) | Met | `handleGateRefusal`'s first branch |
| AC-213 (NOTICE_CHANGED → noticeAgain → E9 → home) | Met | `renderNoticeAgain`/`agreeToNoticeAgain`; blocks home until E9 resolves `ok` |
| AC-214 (Settings groups) | Met | `renderSettings()` matches `01b` §7.13 groups, no "Sign out" |
| AC-215 (What this app records, no call) | Met | `renderRecords()` reads `notice-cache.js` only; falls back to a plain sentence when the cache is empty, exactly as declared |
| AC-216 (Remove: E6, clears both keys + notice cache, no-internet keeps everything) | Met | `doRemove()`; `NO_INTERNET` branch leaves state untouched and shows the exact 01b sentence |
| AC-224 (Language row absent from DOM outside debug) | Met | `renderSettings()`'s `if (buildType === "debug")` gate; the group `<div>` exists but stays empty (no row appended) outside debug — satisfies "cannot be reached by any input method" |
| AC-226 (string-table lint rule) | **Not met, declared** | No string table exists yet for either flow; same state the join flow already shipped in |
| CONSENT_REQUIRED handling (no AC number, but implied by "every code lands on a named screen or an honest fallback") | **Not met** | See M2 — falls to `unknownCode`, which is honest about being a fallback but does not recover a real, desk-visible device state that already has a working fix server-side |

## NFR verification table

| Dimension | Impact analysis said | What the code does | Verdict |
|---|---|---|---|
| Performance | Neutral — one `fieldStatus` on open, one `punch` per tap, no polling | Confirmed: no `setInterval`/polling anywhere in `checkin.js`; `renderHome` never re-calls `fieldStatus` after a punch | Pass, as predicted |
| Security | Neutral, one named gap (mock-location) | Confirmed: same fail-closed `nativePlugin()` gate reused for the origin key; every server value rendered with `textContent` (checked `checkin.js` end to end, no `innerHTML`); `mock_location` gap is real and declared, not hidden | Pass, with the declared gap |
| Reliability | "This is most of the new work" — 21 codes on a named screen or an honest fallback | Mostly true — 20 of the codes device endpoints can send are correctly handled; `CONSENT_REQUIRED` (M2) and the two files' shared DOM state (M1) are the two gaps the claim missed | Partial — see M1/M2 |
| Scalability | Neutral | Confirmed: no new background work, server-side per-phone limits unchanged | Pass, as predicted |
| Maintainability | "One new pure, tested table rather than a bigger edit to a file under review" | The table itself is clean and well tested; the trade-off's blind spot (two files sharing one DOM element with no shared owner) is exactly M1 | Pass on the table, gap on the DOM seam it didn't anticipate |
| Data integrity | "The secret and the tenant origin are now written and cleared together, always" | Confirmed in both directions: `device-secret.js`'s `clear()` removes both keys unconditionally (adversarial test present); write order is secret→origin→notice, and a partial failure (N3) self-heals on the next join rather than corrupting state | Pass, as claimed |
| Compliance / privacy | "ALV-43 closes the phone-model disclosure gap for new joins; the web page's own gap is named, not hidden" | Verified directly: old notice version's text is byte-for-byte untouched (diffed), the new sentence exists only in the new version, and `www/field-checkin.html` genuinely still lacks it (grepped). The updated drift-guard test asserts the new sentence is *absent* from the page, not just that old text is present — a real, non-trivial check | Pass, exactly as claimed |

## Compliance verification

`01c-security-privacy-requirements.md` is this slice's compliance-impact
input; I traced the items this build actually touches:

| Obligation | Mechanism in the diff | Test | Verdict |
|---|---|---|---|
| PRIV-2 / D19 (disclose phone-model collection before any pilot user agrees to the old words) | New `"2026-09-22"` notice version in `field_app_notice.py`, `CURRENT_VERSION` moved | `test_013_the_current_notice_reads_exactly_this` (pins new text); confirmed by reading the file that the old entry is untouched | **Discharged** |
| "A published version is never edited" (the module's own rule) | Old `"2026-09-13"` entry left byte-for-byte identical | `test_013_a_published_version_is_never_edited` now also asserts the old rows equal `OLD_ROWS` | **Discharged** |
| AC-35 (the web check-in page is not touched by this slice) | No edit to `www/field-checkin.html` in this diff | `test_013_the_web_page_still_shows_the_pre_review_wording` — I independently grepped the page and confirmed it, not just trusted the test | **Discharged**, with the named follow-up gap (page migration) correctly left open, not hidden |
| PRIV-1/PRIV-7 (only model name/platform/app version; no image file ever written to disk) | Photo captured to an in-memory `dataUrl`, never a file; `capturePunchPhoto()` uses `canvas`, not `navigator.mediaDevices` file capture | Unrun without a device (declared) — code path itself has no file-write call | **Partial** — mechanism present, unproven without a phone, honestly declared |
| SEC-21 (mock-location flag) | Not implemented — always `0` | N/A | **Not discharged**, declared as a decision needed, not hidden |
| "Withdrawing consent must be as easy as giving it," a separate choice from Remove this phone (01c "Withdrawal" section) | Not built in this diff | N/A | **Correctly out of scope** — `02-functional-spec.md`'s own C-2 decision explicitly defers this to before the first paying customer, named and dated, not this build's ACs. Noting only because it makes `withdraw_agreement` (a live, whitelisted endpoint) currently unreachable by any client — see M2's connection to it |
| SEC-17/MA-30 (server text never as HTML, screen picked by code alone) | `checkin.js` uses `textContent` throughout; `screenFor` keys only on `code` | `checkin-screens.test.js`'s injection test (hostile `site` string stays literal) | **Discharged** |

## What to delete

Nothing built here is unnecessary. The scope discipline is good — no
speculative abstraction, no new dependency, no settings feature beyond what
US-43 asked for, and the language gate is honestly labelled a scaffold
rather than dressed up as a real feature.

## What was done well

- **Verifying a claim before trusting it.** "The `/enrol` page already
  exists" could have been taken on faith from the impact analysis; instead
  the implementation notes say the engineer ran `git ls-tree` to check, and I
  independently confirmed with `git merge-base --is-ancestor` that `a7cc42e`
  really is already on `origin/dev`. This is the right instinct, applied
  correctly.
- **The drift-guard test for ALV-43 is a real test, not a rename.** It
  doesn't just check the old words are present — it explicitly asserts the
  new sentence is **absent** from the web page, which is the only way a test
  like this can fail if someone edits the page carelessly at the exact wrong
  moment. I checked the page directly and the assertion is genuinely true
  today, not a coincidence.
- **The mock-location gap and the OPS-58 button gap are declared where a
  reader will actually find them** — in the code comment at the exact line
  that matters, not only in a document three files away. `check_app.mjs`
  correctly refused a placeholder store URL, and rather than working around
  that guardrail the engineer removed the broken feature and said so — the
  right response to a control doing its job.
- **`clear()`'s "never one key without the other" design is proven
  adversarially**, not just asserted: the test constructs a store with only
  one of the two keys present and checks `clear()` still behaves correctly —
  the right kind of test for a control whose whole job is "never partially."

## Confidence

High on everything read and run from source: the screen-selection logic, the
device-secret extension, the ALV-43 text change and its test, the `/enrol`
claim, and the two seam bugs (M1, M2) — both traced to specific lines in both
the client and the server, not inferred from documentation.

Low, and not claimed otherwise by the build itself, on anything needing a
real phone: the Keystore round-trip for the new origin key, camera/geolocation
timing, and whether `#problem-card`'s stale-content bug (M1) is exactly as
visually jarring on a real WebView as the DOM trace suggests — the trace says
it will show, but only a device confirms how it looks. If the user wants M1
and M2 fixed and re-verified before a pilot build, that's a small, targeted
re-review, not a full one.

## Worktree / commit

Branch `review/013-mobile-app-daily-use`, worktree
`.claude/worktrees/review-013-daily-use`, cut from `origin/dev@1c4e84c`. This
review document is committed on top of the three cherry-picked commits.
