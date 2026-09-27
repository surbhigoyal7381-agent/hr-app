---
slice: 013-mobile-app
artifact: 06-security-review
author: hrms-security-privacy-engineer
date: 2026-09-22
status: review complete for ALV-39. I recommend; the user decides whether this goes to pilot.
inputs: [01-product-brief.md, 01b-ux-design.md, 01c-security-privacy-requirements.md, 00-impact-analysis-app-client.md, 04-impact-analysis-server.md, 03-implementation-notes-server-step1..5.md, 03-implementation-notes.md §7-8, code on origin/dev @ 1c4e84c (includes b6021ad)]
---

# 013 — Security review of the QR join flow (ALV-39)

**I recommend. You decide.** I am not a lawyer. Nothing here was run against a real
phone — I read code, ran the app's own JS test suite (63 tests, all pass) and its
static checks, and read the server's own test files, but did not touch the bench, a
device, or production. Where I say something is "proven", I mean proven by a test I
can see; where I say "not proven", I mean nobody has, not that it is wrong.

## The short answer

**Correcting the premise first, in plain words:** it is not true that no security
review happened before the code was written. `01c-security-privacy-requirements.md`
(17 Sep) did exactly what the brief asked for — it challenged the 7-day QR, set 25
security requirements and 15 privacy requirements, and got the user to accept 24
hours as the default lifetime instead of 7 days. What is true, and is the real gap
this review closes, is that **nobody had checked whether the code that got built —
especially the app-client code merged in `b6021ad` — actually does what `01c`
required.** That check is what follows.

**My verdict on the design:** the QR-with-no-approval design, as specified in `01c`
and as actually built, **is defensible for a controlled pilot with Alvoraa's own test
staff.** I checked the code, not just the documents, and the controls `01c` asked for
are there: a code is single-use inside a locked database transaction, it expires by
default in 24 hours (not 7 days), it is bound to one named employee from the moment
HR makes it, HR is told the moment it is used, and a blocked or replaced phone can
never be switched back on by anyone, including a System Manager. I do **not** think
this needs a new control such as SMS or OTP — the app has no verified phone number to
send one to, and the product's own reasoning for not collecting one is sound.

**What stops this from being "proven safe for real field workers today"** is not the
design. It is that the one piece of the whole flow that actually protects a
worker's secret on their phone — the Android Keystore-backed storage — **has never
been run on a real phone.** It is well-tested in a way that proves the *logic* is
right (it refuses to fall back to an unsafe method), but nobody has proven the
*storage itself* survives a phone restart on real Android hardware. That is a Blocker
for a pilot with real workers' phones, not for continuing to build.

## 1. What "QR with no HR approval" actually means, checked against the code

A **QR code** here is a link like `https://ppj.alvoraa.co/enrol#t=<random-code>`. HR
makes one from an employee's record. Whoever has the phone that scans it, and taps
"Yes, this is me", gets a working attendance app with no further HR action — that is
the "no approval" part the product manager flagged.

**Who would want this, and the cheapest way to get it (threat model, plainly).**
Not a stranger from the internet. The realistic attacker is someone already close to
the process:

- **A colleague who sees the QR before the real worker uses it** — over HR's
  shoulder, on a printed sheet on a desk, or forwarded on WhatsApp — and scans it
  first, becoming "Ramesh" on their own phone.
- **A worker who deliberately hands their code to a friend**, so the friend can punch
  attendance for them (buddy punching).
- **An HR user** who makes a code and joins it on their own phone, or edits a phone
  record to point at someone else.

**What's the worst that happens from one mistake?** One employee's attendance can be
marked by the wrong person, for the days between the leak and HR noticing. It cannot
spread to other employees (each code is for one named person) or to other companies
(each company is a separate database — I checked this is tested, see §3). The
attendance record feeds pay, so the real damage is wrong pay for a few days, not a
data breach in the usual sense: the "is this you" screen only reveals a first name,
a surname initial, a job title and a company name — less than what is already printed
on the paper HR hands over today.

**What does this make newly possible?** A phone can start marking someone present
with **no human decision at the exact moment it happens.** Today (the older web
page), a human at HR still has to click "Activate" — badly, since HR checks almost
nothing before doing it, but a click still happens. The QR design moves that human
decision earlier, to the moment HR makes the code, and locks it under a secret only
the intended person should see.

