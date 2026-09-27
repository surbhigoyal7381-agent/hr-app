---
slice: 013-mobile-app
artifact: 05-review
author: hrms-technofunctional-reviewer
date: 2026-09-22
scope: mobile/field-app app-client only — stage 1 (a473e22, already reviewed once,
  its one finding fixed in 0233063 — not re-litigated here), the stage-2 spike
  (debe06b), and US-35–38, the real join screens (b6021ad, never reviewed before
  this report)
---

# 013 mobile app — techno-functional review (app client)

## Verdict: SHIP WITH FIXES

The join flow is well built and the parts that can be proven without a phone are
genuinely proven — 63 real tests, read line by line, not just counted. But two
concrete, user-facing wording bugs made it to `dev` because nothing checked the
copy against its source of truth, and one of them actively misleads a rate-limited
worker about how long to wait. Neither is a security or data problem, and neither
should block starting device testing — but neither should reach a pilot phone
either. Fix both, add one drift test, and this is ready to present for a pilot
build.

This is advice only. The user decides whether this ships.

## How this review was done

Read every changed file in full in a fresh worktree of `origin/dev`
(`.claude/worktrees/review-013-alv39`, branch `review/013-alv39`): `api.js`,
`join-screens.js`, `join.js`, `device-secret.js`, `build-type.js`, `qr-decode.js`,
`host-check.js`, `app-version.js`, `index.html`, all five test files that cover
them, and the vendored files' hashes. Cross-checked every claim against the real
server code it depends on: `field_app_errors.py`, `field_app_join.py`,
`field_checkin.py`, `field_app_limits.py`, `field_app_notice.py`,
`field_app_settings.py` — not just the app's own comments about what the server
does. Ran `npm test`, `npm run check` and `python3 scripts/check_tracked_keys.py`
myself; results are in `04-test-report.md`. Read `01-product-brief.md`,
`01b-ux-design.md` (§7, §7.12, §8, D1–D20), `01c-security-privacy-requirements.md`,
`00-impact-analysis-app-client.md`, and `03-implementation-notes.md` §7–8 in full.

## Blockers

None.

## Majors

### M1 — The rate-limit screen tells a driver the wrong wait, every time

`mobile/field-app/web/js/join-screens.js:174-183` (`TOO_MANY_TRIES`)

The screen says: *"This phone tried many times in a short time. Wait one minute,
then press Try again."* The server's real rate-limit window
(`field_app_limits.py:34`, `WINDOW_SECONDS = 60 * 60`) is **one hour**, not one
minute, and the refusal already carries the real number of seconds left
(`field_app_errors.py:73`, `"retry_after_s"`; computed from the actual Redis TTL in
`field_app_limits.py:76-83`). `join-screens.js`'s `TOO_MANY_TRIES` builder takes no
`values` argument at all — `function () { return {...} }` — so `retry_after_s` is
silently thrown away. `01b-ux-design.md` line 426 itself lists `retry_after_s` as a
value the app is meant to use ("Yes"), so this is a real gap between the approved
contract and what shipped, not a matter of taste.

**Failure scenario:** a worker mistypes or re-scans a stale code enough times to
hit the 5-per-hour limit on `join_with_code`. They see "wait one minute," wait a
minute, press Try again, get refused again — because the real wait can be up to 59
more minutes. They have no way to know this isn't a broken app, and the one
number that would tell them (`retry_after_s`) was sent by the server and dropped
on the floor by the client. This directly undercuts the brief's "join in under two
minutes, no HR wait" promise for exactly the person who has just failed to join.