**How would anyone find out?** This is the part I checked most closely, because a
control nobody ever looks at is not a control. I read `field_app_alerts.py`: HR gets
a notification (the desk bell, and email if they have it on) the moment a code is
used, the moment someone taps "this is not me", if a used code is scanned again from
a *different* phone (a likely sign of a hijack), and if one phone tries to join a
*second* person. None of these messages carry the code, the secret, a photo or a
location — I checked the file does not put them there. **This is a real detection
control, not "a customer will tell us".**

## 2. Is 24-hour, single-use, HR-alerted enough — or does it need more?

**My independent answer: no additional control is needed for a pilot.** Here is why,
weighing what is already there against the two extra controls the brief asked me to
consider by name:

| Extra control | Would it help? | My recommendation |
|---|---|---|
| **Tie the code to a specific expected employee** | **Already done.** The code is bound to one named `Employee` the moment HR makes it (`field_app_join.py:make_code`), not just to "whoever scans first". The confirm screen shows that person's name so an honest mistake (forwarded to the wrong phone) is caught before anything is set up | No further work needed |
| **An SMS or OTP step** | Would need a verified phone number on file for every field worker. The product brief already rejected this on purpose (§3: "SMS cost per login, and a number must be on file" — many drivers and guards do not have one on record). Adding it now would mean collecting a new, verified personal data field for the sole purpose of this control — a bigger change than the QR design it is meant to backstop | Do not add it |

What actually limits the damage, and what I verified in the code rather than took on
trust:

1. **Single use, inside a locked database transaction** (`field_app_join.py:271-393`,
   `join_with_code`). I read the lock order and the test that proves it
   (`test_013_ac70...` in `tests/test_field_app_step3_013.py`): two phones racing to
   use the same code cannot both win. One gets in; the other is told the code is
   already used.
2. **The code itself cannot be guessed.** It is 256 bits of randomness
   (`secrets.token_urlsafe(32)`), never stored in the clear — only its hash. Brute
   force is not a realistic path regardless of rate limits.
3. **24 hours by default, 7 days at most, and the server enforces the ceiling**
   (`_lifetime()`, `field_app_join.py:474-489`) — a browser cannot ask for longer than
   the organisation's own setting allows. This is the change `01c` asked for and the
   user approved on 17 Sep, replacing the brief's original 7-day default.
4. **A block is permanent and cannot be reopened by anyone** — I read the doctype's
   own rules (`alvoraa_field_device.py:163-198`): once a phone is Blocked, Replaced
   or Removed, no form, bulk edit, import or API call can move it back to Active,
   including for a System Manager. The only way forward is a new code.
5. **HR finds out immediately** (§1 above), and can block a phone in one action, from
   the Employee record, with no further approval step.

**What this does NOT prevent, and I want to say so plainly rather than let the
controls above sound like more than they are:** if a worker willingly hands their own
phone or their own code to a friend so the friend can punch for them, nothing in this
design stops it — only a photo taken at the moment of the punch might later reveal
it, and only if someone looks at the photo. This is a known, named, accepted
limitation (`01c` calls it R2), not something this review can fix with a technical
control — it is a management and audit question, same as it would be with a
fingerprint machine a colleague could also press for a friend.

**My conclusion:** the design is proportionate to what it protects (attendance, not
banking or medical data) and proportionate to who the realistic attacker is (an
insider or a careless forward, not an outside hacker). I would not spend more
engineering effort hardening the join step itself before a pilot. I would spend it on
the two things in §4 that are not yet proven.

## 3. SEC/PRIV requirements from `01c` — verified against the code, one by one

"Met" means I found the mechanism in the code and a test that exercises it. "Partial"
means the mechanism exists but something about it is unproven, incomplete, or only
covers part of the requirement. "Not met" means I looked and it is not there.