**Smallest fix:** read `v.retry_after_s` in the `TOO_MANY_TRIES` builder and word
it approximately, the same way `QR_EXPIRED`/`QR_USED` already turn a raw
timestamp into words (e.g. "Wait about a minute" under 90 s, "Wait about {N}
minutes" above that) — reuse the existing values-to-words pattern in this same
file rather than inventing a new one. Add a test asserting the wording changes
with `retry_after_s`, the way `QR_USED`'s today/date branch already has one.

## Minors

### N1 — `FEATURE_OFF`'s wording does not match the page it says it was carried over from

`mobile/field-app/web/js/join-screens.js:140-152`

The code's own comment says the wording is *"carried over from the 008 web
check-in page … confirm byte-for-byte against that page before this ships past a
debug build."* It was not confirmed, and it does not match. The real 008 page
(`alvoraa_portal/alvoraa_portal/www/field-checkin.html:1038-1041`) says: *"Field
check-in is not part of your company's plan yet. Please tell HR."* The app says:
*"Ask HR about the Alvoraa app for your company."* The heading matches exactly;
the body does not. Not a security issue, and low-frequency (a plan being off is
rare), but it means the same refusal reads differently depending on which of the
two surfaces a person sees it on, which is exactly the inconsistency the
engineer's own comment flagged as a risk and then didn't check.

**Smallest fix:** copy the exact 008 body sentence into `join-screens.js`'s
`FEATURE_OFF` entry, and delete the "confirm before shipping" comment once it's
actually confirmed. Two-line change.

### N2 — No automated drift check between the server's code table and the app's screen table

`alvoraa_portal/alvoraa_portal/field_app_errors.py` (`CODES`) vs.
`mobile/field-app/web/js/join-screens.js` (`SCREENS`)

I checked this by hand for this review (see AC table below) and found no gaps —
every code `check_code`/`refuse_code`/`join_with_code` can actually raise has a
named screen, and `UNKNOWN_SCREEN` means a future code the app doesn't know about
still gets a real screen, never a blank one. But nothing in CI re-checks this the
way the server's own tests walk `CODES` and fail if a code loses its status or
gains an unlisted value (`field_app_errors.py:33-35`). The two M1/N1 findings
above are exactly the kind of drift that a one-off manual check like this one
will not always catch a second time.

**Smallest fix:** a small Node test that imports `join-screens.js` and asserts,
for the fixed list of codes E1/E2/E3 can send (documented already in
`field_app_errors.py`'s own comments), that `screenFor` returns something other
than the `unknownCode` fallback for each — cheap, and it would have caught
neither M1 nor N1 (those are wording bugs, not missing-row bugs), but it closes
the "a code silently falls through to the generic screen" class of regression
this file is explicitly designed to prevent.

### N3 — The debug/pilot Content-Security-Policy has no per-build-type override, unlike everything else in this build

`mobile/field-app/web/index.html:12-13`

Every other build-type-dependent fact in this app (network cleartext rules,
`BUILD_TYPE` itself) has a debug/pilot override under
`android/app/src/{debug,pilot}/...`, following the pattern the README and
`build-type.js` describe. `index.html`'s CSP `connect-src https://*.alvoraa.co`
has no such override, and the file itself says the debug build "adds its local
address at build time, never in this file" — but no mechanism that does that
addition exists yet anywhere in this codebase. I could not confirm from source
whether a browser's CSP wildcard-host match actually extends to the two-label
`*.dev.alvoraa.co` hosts `host-check.js` already allows in debug/pilot builds
(this needs a real WebView to settle, not a read of the spec). If it doesn't
match, the practical effect is not a security hole — a blocked `fetch` becomes a
rejected promise, which `api.js` already turns into `NO_INTERNET` (fails safe,
not open) — but it would make every debug/pilot join against a `dev.alvoraa.co`
tenant look like "no internet" with no way to tell that's what happened. Worth
settling on the very first real-device pilot/debug build, before concluding a
join failure is something else.

## AC verification table (US-35–38, this build's scope)

| AC | Met | Evidence |
|---|---|---|
| AC-181–190 (join flow screens, first→welcome) | Met | `index.html`/`join.js` screens match `01b` §7.1–7.8 wording word for word (checked side by side); `03-implementation-notes.md` §8.4 honestly lists the two declared exceptions (no Hindi, no Check In screen) |
| AC-192 (dead-code screens: heading/body/steps/values/no-Try-again/footer) | Met | `join-screens.test.js` proves the two date-shaped bodies and the footer code; verified by hand against `01b` §7.12's exact text for `qrExpired`/`qrUsed`/`qrCancelled` |
| AC-193 (`QR_NOT_RECOGNISED` exact drafted copy) | Met | `join-screens.js`'s `QR_NOT_RECOGNISED` entry matches AC-193's drafted text exactly, including reusing the `qrExpired` screen shape as AC-193 itself specifies |
| AC-194 (`camDenied` buttons act) | Partial | "Choose a picture instead" works (file picker, proven). "Open phone settings" does not open settings — re-attempts the camera prompt instead. **Declared** in `03-implementation-notes.md` §8.3 point 5 as a known simplification (no vetted plugin yet), not a silent gap |
| AC-195 (This is not me → E2 → cancelled screen) | Met | `join.js:refuseCode`; matches `01b` §7.6 wording exactly; server-side `refuse_code` behaviour checked directly in `field_app_join.py:256-268` |
| AC-196 (no internet on Cancel this code) | Met | `refuseCode()`'s `result.code === "NO_INTERNET"` branch |
| AC-203 (version header, 30 s timeout, manual retry only) | Met | `api.js:27,68-79`; no automatic retry anywhere in `join.js` |
| AC-217/AC-218 (secret in secure storage only; join-flow state memory-only, never on disk) | Met | `device-secret.js`'s native-platform gate, proven adversarially in `device-secret.test.js`; `join.js`'s `state` object is a plain in-memory variable with no `localStorage`/`Preferences` write anywhere in the file (grepped) |
| MA-30 (screen picked from `code` alone, never English text) | Met | `api.js` never reads `body.message` for a refusal; `join-screens.js` keys only on `code` |
| SEC-17/US-45 (server text never as HTML) | Met | `check_app.mjs`'s `HTML_SINK` rule stayed green (confirmed: `grep` found no `innerHTML`/`insertAdjacentHTML`/`document.write` in any of the changed files, only comments referencing the rule) |

## NFR verification table

| Dimension | Impact analysis said (`00-impact-analysis-app-client.md` §2) | What the code actually does | Verdict |
|---|---|---|---|
| Performance | Neutral, contingent on version header + 30 s timeout + manual-only retry, package ≤ 10 MB | All three held: `api.js` sends the header and times out at 30 s; `join.js` never auto-retries; `npm run check`'s bundle/dependency checks stayed green through three new dependencies (jsQR, Capacitor core, the storage plugin) | Pass, as predicted |
| Security | "The two decisions still open are how the app reads a QR code and where it stores the secret" | Both landed exactly where the spike said they should: jsQR read as pure pixels (no new permission), secret gated on a real native-platform check that is proven to fail closed against the plugin's own unencrypted web fallback | Pass, as predicted |
| Reliability | Recommended one data-driven code→screen table with a hard `unknownCode` default | Built exactly as recommended (`join-screens.js`); verified by hand it covers every code E1/E2/E3 can actually raise (see N2 for the gap: no automated check that this stays true) | Pass, with the gap noted in N2 |
| Scalability | "The client's only obligation is not to work against" the server's existing per-device limits — no auto-polling, no retry storms | Held: no polling anywhere in this build, no auto-retry | Pass, as predicted |
| Maintainability | Recommended small, pure, Node-testable modules, not one large `app.js` | Followed precisely: `api.js`, `join-screens.js`, `device-secret.js`, `build-type.js`, `qr-decode.js` are all pure and DOM-free; `join.js` is the one DOM-driven file and stays a thin dispatcher | Pass, as predicted |
| Data integrity | "The secret must be written synchronously, after the server confirms... never before" | `join.js:agreeAndFinish` calls `device-secret.js.save()` only after `joinWithCode` resolves `ok`, and only shows `welcome` after `save()` itself resolves; a save failure shows `SERVER_ERROR` instead of a false `welcome` | Pass, exactly as specified |
| Compliance / privacy | PRIV-4: no app-facing string may say "consent"; PRIV-1: only model name/platform/app version ever sent | Grepped: no user-visible "consent" text anywhere in the built screens. `device_label` is currently sent as `""` (real value deferred to a declared future story), so nothing beyond `platform`/app version is sent yet | Pass today; watch when `device_label` is wired to a real value (see security note below) |

## Compliance verification

No dedicated compliance-impact sub-analysis exists as a separate section in this
slice's spec beyond `01c-security-privacy-requirements.md`'s SEC/PRIV items, which
this review traced individually above (SEC-17, PRIV-1, PRIV-4, PRIV-7, SEC-14).
Each is discharged by a mechanism I read and, where testable without a phone,
saw proven by a test — not by a comment asserting it. I did not find an item in
`01c` that applies to this build's scope (E1/E2/E3, the join screens) and is
undischarged.

## What to delete

Nothing. This build is notably restrained: no speculative abstraction, no new
dependency beyond the two the spike justified, no settings screen or feature not
asked for. The one piece of dead-looking code —
`join.js:358-361`'s `"scan-pressed": openScanner` entry in the `ACTIONS` table,
immediately overwritten at line 399 by `"scan-pressed": function () { show
("camExplain"); }` — is confusing to read (declare it once, then overwrite it 40
lines later, unconditionally) but is not a functional bug: the click handler
reads `ACTIONS` fresh on every click, so the final assignment always wins. Worth
a one-line comment explaining why it's written this way, or simply deleting the
first assignment, next time this file is touched — not worth a change on its own.

## What was done well

- **Verifying the wire contract against the real server file, not the spec's
  paraphrase of it.** `api.js`'s header comment cites `field_app_errors.py` by
  name and by the actual mechanism (`_private_request`), and the code matches
  what that file actually does — not just what the functional spec says it
  should do. This is the difference between a client that works today and one
  that also survives the next small server refactor.
- **The device-secret safety check is proven adversarially, not just written.**
  `device-secret.test.js` doesn't just test the happy path — it constructs a fake
  Capacitor object shaped exactly like the plugin's own known-unsafe web
  fallback and proves the code refuses it. That is a materially stronger test
  than "does save() work," and it is the right test for a control the spike
  itself flagged as the one thing most likely to be silently bypassed.
- **Honesty about the boundary of what a sandbox without an Android SDK can
  prove.** `03-implementation-notes.md` §8.3 ranks the unproven risks by how much
  the build depends on each, states the exact console-error symptom to look for
  if the riskiest one is wrong, and does not pad the "proven" list with
  device-only claims. That made this review faster and more accurate, because
  I could trust the boundary the engineer drew rather than needing to
  re-derive it.
- **Declaring a scope decision as a decision, not hiding it as an oversight** —
  e.g. `join-screens.js`'s `APP_TOO_OLD` entry ships an empty `buttons: []` with
  a comment naming exactly which future story (US-41) owns the real button,
  rather than a silent no-op or a button that does nothing.

## On the 7-day single-use QR / no-HR-approval design decision

The task asked me to flag whether I can assess this, or whether it needs the
security-privacy-engineer specifically. **This needs the security-privacy
reviewer, not this review** — it is a business-risk/threat-model judgement (is a
QR that anyone who intercepts it can use, for up to its lifetime, before a human
at HR ever looks at it, an acceptable trade against "join in under two minutes
with no HR wait"), not a code-correctness question. What I can and did verify
from the code, which the security review may find useful as inputs rather than
conclusions:

- The code itself is genuinely single-use and locked (`field_app_join.py`'s
  fixed lock order, re-read-after-lock pattern, verified by reading the
  server's own concurrency test description) — the *mechanism* behind "single
  use" holds up under two simultaneous joins.
- The 43-character code lives only in the URL fragment, never the query string
  (so it never reaches an access log — `host-check.js:69`, `field_app_join.py`
  comments), and the app never stores it outside memory (`join.js`'s `state`
  object).
- **What the security reviewer should specifically look at, that I found while
  reading but is outside a techno-functional review's remit:** the notice a
  worker agrees to (`field_app_notice.py`, `CURRENT_VERSION = "2026-09-13"`)
  still does not disclose that the app collects the phone's model name at join
  — `01b-ux-design.md` D19 explicitly instructed this be fixed before any pilot
  user agrees, and `00-impact-analysis-app-client.md` §0.3 already flagged that
  the instruction was not carried out. This build doesn't make that worse (it
  currently sends an empty string for `device_label`, not a real value — see
  the NFR table above), but the notice text gap is real, already-flagged, and
  still open on `dev` today. Also worth the security reviewer's eyes: the
  server-side `CONSENT_REQUIRED` / `"Consent not given"` state exists
  (`field_checkin.py:272`, `field_app_join.py`'s `agreed=0` path) but was never
  in the approved `01b` design or `02` spec — I confirmed by reading
  `check_code`/`refuse_code`/`join_with_code` line by line that this build's
  three endpoints cannot reach that state (none of them call
  `_device_from_token` or `register_device`, the only two functions that raise
  it), so it is genuinely inert *today*. But it is live, reachable code on the
  server (`withdraw_agreement`, `acknowledge_notice`) that was never through
  the design or security-requirements process this repo's own `change-process.md`
  requires. That gap is `00-impact-analysis-app-client.md`'s own §0.2 finding,
  not mine — I'm re-surfacing it here because it's exactly the kind of thing a
  security review of this slice should not skip past.

## Confidence

High on everything I could read and run: the wire contract, the screen-selection
table, the device-secret safety logic, and the test suite's actual assertions —
all checked against the real server source, not the spec's description of it,
and all backed by a test run I executed myself (63/63 pass, `04-test-report.md`).

Low, and explicitly not claimed, on anything that needs a real phone: the
Capacitor bridge wiring, the Keystore round-trip, camera-frame scan timing, and
the CSP wildcard-host question in N3. These are not gaps in this review; they are
gaps that no review without a device can close, and `03-implementation-notes.md`
§8.3 already says so plainly. If the user wants those specifically re-verified,
that needs the engineer's own on-device pilot build (already declared as running
in parallel), not another read of the source.

I could not assess the 7-day-QR/no-HR-approval business decision itself — that is
a judgement call for the security-privacy-engineer, not something a code review
can settle either way.