| # | Requirement (short form) | Status | Where, and what proves it |
|---|---|---|---|
| SEC-1 | Code is 256-bit random, never stored in the clear | **Met** | `secrets.token_urlsafe(32)`, `_hash()` (SHA-256) in `field_app_join.py`; only the hash goes in `Alvoraa App Invite.token_hash` |
| SEC-2 | Code only travels in the URL fragment and POST bodies | **Met** | `host-check.js` parses `#t=<code>` only, rejects a query string (`url.search !== ""`); `api.js` posts JSON bodies only |
| SEC-3 | Checking a code changes nothing and reveals little | **Met** | `check_code()` returns only first name, surname initial, designation, company, notice and version — no employee ID, no full name |
| SEC-4 | Server clamps the lifetime, 1h–7d, default 24h | **Met** | `_lifetime()` refuses anything above the organisation's own setting; the user's 17 Sep decision (24h default) is the live default in `field_app_settings.py` |
| SEC-5 | Single use, inside one locked transaction | **Met** | `join_with_code()`'s fixed lock order (employee → invites → phones); `test_013_ac70...` proves two racing joins do not both win |
| SEC-6 | One waiting code per person | **Met** | `make_code()` cancels every other waiting code for that employee inside the same locked save |
| SEC-7 | Codes cancel from every place they should | **Met** | HR cancel (`cancel_code`), "this is not me" (`refuse_code`), leaver hook (`block_devices_for_leaver`, rewritten — see Finding A below) |
| SEC-8 | A block is final, on every path | **Met** | `alvoraa_field_device.py`: `FINAL` states cannot be exited by a form, bulk edit, import or API call; enforced in `validate()`, not a hidden button |
| SEC-9 | HR cannot forge, re-point or delete a phone record | **Met** | Permissions JSON has no `create` or `delete` for any role; `employee`, `join_method`, `invite`, `registered_on` are frozen after insert; `on_trash()` refuses deletion outright |
| SEC-10 | Only `Active` phones may do anything | **Met** | `_device_from_token()` refuses every other status with its own code |
| SEC-11 | Secrets never reach a log | **Met, with one thing I could not independently verify** | `_private_request()` strips named fields from `form_dict` before any error path runs, and `_log_server_error()` logs only exception class + file:line, never values. `remove_my_phone`'s `_private_request()` lists no fields, but its only argument is named `token` — the code comments assert Frappe's own field-name redaction (fields containing "token"/"secret"/"key") catches it independently. **I could not check this against Frappe's own source in this checkout** (it is not installed here) — worth a five-minute confirmation on the bench before pilot, not a blocker |
| SEC-12 | Rate limits keyed on a hash, not the secret | **Met** | `field_app_limits.py`: `_limited()` hashes the code/token into a differently-named field before calling Frappe's limiter, so the real secret never reaches Redis |
| SEC-13 | HR is told, not left to look | **Met** | `field_app_alerts.py`, four events, each with a test; messages carry no code, secret, photo or location (checked by reading the message-building functions) |
| SEC-14 | The app talks to one real tenant only | **Met** | `host-check.js`: strict URL parsing, refuses user-info, ports, extra labels, punycode, `alvoraa.co` itself, look-alikes; a refusal makes no network call. 26 hostile links in `test/host-check.test.js`, all pass |
| SEC-15 | A code works only on the site that made it | **Partial** | The mechanism (per-tenant database, no shared invite table) is real, but the specific test `01c` asked for (an unknown Host header on the local bench) is explicitly marked **not verified** in `01c` §13 and I found nothing that closes it since. Low risk in practice — I could not find a code path that looks up an invite without the tenant's own site context — but it is still an open item, not a proven one |
| SEC-16 | The native shell has no open doors | **Met** | `capacitor.config.json` has no `server` block; `CapacitorHttp`/`CapacitorCookies` disabled; `check_app.mjs` enforces this in CI and passes |
| SEC-17 | Server text is always drawn as text, never HTML | **Met** | `join.js` uses `textContent` exclusively (I read every DOM-writing line); `check_app.mjs`'s `HTML_SINK` lint rule passes with no exceptions |
| SEC-18 | No CORS surprises | **Met** | `deploy/nginx.conf` has no `field_checkin`/`field_app` entries at all yet (checked directly) — meaning no CORS rule has been added either. Native HTTP is used, matching the plan |
| SEC-19 | Old app versions can be stopped | **Met** | `errors.check_app_version()` called at the top of every device endpoint |
| SEC-20 | The app cannot quietly gain new permissions | **Met** | `AndroidManifest.xml` lists exactly the five allowed permissions; `check_app.mjs` fails the build on anything else, and I ran it — passes |
| SEC-21 | A faked GPS position is flagged | **Not exercised by this build** | The server-side flag exists (`alvoraa_mock_location`), but the app-client work reviewed here (`join.js`, `api.js`) only covers the join flow, not the punch screen (US-39, not built yet). Nothing to find wrong here yet — just not built |
| SEC-22 | "Remove this phone" is real | **Met, mechanism only** | `remove_my_phone()` in `field_app_device.py` is correct and tested server-side. The app-client button for it does not exist yet (`join.js`'s `welcome` screen has no remove-phone action — that is US-43, explicitly not built in this increment) |
| SEC-23 | Signing keys never reach the repo | **Met** | `check_tracked_keys.py` passes; a dedicated CI job exists (`ci.yml`'s key-guard) |
| SEC-24 | No caching of answers | **Met** | `_never_cache()` sets `Cache-Control: no-store` on every device/join endpoint |
| SEC-25 | New `ignore_permissions` uses are counted | **Not met — pre-existing gap, unchanged** | No CI counter exists (confirmed: no such check in `.github/workflows/*.yml`). This slice's own new uses (`field_app_join.py`, guest inserts) are each individually justified in comments, but nothing stops the count rising elsewhere without review. This is a repo-wide gap `01c` and the compliance map already named (I3); this slice did not make it worse, and did not fix it either |
| PRIV-1 | Only listed fields collected (model name, platform, version) | **Met, currently over-satisfied** | The app sends `device_label: ""` today — no real model name yet (`03-implementation-notes.md` §8.3 point 6). Nothing from the "never collect" list appears in `api.js` or `join.js` |
| PRIV-2 | The notice is server-owned and current | **Not met, but not yet triggered** | `field_app_notice.py`'s `CURRENT_VERSION` is still `"2026-09-13"`, the version `01b` explicitly said not to build against, and it still does not disclose phone-model collection. This does not mislead anyone **today** only because no model name is actually being sent yet — the moment `device_label` is wired up to a real value (a small, "worth a quick decision" item flagged in the implementation notes), the notice becomes wrong the same day. **Fix before device_label is ever turned on**, not before this review |
| PRIV-4 | No app-facing text uses the word "consent" | **Met** | I grepped every string in `mobile/field-app/web/`: zero occurrences of "consent". The tick text is exactly "I have read this and I understand." |
| PRIV-5 | Confirm screen shows the least | **Met** | `check_code()`'s answer and `renderConfirm()` in `join.js` match exactly: first name, initial, designation, company — no photo, no ID |
| PRIV-6 | No workplace coordinates sent to the phone | **Met, for the join flow reviewed here** | `join_with_code()`'s answer includes `workplace` from `_workplace()`, which (per `04-impact-analysis-server.md`) was corrected to drop latitude/longitude. I did not re-verify the punch-time (`field_status`) answer, as that endpoint is outside this app-client build |
| PRIV-7 | Photo and QR picture never touch disk | **Met, for the QR side** | `qr-decode.js` and `join.js`'s picker path decode entirely in memory (`getUserMedia`, `canvas`, `URL.createObjectURL` immediately revoked) — no file write. The punch photo path (`photo.js`) is unit-tested but not wired into a real screen yet (US-39 not built) |
| PRIV-8 | Location only "while using the app" | **Met at the manifest level** | `ACCESS_BACKGROUND_LOCATION` is not requested and CI fails the build if it appears. No location code is exercised by the join flow itself (join needs no GPS) |

**On the device secret specifically (the question this review was explicitly asked to
answer):**

> "Is the device secret actually stored the way the code review claims — Keystore-backed
> on Android, refusing any less-secure fallback?"

**Partially proven, and the honest gap matters.** I read `device-secret.js` in full.
The *logic* is right and well-tested:

- It calls `Capacitor.isNativePlatform()` before touching storage at all, and refuses
  (rejects the promise, or returns `null`/`false`) if that check fails — it never
  falls through to the plugin's own web fallback, which the implementation notes
  correctly identify as *plain `localStorage` plus base64, no encryption at all.*
- `mobile/field-app/test/device-secret.test.js` proves this with a fake plugin object
  that *would* have quietly worked if the safety check were missing — a real test of
  the failure mode, not a happy-path test.

What is **not proven, because it cannot be proven without a real phone:**

- Whether `capacitor-secure-storage-plugin` actually round-trips a secret through the
  Android Keystore on a real device, survives an app restart, and works on the
  32-bit/low-end phones the pilot is meant to run on. The engineer's own notes
  (`03-implementation-notes.md` §7.4–7.5, §8.3) say this outright and I have nothing
  to add beyond confirming they are right to flag it — I read the plugin's vendored
  source reference and the reasoning is sound, but reasoning about Java source is not
  the same as watching it work.
- Whether the two vendored scripts (`capacitor-core.js` then `secure-storage-plugin.js`)
  actually load in the right order inside a real WebView. If they do not, the
  documented failure mode is total: no screen after "Welcome" can save a secret, and
  every phone would need to rejoin.

## 4. Findings, ranked

**Blocker (must clear before any real field worker's phone is used, i.e. before
pilot) — 1 item**

1. **The device secret has never been written to, or read from, a real Android
   Keystore.** Everything downstream of "the app is set up" depends on this working.
   If it does not — wrong load order, or the Keystore behaving differently on a
   cheap 32-bit phone — a worker sees "Welcome, you are set up" and then cannot
   check in, or worse, the app silently keeps working against an insecure fallback
   that was never actually exercised in this build (the code refuses the fallback,
   but that refusal path itself has never run outside a Node test). *This is not a
   design flaw — it is an unverified claim, and the engineer has already said so
   in writing.* **Recommendation: run the actual join flow on all three pilot
   phones, including a full app kill and restart, before anyone outside the team
   uses the app.** This is a same-day check once a phone and the Android SDK are
   available — it does not need new code.

**Should-fix-before-pilot — 3 items**

2. **The notice text is stale and will become wrong the moment `device_label` is
   populated with a real phone model.** `field_app_notice.py`'s `CURRENT_VERSION`
   is unchanged since before this slice started, and does not mention collecting
   the phone's model name. Today this causes no actual harm — the app sends an
   empty string for `device_label` — but the moment someone adds the one line that
   reads the real model (flagged as a "quick decision" still open in the
   implementation notes), the notice a worker agreed to will no longer match what
   is collected. **Recommendation: fix the notice text and the model-name
   collection in the same change, not separately — don't let the config drift
   happen even for a day.**
3. **SEC-15 (a code only works on the site that made it) is not proven, only
   argued.** I agree with `01c`'s own assessment that the risk is low — I could
   not find a code path that resolves an invite outside its own tenant's database
   — but "I could not find a path" is not the same as a test that tries. Cross-tenant
   leakage is the single worst thing this kind of bug could do, and it is cheap to
   test. **Recommendation: the local-bench test `01c` already specifies (an
   unrecognised Host header) before the pilot, not after.**
4. **`SEC-11`'s claim about `remove_my_phone` relies on Frappe's own field-name
   redaction, which nobody in this codebase has independently checked still exists
   and still behaves as described.** Low likelihood of being wrong (it is a
   documented Frappe convention, and other code here uses the same convention on
   purpose), but a five-minute check on the bench (force an error inside
   `remove_my_phone` with a real token and look at the Error Log) turns an assumption
   into a fact. **Recommendation: do this check once, alongside the pilot-phone
   test above, and record the answer in this document.**

**Notes — worth recording, not worth delaying the pilot over**

5. **SEC-25 (`ignore_permissions` counter) remains unbuilt**, a pre-existing,
   repo-wide gap this slice did not create and did not close. It sits on the
   backlog already (`compliance-feature-map.md` I3).
6. **SEC-21 (mock-location flag) and SEC-22's client-side "Remove this phone"
   button are correctly absent** — they belong to stories (US-39, US-43) that are
   deliberately not part of this build. Nothing to fix; just don't mistake "not
   built yet" for "built wrong".
7. The engineer's own documents (`00-impact-analysis-app-client.md`,
   `03-implementation-notes.md` §8) are unusually candid about what is and is not
   proven. I want to say plainly that this made the review faster and more honest
   than it would otherwise have been — the "what is NOT proven" section in §8.3 of
   the implementation notes independently reaches the same conclusion as my
   Blocker above, before I wrote it. That is the right way to hand off code for
   review.

## 5. Compliance verification table (obligations engaged)

| Obligation | Engaged by this slice? | Verified position |
|---|---|---|
| DPDP Act 2023 — notice & lawful basis | Yes — photo/location at punch, not at join itself | Basis is the employment "legitimate use" framing per the user's 17 Sep decision, with a plain notice (not consent language). The join flow reviewed here correctly avoids the word "consent" anywhere in the UI (PRIV-4, verified). Legal basis still awaits a DPDP lawyer's review before the first paying customer (unchanged; recorded in `01c` §8, Q-C1) |
| DPDP Rules 2025 — timing | Not urgent | Full obligations phase in around May 2027; nothing here is overdue |
| CERT-In Directions 2022 | Yes, indirectly | No new infrastructure duty from this slice. The pre-existing gap (180-day India log residency; baseline §3a) is unaffected by this code |
| OWASP ASVS 5.0 Level 2 | Partially checked | The authentication/session-relevant requirements (token entropy, no plaintext secret storage, session-equivalent revocation) are met in the server code I read; I did not do a line-by-line ASVS pass |

No new obligation is triggered by this slice beyond what `01c` already named. I did
not find anything in the app-client code that changes the compliance picture `01c`
already drew — the code matches the design that compliance analysis was written
against, with the gaps named in §4 above.

## 6. Residual risk

| # | Risk | Size | Owner (proposed) | Accepted by / date |
|---|---|---|---|---|
| R1 (from `01c`, unchanged) | A leaked, unused code lets someone join as the worker until noticed | Low, with the 24h default now in code | Surbhi | Not yet — no explicit sign-off found in this slice's documents since the 17 Sep decision |
| R2 (from `01c`, unchanged) | Buddy punching by agreement is not prevented by this design | Medium | Customer HR practice; Surbhi for the product rule | Not yet |
| New — R10 | Device secret storage is unverified on real Android hardware | **High until the pilot-phone test runs; drops to Low once it does** | Engineer, before pilot | Not yet — this is the Blocker in §4 |
| New — R11 | Notice text will silently under-disclose the moment `device_label` carries a real value | Low today, rising to Medium the day that code is added | Engineer | Not yet |

## 7. What I could not verify, and what would settle it

- **Whether Frappe's own field-name redaction actually masks a field named `token`
  in an Error Log row.** `frappe` is not installed in this checkout (confirmed by
  `04-impact-analysis-server.md`'s own note); settled by forcing an error on the
  bench and reading the resulting Error Log row.
- **The real Keystore round-trip**, as above — settled by running the app on the
  three pilot phones.
- **SEC-15's cross-tenant claim** — settled by the local-bench test `01c` already
  names (never against production).
- **Whether nginx's per-IP protection for the join endpoints (`01c`'s SEC-12, the
  network layer, US-24) has landed.** I checked `deploy/nginx.conf` directly: it has
  no `field_checkin`/`field_app` rules at all yet. This matches the documented plan
  (US-24 goes last, its own approval, because the same nginx file also serves
  production) — not a defect, but also not yet true, and worth remembering it is
  still owed before a wider rollout than a small pilot.

## Final verdict

**The QR-with-no-approval design is defensible as specified, and the code I read
matches that design closely and honestly.** I would not ask for a different control
than the ones already built — not SMS, not OTP, not a stricter default lifetime than
24 hours. The product manager's challenge was answered properly in `01c`, and this
review's job was to check the app-client code did not quietly drift from that answer.
It did not, on any point that matters to the join flow itself.

**What I will not sign off on yet is running this on a real field worker's phone**,
because the one piece that protects the phone's own secret has only ever been tested
against a fake plugin, never against a real Android Keystore. That is a same-day
check, not a redesign — but it has to happen, on a real phone, before the first real
person's join.

**My recommendation:** run the Blocker's check (§4.1) and the two Should-fix items
(§4.2–4.3) before the pilot starts. None of them should take more than a day once a
phone and the Android SDK are available. Everything else in this review is either
already met or is a known, already-named, already-accepted gap that this slice did
not create.
